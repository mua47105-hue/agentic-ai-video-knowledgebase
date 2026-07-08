"""
Intelligent Planner (Phase 9, M2 module) — produces EditPlan + Storyboard.

Consumes:
  - SourceProfile (Phase 6)
  - RelevanceMap + cut points (Phase 7)
  - PacedCutPlan + slow-mo proposals + music sync plan (Phase 8)
  - EditPatternMemory hints (Phase 9 §9.4)
  - Hard Rules #1-#28

Produces an EditPlan via LLM (if available), then runs Plan Critic (§9.1) to
red-team it; if not approved, revises with suggestions (max 3 rounds).

If LLM is unavailable, falls back to a recipe-YAML-style plan assembled from
the Phase 6-8 outputs (cut points, paced plan, slow-mo proposals).

Public surface:
  - generate_plan(source_profile, relevance_map, cut_points, paced_plan,
                  slowmo_proposals, music_sync_plan, content_type, intents,
                  memory_hints, plan_llm_model, max_critique_rounds) -> dict
"""
from __future__ import annotations

import json
import typing as t


def generate_plan(source_profile: dict, relevance_map: dict,
                  cut_points: list[dict], paced_plan: dict,
                  slowmo_proposals: list[dict], music_sync_plan: dict,
                  content_type: str, intents: list[str],
                  memory_hints: list[dict],
                  plan_llm_model: str = "ollama/qwen2.5-coder:7b",
                  max_critique_rounds: int = 3,
                  editing_blueprint: t.Optional[dict] = None) -> dict:
    """Generate an EditPlan via LLM (with critique-and-revise), or fallback to rule-based.

    Phase 5 additions:
    - Uses LLMRouter (CutClaw pattern) for per-task model routing
    - Accepts an editing_blueprint (Crayotter's Editing Research sub-phase) as prior input
    - Produces a storyboard as a first-class artifact (Project Montage pattern)
    """
    from kb.tools.plan_critic import critique_plan
    from kb.tools.llm_router import get_router

    router = get_router()

    # Try LLM-based planning
    if router.available():
        plan_dict = None
        critic_result = None
        for round_num in range(1, max_critique_rounds + 1):
            prompt = _build_prompt(source_profile, relevance_map, cut_points,
                                   paced_plan, slowmo_proposals, music_sync_plan,
                                   content_type, intents, memory_hints, critic_result,
                                   editing_blueprint)
            # Use router for plan task (routes to best available model)
            plan_dict = _call_plan_llm_via_router(prompt, router)
            if not plan_dict:
                break
            critic_result = critique_plan(plan_dict, source_profile, relevance_map, content_type)
            critic_result["rounds"] = round_num
            if critic_result["approved"]:
                plan_dict["plan_critic_result"] = critic_result.__dict__ if hasattr(critic_result, "__dict__") else critic_result
                plan_dict["editing_blueprint"] = editing_blueprint
                return plan_dict
        if plan_dict is not None:
            plan_dict["plan_critic_result"] = critic_result.__dict__ if hasattr(critic_result, "__dict__") else critic_result
            plan_dict["editing_blueprint"] = editing_blueprint
            return plan_dict

    # Fallback: rule-based plan from Phase 6-8 outputs
    plan = _fallback_plan(source_profile, relevance_map, cut_points, paced_plan,
                          slowmo_proposals, music_sync_plan, content_type, intents,
                          memory_hints)
    plan["editing_blueprint"] = editing_blueprint

    # S3: On-demand research loop — check for composite pattern matches before
    # falling back to boring atomic steps. If no match, log a research gap.
    try:
        from kb.tools.edit_memory import EditPatternDB
        db = EditPatternDB()
        # Ensure built-in patterns are seeded
        db.seed_builtin_patterns()

        # Detect available triggers from the intelligence layer
        triggers = []
        if slowmo_proposals:
            triggers.append("high_motion_peak")
        if any(h.get("level", 0) >= 2 for h in (relevance_map or {}).get("hero_moments", [])):
            triggers.append("hero_moment")
            triggers.append("semantic_salience_peak")
        if music_sync_plan and music_sync_plan.get("structure"):
            triggers.append("beat_drop_detected")
        if source_profile.get("visual", {}).get("scene_boundaries", []):
            triggers.append("scene_boundary")
        if any(p.get("moment_type") == "impact" for p in slowmo_proposals):
            triggers.append("has_forward_action_clip")

        # Query composite patterns matching our triggers
        composite_matches = db.query_composite_patterns(content_type, triggers=triggers)
        if composite_matches:
            plan["composite_patterns_matched"] = [m["name"] for m in composite_matches]
            plan["composite_patterns"] = composite_matches
        else:
            # S3: Research gap — no matching technique in edit_memory or signature-move library
            plan["research_gap"] = {
                "triggers_available": triggers,
                "content_type": content_type,
                "message": "No composite pattern matched. Consider researching new techniques.",
                "suggested_search": f"video editing technique for {content_type} with {', '.join(triggers[:3])}",
            }
    except Exception as e:
        import sys
        print(f"[debug] composite pattern lookup failed: {e}", file=sys.stderr)

    return plan


