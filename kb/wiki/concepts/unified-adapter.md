---
title: Unified Adapter
type: concept
created: 2026-07-06
updated: 2026-07-06
---

# Unified Adapter

> **Single import surface combining mcp_video.Client (60+ safe wrappers) with audited ffmpeg_adapter functions.** Routes around 4 known-buggy mcp_video functions automatically. The one import agents need.

## Why

Before the unified adapter, agents had to choose between:

1. `mcp_video.Client` — 106 tools but 4 have bugs
2. `ffmpeg_adapter` — 44 functions, all audited, but no access to 60+ new capabilities

The unified adapter solves this by providing a single `edit` module that routes each function to the best implementation:

- **mcp_video** for safe functions (info, trim, detect_scenes, color_grade, audio_compose, etc.)
- **ffmpeg_adapter** for buggy/inferior mcp_video functions (merge, silence_remove, transcribe)
- **ffmpeg_adapter** for unique capabilities (J/L-cuts, scopes, project files, quality metrics)

## Architecture

```
┌─────────────────────────────────────────────┐
│          Agent / User Code                   │
│  from kb.tools.unified_adapter import edit   │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│          unified_adapter.py                  │
│  Routes each symbol to best implementation   │
└──────┬────────────────────────┬─────────────┘
       │                        │
┌──────▼──────┐          ┌──────▼──────────┐
│ _mcp_bridge │          │ ffmpeg_adapter  │
│ ~65 wrappers│          │ 44 functions    │
│ → mcp_video │          │ (audited+unique)│
│ (safe only) │          │                 │
└─────────────┘          └────────────────┘
```

## Symbols

| Category | Source | Functions |
|----------|--------|-----------|
| Overlapping (7) | mcp_video | info, trim, resize, speed, stabilize, color_grade, text_subtitles |
| MCP-Unique (92) | mcp_video | All other safe mcp_video wrappers |
| Audited (3) | ffmpeg_adapter | merge, silence_remove, transcribe |
| Unique (29) | ffmpeg_adapter | J/L-cuts, scopes, quality, project, render, loudnorm |

## Deprecation

Direct `import kb.tools.ffmpeg_adapter` emits a `DeprecationWarning`. All code should use `from kb.tools.unified_adapter import edit` instead.

## Hard Rule #25

Non-negotiable: use unified_adapter, never direct mcp_video or raw ffmpeg_adapter. Direct mcp_video.Client usage bypasses the 4 known-buggy wrappers. Direct ffmpeg_adapter usage emits a deprecation warning.

## Graceful Degradation

If `mcp_video` is not installed, the unified adapter still works — all ffmpeg_adapter functions remain available. Only the mcp_video-backed functions raise `RuntimeError("mcp_video not installed")` at call time.

## Related

- [mcp-video](../entities/mcp-video) — the MCP server providing 106 tools
- [SKILL.md](../../SKILL.md) — agent skill with all 25 Hard Rules
- [ffmpeg_adapter.py](../../kb/tools/ffmpeg_adapter.py) — audited fallback (deprecated)
