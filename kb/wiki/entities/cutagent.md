---
title: CutAgent
type: entity
tags: [ffmpeg, python, edl, scene-detection, mcp]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [make-my-clip, mcp-video-servers, whisper-ecosystem]
---

# CutAgent

FFmpeg for AI agents. Every command returns structured JSON with recovery hints. Declarative EDL (Edit Decision List) format. Built-in scene detection, silence detection, beat detection, keyframe extraction, audio level analysis. MCP-ready.

## Architecture

Python library that wraps FFmpeg with structured JSON output. Every operation returns machine-readable results the agent can act on.

## Capabilities

- **Scene detection** — detect shot boundaries, return timestamps
- **Silence detection** — find pauses and gaps
- **Beat detection** — detect musical beats for rhythm-aligned cuts
- **Keyframe extraction** — extract representative frames
- **Audio levels** — measure loudness, normalize
- **Declarative EDL** — define edits as structured JSON, not raw FFmpeg flags
- **Recovery hints** — on failure, returns suggested fixes the agent can apply

## Key differentiator

Designed specifically for AI agent consumption. Every output is structured JSON. Includes recovery hints so the agent can self-correct on failures. The declarative EDL format is more agent-friendly than raw FFmpeg commands.

## Install

```bash
pip install cutagent
```

## Links

- [GitHub](https://github.com/DaKev/cutagent)
