---
title: Change Log
type: log
created: 2026-07-06
updated: 2026-07-06
---

# Change Log

## [2026-07-06] scaffold | Wiki initialized

Created the initial wiki structure and schema. Empty wiki ready for first source ingestion.

## [2026-07-06] ingest | Deep Research Batch 1 — Agentic Frameworks

Researched and documented 5 agentic frameworks:
- **VideoAgent** — HKU multi-agent, textual-gradient graph optimization, 87-95% success rate
- **Crayotter** — v1.0.0, traceable multi-agent, 3.40/5 human eval
- **OpenMontage** — 34k+ stars, agent-first, 12 pipelines
- **UniVA** — Plan-Act dual-agent, MCP-native research prototype
- **X-Cut** — chat + Remotion, concept stage

Created 3 concept pages:
- Multi-Agent Orchestration
- Self-Evaluation Loop
- Agentic vs Generative

Updated overview and index.

## [2026-07-06] ingest | Deep Research Batch 2 — Generative Models + Commercial Tools + Remaining Frameworks

Researched and documented 12 entities:
- **Generative models**: Runway Gen-4, Pika 2.5, Google Veo 3, Sora (discontinued), Kling 3.0
- **Commercial tools**: EzVideo (private beta, Gemini director), Shorz (MCP-agent-callable)
- **Remaining frameworks**: CutClaw (music-sync), video-use (transcript-first, 14.8k stars), AVE (CLI with retry gates), Pilipili-AutoVideo (local, Mem0, CapCut export)

Running tally: 21 entities, 3 concepts, 0 sources, 0 guides, 0 comparisons, 0 charts.

## [2026-07-06] chart | Model Quality vs Speed vs Cost

Generated matplotlib bubble chart comparing 5 AI video models on quality, speed, and cost.

## [2026-07-06] ingest | Deep Research Batch 4 — Comparisons + Chart

Created:
- **AI Video Models 2026** comparison — Runway vs Pika vs Veo vs Kling vs Sora
- **Agentic Frameworks 2026** comparison — 10 frameworks across architecture, capabilities, maturity
- **Model Quality vs Speed vs Cost** chart — matplotlib bubble chart

Running tally: 21 entities, 3 concepts, 2 comparisons, 1 chart, 0 sources, 0 guides.

## [2026-07-06] refocus | Stripped generative models, rebuilt for editing-only focus

Major refocus: removed generative model pages (Runway, Pika, Sora, Veo, Kling, Nano Banana, EzVideo, Shorz, Magicroll) to archive. This wiki is now exclusively about AI agents that EDIT existing video footage.

Created:
- **Complete Free AI Video Editing Stack** guide — 4 options for free editing
- **MCP Servers for Video Editing** — comprehensive list of 15+ free MCP servers
- **MakeMyClip Editor** — zero-config FFmpeg tool for agents
- **CutAgent** — FFmpeg for agents with declarative EDL
- **CutRoom** — local-first film editor with session resume
- **Whisper Transcription Ecosystem** — free local subtitle tools

Rewrote overview entirely. New focus: "Free and open-source AI agents that EDIT existing video footage."

## [2026-07-06] ingest | Deep Research Batch 3 — Remaining Frameworks + Nano Banana

Researched and documented 4 more entities:
- **AI_Editor** — full-stack pipeline with CV scene analysis + Shotstack
- **Google Project Montage** — Google's multi-agent video builder
- **Magicroll AI Agent** — India-focused vernacular platform
- **Nano Banana** — keyframe lock for character consistency in AI video

Running tally: 21 entities, 3 concepts, 0 sources, 0 guides, 0 comparisons, 0 charts.

## [2026-07-06] guide | MCP Server Comparison Matrix — 12 servers across 30+ dimensions

Created definitive comparison of all known free MCP servers: 12 main servers, 5 transcription servers, 4 NLE control servers. Feature matrix with 30+ edit operations. Winner-by-use-case recommendations. Architecture comparison (tool-per-op vs pipeline vs minimal-executor vs NLE-control).

## [2026-07-06] skill | SKILL.md — Complete AI Video Editing Agent Skill

