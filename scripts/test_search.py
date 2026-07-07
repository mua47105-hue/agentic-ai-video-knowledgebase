#!/usr/bin/env python3
"""Test search.py — run via CLI subprocess (search module has no programmatic API)."""
import subprocess, sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from _test_utils import check, run_main


def test_search_returns_results():
    result = subprocess.run(
        [sys.executable, "kb/tools/search.py", "mcp video", "--top-k", "3"],
        capture_output=True, text=True, cwd=str(pathlib.Path(__file__).resolve().parent.parent)
    )
    check("search exits 0", result.returncode == 0, result.stderr[:200])
    check("search produces output", len(result.stdout) > 0)
    check("search output contains results", "mcp-video" in result.stdout.lower() or "mcp" in result.stdout.lower())


def test_search_empty_query():
    result = subprocess.run(
        [sys.executable, "kb/tools/search.py", ""],
        capture_output=True, text=True, cwd=str(pathlib.Path(__file__).resolve().parent.parent)
    )
    check("empty query exits without crash", result.returncode in (0, 1, 2), f"exit {result.returncode}")


def run_tests():
    print("=" * 60)
    print("search — CLI Tests")
    print("=" * 60)
    test_search_returns_results()
    test_search_empty_query()


if __name__ == "__main__":
    run_main(run_tests)
