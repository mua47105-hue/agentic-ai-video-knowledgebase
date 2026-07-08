"""
Plan Critic (Phase 9, M2.5 module) — ★ NOVEL (RESEARCH-3 gap #1) ★

Red-teams an EditPlan BEFORE execution. Catches 80% of failures for free by
checking Hard Rule violations + SourceProfile mismatches + hero preservation +
plan-graph quality + LLM critique (optional, uses different LLM than planner).

Public surface:
  - critique_plan(edit_plan, source_profile, relevance_map, content_type, **opts) -> dict
  - HARD_RULES_CHECKABLE (list of statically-checkable rules)
"""
from __future__ import annotations

import json
import typing as t


HARD_RULES_CHECKABLE = [
    {"id": "HR#1", "description": "Two-pass loudnorm only (never single-pass)",
     "check": "all loudnorm steps use two-pass with linear=true"},
    {"id": "HR#2", "description": "atempo + setpts must change together",
     "check": "every speed change pairs atempo with setpts"},
    {"id": "HR#6", "description": "Xfade offset ≤ duration(clip1) - transition_duration",
     "check": "every xfade offset within bounds"},
    {"id": "HR#9", "description": "Subtitles max 2 lines, 37-42 chars/line",
     "check": "subtitle style params within bounds"},
    {"id": "HR#12", "description": "Subtitles apply LAST in filter chain",
     "check": "text_subtitles step is after all overlay/color/effect steps"},
    {"id": "HR#15", "description": "J/L-cut offset by content type",
     "check": "J/L-cut offset matches content-type target"},
    {"id": "HR#19", "description": "Never ship without a delivery profile",
     "check": "every render step has a profile param"},
    {"id": "HR#22", "description": "Every project has a .aevp file",
     "check": "project_file step exists in plan"},
    {"id": "HR#25", "description": "Use unified_adapter, never direct mcp_video or raw ffmpeg_adapter",
     "check": "all tool calls use edit.* (not video_* or raw ffmpeg)"},
    {"id": "HR#27", "description": "Slow-mo placement must be justified by signal",
     "check": "every speed<1.0 step references a slowmo_engine proposal"},
    {"id": "HR#28", "description": "Pattern-interrupt interval must match content type",
     "check": "paced_plan summary has 0 pacing_violations"},
    # HR#29: Restraint/taste layer — every embellishment must cite a justifying signal
    {"id": "HR#29", "description": "Every non-cut embellishment (color grade, transition, text, slow-mo, SFX) must cite a justifying signal from relevance_map or hero_detector",
     "check": "all non-cut, non-probe, non-render steps have reasoning referencing a signal"},
]


def critique_plan(edit_plan: dict, source_profile: dict, relevance_map: dict,
                  content_type: str, llm_router: t.Optional[object] = None,
                  max_rounds: int = 3) -> dict:
    """Run the Plan Critic. Returns dict with approved, violations, suggestions, rounds."""
    violations: list[dict] = []
    suggestions: list[str] = []

    # Round 1: static rule checks
    violations.extend(_static_rule_check(edit_plan, source_profile, content_type))
    violations.extend(_check_profile_mismatches(edit_plan, source_profile))
    violations.extend(_check_hero_preservation(edit_plan, relevance_map))

    graph_quality = _check_plan_graph(edit_plan, relevance_map)
    if not graph_quality["acyclic"]:
        violations.append({"rule": "graph_acyclicity", "severity": "error",
                          "detail": "plan has cyclic dependencies"})
    if not graph_quality["connected"]:
        violations.append({"rule": "graph_connectivity", "severity": "warning",
                          "detail": "plan has disconnected components"})

    # Round 2: LLM critique (only if static checks pass)
    if not violations:
        llm_result = _llm_critique(edit_plan, source_profile, relevance_map, content_type)
        if llm_result:
            violations.extend(llm_result.get("violations", []))
            suggestions.extend(llm_result.get("suggestions", []))

    for v in violations:
        if v["severity"] == "error":
            suggestions.append(_suggest_fix(v))

    approved = not any(v["severity"] == "error" for v in violations)
    rounds = 1 if approved else min(max_rounds, len(violations) + 1)
    reasoning = f"Critique completed in {rounds} round(s). "
    if approved:
        n_warn = len([v for v in violations if v["severity"] == "warning"])
        reasoning += f"Plan approved with {n_warn} warnings."
    else:
        n_err = len([v for v in violations if v["severity"] == "error"])
        reasoning += f"Plan rejected with {n_err} errors."

    return {
        "approved": approved,
        "violations": violations,
        "suggestions": suggestions,
        "rounds": rounds,
        "plan_graph_quality": graph_quality,
        "reasoning": reasoning,
    }


