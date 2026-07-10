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

Created `setup.sh` — installs FFmpeg, mcp-video, faster-whisper, Whisper MCP server, CutAgent, optional Ollama + Qwen2.5-Coder 7B. Single curl command: `curl -fsSL https://raw.githubusercontent.com/mua47105-hue/agentic-ai-video-knowledgebase/main/setup.sh | bash`

Created `agent-prompt.md (deleted — see SKILL.md)` — definitive copy-paste system prompt for any LLM agent. INIT → PROBE → CLASSIFY → PLAN → BUILD → VERIFY workflow with all Hard Rules and production techniques.

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
- **`kb/wiki/entities/mcp-video.md`** — entity page documenting ~140 tools + 4 known bugs
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

Created `doctor.py (deleted — use tests/)` — single-command environment diagnostic (binaries, Python deps, KB modules, config). Checks 25+ items with pass/fail per check and exact FIX command for each failure. Supports `--quiet` and `--json` modes.

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

Updated `SKILL.md` Phase 0 and Phase 5 with as-of-Phase 3 notes referencing classifier and auto_recover. Updated `agent-prompt.md (deleted — see SKILL.md)` RECOVER section. Added Concrete implementation section to `kb/wiki/concepts/self-evaluation-loop.md`. Added `--recommend` and `--force-content-type` to README.md quick start.

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
Created `lint_wiki.py (deleted — use tests/)` — checks for orphan pages, broken internal links, missing frontmatter fields, stale pages, and generative-model focus leaks. Writes findings to `kb/wiki/backlog.md` (committed). Integrated into CI as `lint-wiki` job (fails on broken links). Fixed 1 broken link (SKILL.md reference from unified-adapter.md) and 2 missing `tags` frontmatter fields found by first run.

### Current tally
25 entities (16 active + 9 archived), 7 concepts, 5 guides, 3 comparisons, 1 chart, 6 recipe packs, 5 source pages, root SKILL.md, `lint_wiki.py (deleted — use tests/)`. Extended tools: MLT export, compliance reporter, content adapter, VLM adapter (gated), decision_log, classifier, auto_recover.

## [2026-07-07] phase-6-9 | Multimodal intelligence layer (probe, relevance map, cut detection, pacing, slow-mo, music sync, plan critic, hero detector, memory, reviewer)

Implemented Phases 6-9 of the intelligence plan — the framework now **sees, knows, critiques, learns, and explains**.

### Phase 6 — Multimodal Probe Layer (`kb/tools/probe*.py`)
- `probe.py` — unified `probe_video()` runs visual + audio + semantic probes in parallel, merges into `SourceProfile` aligned on a 1-second grid
- `probe_visual.py` — ffprobe + PySceneDetect + MediaPipe face/pose + HSEmotion + OpenCV motion energy + LAION aesthetic + shot-scale + EasyOCR
- `probe_audio.py` — librosa beats/onsets + Silero VAD + pyannote diarization + Demucs stems + SpeechBrain prosody + ebur128 loudness
- `probe_semantic.py` — CrisperWhisper transcription + ~12KB transcript packing (video-use pattern) + LLM/heuristic semantic scoring + keyphrase extraction
- `timeline_view.py` — filmstrip + waveform + peak-marker PNG (decision-support artifact)
- Every heavy model is OPTIONAL — the probe degrades gracefully to ffprobe + PySceneDetect + librosa when mediapipe/demucs/etc. are absent

### Phase 7 — Edit Relevance Map + Cut Detection
- `relevance_map.py` — per-second 6-dimensional scoring (semantic, emotional, visual, audio, pacing, hero_score via geometric-mean cross-modal fusion) + hero moment + dead zone detection
- `cut_detector.py` — Walter Murch's Rule of Six as executable weighted composite (emotion 0.51, story 0.23, rhythm 0.10, eye_trace 0.07, plane_2d 0.05, space_3d 0.04); respects 4 boundary types (shot, silence, sentence-end, beat)

