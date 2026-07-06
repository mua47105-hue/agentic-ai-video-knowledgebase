---
title: Local LLM Setup for AI Video Editing
type: guide
tags: [llm, local, ollama, qwen, setup, guide]
created: 2026-07-06
updated: 2026-07-06
sources: []
related: [free-ai-video-editing-stack, ffmpeg-command-reference]
---

# Local LLM Setup for AI Video Editing

How to set up a fully local, free LLM that can drive AI video editing. No cloud, no API keys, no subscriptions.

## Why Local LLMs for Video Editing?

| Aspect | Local LLM | Cloud LLM |
|--------|-----------|-----------|
| Cost | $0 | Free tiers exist but limited |
| Privacy | 100% — video content never leaves your machine | Video frames may be uploaded |
| Speed | Depends on GPU | Usually faster |
| Quality | Good for simple edits | Better for complex workflows |
| FFmpeg accuracy | Qwen2.5-Coder: 88% (ELLMPEG) | Claude/GPT-4o: ~95% |

## Recommended Models

### Best: Qwen2.5-Coder (7B or 14B)

The ELLMPEG paper (arXiv:2602.00028) evaluated models specifically on FFmpeg command generation. Qwen2.5-Coder achieved **88% accuracy** with GPT-4o evaluation — the highest of any model tested under 70B parameters.

| Model | Size | RAM | Quality | FFmpeg Accuracy |
|-------|------|-----|---------|-----------------|
| Qwen2.5-Coder 7B | 4.1GB | 8GB+ | Good | 88% |
| Qwen2.5-Coder 14B | 8.2GB | 16GB+ | Very good | ~90% |
| Qwen2.5-Coder 32B | 18GB | 24GB+ | Excellent | ~92% |

### Alternative: Llama 3.2 (3B or 8B)

Good general-purpose model, slightly worse at FFmpeg but more widely used.

| Model | Size | RAM | Quality | Notes |
|-------|------|-----|---------|-------|
| Llama 3.2 3B | 1.7GB | 4GB+ | Acceptable | Fastest option, good for simple trim/cut |
| Llama 3.2 8B | 4.5GB | 8GB+ | Good | Best balance of speed and quality |

### Alternative: DeepSeek Coder V2

Competitive with Qwen on code tasks, slightly larger.

| Model | Size | RAM | Quality |
|-------|------|-----|---------|
| DeepSeek Coder V2 Lite 16B | 9GB | 16GB+ | Very good |

## Installation

### Step 1: Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Verify
ollama --version
```

### Step 2: Pull a model

```bash
# Recommended: Qwen2.5-Coder 7B (best FFmpeg accuracy)
ollama pull qwen2.5-coder:7b

# Smaller option: Llama 3.2 3B (fast, low resources)
ollama pull llama3.2:3b

# Larger option (if you have GPU with 16GB+)
ollama pull qwen2.5-coder:14b
```

### Step 3: Test the model

```bash
ollama run qwen2.5-coder:7b "Write an ffmpeg command to trim input.mp4 from 30s to 1m30s with re-encoding"
```

## Integrating with Video Editing Tools

### With an MCP server (recommended)

Use Ollama as the LLM backend for your AI agent (Claude Desktop, Cline, Cursor, or OpenCode). The MCP server provides the editing tools; Ollama provides the decision-making.

```json
// Claude Desktop config
{
  "mcpServers": {
    "mcp-video": {
      "command": "uvx",
      "args": ["mcp-video"]
    }
  }
}
```

Then in Claude Desktop, set the model provider to Ollama (Settings → Provider → Ollama).

### With CutAgent (declarative EDL)

```bash
# CutAgent uses local LLMs or APIs
pip install cutagent

# Use with Ollama
cutagent --llm ollama:qwen2.5-coder:7b edit "trim clip1.mp4 from 0:30 to 1:30"
```

### With wtffmpeg (REPL)

```bash
pip install wtffmpeg

# Use with Ollama
wtffmpeg --model ollama:qwen2.5-coder:7b
# Then type: trim first 30 seconds, add fade in, output as 1080p
```

## Performance Optimization

### Quantization levels (trade-off)
```bash
# Q4_K_M — Best balance (default, ~4.5GB for 7B)
ollama pull qwen2.5-coder:7b-q4_K_M

# Q8_0 — Higher quality, larger (~7.5GB for 7B)
ollama pull qwen2.5-coder:7b-q8_0

# Q3_K_S — Smaller, faster, lower quality (~3.5GB for 7B)
ollama pull qwen2.5-coder:7b-q3_K_S
```

### GPU acceleration

```bash
# NVIDIA CUDA (Ollama handles this automatically if CUDA is installed)
ollama run qwen2.5-coder:7b

