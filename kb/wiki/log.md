---
title: Change Log
type: log
created: 2026-07-06
updated: 2026-07-06
---

# Change Log

## [2026-07-06] scaffold | Wiki initialized

Created the initial wiki structure and schema. Empty wiki ready for first source ingestion.

## [2026-07-06] ingest | Deep Research Batch 1 — Agentic Frameworks

Researched and documented 5 agentic frameworks:
- **VideoAgent** — HKU multi-agent, textual-gradient graph optimization, 87-95% success rate
- **Crayotter** — v1.0.0, traceable multi-agent, 3.40/5 human eval
- **OpenMontage** — 34k+ stars, agent-first, 12 pipelines
- **UniVA** — Plan-Act dual-agent, MCP-native research prototype
- **X-Cut** — chat + Remotion, concept stage

Created 3 concept pages:
- Multi-Agent Orchestration
- Self-Evaluation Loop
- Agentic vs Generative

Updated overview and index.

## [2026-07-06] ingest | Deep Research Batch 2 — Generative Models + Commercial Tools + Remaining Frameworks

Researched and documented 12 entities:
- **Generative models**: Runway Gen-4, Pika 2.5, Google Veo 3, Sora (discontinued), Kling 3.0
- **Commercial tools**: EzVideo (private beta, Gemini director), Shorz (MCP-agent-callable)
- **Remaining frameworks**: CutClaw (music-sync), video-use (transcript-first, 14.8k stars), AVE (CLI with retry gates), Pilipili-AutoVideo (local, Mem0, CapCut export)

Running tally: 21 entities, 3 concepts, 0 sources, 0 guides, 0 comparisons, 0 charts.

## [2026-07-06] chart | Model Quality vs Speed vs Cost

Generated matplotlib bubble chart comparing 5 AI video models on quality, speed, and cost.

## [2026-07-06] ingest | Deep Research Batch 4 — Comparisons + Chart

Created:
- **AI Video Models 2026** comparison — Runway vs Pika vs Veo vs Kling vs Sora
- **Agentic Frameworks 2026** comparison — 10 frameworks across architecture, capabilities, maturity
- **Model Quality vs Speed vs Cost** chart — matplotlib bubble chart

Running tally: 21 entities, 3 concepts, 2 comparisons, 1 chart, 0 sources, 0 guides.

## [2026-07-06] refocus | Stripped generative models, rebuilt for editing-only focus

Major refocus: removed generative model pages (Runway, Pika, Sora, Veo, Kling, Nano Banana, EzVideo, Shorz, Magicroll) to archive. This wiki is now exclusively about AI agents that EDIT existing video footage.

Created:
- **Complete Free AI Video Editing Stack** guide — 4 options for free editing
- **MCP Servers for Video Editing** — comprehensive list of 15+ free MCP servers
- **MakeMyClip Editor** — zero-config FFmpeg tool for agents
- **CutAgent** — FFmpeg for agents with declarative EDL
- **CutRoom** — local-first film editor with session resume
- **Whisper Transcription Ecosystem** — free local subtitle tools

Rewrote overview entirely. New focus: "Free and open-source AI agents that EDIT existing video footage."

## [2026-07-06] ingest | Deep Research Batch 3 — Remaining Frameworks + Nano Banana

Researched and documented 4 more entities:
- **AI_Editor** — full-stack pipeline with CV scene analysis + Shotstack
- **Google Project Montage** — Google's multi-agent video builder
- **Magicroll AI Agent** — India-focused vernacular platform
- **Nano Banana** — keyframe lock for character consistency in AI video

Running tally: 21 entities, 3 concepts, 0 sources, 0 guides, 0 comparisons, 0 charts.

## [2026-07-06] guide | MCP Server Comparison Matrix — 12 servers across 30+ dimensions

Created definitive comparison of all known free MCP servers: 12 main servers, 5 transcription servers, 4 NLE control servers. Feature matrix with 30+ edit operations. Winner-by-use-case recommendations. Architecture comparison (tool-per-op vs pipeline vs minimal-executor vs NLE-control).

## [2026-07-06] skill | SKILL.md — Complete AI Video Editing Agent Skill

