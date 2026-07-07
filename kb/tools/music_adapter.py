#!/usr/bin/env python3
"""
Music understanding + internet download for AI video editing agents.

Three public functions (mirrors ffmpeg_adapter.py pattern):
  music_describe  — analyze any audio file: BPM, key, mood, structure, genre
  music_search    — search royalty-free libraries (Pixabay, Incompetech, MusOpen)
  music_download  — download a track with license sidecar

Usage:
    from kb.tools.music_adapter import music
    profile = music.describe("track.mp3")
    results = music.search("sad piano")
    info = music.download(results[0])
"""

from __future__ import annotations
import hashlib, json, os, pathlib, re, shutil, subprocess, time, typing as t

import numpy as np
import requests

_FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
_FFPROBE = shutil.which("ffprobe") or "ffprobe"
UA = "Mozilla/5.0 (agentic-ai-video-kb/1.0)"
_CACHE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "kb" / "raw" / "assets" / "music" / ".search_cache"
_MUSIC_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "kb" / "raw" / "assets" / "music"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def _probe_json(path: str) -> dict:
    res = _run([_FFPROBE, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", path])
    return json.loads(res.stdout)


# ═══════════════════════════════════════════════════════════
#  Capability 1 — Music Understanding
# ═══════════════════════════════════════════════════════════

def music_describe(
    audio_path: t.Optional[str] = None,
    *,
    detailed: bool = True,
    include_waveform: bool = False,
    waveform_path: t.Optional[str] = None,
) -> dict:
    """
    Analyze any audio file and return its full 'taste profile'.
    Runs entirely locally using librosa + ffmpeg.  No API calls, no network.
    Returns empty profile if audio_path is None (graceful for recipe use).
    """
    if audio_path is None or not os.path.exists(audio_path):
        return {"error": "no audio path provided", "bpm": None, "duration": 0, "beats": [], "downbeats": []}

    import librosa
    from scipy import signal as sg

    y, sr = librosa.load(audio_path, sr=None, mono=True)
    duration = float(len(y)) / sr

    result: dict = {
        "duration": duration,
        "sample_rate": sr,
        "channels": 1,  # librosa loaded as mono
        "codec": "unknown",
    }
    # Enrich with ffprobe metadata if available (non-fatal if missing)
    try:
        probe = _probe_json(audio_path)
        a_stream = next((s for s in probe.get("streams", [])
                         if s.get("codec_type") == "audio"), {})
        if a_stream:
            result["channels"] = a_stream.get("channels", 1)
            result["codec"] = a_stream.get("codec_name", "unknown")
    except Exception:
        pass

    # ── Tempo & rhythm ──
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, units="time")
    bpm_val = float(np.round(tempo, 1)) if isinstance(tempo, (int, float, np.floating)) else float(tempo[0])
    beat_times = beats.tolist() if hasattr(beats, "tolist") else list(beats)

    bpm_conf = _bpm_confidence(onset_env, sr)
    time_sig = _detect_time_signature(beat_times, duration)
    rhythm_reg = _rhythm_regularity(beat_times)

    downbeats = beat_times[::4] if time_sig == "4/4" and len(beat_times) >= 4 else beat_times[::3] if time_sig == "3/4" and len(beat_times) >= 3 else []
    bars = len(downbeats)

    result.update({
        "bpm": bpm_val,
        "bpm_confidence": round(bpm_conf, 2),
        "time_signature": time_sig,
        "beats": beat_times,
        "downbeats": downbeats,
        "bars": bars,
        "rhythm_regularity": round(rhythm_reg, 2),
    })

    # ── Harmony: key ──
    key_str, key_conf = _detect_key(y, sr)
    result.update({
        "key": key_str,
        "key_confidence": round(key_conf, 2),
        "camelot_code": _key_to_camelot(key_str) if key_str != "unknown" else "unknown",
    })

    # ── Energy curve ──
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    target_frames = max(int(duration * 10), 1)
    if len(rms) > target_frames:
        rms_resampled = sg.resample(rms, target_frames)
    else:
        rms_resampled = rms
    energy_curve = [float(v) for v in rms_resampled]

    # ── Mood (valence x arousal) ──
    valence = _compute_valence(y, sr, bpm_val, key_str)
    arousal = _compute_arousal(y, sr, bpm_val)
    moods = _valence_arousal_to_moods(valence, arousal)
    result.update({
        "mood": moods,
        "valence": round(valence, 3),
        "arousal": round(arousal, 3),
        "energy_curve": energy_curve,
    })

    # ── Structure ──
    structure = _detect_structure(y, sr, duration)
    result["structure"] = structure

    # ── Instrumentation (heuristic) ──
    instr, instr_conf = _detect_instruments(y, sr)
    result.update({
        "instruments_detected": instr,
        "instrument_confidence": round(instr_conf, 2),
    })

    # ── Genre ──
    genre_primary, genre_tags = _classify_genre(result)
    result.update({
        "genre_primary": genre_primary,
        "genre_tags": genre_tags,
    })

    # ── Production metrics via ffmpeg loudnorm ──
    loudness = _measure_loudness(audio_path)
    result.update(loudness)

    # ── Vocals ──
    has_vocals, vocal_conf = _detect_vocals(y, sr)
    result.update({
        "has_vocals": has_vocals,
        "vocal_confidence": round(vocal_conf, 2),
    })

    # ── Suitability hints ──
    ctypes, mbriefs, role, lufs_offset = _compute_suitability(result)
    result.update({
        "fits_content_types": ctypes,
        "fits_mood_briefs": mbriefs,
        "recommended_role": role,
        "recommended_lufs_offset": lufs_offset,
    })

    return result


# ── private analysis helpers ──


def _bpm_confidence(onset_env: np.ndarray, sr: float) -> float:
    from librosa import autocorrelate
    ac = autocorrelate(onset_env)
    ac_norm = ac / ac[0] if ac[0] != 0 else ac
    hop = 512
    frame_rate = sr / hop
    min_lag = max(int(frame_rate / 300 * 60), 1)
    max_lag = int(frame_rate / 30 * 60)
    if min_lag >= max_lag or min_lag < 1:
        return 0.0
    search = ac_norm[min_lag : max_lag + 1]
    return float(np.max(search)) if len(search) > 0 else 0.0


def _detect_time_signature(beats: list[float], duration: float) -> str:
    if len(beats) < 4:
        return "unknown"
    ibi = np.diff(beats)
    mean_ibi = float(np.mean(ibi))
    if mean_ibi == 0:
        return "unknown"
    # Count beats per 4-bar window; cluster around 4/4 or 3/4
    bar_4 = 4 * mean_ibi
    bar_3 = 3 * mean_ibi
    # Check how well beat positions align with 4/4 downbeats
    downbeats_4 = np.arange(0, duration, bar_4)
    downbeats_3 = np.arange(0, duration, bar_3)
    beat_arr = np.array(beats)
    align_4 = sum(1 for db in downbeats_4 if np.any(np.abs(beat_arr - db) < mean_ibi * 0.3))
    align_3 = sum(1 for db in downbeats_3 if np.any(np.abs(beat_arr - db) < mean_ibi * 0.3))
    return "3/4" if align_3 > align_4 else "4/4"


def _rhythm_regularity(beats: list[float]) -> float:
    if len(beats) < 4:
        return 0.0
    ibi = np.diff(beats)
    mean_ibi = float(np.mean(ibi))
    if mean_ibi == 0:
        return 0.0
    return 1.0 - min(float(np.std(ibi)) / mean_ibi, 1.0)


def _detect_key(y: np.ndarray, sr: float) -> tuple[str, float]:
    import librosa
    try:
        key_str, key_conf = librosa.key.key(y=y, sr=sr)
        return str(key_str), float(key_conf)
    except Exception:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        # Krumhansl-Schmuckler profiles
        major_prof = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_prof = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        keys_major = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        keys_minor = [f"{k}m" for k in keys_major]
        best_corr = -1
        best_key = "C major"
        for shift in range(12):
            rolled = np.roll(chroma_mean, shift)
            corr_maj = float(np.corrcoef(rolled, major_prof)[0, 1])
            corr_min = float(np.corrcoef(rolled, minor_prof)[0, 1])
            if corr_maj > best_corr:
                best_corr = corr_maj
                best_key = f"{keys_major[shift]} major"
            if corr_min > best_corr:
                best_corr = corr_min
                best_key = f"{keys_minor[shift]}"
        return best_key, round(max(best_corr, 0), 2)


def _key_to_camelot(key_str: str) -> str:
    """Convert key string to Camelot wheel code (harmonic mixing)."""
    key_str = key_str.lower().replace(" ", "")
    if "major" in key_str:
        root = key_str.replace("major", "")
        roots_major = {
            "c": "8B", "c#": "5B", "d": "10B", "d#": "3B",
            "e": "12B", "f": "7B", "f#": "2B", "g": "9B",
            "g#": "4B", "a": "11B", "a#": "6B", "b": "1B",
        }
        return roots_major.get(root, "unknown")
    elif "minor" in key_str or key_str.endswith("m"):
        root = key_str.replace("minor", "").replace("m", "")
        roots_minor = {
            "c": "5A", "c#": "12A", "d": "7A", "d#": "2A",
            "e": "9A", "f": "4A", "f#": "11A", "g": "6A",
            "g#": "1A", "a": "8A", "a#": "3A", "b": "10A",
        }
        return roots_minor.get(root, "unknown")
    return "unknown"


def _compute_valence(y: np.ndarray, sr: float, bpm: float, key_str: str) -> float:
    """0 = sad, 1 = happy.  Based on key mode, tempo, spectral brightness."""
    import librosa
    v = 0.5  # neutral start
    # Key mode -> valence
    if "major" in key_str:
        v += 0.25
    elif "minor" in key_str:
        v -= 0.15
    # Faster tempo -> higher valence
    v += (min(bpm, 160) / 160) * 0.15
    # Spectral brightness (high centroid -> brighter -> happier)
    cent = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    max_cent = sr / 4
    v += (min(cent, max_cent) / max_cent) * 0.1
    return max(0.0, min(1.0, v))


def _compute_arousal(y: np.ndarray, sr: float, bpm: float) -> float:
    """0 = calm, 1 = energetic.  Based on RMS energy + tempo."""
    rms = float(np.sqrt(np.mean(y ** 2)))
    # Normalize RMS (typical peak ~0.3 for mastered audio)
    rms_norm = min(rms * 10, 1.0)
    # Tempo factor
    tempo_factor = min(bpm / 160, 1.0)
    return max(0.0, min(1.0, rms_norm * 0.6 + tempo_factor * 0.4))


def _valence_arousal_to_moods(valence: float, arousal: float) -> list[str]:
    """
    Map (valence, arousal) onto 12 mood labels in 2D space.
    Quadrants: high-V/high-A = energetic/uplifting, high-V/low-A = calm/peaceful,
               low-V/high-A = tense/suspenseful, low-V/low-A = sad/melancholic.
    """
    moods = []
    # Low valence region
    if valence < 0.4:
        if arousal < 0.4:
            moods.extend(["sad", "melancholic"])
        elif arousal < 0.7:
            moods.extend(["melancholic", "calm"])
        else:
            moods.extend(["tense", "suspenseful"])
            if arousal > 0.85:
                moods.append("angry")
    # Mid valence
    elif valence < 0.6:
        if arousal < 0.3:
            moods.extend(["calm", "peaceful"])
        elif arousal < 0.7:
            moods.append("reflective")
        else:
            moods.extend(["epic", "uplifting"])
    # High valence
    else:
        if arousal < 0.4:
            moods.extend(["calm", "peaceful"])
        elif arousal < 0.7:
            moods.extend(["uplifting", "joyful"])
        else:
            moods.extend(["energetic", "joyful"])
            if arousal > 0.9:
                moods.append("playful")
    if not moods:
        moods = ["neutral"]
    return moods[:3]


def _detect_structure(y: np.ndarray, sr: float, duration: float) -> list[dict]:
    """
    Segment track using MFCC self-similarity + agglomerative clustering.
    Returns sections with label, start, end, bars.
    """
    import librosa
    if duration < 2:
        return [{"label": "full", "start": 0.0, "end": duration, "bars": 1}]

    hop_length = 512
    mfcc = np.zeros((13, max(1, int(duration * sr / hop_length))))
    try:
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
        ss_matrix = librosa.segment.recurrence_matrix(mfcc, mode="affinity", sparse=False)
        segs = librosa.segment.agglomerative(ss_matrix, max(2, min(8, int(duration / 15))))
    except Exception:
        segs = [0, mfcc.shape[1] - 1]

    # Convert frame boundaries to times
    frame_sec = hop_length / sr
    boundaries = [0.0]
    for s in segs[1:]:
        t = float(s) * frame_sec
        if t < duration - 0.5:
            boundaries.append(t)
    boundaries.append(duration)
    boundaries = sorted(set(boundaries))

    # Label sections by energy and position
    try:
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    except Exception:
        rms = np.zeros(int(duration * sr / hop_length) + 1)
    sections = []
    for i in range(len(boundaries) - 1):
        st, et = float(boundaries[i]), float(boundaries[i + 1])
        mid = min(int((st + et) / 2 / frame_sec), len(rms) - 1) if len(rms) > 0 else 0
        mid = max(mid, 0)
        lo = max(mid - 5, 0)
        hi = min(mid + 5, len(rms))
        energy = float(rms[lo:hi].mean()) if hi > lo else 0.0
        label = _label_section(i, len(boundaries) - 1, energy, duration, st, et)
        bars_est = max(1, int((et - st) / (duration / (len(boundaries) * 2))))
        sections.append({"label": label, "start": round(st, 2), "end": round(et, 2), "bars": bars_est})

    return sections


def _label_section(idx: int, total: int, energy: float, duration: float,
                   st: float, et: float) -> str:
    if idx == 0:
        return "intro"
    if idx == total - 1:
        return "outro"
    # Check if it's a building section (low energy after intro, before peak)
    if energy < 0.03 and idx < total / 2:
        return "verse"
    if energy > 0.08:
        return "chorus"
    # Mid-section with transition feel
    if idx <= total // 2:
        # After first verse before second chorus
        prev_sections = idx
        return "verse" if prev_sections % 2 == 1 else "bridge"
    return "bridge"


def _detect_instruments(y: np.ndarray, sr: float) -> tuple[list[str], float]:
    """
    Heuristic instrument detection from spectral features.
    Returns (instruments_list, confidence).
    """
    import librosa
    cent = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))
    onset_strength = librosa.onset.onset_strength(y=y, sr=sr)
    onset_rate = float(np.sum(onset_strength > np.mean(onset_strength) * 1.5)) / (len(y) / sr) if len(y) > 0 else 0

    instr: list[str] = []
    conf = 0.5

    # Piano-like: moderate centroid, moderate rolloff, percussive onsets
    if 500 < cent < 2000 and rolloff < 4000:
        instr.append("piano")
        conf += 0.1
    # Strings/bowed: lower centroid, smooth
    if cent < 1000 and rolloff < 2500 and onset_rate < 3:
        instr.append("strings")
        conf += 0.1
    # Bright/brass: high centroid, high rolloff
    if cent > 2000 and rolloff > 5000:
        instr.append("brass")
        conf += 0.1
    # Percussive: high onset rate
    if onset_rate > 5:
        instr.append("percussion")
        conf += 0.1
    # Synth: very high centroid, extreme rolloff
    if cent > 3000 and rolloff > 7000:
        instr.append("synth")
        conf += 0.1
    # Guitar: mid centroid, moderate onset rate
    if 1000 < cent < 3000 and 2 < onset_rate < 6 and "piano" not in instr:
        instr.append("guitar")
        conf += 0.1
    # Bass: very low centroid
    if cent < 300:
        instr.append("bass")
        conf += 0.05

    if not instr:
        instr = ["unknown"]
        conf = 0.0

    return instr, min(conf, 1.0)


