---
title: Google Project Montage
type: entity
tags: [google, multi-agent, mcp, open-source]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [google-veo-3, nano-banana, ezvideo]
---

# Google Project Montage

Google's modular, AI-powered video builder. A multi-agent framework that transforms a storyboard outline into a production-quality video using Google's first-party models: Gemini, Veo 3.1, Nano Banana, and Lyria.

## Architecture

Modular multi-agent framework on Google ADK:

- **MCP Server** — `mcp_montage/` with FastAPI, port 8001
- **MCP Client / ADK Web UI** — `mcp_client/` on port 8000
- **Sign Server** — `sign_server/` on port 8080

Central **Gemini-powered orchestrator** delegates to:
- **Storyboard Agent** — drafts scene-by-scene plan, selects optimal input images
- **Image Agent** — Nano Banana for character integration + asset resizing
- **Video Agent** — Veo 3.1 for cinematic clip generation
- **Post-production** — automated transitions + generative music (Lyria)

## Capabilities

- Storyboard outline → production-quality video (fully automated)
- Multi-agent orchestration with MCP-based tool protocol
- Enterprise data integration via GCP
- Deployable on Cloud Run
- ADK Web UI for workflow management

## Key Differentiator

Google's own multi-agent video production framework leveraging first-party models in a unified pipeline. The "Google-native" alternative to Runway and Sora.

## Limitations

- Optimized for GCP (though modular)
- Requires GCP project with billing
- Early-stage (initial commit May 2026, ~9 stars)
- Requires 3 services running simultaneously
- GCP API costs can be significant at scale

## Links

- [GitHub](https://github.com/google/project-montage)
