"""
Cross-modal Hero Moment Detector (Phase 9). ★ NOVEL (RESEARCH-3 gap #3) ★

Finds moments where peaks from multiple modalities co-occur within a tight window.
Stronger signal than Phase 7's per-second geometric mean because it requires
actual peak alignment, not just high average scores.

Three fusion levels:
  - Level 3 (TRIPLE): audio peak + visual peak + semantic salience within 1.0s
    → "hero_moment" (always keep, consider slow-mo)
  - Level 2 (DOUBLE): two of three modalities peak within 1.0s
    → "strong_moment" (keep, candidate for emphasis)
  - Level 1 (SINGLE): one modality peaks
    → "notable_moment" (consider keeping)

Public surface:
  - detect_hero_moments(source_profile, relevance_map, co_occurrence_window) -> list[dict]
"""
from __future__ import annotations


def detect_hero_moments(source_profile: dict, relevance_map: dict,
                        co_occurrence_window: float = None) -> list[dict]:
    from kb.tools.intelligence_config import get_config
    _cfg = get_config(source_profile.get('metadata', {}).get('content_type', 'vlog'))
    if co_occurrence_window is None: co_occurrence_window = _cfg.co_occurrence_window
    """Detect cross-modal hero moments by fusing peaks from audio, visual, semantic."""
    audio_peaks = _extract_audio_peaks(source_profile)
    visual_peaks = _extract_visual_peaks(source_profile)
    semantic_peaks = _extract_semantic_peaks(source_profile, relevance_map)

    moments: list[dict] = []
    captured_ts: set[float] = set()

    # Triple co-occurrence
    for ap in audio_peaks:
        for vp in visual_peaks:
            if abs(ap["timestamp"] - vp["timestamp"]) > co_occurrence_window:
                continue
            for sp in semantic_peaks:
                if (abs(ap["timestamp"] - sp["timestamp"]) <= co_occurrence_window and
                    abs(vp["timestamp"] - sp["timestamp"]) <= co_occurrence_window):
                    center = (ap["timestamp"] + vp["timestamp"] + sp["timestamp"]) / 3
                    moments.append(_build_hero(center, 3, "hero_moment",
                                              ["audio", "visual", "semantic"],
                                              {"audio": ap, "visual": vp, "semantic": sp}))
                    captured_ts.add(round(center, 1))

    # Double co-occurrence (not already captured by triple)
    for ap in audio_peaks:
        for vp in visual_peaks:
            if abs(ap["timestamp"] - vp["timestamp"]) <= co_occurrence_window:
                center = (ap["timestamp"] + vp["timestamp"]) / 2
                if round(center, 1) not in captured_ts:
                    moments.append(_build_hero(center, 2, "strong_moment",
                                              ["audio", "visual"],
                                              {"audio": ap, "visual": vp}))
                    captured_ts.add(round(center, 1))
        for sp in semantic_peaks:
            if abs(ap["timestamp"] - sp["timestamp"]) <= co_occurrence_window:
                center = (ap["timestamp"] + sp["timestamp"]) / 2
                if round(center, 1) not in captured_ts:
                    moments.append(_build_hero(center, 2, "strong_moment",
                                              ["audio", "semantic"],
                                              {"audio": ap, "semantic": sp}))
                    captured_ts.add(round(center, 1))
    for vp in visual_peaks:
        for sp in semantic_peaks:
            if abs(vp["timestamp"] - sp["timestamp"]) <= co_occurrence_window:
                center = (vp["timestamp"] + sp["timestamp"]) / 2
                if round(center, 1) not in captured_ts:
                    moments.append(_build_hero(center, 2, "strong_moment",
                                              ["visual", "semantic"],
                                              {"visual": vp, "semantic": sp}))
                    captured_ts.add(round(center, 1))

    # Single peaks (top 5 per modality)
    for ap in audio_peaks[:5]:
        if round(ap["timestamp"], 1) not in captured_ts:
            moments.append(_build_hero(ap["timestamp"], 1, "notable_moment",
                                      ["audio"], {"audio": ap}))
    for vp in visual_peaks[:5]:
        if round(vp["timestamp"], 1) not in captured_ts:
            moments.append(_build_hero(vp["timestamp"], 1, "notable_moment",
                                      ["visual"], {"visual": vp}))

    # Temporal decay: suppress clustered peaks (keep only the strongest within 2s)
    filtered = []
    for m in moments:
        too_close = any(abs(m["start"] - f["start"]) < 2.0 and m["level"] <= f["level"] for f in filtered)
        if not too_close:
            filtered.append(m)
    moments = filtered
    moments.sort(key=lambda m: (-m["level"], -m["geometric_mean"]))
    return moments


