"""
Low-level bridge to mcp_video.Client (v1.5.1).
Wraps ~65 safe mcp_video methods with BaseModel→dict conversion
and Hard Rule enforcement.  Known-buggy functions are excluded
(ai_remove_silence, merge, pipeline, ai_transcribe — use
ffmpeg_adapter instead).

Usage:
    from kb.tools._mcp_bridge import mcp_info, mcp_trim, ...
    info = mcp_info("video.mp4")
"""

from __future__ import annotations
import typing as t
import warnings as _warnings

_MCP_AVAILABLE: bool = False
_client: t.Any = None

try:
    from mcp_video import Client as _MCPClient

    _client = _MCPClient()
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False


def _require_mcp() -> None:
    if not _MCP_AVAILABLE:
        raise RuntimeError(
            "mcp_video is not installed. Install it: pip install mcp-video==1.5.1"
        )


def _to_dict(obj: t.Any) -> t.Any:
    """Recursively convert pydantic BaseModel → dict (agent-safe JSON)."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_to_dict(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_to_dict(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def _warn_deprecated(name: str, reason: str = "") -> None:
    msg = (
        f"Direct use of mcp_{name}() is deprecated. "
        f"Use from kb.tools.unified_adapter import {name} instead."
    )
    if reason:
        msg += f" Reason: {reason}"
    _warnings.warn(msg, DeprecationWarning, stacklevel=2)


# ═══════════════════════════════════════════════════════════════
# 1. Core Media Info & Probe
# ═══════════════════════════════════════════════════════════════

def mcp_info(input_path: str) -> dict:
    """Get metadata about a video file (duration, resolution, codecs, etc.)."""
    _require_mcp()
    return _to_dict(_client.info(input_path))


def mcp_video_info_detailed(video: str) -> dict:
    """Get detailed technical metadata about a video file."""
    _require_mcp()
    return _to_dict(_client.video_info_detailed(video))


def mcp_inspect(method_name: str) -> dict:
    """Inspect mcp_video internals or FFmpeg capabilities."""
    _require_mcp()
    return _to_dict(_client.inspect(method_name))


def mcp_search_tools(query: str) -> dict:
    """Search available mcp_video tools by keyword."""
    _require_mcp()
    return _to_dict(_client.search_tools(query))


# ═══════════════════════════════════════════════════════════════
# 2. Trimming & Cutting
# ═══════════════════════════════════════════════════════════════

def mcp_trim(
    input: str,
    start: str | float = 0,
    duration: str | float | None = None,
    end: str | float | None = None,
    output: str | None = None,
    accurate: bool = False,
) -> dict:
    """Trim a video segment. Use accurate=True for frame-accurate cuts."""
    _require_mcp()
    return _to_dict(_client.trim(input, start, duration, end, output, accurate))


def mcp_crop(
    video: str,
    width: int | None = None,
    height: int | None = None,
    x: int | None = None,
    y: int | None = None,
    output: str | None = None,
    crop_percent: float | None = None,
) -> dict:
    """Crop a video region."""
    _require_mcp()
    return _to_dict(
        _client.crop(video, width, height, x, y, output, crop_percent)
    )


# ═══════════════════════════════════════════════════════════════
# 3. Transform (resize, rotate, reverse, speed, stabilize)
# ═══════════════════════════════════════════════════════════════

def mcp_resize(
    video: str,
    width: int | None = None,
    height: int | None = None,
    aspect_ratio: str | None = None,
    quality: str = "high",
    output: str | None = None,
) -> dict:
    """Resize/scale a video."""
    _require_mcp()
    return _to_dict(_client.resize(video, width, height, aspect_ratio, quality, output))


def mcp_rotate(
    video: str,
    angle: int = 0,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    output: str | None = None,
) -> dict:
    """Rotate or flip a video."""
    _require_mcp()
    return _to_dict(_client.rotate(video, angle, flip_horizontal, flip_vertical, output))


def mcp_reverse(video: str, output: str | None = None) -> dict:
    """Reverse a video (play backwards)."""
    _require_mcp()
    return _to_dict(_client.reverse(video, output))


def mcp_speed(video: str, factor: float = 1.0, output: str | None = None) -> dict:
    """Change playback speed of a video."""
    _require_mcp()
    return _to_dict(_client.speed(video, factor, output))


def mcp_stabilize(
    video: str, smoothing: float = 15, zooming: float = 0, output: str | None = None
) -> dict:
    """Stabilize shaky video."""
    _require_mcp()
    return _to_dict(_client.stabilize(video, smoothing, zooming, output))


# ═══════════════════════════════════════════════════════════════
# 4. Color Grading & Effects
# ═══════════════════════════════════════════════════════════════

def mcp_color_grade(
    video: str, preset: str = "warm", output: str | None = None
) -> dict:
    """Apply a color grading preset.
    Hard Rule #14: generate a scope image for verification after grading."""
    _require_mcp()
    result = _client.color_grade(video, preset, output)
    return _to_dict(result)


