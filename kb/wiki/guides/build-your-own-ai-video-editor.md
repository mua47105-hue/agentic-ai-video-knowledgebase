---
title: Build Your Own AI Video Editor — Blueprint
type: guide
tags: [blueprint, architecture, workflow, guide]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [free-ai-video-editing-stack, skill, ffmpeg-command-reference, local-llm-setup, mcp-servers-2026]
---

# Build Your Own AI Video Editor — Blueprint

A complete, step-by-step plan for building an AI agent that edits videos autonomously. All free, all open-source, all local if desired.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (LLM)                        │
│  Understands intent, plans edits, calls tools, reviews  │
└──────┬──────────────┬──────────────┬────────────────┬───┘
       │              │              │                │
       ▼              ▼              ▼                ▼
┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ MCP      │ │ Whisper      │ │ FFmpeg   │ │ NLE (melt)   │
│ Server   │ │ (faster-     │ │ (raw)    │ │ (Kdenlive    │
│ (119     │ │ whisper)     │ │          │ │  MLT XML)    │
│  tools)  │ │              │ │          │ │              │
└──────────┘ └──────────────┘ └──────────┘ └──────────────┘
```

## Level 1: The MVP (30 minutes to build)

### Goal
An AI agent that can trim, cut, and merge videos with subtitles.

### What you need
- A terminal
- 5 minutes

### Steps

```bash
# 1. Install FFmpeg
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Linux

# 2. Install MCP server
pip install mcp-video

# 3. Configure your agent
```

Add this to your MCP settings:
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

### What you can do
```
"Trim this video from 1:30 to 2:45"
"Merge these 3 clips"
"Add subtitles from the audio"
"Speed up this clip 2x"
"Resize to portrait for TikTok"
```

### Time to value: 5 minutes

---

## Level 2: The Workstation (2 hours)

### Goal
Full editing pipeline: transcribe → plan → edit → review → iterate. Agent probes the video, makes intelligent decisions, and reviews output.

### Additions to Level 1

```bash
# 1. Add Whisper for transcription
pip install faster-whisper
# or brew install whisper-cpp

# 2. Install Whisper MCP server
pip install mcp-server-whisper

# 3. Add scene detection support
pip install scenedetect
```

### Updated MCP config
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    },
    "whisper-transcribe": {
      "command": "uvx",
      "args": ["whisper-transcribe-mcp"]
    }
  }
}
```

### Agent workflow (instruct your agent)
```
For every editing task:
1. PROBE: Run ffprobe and get video metadata
2. TRANSCRIBE: Get transcript with word-level timestamps
3. PLAN: Based on transcript + metadata, decide what edits to make
4. EXECUTE: Use MCP tools to perform edits
5. REVIEW: Check output with ffprobe, compare durations, verify no corruption
6. ITERATE: If output is wrong, fix and retry (max 3 attempts)
```

### What you can do (new)
```
"Find all the silences and remove them"
"Extract the segment where the speaker mentions 'startup'"
"Color grade this for a warm cinematic look"
"Auto-generate chapters from scene changes"
"Create a storyboard with thumbnails of every scene"
```

### Time to value: 2 hours

---

## Level 3: Autonomous Editor (1 day)

### Goal
Agent auto-edits raw footage into a finished video with minimal human input. Implements self-evaluation, error recovery, and batch processing.

### Additions to Level 2

```bash
# 1. Install local LLM (optional, for fully local setup)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b

# 2. Install CutAgent for declarative editing
pip install cutagent

# 3. Set up quality checks
```

### Agent prompt template
```
You are an AI video editor. You have these tools: [list MCP tools].
Your workflow:
1. ANALYZE — Probe the input file. Get metadata, transcript, scene list.
2. PLAN — Write a step-by-step editing plan.
3. EXECUTE — Execute each step using the best tool.
4. VERIFY — Check each output before proceeding to the next step.
5. CORRECT — If verification fails, diagnose and fix.
6. REPORT — Summarize what was done.

Edge cases to handle:
- If FFmpeg fails with "No such filter", try an alternative approach
- If audio is missing, use silent audio track
- If Whisper produces no segments, try a different model/language
- If output is corrupted (checked via ffprobe), re-encode
```

### What you can do (new)
```
"Edit this interview video — remove pauses, add intro/outro, color grade"
"Take this raw footage and make a 60-second highlight reel"
"Auto-subtitle and format this video for YouTube, TikTok, and Instagram"
"Process this entire directory of clips into a finished video"
```

### Time to value: 1 day

---

## Level 4: Professional Pipeline (1 week)

### Goal
Multi-track timeline editing via NLE control, motion graphics, and complex compositing. Agent controls Kdenlive or builds Remotion projects.

### Additions to Level 3

```bash
# 1. Install Kdenlive + MCP control
sudo apt install kdenlive  # Linux
brew install --cask kdenlive  # macOS

git clone https://github.com/D-Ogi/mcp-kdenlive
# Configure D-Bus MCP server

# 2. Install Remotion for motion graphics
npx create-video@latest

# 3. Install cli-anything-kdenlive for MLT XML generation
pip install cli-anything-kdenlive

# 4. Hyperframes (for HTML-native video)
pip install mcp-video  # Already has Hyperframes support
```