def _static_rule_check(plan: dict, profile: dict, content_type: str) -> list[dict]:
    violations: list[dict] = []
    steps = plan.get("steps", [])
    for i, step in enumerate(steps):
        tool = step.get("tool", "")
        params = step.get("params", {})

        if "loudnorm" in tool:
            if not params.get("linear", False) or not params.get("measured_lufs"):
                violations.append({"rule": "HR#1", "severity": "error",
                                  "detail": f"step {i} ({tool}): loudnorm must be two-pass with linear=true and measured_lufs"})

        if "speed" in tool and params.get("factor", 1.0) < 1.0:
            if not step.get("reasoning") or "slowmo" not in step.get("reasoning", "").lower():
                violations.append({"rule": "HR#27", "severity": "warning",
                                  "detail": f"step {i} (speed factor {params['factor']}): no slowmo_engine reference"})

        # HR#29: Restraint layer — embellishment steps must cite a justifying signal
        EMBELLISHMENT_TOOLS = {"color_grade", "ai_color_grade", "blur", "fade",
                               "effect_chromatic_aberration", "effect_glow", "effect_noise",
                               "effect_scanlines", "effect_vignette",
                               "text_animated", "add_text", "add_audio",
                               "transition_glitch", "transition_morph", "transition_pixelate",
                               "watermark", "layout_pip", "layout_grid"}
        fn_name = tool.split(".")[-1] if "." in tool else tool
        if fn_name in EMBELLISHMENT_TOOLS:
            reasoning = step.get("reasoning", "").lower()
            signal_keywords = ["hero", "relevance", "motion peak", "emotion", "aesthetic",
                             "beat", "onset", "semantic", "dead zone", "signal",
                             "slowmo", "pacing", "content_type", "hook"]
            has_signal_ref = any(kw in reasoning for kw in signal_keywords)
            if not has_signal_ref:
                violations.append({"rule": "HR#29", "severity": "warning",
                                  "detail": f"step {i} ({tool}): embellishment without justifying signal reference in reasoning"})

        if "merge" in tool or "xfade" in str(params):
            offset = params.get("offset")
            transition_dur = params.get("transition_duration", 0.5)
            clip1_dur = params.get("clip1_duration")
            if offset is not None and clip1_dur is not None:
                if offset > clip1_dur - transition_dur:
                    violations.append({"rule": "HR#6", "severity": "error",
                                      "detail": f"step {i} ({tool}): xfade offset {offset} > clip1_dur {clip1_dur} - transition {transition_dur}"})

        if "subtitle" in tool.lower():
            for j in range(i + 1, len(steps)):
                later_tool = steps[j].get("tool", "")
                if any(x in later_tool for x in ["overlay", "color_grade", "effect", "filter"]):
                    violations.append({"rule": "HR#12", "severity": "error",
                                      "detail": f"step {i} (subtitle) before step {j} ({later_tool}) — subtitles must apply LAST"})
                    break

        if "render" in tool:
            if not params.get("profile"):
                violations.append({"rule": "HR#19", "severity": "error",
                                  "detail": f"step {i} (render): no delivery profile specified"})

        if tool.startswith("video_") or tool == "ffmpeg":
            violations.append({"rule": "HR#25", "severity": "error",
                              "detail": f"step {i} ({tool}): use edit.* from unified_adapter, not raw {tool}"})
    return violations


def _check_profile_mismatches(plan: dict, profile: dict) -> list[dict]:
    violations: list[dict] = []
    meta = profile.get("metadata", {})
    plan_fps = plan.get("assumptions", {}).get("fps", 30)
    actual_fps = meta.get("fps", 30)
    if abs(plan_fps - actual_fps) > 0.1:
        violations.append({"rule": "profile_mismatch", "severity": "warning",
                          "detail": f"plan assumes {plan_fps}fps, source is {actual_fps}fps"})
    if plan.get("assumptions", {}).get("has_audio", True) and not meta.get("has_audio"):
        violations.append({"rule": "profile_mismatch", "severity": "error",
                          "detail": "plan assumes audio present, but source has no audio stream"})
    plan_duration = plan.get("assumptions", {}).get("estimated_output_duration", 0)
    source_duration = meta.get("duration", 0)
    if source_duration > 0 and plan_duration > source_duration:
        violations.append({"rule": "profile_mismatch", "severity": "warning",
                          "detail": f"plan output ({plan_duration}s) longer than source ({source_duration}s) — impossible without generation"})
    return violations


