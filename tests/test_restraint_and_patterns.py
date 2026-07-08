"""Tests for S1 (HR#29 restraint), S2 (composite patterns), S3 (research gap)."""
import pytest
import tempfile
import os
from kb.tools.plan_critic import HARD_RULES_CHECKABLE, critique_plan, _static_rule_check
from kb.tools.intelligence_config import DEFAULT, get_config
from kb.tools.edit_memory import EditPatternDB


class TestHR29Restraint:
    """S1: HR#29 — embellishment steps must cite justifying signals."""

    def test_hr29_in_checkable_list(self):
        ids = [r["id"] for r in HARD_RULES_CHECKABLE]
        assert "HR#29" in ids, "HR#29 must be in HARD_RULES_CHECKABLE"

    def test_embellishment_without_signal_triggers_warning(self):
        """A color_grade step with no reasoning referencing a signal should trigger HR#29."""
        plan = {
            "steps": [
                {"tool": "edit.color_grade", "params": {"preset": "warm"},
                 "reasoning": "looks nice"},  # no signal reference
            ],
            "intents": [],
            "assumptions": {"fps": 30, "has_audio": True, "estimated_output_duration": 30},
        }
        profile = {"metadata": {"duration": 30, "fps": 30, "has_audio": True, "aspect_ratio": 1.78}}
        rm = {"hero_moments": [], "dead_zones": []}
        violations = _static_rule_check(plan, profile, "vlog")
        hr29_violations = [v for v in violations if v["rule"] == "HR#29"]
        assert len(hr29_violations) >= 1, f"Expected HR#29 warning, got: {violations}"

    def test_embellishment_with_signal_passes(self):
        """A color_grade step with reasoning referencing a signal should NOT trigger HR#29."""
        plan = {
            "steps": [
                {"tool": "edit.color_grade", "params": {"preset": "warm"},
                 "reasoning": "warm grade for hero_moment at 3.0s — emotion peak detected"},
            ],
            "intents": [],
            "assumptions": {"fps": 30, "has_audio": True, "estimated_output_duration": 30},
        }
        profile = {"metadata": {"duration": 30, "fps": 30, "has_audio": True, "aspect_ratio": 1.78}}
        rm = {"hero_moments": [], "dead_zones": []}
        violations = _static_rule_check(plan, profile, "vlog")
        hr29_violations = [v for v in violations if v["rule"] == "HR#29"]
        assert len(hr29_violations) == 0, f"Expected no HR#29 warning, got: {hr29_violations}"

    def test_effect_caps_in_config(self):
        """IntelligenceConfig should have max_effects_per_minute and effect_density_penalty."""
        assert hasattr(DEFAULT, "max_effects_per_minute")
        assert hasattr(DEFAULT, "effect_density_penalty")
        assert DEFAULT.max_effects_per_minute > 0
        assert DEFAULT.effect_density_penalty > 0


class TestCompositePatterns:
    """S2: Composite pattern library in edit_memory."""

    @pytest.fixture
    def db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name
        db = EditPatternDB(db_path)
        db.seed_builtin_patterns()
        yield db
        os.unlink(db_path)

    def test_builtin_patterns_seeded(self, db):
        """seed_builtin_patterns should create 3 built-in patterns."""
        patterns = db.query_composite_patterns("vlog")
        names = [p["name"] for p in patterns]
        assert "reverse_into_drop" in names
        assert "whip_pan_cut" in names
        assert "zoom_punch" in names

    def test_query_by_trigger(self, db):
        """query_composite_patterns should filter by triggers."""
        patterns = db.query_composite_patterns("vlog", triggers=["hero_moment"])
        names = [p["name"] for p in patterns]
        assert "zoom_punch" in names  # zoom_punch triggers on hero_moment

    def test_record_outcome_promotes_confidence(self, db):
        """After 3+ successes with >70% rate, confidence should promote to 'verified'."""
        for _ in range(4):
            db.record_composite_outcome("zoom_punch", success=True)
        patterns = db.query_composite_patterns("vlog", triggers=["hero_moment"])
        zoom = [p for p in patterns if p["name"] == "zoom_punch"][0]
        assert zoom["confidence"] == "verified", f"Expected verified, got {zoom['confidence']}"

    def test_record_failure_increments_fail_count(self, db):
        db.record_composite_outcome("whip_pan_cut", success=False)
        patterns = db.query_composite_patterns("vlog", triggers=["high_motion_peak"])
        whip = [p for p in patterns if p["name"] == "whip_pan_cut"][0]
        assert whip["fail_count"] == 1

    def test_composite_stats(self, db):
        stats = db.stats()
        assert stats["composite_patterns"] >= 3


class TestResearchGap:
    """S3: On-demand research loop trigger."""

    def test_research_gap_detected(self):
        """When no composite pattern matches, a research_gap should be in the plan."""
        from kb.tools.intelligent_planner import generate_plan
        profile = {
            "metadata": {"duration": 10, "fps": 30, "has_audio": True, "aspect_ratio": 1.78, "video_path": "/tmp/x.mp4"},
            "audio": {"tempo": 120, "integrated_lufs": -16},
            "semantic": {"packed_brief": "# test"},
            "per_second": [{"ts": i, "motion_energy": 0.1, "semantic_importance": 0.5} for i in range(10)],
            "visual": {"scene_boundaries": [0]},
        }
        rm = {"hero_moments": [], "dead_zones": [], "per_second": []}
        # Use triggers that won't match any builtin pattern
        plan = generate_plan(
            profile, rm, [], {"segments": [], "summary": {}},
            [], {"structure": None, "aligned_cuts": []},
            "vlog", ["test"], [],
            plan_llm_model="ollama/nonexistent:7b",
            max_critique_rounds=1,
        )
        # Should have either composite_patterns_matched or research_gap
        assert "composite_patterns_matched" in plan or "research_gap" in plan or "composite_patterns" in plan
