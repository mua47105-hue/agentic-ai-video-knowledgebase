---
title: AI Video Editing — Overview
type: overview
created: 2026-07-06
updated: 2026-07-06
tags: [ai-video, overview, editing, free]
related: [free-ai-video-editing-stack, mcp-video-servers, make-my-clip, cutagent, video-use]
---

# AI Video Editing — Overview

*This page is a living synthesis. It evolves as sources are ingested.*

**Focus: Free and open-source AI agents that EDIT existing video footage.** This wiki is NOT about AI video generation (Runway, Pika, Sora, Veo, etc.). It is about AI agents that take your raw footage and professionally edit it — cuts, transitions, color grading, subtitles, audio sync, pacing, and assembly.

## The core insight

You can edit videos with AI agents using a **completely free, local stack**:

```
Your footage → AI Agent (via MCP) → FFmpeg → Edited video
                                  → Whisper → Subtitles
                                  → melt → Professional timeline
```

The agent understands your intent, calls the right tools, and produces the finished edit. All the tools are free and open-source. The only variable is which LLM you use — local models (Ollama) are free, cloud models give better results.

## How it works

1. **Agent understands** what you want (natural language)
2. **Agent calls tools** via MCP servers (trim, cut, merge, subtitle, color grade)
3. **FFmpeg executes** the operations (free, battle-tested, runs everything)
4. **Agent reviews** the output and iterates

## What's possible today (for free)

- Trim and cut footage based on transcript content
- Auto-generate and burn subtitles
- Remove silences and filler words
- Merge clips with transitions
- Color grading and effects
- Scene detection and shot selection
- Audio sync and leveling
- Professional multi-track editing (via Kdenlive headless)

## Current wiki contents

- **Editing tools (16 active)**: MCP Servers, video-use, MakeMyClip, CutAgent, CutRoom, OpenMontage, AVE, AI_Editor, Crayotter, VideoAgent, UniVA, CutClaw, X-Cut, Pilipili-AutoVideo, Project Montage, Whisper Ecosystem
- **MCP ecosystem**: 15+ free MCP servers for FFmpeg operations (119 tools in mcp-video) + 12-server comparison matrix
- **Transcription**: Whisper ecosystem (whisper.cpp, faster-whisper, WhisperX)
- **Guides**: Complete free stack setup, FFmpeg command reference (100+ patterns), local LLM setup (Qwen2.5-Coder 88% accuracy), build-your-own blueprint (5 levels), recipe packs (6 YAML workflows)
- **Recipe packs**: 6 one-command YAML workflow templates (podcast-to-shorts, wedding highlights, sports highlights, documentary assembly, tutorial editing, vlog assembly)
- **Skills**: `SKILL.md` at root — 5-phase decision engine, 12 Hard Rules, production techniques, MCP mappings
- **Agent prompt**: `scripts/agent-prompt.md` — universal copy-paste system prompt for any LLM
- **Setup script**: `scripts/setup.sh` — one-command install (FFmpeg + MCP + Whisper + Ollama)
- **Comparisons**: MCP server feature matrix (12 servers, 30+ dimensions), 10 agentic frameworks, AI video models
- **Charts**: Model quality vs speed vs cost (matplotlib)
- **Extended tools**: MLT XML export (Kdenlive/Shotcut interop), compliance reporter (6 delivery specs), content adapter (Pexels + Freesound), VLM adapter (Qwen2.5-VL, gated)
- **Archive (9 gen models)**: Runway Gen-4, Pika 2.5, Veo 3, Sora, Kling 3.0, Nano Banana, EzVideo, Shorz, Magicroll

## Key questions

1. What free tools can I use TODAY to edit videos with an AI agent?
2. How do I set up the complete stack (MCP + Whisper + FFmpeg)?
3. What can local LLMs handle vs. when do I need cloud LLMs?
4. What MCP server gives me the most editing capabilities?
5. How do professional NLEs (Kdenlive, Shotcut) fit into an agentic workflow?

## Quick start

```bash
# Install the core stack
pip install mcp-video
pip install faster-whisper
brew install ffmpeg

# Configure your AI agent to use mcp-video
# Then say: "Edit this video. Remove pauses, add subtitles, and color grade it."
```