def _llm_available() -> bool:
    try:
        import litellm  # noqa
        return True
    except ImportError:
        return False


def _build_prompt(source_profile, relevance_map, cut_points, paced_plan,
                  slowmo_proposals, music_sync_plan, content_type, intents,
                  memory_hints, previous_critique, editing_blueprint=None):
    meta = source_profile.get("metadata", {})
    audio = source_profile.get("audio", {})
    semantic = source_profile.get("semantic", {})
    feedback = ""
    if previous_critique and not previous_critique.get("approved", True):
        feedback = "\n\n## Previous Critique (round " + str(previous_critique.get("rounds", 1)) + ")\nPlan was rejected. Fix these:\n"
        for v in previous_critique.get("violations", []):
            feedback += f"- [{v['severity']}] {v['rule']}: {v['detail']}\n"
        for s in previous_critique.get("suggestions", []):
            feedback += f"- SUGGESTION: {s}\n"
    blueprint_section = ""
    if editing_blueprint:
        blueprint_section = (
            f"\nEditing Blueprint (from Editing Research sub-phase):\n"
            f"- Narrative: {editing_blueprint.get('narrative_strategy', 'N/A')}\n"
            f"- Visual: {editing_blueprint.get('visual_strategy', 'N/A')}\n"
            f"- Pacing: {editing_blueprint.get('pacing_strategy', 'N/A')}\n"
            f"- Narration: {editing_blueprint.get('narration_strategy', 'N/A')}\n"
        )
    from kb.tools.plan_critic import HARD_RULES_CHECKABLE
    return (
        "You are an expert video editing planner. Produce a complete EditPlan as JSON.\n\n"
        f"Source: duration={meta.get('duration')}s, content_type={content_type}, fps={meta.get('fps')}, "
        f"aspect={meta.get('aspect_ratio')}, has_audio={meta.get('has_audio')}, speakers={audio.get('speaker_count', 1)}, tempo={audio.get('tempo', 120)}\n\n"
        f"Packed Transcript:\n{(semantic.get('packed_brief', '(no transcript)') or '')[:3000]}\n\n"
        f"Hero moments: {json.dumps(relevance_map.get('hero_moments', [])[:5], default=str)}\n"
        f"Dead zones: {json.dumps(relevance_map.get('dead_zones', [])[:5], default=str)}\n"
        f"Cut points (top 10): {json.dumps(cut_points[:10], default=str)}\n"
        f"Paced plan summary: {json.dumps(paced_plan.get('summary', {}), default=str)}\n"
        f"Slow-mo proposals: {json.dumps(slowmo_proposals[:5], default=str)}\n"
        f"Music sync: {json.dumps({'sections': (music_sync_plan.get('structure') or {}).get('sections', []), 'aligned_cuts': music_sync_plan.get('aligned_cuts', [])[:5]}, default=str)}\n"
        f"Memory hints: {json.dumps(memory_hints[:5], default=str)}\n"
        f"Intents: {intents}\n"
        f"{blueprint_section}\n"
        "Hard Rules:\n" + "\n".join(f"- {r['id']}: {r['description']}" for r in HARD_RULES_CHECKABLE) + "\n\n"
        "Return ONLY a JSON object: {\"steps\": [{\"operation\": str, \"tool\": \"edit.X\", \"params\": {}, \"output\": str, \"reasoning\": str}], "
        "\"storyboard\": \"markdown scene-by-scene visual description\", \"assumptions\": {\"fps\": N, \"has_audio\": bool, \"estimated_output_duration\": N}, "
        "\"intents\": [str], \"estimated_cost\": {\"whisper_seconds\": N, \"vlm_calls\": N, \"ffmpeg_seconds\": N}}"
        + feedback
    )


def _call_plan_llm_via_router(prompt: str, router) -> t.Optional[dict]:
    """Call LLM via the router (CutClaw per-task routing pattern)."""
    return router.route_json("plan", prompt, temperature=0.4, max_tokens=8000, timeout=300)


def _call_plan_llm(prompt: str, model: str) -> t.Optional[dict]:
    try:
        import litellm
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json", temperature=0.4, max_tokens=8000,
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        try:
            import subprocess
            result = subprocess.run(
                ["ollama", "run", "qwen2.5-coder:7b", prompt],
                capture_output=True, text=True, timeout=300)
            return json.loads(result.stdout)
        except Exception:
            return None