def mcp_ai_color_grade(
    video: str, output: str, reference: str | None = None, style: str = "auto"
) -> str:
    """AI-assisted color grading, optionally matching a reference look."""
    _require_mcp()
    return _client.ai_color_grade(video, output, reference, style)


def mcp_blur(
    video: str, radius: int = 5, strength: int = 1, output: str | None = None
) -> dict:
    """Apply gaussian blur to a video."""
    _require_mcp()
    return _to_dict(_client.blur(video, radius, strength, output))


def mcp_fade(
    video: str,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    output: str | None = None,
    crf: int | None = None,
    preset: str | None = None,
) -> dict:
    """Add fade-in/fade-out to a video."""
    _require_mcp()
    return _to_dict(_client.fade(video, fade_in, fade_out, output, crf, preset))


# ═══════════════════════════════════════════════════════════════
# 5. Effects (Chromatic Aberration, Glow, Noise, Scanlines, Vignette)
# ═══════════════════════════════════════════════════════════════

def mcp_effect_chromatic_aberration(
    video: str, output: str, intensity: float = 2.0, angle: float = 0
) -> dict:
    """Apply chromatic aberration effect."""
    _require_mcp()
    return _to_dict(_client.effect_chromatic_aberration(video, output, intensity, angle))


def mcp_effect_glow(
    video: str | None = None,
    output: str | None = None,
    intensity: float = 0.5,
    radius: int = 10,
    threshold: float = 0.7,
    *,
    input_path: str | None = None,
    output_path: str | None = None,
) -> dict:
    """Apply glow effect to highlights."""
    _require_mcp()
    return _to_dict(
        _client.effect_glow(video, output, intensity, radius, threshold, input_path=input_path, output_path=output_path)
    )


def mcp_effect_noise(
    video: str, output: str, intensity: float = 0.05, mode: str = "film", animated: bool = True
) -> dict:
    """Add film grain / noise effect."""
    _require_mcp()
    return _to_dict(_client.effect_noise(video, output, intensity, mode, animated))


def mcp_effect_scanlines(
    video: str | None = None,
    output: str | None = None,
    line_height: int = 2,
    opacity: float = 0.3,
    flicker: float = 0.1,
    *,
    input_path: str | None = None,
    output_path: str | None = None,
    intensity: float | None = None,
) -> dict:
    """Apply CRT scanlines effect."""
    _require_mcp()
    return _to_dict(
        _client.effect_scanlines(video, output, line_height, opacity, flicker, input_path=input_path, output_path=output_path, intensity=intensity)
    )


def mcp_effect_vignette(
    video: str, output: str, intensity: float = 0.5, radius: float = 0.8, smoothness: float = 0.5
) -> dict:
    """Apply vignette effect."""
    _require_mcp()
    return _to_dict(_client.effect_vignette(video, output, intensity, radius, smoothness))


# ═══════════════════════════════════════════════════════════════
# 6. Audio
# ═══════════════════════════════════════════════════════════════

def mcp_normalize_audio(
    video: str, target_lufs: float = -16.0, output: str | None = None
) -> dict:
    """Normalize audio loudness to a target LUFS level.
    Note: for production, prefer loudnorm_limited() from ffmpeg_adapter
    which adds true-peak limiting (Hard Rule #17)."""
    _require_mcp()
    return _to_dict(_client.normalize_audio(video, target_lufs, output))


def mcp_audio_compose(tracks: list[dict], duration: float, output: str) -> dict:
    """Compose multiple audio tracks into one.
    Hard Rule #16: each stem must have its own processing chain."""
    _require_mcp()
    return _to_dict(_client.audio_compose(tracks, duration, output))


def mcp_audio_effects(input_path: str, output: str, effects: list[dict]) -> dict:
    """Apply audio effects (EQ, compression, reverb, etc.)."""
    _require_mcp()
    return _to_dict(_client.audio_effects(input_path, output, effects))


def mcp_audio_preset(
    preset: str,
    output: str | None = None,
    pitch: str = "mid",
    duration: float | None = None,
    intensity: float = 0.5,
    *,
    output_path: str | None = None,
) -> dict:
    """Apply an audio preset (voiceover, podcast, cinematic, etc.)."""
    _require_mcp()
    return _to_dict(
        _client.audio_preset(preset, output, pitch, duration, intensity, output_path=output_path)
    )


def mcp_audio_sequence(sequence: list[dict], output: str) -> dict:
    """Sequence multiple audio clips with transitions."""
    _require_mcp()
    return _to_dict(_client.audio_sequence(sequence, output))


def mcp_audio_spatial(
    video: str, output: str, positions: list[dict], method: str = "hrtf"
) -> dict:
    """Apply spatial audio positioning."""
    _require_mcp()
    return _to_dict(_client.audio_spatial(video, output, positions, method))


