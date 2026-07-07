"""
Editing Research (Phase 5 — Crayotter's pure-reasoning sub-phase).

A deliberate no-tool LLM reasoning phase that produces a structured "editing
blueprint" BEFORE any planning happens. Crayotter pattern: "Pure-reasoning phase
analyzing source videos to produce a structured editing blueprint (narrative,
visual, pacing, narration strategies). No tools called."

This separates "analyze the material and decide strategy" from "produce the
concrete EditPlan" — the planner then consumes the blueprint as input.

If LLM is unavailable, falls back to a rule-based blueprint derived from the
SourceProfile + RelevanceMap + content_type.

Public surface:
  - research_edit(source_profile, relevance_map, content_type, intents, router) -> dict
    Returns {"narrative_strategy": str, "visual_strategy": str,
             "pacing_strategy": str, "narration_strategy": str,
             "blueprint_md": str, "source": "llm"|"rule-based"}
"""
from __future__ import annotations

import json
import typing as t


RESEARCH_PROMPT_TEMPLATE = """You are a video editing strategist. Analyze the source material and produce a structured editing blueprint. Do NOT write specific FFmpeg commands or tool calls — this is a pure-reasoning strategy phase.

## Source Material Summary
- Duration: {duration}s
- Content type: {content_type}
- FPS: {fps}, aspect ratio: {aspect_ratio}
- Has audio: {has_audio}
- Speakers: {speaker_count}
- Tempo: {tempo} BPM
- Scene count: {scene_count}

## Packed Transcript
{packed_transcript}

## Relevance Map Summary
- Hero moments: {hero_count} (top score: {top_hero_score})
- Dead zones: {dead_zone_count}
- Avg hero score: {avg_hero_score}

## Intents
- Explicit: {explicit_intents}
- Implicit: {implicit_intents}

## Your Task
Produce a JSON object with 4 strategy fields (each a 2-3 sentence string):
{{
  "narrative_strategy": "How should the story flow? What's the arc? What to keep/cut?",
  "visual_strategy": "Color, composition, shot selection, B-roll usage",
  "pacing_strategy": "Cut rhythm, shot length distribution, slow-mo placement",
  "narration_strategy": "Subtitle/VO approach, music bed, ducking"
}}

Return ONLY the JSON object, no prose."""


def research_edit(source_profile: dict, relevance_map: dict,
                  content_type: str, intents: list[str],
                  router: t.Optional[object] = None) -> dict:
    """
    Produce an editing blueprint via LLM (pure reasoning, no tools).
    Falls back to rule-based blueprint if LLM unavailable.
    """
    # Try LLM-based research
    if router is not None:
        blueprint = _llm_research(source_profile, relevance_map, content_type, intents, router)
        if blueprint is not None:
            blueprint["source"] = "llm"
            blueprint["blueprint_md"] = _blueprint_to_markdown(blueprint, content_type)
            return blueprint

    # Fallback: rule-based blueprint
    blueprint = _rule_based_blueprint(source_profile, relevance_map, content_type, intents)
    blueprint["source"] = "rule-based"
    blueprint["blueprint_md"] = _blueprint_to_markdown(blueprint, content_type)
    return blueprint


def _llm_research(source_profile: dict, relevance_map: dict,
                  content_type: str, intents: list[str], router) -> t.Optional[dict]:
    meta = source_profile.get("metadata", {})
    audio = source_profile.get("audio", {})
    semantic = source_profile.get("semantic", {})
    visual = source_profile.get("visual", {})

    prompt = RESEARCH_PROMPT_TEMPLATE.format(
        duration=meta.get("duration", 0),
        content_type=content_type,
        fps=meta.get("fps", 30),
        aspect_ratio=meta.get("aspect_ratio", 1.78),
        has_audio=meta.get("has_audio", False),
        speaker_count=audio.get("speaker_count", 1),
        tempo=audio.get("tempo", 0),
        scene_count=len(visual.get("scene_boundaries", [])),
        packed_transcript=(semantic.get("packed_brief", "(no transcript)") or "")[:3000],
        hero_count=len(relevance_map.get("hero_moments", [])),
        top_hero_score=max((h.get("peak_score", 0) for h in relevance_map.get("hero_moments", [])), default=0),
        dead_zone_count=len(relevance_map.get("dead_zones", [])),
        avg_hero_score=relevance_map.get("summary", {}).get("avg_hero_score", 0),
        explicit_intents=[i for i in intents if i],
        implicit_intents=[],
    )

    try:
        result = router.route_json("research", prompt, temperature=0.5, max_tokens=2000, timeout=90)
        if result and "narrative_strategy" in result:
            return result
    except Exception:
        pass
    return None


