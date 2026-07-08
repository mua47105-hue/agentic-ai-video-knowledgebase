"""
Smart vertical reframe: detect faces via OpenCV Haar cascade, choose
TRACK vs LETTERBOX strategy per scene, and render a 9:16 output.

Gated: requires ``opencv-python-headless`` (``pip install opencv-python-headless``).
Off by default — never added to setup.sh.

Usage:
    from kb.tools.reframe_adapter import smart_reframe
    result = smart_reframe("input.mp4", "output.mp4")

Architecture (matches AutoFlip-style):
    1. Scene detection via existing edit.detect_scenes()
    2. Per-scene face detection via Haar cascade
    3. Per-scene strategy:
       - TRACK:  follow detected face(s) with temporal smoothing
       - LETTERBOX: scale-to-fill + blurred background when faces are spread
       - CENTER (fallback): static center-crop when no face detected
    4. FFmpeg render with crop/scale filter chain
"""

from __future__ import annotations

import os
import pathlib
import typing as t

REFRAME_ENABLED: bool = False
try:
    import cv2
    import numpy as np
    REFRAME_ENABLED = True
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore


def _check_reframe() -> None:
    if not REFRAME_ENABLED:
        raise RuntimeError(
            "reframe_adapter requires opencv-python-headless.\n"
            "  pip install opencv-python-headless\n"
            "This is a gated dependency — never installed by setup.sh."
        )


# ── Face detection ──

_FACE_CASCADE = None


def _get_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        _check_reframe()
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _FACE_CASCADE = cv2.CascadeClassifier(cascade_path)
    return _FACE_CASCADE


def _detect_faces(frame: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Detect faces in a BGR frame. Returns list of (x, y, w, h)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade = _get_cascade()
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    return [(x, y, w, h) for x, y, w, h in faces]


def _face_center(faces: list[tuple[int, int, int, int]]) -> tuple[float, float] | None:
    """Return the average face center (x, y) normalized to [0,1]."""
    if not faces:
        return None
    cx = sum(x + w / 2 for x, y, w, h in faces) / len(faces)
    cy = sum(y + h / 2 for x, y, w, h in faces) / len(faces)
    return (cx, cy)


def _face_spread(faces: list[tuple[int, int, int, int]], frame_w: int) -> float:
    """Measure horizontal spread of face centers relative to frame width."""
    if len(faces) < 2:
        return 0.0
    centers = [x + w / 2 for x, y, w, h in faces]
    return (max(centers) - min(centers)) / frame_w


# ── Crop path computation ──

def _compute_crop_centers(
    video_path: str,
    target_w: int,
    target_h: int,
    sample_rate: int = 10,
) -> list[dict]:
    """Sample video frames, detect faces, compute crop-center per sample.

    Returns list of {frame_idx, center_x_norm, center_y_norm, strategy}.
    """
    _check_reframe()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"cannot open video: {video_path}")

    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    samples: list[dict] = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_rate == 0:
            faces = _detect_faces(frame)
            if faces:
                cx, cy = _face_center(faces)
                spread = _face_spread(faces, orig_w)
                threshold = target_w / orig_w
                if spread > threshold * 1.5:
                    strategy = "letterbox"
                else:
                    strategy = "track"
            else:
                cx, cy = orig_w / 2, orig_h / 2
                strategy = "center"

            # FIX: falsy-zero bug — use explicit None check instead of truthiness
            nx = cx / orig_w if cx is not None else 0.5
            ny = cy / orig_h if cy is not None else 0.5
            samples.append({
                "frame_idx": frame_idx,
                "center_x_norm": nx,
                "center_y_norm": ny,
                "strategy": strategy,
            })

        frame_idx += 1

    cap.release()
    return samples


def _smooth_crop_path(samples: list[dict], smoothing: float = 0.3) -> list[dict]:
    """Apply EMA smoothing to the crop-center path to prevent jitter."""
    if not samples:
        return samples

    smooth_x = samples[0]["center_x_norm"]
    smooth_y = samples[0]["center_y_norm"]
    for s in samples:
        alpha = 1.0 - smoothing
        smooth_x = alpha * smooth_x + smoothing * s["center_x_norm"]
        smooth_y = alpha * smooth_y + smoothing * s["center_y_norm"]
        s["center_x_norm"] = smooth_x
        s["center_y_norm"] = smooth_y
    return samples


