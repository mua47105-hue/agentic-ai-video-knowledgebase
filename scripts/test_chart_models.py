#!/usr/bin/env python3
"""Test chart_models — deterministic generation. Gracefully skips without matplotlib."""
import sys, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from _test_utils import check, run_main


def test_chart_generates_png():
    try:
        import matplotlib  # noqa
    except ImportError:
        print("  SKIP: chart_models: matplotlib not installed, skipping")
        return
    import kb.tools.chart_models as cm
    with tempfile.TemporaryDirectory() as d:
        orig = cm.OUTPUT_DIR
        cm.OUTPUT_DIR = d
        try:
            cm.generate_chart()
            out_path = pathlib.Path(d) / "ai-video-models-2026.png"
            check("chart PNG exists", out_path.exists())
            if out_path.exists():
                check("chart PNG non-empty", out_path.stat().st_size > 0)
        finally:
            cm.OUTPUT_DIR = orig


def run_tests():
    print("=" * 60)
    print("chart_models — Unit Tests")
    print("=" * 60)
    test_chart_generates_png()


if __name__ == "__main__":
    run_main(run_tests)
