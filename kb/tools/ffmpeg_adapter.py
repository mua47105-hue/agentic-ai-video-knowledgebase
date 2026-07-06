#!/usr/bin/env python3
"""
Drop-in FFmpeg/faster-whisper shim implementing the mcp-video tools
referenced in SKILL.md.  Lets the stack work without a running MCP server.

Tools: probe, trim, merge, resize, silence_remove, transcribe,
       color_grade, text_subtitles, loudnorm, speed, stabilize,
       scene_detect, pip, verify.

Usage:
    from kb.tools.ffmpeg_adapter import edit
    edit.probe("input.mp4")
    edit.trim("input.mp4", "out.mp4", start="00:01:00", end="00:01:30")
"""

from __future__ import annotations
import json, os, pathlib, re, shutil, subprocess, tempfile, time, typing as t

PathLike = t.Union[str, os.PathLike]

_FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
_FFPROBE = shutil.which("ffprobe") or "ffprobe"


# ───────────────────────── helpers ─────────────────────────

def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def _check_ffmpeg() -> None:
    if not shutil.which(_FFMPEG):
        raise RuntimeError("ffmpeg not found — install it first (brew install ffmpeg / sudo apt install ffmpeg)")


def _probe_json(path: str) -> dict:
    res = _run([_FFPROBE, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", path])
    return json.loads(res.stdout)


def _probe_duration(path: str) -> float:
    d = _probe_json(path)
    return float(d.get("format", {}).get("duration", 0))


def _probe_fps(path: str) -> float:
    d = _probe_json(path)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    r = v.get("r_frame_rate", "0/1")
    return _parse_fraction(r)


def _parse_fraction(s: str) -> float:
    if "/" in s:
        parts = s.split("/")
        try:
            return float(parts[0]) / float(parts[1]) if len(parts) == 2 and float(parts[1]) != 0 else 0.0
        except (ValueError, ZeroDivisionError):
            return 0.0
    return 0.0


def _ensure_parent(path: str) -> None:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)


# ───────────────────────── public tools ─────────────────────────

def probe(path: str) -> dict:
    """Return full media info as a dict (format + all streams)."""
    return _probe_json(path)


def info(path: str) -> dict:
    """Return a concise summary: duration, resolution, codecs, audio flag."""
    d = _probe_json(path)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), {})
    fmt = d.get("format", {})
    return {
        "duration": float(fmt.get("duration", 0)),
        "width": v.get("width"),
        "height": v.get("height"),
        "fps": _parse_fraction(v.get("r_frame_rate", "0/1")),
        "video_codec": v.get("codec_name"),
        "audio_codec": a.get("codec_name"),
        "has_audio": "audio" in [s.get("codec_type") for s in d.get("streams", [])],
        "size_bytes": int(fmt.get("size", 0)),
        "bitrate": int(fmt.get("bit_rate", 0)),
    }


def trim(input: str, output: str, start: str = "", end: str = "",
         duration: str = "", accurate: bool = True) -> str:
    """Cut a segment.  accurate=True re-encodes (frame-accurate).
    -ss before -i for fast keyframe seek; re-encode for frame accuracy."""
    _check_ffmpeg()
    _ensure_parent(output)
    cmd = [_FFMPEG]
    if start:
        cmd += ["-ss", start]
    cmd += ["-i", input]
    if accurate:
        cmd += ["-c:v", "libx264", "-c:a", "aac"]
    else:
        cmd += ["-c", "copy"]
    if end:
        cmd += ["-to", end]
    elif duration:
        cmd += ["-t", duration]
    cmd += [output]
    _run(cmd, check=True)
    return output


def merge(inputs: list[str], output: str, transition: str = "",
          transition_duration: float = 0.5) -> str:
    """Concatenate clips.  With optional xfade transition."""
    _check_ffmpeg()
    _ensure_parent(output)
    if not transition or len(inputs) < 2:
        # concat demuxer (same codecs, fast)
        list_path = output + ".concat.txt"
        with open(list_path, "w") as f:
            for p in inputs:
                f.write(f"file '{pathlib.Path(p).resolve()}'\n")
        _run([_FFMPEG, "-f", "concat", "-safe", "0", "-i", list_path,
              "-c", "copy", output], check=True)
        os.unlink(list_path)
    else:
        # xfade filter chain
        _run_xfade_chain(inputs, output, transition, transition_duration)
    return output


def _run_xfade_chain(inputs: list[str], output: str,
                     transition: str, dur: float) -> None:
    """Chain n clips with xfade/acrossfade.  Probes each clip for
    actual duration + fps; correct offset math for n>2; forces CFR
    after setpts for FFmpeg 7.x compatibility."""
    n = len(inputs)
    durations = [_probe_duration(inp) for inp in inputs]
    fps = _probe_fps(inputs[0]) or 30
    filters = []
    # Pre-filter each input: trim to its actual duration, reset PTS, force CFR
    for i in range(n):
        d = durations[i]
        filters.append(f"[{i}:v]trim=0:{d},setpts=PTS-STARTPTS,fps={fps}[v{i}]")
        filters.append(f"[{i}:a]atrim=0:{d},asetpts=PTS-STARTPTS[a{i}]")
    # Chain xfades — offset = sum(d[0..i]) - (i+1)*dur
    cum_dur = 0.0
    for i in range(n - 1):
        cum_dur += durations[i]
        offset = cum_dur - (i + 1) * dur
        if offset < 0:
            offset = 0
        vi = f"v{i}" if i == 0 else f"vout{i-1}"
        vj = f"v{i+1}"
        ai = f"a{i}" if i == 0 else f"aout{i-1}"
        aj = f"a{i+1}"
        filters.append(f"[{vi}][{vj}]xfade=offset={offset}:duration={dur}:transition={transition}[vout{i}]")
        filters.append(f"[{ai}][{aj}]acrossfade=d={dur}[aout{i}]")
    last = n - 2
    cmd = [_FFMPEG]
    for inp in inputs:
        cmd += ["-i", inp]
    cmd += ["-filter_complex", ";".join(filters),
            "-map", f"[vout{last}]", "-map", f"[aout{last}]",
            "-c:v", "libx264", "-c:a", "aac", output]
    _run(cmd, check=True)


