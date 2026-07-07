---
title: Hardware Acceleration for Video Encoding
type: guide
tags: [guide, encoding, hardware, gpu, nvenc, qsv, videotoolbox]
created: 2026-07-08
updated: 2026-07-08
sources: []
related: [ffmpeg-command-reference, local-llm-setup]
---

# Hardware Acceleration for Video Encoding

## Overview
Hardware-accelerated encoding uses dedicated media engines on GPUs to encode video much faster than software encoding (libx264) — typically 4-8× faster at the cost of slightly lower quality at the same bitrate.

Available on all modern platforms:
- **NVIDIA NVENC** (Windows/Linux) — most mature, best quality/speed ratio
- **Intel QSV** (QuickSync Video, Windows/Linux) — good quality on 11th-gen+ iGPUs
- **Apple VideoToolbox** (macOS) — excellent quality on Apple Silicon M-series
- **AMD AMF** (Windows/Linux) — good, less ecosystem support

## When to use hardware encoding

### Pros
- **Speed**: 4-8× faster than software encoding. A 10-minute 4K render drops from 20 minutes to 3 minutes.
- **Power efficiency**: Hardware encoders use dedicated silicon, not CPU cores. Laptop battery drain is significantly lower.
- **Real-time encoding**: Critical for streaming or live workflows.

### Cons
- **Quality**: At the same bitrate, NVENC/QSV produces slightly lower quality than libx264 `-preset slow` — around 10-15% higher bitrate needed for equivalent perceptual quality.
- **Filter compatibility**: Hardware encoders don't support all filter chains. Complex filter graphs may require partial software processing.
- **Codec support**: Hardware encoders often lack high-bit-depth (10-bit) or specific chroma subsampling modes that software encoders support.

## Detecting available encoders

```bash
# List all encoders
ffmpeg -encoders | grep -E "nvenc|qsv|videotoolbox|h264_amf|hevc_amf"

# Check NVENC specifically
ffmpeg -hide_banner -encoders | grep nvenc

# Verify hardware decoder support
ffmpeg -hide_banner -hwaccels
```

## Encoding commands per platform

### NVIDIA NVENC
```bash
# H.264
ffmpeg -i input.mp4 -c:v h264_nvenc -preset p7 -cq 23 -c:a aac output.mp4

# H.265/HEVC (better quality at same bitrate, wider compatibility on modern devices)
ffmpeg -i input.mp4 -c:v hevc_nvenc -preset p7 -cq 26 -c:a aac output.mp4

# With hardware decode + encode (full GPU pipeline)
ffmpeg -hwaccel cuda -i input.mp4 -c:v h264_nvenc -preset p7 -cq 23 output.mp4
```

### Intel QSV
```bash
# H.264
ffmpeg -i input.mp4 -c:v h264_qsv -preset medium -global_quality 23 -c:a aac output.mp4

# H.265
ffmpeg -i input.mp4 -c:v hevc_qsv -preset medium -global_quality 26 -c:a aac output.mp4

# With hardware decode
ffmpeg -hwaccel qsv -i input.mp4 -c:v h264_qsv -preset medium -global_quality 23 output.mp4
```

### Apple VideoToolbox
```bash
# H.264
ffmpeg -i input.mp4 -c:v h264_videotoolbox -b:v 5M -c:a aac output.mp4

# H.265 (HEVC) — best quality on Apple Silicon
ffmpeg -i input.mp4 -c:v hevc_videotoolbox -b:v 4M -c:a aac output.mp4
```

## Integrating with recipes

Hardware acceleration is not enabled by default in recipe packs because:
1. Recipes prioritize quality over speed (they are batch processes, not live streams).
2. Hardware encoder availability varies across platforms.
3. Some recipes use filter chains incompatible with hardware encoders (e.g., complex chromakey + overlay pipelines).

**To enable**: Pass the hardware encoder explicitly in render steps by modifying the recipe's render params:
```yaml
- operation: render
  tool: edit.render
  params:
    profile: youtube-1080p
    encoder: h264_nvenc   # override software encoder
```

## Links
- [FFmpeg Command Reference](../guides/ffmpeg-command-reference) — encoder flags and hardware acceleration options
- [Local LLM Setup](../guides/local-llm-setup) — GPU considerations for LLM + video pipelines
- [Recipe Packs](../guides/recipe-packs) — how to modify render steps for hardware encoding

## References
- NVIDIA Video Codec SDK documentation
- Intel Media SDK documentation
- Apple VideoToolbox framework documentation
- FFmpeg Hardware Acceleration Guide (ffmpeg.org)
