---
title: UniVA
type: entity
tags: [plan-act, mcp, open-source, research, generalist]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [openmontage, video-agent]
---

# UniVA

Universal Video Agent — an open-source next-generation video generalist system that unifies video understanding, segmentation, editing, and generation into a single agentic framework. Uses a Plan Agent + Act Agent dual-agent architecture with MCP-native extensibility.

## Architecture

**Plan Agent** — Decomposes high-level user intent into structured subtasks. Multi-round co-creation with implicit intent reading (understands vague and evolving instructions). Proactive — auto-plans, checks, and suggests better shots.

**Act Agent** — Executes tasks via MCP-connected tool servers. Supports atomic + workflow tools across video, AI, and non-AI categories.

**Memory**: Three-level hierarchical memory (trace/global, user, task) for consistent characters, styles, and preferences across long-form narratives.

## Capabilities

- Multi-scene, multi-role, multi-shot narratives
- Super HD consistent output with stable identity
- Ultra-long & fine-grained editing
- Complex multi-step workflows (text→image→video→edit→segment→synthesize)
- CLI and web UI
- Supports OpenAI, DeepSeek, Qwen, local models

## Key Technologies

- MCP (Model Context Protocol) tool fabric
- Wan2.1 for video editing
- Qwen2.5-VL for video understanding
- Wavespeed API for generation
- UniVA-Bench benchmark suite

## Key Differentiator

First open-source video generalist unifying understanding + segmentation + editing + generation. Plan-Act dual-agent with MCP-native extensibility for complex multi-step workflows. Deep memory system for coherent long-form narratives.

## Limitations

- Research prototype — strictly prohibited for commercial use without written permission
- Limited maturity (16 commits, 516 stars)
- Requires Wavespeed API key for generation
- Documentation still maturing

## Links

- [GitHub](https://github.com/univa-agent/univa)
- [Paper](https://arxiv.org/abs/2511.08521)
