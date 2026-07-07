"""
Slow-Mo Placement Engine (Phase 8).

Detects impact/reveal/beauty moments and proposes speed ramps with SFX pairing
and beat-snapping. Three moment types (from RESEARCH-2 §B.3):
  - impact:  motion spike (2σ+) + audio onset. speed 0.30×, sub-bass 70Hz, 1 bar
  - reveal:  emotion peak (arousal ≥0.6) + semantic importance. speed 0.45×, riser
  - beauty:  aesthetic peak (≥0.7) + low motion. speed 0.50×, ambient swell, 2 bars

Beat-snapping: slow-mo duration snaps to musical phrase (1 bar impact, 2 bars beauty).

Public surface:
  - find_slowmo_moments(source_profile, relevance_map, max_per_minute) -> list[dict]
  - proposals_to_filter_chain(proposals) -> list[dict] (recipe-runner ops)
"""
from __future__ import annotations

import typing as t


SPEED_FACTORS = {"impact": 0.30, "reveal": 0.45, "beauty": 0.50}
TIMING = {
    "impact": {"pre_roll": 0.4, "release": 0.4},
    "reveal": {"pre_roll": 0.6, "release": 0.5},
    "beauty": {"pre_roll": 0.0, "release": 0.5},
}
SFX = {
    "impact": {"type": "sub_bass", "freq_hz": 70, "duration_s": 0.8},
    "reveal": {"type": "riser_reverse", "freq_hz": 0, "duration_s": 1.5},
    "beauty": {"type": "ambient_swell", "freq_hz": 0, "duration_s": 2.0},
}


def find_slowmo_moments(source_profile: dict, relevance_map: dict,
                        max_per_minute: int = 2,
                        motion_only_threshold: float = 3.0) -> list[dict]:
    """Find candidate slow-mo moments in the video.

    P1 #6 fix: relaxed co-occurrence window from 0.3s to 1.0s (real-world footage has
    motion/sound offset). Added motion_only_threshold: if sigma >= 3.0, propose slow-mo
    even WITHOUT audio onset (strong motion alone is sufficient evidence of impact)."""
    duration = source_profile.get("metadata", {}).get("duration", 0)
    tempo = source_profile.get("audio", {}).get("tempo", 120.0) or 120.0
    downbeats = source_profile.get("audio", {}).get("downbeats", [])
    proposals: list[dict] = []

    # Impact moments
    for peak in source_profile.get("peaks", {}).get("motion", []):
        ts = float(peak["timestamp"])
        sigma = float(peak.get("sigma", 2.0))
        if sigma < 2.0:
            continue
        onsets = source_profile.get("audio", {}).get("onsets", [])
        # P1 #6: relaxed from 0.3s to 1.0s
        has_onset = any(abs(float(o) - ts) < 1.0 for o in onsets)
        # P1 #6: motion-only trigger — sigma >= motion_only_threshold doesn't need audio
        motion_only = sigma >= motion_only_threshold
        if has_onset or motion_only:
            bar_duration = 4 * (60.0 / tempo) if tempo > 0 else 2.0
            nearest_bar = _find_nearest_bar(ts, downbeats, bar_duration)
            start = nearest_bar if nearest_bar is not None else ts
            timing = TIMING["impact"]
            proposals.append({
                "moment_type": "impact",
                "start": start, "end": start + bar_duration,
                "duration": bar_duration,
                "speed_factor": SPEED_FACTORS["impact"],
                "pre_roll": timing["pre_roll"], "release": timing["release"],
                "impact_frame_ts": ts,
                "sfx": SFX["impact"].copy(),
                "beat_snapped": nearest_bar is not None,
                "nearest_bar_ts": nearest_bar,
                "reasoning": (f"motion peak σ={sigma:.2f}" +
                              (f" + audio onset" if has_onset else " (motion-only trigger)") +
                              f" at t={ts:.2f}s"
                              + (f"; snapped to bar at {nearest_bar:.2f}s" if nearest_bar is not None else "")),
            })

    # Reveal moments
    for ep in source_profile.get("peaks", {}).get("emotion", []):
        ts = float(ep["timestamp"])
        arousal = float(ep.get("arousal", 0.0))
        if arousal < 0.6:
            continue
        per_second = source_profile.get("per_second", [])
        sec = int(ts)
        if sec < len(per_second):
            semantic = float(per_second[sec].get("semantic_importance", 0.5))
        else:
            semantic = 0.5
        if semantic > 0.6:
            timing = TIMING["reveal"]
            duration_s = 2.0
            proposals.append({
                "moment_type": "reveal",
                "start": ts, "end": ts + duration_s, "duration": duration_s,
                "speed_factor": SPEED_FACTORS["reveal"],
                "pre_roll": timing["pre_roll"], "release": timing["release"],
                "impact_frame_ts": ts,
                "sfx": SFX["reveal"].copy(),
                "beat_snapped": False, "nearest_bar_ts": None,
                "reasoning": f"emotion peak arousal={arousal:.2f} + semantic={semantic:.2f} at t={ts:.2f}s",
            })

    # Beauty moments
    for ap in source_profile.get("peaks", {}).get("aesthetic", []):
        ts = float(ap["timestamp"])
        score = float(ap.get("score", 0.0))
        if score < 0.7:
            continue
        per_second = source_profile.get("per_second", [])
        sec = int(ts)
        if sec < len(per_second):
            motion = float(per_second[sec].get("motion_energy", 0.0))
        else:
            motion = 0.5
        if motion < 0.3:
            timing = TIMING["beauty"]
            bar_duration = 4 * (60.0 / tempo) if tempo > 0 else 2.0
            two_bars = bar_duration * 2
            nearest_bar = _find_nearest_bar(ts, downbeats, bar_duration)
            start = nearest_bar if nearest_bar is not None else ts
            proposals.append({
                "moment_type": "beauty",
                "start": start, "end": start + two_bars, "duration": two_bars,
                "speed_factor": SPEED_FACTORS["beauty"],
                "pre_roll": timing["pre_roll"], "release": timing["release"],
                "impact_frame_ts": None,
                "sfx": SFX["beauty"].copy(),
                "beat_snapped": nearest_bar is not None,
                "nearest_bar_ts": nearest_bar,
                "reasoning": f"aesthetic peak score={score:.2f} + low motion={motion:.2f} at t={ts:.2f}s",
            })

    proposals.sort(key=lambda p: p["start"])
    if max_per_minute > 0 and duration > 0:
        max_total = int((duration / 60.0) * max_per_minute)
        # Fix: ensure at least 1 proposal for short videos (< 30s with max_per_minute=2 = 0.67 → 0)
        max_total = max(1, max_total)
        if len(proposals) > max_total:
            proposals.sort(key=lambda p: (
                p.get("sfx", {}).get("type") == "sub_bass",
                p.get("duration", 0),
            ), reverse=True)
            proposals = proposals[:max_total]
            proposals.sort(key=lambda p: p["start"])
    return proposals


