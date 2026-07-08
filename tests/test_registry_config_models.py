"""Tests for Phase 2+3+5: tool registry, intelligence config, typed models."""
import pytest
from kb.tools.tool_registry import TOOL_REGISTRY, tools_by_category, generate_tools_markdown
from kb.tools.intelligence_config import IntelligenceConfig, DEFAULT, get_config
from kb.tools.typed_models import VideoMetadata, RecipeStep, EditPlan, ComplianceSpec


class TestToolRegistry:
    def test_registry_has_entries(self):
        assert len(TOOL_REGISTRY) > 30, f"Expected 30+ tools, got {len(TOOL_REGISTRY)}"

    def test_tools_by_category(self):
        cats = tools_by_category()
        assert "core" in cats
        assert "color" in cats
        assert "subtitle" in cats
        assert len(cats) >= 6

    def test_generate_markdown(self):
        md = generate_tools_markdown()
        assert "# Tool Reference" in md
        assert "edit.trim" in md
        assert "## Core" in md

    def test_every_tool_has_summary(self):
        for t in TOOL_REGISTRY:
            assert t.summary, f"Tool {t.name} has empty summary"

    def test_core_tools_have_ffmpeg_fallback(self):
        """The 8 core operations should have FFmpeg fallbacks."""
        core = tools_by_category()["core"]
        with_fallback = [t for t in core if t.has_ffmpeg_fallback]
        assert len(with_fallback) >= 8, (
            f"Expected 8+ core tools with fallback, got {len(with_fallback)}"
        )


class TestIntelligenceConfig:
    def test_default_config(self):
        assert DEFAULT.hero_threshold == 0.6
        assert DEFAULT.co_occurrence_window == 1.0
        assert DEFAULT.motion_only_threshold == 3.0

    def test_get_config_per_content_type(self):
        social = get_config("social-short")
        assert social.max_slowmo_per_minute == 3

        cinematic = get_config("cinematic")
        assert cinematic.hero_threshold == 0.7

    def test_get_config_falls_back_to_default(self):
        vlog = get_config("vlog")
        assert vlog.hero_threshold == DEFAULT.hero_threshold

    def test_short_form_normalizes(self):
        """short_form should get the social-short config."""
        sf = get_config("short_form")
        assert sf.max_slowmo_per_minute == 3  # same as social-short


class TestTypedModels:
    def test_video_metadata_roundtrip(self):
        d = {"duration": 10.5, "width": 1920, "height": 1080, "fps": 30.0}
        vm = VideoMetadata.from_dict(d)
        assert vm.duration == 10.5
        assert vm.width == 1920
        d2 = vm.to_dict()
        assert d2["duration"] == 10.5

    def test_recipe_step_properties(self):
        step = RecipeStep(operation="trim", tool="edit.trim", params={"start": 5})
        assert step.tool_category == "edit"
        assert step.tool_name == "trim"

    def test_recipe_step_from_dict(self):
        d = {"operation": "probe", "tool": "edit.info", "output": "source_profile"}
        step = RecipeStep.from_dict(d)
        assert step.operation == "probe"
        assert step.output == "source_profile"

    def test_edit_plan_is_approved(self):
        plan = EditPlan(plan_critic_result={"approved": True})
        assert plan.is_approved is True

        plan2 = EditPlan(plan_critic_result={"approved": False})
        assert plan2.is_approved is False

        plan3 = EditPlan()  # no critic run
        assert plan3.is_approved is True  # fallback plans are assumed approved

    def test_compliance_spec(self):
        spec = ComplianceSpec(name="EBU R128", integrated_lufs=-23.0, true_peak_db=-1.0)
        assert spec.name == "EBU R128"
        d = spec.to_dict()
        assert d["integrated_lufs"] == -23.0


class TestValidateMode:
    """Tests for the --validate dry-run mode (Phase 0.4)."""

    def test_validate_valid_recipe(self):
        from kb.tools.recipe_runner import _validate_recipe
        errors = _validate_recipe("recipes/podcast-to-shorts.yaml")
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_validate_all_recipes(self):
        import pathlib
        from kb.tools.recipe_runner import _validate_recipe
        recipes_dir = pathlib.Path("recipes")
        for recipe in sorted(recipes_dir.glob("*.yaml")):
            errors = _validate_recipe(str(recipe))
            assert errors == [], f"{recipe.name} has errors: {errors}"
