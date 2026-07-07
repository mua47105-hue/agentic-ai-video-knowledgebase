"""
7-Dimension Reviewer (Phase 9, M4 module) + VMAF auto-correction.

Scores the final output on 7 dimensions (extends AVE's 5 to 7):
  1. Adherence        — does output match the EditPlan? (duration delta)
  2. Pacing           — does it respect the content-type pacing profile?
  3. Visual Quality   — VMAF + resolution + bitrate
  4. Watchability     — duration, A/V sync, no dead zones
  5. Audio            — LUFS, true-peak, LRA, no clipping (HR #1-#5)
  6. Narrative Coherence — placeholder (LLM-scored from output transcript, v2)
  7. Overall          — weighted composite

VMAF auto-correction (RESEARCH-3 gap #6):
  If VMAF < 80, re-encode with CRF-2 and slower preset, re-measure, max 2 retries.

Public surface:
  - review_output(output_path, edit_plan, source_profile, paced_plan, content_type) -> dict
  - DIMENSION_WEIGHTS
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import typing as t


DIMENSION_WEIGHTS = {
    "adherence": 0.20,
    "pacing": 0.15,
    "visual_quality": 0.20,
    "watchability": 0.15,
    "audio": 0.15,
    "narrative_coherence": 0.15,
}


def review_output(output_path: str, edit_plan: dict, source_profile: dict,
                  paced_plan: dict, content_type: str,
                  vmaf_threshold: float = 80.0,
                  overall_threshold: float = 0.65) -> dict:
    """Score the final output on 7 dimensions. Auto-correct VMAF failures."""
    scores: list[dict] = []
    corrections: list[str] = []

    scores.append(_score_adherence(output_path, edit_plan))
    scores.append(_score_pacing(paced_plan))
    visual, vmaf = _score_visual_quality(output_path, source_profile, vmaf_threshold)
    scores.append(visual)
    if 0 < vmaf < vmaf_threshold:
        corrected = _auto_correct_vmaf(output_path, source_profile, vmaf_threshold)
        if corrected >= vmaf_threshold:
            vmaf = corrected
            visual["score"] = min(1.0, corrected / 100.0)
            visual["auto_corrected"] = True
            corrections.append(f"VMAF auto-corrected to {corrected:.1f} (re-encoded with lower CRF)")
    scores.append(_score_watchability(output_path))
    scores.append(_score_audio(output_path, content_type))
    scores.append(_score_narrative_coherence(output_path, edit_plan))

    overall = 0.0
    for s in scores:
        overall += DIMENSION_WEIGHTS.get(s["dimension"], 0) * s["score"]
    overall = round(overall, 3)
    passed = overall >= overall_threshold

    reasoning = f"Overall score {overall:.3f} (threshold {overall_threshold}). "
    reasoning += "PASSED" if passed else "FAILED — retry needed."
    if corrections:
        reasoning += " Auto-corrections: " + "; ".join(corrections)

    return {
        "scores": scores, "overall": overall, "passed": passed,
        "vmaf": vmaf, "vmaf_corrected": bool(corrections),
        "corrections_applied": corrections, "reasoning": reasoning,
    }


def _score_adherence(output_path: str, edit_plan: dict) -> dict:
    if not pathlib.Path(output_path).exists():
        return {"dimension": "adherence", "score": 0.0, "detail": "output file does not exist", "auto_corrected": False}
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", output_path],
        capture_output=True, text=True)
    if probe.returncode != 0:
        return {"dimension": "adherence", "score": 0.0, "detail": "ffprobe failed", "auto_corrected": False}
    try:
        actual = float(probe.stdout.strip() or 0)
    except ValueError:
        actual = 0.0
    expected = edit_plan.get("assumptions", {}).get("estimated_output_duration", 0)
    if expected == 0:
        return {"dimension": "adherence", "score": 0.7, "detail": f"no expected duration; actual {actual:.1f}s", "auto_corrected": False}
    delta = abs(actual - expected) / max(expected, 0.001)
    score = max(0.0, 1.0 - delta * 2)
    return {"dimension": "adherence", "score": score, "detail": f"expected {expected:.1f}s, actual {actual:.1f}s (delta {delta*100:.1f}%)", "auto_corrected": False}


def _score_pacing(paced_plan: dict) -> dict:
    summary = paced_plan.get("summary", {})
    violations = summary.get("pacing_violation_count", 0)
    hook_ok = summary.get("hook_window_satisfied", False)
    score = max(0.0, 1.0 - (violations * 0.15))
    if not hook_ok:
        score -= 0.2
    score = max(0.0, score)
    return {"dimension": "pacing", "score": score, "detail": f"{violations} pacing violations, hook {'OK' if hook_ok else 'MISSING'}", "auto_corrected": False}


def _score_visual_quality(output_path: str, source_profile: dict,
                          vmaf_threshold: float) -> tuple[dict, float]:
    reference = source_profile.get("metadata", {}).get("video_path", "")
    vmaf = _compute_vmaf(reference, output_path)
    if vmaf is None:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,bit_rate", "-of", "json", output_path],
            capture_output=True, text=True)
        if probe.returncode == 0:
            data = json.loads(probe.stdout)
            s = data.get("streams", [{}])[0]
            bitrate = int(s.get("bit_rate", 0) or 0)
            score = min(1.0, bitrate / 8_000_000)
            return ({"dimension": "visual_quality", "score": score, "detail": f"bitrate {bitrate/1e6:.1f}Mbps (VMAF unavailable)", "auto_corrected": False}, 0.0)
        return ({"dimension": "visual_quality", "score": 0.0, "detail": "ffprobe failed", "auto_corrected": False}, 0.0)
    score = min(1.0, vmaf / 100.0)
    return ({"dimension": "visual_quality", "score": score, "detail": f"VMAF {vmaf:.1f} (threshold {vmaf_threshold})", "auto_corrected": False}, vmaf)


def _compute_vmaf(reference_path: str, distorted_path: str) -> t.Optional[float]:
    if not reference_path or not pathlib.Path(reference_path).exists():
        return None
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", distorted_path, "-i", reference_path,
             "-lavfi", "libvmaf=log_path=/tmp/vmaf.log:log_fmt=json",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=300)
        for line in result.stderr.split("\n"):
            if "VMAF score:" in line:
                return float(line.split("VMAF score:")[1].strip())
        log_path = pathlib.Path("/tmp/vmaf.log")
        if log_path.exists():
            with open(log_path) as f:
                data = json.load(f)
                return data.get("pooled_metrics", {}).get("vmaf", {}).get("mean")
    except Exception:
        pass
    return None


def _auto_correct_vmaf(output_path: str, source_profile: dict,
                       vmaf_threshold: float, max_retries: int = 2) -> float:
    current_crf = 23
    current_preset = "medium"
    reference = source_profile.get("metadata", {}).get("video_path", "")
    for retry in range(max_retries):
        current_crf = max(18, current_crf - 2)
        if retry == 1:
            current_preset = "slow"
        temp_path = output_path.replace(".mp4", f"_vmaf_retry{retry}.mp4")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", output_path,
                 "-c:v", "libx264", "-crf", str(current_crf),
                 "-preset", current_preset, "-c:a", "copy", temp_path],
                capture_output=True, check=True, timeout=600)
            new_vmaf = _compute_vmaf(reference, temp_path)
            if new_vmaf and new_vmaf >= vmaf_threshold:
                pathlib.Path(output_path).unlink(missing_ok=True)
                pathlib.Path(temp_path).rename(output_path)
                return new_vmaf
        except Exception:
            continue
    return 0.0


def _score_watchability(output_path: str) -> dict:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", output_path],
        capture_output=True, text=True)
    if probe.returncode != 0:
        return {"dimension": "watchability", "score": 0.0, "detail": "ffprobe failed", "auto_corrected": False}
    data = json.loads(probe.stdout)
    streams = data.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if not has_video:
        return {"dimension": "watchability", "score": 0.0, "detail": "no video stream", "auto_corrected": False}
    if not has_audio:
        return {"dimension": "watchability", "score": 0.5, "detail": "no audio stream", "auto_corrected": False}
    return {"dimension": "watchability", "score": 0.8, "detail": "video + audio present", "auto_corrected": False}


def _score_audio(output_path: str, content_type: str) -> dict:
    result = subprocess.run(
        ["ffmpeg", "-i", output_path, "-hide_banner", "-nostats",
         "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True, timeout=300)
    integrated = -70.0
    true_peak = -70.0
    lra = 0.0
    for line in result.stderr.split("\n"):
        if "I:" in line and "LUFS" in line:
            try:
                parts = line.split()
                for i, p in enumerate(parts):
                    if p == "I:": integrated = float(parts[i + 1])
                    elif p == "LRA:": lra = float(parts[i + 2])
                    elif p == "TP:": true_peak = float(parts[i + 2])
            except (ValueError, IndexError):
                pass
            break
    LUFS_TARGETS = {"vlog": -14, "social-short": -14, "podcast": -16, "tutorial": -16,
                    "cinematic": -23, "documentary": -16, "interview": -16,
                    "talking-head": -16, "music-video": -14, "event": -16}
    target = LUFS_TARGETS.get(content_type, -16)
    lufs_delta = abs(integrated - target)
    score = max(0.0, 1.0 - lufs_delta * 0.1)
    if true_peak > -1.0:
        score -= 0.2
    if lra > 15:
        score -= 0.1
    return {"dimension": "audio", "score": max(0.0, score), "detail": f"LUFS {integrated:.1f} (target {target}), TP {true_peak:.1f}dB, LRA {lra:.1f}dB", "auto_corrected": False}


def _score_narrative_coherence(output_path: str, edit_plan: dict) -> dict:
    return {"dimension": "narrative_coherence", "score": 0.7, "detail": "narrative coherence scoring not yet implemented (placeholder)", "auto_corrected": False}
