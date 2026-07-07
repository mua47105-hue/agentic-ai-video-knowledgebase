"""
Audio feature extraction for the intelligent pipeline (Phase 6).

Extracts per-window audio features. Every heavy-model dependency is OPTIONAL:
the probe always returns a valid AudioProfile, with richer signals unlocked
when librosa / silero-vad / pyannote.audio / demucs / speechbrain are installed.

Public surface:
  - probe_audio(video_path, separate_stems=True) -> AudioProfile

Features extracted (best-effort):
  - audio presence + duration (ffprobe, always)
  - beats / downbeats / onsets / tempo (librosa)
  - speech vs silence segments (Silero VAD, optional)
  - speaker diarization (pyannote.audio, optional, HF-gated)
  - stem separation vocals/music (Demucs, optional)
  - prosody emotion (SpeechBrain, optional)
  - integrated loudness / LRA / true-peak (ffmpeg ebur128, always if audio)
"""
from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import subprocess
import tempfile
import typing as t


@dataclasses.dataclass
class AudioProfile:
    duration: float = 0.0
    sample_rate: int = 0
    has_audio: bool = False
    tempo: float = 0.0
    beats: list[float] = dataclasses.field(default_factory=list)
    downbeats: list[float] = dataclasses.field(default_factory=list)
    onsets: list[float] = dataclasses.field(default_factory=list)
    music_present: bool = False
    music_sections: list[dict] = dataclasses.field(default_factory=list)
    speech_segments: list[dict] = dataclasses.field(default_factory=list)
    silence_segments: list[dict] = dataclasses.field(default_factory=list)
    silence_ratio: float = 0.0
    speaker_segments: list[dict] = dataclasses.field(default_factory=list)
    speaker_count: int = 0
    stems_separated: bool = False
    vocals_path: t.Optional[str] = None
    music_path: t.Optional[str] = None
    prosody_emotion: list[dict] = dataclasses.field(default_factory=list)
    integrated_lufs: float = -70.0
    loudness_range: float = 0.0
    true_peak_db: float = -70.0
    per_second: list[dict] = dataclasses.field(default_factory=list)
    components_used: list[str] = dataclasses.field(default_factory=list)

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def extract_audio_wav(video_path: str, target_sr: int = 16000) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1",
         "-ar", str(target_sr), "-c:a", "pcm_s16le", tmp.name],
        capture_output=True, check=True,
    )
    return tmp.name


def probe_beats(audio_wav: str) -> tuple[float, list[float], list[float], list[float]]:
    """Returns (tempo, beats, downbeats, onsets). librosa required."""
    try:
        import librosa
        import numpy as np
    except ImportError:
        return 0.0, [], [], []

    try:
        y, sr = librosa.load(audio_wav, sr=None, mono=True)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        onsets = librosa.onset.onset_detect(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        onset_times = librosa.frames_to_time(onsets, sr=sr)
        downbeat_times = list(beat_times[::4])  # heuristic: every 4th beat
        return float(tempo), list(beat_times), downbeat_times, list(onset_times)
    except Exception:
        return 0.0, [], [], []


def probe_vad(audio_wav: str) -> tuple[list[dict], list[dict], float]:
    """Returns (speech_segments, silence_segments, silence_ratio). Silero required."""
    try:
        from silero_vad import load_silero_vad, read_audio, get_speech_timestamps
    except ImportError:
        return [], [], 0.0

    try:
        model = load_silero_vad()
        wav = read_audio(audio_wav)
        sr = 16000
        speech_ts = get_speech_timestamps(wav, model, return_seconds=True)
        silence_segments: list[dict] = []
        prev_end = 0.0
        total_duration = len(wav) / sr
        for seg in speech_ts:
            if seg["start"] > prev_end:
                silence_segments.append({"start": prev_end, "end": seg["start"]})
            prev_end = seg["end"]
        if prev_end < total_duration:
            silence_segments.append({"start": prev_end, "end": total_duration})
        silence_total = sum(s["end"] - s["start"] for s in silence_segments)
        silence_ratio = silence_total / total_duration if total_duration > 0 else 0.0
        return speech_ts, silence_segments, silence_ratio
    except Exception:
        return [], [], 0.0


def probe_diarization(audio_wav: str) -> tuple[list[dict], int]:
    """Returns (speaker_segments, speaker_count). pyannote required (HF-gated)."""
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        return [{"start": 0, "end": -1, "speaker": "SPEAKER_00"}], 1

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        return [{"start": 0, "end": -1, "speaker": "SPEAKER_00"}], 1

    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1", use_auth_token=hf_token
        )
        diarization = pipeline(audio_wav)
        segments: list[dict] = []
        speakers: set[str] = set()
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({"start": turn.start, "end": turn.end, "speaker": speaker})
            speakers.add(speaker)
        return segments, len(speakers)
    except Exception:
        return [{"start": 0, "end": -1, "speaker": "SPEAKER_00"}], 1