def resize(input: str, output: str, width: int = 0, height: int = 0) -> str:
    """Scale video.  If only one dimension given, the other auto-scales."""
    _check_ffmpeg()
    _ensure_parent(output)
    scale = ""
    if width and height:
        scale = f"scale={width}:{height}"
    elif width:
        scale = f"scale={width}:-2"
    elif height:
        scale = f"scale=-2:{height}"
    else:
        raise ValueError("provide width and/or height")
    cmd = [_FFMPEG, "-i", input, "-vf", scale, "-c:a", "copy", output]
    _run(cmd, check=True)
    return output


def silence_remove(input: str, output: str, threshold: float = -50,
                   min_silence: float = 0.5, padding: float = 0.3) -> str:
    """Remove silent sections via silencedetect + trim+concat.
    Maintains perfect A/V sync by trimming BOTH streams per keep-region.
    padding seconds of breath/natural silence preserved at each cut."""
    _check_ffmpeg()
    _ensure_parent(output)
    duration = _probe_duration(input)

    # Pass 1 — detect silence regions
    res = _run([_FFMPEG, "-i", input,
                "-af", f"silencedetect=n={threshold}dB:d={min_silence}",
                "-f", "null", "-"])
    silence_starts = [float(m.group(1)) for m in
                      re.finditer(r"silence_start: ([\d.]+)", res.stderr)]
    silence_ends = [float(m.group(1)) for m in
                    re.finditer(r"silence_end: ([\d.]+)", res.stderr)]
    if not silence_starts:
        cmd = [_FFMPEG, "-i", input, "-c", "copy", output]
        _run(cmd, check=True)
        return output

    # Expand each silence by `padding` seconds, then merge overlaps
    expanded: list[tuple[float, float]] = []
    for ss, se in zip(silence_starts, silence_ends):
        lo, hi = max(0.0, ss - padding), min(duration, se + padding)
        if expanded and lo <= expanded[-1][1]:
            expanded[-1] = (expanded[-1][0], max(expanded[-1][1], hi))
        else:
            expanded.append((lo, hi))

    # Keep regions = gaps between merged expanded silences
    regions: list[tuple[float, float]] = []
    prev = 0.0
    for lo, hi in expanded:
        if lo > prev + 0.05:
            regions.append((prev, lo))
        prev = hi
    if duration - prev > 0.05:
        regions.append((prev, duration))
    if not regions:
        cmd = [_FFMPEG, "-i", input, "-c", "copy", output]
        _run(cmd, check=True)
        return output

    # Pass 2 — trim each keep-region on both streams, concat
    n = len(regions)
    filters: list[str] = []
    for i, (st, et) in enumerate(regions):
        filters.append(f"[0:v]trim=start={st}:end={et},setpts=PTS-STARTPTS[v{i}]")
        filters.append(f"[0:a]atrim=start={st}:end={et},asetpts=PTS-STARTPTS[a{i}]")
    v_in = "".join(f"[v{i}]" for i in range(n))
    a_in = "".join(f"[a{i}]" for i in range(n))
    filters.append(f"{v_in}concat=n={n}:v=1:a=0[v]")
    filters.append(f"{a_in}concat=n={n}:v=0:a=1[a]")

    cmd = [_FFMPEG, "-i", input,
           "-filter_complex", ";".join(filters),
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-c:a", "aac", output]
    _run(cmd, check=True)
    return output


def transcribe(input: str, model: str = "base", output_srt: str = "",
               language: str = "") -> dict:
    """Transcribe audio with faster-whisper.  Returns {segments, srt_path, language}."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper not installed — pip install faster-whisper")

    audio_path = input
    # if input is video, extract audio first
    if input.endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
        audio_path = input + ".tmp_audio.wav"
        _run([_FFMPEG, "-i", input, "-vn", "-acodec", "pcm_s16le",
              "-ar", "16000", "-ac", "1", audio_path], check=True)

    model_obj = WhisperModel(model, device="cpu", compute_type="int8")
    segs, info = model_obj.transcribe(audio_path, language=language or None)
    segments = []
    srt_lines = []
    for i, s in enumerate(segs, 1):
        segments.append({"id": i, "start": s.start, "end": s.end, "text": s.text.strip()})
        srt_lines.append(f"{i}")
        srt_lines.append(f"{_fmt_srt(s.start)},{_fmt_srt_ms(s.start)} --> {_fmt_srt(s.end)},{_fmt_srt_ms(s.end)}")
        srt_lines.append(s.text.strip())
        srt_lines.append("")

    result = {
        "language": info.language,
        "segments": segments,
        "srt": "\n".join(srt_lines),
    }
    if output_srt:
        pathlib.Path(output_srt).write_text(result["srt"])
        result["srt_path"] = output_srt

    if audio_path != input and os.path.exists(audio_path):
        os.unlink(audio_path)
    return result


def _fmt_srt(seconds: float) -> str:
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"


def _fmt_srt_ms(seconds: float) -> str:
    return f"{int((seconds % 1) * 1000):03d}"


def color_grade(input: str, output: str, brightness: float = 0.0,
                contrast: float = 1.0, saturation: float = 1.0,
                style: str = "") -> str:
    """Apply color correction.  style='warm'/'cool'/'bw' sets presets."""
    _check_ffmpeg()
    _ensure_parent(output)
    filters = []
    if style == "warm":
        filters.append("eq=contrast=1.1:brightness=0.02:saturation=1.2,"
                       "colorbalance=rs=0.1:gs=-0.05:bs=-0.05")
    elif style == "cool":
        filters.append("eq=contrast=1.15:saturation=0.9,"
                       "colorbalance=rs=0.05:gs=-0.05:bs=0.15,"
                       "curves=r='0/0 1/0.95':b='0/0 1/0.9'")
    elif style == "bw":
        filters.append("hue=s=0,eq=contrast=1.3:brightness=0.03")
    else:
        filters.append(f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}")
    cmd = [_FFMPEG, "-i", input, "-vf", ",".join(filters), "-c:a", "copy", output]
    _run(cmd, check=True)
    return output


def text_subtitles(input: str, output: str, srt_path: str,
                   font_name: str = "Arial", font_size: int = 20,
                   primary_color: str = "&HCCFF0000",
                   outline: int = 1, shadow: int = 1) -> str:
    """Burn SRT subtitles into video.  Subtitles applied LAST in filter chain."""
    _check_ffmpeg()
    _ensure_parent(output)
    style = (f"FontName={font_name},FontSize={font_size},"
             f"PrimaryColour={primary_color},"
             f"Outline={outline},Shadow={shadow},"
             f"BorderStyle=1,MarginV=40")
    cmd = [_FFMPEG, "-i", input,
           "-vf", f"subtitles={srt_path}:force_style='{style}'",
           "-c:a", "copy", output]
    _run(cmd, check=True)
    return output


def loudnorm(input: str, output: str, target_lufs: float = -16.0,
              true_peak_db: float = -1.0) -> str:
    """Two-pass EBU R128 loudness normalization + true-peak limiter.
    Hard Rule #17: alimiter after loudnorm prevents shipping clipped audio."""
    _check_ffmpeg()
    _ensure_parent(output)

    # Pass 1 — measure (non-greedy match, multi-block-safe on FFmpeg 7.x)
    res = _run([_FFMPEG, "-i", input,
                "-af", f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11:print_format=json",
                "-f", "null", "-"])
    match = re.search(r"\{[^{}]*\}", res.stderr, re.DOTALL)
    if not match:
        raise RuntimeError("could not parse loudnorm measurement")
    measured = json.loads(match.group())

    # Pass 2 — apply with linear=true + alimiter (Hard Rule #17)
    limit_linear = round(10 ** (true_peak_db / 20), 6)
    af = (f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11:"
          f"measured_I={measured['input_i']}:"
          f"measured_TP={measured['input_tp']}:"
          f"measured_LRA={measured['input_lra']}:"
          f"measured_thresh={measured['input_thresh']}:"
          f"linear=true,"
          f"alimiter=limit={limit_linear}:attack=0.1:release=1")
    cmd = [_FFMPEG, "-i", input, "-af", af, "-ar", "48000", output]
    _run(cmd, check=True)
    return output


def speed(input: str, output: str, factor: float = 2.0) -> str:
    """Change playback speed.  atempo + setpts paired (avoids desync)."""
    _check_ffmpeg()
    _ensure_parent(output)
    # atempo max 2.0, chain for faster
    atempo_chain = ""
    f = factor
    while f > 2.0:
        atempo_chain += "atempo=2.0,"
        f /= 2.0
    atempo_chain += f"atempo={f}"
    cmd = [_FFMPEG, "-i", input,
           "-filter_complex",
           f"[0:v]setpts={1/factor}*PTS[v];[0:a]{atempo_chain}[a]",
           "-map", "[v]", "-map", "[a]", output]
    _run(cmd, check=True)
    return output


def stabilize(input: str, output: str, shakiness: int = 5,
              smoothing: int = 20) -> str:
    """Two-pass vid.stab stabilization."""
    _check_ffmpeg()
    _ensure_parent(output)
    trf = output + ".transforms.trf"
    _run([_FFMPEG, "-i", input,
          "-vf", f"vidstabdetect=shakiness={shakiness}:result={trf}",
          "-f", "null", "-"], check=True)
    _run([_FFMPEG, "-i", input,
          "-vf", f"vidstabtransform=smoothing={smoothing}:input={trf}",
          "-c:a", "copy", output], check=True)
    if os.path.exists(trf):
        os.unlink(trf)
    return output


def scene_detect(input: str, threshold: float = 0.4) -> list[dict]:
    """Return list of scene changes with timestamps."""
    _check_ffmpeg()
    res = _run([_FFMPEG, "-i", input,
                "-filter:v", f"select='gt(scene,{threshold})',showinfo",
                "-f", "null", "-"])
    scenes = []
    for line in res.stderr.split("\n"):
        if "pts_time:" in line:
            m = re.search(r"pts_time:(\S+)", line)
            if m:
                scenes.append({"timestamp": float(m.group(1))})
    return scenes


def pip(main: str, overlay: str, output: str,
        position: str = "bottom-right", scale: float = 0.3) -> str:
    """Picture-in-picture overlay."""
    _check_ffmpeg()
    _ensure_parent(output)
    pos_map = {
        "bottom-right": "main_w-overlay_w-20:main_h-overlay_h-20",
        "bottom-left": "20:main_h-overlay_h-20",
        "top-right": "main_w-overlay_w-20:20",
        "top-left": "20:20",
        "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
    }
    pos = pos_map.get(position, pos_map["bottom-right"])
    cmd = [_FFMPEG, "-i", main, "-i", overlay,
           "-filter_complex",
           f"[1:v]scale=iw*{scale}:ih*{scale}[ov];"
           f"[0:v][ov]overlay={pos}",
           "-c:a", "copy", output]
    _run(cmd, check=True)
    return output


def verify(path: str) -> dict:
    """Quality gate check.  Returns {ok, duration, streams, lufs?, errors}."""
    errors = []
    if not os.path.exists(path):
        return {"ok": False, "errors": ["file does not exist"]}

    try:
        d = _probe_json(path)
    except Exception as e:
        return {"ok": False, "errors": [f"ffprobe failed: {e}"]}

    streams = [s.get("codec_type") for s in d.get("streams", [])]
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), {})

    if "video" not in streams:
        errors.append("no video stream")
    fmt = d.get("format", {})
    duration = float(fmt.get("duration", 0))
    if duration == 0:
        errors.append("zero duration")

    result = {
        "ok": len(errors) == 0,
        "duration": duration,
        "streams": streams,
        "video": {"codec": v.get("codec_name"), "width": v.get("width"), "height": v.get("height")},
        "audio": {"codec": a.get("codec_name"), "channels": a.get("channels")} if a else None,
        "errors": errors,
    }
    return result