### MCP config
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    },
    "mcp-kdenlive": {
      "command": "python",
      "args": ["path/to/mcp-kdenlive/server.py"]
    },
    "whisper-transcribe": {
      "command": "uvx",
      "args": ["whisper-transcribe-mcp"]
    }
  }
}
```

### What you can do (new)
```
"Build a multi-track timeline: main video on track 1, b-roll on track 2, music on track 3"
"Add a title sequence with animated text and transitions"
"Create a picture-in-picture overlay with the speaker and slides"
"Generate a complete video from a script with matching b-roll"
"Auto-compose a music video with beat-synced cuts"
```

### Time to value: 1 week

---

## Level 5: Fully Autonomous (1 month)

### Goal
Agent ingests raw footage, analyzes content, makes creative decisions, and produces a finished edit without any human guidance.

### Additions to Level 4

- **Content analysis**: Scene classification, speaker diarization, emotional tone analysis
- **Smart selection**: Best takes identified via audio quality, facial expression, pacing
- **Creative decisions**: Transition type selection, music matching, color palette
- **Batch intelligence**: Maintains a "project memory" across edits, learns from feedback
- **Self-correction loop**: Automated quality metrics, A/B comparison, auto-retry

### Key components
```
VideoAgent framework (HKU) — 30+ specialized agents, DAG orchestration
+ mcp-video — execution layer
+ WhisperX — word-level diarized transcription
+ Qwen2.5-Coder (or Claude) — decision making
+ Kdenlive + MLT — professional rendering
```

### What you can do (new)
```
"Take this 2-hour interview and make a 10-minute highlight reel"
"Edit this wedding footage into a 5-minute film with music, transitions, and color grading"
"Process my weekly podcast: remove silences, add intro/outro, generate chapters"
```

---

## Decision Flowchart

```
User says: "Edit this video"
                │
                ▼
        ┌─────────────────┐
        │ PROBE the video  │
        │ (ffprobe +       │
        │  whisper)        │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Can I handle    │──── No ──► Suggest cloud LLM / human
        │ this with MCP?  │
        └────────┬────────┘
                 │ Yes
                 ▼
        ┌─────────────────┐
        │ Need more than  │
        │ simple trim?    │──── No ──► Single MCP tool call
        └────────┬────────┘
                 │ Yes
                 ▼
        ┌─────────────────┐
        │ Write edit plan  │
        │ (ordered steps)  │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────────────┐
        │ Execute step by step    │
        │ Verify each step before │
        │ moving to next          │
        └────────┬────────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ All steps pass? │──── No ──► Diagnose → Fix → Retry (max 3)
        └────────┬────────┘
                 │ Yes
                 ▼
        ┌─────────────────┐
        │ Final quality    │
        │ check            │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Report: what was │
        │ done, duration,  │
        │ output path      │
        └─────────────────┘
```

## MCP Server Selection Guide

Your choice of MCP server depends on your Level:

| Level | Recommended Server | Why |
|-------|-------------------|-----|
| 1 (MVP) | mcp-video | 119 tools, covers everything |
| 2 (Workstation) | mcp-video + whisper-transcribe | Add transcription |
| 3 (Autonomous) | mcp-video + whisper + cutagent | Declarative EDL for complex edits |
| 4 (Professional) | mcp-video + mcp-kdenlive | Timeline control + FFmpeg |
| 5 (Fully auto) | All of the above + VideoAgent | Multi-agent orchestration |

## Agent Prompt Template

Copy this into your agent's instructions:

```markdown
# AI Video Editor Agent Instructions

You are an AI agent equipped with MCP tools for video editing.
Your task is to edit videos based on user requests.

## Tools available
- mcp-video: 119 video editing tools (trim, merge, resize, color, subtitles, etc.)
- whisper-transcribe: Speech-to-text transcription
- ffprobe: Built-in media analysis

## Workflow
1. PROBE: Run `video_info_detailed` on the input to understand format/codecs
2. TRANSCRIBE: If the request involves content-based editing, transcribe first
3. PLAN: Write a step-by-step plan with specific tool calls
4. EXECUTE: Call tools one at a time, verify each output
5. REVIEW: Check output quality, compare expected vs actual duration
6. REPORT: Summarize what was done

## Constraints
- Edit existing footage only — never generate video
- Always verify output files exist and are playable
- If a tool fails, try an alternative approach before giving up
- Max 3 retries per operation
- For anything you can't handle, explain why and suggest alternatives
```

## Full Stack Installation Script

Save as `install-video-stack.sh`:

```bash
#!/bin/bash
set -e

echo "=== AI Video Editing Stack Installation ==="

# FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt update && sudo apt install -y ffmpeg
    fi
fi

# Python deps
echo "Installing Python packages..."
pip install mcp-video faster-whisper mcp-server-whisper cutagent

# Ollama (optional)
read -p "Install Ollama for local LLM? (y/n): " install_ollama
if [[ "$install_ollama" == "y" ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ollama
    else
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    ollama pull qwen2.5-coder:7b
fi

echo "=== Done! ==="
echo "Configure your AI agent's MCP settings to use mcp-video."
echo "Then try: 'Trim this video from 30s to 1m30s'"
```

## Verification Checklist

After setup, verify each capability:

- [ ] Agent can probe video: `video_info_detailed`
- [ ] Agent can trim: `video_trim`
- [ ] Agent can merge: `video_merge`
- [ ] Agent can resize: `video_resize`
- [ ] Agent can transcribe: `video_ai_transcribe` or `whisper-transcribe`
- [ ] Agent can subtitle: `video_subtitles` or `video_text_subtitles`
- [ ] Agent can color grade: `video_ai_color_grade` or `video_color`
- [ ] Agent can remove silence: `video_ai_remove_silence`
- [ ] Agent can detect scenes: `video_ai_scene_detect`
- [ ] Agent can stabilize: `video_stabilize`
- [ ] Agent can apply effects: `video_effect_*`
- [ ] Agent can create layouts: `video_layout_*`