def _classify_genre(profile: dict) -> tuple[str, list[str]]:
    """
    Rule-based genre classification from analysis features.
    Returns (primary_genre, tag_list).
    """
    bpm = profile.get("bpm", 120)
    moods = profile.get("mood", [])
    instr = profile.get("instruments_detected", [])
    has_vocals = profile.get("has_vocals", False)
    key_str = profile.get("key", "")
    arousal = profile.get("arousal", 0.5)

    tags: list[str] = [m for m in moods]
    tags.extend(i.lower() for i in instr)

    genre = "Cinematic"

    if has_vocals:
        if bpm > 110:
            genre = "Pop"
            tags.extend(["pop", "upbeat"])
        elif bpm > 80:
            genre = "Indie"
            tags.extend(["indie", "alternative"])
        else:
            genre = "Folk"
            tags.extend(["folk", "acoustic"])
    elif "piano" in instr:
        if "sad" in moods or "melancholic" in moods:
            genre = "Cinematic"
            tags.extend(["piano", "film-score", "melancholic"])
        elif "calm" in moods:
            genre = "Ambient"
            tags.extend(["ambient", "piano", "atmospheric"])
        else:
            genre = "Neoclassical"
            tags.extend(["neoclassical", "piano", "modern-classical"])
    elif "synth" in instr:
        if arousal > 0.7:
            genre = "Electronic"
            tags.extend(["electronic", "synth"])
        else:
            genre = "Ambient"
            tags.extend(["ambient", "synth", "chill"])
    elif "strings" in instr:
        if "epic" in moods or arousal > 0.7:
            genre = "Orchestral"
            tags.extend(["orchestral", "epic", "cinematic"])
        else:
            genre = "Classical"
            tags.extend(["classical", "strings"])
    elif "percussion" in instr and arousal > 0.7:
        genre = "Cinematic"
        tags.extend(["cinematic", "percussive", "action"])

    if bpm < 80:
        tags.append("slow")
    elif bpm < 110:
        tags.append("medium")
    else:
        tags.append("fast")

    if "minor" in key_str:
        tags.append("dark")
    elif "major" in key_str:
        tags.append("bright")

    return genre, sorted(set(tags))


