"""Synthetic video clip fixtures for testing.

Generates short synthetic clips via ffmpeg lavfi so tests don't need real footage.
"""
from __future__ import annotations

import pathlib
import subprocess
import pytest


CLIPS_DIR = pathlib.Path("/tmp/test_clips")


def _make_clip(name: str, duration: float, size: str, rate: int,
               freq: int, drawtext: str = "") -> pathlib.Path:
    """Generate a synthetic clip. Returns path."""
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    out = CLIPS_DIR / f"{name}.mp4"
    if out.exists() and out.stat().st_size > 1000:
        return out  # reuse existing
    vf = f"testsrc2=duration={duration}:size={size}:rate={rate}"
    if drawtext:
        vf += f",drawtext=text='{drawtext}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2"
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", vf,
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-c:a", "aac", "-shortest", str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=60)
    return out


@pytest.fixture(scope="session")
def talking_head_clip():
    """A 5s 640x360 clip with mid-frequency audio (simulates talking head)."""
    return _make_clip("talking_head", 5, "640x360", 30, 220, "test")


@pytest.fixture(scope="session")
def short_clip():
    """A 3s 320x240 clip (minimal, for fast tests)."""
    return _make_clip("short", 3, "320x240", 15, 440)


@pytest.fixture(scope="session")
def vertical_clip():
    """A 4s 360x640 vertical clip (simulates phone video)."""
    return _make_clip("vertical", 4, "360x640", 30, 110, "action")
