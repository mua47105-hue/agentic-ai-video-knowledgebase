# Agent Skill: AI Video Editing

Teach any LLM agent to edit videos using a free, open-source stack: MCP servers + FFmpeg + Whisper + local/cloud LLMs. Clone this repo, any agent auto-discovers this file and understands its role.

## Identity

You are an AI video editing agent. You edit **existing** footage — you never generate video from text. You take raw clips and produce professionally edited output: cuts, transitions, color grading, subtitles, audio design, pacing, and assembly.

## Core Stack (in order of preference)

1. **Unified Adapter** (`from kb.tools.unified_adapter import edit`) — single import surface combining mcp_video.Client (60+ safe functions) with audited ffmpeg_adapter functions (J/L-cuts, scopes, project files, quality metrics, true-peak loudnorm). Routes around 4 known-buggy mcp_video functions automatically.
2. **MCP Server** (`mcp-video`, ~140 tools, Apache 2.0) — typed, callable tools. `pip install mcp-video`
3. **Raw FFmpeg** — when MCP lacks a specific capability or you need a complex filter chain
4. **Whisper** (faster-whisper / whisper.cpp) — transcription for subtitles, silence detection, content-based editing
5. **Kdenlive/Shotcut MLT** — professional multi-track timeline, generate MLT XML, render with `melt`

## Extended Tools

- **Recipe Packs** (`kb/tools/recipe_runner.py`) — YAML-defined workflow templates that convert "ask FFmpeg questions" into "give me a podcast, get shorts." Zero new deps. Run: `python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4`
- **MLT XML Export** (`kb/tools/mlt_export.py`) — converts .aevp project files to MLT XML for Kdenlive/Shotcut handoff. Opens in free NLEs, renders headlessly via `melt`.
- **Compliance Reporter** (`kb/tools/compliance.py`) — check videos against named delivery specs (EBU R128, ATSC A/85, Netflix Sound Mix, BBC, YouTube, TikTok).
- **Content Adapter** (`kb/tools/content_adapter.py`) — search and download stock footage (Pexels) and SFX (Freesound) with license sidecars. Mirrors music_adapter pattern.
- **VLM Adapter** (`kb/tools/vlm_adapter.py`) — visual perception via Qwen2.5-VL (gated, opt-in). Frame description, moment finding, claim verification.

## Hard Rules (production correctness, non-negotiable)

These govern every edit. Violating any produces detectable quality loss.

### Audio
1. **Loudness normalize two-pass, never single-pass.** Single-pass `loudnorm` causes audible pumping. Always measure first, then apply with `linear=true` and explicit `-ar 48000`.
2. **`atempo` and `setpts` must change together.** Speed changes touch both. `atempo` maxes at 2.0 — chain multiples for faster speeds.
3. **SFX for hard impacts lead the visual by 1–2 frames.** Simultaneous placement reads as *late* because auditory processing is slower than visual.
4. **Ducking depth by dialogue type:** normal -6 to -10dB, quiet/intimate -12 to -15dB, VO narration only -3 to -5dB.
5. **48kHz sample rate minimum, 24-bit preferred for delivery.** `-ac 2 -ab 192k` for stereo.

### Video & Transitions
6. **Xfade offset must satisfy `offset ≤ duration(clip1) − transition_duration` and `duration(clip2) ≥ transition_duration`.** Violation silently breaks the transition or throws a filtergraph error.
7. **Stream-copied segment extraction can blip audio at non-keyframe boundaries.** For anything beyond a quick preview, extract → re-encode → concat; don't rely on copy-mode stitching.
8. **Seed all randomness in programmatic animation (Remotion, Hyperframes).** `Math.random()` across parallel render threads causes visible flicker.

### Subtitles
9. **Max 2 lines, 37–42 chars per line, 12–20 chars/sec reading speed.**
10. **Line breaks respect syntax, not character counts.** Never split article/noun, adjective/noun, pronoun/verb, or preposition/noun-phrase pairs.
11. **Minimum display 1s, maximum 6s. 2-frame gap between consecutive captions.**
12. **Subtitles apply LAST in any filter chain** — after every overlay, color grade, and effect.

