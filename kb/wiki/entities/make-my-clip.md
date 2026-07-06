---
title: MakeMyClip Editor
type: entity
tags: [ffmpeg, local, mit, mcp, skill]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [mcp-video-servers, cutagent, free-ai-video-editing-stack]
---

# MakeMyClip Editor

"FFmpeg you can talk to." MIT-licensed, local-first video editing tool. Ships as a Claude Code skill + CLI + browser UI + MCP server. 19 deterministic FFmpeg tools any agent can call. No cloud, no account, no telemetry, no API key required.

## Architecture

- **Core**: 19 deterministic FFmpeg tools (trim, merge, crop, resize, subtitles, speed, audio, etc.)
- **Interface**: Claude Code skill + CLI + web browser UI + MCP server
- **Design**: No cloud dependencies, no telemetry, runs entirely on your machine
- **FFmpeg**: Bundled via `ffmpeg-static` — no separate install needed

## Capabilities

- Trim, cut, merge video clips
- Resize, crop, rotate
- Add/subtitles (burn-in)
- Speed change, audio extract/replace
- Format conversion
- All operations are deterministic — same input always produces same output

## How an AI agent drives it

The agent reads the skill file which teaches it how to call the tools. The MCP server makes each operation a callable tool with typed parameters.

## Install

```bash
npx skills add MakeMyClip/editor
```

That's it. No accounts, no API keys, no cloud setup.

## Key differentiator

Zero-config. Install one command and your agent can edit videos. No API keys, no cloud dependencies, no accounts. Everything runs locally.

## Links

- [GitHub](https://github.com/MakeMyClip/editor)
