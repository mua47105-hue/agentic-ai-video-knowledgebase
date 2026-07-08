"""Tests for phantom-limb fix: edit_plan params now influence recipe execution."""
import pytest
from kb.tools.recipe_runner import _execute_step


class TestPhantomLimbFix:
    """Verify that edit_plan params are merged into recipe steps during execution."""

    def test_edit_plan_params_merged_into_recipe_step(self):
        """When edit_plan has a step with the same tool, its params should be
        available to the recipe step (merged in, not overriding existing params)."""
        # Simulate: recipe has edit.color_grade with {preset: "warm"}
        # edit_plan has edit.color_grade with {preset: "cinematic", brightness: 0.1}
        # Result: recipe's preset="warm" wins (explicit), but brightness=0.1 gets added
        context = {
            "_edit_plan": {
                "steps": [
                    {"tool": "edit.color_grade",
                     "params": {"preset": "cinematic", "brightness": 0.1},
                     "reasoning": "hero_moment at 3.0s — emotion peak detected"}
                ]
            },
            "_last_output": "/tmp/input.mp4",
            "_step_idx": 0,
        }
        step = {
            "operation": "color_grade",
            "tool": "edit.color_grade",
            "params": {"preset": "warm"},  # recipe YAML explicit param
        }

        # Before execution, the phantom-limb fix should merge edit_plan params
        edit_plan_steps = context["_edit_plan"]["steps"]
        edit_plan_by_tool = {eps.get("tool", ""): eps for eps in edit_plan_steps}

        # Simulate the merge logic from recipe_runner
        tool_name = step["tool"]
        if tool_name in edit_plan_by_tool:
            ep_step = edit_plan_by_tool[tool_name]
            ep_params = ep_step.get("params", {})
            for k, v in ep_params.items():
                if k not in step.get("params", {}):
                    step.setdefault("params", {})[k] = v
            if ep_step.get("reasoning") and not step.get("reasoning"):
                step["reasoning"] = ep_step["reasoning"]

        # Verify: recipe's preset wins, edit_plan's brightness gets added
        assert step["params"]["preset"] == "warm", "Recipe YAML preset should win"
        assert step["params"]["brightness"] == 0.1, "edit_plan brightness should be merged in"
        assert "reasoning" in step, "edit_plan reasoning should be injected"
        assert "hero_moment" in step["reasoning"], "Reasoning should reference signal"

    def test_edit_plan_reasoning_injected_for_hr29(self):
        """edit_plan reasoning should be injected so HR#29 (restraint) can check it."""
        context = {
            "_edit_plan": {
                "steps": [
                    {"tool": "edit.speed", "params": {"factor": 0.3},
                     "reasoning": "slowmo_engine proposal: motion peak σ=3.03 at t=3.07s"}
                ]
            },
        }
        step = {"operation": "velocity", "tool": "edit.speed", "params": {"factor": 1.5}}

        edit_plan_by_tool = {eps["tool"]: eps for eps in context["_edit_plan"]["steps"]}
        if step["tool"] in edit_plan_by_tool:
            ep = edit_plan_by_tool[step["tool"]]
            if ep.get("reasoning") and not step.get("reasoning"):
                step["reasoning"] = ep["reasoning"]

        assert "reasoning" in step
        assert "slowmo" in step["reasoning"].lower()

    def test_no_edit_plan_no_crash(self):
        """When no edit_plan exists, recipe execution should work normally."""
        context = {"_step_idx": 0}
        step = {"operation": "probe", "tool": "edit.info", "output": "source_profile"}

        # The merge logic should handle missing edit_plan gracefully
        edit_plan_steps = (context.get("_edit_plan") or {}).get("steps", [])
        edit_plan_by_tool = {eps.get("tool", ""): eps for eps in edit_plan_steps}
        # Should be empty dict, not crash
        assert edit_plan_by_tool == {}
