"""
Timeline composite PNG renderer (video-use pattern).

Renders a filmstrip + waveform + peak-markers PNG so the LLM (or human) can
'see' the video at a glance without processing every frame. Used as a
decision-support artifact by the intelligent planner.

Public surface:
  - render_timeline(video_path, per_second, peaks, duration, output_path) -> path | None
"""
from __future__ import annotations

import pathlib
import subprocess
import typing as t


def render_timeline(video_path: str, per_second: list[dict], peaks: dict,
                    duration: float, output_path: str,
                    num_frames: int = 16) -> t.Optional[str]:
    """Render filmstrip + waveform + peak markers PNG. Returns path or None on failure."""
    try:
        import av
        import numpy as np
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    FRAME_W, FRAME_H = 160, 90
    WAVEFORM_H = 60
    LABELS_H = 80
    MARGIN = 8
    WIDTH = num_frames * FRAME_W + (num_frames + 1) * MARGIN
    HEIGHT = FRAME_H + WAVEFORM_H + LABELS_H + 4 * MARGIN
    IMG = Image.new("RGB", (WIDTH, HEIGHT), (20, 20, 30))
    draw = ImageDraw.Draw(IMG)

    # 1. Filmstrip
    try:
        container = av.open(video_path)
        total_frames = int(duration * 30)
        if total_frames <= 0:
            container.close()
            return None
        sample_indices = set(int(x) for x in np.linspace(0, total_frames - 1, num_frames))
        frame_idx = 0
        x = MARGIN
        for frame in container.decode(video=0):
            if frame_idx in sample_indices:
                try:
                    img = frame.to_ndarray(format="rgb24")
                    pil = Image.fromarray(img).resize((FRAME_W, FRAME_H))
                    IMG.paste(pil, (x, MARGIN))
                    ts = frame_idx / 30.0
                    m, s = int(ts // 60), int(ts % 60)
                    draw.text((x + 2, MARGIN + FRAME_H + 2), f"{m:02d}:{s:02d}",
                              fill=(150, 150, 150))
                    x += FRAME_W + MARGIN
                except Exception:
                    pass
            frame_idx += 1
            if frame_idx > max(sample_indices) + 1:
                break
        container.close()
    except Exception:
        pass

    # 2. Waveform
    wav_path = output_path.replace(".png", "_tmp.wav")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1",
             "-ar", "8000", "-c:a", "pcm_s16le", wav_path],
            capture_output=True, check=True, timeout=120,
        )
        import wave
        with wave.open(wav_path) as wf:
            frames = wf.readframes(wf.getnframes())
            samples = np.frombuffer(frames, dtype=np.int16)
        pathlib.Path(wav_path).unlink(missing_ok=True)

        chunk_size = max(1, len(samples) // WIDTH)
        waveform = np.abs(samples[::chunk_size])[:WIDTH]
        max_val = max(int(waveform.max()) if len(waveform) else 1, 1)
        wave_y = MARGIN * 2 + FRAME_H + LABELS_H // 2
        for i, val in enumerate(waveform):
            h = int((int(val) / max_val) * (WAVEFORM_H // 2))
            draw.line([(i, wave_y - h), (i, wave_y + h)], fill=(100, 200, 255), width=1)
    except Exception:
        if pathlib.Path(wav_path).exists():
            pathlib.Path(wav_path).unlink(missing_ok=True)

    # 3. Peak markers
    if duration > 0:
        for mp in peaks.get("motion", []):
            x = int((mp["timestamp"] / duration) * WIDTH)
            draw.rectangle([x - 1, MARGIN, x + 1, MARGIN + FRAME_H], fill=(255, 50, 50))
        for ep in peaks.get("emotion", []):
            x = int((ep["timestamp"] / duration) * WIDTH)
            draw.rectangle([x - 1, MARGIN, x + 1, MARGIN + FRAME_H], fill=(255, 220, 50))
        for ao in peaks.get("audio_onset", [])[:20]:
            x = int((ao / duration) * WIDTH)
            draw.line([(x, MARGIN * 2 + FRAME_H), (x, MARGIN * 2 + FRAME_H + WAVEFORM_H)],
                      fill=(100, 255, 200), width=1)

    try:
        IMG.save(output_path)
        return output_path
    except Exception:
        return None
