#!/usr/bin/env python3
"""
End-to-end recipe runner test.

Generates synthetic clips, runs each recipe, asserts the manifest shows
successful execution. This is the test that would have caught every Phase 1 bug.

Usage:
    pytest scripts/test_recipes_e2e.py -v
    python3 scripts/test_recipes_e2e.py  # without pytest
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    import pytest
    HAVE_PYTEST = True
except ImportError:
    HAVE_PYTEST = False
    class _pytest:  # minimal shim
        @staticmethod
        def skip(reason):
            print(f"SKIP: {reason}")
            sys.exit(0)
        @staticmethod
        def main(args):
            print("pytest not installed — running in standalone mode")
            return _run_all()
    pytest = _pytest


def _ensure_clips(clip_dir: Path) -> Path:
    clip_dir.mkdir(parents=True, exist_ok=True)
    talking = clip_dir / "talking_head.mp4"
    if not talking.exists():
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts/make_synthetic_clip.py"),
             "talking_head", "--out", str(clip_dir)],
            check=True
        )
    return talking


def _run_recipe(recipe_name: str, input_path: Path, output_dir: Path) -> dict:
    recipe_path = REPO_ROOT / "recipes" / recipe_name
    result = subprocess.run(
        [sys.executable, "-m", "kb.tools.recipe_runner",
         str(recipe_path), str(input_path), "--output", str(output_dir)],
        capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT)
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"recipe {recipe_name} failed (exit {result.returncode}):\n"
            f"STDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
        )
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"recipe {recipe_name} did not write manifest.json")
    with open(manifest_path) as f:
        return json.load(f)


if HAVE_PYTEST:
    @pytest.fixture(scope="session")
    def test_clip():
        clip_dir = Path(tempfile.mkdtemp(prefix="recipe_test_"))
        return _ensure_clips(clip_dir)
else:
    test_clip = None


RECIPES = [
    "podcast-to-shorts.yaml",
    "documentary-assembly.yaml",
    "shorts-punchy.yaml",
    "wedding-highlights.yaml",
    "sports-highlights.yaml",
    "tutorial-editing.yaml",
    "vlog-assembly.yaml",
]


def _test_recipe_runs(recipe_name: str, input_path: Path):
    output_dir = Path(tempfile.mkdtemp(prefix=f"recipe_{recipe_name}_"))
    try:
        manifest = _run_recipe(recipe_name, input_path, output_dir)

        assert manifest["recipe"], f"{recipe_name}: manifest has no recipe name"
        assert manifest["steps_executed"] > 0, f"{recipe_name}: 0 steps executed"
        assert "quality_gates" in manifest, f"{recipe_name}: no quality_gates in manifest"

        output_mp4 = output_dir / "output.mp4"
        assert output_mp4.exists(), f"{recipe_name}: output.mp4 not written"
        assert output_mp4.stat().st_size > 1024, f"{recipe_name}: output.mp4 is <1KB (likely broken)"

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(output_mp4)],
            capture_output=True, text=True
        )
        if probe.returncode == 0 and probe.stdout.strip():
            duration = float(probe.stdout.strip())
            assert duration > 0, f"{recipe_name}: output duration is {duration}"

        print(f"  PASS: {recipe_name} — {manifest['steps_executed']} steps, "
              f"output {output_mp4.stat().st_size} bytes")

    finally:
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)


def _run_all():
    clip_dir = Path(tempfile.mkdtemp(prefix="recipe_test_"))
    clip = _ensure_clips(clip_dir)

    passed, failed = 0, 0
    for recipe in RECIPES:
        try:
            _test_recipe_runs(recipe, clip)
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  FAIL: {recipe} — {e}")

    print(f"\n{passed}/{passed+failed} recipes passed")
    return 1 if failed else 0


if HAVE_PYTEST:
    def _make_test(rn):
        def test_func(test_clip):
            _test_recipe_runs(rn, test_clip)
        test_func.__name__ = f"test_recipe_{rn.replace('.yaml','').replace('-','_')}"
        return test_func

    for _r in RECIPES:
        globals()[f"test_recipe_{_r.replace('.yaml','').replace('-','_')}"] = _make_test(_r)

    try:
        import mcp_video  # noqa
    except ImportError:
        pytest.skip("mcp_video not installed — recipe e2e tests require it", allow_module_level=True)


if __name__ == "__main__":
    if HAVE_PYTEST:
        sys.exit(pytest.main([__file__, "-v"]))
    else:
        sys.exit(_run_all())
