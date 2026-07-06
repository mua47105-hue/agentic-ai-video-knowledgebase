---
title: Complete Free AI Video Editing Stack
type: guide
tags: [guide, free, stack, local, ffmpeg]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [mcp-video-servers, video-use, make-my-clip, cutagent, whisper-ecosystem]
---

# Complete Free AI Video Editing Stack

A fully free, local, open-source stack for editing videos using AI agents. No subscriptions, no API keys, no cloud dependencies (except optional LLM access).

## The Stack

```
You (describe what you want)
  │
  ▼
LLM Agent (Claude Code / OpenCode / Ollama)
  │
  ├──► MCP Server (mcp-video / ffmpeg-mcp) ──► FFmpeg (edit video)
  ├──► Whisper (whisper.cpp / faster-whisper) ──► Subtitles
  ├──► melt (Kdenlive/Shotcut headless) ──► Professional timeline
  └──► Remotion (programmatic video) ──► Motion graphics
```

## Option 1: MCP Server Stack (Recommended for beginners)

This is the simplest way to get started. An MCP server exposes video editing tools to any MCP-compatible AI agent.

### Components

| Component | Tool | Cost | Role |
|-----------|------|------|------|
| LLM Agent | Claude Code / OpenCode / Ollama | Free (Ollama local) or free-tier Claude | Understands your intent, calls tools |
| MCP Server | [mcp-video](../entities/mcp-video-servers) | Free (open-source) | 119 FFmpeg tools callable by the agent |
| Subtitles | whisper.cpp / faster-whisper | Free (local) | Transcribe audio → SRT |
| Execution | FFmpeg | Free (pre-installed or `brew install ffmpeg`) | Does the actual video processing |

### Setup

```bash
# 1. Install FFmpeg
brew install ffmpeg    # macOS
sudo apt install ffmpeg # Linux

# 2. Install MCP server
pip install mcp-video
# or: uvx mcp-video

# 3. Install whisper (for subtitles)
pip install faster-whisper
# or: brew install whisper-cpp

# 4. Configure your AI agent to use the MCP server
# In Claude Desktop: Add to mcp_servers config
# In Cline/Cursor: Add to MCP settings
```

### What you can do

Once set up, tell your agent:

- "Trim the first 30 seconds from this video"
- "Add subtitles from the audio track"
- "Cut out all the silences and pauses"
- "Merge these three clips with a crossfade transition"
- "Stabilize this shaky footage"
- "Color grade this clip for a warm cinematic look"
- "Extract all scenes where the speaker mentions 'innovation'"

The agent calls MCP tools like `trim_video`, `burn_subtitles`, `detect_silence`, `merge_clips` — you don't write FFmpeg commands.

## Option 2: FFmpeg + LLM Agent (Advanced)

Direct FFmpeg command generation. The LLM writes FFmpeg commands based on your description.

### Tools

| Tool | How it works | Free? |
|------|-------------|-------|
| [wtffmpeg](https://github.com/scottvr/wtffmpeg) | REPL: describe edit → gets FFmpeg command → execute | ✅ Free with Ollama |
| [FFmigo](https://github.com/apurvns/FFmigo) | GUI chat: English → FFmpeg | ✅ Free with Ollama |
| [llmpeg](https://github.com/ali-master/llmpeg) | CLI: English → FFmpeg, 30+ presets | ⚠️ Needs API key |
| [CutAgent](https://github.com/DaKev/cutagent) | Python lib: declarative EDL, scene/silence detection | ✅ Free, MCP-ready |

### Example with Ollama (fully local)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2

# Use wtffmpeg with local LLM
pip install wtffmpeg
wtffmpeg --model ollama:llama3.2
# Then: "cut the first 10 seconds and add a fade in"
```

## Option 3: Full NLE Control (Professional)

Drive a professional non-linear editor (NLE) programmatically via an AI agent.

| Tool | NLE | How |
|------|-----|-----|
| [cli-anything-kdenlive](https://pypi.org/project/cli-anything-kdenlive/) | Kdenlive | Generate MLT XML, render headlessly via `melt` |
| [cli-anything-shotcut](https://pypi.org/project/cli-anything-shotcut/) | Shotcut | Generate MLT XML, render via `melt` |
| [mcp-kdenlive](https://github.com/D-Ogi/mcp-kdenlive) | Kdenlive | D-Bus MCP server — build timelines, add effects, render |
| [kdenlive-mcp](https://github.com/IO-AtelierTech/kdenlive-automation) | Kdenlive | 60+ tools via WebSocket JSON-RPC |

These give you **professional-grade editing** (multi-track timelines, keyframe effects, transitions, color grading) driven entirely by an AI agent. No GUI needed — the agent builds the project file and renders it.

## Option 4: Programmatic Video with Remotion

For motion graphics, animated text, and complex compositions.

```bash
# Install Remotion + agent skills
npx create-video@latest
npx skills add remotion-dev/skills

# Tell your agent: "Create a video with animated title cards, 
# transitions between scenes, and a synchronized voiceover"
```

Remotion is free for individuals and companies <3 employees. The agent writes React/TSX components and renders them.

## Recommended Free Stack by Use Case

| What you want | Stack |
|--------------|-------|
| "Edit my existing footage" | MCP Server + FFmpeg (Option 1) |
| "I want to learn FFmpeg" | Ollama + wtffmpeg (Option 2) |
| "Professional multi-track editing" | Kdenlive + cli-anything-kdenlive (Option 3) |
| "Animated motion graphics" | Remotion (Option 4) |
| "Everything combined" | MCP Server + Remotion + Whisper |

## LLM Options (Free)

| Option | Cost | Quality |
|--------|------|---------|
| Ollama (llama3.2, qwen2.5) | Free, local | Good for simple edits |
| Claude Code (free tier) | Free (limited) | Excellent |
| OpenCode (free tier) | Free (limited) | Excellent |
| Groq API | Free tier available | Fast, good |
| GitHub Copilot | Free (with GitHub Student) | Good |

For complex editing workflows, cloud LLMs are more reliable. For simple trim/cut/subtitle workflows, local models work fine.
