# Agent Instructions

> **Router**: For video editing tasks, read [`SKILL.md`](SKILL.md).
> For wiki/KB maintenance tasks, read [`kb/wiki/MAINTENANCE.md`](kb/wiki/MAINTENANCE.md) (or the schema section below).

## Quick Start

```bash
# Install
bash setup.sh

# List recipes
python3 -m kb.tools.recipe_runner --list

# Analyze a video (intelligence layer only, no execution)
python3 -m kb.tools.recipe_runner --analyze-only input.mp4 --output /tmp/

# Run a recipe
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4
```

## Key Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Video editing agent skill (auto-loaded first, ~250 lines of rules + TOC) |
| `kb/tools/` | Python tool library (42 modules) |
| `recipes/` | YAML recipe packs (12 one-command workflows) |
| `kb/wiki/` | Reference wiki (entities, concepts, guides, comparisons) |
| `tests/` | Test suite (pytest, run with `pytest tests/`) |

## Wiki Maintenance

- **Ingest**: drop a source into `kb/raw/` and ask "ingest this source"
- **Query**: ask questions against the wiki — the agent searches and synthesizes
- **Lint**: `python3 -m kb.tools.search` or the wiki lint script
- **Page conventions**: see `kb/wiki/MAINTENANCE.md` (or the original schema in `CLAUDE.md`)

## Content Types

All content types are defined in `kb/tools/content_types.py` (single source of truth).
Recipe YAMLs must use values from the `ContentType` enum. The test suite enforces this.
