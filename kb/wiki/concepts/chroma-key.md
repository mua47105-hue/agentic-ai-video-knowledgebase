---
title: Chroma Key / Green Screen
type: concept
tags: [editing, compositing, chroma-key, green-screen]
created: 2026-07-08
updated: 2026-07-08
sources: []
related: [ffmpeg-command-reference, unified-adapter, tutorial-editing]
---

# Chroma Key / Green Screen

## Definition
Chroma key (commonly called "green screen") is a visual effects technique that replaces a solid-color background (traditionally green or blue) with another image or video. The subject stands in front of the colored background; software removes the background color and composites the subject onto a new background.

## Why it matters
- **Tutorials and talking-head videos** often use green screen to place the presenter over slides, screen recordings, or virtual backgrounds.
- **Weather broadcasts** use chroma key to composite the presenter in front of animated maps.
- **Vlogs and indie films** use it for creative backgrounds and virtual sets.
- **Hard Rule #11** in SKILL.md mandates: *Match chroma key color to source — never guess green.* Probing the actual key color prevents edge artifacts.

## How AI agents handle chroma key

### Key color detection
```bash
ffprobe -v error -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 input.mp4
python3 -c "
import subprocess, json
# Sample a frame and find dominant background color
cmd = ['ffmpeg', '-ss', '0.5', '-i', 'input.mp4', '-frames:v', '1', '-vf', 'format=rgb24', '-f', 'rawvideo', '-']
out = subprocess.run(cmd, capture_output=True).stdout
# Analyze corners + edges to determine key color
"
```

### FFmpeg chromakey
```bash
# Standard green screen (0x00FF00), similarity=0.3, blend=0.1
ffmpeg -i input.mp4 -i background.mp4 -filter_complex \
  "[0:v]chromakey=0x00FF00:0.3:0.1[ck];[ck][1:v]overlay=format=auto" \
  output.mp4

# Blue screen
ffmpeg -i input.mp4 -i background.mp4 -filter_complex \
  "[0:v]chromakey=0x0000FF:0.2:0.05[ck];[ck][1:v]overlay=format=auto" \
  output.mp4

# Colorkey for custom hues
ffmpeg -i input.mp4 -i background.mp4 -filter_complex \
  "[0:v]colorkey=0x00FF00:0.3:0.1[ck];[ck][1:v]overlay" \
  output.mp4
```

### Key parameters
- **Similarity (0-1)**: How close a pixel must be to the key color. Lower = stricter (may miss edges). Higher = looser (may remove parts of the subject).
- **Blend (0-1)**: Feathering at the edges of the key. Higher = softer edges, better with hair/fur. Lower = harder edges, better for sharp objects.
- **Key color**: Always probe the actual background color. Common green screens vary: chroma green (#00FF00), TV green (#00B140), or custom paints.

## Links
- [FFmpeg Command Reference](../guides/ffmpeg-command-reference) — `chromakey`, `colorkey`, and `overlay` filter documentation
- [Unified Adapter](../concepts/unified-adapter) — wraps chromakey as a parameterized tool
- [Tutorial Editing Recipe](../guides/recipe-packs) — tutorial workflow uses green screen for PiP

## References
- Chroma key compositing is a standard technique dating to early film (The Thief of Bagdad, 1940). Modern implementations in ffmpeg are straightforward but require parameter tuning per source.
