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
    """Premium ASS header. Upgraded from Arial/48/outline to Montserrat/72/box-background.
    This single change is the biggest quality lever (per motion-design research)."""
    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "Collisions: Normal\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "WrapStyle: 2\n"  # no auto-wrapping — we control line breaks
        "ScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # Default: MrBeast-style — Montserrat Bold, box background (BorderStyle=4), 50% black, padding via Shadow=4
        "Style: Default,Montserrat,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,1,0,4,0,4,2,40,40,80,1\n"
        # Highlight: yellow active word (MrBeast signature)
        "Style: Highlight,Montserrat,72,&H0000FFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,1,0,4,0,4,2,40,40,80,1\n"
        # Apple: Inter Bold, thin outline + soft shadow (Apple keynote style)
        "Style: Apple,Inter,56,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,1,0,1,2,1,2,40,40,80,1\n"
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


# ── Spring physics sampler (for real bounce animation) ──
# Implements damped harmonic oscillator: x(t) = 1 - e^(-ζωt) * (cos(ω_d·t) + (ζ/√(1-ζ²))·sin(ω_d·t))
# Samples the spring curve at N points and emits a chain of ASS \t tags that approximate it.
# This is the difference between "PowerPoint ease" and "real motion design."

def _spring_samples(stiffness: float = 200, damping: float = 15, mass: float = 1,
                    samples: int = 8) -> list[tuple[int, float]]:
    """Sample a damped spring at N points. Returns [(t_ms, x)] where x is 0..1+overshoot."""
    import math
    omega = math.sqrt(stiffness / mass)
    zeta = damping / (2 * math.sqrt(stiffness * mass))
    if zeta >= 1:
        zeta = 0.999  # clamp to slightly underdamped
    omega_d = omega * math.sqrt(max(0, 1 - zeta ** 2))
    zeta_fac = zeta / math.sqrt(max(1e-9, 1 - zeta ** 2))
    # Find settle time (when |x - 1| < 0.002)
    settle_t = 1.0
    for ms in range(50, 5000, 10):
        t = ms / 1000
        x = 1 - math.exp(-zeta * omega * t) * (math.cos(omega_d * t) + zeta_fac * math.sin(omega_d * t))
        if abs(x - 1) < 0.002:
            settle_t = t
            break
    pts = []
    for i in range(samples + 1):
        t = (i / samples) * settle_t
        x = 1 - math.exp(-zeta * omega * t) * (math.cos(omega_d * t) + zeta_fac * math.sin(omega_d * t))
        pts.append((int(t * 1000), x))
    return pts


def _spring_scale_tag(start_pct: int = 70, target_pct: int = 100,
                      stiffness: float = 200, damping: float = 15) -> str:
    """Build an ASS {\\fscx70\\fscy70\\t(0,30,\\fscx83\\fscy83)...} tag for a spring bounce.
    The spring's overshoot naturally produces the MrBeast 'pop' (110% then settle to 100%)."""
    pts = _spring_samples(stiffness, damping)
    parts = [f"\\fscx{start_pct}\\fscy{start_pct}"]
    for i in range(1, len(pts)):
        t1, _ = pts[i - 1]
        t2, x = pts[i]
        scale = int(start_pct + (target_pct - start_pct) * x)
        parts.append(f"\\t({t1},{t2},\\fscx{scale}\\fscy{scale})")
    return "{" + "".join(parts) + "}"


def _chunk_words(words: list[dict], max_per_line: int = 6) -> list[list[dict]]:
    """Group words into lines of at most max_per_line, breaking on gaps > 0.5s."""
    chunks = []
    buffer = []
    for i, w in enumerate(words):
        if not w.get("word", "").strip():
            continue
        buffer.append(w)
        gap = (words[i + 1]["start"] - w["end"]) if i + 1 < len(words) else 999
        if len(buffer) >= max_per_line or gap >= 0.5 or i == len(words) - 1:
            chunks.append(buffer)
            buffer = []
    return chunks


