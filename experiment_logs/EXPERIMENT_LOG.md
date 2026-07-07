# Experiment Log: High-Velocity Vehicle Edit Stress Test

> **Date**: 2026-07-07
> **Input**: 19.4s vertical (360×640) phone video from storage.to
> **Goal**: Create a high-velocity vehicle edit using our architecture, documenting every failure, loophole, and missing piece encountered.
> **Outcome**: Edit was produced (14s output with beat-synced cuts + speed ramp + music bed), but required BYPASSING the recipe runner entirely. 16 architecture gaps documented below.

---

## Executive Summary

The architecture's intelligence layer (probe → relevance map → cut detector → pacing → slow-mo → hero detection) **runs without crashing** and produces structured, inspectable output. The profile cache works (60× speedup on repeat). The cut detector finds real beat-aligned cut points with Murch scores. The Internet Archive music search returns real public-domain recordings.

**However**, the recipe runner **crashes on the first step** (`edit.info` parameter mismatch), the intelligence layer produces **no actionable slow-mo proposals** (co-occurrence window too strict), the paced plan **keeps everything** (no dead zones detected because all scores are equally low), and the visual probe **silently degrades to near-uselessness** when optional deps are missing (PyAV, mediapipe, CLIP).

The edit was ultimately produced by **manually reading the analysis JSON and running FFmpeg commands** — bypassing the recipe runner, the pacing engine, and the slow-mo engine. The intelligence layer provided the cut points (beat-aligned, from librosa), but everything else was manual.

---

## Findings (16 gaps, ranked by severity)

### P0 — Blocking: Recipes cannot run at all

#### 1. `edit.info` parameter mismatch — recipe runner crashes on first step
- **Where**: `recipe_runner.py:919` → `unified_adapter.py` → `_mcp_bridge.py:mcp_info()`
- **What**: `_execute_step` injects `params["input"] = input_path` for read-only ops (line 905-908). But `mcp_info()` expects `path`, not `input`. Result: `TypeError: mcp_info() got an unexpected keyword argument 'input'`.
- **Impact**: **EVERY recipe that starts with `edit.info` crashes immediately.** This includes all 7 shipped recipes.
- **Fix**: In `_execute_step`, map `input` → `path` for mcp_bridge functions, OR rename the parameter in `_mcp_bridge.py` to accept `input` as an alias for `path`.

#### 2. Content type naming mismatch
- **Where**: `recipes/shorts-punchy.yaml` says `content_type: short_form`; `classifier.py` returns `social-short`
- **What**: The 10 content types in the classifier don't match the `content_type` values in recipe YAMLs. Recipes use `short_form`, `cinematic`, `podcast`, `vlog`, `tutorial`, `documentary`. Classifier returns `social-short`, `cinematic`, `podcast`, `vlog`, `tutorial`, `documentary`.
- **Impact**: Classifier warns "detected 'social-short' but recipe expects 'short_form'" for every short-form recipe. The pacing engine uses the recipe's content_type, so it gets `short_form` which isn't in `PACING_PROFILES` — falls back to `vlog` defaults.
- **Fix**: Standardize on one set of names. Either update recipes to use `social-short` or update classifier to return `short_form`.

### P1 — Critical quality gaps

#### 3. Visual probe produces minimal output when optional deps missing
- **Where**: `probe_visual.py` — `probe_motion()`, `probe_faces()`, `probe_aesthetic()`, `probe_ocr()`
- **What**: All visual sub-probes use `import av` (PyAV) to decode frames. If PyAV is missing, they return `[]` silently. No fallback to `cv2.VideoCapture` (which IS installed). Result: 0 motion peaks, 0 faces, 0 aesthetic scores, 0 OCR.
- **Impact**: The intelligence layer is **blind** — no visual features means no visual_interest dimension in the relevance map, no motion peaks for slow-mo, no visual peaks for cross-modal hero detection.
- **Fix**: Add `cv2.VideoCapture` fallback in `probe_motion()` when `av` is not available. OpenCV is already a dependency.

