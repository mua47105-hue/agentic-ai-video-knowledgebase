"""
Visual Perception adapter (Qwen2.5-VL): enables AI agents to "see" video frames.

GATED — this adapter is OFF by default. It only activates when:
  1. Ollama is running with qwen2.5-vl:7b pulled
  2. The user explicitly enables VLM in project config or via env var

Usage:
    from kb.tools.vlm_adapter import vlm
    desc = vlm.describe_frame("video.mp4", 15.0)
    moments = vlm.find_moment("video.mp4", "the speaker smiles")
    verified = vlm.verify_claim("video.mp4", 30.0, "the speaker is wearing glasses")
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import subprocess
import tempfile
import time
import typing as t

_FFMPEG = "ffmpeg"

VLM_ENABLED_ENV = "VLM_ENABLED"
VLM_MODEL = "qwen2.5-vl:7b"
VLM_AVAILABLE: bool = False


def _check_vlm() -> bool:
    """Check if Ollama is running and the VLM model is available."""
    global VLM_AVAILABLE
    if not os.environ.get(VLM_ENABLED_ENV, "").lower() in ("1", "true", "yes"):
        VLM_AVAILABLE = False
        return False

    try:
        res = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if VLM_MODEL in res.stdout:
            VLM_AVAILABLE = True
            return True
        VLM_AVAILABLE = False
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        VLM_AVAILABLE = False
        return False


def _extract_frame(video: str, timestamp: float) -> str:
    """Extract a single frame from video as a JPEG in a temp file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp_path = tmp.name
    tmp.close()
    subprocess.run(
        [_FFMPEG, "-ss", str(timestamp), "-i", video, "-frames:v", "1",
         "-q:v", "2", tmp_path],
        capture_output=True, check=True,
    )
    return tmp_path


