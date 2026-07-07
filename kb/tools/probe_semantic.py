"""
Semantic feature extraction for the intelligent pipeline (Phase 6).

Three responsibilities:
  1. transcribe() — Whisper transcription (faster-whisper, optional CrisperWhisper)
  2. pack_transcript() — compress Whisper JSON into ~12KB Markdown brief
     (video-use pattern — LLM holds this in working memory)
  3. score_segments() — LLM-score each segment on semantic_importance,
     emotional_intensity, hook_potential (optional — falls back to heuristics)
  4. extract_keyphrases() — top-N keyphrases with timestamps for cross-modal hero
     moment detection (Phase 9 §9.3)

Public surface:
  - probe_semantic(video_path, duration, score_with_llm, llm_router) -> SemanticProfile

Graceful degradation:
  - If faster-whisper unavailable: returns empty profile
  - If LLM unavailable: scores via heuristic (text length, question/exclamation marks)
  - Always returns a packed brief (even if empty transcript)
"""
from __future__ import annotations

import dataclasses
import json
import re
import typing as t


# Module-level model cache (avoids 3-8s cold-start on every transcribe call)
_WHISPER_CACHE: t.Optional[dict] = None


@dataclasses.dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: list[dict] = dataclasses.field(default_factory=list)
    semantic_importance: float = 0.5
    emotional_intensity: float = 0.0
    hook_potential: float = 0.0

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class SemanticProfile:
    transcript: list[dict] = dataclasses.field(default_factory=list)
    packed_brief: str = ""
    keyphrases: list[dict] = dataclasses.field(default_factory=list)
    language: str = "en"
    total_words: int = 0
    words_per_minute: float = 0.0
    filler_word_ratio: float = 0.0
    per_second: list[dict] = dataclasses.field(default_factory=list)
    components_used: list[str] = dataclasses.field(default_factory=list)

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


