---
title: MCP Servers for Video Editing
type: entity
tags: [mcp, servers, ffmpeg, editing]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [make-my-clip, cutagent, video-use, free-ai-video-editing-stack]
---

# MCP Servers for Video Editing

MCP (Model Context Protocol) servers let any AI agent (Claude Desktop, Cline, Cursor, OpenCode) call video editing tools directly. These are the easiest way to give an AI agent video editing capabilities — the server wraps FFmpeg into typed, callable tools.

## Best Overall: mcp-video

**mcp-video** ([KyaniteLabs/mcp-video](https://github.com/KyaniteLabs/mcp-video)) is the most comprehensive option with 106 tools.

**Capabilities:**
- Trim, merge, resize, crop, rotate, convert
- Color grading (brightness, contrast, saturation, curves)
- AI transcription via Whisper
- Scene detection, silence removal, auto-chapters
- Upscaling (Real-ESRGAN), stem separation (Demucs)
- Visual effects, transitions, procedural audio
- Layout/grid, picture-in-picture, animated text
- Quality checks, social format repurposing
- Subtitles: extract, burn, add track

**Install:** `pip install mcp-video` or `uvx mcp-video`
**Free:** ✅ Open-source, Apache 2.0
**Requires:** FFmpeg on PATH

## Feature Comparison

| Server | Tools | Highlights | Install |
|--------|-------|-----------|---------|
| [mcp-video](https://github.com/KyaniteLabs/mcp-video) | 119 | Most comprehensive, color grading, Whisper, scene detection | `pip install mcp-video` |
| [VEMCP](https://github.com/dahshury/video_editing_mcp) | 20+ | Pipeline architecture, color grading, chroma key, CUDA | `git clone + uv run` |
| [mcp-video-editor](https://github.com/chandler767/mcp-video-editor) | 25+ | Go binary (9MB, zero deps), color grade, chroma key, AI vision | Download binary |
| [ffmpeg-mcp](https://github.com/dubnium0/ffmpeg-mcp) | 40+ | Probe, convert, effects, subtitles, streaming, HLS/DASH | `git clone + uv run` |
| [vfx-mcp](https://github.com/connerohnesorge/vfx-mcp) | 15+ | Trim, concat, effects, speed, reverse | `uv run mcp` |
| [mcp-ffmpeg](https://github.com/kevinten-ai/mcp-ffmpeg) | 30+ | Trim, concat with xfade, B-roll overlay, silence removal | `git clone` |
| [studiomeyer mcp-video](https://github.com/studiomeyer-io/mcp-video) | 8 | Cinema-grade: 22 LUT presets, chroma key, beat sync, screen record | Node.js 18+ |
| [ffmpeg-mcp](https://github.com/yubraaj11/ffmpeg-mcp) | 12 | Simple, composable, well-validated | `uv run main.py` |
| [media-mcp-editor](https://github.com/ofekfell/media-mcp-editor) | 15+ | Trim, cut, scale, rotate, blur, fade, speed, crossfade | `git clone` |
| [VibeStudio](https://github.com/wizenheimer/vibestudio) | 10 | Pure Bash, zero runtime deps | `chmod +x` scripts |

## Transcription / Subtitle MCP Servers

| Server | What it does | Install |
|--------|-------------|---------|
| [mcp-server-whisper](https://github.com/shdwkl/mcp-server-whisper) | Multi-model transcription, SRT/VTT output, local + cloud | `pip install mcp-server-whisper` |
| [media-transcriber-mcp](https://github.com/raultov/media-transcriber-mcp) | Transcribe files + URLs, translation, SRT output | `pip install media-transcriber-mcp` |
| [Subtitles King MCP](https://github.com/kirillzubovsky/subtitlesking-mcp) | Whisper → burn subtitles into video, self-host | Download binary |
| [Fast-Whisper-MCP](https://github.com/BigUncle/Fast-Whisper-MCP-Server) | CUDA-accelerated, batch processing, VAD filtering | `pip install -r requirements.txt` |
| [whisper-transcribe-mcp](https://github.com/ZahiriNatZuke/whisper-transcribe-mcp) | Dual backend: local faster-whisper or OpenAI API | `uvx whisper-transcribe-mcp` |

## NLE Control MCP Servers

| Server | NLE | What it does |
|--------|-----|-------------|
| [mcp-kdenlive](https://github.com/D-Ogi/mcp-kdenlive) | Kdenlive | D-Bus MCP server — build timelines, add effects, render |
| [kdenlive-mcp](https://github.com/IO-AtelierTech/kdenlive-automation) | Kdenlive | 60+ tools via WebSocket JSON-RPC |

## How to use with your agent

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

### Cline / Cursor
Add to MCP settings file:
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

### OpenCode
MCP servers can be configured in the OpenCode settings.

## Key insight

All of these are **free and open-source**. The only cost is the LLM you use to drive them. If you use a local model (Ollama), the entire stack is $0.
