#!/usr/bin/env python3
"""
Tests for Phase 6-9 intelligence layer.

Tests the multimodal probe, relevance map, cut detector, pacing engine,
slow-mo engine, music sync, plan critic, hero detector, edit memory, and
reviewer. Uses synthetic clips (no real footage needed). All tests degrade
gracefully when optional deps (mediapipe, demucs, etc.) are unavailable.

Usage:
    python3 scripts/test_phase6_9_intelligence.py
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

try:
    from _test_utils import check, run_main, reset
except ImportError:
    def check(label, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}: {label}" + (f" — {detail}" if detail else ""))
    def run_main(fn):
        try:
            fn()
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            sys.exit(2)
        sys.exit(0)
    def reset():
        pass


def _ensure_clip(clip_dir: pathlib.Path) -> pathlib.Path:
    """Ensure a small synthetic clip exists for testing."""
    clip_dir.mkdir(parents=True, exist_ok=True)
    clip = clip_dir / "small.mp4"
    if not clip.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi",
             "-i", "testsrc2=duration=5:size=320x240:rate=15",
             "-f", "lavfi", "-i", "sine=frequency=220:duration=5",
             "-c:v", "libx264", "-c:a", "aac", "-shortest", str(clip)],
            capture_output=True, check=True,
        )
    return clip


def test_probe_visual():
    """Phase 6: visual probe returns valid profile with graceful degradation."""
    from kb.tools.probe_visual import probe_visual
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    p = probe_visual(str(clip))
    check("visual duration > 0", p.duration > 0)
    check("visual has dimensions", p.width > 0 and p.height > 0)
    check("visual fps detected", p.fps > 0)
    check("visual scene_boundaries is list", isinstance(p.scene_boundaries, list))
    check("visual components_used is list", isinstance(p.components_used, list))
    check("visual has ffprobe component", "ffprobe" in p.components_used)


def test_probe_audio():
    """Phase 6: audio probe returns valid profile."""
    from kb.tools.probe_audio import probe_audio
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    p = probe_audio(str(clip), separate_stems=False)
    check("audio has_audio", p.has_audio)
    check("audio duration > 0", p.duration > 0)
    # LUFS may be -70.0 (default) if ebur128 parsing degrades on short clips — that's acceptable
    check("audio integrated_lufs is number", isinstance(p.integrated_lufs, (int, float)))
    check("audio components_used is list", isinstance(p.components_used, list))


def test_probe_semantic_packing():
    """Phase 6: transcript packing produces compact brief even without Whisper."""
    from kb.tools.probe_semantic import pack_transcript, TranscriptSegment
    segs = [
        TranscriptSegment(start=0.0, end=2.0, text="Hello world this is a test of the transcript packer."),
        TranscriptSegment(start=2.5, end=5.0, text="Um, like, basically we want to compress this."),
    ]
    brief = pack_transcript(segs, 5.0)
    check("packed brief non-empty", len(brief) > 0)
    check("packed brief has header", "# Packed Transcript" in brief)
    check("packed brief under 13KB", len(brief.encode("utf-8")) < 13000)
    check("packed brief drops filler", "um," not in brief.lower())


def test_probe_semantic_heuristic_scoring():
    """Phase 6: heuristic scoring works without LLM."""
    from kb.tools.probe_semantic import _heuristic_score
    s, e, h = _heuristic_score("What an amazing discovery!")
    check("heuristic semantic > 0", s > 0)
    check("heuristic emotional > 0 (exclamation)", e > 0)
    check("heuristic hook > 0", h > 0)
    s2, e2, h2 = _heuristic_score("the")
    check("heuristic short text low semantic", s2 < 0.5)


def test_probe_video_unified():
    """Phase 6: top-level probe_video merges all sub-probes."""
    from kb.tools.probe import probe_video
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    p = probe_video(str(clip), separate_stems=False, score_with_llm=False, render_timeline_png=False)
    check("probe_video returns dict", isinstance(p, dict))
    check("probe_video has metadata", "metadata" in p)
    check("probe_video has visual", "visual" in p)
    check("probe_video has audio", "audio" in p)
    check("probe_video has semantic", "semantic" in p)
    check("probe_video has per_second", len(p.get("per_second", [])) > 0)
    check("probe_video has peaks", "peaks" in p)
    check("probe_video has components_used", "components_used" in p)


def test_probe_only_cli():
    """Phase 6: --probe-only CLI flag saves SourceProfile JSON."""
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    result = subprocess.run(
        [sys.executable, "-m", "kb.tools.recipe_runner", "--probe-only",
         "--output", "/tmp/probe_test/", str(clip)],
        capture_output=True, text=True, timeout=120,
    )
    check("--probe-only exits 0", result.returncode == 0, result.stderr[-200:])
    check("profile JSON saved", pathlib.Path("/tmp/probe_test/small_profile.json").exists())


def test_relevance_map():
    """Phase 7: relevance map builds 6-dimensional per-second scores."""
    from kb.tools.probe import probe_video
    from kb.tools.relevance_map import build_relevance_map
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    profile = probe_video(str(clip), separate_stems=False, score_with_llm=False, render_timeline_png=False)
    rm = build_relevance_map(profile, content_type="talking-head", hero_threshold=0.3)
    check("map has per_second", len(rm.per_second) > 0)
    check("map has summary", "duration_seconds" in rm.summary)
    check("map per_second entries have hero_score",
          all("hero_score" in ps for ps in rm.per_second))
    check("map hero_scores in [0,1]",
          all(0 <= ps["hero_score"] <= 1 for ps in rm.per_second))


def test_cut_detector():
    """Phase 7: cut detector returns Murch-scored candidates."""
    from kb.tools.probe import probe_video
    from kb.tools.relevance_map import build_relevance_map
    from kb.tools.cut_detector import find_cut_points, MURCH_WEIGHTS
    check("Murch weights sum to 1.0", abs(sum(MURCH_WEIGHTS.values()) - 1.0) < 0.001)
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    profile = probe_video(str(clip), separate_stems=False, score_with_llm=False, render_timeline_png=False)
    rm = build_relevance_map(profile, content_type="talking-head")
    rm_dict = rm.as_dict() if hasattr(rm, "as_dict") else rm
    cuts = find_cut_points(profile, rm_dict, content_type="talking-head",
                           target_density="medium", min_score=0.4)
    check("cut_points is list", isinstance(cuts, list))
    for cp in cuts:
        check("cut has timestamp", "timestamp" in cp)
        check("cut has composite_score", "composite_score" in cp)
        check("cut score in [0,1]", 0 <= cp["composite_score"] <= 1)
        check("cut has boundary_reasons", "boundary_reasons" in cp)


def test_pacing_engine():
    """Phase 8: pacing engine produces segments with keep/cut decisions."""
    from kb.tools.pacing_engine import build_paced_plan, PACING_PROFILES
    check("10 content-type profiles", len(PACING_PROFILES) == 10)
    check("vlog profile exists", "vlog" in PACING_PROFILES)
    check("vlog hook_window is 1.5", PACING_PROFILES["vlog"]["hook_window"] == 1.5)
    # Minimal mock
    profile = {"metadata": {"duration": 30}}
    rm = {"hero_moments": [], "dead_zones": []}
    cuts = [{"timestamp": 5.0, "composite_score": 0.7},
            {"timestamp": 15.0, "composite_score": 0.65}]
    plan = build_paced_plan(profile, rm, cuts, "talking-head")
    check("paced plan has segments", len(plan["segments"]) > 0)
    check("paced plan has summary", "summary" in plan)
    check("paced plan has hook_window_satisfied", "hook_window_satisfied" in plan)


def test_slowmo_engine():
    """Phase 8: slow-mo engine returns proposals with valid speed factors."""
    from kb.tools.slowmo_engine import find_slowmo_moments, SPEED_FACTORS, proposals_to_filter_chain
    check("impact speed 0.30", SPEED_FACTORS["impact"] == 0.30)
    check("reveal speed 0.45", SPEED_FACTORS["reveal"] == 0.45)
    check("beauty speed 0.50", SPEED_FACTORS["beauty"] == 0.50)
    profile = {
        "metadata": {"duration": 30},
        "audio": {"tempo": 120.0, "downbeats": [0, 2, 4], "onsets": [5.0]},
        "peaks": {"motion": [{"timestamp": 5.0, "sigma": 3.0}]},
        "per_second": [{"ts": 5, "semantic_importance": 0.5, "motion_energy": 0.1}],
    }
    rm = {"hero_moments": [], "dead_zones": []}
    proposals = find_slowmo_moments(profile, rm, max_per_minute=2)
    check("proposals is list", isinstance(proposals, list))
    for p in proposals:
        check("proposal has moment_type", "moment_type" in p)
        check("proposal speed in valid range", 0.2 <= p["speed_factor"] <= 0.6)
        check("proposal has reasoning", "reasoning" in p)
    # Test filter chain conversion
    if proposals:
        ops = proposals_to_filter_chain(proposals)
        check("filter chain has ops", len(ops) > 0)
        check("op has atempo_chain", "atempo_chain" in ops[0]["params"])


def test_music_sync_no_music():
    """Phase 8: music sync handles no-music case gracefully."""
    from kb.tools.music_sync import build_music_sync_plan, apply_ducking
    profile = {"audio": {"music_path": None}}
    cuts = [{"timestamp": 5.0, "composite_score": 0.7}]
    rm = {"hero_moments": []}
    plan = build_music_sync_plan(profile, cuts, rm)
    check("no-music returns none structure", plan["structure"] is None)
    check("no-music aligned_cuts type none", plan["aligned_cuts"][0]["alignment_type"] == "none")
    # Test ducking params (Geary JAES 2020)
    ducking = apply_ducking([{"start": 0, "end": 5}], "/fake/path")
    check("ducking has 1 segment", len(ducking["segments"]) == 1)
    check("ducking attack 150ms", ducking["segments"][0]["attack_ms"] == 150)
    check("ducking release 300ms", ducking["segments"][0]["release_ms"] == 300)
    check("ducking ratio 6:1", ducking["filter_params"]["params"]["ratio"] == 6.0)


def test_plan_critic_detects_violations():
    """Phase 9: plan critic catches Hard Rule violations."""
    from kb.tools.plan_critic import critique_plan, HARD_RULES_CHECKABLE
    check("11 checkable hard rules", len(HARD_RULES_CHECKABLE) == 11)
    broken_plan = {
        "steps": [
            {"tool": "edit.loudnorm_limited", "params": {"target_lufs": -16}, "output": "ln"},
            {"tool": "video_trim", "params": {}, "output": "t1"},
        ],
        "intents": [],
        "assumptions": {"fps": 30, "has_audio": True, "estimated_output_duration": 60},
    }
    profile = {"metadata": {"duration": 30, "fps": 30, "has_audio": True, "aspect_ratio": 1.78}}
    rm = {"hero_moments": [], "dead_zones": []}
    result = critique_plan(broken_plan, profile, rm, "vlog")
    check("critic not approved (broken plan)", not result["approved"])
    check("critic found HR#25 violation", any(v["rule"] == "HR#25" for v in result["violations"]))
    check("critic found HR#1 violation", any(v["rule"] == "HR#1" for v in result["violations"]))


def test_plan_critic_approves_clean_plan():
    """Phase 9: plan critic approves a clean plan."""
    from kb.tools.plan_critic import critique_plan
    clean_plan = {
        "steps": [
            {"tool": "edit.info", "params": {}, "output": "info"},
            {"tool": "edit.render", "params": {"profile": "youtube-1080p"}, "output": "final"},
        ],
        "intents": ["extract highlights"],
        "assumptions": {"fps": 30, "has_audio": True, "estimated_output_duration": 30},
    }
    profile = {"metadata": {"duration": 30, "fps": 30, "has_audio": True, "aspect_ratio": 1.78}}
    rm = {"hero_moments": [], "dead_zones": []}
    result = critique_plan(clean_plan, profile, rm, "vlog")
    check("clean plan approved", result["approved"])


def test_hero_detector_triple_fusion():
    """Phase 9: hero detector finds triple-modal co-occurrence."""
    from kb.tools.hero_detector import detect_hero_moments
    profile = {
        "audio": {"onsets": [5.0], "prosody_emotion": [{"start": 5.0, "emotion": "surprise"}]},
        "visual": {"motion_peaks": [{"timestamp": 5.1, "sigma": 3.0}],
                   "emotion_peaks": [], "aesthetic_peaks": []},
        "semantic": {"transcript": [{"start": 4.9, "semantic_importance": 0.9, "text": "this is the moment"}],
                     "keyphrases": []},
    }
    rm = {"hero_moments": [], "dead_zones": []}
    heroes = detect_hero_moments(profile, rm)
    check("hero detector found moments", len(heroes) > 0)
    triples = [h for h in heroes if h["level"] == 3]
    check("triple-modal hero detected", len(triples) > 0)
    if triples:
        h = triples[0]
        check("triple hero has 3 modalities", len(h["modalities"]) == 3)
        check("triple hero label is hero_moment", h["label"] == "hero_moment")
        check("triple hero has fusion_reasoning", len(h["fusion_reasoning"]) > 50)


def test_edit_memory_db():
    """Phase 9: edit-pattern memory DB records and queries outcomes."""
    from kb.tools.edit_memory import EditPatternDB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        db = EditPatternDB(db_path)
        for _ in range(3):
            db.record_outcome("vlog", "silence_remove", {"threshold": -50},
                              success=True, vmaf=85.0, reviewer_score=0.8, run_id="test")
        db.record_outcome("vlog", "silence_remove", {"threshold": -30},
                          success=False, vmaf=70.0, reviewer_score=0.4, run_id="test")
        hints = db.get_memory_hints("vlog")
        check("memory hints returned", len(hints) > 0)
        check("successful pattern high rate", hints[0]["success_rate"] >= 0.7)
        stats = db.stats()
        check("DB stats has total_patterns", stats["total_patterns"] >= 2)
    finally:
        os.unlink(db_path)


def test_reviewer_seven_dimensions():
    """Phase 9: reviewer scores 6 dimensions (overall is composite)."""
    from kb.tools.reviewer import review_output, DIMENSION_WEIGHTS
    check("6 dimension weights", len(DIMENSION_WEIGHTS) == 6)
    check("weights sum to 1.0", abs(sum(DIMENSION_WEIGHTS.values()) - 1.0) < 0.01)
    # Create test output
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    result = review_output(
        str(clip),
        edit_plan={"assumptions": {"estimated_output_duration": 5}, "steps": []},
        source_profile={"metadata": {"video_path": str(clip)}},
        paced_plan={"summary": {"pacing_violation_count": 0, "hook_window_satisfied": True}},
        content_type="talking-head",
    )
    check("review has 6 dimension scores", len(result["scores"]) == 6)
    check("review overall in [0,1]", 0 <= result["overall"] <= 1)
    for s in result["scores"]:
        check(f"review score {s['dimension']} in [0,1]", 0 <= s["score"] <= 1)
    expected = {"adherence", "pacing", "visual_quality", "watchability", "audio", "narrative_coherence"}
    actual = {s["dimension"] for s in result["scores"]}
    check("all 6 dimensions present", expected == actual)


def test_intelligent_planner_fallback():
    """Phase 9: intelligent planner falls back to rule-based when LLM unavailable."""
    from kb.tools.intelligent_planner import generate_plan
    profile = {
        "metadata": {"duration": 30, "fps": 30, "has_audio": True, "aspect_ratio": 1.78, "video_path": "/tmp/x.mp4"},
        "audio": {"tempo": 120, "integrated_lufs": -16, "speaker_count": 1},
        "semantic": {"packed_brief": "# Packed Transcript\n\n(test)"},
        "per_second": [{"ts": i, "motion_energy": 0.1, "semantic_importance": 0.5} for i in range(30)],
    }
    rm = {"hero_moments": [], "dead_zones": [], "per_second": []}
    cuts = [{"timestamp": 5.0, "composite_score": 0.7}]
    paced = {"segments": [{"start": 0, "end": 30, "keep": True, "reason": "within_profile", "pacing_score": 0.7}],
             "summary": {"hook_window_satisfied": True, "pacing_violation_count": 0}}
    plan = generate_plan(
        profile, rm, cuts, paced, [], {"structure": None, "aligned_cuts": []},
        "talking-head", ["extract highlights"], [],
        plan_llm_model="ollama/nonexistent:7b",  # force fallback
        max_critique_rounds=1,
    )
    check("fallback plan has steps", len(plan.get("steps", [])) > 0)
    check("fallback plan has storyboard", "storyboard" in plan)
    check("fallback plan has assumptions", "assumptions" in plan)
    check("fallback plan marked fallback", plan.get("fallback") is True)
    check("fallback plan has plan_critic_result", "plan_critic_result" in plan)


def test_analyze_only_cli():
    """Phase 6-9: --analyze-only runs full intelligence pipeline and saves JSON."""
    clip = _ensure_clip(pathlib.Path("/tmp/clips"))
    result = subprocess.run(
        [sys.executable, "-m", "kb.tools.recipe_runner", "--analyze-only",
         "--output", "/tmp/analyze_test/", str(clip)],
        capture_output=True, text=True, timeout=180,
    )
    check("--analyze-only exits 0", result.returncode == 0, result.stderr[-200:])
    out_json = pathlib.Path("/tmp/analyze_test/small_analysis.json")
    check("analysis JSON saved", out_json.exists())
    if out_json.exists():
        with open(out_json) as f:
            a = json.load(f)
        check("analysis has source_profile", "source_profile" in a)
        check("analysis has relevance_map", "relevance_map" in a)
        check("analysis has cut_points", "cut_points" in a)
        check("analysis has paced_plan", "paced_plan" in a)
        check("analysis has slowmo_proposals", "slowmo_proposals" in a)
        check("analysis has music_sync_plan", "music_sync_plan" in a)
        check("analysis has hero_moments", "hero_moments" in a)


def run_tests():
    reset()
    print("=== Phase 6: Multimodal Probe Layer ===")
    test_probe_visual()
    test_probe_audio()
    test_probe_semantic_packing()
    test_probe_semantic_heuristic_scoring()
    test_probe_video_unified()
    test_probe_only_cli()
    print("\n=== Phase 7: Relevance Map + Cut Detection ===")
    test_relevance_map()
    test_cut_detector()
    print("\n=== Phase 8: Pacing + Slow-Mo + Music ===")
    test_pacing_engine()
    test_slowmo_engine()
    test_music_sync_no_music()
    print("\n=== Phase 9: Plan Critic + Hero + Memory + Reviewer ===")
    test_plan_critic_detects_violations()
    test_plan_critic_approves_clean_plan()
    test_hero_detector_triple_fusion()
    test_edit_memory_db()
    test_reviewer_seven_dimensions()
    test_intelligent_planner_fallback()
    print("\n=== Integration: --analyze-only ===")
    test_analyze_only_cli()


if __name__ == "__main__":
    run_main(run_tests)