def _has_speech(video_path: str) -> bool:
    """P1 #5 fix: Energy-based speech pre-check.
    Samples 3 random 2-second windows, computes RMS energy variance.
    If variance is very low (constant noise like engine/wind), returns False — skip Whisper.
    If variance is high (speech has pauses + bursts), returns True."""
    try:
        import subprocess
        import tempfile
        import os
        import wave
        import struct

        # Extract a 6-second sample from the middle of the video
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(result.stdout.strip() or 0)
        if duration < 2:
            return True  # too short to check — assume speech

        # Extract 6 seconds from middle as 8kHz mono WAV
        start = max(0, duration / 2 - 3)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(start), "-t", "6", "-i", video_path,
             "-vn", "-ac", "1", "-ar", "8000", "-c:a", "pcm_s16le", tmp.name],
            capture_output=True, timeout=30,
        )

        # Read samples
        with wave.open(tmp.name) as wf:
            frames = wf.readframes(wf.getnframes())
            samples = struct.unpack(f'<{len(frames)//2}h', frames)

        os.unlink(tmp.name)

        if len(samples) < 8000:
            return True  # not enough data — assume speech

        # Compute RMS energy for 3 random 2-second windows
        import math
        window_size = 16000  # 2 seconds at 8kHz
        energies = []
        for offset in [0, len(samples) // 3, len(samples) * 2 // 3]:
            if offset + window_size > len(samples):
                offset = len(samples) - window_size
            window = samples[offset:offset + window_size]
            rms = math.sqrt(sum(s ** 2 for s in window) / len(window))
            energies.append(rms)

        if not energies:
            return True

        # Speech has HIGH variance (pauses + bursts). Engine noise has LOW variance.
        mean_e = sum(energies) / len(energies)
        if mean_e == 0:
            return False  # silence — no speech
        variance = sum((e - mean_e) ** 2 for e in energies) / len(energies)
        cv = (variance ** 0.5) / mean_e  # coefficient of variation

        # CV > 0.3 means significant energy variation → likely speech
        # CV < 0.15 means uniform energy → likely constant noise (engine, wind)
        return cv > 0.15
    except Exception:
        return True  # if pre-check fails, run Whisper (safe default)


def transcribe(video_path: str, model_size: str = "base",
               use_crisperwhisper: bool = False) -> tuple[list[TranscriptSegment], str]:
    """Transcribe using faster-whisper.

    Speed fix: by default uses the requested model_size (fast — 'base' is ~20x realtime).
    CrisperWhisper (3GB, 5-20x slower) is opt-in via use_crisperwhisper=True.
    Module-level cache avoids re-loading the model on every call.
    P1 #5 fix: speech detection gate — skips Whisper on non-speech audio (engine/wind/music).
    """
    global _WHISPER_CACHE

    # P1 #5: Speech detection gate — skip Whisper on non-speech audio
    if not _has_speech(video_path):
        return [], "en"

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return [], "en"

    # Module-level model cache: avoid re-loading on every call (saves 3-8s per call)
    cache_key = (model_size, use_crisperwhisper)
    if _WHISPER_CACHE is None:
        _WHISPER_CACHE = {}
    if cache_key in _WHISPER_CACHE:
        model = _WHISPER_CACHE[cache_key]
    else:
        # Try CrisperWhisper first ONLY if explicitly requested; else use requested model
        model = None
        candidates = (("nyrahealth/faster_CrisperWhisper", model_size) if use_crisperwhisper
                      else (model_size,))
        for model_id in candidates:
            try:
                model = WhisperModel(model_id, device="cpu", compute_type="int8")
                break
            except Exception:
                continue
        if model is None:
            return [], "en"
        _WHISPER_CACHE[cache_key] = model

    try:
        segments_iter, info = model.transcribe(video_path, word_timestamps=True)
        segments: list[TranscriptSegment] = []
        for seg in segments_iter:
            words = []
            if hasattr(seg, "words") and seg.words:
                for w in seg.words:
                    words.append({"word": w.word, "start": w.start, "end": w.end})
            segments.append(TranscriptSegment(
                start=seg.start, end=seg.end,
                text=seg.text.strip(), words=words,
            ))
        return segments, info.language
    except Exception:
        return [], "en"


def pack_transcript(segments: list[TranscriptSegment], duration: float) -> str:
    """Pack transcript into a compact Markdown brief (~12KB target)."""
    lines = ["# Packed Transcript", ""]
    lines.append(f"Duration: {duration:.1f}s ({duration / 60:.1f} min)")
    lines.append(f"Segments: {len(segments)}")
    total_words = sum(len(s.text.split()) for s in segments)
    lines.append(f"Total words: {total_words}")
    lines.append("")

    FILLER = {"um", "uh", "like", "you know", "basically", "actually", "literally",
              "kind of", "sort of", "i mean", "right"}

    current_turn: list[TranscriptSegment] = []
    for seg in segments:
        if current_turn and seg.start - current_turn[-1].end > 1.0:
            _emit_turn(lines, current_turn, FILLER)
            current_turn = []
        current_turn.append(seg)
    if current_turn:
        _emit_turn(lines, current_turn, FILLER)

    brief = "\n".join(lines)
    MAX_BYTES = 12288
    if len(brief.encode("utf-8")) > MAX_BYTES:
        brief = brief.encode("utf-8")[:MAX_BYTES].decode("utf-8", errors="ignore")
        last_nl = brief.rfind("\n")
        if last_nl > 0:
            brief = brief[:last_nl]
        brief += "\n\n[... truncated for context budget ...]"
    return brief


def _emit_turn(lines: list[str], turn: list[TranscriptSegment], filler: set) -> None:
    if not turn:
        return
    start = turn[0].start
    end = turn[-1].end
    text = " ".join(s.text for s in turn)
    words = text.split()
    cleaned = [w for w in words if w.lower().strip(".,!?") not in filler]
    text = " ".join(cleaned) if cleaned else text
    lines.append(f"[{_fmt_ts(start)} - {_fmt_ts(end)}] {text}")


def _fmt_ts(sec: float) -> str:
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m:02d}:{s:02d}"


