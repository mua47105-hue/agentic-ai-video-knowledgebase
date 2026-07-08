"""
Tool Registry — single source of truth for the edit.* tool surface.

Instead of maintaining tool tables in CLAUDE.md, AGENTS.md, and kb/wiki/tools/*.md
by hand, this registry generates them from code. The registry is a list of
ToolEntry dataclasses, each describing: name, category, module, summary.

Phase 2 of the upgrade plan.

Public surface:
  - TOOL_REGISTRY (list[ToolEntry])
  - tools_by_category() -> dict[str, list[ToolEntry]]
  - generate_tools_json() -> dict (machine-readable)
  - generate_tools_markdown() -> str (human-readable wiki page)
"""
from __future__ import annotations

import dataclasses
import json
import typing as t


@dataclasses.dataclass(frozen=True)
class ToolEntry:
    """A single tool in the edit.* surface."""
    name: str
    category: str  # "core", "color", "audio", "subtitle", "fx", "layout", "quality", "project", "hyperframes"
    summary: str
    has_ffmpeg_fallback: bool = False
    related_hard_rules: list[str] = dataclasses.field(default_factory=list)


TOOL_REGISTRY: list[ToolEntry] = [
    # ── Core (probe, trim, resize, speed) ──
    ToolEntry("info", "core", "Get video metadata (duration, resolution, codecs)", has_ffmpeg_fallback=True),
    ToolEntry("trim", "core", "Trim/cut a video segment", has_ffmpeg_fallback=True, related_hard_rules=["HR#7"]),
    ToolEntry("resize", "core", "Resize/scale a video", has_ffmpeg_fallback=True),
    ToolEntry("speed", "core", "Change playback speed (atempo+setpts)", has_ffmpeg_fallback=True, related_hard_rules=["HR#2"]),
    ToolEntry("crop", "core", "Crop a video region"),
    ToolEntry("rotate", "core", "Rotate/flip a video"),
    ToolEntry("reverse", "core", "Reverse video playback", has_ffmpeg_fallback=True),
    ToolEntry("stabilize", "core", "Stabilize shaky footage", has_ffmpeg_fallback=True),
    ToolEntry("detect_scenes", "core", "Detect scene changes", has_ffmpeg_fallback=True),
    ToolEntry("extract_audio", "core", "Extract audio track", has_ffmpeg_fallback=True),

    # ── Color ──
    ToolEntry("color_grade", "color", "Apply color grading preset", has_ffmpeg_fallback=True, related_hard_rules=["HR#13", "HR#14"]),
    ToolEntry("ai_color_grade", "color", "AI-powered color grading"),
    ToolEntry("blur", "color", "Apply blur effect"),
    ToolEntry("fade", "color", "Fade in/out transitions"),

    # ── Effects ──
    ToolEntry("effect_chromatic_aberration", "fx", "Chromatic aberration effect"),
    ToolEntry("effect_glow", "fx", "Glow effect"),
    ToolEntry("effect_noise", "fx", "Film noise/grain effect"),
    ToolEntry("effect_scanlines", "fx", "CRT scanline effect"),
    ToolEntry("effect_vignette", "fx", "Vignette effect"),

    # ── Audio ──
    ToolEntry("normalize_audio", "audio", "Normalize audio levels"),
    ToolEntry("audio_compose", "audio", "Compose multiple audio tracks"),
    ToolEntry("audio_effects", "audio", "Apply audio effects chain"),
    ToolEntry("audio_preset", "audio", "Apply audio preset"),
    ToolEntry("add_audio", "audio", "Add/overlay audio track"),
    ToolEntry("add_generated_audio", "audio", "Add AI-generated audio"),

    # ── Subtitles & Text ──
    ToolEntry("text_subtitles", "subtitle", "Burn subtitles into video", has_ffmpeg_fallback=True, related_hard_rules=["HR#9", "HR#12"]),
    ToolEntry("subtitles_styled", "subtitle", "Burn styled ASS subtitles"),
    ToolEntry("subtitles", "subtitle", "Add subtitle track (non-burned)"),
    ToolEntry("generate_subtitles", "subtitle", "Auto-generate subtitles via Whisper"),
    ToolEntry("add_text", "subtitle", "Add text overlay"),
    ToolEntry("text_animated", "subtitle", "Add animated text"),

    # ── Layout ──
    ToolEntry("layout_pip", "layout", "Picture-in-picture layout"),
    ToolEntry("layout_grid", "layout", "Grid layout (multi-video)"),
    ToolEntry("split_screen", "layout", "Split-screen layout"),
    ToolEntry("overlay_video", "layout", "Overlay one video on another"),
    ToolEntry("watermark", "layout", "Add watermark/logo"),

    # ── Quality ──
    ToolEntry("quality_check", "quality", "Check video quality"),
    ToolEntry("assert_quality", "quality", "Assert video meets quality threshold"),
    ToolEntry("compare_quality", "quality", "Compare quality of two videos"),
    ToolEntry("analyze_video", "quality", "Full video analysis"),

    # ── Project (ffmpeg_adapter unique) ──
    ToolEntry("render", "project", "Render with delivery profile", related_hard_rules=["HR#19"]),
    ToolEntry("render_multi", "project", "Render multiple outputs"),
    ToolEntry("loudnorm", "project", "Two-pass loudness normalization", related_hard_rules=["HR#1"]),
    ToolEntry("loudnorm_limited", "project", "Limited-range loudness normalization"),
    ToolEntry("merge", "project", "Merge clips with transitions", related_hard_rules=["HR#6"]),
    ToolEntry("silence_remove", "project", "Remove silence from video"),
    ToolEntry("transcribe", "project", "Transcribe audio via faster-whisper"),
    ToolEntry("j_cut", "project", "J-cut (audio leads video)", related_hard_rules=["HR#15"]),
    ToolEntry("l_cut", "project", "L-cut (video leads audio)", related_hard_rules=["HR#15"]),
    ToolEntry("verify", "project", "Verify output (streams, duration, sync)"),
    ToolEntry("scene_detect", "project", "FFmpeg scene detection"),
    ToolEntry("pip", "project", "Picture-in-picture (ffmpeg_adapter)"),

    # ── Scopes ──
    ToolEntry("scope_waveform", "quality", "Generate waveform scope"),
    ToolEntry("scope_vectorscope", "quality", "Generate vectorscope"),
    ToolEntry("scope_histogram", "quality", "Generate histogram"),
    ToolEntry("scope_parade", "quality", "Generate RGB parade"),
    ToolEntry("scope_analyze", "quality", "Analyze scope image"),
    ToolEntry("quality_vmaf", "quality", "VMAF quality score", related_hard_rules=["HR#20"]),
    ToolEntry("quality_psnr", "quality", "PSNR quality score"),
    ToolEntry("quality_ssim", "quality", "SSIM quality score"),
    ToolEntry("quality_audio", "quality", "Audio quality check"),
    ToolEntry("quality_full_qc", "quality", "Full quality control check"),

    # ── Project files ──
    ToolEntry("project_create", "project", "Create .aevp project file", related_hard_rules=["HR#22"]),
    ToolEntry("project_step", "project", "Log a step to project file"),
    ToolEntry("project_resume", "project", "Resume from project file"),
    ToolEntry("project_snapshot", "project", "Snapshot before destructive op", related_hard_rules=["HR#23"]),
    ToolEntry("project_audit_report", "project", "Generate audit report", related_hard_rules=["HR#24"]),
]


