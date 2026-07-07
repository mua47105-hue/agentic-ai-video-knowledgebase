"""
Unified adapter: single import surface combining mcp_video.Client (safe wrappers)
with audited ffmpeg_adapter functions.

Usage:
    from kb.tools.unified_adapter import edit
    info = edit.info("video.mp4")
    edit.trim("video.mp4", output="trimmed.mp4", start="00:01:00")
    edit.silence_remove("video.mp4", "no_silence.mp4")  # audited, not mcp_video

Architecture:
    - mcp_video.Client wraps ~60+ stable functions (via _mcp_bridge.py)
    - ffmpeg_adapter provides 9 audited functions (ours is better) +
      20 unique functions (J/L-cuts, scopes, project files, quality, etc.)
    - Hard Rules enforced at the bridge level
    - Graceful degradation if mcp_video is not installed
"""

from __future__ import annotations
import types as _types
import typing as t
import warnings as _warnings

# Suppress deprecation warning from ffmpeg_adapter — this is the intended path
_warnings.filterwarnings("ignore", message=".*ffmpeg_adapter is deprecated.*", category=DeprecationWarning)

# ── Import from bridge (mcp_video safe wrappers) ──
# 7 overlapping names: mcp_video wins (better implementation)
from kb.tools._mcp_bridge import (
    mcp_info as info,
    mcp_trim as trim,
    mcp_resize as resize,
    mcp_speed as speed,
    mcp_stabilize as stabilize,
    mcp_color_grade as color_grade,
    mcp_text_subtitles as text_subtitles,
)

# 92 unique mcp_video capabilities (no ffmpeg_adapter equivalent)
from kb.tools._mcp_bridge import (
    mcp_video_info_detailed as video_info_detailed,
    mcp_inspect as inspect,
    mcp_search_tools as search_tools,
    mcp_crop as crop,
    mcp_rotate as rotate,
    mcp_reverse as reverse,
    mcp_blur as blur,
    mcp_fade as fade,
    mcp_ai_color_grade as ai_color_grade,
    mcp_effect_chromatic_aberration as effect_chromatic_aberration,
    mcp_effect_glow as effect_glow,
    mcp_effect_noise as effect_noise,
    mcp_effect_scanlines as effect_scanlines,
    mcp_effect_vignette as effect_vignette,
    mcp_normalize_audio as normalize_audio,
    mcp_audio_compose as audio_compose,
    mcp_audio_effects as audio_effects,
    mcp_audio_preset as audio_preset,
    mcp_audio_sequence as audio_sequence,
    mcp_audio_spatial as audio_spatial,
    mcp_audio_synthesize as audio_synthesize,
    mcp_audio_waveform as audio_waveform,
    mcp_add_audio as add_audio,
    mcp_add_generated_audio as add_generated_audio,
    mcp_extract_audio as extract_audio,
    mcp_subtitles_styled as subtitles_styled,
    mcp_subtitles as subtitles,
    mcp_generate_subtitles as generate_subtitles,
    mcp_add_text as add_text,
    mcp_text_animated as text_animated,
    mcp_layout_pip as layout_pip,
    mcp_layout_grid as layout_grid,
    mcp_split_screen as split_screen,
    mcp_overlay_video as overlay_video,
    mcp_watermark as watermark,
    mcp_transition_glitch as transition_glitch,
    mcp_transition_morph as transition_morph,
    mcp_transition_pixelate as transition_pixelate,
    mcp_detect_scenes as detect_scenes,
    mcp_ai_scene_detect as ai_scene_detect,
    mcp_auto_chapters as auto_chapters,
    mcp_quality_check as quality_check,
    mcp_assert_quality as assert_quality,
    mcp_compare_quality as compare_quality,
    mcp_design_quality_check as design_quality_check,
    mcp_fix_design_issues as fix_design_issues,
    mcp_analyze_video as analyze_video,
    mcp_analyze_product as analyze_product,
    mcp_export as export,
    mcp_convert as convert,
    mcp_preview as preview,
    mcp_hls_segment as hls_segment,
    mcp_thumbnail as thumbnail,
    mcp_extract_frame as extract_frame,
    mcp_export_frames as export_frames,
    mcp_storyboard as storyboard,
    mcp_chroma_key as chroma_key,
    mcp_luma_key as luma_key,
    mcp_apply_mask as apply_mask,
    mcp_shape_mask as shape_mask,
    mcp_ai_stem_separation as ai_stem_separation,
    mcp_ai_upscale as ai_upscale,
    mcp_read_metadata as read_metadata,
    mcp_write_metadata as write_metadata,
    mcp_extract_colors as extract_colors,
    mcp_generate_palette as generate_palette,
    mcp_batch as batch,
    mcp_repurpose as repurpose,
    mcp_repurpose_plan as repurpose_plan,
    mcp_release_checkpoint as release_checkpoint,
    mcp_mograph_count as mograph_count,
    mcp_mograph_progress as mograph_progress,
    mcp_filter as filter,
    mcp_edit as edit_timeline,
    mcp_create_from_images as create_from_images,
    # Hyperframes (programmatic animation)
    mcp_hyperframes_init as hyperframes_init,
    mcp_hyperframes_info as hyperframes_info,
    mcp_hyperframes_validate as hyperframes_validate,
    mcp_hyperframes_render as hyperframes_render,
    mcp_hyperframes_preview as hyperframes_preview,
    mcp_hyperframes_snapshot as hyperframes_snapshot,
    mcp_hyperframes_still as hyperframes_still,
    mcp_hyperframes_compositions as hyperframes_compositions,
    mcp_hyperframes_capture as hyperframes_capture,
    mcp_hyperframes_to_mcpvideo as hyperframes_to_mcpvideo,
    mcp_hyperframes_transcribe as hyperframes_transcribe,
    mcp_hyperframes_tts as hyperframes_tts,
    mcp_hyperframes_doctor as hyperframes_doctor,
    mcp_hyperframes_catalog as hyperframes_catalog,
    mcp_hyperframes_benchmark as hyperframes_benchmark,
    mcp_hyperframes_add_block as hyperframes_add_block,
    mcp_hyperframes_remove_background as hyperframes_remove_background,
    # Availability flag
    _MCP_AVAILABLE as mcp_available,
)

