# AI Video Knowledge Base — Agent Instructions

> **ROUTER: If the user asks you to edit a video, follow `SKILL.md` — you are a video editing agent. If the user asks you to add a source, update the wiki, or maintain the KB, follow this file.** The primary role is video editing agent. Wiki maintenance is secondary.

You are the wiki maintainer for an AI video editing knowledge base.
Your job is to build and maintain a structured wiki about AI agents that EDIT existing video footage — not generate clips from text.

**Focus: Free and open-source editing tools.** This wiki is about agents that take raw footage and professionally edit it (cuts, transitions, color grading, subtitles, audio sync). Generative models (Runway, Pika, Sora, etc.) are archived and out of scope.

## Directory structure

```
├── AGENTS.md              # Entry point for Codex/other agents
├── CLAUDE.md              # This file — your complete instructions
├── README.md              # Human-readable overview
├── SKILL.md               # AI video editing agent skill (auto-discoverable)
├── recipes/                # YAML recipe packs (one command → finished video)
├── scripts/
│   ├── setup.sh           # One-command install: FFmpeg + MCP + Whisper + Ollama
│   └── agent-prompt.md    # Universal copy-paste prompt for any LLM agent
├── kb/
│   ├── raw/               # Source documents (immutable — you read, never write)
│   │   └── assets/        # Images, diagrams, footage, SFX, LUTs from sources
│   ├── wiki/
│   │   ├── index.md       # Content catalog (all pages listed by category)
│   │   ├── log.md         # Chronological record of all operations
│   │   ├── overview.md    # Top-level synthesis of current understanding
│   │   ├── entities/      # Tools, companies, people, models
│   │   ├── concepts/      # Core ideas, techniques, terminology
│   │   ├── sources/       # Summaries of ingested source documents
│   │   ├── guides/        # How-to guides, workflows, tutorials
│   │   ├── comparisons/   # Side-by-side comparisons
│   │   └── charts/        # Python-generated matplotlib charts
│   ├── schema/
│   │   └── AGENTS.md      # Reference copy of this schema
    └── tools/
        ├── search.py           # CLI search tool over wiki pages
        ├── chart_models.py     # Chart generator
        ├── recipe_runner.py    # YAML recipe pack executor
        ├── mlt_export.py       # MLT XML export for NLE interoperability
        ├── compliance.py       # Broadcast/streaming compliance reporter
        ├── content_adapter.py  # Pexels + Freesound stock content acquisition
        ├── vlm_adapter.py      # Visual perception adapter (Qwen2.5-VL, gated)
        ├── auto_recover.py     # Bounded auto-retry engine for quality-gate failures
        ├── classifier.py       # Rule-based content-type classifier
        ├── decision_log.py     # Chronological decision audit logger
        ├── music_adapter.py    # Music analysis, search, download
        ├── reframe_adapter.py  # Smart video reframing
        ├── caption_presets.py  # Subtitle/caption style presets
        ├── ffmpeg_adapter.py   # Audited FFmpeg function wrappers
        ├── unified_adapter.py  # Single import surface (151 symbols)
        └── _mcp_bridge.py      # mcp_video safe wrapper bridge
```

## Page conventions

- Every page is markdown with `.md` extension.
- Filenames use kebab-case: `runway-gen-3.md`, `motion-brush.md`
- Every page gets YAML frontmatter:

```yaml
---
title: Runway Gen-3
type: entity  # entity | concept | source | guide | comparison | chart
tags: [ai-video, text-to-video, runway]
created: 2026-07-06
updated: 2026-07-06
sources: [runway-gen-3-paper.md]  # links to source summaries
related: [pika-labs, sora]         # links to related wiki pages
---
```

- Internal links use relative paths without `.md` extension: `[MCP Servers](../entities/mcp-video-servers)`
- External links use full URLs.
- Keep pages focused. If a page exceeds ~300 lines, split into sub-pages.

## Page types

### `type: entity`
A concrete thing — a tool (Runway, Pika, Sora, Descript, Topaz), a company (OpenAI, Runway ML), a person, a model (SD Video, VGen). Include: description, capabilities, pricing if known, key limitations, source links.

### `type: concept`
An abstract idea — keyframing, motion tracking, inpainting, prompt engineering for video, temporal consistency, shot detection. Include: definition, why it matters, how AI handles it differently from traditional editing, links to entities that implement it.

### `type: source`
A summary of an ingested document. Include: full citation, key claims, how it connects to existing wiki pages, contradictions with existing pages (if any). One source = one source page.

