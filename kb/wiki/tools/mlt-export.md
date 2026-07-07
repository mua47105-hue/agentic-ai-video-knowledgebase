---
title: MLT XML Export
type: entity
tags: [tool, mlt, nle, xml, kdenlive, shotcut]
created: 2026-07-07
updated: 2026-07-07
related: [free-ai-video-editing-stack, recipe-packs]
---

# MLT XML Export

Converts `.aevp` project files to MLT XML for NLE interoperability. Opens in Kdenlive and Shotcut. Renders headlessly via `melt`.

## Location

`kb/tools/mlt_export.py`

## Usage

```python
from kb.tools.mlt_export import export_mlt, render_mlt, export_fcpxml

# Export to MLT XML
mlt_path = export_mlt("project.aevp", "project.mlt")

# Render headlessly
render_mlt("project.mlt", "output.mp4", profile="youtube-1080p")

# Export to FCPXML for Final Cut Pro
fcpxml_path = export_fcpxml("project.aevp", "project.fcpxml")
```

## Supported operations (round-trip safe)

- trim, merge (with xfade transitions)
- resize, crop
- color_grade (warm/cool/bw → MLT avfilter.eq)
- text_subtitles (burned-in)
- speed changes
- audio fade in/out
- J-cuts, L-cuts

## Not supported (flattened to rendered video)

- stabilize (vidstab has no MLT equivalent)
- complex FFmpeg filter chains
- VMAF quality scoring

## Requirements

- `melt` binary for headless rendering (`apt install melt` or `brew install mlt`)
- Optional: `opentimelineio` for FCPXML export (`pip install opentimelineio`)