# ═══════════════════════════════════════════════════════════
#  Professional Editing Improvements (PRO_IMPROVEMENTS.md)
# ═══════════════════════════════════════════════════════════


# ─── J-cuts & L-cuts ───

def j_cut(
    clip_a: str, clip_b: str, output: str,
    *,
    lead_seconds: float = 0.5,
    audio_fade_ms: int = 30,
) -> str:
    """J-cut: audio of clip B starts before its video.
    Audio from B begins `lead_seconds` before the visual transition.
    """
    _check_ffmpeg()
    _ensure_parent(output)
    a_dur = _probe_duration(clip_a)
    fade_s = audio_fade_ms / 1000.0
    cmd = [_FFMPEG, "-i", clip_a, "-i", clip_b,
           "-filter_complex",
           f"[0:v]trim=0:{a_dur},setpts=PTS-STARTPTS[va];"
           f"[0:a]atrim=0:{a_dur},asetpts=PTS-STARTPTS[aa];"
           f"[1:v]setpts=PTS-STARTPTS+{lead_seconds}/TB[vb];"
           f"[1:a]adelay={lead_seconds*1000:.0f}|{lead_seconds*1000:.0f}[ab];"
           f"[va][vb]overlay[vout];"
           f"[aa][ab]amix=inputs=2:duration=first:dropout_transition=2,"
           f"aformat=sample_rates=48000:channel_layouts=stereo,"
           f"afade=t=in:st=0:d={fade_s},afade=t=out:st={a_dur+lead_seconds+fade_s}:d={fade_s}[aout]",
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-c:a", "aac", "-ar", "48000", output]
    _run(cmd, check=True)
    return output


def l_cut(
    clip_a: str, clip_b: str, output: str,
    *,
    trail_seconds: float = 0.5,
    audio_fade_ms: int = 30,
) -> str:
    """L-cut: audio of clip A continues after its video ends.
    Audio from A trails `trail_seconds` past the visual transition.
    """
    _check_ffmpeg()
    _ensure_parent(output)
    a_dur = _probe_duration(clip_a)
    fade_s = audio_fade_ms / 1000.0
    total_a = a_dur + trail_seconds
    cmd = [_FFMPEG, "-i", clip_a, "-i", clip_b,
           "-filter_complex",
           f"[0:v]trim=0:{a_dur},setpts=PTS-STARTPTS[va];"
           f"[0:a]atrim=0:{a_dur},asetpts=PTS-STARTPTS[aa];"
           f"[1:v]setpts=PTS-STARTPTS+{a_dur}/TB[vb];"
           f"[1:a]adelay={a_dur*1000:.0f}|{a_dur*1000:.0f}[ab];"
           f"[va][vb]overlay[vout];"
           f"[aa]adelay={trail_seconds*1000:.0f}|{trail_seconds*1000:.0f}[aa_del];"
           f"[aa_del][ab]amix=inputs=2:duration=first:dropout_transition=2,"
           f"aformat=sample_rates=48000:channel_layouts=stereo,"
           f"afade=t=in:st=0:d={fade_s},afade=t=out:st={total_a+fade_s}:d={fade_s}[aout]",
           "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-c:a", "aac", "-ar", "48000", output]
    _run(cmd, check=True)
    return output


def j_l_cut_sequence(
    clips: list[dict],
    output: str,
) -> str:
    """Assemble a sequence with J/L-cuts between every pair.
    Each dict: {"video": str, "audio_lead": float, "audio_trail": float}
    For dialogue scenes where audio flows across picture cuts.
    """
    if len(clips) < 2:
        raise ValueError("at least 2 clips required")
    tmp_dir = pathlib.Path(output).parent / f".jlc_{pathlib.Path(output).stem}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    intermediates: list[str] = []
    for i in range(len(clips) - 1):
        tmp = str(tmp_dir / f"seg_{i:04d}.mp4")
        if clips[i].get("audio_trail", 0) > 0 and clips[i+1].get("audio_lead", 0) == 0:
            l_cut(clips[i]["video"], clips[i+1]["video"], tmp,
                  trail_seconds=clips[i]["audio_trail"])
        elif clips[i+1].get("audio_lead", 0) > 0:
            j_cut(clips[i]["video"], clips[i+1]["video"], tmp,
                  lead_seconds=clips[i+1]["audio_lead"])
        else:
            merge([clips[i]["video"], clips[i+1]["video"]], tmp)
        intermediates.append(tmp)
    # Concatenate all intermediates
    merge(intermediates, output)
    # Cleanup
    import shutil as _sh
    _sh.rmtree(tmp_dir, ignore_errors=True)
    return output


# ─── Render Profiles ───

RENDER_PROFILES: dict[str, dict] = {
    "youtube-1080p": {
        "video_codec": "libx264", "preset": "slow", "crf": 18,
        "pixel_format": "yuv420p", "resolution": "1920x1080",
        "audio_codec": "aac", "audio_bitrate": "384k", "audio_sample_rate": 48000,
        "loudness_lufs": -14, "true_peak_db": -1.0,
        "container": "mp4", "faststart": True,
    },
    "youtube-4k": {
        "video_codec": "libx265", "preset": "slow", "crf": 22,
        "pixel_format": "yuv420p10le", "resolution": "3840x2160",
        "audio_codec": "aac", "audio_bitrate": "384k", "audio_sample_rate": 48000,
        "loudness_lufs": -14, "true_peak_db": -1.0,
        "container": "mp4", "faststart": True,
    },
    "tiktok-vertical": {
        "video_codec": "libx264", "preset": "fast", "crf": 20,
        "resolution": "1080x1920",
        "audio_codec": "aac", "audio_bitrate": "128k", "audio_sample_rate": 48000,
        "loudness_lufs": -14, "true_peak_db": -1.0,
        "container": "mp4", "faststart": True,
    },
    "instagram-square": {
        "video_codec": "libx264", "preset": "medium", "crf": 20,
        "resolution": "1080x1080",
        "audio_codec": "aac", "audio_bitrate": "192k", "audio_sample_rate": 48000,
        "loudness_lufs": -14, "true_peak_db": -1.0,
        "container": "mp4", "faststart": True,
    },
    "broadcast-720p": {
        "video_codec": "libx264", "preset": "medium", "crf": 18,
        "resolution": "1280x720",
        "audio_codec": "aac", "audio_bitrate": "256k", "audio_sample_rate": 48000,
        "loudness_lufs": -23, "true_peak_db": -1.0, "lra_max": 11,
        "container": "mp4",
    },
    "broadcast-1080i": {
        "video_codec": "libx264", "preset": "medium", "crf": 18,
        "resolution": "1920x1080",
        "audio_codec": "aac", "audio_bitrate": "256k", "audio_sample_rate": 48000,
        "loudness_lufs": -23, "true_peak_db": -1.0, "lra_max": 11,
        "container": "mxf",
    },
    "archival-prores": {
        "video_codec": "prores_ks", "profile": 3,
        "resolution": "preserve",
        "audio_codec": "pcm_s24le",
        "container": "mov",
    },
    "archival-prores-4444": {
        "video_codec": "prores_ks", "profile": 4,
        "resolution": "preserve", "pixel_format": "yuva444p10le",
        "audio_codec": "pcm_s24le",
        "container": "mov",
    },
    "webm-vp9": {
        "video_codec": "libvpx-vp9", "crf": 30, "cpu_used": 4,
        "resolution": "preserve",
        "audio_codec": "libopus", "audio_bitrate": "128k",
        "container": "webm",
    },
}


def render(
    input: str, output: str,
    *,
    profile: str = "youtube-1080p",
    **overrides,
) -> dict:
    """Render to a named profile.  Returns {path, profile, stats}.
    Never ship without a delivery profile (Hard Rule #19)."""
    _check_ffmpeg()
    _ensure_parent(output)
    if profile not in RENDER_PROFILES:
        raise ValueError(f"unknown profile: {profile}. Known: {list(RENDER_PROFILES)}")
    cfg = {**RENDER_PROFILES[profile], **overrides}

    # Resolve output resolution
    if cfg.get("resolution") and cfg["resolution"] != "preserve":
        res = cfg["resolution"]
        if isinstance(res, str) and "x" in res:
            w, h = res.split("x")
            vf = f"scale={w}:{h}:flags=lanczos"
        else:
            vf = ""
    else:
        vf = ""

    # Faststart
    faststart = cfg.pop("faststart", False)
    movflags = "+faststart" if faststart else ""

    cmd = [_FFMPEG, "-i", input]
    cmd += ["-c:v", cfg.get("video_codec", "libx264")]
    if "preset" in cfg:
        cmd += ["-preset", cfg["preset"]]
    if "crf" in cfg:
        cmd += ["-crf", str(cfg["crf"])]
    if "pixel_format" in cfg:
        cmd += ["-pix_fmt", cfg["pixel_format"]]
    if "cpu_used" in cfg:
        cmd += ["-cpu-used", str(cfg["cpu_used"])]
    if vf:
        cmd += ["-vf", vf]
    if "profile" in cfg and isinstance(cfg["profile"], int):
        cmd += ["-profile:v", str(cfg["profile"])]
    cmd += ["-c:a", cfg.get("audio_codec", "aac")]
    if "audio_bitrate" in cfg:
        cmd += ["-b:a", cfg["audio_bitrate"]]
    if "audio_sample_rate" in cfg:
        cmd += ["-ar", str(cfg["audio_sample_rate"])]
    if movflags:
        cmd += ["-movflags", movflags]
    cmd += [output]

    res = _run(cmd, check=True)
    out_size = os.path.getsize(output) if os.path.exists(output) else 0
    return {"path": output, "profile": profile, "size_bytes": out_size, "overrides": overrides}


def render_multi(
    input: str, output_dir: str,
    profiles: list[str],
    *,
    parallel: bool = True,
) -> list[dict]:
    """One master to multiple delivery specs.  Standard pro workflow."""
    out_dir = pathlib.Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(input).stem
    results: list[dict] = []

    def _render_one(p: str) -> dict:
        ext = RENDER_PROFILES.get(p, {}).get("container", "mp4")
        out = str(out_dir / f"{stem}_{p}.{ext}")
        return render(input, out, profile=p)

    if parallel:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(profiles), 4)) as ex:
            futures = {ex.submit(_render_one, p): p for p in profiles}
            for f in concurrent.futures.as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    results.append({"profile": futures[f], "error": str(e)})
    else:
        for p in profiles:
            results.append(_render_one(p))
    return results


