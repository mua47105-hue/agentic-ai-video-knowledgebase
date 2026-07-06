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
import json, os, pathlib, re, shutil, subprocess, tempfile, typing as t

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
        "fps": eval(v.get("r_frame_rate", "0/1")) if "/" in v.get("r_frame_rate", "") else 0,
        "video_codec": v.get("codec_name"),
        "audio_codec": a.get("codec_name"),
        "has_audio": "audio" in [s.get("codec_type") for s in d.get("streams", [])],
        "size_bytes": int(fmt.get("size", 0)),
        "bitrate": int(fmt.get("bit_rate", 0)),
    }


def trim(input: str, output: str, start: str = "", end: str = "",
         duration: str = "", accurate: bool = True) -> str:
    """Cut a segment.  accurate=True re-encodes (frame-accurate)."""
    _check_ffmpeg()
    _ensure_parent(output)
    cmd = [_FFMPEG, "-i", input]
    if start:
        cmd += ["-ss", start]
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
    # Build filter_complex for n-1 xfades between n clips
    n = len(inputs)
    seg_dur = 5  # take first 5s of each clip (or trim to shortest)
    filters = []
    for i, inp in enumerate(inputs):
        filters.append(f"[{i}:v]trim=0:{seg_dur},setpts=PTS-STARTPTS[v{i}]")
        filters.append(f"[{i}:a]atrim=0:{seg_dur},asetpts=PTS-STARTPTS[a{i}]")
    # chain xfades
    offset = seg_dur - dur
    for i in range(n - 1):
        vi, vj = f"v{i}", f"v{i+1}"
        ai, aj = f"a{i}", f"a{i+1}"
        if i == 0:
            filters.append(f"[{vi}][{vj}]xfade=offset={offset}:duration={dur}:transition={transition}[vout{i}]")
            filters.append(f"[{ai}][{aj}]acrossfade=d={dur}[aout{i}]")
        else:
            filters.append(f"[vout{i-1}][{vj}]xfade=offset={offset*(i+1)}:duration={dur}:transition={transition}[vout{i}]")
            filters.append(f"[aout{i-1}][{aj}]acrossfade=d={dur}[aout{i}]")
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
    """Remove silent sections.  Keeps `padding` seconds around speech."""
    _check_ffmpeg()
    _ensure_parent(output)
    cmd = [_FFMPEG, "-i", input,
           "-af", (f"silenceremove=start_periods=1:start_duration=1:"
                   f"start_threshold={threshold}dB:"
                   f"stop_periods=-1:stop_duration={min_silence}:"
                   f"stop_threshold={threshold}dB:"
                   f"leave_silence={padding},"
                   f"afade=t=in:st=0:d=0.03"),
           "-c:v", "copy", output]
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


def loudnorm(input: str, output: str, target_lufs: float = -16.0) -> str:
    """Two-pass EBU R128 loudness normalization.  Never single-pass."""
    _check_ffmpeg()
    _ensure_parent(output)

    # Pass 1 — measure
    res = _run([_FFMPEG, "-i", input,
                "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:print_format=json",
                "-f", "null", "-"])
    match = re.search(r"\{.*\}", res.stderr, re.DOTALL)
    if not match:
        raise RuntimeError("could not parse loudnorm measurement")
    measured = json.loads(match.group())

    # Pass 2 — apply with linear=true + explicit sample rate
    cmd = [_FFMPEG, "-i", input,
           "-af", (f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11:"
                   f"measured_I={measured['input_i']}:"
                   f"measured_TP={measured['input_tp']}:"
                   f"measured_LRA={measured['input_lra']}:"
                   f"measured_thresh={measured['input_thresh']}:"
                   f"linear=true"),
           "-ar", "48000", output]
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


# Allow both `import kb.tools.ffmpeg_adapter as edit` and
# `from kb.tools.ffmpeg_adapter import edit` patterns:
import sys as _sys
edit = _sys.modules[__name__]