def _heuristic_score(text: str) -> tuple[float, float, float]:
    """Heuristic scoring when LLM unavailable."""
    words = text.split()
    n = len(words)
    if n == 0:
        return 0.3, 0.0, 0.0
    # Semantic importance: longer utterances with content words score higher
    semantic = min(1.0, 0.3 + n / 40.0)
    # Emotional intensity: exclamation/question marks, emotional keywords
    emo_kw = {"love", "hate", "amazing", "terrible", "wow", "incredible",
              "shocking", "best", "worst", "never", "always", "everyone", "nobody"}
    text_lower = text.lower()
    emo_count = sum(1 for kw in emo_kw if kw in text_lower)
    excl = text.count("!") + text.count("?")
    emotional = min(1.0, (emo_count * 0.3) + (excl * 0.15))
    # Hook potential: short, punchy, starts with question or strong word
    hook = 0.3
    if n < 12:
        hook += 0.3
    if text.strip().startswith(("What", "Why", "How", "Did", "Is", "Are", "Imagine", "Never")):
        hook += 0.3
    hook = min(1.0, hook)
    return semantic, emotional, hook


def score_segments(segments: list[TranscriptSegment],
                   llm_router: t.Optional[object] = None) -> list[TranscriptSegment]:
    """Score segments. Tries LLM first; falls back to heuristic."""
    if not segments:
        return segments

    # Try LLM scoring in batches
    if llm_router is not None or _llm_available():
        BATCH = 50
        for batch_start in range(0, len(segments), BATCH):
            batch = segments[batch_start:batch_start + BATCH]
            try:
                scores = _call_llm_for_scores(batch)
                if scores and len(scores) == len(batch):
                    for seg, sc in zip(batch, scores):
                        seg.semantic_importance = float(sc.get("semantic_importance", 0.5))
                        seg.emotional_intensity = float(sc.get("emotional_intensity", 0.0))
                        seg.hook_potential = float(sc.get("hook_potential", 0.0))
                    continue
            except Exception:
                pass
            # Fallback for this batch
            for seg in batch:
                s, e, h = _heuristic_score(seg.text)
                seg.semantic_importance = s
                seg.emotional_intensity = e
                seg.hook_potential = h
        return segments

    # No LLM — pure heuristic
    for seg in segments:
        s, e, h = _heuristic_score(seg.text)
        seg.semantic_importance = s
        seg.emotional_intensity = e
        seg.hook_potential = h
    return segments


def _llm_available() -> bool:
    try:
        import litellm  # noqa
        return True
    except ImportError:
        return False


def _call_llm_for_scores(batch: list[TranscriptSegment]) -> t.Optional[list[dict]]:
    try:
        import litellm
        segs_json = json.dumps([
            {"start": s.start, "end": s.end, "text": s.text[:200]} for s in batch
        ])
        prompt = (
            "Score each transcript segment 0.0-1.0 on: semantic_importance, "
            "emotional_intensity, hook_potential. Return ONLY a JSON array, one "
            "object per segment, in order. Segments:\n" + segs_json
        )
        response = litellm.completion(
            model="ollama/qwen2.5-coder:7b",
            messages=[{"role": "user", "content": prompt}],
            format="json", temperature=0.3, max_tokens=4000,
        )
        text = response.choices[0].message.content
        return json.loads(text)
    except Exception:
        return None


