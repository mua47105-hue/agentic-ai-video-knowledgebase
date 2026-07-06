---
title: Multi-Agent Orchestration
type: concept
tags: [architecture, orchestration, agents]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [video-agent, crayotter, openmontage, univa]
---

# Multi-Agent Orchestration

The coordination of multiple AI agents working together to produce a video edit. Instead of a single monolithic model generating the output, different agents handle different aspects: planning, shot selection, editing, reviewing.

## Approaches

### Graph-based orchestration (VideoAgent)
Agents are composed into a DAG via textual-gradient graph optimization. The graph is iteratively refined through structured quality signals. Treats workflow assembly as optimization over graph topology.

### Phase-based orchestration (Crayotter)
Three sequential phases (material prep → editing research → execution) with bounded resource pools per phase. Each phase produces inspectable artifacts.

### Agent-first (OpenMontage)
The AI coding assistant IS the orchestrator. It reads YAML pipeline manifests + Markdown director skills, calls Python tools, self-reviews, and checkpoints state.

### Plan-Act (UniVA)
Dual-agent: Plan Agent decomposes intent into subtasks, Act Agent executes via MCP-connected tool servers.

### Skill-based (X-Cut)
Dynamic composition of skills (`.md` files) at runtime. RuntimeSkillBuilder copies entry skill, stages scene/user/shared skills as references.

### Pipeline-as-code (AVE, CutClaw)
Editing pipelines defined as YAML manifests with named steps, retry conditions, and feedback loops.

## Why it matters

Single AI models generate one clip at a time. Multi-agent orchestration enables end-to-end video production — planning narratives, selecting shots, assembling timelines, adding effects, and reviewing quality — without human intervention at each step.

## Implementations

- [VideoAgent](../entities/video-agent) — 30+ agents, DAG orchestration
- [Crayotter](../entities/crayotter) — 3-phase, artifact-grounded
- [OpenMontage](../entities/openmontage) — agent-first, pipeline-driven
- [UniVA](../entities/univa) — Plan-Act dual-agent
- [X-Cut](../entities/x-cut) — skill-based composition
