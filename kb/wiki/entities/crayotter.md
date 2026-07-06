---
title: Crayotter
type: entity
tags: [multi-agent, open-source, traceable, long-form, research]
created: 2026-07-06
updated: 2026-07-06
sources: [source-crayotter-arxiv]
related: [video-agent, cutclaw, openmontage]
---

# Crayotter

Open-source multimodal multi-agent system for prompt-driven long-form video editing. Crayotter organizes production into three phases with inspectable artifacts at every stage, enabling surgical failure diagnosis and selective revision instead of full restarts.

## Architecture

Three-phase pipeline:

1. **Material Preparation** — Planner emits a dependency DAG; deterministic executor runs search/download/analysis with bounded resource pools. Material gap evaluator decides on supplement rounds.

2. **Editing Research** — Pure-reasoning phase analyzing source videos to produce a structured editing blueprint (narrative, visual, pacing, narration strategies). No tools called.

3. **Tool-grounded Execution** — ReAct Editor (or controlled DAG) performs cutting, transitions, TTS, subtitles, audio mixing, export. Full tool-call trajectory logging.

Orchestrated via LangGraph. RLVR (Reinforcement Learning from Verifiable Rewards) ready.

## Key Innovations

- **Artifact-grounded traceability** — every phase externalizes inspectable artifacts: coverage reports, multimodal analyses, editing blueprints, tool calls, intermediate renders
- **Replayable trajectory schema** — editing runs can be replayed and diagnosed
- **Selective revision** — failed segments diagnosed and fixed without full restart

## Benchmarks

| Metric | Value |
|--------|-------|
| Human evaluation (1-5) | 3.40 |
| CapCut-Mate (baseline) | 2.44 |
| CutClaw (baseline) | 1.70 |
| Evaluation | 23 editing themes |
| Gains | Theme alignment, narrative coherence, editing smoothness |

## Capabilities

- Single NL prompt → complete edited video
- Multi-source import (Bilibili, Douyin, YouTube, generic URLs)
- Coverage-aware multimodal retrieval
- Segmented TTS, subtitles, audio mixing
- Local-first material mode
- User approval gate for plan review
- Checkpoint/resume
- Visual trace analysis (web + static HTML export)

## Limitations

- Requires external API keys for multimodal LLMs (Qwen, etc.)
- Quality depends on commercial LLM capability
- 3.40/5 — decent but not professional-grade
- Evaluated on 23 themes only

## Links

- [GitHub](https://github.com/idwts/Crayotter) — v1.0.0 released June 2026
- [Paper](https://arxiv.org/abs/2606.07636)
- [Project Page](https://idwts.github.io/Crayotter/)
