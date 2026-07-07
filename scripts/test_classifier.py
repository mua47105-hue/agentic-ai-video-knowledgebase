"""Tests for kb/tools/classifier.py — content-type classifier."""
from __future__ import annotations

import sys
import json
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from kb.tools.classifier import ContentSignals, classify, recommend_recipe


def check(condition: bool, msg: str) -> None:
    if not condition:
        print(f"FAIL: {msg}")
        raise SystemExit(1)
    print(f"  ok: {msg}")


def test_classify_talking_head():
    s = ContentSignals(
        duration=900,
        width=1920, height=1080,
        aspect_ratio=1.777,
        has_audio=True,
        audio_lufs_mean=-16, audio_lufs_std=4,
        scene_count=20,
        cuts_per_minute=1.33,
        word_count=4500,
        words_per_minute=300,
        filler_word_ratio=0.03,
        silence_ratio=0.05,
    )
    r = classify(s)
    check(r["content_type"] in ("podcast", "talking-head", "tutorial"),
           f"longform medium-word-rate → {r['content_type']} (conf={r['confidence']})")
    check(0 < r["confidence"] <= 1.0, "confidence in range")
    check(len(r["reasoning"]) > 10, "reasoning non-empty")


def test_classify_social_short():
    s = ContentSignals(
        duration=30,
        width=1080, height=1920,
        aspect_ratio=0.5625,
        has_audio=True,
        audio_lufs_mean=-14,
        scene_count=15,
        cuts_per_minute=30,
        word_count=100,
        words_per_minute=200,
        filler_word_ratio=0.01,
        silence_ratio=0.01,
    )
    r = classify(s)
    check(r["content_type"] == "social-short",
           f"vertical short high-cut → social-short, got {r['content_type']}")
    check(r["confidence"] > 0.2, "confidence positive")


def test_classify_cinematic():
    s = ContentSignals(
        duration=600,
        width=3840, height=1600,
        aspect_ratio=2.4,
        has_audio=True,
        audio_lufs_mean=-23, audio_lufs_std=15,
        scene_count=60,
        cuts_per_minute=6,
        word_count=300,
        words_per_minute=30,
        filler_word_ratio=0.001,
        silence_ratio=0.1,
    )
    r = classify(s)
    check(r["content_type"] == "cinematic",
           f"ultrawide low-word-rate → cinematic, got {r['content_type']}")


def test_classify_podcast():
    s = ContentSignals(
        duration=3600,
        width=1920, height=1080,
        aspect_ratio=1.777,
        has_audio=True,
        audio_lufs_mean=-16, audio_lufs_std=3,
        scene_count=5,
        cuts_per_minute=0.08,
        word_count=18000,
        words_per_minute=300,
        filler_word_ratio=0.05,
        silence_ratio=0.2,
    )
    r = classify(s)
    check(r["content_type"] == "podcast",
           f"long narrow-LRA high-filler → podcast, got {r['content_type']}")


def test_classify_music_video():
    s = ContentSignals(
        duration=240,
        width=1920, height=1080,
        aspect_ratio=1.777,
        has_audio=True,
        audio_lufs_mean=-10, audio_lufs_std=14,
        scene_count=80,
        cuts_per_minute=20,
        word_count=120,
        words_per_minute=30,
        filler_word_ratio=0.001,
        silence_ratio=0.005,
    )
    r = classify(s)
    check(r["content_type"] in ("music-video", "vlog"),
           f"high-cut low-word-rate → music-video/vlog, got {r['content_type']}")


def test_recommend_recipe():
    r = recommend_recipe({"content_type": "podcast"})
    check(r == "podcast-to-shorts", f"podcast → podcast-to-shorts, got {r}")

    r2 = recommend_recipe({"content_type": "social-short"})
    check(r2 == "shorts-punchy", f"social-short → shorts-punchy, got {r2}")

    r3 = recommend_recipe({"content_type": "talking-head"})
    check(r3 == "podcast-to-shorts", f"talking-head → podcast-to-shorts, got {r3}")

    r4 = recommend_recipe({"content_type": "unknown"})
    check(r4 is None, f"unknown → None, got {r4}")


def test_classify_no_audio():
    s = ContentSignals(
        duration=60,
        width=1920, height=1080,
        aspect_ratio=1.777,
        has_audio=False,
    )
    r = classify(s)
    check("content_type" in r, "no-audio still produces a classification")


if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        print(f"[{name}]")
        fn()
    print("\nAll classifier tests passed.")
