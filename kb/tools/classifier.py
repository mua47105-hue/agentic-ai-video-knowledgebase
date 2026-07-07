"""
Local content-type classifier for video editing.

Takes an input video path, runs Whisper transcription (if not provided) and
ffprobe metadata extraction, then classifies into one of 10 content types:
  talking-head, podcast, vlog, tutorial, cinematic, social-short,
  music-video, documentary, interview, event

Pure-rule-based. No cloud, no GPU, no model beyond Whisper.

Returns: {"content_type": str, "confidence": float, "signals": dict, "reasoning": str}
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import typing as t
from dataclasses import dataclass, field


@dataclass
class ContentSignals:
    duration: float = 0.0
    width: int = 0
    height: int = 0
    aspect_ratio: float = 0.0
    has_audio: bool = False
    audio_lufs_mean: float = -70.0
    audio_lufs_std: float = 0.0
    scene_count: int = 0
    cuts_per_minute: float = 0.0
    word_count: int = 0
    words_per_minute: float = 0.0
    filler_word_ratio: float = 0.0
    silence_ratio: float = 0.0

    def as_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


FILLER_WORDS = {
    "um", "uh", "like", "you know", "basically", "actually", "literally",
    "kind of", "sort of", "i mean", "right", "so yeah", "anyway",
}


def extract_signals(video_path: str, transcript: t.Optional[list[dict]] = None) -> ContentSignals:
    s = ContentSignals()

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration",
         "-of", "json", video_path],
        capture_output=True, text=True
    )
    if probe.returncode == 0:
        data = json.loads(probe.stdout)
        streams = data.get("streams", [])
        if streams:
            s.width = int(streams[0].get("width", 0))
            s.height = int(streams[0].get("height", 0))
            if s.height:
                s.aspect_ratio = s.width / s.height
        fmt = data.get("format", {})
        s.duration = float(fmt.get("duration", 0))

    probe_a = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    s.has_audio = "audio" in probe_a.stdout

    if s.has_audio and s.duration > 0:
        ebur = subprocess.run(
            ["ffmpeg", "-i", video_path, "-hide_banner", "-nostats",
             "-filter_complex", "ebur128=peak=true", "-f", "null", "-"],
            capture_output=True, text=True, timeout=60
        )
        for line in ebur.stderr.split("\n"):
            if "I:" in line and "LUFS" in line:
                try:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "I:":
                            s.audio_lufs_mean = float(parts[i+1])
                        if p == "LRA:":
                            s.audio_lufs_std = float(parts[i+2])
                except (ValueError, IndexError):
                    pass
                break

        sil = subprocess.run(
            ["ffmpeg", "-i", video_path, "-hide_banner", "-nostats",
             "-af", "silencedetect=n=-50dB:d=0.5", "-f", "null", "-"],
            capture_output=True, text=True, timeout=60
        )
        silence_total = 0.0
        sil_start = None
        for line in sil.stderr.split("\n"):
            if "silence_start" in line:
                try:
                    sil_start = float(line.split("silence_start:")[1].strip())
                except (ValueError, IndexError):
                    pass
            elif "silence_end" in line and sil_start is not None:
                try:
                    sil_end = float(line.split("silence_end:")[1].split()[0])
                    silence_total += sil_end - sil_start
                    sil_start = None
                except (ValueError, IndexError):
                    pass
        if s.duration > 0:
            s.silence_ratio = silence_total / s.duration

    sc = subprocess.run(
        ["ffmpeg", "-i", video_path, "-hide_banner", "-nostats",
         "-filter:v", "scdet=threshold=30", "-f", "null", "-"],
        capture_output=True, text=True, timeout=120
    )
    s.scene_count = sc.stderr.count("scene_change")
    if s.duration > 0:
        s.cuts_per_minute = s.scene_count / (s.duration / 60.0)

    if transcript is None:
        try:
            from kb.tools.ffmpeg_adapter import transcribe
            result = transcribe(video_path, model="base")
            transcript = result.get("segments", [])
        except Exception:
            transcript = []

    if transcript:
        total_words = 0
        filler_count = 0
        for seg in transcript:
            text = seg.get("text", "").lower()
            words = text.split()
            total_words += len(words)
            for fw in FILLER_WORDS:
                filler_count += text.count(fw)
        s.word_count = total_words
        if s.duration > 0:
            s.words_per_minute = total_words / (s.duration / 60.0)
        if total_words > 0:
            s.filler_word_ratio = filler_count / total_words

    return s


def classify(signals: ContentSignals) -> dict:
    scores: dict[str, float] = {ct: 0.0 for ct in [
        "talking-head", "podcast", "vlog", "tutorial", "cinematic",
        "social-short", "music-video", "documentary", "interview", "event"
    ]}
    reasoning: list[str] = []

    ar = signals.aspect_ratio
    if ar > 0:
        if 0.5 <= ar <= 0.6:
            scores["social-short"] += 3
            reasoning.append(f"aspect {ar:.2f} -> vertical (social-short)")
        elif 1.7 <= ar <= 1.8:
            scores["podcast"] += 1; scores["vlog"] += 1; scores["tutorial"] += 1
            scores["talking-head"] += 1; scores["interview"] += 1
            reasoning.append(f"aspect {ar:.2f} -> 16:9 (podcast/vlog/tutorial)")
        elif ar >= 2.0:
            scores["cinematic"] += 3
            reasoning.append(f"aspect {ar:.2f} -> ultrawide (cinematic)")

    dur = signals.duration
    if dur > 0:
        if dur < 90:
            scores["social-short"] += 3
            reasoning.append(f"duration {dur:.0f}s -> social-short")
        elif 90 <= dur < 600:
            scores["vlog"] += 2; scores["tutorial"] += 1
            reasoning.append(f"duration {dur:.0f}s -> vlog/tutorial")
        elif 600 <= dur < 1800:
            scores["talking-head"] += 2; scores["interview"] += 1; scores["tutorial"] += 1
            reasoning.append(f"duration {dur:.0f}s -> talking-head/interview")
        elif dur >= 1800:
            scores["podcast"] += 3; scores["documentary"] += 1
            reasoning.append(f"duration {dur:.0f}s -> long-form (podcast/documentary)")

    cpm = signals.cuts_per_minute
    if cpm > 0:
        if cpm < 3:
            scores["podcast"] += 2; scores["talking-head"] += 1
            reasoning.append(f"cuts/min {cpm:.1f} -> low (podcast/talking-head)")
        elif 3 <= cpm < 10:
            scores["tutorial"] += 1; scores["interview"] += 1; scores["documentary"] += 1
            reasoning.append(f"cuts/min {cpm:.1f} -> medium (tutorial/interview)")
        elif 10 <= cpm < 25:
            scores["vlog"] += 2; scores["music-video"] += 1
            reasoning.append(f"cuts/min {cpm:.1f} -> high (vlog/music-video)")
        elif cpm >= 25:
            scores["social-short"] += 2; scores["music-video"] += 2
            reasoning.append(f"cuts/min {cpm:.1f} -> very high (social-short/music-video)")

    wpm = signals.words_per_minute
    if wpm > 0:
        if wpm < 80:
            scores["cinematic"] += 2; scores["music-video"] += 2; scores["event"] += 1
            reasoning.append(f"words/min {wpm:.0f} -> very low (cinematic/music-video)")
        elif 80 <= wpm < 130:
            scores["documentary"] += 2; scores["vlog"] += 1
            reasoning.append(f"words/min {wpm:.0f} -> low (documentary/vlog)")
        elif 130 <= wpm < 170:
            scores["podcast"] += 2; scores["tutorial"] += 2; scores["talking-head"] += 1
            reasoning.append(f"words/min {wpm:.0f} -> conversational (podcast/tutorial)")
        elif wpm >= 170:
            scores["vlog"] += 2; scores["social-short"] += 1
            reasoning.append(f"words/min {wpm:.0f} -> fast (vlog/social-short)")

    fwr = signals.filler_word_ratio
    if fwr > 0:
        if fwr > 0.04:
            scores["podcast"] += 2; scores["talking-head"] += 1; scores["vlog"] += 1
            reasoning.append(f"filler ratio {fwr:.3f} -> high (unscripted)")
        elif fwr < 0.01:
            scores["cinematic"] += 1; scores["documentary"] += 1; scores["tutorial"] += 1
            reasoning.append(f"filler ratio {fwr:.3f} -> low (scripted)")

    sr = signals.silence_ratio
    if sr > 0:
        if sr > 0.15:
            scores["podcast"] += 1; scores["interview"] += 1
            reasoning.append(f"silence ratio {sr:.2f} -> high (podcast/interview)")
        elif sr < 0.02:
            scores["social-short"] += 1; scores["music-video"] += 1; scores["vlog"] += 1
            reasoning.append(f"silence ratio {sr:.2f} -> low (social/music-video)")

    if signals.audio_lufs_std > 0:
        if signals.audio_lufs_std > 12:
            scores["cinematic"] += 2; scores["music-video"] += 1
            reasoning.append(f"audio LRA {signals.audio_lufs_std:.1f}dB -> wide (cinematic)")
        elif signals.audio_lufs_std < 5:
            scores["podcast"] += 1; scores["talking-head"] += 1
            reasoning.append(f"audio LRA {signals.audio_lufs_std:.1f}dB -> narrow (podcast)")

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[best] / total if total > 0 else 0.0

    return {
        "content_type": best,
        "confidence": round(confidence, 3),
        "scores": {k: round(v, 2) for k, v in sorted(scores.items(), key=lambda x: -x[1])},
        "signals": signals.as_dict(),
        "reasoning": "; ".join(reasoning),
    }


def classify_video(video_path: str, transcript: t.Optional[list[dict]] = None) -> dict:
    signals = extract_signals(video_path, transcript=transcript)
    return classify(signals)


RECIPE_TO_CONTENT_TYPE = {
    "podcast-to-shorts": "podcast",
    "documentary-assembly": "documentary",
    "shorts-punchy": "social-short",
    "wedding-highlights": "cinematic",
    "sports-highlights": "event",
    "tutorial-editing": "tutorial",
    "vlog-assembly": "vlog",
}


def recommend_recipe(classification: dict, recipes_dir: str = "recipes") -> t.Optional[str]:
    detected = classification["content_type"]
    for recipe_name, ct in RECIPE_TO_CONTENT_TYPE.items():
        if ct == detected:
            return recipe_name
    if detected == "talking-head":
        return "podcast-to-shorts"
    if detected == "interview":
        return "podcast-to-shorts"
    if detected == "music-video":
        return "vlog-assembly"
    if detected == "event":
        return "wedding-highlights"
    return None
