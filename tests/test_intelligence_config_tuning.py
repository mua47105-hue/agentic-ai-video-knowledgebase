"""Tests for autoresearch-tuned intelligence config values."""
from kb.tools.intelligence_config import DEFAULT, get_config


class TestTunedConfig:
    def test_co_occurrence_window_is_0_8(self):
        assert DEFAULT.co_occurrence_window == 0.8, f"Expected 0.8, got {DEFAULT.co_occurrence_window}"

    def test_motion_only_threshold_is_2_5(self):
        assert DEFAULT.motion_only_threshold == 2.5, f"Expected 2.5, got {DEFAULT.motion_only_threshold}"

    def test_dead_zone_threshold_is_0_20(self):
        assert DEFAULT.dead_zone_threshold == 0.20, f"Expected 0.20, got {DEFAULT.dead_zone_threshold}"

    def test_min_cut_score_is_0_55(self):
        assert DEFAULT.min_cut_score == 0.55, f"Expected 0.55, got {DEFAULT.min_cut_score}"

    def test_speech_cv_threshold_is_0_12(self):
        assert DEFAULT.speech_cv_threshold == 0.12, f"Expected 0.12, got {DEFAULT.speech_cv_threshold}"

    def test_hero_threshold_is_0_5(self):
        assert DEFAULT.hero_threshold == 0.5, f"Expected 0.5, got {DEFAULT.hero_threshold}"

    def test_motion_stride_is_3(self):
        assert DEFAULT.motion_sample_stride == 3, f"Expected 3, got {DEFAULT.motion_sample_stride}"

    def test_aesthetic_interval_is_6(self):
        assert DEFAULT.aesthetic_sample_interval == 6.0, f"Expected 6.0, got {DEFAULT.aesthetic_sample_interval}"

    def test_max_slowmo_is_3(self):
        assert DEFAULT.max_slowmo_per_minute == 3, f"Expected 3, got {DEFAULT.max_slowmo_per_minute}"

    def test_vehicle_action_config_exists(self):
        cfg = get_config("vehicle-action")
        assert cfg.max_slowmo_per_minute == 4, f"Expected 4, got {cfg.max_slowmo_per_minute}"

    def test_slowmo_co_occurrence_is_1_5(self):
        assert DEFAULT.slowmo_co_occurrence_window == 1.5, f"Expected 1.5, got {DEFAULT.slowmo_co_occurrence_window}"

    def test_face_stride_is_8(self):
        assert DEFAULT.face_sample_stride == 8, f"Expected 8, got {DEFAULT.face_sample_stride}"

    def test_beat_tolerance_is_0_15(self):
        assert DEFAULT.beat_tolerance == 0.15, f"Expected 0.15, got {DEFAULT.beat_tolerance}"

    def test_dead_zone_min_duration_is_2(self):
        assert DEFAULT.dead_zone_min_duration == 2, f"Expected 2, got {DEFAULT.dead_zone_min_duration}"

    def test_section_tolerance_is_1_5(self):
        assert DEFAULT.section_tolerance == 1.5, f"Expected 1.5, got {DEFAULT.section_tolerance}"
