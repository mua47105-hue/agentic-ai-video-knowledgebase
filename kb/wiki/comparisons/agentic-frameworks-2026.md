---
title: Agentic Frameworks — Comparison (2026)
type: comparison
tags: [comparison, frameworks, agents]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [video-agent, crayotter, openmontage, univa, x-cut, cutclaw, video-use, agentic-video-editor, pilipili-autovideo, project-montage]
---

# Agentic Frameworks — Comparison (2026)

## Quick Pick

| Need | Framework |
|------|-----------|
| Most capable academic framework | [VideoAgent](../entities/video-agent) (30+ agents, 87-95% success) |
| Best open-source to actually run today | [Crayotter](../entities/crayotter) (v1.0.0, traceable) |
| Biggest community / most pipelines | [OpenMontage](../entities/openmontage) (34k stars, 12 pipelines) |
| For Claude Code users | [video-use](../entities/video-use) (14.8k stars, transcript-first) |
| Best for music-synced editing | [CutClaw](../entities/cutclaw) (beat detection, hours-long footage) |
| Local-first / CapCut export | [Pilipili-AutoVideo](../entities/pilipili-autovideo) (Mem0 memory, keyframe lock) |

## Architecture Comparison

| Framework | Architecture Type | Agent Count | Orchestration Method | Runtime |
|-----------|-----------------|-------------|---------------------|---------|
| VideoAgent | Multi-agent DAG | 30+ | Textual-gradient graph opt | Python + LLM APIs |
| Crayotter | 3-phase pipeline | 3-5 | LangGraph StateGraph | Python + LLM APIs |
| OpenMontage | Agent-first | N/A (varies) | AI coding assistant = orchestrator | Claude/Codex + Python tools |
| UniVA | Plan-Act dual-agent | 2 (+MCP tools) | Plan agent → Act agent | Python + MCP servers |
| X-Cut | Skill-based | N/A | RuntimeSkillBuilder | Python + Remotion |
| CutClaw | Multi-agent MLLM | 3 | Screenwriter → Editor → Reviewer | Python + LiteLLM |
| video-use | Agent skill | 1 (+sub-agents) | LLM reasons from transcript | Claude Code skill |
| AVE | Pipeline with retry gates | 4 | YAML pipeline → Director → Editor → Reviewer | Python + Gemini ADK |
| Pilipili-AutoVideo | 7-layer pipeline | 1 (orchestrator) | LangGraph → sequential stages | Python + cloud APIs |
| Project Montage | Multi-agent MCP | 3-4 | Gemini orchestrator → sub-agents via MCP | Google ADK |

## Capability Comparison

| Capability | VideoAgent | Crayotter | OpenMontage | video-use | Pilipili | AVE | CutClaw |
|------------|-----------|-----------|-------------|-----------|----------|-----|---------|
| Text-to-video gen | ✗ (retrieval only) | ✗ (retrieval only) | ✅ (14 providers) | ✗ (animation only) | ✅ (Kling/Seedance) | ✗ | ✗ |
| Real footage editing | ✅ | ✅ | ✅ | ✅ | ✗ (generates) | ✅ | ✅ |
| Music sync | Partial | ✗ | ✗ | ✗ | ✗ | ✗ | ✅ (core) |
| Self-evaluation | ✅ | ✅ | ✅ | ✅ | ✗ | ✅ | ✅ |
| Character consistency | ✗ | ✗ | ✅ (Nano Banana) | ✗ | ✅ (keyframe lock) | ✗ | ✗ |
| Memory / learning | ✗ | ✗ | ✗ | project.md only | ✅ Mem0 | ✗ | ✗ |
| CapCut export | ✗ | ✗ | ✗ | ✗ | ✅ | ✗ | ✗ |
| API cost efficiency | 60% reduction | Moderate | Varies | Low | High (multiple APIs) | Low | High |
| Local deployment | Partial (GPU needed) | Partial | ✅ (zero API keys option) | ✅ | ✅ (Docker) | ✗ (Gemini API) | ✗ (API-dependent) |

## Maturity Comparison

| Framework | Stars | Version | Last Release | Has Paper | Actually Runable |
|-----------|-------|---------|-------------|-----------|-----------------|
| OpenMontage | 34k+ | Active | Ongoing | ✗ | ✅ (agent required) |
| video-use | 14.8k | Active | Ongoing | ✗ | ✅ (Claude Code) |
| Crayotter | ~900 | v1.0.0 | June 2026 | ✅ | ✅ |
| CutClaw | ~905 | v1.0 | 2026 | ✅ | ✅ |
| UniVA | ~516 | Pre-release | 2026 | ✅ | ⚠️ (research only) |
| AVE | ~458 | Active | 2026 | ✗ | ✅ |
| Pilipili-AutoVideo | ~185 | Active | 2026 | ✗ | ✅ (Docker) |
| VideoAgent | Active | Pre-release | June 2026 | ✅ | ⚠️ (multi-API setup) |
| Project Montage | ~9 | Pre-release | May 2026 | ✗ | ⚠️ (early stage) |
| X-Cut | ~25 | Concept | 2026 | ✗ | ❌ (code not released) |
