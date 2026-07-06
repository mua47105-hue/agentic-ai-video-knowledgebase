---
title: FFmpeg Command Reference for AI Agents
type: guide
tags: [ffmpeg, commands, reference, editing]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [free-ai-video-editing-stack, mcp-video-servers, skill]
---

# FFmpeg Command Reference for AI Agents

Complete command patterns organized by editing task. Every agent should understand these patterns before attempting video editing with raw FFmpeg.

## Contents

1. [Probing & Analysis](#probing--analysis)
2. [Trimming & Cutting](#trimming--cutting)
3. [Concatenation](#concatenation)
4. [Transitions](#transitions)
5. [Color Grading](#color-grading)
6. [Subtitles & Text](#subtitles--text)
7. [Audio Operations](#audio-operations)
8. [Speed Changes](#speed-changes)
9. [Stabilization](#stabilization)
10. [Scene Detection](#scene-detection)
11. [Silence Removal](#silence-removal)
12. [Effects & Filters](#effects--filters)
13. [Format Conversion](#format-conversion)
14. [Compositing & Layout](#compositing--layout)
15. [Quality & Compression](#quality--compression)
16. [Batch Processing](#batch-processing)
17. [Best Practices](#best-practices)

---

## Probing & Analysis

### Get full media info (JSON)
```bash
ffprobe -v quiet -print_format json -show_format -show_streams input.mp4
```

### Get duration only
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 input.mp4
```

### Get resolution and codec
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name -of csv=p=0 input.mp4
```

### Get frame count
```bash
ffprobe -v error -select_streams v:0 -count_frames -show_entries stream=nb_read_frames -of default=nokey=1:noprint_wrappers=1 input.mp4
```

### Check if audio stream exists
```bash
ffprobe -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 input.mp4
```

### Extract thumbnail frame
```bash
ffmpeg -i input.mp4 -ss 00:00:30 -vframes 1 -q:v 2 thumbnail.jpg
```

### Generate filmstrip (tiled thumbnails)
```bash
ffmpeg -i input.mp4 -vf "fps=1/10,scale=320:-1,tile=5x4" -q:v 2 filmstrip.jpg
```

### Audio waveform visualization
```bash
ffmpeg -i input.mp4 -filter_complex "showwaves=s=1280x240:mode=line:rate=25,format=yuv420p" -c:v libx264 waveform.mp4
```

---

## Trimming & Cutting

### Fast cut (stream copy, not frame-accurate)
```bash
ffmpeg -i input.mp4 -ss 00:01:30 -to 00:02:45 -c copy output.mp4
```

### Frame-accurate cut (re-encode)
```bash
ffmpeg -i input.mp4 -ss 00:01:30 -to 00:02:45 -c:v libx264 -c:a aac output.mp4
```

### Cut from start (duration-based)
```bash
ffmpeg -i input.mp4 -t 00:00:30 -c copy output.mp4
```

### Multiple cuts (using trim filter)
```bash
ffmpeg -i input.mp4 -filter_complex \
  "[0:v]trim=start=10:end=20,setpts=PTS-STARTPTS[v0]; \
   [0:v]trim=start=40:end=50,setpts=PTS-STARTPTS[v1]; \
   [v0][v1]concat=n=2:v=1:a=0[outv]" \
  -map "[outv]" output.mp4
```

### Extract segment with fade in/out
```bash
ffmpeg -i input.mp4 -ss 00:00:30 -t 00:00:10 -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=9.5:d=0.5" -af "afade=t=in:st=0:d=0.5,afade=t=out:st=9.5:d=0.5" output.mp4
```

---

## Concatenation

### Method 1: Concat demuxer (same codecs, no re-encode)
```bash
# Create file list
printf "file '%s'\n" clip1.mp4 clip2.mp4 clip3.mp4 > clips.txt
# OR: echo "file 'clip1.mp4'" > clips.txt && echo "file 'clip2.mp4'" >> clips.txt

# Concatenate
ffmpeg -f concat -safe 0 -i clips.txt -c copy output.mp4
```

### Method 2: Concat filter (different codecs, re-encodes)
```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" output.mp4
```

### Method 3: Concat protocol (MPEG-TS intermediate)
```bash
ffmpeg -i "concat:intermediate1.ts|intermediate2.ts" -c copy -bsf:a aac_adtstoasc output.mp4
```

---

## Transitions

### Crossfade between two clips (xfade)
```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v]trim=0:5[v0];[1:v]trim=0:5[v1]; \
   [v0][v1]xfade=offset=3:duration=2:transition=fade" \
  -c:a copy output.mp4
```

Available xfade transitions: `fade`, `fadeblack`, `fadewhite`, `fadegrays`, `dissolve`, `pixelize`, `hblur`, `wipetl`, `wipebr`, `slideright`, `slideleft`, `slidetop`, `slidebottom`, `smoothleft`, `smoothright`, `smoothup`, `smoothdown`, `circlecrop`, `rectcrop`, `circleclose`, `circleopen`, `horzclose`, `horzopen`, `vertclose`, `vertopen`, `diagbl`, `diagbr`, `diagtl`, `diagtr`, `hlslice`, `hrslice`, `vuslice`, `vdslice`, `hblur`, `fadegrays`, `burnt`, `fade` (default)

### Crossfade with audio
```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v]trim=0:5[v0];[1:v]trim=0:5[v1]; \
   [v0][v1]xfade=offset=3:duration=2:transition=fade[vout]; \
   [0:a]atrim=0:5[a0];[1:a]atrim=0:5[a1]; \
   [a0][a1]acrossfade=d=2[aout]" \
  -map "[vout]" -map "[aout]" output.mp4
```

### Slide transitions between multiple clips
```bash
ffmpeg -i clip1.mp4 -i clip2.mp4 -i clip3.mp4 -filter_complex \
  "[0:v]trim=0:3[v0];[1:v]trim=0:3[v1];[2:v]trim=0:3[v2]; \
   [v0][v1]xfade=offset=2:duration=1:transition=slideleft[tmp]; \
   [tmp][v2]xfade=offset=4:duration=1:transition=slideleft[vout]" \
  -map "[vout]" output.mp4
```

---

## Color Grading

### Brightness, contrast, saturation
```bash
# Brightness: -1.0 to 1.0, Contrast: -2.0 to 2.0, Saturation: 0.0 to 3.0
ffmpeg -i input.mp4 -vf "eq=brightness=0.05:contrast=1.2:saturation=1.3" -c:a copy output.mp4
```

### Color balance (shadows, midtones, highlights)
```bash
# Shadows(rs/gs/bs), Midtones(gm), Highlights(bh)
# rs=-0.1 = reduce red in shadows
ffmpeg -i input.mp4 -vf "colorbalance=rs=-0.05:gs=0.03:bs=0.08" output.mp4
```

### Curves (precise tonal control)
```bash
# S-curve for contrast
ffmpeg -i input.mp4 -vf "curves=r='0/0 0.25/0.2 0.5/0.5 0.75/0.8 1/1':g='0/0 0.25/0.2 0.5/0.5 0.75/0.8 1/1':b='0/0 0.25/0.2 0.5/0.5 0.75/0.8 1/1'" output.mp4
```

### Apply 3D LUT
```bash
ffmpeg -i input.mp4 -vf "lut3d=file=cinestyle.cube" -c:a copy output.mp4
```

### Warm cinematic look
```bash
ffmpeg -i input.mp4 -vf "eq=contrast=1.1:brightness=0.02:saturation=1.2,colorbalance=rs=0.1:gs=-0.05:bs=-0.05" output.mp4
```

### Cool / teal-and-orange look
```bash
ffmpeg -i input.mp4 -vf "eq=contrast=1.15:saturation=0.9,colorbalance=rs=0.05:gs=-0.05:bs=0.15,curves=r='0/0 1/0.95':b='0/0 1/0.9'" output.mp4
```

### Black and white
```bash
ffmpeg -i input.mp4 -vf "hue=s=0,eq=contrast=1.3:brightness=0.03" output.mp4
```

### Vintage / sepia
```bash
ffmpeg -i input.mp4 -vf "colorchannelmixer=.393:.769:.189:.349:.686:.168:.272:.534:.131" output.mp4
```

### Night vision / green tint
```bash
ffmpeg -i input.mp4 -vf "colorbalance=gs=0.3:bs=-0.3,eq=brightness=0.2:contrast=1.5" output.mp4
```

### Vignette (darken edges)
```bash
ffmpeg -i input.mp4 -vf "vignette=PI/4:max_eval=frame" output.mp4
```

---

## Subtitles & Text

### Transcribe with Whisper (CLI)
```bash
# Install: brew install whisper-cpp or pip install openai-whisper
whisper input.mp4 --model base --output-srt --output-vtt

# Specify language
whisper input.mp4 --model base --language en --output-srt

# Word-level timestamps (WhisperX)
whisperx input.mp4 --model base --align_model WAV2VEC2_ASR_LARGE_LV60K_960H --output_srt
```

### Burn SRT subtitles (hardcode into video)
```bash
ffmpeg -i input.mp4 -vf "subtitles=subtitles.srt:force_style='FontName=Arial,FontSize=20,PrimaryColour=&HFFFFFF,BackColour=&H80000000,Outline=1,Shadow=1,MarginV=40'" output.mp4
```

### Soft subtitles (separate track)
```bash
ffmpeg -i input.mp4 -i subtitles.srt -c copy -c:s mov_text -metadata:s:s:0 language=eng output.mp4
```

### Add text overlay (drawtext filter)
```bash
# Static text
ffmpeg -i input.mp4 -vf "drawtext=text='Hello World':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=h-text_h-100" output.mp4

# Timestamp overlay
ffmpeg -i input.mp4 -vf "drawtext=text='%{pts\:hms}':fontsize=32:fontcolor=yellow:x=10:y=10" output.mp4

# Scrolling ticker
ffmpeg -i input.mp4 -vf "drawtext=text='Breaking News':fontsize=36:fontcolor=white:x=w-mod(t*100\,w+text_w):y=h-100" output.mp4
```

### Generate SRT from transcript text
```bash
# If you have transcript with timestamps, format as:
# 1
# 00:00:01,000 --> 00:00:04,000
# Hello, welcome to this video.
```

---

## Audio Operations

### Extract audio
```bash
ffmpeg -i input.mp4 -q:a 0 -map a output.mp3
ffmpeg -i input.mp4 -c:a flac -map a output.flac  # Lossless
ffmpeg -i input.mp4 -c:a pcm_s16le -map a output.wav  # WAV
```

### Replace audio track
```bash
ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 -shortest output.mp4
```

### Mix audio tracks (voiceover + background music)
```bash
# Voice at full volume, music at 30%
ffmpeg -i video.mp4 -i background_music.mp3 -filter_complex \
  "[0:a]volume=1.0[a0];[1:a]volume=0.3[a1];[a0][a1]amix=inputs=2:duration=first[aout]" \
  -map 0:v -map "[aout]" -c:v copy output.mp4
```

### Audio ducking (music lowers when voice speaks)
```bash
ffmpeg -i voice.mp4 -i music.mp3 -filter_complex \
  "[1:a]volume=1.0[music];[0:a]asplit=2[voice][side]; \
   [side]asendcmd='0.0 sidechaincompress threshold=-30dB ratio=4,adelay=1|1[sc]; \
   [music][sc]amix=inputs=2:duration=first[aout]" \
  -map 0:v -map "[aout]" -c:v copy output.mp4
```

### Loudness normalization
```bash
# EBU R128 (broadcast standard, target -23 LUFS)
ffmpeg -i input.mp4 -af "loudnorm=I=-23:LRA=7:TP=-2" output.mp4

# Streaming standard (target -14 LUFS)
ffmpeg -i input.mp4 -af "loudnorm=I=-14:LRA=1:TP=-1" output.mp4
```

### Silence detection
```bash
ffmpeg -i input.mp4 -af "silencedetect=noise=-30dB:d=0.5" -f null - 2>&1 | grep -E "silence_(start|end)"
```

### Noise reduction
```bash
# Generate noise profile (from silent section)
ffmpeg -i input.mp4 -ss 00:00:00 -t 00:00:01 -af "afftdn=nn='t'|" -f null -

# Apply noise reduction
ffmpeg -i input.mp4 -af "afftdn=nf=-25" output.mp4
```

### Change audio pitch (without changing speed)
```bash
ffmpeg -i input.mp4 -af "asetrate=48000*0.9,aresample=48000,atempo=1.111" output.mp4  # Lower pitch
```

---

## Speed Changes

### Speed up (retain audio pitch)
```bash
# 2x speed
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]" -map "[v]" -map "[a]" output.mp4

# 4x speed (atempo max is 2.0, chain for higher)
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=0.25*PTS[v];[0:a]atempo=2.0,atempo=2.0[a]" -map "[v]" -map "[a]" output.mp4
```

### Slow motion
```bash
# 0.5x speed
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]" -map "[v]" -map "[a]" output.mp4

# 0.25x with motion interpolation (smooth slow-mo)
ffmpeg -i input.mp4 -vf "minterpolate=fps=60:mi_mode=mci" -filter_complex "[0:v]setpts=4.0*PTS[v]" -map "[v]" output.mp4
```

### Variable speed (accelerate/decelerate at specific points)
```bash
ffmpeg -i input.mp4 -filter_complex " \
  [0:v]trim=0:5,setpts=PTS-STARTPTS[v0]; \
  [0:v]trim=5:10,setpts=0.5*PTS-STARTPTS[v1]; \
  [0:v]trim=10:15,setpts=PTS-STARTPTS[v2]; \
  [v0][v1][v2]concat=n=3:v=1:a=0[outv]" \
  -map "[outv]" output.mp4
```

### Timelapse (extreme speedup)
```bash
# 30x speed
ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=1/30*PTS[v]" -an output.mp4
```

### Reverse video
```bash
ffmpeg -i input.mp4 -vf "reverse" -af "areverse" output.mp4
```

---

## Stabilization

### Two-pass stabilization
```bash
# Pass 1: Analyze motion
ffmpeg -i input.mp4 -vf "vidstabdetect=shakiness=10:accuracy=15:result=transforms.trf" -f null -

# Pass 2: Apply stabilization
ffmpeg -i input.mp4 -vf "vidstabtransform=smoothing=30:input=transforms.trf:zoom=1:optzoom=1" output.mp4
```

### One-pass stabilization (less accurate)
```bash
ffmpeg -i input.mp4 -vf "vidstabdetect=shakiness=5:accuracy=10,vidstabtransform=smoothing=20" output.mp4
```

### Stabilization parameters
```
shakiness: 1 (low) to 10 (very shaky)
accuracy:  1 (low) to 15 (high)
smoothing: 5 (low) to 50 (high) — higher = smoother but more crop
zoom:      how much to zoom in to hide borders (0 = no zoom, >0 = auto)
optzoom:   0 = no zoom, 1 = optimal zoom (default), 2 = fixed zoom
```

---

## Scene Detection

### Detect scene changes (output to console)
```bash
ffmpeg -i input.mp4 -filter:v "select='gt(scene,0.4)',showinfo" -f null - 2>&1 | grep pts_time
```

### Extract scene change frames as images
```bash
ffmpeg -i input.mp4 -vf "select='gt(scene,0.4)'" -vsync vfr -q:v 2 scene_%04d.jpg
```

### Scene detection threshold guide
```
0.1  = Very sensitive (detects gradual changes)
0.3  = Normal sensitivity
0.4  = Standard (good for talking heads)
0.6  = Low sensitivity (only hard cuts)
0.8  = Very low sensitivity
```

### Generate chapter markers from scenes
```bash
ffmpeg -i input.mp4 -vf "select='gt(scene,0.4)',showinfo" -f null - 2>&1 | \
  grep pts_time | awk '{print $NF}' | awk -F: '{printf "CHAPTER%.2d=%02d:%02d:%.2f\nCHAPTER%.2dNAME=Scene%.2d\n", NR,$1,$2,$3, NR, NR}' > chapters.txt
```

---

## Silence Removal

### Detect silence segments
```bash
ffmpeg -i input.mp4 -af "silencedetect=noise=-30dB:d=0.5" -f null - 2>&1
```

### Remove silence (automatically)
```bash
# Map silence detection output to trim
ffmpeg -i input.mp4 -af "silenceremove=start_periods=1:start_duration=1:start_threshold=-30dB:detection=peak" output.mp4
```

### Advanced silence removal with padding
```bash
# Remove silence >0.5s, keep 0.2s padding at each side of speech
ffmpeg -i input.mp4 -af "silenceremove=start_periods=1:start_duration=1:start_threshold=-30dB:stop_periods=-1:stop_duration=0.5:stop_threshold=-30dB:leave_silence=0.2" output.mp4
```

### Silence removal from audio track only
```bash
ffmpeg -i input.mp4 -af "silenceremove=1:0:-50dB" -c:v copy output.mp4
```

---

## Effects & Filters

### Film grain / noise
```bash
ffmpeg -i input.mp4 -vf "noise=alls=10:allf=t" output.mp4
```

### Blur
```bash
# Box blur
ffmpeg -i input.mp4 -vf "boxblur=10:5" output.mp4

# Gaussian blur
ffmpeg -i input.mp4 -vf "gblur=sigma=5" output.mp4
```

### Pixelate (face blur / censor)
```bash
ffmpeg -i input.mp4 -vf "geq=lum='p(X,Y)':cr='p(X,Y)-p(mod(X+10\,W),mod(Y+10\,H))':cb='p(X,Y)+p(mod(X+10\,W),mod(Y+10\,H))'" output.mp4
```

### Glow / bloom
```bash
ffmpeg -i input.mp4 -vf "gblur=sigma=20:steps=3,eq=brightness=0.2,format=yuv420p" output.mp4
```

### Chromatic aberration
```bash
ffmpeg -i input.mp4 -vf "eq=saturation=1.3:contrast=0.9,curves=r='0/0 0.25/0.1 0.75/0.9 1/1':b='0/0 0.25/0.3 0.75/0.7 1/1'" output.mp4
```

### Split screen / multi-view
```bash
# Side by side
ffmpeg -i left.mp4 -i right.mp4 -filter_complex \
  "[0:v]scale=960:540[l];[1:v]scale=960:540[r];[l][r]hstack=inputs=2" \
  -c:v libx264 output.mp4

# 2x2 grid
ffmpeg -i tl.mp4 -i tr.mp4 -i bl.mp4 -i br.mp4 -filter_complex \
  "[0:v]scale=960:540[a];[1:v]scale=960:540[b];[2:v]scale=960:540[c];[3:v]scale=960:540[d]; \
   [a][b]hstack=inputs=2[row1];[c][d]hstack=inputs=2[row2];[row1][row2]vstack=inputs=2" \
  -c:v libx264 output.mp4
```

### Ken Burns effect (slow zoom)
```bash
# Zoom in
ffmpeg -i input.mp4 -vf "zoompan=z='min(zoom+0.002,1.2)':d=150:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" output.mp4

# Pan across
ffmpeg -i input.mp4 -vf "zoompan=z=1.0:x='iw/2-(iw/zoom/2)+min(30,0.1*n)':y='ih/2-(ih/zoom/2)':d=150" output.mp4
```

### Mirror effect
```bash
ffmpeg -i input.mp4 -vf "hflip" output.mp4  # Horizontal flip
ffmpeg -i input.mp4 -vf "vflip" output.mp4  # Vertical flip
```

### Old film effect
```bash
ffmpeg -i input.mp4 -vf "colorchannelmixer=.393:.769:.189:.349:.686:.168:.272:.534:.131,vignette=PI/3,noise=alls=5:allf=t" output.mp4
```

---

## Format Conversion

### Common format conversions
```bash
# MP4 (H.264 / AAC) — most compatible
ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4

# WebM (VP9 / Opus) — web optimized
ffmpeg -i input.mp4 -c:v libvpx-vp9 -c:a libopus output.webm

# MKV (any codec)
ffmpeg -i input.mp4 -c copy output.mkv

# GIF
ffmpeg -i input.mp4 -vf "fps=10,scale=480:-1:flags=lanczos,palettegen=max_colors=256" palette.png
ffmpeg -i input.mp4 -i palette.png -lavfi "fps=10,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse" output.gif
```

### Platform-specific output
```bash
# YouTube (1080p)
ffmpeg -i input.mp4 -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" youtube.mp4

# TikTok / Reels / Shorts (9:16 vertical)
ffmpeg -i input.mp4 -vf "crop=ih*9/16:ih" -c:v libx264 -crf 22 tiktok.mp4

# Instagram feed (1:1 square)
ffmpeg -i input.mp4 -vf "crop=min(iw\,ih):min(iw\,ih)" -c:v libx264 -crf 22 square.mp4

# LinkedIn / Twitter (16:9)
ffmpeg -i input.mp4 -c:v libx264 -crf 22 -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" social.mp4
```

### Compression for web
```bash
# Light compression (CRF 23)
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -c:a aac -b:a 128k output_web.mp4

# Heavy compression (CRF 28)
ffmpeg -i input.mp4 -c:v libx264 -crf 28 -c:a aac -b:a 96k -vf "scale=1280:720" output_small.mp4

# Target file size (2MB example)
ffmpeg -i input.mp4 -c:v libx264 -b:v 500k -c:a aac -b:a 96k -vf "scale=854:480" output_2mb.mp4
```

---

## Compositing & Layout

### Picture-in-picture
```bash
# Small overlay in bottom-right corner
ffmpeg -i main.mp4 -i overlay.mp4 -filter_complex \
  "[1:v]scale=320:240[ov];[0:v][ov]overlay=main_w-overlay_w-20:main_h-overlay_h-20" \
  -c:a copy output.mp4
```

### Overlay with fade transition
```bash
ffmpeg -i main.mp4 -i overlay.mp4 -filter_complex \
  "[1:v]scale=320:240,fade=t=in:st=0:d=1:alpha=1[ov]; \
   [0:v][ov]overlay=W-w-20:H-h-20:enable='between(t,5,20)'" \
  -c:a copy output.mp4
```

### Chroma key (green screen)
```bash
ffmpeg -i foreground.mp4 -i background.mp4 -filter_complex \
  "[0:v]chromakey=color=0x00FF00:similarity=0.1:blend=0.1[fg]; \
   [bg][fg]overlay[outv]" \
  -map "[outv]" -map 0:a output.mp4
```

### Text with animated position
```bash
ffmpeg -i input.mp4 -vf "drawtext=text='Sliding Text':fontsize=48:fontcolor=white:x=w-mod(t*80\,w+text_w):y=h/2" output.mp4
```

---

## Quality & Compression

### CRF guide (recommended approach)
```
CRF 0  = Lossless (huge file)
CRF 18 = Visually lossless
CRF 22 = Good quality (default for many encoders)
CRF 23 = Standard compression
CRF 28 = Heavy compression (acceptable for web)
CRF 35 = Very low quality (small file)
```

### Two-pass VBR (for precise bitrate targeting)
```bash
# Pass 1
ffmpeg -i input.mp4 -c:v libx264 -b:v 4M -preset medium -pass 1 -f mp4 /dev/null

# Pass 2
ffmpeg -i input.mp4 -c:v libx264 -b:v 4M -preset medium -pass 2 -c:a aac -b:a 192k output.mp4
```

### Hardware acceleration (NVIDIA)
```bash
ffmpeg -i input.mp4 -c:v h264_nvenc -preset p4 -cq 23 -c:a aac output.mp4
```

### Hardware acceleration (Apple Silicon)
```bash
ffmpeg -i input.mp4 -c:v h264_videotoolbox -b:v 5M -c:a aac output.mp4
```

### Check encoding parameters of existing video
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,profile,level,bit_rate,width,height -of json input.mp4
```

---

## Batch Processing

### Process all MP4s in a directory
```bash
for f in *.mp4; do
  ffmpeg -i "$f" -vf "eq=brightness=0.05:contrast=1.1:saturation=1.2" -c:a copy "graded_$f"
done
```

### Resize all videos to 1080p
```bash
for f in *.mp4; do
  ffmpeg -i "$f" -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2" -c:a copy "1080p_$f"
done
```

### Extract audio from all videos
```bash
for f in *.mp4; do
  ffmpeg -i "$f" -q:a 0 -map a "${f%.mp4}.mp3"
done
```

### Parallel processing with xargs
```bash
ls *.mp4 | xargs -P 4 -I {} ffmpeg -i {} -c:v libx264 -crf 23 "compressed_{}"
```

---

## Best Practices

### Always probe first
Before any edit, run ffprobe to understand the source format. Codec, resolution, bitrate, and duration determine your approach.

### Stream copy vs re-encode
```
Stream copy (-c copy) = No quality loss, fast, but NOT frame-accurate
Re-encode             = Frame-accurate, can change codecs, quality loss on re-re-encode
```

Use stream copy for: simple trimming, format wrapping, concatenation of identical codecs
Use re-encode for: frame-accurate cuts, transitions, effects, codec changes, resizing

### Common mistakes
1. **Forgetting to re-encode after seeking**: `-ss` after `-i` with `-c copy` may not be accurate
2. **Not normalizing audio**: Quiet videos, loud ads — always normalize to -14 LUFS for web
3. **Mixing incompatible codecs in concat**: Use the concat FILTER (not demuxer) when codecs differ
4. **Over-compressing**: CRF 18-23 is the sweet spot; below 18 is overkill, above 28 is too lossy
5. **Ignoring keyframes**: Frame-accurate cuts need re-encoding or keyframe-seeking

### Preset speed guide
```
ultrafast → superfast → veryfast → faster → fast → medium → slow → slower → veryslow
(larger file)                                                (smaller file, slower)
```

### MCP vs Raw FFmpeg Decision
| Scenario | Use |
|----------|-----|
| Simple trim/merge/subtitle | MCP tool (1 call) |
| Complex filter chain | Raw FFmpeg (MCP may not have the exact tool) |
| Custom effect not in MCP | Raw FFmpeg |
| Batch processing | MCP or scripted FFmpeg |
| Learning/exploration | MCP tool (no flags to memorize) |