def mcp_audio_synthesize(
    output: str,
    waveform: str = "sine",
    frequency: float = 440.0,
    duration: float = 1.0,
    volume: float = 0.5,
    effects: dict | None = None,
) -> dict:
    """Synthesize audio (sine, square, sawtooth, triangle, noise)."""
    _require_mcp()
    return _to_dict(_client.audio_synthesize(output, waveform, frequency, duration, volume, effects))


def mcp_audio_waveform(video: str, bins: int = 50) -> dict:
    """Generate audio waveform data."""
    _require_mcp()
    return _to_dict(_client.audio_waveform(video, bins))


def mcp_add_audio(
    video: str,
    audio: str,
    volume: float = 1.0,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    mix: bool = False,
    start_time: float | None = None,
    output: str | None = None,
) -> dict:
    """Add/replace/mix an audio track onto a video."""
    _require_mcp()
    return _to_dict(_client.add_audio(video, audio, volume, fade_in, fade_out, mix, start_time, output))


def mcp_add_generated_audio(video: str, audio_config: dict, output: str) -> dict:
    """Add procedurally generated audio to a video."""
    _require_mcp()
    return _to_dict(_client.add_generated_audio(video, audio_config, output))


def mcp_extract_audio(
    video: str, output: str | None = None, format: str = "mp3"
) -> dict:
    """Extract audio track from a video file."""
    _require_mcp()
    return _to_dict(_client.extract_audio(video, output, format))


# ═══════════════════════════════════════════════════════════════
# 7. Subtitles & Text
# ═══════════════════════════════════════════════════════════════

def mcp_text_subtitles(
    video: str, subtitles: str, output: str, style: dict | None = None
) -> dict:
    """Burn subtitles into a video.
    Subtitles apply LAST in filter chain (Hard Rule #12)."""
    _require_mcp()
    return _to_dict(_client.text_subtitles(video, subtitles, output, style))


def mcp_subtitles_styled(
    video: str, subtitles: str, output: str, style: dict | None = None
) -> dict:
    """Burn subtitles with advanced styling options."""
    _require_mcp()
    return _to_dict(_client.subtitles_styled(video, subtitles, output, style))


def mcp_subtitles(video: str, subtitle_file: str, output: str | None = None) -> dict:
    """Burn subtitle file into video (default styling)."""
    _require_mcp()
    return _to_dict(_client.subtitles(video, subtitle_file, output))


def mcp_generate_subtitles(
    video: str, entries: list[dict], burn: bool = False, output: str | None = None
) -> dict:
    """Create subtitle entries programmatically."""
    _require_mcp()
    return _to_dict(_client.generate_subtitles(video, entries, burn, output))


def mcp_add_text(
    video: str,
    text: str,
    position: str = "top-center",
    font: str | None = None,
    size: int = 48,
    color: str = "white",
    shadow: bool = True,
    start_time: float | None = None,
    duration: float | None = None,
    output: str | None = None,
    crf: int | None = None,
    preset: str | None = None,
) -> dict:
    """Add static text overlay to a video."""
    _require_mcp()
    return _to_dict(
        _client.add_text(video, text, position, font, size, color, shadow, start_time, duration, output, crf, preset)
    )


def mcp_text_animated(
    video: str,
    text: str,
    output: str,
    animation: str = "fade",
    font: str = "Arial",
    size: int = 48,
    color: str = "white",
    position: str = "center",
    start: float = 0,
    duration: float = 3.0,
    typewriter_speed: float = 0.08,
) -> dict:
    """Add animated text overlay."""
    _require_mcp()
    return _to_dict(
        _client.text_animated(video, text, output, animation, font, size, color, position, start, duration, typewriter_speed)
    )


# ═══════════════════════════════════════════════════════════════
# 8. Layout (PiP, Grid, Split Screen, Overlay, Watermark)
# ═══════════════════════════════════════════════════════════════

def mcp_layout_pip(
    main: str,
    pip: str,
    output: str,
    position: str = "bottom-right",
    size: float = 0.25,
    margin: int = 20,
    rounded_corners: bool = True,
    border: bool = True,
    border_color: str = "#CCFF00",
    border_width: int = 2,
) -> dict:
    """Picture-in-picture overlay with configurable styling."""
    _require_mcp()
    return _to_dict(
        _client.layout_pip(main, pip, output, position, size, margin, rounded_corners, border, border_color, border_width)
    )


def mcp_layout_grid(
    clips: list[str], layout: str, output: str, gap: int = 10, padding: int = 20, background: str = "#141414"
) -> dict:
    """Arrange multiple clips in a grid layout."""
    _require_mcp()
    return _to_dict(_client.layout_grid(clips, layout, output, gap, padding, background))


def mcp_split_screen(
    left: str, right: str, layout: str = "side-by-side", output: str | None = None
) -> dict:
    """Side-by-side split screen."""
    _require_mcp()
    return _to_dict(_client.split_screen(left, right, layout, output))