Created `SKILL.md` at root level — auto-discoverable by any LLM agent. Includes: identity, core stack, probe-plan-edit-review-iterate workflow, MCP tool usage by task, 50+ raw FFmpeg commands organized by operation, workflow templates (podcast-to-shorts, silence removal, auto-subtitles), edge case handling, validation checklist, config snippets for all agents, LLM recommendations.

## [2026-07-06] guide | FFmpeg Command Reference for AI Agents

Created exhaustive FFmpeg command reference organized by editing task (17 categories): probing, trimming, concatenation, transitions, color grading, subtitles, audio, speed, stabilization, scene detection, silence removal, effects, format conversion, compositing, quality/compression, batch processing, best practices. 100+ validated command patterns.

## [2026-07-06] guide | Local LLM Setup for Video Editing

Created guide for fully local, free LLM setup. Covers: Qwen2.5-Coder (88% FFmpeg accuracy per ELLMPEG paper) vs Llama 3.2 vs DeepSeek Coder, Ollama installation, integration with MCP servers/CutAgent/wtffmpeg, quantization options, GPU/CPU optimization, RAG setup for better accuracy, detailed benchmark table, decision matrix for local vs cloud.

## [2026-07-06] guide | Build Your Own AI Video Editor — 5-Level Blueprint

Created step-by-step blueprint from MVP (5 mins) to fully autonomous (1 month). Each level has exact steps, MCP config, capabilities, and estimated build time. Includes: architecture diagram, decision flowchart, agent prompt template, full installation script, verification checklist. Four levels: MVP → Workstation → Autonomous → Professional → Fully Autonomous.

## [2026-07-06] merge | SKILL.md — Integrated production techniques from video-use/editing-craft

Major SKILL.md rewrite: merged editing-craft's 12 Hard Rules (two-pass loudnorm, xfade offset validation, subtitle readability rules, SFX timing) with our agent-first MCP workflow. Added 6-phase decision engine (INIT → PROBE → CLASSIFY → PLAN → BUILD → VERIFY) — later expanded to 26 Hard Rules with color science, filter order, and loudness-range constraints, content-type routing table (8 content types with unique workflows), production technique library mapped to MCP tools, error recovery table with 12 specific failure patterns, contradiction log, project memory pattern. SKILL.md is now the definitive single-file agent skill for video editing.

## [2026-07-06] scripts | One-command setup + universal agent prompt

Created `scripts/setup.sh` — installs FFmpeg, mcp-video, faster-whisper, Whisper MCP server, CutAgent, optional Ollama + Qwen2.5-Coder 7B. Single curl command: `curl -fsSL https://raw.githubusercontent.com/mua47105-hue/agentic-ai-video-knowledgebase/main/scripts/setup.sh | bash`

Created `scripts/agent-prompt.md` — definitive copy-paste system prompt for any LLM agent. INIT → PROBE → CLASSIFY → PLAN → BUILD → VERIFY workflow with all Hard Rules and production techniques.

## [2026-07-06] enhance | FFmpeg reference — production-grade commands

Updated FFmpeg reference with: two-pass loudnorm (measurement + linear apply, explicit -ar 48000), xfade offset validation (pre-render bound check), cubic-ease easing for transitions, -50dB silence threshold (from -30dB), 0.3s silence removal padding with 0.03s audio fades, transition SFX integration.

## [2026-07-06] enhance | Blueprint — production gates + content-type routing

Updated blueprint with: content-type routing table (8 content types), production correctness checklist (10 items beyond tool check), contradiction log (6 disagreements surfaced to user), enhanced 6-phase decision flowchart (INIT → PROBE → CLASSIFY → PLAN → BUILD → VERIFY).

## [2026-07-06] audit | Full repo audit and fix

Ran comprehensive audit: fixed 7 broken links from archived pages, removed 2 dangling sources refs, fixed 4 dangling related refs, added 3 missing pages from index (Project Montage, AI video models comparison, chart), fixed README entity count (25) and stale example path, updated overview with complete entity list, added AGENTS.md/SKILL.md/scripts/ to CLAUDE.md structure, added scripts/ to AGENTS.md, added chart reference to index, hyperlinked archive entries, created missing assets directory, updated stale example slugs in CLAUDE.md and schema.

Overall tally: 16 active entities, 9 archived entities, 3 concepts, 4 guides, 3 comparisons, 1 chart, 0 sources, plus SKILL.md at root level.

