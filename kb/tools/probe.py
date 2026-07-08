"""
Unified multimodal probe (Phase 6, M0 module).

Runs visual + audio + semantic probes in parallel, merges into a single
SourceProfile aligned on a 1-second grid. Every sub-probe degrades gracefully;
the SourceProfile is always valid (possibly sparse if deps missing).

Public surface:
  - probe_video(video_path, **opts) -> dict (SourceProfile, JSON-serializable)
  - save_profile(profile, path), load_profile(path)

Wired into recipe_runner.run_recipe() via context["_source_profile"].
"""
from __future__ import annotations

import json
import os
import pathlib
import typing as t
from concurrent.futures import ThreadPoolExecutor, as_completed


def _check_has_audio(video_path: str) -> bool:
    """Phase 1c: Fast ffprobe check if video has an audio stream.
    Returns True if audio exists, False otherwise. ~50ms."""
    import subprocess
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=10,
        )
        return "audio" in result.stdout
    except Exception:
        return True  # assume audio on error (safe default)


def probe_video(video_path: str, *,
                separate_stems: bool = False,
                score_with_llm: bool = False,
                llm_router: t.Optional[object] = None,
                render_timeline_png: bool = False) -> dict:
    """Run all probes in parallel, merge into SourceProfile dict.
    P2 #9 fix: render_timeline_png defaults to False (was True — caused OOM in constrained environments).
    P2 #8 fix: memory check — falls back to sequential if available RAM < 1GB."""
    from kb.tools.probe_visual import probe_visual
    from kb.tools.probe_audio import probe_audio
    from kb.tools.probe_semantic import probe_semantic

    visual_result = None
    audio_result = None
    semantic_result = None

    # P2 #8: Memory check — if available RAM < 1GB, run probes sequentially
    run_parallel = True
    try:
        import psutil
        avail_mb = psutil.virtual_memory().available / (1024 * 1024)
        if avail_mb < 1024:
            run_parallel = False
            print(f"[probe] Low memory ({avail_mb:.0f}MB available) — running probes sequentially", file=__import__("sys").stderr)
    except ImportError:
        pass  # psutil not installed — assume enough memory, run parallel

    # Phase 1c: No-audio fast path — check if video has audio before launching probes.
    # If no audio, skip audio + semantic probes entirely (saves 30-120s on silent videos).
    has_audio = _check_has_audio(video_path)
    if not has_audio:
        print("[probe] No audio track detected — skipping audio + semantic probes", file=__import__("sys").stderr)

    if run_parallel and has_audio:
        # Run all 3 probes in PARALLEL
        with ThreadPoolExecutor(max_workers=3) as ex:
            futures = {
                ex.submit(probe_visual, video_path): "visual",
                ex.submit(probe_audio, video_path, separate_stems): "audio",
                ex.submit(probe_semantic, video_path, 0, score_with_llm, llm_router): "semantic",
            }
            for future in as_completed(futures):
                label = futures[future]
                try:
                    if label == "visual":
                        visual_result = future.result()
                    elif label == "audio":
                        audio_result = future.result()
                    elif label == "semantic":
                        semantic_result = future.result()
                except Exception as e:
                    print(f"[probe] {label} probe failed: {e}", file=__import__("sys").stderr)
    else:
        # Sequential fallback (P2 #8 fix — prevents OOM on constrained machines)
        # Phase 1c: also handles no-audio case (skip audio + semantic)
        try:
            visual_result = probe_visual(video_path)
        except Exception as e:
            print(f"[probe] visual probe failed: {e}", file=__import__("sys").stderr)
        if has_audio:
            try:
                audio_result = probe_audio(video_path, separate_stems)
            except Exception as e:
                print(f"[probe] audio probe failed: {e}", file=__import__("sys").stderr)
            try:
                semantic_result = probe_semantic(video_path, 0, score_with_llm, llm_router)
            except Exception as e:
                print(f"[probe] semantic probe failed: {e}", file=__import__("sys").stderr)

    if semantic_result is None:
        from kb.tools.probe_semantic import SemanticProfile
        semantic_result = SemanticProfile()

    duration = visual_result.duration if visual_result else (audio_result.duration if audio_result else 0.0)

    per_second = _merge_per_second(visual_result, audio_result, semantic_result, duration)

    peaks = {
        "motion": visual_result.motion_peaks if visual_result else [],
        "emotion": visual_result.emotion_peaks if visual_result else [],
        "aesthetic": visual_result.aesthetic_peaks if visual_result else [],
        "audio_onset": (audio_result.onsets[:50] if audio_result else []),
        "semantic_importance": [
            {"timestamp": s.get("start", 0), "score": s.get("semantic_importance", 0),
             "text": (s.get("text", "") or "")[:80]}
            for s in (semantic_result.transcript if semantic_result else [])
            if s.get("semantic_importance", 0) > 0.7
        ],
    }

    timeline_png_path = None
    if render_timeline_png and duration > 0:
        try:
            from kb.tools.timeline_view import render_timeline
            out_png = str(pathlib.Path(video_path).parent /
                          f"{pathlib.Path(video_path).stem}_timeline.png")
            timeline_png_path = render_timeline(video_path, per_second, peaks, duration, out_png)
        except Exception as e:
            print(f"[probe] timeline render failed: {e}", file=__import__("sys").stderr)

    profile = {
        "metadata": {
            "video_path": video_path,
            "duration": duration,
            "width": visual_result.width if visual_result else 0,
            "height": visual_result.height if visual_result else 0,
            "fps": visual_result.fps if visual_result else 30.0,
            "aspect_ratio": visual_result.aspect_ratio if visual_result else 0.0,
            "has_video": visual_result.has_video_stream if visual_result else False,
            "has_audio": audio_result.has_audio if audio_result else False,
        },
        "visual": visual_result.as_dict() if visual_result else {},
        "audio": audio_result.as_dict() if audio_result else {},
        "semantic": semantic_result.as_dict() if semantic_result else {},
        "per_second": per_second,
        "peaks": peaks,
        "timeline_png_path": timeline_png_path,
        "components_used": {
            "visual": visual_result.components_used if visual_result else [],
            "audio": audio_result.components_used if audio_result else [],
            "semantic": semantic_result.components_used if semantic_result else [],
        },
    }
    return profile


