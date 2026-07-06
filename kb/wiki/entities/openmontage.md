---
title: OpenMontage
type: entity
tags: [agent-first, open-source, production, pipelines]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [x-cut, univa, video-use]
---

# OpenMontage

World's first open-source agentic video production system. 12 pipelines, 52 tools, 400+ agent skills. Uses an **agent-first architecture** — your AI coding assistant (Claude Code, Cursor, Copilot, Codex) IS the orchestrator. There is no Python orchestrator; the agent reads YAML pipeline manifests + Markdown stage director skills and calls Python tools.

## Architecture

Three-layer knowledge system:
- `tools/` + `pipeline_defs/` — what exists
- `skills/` — how to use the tools (Markdown instructions)
- `.agents/skills/` — deep technical knowledge

Flow: Agent reads pipeline YAML → loads stage director skill → calls Python tools → self-reviews → checkpoints state → asks for human approval at creative decision points.

## Key Technologies

- **Composition engines**: Remotion (React) + HyperFrames (HTML/GSAP)
- **Real-footage documentary**: CLIP-indexed corpus from free/open archives
- **14 video providers**: Kling, Runway, Veo, Grok, Wan2.1 local, Hunyuan
- **Self-review**: ffprobe validation, frame sampling, audio analysis, delivery promise verification
- **Provider selection**: scored across 7 dimensions with auditable decision log
- **Budget governance**: cap/warn/observe modes

## Pipelines

Animated Explainer, Animation, Avatar Spokesperson, Cinematic, Clip Factory, Documentary Montage, Hybrid, Localization & Dub, Podcast Repurpose, Screen Demo, Talking Head.

## Key Differentiator

Unlike tools that "animate stills and call it video," OpenMontage can build a finished video from real footage pulled from free/open sources, ranked semantically, edited intentionally, and rendered as a proper timeline. Works with zero API keys (Piper TTS + archive.org + Remotion).

## Limitations

- Requires external AI coding assistant to orchestrate
- Local LLM support (Ollama/LM Studio) marked "coming soon"
- AGPLv3 license
- API keys needed for cloud video/image providers

## Links

- [GitHub](https://github.com/calesthio/OpenMontage) — 34k+ stars
