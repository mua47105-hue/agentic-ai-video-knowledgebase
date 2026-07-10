---
title: auto-editor
type: entity
tags: [tool, editing, silence-removal, automation, cli]
created: 2026-07-10
updated: 2026-07-10
sources: []
related: [whisper-ecosystem, mlt-export, unified-adapter, free-ai-video-editing-stack]
---
# auto-editor

## What it is
auto-editor is an open-source (MIT) CLI tool for automatic video editing —
silence removal, motion-based cutting, and beat-synced assembly. Rust binary
distributed via PyPI launcher. The open-source equivalent of Descript's auto-cut.

## Capabilities
- **Silence auto-cut**: Detect and remove silent segments with configurable margin
- **Motion detection**: Cut based on visual motion (not just audio)
- **Speed control**: Per-segment speed (keep at 1x, silent at 999x = cut)
- **EDL export**: Premiere Pro, DaVinci Resolve, Final Cut Pro, Shotcut, Kdenlive
- **JSON analysis**: Dry-run output of cut decisions for programmatic use

## Integration
Subprocess adapter at `kb/tools/auto_editor_adapter.py`.
```python
from kb.tools.unified_adapter import edit
edit.auto_edit("livestream.mp4", "highlights.mp4", margin=0.3)
edit.auto_edit_to_edl("input.mp4", "cuts.edl", target_nle="premiere")
```

## When to use vs edit.silence_remove
| Use case | Tool | Why |
|---|---|---|
| Quick silence removal on short video | edit.silence_remove | FFmpeg-native, no subprocess overhead |
| Long-form (1hr+) auto-cut | edit.auto_edit | Purpose-built, faster, handles edge cases |
| EDL export for NLE handoff | edit.auto_edit_to_edl | Only auto-editor exports EDLs |

## License: MIT | Links: [PyPI](https://pypi.org/project/auto-editor/) | [GitHub](https://github.com/WyattBlue/auto-editor)
