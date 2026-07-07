---
title: Content Adapter
type: entity
tags: [tool, pexels, freesound, footage, sfx, lut]
created: 2026-07-07
updated: 2026-07-07
related: [whisper-ecosystem, free-ai-video-editing-stack]
---

# Content Adapter

Stock footage and sound effects acquisition for AI video editing agents. Parallel to `music_adapter` in design.

## Location

`kb/tools/content_adapter.py`

## Usage

```python
from kb.tools.unified_adapter import footage, sfx

# Search and download stock footage (Pexels)
clips = footage.search("city night", orientation="landscape", duration_min=5)
clip = footage.download(clips[0])
# clip.path -> /path/to/downloaded.mp4
# clip.license_path -> /path/to/downloaded.license.json

# Search and download SFX (Freesound)
sounds = sfx.search("whoosh", duration_max=2)
sfx_file = sfx.download(sounds[0])

# LUTs
from kb.tools.unified_adapter import lut_list, lut_apply
luts = lut_list()
lut_apply("video.mp4", "warm_cinematic", "graded.mp4", intensity=0.8)
```

## Pexels Video API

- 30k+ CC0-licensed video clips
- Requires free API key (`PEXELS_API_KEY` env var)
- 200 req/hr anonymous, 20k req/hr with key
- All clips are CC0 (no attribution required, commercial-safe)
- Search by query, orientation, size

## Freesound SFX API

- 500k+ sound effects
- Requires API key (`FREESOUND_API_KEY` env var)
- Default license filter excludes NC (non-commercial) sounds
- `.license.json` sidecar records exact license
- `project_audit_report()` flags NC-licensed assets

## IWLTBAP LUT Pack

- 16 free LUTs (CC-BY-NC)
- One-time download to `kb/raw/assets/luts/iwltbap/`
- `lut_apply()` wraps FFmpeg's lut3d filter with tetrahedral interpolation
- Supports intensity blending (0.0-1.0)
