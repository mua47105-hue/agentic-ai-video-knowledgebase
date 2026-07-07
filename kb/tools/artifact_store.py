"""
Artifact Store (Phase 5 — Crayotter's artifact-grounded traceability).

Externalizes every phase's output as inspectable artifacts in the output dir,
so any editing run can be replayed, diagnosed, and audited. Crayotter pattern:
"every phase externalizes inspectable artifacts: coverage reports, multimodal
analyses, editing blueprints, tool calls, intermediate renders."

Artifacts saved per run:
  - source_profile.json   (M0 PROBE output)
  - relevance_map.json    (M1 RELEVANCE MAP output)
  - cut_points.json       (M1 cut detection output)
  - paced_plan.json       (M1+ pacing engine output)
  - slowmo_proposals.json (M1+ slow-mo engine output)
  - music_sync_plan.json  (M1+ music sync output)
  - hero_moments.json     (M1+ cross-modal hero detection output)
  - editing_blueprint.md  (M2 Editing Research pure-reasoning output, Crayotter)
  - edit_plan.json        (M2 PLAN output)
  - storyboard.md         (M2 storyboard artifact, Project Montage)
  - plan_critic.json      (M2.5 CRITIC output)
  - review.json           (M4 VERIFY output)
  - decision_log.json     (full decision log)
  - manifest.json         (final manifest, already exists)

Public surface:
  - ArtifactStore class (save(name, data), save_json(name, data), save_markdown(name, text), list())
"""
from __future__ import annotations

import json
import pathlib
import typing as t


class ArtifactStore:
    """Saves per-phase artifacts to the output dir for traceability."""

    def __init__(self, output_dir: str):
        self.dir = pathlib.Path(output_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._artifacts: list[str] = []

    def save_json(self, name: str, data: t.Any) -> str:
        """Save data as {name}.json. Returns path."""
        path = self.dir / f"{name}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        self._artifacts.append(f"{name}.json")
        return str(path)

    def save_markdown(self, name: str, text: str) -> str:
        """Save text as {name}.md. Returns path."""
        path = self.dir / f"{name}.md"
        with open(path, "w") as f:
            f.write(text)
        self._artifacts.append(f"{name}.md")
        return str(path)

    def save_text(self, name: str, text: str) -> str:
        """Save text as {name}.txt. Returns path."""
        path = self.dir / f"{name}.txt"
        with open(path, "w") as f:
            f.write(text)
        self._artifacts.append(f"{name}.txt")
        return str(path)

    def list(self) -> list[str]:
        """Return list of saved artifact filenames."""
        return sorted(self._artifacts)

    def summary(self) -> dict:
        """Return summary dict for manifest."""
        return {
            "output_dir": str(self.dir),
            "artifact_count": len(self._artifacts),
            "artifacts": self._artifacts,
        }
