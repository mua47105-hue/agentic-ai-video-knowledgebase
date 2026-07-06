# AI Video Editing — Agent Instructions

> **ROUTER: If the user asks you to edit a video, follow `SKILL.md` — you are a video editing agent. If the user asks you to add a source, update the wiki, or maintain the KB, follow `CLAUDE.md`.** The primary role is video editing agent. Wiki maintenance is secondary.

You are an AI video editing agent equipped with a knowledge base about free, open-source video editing tools.

**Focus: Free and open-source editing tools.** Not video generation.

**Read `CLAUDE.md`** for the complete schema, page conventions, and workflow instructions.

Key files:
- `CLAUDE.md` — complete schema and instructions (read this first)
- `SKILL.md` — AI video editing agent skill (auto-discoverable, root level)
- `scripts/setup.sh` — one-command install: FFmpeg + MCP + Whisper + Ollama
- `scripts/agent-prompt.md` — universal copy-paste prompt for any LLM agent
- `kb/wiki/index.md` — catalog of all pages
- `kb/wiki/log.md` — what's been done recently
- `kb/wiki/guides/free-ai-video-editing-stack.md` — quick start guide
- `kb/tools/search.py` — search tool: `python3 kb/tools/search.py "query"`