def _find_nearest_bar(ts: float, downbeats: list[float], bar_duration: float) -> t.Optional[float]:
    if not downbeats:
        return None
    nearest = min(downbeats, key=lambda b: abs(float(b) - ts))
    if abs(float(nearest) - ts) < bar_duration:
        return float(nearest)
    return None


def proposals_to_filter_chain(proposals: list[dict]) -> list[dict]:
    """Convert slow-mo proposals into recipe-runner operations."""
    operations: list[dict] = []
    for i, p in enumerate(proposals):
        speed = p["speed_factor"]
        atempo_chain: list[float] = []
        remaining = speed
        while remaining < 0.5:
            atempo_chain.append(0.5)
            remaining /= 0.5
        atempo_chain.append(round(remaining, 4))
        operations.append({
            "operation": f"slowmo_{p['moment_type']}_{i}",
            "tool": "edit.speed",
            "params": {
                "start": p["start"] - p["pre_roll"],
                "duration": p["duration"] + p["pre_roll"] + p["release"],
                "factor": speed,
                "atempo_chain": atempo_chain,
                "setpts_factor": round(1.0 / speed, 4),
            },
            "output": f"slowmo_{i}",
            "reasoning": p["reasoning"],
        })
        if p.get("sfx"):
            operations.append({
                "operation": f"sfx_{p['moment_type']}_{i}",
                "tool": "edit.add_audio",
                "params": {
                    "sfx_type": p["sfx"]["type"],
                    "freq_hz": p["sfx"]["freq_hz"],
                    "duration_s": p["sfx"]["duration_s"],
                    "at_ts": p.get("impact_frame_ts") or p["start"],
                },
                "output": f"sfx_{i}",
                "reasoning": f"SFX pairing for {p['moment_type']} moment",
            })
    return operations
