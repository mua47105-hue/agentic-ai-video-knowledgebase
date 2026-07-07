---
title: Recipe Runner
type: entity
tags: [tool, recipe, yaml, workflow]
created: 2026-07-07
updated: 2026-07-07
related: [recipe-packs, free-ai-video-editing-stack]
---

# Recipe Runner

Executes YAML recipe packs against input video files. The core engine behind one-command video workflows.

## Location

`kb/tools/recipe_runner.py`

## Usage

```bash
python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4 --output shorts/
python3 -m kb.tools.recipe_runner --list
```

## Architecture

- Parses YAML recipe files with metadata, steps, and quality gates
- Resolves `$variable` references from step outputs
- Executes steps in order; supports `for_each_segment` with parallel execution
- Runs post-execution quality gates (verify, VMAF, LUFS tolerance)
- Writes output manifest to `output_dir/manifest.json`
- Zero new dependencies (requires PyYAML)

## Built-in tools

Six built-in `recipe.*` tools: `find_engaging_segments`, `find_key_moments`, `find_action_moments`, `segment_by_topic`, `find_best_shots`, `speed_ramp`.
