"""
Edit Relevance Map (Phase 7, M1 module).

Takes a SourceProfile (Phase 6) and produces a per-second 6-dimensional score
vector + hero moments + dead zones.

The 6 dimensions per second:
  1. semantic_importance  — from Phase 6 transcript scoring
  2. emotional_intensity  — fusion of face arousal + audio prosody emotion
  3. visual_interest      — fusion of motion + aesthetic + shot change
  4. audio_energy         — fusion of speech + onset + beat
  5. pacing_fit           — does this window match content-type target pacing?
  6. hero_score           — geometric mean of dims 1-4 (cross-modal fusion)

Public surface:
  - build_relevance_map(source_profile, content_type, **opts) -> RelevanceMap
"""
from __future__ import annotations

import dataclasses
import statistics
import typing as t


@dataclasses.dataclass
class WindowScore:
    ts: float
    semantic_importance: float = 0.5
    emotional_intensity: float = 0.0
    visual_interest: float = 0.0
    audio_energy: float = 0.0
    pacing_fit: float = 0.5
    hero_score: float = 0.0

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class RelevanceMap:
    per_second: list[dict] = dataclasses.field(default_factory=list)
    hero_moments: list[dict] = dataclasses.field(default_factory=list)
    dead_zones: list[dict] = dataclasses.field(default_factory=list)
    dimension_correlations: dict = dataclasses.field(default_factory=dict)
    summary: dict = dataclasses.field(default_factory=dict)

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def _dim_semantic(ps: dict) -> float:
    return float(ps.get("semantic_importance", 0.5))


def _dim_emotional(ps: dict) -> float:
    face_arousal = float(ps.get("face_arousal", 0.0))
    prosody = ps.get("audio_prosody_emotion")
    PROSODY_INTENSITY = {
        "angry": 0.9, "happy": 0.7, "sad": 0.6, "surprise": 0.95,
        "fear": 0.95, "disgust": 0.7, "neutral": 0.2, None: 0.0,
    }
    prosody_intensity = PROSODY_INTENSITY.get(prosody, 0.3)
    return 0.6 * face_arousal + 0.4 * prosody_intensity


def _dim_visual(ps: dict, prev_ps: t.Optional[dict] = None) -> float:
    motion = float(ps.get("motion_energy", 0.0))
    aesthetic = float(ps.get("aesthetic_score", 0.5))
    shot_change = 0.0
    if prev_ps and ps.get("shot_scale") != prev_ps.get("shot_scale") and ps.get("shot_scale") != "unknown":
        shot_change = 0.3
    ocr_bonus = 0.2 if ps.get("ocr_text") else 0.0
    return min(1.0, 0.5 * motion + 0.3 * aesthetic + shot_change + ocr_bonus)


def _dim_audio(ps: dict) -> float:
    speech = 1.0 if ps.get("audio_speech") else 0.0
    onset = 0.5 if ps.get("audio_onset") else 0.0
    beat = 0.3 if ps.get("audio_beat") else 0.0
    return min(1.0, 0.6 * speech + 0.3 * onset + 0.1 * beat)


def _dim_pacing(ps: dict, content_type: str, recent_window: list[dict]) -> float:
    PACING_INTERVAL = {
        "vlog": 7.0, "social-short": 4.0, "tutorial": 30.0, "podcast": 60.0,
        "cinematic": 12.0, "interview": 20.0, "documentary": 15.0,
        "talking-head": 15.0, "music-video": 4.0, "event": 10.0,
    }
    interval = PACING_INTERVAL.get(content_type, 10.0)
    interrupts = 0
    for past in recent_window:
        if float(past.get("motion_energy", 0)) > 0.5:
            interrupts += 1
        if float(past.get("face_arousal", 0)) > 0.6:
            interrupts += 1
        if past.get("audio_onset"):
            interrupts += 1
    if interrupts == 0 and len(recent_window) >= int(interval):
        return 0.3
    elif interrupts >= 2:
        return 0.6
    return 0.8


def _hero_score(s: float, e: float, v: float, a: float) -> float:
    eps = 0.01
    product = (s + eps) * (e + eps) * (v + eps) * (a + eps)
    return product ** 0.25


