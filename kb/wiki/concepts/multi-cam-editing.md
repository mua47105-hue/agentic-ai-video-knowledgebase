---
title: Multi-Cam Editing
type: concept
tags: [editing, multi-cam, podcast, interview]
created: 2026-07-08
updated: 2026-07-08
sources: []
related: [podcast-to-shorts, video-agent, unified-adapter]
---

# Multi-Cam Editing

## Definition
Multi-cam (multi-camera) editing is the practice of synchronizing and switching between footage from multiple cameras covering the same event. This is standard for podcasts (2-3 cameras on host/guests), interviews (interviewer + subject + b-roll camera), concerts (wide + close-up + crowd), and wedding ceremonies (altar + guest reaction + processional).

## Why it matters
- **Podcasts and interviews** are the #1 use case for this repo's recipe system. The `podcast-to-shorts.yaml` recipe expects single-camera or multi-cam source.
- **Without multi-cam awareness**, an agent can't switch angles for visual variety, match color between cameras, or sync audio from the best mic source.

## How AI agents handle multi-cam

### Sync
- **Whisper transcript**: Same words spoken at the same time across two cameras' audio tracks → alignment anchor. Use word-level timestamps to find offset.
- **ffmpeg**: `ffmpeg -i cam1.mp4 -i cam2.mp4 -filter_complex "[0:a][1:a]crosscorrelation"` to find sample-accurate offset.
- **Timecode**: If cameras have genlocked timecode, sync is trivial.

### Angle switching
- **Scene detection**: Find when the speaker changes (one person stops, another starts) → switch to the camera facing the active speaker.
- **Energy-based**: Switch to the camera with the most motion/energy during key moments (laugh, gesture, reaction shot).

### Color matching
- **ffmpeg colormatrix**: `ffmpeg -i cam1.mp4 -vf "colormatrix=bt709:bt709"` won't match two different cameras — use `ffmpeg -i cam1.mp4 -i cam2.mp4 -filter_complex "colorbalance"` or a LUT-based approach.
- **Histogram matching**: `ffmpeg -i cam1.mp4 -i cam2.mp4 -filter_complex "histeq=strength=0.3"` to normalize brightness before switching.

## Links
- [VideoAgent](../entities/video-agent) — DAG-based multi-agent framework that handles multi-cam scenes
- [Unified Adapter](../concepts/unified-adapter) — probe and transcribe tools for sync
- [Recipe Packs](../guides/recipe-packs) — podcast-to-shorts uses multi-cam patterns

## References
- Multi-cam editing is well-documented in professional NLEs (Premiere Pro, DaVinci Resolve). This concept page adapts those workflows for AI agents using free tools.