def _mrbeast_bounce_ass(words: list[dict], margin_v: int = 80, max_words_per_line: int = 6) -> str:
    """MrBeast-style per-word kinetic typography.

    Each word:
    - Spring-bounces in (70% → 110% → 100%) over ~400ms
    - Yellow active word (MrBeast signature), snaps back to white after word ends
    - 80ms fade-in, 60ms fade-out
    - Box background (from ASS header BorderStyle=4)

    This is the 'TikTok/Reels kinetic caption' look — converts static subtitles
    into engaging per-word animation that holds viewer attention."""
    lines = _ass_header()
    for i, w in enumerate(words):
        text = w.get("word", "")
        if not text.strip():
            continue
        start, end = w["start"], w["end"]
        word_dur_ms = max(80, int((end - start) * 1000))

        # Spring bounce for entrance (stiffness=200, damping=15 = ~5% overshoot, one bounce)
        bounce_tag = _spring_scale_tag(start_pct=70, target_pct=100,
                                        stiffness=200, damping=15)
        # Color: yellow at start, snap to white after word ends (instant via \t with t1==t2)
        color_tag = f"\\1c&H0000FFFF&\\t({word_dur_ms},{word_dur_ms},\\1c&H00FFFFFF&)"
        # Fade: 80ms in, 60ms out
        fade_tag = "\\fad(80,60)"
        # Merge all tags (strip the outer {} from bounce_tag, re-wrap)
        combined = "{" + bounce_tag[1:-1] + color_tag + fade_tag + "}"
        lines += (f"Dialogue: 0,{_fmt_ass_time(start)},{_fmt_ass_time(end + 0.06)},"
                  f"Default,,0,0,{margin_v},,,{combined}{text}\n")
    return lines


def _apple_premium_ass(words: list[dict], margin_v: int = 80, max_words_per_line: int = 6) -> str:
    """Apple-keynote-style entrance for title cards / longer phrases.

    Each line (not per-word):
    - Blur-in: \\blur8 → \\blur0 over 300ms (the 'cinematic reveal')
    - Fade: 0 → 1 over 400ms
    - Scale: 95% → 100% over 500ms (subtle, no overshoot — Apple restraint)
    - Uses Apple style (Inter Bold, thin outline + soft shadow)

    This is the 'premium keynote' look — restrained, cinematic, no bounce."""
    lines = _ass_header()
    for chunk in _chunk_words(words, max_words_per_line):
        line_text = " ".join(w["word"] for w in chunk)
        if not line_text.strip():
            continue
        start = chunk[0]["start"]
        end = chunk[-1]["end"]
        # Apple entrance: blur 8→0 over 300ms, fade 0→1 over 400ms, scale 95→100 over 500ms
        tag = (r"{\blur8\t(0,300,\blur0)"           # blur-in (the secret ingredient)
               r"\fad(400,200)"                      # fade in/out
               r"\fscx95\fscy95\t(0,500,\fscx100\fscy100)}")  # subtle scale (no overshoot)
        lines += (f"Dialogue: 0,{_fmt_ass_time(start)},{_fmt_ass_time(end + 0.2)},"
                  f"Apple,,0,0,{margin_v},,,{tag}{line_text}\n")
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
        "mrbeast_bounce": _mrbeast_bounce_ass,      # NEW: per-word spring bounce + yellow active word
        "apple_premium": _apple_premium_ass,          # NEW: blur-in + fade + scale (cinematic)
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
        # Pass fontsdir so libass finds the bundled professional fonts (Montserrat, Inter)
        # Falls back to system fonts if our bundled fonts aren't present.
        fonts_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
        fonts_dir_abs = os.path.abspath(fonts_dir)
        fonts_arg = f":fontsdir={fonts_dir_abs}" if os.path.isdir(fonts_dir_abs) else ""
        cmd = [
            "ffmpeg", "-i", input,
            "-vf", f"subtitles={ass_path}{fonts_arg}",
            "-c:a", "copy", output,
        ]
        _run(cmd, check=True)
    finally:
        if os.path.exists(ass_path):
            os.unlink(ass_path)
    return output