def tools_by_category() -> dict[str, list[ToolEntry]]:
    """Group tools by category."""
    result: dict[str, list[ToolEntry]] = {}
    for tool in TOOL_REGISTRY:
        result.setdefault(tool.category, []).append(tool)
    return result


def generate_tools_json() -> str:
    """Generate machine-readable JSON of all tools."""
    data = [dataclasses.asdict(t) for t in TOOL_REGISTRY]
    return json.dumps(data, indent=2)


def generate_tools_markdown() -> str:
    """Generate a human-readable markdown wiki page of all tools."""
    lines = [
        "---",
        "title: Tool Reference (Auto-Generated)",
        "type: guide",
        "tags: [tools, reference, auto-generated]",
        "---",
        "",
        "# Tool Reference",
        "",
        "> Auto-generated from `kb/tools/tool_registry.py`. Do not edit by hand.",
        "> Run `python3 -c \"from kb.tools.tool_registry import generate_tools_markdown; print(generate_tools_markdown())\"` to regenerate.",
        "",
    ]
    for category, tools in tools_by_category().items():
        lines.append(f"## {category.title()}")
        lines.append("")
        lines.append("| Tool | Summary | FFmpeg Fallback | Hard Rules |")
        lines.append("|------|---------|-----------------|------------|")
        for t in tools:
            fb = "✅" if t.has_ffmpeg_fallback else "—"
            hr = ", ".join(t.related_hard_rules) if t.related_hard_rules else "—"
            lines.append(f"| `edit.{t.name}` | {t.summary} | {fb} | {hr} |")
        lines.append("")
    return "\n".join(lines)