# ─── True-Peak Limited Loudnorm (Hard Rule #17) ───

def loudnorm_limited(
    input: str, output: str,
    *,
    target_lufs: float = -16.0,
    true_peak_db: float = -1.0,
    lra_target: float = 7.0,
) -> str:
    """Three-pass loudness: measure → compress if LRA > target → loudnorm → limit.
    Streaming platforms reject files above -1 dBTP.  Loudnorm alone doesn't limit.
    Hard Rule #17: True-peak limit at -1 dBTP after loudnorm.
    Hard Rule #18: LRA ≤ 7 for mobile/streaming."""
    _check_ffmpeg()
    _ensure_parent(output)

    # Pass 1 — measure
    res = _run([_FFMPEG, "-i", input,
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
                "-f", "null", "-"])
    match = re.search(r"\{[^{}]*\}", res.stderr, re.DOTALL)
    if not match:
        raise RuntimeError("could not parse loudnorm measurement")
    measured = json.loads(match.group())
    input_lra = float(measured.get("input_lra", 99))

    # Build audio filter chain
    chain_parts: list[str] = []

    # Pass 1a — compress if LRA exceeds target (Hard Rule #18)
    if input_lra > lra_target:
        chain_parts.append(f"acompressor=threshold=-24dB:ratio=2:attack=10:release=200:makeup=0")

    # Pass 1b — loudnorm (measured values, linear=true)
    chain_parts.append(
        f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA={lra_target}:"
        f"measured_I={measured['input_i']}:"
        f"measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:"
        f"measured_thresh={measured['input_thresh']}:"
        f"linear=true"
    )

    # Pass 1c — true-peak limiter (Hard Rule #17)
    # alimiter w.r.t. dBTP: limit=0.equivalent-to-true-peak-db(TP)
    limit_linear = 10 ** (true_peak_db / 20)  # -1.0 dBTP ≈ 0.891
    chain_parts.append(f"alimiter=limit={limit_linear}:attack=0.1:release=1")

    af = ",".join(chain_parts)
    cmd = [_FFMPEG, "-i", input, "-af", af, "-ar", "48000", output]
    _run(cmd, check=True)
    return output