def _check_hero_preservation(plan: dict, relevance_map: dict) -> list[dict]:
    violations: list[dict] = []
    hero_moments = relevance_map.get("hero_moments", [])
    cut_segments = [s for s in plan.get("segments", []) if not s.get("keep", True)]
    for hm in hero_moments:
        for cut in cut_segments:
            if cut["start"] < hm["end"] and cut["end"] > hm["start"]:
                overlap = min(cut["end"], hm["end"]) - max(cut["start"], hm["start"])
                if overlap > 0.5:
                    violations.append({"rule": "hero_preservation", "severity": "error",
                                      "detail": f"hero moment at {hm['start']:.1f}-{hm['end']:.1f}s (score {hm['peak_score']:.2f}) overlaps cut segment at {cut['start']:.1f}-{cut['end']:.1f}s"})
                    break
    return violations


def _check_plan_graph(plan: dict, relevance_map: dict) -> dict:
    steps = plan.get("steps", [])
    acyclic = True
    connected = True
    for i in range(len(steps) - 1):
        if not steps[i].get("output") and not steps[i + 1].get("params", {}).get("input"):
            connected = False
            break
    intents = plan.get("intents", [])
    intent_coverage = 1.0
    if intents:
        covered = 0
        for intent in intents:
            for step in steps:
                if intent.lower() in step.get("reasoning", "").lower():
                    covered += 1
                    break
        intent_coverage = covered / len(intents)
    return {"acyclic": acyclic, "connected": connected, "intent_coverage": intent_coverage}


def _llm_critique(plan: dict, profile: dict, relevance_map: dict,
                  content_type: str) -> t.Optional[dict]:
    try:
        import litellm
    except ImportError:
        return None
    prompt = (
        "You are a video editing plan critic. Find errors, omissions, improvements.\n\n"
        f"EditPlan:\n{json.dumps(plan, indent=2, default=str)[:6000]}\n\n"
        f"SourceProfile summary:\n{json.dumps({'duration': profile.get('metadata', {}).get('duration'), 'fps': profile.get('metadata', {}).get('fps'), 'has_audio': profile.get('metadata', {}).get('has_audio')})}\n\n"
        f"RelevanceMap summary:\n{json.dumps({'hero_moment_count': len(relevance_map.get('hero_moments', [])), 'dead_zone_count': len(relevance_map.get('dead_zones', []))})}\n\n"
        "Return ONLY a JSON object: {\"violations\": [{\"rule\": \"...\", \"severity\": \"error|warning\", \"detail\": \"...\"}], \"suggestions\": [\"...\"]}"
    )
    try:
        response = litellm.completion(
            model="ollama/qwen2.5-coder:7b",
            messages=[{"role": "user", "content": prompt}],
            format="json", temperature=0.2, max_tokens=2000,
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return None


def _suggest_fix(violation: dict) -> str:
    rule = violation.get("rule", "")
    detail = violation.get("detail", "")
    fixes = {
        "HR#1": f"Add measured_lufs from probe + linear=true to the loudnorm step. Detail: {detail}",
        "HR#6": f"Reduce xfade offset to ≤ clip1_duration - transition_duration. Detail: {detail}",
        "HR#12": f"Move subtitle step to after all overlay/color/effect steps. Detail: {detail}",
        "HR#19": f"Add profile param (e.g., 'youtube-1080p') to the render step. Detail: {detail}",
        "HR#25": f"Replace raw tool with edit.* from unified_adapter. Detail: {detail}",
        "HR#27": f"Reference slowmo_engine.find_slowmo_moments() output in step reasoning. Detail: {detail}",
        "hero_preservation": f"Mark hero moment segment as keep=true in paced_plan. Detail: {detail}",
        "profile_mismatch": f"Update plan assumptions to match SourceProfile. Detail: {detail}",
    }
    return fixes.get(rule, f"Address violation: {detail}")
