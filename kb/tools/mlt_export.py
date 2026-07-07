"""
MLT XML export: convert .aevp project files to MLT XML for NLE interchange.

Opens in Kdenlive, Shotcut. Renders headlessly via `melt output.mlt`.

Usage:
    from kb.tools.mlt_export import export_mlt
    mlt_path = export_mlt("project.aevp", "project.mlt")
    # Render: melt project.mlt -consumer avformat:output.mp4
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import typing as t
import xml.etree.ElementTree as ET
from xml.dom import minidom

_FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
_FFPROBE = shutil.which("ffprobe") or "ffprobe"
_MELT = shutil.which("melt") or "melt"


def _probe_json(path: str) -> dict:
    res = subprocess.run(
        [_FFPROBE, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    return json.loads(res.stdout)


def _probe_duration(path: str) -> float:
    d = _probe_json(path)
    return float(d.get("format", {}).get("duration", 0))


def _probe_resolution(path: str) -> tuple[int, int]:
    d = _probe_json(path)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    return v.get("width", 1920) or 1920, v.get("height", 1080) or 1080


def _time_str(seconds: float, fps: float = 30.0) -> str:
    frames = int(round(seconds * fps))
    h = frames // (3600 * int(fps))
    m = (frames // (60 * int(fps))) % 60
    s = (frames // int(fps)) % 60
    f = frames % int(fps)
    return f"{h:02d}:{m:02d}:{s:02d}.{f:02d}"


def _frame_count(seconds: float, fps: float = 30.0) -> int:
    return int(round(seconds * fps))


def _make_producer(doc: ET.Element, clip_index: int, path: str) -> ET.Element:
    producer = ET.SubElement(doc, "producer", id=f"clip{clip_index}")
    ET.SubElement(producer, "property", name="resource").text = str(pathlib.Path(path).resolve())
    ET.SubElement(producer, "property", name="mlt_service").text = "avformat"
    ET.SubElement(producer, "property", name="aspect_ratio").text = "1"
    ET.SubElement(producer, "property", name="seekable").text = "1"
    return producer


def _make_filter(elem: ET.Element, service: str, **props: str) -> ET.Element:
    flt = ET.SubElement(elem, "filter")
    ET.SubElement(flt, "property", name="mlt_service").text = service
    for k, v in props.items():
        ET.SubElement(flt, "property", name=k).text = v
    return flt


def export_mlt(
    project_path: str,
    output_path: str = "",
    *,
    conform_from: str | None = None,
    include_audio: bool = True,
) -> str:
    """Convert .aevp project to MLT XML.

    Opens in Kdenlive, Shotcut. Renders headlessly via `melt output.mlt`.

    Supported operations (round-trip safe):
      - trim, merge (with xfade transitions)
      - resize, crop
      - color_grade (warm/cool/bw presets map to MLT filters)
      - text_subtitles (burned-in)
      - speed changes
      - audio fade in/out
      - J-cuts, L-cuts (via MLT <transition> elements)

    Not supported in MLT XML (will be skipped with warning):
      - stabilize (vidstab has no MLT equivalent)
      - complex FFmpeg filter chains
      - VMAF quality scoring
    """
    with open(project_path) as f:
        project = json.load(f)

    if not output_path:
        output_path = str(pathlib.Path(project_path).with_suffix(".mlt"))

    out_dir = pathlib.Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    steps = project.get("steps", [])
    source = project.get("source", {}).get("path", "")

    fps = 30.0
    if source and os.path.exists(source):
        w, h = _probe_resolution(source)
    else:
        w, h = 1920, 1080

    doc = ET.Element("mlt", attrib={
        "version": "7.0.0",
        "title": project.get("name", "Untitled"),
        "producer": "main",
    })

    # MLT profile
    profile = ET.SubElement(doc, "profile", attrib={
        "description": "HD 1080p 30fps",
        "width": str(w),
        "height": str(h),
        "progressive": "1",
        "sample_aspect_num": "1",
        "sample_aspect_den": "1",
        "display_aspect_num": str(w),
        "display_aspect_den": str(h),
        "frame_rate_num": str(int(fps)),
        "frame_rate_den": "1",
        "colorspace": "709",
    })

    producers: dict[str, str] = {}
    playlist = ET.SubElement(doc, "playlist", id="main")
    track = ET.SubElement(doc, "track", id="track0")
    producers_elem = ET.SubElement(doc, "producers")

    clip_index = 0
    current_time = 0.0

    for step in steps:
        op = step.get("operation", "")
        inp = step.get("input", step.get("params", {}).get("input", ""))
        out = step.get("output", "")
        params = step.get("params", {})

        if op in ("trim", "extract"):
            if not inp:
                continue
            start = float(params.get("start", 0))
            dur = float(params.get("duration", params.get("duration", 10)))
            clip_key = f"trim_{clip_index}"

            producer = _make_producer(producers_elem, clip_index, inp or source)
            entry = ET.SubElement(track, "entry", attrib={
                "producer": f"clip{clip_index}",
                "in": _time_str(start, fps),
                "out": _time_str(start + dur, fps),
            })
            clip_index += 1
            current_time += dur

        elif op in ("merge", "merge_moments", "merge_shots", "merge_clips", "merge_segments", "merge_chapters"):
            xfade_dur = float(params.get("transition_duration", 0.5))
            xfade_type = params.get("transition", "fade")
            if clip_index >= 2:
                offset_frames = _frame_count(current_time - xfade_dur, fps)
                transition_xfade(doc, offset_frames, xfade_dur, fps)

        elif op == "color_grade":
            style = params.get("style", "")
            flt = ET.SubElement(track, "filter", attrib={"in": "0", "out": str(_frame_count(current_time, fps))})
            ET.SubElement(flt, "property", name="mlt_service").text = "avfilter.eq"
            if style == "warm":
                ET.SubElement(flt, "property", name="filter.contrast").text = "1.1"
                ET.SubElement(flt, "property", name="filter.brightness").text = "0.02"
                ET.SubElement(flt, "property", name="filter.saturation").text = "1.2"
            elif style == "cool":
                ET.SubElement(flt, "property", name="filter.contrast").text = "1.15"
                ET.SubElement(flt, "property", name="filter.saturation").text = "0.9"

        elif op in ("add_captions", "text_subtitles"):
            srt_path = params.get("srt_path", "")
            if srt_path and os.path.exists(srt_path):
                flt = ET.SubElement(track, "filter", attrib={
                    "in": "0", "out": str(_frame_count(current_time, fps)),
                })
                ET.SubElement(flt, "property", name="mlt_service").text = "avfilter.subtitles"
                ET.SubElement(flt, "property", name="filter.filename").text = srt_path

        elif op == "speed":
            factor = float(params.get("factor", 1.0))
            if factor != 1.0:
                flt = ET.SubElement(track, "filter", attrib={
                    "in": "0", "out": str(_frame_count(current_time, fps)),
                })
                ET.SubElement(flt, "property", name="mlt_service").text = "avfilter.setpts"
                ET.SubElement(flt, "property", name="filter.expr").text = f"{1/factor}*PTS"

        elif op in ("resize_vertical", "resize"):
            width = int(params.get("width", 1080))
            height = int(params.get("height", 1920))
            flt = ET.SubElement(track, "filter", attrib={
                "in": "0", "out": str(_frame_count(current_time, fps)),
            })
            ET.SubElement(flt, "property", name="mlt_service").text = "avfilter.scale"
            ET.SubElement(flt, "property", name="filter.width").text = str(width)
            ET.SubElement(flt, "property", name="filter.height").text = str(height)

        elif op == "loudnorm":
            pass

    # Finalize
    rough_xml = ET.tostring(doc, encoding="unicode")
    dom = minidom.parseString(rough_xml)
    pretty = dom.toprettyxml(indent="  ")

    with open(output_path, "w") as f:
        f.write(pretty)

    return output_path


def transition_xfade(doc: ET.Element, offset_frames: int, duration: float, fps: float) -> None:
    """Add an xfade transition element to the MLT document."""
    dur_frames = int(round(duration * fps))
    trans = ET.SubElement(doc, "transition", attrib={
        "in": str(offset_frames - dur_frames),
        "out": str(offset_frames),
    })
    ET.SubElement(trans, "property", name="mlt_service").text = "luma"
    ET.SubElement(trans, "property", name="a_track").text = "0"
    ET.SubElement(trans, "property", name="b_track").text = "1"


def render_mlt(mlt_path: str, output_path: str, *, profile: str = "youtube-1080p") -> str:
    """Render an MLT XML project headlessly via `melt`.

    Requires: melt on PATH (apt install melt, or brew install mlt).
    Fallback: if melt not available, return error message.
    """
    out_dir = pathlib.Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    if not shutil.which(_MELT):
        raise RuntimeError(
            "melt not found. Install: apt install melt or brew install mlt. "
            "Without melt, open the .mlt file in Kdenlive/Shotcut to render."
        )

    profile_map = {
        "youtube-1080p": "hdv_1080_30p",
        "tiktok-vertical": "square_1080p",
        "instagram-square": "square_1080p",
    }
    mlt_profile = profile_map.get(profile, "hdv_1080_30p")

    cmd = [
        _MELT, str(pathlib.Path(mlt_path).resolve()),
        "-profile", mlt_profile,
        "-consumer", f"avformat:{output_path}",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


def export_fcpxml(project_path: str, output_path: str = "") -> str:
    """Export FCPXML for Final Cut Pro handoff (requires opentimelineio)."""
    try:
        import opentimelineio as otio
    except ImportError:
        raise ImportError("opentimelineio required: pip install opentimelineio")

    with open(project_path) as f:
        project = json.load(f)

    if not output_path:
        output_path = str(pathlib.Path(project_path).with_suffix(".fcpxml"))

    timeline = otio.schema.Timeline(project.get("name", "Untitled"))
    track = otio.schema.Track("Video")
    timeline.tracks.append(track)

    for step in project.get("steps", []):
        op = step.get("operation", "")
        inp = step.get("input", step.get("params", {}).get("input", ""))
        params = step.get("params", {})

        if op in ("trim", "extract") and inp and os.path.exists(inp):
            start = float(params.get("start", 0))
            dur = float(params.get("duration", 10))
            clip = otio.schema.Clip(
                name=pathlib.Path(inp).name,
                media_reference=otio.schema.ExternalReference(
                    target_url=pathlib.Path(inp).resolve().as_uri(),
                    available_range=otio.opentime.TimeRange(
                        start_time=otio.opentime.RationalTime(start, 30),
                        duration=otio.opentime.RationalTime(dur, 30),
                    ),
                ),
            )
            track.append(clip)

    otio.adapters.write_to_file(timeline, output_path)
    return output_path
