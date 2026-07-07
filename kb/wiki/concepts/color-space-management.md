---
title: Color-Space Management
type: concept
tags: [color, grading, technical, standards]
created: 2026-07-08
updated: 2026-07-08
sources: []
related: [ffmpeg-command-reference, unified-adapter, mcp-video]
---

# Color-Space Management

## Definition
Color-space management is the practice of explicitly knowing and controlling the color space (working space, transfer function, primaries) at every stage of the video pipeline — from source file through grading to delivery encode.

Without management, applying `eq`, `curves`, or `color_grade` to log-encoded footage without conversion produces unpredictable results: crushed blacks, blown highlights, or unnatural color shifts.

## Why it matters
- **Log footage** (S-Log, V-Log, C-Log, RED Log) stores scene-linear or log-encoded light values. Display on Rec.709 without conversion looks flat and desaturated (this is normal — it's the "log look").
- **Applying grading before conversion** adjusts values in the log domain, which is non-uniform relative to human perception. A 10% contrast bump in log space may clip highlights or crush shadows.
- **Hard Rule #13** in SKILL.md mandates: *Probe and convert color space before any color operation.* This is the only way to guarantee consistent grading results.
- **Multi-cam shoots** with different cameras (Sony S-Log vs Canon C-Log vs DJI D-Log) require per-clip color space detection and conversion to a common working space before any color matching.

## How AI agents handle it
1. **Probe**: `ffprobe -show_entries stream=color_space,color_transfer,color_primaries` reads the source metadata fields.
2. **Detect**: If `color_transfer` is `bt2020-10`, `smpte2084` (PQ), or `arib-std-b67` (HLG), the footage is HDR. If `color_primaries` is `bt2020`, convert to Rec.709 for SDR delivery.
3. **Convert**: `ffmpeg -colorspace bt709 -color_trc bt709 -color_primaries bt709` or the `zscale` filter for precise conversions: `zscale=transfer=linear, zscale=primaries=bt709, zscale=transfer=bt709`.
4. **Grade**: Apply curves, contrast, saturation in the standardized working space. Then convert to delivery color space.

## Links
- [FFmpeg Command Reference](../guides/ffmpeg-command-reference) — `colorspace` and `zscale` filter documentation
- [Unified Adapter](../concepts/unified-adapter) — exposes `probe()` which includes color-space metadata
- [mcp-video](../entities/mcp-video) — provides `edit.color_grade()` which handles conversion internally

## References
- ITU-R BT.709-6 (HD color space), ITU-R BT.2020-2 (UHD/HDR color space)
- ACES (Academy Color Encoding System) — production color management standard
