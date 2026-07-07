"""
Recipe runner: execute YAML recipe packs against input video files.

Usage:
    python3 -m kb.tools.recipe_runner recipes/podcast-to-shorts.yaml input.mp4 --output shorts/
    python3 -m kb.tools.recipe_runner recipes/wedding-highlights.yaml input.mp4

Schema:
    Each recipe is a YAML file with:
      - metadata (name, version, content_type, target_platform, output_lufs)
      - steps: ordered list of operations
      - quality_gates: post-execution checks
      - for_each_segment: parallel loop construct (loop_var, source, steps)
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import typing as t
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


# ── Variable substitution ──

def _substitute(value: t.Any, context: dict) -> t.Any:
    if isinstance(value, str):
        def _replace_var(m: re.Match) -> str:
            path = m.group(1).strip()
            parts = path.split(".")
            cur = context
            for p in parts:
                if isinstance(cur, dict):
                    cur = cur.get(p, "")
                elif isinstance(cur, list):
                    try:
                        idx = int(p)
                        cur = cur[idx] if 0 <= idx < len(cur) else ""
                    except (ValueError, IndexError):
                        cur = ""
                else:
                    cur = ""
            return str(cur) if cur is not None else ""
        return re.sub(r"\$([\w.]+)", _replace_var, value)
    elif isinstance(value, dict):
        return {k: _substitute(v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [_substitute(v, context) for v in value]
    return value


# ── Tool resolver ──

_TOOL_CACHE: dict[str, t.Callable] = {}


def _resolve_tool(tool_name: str) -> t.Callable:
    if tool_name in _TOOL_CACHE:
        return _TOOL_CACHE[tool_name]

    if tool_name.startswith("edit."):
        from kb.tools.unified_adapter import edit
        fn = getattr(edit, tool_name[5:], None)
    elif tool_name.startswith("music."):
        from kb.tools.unified_adapter import music
        fn = getattr(music, tool_name[6:], None)
    elif tool_name == "recipe.find_engaging_segments":
        fn = _find_engaging_segments
    elif tool_name == "recipe.find_key_moments":
        fn = _find_key_moments
    elif tool_name == "recipe.find_action_moments":
        fn = _find_action_moments
    elif tool_name == "recipe.segment_by_topic":
        fn = _segment_by_topic
    elif tool_name == "recipe.find_best_shots":
        fn = _find_best_shots
    elif tool_name == "recipe.speed_ramp":
        fn = _speed_ramp
    else:
        raise ValueError(f"unknown tool: {tool_name}")

    _TOOL_CACHE[tool_name] = fn
    return fn


def _call_tool(tool_name: str, params: dict) -> t.Any:
    fn = _resolve_tool(tool_name)
    try:
        return fn(**params)
    except TypeError as e:
        raise TypeError(f"tool {tool_name}({list(params)}): {e}")


# ── Built-in recipe tools ──

def _find_engaging_segments(
    transcript: dict,
    chapters: list[dict] | None = None,
    *,
    min_duration: float = 30,
    max_duration: float = 60,
    criteria: list[str] | None = None,
) -> list[dict]:
    segs = transcript.get("segments", [])
    if not segs:
        return [{"start": 0, "duration": max_duration, "label": "full"}]
    candidates: list[dict] = []
    for s in segs:
        dur = s.get("end", 0) - s.get("start", 0)
        if min_duration <= dur <= max_duration:
            text = s.get("text", "")
            score = len(text.strip().split())
            if text:
                candidates.append({
                    "start": s["start"],
                    "duration": dur,
                    "label": text[:60],
                    "score": score,
                })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:5] if candidates else [{"start": 0, "duration": max_duration, "label": "clip"}]


def _find_key_moments(
    transcript: dict,
    scenes: list[dict] | None = None,
    *,
    categories: list[str] | None = None,
    max_duration_per_moment: float = 45,
) -> list[dict]:
    if transcript:
        segs = transcript.get("segments", [])
        return [{"start": s["start"], "duration": min(s["end"] - s["start"], max_duration_per_moment), "label": s.get("text", "")[:40]} for s in segs[:10]]
    return [{"start": 0, "duration": max_duration_per_moment, "label": "moment"}]


def _find_action_moments(
    scenes: list[dict] | None = None,
    *,
    min_duration: float = 3,
    max_duration: float = 15,
    min_energy_threshold: float = 0.6,
) -> list[dict]:
    if not scenes:
        return [{"start": 0, "duration": max_duration, "label": "action"}]
    candidates = []
    for i, s in enumerate(scenes):
        t = s.get("timestamp", 0)
        dur = max_duration
        if i + 1 < len(scenes):
            dur = min(scenes[i + 1].get("timestamp", t + max_duration) - t, max_duration)
        if dur >= min_duration:
            candidates.append({"start": t, "duration": dur, "label": f"action_{i}"})
    return candidates[:15] if candidates else [{"start": 0, "duration": max_duration, "label": "action"}]


def _segment_by_topic(
    transcript: dict,
    *,
    min_segment_duration: float = 30,
    max_segment_duration: float = 180,
) -> list[dict]:
    segs = transcript.get("segments", [])
    if not segs:
        return [{"start": 0, "duration": max_segment_duration, "label": "full"}]
    chunks: list[dict] = []
    current_start = segs[0]["start"]
    current_text = ""
    for s in segs:
        dur = s["end"] - current_start
        if dur >= max_segment_duration:
            chunks.append({"start": current_start, "duration": dur, "label": current_text[:60]})
            current_start = s["start"]
            current_text = ""
        current_text += " " + s.get("text", "")
    if current_text:
        dur = segs[-1]["end"] - current_start
        if dur >= min_segment_duration:
            chunks.append({"start": current_start, "duration": dur, "label": current_text[:60]})
    return chunks if chunks else [{"start": 0, "duration": max_segment_duration, "label": "full"}]


def _find_best_shots(
    scenes: list[dict] | None = None,
    *,
    max_clips: int = 20,
    min_duration: float = 3,
    max_duration: float = 12,
) -> list[dict]:
    if not scenes:
        return [{"start": 0, "duration": max_duration, "label": "shot"}]
    candidates = []
    for i, s in enumerate(scenes):
        t = s.get("timestamp", 0)
        dur = max_duration
        if i + 1 < len(scenes):
            dur = min(scenes[i + 1].get("timestamp", t + max_duration) - t, max_duration)
        if dur >= min_duration:
            candidates.append({"start": t, "duration": dur, "label": f"shot_{i}"})
    return candidates[:max_clips] if candidates else [{"start": 0, "duration": max_duration, "label": "shot"}]


def _speed_ramp(
    input: str,
    output: str,
    *,
    pre_roll: float = 0.5,
    pre_speed: float = 0.5,
    impact_speed: float = 1.0,
    post_roll: float = 1.0,
    post_speed: float = 0.35,
) -> str:
    from kb.tools.ffmpeg_adapter import _run, _check_ffmpeg, _ensure_parent
    _check_ffmpeg()
    _ensure_parent(output)
    total = pre_roll + 0.5 + post_roll
    cmd = [
        "ffmpeg", "-i", input,
        "-filter_complex",
        (
            f"[0:v]trim=0:{pre_roll},setpts={1/pre_speed}*PTS[v0];"
            f"[0:v]trim={pre_roll}:{pre_roll+0.5},setpts={1/impact_speed}*PTS[v1];"
            f"[0:v]trim={pre_roll+0.5}:{total},setpts={1/post_speed}*PTS[v2];"
            f"[v0][v1][v2]concat=n=3:v=1:a=0[v];"
            f"[0:a]atrim=0:{pre_roll},atempo={pre_speed}[a0];"
            f"[0:a]atrim={pre_roll}:{pre_roll+0.5},atempo={impact_speed}[a1];"
            f"[0:a]atrim={pre_roll+0.5}:{total},atempo={post_speed}[a2];"
            f"[a0][a1][a2]concat=n=3:v=0:a=1[a]"
        ),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-c:a", "aac", output,
    ]
    _run(cmd, check=True)
    return output


# ── Quality gate runner ──

def _run_quality_gates(gates: list[dict], context: dict, output_path: str) -> list[dict]:
    results: list[dict] = []
    for gate in gates:
        check = gate.get("check", "")
        try:
            if check == "edit.verify":
                from kb.tools.unified_adapter import edit
                r = edit.verify(output_path)
                results.append({"check": check, "passed": r.get("ok", False), "details": r})
            elif check == "edit.quality_full_qc":
                from kb.tools.unified_adapter import edit
                r = edit.quality_full_qc(output_path)
                passed = r.get("file_integrity", False)
                results.append({"check": check, "passed": passed, "details": r})
            elif check == "lufs_within_1db":
                target = gate.get("target", -14)
                from kb.tools.unified_adapter import edit
                r = edit.quality_audio(output_path)
                lufs = r.get("lufs", 0)
                passed = abs(lufs - target) <= 1.0
                results.append({"check": check, "passed": passed, "details": {"measured": lufs, "target": target}})
            elif check == "duration_within":
                dmin = gate.get("min", 0)
                dmax = gate.get("max", 9999)
                from kb.tools.unified_adapter import edit
                r = edit.info(output_path)
                dur = r.get("duration", 0)
                passed = dmin <= dur <= dmax
                results.append({"check": check, "passed": passed, "details": {"duration": dur, "min": dmin, "max": dmax}})
            else:
                results.append({"check": check, "passed": False, "details": {"error": f"unknown gate: {check}"}})
        except Exception as e:
            results.append({"check": check, "passed": False, "details": {"error": str(e)}})
    return results


# ── Step executor ──

def _execute_step(step: dict, context: dict, input_path: str, output_dir: str) -> dict:
    op = step.get("operation", "unknown")
    tool = step.get("tool", "")
    params = _substitute(copy.deepcopy(step.get("params", {})), context)
    output_key = step.get("output", "")

    if op == "for_each_segment":
        return _execute_loop(step, context, input_path, output_dir)

    if op == "render":
        params.setdefault("output", "")
    if tool.startswith("edit."):
        params.setdefault("input", input_path)
        fn = tool[5:]
        from kb.tools.unified_adapter import edit
        caller = getattr(edit, fn, None)
        if caller is None:
            raise ValueError(f"unknown edit tool: {fn}")
        result = caller(**params)
        if isinstance(result, str):
            result = {"path": result}
    elif tool.startswith("music."):
        fn = tool[6:]
        from kb.tools.unified_adapter import music
        caller = getattr(music, fn, None)
        if caller is None:
            raise ValueError(f"unknown music tool: {fn}")
        result = caller(**params)
    elif tool.startswith("recipe."):
        result = _call_tool(tool, params)
    else:
        result = _call_tool(tool or op, params)

    step_result = {
        "operation": op,
        "tool": tool,
        "output_key": output_key,
        "result": result,
    }
    if output_key:
        context[output_key] = result
    return step_result


def _execute_loop(step: dict, context: dict, input_path: str, output_dir: str) -> dict:
    loop_var = step.get("loop_var", "item")
    source_key = step.get("source", "")
    items = context.get(source_key, context.get("segment_list", context.get("chapters", context.get("shots", []))))
    sub_steps = step.get("steps", [])
    parallel = step.get("parallel", True)
    results: list[dict] = []

    def _run_one(item: dict, idx: int) -> dict:
        ctx = {**context, loop_var: item}
        out = pathlib.Path(output_dir) / f"seg_{idx:04d}"
        out.mkdir(parents=True, exist_ok=True)
        for ss in sub_steps:
            _execute_step(ss, ctx, input_path, str(out))
        return ctx

    if parallel and len(items) > 1:
        with ThreadPoolExecutor(max_workers=min(len(items), 4)) as ex:
            futures = {ex.submit(_run_one, item, i): i for i, item in enumerate(items)}
            for f in as_completed(futures):
                try:
                    results.append(f.result())
                except Exception as e:
                    results.append({"error": str(e)})
    else:
        for i, item in enumerate(items):
            results.append(_run_one(item, i))

    return {"operation": "for_each_segment", "count": len(items), "results": results}


# ── Main runner ──

def run_recipe(
    recipe_path: str,
    input_path: str,
    *,
    output_dir: str = "",
) -> dict:
    if yaml is None:
        raise ImportError("PyYAML is required. Install: pip install pyyaml")

    with open(recipe_path) as f:
        recipe = yaml.safe_load(f)

    if not output_dir:
        stem = pathlib.Path(input_path).stem
        output_dir = f"./{stem}_{recipe.get('name', 'output')}"
    out_path = pathlib.Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    context: dict = {}
    step_results: list[dict] = []

    for i, step in enumerate(recipe.get("steps", [])):
        step_result = _execute_step(step, context, input_path, str(out_path))
        step["_index"] = i
        step_result["step_index"] = i
        step_results.append(step_result)

    final_output = str(out_path / "output.mp4")
    if os.path.exists(final_output):
        pass

    gates = recipe.get("quality_gates", [])
    quality_results = _run_quality_gates(gates, context, final_output) if gates else []

    manifest = {
        "recipe": recipe.get("name", "unknown"),
        "version": recipe.get("version", "1.0"),
        "input": input_path,
        "output_dir": str(out_path.resolve()),
        "steps_executed": len(step_results),
        "gates_passed": all(g.get("passed", False) for g in quality_results),
        "quality_gates": quality_results,
        "step_results": step_results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    manifest_path = out_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def cli() -> None:
    parser = argparse.ArgumentParser(description="Run a recipe pack on input video")
    parser.add_argument("recipe", help="Path to recipe YAML file")
    parser.add_argument("input", help="Path to input video file")
    parser.add_argument("--output", "-o", default="", help="Output directory")
    parser.add_argument("--list", action="store_true", help="List available recipes")
    args = parser.parse_args()

    if args.list:
        recipes_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "recipes"
        for f in sorted(recipes_dir.glob("*.yaml")):
            with open(f) as fh:
                r = yaml.safe_load(fh)
            print(f"  {f.name:<40s} {r.get('description', '')}")
        return

    manifest = run_recipe(args.recipe, args.input, output_dir=args.output)
    print(json.dumps(manifest, indent=2, default=str))


if __name__ == "__main__":
    cli()