# ── Import from ffmpeg_adapter (audited — ours is better) ──
# These replace buggy/inferior mcp_video equivalents:
from kb.tools.ffmpeg_adapter import (
    merge,              # mcp_video merge: wrong duration for >2 clips + transition
    silence_remove,     # mcp_video ai_remove_silence: 11.62s A/V desync
    transcribe,         # mcp_video ai_transcribe: heavy openai-whisper deps (~1GB)
)

# ── Import from ffmpeg_adapter (unique — mcp_video has no equivalent) ──
from kb.tools.ffmpeg_adapter import (
    # J/L-cuts
    j_cut,
    l_cut,
    j_l_cut_sequence,
    # Audio (& hard rules)
    loudnorm,
    loudnorm_limited,
    # Scopes
    scope_waveform,
    scope_vectorscope,
    scope_histogram,
    scope_parade,
    scope_analyze,
    # Quality metrics
    probe,
    verify,
    quality_vmaf,
    quality_psnr,
    quality_ssim,
    quality_audio,
    quality_full_qc,
    # Render profiles
    RENDER_PROFILES,
    render,
    render_multi,
    # Project files
    project_create,
    project_step,
    project_resume,
    project_snapshot,
    project_audit_report,
    # Legacy aliases
    scene_detect,    # renamed from detect_scenes in bridge — keep both
    pip,             # renamed from layout_pip in bridge — keep both
)

# ═══════════════════════════════════════════════════════════════
# Music adapter (audio analysis + royalty-free search/download)
# ═══════════════════════════════════════════════════════════════

import kb.tools.music_adapter as _music_adapter

class _MusicModule(_types.ModuleType):
    """Convenience module: music.describe(), music.search(), music.download()"""

    def describe(self, audio_path: str, **kwargs) -> dict:
        return _music_adapter.music_describe(audio_path, **kwargs)

    def search(self, query: str, **kwargs) -> list[dict]:
        return _music_adapter.music_search(query, **kwargs)

    def download(self, track: dict, **kwargs) -> dict:
        return _music_adapter.music_download(track, **kwargs)

music = _MusicModule("music_adapter")

# ═══════════════════════════════════════════════════════════
# Compliance reporter
# ═══════════════════════════════════════════════════════════

from kb.tools.compliance import (
    compliance_report,
    list_specs,
    COMPLIANCE_SPECS,
)

# ═══════════════════════════════════════════════════════════
# MLT XML export
# ═══════════════════════════════════════════════════════════

from kb.tools.mlt_export import (
    export_mlt,
    render_mlt,
    export_fcpxml,
)

# ═══════════════════════════════════════════════════════════
# Recipe runner
# ═══════════════════════════════════════════════════════════

from kb.tools.recipe_runner import run_recipe

# ═══════════════════════════════════════════════════════════
# Content adapter (Pexels + Freesound)
# ═══════════════════════════════════════════════════════════

import kb.tools.content_adapter as _content_adapter

class _FootageModule(_types.ModuleType):
    """Convenience module: footage.search(), footage.download()"""

    def search(self, query: str, **kwargs) -> list[dict]:
        return _content_adapter.footage_search(query, **kwargs)

    def download(self, track: dict, **kwargs) -> dict:
        return _content_adapter.footage_download(track, **kwargs)

footage = _FootageModule("content_adapter")

class _SfxModule(_types.ModuleType):
    """Convenience module: sfx.search(), sfx.download()"""

    def search(self, query: str, **kwargs) -> list[dict]:
        return _content_adapter.sfx_search(query, **kwargs)

    def download(self, track: dict, **kwargs) -> dict:
        return _content_adapter.sfx_download(track, **kwargs)

