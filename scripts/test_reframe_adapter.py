#!/usr/bin/env python3
"""Test reframe_adapter — verify the Phase 1 fixes and graceful skip without ffmpeg."""
import subprocess, sys, pathlib, tempfile, shutil
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from _test_utils import check, run_main


def test_reframe_constant_name():
    from kb.tools import reframe_adapter
    check("REFRAME_ENABLED exists", hasattr(reframe_adapter, "REFRAME_ENABLED"))
    check("REFAME_ENABLED does NOT exist", not hasattr(reframe_adapter, "REFAME_ENABLED"))


def test_reframe_runs_on_synthetic():
    if not shutil.which("ffmpeg"):
        print("  SKIP: reframe: ffmpeg not available, skipping")
        return
    with tempfile.TemporaryDirectory() as d:
        src = pathlib.Path(d) / "in.mp4"
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc2=duration=3:size=1280x720:rate=30",
                        "-c:v", "libx264", str(src)], check=True, capture_output=True)
        out = pathlib.Path(d) / "out.mp4"
        from kb.tools.reframe_adapter import reframe
        try:
            reframe(str(src), str(out), target_ratio="9:16")
            check("reframe produced output", out.exists() and out.stat().st_size > 0)
        except Exception as e:
            check("reframe produced output", False, str(e))


def run_tests():
    print("=" * 60)
    print("reframe_adapter — Unit Tests")
    print("=" * 60)
    test_reframe_constant_name()
    test_reframe_runs_on_synthetic()


if __name__ == "__main__":
    run_main(run_tests)
