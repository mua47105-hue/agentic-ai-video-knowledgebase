---
title: VideoAgent
type: entity
tags: [multi-agent, open-source, research, hku]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [crayotter, openmontage, univa, multi-cam-editing]
---

# VideoAgent

All-in-one multi-agent framework for video understanding and editing from HKUDS (University of Hong Kong). Integrates over 30 specialized editing agents with dynamic pipeline assembly via textual-gradient graph optimization.

## Architecture

Two-stage design:

1. **Automated Video Shot Creation** — Shot Planning Agent generates structured storyboards with global awareness of available material. Cross-modal retrieval (ImageBind + CLIP) fetches semantically aligned clips, followed by VLM-driven fine-grained trimming for per-shot duration control.

2. **Multi-Agent Graph Orchestration** — Over 30 specialized editing agents dynamically composed into a DAG via textual-gradient graph optimization. The graph is iteratively refined through structured quality signals (acyclicity, connectivity, intent coverage), where an LLM generates "textual gradient" updates — analogous to gradient descent in combinatorial space.

## Capabilities

- Video understanding, summarization, transcription
- Rhythm-synced montages, scene assembly, storytelling
- Video remaking (memes, AI music videos, cross-cultural adaptation)
- Cross-lingual adaptation (e.g. English stand-up → Chinese crosstalk)
- Fully automated from NL instruction to finished video

## Key Technologies

- **Intent Parsing** — Decomposes user instructions into explicit + implicit sub-intents
- **Textual-Gradient Graph Optimization** — Workflow assembly as iterative optimization over graph topology
- Backbone LLMs: Claude (mandatory for graph router), GPT-4o, DeepSeek-v3, Gemini
- Open models: CosyVoice, Fish Speech, Seed-VC, DiffSinger, Whisper, ImageBind

## Benchmarks

| Metric | Value |
|--------|-------|
| Orchestration success rate | 87–95% |
| API cost reduction vs baselines | 60% |
| Human evaluation vs human editors | Only 4% below professional human-created videos |
| Best backbone | Claude-Sonnet-3.7 (95% Audio, 93% Video) |

## Limitations

- Output quality constrained by available source footage (no generative video internally)
- Requires Claude for the Agentic Graph Router
- ~8GB GPU minimum, no AMD support
- Multi-model dependency (many open models to set up)

## Links

- [GitHub](https://github.com/HKUDS/VideoAgent)
- [Paper](https://arxiv.org/abs/2606.23327)