def _merge_per_second(visual, audio, semantic, duration: float) -> list[dict]:
    """Merge per-second features from all three probes into a unified timeline."""
    per_second: list[dict] = []
    visual_ps = {ps["ts"]: ps for ps in (visual.per_second if visual else [])}
    audio_ps = {ps["ts"]: ps for ps in (audio.per_second if audio else [])}
    semantic_ps = {ps["ts"]: ps for ps in (semantic.per_second if semantic else [])}

    for sec in range(int(duration)):
        v = visual_ps.get(sec, {})
        a = audio_ps.get(sec, {})
        s = semantic_ps.get(sec, {})
        per_second.append({
            "ts": sec,
            "face_present": v.get("face_present", False),
            "face_emotion": v.get("face_emotion"),
            "face_arousal": v.get("face_arousal", 0.0),
            "face_valence": v.get("face_valence", 0.5),
            "motion_energy": v.get("motion_energy", 0.0),
            "aesthetic_score": v.get("aesthetic_score", 0.5),
            "shot_scale": v.get("shot_scale", "unknown"),
            "ocr_text": v.get("ocr_text"),
            "audio_speech": a.get("speech", False),
            "audio_speaker": a.get("speaker"),
            "audio_prosody_emotion": a.get("prosody_emotion"),
            "audio_beat": a.get("beat", False),
            "audio_onset": a.get("onset", False),
            "semantic_speech": s.get("speech", False),
            "semantic_importance": s.get("semantic_importance", 0.5),
            "emotional_intensity": s.get("emotional_intensity", 0.0),
            "hook_potential": s.get("hook_potential", 0.0),
            "text": s.get("text", ""),
        })
    return per_second


def save_profile(profile: dict, output_path: str) -> None:
    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2, default=str)


def load_profile(path: str) -> dict:
    with open(path) as f:
        return json.load(f)