def _measure_loudness(audio_path: str) -> dict:
    """Single-pass loudnorm measurement for production metrics.
    Returns zeros if ffmpeg is not available (non-fatal)."""
    if not shutil.which(_FFMPEG):
        return {"loudness_lufs": 0.0, "dynamic_range_lra": 0.0, "true_peak_db": 0.0}
    try:
        res = _run([_FFMPEG, "-i", audio_path,
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                    "-f", "null", "-"])
        match = re.search(r"\{[^{}]*\}", res.stderr, re.DOTALL)
        if not match:
            return {"loudness_lufs": 0.0, "dynamic_range_lra": 0.0, "true_peak_db": 0.0}
        d = json.loads(match.group())
        return {
            "loudness_lufs": round(float(d.get("input_i", 0)), 1),
            "dynamic_range_lra": round(float(d.get("input_lra", 0)), 1),
            "true_peak_db": round(float(d.get("input_tp", 0)), 1),
        }
    except Exception:
        return {"loudness_lufs": 0.0, "dynamic_range_lra": 0.0, "true_peak_db": 0.0}


def _detect_vocals(y: np.ndarray, sr: float) -> tuple[bool, float]:
    """
    Detect presence of vocals using HPSS + spectral features.
    Returns (has_vocals, confidence).
    """
    import librosa
    hop_length = 512
    # Harmonic-percussive separation
    try:
        D = librosa.stft(y)
        D_harm = librosa.decompose.hpss(D, margin=5.0)[0]
    except Exception:
        return False, 0.0

    # Harmonic component = more regular (vocals have vibrato, not purely harmonic)
    harm_energy = float(np.sum(np.abs(D_harm)))
    total_energy = float(np.sum(np.abs(D)))
    if total_energy == 0:
        return False, 0.0
    harm_ratio = harm_energy / total_energy

    # Spectral flux in mid frequencies (300-3000 Hz = vocal range)
    spec = np.abs(D)
    freqs = librosa.fft_frequencies(sr=sr)
    mask = (freqs >= 300) & (freqs <= 3000)
    if np.any(mask):
        mid_spec = spec[mask, :]
        flux = float(np.mean(np.abs(np.diff(mid_spec, axis=1))))
    else:
        flux = 0.0

    # Vocals tend to have moderate harm_ratio (0.4-0.7) and high mid-frequency flux
    if 0.35 < harm_ratio < 0.75 and flux > 0.05:
        return True, min(flux * 10, 0.95)
    return False, 0.3


