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

### Run recipe packs (one-command video workflows)

```bash
# List available recipes
python3 -m kb.tools.recipe_runner --list

# Run a recipe
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4 --output shorts/
python3 -m kb.tools.recipe_runner recipes/wedding-highlights.yaml ceremony.mp4

# Auto-classify input and recommend a recipe
python3 -m kb.tools.recipe_runner --recommend input.mp4

# Override recipe content type
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4 --force-content-type social-short
```

### Check delivery compliance

```bash
python3 -c "
from kb.tools.compliance import compliance_report
report = compliance_report('output.mp4', 'youtube_streaming')
print('Passed:', report['passed'])
"
```

## Structure

```
agentic-ai-video-knowledgebase/
├── README.md
├── .gitignore
├── recipes/              # YAML recipe packs (one-command video workflows)
│   ├── podcast-to-shorts.yaml
│   ├── wedding-highlights.yaml
│   ├── shorts-punchy.yaml
│   ├── sports-highlights.yaml
│   ├── documentary-assembly.yaml
│   ├── tutorial-editing.yaml
│   └── vlog-assembly.yaml
└── kb/
    ├── raw/              # Source documents (drop files here to ingest)
    │   └── assets/       # Downloaded footage, SFX, LUTs, music
    ├── schema/
    │   └── AGENTS.md     # Instructions for LLM wiki maintainers
    ├── tools/
    │   ├── auto_recover.py     # Bounded auto-retry engine for quality-gate failures
    │   ├── caption_presets.py  # Subtitle/caption style presets
    │   ├── chart_models.py     # Matplotlib chart generator
    │   ├── classifier.py       # Rule-based content-type classifier
    │   ├── compliance.py       # Broadcast/streaming compliance reporter
    │   ├── content_adapter.py  # Pexels + Freesound stock acquisition
    │   ├── decision_log.py     # Chronological decision audit logger
    │   ├── ffmpeg_adapter.py   # Audited FFmpeg function wrappers
    │   ├── _mcp_bridge.py      # mcp_video safe wrapper bridge
    │   ├── mlt_export.py       # MLT XML export for NLE interop
    │   ├── music_adapter.py    # Music analysis, search, download
    │   ├── recipe_runner.py    # YAML recipe pack executor
    │   ├── reframe_adapter.py  # Smart video reframing (vertical/horizontal)
    │   ├── search.py           # Hybrid BM25/vector search CLI
    │   ├── unified_adapter.py  # Single import surface (151 symbols)
    │   └── vlm_adapter.py      # Visual LLM (gated/opt-in)
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
4. Run: `python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4` for one-command video
5. Run: `compliance_report('output.mp4', 'youtube_streaming')` for delivery compliance

### Adding Sources

1. Save the article/resource as markdown in `kb/raw/`
2. Tell your LLM agent to process it
3. The agent writes a source summary, updates entity/concept pages, and logs the change

## Current Contents (July 2026)

- **25 entities** (16 active + 9 archived): MCP servers, Whisper ecosystem, video-use, MakeMyClip, CutAgent, CutRoom, Hyperframes, VideoAgent, OpenMontage, Crayotter, UniVA, CutClaw, AVE, AI_Editor, Pilipili-AutoVideo, X-Cut, Project Montage + gen models archived
- **7 concepts**: Multi-Agent Orchestration, Self-Evaluation Loop, Agentic vs Generative, Unified Adapter, Color-Space Management, Multi-Cam Editing, Chroma Key
- **3 comparisons**: MCP server matrix (12 servers), agentic frameworks (10 frameworks), AI video models
- **Root-level SKILL.md**: Auto-discoverable by any LLM agent, complete video editing skill
- **6 guides**: Free stack setup, FFmpeg command reference, local LLM setup, build-your-own blueprint, recipe packs, hardware acceleration
- **1 chart**: Model quality vs speed vs cost
- **6 recipe packs**: Podcast-to-shorts, wedding highlights, sports highlights, documentary assembly, tutorial editing, vlog assembly
- **5 source pages**: EBU R128, ITU-R BS.1770-4, Netflix Sound Mix Spec, ELLMPEG paper, mcp-video docs
- **Scripts**: One-command setup (`scripts/setup.sh`), universal agent prompt (`scripts/agent-prompt.md`), wiki lint (`scripts/lint_wiki.py`)
- **Extended tools**: MLT export, compliance reporter, content adapter (Pexels + Freesound), VLM adapter (gated), decision logger, classifier, auto-recover engine

## Requirements

- **Python 3.10+** for search tool and chart generation
- **Obsidian** (optional) for graph view and rich browsing
- **API keys** (optional, for transcription/generation tools) — see individual tool docs