## [2026-07-06] adapter | Unified Adapter — mcp_video hybrid architecture

Architected, built, and verified the Unified Adapter — a single import surface combining mcp_video.Client (60+ safe wrappers) with audited ffmpeg_adapter functions (44 audited+unique). Added 131 exportable symbols across three layers (later expanded to 151):

### New Files
- **`kb/tools/_mcp_bridge.py`** — 100-exports bridge module wrapping ~65 safe mcp_video methods. Each wrapper handles graceful degradation (mcp_video unavailable), BaseModel→dict conversion, and Hard Rule enforcement. Excludes 4 known-buggy mcp_video functions (ai_remove_silence, merge, pipeline, ai_transcribe).
- **`kb/tools/unified_adapter.py`** — 151-symbol single import surface routing: 7 overlapping functions → mcp_video, 92 new capabilities → mcp_video, 3 audited → ffmpeg_adapter, 29 unique → ffmpeg_adapter, plus VLM, decision_log, classifier, auto_recover, music, reframe. Supports `edit.info()`, `edit.merge()`, etc.
- **`scripts/verify_mcp_video.py`** — 99/99 checks on mcp_video 1.5.1 availability
- **`scripts/verify_unified_adapter.py`** — 159/159 checks on routing correctness
- **`kb/wiki/entities/mcp-video.md`** — entity page documenting 106 tools + 4 known bugs
- **`kb/wiki/concepts/unified-adapter.md`** — concept page with architecture diagram

### Changes
- **`SKILL.md`** — Added Hard Rule #25 (use unified_adapter), updated Core Stack order
- **`ffmpeg_adapter.py`** — Added `DeprecationWarning` on direct import (points to unified_adapter)
- **`test_ffmpeg_adapter.py`, `test_transcribe.py`** — Suppressed deprecation warning in legacy test suites
- **`kb/wiki/index.md`** — Added mcp-video entity and unified-adapter concept

### Routing Decisions
- mcp_video wins for: info, trim, resize, speed, stabilize, color_grade, text_subtitles
- ffmpeg_adapter wins for: merge, silence_remove, transcribe (buggy/inferior in mcp_video)
- ffmpeg_adapter unique: J/L-cuts, scopes, quality metrics, project files, render profiles, loudnorm

## [2026-07-07] upgrade | Recipe Packs — 6 YAML workflow templates

Created `recipes/` directory with 6 one-command YAML recipe packs for common video editing patterns:

- **Podcast-to-shorts** — extract 30-60s engaging segments, format as TikTok/Reels shorts
- **Wedding highlights** — extract key moments (vows, first kiss, speeches, first dance), color grade, add music bed
- **Sports highlights** — beat-synced action reel with speed ramping (pre-roll slow → impact → slow-mo release)
- **Documentary assembly** — transcript-first, topic-segmented, B-roll overlay with J/L-cuts
- **Tutorial editing** — screen + face PiP, chapter markers, callout animations
- **Vlog assembly** — montage-style with music bed, fast pacing, dynamic transitions

Created `kb/tools/recipe_runner.py` — YAML recipe executor with variable substitution, parallel for_each loops, quality gates, and output manifest generation.

## [2026-07-07] upgrade | MLT XML Export — NLE Interoperability

Created `kb/tools/mlt_export.py` — converts `.aevp` project files to MLT XML format compatible with Kdenlive and Shotcut. Supports round-trip: trim, merge (xfade), resize, color_grade, text_subtitles, speed changes, and J/L-cuts. Added `render_mlt()` for headless melt rendering and `export_fcpxml()` for Final Cut Pro handoff via OpenTimelineIO.

## [2026-07-07] upgrade | Compliance Reporter — 6 Delivery Specs

Created `kb/tools/compliance.py` — checks videos against EBU R128, ATSC A/85, Netflix Sound Mix, BBC, YouTube, and TikTok streaming specs. Reports pass/fail per metric (LUFS, true-peak, LRA, stream integrity, VMAF). Outputs markdown or JSON reports.

## [2026-07-07] upgrade | Content Adapter — Pexels + Freesound

Created `kb/tools/content_adapter.py` — parallel to music_adapter. Provides `footage.search()`/`footage.download()` for Pexels video API (CC0, 30k+ clips) and `sfx.search()`/`sfx.download()` for Freesound API (500k+ SFX). Includes license sidecars (.license.json), NC filtering, LUT pack helpers (IWLTBAP).

