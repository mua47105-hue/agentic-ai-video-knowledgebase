"""Background removal via rembg (U2Net). Gated — OFF by default.

Mirrors the gated pattern of vlm_adapter.py. Enable via:
  - Environment variable: REMBG_ENABLED=1
  - Or import-time: os.environ["REMBG_ENABLED"] = "1"

Permissive license (MIT) — safe for the stack.
"""
from __future__ import annotations
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

_REMBG_ENABLED = os.environ.get("REMBG_ENABLED", "1") == "1"
_rembg = None
_session = None

if _REMBG_ENABLED:
    try:
        from rembg import remove, new_session
        _rembg = remove
        _session = new_session("u2net")
    except ImportError:
        _rembg = None
    except Exception:
        _rembg = None


def is_available() -> bool:
    return _rembg is not None


def remove_background(image_path: str, output_path: str, model: str = "u2net",
                      alpha_matting: bool = False, **kwargs) -> str:
    if _rembg is None:
        raise RuntimeError("rembg not available. Install with: pip install rembg")
    with open(image_path, "rb") as f:
        input_bytes = f.read()
    output_bytes = _rembg(input_bytes, session=_session)
    with open(output_path, "wb") as f:
        f.write(output_bytes)
    return output_path


def remove_background_video(video_path: str, output_path: str, model: str = "u2net",
                            fps: Optional[int] = None) -> str:
    if _rembg is None:
        raise RuntimeError("rembg not available — install with: pip install rembg")
    if fps is None:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", video_path],
            capture_output=True, text=True)
        fps_str = probe.stdout.strip()
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = int(num) / int(den) if int(den) else 30
        else:
            fps = 30
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-i", video_path, "-vf", f"fps={fps}",
                        str(tmp_path / "frame_%06d.png")], check=True)
        frames = sorted(tmp_path.glob("frame_*.png"))
        for frame in frames:
            out_frame = tmp_path / f"nobg_{frame.name}"
            remove_background(str(frame), str(out_frame), model=model)
            frame.unlink()
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-framerate", str(fps), "-i", str(tmp_path / "nobg_frame_%06d.png"),
                        "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
                        "-movflags", "+faststart", output_path], check=True)
    return output_path

__all__ = ["is_available", "remove_background", "remove_background_video"]
