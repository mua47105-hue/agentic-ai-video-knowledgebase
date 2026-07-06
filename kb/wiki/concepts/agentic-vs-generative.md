---
title: Agentic vs Generative — The Two Layers
type: concept
tags: [architecture, taxonomy]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [multi-agent-orchestration, runway-gen-4, pika-2-5]
---

# Agentic vs Generative — The Two Layers

A critical distinction in AI video that is often confused. These are two separate layers that work together.

## Generative Layer

The models that produce video frames from prompts: Runway Gen-4, Pika 2.5, Google Veo 3, Kling 3.0. These take a text/image prompt and generate a clip. They have no concept of narrative, pacing, or editing — they just generate.

**Examples**: Runway (text-to-video, image-to-video), Sora, Pika, Veo

## Agentic Layer

The systems that decide *what* to generate, *when* to cut, *how* to sequence clips, *where* to add transitions and effects. These are the "editors" that orchestrate the generative models.

**Examples**: VideoAgent, Crayotter, OpenMontage, X-Cut, AVE

## How they combine

A typical agentic video editing pipeline:

1. **Plan** — Agent understands the brief, plans shot list, narrative structure
2. **Generate** — Agent calls generative models (Runway, Veo, etc.) for each shot
3. **Edit** — Agent assembles clips, adds transitions, syncs audio
4. **Review** — Agent evaluates output, retries if needed

The same person or agent can use multiple generative models for different shots. For example, using Pika for social clips and Runway for hero shots.

## Relationship

The agentic layer is the brain; the generative layer is the hands. Neither is useful alone for autonomous video editing.