def _fallback_plan(source_profile: dict, relevance_map: dict,
                   cut_points: list[dict], paced_plan: dict,
                   slowmo_proposals: list[dict], music_sync_plan: dict,
                   content_type: str, intents: list[str],
                   memory_hints: list[dict]) -> dict:
    """Rule-based fallback plan assembled from Phase 6-8 outputs. Used when LLM unavailable."""
    meta = source_profile.get("metadata", {})
    duration = meta.get("duration", 0)
    kept_segments = [s for s in paced_plan.get("segments", []) if s.get("keep", True)]
    estimated_output = sum(s["end"] - s["start"] for s in kept_segments) if kept_segments else duration

    steps: list[dict] = []
    # 1. Probe
    steps.append({"operation": "probe", "tool": "edit.info", "params": {},
                  "output": "source_profile", "reasoning": "extract source metadata"})
    # 2. Transcribe (if audio)
    if meta.get("has_audio"):
        steps.append({"operation": "transcribe", "tool": "edit.transcribe",
                      "params": {"model": "base"}, "output": "transcript",
                      "reasoning": "transcribe for subtitle + content understanding"})
    # 3. Cut segments per paced plan (trim each kept segment)
    for i, seg in enumerate(kept_segments[:20]):  # cap at 20 segments
        steps.append({
            "operation": f"trim_seg_{i}", "tool": "edit.trim",
            "params": {"start": seg["start"], "duration": seg["end"] - seg["start"], "accurate": True},
            "output": f"seg_{i}",
            "reasoning": f"kept segment ({seg['reason']}): {seg['start']:.1f}-{seg['end']:.1f}s",
        })
    # 4. Slow-mo proposals
    for i, p in enumerate(slowmo_proposals[:5]):
        speed = p["speed_factor"]
        atempo_chain = []
        remaining = speed
        while remaining < 0.5:
            atempo_chain.append(0.5)
            remaining /= 0.5
        atempo_chain.append(round(remaining, 4))
        steps.append({
            "operation": f"slowmo_{p['moment_type']}_{i}", "tool": "edit.speed",
            "params": {"factor": speed, "atempo_chain": atempo_chain},
            "output": f"slowmo_{i}",
            "reasoning": f"slowmo_engine proposal: {p['reasoning']}",
        })
    # 5. Merge
    if len(kept_segments) > 1:
        steps.append({"operation": "merge", "tool": "edit.merge",
                      "params": {"transition": "fade", "transition_duration": 0.4},
                      "output": "merged", "reasoning": "merge kept segments with fade transition"})
    # 6. Color grade
    steps.append({"operation": "color_grade", "tool": "edit.color_grade",
                  "params": {"style": "warm"}, "output": "graded",
                  "reasoning": "apply warm color grade for talking-head content"})
    # 7. Loudnorm (two-pass per HR#1)
    if meta.get("has_audio"):
        LUFS_TARGETS = {"vlog": -14, "social-short": -14, "podcast": -16, "tutorial": -16,
                        "cinematic": -23, "documentary": -16, "interview": -16,
                        "talking-head": -16, "music-video": -14, "event": -16}
        target_lufs = LUFS_TARGETS.get(content_type, -16)
        measured = source_profile.get("audio", {}).get("integrated_lufs", target_lufs)
        steps.append({"operation": "loudnorm", "tool": "edit.loudnorm_limited",
                      "params": {"target_lufs": target_lufs, "true_peak": -1.0,
                                 "measured_lufs": measured, "linear": True},
                      "output": "loudnormed",
                      "reasoning": f"two-pass loudnorm to {target_lufs} LUFS (HR#1)"})
    # 8. Subtitles (LAST per HR#12)
    if meta.get("has_audio"):
        steps.append({"operation": "subtitles", "tool": "edit.text_subtitles",
                      "params": {"style": {"max_lines": 2, "chars_per_line": 42}},
                      "output": "subtitled", "reasoning": "burn subtitles last (HR#12)"})
    # 9. Render with delivery profile (HR#19)
    profile_map = {"youtube": "youtube-1080p", "tiktok": "tiktok-1080x1920",
                   "instagram": "instagram-1080x1920"}
    render_profile = "youtube-1080p"
    steps.append({"operation": "render", "tool": "edit.render",
                  "params": {"profile": render_profile}, "output": "final",
                  "reasoning": f"final render with {render_profile} delivery profile (HR#19)"})

    storyboard = f"# Storyboard ({content_type})\n\n"
    for i, seg in enumerate(kept_segments[:10]):
        storyboard += f"## Segment {i+1}: {seg['start']:.1f}s - {seg['end']:.1f}s\n"
        storyboard += f"Reason: {seg['reason']}\n\n"

    return {
        "steps": steps,
        "storyboard": storyboard,
        "assumptions": {
            "fps": meta.get("fps", 30),
            "has_audio": meta.get("has_audio", False),
            "estimated_output_duration": round(estimated_output, 1),
        },
        "intents": intents,
        "estimated_cost": {
            "whisper_seconds": 0,
            "vlm_calls": 0,
            "ffmpeg_seconds": round(duration * 1.5),
        },
        "plan_critic_result": {
            "approved": True,
            "violations": [],
            "suggestions": [],
            "rounds": 0,
            "reasoning": "fallback rule-based plan (no LLM available) — no critique applied",
        },
        "memory_hints_used": len(memory_hints),
        "fallback": True,
    }