def _compute_suitability(profile: dict) -> tuple[list[str], list[str], str, int]:
    """Rule-based mapping from profile to content-type fit."""
    bpm = profile.get("bpm", 120)
    moods = profile.get("mood", [])
    has_vocals = profile.get("has_vocals", False)
    arousal = profile.get("arousal", 0.5)
    instr = profile.get("instruments_detected", [])

    ctypes: list[str] = []
    mbriefs: list[str] = moods[:]

    if not has_vocals:
        if bpm < 80 and any(m in ["sad", "melancholic", "calm"] for m in moods):
            ctypes.extend(["documentary", "interview", "cinematic", "talking-head"])
            mbriefs.extend(["sad", "melancholic", "reflective"])
        elif arousal < 0.4:
            ctypes.extend(["ambient", "background", "podcast"])
            mbriefs.append("peaceful")
        elif arousal > 0.7 or bpm > 120:
            ctypes.extend(["vlog", "social-media", "montage", "commercial"])
            mbriefs.extend(["energetic", "upbeat"])
        else:
            ctypes.extend(["corporate", "presentation", "explainer"])
    else:
        ctypes.extend(["music-video", "vocal-performance"])

    # Recommended role
    if has_vocals and arousal > 0.6:
        role = "feature"
    elif not has_vocals and arousal < 0.4:
        role = "bed"
    elif not has_vocals:
        role = "underscore"
    else:
        role = "bed"
    lufs_offset = -6 if role == "feature" else -3  # EBU R128 music-to-voice

    return sorted(set(ctypes)), sorted(set(mbriefs)), role, lufs_offset


