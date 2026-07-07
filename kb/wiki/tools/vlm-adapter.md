---
title: VLM Adapter
type: entity
tags: [tool, vlm, visual, qwen, ollama, gated]
created: 2026-07-07
updated: 2026-07-07
related: [whisper-ecosystem, content-adapter]
---

# VLM Adapter

Visual perception via Qwen2.5-VL — enables AI agents to "see" video frames.

**GATED:** OFF by default. Only activates when `VLM_ENABLED=1` env var is set and `ollama pull qwen2.5-vl:7b` has been run.

## Location

`kb/tools/vlm_adapter.py`

## Usage

```python
from kb.tools.unified_adapter import vlm

# Describe a single frame
desc = vlm.describe_frame("video.mp4", 15.0)
# -> "A person standing in front of a whiteboard, gesturing with their right hand."

# Describe a clip by sampling frames
result = vlm.describe_clip("video.mp4", start=0, end=60, question="What happens?")
# result.summary, result.frame_descriptions

# Find a moment matching a natural language query
moments = vlm.find_moment("video.mp4", "the speaker smiles")
# -> [{timestamp: 12.5, confidence: 0.8, frame_description: ...}]

# Verify a VLM-driven claim
verification = vlm.verify_claim("video.mp4", 30.0, "the speaker is wearing glasses")
# -> {verified: true, confidence: 0.67, evidence: [...]}
```

## Activation

```bash
export VLM_ENABLED=1
ollama pull qwen2.5-vl:7b  # ~4.7GB download
```

## Requirements

- Ollama running with `qwen2.5-vl:7b` model
- ~4.4GB VRAM (7B Q4 quantized)
- Not installed by `setup.sh` — user-initiated only

## Limitations

- 7B model is not as accurate as larger models for fine-grained visual tasks
- Frame sampling is approximate; not all details will be caught
- VLM hallucination is possible — always use `verify_claim()` for critical decisions
- Verification threshold is 50% (majority vote across 3 frames)
