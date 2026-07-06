---
title: Pilipili-AutoVideo
type: entity
tags: [local, end-to-end, capcut, mem0, open-source]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [openmontage, univa]
---

# Pilipili-AutoVideo

Fully local, end-to-end AI video agent. One sentence → full MP4 with subtitles + CapCut draft project for final human touch-ups. Features Mem0 digital twin memory that learns creator style over time.

## Architecture

7-layer system:

- **Brain (LLM)**: DeepSeek/Kimi/MiniMax/Gemini → script + storyboard
- **Vision (Image Gen)**: Nano Banana (Gemini 3 Pro Image) — 4K keyframe lock
- **Motion (Video Gen)**: Kling 3.0 / Seedance 1.5 Pro — dual-engine I2V
- **Voice (TTS)**: MiniMax Speech 2.8 HD — generated first, ms-precision duration measurement
- **Assembly**: Python + FFmpeg + WhisperX — transitions + subtitles
- **Draft**: pyJianYingDraft → CapCut/JianYing project export
- **Memory**: Mem0 (local SQLite/cloud) — digital twin style learning

## Capabilities

- One sentence → full video with subtitles
- **Absolute audio-video sync** — TTS first, measure ms duration, then match video
- **Keyframe lock** — Nano Banana generates 4K keyframe, then I2V ensures subject consistency
- **Mem0 digital twin** — learns aesthetic preferences over time
- **CapCut draft export** — AI handles 90%, human fine-tunes the last 10%
- Standard Skill packaging — callable by any AI Agent
- Docker compose, CLI, Web UI, Python API

## Key Differentiator

TTS-first duration control (perfect AV sync), Nano Banana 4K keyframe lock (no subject drift), Mem0 memory (learns your style), CapCut draft export (human-in-the-loop).

## Limitations

- Requires multiple API keys (DeepSeek, Kling, MiniMax)
- Video generation slow (2-5 min per scene)
- Needs Python/FFmpeg setup
- Limited to Chinese ecosystem (JianYing) for draft export
- Small community (185 stars)

## Links

- [GitHub](https://github.com/OpenDemon/Pilipili-AutoVideo)