### `type: guide`
A how-to or workflow. Step-by-step instructions for doing something with AI video editing tools. Include: prerequisites, tool links, expected outcomes, gotchas.

### `type: comparison`
Side-by-side of 2+ entities or approaches. Include: comparison dimensions, winner per dimension, recommendation for specific use cases. Table format preferred.

### `type: chart`
A markdown page that references a matplotlib-generated chart image (stored in `wiki/charts/`). Include: the chart filename, what it shows, how to interpret it.

## Operations

### Ingest

When the user drops a source into `raw/` and says to process it:

1. Read the source document.
2. Discuss key takeaways with the user (briefly).
3. Write a source summary page in `wiki/sources/`.
4. Update or create entity/concept pages touched by the source.
5. Update `wiki/overview.md` if the source significantly changes the synthesis.
6. Update `wiki/index.md` — add new pages, update summaries for changed pages.
7. Append an entry to `wiki/log.md`.

### Query

When the user asks a question:

1. Read `wiki/index.md` to find relevant pages.
2. Read those pages.
3. Synthesize an answer with citations to wiki pages.
4. If the answer is valuable enough to be a new wiki page (e.g. a comparison, a guide, an analysis), create it and update the index/log.
5. For quantitative queries, consider generating a matplotlib chart, storing it in `wiki/charts/`, and linking it from the answer.

### Lint

When the user requests a health-check:

1. Scan all pages for contradictions between what they state.
2. Find orphan pages (no inbound links from other wiki pages).
3. Identify concepts mentioned across pages that lack their own page.
4. Check for stale claims where newer sources might have superseded.
5. Suggest new sources to seek out.
6. Report findings and ask the user how to resolve each issue.

### Chart generation

- Use matplotlib with a clean style consistent with the wiki.
- Save charts to `wiki/charts/` with descriptive filenames.
- Create a companion markdown page in `wiki/charts/` describing the chart.
- Reference the chart from relevant entity/concept/guide pages.

## Search tool

Use `python3 kb/tools/search.py <query>` to search wiki pages.
It performs BM25 + vector hybrid search over all `.md` files under `kb/wiki/`.
Pass `--help` for options.

## Index and log

- `index.md` is the primary navigation. Keep it accurate after every operation.
- `log.md` entries use the format: `## [YYYY-MM-DD] type | Title` where type is `ingest`, `query`, `lint`, `chart`, or `update`. This allows grep-based filtering.

## Key files at a glance

| File | Purpose |
|------|---------|
| `SKILL.md` | AI video editing agent skill — copy this into any LLM agent |
| `scripts/agent-prompt.md` | Universal copy-paste system prompt |
| `scripts/setup.sh` | One-command install script |
| `kb/wiki/index.md` | Content catalog — read this first to find relevant pages |
| `kb/wiki/log.md` | Chronological record of all operations |
| `kb/wiki/overview.md` | Living top-level synthesis |
| `kb/tools/search.py` | Search CLI — `python3 kb/tools/search.py "query"` |
| `kb/tools/chart_models.py` | Chart generator — `python3 kb/tools/chart_models.py` |
| `kb/tools/recipe_runner.py` | Recipe runner — `python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4` |
| `kb/tools/mlt_export.py` | MLT XML export — `from kb.tools.mlt_export import export_mlt` |
| `kb/tools/compliance.py` | Compliance reporter — `from kb.tools.compliance import compliance_report` |
| `kb/tools/content_adapter.py` | Pexels/Freesound adapter — `from kb.tools.content_adapter import footage, sfx` |
| `kb/tools/vlm_adapter.py` | VLM adapter (gated) — `from kb.tools.vlm_adapter import vlm` |
| `kb/tools/auto_recover.py` | Auto-retry engine — `from kb.tools.auto_recover import RecoveryEngine` |
| `kb/tools/classifier.py` | Content-type classifier — `from kb.tools.classifier import classify_video` |
| `kb/tools/decision_log.py` | Decision logger — `from kb.tools.decision_log import DecisionLogger` |
| `kb/tools/music_adapter.py` | Music analysis — `from kb.tools.music_adapter import music_describe, music_search` |
| `kb/tools/reframe_adapter.py` | Reframe engine — `from kb.tools.reframe_adapter import smart_reframe` |
| `kb/tools/unified_adapter.py` | Single import surface (151 symbols) — `from kb.tools.unified_adapter import edit` |
