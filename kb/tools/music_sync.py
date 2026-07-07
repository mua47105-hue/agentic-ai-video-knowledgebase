"""
Music Synchronization Engine (Phase 8).

Three responsibilities:
  1. detect_structure(music_path) — label music sections via librosa SSF + novelty
  2. align_cuts_to_music(cut_points, music_structure, hero_moments) — snap cuts
     to section boundaries (hero) or downbeats (others), Δt ≤ 0.1s for beats
  3. apply_ducking(speech_segments, music_path) — sidechaincompress per Geary
     et al. JAES 2020 (14 LU midpoint, 150ms attack, 300ms release, 6:1 ratio)

Public surface:
  - build_music_sync_plan(source_profile, cut_points, relevance_map) -> dict
"""
from __future__ import annotations

import typing as t


def detect_structure(music_path: str) -> dict:
    """Detect music structure via librosa SSF + novelty. Returns dict (JSON-serializable)."""
    try:
        import librosa
        import numpy as np
    except ImportError:
        return {"sections": [], "tempo": 120.0, "beats": [], "downbeats": [], "duration": 0.0}

    try:
        y, sr = librosa.load(music_path, sr=22050, mono=True)
        duration = len(y) / sr
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        downbeat_times = list(beat_times[::4])

        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        n_segments = max(3, int(duration / 15))
        bound_frames = librosa.segment.agglomerative(chroma, k=n_segments)
        bound_times = librosa.frames_to_time(bound_frames, sr=sr)

        sections: list[dict] = []
        section_starts = [0.0] + list(bound_times) + [duration]
        for i in range(len(section_starts) - 1):
            start = float(section_starts[i])
            end = float(section_starts[i + 1])
            if end - start < 2.0:
                continue
            start_sample = int(start * sr)
            end_sample = int(end * sr)
            section_y = y[start_sample:end_sample]
            rms = float(np.sqrt(np.mean(section_y ** 2))) if len(section_y) > 0 else 0.0
            if i == 0:
                label = "intro"
            elif i == len(section_starts) - 2:
                label = "outro"
            else:
                label = "unknown"
            sections.append({
                "start": start, "end": end, "label": label,
                "confidence": 0.6, "energy": rms,
            })

        # Label middle sections: highest-energy = chorus
        if sections:
            middle = sections[1:-1] if len(sections) > 2 else sections
            if middle:
                max_energy = max(middle, key=lambda s: s["energy"])
                max_energy["label"] = "chorus"
                max_energy["confidence"] = 0.7
                for s in middle:
                    if s["label"] == "unknown":
                        if abs(s["energy"] - max_energy["energy"]) < 0.02:
                            s["label"] = "verse"
                        else:
                            s["label"] = "bridge"

        return {
            "sections": sections,
            "tempo": float(tempo),
            "beats": list(beat_times),
            "downbeats": downbeat_times,
            "duration": duration,
        }
    except Exception:
        return {"sections": [], "tempo": 120.0, "beats": [], "downbeats": [], "duration": 0.0}


def align_cuts_to_music(cut_points: list[dict], music_structure: dict,
                        hero_moments: list[dict],
                        section_tolerance: float = 1.0,
                        beat_tolerance: float = 0.1) -> list[dict]:
    """Snap cut points to music structure. Returns list of aligned-cut dicts."""
    sections = music_structure.get("sections", [])
    if not sections:
        return [{
            "original_ts": cp["timestamp"], "aligned_ts": cp["timestamp"],
            "alignment_type": "none", "delta": 0.0, "cut_point": cp,
        } for cp in cut_points]

    section_boundaries = [s["start"] for s in sections] + [music_structure.get("duration", 0)]
    hero_starts = {hm["start"] for hm in hero_moments}
    hero_ends = {hm["end"] for hm in hero_moments}
    downbeats = music_structure.get("downbeats", [])

    aligned: list[dict] = []
    for cp in cut_points:
        ts = cp["timestamp"]
        is_hero_boundary = ts in hero_starts or ts in hero_ends
        if is_hero_boundary:
            nearest = min(section_boundaries, key=lambda b: abs(b - ts))
            delta = nearest - ts
            if abs(delta) <= section_tolerance:
                aligned.append({
                    "original_ts": ts, "aligned_ts": nearest,
                    "alignment_type": "section", "delta": delta, "cut_point": cp,
                })
                continue
        if downbeats:
            nearest = min(downbeats, key=lambda b: abs(b - ts))
            delta = nearest - ts
            if abs(delta) <= beat_tolerance:
                aligned.append({
                    "original_ts": ts, "aligned_ts": nearest,
                    "alignment_type": "downbeat", "delta": delta, "cut_point": cp,
                })
                continue
        aligned.append({
            "original_ts": ts, "aligned_ts": ts,
            "alignment_type": "none", "delta": 0.0, "cut_point": cp,
        })
    return aligned


def apply_ducking(speech_segments: list[dict], music_path: str,
                  target_lufs_diff: float = 14.0) -> dict:
    """Generate sidechain compression plan for music under speech (Geary JAES 2020)."""
    segments = [{
        "start": seg["start"], "end": seg["end"],
        "gain_reduction_db": target_lufs_diff,
        "attack_ms": 150, "release_ms": 300,
    } for seg in speech_segments]
    return {
        "segments": segments,
        "filter_params": {
            "filter": "sidechaincompress",
            "params": {
                "threshold": -20.0, "ratio": 6.0,
                "attack": 0.150, "release": 0.300,
                "makeup": target_lufs_diff,
            },
            "sidechain_source": "speech_segments",
            "segments": segments,
        },
    }


def build_music_sync_plan(source_profile: dict, cut_points: list[dict],
                          relevance_map: dict) -> dict:
    """Build complete music sync plan: structure + aligned cuts + ducking."""
    music_path = source_profile.get("audio", {}).get("music_path")
    if not music_path:
        return {
            "structure": None,
            "aligned_cuts": [{
                "original_ts": cp["timestamp"], "aligned_ts": cp["timestamp"],
                "alignment_type": "none", "delta": 0.0, "cut_point": cp,
            } for cp in cut_points],
            "ducking": None,
            "reasoning": "no music track separated — skip music sync",
        }
    structure = detect_structure(music_path)
    hero_moments = relevance_map.get("hero_moments", [])
    aligned = align_cuts_to_music(cut_points, structure, hero_moments)
    speech_segments = source_profile.get("audio", {}).get("speech_segments", [])
    ducking = apply_ducking(speech_segments, music_path)
    n_aligned = sum(1 for a in aligned if a["alignment_type"] != "none")
    return {
        "structure": structure,
        "aligned_cuts": aligned,
        "ducking": ducking,
        "reasoning": f"music structure detected: {len(structure['sections'])} sections, "
                     f"{n_aligned} of {len(aligned)} cuts aligned",
    }