def mcp_overlay_video(
    background: str,
    overlay: str,
    position: str = "top-right",
    width: int | None = None,
    height: int | None = None,
    opacity: float = 0.8,
    start_time: float | None = None,
    duration: float | None = None,
    output: str | None = None,
    crf: int | None = None,
    preset: str | None = None,
) -> dict:
    """Overlay one video on top of another."""
    _require_mcp()
    return _to_dict(
        _client.overlay_video(background, overlay, position, width, height, opacity, start_time, duration, output, crf, preset)
    )


def mcp_watermark(
    video: str,
    image: str,
    position: str = "bottom-right",
    opacity: float = 0.7,
    margin: int = 20,
    output: str | None = None,
    crf: int | None = None,
    preset: str | None = None,
) -> dict:
    """Add image watermark overlay."""
    _require_mcp()
    return _to_dict(_client.watermark(video, image, position, opacity, margin, output, crf, preset))


# ═══════════════════════════════════════════════════════════════
# 9. Transitions
# ═══════════════════════════════════════════════════════════════
# Note: mcp_video's merge() is buggy for >2 clips.
# For production xfade chains, use ffmpeg_adapter.merge().
# These transitions work for single clip-to-clip transitions.

def mcp_transition_glitch(
    clip1: str, clip2: str, output: str, duration: float = 0.5, intensity: float = 0.3
) -> dict:
    """Glitch transition between two clips."""
    _require_mcp()
    return _to_dict(_client.transition_glitch(clip1, clip2, output, duration, intensity))


def mcp_transition_morph(
    clip1: str, clip2: str, output: str, duration: float = 0.6, mesh_size: int = 10
) -> dict:
    """Morph transition between two clips."""
    _require_mcp()
    return _to_dict(_client.transition_morph(clip1, clip2, output, duration, mesh_size))


def mcp_transition_pixelate(
    clip1: str, clip2: str, output: str, duration: float = 0.4, pixel_size: int = 50
) -> dict:
    """Pixelate transition between two clips."""
    _require_mcp()
    return _to_dict(_client.transition_pixelate(clip1, clip2, output, duration, pixel_size))


# ═══════════════════════════════════════════════════════════════
# 10. Scene Detection & Analysis
# ═══════════════════════════════════════════════════════════════

def mcp_detect_scenes(
    video: str, threshold: float = 0.3, min_scene_duration: float = 1.0
) -> dict:
    """Detect scene changes in a video."""
    _require_mcp()
    return _to_dict(_client.detect_scenes(video, threshold, min_scene_duration))


def mcp_ai_scene_detect(video: str, threshold: float = 0.3, use_ai: bool = False) -> list[dict]:
    """AI-powered scene detection (optionally using ML model)."""
    _require_mcp()
    return _to_dict(_client.ai_scene_detect(video, threshold, use_ai))


def mcp_auto_chapters(video: str, threshold: float = 0.3) -> list:
    """Auto-generate chapter markers based on scene detection."""
    _require_mcp()
    return _to_dict(_client.auto_chapters(video, threshold))


# ═══════════════════════════════════════════════════════════════
# 11. Quality & Analysis
# ═══════════════════════════════════════════════════════════════

def mcp_quality_check(video: str, fail_on_warning: bool = False) -> dict:
    """Run quality check on a video file."""
    _require_mcp()
    return _to_dict(_client.quality_check(video, fail_on_warning))


def mcp_assert_quality(video: str, min_score: float = 80.0) -> dict:
    """Assert video quality meets a minimum score.
    Hard Rule #20: VMAF >= 80 for any re-encode."""
    _require_mcp()
    return _to_dict(_client.assert_quality(video, min_score))


def mcp_compare_quality(
    original: str, distorted: str, metrics: list[str] | None = None
) -> dict:
    """Compare quality metrics between two videos."""
    _require_mcp()
    return _to_dict(_client.compare_quality(original, distorted, metrics))


def mcp_design_quality_check(video: str, auto_fix: bool = False, strict: bool = False) -> dict:
    """Check design quality (composition, framing, exposure)."""
    _require_mcp()
    return _to_dict(_client.design_quality_check(video, auto_fix, strict))


def mcp_fix_design_issues(video: str, output: str | None = None) -> str:
    """Auto-fix common design issues."""
    _require_mcp()
    return _client.fix_design_issues(video, output)


