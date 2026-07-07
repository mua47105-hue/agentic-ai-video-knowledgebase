"""
Caption style presets: generate ASS subtitle files with word-level animated highlights.

Presets:
  - word_pop          One word visible at a time, scale/pop animation via \\kf
  - karaoke_highlight Full phrase visible, active word sweeps white to yellow
  - bold_keyword      Static phrase, emphasis words (numbers, superlatives, CTA) bold/colored
  - minimal           Standard static subtitle (same as SRT burn-in)

Usage:
    from kb.tools.caption_presets import caption_ass
    ass_path = caption_ass(words, output_path, preset="karaoke_highlight")
    # then: ffmpeg -i video -vf "subtitles=captions.ass" out.mp4
"""

from __future__ import annotations

import os
import pathlib
import typing as t

# ── Platform safe-zone config (used by Section 7 integration) ──
PLATFORM_SAFE_ZONES: dict[str, dict] = {
    "tiktok":       {"safe_w": 900, "safe_h": 1400, "margin_v": 350, "margin_r": 130},
    "instagram":    {"safe_w": 900, "safe_h": 1400, "margin_v": 400, "margin_r": 0},
    "youtube_shorts": {"safe_w": 900, "safe_h": 1400, "margin_v": 400, "margin_r": 0},
    "default":      {"safe_w": 900, "safe_h": 1400, "margin_v": 40,  "margin_r": 0},
}

EMPHASIS_WORDS: set[str] = {
    "top", "best", "worst", "never", "always", "most", "only", "ever",
    "but", "actually", "turns", "out", "literally", "finally", "finally",
    "one", "two", "three", "first", "second", "last", "new", "big",
    "huge", "massive", "incredible", "amazing", "terrible", "secret",
    "you", "your", "because", "so", "here", "watch", "look", "try",
    "free", "now", "today", "right", "now", "number", "how", "why",
    "what", "when", "does", "don't", "do", "will", "can",
}

FILLER_WORDS: set[str] = {"um", "uh", "uhh", "umm", "like", "you know", "actually", "basically", "literally", "honestly"}


def _fmt_ass_time(seconds: float) -> str:
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    cs = int(s * 100) % 100
    return f"{int(h):01d}:{int(m):02d}:{int(s):02d}.{cs:02d}"


def _ass_header(width: int = 1920, height: int = 1080) -> str:
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "Collisions: Normal\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,30,30,80,1\n"
        "Style: Highlight,Arial,48,&H0000FFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,2,1,2,30,30,80,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )


def _word_duration_cs(word: dict, next_word: dict | None = None) -> int:
    dur = word["end"] - word["start"]
    if next_word and next_word["start"] > word["end"]:
        gap = next_word["start"] - word["end"]
        dur += min(gap, 0.1)
    return max(1, int(dur * 100))


def _min_confidence_gate(words: list[dict], min_prob: float = 0.4) -> bool:
    low_conf = [w for w in words if w.get("probability", 1.0) < min_prob]
    return len(low_conf) / max(len(words), 1) < 0.5


def _word_pop_ass(words: list[dict], margin_v: int = 80) -> str:
    lines = _ass_header()
    for i, w in enumerate(words):
        w_text = w["word"]
        if not w_text.strip():
            continue
        start = w["start"]
        dur_cs = _word_duration_cs(w, words[i + 1] if i + 1 < len(words) else None)
        ts = max(dur_cs - 3, 1)
        end = w["end"]
        lines += f"Dialogue: 0,{_fmt_ass_time(start)},{_fmt_ass_time(end)},Highlight,,0,0,{margin_v},,,{{\\kf{dur_cs}}}{w_text}\n"
    return lines