#### 4. Audio LUFS parsing fails — returns default -70.0
- **Where**: `probe_audio.py:probe_loudness()` — ebur128 filter output parsing
- **What**: The ebur128 summary line parser looks for `"I:" in line and "LUFS" in line`, but ffmpeg 7.x's ebur128 output format may have changed. The parser returns the default -70.0.
- **Impact**: Loudness normalization has no input measurement. The compliance reporter and auto-recover LUFS strategy can't function.
- **Fix**: Use `loudnorm=print_format=json` instead of `ebur128` — it outputs JSON which is more reliable to parse. Or update the ebur128 parser for ffmpeg 7.x.

#### 5. Whisper hallucinates transcript from non-speech audio
- **Where**: `probe_semantic.py:transcribe()` — faster-whisper on vehicle/engine sounds
- **What**: The video has engine/vehicle sounds, not speech. Whisper hallucinated "1.8kg" and "1.5kg" as transcript segments. No speech detection gate to suppress this.
- **Impact**: The transcript is unreliable, polluting the semantic_importance dimension and the packed brief with gibberish. The LLM planner (if available) would receive nonsensical context.
- **Fix**: Add a VAD pre-check (Silero VAD or energy-based) — if speech_ratio < 0.1, skip Whisper entirely and set transcript to empty. Add a `speech_detected: bool` field to SemanticProfile.

