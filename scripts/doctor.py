#!/usr/bin/env python3
"""
AI Video Editing Stack — Doctor

Diagnoses every dependency, binary, and import the codebase needs.
Reports pass/fail per check with the exact install command for failures.

Usage:
    python3 scripts/doctor.py           # full check
    python3 scripts/doctor.py --quiet   # exit code only (0=healthy, 1=issues)
    python3 scripts/doctor.py --json    # machine-readable output
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
import dataclasses
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclasses.dataclass
class Check:
    name: str
    category: str  # "binary" | "python" | "kb_module" | "config"
    passed: bool
    detail: str = ""
    fix: str = ""


def check_binary(name: str, min_version: str = "", version_flag: str = "--version") -> Check:
    if not shutil.which(name):
        return Check(name, "binary", False, "not found on PATH",
                     f"Install {name}: see https://ffmpeg.org/download.html or your OS package manager")
    try:
        out = subprocess.run([name, version_flag], capture_output=True, text=True, timeout=10)
        version_str = (out.stdout + out.stderr).split("\n")[0]
        return Check(name, "binary", True, version_str)
    except Exception as e:
        return Check(name, "binary", False, f"found but unrunnable: {e}")


def check_python_module(modname: str, pip_name: str = "") -> Check:
    pip_name = pip_name or modname
    try:
        m = importlib.import_module(modname)
        ver = getattr(m, "__version__", "unknown")
        return Check(modname, "python", True, ver)
    except ImportError as e:
        return Check(modname, "python", False, str(e),
                     f"pip install {pip_name}")


def check_kb_module(relpath: str) -> Check:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        importlib.import_module(relpath)
        return Check(relpath, "kb_module", True, "importable")
    except Exception as e:
        return Check(relpath, "kb_module", False, str(e),
                     f"Check kb/tools/{relpath.split('.')[-1]}.py")


def run_all() -> list[Check]:
    checks: list[Check] = []

    # Binaries
    checks.append(check_binary("ffmpeg"))
    checks.append(check_binary("ffprobe"))
    checks.append(check_binary("uvx", version_flag="--version"))
    if shutil.which("ollama"):
        checks.append(check_binary("ollama"))

    # Core Python deps
    for mod, pip in [
        ("yaml", "pyyaml"), ("numpy", "numpy"), ("requests", "requests"),
        ("PIL", "pillow"), ("matplotlib", "matplotlib"),
    ]:
        checks.append(check_python_module(mod, pip))

    # Optional Python deps (per adapter)
    for mod, pip in [
        ("librosa", "librosa"), ("scipy", "scipy"), ("cv2", "opencv-python"),
        ("bs4", "beautifulsoup4"), ("opentimelineio", "opentimelineio"),
        ("sentence_transformers", "sentence-transformers"),
    ]:
        checks.append(check_python_module(mod, pip))

    # MCP + Whisper
    checks.append(check_python_module("mcp_video", "mcp-video"))
    checks.append(check_python_module("faster_whisper", "faster-whisper"))

    # Phase 6-9 probe + intelligence layer (all optional)
    for mod, pip in [
        ("av", "av"), ("pyscenedetect", "pyscenedetect"),
        ("silero_vad", "silero-vad"), ("demucs", "demucs"),
        ("speechbrain", "speechbrain"), ("easyocr", "easyocr"),
        ("litellm", "litellm"), ("mediapipe", "mediapipe"),
        ("clip", "open-clip-torch"), ("pyannote.audio", "pyannote.audio"),
    ]:
        checks.append(check_python_module(mod, pip))

    # KB modules
    for rel in [
        "kb.tools.recipe_runner", "kb.tools.unified_adapter", "kb.tools._mcp_bridge",
        "kb.tools.ffmpeg_adapter", "kb.tools.music_adapter", "kb.tools.content_adapter",
        "kb.tools.compliance", "kb.tools.mlt_export", "kb.tools.search",
        "kb.tools.chart_models", "kb.tools.reframe_adapter", "kb.tools.vlm_adapter",
        "kb.tools.caption_presets",
        # Phase 6-9 intelligence modules
        "kb.tools.probe", "kb.tools.probe_visual", "kb.tools.probe_audio",
        "kb.tools.probe_semantic", "kb.tools.timeline_view",
        "kb.tools.relevance_map", "kb.tools.cut_detector",
        "kb.tools.pacing_engine", "kb.tools.slowmo_engine", "kb.tools.music_sync",
        "kb.tools.plan_critic", "kb.tools.intelligent_planner",
        "kb.tools.hero_detector", "kb.tools.edit_memory", "kb.tools.reviewer",
    ]:
        checks.append(check_kb_module(rel))

    # Config: recipes dir exists and has 7 yaml files
    recipes_dir = REPO_ROOT / "recipes"
    recipe_count = len(list(recipes_dir.glob("*.yaml"))) if recipes_dir.exists() else 0
    checks.append(Check("recipes_dir", "config",
                        recipe_count >= 7,
                        f"{recipe_count} recipes found",
                        "Expected ≥7 YAML files in recipes/"))

    return checks


def print_report(checks: list[Check]) -> int:
    cats: dict[str, list[Check]] = {}
    for c in checks:
        cats.setdefault(c.category, []).append(c)

    print("=" * 60)
    print("AI Video Editing Stack — Doctor Report")
    print("=" * 60)

    failures = 0
    for cat, cat_checks in cats.items():
        print(f"\n── {cat.upper()} ──")
        for c in cat_checks:
            icon = "[PASS]" if c.passed else "[FAIL]"
            print(f"  {icon} {c.name:<35s} {c.detail}")
            if not c.passed and c.fix:
                print(f"        FIX: {c.fix}")
                failures += 1

    print("\n" + "=" * 60)
    total = len(checks)
    passed = total - failures
    print(f"Result: {passed}/{total} checks passed, {failures} failed")
    if failures == 0:
        print("Environment is healthy.")
    else:
        print(f"{failures} issue(s) need attention. Run the FIX commands above.")
    print("=" * 60)
    return 1 if failures else 0


def main():
    import argparse
    p = argparse.ArgumentParser(description="AI Video Editing Stack — environment doctor")
    p.add_argument("--quiet", action="store_true", help="exit code only, no output")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = p.parse_args()

    checks = run_all()

    if args.json:
        print(json.dumps([dataclasses.asdict(c) for c in checks], indent=2))
        return 0 if all(c.passed for c in checks) else 1

    if args.quiet:
        return 0 if all(c.passed for c in checks) else 1

    return print_report(checks)


if __name__ == "__main__":
    sys.exit(main())
