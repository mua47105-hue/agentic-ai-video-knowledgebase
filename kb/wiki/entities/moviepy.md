---
title: MoviePy
type: entity
tags: [tool, nle, composition, python, gated]
created: 2026-07-10
updated: 2026-07-10
sources: []
related: [mlt-export, unified-adapter, free-ai-video-editing-stack]
---
# MoviePy

## What it is
MoviePy is an open-source (MIT) Python library for programmatic video editing.
It provides a clip-based API (VideoFileClip, CompositeVideoClip, TextClip) that
abstracts FFmpeg filtergraphs — the Python-native alternative to writing complex
filter chains. Used by Zulko since 2014, rewritten in v2.0 (2024).

## When to use (HR#31)
Per Hard Rule #31: **FFmpeg filtergraphs exceeding 5 nodes must switch to MoviePy.**

| Use case | Tool | Why |
|---|---|---|
| Simple trim/concat | edit.trim, edit.merge | FFmpeg-native, faster |
| Multi-clip PiP with animation | edit.moviepy_compose | MoviePy — filtergraph would be 10+ nodes |
| Text with motion tracking | edit.moviepy_compose | MoviePy — lambda functions for position |
| Complex timeline (>5 elements) | edit.moviepy_compose | MoviePy — HR#31 |

## Integration
Gated adapter at `kb/tools/moviepy_adapter.py`.
```python
from kb.tools.unified_adapter import edit
edit.moviepy_compose(clips_spec=[...], output_path="composite.mp4")
edit.moviepy_concatenate(["a.mp4", "b.mp4"], "merged.mp4", transition="crossfade")
```

## Limitations
- Memory: Decodes frames into numpy (~6MB per 1080p frame)
- Speed: Slower than raw FFmpeg (Python overhead per frame)
- v2.0 breaking changes: v1 API deprecated; v2 uses with_* methods

## License: MIT | Links: [PyPI](https://pypi.org/project/moviepy/) | [GitHub](https://github.com/Zulko/moviepy)