# ═══════════════════════════════════════════════════════════
#  Capability 2 — Internet Download
# ═══════════════════════════════════════════════════════════

def music_search(
    query: str,
    *,
    bpm_range: t.Optional[tuple[int, int]] = None,
    key: t.Optional[str] = None,
    duration_min: float = 30.0,
    duration_max: t.Optional[float] = None,
    instrumental_only: t.Optional[bool] = None,
    license_filter: t.Optional[list[str]] = None,
    sources: t.Optional[list[str]] = None,
    top_k: int = 10,
    timeout_per_source: float = 8.0,
) -> list[dict]:
    """
    Search royalty-free music libraries in parallel.  Returns normalized results.

    `query` is natural language: "sad piano", "90s funk", "uplifting corporate".
    Default sources: Pixabay (primary), Incompetech, MusOpen (classical).
    """
    if sources is None:
        sources = ["pixabay", "incompetech", "musopen"]
    if license_filter is None:
        license_filter = ["Pixabay", "CC-BY 4.0", "CC0", "Public Domain", "CC-BY"]

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache
    cache_key = hashlib.sha256(
        json.dumps({"q": query, "src": sources, "k": top_k}, sort_keys=True).encode()
    ).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < 86400:  # 24h cache
            with open(cache_path) as f:
                return json.load(f)

    all_results: list[dict] = []

    for src in sources:
        try:
            if src == "pixabay":
                results = _search_pixabay(query, top_k, timeout_per_source)
            elif src == "incompetech":
                results = _search_incompetech(query, top_k, timeout_per_source)
            elif src == "musopen":
                results = _search_musopen(query, top_k, timeout_per_source)
            else:
                continue
            all_results.extend(results)
        except Exception as e:
            all_results.append({
                "id": f"{src}_error",
                "source": src,
                "title": f"[{src} error: {e}]",
                "error": str(e),
            })

    # Score and rank
    for r in all_results:
        if "score" not in r:
            r["score"] = _score_track(query, r)

    all_results.sort(key=lambda r: r.get("score", 0), reverse=True)

    # Post-filter
    filtered = _filter_results(
        all_results, bpm_range, key, duration_min, duration_max,
        instrumental_only, license_filter
    )

    # Cache
    with open(cache_path, "w") as f:
        json.dump(filtered, f, indent=2)

    return filtered[:top_k]