def mcp_analyze_video(
    video: str,
    *,
    whisper_model: str = "base",
    language: str | None = None,
    scene_threshold: float = 0.3,
    include_transcript: bool = True,
    include_scenes: bool = True,
    include_audio: bool = True,
    include_quality: bool = True,
    include_chapters: bool = True,
    include_colors: bool = True,
    output_srt: str | None = None,
    output_txt: str | None = None,
    output_md: str | None = None,
    output_json: str | None = None,
) -> dict:
    """Comprehensive video analysis: transcript, scenes, audio, quality, colors."""
    _require_mcp()
    return _to_dict(
        _client.analyze_video(
            video,
            whisper_model=whisper_model,
            language=language,
            scene_threshold=scene_threshold,
            include_transcript=include_transcript,
            include_scenes=include_scenes,
            include_audio=include_audio,
            include_quality=include_quality,
            include_chapters=include_chapters,
            include_colors=include_colors,
            output_srt=output_srt,
            output_txt=output_txt,
            output_md=output_md,
            output_json=output_json,
        )
    )


def mcp_analyze_product(image_path: str, use_ai: bool = False, n_colors: int = 5) -> dict:
    """Analyze a product image for colors and composition."""
    _require_mcp()
    return _to_dict(_client.analyze_product(image_path, use_ai, n_colors))


# ═══════════════════════════════════════════════════════════════
# 12. Export & Conversion
# ═══════════════════════════════════════════════════════════════

def mcp_export(
    video: str, output: str | None = None, quality: str = "high", format: str = "mp4"
) -> dict:
    """Export video with quality settings.
    For platform-specific delivery, use render() from ffmpeg_adapter
    which enforces platform profiles (Hard Rule #19)."""
    _require_mcp()
    return _to_dict(_client.export(video, output, quality, format))


def mcp_convert(
    video: str,
    format: str = "mp4",
    quality: str = "high",
    output: str | None = None,
    two_pass: bool = False,
    target_bitrate: int | None = None,
) -> dict:
    """Convert video to a different format/codec."""
    _require_mcp()
    return _to_dict(_client.convert(video, format, quality, output, two_pass, target_bitrate))


def mcp_preview(video: str, output: str | None = None, scale_factor: int = 4) -> dict:
    """Generate low-resolution preview."""
    _require_mcp()
    return _to_dict(_client.preview(video, output, scale_factor))


def mcp_hls_segment(
    video: str,
    output_dir: str | None = None,
    segment_duration: int = 4,
    playlist_name: str = "playlist.m3u8",
    qualities: list[str] | None = None,
) -> dict:
    """Segment video into HLS chunks."""
    _require_mcp()
    return _to_dict(
        _client.hls_segment(video, output_dir, segment_duration, playlist_name, qualities)
    )


# ═══════════════════════════════════════════════════════════════
# 13. Frame & Thumbnail Operations
# ═══════════════════════════════════════════════════════════════

def mcp_thumbnail(
    video: str, timestamp: float | None = None, output: str | None = None
) -> dict:
    """Extract a frame at a given timestamp as thumbnail."""
    _require_mcp()
    return _to_dict(_client.thumbnail(video, timestamp, output))


def mcp_extract_frame(
    video: str, timestamp: float | None = None, output: str | None = None
) -> dict:
    """Extract a single frame at a given timestamp."""
    _require_mcp()
    return _to_dict(_client.extract_frame(video, timestamp, output))


def mcp_export_frames(
    video: str, output_dir: str | None = None, fps: float = 1.0, format: str = "jpg"
) -> dict:
    """Export frames as image sequence."""
    _require_mcp()
    return _to_dict(_client.export_frames(video, output_dir, fps, format))


def mcp_storyboard(
    video: str, output_dir: str | None = None, frame_count: int = 8
) -> dict:
    """Generate storyboard thumbnails."""
    _require_mcp()
    return _to_dict(_client.storyboard(video, output_dir, frame_count))


# ═══════════════════════════════════════════════════════════════
# 14. Chroma Key & Masking
# ═══════════════════════════════════════════════════════════════

def mcp_chroma_key(
    video: str,
    color: str = "0x00FF00",
    similarity: float = 0.01,
    blend: float = 0.0,
    output: str | None = None,
) -> dict:
    """Apply chroma key (green screen) effect."""
    _require_mcp()
    return _to_dict(_client.chroma_key(video, color, similarity, blend, output))


def mcp_luma_key(video: str, threshold: float = 0.5, output: str | None = None) -> dict:
    """Apply luma key (brightness-based transparency)."""
    _require_mcp()
    return _to_dict(_client.luma_key(video, threshold, output))


def mcp_apply_mask(
    video: str, mask: str, feather: int = 5, output: str | None = None
) -> dict:
    """Apply a mask image to a video."""
    _require_mcp()
    return _to_dict(_client.apply_mask(video, mask, feather, output))


def mcp_shape_mask(
    video: str, shape: str = "circle", output: str | None = None, feather: int = 0
) -> dict:
    """Apply a shape mask to a video."""
    _require_mcp()
    return _to_dict(_client.shape_mask(video, shape, output, feather))


# ═══════════════════════════════════════════════════════════════
# 15. AI Features (Stem Separation, Upscale)
# ═══════════════════════════════════════════════════════════════