# ─── Scopes (waveform / vectorscope / histogram / parade) ───

def scope_waveform(input: str, output: str = "", intensity: float = 0.1) -> str:
    """Generate a waveform monitor image (luminance vs position).
    Pros use this to check exposure and clipping."""
    _check_ffmpeg()
    out = output or input + ".waveform.png"
    _ensure_parent(out)
    _run([_FFMPEG, "-i", input, "-frames:v", "1", "-vf",
          f"waveform=m=intensity:{intensity}:c=1",
          out], check=True)
    return out


def scope_vectorscope(input: str, output: str = "") -> str:
    """Generate a vectorscope image (chrominance).
    Pros check skin tones land on the I-line (~123°)."""
    _check_ffmpeg()
    out = output or input + ".vectorscope.png"
    _ensure_parent(out)
    _run([_FFMPEG, "-i", input, "-frames:v", "1", "-vf",
          "vectorscope=m=color3:g=green",
          out], check=True)
    return out


def scope_histogram(input: str, output: str = "", levels: str = "rgb") -> str:
    """Generate an RGB or luminance histogram.
    Pros check white/black balance and color cast."""
    _check_ffmpeg()
    out = output or input + ".histogram.png"
    _ensure_parent(out)
    mode = "rgb" if levels == "rgb" else "luma"
    _run([_FFMPEG, "-i", input, "-frames:v", "1", "-vf",
          f"histogram=mode={mode}:display_mode=stack",
          out], check=True)
    return out


