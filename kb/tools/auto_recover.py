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

    # ── Phase 5 additions: AVE YAML retry_if gates + selective revision ──

    def evaluate_retry_gates(self, retry_gates: list[dict],
                             review_result: t.Optional[dict] = None,
                             quality_results: t.Optional[list[dict]] = None) -> list[dict]:
        """
        Evaluate AVE-style retry_if gates against the review/quality results.

        Each gate: {"metric": "overall"|"audio"|"visual_quality"|...,
                    "threshold": float, "max_retries": int, "feedback_target": "planner"|"editor"}

        Returns list of triggered gates (metric below threshold) that still have retries left.
        """
        triggered: list[dict] = []
        for gate in retry_gates:
            metric = gate.get("metric", "overall")
            threshold = gate.get("threshold", 0.65)
            max_retries = gate.get("max_retries", 2)

            # Get the metric value
            value = None
            if review_result and metric == "overall":
                value = review_result.get("overall", 0)
            elif review_result and metric == "vmaf":
                value = review_result.get("vmaf", 0)
                # VMAF threshold is inverted (higher = better, threshold is minimum)
                if value < threshold and self.retry_counts.get(-1, 0) < max_retries:
                    triggered.append({**gate, "actual_value": value, "direction": "below"})
                continue
            elif review_result:
                # Check dimension scores
                for score in review_result.get("scores", []):
                    if score.get("dimension") == metric:
                        value = score.get("score", 0)
                        break
            elif quality_results:
                # Check quality gate results
                for qg in quality_results:
                    if metric in qg.get("check", ""):
                        value = 1.0 if qg.get("passed") else 0.0
                        break

            if value is not None and value < threshold:
                gate_key = hash(f"{metric}_{gate.get('feedback_target', 'editor')}")
                if self.retry_counts.get(gate_key, 0) < max_retries:
                    triggered.append({**gate, "actual_value": value, "direction": "below"})

        return triggered

    def get_downstream_steps(self, failed_step_index: int, total_steps: int) -> list[int]:
        """
        Selective revision (Crayotter pattern): return indices of the failed step
        AND all steps downstream of it (higher indices that depend on its output).
        """
        # Simple heuristic: all steps after the failed one are downstream.
        # A more sophisticated version would trace the output→input dependency graph,
        # but for our linear pipeline, "all subsequent steps" is correct.
        return list(range(failed_step_index, total_steps))

    def selective_revision_plan(self, failed_step_index: int, total_steps: int,
                                param_overrides: t.Optional[dict] = None) -> dict:
        """
        Build a selective revision plan: redo the failed step + all downstream steps.
        Returns {"steps_to_redo": [int], "param_overrides": dict, "strategy": "selective_revision"}
        """
        downstream = self.get_downstream_steps(failed_step_index, total_steps)
        return {
            "strategy": "selective_revision",
            "failed_step": failed_step_index,
            "steps_to_redo": downstream,
            "param_overrides": param_overrides or {},
            "reasoning": f"selective revision: redo step {failed_step_index} + {len(downstream)-1} downstream steps (Crayotter pattern)",
        }


def parse_retry_if_from_yaml(recipe: dict) -> list[dict]:
    """
    Parse AVE-style retry_if gates from a recipe YAML.

    Recipe YAML format:
      retry_if:
        - metric: overall
          threshold: 0.65
          max_retries: 2
          feedback_target: planner
        - metric: vmaf
          threshold: 80
          max_retries: 1
          feedback_target: editor

    Returns list of gate dicts. Empty if no retry_if block.
    """
    retry_block = recipe.get("retry_if", [])
    if not isinstance(retry_block, list):
        return []
    gates: list[dict] = []
    for gate in retry_block:
        if isinstance(gate, dict) and "metric" in gate and "threshold" in gate:
            gates.append({
                "metric": gate["metric"],
                "threshold": float(gate["threshold"]),
                "max_retries": int(gate.get("max_retries", 2)),
                "feedback_target": gate.get("feedback_target", "editor"),
            })
    return gates