sfx = _SfxModule("content_adapter")

from kb.tools.content_adapter import (
    lut_list,
    lut_apply,
)

# ═══════════════════════════════════════════════════════════
# VLM adapter (gated — Qwen2.5-VL)
# ═══════════════════════════════════════════════════════════

import kb.tools.vlm_adapter as _vlm_adapter

class _VlmModule(_types.ModuleType):
    """Convenience module: vlm.describe_frame(), vlm.find_moment(), etc."""

    def describe_frame(self, video: str, timestamp: float, **kwargs) -> str:
        return _vlm_adapter.describe_frame(video, timestamp, **kwargs)

    def describe_clip(self, video: str, **kwargs) -> dict:
        return _vlm_adapter.describe_clip(video, **kwargs)

    def find_moment(self, video: str, query: str, **kwargs) -> list[dict]:
        return _vlm_adapter.find_moment(video, query, **kwargs)

    def verify_claim(self, video: str, timestamp: float, claim: str, **kwargs) -> dict:
        return _vlm_adapter.verify_claim(video, timestamp, claim, **kwargs)

    @property
    def available(self) -> bool:
        return _vlm_adapter._check_vlm()

vlm = _VlmModule("vlm_adapter")

# ═══════════════════════════════════════════════════════════════
# Deprecation helpers — `from kb.tools.unified_adapter import edit`
# ═══════════════════════════════════════════════════════════════

import sys as _sys

class _UnifiedEditModule(_types.ModuleType):
    """Convenience module: edit.info(), edit.trim(), etc."""

_unified_edit = _UnifiedEditModule("unified_adapter")
_unified_edit.__dict__.update({k: v for k, v in globals().items() if not k.startswith("_")})
edit = _unified_edit


__all__ = [
    # Overlapping (mcp_video wins)
    "info", "trim", "resize", "speed", "stabilize", "color_grade", "text_subtitles",
    # MCP-unique
    "video_info_detailed", "inspect", "search_tools",
    "crop", "rotate", "reverse", "blur", "fade",
    "ai_color_grade", "effect_chromatic_aberration", "effect_glow",
    "effect_noise", "effect_scanlines", "effect_vignette",
    "normalize_audio", "audio_compose", "audio_effects", "audio_preset",
    "audio_sequence", "audio_spatial", "audio_synthesize", "audio_waveform",
    "add_audio", "add_generated_audio", "extract_audio",
    "subtitles_styled", "subtitles", "generate_subtitles", "add_text", "text_animated",
    "layout_pip", "layout_grid", "split_screen", "overlay_video", "watermark",
    "transition_glitch", "transition_morph", "transition_pixelate",
    "detect_scenes", "ai_scene_detect", "auto_chapters",
    "quality_check", "assert_quality", "compare_quality",
    "design_quality_check", "fix_design_issues", "analyze_video", "analyze_product",
    "export", "convert", "preview", "hls_segment",
    "thumbnail", "extract_frame", "export_frames", "storyboard",
    "chroma_key", "luma_key", "apply_mask", "shape_mask",
    "ai_stem_separation", "ai_upscale",
    "read_metadata", "write_metadata", "extract_colors", "generate_palette",
    "batch", "repurpose", "repurpose_plan", "release_checkpoint",
    "mograph_count", "mograph_progress",
    "filter", "edit_timeline", "create_from_images",
    "hyperframes_init", "hyperframes_info", "hyperframes_validate",
    "hyperframes_render", "hyperframes_preview", "hyperframes_snapshot",
    "hyperframes_still", "hyperframes_compositions", "hyperframes_capture",
    "hyperframes_to_mcpvideo", "hyperframes_transcribe", "hyperframes_tts",
    "hyperframes_doctor", "hyperframes_catalog", "hyperframes_benchmark",
    "hyperframes_add_block", "hyperframes_remove_background",
    # Audited (ours)
    "merge", "silence_remove", "transcribe",
    # Unique (ffmpeg_adapter)
    "j_cut", "l_cut", "j_l_cut_sequence",
    "loudnorm", "loudnorm_limited",
    "scope_waveform", "scope_vectorscope", "scope_histogram", "scope_parade", "scope_analyze",
    "probe", "verify",
    "quality_vmaf", "quality_psnr", "quality_ssim", "quality_audio", "quality_full_qc",
    "RENDER_PROFILES", "render", "render_multi",
    "project_create", "project_step", "project_resume", "project_snapshot", "project_audit_report",
    # Deprecated aliases
    "scene_detect", "pip",
    # Music (adapter)
    "music",
    # Content adapter
    "footage", "sfx", "lut_list", "lut_apply",
    # Compliance reporter
    "compliance_report", "list_specs", "COMPLIANCE_SPECS",
    # MLT export
    "export_mlt", "render_mlt", "export_fcpxml",
    # Recipe runner
    "run_recipe",
    # VLM adapter (gated)
    "vlm",
    # Convenience
    "edit", "mcp_available",
]
