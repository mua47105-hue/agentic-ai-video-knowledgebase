---
title: AI_Editor
type: entity
tags: [open-source, pipeline, scene-detection, shotstack]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [agentic-video-editor, openmontage]
---

# AI_Editor

Open-source AI-assisted video editing pipeline. Combines computer vision scene analysis with LLM edit planning and cloud rendering via Shotstack. Includes YouTube publishing.

## Architecture

Multi-stage media pipeline: **FastAPI backend + React frontend** → Groq LLM chat brief builder → Analyzer (SceneDetect + EasyOCR + PaddleOCR) → Pipeline runner (download, edit assembly, overlay planning, render) → Shotstack cloud rendering → optional 16:9→9:16 Shorts conversion → YouTube OAuth upload.

## Capabilities

- Reference video analysis (scene detection + OCR text extraction)
- AI edit planning via Groq conversational brief
- Structured multi-stage pipeline with state persistence
- Shotstack cloud timeline assembly + render
- 16:9→9:16 Shorts conversion
- YouTube direct upload with OAuth 2.0
- Google Drive asset ingestion
- Job status tracking UI

## Key Differentiator

Not just an LLM wrapper — a full-stack pipeline bridging CV-based scene analysis with LLM planning and cloud rendering. Structured ingest→analyze→plan→render→publish pipeline with a React frontend.

## Limitations

- Shotstack rendering is async (long videos need extended polling)
- PaddleOCR has large install footprint
- ~10 min avg job duration
- OCR+scene detection can take 4-5 min
- No built-in queue/worker system

## Links

- [GitHub](https://github.com/carlamine/ai_editor) — MIT License