# Apple Metal (automatic on Apple Silicon)
ollama run qwen2.5-coder:7b
```

### Running without GPU (CPU only)

7B models run at ~5-10 tokens/sec on modern CPUs. This is usable but slow for complex edits. The 3B models run at ~20-30 tokens/sec.

## RAG Setup for Better FFmpeg Accuracy

ELLMPEG paper achieved the 88% accuracy with RAG (Retrieval-Augmented Generation). Here's how to replicate it:

### Option 1: Simple prompt prefix (no extra tools)

```python
FFMPEG_CONTEXT = """
FFmpeg key patterns:
- Trim: -ss [start] -to [end] or -t [duration]
- Stream copy: -c copy (fast, no re-encode, not frame-accurate)
- Re-encode: -c:v libx264 -c:a aac (frame-accurate)
- Concat: Use concat demuxer (same codecs) or concat filter (different codecs)
- Crossfade: xfade=offset=...:duration=...:transition=...
- Subtitles: subtitles=file.srt or drawtext
- Speed: setpts for video, atempo for audio (max 2.0, chain for higher)
- Color: eq=brightness=...:contrast=...:saturation=...
- Stabilization: vidstabdetect + vidstabtransform (two-pass)
- Scale: scale=width:height or -vf "scale=-1:720" (auto width)
"""

prompt = f"{FFMPEG_CONTEXT}\n\nUser request: {user_request}"
```

### Option 2: Using llama-index or langchain

```bash
pip install llama-index llama-index-embeddings-huggingface
```

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Load FFmpeg documentation as documents
documents = SimpleDirectoryReader("ffmpeg_docs/").load_data()
embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
retriever = index.as_retriever(similarity_top_k=3)

# Retrieve relevant sections for each query
def get_ffmpeg_context(query):
    nodes = retriever.retrieve(query)
    return "\n".join([n.text for n in nodes])
```

### Option 3: Pre-built FFmpeg context file

Create `ffmpeg_context.md` for the LLM to reference:

```markdown
# FFmpeg Quick Reference

## Trimming
- Stream copy: `ffmpeg -i in -ss 10 -to 20 -c copy out` (fast, not frame-accurate)
- Re-encode: `ffmpeg -i in -ss 10 -to 20 -c:v libx264 -c:a aac out` (accurate)

## Key parameters
- crf: 18 (lossless-ish) to 28 (heavy compression), 23 default
- preset: ultrafast → medium → veryslow (smaller file, slower encode)
- -map 0:v = first video stream, -map 1:a:0 = first audio from second input
```

## Model Comparison Benchmarks

| Model | FFmpeg Acc. | Speed (tok/s) | RAM | GPU Required |
|-------|-------------|---------------|-----|-------------|
| Qwen2.5-Coder 0.5B | ~50% | 40+ | 512MB | No |
| Qwen2.5-Coder 1.5B | ~65% | 30+ | 1GB | No |
| Qwen2.5-Coder 3B | ~75% | 25+ | 2GB | No |
| Qwen2.5-Coder 7B | 88% | 15+ | 4GB | Optional |
| Qwen2.5-Coder 14B | ~90% | 10+ | 8GB | Recommended |
| Qwen2.5-Coder 32B | ~92% | 5+ | 18GB | Required |
| Llama 3.2 3B | ~60% | 30+ | 2GB | No |
| Llama 3.2 8B | ~75% | 15+ | 4.5GB | Optional |
| DeepSeek Coder V2 Lite 16B | ~85% | 8+ | 9GB | Recommended |

> Note: FFmpeg accuracy from ELLMPEG paper (qwen2.5-coder) or estimated based on code-generation benchmarks. Speed measured on RTX 4090.

## When to Use Cloud vs Local

| Task | Local LLM | Cloud LLM |
|------|-----------|-----------|
| Trim a clip | ✅ Excellent | ✅ Overkill |
| Merge clips | ✅ Excellent | ✅ Overkill |
| Add subtitles | ✅ Good | ✅ Better |
| Color grade | ⚠️ Decent | ✅ Excellent |
| Complex multi-step | ⚠️ Struggles | ✅ Best |
| Auto-repair failed output | ❌ Poor | ✅ Good |
| Scene analysis | ⚠️ Basic | ✅ Detailed |

**Rule of thumb:** Local LLMs handle ~80% of simple editing tasks. Cloud LLMs handle the remaining ~20% of complex, multi-step workflows. Use Qwen2.5-Coder 7B+ as your default, and fall back to a cloud LLM for difficult edits.

## Troubleshooting

### Model doesn't understand video editing
```bash
# Try a different model
ollama pull qwen2.5-coder:7b  # Better for FFmpeg tasks

# Or use a system prompt
ollama run qwen2.5-coder:7b --system "You are a video editing assistant. You write FFmpeg commands."
```

### Slow response times
```bash
# Use smaller model (3B instead of 7B)
ollama pull qwen2.5-coder:3b

# Check if GPU is being used
ollama ps  # Shows running models and their GPU usage

# Enable GPU (NVIDIA)
# Ensure nvidia-container-toolkit is installed
```

### Out of memory
```bash
# Use a lower quantization
ollama pull qwen2.5-coder:7b-q3_K_S  # 3.5GB instead of 4.1GB

# Or use a smaller model
ollama pull llama3.2:3b  # 1.7GB
```

### Model hallucinates FFmpeg flags
The ELLMPEG paper found this is the main failure mode. Mitigation:
1. Use RAG with real FFmpeg docs
2. Always validate commands with `ffmpeg` dry run before executing
3. Start with MCP tools (pre-validated) instead of raw FFmpeg
