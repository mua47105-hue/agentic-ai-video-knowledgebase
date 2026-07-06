---
title: Self-Evaluation Loop
type: concept
tags: [quality, feedback, review]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [openmontage, video-use, agentic-video-editor, multi-agent-orchestration]
---

# Self-Evaluation Loop

The practice of having the AI agent score its own output across multiple quality dimensions and retry if the score falls below a threshold. This enables autonomous quality control without human review.

## Common dimensions scored

- **Pacing** — does the edit flow naturally?
- **Visual quality** — are there artifacts, jumps, or inconsistencies?
- **Theme alignment** — does the output match the brief?
- **Watchability** — would a human find this engaging?
- **Audio quality** — pops, clicks, sync issues
- **Narrative coherence** — does the story make sense?

## Implementation patterns

### Retry gates (AVE, CutClaw)
Pipelines defined as YAML with retry conditions: if overall score < threshold, feed reviewer feedback back to the Director agent and retry (up to N attempts).

### ffprobe validation (OpenMontage)
Post-render self-review using ffprobe for codec validation, frame sampling for visual artifacts, audio level analysis, delivery promise verification, and subtitle checks.

### Cut-boundary evaluation (video-use)
Self-evaluation at every cut boundary before showing output to the user. Max 3 retry attempts per cut.

## Why it matters

Without self-evaluation, the human must check every output. Self-evaluation loops make autonomous editing viable by catching failures before the human sees them.

## Implementations

- [OpenMontage](../entities/openmontage) — ffprobe + frame + audio self-review
- [video-use](../entities/video-use) — cut-boundary evaluation
- [Agentic Video Editor](../entities/agentic-video-editor) — 5-dimension scoring with retry gates