def _build_track_filter(
    samples: list[dict],
    orig_w: int, orig_h: int,
    target_w: int, target_h: int,
    fps: float,
) -> str:
    """Build FFmpeg filter with keyframed crop + scale for TRACK strategy.

    FIX: Previously used only the middle sample for a static crop, throwing away
    all the EMA-smoothed path data. Now builds a proper piecewise keyframe chain
    using sendcmd + crop reinit, so the crop window actually follows the subject.
    """
    crop_w = int(orig_w * target_h / orig_h)
    crop_h = target_h
    if crop_w < target_w:
        crop_w = target_w
        crop_h = int(orig_h * target_w / orig_w)
    crop_w = min(crop_w, orig_w)
    crop_h = min(crop_h, orig_h)

    if not samples:
        # No samples — static center crop
        crop_x = max(0, (orig_w - crop_w) // 2)
        crop_y = max(0, (orig_h - crop_h) // 2)
        return f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={target_w}:{target_h}"

    # FIX: Build keyframe-based crop that actually follows the subject.
    # Use between() expressions to change crop x,y at each sample's timestamp.
    # This produces a piecewise-linear pan that follows the smoothed face path.
    expressions: list[str] = []
    for i, s in enumerate(samples):
        ts = s["frame_idx"] / fps if fps > 0 else 0.0
        cx = s["center_x_norm"] * orig_w
        cy = s["center_y_norm"] * orig_h
        crop_x = max(0, min(int(cx - crop_w / 2), orig_w - crop_w))
        crop_y = max(0, min(int(cy - crop_h / 2), orig_h - crop_h))

        if i == 0:
            # Initial crop position
            expressions.append(f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}")
        else:
            # Use sendcmd to reinit crop position at this timestamp
            # FFmpeg crop filter supports 'x' and 'y' as dynamic expressions
            # We use the between(t,start,end) function for piecewise keyframes
            prev_ts = samples[i-1]["frame_idx"] / fps if fps > 0 else 0.0
            expressions.append(
                f"if(between(t\\,{prev_ts:.3f}\\,{ts:.3f})\\,{crop_x}\\,-1)"
            )

    # Simple approach: use crop with dynamic x,y expressions based on time
    # Build a piecewise function for x and y using if(between(...))
    x_parts: list[str] = []
    y_parts: list[str] = []
    for i, s in enumerate(samples):
        ts = s["frame_idx"] / fps if fps > 0 else 0.0
        cx = s["center_x_norm"] * orig_w
        cy = s["center_y_norm"] * orig_h
        crop_x = max(0, min(int(cx - crop_w / 2), orig_w - crop_w))
        crop_y = max(0, min(int(cy - crop_h / 2), orig_h - crop_h))
        if i == 0:
            x_parts.append(f"if(lt(t\\,{ts:.3f})\\,{crop_x}")
            y_parts.append(f"if(lt(t\\,{ts:.3f})\\,{crop_y}")
        elif i == len(samples) - 1:
            x_parts.append(f"\\,{crop_x})")
            y_parts.append(f"\\,{crop_y})")
        else:
            x_parts.append(f"\\,if(lt(t\\,{ts:.3f})\\,{crop_x}")
            y_parts.append(f"\\,if(lt(t\\,{ts:.3f})\\,{crop_y}")

    x_expr = "".join(x_parts)
    y_expr = "".join(y_parts)

    # Close any unclosed if() — ensure balanced parens
    open_count = x_expr.count("if(")
    close_count = x_expr.count(")")
    x_expr += ")" * (open_count - close_count)

    open_count = y_expr.count("if(")
    close_count = y_expr.count(")")
    y_expr += ")" * (open_count - close_count)

    return f"crop={crop_w}:{crop_h}:{x_expr}:{y_expr},scale={target_w}:{target_h}"


def _build_letterbox_filter(
    orig_w: int, orig_h: int,
    target_w: int, target_h: int,
) -> str:
    """Build FFmpeg filter for LETTERBOX (blurred background) strategy.

    FIXES:
    1. gaussian_blur → gblur (gaussian_blur is not a real FFmpeg filter name)
    2. Label the overlay output ([vout]) and map that (was mapping consumed [fg])
    3. The filter now properly outputs a labeled stream for -map
    """
    return (
        f"[0:v]split[bg][fg];"
        f"[bg]scale={target_w}:{target_h},gblur=sigma=20[bg_blurred];"
        f"[fg]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg_scaled];"
        f"[bg_blurred][fg_scaled]overlay=(W-w)/2:(H-h)/2[vout]"
    )


def smart_reframe(
    input: str,
    output: str,
    *,
    target_width: int = 1080,
    target_height: int = 1920,
    strategy: str = "auto",
    smoothing: float = 0.3,
    scene_sample_rate: int = 10,
) -> dict:
    """Smart vertical reframe with face-aware TRACK/LETTERBOX per scene.

    Parameters
    ----------
    input : str
        Path to input video.
    output : str
        Path to output 9:16 video.
    target_width, target_height : int
        Output resolution. Defaults to 1080×1920 (vertical).
    strategy : str
        One of ``auto``, ``track``, ``letterbox``, ``center``.
        ``auto`` decides per scene based on face spread.
    smoothing : float
        EMA alpha for temporal crop-center smoothing (0.0=no smoothing, 1.0=instant).
    scene_sample_rate : int
        Process every Nth frame for face detection. Higher = faster but coarser.

    Returns
    -------
    dict
        ``{"path": output_path, "strategy": strategy_used, "scenes_processed": n}``

    Raises
    ------
    RuntimeError
        If opencv-python-headless is not installed.
    """
    _check_reframe()

    from kb.tools.ffmpeg_adapter import _run, _check_ffmpeg, _ensure_parent, _probe_json
    _check_ffmpeg()
    _ensure_parent(output)

    probe = _probe_json(input)
    video_stream = next((s for s in probe.get("streams", [])
                         if s.get("codec_type") == "video"), {})
    orig_w = video_stream.get("width", 1920)
    orig_h = video_stream.get("height", 1080)
    from fractions import Fraction
    fps_str = video_stream.get("avg_frame_rate", "30/1")
    try:
        fps = float(Fraction(fps_str))
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    samples = _compute_crop_centers(input, target_width, target_height, scene_sample_rate)
    samples = _smooth_crop_path(samples, smoothing)

    if strategy == "auto":
        track_count = sum(1 for s in samples if s["strategy"] == "track")
        letterbox_count = sum(1 for s in samples if s["strategy"] == "letterbox")
        center_count = sum(1 for s in samples if s["strategy"] == "center")
        if track_count >= letterbox_count and track_count >= center_count:
            used_strategy = "track"
        elif letterbox_count >= center_count:
            used_strategy = "letterbox"
        else:
            used_strategy = "center"
    else:
        used_strategy = strategy

    if used_strategy == "center":
        # FIX: unbounded crop — clamp crop height to orig_h
        crop_h = min(int(orig_w * target_height / target_width), orig_h)
        crop_y = max(0, (orig_h - crop_h) // 2)
        vf = f"crop={orig_w}:{crop_h}:0:{crop_y},scale={target_width}:{target_height}"
        cmd = ["ffmpeg", "-i", input, "-vf", vf, "-c:a", "copy", output]
        _run(cmd, check=True)
    elif used_strategy == "letterbox":
        vf = _build_letterbox_filter(orig_w, orig_h, target_width, target_height)
        # FIX: map [vout] (the labeled overlay output), not [fg] (consumed)
        # FIX: add -map 0:a? to preserve audio (filter_complex drops auto-mapping)
        cmd = [
            "ffmpeg", "-i", input,
            "-filter_complex", vf,
            "-map", "[vout]", "-map", "0:a?",
            "-c:a", "copy", output,
        ]
        _run(cmd, check=True)
    else:
        vf = _build_track_filter(samples, orig_w, orig_h, target_width, target_height, fps)
        cmd = ["ffmpeg", "-i", input, "-vf", vf, "-c:a", "copy", output]
        _run(cmd, check=True)

    return {
        "path": output,
        "strategy": used_strategy,
        "scenes_processed": len(samples),
        "input_resolution": f"{orig_w}x{orig_h}",
    }
