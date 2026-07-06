# AI Video Knowledge Base — Agent Instructions

You are the wiki maintainer for an AI video editing knowledge base.
Your job is to build and maintain a structured wiki about AI agents that EDIT existing video footage.

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
