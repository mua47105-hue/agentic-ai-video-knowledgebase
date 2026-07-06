---
title: CutRoom
type: entity
tags: [local, whisper, edl, mit, open-source]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [cutagent, whisper-ecosystem, free-ai-video-editing-stack]
---

# CutRoom

Film-editor agent with receipts. Local-first, GPU-free. Uses faster-whisper on CPU for transcription, FFmpeg for rendering. Logs footage, creates EDLs, word-level subtitles, session resume and fork. MIT license.

## Architecture

- **Transcription**: faster-whisper on CPU (no GPU needed)
- **Rendering**: FFmpeg
- **State**: Footage logs, EDLs, session resume/fork
- **Subtitles**: Word-level precision

## Capabilities

- Log all footage with metadata
- Create EDLs (Edit Decision Lists) declaratively
- Word-level subtitle generation
- Session resume — pick up where you left off
- Session fork — branch edits for experimentation
- CPU-only operation (no GPU required)

## Key differentiator

Local-first with no GPU requirement. Session resume and fork are unique — you can branch your edit and try different approaches, then go back. The "receipts" model means every edit is logged and reproducible.

## Links

- [GitHub](https://github.com/Young-1231/cutroom)