def mcp_ai_stem_separation(
    video: str,
    output_dir: str,
    stems: list[str] | None = None,
    model: str = "htdemucs",
) -> dict:
    """Separate audio into stems (vocals, drums, bass, other)."""
    _require_mcp()
    return _to_dict(_client.ai_stem_separation(video, output_dir, stems, model))


def mcp_ai_upscale(
    video: str, output: str, scale: int = 2, model: str = "realesrgan"
) -> str:
    """AI upscaling of video resolution."""
    _require_mcp()
    return _client.ai_upscale(video, output, scale, model)


# ═══════════════════════════════════════════════════════════════
# 16. Metadata
# ═══════════════════════════════════════════════════════════════

def mcp_read_metadata(video: str) -> dict:
    """Read metadata from a video file."""
    _require_mcp()
    return _to_dict(_client.read_metadata(video))


def mcp_write_metadata(
    video: str, metadata: dict[str, str], output: str | None = None
) -> dict:
    """Write metadata to a video file."""
    _require_mcp()
    return _to_dict(_client.write_metadata(video, metadata, output))


def mcp_extract_colors(image_path: str, n_colors: int = 5) -> dict:
    """Extract dominant colors from an image."""
    _require_mcp()
    return _to_dict(_client.extract_colors(image_path, n_colors))


def mcp_generate_palette(
    image_path: str, harmony: str = "complementary", n_colors: int = 5
) -> dict:
    """Generate a color palette from an image."""
    _require_mcp()
    return _to_dict(_client.generate_palette(image_path, harmony, n_colors))


# ═══════════════════════════════════════════════════════════════
# 17. Batch & Workflow
# ═══════════════════════════════════════════════════════════════

def mcp_batch(
    inputs: list[str],
    operation: str,
    params: dict | None = None,
    output_dir: str | None = None,
) -> dict:
    """Run an operation on a batch of inputs."""
    _require_mcp()
    return _to_dict(_client.batch(inputs, operation, params, output_dir))


def mcp_repurpose(
    video: str,
    output_dir: str | None = None,
    platforms: list[str] | None = None,
    include_release_checkpoint: bool = True,
    min_score: float = 0.0,
) -> dict:
    """Repurpose video for multiple platform formats."""
    _require_mcp()
    return _to_dict(
        _client.repurpose(video, output_dir, platforms, include_release_checkpoint, min_score)
    )


def mcp_repurpose_plan(
    video: str,
    output_dir: str | None = None,
    platforms: list[str] | None = None,
) -> dict:
    """Generate a repurpose plan without executing it."""
    _require_mcp()
    return _to_dict(_client.repurpose_plan(video, output_dir, platforms))


def mcp_release_checkpoint(
    input_path: str,
    output_dir: str | None = None,
    min_score: float = 80.0,
    frame_count: int = 6,
) -> dict:
    """Create a release checkpoint with quality validation."""
    _require_mcp()
    return _to_dict(_client.release_checkpoint(input_path, output_dir, min_score, frame_count))


# ═══════════════════════════════════════════════════════════════
# 18. Motion Graphics
# ═══════════════════════════════════════════════════════════════

def mcp_mograph_count(
    start: int,
    end: int,
    duration: float,
    output: str,
    style: dict | None = None,
    fps: int = 30,
) -> dict:
    """Animated counting number motion graphic."""
    _require_mcp()
    return _to_dict(_client.mograph_count(start, end, duration, output, style, fps))


def mcp_mograph_progress(
    duration: float,
    output: str,
    style: str = "bar",
    color: str = "#CCFF00",
    track_color: str = "#333333",
    fps: int = 30,
) -> dict:
    """Animated progress bar motion graphic."""
    _require_mcp()
    return _to_dict(_client.mograph_progress(duration, output, style, color, track_color, fps))


# ═══════════════════════════════════════════════════════════════
# 19. Custom Filter & Timeline Edit
# ═══════════════════════════════════════════════════════════════

def mcp_filter(
    video: str,
    filter_type: str,
    params: dict | None = None,
    output: str | None = None,
    crf: int | None = None,
    preset: str | None = None,
) -> dict:
    """Apply a custom FFmpeg filter."""
    _require_mcp()
    return _to_dict(_client.filter(video, filter_type, params, output, crf, preset))


def mcp_edit(timeline: dict, output: str | None = None) -> dict:
    """Execute a timeline-based edit (multi-track, multi-clip)."""
    _require_mcp()
    return _to_dict(_client.edit(timeline, output))


def mcp_create_from_images(
    images: list[str] | None = None,
    output: str | None = None,
    fps: float = 30.0,
    *,
    output_path: str | None = None,
    **kwargs,
) -> dict:
    """Create a video from a sequence of images."""
    _require_mcp()
    return _to_dict(_client.create_from_images(images, output, fps, output_path=output_path, **kwargs))


# ═══════════════════════════════════════════════════════════════
# 20. Hyperframes (Programmatic Animation)
# ═══════════════════════════════════════════════════════════════

