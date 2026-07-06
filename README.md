# Agentic AI Video Knowledge Base

A structured, interlinked knowledge base about AI agents that edit videos autonomously. Built and maintained collaboratively with LLM agents — the wiki is a persistent, compounding artifact that grows richer with every source ingested and every question asked.

## Quick Start

```bash
git clone <repo-url>
cd agentic-ai-video-knowledgebase
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
python3 kb/tools/search.py --page entities/runway-gen-4.md

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
- `CLAUDE.md` (root) — complete self-contained instructions for maintaining the wiki
- `AGENTS.md` (root) — entry point for Codex/other agents

Then:
1. Drop a source article into `kb/raw/` and ask: "Ingest this source"
2. Ask questions against the wiki — the agent searches pages and synthesizes answers
3. Ask: "Lint the wiki" periodically to catch contradictions and orphans

### Adding Sources

1. Save the article/resource as markdown in `kb/raw/`
2. Tell your LLM agent to process it
3. The agent writes a source summary, updates entity/concept pages, and logs the change

## Current Contents (July 2026)

- **21 entities**: VideoAgent, Crayotter, OpenMontage, UniVA, X-Cut, Runway Gen-4, Pika 2.5, Google Veo 3, Sora (discontinued), Kling 3.0, EzVideo, Shorz, CutClaw, video-use, AVE, Pilipili-AutoVideo, AI_Editor, Magicroll, Project Montage, Nano Banana
- **3 concepts**: Multi-Agent Orchestration, Self-Evaluation Loop, Agentic vs Generative
- **2 comparisons**: AI video models, agentic frameworks
- **1 chart**: Model quality vs speed vs cost

## Requirements

- **Python 3.10+** for search tool and chart generation
- **Obsidian** (optional) for graph view and rich browsing
- **API keys** (optional, for transcription/generation tools) — see individual tool docs