def build_relevance_map(source_profile: dict, content_type: str = "vlog",
                        hero_threshold: float = 0.6,
                        dead_zone_threshold: float = 0.25) -> RelevanceMap:
    per_second_raw = source_profile.get("per_second", [])
    if not per_second_raw:
        return RelevanceMap()

    # P1 #7 fix: Adaptive dead-zone threshold.
    # If the fixed threshold is left at default (0.25), compute an adaptive one:
    # dead_zone_threshold = max(0.15, avg_hero_score * 0.5)
    # This ensures that for videos where all scores are low (no visual features),
    # the bottom half of scores are still flagged as dead zones.
    # For videos with high scores, the threshold stays at 0.25 (or higher).
    if dead_zone_threshold == 0.25:
        # Compute a preliminary score to determine the adaptive threshold
        preliminary_scores = []
        for ps in per_second_raw:
            s = _dim_semantic(ps)
            e = _dim_emotional(ps)
            v = _dim_visual(ps, None)
            a = _dim_audio(ps)
            h = _hero_score(s, e, v, a)
            preliminary_scores.append(h)
        if preliminary_scores:
            avg_h = sum(preliminary_scores) / len(preliminary_scores)
            max_h = max(preliminary_scores)
            # Adaptive: use the lower of the fixed threshold and avg*0.5
            # This ensures dead zones are found even when all scores are low
            adaptive = max(0.10, avg_h * 0.6)
            if max_h < 0.3:
                # Very low-energy content — use adaptive threshold (lower it)
                dead_zone_threshold = adaptive
            # else: keep the fixed 0.25 threshold (content has real signal)

    per_second: list[WindowScore] = []
    recent_window: list[dict] = []

    for i, ps in enumerate(per_second_raw):
        recent_window.append(ps)
        if len(recent_window) > 10:
            recent_window.pop(0)
        prev_ps = per_second_raw[i - 1] if i > 0 else None
        s = _dim_semantic(ps)
        e = _dim_emotional(ps)
        v = _dim_visual(ps, prev_ps)
        a = _dim_audio(ps)
        p = _dim_pacing(ps, content_type, recent_window[:-1])
        h = _hero_score(s, e, v, a)
        per_second.append(WindowScore(
            ts=float(ps.get("ts", i)),
            semantic_importance=s, emotional_intensity=e,
            visual_interest=v, audio_energy=a,
            pacing_fit=p, hero_score=h,
        ))

    hero_moments = _detect_sustained_high(
        per_second, key="hero_score", threshold=hero_threshold,
        min_duration=2, merge_gap=1.0,
    )
    dead_zones = _detect_sustained_low(
        per_second,
        keys=["semantic_importance", "emotional_intensity", "visual_interest", "audio_energy"],
        threshold=dead_zone_threshold, min_duration=3,
    )
    correlations = _compute_correlations(per_second)
    summary = {
        "duration_seconds": len(per_second),
        "content_type": content_type,
        "hero_moment_count": len(hero_moments),
        "dead_zone_count": len(dead_zones),
        "dead_zone_total_seconds": sum(dz["end"] - dz["start"] for dz in dead_zones),
        "avg_hero_score": statistics.mean([w.hero_score for w in per_second]) if per_second else 0,
        "max_hero_score": max((w.hero_score for w in per_second), default=0),
        "dimension_correlations": correlations,
    }
    return RelevanceMap(
        per_second=[w.as_dict() for w in per_second],
        hero_moments=hero_moments,
        dead_zones=dead_zones,
        dimension_correlations=correlations,
        summary=summary,
    )


def _detect_sustained_high(windows: list[WindowScore], key: str, threshold: float,
                            min_duration: int, merge_gap: float = 1.0) -> list[dict]:
    moments: list[dict] = []
    current_run: list[WindowScore] = []
    for w in windows:
        if getattr(w, key) >= threshold:
            current_run.append(w)
        else:
            if len(current_run) >= min_duration:
                moments.append(_finalize_run(current_run, key))
            current_run = []
    if len(current_run) >= min_duration:
        moments.append(_finalize_run(current_run, key))
    return _merge_runs(moments, gap=merge_gap)


def _detect_sustained_low(windows: list[WindowScore], keys: list[str],
                           threshold: float, min_duration: int) -> list[dict]:
    dead_zones: list[dict] = []
    current_run: list[WindowScore] = []
    for w in windows:
        all_low = all(getattr(w, k) < threshold for k in keys)
        if all_low:
            current_run.append(w)
        else:
            if len(current_run) >= min_duration:
                dead_zones.append({
                    "start": current_run[0].ts,
                    "end": current_run[-1].ts + 1,
                    "duration": len(current_run),
                    "avg_scores": {k: statistics.mean([getattr(w, k) for w in current_run]) for k in keys},
                })
            current_run = []
    if len(current_run) >= min_duration:
        dead_zones.append({
            "start": current_run[0].ts,
            "end": current_run[-1].ts + 1,
            "duration": len(current_run),
            "avg_scores": {k: statistics.mean([getattr(w, k) for w in current_run]) for k in keys},
        })
    return dead_zones


def _finalize_run(run: list[WindowScore], key: str) -> dict:
    return {
        "start": run[0].ts,
        "end": run[-1].ts + 1,
        "duration": len(run),
        "peak_score": max(getattr(w, key) for w in run),
        "peak_ts": max(run, key=lambda w: getattr(w, key)).ts,
        "avg_scores": {
            "semantic_importance": statistics.mean([w.semantic_importance for w in run]),
            "emotional_intensity": statistics.mean([w.emotional_intensity for w in run]),
            "visual_interest": statistics.mean([w.visual_interest for w in run]),
            "audio_energy": statistics.mean([w.audio_energy for w in run]),
            "hero_score": statistics.mean([w.hero_score for w in run]),
        },
    }


def _merge_runs(runs: list[dict], gap: float) -> list[dict]:
    if not runs:
        return []
    merged = [runs[0]]
    for r in runs[1:]:
        if r["start"] - merged[-1]["end"] <= gap:
            merged[-1]["end"] = r["end"]
            merged[-1]["duration"] = merged[-1]["end"] - merged[-1]["start"]
            merged[-1]["peak_score"] = max(merged[-1]["peak_score"], r["peak_score"])
        else:
            merged.append(r)
    return merged


def _compute_correlations(windows: list[WindowScore]) -> dict:
    dims = ["semantic_importance", "emotional_intensity", "visual_interest",
            "audio_energy", "hero_score"]
    corrs: dict[str, float] = {}
    for i, d1 in enumerate(dims):
        for d2 in dims[i + 1:]:
            xs = [getattr(w, d1) for w in windows]
            ys = [getattr(w, d2) for w in windows]
            corrs[f"{d1}__{d2}"] = _pearson(xs, ys)
    return corrs


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    den_y = (sum((y - my) ** 2 for y in ys)) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)
