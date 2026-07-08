---
title: Hyperframes
type: entity
tags: [tool, rendering, animations, nodejs]
created: 2026-07-08
updated: 2026-07-08
sources: []
related: [mcp-video, ffmpeg-command-reference, local-llm-setup]
---

# Hyperframes

## What it is
Hyperframes is an open-source (MIT) Remotion-based library for generating programmatic video frames — kinetic text, animated overlays, data-driven visualizations, and motion graphics. It wraps Remotion's React-based rendering pipeline into a simpler API specifically designed for video editing pipelines.

## Capabilities
- **Kinetic text**: Animated lower-thirds, title cards, credits rolls with customizable easing curves.
- **Data-driven visualizations**: Charts, graphs, and data overlays rendered frame-by-frame.
- **Animated overlays**: Progress bars, countdown timers, corner bugs, watermarks.
- **Template rendering**: Pre-built templates for YouTube intros, social-media cards, and call-to-action overlays.

## Integration with mcp-video
**18 mcp-video tools** wrap Hyperframes functionality. When the unified adapter receives a `text_subtitles_animated`, `add_overlay`, or `generate_intro` call, it delegates to the appropriate Hyperframes tool if available:
- `edit.text_subtitles_animated` → Hyperframes kinetic text
- `edit.add_overlay` → Hyperframes animated overlay
- `edit.generate_intro` → Hyperframes template

## Pricing and requirements
- **License**: MIT — fully open source, free for commercial use.
- **Runtime**: Requires Node.js 18+ installed on the system.
- **Rendering**: Slower than equivalent FFmpeg filter chains (Remotion renders each frame individually via Puppeteer). A 10-second animated title card takes ~30 seconds to render on modern hardware.
- **Setup**: The repo's `setup.sh` checks for Node.js and will install Hyperframes if requested, but it is optional — FFmpeg fallbacks exist for every Hyperframes tool.

## Limitations
- **Performance**: Rendering speed is the primary limitation. For simple overlays (static text, basic shapes), FFmpeg's `drawtext` filter is faster and should be preferred.
- **Dependency**: Requires Node.js + npm + Puppeteer (Chromium download ~300MB). Not suitable for containerized deployments where minimizing image size matters.
- **Complexity**: True production kinetic typography (per-character animation, variable fonts, complex easing) is best done with Hyperframes. Simple lower-thirds should use FFmpeg.

## Links
- [mcp-video](../entities/mcp-video) — tools that wrap Hyperframes functionality
- [FFmpeg Command Reference](../guides/ffmpeg-command-reference) — `drawtext` and `subtitles` filters for simpler text overlays
- [Local LLM Setup](../guides/local-llm-setup) — Node.js installation requirements
- [Unified Adapter](../concepts/unified-adapter) — routes between mcp-video/Hyperframes and FFmpeg fallbacks

## References
- Hyperframes GitHub repository (remotion-dev/hyperframes)
- Remotion documentation (remotion.dev)
- mcp-video tool documentation — 18 Hyperframes-wrapping tools