## [2026-07-07] upgrade | VLM Adapter — Visual Perception (Gated)

Created `kb/tools/vlm_adapter.py` — gated/opt-in adapter for Qwen2.5-VL visual queries. Provides `describe_frame()`, `describe_clip()`, `find_moment()`, and `verify_claim()`. OFF by default — requires `VLM_ENABLED=1` env var and `ollama pull qwen2.5-vl:7b`.

## [2026-07-07] integrate | Unified adapter — all new modules registered

Updated `kb/tools/unified_adapter.py` with `compliance_report`, `export_mlt`, `render_mlt`, `export_fcpxml`, `run_recipe`, `footage`, `sfx`, `lut_list`, `lut_apply`, `vlm` — all accessible via single import.

## [2026-07-07] update | CLAUDE.md, AGENTS.md, README.md, SKILL.md, agent-prompt.md

Updated all configuration and documentation files to reflect new capabilities. Added recipe packs section to SKILL.md core stack. Updated CLI documentation with recipe runner and compliance reporter examples.

## [2026-07-07] phase-2 | Prove-it-stays-fixed — testing infrastructure + CI

Created `scripts/doctor.py` — single-command environment diagnostic (binaries, Python deps, KB modules, config). Checks 25+ items with pass/fail per check and exact FIX command for each failure. Supports `--quiet` and `--json` modes.

Created `scripts/make_synthetic_clip.py` — deterministic synthetic test footage generator using only `ffmpeg -f lavfi`. Produces talking_head (30s), podcast (60s), vlog_short (15s vertical), and silent (10s no-audio) clips. Fully reproducible, no downloads.

Created `scripts/test_recipes_e2e.py` — pytest-compatible end-to-end recipe runner test. Runs each of 7 recipes against synthetic clips, asserts manifest validity and output file existence. Gracefully skips when mcp_video is not installed.

Created `scripts/_test_utils.py` — shared check()/skip()/run_main() helpers. All 7 existing test scripts now import from this single module instead of duplicating the pattern.

Fixed 3 broken test scripts: `test_transcribe.py` (NameError on shutil, now imports early), `test_ffmpeg_adapter.py` (removed dead subprocess re-import, added atexit cleanup), `verify_unified_adapter.py` §14 (tautology replaced with real inspect-based parameter check).

Added 5 new test scripts covering previously untested modules: `test_content_adapter.py` (LUT list fix + error handling), `test_vlm_adapter.py` (gating off/on), `test_reframe_adapter.py` (constant name fix + synthetic reframe), `test_chart_models.py` (PNG generation), `test_search.py` (BM25 query + empty query).

Added `.github/workflows/ci.yml` — 4-job CI (doctor, parse-tests, e2e-tests, unit-tests) on ubuntu + macOS. Added `pytest.ini` config in `pyproject.toml`. Added `.github/CODEOWNERS`.

Current tally: 16 active entities, 9 archived entities, 4 concepts, 5 guides, 3 comparisons, 1 chart, 6 recipes, 0 sources, plus SKILL.md at root level.

## [2026-07-07] phase-3 | Decision engine — auto-recovery + content-type classifier

Created `kb/tools/classifier.py` — zero-cloud, pure-rule content-type classifier. Extracts 11 signals from ffprobe + Whisper (duration, aspect ratio, scene density, LUFS, LRA, word rate, filler ratio, silence ratio). Decision tree maps to 10 content types with confidence and reasoning. Includes `recommend_recipe()` for zero-shot recipe suggestion.

Created `kb/tools/auto_recover.py` — `RecoveryEngine` with 5 RECOVERY_STRATEGIES (`loudnorm_remeasure`, `render_force_sync`, `add_silent_audio`, `rerun_subtitles`). Bounded: 2 retries per step, 3 rounds per recipe. Tracks all attempts via `RecoveryResult` and `summary()`.

Wired both into `kb/tools/recipe_runner.py`:
- `--recommend` flag: classify input and print recommended recipe, then exit
- `--force-content-type` flag: override recipe content_type before execution
- Pre-run classification warning when detected type mismatches recipe expectation
- Post-rendering recovery loop: quality gate failures trigger strategy lookup and step re-execution
- Manifest now includes `classification` and `recovery_attempts` fields

