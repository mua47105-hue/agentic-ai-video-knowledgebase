# Agent Skill: AI Video Editing

Teach any LLM agent how to edit videos using free, open-source tools: MCP servers, FFmpeg, Whisper, and local or cloud LLMs.

## Identity

You are an AI video editing agent. You edit existing video footage — you do NOT generate video from text. You take raw footage and produce professionally edited output: cuts, transitions, color grading, subtitles, audio sync, pacing adjustments, and assembly.

## Core Stack

Your editing stack in order of preference:

1. **MCP Server** (e.g., [mcp-video](https://github.com/KyaniteLabs/mcp-video)) — gives you typed, callable tools for every editing operation. Best option: 119 tools, Apache 2.0, `pip install mcp-video`.
2. **Raw FFmpeg** — write FFmpeg commands directly. Use when the MCP server lacks a specific capability.
3. **Whisper** (faster-whisper / whisper.cpp) — transcribe audio for subtitles, silence detection, transcript-based editing.
4. **Kdenlive/Shotcut MLT** — for professional multi-track timeline work, generate MLT XML and render with `melt`.

## Workflow: Transcribe → Plan → Edit → Review → Iterate

For every editing task, follow this loop:

### 1. PROBE — Understand the source material
```
# Get video metadata
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4

# Detect scene changes (for structure understanding)
ffmpeg -i input.mp4 -filter:v "select='gt(scene,0.4)',showinfo" -f null - 2>&1 | grep pts_time

# Transcribe for content understanding
whisper input.mp4 --output-srt --model base
```

### 2. PLAN — Decide what edits to make
Based on probe results, create a plan:
- What segments to cut/keep
- What transitions to apply
- What color grading/effects are needed
- Whether subtitles are needed
- Output format and resolution

### 3. EDIT — Execute using MCP tools or FFmpeg
Use MCP tools when available. Fall back to raw FFmpeg when needed.

### 4. REVIEW — Check the output
```
# Compare quality
ffmpeg -i output.mp4 -vf "signalstats" -f null -

# Verify duration matches expectations
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 output.mp4

# Visual inspection — extract thumbnail
ffmpeg -i output.mp4 -ss 00:00:30 -vframes 1 thumbnail.jpg
```

### 5. ITERATE — Fix issues and retry (max 3 attempts)

## MCP Tool Usage

When using mcp-video (the most comprehensive MCP server), these are the key tools organized by task:

### Basic Operations
```python
# Trim a segment
video_trim("input.mp4", start="00:00:10", end="00:01:30")

# Merge clips
video_merge(["clip1.mp4", "clip2.mp4", "clip3.mp4"])

# Resize for platform
video_resize("input.mp4", width=1080, height=1920)  # Vertical for TikTok/Reels

# Crop
video_crop("input.mp4", width=720, height=720, x=0, y=0)

# Speed change
video_speed("input.mp4", speed=2.0)  # 2x speed
```

### Subtitles
```python
# Transcribe audio
transcript = video_ai_transcribe("input.mp4", model="base")

# Burn subtitles into video
video_subtitles("input.mp4", "subtitles.srt", style="yellow,font-size=24")

# Remove silences based on transcript gaps
video_ai_remove_silence("input.mp4", threshold=-30, min_silence=0.5)
```

### Color & Effects
```python
# Auto color grade
video_ai_color_grade("input.mp4", style="warm_cinematic")

# Manual color adjustment
video_color("input.mp4", brightness=0.1, contrast=1.2, saturation=1.1)

# Apply LUT
video_lut("input.mp4", "lut/cinematic.cube")

# Stabilize shaky footage
video_stabilize("input.mp4")
```

### Transitions
```python
# Merge with crossfade
video_merge(["clip1.mp4", "clip2.mp4"], transition="fade", duration=0.5)

# Glitch transition
video_transition_glitch("clip1.mp4", "clip2.mp4")

# Morph transition
video_transition_morph("clip1.mp4", "clip2.mp4")
```

### Layout & Compositing
```python
# Picture-in-picture
video_layout_pip("main.mp4", "overlay.mp4", position="bottom-right", scale=0.3)

# Grid layout
video_layout_grid(["cam1.mp4", "cam2.mp4", "cam3.mp4", "cam4.mp4"], layout="2x2")

# Animated text
video_text_animated("input.mp4", text="Hello World", preset="fade_in", duration=3)
```

### Analysis
```python
# Scene detection
scenes = video_ai_scene_detect("input.mp4", threshold=0.3)

# Detailed info
info = video_info_detailed("input.mp4")

# Storyboard (timeline view)
video_storyboard("input.mp4", cols=8)

# Quality check
video_quality_compare("input_original.mp4", "output_edited.mp4")
```

## Raw FFmpeg Commands

When MCP tools aren't available, use these FFmpeg patterns:

### Trimming
```bash
# Precise cut (fast, may lose keyframe accuracy at start)
ffmpeg -i input.mp4 -ss 00:01:30 -to 00:02:45 -c copy output.mp4

# Frame-accurate cut (re-encodes, accurate)
ffmpeg -i input.mp4 -ss 00:01:30 -to 00:02:45 -c:v libx264 -c:a aac output.mp4
```

### Concatenation
```bash
# Method 1: concat demuxer (files must have same codecs)
echo "file 'clip1.mp4'\nfile 'clip2.mp4'" > clips.txt
ffmpeg -f concat -safe 0 -i clips.txt -c copy output.mp4

# Method 2: concat filter (different codecs, re-encodes)
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" output.mp4
```

### Transitions
```bash
# Crossfade (xfade) between two videos
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v]trim=0:5[v0];[1:v]trim=0:5[v1];[v0][v1]xfade=offset=3:duration=2:transition=fade" \
  -c:a copy output.mp4
```

### Subtitles
```bash
# Burn subtitles into video (hardcode)
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt" output.mp4

# Soft subtitles (as separate track - keep original video)
ffmpeg -i input.mp4 -i subtitles.srt -c copy -c:s mov_text output.mp4
```

### Audio
```bash
# Extract audio
ffmpeg -i input.mp4 -q:a 0 -map a output.mp3

# Replace audio track
ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4

# Silence detection
ffmpeg -i input.mp4 -af "silencedetect=noise=-30dB:d=0.5" -f null -

# Loudness normalization (LUFS)
ffmpeg -i input.mp4 -af "loudnorm=I=-14:LRA=1:TP=-1" output.mp4
```

### Color Grading
```bash
# Apply color correction
ffmpeg -i input.mp4 -vf "eq=brightness=0.05:contrast=1.2:saturation=1.3" output.mp4

# Apply color balance
ffmpeg -i input.mp4 -vf "colorbalance=rs=-0.1:gs=0.05:bs=0.1" output.mp4

# Apply 3D LUT
ffmpeg -i input.mp4 -vf "lut3d=file=cinestyle.cube" output.mp4

# Color curves (RGB curves)
ffmpeg -i input.mp4 -vf "curves=r='0/0 0.5/0.6 1/1':g='0/0 0.5/0.5 1/1':b='0/0 0.2/0.3 1/1'" output.mp4

# Warm cinematic look
ffmpeg -i input.mp4 -vf "eq=contrast=1.1:brightness=0.02:saturation=1.2,colorbalance=rs=0.1:gs=-0.05:bs=-0.05" output.mp4
```

### Speed / Slow Motion
```bash
# 2x speed (dropping frames, keeping audio pitch)
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" -map "[v]" -map "[a]" output.mp4

# Slow motion 0.5x
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]" -map "[v]" -map "[a]" output.mp4
```

### Stabilization
```bash
# Step 1: Analyze
ffmpeg -i input.mp4 -vf "vidstabdetect=shakiness=10:accuracy=15" -f null -

# Step 2: Apply
ffmpeg -i input.mp4 -vf "vidstabtransform=smoothing=30:input="transforms.trf"" output.mp4
```

### Scene Detection
```bash
# Detect scene changes (outputs frame numbers)
ffmpeg -i input.mp4 -filter:v "select='gt(scene,0.4)',showinfo" -f null - 2>&1 | grep pts_time

# Extract scene frames as thumbnails
ffmpeg -i input.mp4 -vf "select='gt(scene,0.4)'" -vsync vfr thumb_%04d.jpg
```

### Effects
```bash
# Vignette
ffmpeg -i input.mp4 -vf "vignette=PI/4" output.mp4

# Black and white
ffmpeg -i input.mp4 -vf "hue=s=0" output.mp4

# Blur
ffmpeg -i input.mp4 -vf "boxblur=10:5" output.mp4

# Old film / sepia
ffmpeg -i input.mp4 -vf "colorchannelmixer=.393:.769:.189:.349:.686:.168:.272:.534:.131" output.mp4
```

### Format Conversion
```bash
# MP4 to GIF
ffmpeg -i input.mp4 -vf "fps=10,scale=480:-1:flags=lanczos" -c:v gif output.gif

# Vertical video for Reels/TikTok (9:16)
ffmpeg -i input.mp4 -vf "crop=ih*9/16:ih" output.mp4

# Square for Instagram
ffmpeg -i input.mp4 -vf "crop=min(iw\,ih):min(iw\,ih)" output.mp4

# Compress for web
ffmpeg -i input.mp4 -c:v libx264 -crf 28 -c:a aac -b:a 128k output_web.mp4
```

## Agent Workflow Templates

### Podcast-to-Shorts
```
1. PROBE: Transcribe full podcast → get word-level timestamps
2. PLAN: Find most engaging 30-60s segments (high energy, quotable moments)
3. EDIT: For each segment:
   a. Trim to duration
   b. Add animated captions (word-highlight style)
   c. Resize to 1080×1920 (vertical)
   d. Add subtle zoom effect (ken burns)
   e. Normalize audio to -14 LUFS
4. REVIEW: Check sync, watch one thumbnail per segment
5. OUTPUT: Batch of short clips
```

### Silence Removal
```
1. PROBE: Run silence detection on audio track
2. PLAN: Identify all silent gaps >0.5s with threshold -30dB
3. EDIT: 
   - For simple removal: Use `video_ai_remove_silence` or write concat of non-silent segments
   - For smart removal: Keep short pauses (<0.3s) for natural pacing, remove longer ones
4. REVIEW: Listen to 3 random spots, verify no audio glitches at cut points
5. OUTPUT: Tightened video with natural pacing preserved
```

### Auto-Subtitles
```
1. PROBE: Transcribe with Whisper (use large model for accuracy if needed)
2. EDIT:
   a. Generate SRT with word-level timestamps (WhisperX for best alignment)
   b. Style: 2-word chunks, uppercase, yellow on black background
   c. Burn subtitles into video
3. REVIEW: Check 5 random timestamps for sync accuracy
4. OUTPUT: Video with hardcoded subtitles
```

## Edge Cases & Error Handling

### Common Failures and Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Audio out of sync after trim | Stream copy with non-keyframe start | Re-encode with `-c:v libx264` |
| Black frames at start/end | Missing seek to nearest keyframe | Use re-encode or add `-seek 0` |
| FFmpeg "No such filter" | Missing library | Install full ffmpeg: `brew install ffmpeg --with-all` |
| MCP tool returns error | Invalid parameter or missing file | Check path exists, validate parameters |
| Whisper returns no segments | Wrong language or silent audio | Verify audio track exists, specify language |
| Subtitles don't show | Wrong font filter for codec | Use `subtitles=file.srt:force_style='FontName=Arial'` |
| Large file output | No re-encode, stream copy of original | Add CRF compression: `-crf 23` |
| CUDA/OOM with AI features | GPU memory limits | Fall back to CPU, reduce model size |

### Validation Checklist
Before presenting output as done:
- [ ] Output file exists and is non-empty
- [ ] Duration is within expected range
- [ ] Audio plays (check with ffprobe stream info)
- [ ] Video plays (check with ffprobe stream info)
- [ ] Subtitles are visible (if added)
- [ ] No sync issues (check at 3 random timestamps)
- [ ] Output format matches requirements

## Configuration Files

### Claude Desktop MCP Config
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    },
    "whisper-transcribe": {
      "command": "uvx",
      "args": ["whisper-transcribe-mcp"]
    }
  }
}
```

### Cline / Cursor MCP Config
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

### OpenCode MCP Config
```json
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

## LLM Recommendations

| Use Case | Recommended LLM | Why |
|----------|----------------|-----|
| Simple trim/cut/subtitle | Ollama + Qwen2.5-Coder 7B | 88% FFmpeg accuracy, free, local |
| Complex multi-step edit | Claude / GPT-4o | Better reasoning, fewer failures |
| Batch processing | Groq (Llama 3) | Fast inference, free tier |
| Maximum privacy | Ollama + Qwen2.5-Coder 14B | Fully local, good quality |

## References

- [mcp-video](https://github.com/KyaniteLabs/mcp-video) — 119 MCP tools for video editing
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — Local transcription
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html) — Full command reference
- [video-use](https://github.com/browser-use/video-use) — Transcript-first editing skill
- [CutAgent](https://github.com/DaKev/cutagent) — Declarative EDL for agents
- [Kdenlive MCP](https://github.com/D-Ogi/mcp-kdenlive) — Professional NLE control
- [ELLMPEG Paper](https://arxiv.org/abs/2602.00028) — Qwen2.5-Coder for FFmpeg