def extract_keyphrases(segments: list[TranscriptSegment], top_n: int = 20) -> list[dict]:
    """Extract top-N keyphrases with timestamps via simple TF-IDF + position weighting."""
    from collections import Counter, defaultdict

    STOPWORDS = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
                 "be", "been", "have", "has", "had", "do", "does", "did", "will",
                 "would", "could", "should", "may", "might", "must", "can", "this",
                 "that", "these", "those", "i", "you", "he", "she", "it", "we", "they",
                 "what", "which", "who", "when", "where", "why", "how", "all", "each",
                 "every", "both", "few", "more", "most", "other", "some", "such",
                 "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
                 "just", "really", "quite", "pretty", "kind", "sort"}

    doc_freq: Counter = Counter()
    phrase_positions: dict[str, list[float]] = defaultdict(list)

    for seg in segments:
        words = re.findall(r"\b[a-z]{3,}\b", seg.text.lower())
        words = [w for w in words if w not in STOPWORDS]
        for w in words:
            doc_freq[w] += 1
            phrase_positions[w].append(seg.start)
        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i + 1]}"
            doc_freq[bg] += 1
            phrase_positions[bg].append(seg.start)

    total_docs = max(1, len(segments))
    scored: list[dict] = []
    for phrase, df in doc_freq.most_common(top_n * 3):
        if df < 2:
            continue
        idf = total_docs / df if df > 0 else 0
        first_pos = phrase_positions[phrase][0]
        position_weight = 1.0 + max(0, 0.5 - (first_pos / max(1, segments[-1].end if segments else 1))) * 0.5
        score = df * idf * position_weight
        scored.append({
            "phrase": phrase, "timestamp": first_pos,
            "score": float(score), "frequency": df,
        })
    return sorted(scored, key=lambda x: -x["score"])[:top_n]


def probe_semantic(video_path: str, duration: float,
                   score_with_llm: bool = True,
                   llm_router: t.Optional[object] = None) -> SemanticProfile:
    """Run all semantic probes, merge into SemanticProfile."""
    profile = SemanticProfile()
    components: list[str] = []

    segments, lang = transcribe(video_path)
    profile.language = lang
    profile.transcript = [s.as_dict() for s in segments]

    if not segments:
        profile.packed_brief = "# Packed Transcript\n\n(no transcript available)\n"
        profile.components_used = components
        return profile
    components.append("faster_whisper")

    profile.total_words = sum(len(s.text.split()) for s in segments)
    if duration > 0:
        profile.words_per_minute = profile.total_words / (duration / 60.0)

    FILLER = {"um", "uh", "like", "you know", "basically", "actually", "literally"}
    filler_count = sum(s.text.lower().count(fw) for s in segments for fw in FILLER)
    profile.filler_word_ratio = filler_count / profile.total_words if profile.total_words > 0 else 0.0

    if score_with_llm:
        segments = score_segments(segments, llm_router)
        profile.transcript = [s.as_dict() for s in segments]
        components.append("llm_scoring" if _llm_available() else "heuristic_scoring")
    else:
        for s in segments:
            si, ei, hp = _heuristic_score(s.text)
            s.semantic_importance = si
            s.emotional_intensity = ei
            s.hook_potential = hp
        profile.transcript = [s.as_dict() for s in segments]
        components.append("heuristic_scoring")

    profile.packed_brief = pack_transcript(segments, duration)
    profile.keyphrases = extract_keyphrases(segments)

    # Per-second aggregation
    per_second: list[dict] = []
    for sec in range(int(duration)):
        entry = {
            "ts": sec, "speech": False, "semantic_importance": 0.5,
            "emotional_intensity": 0.0, "hook_potential": 0.0, "text": "",
        }
        for s in segments:
            if s.start <= sec < s.end:
                entry["speech"] = True
                entry["semantic_importance"] = max(entry["semantic_importance"], s.semantic_importance)
                entry["emotional_intensity"] = max(entry["emotional_intensity"], s.emotional_intensity)
                entry["hook_potential"] = max(entry["hook_potential"], s.hook_potential)
                entry["text"] = s.text[:100]
                break
        per_second.append(entry)
    profile.per_second = per_second

    profile.components_used = components
    return profile
