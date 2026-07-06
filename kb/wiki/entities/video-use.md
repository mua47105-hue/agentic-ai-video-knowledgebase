---
title: video-use
type: entity
tags: [agent-skill, claude-code, open-source, transcript-first]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [openmontage, agentic-video-editor]
---

# video-use

Open-source Claude Code video editing skill (14.8k stars). Uses a **transcript-first, zero-frame-dump approach** — the LLM never "watches" video, working instead from a ~12KB text transcript and on-demand visual composites.

## Architecture

**Two-layer approach:**
- **Layer 1 — Audio transcript** (always loaded): ElevenLabs Scribe gives word-level timestamps, speaker diarization, and audio events. All takes packed into `takes_packed.md` (~12KB).
- **Layer 2 — Visual composite** (on demand): `timeline_view` produces a filmstrip + waveform + word labels PNG at decision points.

Pipeline: **Transcribe → Pack → LLM Reasons → EDL → Render → Self-Eval → Repeat (max 3x)**

Parallel sub-agents handle animation overlays (Manim, Remotion, HyperFrames, PIL).

## Capabilities

- Cuts filler words (umm, uh) and dead space
- Auto color grades every segment
- 30ms audio fades at every cut
- Customizable subtitles (2-word UPPERCASE chunks by default)
- Animation overlays via parallel sub-agents
- Self-evaluates every cut boundary
- Persists session memory in `project.md`
- Works for: talking heads, montages, tutorials, travel, interviews

## Key Differentiator

**Transcript-first approach** avoids processing 45M tokens of frame noise. LLM reasons from ~12KB text + a handful of PNGs instead of 30K frames. Agent-as-editor paradigm with skill-based orchestration.

## Limitations

- Requires ElevenLabs API key for transcription
- Only works inside agent-enabled CLI (Claude Code, Codex)
- LLM never processes raw video frames directly
- Self-eval max 3 retries
- No native beat/music synchronization

## Links

- [GitHub](https://github.com/browser-use/video-use)
