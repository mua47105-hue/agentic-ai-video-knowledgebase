---
title: MCP Server Comparison Matrix — 2026
type: comparison
tags: [mcp, servers, comparison, ffmpeg, editing]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [mcp-video-servers, free-ai-video-editing-stack, make-my-clip, cutagent]
---

# MCP Server Comparison Matrix — 2026

Comprehensive comparison of every known free/open-source MCP server for video editing. All are free — the only cost is the LLM driving them.

## The Contenders

| # | Server | Tools | Language | License | Stars | Updated | Install |
|---|--------|-------|----------|---------|-------|---------|---------|
| 1 | [mcp-video](https://github.com/KyaniteLabs/mcp-video) | 119 | Python | Apache 2.0 | ~61 | May 2026 | `pip install mcp-video` |
| 2 | [VEMCP](https://github.com/dahshury/video_editing_mcp) | 20+ | Python | MIT | New | Jan 2026 | `git clone + uv run` |
| 3 | [mcp-video-editor](https://github.com/chandler767/mcp-video-editor) | 25+ | Go | MIT | ~30 | 2025 | Download 9MB binary |
| 4 | [ffmpeg-mcp (dubnium0)](https://github.com/dubnium0/ffmpeg-mcp) | 40+ | Python | MIT | ~16 | Feb 2026 | `git clone + pip install` |
| 5 | [vfx-mcp](https://github.com/connerohnesorge/vfx-mcp) | 15+ | Python | MIT | ~10 | 2025 | `uv run mcp` |
| 6 | [mcp-ffmpeg (kevinten)](https://github.com/kevinten-ai/mcp-ffmpeg) | 30+ | Python | MIT | ~20 | 2025 | `git clone` |
| 7 | [mcp-video (studiomeyer)](https://github.com/studiomeyer-io/mcp-video) | 8 | Node.js | MIT | ~15 | 2025 | Node.js 18+ |
| 8 | [ffmpeg-mcp (yubraaj11)](https://github.com/yubraaj11/ffmpeg-mcp) | 12 | Python | MIT | ~5 | Aug 2025 | `uv run` |
| 9 | [media-mcp-editor](https://github.com/ofekfell/media-mcp-editor) | 15+ | Python | MIT | ~8 | 2025 | `git clone` |
| 10 | [VibeStudio](https://github.com/wizenheimer/vibestudio) | 10 | Bash | MIT | ~12 | 2025 | `chmod +x` scripts |
| 11 | [ffmpeg-mcp (mrdainami)](https://github.com/mrdainami/ffmpeg-mcp) | 2 | JS | MIT | ~2 | May 2026 | `.mcpb` binary |
| 12 | [video-audio-mcp](https://github.com/misbahsy/video-audio-mcp) | 15+ | Python | MIT | ~5 | 2025 | `pip install` |

## Feature Matrix

| Feature | mcp-video | VEMCP | mcp-video-editor | ffmpeg-mcp(dub) | vfx-mcp | mcp-ffmpeg | stud.me | yubraaj11 | media-mcp | VibeSt. | mrdainami |
|---------|-----------|-------|-----------------|-----------------|---------|------------|---------|-----------|-----------|---------|-----------|
| Trim/cut | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚡ |
| Merge/concat | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚡ |
| Resize/scale | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ⚡ |
| Crop | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | ✅ | ✅ | ✅ | ⚡ |
| Rotate | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — | — | — | ⚡ |
| Speed change | ✅ | ✅ | — | ✅ | ✅ | ✅ | — | — | ✅ | ✅ | ⚡ |
| Reverse | ✅ | — | — | ✅ | — | — | — | — | — | — | ⚡ |
| Color grading | ✅ | ✅ | ✅ | ✅ | — | — | ✅ | — | — | — | ⚡ |
| Color curves | ✅ | ✅ | — | — | — | — | ✅ | — | — | — | — |
| LUT presets | ✅ | — | — | — | — | — | ✅ | — | — | — | — |
| Subtitles | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | — | — | ⚡ |
| Transcription | ✅ | ✅ | ✅ | — | — | — | — | — | — | — | ⚡ |
| Scene detection | ✅ | — | — | — | — | ✅ | — | — | — | — | ⚡ |
| Silence removal | ✅ | — | — | — | — | ✅ | — | — | — | — | — |
| Stabilization | ✅ | — | — | ✅ | — | — | — | — | — | — | ⚡ |
| Denoise | ✅ | — | — | ✅ | — | — | — | — | — | — | ⚡ |
| Chroma key | ✅ | — | ✅ | — | — | — | ✅ | — | — | — | — |
| Overlay/PiP | ✅ | — | — | — | — | ✅ | — | ✅ | — | — | ⚡ |
| Transitions | ✅ | — | — | — | ✅ | ✅ | — | ✅ | ✅ | — | ⚡ |
| Text/titles | ✅ | — | — | — | — | — | — | — | — | — | ⚡ |
| Audio extract | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ | ⚡ |
| Audio effects | ✅ | ✅ | — | ✅ | — | — | — | — | — | — | ⚡ |
| Audio synthesis | ✅ | — | — | — | — | — | — | — | — | — | — |
| Stem separation | ✅ | — | — | — | — | — | — | — | — | — | — |
| Upscaling | ✅ | — | — | — | — | — | — | — | — | — | ⚡ |
| GIF creation | ✅ | — | — | — | — | — | — | ✅ | — | ✅ | ⚡ |
| Grid/mosaic | ✅ | — | — | ✅ | — | — | — | — | — | — | ⚡ |
| Streaming | — | — | — | ✅ | — | — | — | — | — | — | — |
| Custom FFmpeg | — | — | — | ✅ | — | — | — | — | — | — | ✅ |
| Motion graphics | ✅ | — | — | — | — | — | — | — | — | — | — |
| Video analysis | ✅ | ✅ | — | ✅ | — | — | — | — | — | — | ⚡ |
| AI upscale | ✅ | — | ✅ | — | — | — | — | — | — | — | — |
| NLE control | — | — | — | — | — | — | — | — | — | — | — |

> ⚡ = Agent writes raw FFmpeg, server just executes (mrdainami approach)

## Transcription MCP Servers

| Server | Backend | Formats | Batch | CUDA | Install |
|--------|---------|---------|-------|------|---------|
| [mcp-server-whisper](https://github.com/shdwkl/mcp-server-whisper) | whisper.cpp / OpenAI | SRT, VTT, JSON, TXT | ✅ | ✅ | `pip install mcp-server-whisper` |
| [media-transcriber-mcp](https://github.com/raultov/media-transcriber-mcp) | faster-whisper | SRT, VTT, TXT | ✅ | ✅ | `pip install media-transcriber-mcp` |
| [Subtitles King MCP](https://github.com/kirillzubovsky/subtitlesking-mcp) | Whisper | SRT, burned-in | — | — | Download binary |
| [Fast-Whisper-MCP](https://github.com/BigUncle/Fast-Whisper-MCP-Server) | faster-whisper | SRT | ✅ | ✅ | `pip install -r requirements.txt` |
| [whisper-transcribe-mcp](https://github.com/ZahiriNatZuke/whisper-transcribe-mcp) | faster-whisper / OpenAI | SRT, VTT, JSON | — | ✅ | `uvx whisper-transcribe-mcp` |

## NLE Control MCP Servers

| Server | NLE | Protocol | Tools | Install |
|--------|-----|----------|-------|---------|
| [mcp-kdenlive](https://github.com/D-Ogi/mcp-kdenlive) | Kdenlive | D-Bus | 10+ | `git clone` |
| [kdenlive-mcp](https://github.com/IO-AtelierTech/kdenlive-automation) | Kdenlive | WebSocket JSON-RPC | 60+ | Node.js |
| [cli-anything-kdenlive](https://pypi.org/project/cli-anything-kdenlive/) | Kdenlive | MLT XML | Declarative | `pip install` |
| [cli-anything-shotcut](https://pypi.org/project/cli-anything-shotcut/) | Shotcut | MLT XML | Declarative | `pip install` |

## Winner by Use Case

| You want to... | Best Server | Why |
|---------------|-------------|-----|
| **Maximum capability** | mcp-video | ~140 tools, everything built-in |
| **Simple, focused editing** | ffmpeg-mcp (yubraaj11) | 12 composable tools, well-validated |
| **Pipeline / multi-step** | VEMCP | Pipeline architecture, single-pass render |
| **Zero-dependency** | mcp-video-editor | 9MB Go binary, nothing to install |
| **Just execute (agent writes FFmpeg)** | ffmpeg-mcp (mrdainami) | 2 tools: download + shell_run |
| **Professional timeline** | mcp-kdenlive + kdenlive-mcp | Full NLE control with Kdenlive |
| **Subtitles + transcription** | mcp-server-whisper | Multi-model, multi-format |
| **HLS/DASH streaming** | ffmpeg-mcp (dubnium0) | Only server with streaming tools |
| **Bash-only / no Python** | VibeStudio | Pure Bash, zero runtime deps |

## Key Insight

**mcp-video** leads on raw tool count and breadth (~140 tools, Apache 2.0, 690+ tests, security-audited). But for most workflows, you don't need 119 tools — a focused server like VEMCP (pipeline) or yubraaj11's ffmpeg-mcp (composable blocks) gives you what you need with less context overhead. And for maximum flexibility, mrdainami's 2-tool approach lets the agent write any FFmpeg command itself.

The NLE servers (mcp-kdenlive, kdenlive-mcp) are a separate category — they control a desktop app rather than wrapping FFmpeg. Use them for multi-track timeline work that's impractical with raw FFmpeg.

## MCP Server Architecture Comparison

| Approach | Example | Pros | Cons |
|----------|---------|------|------|
| **Tool-per-operation** | mcp-video, ffmpeg-mcp | Simple, discoverable, good for agents | Many tools, large context |
| **Pipeline** | VEMCP | Single-pass, efficient | Complex, fewer tools |
| **Minimal executor** | mrdainami ffmpeg-mcp | Total flexibility, lean | Agent must know FFmpeg |
| **NLE control** | kdenlive-mcp | Professional timeline power | Needs Kdenlive installed |

## How to Choose

1. **Start with mcp-video** for maximum capability — if it doesn't have a tool for what you need, nothing will
2. **Switch to a lighter server** (VEMCP, yubraaj11 ffmpeg-mcp) if context overhead is a concern
3. **Add a transcription server** (mcp-server-whisper) for subtitle workflows
4. **Add an NLE server** (kdenlive-mcp) when you need professional multi-track editing
5. **Use mrdainami's ffmpeg-mcp** as a fallback — it can execute any FFmpeg command your agent writes
