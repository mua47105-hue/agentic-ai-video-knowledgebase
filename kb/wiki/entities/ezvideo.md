---
title: EzVideo
type: entity
tags: [commercial, desktop, google-ecosystem, autonomous]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [google-veo-3, shorz]
---

# EzVideo

Autonomous AI video editing agent positioned as "the first IDE for video generation." Google Gemini acts as a film director, orchestrating the full production pipeline from a sidebar chat while a traditional NLE timeline sits underneath for manual refinement.

## Architecture

Desktop NLE (IDE-like) with a sidebar Chat Agent orchestrating: **Gemini 3.1** (Director: script, scene breakdown, shot selection) → **Imagen** (photorealistic stills) → **Veo 3** (video B-roll) → **ElevenLabs** (voiceover) → auto-timeline assembly → local GPU rendering.

## Capabilities

- Text prompt → full MP4 (script, scenes, shots, voiceover, captions, transitions)
- Auto-captions with word-level sync
- Color grading and transitions
- Desktop app (local GPU rendering)
- Planned: B2B REST API (Q3 2026), pixel-level editing (Q4 2026)

## Pricing

Not yet public. In private beta (waitlist only). Two planned models:
- **Desktop IDE**: subscription (local rendering, no server costs)
- **Enterprise API**: pay-as-you-go cloud rendering

## Status

Private beta. Ambitious roadmap through 2028 (feature-film generation). No shipped product yet.

## Limitations

- Still in private beta — no public pricing, no product to test
- Windows-only (inferred)
- Fully dependent on Google Cloud APIs (cost, latency, limits)
- Local GPU required for IDE rendering

## Links

- [EzVideo](https://ezvideo.net/)
