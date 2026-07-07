"""Tests for kb/tools/auto_recover.py — bounded auto-recovery engine."""
from __future__ import annotations

import sys
import pathlib
import copy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from kb.tools.auto_recover import RecoveryEngine, RecoveryResult


def check(condition: bool, msg: str) -> None:
    if not condition:
        print(f"FAIL: {msg}")
        raise SystemExit(1)
    print(f"  ok: {msg}")


def test_engine_initial_state():
    e = RecoveryEngine(max_retries_per_step=2)
    check(e.max_retries == 2, "max_retries default")
    check(len(e.attempts) == 0, "no attempts yet")
    check(len(e.retry_counts) == 0, "no retries yet")


def test_can_recover_lufs():
    e = RecoveryEngine()
    gate = {"check": "lufs_within_1db", "details": {"measured": -15, "target": -14}}
    context = {
        "_step_results": [
            {"tool": "edit.loudnorm", "operation": "loudnorm"},
        ]
    }
    plan = e.can_recover(gate, context)
    check(plan is not None, "lufs_within_1db recoverable")
    check(plan["strategy"] == "loudnorm_remeasure", "strategy name")
    check("target_lufs" in plan["param_overrides"], "param override present")
    check("linear" in plan["param_overrides"], "linear override present")


def test_can_recover_missing_audio():
    e = RecoveryEngine()
    gate = {"check": "edit.verify", "details": {"error": "no audio stream"}}
    context = {"_last_output": "/tmp/test.mp4"}
    plan = e.can_recover(gate, context)
    check(plan is not None, "missing audio recoverable")
    check(plan["strategy"] == "add_silent_audio", "strategy name")


def test_can_recover_av_drift():
    e = RecoveryEngine()
    gate = {"check": "av_duration_drift", "details": {"audio_dur": 30.5, "video_dur": 31.2}}
    context = {
        "_step_results": [
            {"tool": "edit.render", "operation": "render"},
        ]
    }
    plan = e.can_recover(gate, context)
    check(plan is not None, "av drift recoverable")
    check(plan["strategy"] == "render_force_sync", "strategy name")
    check(plan["param_overrides"]["force_fps"] == 30, "force_fps set")
    check(plan["param_overrides"]["force_audio_rate"] == 48000, "force_audio_rate set")


def test_can_recover_subtitles():
    e = RecoveryEngine()
    gate = {"check": "edit.verify", "details": {"error": "no subtitle stream"}}
    context = {
        "_step_results": [
            {"tool": "edit.subtitles"},
            {"tool": "edit.render"},
        ]
    }
    plan = e.can_recover(gate, context)
    check(plan is not None, "missing subtitle recoverable")
    check(plan["strategy"] == "rerun_subtitles", "strategy name")


def test_can_recover_returns_none_for_unknown():
    e = RecoveryEngine()
    gate = {"check": "unknown_gate", "details": {}}
    plan = e.can_recover(gate, {})
    check(plan is None, "unknown gate → None")


def test_bounded_retries():
    e = RecoveryEngine(max_retries_per_step=1)
    gate = {"check": "lufs_within_1db", "details": {"measured": -15, "target": -14}}
    context = {
        "_step_results": [
            {"tool": "edit.loudnorm", "operation": "loudnorm"},
        ]
    }
    plan1 = e.can_recover(gate, context)
    check(plan1 is not None, "first retry allowed")
    e.retry_counts[0] = 1
    plan2 = e.can_recover(gate, context)
    check(plan2 is None, "second retry blocked (max 1)")


def test_record_attempt():
    e = RecoveryEngine()
    r = RecoveryResult(
        attempted=True,
        strategy_name="loudnorm_remeasure",
        step_index=0,
        param_overrides={"target_lufs": -14},
        retry_count=0,
        succeeded=False,
        detail="round 1",
    )
    e.record_attempt(r)
    check(len(e.attempts) == 1, "attempt recorded")
    check(e.retry_counts[0] == 1, "retry count incremented")


def test_summary():
    e = RecoveryEngine()
    r = RecoveryResult(True, "test", 0, {}, 0, False, "round 1")
    e.record_attempt(r)
    s = e.summary()
    check(len(s) == 1, "summary length")
    check(s[0]["strategy_name"] == "test", "summary content")
    check(s[0]["attempted"] is True, "attempted field preserved")


def test_can_recover_lufs_out_of_range():
    e = RecoveryEngine()
    gate = {"check": "lufs_out_of_range", "details": {"measured": -18, "target": -14}}
    context = {
        "_step_results": [
            {"tool": "edit.loudnorm", "operation": "loudnorm"},
        ]
    }
    plan = e.can_recover(gate, context)
    check(plan is not None, "lufs_out_of_range recoverable")
    check(plan["strategy"] == "loudnorm_remeasure", "strategy name")


def test_can_recover_av_drift_via_gate_matches():
    e = RecoveryEngine()
    gate = {"check": "edit.verify", "details": "av_duration_drift 0.7s"}
    context = {
        "_step_results": [
            {"operation": "render"},
        ]
    }
    plan = e.can_recover(gate, context)
    check(plan is not None, "drift via gate_matches recoverable")
    check(plan["strategy"] == "render_force_sync", "strategy name")


if __name__ == "__main__":
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_")):
        print(f"[{name}]")
        fn()
    print("\nAll auto_recover tests passed.")
