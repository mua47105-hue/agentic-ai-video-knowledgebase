---
title: Agentic Video Editor (AVE)
type: entity
tags: [cli, pipeline, retry-gates, open-source]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [video-use, openmontage]
---

# Agentic Video Editor (AVE)

Command-line AI video editor with YAML-defined pipelines and retry gates. An ensemble of specialized agents (Director → Trim Refiner → Editor → Reviewer) produces a polished ad from raw footage and a creative brief.

## Architecture

**5-stage CLI pipeline:**

1. **Preprocess** — PySceneDetect scene detection + Faster-Whisper transcription → FootageIndex JSON
2. **Director Agent** — Searches index, selects shots, produces EditPlan (Gemini ADK)
3. **Trim Refiner Agent** — Probes cut boundaries, refines trim points
4. **Editor Agent** — Renders via FFmpeg/MoviePy
5. **Reviewer Agent** — Scores 5 dimensions, feeds back to Director for retry

Pipelines defined as YAML manifests with retry gates:

```yaml
steps:
  - agent: director
  - agent: trim_refiner
  - agent: editor
  - agent: reviewer
    retry_if:
      metric: overall
      threshold: 0.65
      max_retries: 2
      feedback_target: director
```

## Capabilities

- `ave edit` CLI — raw footage + brief → polished ad
- Scene detection + shot indexing + transcription
- A-Roll/B-Roll compositing
- 5-dimension reviewer scoring (Adherence, Pacing, Visual Quality, Watchability, Overall)
- Versioned retry loop (max 3 passes)
- Custom YAML pipelines + style templates
- Optional web UI (pre-alpha)

## Key Differentiator

Deterministic YAML-defined pipelines with retry gates. Reviewer score thresholds drive automated re-editing loops. Clean separation of concerns (Director/TrimRefiner/Editor/Reviewer).

## Limitations

- Depends on Google Gemini API (no offline mode)
- Web UI is pre-alpha
- Narrow domain focus (short-form ads)
- Requires Python 3.11 + FFmpeg

## Links

- [GitHub](https://github.com/jorgefsb/agentic-video-editor)
