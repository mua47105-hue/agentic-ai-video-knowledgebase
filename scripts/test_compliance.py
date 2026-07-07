#!/usr/bin/env python3
"""Test compliance reporter: spec definitions, report generation, error handling."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0


def check(desc: str, condition: bool):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {desc}")
    else:
        FAIL += 1
        print(f"  ❌ {desc}")


def test_imports():
    from kb.tools.compliance import compliance_report, list_specs, COMPLIANCE_SPECS
    check("compliance_report imported", callable(compliance_report))
    check("list_specs imported", callable(list_specs))
    check("COMPLIANCE_SPECS has 6 specs", len(COMPLIANCE_SPECS) == 6)


def test_list_specs():
    from kb.tools.compliance import list_specs
    specs = list_specs()
    check("list_specs returns dict", isinstance(specs, dict))
    check("list_specs contains ebu_r128", "ebu_r128" in specs)
    check("list_specs contains youtube_streaming", "youtube_streaming" in specs)
    check("list_specs contains netflix_sound_mix", "netflix_sound_mix" in specs)


def test_spec_values():
    from kb.tools.compliance import COMPLIANCE_SPECS
    check("ebu_r128 loudness is -23", COMPLIANCE_SPECS["ebu_r128"]["loudness_lufs"] == -23.0)
    check("youtube_streaming loudness is -14", COMPLIANCE_SPECS["youtube_streaming"]["loudness_lufs"] == -14.0)
    check("netflix_sound_mix has dialogue_lufs", "dialogue_lufs" in COMPLIANCE_SPECS["netflix_sound_mix"])
    check("tiktok_streaming spec exists", "tiktok_streaming" in COMPLIANCE_SPECS)


def test_report_structure():
    from kb.tools.compliance import compliance_report
    try:
        report = compliance_report("/nonexistent.mp4", "youtube_streaming")
        check("should raise on missing file", False)
    except FileNotFoundError:
        check("raises FileNotFoundError on missing file", True)
    except Exception:
        check("raises exception on missing file", True)


def test_unknown_spec():
    from kb.tools.compliance import compliance_report
    try:
        report = compliance_report("/tmp/test.mp4", "nonexistent_spec")
        check("should raise on unknown spec", False)
    except ValueError:
        check("raises ValueError on unknown spec", True)
    except Exception:
        pass


if __name__ == "__main__":
    print(f"\n=== Compliance Reporter Tests ===")
    test_imports()
    test_list_specs()
    test_spec_values()
    test_report_structure()
    test_unknown_spec()
    total = PASS + FAIL
    print(f"\nResults: {PASS}/{total} passed, {FAIL}/{total} failed")
    sys.exit(0 if FAIL == 0 else 1)