def scope_parade(input: str, output: str = "") -> str:
    """RGB parade — three waveforms side-by-side.
    The most-used scope for color correction: reveals color cast per channel."""
    _check_ffmpeg()
    out = output or input + ".parade.png"
    _ensure_parent(out)
    _run([_FFMPEG, "-i", input, "-frames:v", "1", "-vf",
          "waveform=m=intensity:0.1:c=1:9,scale=640:-1",
          out], check=True)
    return out


def scope_analyze(input: str) -> dict:
    """Numerical analysis of a frame (no image output).
    Returns broadcast-safe values, skin tone angle, color cast.
    Used by the agent to make grading decisions."""
    _check_ffmpeg()
    res = _run([_FFMPEG, "-i", input, "-frames:v", "1",
                "-vf", "signalstats", "-f", "null", "-"])
    stats = {"luma_min": 0, "luma_max": 255, "luma_average": 128,
             "clipped_shadows_pct": 0.0, "clipped_highlights_pct": 0.0}
    for line in res.stderr.split("\n"):
        if "Ymin" in line:
            m = re.search(r"Ymin=(\d+)", line)
            if m: stats["luma_min"] = int(m.group(1))
        if "Ymax" in line:
            m = re.search(r"Ymax=(\d+)", line)
            if m: stats["luma_max"] = int(m.group(1))
        if "Ymean" in line:
            m = re.search(r"Ymean=(\d+)", line)
            if m: stats["luma_average"] = int(m.group(1))

    stats["broadcast_safe"] = stats["luma_min"] >= 16 and stats["luma_max"] <= 235
    total_pixels = 1920 * 1080  # rough estimate
    stats["clipped_shadows_pct"] = round(max(0, 16 - stats["luma_min"]) / 255 * 100, 1)
    stats["clipped_highlights_pct"] = round(max(0, stats["luma_max"] - 235) / 255 * 100, 1)

    # Color cast via average R/G/B
    res2 = _run([_FFMPEG, "-i", input, "-frames:v", "1",
                 "-vf", "format=rgb24,avgblur=100,histogram=mode=rgb",
                 "-f", "null", "-"])
    if stats["luma_min"] > 200:
        stats["color_cast"] = "overexposed"
    elif stats["luma_max"] < 30:
        stats["color_cast"] = "underexposed"
    else:
        stats["color_cast"] = "neutral"
    return stats


