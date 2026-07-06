---
title: X-Cut
type: entity
tags: [chat-driven, remotion, skill-based, open-source]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [openmontage, crayotter]
---

# X-Cut

Chat-driven AI video editing agent by MeiGen-AI with real-time Remotion rendering. Users describe edits in natural language; the agent dynamically selects and combines skills, edits a multi-track timeline, and renders results instantly via Remotion Player.

## Architecture

Skill-based, four-stage flow: **Entry Skill → Scene Selection → RuntimeSkillBuilder staging → Flexible Execution**.

Skills are organized as `.md` files under `.xcut_skills/system/`:
- `entry/` — single top-level capability
- `scenes/` — vlog, marketing, free-edit templates
- `operations/` — audio, dubbing, MG animations, transitions, track delete
- `styles/` — visual style presets
- `tools/` — asset analysis, script building, MG code generation, music generation

## Capabilities

- Intelligent asset analysis (shot scale, camera movement, content understanding)
- Script generation from uploaded assets
- MG animation generation from NL descriptions (LLM → Remotion JSX)
- Chat-based editing: add/remove/modify dubbing, animations, subtitles, voice styles
- Drag-and-drop timeline for manual override
- Editing style sharing as reusable `.md` Skills

## Status

**Code not yet released** as of July 2026. The repository has minimal commits and is at concept stage. Roadmap items include web release, standalone skills (Claude/OpenCode pluggable), CLI, long video support, and talking-head editing.

## Key Differentiator

Real-time Remotion rendering in a chat interface — every edit is instantly visible. Skill-based architecture makes editing styles portable as markdown files.

## Links

- [GitHub](https://github.com/MeiGen-AI/X-Cut)