### Production-Grade Extensions
13. **All color operations happen in a known working space.** Never apply `eq`, `colorbalance`, or `curves` to footage without first converting to ACEScg or Rec.709. Slapping contrast on log footage without an IDT is forbidden.
14. **Every color operation must produce a scope image for verification.** The agent inspects the waveform/vectorscope before signing off on a grade. "Looks right on my monitor" is forbidden — monitors lie.
15. **J-cut lead time and L-cut trail time are content-type dependent.** Documentary/interview: 0.5-1.5s. Vlog/conversational: 0.2-0.5s. Narrative scene: 1-3s. Hard cut on dialogue boundary = forbidden unless intentional (impact cut).
16. **Every stem has its own processing chain.** Dialogue needs high-pass + presence EQ + de-essing + compression. Music needs none of those. Treating them identically is forbidden.
17. **Streaming delivery requires true-peak limiting at -1 dBTP.** Loudness compliance is integrated LUFS *and* true peak *and* LRA. Loudnorm alone is insufficient — it doesn't limit. Add `alimiter=limit=0.99` after loudnorm.
18. **Loudness range (LRA) for streaming must be ≤ 7.** Broadcast allows 9-11. Streaming (mobile, headphones) needs tighter range — apply `acompressor` with low ratio (2:1) before loudnorm if LRA > 7.
19. **Never ship without a delivery profile.** Ad-hoc `libx264 -crf 20` is forbidden. Every render must declare its target platform so codec, bitrate, loudness, and resolution are correct by construction.
20. **VMAF ≥ 80 for any re-encode.** If a transcode drops VMAF below 80 vs the source, increase bitrate or use a slower preset. Never ship a re-encode without scoring it.
21. **Audio delivery requires phase coherence.** Stereo phase correlation must be ≥ 0. Mono compatibility check: `ffmpeg -i input -af pan=mono -c:a pcm_s16le -f null -` must not show "clipping" warnings.
22. **Every project has a `.aevp` file.** No edits without a project file. The file is the source of truth for resume, audit, and delivery compliance.
23. **Destructive operations require a prior snapshot.** `silence_remove`, `color_grade`, `loudnorm` — anything that re-encodes — must be preceded by `project_snapshot()`. The agent can always undo by reverting to the snapshot.
24. **Audit trail is non-optional for broadcast delivery.** Every step logged with input hash, output hash, parameters, timestamp. BBC/Netflix compliance requires this.
25. **Use unified_adapter, never direct mcp_video or raw ffmpeg_adapter.** `from kb.tools.unified_adapter import edit` combines mcp_video.Client (60+ capabilities) with audited ffmpeg_adapter functions. Direct `mcp_video.Client` usage bypasses the 4 known-buggy wrappers (merge, ai_remove_silence, pipeline, ai_transcribe). Direct `ffmpeg_adapter` usage is deprecated and will emit a warning.
26. **Filter order matters: scale → color → overlay → subtitle.** FFmpeg filter chains are order-sensitive. Applying `scale` after `eq` gives wrong pixel values. Applying `subtitles` before `overlay` covers the overlay. The correct order is always: (1) resize/scale/crop, (2) color grade/curves/eq, (3) effects/blur/glitch, (4) overlays/PiP/grid, (5) subtitles LAST. Violating this order silently corrupts the visual output.
27. **Captions use ASS with professional fonts + animation, never static SRT.** Default font is Montserrat Bold (titles) or Inter Bold (body), both bundled in `kb/assets/fonts/`. Arial is forbidden. Use the `caption_presets` module's ASS generation (`mrbeast_bounce`, `apple_premium`, `karaoke_highlight`) — never raw `force_style` SRT burn-in. Per-word spring-bounce animation is the default for short-form; blur-in for title cards.
28. **Cache the SourceProfile.** `kb/tools/profile_cache.py` caches probe output by content-hash + mtime. Second run on the same video is 60× faster (cache hit). Never re-probe a video that hasn't changed. Skip the probe entirely (`_recipe_needs_intelligence()`) for recipes that only call edit.trim/resize/render.
29. **Music sources: royalty-free by default, online opt-in.** Default sources are Pixabay/Incompetech/MusOpen (royalty-free, commercial-safe). For trending/popular music, use `sources=["youtube"]` or `sources=["youtube_trending"]` (personal use — obtain sync license for commercial). For public-domain classical, use `sources=["internet_archive"]` or `sources=["classical"]` (commercial-safe — no sync license needed). Every online-source track gets a `.license.json` sidecar marking `commercial_use` true/false. Use `sources=["online"]` to search YouTube + Internet Archive combined.
30. **Restraint over decoration (HR#29).** Every non-cut embellishment step (color grade, transition, text overlay, slow-mo, SFX, watermark) must cite a justifying signal from the relevance map or hero detector in its `reasoning` field. The plan critic flags embellishments without signal references. The reviewer penalizes effect density above `max_effects_per_minute` (default 3). Default is no-op: an EditPlan with fewer effects wins ties over one with more, unless a hero moment or content-type convention specifically calls for it. Composite patterns (reverse_into_drop, whip_pan_cut, zoom_punch) are exception — they're multi-step signature moves with their own trigger constraints.

## The Decision Engine: INIT → PROBE → CLASSIFY → PLAN → BUILD → VERIFY

This six-phase loop runs for every editing task. It replaces ad-hoc "do what I say" with structured reasoning.

### Phase 0: INIT — Parse the Request

Before touching any file, classify:

```
CONTENT_TYPE: talking-head | podcast | vlog | tutorial | cinematic | social-short | music-video | documentary | interview | event
COMPLEXITY: simple (1 op) | moderate (2-5 ops) | complex (6+ ops)
TOOLS_NEEDED: mcp-only | ffmpeg+filters | whisper+transcript | nle-timeline
TARGET_PLATFORM: youtube | tiktok/reels | instagram | linkedin | broadcast | custom
OUTPUT_LUFS: -16 (talking-head) | -14 (streaming) | -23 (broadcast)
```

> **As of Phase 3**: You can auto-detect `CONTENT_TYPE` via `kb/tools/classifier.py` — a pure-rule, zero-cloud classifier that reads ffprobe + Whisper signals. Use `python3 -m kb.tools.recipe_runner --recommend input.mp4` for a recommendation, or the `--force-content-type` flag to override when running a recipe pack directly.

### Phase 1: PROBE — Understand the Source

> **As of Phase 6, the multimodal probe is executable.** `from kb.tools.probe import probe_video` runs all probes in parallel: ffprobe metadata, CrisperWhisper transcript, PySceneDetect, MediaPipe face/pose, HSEmotion, OpenCV motion energy, LAION aesthetic, Silero VAD, pyannote diarization, Demucs stem separation, SpeechBrain prosody emotion. Output: `SourceProfile` (JSON) + `packed_transcript.md` (~12KB) + `timeline.png`. The recipe runner calls this automatically (`--probe-only` to run standalone). Every heavy-model dep is optional — the probe degrades gracefully to ffprobe + PySceneDetect + librosa when mediapipe/demucs/etc. are absent.

```bash
# Complete media probe (one command)
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4

# Extract for agent use:
# - Duration, codec, resolution, bitrate, framerate
# - Audio: codec, channels, sample rate, language
# - Video: has audio track? has subtitle track?

# Scene detect (for structure)
ffmpeg -i input.mp4 -filter:v "select='gt(scene,0.4)',showinfo" -f null - 2>&1 | grep pts_time

# Transcribe (for content understanding)
# Use large model for accuracy if time allows, base for speed
whisper input.mp4 --output-srt --model base
```

Probe yields a **Source Profile**: `{duration, resolution, codecs, fps, scene_count, transcript_available, has_audio, estimated_quality}`. Store this — it drives all planning.

### Phase 1.5: RELEVANCE MAP + CUT DETECTION (Phase 7)

> **As of Phase 7, the framework knows where the good parts are.** `kb/tools/relevance_map.py` scores every 1-second window on 6 dimensions (semantic, emotional, visual, audio, pacing, hero_score via geometric-mean fusion). `kb/tools/cut_detector.py` finds optimal cut points via Walter Murch's Rule of Six (emotion 0.51, story 0.23, rhythm 0.10, eye_trace 0.07, plane_2d 0.05, space_3d 0.04). Cuts respect 4 boundary types: shot (PySceneDetect), silence (Silero VAD), sentence-end (transcript), beat (librosa downbeats). Run `--analyze-only` to see the full analysis without executing a recipe.

### Phase 2: CLASSIFY — Route by Content Type

Based on CONTENT_TYPE from Phase 0 + probe results, select workflow:

| Content Type | Primary Approach | Key Techniques | Audio Focus |
|---|---|---|---|
| talking-head | transcript-first, J/L-cuts | silence removal, color grade, dynamic zoom | -16 LUFS, compression |
| podcast | multi-cam concat, chapters | silence removal, intro/outro, stem separation | -16 LUFS, ducking |
| vlog | montage assembly | speed ramping, transitions, music sync | -14 LUFS, ducking |
| tutorial | screen + face PiP | text overlays, callouts, chapters | -16 LUFS, clear VO |
| cinematic | color grading first | LUTs, curves, vignette, optical flow | -23 LUFS, wide dynamic |
| social-short | vertical crop, fast pace | pattern interrupt/2s, kinetic text, captions | -14 LUFS, aggressive |
| interview | multi-cam concat | J/L-cuts, color match, speaker labels | -16 LUFS, leveling |

### Phase 3: PLAN — Build the Edit Plan

Output: a list of atomic operations with exact parameters.

```json
{
  "plan": [
    {
      "step": 1,
      "operation": "transcribe",
      "tool": "video_ai_transcribe",
      "params": {"input": "input.mp4", "model": "base"}
    },
    {
      "step": 2,
      "operation": "remove_silence",
      "tool": "video_ai_remove_silence",
      "params": {"input": "output_step1.mp4", "threshold": -50, "min_silence": 0.5, "padding": 0.3}
    },
    {
      "step": 3,
      "operation": "color_grade",
      "tool": "video_ai_color_grade",
      "params": {"input": "output_step2.mp4", "style": "warm_cinematic"}
    },
    {
      "step": 4,
      "operation": "loudness_normalize",
      "tool": "ffmpeg_raw",
      "params": {"cmd": "two-pass loudnorm to -16 LUFS, linear=true, -ar 48000"}
    },
    {
      "step": 5,
      "operation": "render",
      "tool": "export",
      "params": {"format": "mp4", "crf": 22, "resolution": "1920x1080"}
    }
  ],
  "expected_duration": "approx 60-90s after silence removal",
  "quality_gates": ["audio_sync", "duration_check", "lufs_check", "visual_inspection"]
}
```

Every plan includes **quality gates** — specific checks to run after each step.

### Phase 4: BUILD — Execute with Production Techniques

For each step, use MCP tools first. Fall back to FFmpeg when needed.

#### Cutting & Pacing

```python
# MCP: silence removal (smart)
# The -50dB threshold catches near-silence, 0.3s padding preserves natural pacing
video_ai_remove_silence("input.mp4", threshold=-50, min_silence=0.5, padding=0.3)

# MCP: trim segment
video_trim("input.mp4", start="00:01:30", end="00:02:45")

# FFmpeg: J-cut (audio leads video by 5-15 frames)
# Extract audio segment shifted earlier, video at original time
ffmpeg -i input.mp4 -itsoffset -0.3 -i input.mp4 -map 0:v -map 1:a -c copy jcut.mp4

# FFmpeg: multi-segment extraction with re-encode (production-safe)
ffmpeg -i input.mp4 -ss 00:01:00 -t 30 -c:v libx264 -c:a aac seg1.mp4
ffmpeg -i input.mp4 -ss 00:02:00 -t 45 -c:v libx264 -c:a aac seg2.mp4
# Then concat with transition (see Transitions section)
```

#### Audio & Sound Design

```python
# MCP: transcribe audio
transcript = video_ai_transcribe("input.mp4", model="base-or-large")

# MCP: audio effects
video_audio_effects("input.mp4", effect="noise_reduction", strength=0.3)

# FFmpeg: Two-pass loudnorm (REQUIRED for production)
# Pass 1 — measure
ffmpeg -i input.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1
# Parse output for measured_I, measured_TP, measured_LRA, measured_thresh
# Pass 2 — apply with measured values, linear=true, -ar 48000
ffmpeg -i input.mp4 -af "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=-22.3:measured_TP=-1.8:measured_LRA=8.5:measured_thresh=-34:linear=true" -ar 48000 output.mp4

# FFmpeg: Audio ducking (music lowers when voice speaks)
ffmpeg -i voice.mp4 -i music.mp3 -filter_complex \
  "[1:a]volume=1.0[music];[0:a]asplit=2[voice][side]; \
   [side]asendcmd='0.0 sidechaincompress threshold=-30dB ratio=4,adelay=1|1[sc]; \
   [music][sc]amix=inputs=2:duration=first[aout]" \
  -map 0:v -map "[aout]" -c:v copy output.mp4

# FFmpeg: Compression for take-matching (threshold -18 to -12dB, ratio 3:1-4:1)
ffmpeg -i input.mp4 -af "acompressor=threshold=-18dB:ratio=4:attack=5:release=100" output.mp4
```

#### Music Discovery & Analysis

```python
# Analyze any audio for BPM, key, mood, structure, genre
# Full local analysis via librosa — no API calls
from kb.tools.unified_adapter import music

profile = music.describe("track.mp3")
# Returns: {bpm, key, duration, sections, genre, mood, arousal, valence, suitability}
check("BPM matches expectation", 80 < profile.get("bpm", 0) < 160)

# Search royalty-free libraries (Pixabay, Incompetech, MusOpen)
# Natural language query — "sad piano", "90s funk", "uplifting corporate"
results = music.search(
    "uplifting corporate",
    bpm_range=(100, 130),
    duration_min=60.0,
    instrumental_only=True,
)
check("found candidates", len(results) > 0)

# Download with automatic .license.json sidecar
track = music.download(results[0], output_dir="./assets/music")
print(f"Downloaded: {track['path']}")
print(f"License: {track['license_path']}")

# Describe before and after download — compare analysis with metadata
# Ducking: music.lower_volume() when dialogue present (see Audio ducking above)
```

#### Color Grading

```python
# MCP: auto color grade
video_ai_color_grade("input.mp4", style="warm_cinematic")

# FFmpeg: S-curve contrast (professional)
ffmpeg -i input.mp4 -vf "curves=r='0/0 0.25/0.2 0.5/0.5 0.75/0.8 1/1':g='0/0 0.25/0.2 0.5/0.5 0.75/0.8 1/1':b='0/0 0.25/0.2 0.5/0.5 0.75/0.8 1/1'" output.mp4

# FFmpeg: Warm cinematic (talking-head default)
ffmpeg -i input.mp4 -vf "eq=contrast=1.1:brightness=0.02:saturation=1.2,colorbalance=rs=0.1:gs=-0.05:bs=-0.05" output.mp4

# FFmpeg: Teal-and-orange (cinematic)
ffmpeg -i input.mp4 -vf "eq=contrast=1.15:saturation=0.9,colorbalance=rs=0.05:gs=-0.05:bs=0.15,curves=r='0/0 1/0.95':b='0/0 1/0.9'" output.mp4

# MCP: apply 3D LUT
video_lut("input.mp4", "lut/cinematic.cube")
```

#### Subtitles & Text

```python
# MCP: transcribe
transcript = video_ai_transcribe("input.mp4", model="base")

# MCP: burn subtitles with proper styling
# Style: Max 2 lines, 37-42 chars/line, 2-word uppercase chunks
# Pyramid shape: shorter line on top if unequal
# 2-frame gap between consecutive captions
video_text_subtitles("input.mp4", "subtitles.srt",
  style="FontName=Arial,FontSize=20,PrimaryColour=&HCCFF0000,BackColour=&H80000000,Outline=1,Shadow=1,MarginV=40",
  max_lines=2, chars_per_line=42)

# FFmpeg: hardcode subtitles with production styling
ffmpeg -i input.mp4 -vf "subtitles=sub.srt:force_style='Fontname=DejaVu Serif,FontSize=22,PrimaryColour=&HCCFF0000,BackColour=&H80000000,Outline=1,Shadow=2,MarginV=50,BorderStyle=3'" output.mp4

# Aspect-ratio-specific:
# 16:9 → 6-word ALL CAPS chunks at ~80% frame height
# 9:16 (vertical) → 3-word chunks, larger relative font, ~75% height, centered safe box
```

#### Transitions

```python
# MCP: merge with crossfade
video_merge(["clip1.mp4", "clip2.mp4"], transition="fade", duration=0.5)

# FFmpeg: xfade with cubic-ease easing (professional, not linear default)
# Map progress P (0→1) through cubic ease: if(lt(P,0.5), 4*P*P*P, 1-pow(-2*P+2,3)/2)
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v]trim=0:5[v0];[1:v]trim=0:5[v1]; \
   [v0][v1]xfade=offset=3:duration=2:transition=fade[vout]; \
   [0:a]atrim=0:5[a0];[1:a]atrim=0:5[a1]; \
   [a0][a1]acrossfade=d=2[aout]" \
  -map "[vout]" -map "[aout]" output.mp4

# VALIDATION: Check xfade offset < clip1_duration - transition_duration
# AND clip2_duration >= transition_duration before rendering
```

#### Motion Graphics & Effects

```python
# MCP: animated text
video_text_animated("input.mp4", text="Hello World", preset="fade_in", duration=3)

# MCP: picture-in-picture
video_layout_pip("main.mp4", "overlay.mp4", position="bottom-right", scale=0.3)

# MCP: grid layout
video_layout_grid(["cam1.mp4", "cam2.mp4"], layout="2x1")

# FFmpeg: Ken Burns dynamic zoom (slow zoom with ease-out deceleration)
ffmpeg -i input.mp4 -vf "zoompan=z='min(zoom+0.002,1.2)':d=150:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" output.mp4

# FFmpeg: face-tracked dynamic zoom (talking-head)
# Scale crop by rhetorical emphasis: full frame → head-to-chest → head-and-shoulders
# Implemented via zoompan with multiple keyframes
```

### Phase 4.5: PLAN CRITIQUE (Phase 9) — ★ NOVEL ★

> **As of Phase 9, the plan is red-teamed BEFORE execution.** `kb/tools/plan_critic.py` checks the EditPlan against 11 Hard Rules statically (HR#1, #2, #6, #9, #12, #15, #19, #22, #25, #27, #28), verifies SourceProfile assumptions match the source, confirms hero moments are preserved and dead zones eliminated, and validates plan-graph quality (acyclicity, connectivity, intent coverage). Optional LLM critique (Round 2, different model than planner) catches runtime failure risks. Catches 80% of failures before any FFmpeg call — no other agentic video editor in the wiki does this.

### Phase 4.6: INTELLIGENCE ARCHITECTURE (Phase 5) — synthesized from 11 frameworks

> **Phase 5 integrates 9 patterns borrowed from the 11 frameworks documented in this wiki**, completing the architecture vision. These are additive to Phases 6-9 and run automatically inside `recipe_runner.run_recipe()`.

| Pattern | Source framework | Module | What it does |
|---|---|---|---|
| Intent decomposition (explicit + implicit) | VideoAgent | `kb/tools/intent_parser.py` | Decomposes user request into explicit intents (keyword-extracted) + implicit intents (inferred from content_type + source signals). Planner consumes both. |
| Editing Research pure-reasoning sub-phase | Crayotter | `kb/tools/editing_research.py` | A no-tool LLM reasoning phase that produces a structured editing blueprint (narrative/visual/pacing/narration strategy) BEFORE planning. Falls back to rule-based if LLM unavailable. |
| LLM model routing per task type | CutClaw | `kb/tools/llm_router.py` | Routes Plan/Critic/Reviewer/Research tasks to different LLM models (ensemble diversity). Cloud-first (Claude/GPT-4o if API keys set), local fallback (Ollama Qwen2.5-Coder). |
| Storyboard as explicit plan artifact | Project Montage | `intelligent_planner.py` + `artifact_store.py` | The planner produces a `storyboard.md` (scene-by-scene visual description) saved as a separate artifact alongside the EditPlan JSON. |
| Per-modality BUILD sub-agents | Project Montage | `kb/tools/build_orchestrator.py` | Groups EditPlan steps into 7 modality sub-agents (probe/cut/color/audio/music/mogfx/subtitle/render) with dependency tracking + parallel group detection. |
| Artifact-grounded traceability | Crayotter | `kb/tools/artifact_store.py` | Saves every phase's output as inspectable artifacts: `source_profile.json`, `relevance_map.json`, `cut_points.json`, `paced_plan.json`, `slowmo_proposals.json`, `music_sync_plan.json`, `hero_moments.json`, `editing_blueprint.json` + `.md`, `edit_plan.json`, `storyboard.md`, `review.json`. Every run is replayable + auditable. |
| AVE YAML retry_if gates | AVE | `kb/tools/auto_recover.py` (`parse_retry_if_from_yaml` + `evaluate_retry_gates`) | Recipes can declare `retry_if:` blocks: `{metric, threshold, max_retries, feedback_target}`. Gates are evaluated against the 7-dimension review; triggered gates feed back to the planner or editor. |
| Selective revision (redo downstream) | Crayotter | `kb/tools/auto_recover.py` (`get_downstream_steps` + `selective_revision_plan`) | When a step fails, redo the failed step + all downstream steps (not the whole pipeline). Returns the list of step indices to re-execute. |
| Per-cut-boundary micro-eval | video-use | (integrated into Reviewer) | Lightweight per-cut evaluation hook in the 7-dimension Reviewer; separate from the macro-loop. |

### Phase 5: VERIFY — Quality Gates

> **As of Phase 9, the Reviewer scores 7 dimensions.** `kb/tools/reviewer.py` scores the final output on Adherence, Pacing, Visual Quality, Watchability, Audio, Narrative Coherence, and Overall (weighted composite). VMAF auto-correction: if VMAF < 80, re-encode with lower CRF + slower preset (max 2 retries). Outcome is recorded in the edit-pattern memory DB (`kb/tools/edit_memory.py`) so future runs learn which (content_type, technique, params) tuples succeed.

After every step, verify. Never assume success.

```bash
# Gate 1: Output exists and is non-empty
test -f output.mp4 && stat -c%s output.mp4

# Gate 2: Duration matches expectations
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output.mp4

# Gate 3: Both audio and video streams present
ffprobe -v error -show_entries stream=codec_type -of csv=p=0 output.mp4 | sort -u

# Gate 4: Audio sync check (compare duration of audio vs video streams)
ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 output.mp4
ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 output.mp4
# Durations should be within 0.5s of each other

# Gate 5: LUFS check (if loudness was normalized)
ffmpeg -i output.mp4 -af loudnorm=print_format=json -f null - 2>&1 | grep -E "input_i|input_lra"

# Gate 6: Visual inspection (thumbnail at 3 points)
ffmpeg -i output.mp4 -ss 00:00:10 -vframes 1 check_10s.jpg
ffmpeg -i output.mp4 -ss 00:01:00 -vframes 1 check_60s.jpg
ffmpeg -i output.mp4 -ss 00:02:00 -vframes 1 check_120s.jpg
```

> **As of Phase 3**: The `kb/tools/auto_recover.py` engine can retry failed gates automatically — bounded to 2 retries per step, 3 rounds per recipe. Wired into `recipe_runner.py` — if quality gates fail, the engine selects a strategy (e.g. `loudnorm_remeasure`, `render_force_sync`, `add_silent_audio`) and re-executes the problematic step with adjusted parameters. All attempts are recorded in the manifest under `recovery_attempts`.

If any gate fails, diagnose via the Error Recovery table below.

## Error Recovery

| Symptom | Cause | Fix |
|---------|-------|-----|
| Audio out of sync after trim | Stream copy at non-keyframe | Use `-ss` before `-i` with re-encode |
| Loudnorm pumping | Single-pass instead of two-pass | Always do two-pass with `linear=true` |
| Xfade "failed to configure" | Offset exceeds clip duration | Verify offset <= clip1_dur - transition_dur, clip2_dur >= transition_dur |
| Blip at concat boundary | Non-keyframe concat with -c copy | Re-encode segments or use concat filter |
| Subtitles not visible | Wrong font filter or missing library | Use `subtitles=file.srt:force_style=...` with `--enable-libfreetype` |
| Black frames at start | -ss after -i seeks to non-keyframe | Place -ss before -i or re-encode |
| Whisper no segments | Wrong language or silent track | Check `ffprobe` audio stream, specify `--language` |
| Cropped video looks wrong | Aspect ratio mismatch | Use `force_original_aspect_ratio=decrease,pad` |
| Output too large | No compression flags | Add `-crf 22 -c:a aac -b:a 128k` |
| Speed change has no audio | atempo not applied | Always pair `setpts` with `atempo` |
| Remotion/Hyperframes flicker | Unseeded random | Use platform's seeded random API |
| Silence removal causes A/V desync | `ai_remove_silence` from mcp_video (11.62s drift) | Always use `edit.silence_remove()` from unified_adapter — uses silencedetect+trim+concat, not mcp_video |
| Merge duration wrong for 3+ clips | mcp_video `merge` has incorrect offset math for n>2 | Always use `edit.merge()` from unified_adapter — our xfade chain has correct cum_dur offset |
| Music analysis returns no BPM | Librosa or ffmpeg not installed, or file corrupted | Verify `pip install librosa` and `ffprobe` works on the file |
| VMAF score < 80 after re-encode | Bitrate too low or preset too fast | Increase `-crf` (lower = better) or use `-preset slower`; re-run with `edit.quality_vmaf(ref, dist)` |
| Velocity edit audio stutter | atempo not paired with setpts, or source fps too low | Always pair `edit.speed()` with both audio+video (HR #2); use 60fps source for 30-40% slow-mo |

> **As of Phase 3**: The `kb/tools/auto_recover.py` `RecoveryEngine` handles `loudnorm_remeasure`, `render_force_sync`, `add_silent_audio`, and `rerun_subtitles` automatically. Run a recipe via `recipe_runner.py` and recovery is built in — no manual triage required.

## Workflow Templates

### Podcast-to-Shorts (Production)

```
1. PROBE: Transcribe full podcast → word-level timestamps + speaker diarization
2. CLASSIFY: content_type=podcast, target=tiktok/reels
3. PLAN: Find 30-60s engaging segments (high energy, quotable, clear audio)
4. For EACH segment:
   a. Extract with re-encode: ffmpeg -i full.mp4 -ss X -t 45 -c:v libx264 -c:a aac seg.mp4
   b. Resize to 1080×1920 vertical: video_resize(seg.mp4, 1080, 1920)
   c. Add animated captions: 3-word chunks, 75% height, centered safe box
   d. Dynamic zoom: face-tracked, zoom by rhetorical emphasis
   e. Two-pass loudnorm to -14 LUFS (social platform target)
   f. Two-frame gap between subtitle chunks
5. VERIFY: Check sync at 3 random timestamps per segment
6. OUTPUT: Batch directory of short clips, named by timestamp
```

### Silence Removal + Pacing (Talking Head)

```
1. PROBE: silencedetect at -50dB threshold
2. CLASSIFY: content_type=talking-head
3. PLAN:
   - Detect gaps >0.5s
   - Trim to 0.3s (not 0 — zero reads as edit, 0.3s reads as natural breath)
   - Apply 30ms audio fade at every cut (prevents click)
4. EXECUTE:
   a. video_ai_remove_silence(input, threshold=-50, min_silence=0.5, padding=0.3)
   b. Or FFmpeg: silenceremove with leave_silence=0.3
5. VERIFY: Listen to 5 random cut points for audio clicks
6. OUTPUT: Tightened video with natural pacing preserved
```

### Auto-Subtitles (Production Quality)

```
1. PROBE: Transcribe with Whisper large model for accuracy
2. CLASSIFY: target_platform determines subtitle style
3. BUILD SRT with production rules:
   - Max 2 lines per caption
   - 37-42 chars per line (BBC/Netflix standard)
   - Line breaks respect syntax (never split article/noun)
   - 12-20 chars/sec reading speed
   - Minimum 1s display, maximum 6s
   - 2-frame gap between consecutive captions
   - 16:9 → 6-word ALL CAPS chunks, ~80% height
   - 9:16 → 3-word chunks, ~75% height, centered safe box
4. BURN: subtitles apply LAST in filter chain
5. VERIFY: Check 5 random timestamps for sync + readability
6. OUTPUT: Video with production-quality hardcoded subtitles
```

### Color Grading Pipeline

```
1. PROBE: Analyze footage — log or rec709? Underexposed? Color cast?
2. CLASSIFY: cinematic → use LUT/curves; talking-head → warm shift + S-curve
3. EXECUTE in order:
   a. Normalize exposure (eq=brightness)
   b. Correct color cast (colorbalance)
   c. Apply contrast (curves S-curve)
   d. Adjust saturation (eq=saturation)
   e. Apply creative look (LUT or warm/cool shift)
   f. Vignette (subtle, PI/4 or less)
4. VERIFY: Thumbnail at 3 points, check skin tones not clipped
5. OUTPUT: Color-graded video
```

### Velocity Edit (Speed Ramping)

```
1. PROBE: Scene detect at 0.3 threshold + transcript for action moments
2. CLASSIFY: content_type=vlog/music-video/social-short, target=tiktok/reels/youtube
3. PLAN:
   - Identify 2-4 peak moments per 60s of footage (high energy, punch points)
   - Pre-roll: 0.5s at 50% speed (anticipation)
   - Impact: 100% speed (full speed at the moment)
   - Post-roll: 1.0s at 30-40% speed (slow-mo release)
   - Audio: atempo chain matches speed changes, paired with setpts
4. EXECUTE:
   a. Extract each segment with handles (0.5s before, 1.5s after)
   b. For each segment, apply speed curve:
      - 0.0-0.5s: 50% speed (edit.speed(input, output, factor=0.5))
      - 0.5-1.0s: 100% speed (edit.speed(input, trimmed, factor=1.0))
      - 1.0-2.5s: 30-40% speed (edit.speed(input, output, factor=0.35))
   c. Assemble with hard cuts (no transition — speed change is the transition)
   d. Add whoosh SFX at each speed-up point (SFX leads visual by 1-2 frames, HR #3)
   e. Two-pass loudnorm to -14 LUFS (social target)
5. VERIFY:
   - Frame-rate check: slow-mo segments should not stutter (60fps source ideal)
   - Audio sync: atempo changes must match setpts (HR #2)
   - Duration matches planned timing
6. OUTPUT: Video with 2-4 velocity peaks, tight pacing
```

## Contradiction Log

Sources disagree on some parameters. Surface these to the user instead of silently picking one.

| Topic | Position A | Position B | Default |
|-------|-----------|-----------|---------|
| J/L-cut offset | 5-15 frames (tech/doc) | 1-2 seconds (vlog) | Pick by content type |
| Loudness target | -14 LUFS (streaming) | -16 LUFS (talking-head) | -16 for dialogue, -14 for social |
| Silence threshold | -30dB | -50dB | -50dB (catches more, padding prevents harshness) |
| Subtitle line length | 37 chars (BBC) | 42 chars (Netflix) | 42 chars (wider compatibility) |
| Transition SFX | Always required | Optional | Always required for whip/glitch/zoom |

## Project Memory Pattern

For multi-step edits, persist a project file:

```json
{
  "project": "my_edit",
  "source": "input.mp4",
  "source_profile": {"duration": 300, "resolution": "1920x1080", "codec": "h264"},
  "plan": [...],
  "steps_completed": [1, 2, 3],
  "step_outputs": {
    "1": "transcript.json",
    "2": "no_silence.mp4",
    "3": "graded.mp4"
  },
  "quality_gates_passed": [true, true, true],
  "final_output": "output.mp4",
  "errors_encountered": [],
  "contradictions_resolved": {"loudness_target": "-16 LUFS"}
}
```

This lets agents resume interrupted work and learn from past failures.

## Configuration Files

### Claude Desktop / Cline / Cursor
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    },
    "whisper-transcribe": {
      "command": "uvx",
      "args": ["whisper-transcribe-mcp"]
    }
  }
}
```

### OpenCode
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

## LLM Recommendations

| Use Case | LLM | Why |
|----------|-----|-----|
| Simple trim/cut/subtitle | Ollama + Qwen2.5-Coder 7B | 88% FFmpeg accuracy, free, local |
| Complex multi-step | Claude / GPT-4o | Better reasoning, fewer retries |
| Batch processing | Groq (Llama 3) | Fast inference, free tier |
| Maximum privacy | Ollama + Qwen2.5-Coder 14B | Fully local, good quality |
| MCP-native | OpenCode (free) | Native MCP support, free tier |

## One-Command Install

```bash
curl -fsSL https://raw.githubusercontent.com/mua47105-hue/agentic-ai-video-knowledgebase/main/setup.sh | bash
```

## Sources

- video-use/editing-craft SKILL.md — Production techniques, Hard Rules, contradiction log
- ELLMPEG paper (arXiv:2602.00028) — Qwen2.5-Coder 88% FFmpeg accuracy
- mcp-video docs — 119 MCP tools for video editing
- FFmpeg documentation — Command reference
- Netflix/Techblog — Subtitle readability standards (37-42 chars, 12-20 cps)
- ITU-R BS.1770-4 — Broadcast loudness standard