Created `SKILL.md` at root level — auto-discoverable by any LLM agent. Includes: identity, core stack, probe-plan-edit-review-iterate workflow, MCP tool usage by task, 50+ raw FFmpeg commands organized by operation, workflow templates (podcast-to-shorts, silence removal, auto-subtitles), edge case handling, validation checklist, config snippets for all agents, LLM recommendations.

## [2026-07-06] guide | FFmpeg Command Reference for AI Agents

Created exhaustive FFmpeg command reference organized by editing task (17 categories): probing, trimming, concatenation, transitions, color grading, subtitles, audio, speed, stabilization, scene detection, silence removal, effects, format conversion, compositing, quality/compression, batch processing, best practices. 100+ validated command patterns.

## [2026-07-06] guide | Local LLM Setup for Video Editing

Created guide for fully local, free LLM setup. Covers: Qwen2.5-Coder (88% FFmpeg accuracy per ELLMPEG paper) vs Llama 3.2 vs DeepSeek Coder, Ollama installation, integration with MCP servers/CutAgent/wtffmpeg, quantization options, GPU/CPU optimization, RAG setup for better accuracy, detailed benchmark table, decision matrix for local vs cloud.

## [2026-07-06] guide | Build Your Own AI Video Editor — 5-Level Blueprint

Created step-by-step blueprint from MVP (5 mins) to fully autonomous (1 month). Each level has exact steps, MCP config, capabilities, and estimated build time. Includes: architecture diagram, decision flowchart, agent prompt template, full installation script, verification checklist. Four levels: MVP → Workstation → Autonomous → Professional → Fully Autonomous.

## [2026-07-06] merge | SKILL.md — Integrated production techniques from video-use/editing-craft

Major SKILL.md rewrite: merged editing-craft's 12 Hard Rules (two-pass loudnorm, xfade offset validation, subtitle readability rules, SFX timing) with our agent-first MCP workflow. Added 5-phase decision engine (CLASSIFY → PROBE → PLAN → BUILD → VERIFY), content-type routing table (8 content types with unique workflows), production technique library mapped to MCP tools, error recovery table with 12 specific failure patterns, contradiction log, project memory pattern. SKILL.md is now the definitive single-file agent skill for video editing.

## [2026-07-06] scripts | One-command setup + universal agent prompt

Created `scripts/setup.sh` — installs FFmpeg, mcp-video, faster-whisper, Whisper MCP server, CutAgent, optional Ollama + Qwen2.5-Coder 7B. Single curl command: `curl -fsSL https://raw.githubusercontent.com/mua47105-hue/agentic-ai-video-knowledgebase/main/scripts/setup.sh | bash`

Created `scripts/agent-prompt.md` — definitive copy-paste system prompt for any LLM agent. CLASSIFY → PROBE → PLAN → BUILD → VERIFY workflow with all Hard Rules and production techniques.

## [2026-07-06] enhance | FFmpeg reference — production-grade commands

Updated FFmpeg reference with: two-pass loudnorm (measurement + linear apply, explicit -ar 48000), xfade offset validation (pre-render bound check), cubic-ease easing for transitions, -50dB silence threshold (from -30dB), 0.3s silence removal padding with 0.03s audio fades, transition SFX integration.

## [2026-07-06] enhance | Blueprint — production gates + content-type routing

Updated blueprint with: content-type routing table (8 content types), production correctness checklist (10 items beyond tool check), contradiction log (6 disagreements surfaced to user), enhanced decision flowchart with CLASSIFY and VERIFY phases.

## [2026-07-06] audit | Full repo audit and fix

Ran comprehensive audit: fixed 7 broken links from archived pages, removed 2 dangling sources refs, fixed 4 dangling related refs, added 3 missing pages from index (Project Montage, AI video models comparison, chart), fixed README entity count (25) and stale example path, updated overview with complete entity list, added AGENTS.md/SKILL.md/scripts/ to CLAUDE.md structure, added scripts/ to AGENTS.md, added chart reference to index, hyperlinked archive entries, created missing assets directory, updated stale example slugs in CLAUDE.md and schema.

Overall tally: 16 active entities, 9 archived entities, 3 concepts, 4 guides, 3 comparisons, 1 chart, 0 sources, plus SKILL.md at root level.
