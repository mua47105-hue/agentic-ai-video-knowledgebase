#!/usr/bin/env python3
"""
Generate deterministic synthetic test clips using ffmpeg lavfi sources.

No fixtures, no downloads, fully reproducible. Used by test_recipes_e2e.py.

Outputs:
  - talking_head.mp4     — 30s, 1280x720, 30fps, sine tone audio
  - podcast.mp4          — 60s, 1280x720, 25fps, dual-tone audio
  - vlog_short.mp4       — 15s, 1080x1920 (vertical), 30fps, music-like audio
  - silent.mp4           — 10s, no audio (for testing audio-handling edge cases)

Usage:
    python3 scripts/make_synthetic_clip.py --all --out /tmp/test_clips/
    python3 scripts/make_synthetic_clip.py talking_head --out /tmp/test_clips/
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

CLIPS = {
    "talking_head": {
        "duration": 30,
        "video_filter": (
            "testsrc2=size=1280x720:rate=30,"
            "drawtext=text='talking head test clip':fontcolor=white:fontsize=48:"
            "x=(w-text_w)/2:y=(h-text_h)/2,"
            "hue=s=0"
        ),
        "audio_filter": "sine=frequency=220:duration=30,volume=0.3",
        "desc": "30s 720p with sine tone (simulates talking-head)",
    },
    "podcast": {
        "duration": 60,
        "video_filter": (
            "testsrc2=size=1280x720:rate=25,"
            "drawtext=text='podcast test':fontcolor=white:fontsize=48:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        "audio_filter": "sine=frequency=180:duration=60,volume=0.25",
        "desc": "60s 720p with lower tone (simulates podcast)",
    },
    "vlog_short": {
        "duration": 15,
        "video_filter": (
            "testsrc2=size=1080x1920:rate=30,"
            "drawtext=text='vlog short':fontcolor=white:fontsize=64:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        "audio_filter": "sine=frequency=440:duration=15,volume=0.2",
        "desc": "15s vertical 1080x1920 (simulates social short)",
    },
    "silent": {
        "duration": 10,
        "video_filter": (
            "testsrc2=size=1280x720:rate=30,"
            "drawtext=text='no audio':fontcolor=white:fontsize=48:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
        ),
        "audio_filter": None,
        "desc": "10s 720p with NO audio (edge-case testing)",
    },
}


def make_clip(name: str, out_dir: Path) -> Path:
    spec = CLIPS[name]
    out_path = out_dir / f"{name}.mp4"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

    cmd += ["-f", "lavfi", "-i", spec["video_filter"]]

    if spec["audio_filter"]:
        cmd += ["-f", "lavfi", "-i", spec["audio_filter"]]

    cmd += ["-t", str(spec["duration"])]

    cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p"]
    if spec["audio_filter"]:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-shortest"]

    cmd += [str(out_path)]

    subprocess.run(cmd, check=True)
    print(f"  created {out_path} ({spec['desc']})")
    return out_path


def main():
    p = argparse.ArgumentParser(description="Generate synthetic test clips")
    p.add_argument("clip", nargs="?", choices=list(CLIPS.keys()),
                   help="Which clip to generate (default: all)")
    p.add_argument("--all", action="store_true", help="Generate all clips")
    p.add_argument("--out", default="/tmp/test_clips", help="Output directory")
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.all or not args.clip:
        for name in CLIPS:
            make_clip(name, out_dir)
    else:
        make_clip(args.clip, out_dir)

    print(f"\nAll clips in: {out_dir}")


if __name__ == "__main__":
    main()
