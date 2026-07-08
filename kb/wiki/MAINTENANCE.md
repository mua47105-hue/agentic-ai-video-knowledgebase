# Wiki Maintenance Instructions

> This file is for wiki/KB maintenance tasks. For video editing, read `SKILL.md`.

## Page conventions

- Every page is markdown with `.md` extension, kebab-case filenames
- Every page gets YAML frontmatter: `title`, `type`, `tags`, `created`, `updated`, `sources`, `related`
- Internal links use relative paths without `.md`: `[MCP Servers](entities/mcp-video-servers)`
- Keep pages focused. If a page exceeds ~300 lines, split into sub-pages

## Page types

| Type | Description |
|------|-------------|
| `entity` | Concrete things — tools, companies, models |
| `concept` | Abstract ideas — techniques, approaches |
| `source` | Summary of an ingested document |
| `guide` | How-to / workflow |
| `comparison` | Side-by-side of 2+ entities |
| `chart` | References a matplotlib chart image |

## Operations

### Ingest
1. Read the source in `kb/raw/`
2. Write a source summary in `kb/wiki/sources/`
3. Update/create entity/concept pages
4. Update `overview.md` if significant
5. Update `index.md`
6. Append to `log.md` with format: `## [YYYY-MM-DD] ingest | Title`

### Query
1. Read `index.md` to find relevant pages
2. Read those pages
3. Synthesize answer with citations

### Lint
1. Scan for contradictions
2. Find orphan pages (no inbound links)
3. Check for stale claims
4. Report findings
