#!/usr/bin/env python3
"""Test content_adapter — verify LUT list logic (no network needed)."""
import sys, os, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from _test_utils import check, run_main


def test_lut_list_structure():
    from kb.tools.content_adapter import lut_list
    result = lut_list()
    check("lut_list returns list", isinstance(result, list))
    if result and isinstance(result[0], dict) and "error" not in result[0]:
        check("lut_list items are dicts", True)
        r = result[0]
        check("lut item has name", "name" in r)
        check("lut item has path", "path" in r)
        check("lut item has format", "format" in r)
        check("lut item has size_bytes", "size_bytes" in r)


def test_lut_list_missing_dir():
    from kb.tools.content_adapter import lut_list
    result = lut_list()
    if result and "error" in result[0]:
        check("lut_list returns error when not downloaded", True)
        check("error mentions LUT pack", "LUT" in result[0]["error"], result[0]["error"])


def run_tests():
    print("=" * 60)
    print("content_adapter — Unit Tests")
    print("=" * 60)
    test_lut_list_structure()
    test_lut_list_missing_dir()


if __name__ == "__main__":
    run_main(run_tests)
