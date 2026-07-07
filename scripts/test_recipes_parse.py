#!/usr/bin/env python3
"""
Regression test: every YAML recipe parses cleanly and passes validation.
No input file needed — only checks structural correctness.

Usage:
    python3 scripts/test_recipes_parse.py
"""
import sys, os, pathlib, yaml
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from _test_utils import check, run_main

REPO = pathlib.Path(__file__).resolve().parent.parent
RECIPES_DIR = REPO / "recipes"

REQUIRED_META = ["name", "version", "content_type", "target_platform", "output_lufs"]


def check_step(step, name, path):
    if isinstance(step, str):
        check(f"{name}: {path} is dict", False, f"got string: {step}")
        return
    if not isinstance(step, dict):
        check(f"{name}: {path} is dict", False, f"got {type(step).__name__}")
        return
    op = step.get("operation", "")
    check(f"{name}: {path} has operation", bool(op), f"missing or empty 'operation'")
    is_loop = op and op.startswith("for_each_")
    if not is_loop:
        check(f"{name}: {path} has tool", "tool" in step, f"missing 'tool' key")
    sub_steps = step.get("steps")
    if sub_steps:
        check(f"{name}: {path}.steps is list", isinstance(sub_steps, list), f"got {type(sub_steps).__name__}")
        if isinstance(sub_steps, list) and len(sub_steps):
            for j, s in enumerate(sub_steps):
                check_step(s, name, f"{path}.steps[{j}]")


def run_tests():
    if not RECIPES_DIR.exists():
        check("recipes dir exists", False)
        return

    recipe_files = sorted(RECIPES_DIR.glob("*.yaml"))
    check("found .yaml recipes", len(recipe_files) > 0, f"got {len(recipe_files)}")
    print(f"  {len(recipe_files)} recipe(s): {[f.name for f in recipe_files]}")

    for rp in recipe_files:
        name = rp.name
        try:
            text = rp.read_text(encoding="utf-8")
            data = yaml.safe_load(text)
            check(f"{name}: valid YAML", isinstance(data, dict), f"got {type(data).__name__}")
        except Exception as e:
            check(f"{name}: valid YAML", False, str(e))
            continue

        if not isinstance(data, dict):
            continue

        for key in REQUIRED_META:
            check(f"{name}: has '{key}'", key in data, f"missing required key: {key}")
        if isinstance(data.get("output_lufs"), str):
            check(f"{name}: output_lufs numeric", False, f"got string '{data['output_lufs']}'")

        steps = data.get("steps", [])
        check(f"{name}: steps is list", isinstance(steps, list), f"got {type(steps).__name__}")
        if isinstance(steps, list):
            check(f"{name}: at least 1 step", len(steps) > 0, "recipe has zero steps")
            for i, step in enumerate(steps):
                check_step(step, name, f"steps[{i}]")


if __name__ == "__main__":
    run_main(run_tests)
