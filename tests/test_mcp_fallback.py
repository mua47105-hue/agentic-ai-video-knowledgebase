"""Tests for the MCP/FFmpeg fallback system.

Verifies that core edit.* operations work both WITH mcp_video installed
and WITHOUT (via ffmpeg_adapter fallback).
"""
import pathlib
import pytest
import subprocess
import os


@pytest.fixture
def test_clip(short_clip):
    """Use the short_clip fixture from conftest."""
    return str(short_clip)


@pytest.fixture
def temp_output(tmp_path):
    """A temp output path."""
    return str(tmp_path / "output.mp4")


class TestMCPPath:
    """Tests that run with mcp_video installed (the normal path)."""

    def test_edit_info_returns_metadata(self, test_clip):
        """edit.info should return a dict with duration, width, height."""
        from kb.tools.unified_adapter import edit
        result = edit.info(input_path=test_clip)
        assert isinstance(result, dict)
        assert "duration" in result or "duration" in str(result)

    def test_edit_trim_produces_output(self, test_clip, temp_output):
        """edit.trim should produce a valid output file."""
        from kb.tools.unified_adapter import edit
        result = edit.trim(input=test_clip, start=0, duration=2, output=temp_output)
        assert isinstance(result, (dict, str))
        path = result.get("path", result) if isinstance(result, dict) else result
        assert os.path.exists(path), f"trim output not found: {path}"


class TestFFmpegFallback:
    """Tests that simulate mcp_video being unavailable (fallback path)."""

    def setup_method(self):
        """Patch _MCP_AVAILABLE to False to simulate no mcp_video."""
        import kb.tools._mcp_bridge as bridge
        self._original_available = bridge._MCP_AVAILABLE
        self._original_client = bridge._client
        bridge._MCP_AVAILABLE = False
        bridge._client = None

    def teardown_method(self):
        """Restore original MCP state."""
        import kb.tools._mcp_bridge as bridge
        bridge._MCP_AVAILABLE = self._original_available
        bridge._client = self._original_client

    def test_info_falls_back_to_ffmpeg(self, test_clip):
        """edit.info should fall back to ffmpeg_adapter.info() when MCP is unavailable."""
        from kb.tools.unified_adapter import edit
        result = edit.info(input_path=test_clip)
        assert isinstance(result, dict)
        # ffmpeg_adapter.info returns different key names but should have duration
        assert "duration" in result or "duration" in str(result)

    def test_trim_falls_back_to_ffmpeg(self, test_clip, temp_output):
        """edit.trim should fall back to ffmpeg_adapter.trim() when MCP is unavailable."""
        from kb.tools.unified_adapter import edit
        result = edit.trim(input=test_clip, start=0, duration=2, output=temp_output)
        assert isinstance(result, (dict, str))
        path = result.get("path", result) if isinstance(result, dict) else result
        assert os.path.exists(path), f"trim fallback output not found: {path}"

    def test_mcp_only_function_returns_error_not_crash(self, test_clip, temp_output):
        """Functions without FFmpeg fallback should return error dict, not crash."""
        from kb.tools.unified_adapter import edit
        # rotate has no ffmpeg fallback — should return {"error": ...}
        result = edit.rotate(video=test_clip, angle=90, output=temp_output)
        assert isinstance(result, dict)
        assert "error" in result or "path" in result  # either error or it worked