Updated `SKILL.md` Phase 0 and Phase 5 with as-of-Phase 3 notes referencing classifier and auto_recover. Updated `scripts/agent-prompt.md` RECOVER section. Added Concrete implementation section to `kb/wiki/concepts/self-evaluation-loop.md`. Added `--recommend` and `--force-content-type` to README.md quick start.

## [2026-07-08] phase-4 | Intelligence add-ons — VLM verification, music ranking, decision audit log, sources ingest, wiki coverage gaps, lint script

### VLM highlight verification
Added `verify_highlights()` to `kb/tools/vlm_adapter.py` — takes a list of picked moments (each with start/end/category), samples frames at stride intervals, runs `describe_frame()` and `verify_claim()` for each, returns per-moment verification with confidence. Wired into `recipe_runner.py` — when a recipe declares `verify_moments: true` (wedding-highlights.yaml opts in), moments from `recipe.find_key_moments` are verified post-execution. Failed verifications (confidence > 0.7) print warnings to stderr. Manifest includes `vlm_verification` array.

### BPM/mood-aware music ranking
Added `rank_by_fit()` to `kb/tools/music_adapter.py` — downloads 30s previews, runs `music_describe()`, scores each candidate by BPM proximity and mood match against the recipe's content_type defaults (vlog=100BPM happy, social-short=140BPM energetic, cinematic=80BPM epic, etc.). Returns candidates sorted by `fit_score` with `bpm`, `mood`, `fit_reasoning` attached. Wired into `vlog-assembly.yaml`, `shorts-punchy.yaml`, and `wedding-highlights.yaml` — each now runs `music.rank_by_fit` between `music.search` and `music.download`.

### Decision audit log
Created `kb/tools/decision_log.py` — `DecisionLogger` that captures every auto-decision with timestamp, type, action, input, output, reasoning, and success status. Wired into `recipe_runner.py`: logger created at start of `run_recipe()`, logs classification, each recipe step, each quality gate pass/fail, each recovery attempt, and each VLM verification. Manifest includes `decision_log` array. CLI has `--explain` flag that prints the log in human-readable form after the manifest JSON.

### Sources ingestion
Created 5 source-of-record pages: `sources/ebu-r128.md`, `sources/itu-r-bs-1770-4.md`, `sources/netflix-sound-mix-spec.md`, `sources/ellmpeg-paper.md`, `sources/mcp-video-docs.md`. Each has full frontmatter (title/type/tags/created/updated/related), Citation, Key claims, How this connects, Contradictions, and Notes sections. Updated `compliance-reporter.md` frontmatter to cite ebu-r128, itu-r-bs-1770-4, netflix-sound-mix-spec. Updated `local-llm-setup.md` to cite ellmpeg-paper. Updated `mcp-video.md` to cite mcp-video-docs. Added `## Sources` section to `index.md`.

### Wiki coverage gaps
Created 5 new pages: `concepts/color-space-management.md`, `concepts/multi-cam-editing.md`, `concepts/chroma-key.md`, `guides/hardware-acceleration.md`, `entities/hyperframes.md`. Each has ≥150 words of body content, full frontmatter, and ≥2 inbound links from other wiki pages. Updated `index.md` with new pages under appropriate sections. Added inbound links from `ffmpeg-command-reference.md`, `video-agent.md`, `recipe-packs.md`, `mcp-video.md`, and `unified-adapter.md`.

### Lint script + CI
Created `scripts/lint_wiki.py` — checks for orphan pages, broken internal links, missing frontmatter fields, stale pages, and generative-model focus leaks. Writes findings to `kb/wiki/backlog.md` (committed). Integrated into CI as `lint-wiki` job (fails on broken links). Fixed 1 broken link (SKILL.md reference from unified-adapter.md) and 2 missing `tags` frontmatter fields found by first run.

### Current tally
25 entities (16 active + 9 archived), 7 concepts, 5 guides, 3 comparisons, 1 chart, 6 recipe packs, 5 source pages, root SKILL.md, `scripts/lint_wiki.py`. Extended tools: MLT export, compliance reporter, content adapter, VLM adapter (gated), decision_log, classifier, auto_recover.