def probe_stems(audio_wav: str, output_dir: str) -> tuple[bool, t.Optional[str], t.Optional[str]]:
    """Separate vocals/music via Demucs. Returns (success, vocals_path, music_path)."""
    try:
        result = subprocess.run(
            ["python3", "-m", "demucs.separate", "-n", "htdemucs_ft",
             "--two-stems", "vocals", "-o", output_dir, audio_wav],
            capture_output=True, text=True, timeout=900,
        )
        if result.returncode != 0:
            return False, None, None
        basename = pathlib.Path(audio_wav).stem
        vocals = pathlib.Path(output_dir) / "htdemucs_ft" / basename / "vocals.wav"
        music = pathlib.Path(output_dir) / "htdemucs_ft" / basename / "no_vocals.wav"
        if vocals.exists() and music.exists():
            return True, str(vocals), str(music)
        return False, None, None
    except Exception:
        return False, None, None


def probe_prosody_emotion(audio_wav: str, segment_duration: float = 3.0) -> list[dict]:
    """Audio prosody emotion via SpeechBrain. Returns list of {start, end, emotion, confidence}."""
    try:
        from speechbrain.inference.emotion import EmotionRecognition
        import torchaudio
    except ImportError:
        return []

    try:
        classifier = EmotionRecognition.from_hparams(
            source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
            savedir=tempfile.gettempdir() + "/speechbrain_emotion",
        )
    except Exception:
        return []

    try:
        wav, sr = torchaudio.load(audio_wav)
    except Exception:
        return []

    total_duration = wav.shape[1] / sr
    segment_samples = int(segment_duration * sr)
    results: list[dict] = []

    for start_sec in range(0, int(total_duration), int(segment_duration)):
        end_sec = min(start_sec + segment_duration, total_duration)
        start_sample = int(start_sec * sr)
        end_sample = int(end_sec * sr)
        segment = wav[:, start_sample:end_sample]
        if segment.shape[1] < sr * 0.5:
            continue
        try:
            emotion, _, _, _ = classifier.classify_batch(segment)
            label = emotion[0] if isinstance(emotion, list) else str(emotion)
            results.append({
                "start": float(start_sec), "end": float(end_sec),
                "emotion": label.lower(), "confidence": 0.7,
            })
        except Exception:
            continue
    return results


