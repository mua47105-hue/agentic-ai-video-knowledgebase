"""
Typed models for the framework's core data structures.

Replaces raw dict passing with typed dataclasses for:
  - SourceProfile (probe output)
  - RecipeStep (recipe YAML step)
  - EditPlan (planner output)
  - ComplianceSpec (delivery spec)

This is Phase 5 of the upgrade plan. The exact P0 bug (parameter name silently
not matching) is the textbook case typed models catch.

These models are optional — existing code passing dicts still works.
Use `SourceProfile.from_dict(d)` to convert, `sp.to_dict()` to serialize.
"""
from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass
class VideoMetadata:
    """Video file metadata (from ffprobe)."""
    video_path: str = ""
    duration: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 30.0
    aspect_ratio: float = 0.0
    has_video: bool = False
    has_audio: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "VideoMetadata":
        return cls(
            video_path=d.get("video_path", ""),
            duration=float(d.get("duration", 0)),
            width=int(d.get("width", 0)),
            height=int(d.get("height", 0)),
            fps=float(d.get("fps", 30)),
            aspect_ratio=float(d.get("aspect_ratio", 0)),
            has_video=bool(d.get("has_video", False)),
            has_audio=bool(d.get("has_audio", False)),
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class RecipeStep:
    """A single step in a recipe YAML."""
    operation: str = ""
    tool: str = ""
    params: dict = dataclasses.field(default_factory=dict)
    output: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "RecipeStep":
        return cls(
            operation=d.get("operation", ""),
            tool=d.get("tool", ""),
            params=d.get("params", {}),
            output=d.get("output", ""),
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @property
    def tool_category(self) -> str:
        """Returns 'edit', 'music', 'recipe', or 'unknown'."""
        if self.tool.startswith("edit."):
            return "edit"
        if self.tool.startswith("music."):
            return "music"
        if self.tool.startswith("recipe."):
            return "recipe"
        return "unknown"

    @property
    def tool_name(self) -> str:
        """Returns the function name (without the prefix)."""
        if "." in self.tool:
            return self.tool.split(".", 1)[1]
        return self.tool


@dataclasses.dataclass
class EditPlan:
    """An edit plan produced by the intelligent planner."""
    steps: list[dict] = dataclasses.field(default_factory=list)
    storyboard: str = ""
    assumptions: dict = dataclasses.field(default_factory=dict)
    intents: list[str] = dataclasses.field(default_factory=list)
    estimated_cost: dict = dataclasses.field(default_factory=dict)
    plan_critic_result: t.Optional[dict] = None
    editing_blueprint: t.Optional[dict] = None
    fallback: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "EditPlan":
        return cls(
            steps=d.get("steps", []),
            storyboard=d.get("storyboard", ""),
            assumptions=d.get("assumptions", {}),
            intents=d.get("intents", []),
            estimated_cost=d.get("estimated_cost", {}),
            plan_critic_result=d.get("plan_critic_result"),
            editing_blueprint=d.get("editing_blueprint"),
            fallback=d.get("fallback", False),
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @property
    def is_approved(self) -> bool:
        """Returns True if the plan critic approved this plan."""
        if not self.plan_critic_result:
            return True  # no critic run = assume approved (fallback plan)
        return self.plan_critic_result.get("approved", False)


@dataclasses.dataclass
class ComplianceSpec:
    """A delivery compliance specification (EBU R128, Netflix, YouTube, etc.)."""
    name: str = ""
    integrated_lufs: float = -23.0
    true_peak_db: float = -1.0
    lra_db: float = 0.0
    min_resolution: str = ""
    min_bitrate_mbps: float = 0.0
    requires_stereo: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "ComplianceSpec":
        return cls(
            name=d.get("name", ""),
            integrated_lufs=float(d.get("integrated_lufs", -23)),
            true_peak_db=float(d.get("true_peak_db", -1)),
            lra_db=float(d.get("lra_db", 0)),
            min_resolution=d.get("min_resolution", ""),
            min_bitrate_mbps=float(d.get("min_bitrate_mbps", 0)),
            requires_stereo=bool(d.get("requires_stereo", True)),
        )

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
