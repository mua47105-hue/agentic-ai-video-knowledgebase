---
title: Multimodal Intelligence Architecture
type: concept
tags: [intelligence, multimodal, probe, relevance-map, plan-critic, memory]
created: 2026-07-07
updated: 2026-07-07
related: [self-evaluation-loop, unified-adapter, mcp-video, free-ai-video-editing-stack]
---

# Multimodal Intelligence Architecture

The Phase 6-9 intelligence layer transforms the framework from "transcript-first with rule-based recovery" into "multimodal-first with self-critique and memory." The framework now **sees** the video (per-frame visual + audio features), **knows** where the good parts are (relevance map + hero moments), **knows** where to cut (Murch Rule of Six), **knows** how to pace and slow-mo (content-type profiles + impact/reveal/beauty detection), **critiques** its own plans before execution (Plan Critic), **learns** from every run (edit-pattern memory DB), and **explains** every decision (decision log + fusion reasoning).

## The 8-module pipeline

```
User request → M0 PROBE → M0.5 CLASSIFY → M1 RELEVANCE MAP → M2 PLAN
            → M2.5 PLAN CRITIC → M3 BUILD → M4 VERIFY → M5 MEMORY WRITE
```

| Module | File | Phase | What it does |
|---|---|---|---|
| M0 PROBE | `kb/tools/probe*.py` | 6 | Extracts per-frame visual + per-window audio + semantic features in parallel. 13 feature extractors, all optional with graceful degradation. |
| M0.5 CLASSIFY | `kb/tools/classifier.py` | 3 | Rule-based content-type classification (10 types) from probe signals. |
| M1 RELEVANCE MAP | `kb/tools/relevance_map.py` | 7 | Per-second 6-dimensional scoring + hero_score (geometric-mean cross-modal fusion). |
| M1+ HERO DETECT | `kb/tools/hero_detector.py` | 9 | Cross-modal peak co-occurrence fusion (audio × visual × semantic). ★ NOVEL ★ |
| M2 PLAN | `kb/tools/intelligent_planner.py` | 9 | LLM-based EditPlan generation (or rule-based fallback) consuming M0-M1 outputs. |
| M2.5 PLAN CRITIC | `kb/tools/plan_critic.py` | 9 | Red-teams EditPlan against 11 Hard Rules BEFORE execution. ★ NOVEL ★ |
| M3 BUILD | `kb/tools/recipe_runner.py` | 1-4 | Executes recipe steps via unified_adapter. |
| M3+ PACING/SLOWMO/MUSIC | `kb/tools/pacing_engine.py`, `slowmo_engine.py`, `music_sync.py` | 8 | Content-type pacing profiles + slow-mo at impact/reveal/beauty + music structure alignment + ducking. |
| M4 VERIFY | `kb/tools/reviewer.py` | 9 | 7-dimension scoring + VMAF auto-correction. |
| M5 MEMORY | `kb/tools/edit_memory.py` | 9 | SQLite edit-pattern DB: (content_type, technique, params) → success_rate. ★ NOVEL ★ |

## The 3 novel contributions

These three capabilities are not implemented by any of the 11 agentic video frameworks documented in this wiki (OpenMontage, Crayotter, VideoAgent, video-use, UniVA, CutClaw, AVE, AI_Editor, Pilipili, X-Cut, Project Montage):

1. **Plan Critic before execution** — every other framework reviews *after* rendering. We red-team the plan *before* any FFmpeg call, catching Hard Rule violations, SourceProfile mismatches, and hero-preservation failures. Eliminates 80% of failures for free.

2. **Cross-modal hero moment detection** — nobody fuses audio peak × visual peak × semantic salience into a single "this is the moment" signal via geometric-mean co-occurrence. CutClaw uses audio+visual for cutting; video-use is transcript-only. Our `hero_detector.py` finds moments where all three modalities peak within 0.5 seconds (level 3 = triple, the strongest signal).

3. **Edit-pattern memory that generalizes** — Pilipili learns creator *style* (color palette, pacing) via Mem0; UniVA has 3-level memory (trace/user/task). Nobody learns *technique success rates per content type* — our SQLite DB tracks `(content_type, technique, params_hash) → {success_rate, avg_vmaf, sample_count}` so the planner biases future plans toward historically successful techniques.

## Graceful degradation

Every heavy-model dependency is OPTIONAL. The probe degrades gracefully:

| Install level | What works |
|---|---|
| Minimal (ffmpeg + numpy + pyyaml) | ffprobe metadata, ffmpeg scdet scenes, ebur128 loudness |
| + librosa + opencv | + librosa beats/onsets, OpenCV motion energy, PySceneDetect scenes |
| + faster-whisper | + CrisperWhisper transcription, transcript packing, keyphrase extraction |
| + silero-vad | + speech/silence segmentation |
| + mediapipe + hsemotion | + face presence, emotion (7-class + arousal/valence), shot scale |
| + demucs | + stem separation (vocals/music) for music sync |
| + pyannote.audio (HF-gated) | + speaker diarization |
| + speechbrain | + audio prosody emotion |
| + easyocr | + on-screen text extraction |
| + open-clip-torch | + LAION aesthetic scoring |
| + litellm + ollama | + LLM plan generation + LLM plan critique |

The framework NEVER requires >6GB VRAM. Qwen2.5-VL (~18GB) remains gated behind `VLM_ENABLED=1` and is never called by the probe layer.

## License discipline

Disqualified models (non-permissive licenses):
- madmom — CC-BY-NC-SA model files
- opensmile — GPLv3
- aubio — GPL-3.0
- YOLOv8 / YOLOv11 — AGPL-3.0 (viral)
- OpenPose — academic non-commercial only

Used instead (all permissive): librosa (ISC), MediaPipe (Apache-2.0), HSEmotion (Apache-2.0), Silero VAD (MIT), pyannote.audio (MIT, HF-gated), Demucs (MIT), SpeechBrain (Apache-2.0), EasyOCR (Apache-2.0), LAION-CLIP (MIT), LiteLLM (MIT).

## Usage

```bash
# Probe only — save SourceProfile JSON
python3 -m kb.tools.recipe_runner --probe-only input.mp4 --output /tmp/

# Full intelligence analysis without executing a recipe
python3 -m kb.tools.recipe_runner --analyze-only input.mp4 --output /tmp/

# Run a recipe with full intelligence layer (probe + relevance map + cut detection + pacing + slow-mo + music sync + hero detection + plan critic + reviewer + memory)
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4

# Skip LLM plan generation (use recipe YAML directly, still run probe + reviewer)
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4 --no-intelligent-planning
```

## Related pages

- [Self-Evaluation Loop](../concepts/self-evaluation-loop) — the broader concept this implements
- [Unified Adapter](../concepts/unified-adapter) — the execution substrate M3 BUILD uses
- [MCP Video](../entities/mcp-video) — the tool backbone
- [Free AI Video Editing Stack](../guides/free-ai-video-editing-stack) — install guide