def mcp_hyperframes_init(
    name: str,
    output_dir: str | None = None,
    template: str = "blank",
    video: str | None = None,
    audio: str | None = None,
    skip_transcribe: bool = False,
    model: str | None = None,
    language: str | None = None,
    tailwind: bool = False,
    resolution: str | None = None,
) -> dict:
    """Initialize a Hyperframes project."""
    _require_mcp()
    return _to_dict(
        _client.hyperframes_init(
            name, output_dir, template, video, audio,
            skip_transcribe, model, language, tailwind, resolution,
        )
    )


def mcp_hyperframes_info(project_path: str) -> dict:
    """Get info about a Hyperframes project."""
    _require_mcp()
    return _to_dict(_client.hyperframes_info(project_path))


def mcp_hyperframes_validate(project_path: str) -> dict:
    """Validate a Hyperframes project."""
    _require_mcp()
    return _to_dict(_client.hyperframes_validate(project_path))


def mcp_hyperframes_render(
    project_path: str,
    output: str | None = None,
    fps: float | None = None,
    width: int | None = None,
    height: int | None = None,
    composition: str | None = None,
    quality: str | None = None,
    format: str | None = None,
    resolution: str | None = None,
    workers: str | int | None = None,
    crf: int | None = None,
    variables: t.Any | None = None,
    variables_file: str | None = None,
) -> dict:
    """Render a Hyperframes project."""
    _require_mcp()
    return _to_dict(
        _client.hyperframes_render(
            project_path, output, fps, width, height, composition,
            quality, format, resolution, workers, crf,
            variables, variables_file,
        )
    )


def mcp_hyperframes_preview(project_path: str, port: int = 3002) -> dict:
    """Preview a Hyperframes project in a local server."""
    _require_mcp()
    return _to_dict(_client.hyperframes_preview(project_path, port))


def mcp_hyperframes_snapshot(
    project_path: str,
    frames: int = 5,
    at: list[float] | None = None,
    timeout_ms: int | None = None,
    variables: t.Any | None = None,
    variables_file: str | None = None,
) -> dict:
    """Capture snapshots of a Hyperframes project."""
    _require_mcp()
    return _to_dict(
        _client.hyperframes_snapshot(project_path, frames, at, timeout_ms, variables, variables_file)
    )


def mcp_hyperframes_still(
    project_path: str,
    output: str | None = None,
    frame: int = 0,
    variables: t.Any | None = None,
    variables_file: str | None = None,
) -> dict:
    """Render a single frame from a Hyperframes project."""
    _require_mcp()
    return _to_dict(
        _client.hyperframes_still(project_path, output, frame, variables, variables_file)
    )


def mcp_hyperframes_compositions(project_path: str) -> dict:
    """List compositions in a Hyperframes project."""
    _require_mcp()
    return _to_dict(_client.hyperframes_compositions(project_path))


def mcp_hyperframes_capture(
    url: str, output: str | None = None, skip_assets: bool = False,
    max_screenshots: int | None = None, timeout_ms: int | None = None,
) -> dict:
    """Capture a web page as Hyperframes project."""
    _require_mcp()
    return _to_dict(
        _client.hyperframes_capture(url, output, skip_assets, max_screenshots, timeout_ms)
    )


def mcp_hyperframes_to_mcpvideo(project_path: str, post_process: list[dict], output: str | None = None) -> dict:
    """Convert Hyperframes project to mcp-video pipeline."""
    _require_mcp()
    return _to_dict(_client.hyperframes_to_mcpvideo(project_path, post_process, output))


def mcp_hyperframes_transcribe(input_path: str, project_path: str | None = None, model: str | None = None, language: str | None = None) -> dict:
    """Transcribe audio within a Hyperframes context."""
    _require_mcp()
    return _to_dict(_client.hyperframes_transcribe(input_path, project_path, model, language))


def mcp_hyperframes_tts(
    text_or_file: str | None = None,
    output: str | None = None,
    voice: str | None = None,
    speed: float | None = None,
    language: str | None = None,
    list_voices: bool = False,
) -> dict:
    """Text-to-speech for Hyperframes."""
    _require_mcp()
    return _to_dict(_client.hyperframes_tts(text_or_file, output, voice, speed, language, list_voices))


def mcp_hyperframes_doctor() -> dict:
    """Diagnose Hyperframes installation."""
    _require_mcp()
    return _to_dict(_client.hyperframes_doctor())


def mcp_hyperframes_catalog(item_type: str | None = None, tag: str | None = None) -> dict:
    """Browse the Hyperframes template catalog."""
    _require_mcp()
    return _to_dict(_client.hyperframes_catalog(item_type, tag))


def mcp_hyperframes_benchmark(
    project_path: str, output: str | None = None, runs: int | None = None, json_output: bool = True
) -> dict:
    """Benchmark Hyperframes rendering performance."""
    _require_mcp()
    return _to_dict(_client.hyperframes_benchmark(project_path, output, runs, json_output))