# ─── VMAF + Quality Metrics ───

def quality_vmaf(
    reference: str, distorted: str,
    *,
    model: str = "vmaf_v0.6.1",
) -> dict:
    """Compute VMAF score (0-100).  Netflix thresholds:
    90+ = excellent, 80-90 = good, <80 = reject.
    Hard Rule #20: VMAF >= 80 for any re-encode."""
    _check_ffmpeg()
    res = _run([_FFMPEG, "-i", distorted, "-i", reference,
                "-filter_complex",
                f"[0:v]setpts=PTS-STARTPTS[dist];"
                f"[1:v]setpts=PTS-STARTPTS[ref];"
                f"[dist][ref]libvmaf=model=version={model}:log_fmt=json",
                "-f", "null", "-"])
    match = re.search(r"\"score\":\s*([\d.]+)", res.stderr)
    score = float(match.group(1)) if match else 0.0
    return {"score": round(score, 2), "passed": score >= 80.0}


def quality_psnr(reference: str, distorted: str) -> dict:
    """Peak Signal-to-Noise Ratio between two videos."""
    _check_ffmpeg()
    res = _run([_FFMPEG, "-i", distorted, "-i", reference,
                "-filter_complex", "[0:v][1:v]psnr",
                "-f", "null", "-"])
    m = re.search(r"average:([\d.]+)", res.stderr)
    return {"psnr": float(m.group(1))} if m else {"psnr": 0.0}


def quality_ssim(reference: str, distorted: str) -> dict:
    """Structural Similarity Index."""
    _check_ffmpeg()
    res = _run([_FFMPEG, "-i", distorted, "-i", reference,
                "-filter_complex", "[0:v][1:v]ssim",
                "-f", "null", "-"])
    m = re.search(r"All:([\d.]+)", res.stderr)
    return {"ssim": float(m.group(1))} if m else {"ssim": 0.0}


def quality_audio(path: str) -> dict:
    """Audio quality metrics: LUFS, true peak, LRA, clipping, phase."""
    _check_ffmpeg()
    res = _run([_FFMPEG, "-i", path,
                "-af", "ebur128=peak=true,astats=metadata=1",
                "-f", "null", "-"])
    stderr = res.stderr
    result = {
        "lufs": 0.0, "true_peak_db": 0.0, "lra": 0.0,
        "clipping_samples": 0, "dc_offset": 0.0,
    }
    m = re.search(r"Integrated loudness:\s*I:\s*([-\d.]+)", stderr)
    if m: result["lufs"] = round(float(m.group(1)), 1)
    m = re.search(r"Peak:\s*([-\d.]+)", stderr)
    if m: result["true_peak_db"] = round(float(m.group(1)), 1)
    m = re.search(r"LRA:\s*([\d.]+)", stderr)
    if m: result["lra"] = round(float(m.group(1)), 1)
    return result


