# Agentic AI Video Knowledge Base

A structured, interlinked knowledge base about AI agents that edit videos autonomously. Built and maintained collaboratively with LLM agents — the wiki is a persistent, compounding artifact that grows richer with every source ingested and every question asked.

## Quick Start

```bash
git clone <repo-url>
cd agentic-ai-video-knowledgebase

# One-command install (FFmpeg + MCP + Whisper + optional Ollama)
curl -fsSL https://raw.githubusercontent.com/mua47105-hue/agentic-ai-video-knowledgebase/main/scripts/setup.sh | bash
```

### Browse the wiki

Open Obsidian on the `kb/wiki/` folder, or just read the markdown files directly:

- [Overview](kb/wiki/overview.md) — what this wiki covers
- [Index](kb/wiki/index.md) — catalog of every page
- [Log](kb/wiki/log.md) — change history

### Search

```bash
# BM25 search
python3 kb/tools/search.py "your query"

# With vector reranking (requires sentence-transformers)
python3 kb/tools/search.py "your query" --vector

# View a specific page
python3 kb/tools/search.py --page entities/mcp-video-servers.md

# Output as JSON
python3 kb/tools/search.py "text to video" --json
```

### Generate charts

```bash
python3 kb/tools/chart_models.py
```

## Structure

```
agentic-ai-video-knowledgebase/
├── README.md
├── .gitignore
└── kb/
    ├── raw/              # Source documents (drop files here to ingest)
    ├── schema/
    │   └── AGENTS.md     # Instructions for LLM wiki maintainers
    ├── tools/
    │   ├── search.py     # Hybrid BM25/vector search CLI
    │   └── chart_models.py  # Matplotlib chart generator
    └── wiki/
        ├── index.md      # Content catalog
        ├── log.md        # Change log
        ├── overview.md   # Living synthesis
        ├── entities/     # Tools, companies, models
        ├── concepts/     # Core ideas and techniques
        ├── sources/      # Source document summaries
        ├── guides/       # How-to guides and workflows
        ├── comparisons/  # Side-by-side comparisons
        └── charts/       # Generated visualizations
```

## How to Use

### With an LLM Agent (Claude Code, OpenCode, Codex, etc.)

Just tell the agent: **"Clone this repo and explore it. Understand the project and what I'm building."**

The agent will automatically discover:
- `SKILL.md` (root) — primary role: AI video editing agent (auto-loaded first)
- `CLAUDE.md` (root) — secondary role: wiki maintenance (source ingestion, page updates)
- `AGENTS.md` (root) — entry point for Codex/other agents with routing to both roles

Then:
1. Drop a source article into `kb/raw/` and ask: "Ingest this source"
2. Ask questions against the wiki — the agent searches pages and synthesizes answers
3. Ask: "Lint the wiki" periodically to catch contradictions and orphans

### Adding Sources

1. Save the article/resource as markdown in `kb/raw/`
2. Tell your LLM agent to process it
3. The agent writes a source summary, updates entity/concept pages, and logs the change

## Current Contents (July 2026)

- **25 entities** (16 active + 9 archived): MCP servers, Whisper ecosystem, video-use, MakeMyClip, CutAgent, CutRoom, VideoAgent, OpenMontage, Crayotter, UniVA, CutClaw, AVE, AI_Editor, Pilipili-AutoVideo, X-Cut, Project Montage + gen models archived
- **3 concepts**: Multi-Agent Orchestration, Self-Evaluation Loop, Agentic vs Generative
- **3 comparisons**: MCP server matrix (12 servers), agentic frameworks (10 frameworks), AI video models
- **Root-level SKILL.md**: Auto-discoverable by any LLM agent, complete video editing skill
- **4 guides**: Free stack setup, FFmpeg command reference, local LLM setup, build-your-own blueprint
- **1 chart**: Model quality vs speed vs cost
- **Scripts**: One-command setup (`scripts/setup.sh`), universal agent prompt (`scripts/agent-prompt.md`)

## Requirements

- **Python 3.10+** for search tool and chart generation
- **Obsidian** (optional) for graph view and rich browsing
- **API keys** (optional, for transcription/generation tools) — see individual tool docs
