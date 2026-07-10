"""MoviePy adapter — complex programmatic composition.

MoviePy is the Python-native NLE for composites that exceed FFmpeg's
filtergraph practical limits (~5 nodes). Use for:
  - Multi-clip PiP with per-clip animation
  - Text overlays with motion tracking
  - Complex timelines with overlapping elements
  - Programmatic generation (data-driven video)

License: MIT (permissive — safe for the stack).

Hard Rule HR#31 (new): FFmpeg filtergraphs exceeding 5 nodes must switch
to MoviePy for maintainability and memory safety.
"""
from __future__ import annotations
import os
from typing import Optional, List, Dict, Any

_MOVIEPY_ENABLED = os.environ.get("MOVIEPY_ENABLED", "1") == "1"
_moviepy = None

if _MOVIEPY_ENABLED:
    try:
        import moviepy
        from moviepy import (
            VideoFileClip, AudioFileClip, ImageClip, TextClip,
            CompositeVideoClip, concatenate_videoclips, ColorClip,
        )
        from moviepy.video.fx import (
            FadeIn, FadeOut, CrossFadeIn, CrossFadeOut, MultiplySpeed,
        )
        _moviepy = True
    except ImportError:
        _moviepy = None


def is_available() -> bool:
    return _moviepy is not None


def compose(clips_spec: List[Dict[str, Any]], output_path: str,
            width: int = 1920, height: int = 1080, fps: int = 30,
            codec: str = "libx264", preset: str = "medium", crf: int = 18,
            audio_codec: str = "aac", audio_bitrate: str = "192k") -> str:
    if _moviepy is None:
        raise RuntimeError("MoviePy not available. Install with: pip install moviepy")
    clips = [_build_clip(spec, width, height) for spec in clips_spec]
    composite = CompositeVideoClip(clips, size=(width, height))
    composite = composite.with_fps(fps)
    composite.write_videofile(output_path, codec=codec, preset=preset,
                              ffmpeg_params=["-crf", str(crf), "-pix_fmt", "yuv420p"],
                              audio_codec=audio_codec, audio_bitrate=audio_bitrate,
                              threads=2, fps=fps)
    for clip in clips:
        try: clip.close()
        except Exception: pass
    composite.close()
    return output_path


def concatenate(clip_paths: List[str], output_path: str, method: str = "compose",
                transition: Optional[str] = None, transition_duration: float = 0.5,
                fps: int = 30, codec: str = "libx264", preset: str = "medium",
                crf: int = 18) -> str:
    if _moviepy is None:
        raise RuntimeError("MoviePy not available")
    clips = [VideoFileClip(p) for p in clip_paths]
    if transition == "crossfade":
        result = concatenate_videoclips(clips, method="compose", padding=-transition_duration)
    else:
        result = concatenate_videoclips(clips, method=method)
    result.write_videofile(output_path, codec=codec, preset=preset,
                           ffmpeg_params=["-crf", str(crf), "-pix_fmt", "yuv420p"],
                           audio_codec="aac", audio_bitrate="192k", threads=2, fps=fps)
    for clip in clips:
        try: clip.close()
        except Exception: pass
    result.close()
    return output_path


def _build_clip(spec: Dict, comp_w: int, comp_h: int):
    clip_type = spec["type"]
    if clip_type == "video":
        clip = VideoFileClip(spec["path"])
        if spec.get("audio") is False: clip = clip.without_audio()
    elif clip_type == "image":
        clip = ImageClip(spec["path"])
    elif clip_type == "text":
        clip = TextClip(text=spec["text"], font=spec.get("font", "DejaVu-Sans-Bold"),
                        font_size=spec.get("font_size", 72), color=spec.get("color", "white"),
                        stroke_color=spec.get("stroke_color", "black"),
                        stroke_width=spec.get("stroke_width", 2), size=(comp_w, None),
                        method="caption", text_align="center")
    elif clip_type == "color":
        clip = ColorClip(size=spec.get("size", (comp_w, comp_h)), color=spec.get("color", (0, 0, 0)))
    elif clip_type == "audio":
        clip = AudioFileClip(spec["path"])
    else:
        raise ValueError(f"Unknown clip type: {clip_type}")
    if spec.get("duration") is not None: clip = clip.with_duration(spec["duration"])
    elif spec.get("end") is not None: clip = clip.with_duration(spec["end"] - spec.get("start", 0))
    if spec.get("start") is not None: clip = clip.with_start(spec["start"])
    if spec.get("position") is not None: clip = clip.with_position(spec["position"])
    if spec.get("size") is not None: clip = clip.resized(spec["size"])
    if spec.get("opacity") is not None: clip = clip.with_opacity(spec["opacity"])
    for effect_str in spec.get("effects", []):
        clip = _apply_effect(clip, effect_str)
    if spec.get("crop"):
        c = spec["crop"]
        clip = clip.cropped(x1=c.get("x1", 0), y1=c.get("y1", 0),
                            x2=c.get("x2", clip.w), y2=c.get("y2", clip.h))
    if spec.get("rotate"): clip = clip.rotated(spec["rotate"])
    return clip


def _apply_effect(clip, effect_str: str):
    parts = effect_str.split(":")
    name = parts[0]
    params = [float(p) for p in parts[1:]]
    if name == "fade_in": return clip.with_effects([FadeIn(params[0] if params else 0.5)])
    elif name == "fade_out": return clip.with_effects([FadeOut(params[0] if params else 0.5)])
    elif name == "crossfade_in": return clip.with_effects([CrossFadeIn(params[0] if params else 0.5)])
    elif name == "crossfade_out": return clip.with_effects([CrossFadeOut(params[0] if params else 0.5)])
    elif name == "speed": return clip.with_effects([MultiplySpeed(params[0] if params else 1.0)])
    else: raise ValueError(f"Unknown effect: {name}")

__all__ = ["is_available", "compose", "concatenate"]
