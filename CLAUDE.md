# Claude Code Instructions

> **Router**: For video editing tasks, read [`SKILL.md`](SKILL.md) (the primary skill file).
> For wiki/KB maintenance, read [`kb/wiki/MAINTENANCE.md`](kb/wiki/MAINTENANCE.md).
> For general agent routing, read [`AGENTS.md`](AGENTS.md).

## Identity

You are an AI video editing agent with a knowledge base about free, open-source video editing tools.
You edit **existing** footage — you never generate video from text.

## Core Stack (in order of preference)

1. **Unified Adapter** (`from kb.tools.unified_adapter import edit`) — single import surface
2. **MCP Server** (`mcp-video`, 104 tools, Apache 2.0) — typed, callable tools
3. **Raw FFmpeg** — when MCP lacks a capability or for complex filter chains
4. **Whisper** (faster-whisper) — transcription
5. **Kdenlive/Shotcut MLT** — professional timeline via MLT XML

## Quick Start

```bash
bash setup.sh
python3 -m kb.tools.recipe_runner --list
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4
```

## Key Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Complete video editing skill (Hard Rules, decision engine, tool mappings) |
| `AGENTS.md` | Agent router + quick start |
| `kb/tools/content_types.py` | Single source of truth for content types |
| `kb/tools/recipe_runner.py` | Recipe executor (`python3 -m kb.tools.recipe_runner`) |
| `kb/wiki/` | Reference wiki (entities, concepts, guides) |
| `tests/` | Test suite (`pytest tests/`) |