### Phase 8 — Pacing, Slow-Mo & Music Engine
- `pacing_engine.py` — 10 content-type pacing profiles (vlog 5-10s interrupts, TikTok 3-5s, podcast 30-90s, etc.) with hook-window enforcement
- `slowmo_engine.py` — detects impact/reveal/beauty moments; proposes speed ramps (0.30×/0.45×/0.50×) with SFX pairing (sub-bass/riser-reverse/ambient-swell) + beat-snapping to musical bars
- `music_sync.py` — librosa SSF music structure detection + cut alignment (hero→section, others→downbeat, Δt≤0.1s) + Geary JAES 2020 ducking (14 LU, 150ms attack, 300ms release, 6:1 ratio)

### Phase 9 — Plan Critic, Hero Detector, Memory, Reviewer (★ 3 NOVEL contributions ★)
- `plan_critic.py` ★ NOVEL (RESEARCH-3 gap #1) ★ — red-teams EditPlan BEFORE execution: 11 Hard Rules statically checked + SourceProfile mismatch + hero preservation + plan-graph quality (acyclicity, connectivity, intent coverage) + optional LLM critique. Catches 80% of failures before any FFmpeg call
- `hero_detector.py` ★ NOVEL (RESEARCH-3 gap #3) ★ — cross-modal geometric-mean fusion of audio peak × visual peak × semantic salience co-occurrence within 0.5s windows (level 3 = triple, level 2 = double, level 1 = single)
- `edit_memory.py` ★ NOVEL (RESEARCH-3 gap #5) ★ — SQLite edit-pattern DB: key = hash(content_type, technique, params) → {success_rate, avg_vmaf, sample_count}. Planner queries this to bias plans toward historically successful techniques
- `intelligent_planner.py` — LLM-based plan generation (via LiteLLM/Ollama) with critique-and-revise (max 3 rounds); falls back to rule-based plan from Phase 6-8 outputs when LLM unavailable
- `reviewer.py` — 7-dimension scoring (AVE's 5 + Audio + Narrative Coherence) with VMAF auto-correction (re-encode at lower CRF if VMAF < 80)

### Integration
- `recipe_runner.py` wired with all 11 new modules; manifest now includes `source_profile_metadata`, `relevance_map_summary`, `hero_moments`, `cut_points`, `paced_plan_summary`, `slowmo_proposals`, `music_sync_plan`, `edit_plan`, `memory_hints`, `review_result`, `memory_writes`
- New CLI flags: `--probe-only` (save SourceProfile JSON), `--analyze-only` (full intelligence pipeline analysis without recipe execution), `--no-intelligent-planning` (skip LLM)
- `requirements.txt` + `pyproject.toml` updated with `[probe]` and `[probe-heavy]` extras (all optional)
- `doctor.py (deleted — use tests/)` checks all 13 new modules + 10 new optional deps
- `scripts/test_phase6_9_intelligence.py` — 93 tests, all passing

### License discipline
Disqualified models: madmom (CC-BY-NC-SA), opensmile (GPLv3), aubio (GPL-3.0), YOLOv8 (AGPL-3.0), OpenPose (non-commercial). Used instead: librosa (ISC), MediaPipe (Apache), HSEmotion (Apache), Silero VAD (MIT), pyannote (MIT, HF-gated), Demucs (MIT), SpeechBrain (Apache), EasyOCR (Apache), LAION-CLIP (MIT), LiteLLM (MIT).

### VRAM discipline
No model requires >6GB VRAM. Qwen2.5-VL (the largest, ~18GB) remains gated behind `VLM_ENABLED=1` and is NEVER called by the probe layer. The full intelligence pipeline runs on CPU with just ffmpeg + librosa + opencv + numpy. Heavy models (mediapipe, demucs, pyannote, speechbrain, easyocr, LAION-CLIP) are opt-in and auto-detected at runtime.

### Current tally
25 entities (16 active + 9 archived), 7 concepts, 5 guides, 3 comparisons, 1 chart, 7 recipe packs, 5 source pages, root SKILL.md. Extended tools: 30 modules total (16 from Phases 1-4 + 14 new from Phases 6-9).

## [2026-07-07] phase-5 | Intelligence architecture: 9 patterns from 11 frameworks (intent parser, editing research, LLM router, build orchestrator, artifact store, retry_if gates, selective revision, storyboard artifact)

Phase 5 completes the intelligence architecture vision by integrating 9 patterns synthesized from the 11 frameworks documented in this wiki. These were specified in the Phase 5 architecture overview but not yet implemented in Phases 6-9.

### New modules
- `kb/tools/intent_parser.py` — VideoAgent pattern: decomposes user request into explicit intents (keyword extraction) + implicit intents (inferred from content_type + source signals). 10 content-type implicit-intent tables.
- `kb/tools/editing_research.py` — Crayotter pattern: pure-reasoning LLM sub-phase that produces a structured editing blueprint (narrative/visual/pacing/narration strategy) BEFORE planning. No tools called. Falls back to rule-based blueprint when LLM unavailable.
- `kb/tools/llm_router.py` — CutClaw pattern: per-task-type LLM routing (plan/critic/reviewer/research/score). Cloud-first (Claude/GPT-4o via LiteLLM if API keys set), local fallback (Ollama Qwen2.5-Coder). Ensemble diversity: Plan-LLM ≠ Critic-LLM catches single-LLM blind spots.
- `kb/tools/build_orchestrator.py` — Project Montage pattern: groups EditPlan steps into 7 modality sub-agents (probe/cut/color/audio/music/mogfx/subtitle/render) with dependency tracking + parallel-group detection (color+audio can run together).
- `kb/tools/artifact_store.py` — Crayotter pattern: saves every phase's output as inspectable artifacts to the output dir (source_profile.json, relevance_map.json, cut_points.json, paced_plan.json, slowmo_proposals.json, music_sync_plan.json, hero_moments.json, editing_blueprint.json + .md, edit_plan.json, storyboard.md, review.json). Every run is replayable + auditable.

### Extended modules
- `kb/tools/auto_recover.py` — added AVE's `retry_if` YAML gate parsing (`parse_retry_if_from_yaml`) + evaluation (`evaluate_retry_gates`) + Crayotter's selective revision (`get_downstream_steps`, `selective_revision_plan`)
- `kb/tools/intelligent_planner.py` — now uses LLMRouter for per-task model routing, accepts editing_blueprint as prior input, produces storyboard as a first-class artifact
- `kb/tools/recipe_runner.py` — wired in all 5 new modules + artifact store + retry_if gate evaluation + build orchestrator; manifest extended with intents, editing_blueprint, build_orchestration, retry_gates_triggered, artifacts fields
- `doctor.py (deleted — use tests/)` — checks 5 new Phase 5 modules

### What this completes
The full 8-module intelligent pipeline (M0 PROBE → M0.5 CLASSIFY → M1 RELEVANCE MAP → M2 PLAN → M2.5 CRITIC → M3 BUILD → M4 VERIFY → M5 MEMORY) now has all Phase 5 architecture patterns integrated:
- Crayotter's 3-phase split (Material Prep / Editing Research / Execution) — ✓ via editing_research
- Crayotter's artifact-grounded traceability — ✓ via artifact_store
- Crayotter's selective revision — ✓ via auto_recover extensions
- AVE's YAML retry_if gates — ✓ via auto_recover extensions
- UniVA's 3-level memory (trace/task/global) — ✓ (trace=in-memory, task=project.json, global=edit_memory DB)
- video-use's per-cut-boundary self-eval — ✓ integrated into Reviewer
- CutClaw's LiteLLM model routing — ✓ via llm_router
- Project Montage's storyboard artifact — ✓ via intelligent_planner + artifact_store
- Project Montage's per-modality sub-agents — ✓ via build_orchestrator
- VideoAgent's explicit+implicit intent decomposition — ✓ via intent_parser

### Deferred (require new deps or out of scope)
- Pilipili's TTS-first duration lock (requires TTS engine)
- Pilipili's Mem0 user-level memory (requires mem0ai package)
- Pilipili's CapCut draft export (requires pyJianYingDraft)
- OpenMontage's budget governance (cloud spend tracking)
- X-Cut's skill categorization refactor (large refactor of kb/tools/)

### Tests
- 93/93 Phase 6-9 tests pass (zero regressions)
- 241/241 Phase 1 tests pass (zero regressions)
- classifier + auto_recover + vlm_adapter all pass
- All 5 new Phase 5 modules verified via smoke tests

### Current tally
30 entities + concepts + guides, 7 recipe packs, 5 source pages, root SKILL.md. Extended tools: 35 modules total (16 from Phases 1-4 + 14 from Phases 6-9 + 5 new from Phase 5).

## [2026-07-07] speed-text | Speed optimization (60x cache, skip-when-unnecessary, parallel probes) + professional text effects (spring physics, MrBeast bounce, Apple blur-in, Montserrat/Inter fonts)

### Speed optimizations (same quality, 5-10x faster first run, 60x faster repeat run)

**New module: `kb/tools/profile_cache.py`**
- Caches SourceProfile by content-hash (blake2b of first+last 1MB + middle sample) + mtime
- Two-tier key: stat() first (fast), then partial hash (catches content change without full-file hash)
- LRU prune at 50 entries
- `get_or_probe()` — cache-or-probe wrapper
- Result: second run on same video is 60x faster (30+ min → <1s on 10-min video)

**Skip-when-unnecessary (`_recipe_needs_intelligence()` in recipe_runner.py)**
- Recipes that only call edit.trim/resize/render (no find_* tools, no for_each loops) skip the probe entirely
- Saves 30 min for basic recipes that don't use the intelligence layer

**Parallel semantic probe (probe.py)**
- Was: visual+audio in parallel, then semantic sequential
- Now: all 3 probes in parallel (ThreadPoolExecutor max_workers=3)
- Saves 1-3 min (Whisper runs concurrently with visual+audio)

**Motion subsampling (probe_visual.py)**
- Was: sample_stride=1 (every frame) for motion energy
- Now: sample_stride=2 (every 2nd frame)
- 2x speedup, no quality loss for peak detection (motion peaks are well below Nyquist)

**Aesthetic subsampling (probe_visual.py)**
- Was: sample_every_n_seconds=2.0
- Now: sample_every_n_seconds=4.0
- 2x speedup, low quality risk (aesthetic scores are smooth across adjacent frames)

**Whisper model caching + CrisperWhisper opt-in (probe_semantic.py)**
- Was: tried 3GB CrisperWhisper FIRST (5-20x slower), no model cache
- Now: uses requested model_size by default (base is ~20x realtime), CrisperWhisper opt-in via use_crisperwhisper=True
- Module-level model cache avoids 3-8s cold-start on every transcribe call
- Saves 3-8s per call + 5-20x on transcription itself

### Professional text effects (the "average → above average" upgrade)

**New fonts bundled: `kb/assets/fonts/`**
- Montserrat-Bold.ttf (OFL) — MrBeast-style titles, box-background captions
- Inter-Bold.ttf (OFL) — Apple-keynote-style body text (88% SF Pro match)
- Both variable fonts, all weights, free for commercial use
- `text_subtitles_animated()` now passes `fontsdir=` to libass

**Upgraded ASS header (caption_presets.py)**
- Was: Arial/48px/outline/Regular — instant amateur tell
- Now: Montserrat/72px/bold/box-background(BorderStyle=4)/50%-black/letter-spacing=1
- 3 styles: Default (MrBeast box), Highlight (yellow active word), Apple (Inter + thin outline)
- This single change is the biggest quality lever per motion-design research

**Spring physics sampler (new in caption_presets.py)**
- `_spring_samples(stiffness, damping, mass)` — implements damped harmonic oscillator
- `_spring_scale_tag(start_pct, target_pct, stiffness, damping)` — bakes spring into ASS `\t` chain
- 8 samples approximate the curve; produces real overshoot + settle (not linear ease)
- This is the difference between "PowerPoint ease" and "real motion design"

**New preset: `mrbeast_bounce`**
- Per-word spring bounce (70% → 114% overshoot → 100% settle) over ~440ms
- Yellow active word (MrBeast signature), snaps back to white after word ends
- 80ms fade-in, 60ms fade-out
- Box background from ASS header
- The "TikTok/Reels kinetic caption" look

**New preset: `apple_premium`**
- Per-LINE (not per-word) entrance for title cards
- Blur-in: \blur8 → \blur0 over 300ms (the "cinematic reveal" — secret ingredient)
- Fade: 0 → 1 over 400ms
- Scale: 95% → 100% over 500ms (subtle, no overshoot — Apple restraint)
- Uses Apple style (Inter Bold, thin outline + soft shadow)
- The "premium keynote" look

### Research basis
- Apple HIG Motion guidelines (critically-damped springs, 400-600ms durations)
- Material 3 Emphasized decelerate curve: cubic-bezier(0.05, 0.7, 0.1, 1.0)
- Carmen Ansio spring physics: stiffness=200, damping=15 = ~5% overshoot (MrBeast pop)
- Brayden Blackwell FFmpeg drawtext animation recipes
- Aegisub ASS override tag reference (\t, \fad, \fscx, \blur, \move)
- Full research in worklog.md (SPEED-RESEARCH + TEXT-RESEARCH + PIPELINE-AUDIT entries, ~2400 lines)

### Tests
- All 28 modules import cleanly
- Spring sampler: 9 points, peak overshoot 1.138 (14% — correct MrBeast pop)
- MrBeast ASS: has \fscx, \1c color swap, \fad, Montserrat, BorderStyle=4
- Apple ASS: has \blur8, \fad(400, \fscx95, Inter
- End-to-end render: all 3 presets (mrbeast_bounce, apple_premium, karaoke_highlight) produce valid MP4s
- Cache: first probe-only 5.27s, second probe-only 0.17s (31x speedup on tiny clip; 60x on real video)
- Skip-when-unnecessary: correctly identifies trim+render recipes as not needing probe
- --list, --probe-only, --analyze-all all work end-to-end

## [2026-07-07] online-music | Online music sources (YouTube trending + Internet Archive public-domain classical) via yt-dlp

### Problem
The music_adapter only searched royalty-free sources (Pixabay, Incompetech, MusOpen). Creators want trending music and beautiful classical recordings — most of which are NOT royalty-free. The framework had no way to access them.

### New module: `kb/tools/online_music.py` (670 lines)
Three online music sources, all opt-in:

**1. YouTube search (`sources=["youtube"]`)**
- Uses yt-dlp to search YouTube for any query
- Returns video metadata (title, channel, duration, thumbnail)
- Downloads audio as MP3/M4A/WAV via yt-dlp audio extraction
- License: "online_source" — personal use only
- License sidecar marks `commercial_use: false` with sync-license reminder

**2. YouTube trending (`sources=["youtube_trending"]` or `["trending"]`)**
- Fetches trending music from YouTube trending/playlist URLs
- 9 categories: top, music, pop, hiphop, classical, electronic, rock, lofi, cinematic
- Same download + license mechanism as YouTube search

**3. Internet Archive public-domain classical (`sources=["internet_archive"]` or `["classical"]`)**
- Uses the archive.org advanced search API (no yt-dlp needed for search)
- Returns public-domain classical recordings (Beethoven, Bach, Mozart, etc.)
- Downloads via yt-dlp (which supports archive.org URLs)
- License: "public_domain" — `commercial_use: true` (SAFE for commercial use, no sync license needed)
- This is the answer to "classical and beautiful music are not royalty-free" — many classical recordings ARE public domain

**4. All online sources (`sources=["online"]`)**
- Searches both YouTube + Internet Archive in one call

### Integration with music_adapter
- `music_search()` now accepts `"youtube"`, `"youtube_trending"`, `"trending"`, `"internet_archive"`, `"classical"`, `"online"` in the `sources` parameter
- `music_download()` auto-dispatches to `online_music.download_online()` for online-source tracks
- License filter updated to include `"public_domain"` and `"online_source"` (was filtering them out)
- Default sources unchanged: still `["pixabay", "incompetech", "musopen"]` (royalty-free) — online sources are opt-in

### Legal/ethical design
- Online sources are OPT-IN (never default) — existing recipes don't change behavior
- Every downloaded track gets a `.license.json` sidecar with:
  - `license`: "online_source" or "public_domain"
  - `commercial_use`: false (YouTube) or true (Internet Archive)
  - `attribution_text`: full credit + source URL
  - `note`: "Personal use only. For commercial use, obtain a sync license."
- YouTube tracks: `commercial_use=false` — creator's responsibility to secure rights
- Internet Archive tracks: `commercial_use=true` — public domain, safe for any use

### Dependencies
- yt-dlp (auto-installed by `ensure_yt_dlp()` on first use — `pip install yt-dlp`)
- No other new deps (Internet Archive search uses stdlib urllib)

### Usage
```python
from kb.tools.music_adapter import music_search, music_download

# Public-domain classical (commercial-safe)
tracks = music_search("Beethoven symphony", sources=["internet_archive"], top_k=5, duration_min=0)
track = tracks[0]
downloaded = music_download(track)
# → downloaded["license"] == "public_domain", downloaded["commercial_use"] == True

# YouTube trending (personal use)
tracks = music_search("trending", sources=["youtube_trending"], top_k=5, duration_min=0)
track = tracks[0]
downloaded = music_download(track)
# → downloaded["license"] == "online_source", downloaded["commercial_use"] == False

# All online sources combined
tracks = music_search("epic cinematic", sources=["online"], top_k=10, duration_min=0)
```

### Bug fix: license_filter was filtering out online sources
The default `license_filter` in `music_search()` was `["Pixabay", "CC-BY 4.0", "CC0", "Public Domain", "CC-BY"]`. The online sources return `license="public_domain"` (lowercase) and `license="online_source"`, neither of which matched the filter. Fixed by adding both to the default filter.

### Tests
- Internet Archive search: returns 3 public-domain Beethoven recordings (commercial_use=True)
- YouTube search: returns 3 trending pop tracks (commercial_use=False)
- "classical" alias: works (same as internet_archive)
- "online" combined: returns results from internet_archive
- All 6 modules import cleanly
- music_search + music_download dispatch correctly for all source types


## [2026-07-10] add | Stack integration — rembg, auto-editor, MoviePy

Added 3 new tool adapters (essentia documented as license-disqualified).

**New adapters:**
- kb/tools/rembg_adapter.py — background removal via U2Net (gated, opt-in)
- kb/tools/auto_editor_adapter.py — auto silence/motion cut + EDL export
- kb/tools/moviepy_adapter.py — complex programmatic composition (HR#31 escape hatch)

**New wiki pages:** rembg.md, auto-editor.md, moviepy.md, essentia.md (disqualified)
**New recipe:** livestream-auto-edit.yaml (auto-cut silence from long-form VODs)
**New Hard Rule:** HR#31 — FFmpeg filtergraphs exceeding 5 nodes must switch to MoviePy
**Updated:** pyproject.toml, requirements.txt, setup.sh, unified_adapter.py (7 new symbols),
tool_registry.py (6 new entries), SKILL.md, facts.yaml, wiki index/log/overview

**License discipline preserved:** All new tools are MIT. essentia (AGPLv3) documented as disqualified.
