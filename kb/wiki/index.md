---
title: Wiki Index
type: index
created: 2026-07-06
updated: 2026-07-08
---

# Wiki Index

> **Focus: Free AI agents that EDIT existing video.** Generative models (Runway, Pika, Sora, etc.) are archived — this wiki is about editing footage, not generating clips.

## Overview

- [Overview](overview) — top-level synthesis of AI video editing agents
- [Complete Free AI Video Editing Stack](guides/free-ai-video-editing-stack) — step-by-step guide to the free stack
- [Build Your Own AI Video Editor](guides/build-your-own-ai-video-editor) — 5-level blueprint from MVP to fully autonomous
- [FFmpeg Command Reference for AI Agents](guides/ffmpeg-command-reference) — exhaustive command patterns by task
- [Local LLM Setup for Video Editing](guides/local-llm-setup) — Ollama, Qwen2.5-Coder, RAG setup, benchmarks

## Guides

- [Complete Free AI Video Editing Stack](guides/free-ai-video-editing-stack) — 4 options: MCP, FFmpeg+LLM, NLE control, Remotion
- [Build Your Own AI Video Editor](guides/build-your-own-ai-video-editor) — 5-level blueprint, decision flowchart, install script
- [FFmpeg Command Reference](guides/ffmpeg-command-reference) — 17 categories, probing to batch processing
- [Local LLM Setup](guides/local-llm-setup) — Qwen2.5-Coder, Ollama integration, RAG for FFmpeg accuracy
- [Recipe Packs](guides/recipe-packs) — one-command YAML workflow templates for common edit patterns
- [Hardware Acceleration](guides/hardware-acceleration) — NVENC, QSV, VideoToolbox encoding for faster renders

## Extended Tools

- [Recipe Runner](tools/recipe-runner) — YAML recipe executor for one-command video workflows
- [MLT XML Export](tools/mlt-export) — NLE interoperability via Kdenlive/Shotcut-compatible XML
- [Compliance Reporter](tools/compliance-reporter) — check videos against EBU R128, Netflix, YouTube, TikTok specs
- [Content Adapter](tools/content-adapter) — stock footage (Pexels) + SFX (Freesound) with license sidecars
- [VLM Adapter](tools/vlm-adapter) — visual perception via Qwen2.5-VL (gated/opt-in)

## Entities — MCP & Tooling

- [mcp-video](entities/mcp-video) — MCP server, 106 tools, primary surface via unified adapter
- [Hyperframes](entities/hyperframes) — Remotion-based kinetic text and animated overlays
- [MCP Servers for Video Editing](entities/mcp-video-servers) — 15+ free MCP servers wrapping FFmpeg (119 tools in best)
- [MakeMyClip Editor](entities/make-my-clip) — "FFmpeg you can talk to", zero-config, MIT
- [CutAgent](entities/cutagent) — FFmpeg for AI agents, declarative EDL, structured JSON output
- [CutRoom](entities/cutroom) — Local-first film editor, CPU whisper, session resume/fork
- [Whisper Transcription Ecosystem](entities/whisper-ecosystem) — Free local subtitle/transcription tools
- [video-use](entities/video-use) — Claude Code skill, transcript-first, self-evaluating (14.8k stars)

## Entities — Agentic Frameworks

- [VideoAgent](entities/video-agent) — HKU multi-agent framework, 30+ agents, DAG orchestration
- [OpenMontage](entities/openmontage) — 34k stars, 12 pipelines, agent-first video production
- [Crayotter](entities/crayotter) — Traceable multi-agent long-form editing (v1.0.0)
- [UniVA](entities/univa) — Plan-Act dual-agent, MCP-native research prototype
- [CutClaw](entities/cutclaw) — Music-synchronized editing via multi-agent MLLM
- [Agentic Video Editor (AVE)](entities/agentic-video-editor) — CLI pipeline with retry gates, FFmpeg rendering
- [AI_Editor](entities/ai-editor) — Full-stack pipeline, CV scene analysis, Shotstack rendering
- [Pilipili-AutoVideo](entities/pilipili-autovideo) — Local end-to-end, Mem0 memory, CapCut export
- [X-Cut](entities/x-cut) — Chat-driven agent, Remotion rendering (concept stage)
- [Project Montage](entities/project-montage) — Google's multi-agent video builder (research)

## Concepts

- [Unified Adapter](concepts/unified-adapter) — single import surface, routes 151 symbols to best implementation
- [Multi-Agent Orchestration](concepts/multi-agent-orchestration) — how multiple AI agents coordinate in video editing
- [Self-Evaluation Loop](concepts/self-evaluation-loop) — agents that score their own output and retry
- [Agentic vs Generative](concepts/agentic-vs-generative) — the two layers of AI video editing
- [Color-Space Management](concepts/color-space-management) — working in known color spaces before grading
- [Multi-Cam Editing](concepts/multi-cam-editing) — synchronizing and switching between multiple camera angles
- [Chroma Key / Green Screen](concepts/chroma-key) — replacing solid-color backgrounds with composited video

## Comparisons

- [Agentic Frameworks 2026](comparisons/agentic-frameworks-2026) — 10 frameworks compared
- [MCP Server Matrix 2026](comparisons/mcp-servers-2026) — 12 MCP servers across 30+ feature dimensions
- [AI Video Generation Models 2026](comparisons/ai-video-models-2026) — Runway vs Pika vs Veo vs Kling vs Sora (archived reference)

## Skills

- [SKILL.md](../../SKILL.md) — Complete agent skill for AI video editing (root level, auto-discoverable). 6-phase decision engine, 26 Hard Rules, production techniques, MCP tool mappings, error recovery, contradiction log.
- [Agent Prompt](../../scripts/agent-prompt.md) — Universal copy-paste prompt for any LLM agent. CLASSIFY → PROBE → PLAN → BUILD → VERIFY workflow.
- [Setup Script](../../scripts/setup.sh) — One-command install: `curl -fsSL https://raw.githubusercontent.com/mua47105-hue/agentic-ai-video-knowledgebase/main/scripts/setup.sh | bash`

## Charts

- [Model Quality vs Speed vs Cost](charts/model-quality-speed-cost) — Matplotlib bubble chart comparing AI video models

## Sources

- [EBU R128](sources/ebu-r128) — broadcast loudness normalization specification
- [ITU-R BS.1770-4](sources/itu-r-bs-1770-4) — loudness measurement algorithm standard
- [Netflix Sound Mix Spec](sources/netflix-sound-mix-spec) — Netflix delivery audio specification
- [ELLMPEG Paper](sources/ellmpeg-paper) — Qwen2.5-Coder 88% FFmpeg accuracy benchmark
- [mcp-video Docs](sources/mcp-video-docs) — official mcp-video PyPI documentation

## Archive (Generative Models)

Moved to `archive/` — these are AI video generation models, not editing agents:
- [Runway Gen-4](archive/runway-gen-4), [Pika 2.5](archive/pika-2-5), [Google Veo 3](archive/google-veo-3), [Sora](archive/sora), [Kling 3.0](archive/kling-3-0)
- [Nano Banana](archive/nano-banana), [EzVideo](archive/ezvideo), [Shorz](archive/shorz), [Magicroll AI Agent](archive/magicroll)
