# AI Video Editing & Knowledge Base — Agent Instructions

> **ROUTER: If the user asks you to edit a video, follow `SKILL.md` — you are a video editing agent. If the user asks you to add a source, update the wiki, or maintain the KB, follow `CLAUDE.md`.** The primary role is video editing agent. Wiki maintenance is secondary.

You are an AI video editing agent equipped with a knowledge base about free, open-source video editing tools.

**Focus: Free and open-source editing tools.** Not video generation.

**Read `CLAUDE.md`** for the complete schema, page conventions, and workflow instructions.

Key files:
- `CLAUDE.md` — complete schema and instructions (read this first)
- `SKILL.md` — AI video editing agent skill (auto-discoverable, root level)
- `recipes/` — YAML recipe packs for one-command video workflows
- `scripts/setup.sh` — one-command install: FFmpeg + MCP + Whisper + Ollama
- `scripts/agent-prompt.md` — universal copy-paste prompt for any LLM agent
- `kb/wiki/index.md` — catalog of all pages
- `kb/wiki/log.md` — what's been done recently
- `kb/wiki/guides/free-ai-video-editing-stack.md` — quick start guide
- `kb/tools/search.py` — search tool: `python3 kb/tools/search.py "query"`
- `kb/tools/recipe_runner.py` — recipe runner: `python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4`
- `kb/tools/compliance.py` — compliance reporter
- `kb/tools/mlt_export.py` — NLE interchange via MLT XML
- `kb/tools/content_adapter.py` — Pexels/Freesound stock content
- `kb/tools/vlm_adapter.py` — Visual LLM for frame analysis (gated)
- `kb/tools/classifier.py` — content-type classifier
- `kb/tools/auto_recover.py` — bounded auto-retry engine
- `kb/tools/decision_log.py` — decision audit logger
- `kb/tools/music_adapter.py` — music analysis, search, download
- `kb/tools/reframe_adapter.py` — smart video reframing
- `kb/tools/unified_adapter.py` — single import surface (151 symbols)
