---
title: mcp-video
type: entity
tags: [tool, mcp-server, ffmpeg, video-editing]
created: 2026-07-06
updated: 2026-07-08
sources: [mcp-video-docs]
related: [unified-adapter, hyperframes, color-space-management]
---

# mcp-video

> **MCP server for video editing using FFmpeg.** Provides 106 typed, callable tools for editing, analysis, and delivery. Apache 2.0. Used as the primary tool surface via the [Unified Adapter](../concepts/unified-adapter).

## Overview

- **License**: Apache 2.0
- **Install**: `pip install mcp-video`
- **Version**: 1.5.1 (pinned)
- **Surface**: ~140 tools via `mcp_video.Client`
- **Stack**: Python → FFmpeg CLI. No GPU required.

## Architecture

`mcp_video.Client` wraps FFmpeg commands behind typed methods returning Pydantic BaseModel instances. All return values are converted to plain dicts by the bridge layer for agent compatibility.

```
Agent Code → Unified Adapter → _mcp_bridge → mcp_video.Client → FFmpeg
```

## Tool Categories (106 total)

| Category | Tools | Examples |
|----------|-------|---------|
| Core Media | 2 | info, video_info_detailed |
| Trim & Crop | 4 | trim, crop, resize, rotate |
| Speed & Stabilize | 4 | speed, reverse, stabilize, convert |
| Color & Effects | 9 | color_grade, blur, fade, effect_vignette, effect_glow |
| Audio | 15 | normalize_audio, audio_compose, audio_waveform, add_audio |
| Subtitles & Text | 6 | text_subtitles, subtitles_styled, add_text, text_animated |
| Layout | 6 | layout_pip, layout_grid, split_screen, overlay_video, watermark |
| Transitions | 3 | transition_glitch, transition_morph, transition_pixelate |
| Scene Detection | 3 | detect_scenes, ai_scene_detect, auto_chapters |
| Quality & Analysis | 12 | quality_check, analyze_video, compare_quality, repurpose |
| Export & Conversion | 6 | export, convert, preview, hls_segment, export_frames |
| Chroma Key & Mask | 4 | chroma_key, luma_key, apply_mask, shape_mask |
| AI Features | 6 | ai_stem_separation, ai_upscale, ai_color_grade, ai_scene_detect |
| Metadata | 4 | read_metadata, write_metadata, extract_colors, generate_palette |
| Batch & Workflow | 5 | batch, repurpose, release_checkpoint |
| Motion Graphics | 2 | mograph_count, mograph_progress |
| Hyperframes | 18 | hyperframes_init, hyperframes_render, hyperframes_capture |
| Other | 3 | filter, edit (timeline), create_from_images |

## Known Bugs (v1.5.1)

Four functions are bypassed in the Unified Adapter — use audited ffmpeg_adapter equivalents:

| Function | Bug | Replacement |
|----------|-----|-------------|
| `ai_remove_silence` | 11.62s A/V desync | `edit.silence_remove()` |
| `merge` | Wrong duration for >2 clips + transition | `edit.merge()` |
| `pipeline` | Broken API (`op` vs `operation`) | Skip entirely |
| `ai_transcribe` | Heavy `openai-whisper` deps (~1GB) | `edit.transcribe()` (faster-whisper) |

## Usage

```python
# Preferred: through unified adapter
from kb.tools.unified_adapter import edit
info = edit.info("video.mp4")
result = edit.trim("video.mp4", start=10, duration=30)
```

## Related

- [Unified Adapter](../concepts/unified-adapter) — how mcp_video is consumed
- [MCP Servers for Video Editing](mcp-video-servers) — comparison of all MCP servers
- [CutAgent](cutagent) — alternative FFmpeg-for-agents tool
