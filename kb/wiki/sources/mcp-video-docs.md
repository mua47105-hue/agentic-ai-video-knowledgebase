---
title: mcp-video — MCP Server for Video Editing Using FFmpeg
type: source
tags: [tool, mcp-server, ffmpeg, video-editing]
created: 2026-07-08
updated: 2026-07-08
related: [mcp-video, unified-adapter, mcp-video-servers]
---

# mcp-video Documentation

## Citation
"mcp-video: MCP server for video editing using FFmpeg." PyPI package, Apache 2.0, 2025-2026. https://pypi.org/project/mcp-video/

Repository: https://github.com/anthropics/mcp-video (or successor organization)

## Key claims
- Provides **106 typed, callable tools** for video editing via MCP protocol — the largest open-source MCP video server by tool count.
- Tool categories: probe (12), transform (28), filter (18), audio (15), subtitle (10), quality (8), utility (15).
- Every tool has typed parameters, schema, and error handling — no raw FFmpeg string construction needed.
- Uses FFmpeg under the hood but abstracts away command construction, flag ordering, and edge cases.
- Known bugs (documented in the unified adapter): `merge` has incorrect offset math for n > 2 clips; `ai_remove_silence` causes 11.62s A/V desync; `speed` can produce audio stutter if atempo not paired with setpts.
- Licensing: Apache 2.0 — permissive for commercial and research use.

## How this connects to the wiki
- **mcp-video entity**: The `entities/mcp-video.md` page documents all 106 tools and their categories. This source is the primary reference for that page.
- **Unified Adapter**: `kb/tools/unified_adapter.py` routes 151 symbols — 106 from mcp-video plus 45 from the proprietary ffmpeg_adapter and new modules — and automatically routes around the 4 known bugs listed above.
- **MCP Server Matrix**: The `comparisons/mcp-servers-2026.md` comparison ranks mcp-video as the most comprehensive MCP video server. This source supports that ranking.

## Contradictions with existing pages
- The wiki states "106 tools" but the exact count may vary between PyPI releases. The wiki should be updated if subsequent releases change the count.

## Notes
- mcp-video requires Python 3.10+ and an MCP-compatible host (Claude Desktop, OpenCode, Cursor, custom MCP client).
- The unified adapter is the recommended surface for all recipe operations: it tests for mcp-video availability and falls back to raw FFmpeg when mcp-video is absent or buggy.
- The known-bug documentation in the wiki came from independent testing, not from the mcp-video maintainers.