def probe_loudness(video_path: str) -> tuple[float, float, float]:
    """Returns (integrated_lufs, loudness_range, true_peak_db).
    P1 #4 fix: uses loudnorm=print_format=json instead of ebur128 text parsing (more reliable on ffmpeg 7.x)."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", video_path, "-hide_banner", "-nostats",
             "-af", "loudnorm=print_format=json", "-f", "null", "-"],
            capture_output=True, text=True, timeout=600,
        )
        # loudnorm JSON output is in stderr, after the normal ffmpeg output
        stderr = result.stderr
        # Find the JSON block in stderr
        json_start = stderr.rfind("{")
        json_end = stderr.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                import json
                loudness_json = json.loads(stderr[json_start:json_end])
                integrated = float(loudness_json.get("input_i", -70.0))
                lra = float(loudness_json.get("input_lra", 0.0))
                tp = float(loudness_json.get("input_tp", -70.0))
                return integrated, lra, tp
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        # Fallback: try ebur128 text parsing (old method)
        integrated = -70.0
        lra = 0.0
        tp = -70.0
        for line in stderr.split("\n"):
            if "I:" in line and "LUFS" in line:
                try:
                    parts = line.split()
                    for i, p in enumerate(parts):
                        if p == "I:":
                            integrated = float(parts[i + 1])
                        elif p == "LRA:":
                            lra = float(parts[i + 2])
                        elif p == "TP:":
                            tp = float(parts[i + 2])
                except (ValueError, IndexError):
                    pass
                break
        return integrated, lra, tp
    except Exception:
        return -70.0, 0.0, -70.0


def probe_audio(video_path: str, separate_stems: bool = True) -> AudioProfile:
    """Run all available audio probes, merge into AudioProfile."""
    profile = AudioProfile()
    components: list[str] = []

    # Check audio presence
    try:
        probe_a = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type:format=duration",
             "-of", "json", video_path],
            capture_output=True, text=True, timeout=60,
        )
        if probe_a.returncode == 0:
            data = json.loads(probe_a.stdout)
            if data.get("streams"):
                profile.has_audio = True
                profile.duration = float(data.get("format", {}).get("duration", 0))
                components.append("ffprobe_audio")
    except Exception:
        pass

    if not profile.has_audio:
        profile.components_used = components
        return profile

    audio_wav = extract_audio_wav(video_path)
    try:
        # Beats
        profile.tempo, profile.beats, profile.downbeats, profile.onsets = probe_beats(audio_wav)
        if profile.tempo > 0:
            components.append("librosa_beats")

        # VAD
        profile.speech_segments, profile.silence_segments, profile.silence_ratio = probe_vad(audio_wav)
        if profile.speech_segments:
            components.append("silero_vad")

        # Diarization
        profile.speaker_segments, profile.speaker_count = probe_diarization(audio_wav)
        if profile.speaker_count > 0:
            components.append("pyannote_diarization")

        # Stems (slow — opt-in)
        if separate_stems:
            stems_dir = tempfile.mkdtemp(prefix="stems_")
            ok, voc, mus = probe_stems(audio_wav, stems_dir)
            if ok:
                profile.stems_separated = True
                profile.vocals_path = voc
                profile.music_path = mus
                profile.music_present = True
                components.append("demucs_stems")

        # Prosody emotion
        profile.prosody_emotion = probe_prosody_emotion(audio_wav)
        if profile.prosody_emotion:
            components.append("speechbrain_prosody")

        # Loudness
        profile.integrated_lufs, profile.loudness_range, profile.true_peak_db = probe_loudness(video_path)
        components.append("ebur128_loudness")

        # Per-second aggregation
        per_second: list[dict] = []
        for sec in range(int(profile.duration)):
            entry = {
                "ts": sec, "speech": False, "speaker": None,
                "prosody_emotion": None, "onset": False, "beat": False,
            }
            for seg in profile.speech_segments:
                if seg["start"] <= sec < seg["end"]:
                    entry["speech"] = True
                    break
            for seg in profile.speaker_segments:
                end = seg["end"] if seg["end"] > 0 else profile.duration
                if seg["start"] <= sec < end:
                    entry["speaker"] = seg["speaker"]
                    break
            for pe in profile.prosody_emotion:
                if pe["start"] <= sec < pe["end"]:
                    entry["prosody_emotion"] = pe["emotion"]
                    break
            for b in profile.beats:
                if abs(b - sec) < 0.5:
                    entry["beat"] = True
                    break
            for o in profile.onsets:
                if abs(o - sec) < 0.5:
                    entry["onset"] = True
                    break
            per_second.append(entry)
        profile.per_second = per_second
    finally:
        try:
            os.remove(audio_wav)
        except OSError:
            pass

    profile.components_used = components
    return profile