def _frame_to_base64(frame_path: str) -> str:
    with open(frame_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _ollama_vlm(image_b64: str, question: str, model: str = VLM_MODEL) -> str:
    """Send an image + question to Ollama VLM."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "data": f"data:image/jpeg;base64,{image_b64}"},
                    {"type": "text", "text": question},
                ],
            }
        ],
        "options": {"temperature": 0.0},
    }
    res = subprocess.run(
        ["ollama", "chat"],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=60,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Ollama error: {res.stderr}")

    data = json.loads(res.stdout)
    return data.get("message", {}).get("content", "")


# ═══════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════

def describe_frame(
    video: str,
    timestamp: float,
    *,
    question: str = "Describe what's visible in this frame in detail.",
    model: str = VLM_MODEL,
) -> str:
    """Extract a frame and ask a VLM to describe it.

    Requires: VLM_ENABLED=1 env var + Ollama running with qwen2.5-vl:7b.
    """
    if not _check_vlm():
        raise RuntimeError(
            "VLM is disabled. Set VLM_ENABLED=1 and ensure Ollama is running "
            "with qwen2.5-vl:7b pulled (ollama pull qwen2.5-vl:7b)"
        )

    frame_path = _extract_frame(video, timestamp)
    try:
        image_b64 = _frame_to_base64(frame_path)
        response = _ollama_vlm(image_b64, question, model)
        return response
    finally:
        if os.path.exists(frame_path):
            os.unlink(frame_path)


def describe_clip(
    video: str,
    *,
    start: float = 0.0,
    end: float | None = None,
    sample_fps: float = 1.0,
    question: str = "Summarize what happens in this clip.",
    model: str = VLM_MODEL,
) -> dict:
    """Sample frames from a clip and ask a VLM to summarize.

    Returns {summary, frame_descriptions: [{timestamp, description}]}
    """
    if not _check_vlm():
        raise RuntimeError("VLM is disabled. Set VLM_ENABLED=1")

    # Probe duration
    res = subprocess.run(
        [_FFMPEG, "-i", video],
        capture_output=True, text=True,
    )
    duration = end or 60.0
    for line in res.stderr.split("\n"):
        if "Duration" in line:
            import re
            m = re.search(r"(\d+):(\d+):(\d+)\.(\d+)", line)
            if m:
                duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))

    timestamps = []
    t = start
    while t < duration:
        timestamps.append(t)
        t += 1.0 / sample_fps

    frame_descriptions: list[dict] = []
    for ts in timestamps[:8]:
        try:
            desc = describe_frame(video, ts, question="Describe this frame briefly.", model=model)
            frame_descriptions.append({"timestamp": ts, "description": desc})
        except Exception as e:
            frame_descriptions.append({"timestamp": ts, "description": f"[error: {e}]"})

    summary = ""
    if frame_descriptions:
        combined = " ".join(f["description"] for f in frame_descriptions)
        summary_payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Here are frame descriptions from a video clip:\n\n{combined}\n\n"
                        f"Question: {question}\n\nProvide a concise summary."
                    ),
                }
            ],
            "options": {"temperature": 0.0},
        }
        res = subprocess.run(
            ["ollama", "chat"],
            input=json.dumps(summary_payload),
            capture_output=True, text=True, timeout=60,
        )
        if res.returncode == 0:
            summary = json.loads(res.stdout).get("message", {}).get("content", "")

    return {"summary": summary, "frame_descriptions": frame_descriptions}


def find_moment(
    video: str,
    query: str,
    *,
    sample_fps: float = 0.5,
    model: str = VLM_MODEL,
) -> list[dict]:
    """Find moments matching a natural-language query.

    Samples frames at sample_fps, asks VLM if each matches the query.
    Returns [{timestamp, confidence, frame_description}]
    """
    if not _check_vlm():
        raise RuntimeError("VLM is disabled. Set VLM_ENABLED=1")

    res = subprocess.run(
        [_FFMPEG, "-i", video],
        capture_output=True, text=True,
    )
    import re
    duration = 60.0
    for line in res.stderr.split("\n"):
        if "Duration" in line:
            m = re.search(r"(\d+):(\d+):(\d+)\.(\d+)", line)
            if m:
                duration = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))

    timestamps = []
    t = 0.0
    while t < duration:
        timestamps.append(t)
        t += 1.0 / sample_fps

    results: list[dict] = []
    for ts in timestamps[:20]:
        try:
            frame_path = _extract_frame(video, ts)
            image_b64 = _frame_to_base64(frame_path)
            os.unlink(frame_path)

            answer = _ollama_vlm(
                image_b64,
                f"Does this frame match the query '{query}'? Answer YES or NO with brief explanation.",
                model,
            )
            is_match = answer.strip().upper().startswith("YES")
            if is_match:
                results.append({
                    "timestamp": ts,
                    "confidence": 0.7,
                    "frame_description": answer,
                })
        except Exception:
            continue

    return results


def verify_claim(
    video: str,
    timestamp: float,
    claim: str,
    *,
    model: str = VLM_MODEL,
    samples: int = 3,
) -> dict:
    """Verify a VLM claim by re-checking nearby frames.

    Returns {verified: bool, confidence: float, evidence: [...]}
    """
    if not _check_vlm():
        raise RuntimeError("VLM is disabled. Set VLM_ENABLED=1")

    evidence: list[dict] = []
    half_window = max(0.5, samples * 0.5)
    check_times = [
        timestamp - half_window,
        timestamp,
        timestamp + half_window,
    ]

    for ct in check_times[:samples]:
        if ct < 0:
            continue
        try:
            frame_path = _extract_frame(video, ct)
            image_b64 = _frame_to_base64(frame_path)
            os.unlink(frame_path)

            answer = _ollama_vlm(
                image_b64,
                f"Verify this claim: '{claim}'. Answer ONLY: TRUE or FALSE.",
                model,
            )
            is_true = "TRUE" in answer.strip().upper()
            evidence.append({
                "timestamp": ct,
                "response": answer.strip(),
                "supports_claim": is_true,
            })
        except Exception as e:
            evidence.append({"timestamp": ct, "response": f"[error: {e}]", "supports_claim": False})

    true_count = sum(1 for e in evidence if e.get("supports_claim"))
    confidence = true_count / len(evidence) if evidence else 0.0

    return {
        "verified": confidence > 0.5,
        "confidence": round(confidence, 2),
        "evidence": evidence,
    }


class _VlmModule:
    """Convenience module: vlm.describe_frame(), vlm.find_moment(), etc."""

    def describe_frame(self, video: str, timestamp: float, **kwargs) -> str:
        return describe_frame(video, timestamp, **kwargs)

    def describe_clip(self, video: str, **kwargs) -> dict:
        return describe_clip(video, **kwargs)

    def find_moment(self, video: str, query: str, **kwargs) -> list[dict]:
        return find_moment(video, query, **kwargs)

    def verify_claim(self, video: str, timestamp: float, claim: str, **kwargs) -> dict:
        return verify_claim(video, timestamp, claim, **kwargs)

    @property
    def available(self) -> bool:
        return _check_vlm()


vlm = _VlmModule()
