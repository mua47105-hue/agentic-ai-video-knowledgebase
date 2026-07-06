---
title: CutClaw
type: entity
tags: [multi-agent, music-sync, research, long-form]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [crayotter, video-agent]
---

# CutClaw

Agentic hours-long video editing via music synchronization. CutClaw is the first system to treat music structure (beats, energy shifts) as the primary narrative anchor for long-form-to-short video via multi-agent MLLM collaboration.

## Architecture

**Hierarchical Multimodal Decomposition** (visual+audio footage into structured captions/scenes) → **Playwriter Agent** (orchestrates narrative, anchors scenes to music shifts/beats) → **Editor Agent** (selects fine-grained clips) → **Reviewer Agent** (validates aesthetic+semantic quality, loops feedback).

Uses LiteLLM for model routing across Qwen3-VL, Qwen3-Omni, Gemini 3, MiniMax.

## Capabilities

- Hours-long raw footage → music-synced short video
- Beat-aligned cuts (Δt ≤ 0.1s)
- Instruction-following editing
- Smart auto-cropping
- One-click pipeline

## Benchmarks

| Metric | Score |
|--------|-------|
| Visual quality | 77.6 |
| Instruction following | 70.0 |
| AV harmony | 86.5 |
| Human preference | ~50% vs baselines |

## Limitations

- No caption/subtitle generation
- Requires paid MLLM API calls
- Quality depends on source footage
- No online hosted tier
- Setup complexity for non-technical users
- Multi-pass agent loop is slow (not real-time)

## Links

- [GitHub](https://github.com/GVCLab/CutClaw)
- [Paper](https://arxiv.org/abs/2603.29664)
