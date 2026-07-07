#!/usr/bin/env python3
"""
Test music_describe on synthetic audio (generated with Python's wave module).
No ffmpeg needed. Tests all analysis code paths.

Usage:
    python3 scripts/test_music_describe.py
"""
import sys, os, pathlib, tempfile, json, struct, math, wave
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kb.tools.music_adapter import music
from _test_utils import check, run_main
import inspect

TMP = pathlib.Path(tempfile.mkdtemp(prefix="music_describe_test_"))
ERRORS: list[str] = []


def _write_wav(path: str, samples: np.ndarray, sr: int = 22050) -> str:
    samples = np.clip(samples, -1.0, 1.0)
    int16 = (samples * 32767).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(int16.tobytes())
    return path


def _gen_tone(path: str, freq: float = 440, duration: float = 3.0,
              sr: int = 22050, amplitude: float = 0.5) -> str:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    samples = amplitude * np.sin(2 * math.pi * freq * t)
    return _write_wav(path, samples, sr)


def _gen_silence(path: str, duration: float = 2.0, sr: int = 22050) -> str:
    samples = np.zeros(int(sr * duration))
    return _write_wav(path, samples, sr)


def _gen_multi_tone(path: str, sr: int = 22050) -> str:
    segments = []
    for freq in [220, 330, 440, 550]:
        t = np.linspace(0, 4.0, int(sr * 4.0), endpoint=False)
        seg = 0.4 * np.sin(2 * math.pi * freq * t)
        segments.append(seg)
    samples = np.concatenate(segments)
    return _write_wav(path, samples, sr)


def test_describe_basics():
    tone = _gen_tone(str(TMP / "tone.wav"), freq=440, duration=3.0)
    result = music.music_describe(tone)
    check("returns dict", isinstance(result, dict))
    check("has duration", result.get("duration", 0) > 0)
    check("has sample_rate", result.get("sample_rate", 0) > 0)
    check("has bpm", result.get("bpm", 0) > 0)
    check("has key", isinstance(result.get("key"), str))
    check("has mood list", isinstance(result.get("mood"), list) and len(result["mood"]) > 0)
    check("has valence", 0 <= result.get("valence", -1) <= 1)
    check("has arousal", 0 <= result.get("arousal", -1) <= 1)
    check("has structure list", isinstance(result.get("structure"), list))
    check("structure has items", len(result.get("structure", [])) > 0)
    check("structure has labels", all("label" in s for s in result.get("structure", [])))
    check("has energy_curve list", isinstance(result.get("energy_curve"), list))
    check("has genre_primary", isinstance(result.get("genre_primary"), str))
    check("has genre_tags list", isinstance(result.get("genre_tags"), list))
    check("has instruments_detected", isinstance(result.get("instruments_detected"), list))
    check("has loudness_lufs", isinstance(result.get("loudness_lufs"), (int, float)))
    check("has dynamic_range_lra", isinstance(result.get("dynamic_range_lra"), (int, float)))
    check("has true_peak_db", isinstance(result.get("true_peak_db"), (int, float)))
    check("has has_vocals", isinstance(result.get("has_vocals"), bool))
    check("has fits_content_types", isinstance(result.get("fits_content_types"), list))
    check("has fits_mood_briefs", isinstance(result.get("fits_mood_briefs"), list))
    check("has recommended_role", isinstance(result.get("recommended_role"), str))
    check("has recommended_lufs_offset", isinstance(result.get("recommended_lufs_offset"), int))
    print(f"  -> BPM: {result['bpm']}, Key: {result['key']}, Mood: {result['mood']}")
    print(f"  -> Genre: {result['genre_primary']}, Instruments: {result['instruments_detected']}")


def test_describe_silence():
    silent = _gen_silence(str(TMP / "silence.wav"), duration=2.0)
    result = music.music_describe(silent)
    check("silence: no crash", "key" in result)
    check("silence: has duration", result.get("duration", 0) > 0)


def test_describe_multi_tone():
    combined = _gen_multi_tone(str(TMP / "combined.wav"))
    result = music.music_describe(combined)
    check("multi-tone: duration ~16s", abs(result["duration"] - 16.0) < 0.5)
    check("multi-tone: structure has sections", len(result.get("structure", [])) >= 2)


