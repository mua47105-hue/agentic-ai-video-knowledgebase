"""
Bounded auto-recovery for recipe-runner quality-gate failures.

When a VERIFY gate fails, the RecoveryEngine consults RECOVERY_STRATEGIES
to decide whether the failure is auto-recoverable. If so, the runner re-executes
the offending step with adjusted parameters. Bounded: max 2 retries per step.

Wired into recipe_runner.run_recipe() after _run_quality_gates().
"""
from __future__ import annotations

import copy
import dataclasses
import typing as t
from collections import defaultdict


@dataclasses.dataclass
class RecoveryResult:
    attempted: bool
    strategy_name: str
    step_index: int
    param_overrides: dict
    retry_count: int
    succeeded: bool
    detail: str


def _recover_lufs(gate_result: dict, context: dict) -> t.Optional[dict]:
    details = gate_result.get("details", {})
    measured_lufs = details.get("measured_lufs") or details.get("measured")
    target_lufs = details.get("target_lufs") or details.get("target")
    if measured_lufs is None or target_lufs is None:
        return None
    delta = abs(float(measured_lufs) - float(target_lufs))
    if delta > 5.0:
        return None
    step_results = context.get("_step_results", [])
    for i, sr in reversed(list(enumerate(step_results))):
        if sr.get("tool", "").endswith("loudnorm") or sr.get("operation", "") == "loudnorm":
            return {
                "strategy": "loudnorm_remeasure",
                "step_index": i,
                "param_overrides": {
                    "target_lufs": target_lufs,
                    "measured_lufs": measured_lufs,
                    "linear": True,
                },
            }
    return None


def _recover_av_drift(gate_result: dict, context: dict) -> t.Optional[dict]:
    step_results = context.get("_step_results", [])
    for i, sr in reversed(list(enumerate(step_results))):
        if sr.get("operation") == "render" or sr.get("tool", "").endswith("render"):
            return {
                "strategy": "render_force_sync",
                "step_index": i,
                "param_overrides": {
                    "force_fps": 30,
                    "force_audio_rate": 48000,
                    "re_encode": True,
                },
            }
    return None


def _recover_missing_audio(gate_result: dict, context: dict) -> t.Optional[dict]:
    final_output = context.get("_last_output", "")
    if not final_output:
        return None
    return {
        "strategy": "add_silent_audio",
        "step_index": -1,
        "param_overrides": {
            "input": final_output,
            "silent_audio": True,
        },
    }


def _recover_missing_subtitles(gate_result: dict, context: dict) -> t.Optional[dict]:
    step_results = context.get("_step_results", [])
    for i, sr in enumerate(step_results):
        if "subtitle" in sr.get("tool", "").lower():
            return {
                "strategy": "rerun_subtitles",
                "step_index": i,
                "param_overrides": {},
            }
    return None


RECOVERY_STRATEGIES: dict[str, t.Callable] = {
    "lufs_out_of_range": _recover_lufs,
    "lufs_within_1db": _recover_lufs,
    "av_duration_drift": _recover_av_drift,
    "missing_audio_stream": _recover_missing_audio,
    "missing_subtitles": _recover_missing_subtitles,
}


class RecoveryEngine:
    def __init__(self, max_retries_per_step: int = 2):
        self.max_retries = max_retries_per_step
        self.retry_counts: dict[int, int] = defaultdict(int)
        self.attempts: list[RecoveryResult] = []

    def can_recover(self, gate_result: dict, context: dict) -> t.Optional[dict]:
        check_name = gate_result.get("check", "")
        for strategy_key, strategy_fn in RECOVERY_STRATEGIES.items():
            if strategy_key in check_name or self._gate_matches(check_name, strategy_key, gate_result):
                plan = strategy_fn(gate_result, context)
                if plan is None:
                    continue
                step_idx = plan["step_index"]
                if self.retry_counts[step_idx] >= self.max_retries:
                    return None
                return plan
        return None

    def _gate_matches(self, check_name: str, strategy_key: str, gate_result: dict) -> bool:
        details_str = str(gate_result.get("details", "")).lower()
        if strategy_key == "lufs_within_1db" and "lufs" in details_str:
            return True
        if strategy_key == "av_duration_drift" and ("drift" in details_str or "sync" in details_str):
            return True
        if strategy_key == "missing_audio_stream" and "no audio" in details_str:
            return True
        if strategy_key == "missing_subtitles" and "subtitle" in details_str:
            return True
        return False

    def record_attempt(self, result: RecoveryResult):
        self.attempts.append(result)
        if result.attempted:
            self.retry_counts[result.step_index] += 1

    def summary(self) -> list[dict]:
        return [dataclasses.asdict(a) for a in self.attempts]
