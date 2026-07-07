"""
Chronological audit log of every auto-decision a recipe run makes.

Captured decisions:
  - classify: content-type classification (Phase 3)
  - classify_warning: classification mismatch warning (Phase 3)
  - recover: auto-recovery attempt (Phase 3)
  - vlm_verify: VLM highlight verification (Phase 4)
  - music_rank: BPM/mood music re-ranking (Phase 4)
  - recipe_step: each step execution (for context)
  - gate_fail: each quality-gate failure
  - gate_pass: each quality-gate pass (optional, off by default)

The log is appended to the manifest as ``decision_log``.
"""
from __future__ import annotations

import dataclasses
import time
import typing as t


@dataclasses.dataclass
class Decision:
    timestamp: str
    type: str
    action: str
    input: t.Any = None
    output: t.Any = None
    reasoning: str = ""
    succeeded: bool = True


class DecisionLogger:
    def __init__(self):
        self.decisions: list[Decision] = []

    def log(
        self,
        type: str,
        action: str,
        input: t.Any = None,
        output: t.Any = None,
        reasoning: str = "",
        succeeded: bool = True,
    ) -> None:
        self.decisions.append(Decision(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            type=type,
            action=action,
            input=input,
            output=output,
            reasoning=reasoning,
            succeeded=succeeded,
        ))

    def as_list(self) -> list[dict]:
        return [dataclasses.asdict(d) for d in self.decisions]
