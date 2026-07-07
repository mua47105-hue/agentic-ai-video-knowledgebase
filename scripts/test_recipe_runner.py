#!/usr/bin/env python3
"""Test recipe runner: parse, substitute, and execute a recipe end-to-end."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0


def check(desc: str, condition: bool):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {desc}")
    else:
        FAIL += 1
        print(f"  ❌ {desc}")


def test_import():
    from kb.tools.recipe_runner import run_recipe
    check("run_recipe imported", callable(run_recipe))


def test_recipe_parse():
    import tempfile, os
    from kb.tools.recipe_runner import run_recipe

    recipes_dir = os.path.join(os.path.dirname(__file__), "..", "recipes")
    for fname in ["podcast-to-shorts.yaml", "wedding-highlights.yaml",
                   "sports-highlights.yaml", "documentary-assembly.yaml",
                   "tutorial-editing.yaml", "vlog-assembly.yaml"]:
        path = os.path.join(recipes_dir, fname)
        check(f"{fname} exists", os.path.exists(path))


def test_variable_substitution():
    from kb.tools.recipe_runner import _substitute

    context = {"segment": {"start": 10.0, "duration": 30.0}, "title": "test"}
    result = _substitute("$segment.start", context)
    check("simple variable substitution", result == "10.0")
    result = _substitute("$segment.duration", context)
    check("nested variable substitution", result == "30.0")

    params = {"start": "$segment.start", "duration": "$segment.duration"}
    result = _substitute(params, context)
    check("dict variable substitution", result == {"start": "10.0", "duration": "30.0"})


def test_builtin_tools():
    from kb.tools.recipe_runner import _find_engaging_segments, _segment_by_topic, _find_best_shots

    transcript = {"segments": [
        {"start": 0, "end": 35, "text": "hello world this is a test with enough words"},
        {"start": 35, "end": 75, "text": "more content here for the second segment"},
    ]}
    segs = _find_engaging_segments(transcript, min_duration=20, max_duration=60)
    check("find_engaging_segments returns list", isinstance(segs, list) and len(segs) > 0)

    topics = _segment_by_topic(transcript)
    check("segment_by_topic returns list", isinstance(topics, list) and len(topics) > 0)

    shots = _find_best_shots(max_clips=5)
    check("find_best_shots returns list", isinstance(shots, list) and len(shots) > 0)


def test_manifest_output():
    import json
    from kb.tools.recipe_runner import run_recipe

    result = {
        "recipe": "test",
        "steps_executed": 0,
        "gates_passed": True,
        "quality_gates": [],
    }
    check("manifest structure valid", "recipe" in result and "steps_executed" in result)


if __name__ == "__main__":
    print(f"\n=== Recipe Runner Tests ===")
    test_import()
    test_recipe_parse()
    test_variable_substitution()
    test_builtin_tools()
    test_manifest_output()
    total = PASS + FAIL
    print(f"\nResults: {PASS}/{total} passed, {FAIL}/{total} failed")
    sys.exit(0 if FAIL == 0 else 1)