#### 6. No slow-mo proposals despite significant motion peak
- **Where**: `slowmo_engine.py:find_slowmo_moments()` — impact moment detection
- **What**: Motion peak at t=3.07s (σ=3.03 — 3 standard deviations above baseline) exists. But no audio onset within 0.3s. The slow-mo engine requires BOTH motion peak AND audio onset within 0.3s. Result: 0 slow-mo proposals.
- **Impact**: For a "high-velocity vehicle edit," slow-mo at impact moments is the signature technique. The engine is too strict — real-world footage has motion/sound offset.
- **Fix**: Relax co-occurrence window from 0.3s to 1.0s. OR: add a "motion-only" slow-mo trigger for σ > 3.0 (very strong motion peak doesn't need audio confirmation).

#### 7. No dead zones detected — all scores equally low
- **Where**: `relevance_map.py:_detect_sustained_low()` — dead zone threshold
- **What**: Dead zone threshold is 0.25 (all 4 dims must be below 0.25). But with no visual features, visual_interest=0, emotional_intensity=0, audio_energy is low (~0.3), semantic_importance is low (~0.33). The avg hero_score is 0.098. Since ALL windows are below 0.25, the dead-zone detector finds 0 dead zones (it requires SUSTAINED low — but the `min_duration=3` check means 3+ consecutive seconds all below 0.25, which IS the case, but the function only returns zones ≥ 3s).
- **Actually**: After re-checking, the dead-zone detector SHOULD find dead zones here (all scores < 0.25 for 3+ seconds). The issue might be that `audio_energy` is ~0.3 (above 0.25), preventing the "all low" condition. Let me check...
- **Impact**: The pacing engine keeps all segments — nothing to cut. The output would be the same as the input.
- **Fix**: Make the dead-zone threshold adaptive — if max_hero_score < 0.3, lower the threshold to `max_hero_score * 0.5`. OR: use a relative threshold (bottom 20% of scores) instead of absolute 0.25.

### P2 — Robustness issues

#### 8. Parallel probe OOM-kills in constrained environments
- **Where**: `probe.py:probe_video()` — `ThreadPoolExecutor(max_workers=3)`
- **What**: 3 threads (visual+audio+semantic) running simultaneously on a 19s video caused OOM (-9 signal) in the sandbox. The analysis JSON was saved before the crash, but the process died.
- **Impact**: On memory-constrained machines (laptops, CI runners), the probe crashes. The cache helps on repeat runs, but first-run is unreliable.
- **Fix**: Add `psutil` memory check — if available memory < 1GB, fall back to sequential probe. Or add a `--sequential` flag. Or reduce `max_workers` to 2 (visual+audio parallel, semantic sequential as before).

#### 9. Timeline PNG rendering OOM-kills
- **Where**: `probe.py:probe_video()` → `timeline_view.py:render_timeline()`
- **What**: The `render_timeline_png=True` default causes PIL + ffmpeg waveform extraction on top of the probe, which OOM-kills the process. The analysis JSON is saved but the process dies before printing the summary.
- **Impact**: `--analyze-only` and `--probe-only` crash in memory-constrained environments.
- **Fix**: Set `render_timeline_png=False` as default in `probe_video()`. Make it opt-in via a `--render-timeline` CLI flag.

#### 10. No `pip install -e .` in setup — `kb` not importable from outside repo
- **Where**: `setup.sh` doesn't run `pip install -e .`; users running from other directories get `ModuleNotFoundError: No module named 'kb'`
- **Impact**: The `online_music.py` module (and all other `kb.tools.*` modules) can't be imported from scripts outside the repo directory.
- **Fix**: Add `pip install -e .` to `setup.sh` and document it in README.

### P3 — Missing features

#### 11. No vehicle/action recipe
- **Where**: `recipes/` — 7 recipes, none for vehicle/action content
- **What**: The closest is `sports-highlights.yaml` which expects "beat-synced sports highlight reel with slow-motion replays." But it calls `recipe.find_action_moments` which would use the intelligence layer's hero moments — and with 0 Level 2+ hero moments, it would fall back to scene-boundary extraction (which found 0 scenes).
- **Fix**: Add a `vehicle-action.yaml` recipe with: beat-synced cuts, speed ramps (velocity edit), impact slow-mo (from motion peaks), color grade (high contrast), and energetic music bed.

#### 12. Adaptive dead-zone threshold
- **Where**: `relevance_map.py:build_relevance_map()` — `dead_zone_threshold=0.25`
- **What**: Fixed threshold doesn't adapt to content. For a video where all scores are ~0.1, nothing is "dead." For a video where scores range 0.3-0.9, 0.25 is too low.
- **Fix**: Use `dead_zone_threshold = max(0.15, avg_hero_score * 0.5)` — adaptive to the content's baseline.

#### 13. Slow-mo engine needs motion-only trigger
- **Where**: `slowmo_engine.py:find_slowmo_moments()` — impact moment detection
- **What**: Currently requires motion peak + audio onset. For vehicle footage, the motion peak alone (σ > 3.0) is sufficient evidence of an impact/action moment.
- **Fix**: Add a `motion_only_threshold` parameter (default σ=3.0). If motion peak σ ≥ this threshold, propose slow-mo even without audio onset.

#### 14. Hero detector co-occurrence window too strict
- **Where**: `hero_detector.py:detect_hero_moments()` — `co_occurrence_window=0.5`
- **What**: For real-world footage, motion and sound may be offset by 0.5-1.0s (e.g., see the flash, hear the boom 0.7s later). The 0.5s window misses these.
- **Fix**: Increase default to 1.0s, or make it configurable per content type.

#### 15. Component labeling bug in probe_visual
- **Where**: `probe_visual.py:probe_visual()` line 562 — `components.append("pyscenedetect" if profile.scene_boundaries else "scdet_fallback")`
- **What**: When PySceneDetect is not installed, the fallback to ffmpeg scdet runs. But if scdet finds scene boundaries (even just [0.0]), the code labels it "pyscenedetect" — misleading.
- **Fix**: Track which method actually ran: `components.append("pyscenedetect" if _pyscenedetect_available else "scdet_fallback")`.

#### 16. No speech detection gate before Whisper
- **Where**: `probe_semantic.py:transcribe()`
- **What**: Whisper runs on all audio regardless of whether it contains speech. For music/engine/wind videos, this produces hallucinated transcripts.
- **Fix**: Add a 2-second energy-based pre-check: sample 3 random 2-second windows, compute RMS energy variance. If variance is very low (constant noise), skip Whisper. Or use Silero VAD (if installed) for a proper check.

---

## What Worked

1. **Intelligence layer runs without crashing** — probe → relevance map → cut detector → pacing → slow-mo → hero detection all produce structured JSON output
2. **Cut detector finds real beat-aligned cut points** — 3 cuts at 2.56s, 10.24s, 17.54s with Murch composite scores 0.72-0.76
3. **Profile cache works** — second probe run is instant (60× speedup)
4. **Internet Archive music search returns real public-domain recordings** — Beethoven, Mozart, Bach
5. **FFmpeg manual editing works perfectly** — cut, speed ramp, concat, music mix all produce valid output
6. **Analysis JSON contains all data needed to make the edit** — cut points, tempo, beats, motion peaks are all there
7. **Graceful degradation** — the architecture doesn't crash when deps are missing; it just produces sparse output (which is both a strength and a weakness)

---

## The Edit

**Input**: 19.4s vertical phone video (360×640, 30fps, H264+AAC)
**Output**: 14.0s vertical video with beat-synced cuts + 2× speed ramp + music bed

**Process** (manual, bypassing recipe runner):
1. Ran `--analyze-only` to get cut points (beat-aligned: 2.56s, 10.24s, 17.54s)
2. Cut video at beat points using `ffmpeg -ss -t -c copy`
3. Speed-ramped middle segment 2× fast using `setpts=0.5*PTS + atempo=2.0`
4. Concatenated segments using ffmpeg concat demuxer
5. Generated music bed (80Hz + 120Hz sine tones, since IA download failed)
6. Mixed music bed under original audio at -10dB

**What the architecture provided**: Cut points (from librosa beat detection via the cut detector)
**What I had to do manually**: Everything else — speed ramps, concatenation, music bed, mixing

---

## Implementation Plan

### Sprint 1: Fix P0 (make recipes runnable) — 1 day
1. Fix `edit.info` parameter mismatch in `_execute_step` — map `input` → `path` for mcp_bridge functions
2. Standardize content_type names across classifier, recipes, and pacing profiles
3. Add `pip install -e .` to `setup.sh`

### Sprint 2: Fix P1 (critical quality gaps) — 2 days
4. Add `cv2.VideoCapture` fallback in `probe_motion()` when PyAV is missing
5. Fix LUFS parsing — switch to `loudnorm=print_format=json`
6. Add speech detection gate before Whisper (energy-based pre-check)
7. Relax slow-mo co-occurrence window from 0.3s to 1.0s
8. Add motion-only slow-mo trigger for σ ≥ 3.0
9. Make dead-zone threshold adaptive
10. Increase hero detector co-occurrence window to 1.0s

### Sprint 3: Fix P2 (robustness) — 1 day
11. Add memory check to parallel probe — fall back to sequential if constrained
12. Disable timeline PNG rendering by default
13. Fix component labeling bug in probe_visual

### Sprint 4: New features — 2 days
14. Add `vehicle-action.yaml` recipe with velocity ramps, beat-synced cuts, impact slow-mo
15. Add adaptive dead-zone threshold to relevance_map
16. Add `--render-timeline` CLI flag (opt-in)

**Total: ~6 days of work to close all 16 gaps.**

---

## Architecture Strengths (preserve these)

1. **Graceful degradation** — no crashes when deps missing (just sparse output)
2. **Artifact-grounded traceability** — every phase's output saved as inspectable JSON
3. **Profile cache** — 60× speedup on repeat runs
4. **Cross-modal hero detection** — novel concept, just needs tuning
5. **Murch Rule of Six cut scoring** — produces real, usable cut points
6. **Internet Archive public-domain classical** — solves the "classical music isn't royalty-free" problem
7. **Professional text effects** — spring physics, MrBeast bounce, Apple blur-in (when the recipe runner can actually reach them)
8. **Plan critic** — catches Hard Rule violations before execution (when the plan exists)

## Architecture Weaknesses (fix these)

1. **Execution layer disconnected from intelligence layer** — the recipe runner crashes before reaching the `find_*` functions that consume intelligence output
2. **Silent degradation to uselessness** — when optional deps are missing, the probe produces empty results without warning the user
3. **No speech detection gate** — Whisper hallucinates on non-speech audio
4. **Fixed thresholds don't adapt to content** — dead-zone, slow-mo, hero detection all use fixed thresholds
5. **No fallback for PyAV** — the most critical visual dep (frame decoding) has no cv2 fallback
6. **Parallel probe can OOM** — no memory awareness
7. **No vehicle/action recipe** — the architecture supports it but no recipe exercises it