def mcp_hyperframes_add_block(project_path: str, block_name: str, no_clipboard: bool = False) -> dict:
    """Add a block to a Hyperframes project."""
    _require_mcp()
    return _to_dict(_client.hyperframes_add_block(project_path, block_name, no_clipboard))


def mcp_hyperframes_remove_background(
    input_path: str,
    output: str | None = None,
    background_output: str | None = None,
    device: str = "auto",
    quality: str = "balanced",
    info: bool = False,
) -> dict:
    """Remove background from an image using AI."""
    _require_mcp()
    return _to_dict(
        _client.hyperframes_remove_background(input_path, output, background_output, device, quality, info)
    )


# ═══════════════════════════════════════════════════════════════
# Known-buggy functions — NOT wrapped here.
# Use ffmpeg_adapter instead:
#   - ai_remove_silence → ffmpeg_adapter.silence_remove() (desync bug)
#   - merge → ffmpeg_adapter.merge() (wrong duration for >2 clips)
#   - pipeline → skip entirely (broken API — 'op' vs 'operation')
#   - ai_transcribe → ffmpeg_adapter.transcribe() (heavy deps, faster-whisper)
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # 1. Core
    "mcp_info", "mcp_video_info_detailed", "mcp_inspect", "mcp_search_tools",
    # 2. Trim & Crop
    "mcp_trim", "mcp_crop",
    # 3. Transform
    "mcp_resize", "mcp_rotate", "mcp_reverse", "mcp_speed", "mcp_stabilize",
    # 4. Color
    "mcp_color_grade", "mcp_ai_color_grade", "mcp_blur", "mcp_fade",
    # 5. Effects
    "mcp_effect_chromatic_aberration", "mcp_effect_glow", "mcp_effect_noise",
    "mcp_effect_scanlines", "mcp_effect_vignette",
    # 6. Audio
    "mcp_normalize_audio", "mcp_audio_compose", "mcp_audio_effects",
    "mcp_audio_preset", "mcp_audio_sequence", "mcp_audio_spatial",
    "mcp_audio_synthesize", "mcp_audio_waveform", "mcp_add_audio",
    "mcp_add_generated_audio", "mcp_extract_audio",
    # 7. Subtitles & Text
    "mcp_text_subtitles", "mcp_subtitles_styled", "mcp_subtitles",
    "mcp_generate_subtitles", "mcp_add_text", "mcp_text_animated",
    # 8. Layout
    "mcp_layout_pip", "mcp_layout_grid", "mcp_split_screen",
    "mcp_overlay_video", "mcp_watermark",
    # 9. Transitions
    "mcp_transition_glitch", "mcp_transition_morph", "mcp_transition_pixelate",
    # 10. Scene Detection
    "mcp_detect_scenes", "mcp_ai_scene_detect", "mcp_auto_chapters",
    # 11. Quality & Analysis
    "mcp_quality_check", "mcp_assert_quality", "mcp_compare_quality",
    "mcp_design_quality_check", "mcp_fix_design_issues", "mcp_analyze_video",
    "mcp_analyze_product",
    # 12. Export
    "mcp_export", "mcp_convert", "mcp_preview", "mcp_hls_segment",
    # 13. Frames
    "mcp_thumbnail", "mcp_extract_frame", "mcp_export_frames", "mcp_storyboard",
    # 14. Chroma Key & Masking
    "mcp_chroma_key", "mcp_luma_key", "mcp_apply_mask", "mcp_shape_mask",
    # 15. AI
    "mcp_ai_stem_separation", "mcp_ai_upscale",
    # 16. Metadata
    "mcp_read_metadata", "mcp_write_metadata", "mcp_extract_colors", "mcp_generate_palette",
    # 17. Batch & Workflow
    "mcp_batch", "mcp_repurpose", "mcp_repurpose_plan", "mcp_release_checkpoint",
    # 18. Motion Graphics
    "mcp_mograph_count", "mcp_mograph_progress",
    # 19. Custom
    "mcp_filter", "mcp_edit", "mcp_create_from_images",
    # 20. Hyperframes
    "mcp_hyperframes_init", "mcp_hyperframes_info", "mcp_hyperframes_validate",
    "mcp_hyperframes_render", "mcp_hyperframes_preview", "mcp_hyperframes_snapshot",
    "mcp_hyperframes_still", "mcp_hyperframes_compositions", "mcp_hyperframes_capture",
    "mcp_hyperframes_to_mcpvideo", "mcp_hyperframes_transcribe", "mcp_hyperframes_tts",
    "mcp_hyperframes_doctor", "mcp_hyperframes_catalog", "mcp_hyperframes_benchmark",
    "mcp_hyperframes_add_block", "mcp_hyperframes_remove_background",
    # Availability flag
    "_MCP_AVAILABLE",
]