def _rule_based_blueprint(source_profile: dict, relevance_map: dict,
                          content_type: str, intents: list[str]) -> dict:
    """Generate a blueprint from rules when LLM unavailable."""
    meta = source_profile.get("metadata", {})
    audio = source_profile.get("audio", {})
    visual = source_profile.get("visual", {})
    heroes = relevance_map.get("hero_moments", [])
    dead_zones = relevance_map.get("dead_zones", [])
    duration = meta.get("duration", 0)

    # Narrative strategy
    if heroes:
        hero_ts = ", ".join(f"{h['start']:.0f}s" for h in heroes[:3])
        narrative = (f"Anchor the edit around {len(heroes)} hero moment(s) at {hero_ts}. "
                     f"Cut the {len(dead_zones)} dead zone(s) to tighten pacing. "
                     f"Total kept duration target: ~{duration * 0.6:.0f}s (60% of source).")
    else:
        narrative = (f"No strong hero moments detected; use scene boundaries ({len(visual.get('scene_boundaries', []))} scenes) "
                     f"as cut points. Remove {len(dead_zones)} dead zone(s). Maintain narrative flow via transcript ordering.")

    # Visual strategy
    shot_scales = [ps.get("shot_scale", "unknown") for ps in source_profile.get("per_second", [])[:30]]
    close_ups = shot_scales.count("close_up")
    if close_ups > 10:
        visual_strat = "Subject is in close-up frequently — preserve intimacy, use J-cuts for emotion. Apply warm color grade."
    else:
        visual_strat = "Mixed shot scales — use scale changes as natural cut points. Standard color grade with content-type LUT."

    # Pacing strategy
    PACING = {
        "vlog": "5-10s shot lengths, pattern interrupts on motion/emotion peaks",
        "social-short": "3-5s aggressive cuts, hook in first 1.5s, kinetic text",
        "podcast": "30-90s long holds OK, cut only at dead zones + chapter boundaries",
        "tutorial": "30-75s segments, chapter markers at topic changes",
        "cinematic": "8-15s shots, slow pacing, color grade first",
        "documentary": "8-15s shots, J-cuts at 0.5-1.5s, B-roll over talking head",
        "interview": "15-30s speaker switches, J/L-cuts at 0.2-0.5s",
        "talking-head": "10-20s, silence removal, dynamic zoom on emphasis",
        "music-video": "3-8s beat-aligned cuts, section-anchored",
        "event": "5-12s, highlight extraction, music bed",
    }
    pacing = PACING.get(content_type, "10s average shot length")

    # Narration strategy
    if meta.get("has_audio"):
        target_lufs = {"cinematic": -23, "vlog": -14, "social-short": -14, "podcast": -16}.get(content_type, -16)
        narration = (f"Two-pass loudnorm to {target_lufs} LUFS. "
                     f"Subtitles: 2 lines max, 42 chars/line, applied LAST. "
                     f"Music bed ducked {14} LU under speech (150ms attack, 300ms release).")
    else:
        narration = "No audio in source — add silent audio track for delivery compliance."

    return {
        "narrative_strategy": narrative,
        "visual_strategy": visual_strat,
        "pacing_strategy": pacing,
        "narration_strategy": narration,
    }


def _blueprint_to_markdown(bp: dict, content_type: str) -> str:
    """Convert blueprint dict to human-readable Markdown."""
    lines = [
        f"# Editing Blueprint ({content_type})",
        "",
        f"**Source:** {bp.get('source', 'unknown')}",
        "",
        "## Narrative Strategy",
        bp.get("narrative_strategy", ""),
        "",
        "## Visual Strategy",
        bp.get("visual_strategy", ""),
        "",
        "## Pacing Strategy",
        bp.get("pacing_strategy", ""),
        "",
        "## Narration Strategy",
        bp.get("narration_strategy", ""),
        "",
    ]
    return "\n".join(lines)