def _extract_audio_peaks(profile: dict) -> list[dict]:
    peaks: list[dict] = []
    audio = profile.get("audio", {})
    for onset in audio.get("onsets", [])[:50]:
        peaks.append({"timestamp": float(onset), "score": 0.7,
                     "detail": f"audio onset at {onset:.2f}s"})
    for pe in audio.get("prosody_emotion", []):
        if pe.get("emotion") in ("angry", "surprise", "fear"):
            peaks.append({"timestamp": float(pe["start"]), "score": 0.85,
                         "detail": f"prosody emotion '{pe['emotion']}' at {pe['start']:.1f}s"})
    return peaks


def _extract_visual_peaks(profile: dict) -> list[dict]:
    peaks: list[dict] = []
    visual = profile.get("visual", {})
    for mp in visual.get("motion_peaks", []):
        peaks.append({"timestamp": float(mp["timestamp"]),
                     "score": min(1.0, float(mp.get("sigma", 2.0)) / 4.0),
                     "detail": f"motion peak σ={mp.get('sigma', 0):.2f} at {mp['timestamp']:.2f}s"})
    for ep in visual.get("emotion_peaks", []):
        peaks.append({"timestamp": float(ep["timestamp"]),
                     "score": float(ep.get("arousal", 0.5)),
                     "detail": f"face emotion '{ep.get('emotion')}' arousal={ep.get('arousal', 0):.2f} at {ep['timestamp']:.2f}s"})
    for ap in visual.get("aesthetic_peaks", []):
        peaks.append({"timestamp": float(ap["timestamp"]),
                     "score": float(ap.get("score", 0.5)),
                     "detail": f"aesthetic peak score={ap.get('score', 0):.2f} at {ap['timestamp']:.2f}s"})
    return peaks


def _extract_semantic_peaks(profile: dict, relevance_map: dict) -> list[dict]:
    peaks: list[dict] = []
    for seg in profile.get("semantic", {}).get("transcript", []):
        if float(seg.get("semantic_importance", 0)) > 0.7:
            peaks.append({"timestamp": float(seg["start"]),
                         "score": float(seg["semantic_importance"]),
                         "detail": f"semantic importance {seg['semantic_importance']:.2f}: \"{(seg.get('text', '') or '')[:60]}\""})
    for kp in profile.get("semantic", {}).get("keyphrases", [])[:10]:
        peaks.append({"timestamp": float(kp["timestamp"]),
                     "score": min(1.0, float(kp["score"]) / 10.0),
                     "detail": f"keyphrase \"{kp['phrase']}\" at {kp['timestamp']:.1f}s"})
    return peaks


def _build_hero(center_ts: float, level: int, label: str,
                modalities: list[str], peaks: dict) -> dict:
    scores = [peaks[m]["score"] for m in modalities]
    product = 1.0
    for s in scores:
        product *= max(s, 0.01)
    geo_mean = product ** (1.0 / len(scores))
    reasoning_parts = [f"Level {level} ({label}): "]
    for m in modalities:
        p = peaks[m]
        reasoning_parts.append(f"{m} peak at {p['timestamp']:.2f}s (score {p['score']:.2f}) — {p['detail']}; ")
    reasoning = "".join(reasoning_parts) + f"Geometric mean: {geo_mean:.3f}."
    return {
        "start": max(0, center_ts - 1.0),
        "end": center_ts + 1.0,
        "level": level, "label": label,
        "fusion_reasoning": reasoning,
        "modalities": modalities,
        "peak_timestamps": {m: peaks[m]["timestamp"] for m in modalities},
        "peak_scores": {m: peaks[m]["score"] for m in modalities},
        "geometric_mean": geo_mean,
    }
