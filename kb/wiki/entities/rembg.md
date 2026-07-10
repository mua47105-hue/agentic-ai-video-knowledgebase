---
title: rembg
type: entity
tags: [tool, vision, background-removal, ai, gated]
created: 2026-07-10
updated: 2026-07-10
sources: []
related: [vlm-adapter, reframe-adapter, unified-adapter, free-ai-video-editing-stack]
---
# rembg

## What it is
rembg is an open-source (MIT) background removal tool using U2Net. It removes
backgrounds from images and videos with AI matting — the open-source equivalent
of CapCut's "remove background" feature. Runs locally, no API needed.

## Capabilities
- **Image background removal**: Single-image matting via U2Net/U2Netp/U2Net-HumanSeg/ISNet
- **Video background removal**: Frame-by-frame processing via FFmpeg pipe
- **Alpha matting**: Fine hair-edge detection
- **Model selection**: u2net (default), u2netp (fast), u2net_human_seg (people), isnet-general-use (high quality)

## Integration
Gated adapter at `kb/tools/rembg_adapter.py`. Enable via `REMBG_ENABLED=1` + `pip install rembg`.
```python
from kb.tools.unified_adapter import edit
edit.remove_background("input.jpg", "output.png")
edit.remove_background_video("input.mp4", "output.mp4")
```

## Limitations
- Model download (~170MB U2Net weights on first run)
- Video processing is slow (~2s per 1080p frame on CPU)
- U2Net struggles with fine hair vs commercial tools

## License: MIT (permissive — safe for commercial use)
## Links: [PyPI](https://pypi.org/project/rembg/) | [GitHub](https://github.com/danielgatis/rembg)