def music_download(
    track: dict,
    *,
    output_dir: str = "",
    filename: t.Optional[str] = None,
    prefer_format: str = "mp3",
    skip_if_exists: bool = True,
) -> dict:
    """
    Download a track from the internet.  Writes audio file + .license.json sidecar.
    """
    out_dir = pathlib.Path(output_dir) if output_dir else _MUSIC_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    download_url = track.get("download_url") or track.get("preview_url")
    if not download_url:
        raise ValueError(f"no download URL in track: {track.get('id')}")

    if not filename:
        ext = download_url.rsplit(".", 1)[-1].split("?")[0]
        if ext not in ("mp3", "wav", "ogg", "flac", "m4a", "aac"):
            ext = prefer_format
        filename = f"{track['source']}_{track['id'].split('_')[-1]}.{ext}"

    out_path = out_dir / filename
    lic_path = out_dir / f"{pathlib.Path(filename).stem}.license.json"

    if skip_if_exists and out_path.exists():
        result = {
            "path": str(out_path.resolve()),
            "license_path": str(lic_path.resolve()),
            "title": track.get("title", ""),
            "artist": track.get("artist", ""),
            "source": track.get("source", ""),
            "license": track.get("license", ""),
            "attribution_required": track.get("attribution_required", False),
            "commercial_use": track.get("commercial_use", True),
            "attribution_text": "",
            "size_bytes": out_path.stat().st_size,
            "duration": track.get("duration", 0),
            "cached": True,
        }
        if track.get("attribution_required"):
            result["attribution_text"] = (
                f"Track: {track.get('title', '')} by {track.get('artist', '')}. "
                f"License: {track.get('license', '')}. {download_url}"
            )
        return result

    r = requests.get(download_url, headers={"User-Agent": UA}, timeout=60, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    size = out_path.stat().st_size

    # Probe for actual duration
    try:
        probe = _probe_json(str(out_path))
        duration = float(probe.get("format", {}).get("duration", track.get("duration", 0)))
    except Exception:
        duration = track.get("duration", 0)

    license_data = write_license_sidecar(
        track, lic_path, download_url, size, prefix="Track",
    )

    return {
        "path": str(out_path.resolve()),
        "license_path": str(lic_path.resolve()),
        "title": track.get("title", ""),
        "artist": track.get("artist", ""),
        "source": track.get("source", ""),
        "license": track.get("license", ""),
        "attribution_required": track.get("attribution_required", False),
        "commercial_use": track.get("commercial_use", True),
        "attribution_text": license_data.get("attribution_text", ""),
        "size_bytes": size,
        "duration": duration,
        "cached": False,
    }


# ── per-source searchers ──


def _search_pixabay(query: str, top_k: int = 10, timeout: float = 8.0) -> list[dict]:
    """Search Pixabay Music catalog.  Anonymous (no API key needed for low volume)."""
    from bs4 import BeautifulSoup
    url = "https://pixabay.com/music/search/"
    params = {"q": query, "order": "popular"}
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        return []

    data = json.loads(script.string)
    tracks = data.get("props", {}).get("pageProps", {}).get("tracks", {}).get("hits", [])
    return [
        {
            "id": f"pixabay_{t['id']}",
            "source": "pixabay",
            "title": t.get("title", ""),
            "artist": t.get("user", ""),
            "duration": t.get("duration", 0),
            "preview_url": t.get("audioSrc", ""),
            "download_url": t.get("audioSrc", ""),
            "thumbnail_url": t.get("imageSrc", ""),
            "tags": [s.strip() for s in t.get("tags", "").split(",") if s.strip()],
            "genre": t.get("genre", ""),
            "license": "Pixabay",
            "attribution_required": False,
            "commercial_use": True,
            "score": 0.0,
        }
        for t in tracks[:top_k]
    ]


def _search_incompetech(query: str, top_k: int = 10, timeout: float = 8.0) -> list[dict]:
    """Search Incompetech (Kevin MacLeod) catalog.  CC-BY 4.0."""
    from bs4 import BeautifulSoup
    url = "https://incompetech.com/music/royalty-free/index.html"
    params = {"genre": "", "feel": "", "initial": "", "keywords": query}
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    results: list[dict] = []
    for row in soup.select("tr.songRow"):
        td = row.find_all("td")
        if len(td) < 3:
            continue
        title = td[0].get_text(strip=True) if td[0] else ""
        if not title:
            continue
        mp3_link = row.select_one("a[href$='.mp3']")
        if not mp3_link:
            continue
        mp3_url = mp3_link["href"]
        if not mp3_url:
            continue
        if mp3_url.startswith("/"):
            mp3_url = "https://incompetech.com" + mp3_url
        results.append({
            "id": f"incompetech_{title.lower().replace(' ', '_')[:40]}",
            "source": "incompetech",
            "title": title,
            "artist": "Kevin MacLeod",
            "duration": 0,
            "preview_url": mp3_url,
            "download_url": mp3_url,
            "thumbnail_url": "",
            "tags": [],
            "genre": "Production",
            "license": "CC-BY 4.0",
            "attribution_required": True,
            "commercial_use": True,
            "score": 0.0,
        })
        if len(results) >= top_k:
            break
    return results


def _search_musopen(query: str, top_k: int = 10, timeout: float = 8.0,
                    api_key: str = "") -> list[dict]:
    """Search MusOpen classical catalog.  Free API, public domain / CC0."""
    url = "https://api.musopen.org/v1/performances"
    headers = {"X-User-Token": api_key} if api_key else {}
    params = {"search": query, "count": top_k}
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    if r.status_code != 200:
        return []
    data = r.json()
    results = data.get("results", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    return [
        {
            "id": f"musopen_{p.get('id', i)}",
            "source": "musopen",
            "title": p.get("work", {}).get("title", ""),
            "artist": p.get("performer", {}).get("name", ""),
            "duration": p.get("duration", 0),
            "preview_url": p.get("audio_url", ""),
            "download_url": p.get("audio_url", ""),
            "thumbnail_url": "",
            "tags": [],
            "genre": "Classical",
            "license": p.get("license", "Public Domain"),
            "attribution_required": False,
            "commercial_use": True,
            "score": 0.0,
        }
        for i, p in enumerate(results[:top_k])
    ]


# ── scoring & filtering ──


def _score_track(query: str, track: dict) -> float:
    """Jaccard-ish relevance score: query terms matched in title or tags."""
    query_terms = set(query.lower().split())
    if not query_terms:
        return 0.0
    title_terms = set(track.get("title", "").lower().split())
    tag_terms = set(t.lower() for t in track.get("tags", []))
    matched = query_terms & (title_terms | tag_terms)
    base = len(matched) / len(query_terms)
    # Boost Pixabay (largest, most reliable catalog)
    if track.get("source") == "pixabay" and base > 0:
        base *= 1.05
    return min(base, 1.0)


def _filter_results(
    results: list[dict],
    bpm_range: t.Optional[tuple[int, int]] = None,
    key: t.Optional[str] = None,
    duration_min: float = 30.0,
    duration_max: t.Optional[float] = None,
    instrumental_only: t.Optional[bool] = None,
    license_filter: t.Optional[list[str]] = None,
) -> list[dict]:
    """Filter results by constraints that can be checked client-side."""
    filtered: list[dict] = []
    for r in results:
        if r.get("duration", 0) > 0 and r["duration"] < duration_min:
            continue
        if duration_max and r.get("duration", 0) > duration_max:
            continue
        if license_filter and r.get("license") not in license_filter:
            continue
        filtered.append(r)
    return filtered


def write_license_sidecar(
    track: dict, lic_path: pathlib.Path, download_url: str, size_bytes: int,
    *,
    prefix: str = "Track",
) -> dict:
    """Write .license.json sidecar for any downloaded asset.

    Shared across music_adapter, content_adapter, and any other downloader.
    Returns the license dict for inspection.
    """
    attr_text = ""
    if track.get("attribution_required"):
        attr_text = (
            f"{prefix}: {track.get('title', '')} by {track.get('artist', '')}. "
            f"License: {track.get('license', '')}. {download_url}"
        )
    license_data = {
        "title": track.get("title", ""),
        "artist": track.get("artist", ""),
        "source": track.get("source", ""),
        "download_url": download_url,
        "license": track.get("license", ""),
        "attribution_required": track.get("attribution_required", False),
        "commercial_use": track.get("commercial_use", True),
        "attribution_text": attr_text,
        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "size_bytes": size_bytes,
    }
    with open(lic_path, "w") as f:
        json.dump(license_data, f, indent=2)
    return license_data


# ── Phase 4 addition: BPM/mood-aware ranking ──

def rank_by_fit(
    candidates: list[dict],
    *,
    target_bpm: float = None,
    target_mood: str = None,
    content_type: str = None,
) -> list[dict]:
    """
    Re-rank music search candidates by fit to the edit's target pacing and mood.

    For each candidate, downloads a short preview (first 30s), runs
    ``music_describe`` to extract BPM/key/mood, then scores against the target.

    Args:
        candidates: list of track dicts from music_search()
        target_bpm: desired BPM
        target_mood: "happy" | "sad" | "energetic" | "calm" | "epic"
        content_type: used to infer default target_bpm/mood if not specified

    Returns: candidates sorted by fit_score descending, each augmented with
        bpm, key, mood, fit_score, fit_reasoning.
    """
    CT_DEFAULTS = {
        "vlog":          {"bpm": 100, "mood": "happy"},
        "podcast":       {"bpm": None, "mood": "calm"},
        "social-short":  {"bpm": 140, "mood": "energetic"},
        "cinematic":     {"bpm": 80,  "mood": "epic"},
        "tutorial":      {"bpm": 110, "mood": "calm"},
        "sports":        {"bpm": 140, "mood": "energetic"},
        "short_form":    {"bpm": 140, "mood": "energetic"},
    }
    if content_type and content_type in CT_DEFAULTS:
        d = CT_DEFAULTS[content_type]
        if target_bpm is None:
            target_bpm = d["bpm"]
        if target_mood is None:
            target_mood = d["mood"]

    if target_bpm is None and target_mood is None:
        return candidates

    import tempfile
    scored: list[dict] = []
    for cand in candidates:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            _download_preview(cand, tmp_path, max_duration=30)
            desc = music_describe(tmp_path)
        except Exception as e:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            scored.append({**cand, "fit_score": 0.0, "fit_reasoning": f"describe failed: {e}"})
            continue

        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        bpm = desc.get("bpm")
        key = desc.get("key", "unknown")
        mood_list = desc.get("mood", [])

        score = 0.0
        reasoning_parts: list[str] = []

        if target_bpm and bpm:
            delta = abs(bpm - target_bpm)
            if delta <= 5:
                bpm_score = 1.0
            elif delta <= 20:
                bpm_score = 0.5
            elif delta <= 40:
                bpm_score = 0.2
            else:
                bpm_score = 0.0
            score += bpm_score
            reasoning_parts.append(f"BPM {bpm} vs target {target_bpm} (\u0394{delta:.0f}, score {bpm_score})")

        if target_mood:
            mood_match = target_mood in mood_list
            mood_score = 1.0 if mood_match else 0.3
            score += mood_score
            reasoning_parts.append(f"mood {mood_list} vs target '{target_mood}' (score {mood_score})")

        max_score = (1.0 if target_bpm else 0.0) + (1.0 if target_mood else 0.0)
        fit_score = score / max_score if max_score > 0 else 0.0

        scored.append({
            **cand,
            "bpm": bpm,
            "key": key,
            "mood": mood_list,
            "fit_score": round(fit_score, 3),
            "fit_reasoning": "; ".join(reasoning_parts),
        })

    scored.sort(key=lambda x: x.get("fit_score", 0), reverse=True)
    return scored


def _download_preview(track: dict, output_path: str, max_duration: int = 30) -> None:
    full_path = music_download(track, output_dir=os.path.dirname(output_path) or ".")
    fpath = full_path.get("path") if isinstance(full_path, dict) else str(full_path)
    if not fpath or not os.path.exists(fpath):
        raise RuntimeError(f"download failed for {track.get('id')}")
    subprocess.run(
        ["ffmpeg", "-y", "-i", fpath, "-t", str(max_duration), "-c", "copy", output_path],
        capture_output=True, check=True,
    )


# ── module alias (mirrors ffmpeg_adapter.py pattern) ──
import sys as _sys
music = _sys.modules[__name__]