def test_key_helpers():
    from kb.tools.music_adapter import _key_to_camelot, _compute_valence, _compute_arousal
    tests = [
        ("C major", "8B"), ("A minor", "8A"),
        ("F# major", "2B"), ("D# minor", "2A"),
    ]
    for key, expected in tests:
        result = _key_to_camelot(key)
        check(f"camelot {key} -> {expected}", result == expected, f"got {result}")


def test_scoring():
    from kb.tools.music_adapter import _score_track
    track = {"title": "Sad Piano Dreams", "tags": ["piano", "sad", "cinematic"]}
    s1 = _score_track("sad piano", track)
    check("scoring: matches sad piano", s1 > 0.5, f"got {s1}")
    s2 = _score_track("upbeat funk", track)
    check("scoring: no match for funk", s2 == 0.0, f"got {s2}")


def test_filter():
    from kb.tools.music_adapter import _filter_results
    tracks = [
        {"id": "a", "duration": 60, "license": "CC-BY 4.0"},
        {"id": "b", "duration": 20, "license": "CC-BY 4.0"},
        {"id": "c", "duration": 90, "license": "Pixabay"},
    ]
    filtered = _filter_results(tracks, duration_min=30)
    check("filter: removes short tracks", len(filtered) == 2, f"got {len(filtered)}")
    filtered2 = _filter_results(tracks, duration_min=30, license_filter=["Pixabay"])
    check("filter: Pixabay only", len(filtered2) == 1, f"got {len(filtered2)}")


def test_mood_mapping():
    from kb.tools.music_adapter import _valence_arousal_to_moods
    moods = _valence_arousal_to_moods(0.8, 0.9)
    check("mood: high V+A -> energetic/joyful", "joyful" in moods or "energetic" in moods)
    moods2 = _valence_arousal_to_moods(0.2, 0.2)
    check("mood: low V+A -> sad/melancholic", "sad" in moods2 or "melancholic" in moods2)
    moods3 = _valence_arousal_to_moods(0.8, 0.2)
    check("mood: high V+low A -> calm/peaceful", "calm" in moods3 or "peaceful" in moods3)


def test_suitability():
    from kb.tools.music_adapter import _compute_suitability
    profile = {"bpm": 70, "mood": ["sad", "melancholic"], "has_vocals": False,
               "arousal": 0.2, "instruments_detected": ["piano"]}
    ctypes, mbriefs, role, offset = _compute_suitability(profile)
    check("suitability: documentary in ctypes", "documentary" in ctypes)
    check("suitability: role = bed or underscore", role in ("bed", "underscore"))
    check("suitability: offset is negative", offset < 0)


def test_genre():
    from kb.tools.music_adapter import _classify_genre
    profile = {"bpm": 70, "mood": ["sad", "melancholic"], "instruments_detected": ["piano"],
               "has_vocals": False, "key": "B minor", "arousal": 0.2}
    genre, tags = _classify_genre(profile)
    check("genre: piano+sad -> Cinematic or Neoclassical", genre in ("Cinematic", "Neoclassical"))
    check("genre: has tags", len(tags) > 0)


def test_roundtrip_json():
    tone = _gen_tone(str(TMP / "roundtrip.wav"), freq=440, duration=2.0)
    result = music.music_describe(tone)
    json_str = json.dumps(result, indent=2)
    parsed = json.loads(json_str)
    check("roundtrip: JSON serializable", isinstance(parsed, dict))
    check("roundtrip: key preserved", parsed.get("key") == result.get("key"))
    check("roundtrip: bpm preserved", parsed.get("bpm") == result.get("bpm"))


def run_tests():
    print("=" * 60)
    print("music_describe — Unit & Integration Tests")
    print("=" * 60)
    test_describe_basics()
    test_describe_silence()
    test_describe_multi_tone()
    test_key_helpers()
    test_scoring()
    test_filter()
    test_mood_mapping()
    test_suitability()
    test_genre()
    test_roundtrip_json()
    print(f"\nTemp files: {TMP}")


if __name__ == "__main__":
    run_main(run_tests)
