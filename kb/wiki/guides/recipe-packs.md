---
title: Recipe Packs
type: guide
tags: [recipes, workflow, one-command, yaml]
created: 2026-07-07
updated: 2026-07-07
related: [free-ai-video-editing-stack, build-your-own-ai-video-editor, multi-cam-editing, chroma-key]
---

# Recipe Packs

One-command YAML workflow templates that convert raw footage into finished cuts. Six pre-built recipes cover the most common editing archetypes.

## Why recipe packs?

The agent's decision engine already emits a JSON `plan` in Phase 3. But today that plan is generated per-request. Recipe packs capture proven patterns as versioned YAML files — a user can run a single command and get a finished result without LLM reasoning per request.

## Available recipes

| Recipe | Input | Output | Runtime (est.) |
|--------|-------|--------|----------------|
| `podcast-to-shorts.yaml` | Podcast episode (30-60 min) | 5 TikTok-ready shorts (30-60s each) | ~90s |
| `wedding-highlights.yaml` | Ceremony + reception footage | 2-4 min highlight reel | ~5 min |
| `shorts-punchy.yaml` | Any talking-head video | 15-30s punchy short with captions + music | ~60s |
| `sports-highlights.yaml` | Game/match footage | Beat-synced action reel | ~3 min |
| `documentary-assembly.yaml` | Interview + B-roll footage | Documentary with J/L-cuts | ~8 min |
| `tutorial-editing.yaml` | Screen recording + face cam | Tutorial with PiP + chapters | ~4 min |
| `vlog-assembly.yaml` | Raw vlog clips | Montage with music bed | ~3 min |

## Quick start

```bash
# List available recipes
python3 -m kb.tools.recipe_runner --list

# Run podcast-to-shorts
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml my_podcast.mp4 --output shorts/

# Run wedding highlights
python3 -m kb.tools.recipe_runner recipes/wedding-highlights.yaml ceremony_and_reception.mp4

# Run shorts-punchy
python3 -m kb.tools.recipe_runner recipes/shorts-punchy.yaml talking_head.mp4
```

## How it works

Recipes are YAML files with three sections:

1. **Metadata** — name, version, content_type, target_platform, output_lufs
2. **Steps** — ordered list of operations with tool references and variable substitutions (`$segment.start`, `$transcript.topic`)
3. **Quality gates** — post-execution checks (verify, VMAF, LUFS tolerance)

Variable references like `$segment.start` are resolved at runtime from the output of earlier steps. The `for_each_segment` construct supports parallel execution with `ThreadPoolExecutor`.

## Adding new recipes

Create a `.yaml` file in `recipes/` with the following structure:

```yaml
name: my-recipe
description: What this recipe does
version: 1.0
content_type: talking-head
target_platform: youtube
output_lufs: -16

steps:
  - operation: probe
    tool: edit.info
    output: source_profile

  - operation: transcribe
    tool: edit.transcribe
    params:
      model: base
    output: transcript

  - operation: for_each_segment
    parallel: true
    loop_var: segment
    source: segment_list
    steps:
      - operation: extract
        tool: edit.trim
        params:
          start: "$segment.start"
          duration: "$segment.duration"

      - operation: render
        tool: edit.render
        params:
          profile: youtube-1080p

quality_gates:
  - check: edit.verify
  - check: edit.quality_full_qc
```

## Built-in recipe tools

The recipe runner provides helper tools prefixed with `recipe.`:

- `recipe.find_engaging_segments` — scores transcript segments by content density
- `recipe.find_key_moments` — identifies ceremonial/action moments from transcript
- `recipe.find_action_moments` — extracts high-energy segments near scene changes
- `recipe.segment_by_topic` — splits transcript into topic-based chunks
- `recipe.find_best_shots` — selects top shots from scene detection results
- `recipe.speed_ramp` — applies pre-roll slow → impact → post-roll slow-mo curve