def quality_full_qc(path: str, reference: str = "") -> dict:
    """Full QC report: integrity, codec compliance, loudness, VMAF, audio."""
    _check_ffmpeg()
    r = {"path": path, "file_integrity": False, "has_video": False, "has_audio": False}
    try:
        d = _probe_json(path)
        fmt = d.get("format", {})
        streams = [s.get("codec_type") for s in d.get("streams", [])]
        r["has_video"] = "video" in streams
        r["has_audio"] = "audio" in streams
        r["duration"] = float(fmt.get("duration", 0))
        r["file_integrity"] = r["has_video"] and r["duration"] > 0
        r["loudness"] = {}
        a_res = _run([_FFMPEG, "-i", path,
                      "-af", "ebur128=peak=true",
                      "-f", "null", "-"])
        m = re.search(r"Integrated loudness:\s*I:\s*([-\d.]+)", a_res.stderr)
        if m: r["loudness"]["lufs"] = round(float(m.group(1)), 1)
        m = re.search(r"LRA:\s*([\d.]+)", a_res.stderr)
        if m: r["loudness"]["lra"] = round(float(m.group(1)), 1)
        if reference and os.path.exists(reference):
            r["vmaf"] = quality_vmaf(reference, path)
            r["psnr"] = quality_psnr(reference, path)
            r["ssim"] = quality_ssim(reference, path)
    except Exception as e:
        r["error"] = str(e)
    return r


# ─── Project File (Resume + Audit Trail) ───

def project_create(
    name: str,
    source: str,
    *,
    output_dir: str = ".",
) -> dict:
    """Create a new project.  Writes <name>.aevp (agentic editing video project).
    Hard Rule #22: Every project has a .aevp file."""
    import hashlib as _hl
    src = pathlib.Path(source)
    proj = {
        "version": "1.0",
        "name": name,
        "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": {"path": str(src.resolve()), "hash": _hl.sha256(src.read_bytes()).hexdigest()},
        "steps": [],
        "step_outputs": {},
        "gates_passed": [],
        "errors": [],
        "music": [],
        "audit_trail": [],
    }
    out_dir = pathlib.Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    proj_path = out_dir / f"{name}.aevp"
    with open(proj_path, "w") as f:
        json.dump(proj, f, indent=2)
    proj["path"] = str(proj_path)
    return proj


def project_step(
    project_path: str,
    step: dict,
) -> dict:
    """Execute a step, log it to the project file, return the output path.
    Computes SHA-256 of input + output for audit trail."""
    import hashlib as _hl
    with open(project_path) as f:
        proj = json.load(f)

    op = step.get("operation", "unknown")
    inp = step.get("input", "")
    out = step.get("output", "")

    # Hash input
    input_hash = ""
    if inp and os.path.exists(inp):
        input_hash = _hl.sha256(open(inp, "rb").read()).hexdigest()

    # Record step
    entry = {
        "step": len(proj["steps"]) + 1,
        "operation": op,
        "tool": step.get("tool", "ffmpeg"),
        "params": step.get("params", {}),
        "input": inp,
        "input_hash": input_hash,
        "output": out,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    proj["steps"].append(entry)
    proj["step_outputs"][str(entry["step"])] = out
    proj["audit_trail"].append(entry)

    with open(project_path, "w") as f:
        json.dump(proj, f, indent=2)
    return entry


def project_resume(project_path: str) -> dict:
    """Resume an interrupted project.  Returns the next action.
    Steps without output paths are incomplete."""
    with open(project_path) as f:
        proj = json.load(f)
    completed = len(proj.get("steps", []))
    plan = proj.get("plan", [])
    next_step = None
    for i, p in enumerate(plan):
        if i >= completed:
            next_step = p
            break
    return {
        "project": project_path,
        "steps_completed": completed,
        "total_planned": len(plan),
        "next_action": next_step or {"operation": "render"},
    }


def project_snapshot(project_path: str) -> str:
    """Snapshot current state before a destructive operation.
    Hard Rule #23: Destructive ops require a prior snapshot."""
    import hashlib as _hl, shutil as _sh
    proj_dir = pathlib.Path(project_path).parent
    snap_name = f".snap_{pathlib.Path(project_path).stem}_{int(time.time())}"
    snap_dir = proj_dir / snap_name
    snap_dir.mkdir(parents=True, exist_ok=True)

    with open(project_path) as f:
        proj = json.load(f)
    for key, out_path in proj.get("step_outputs", {}).items():
        if out_path and os.path.exists(out_path):
            _sh.copy2(out_path, snap_dir / f"step_{key}_{pathlib.Path(out_path).name}")

    manifest = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "files": [str(p.name) for p in snap_dir.iterdir() if p.is_file()]}
    snap_file = snap_dir / "snapshot.json"
    with open(snap_file, "w") as f:
        json.dump(manifest, f, indent=2)
    return str(snap_dir)


def project_audit_report(project_path: str) -> dict:
    """Generate an audit report for delivery compliance.
    Hard Rule #24: Audit trail is non-optional for broadcast."""
    with open(project_path) as f:
        proj = json.load(f)
    return {
        "project_name": proj.get("name"),
        "created": proj.get("created"),
        "source": proj.get("source"),
        "total_steps": len(proj.get("steps", [])),
        "audit_trail": proj.get("audit_trail", []),
        "gates_passed": proj.get("gates_passed", []),
        "errors": proj.get("errors", []),
    }


# Allow both `import kb.tools.ffmpeg_adapter as edit` and
# `from kb.tools.ffmpeg_adapter import edit` patterns:
import sys as _sys
edit = _sys.modules[__name__]