def _karaoke_highlight_ass(words: list[dict], margin_v: int = 80, max_words_per_line: int = 6) -> str:
    lines = _ass_header()
    buffer: list[dict] = []
    buffer_dur = 0.0
    gap_threshold = 0.5
    for i, w in enumerate(words):
        w_text = w["word"]
        if not w_text.strip():
            continue
        if not buffer:
            buffer_start = w["start"]
        buffer.append(w)
        gap = (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 0
        is_last = (len(buffer) >= max_words_per_line or gap >= gap_threshold or i == len(words) - 1)
        if is_last:
            if len(buffer) == 1:
                dur_cs = _word_duration_cs(w)
                lines += f"Dialogue: 0,{_fmt_ass_time(buffer_start)},{_fmt_ass_time(w['end'])},Highlight,,0,0,{margin_v},,,{{\\kf{dur_cs}}}{w_text}\n"
            else:
                line_text = ""
                for j, bw in enumerate(buffer):
                    bdur_cs = _word_duration_cs(bw, buffer[j + 1] if j + 1 < len(buffer) else None)
                    line_text += f"{{\\kf{bdur_cs}}}{bw['word']} "
                last_word = buffer[-1]
                line_end = last_word["end"]
                for j in range(len(buffer) - 2, -1, -1):
                    bw = buffer[j]
                    next_word = buffer[j + 1]
                    gap_bw = next_word["start"] - bw["end"]
                    if gap_bw > 0.3:
                        line_end = bw["end"] + 0.3
                        break
                lines += f"Dialogue: 0,{_fmt_ass_time(buffer_start)},{_fmt_ass_time(line_end)},Default,,0,0,{margin_v},,,{line_text}\n"
            buffer = []
    return lines


def _bold_keyword_ass(words: list[dict], margin_v: int = 80, max_words_per_line: int = 6) -> str:
    lines = _ass_header()
    buffer: list[dict] = []
    gap_threshold = 0.5
    for i, w in enumerate(words):
        w_text = w["word"]
        if not w_text.strip():
            continue
        if not buffer:
            buffer_start = w["start"]
        buffer.append(w)
        gap = (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 0
        is_last = (len(buffer) >= max_words_per_line or gap >= gap_threshold or i == len(words) - 1)
        if is_last:
            line_text = ""
            for bw in buffer:
                bw_text = bw["word"]
                is_emphasis = bw_text.strip().rstrip(".,!?").lower() in EMPHASIS_WORDS
                if is_emphasis:
                    line_text += f"{{\\b1\\c&H0000FFFF&}}{bw_text}{{\\b0\\c&H00FFFFFF&}} "
                else:
                    line_text += f"{bw_text} "
            last_word = buffer[-1]
            line_end = last_word["end"]
            lines += f"Dialogue: 0,{_fmt_ass_time(buffer_start)},{_fmt_ass_time(line_end)},Default,,0,0,{margin_v},,,{line_text}\n"
            buffer = []
    return lines


def _minimal_ass(words: list[dict], margin_v: int = 80, max_words_per_line: int = 6) -> str:
    lines = _ass_header()
    buffer: list[dict] = []
    gap_threshold = 0.5
    for i, w in enumerate(words):
        w_text = w["word"]
        if not w_text.strip():
            continue
        if not buffer:
            buffer_start = w["start"]
        buffer.append(w)
        gap = (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 0
        is_last = (len(buffer) >= max_words_per_line or gap >= gap_threshold or i == len(words) - 1)
        if is_last:
            line_text = " ".join(bw["word"] for bw in buffer)
            last_word = buffer[-1]
            line_end = last_word["end"]
            lines += f"Dialogue: 0,{_fmt_ass_time(buffer_start)},{_fmt_ass_time(line_end)},Default,,0,0,{margin_v},,,{line_text}\n"
            buffer = []
    return lines


def caption_ass(
    words: list[dict],
    output_path: str,
    *,
    preset: str = "karaoke_highlight",
    width: int = 1920,
    height: int = 1080,
    min_confidence: float = 0.4,
    platform: str = "",
) -> str:
    """Generate an ASS subtitle file with word-level animated captions.

    Parameters
    ----------
    words : list[dict]
        Each dict must have ``word``, ``start``, ``end`` keys
        (and optionally ``probability``).
    output_path : str
        Path for the generated .ass file.
    preset : str
        One of ``word_pop``, ``karaoke_highlight``, ``bold_keyword``, ``minimal``.
        Default is ``karaoke_highlight`` (proven retention lift).
    width, height : int
        Video resolution — used for PlayRes in ASS header.
    min_confidence : float
        Minimum word probability to use animated style.
        If fewer than half the words meet the threshold, falls back to
        segment-level static captions to avoid garbled karaoke on noisy audio.
    platform : str
        Platform name (tiktok, instagram, youtube_shorts) to auto-set
        vertical margins from PLATFORM_SAFE_ZONES.

    Returns
    -------
    str
        Path to the generated .ass file.
    """
    if platform:
        safe = PLATFORM_SAFE_ZONES.get(platform, PLATFORM_SAFE_ZONES["default"])
        margin_v = safe["margin_v"]
    else:
        margin_v = 80

    use_animated = _min_confidence_gate(words, min_confidence)
    if not use_animated:
        preset = "minimal"

    generators = {
        "word_pop": _word_pop_ass,
        "karaoke_highlight": _karaoke_highlight_ass,
        "bold_keyword": _bold_keyword_ass,
        "minimal": _minimal_ass,
    }
    gen = generators.get(preset, _karaoke_highlight_ass)
    ass_content = gen(words, margin_v=margin_v)

    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(output_path).write_text(ass_content, encoding="utf-8")
    return output_path


# ── Integration: one-shot burn-in wrapper ──

def text_subtitles_animated(
    input: str,
    output: str,
    words: list[dict],
    *,
    preset: str = "karaoke_highlight",
    platform: str = "",
    width: int = 1920,
    height: int = 1080,
    min_confidence: float = 0.4,
) -> str:
    """Generate animated ASS captions from word timestamps and burn into video.

    This is the primary entry point for recipes.  Delegates to
    ``caption_ass()`` for ASS generation, then calls FFmpeg's ``subtitles``
    filter for burn-in (same code path as the existing SRT burn-in).

    Returns the output path.
    """
    ass_path = os.path.join(os.path.dirname(output), ".captions_tmp.ass")
    try:
        caption_ass(
            words, ass_path,
            preset=preset, platform=platform,
            width=width, height=height,
            min_confidence=min_confidence,
        )
        from kb.tools.ffmpeg_adapter import _run, _check_ffmpeg, _ensure_parent
        _check_ffmpeg()
        _ensure_parent(output)
        cmd = [
            "ffmpeg", "-i", input,
            "-vf", f"subtitles={ass_path}",
            "-c:a", "copy", output,
        ]
        _run(cmd, check=True)
    finally:
        if os.path.exists(ass_path):
            os.unlink(ass_path)
    return output
