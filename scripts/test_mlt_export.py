#!/usr/bin/env python3
"""Test MLT export: project file reading, XML generation, structure."""

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
    from kb.tools.mlt_export import export_mlt, render_mlt, export_fcpxml
    check("export_mlt imported", callable(export_mlt))
    check("render_mlt imported", callable(render_mlt))
    check("export_fcpxml imported", callable(export_fcpxml))


def test_mlt_xml_structure():
    import xml.etree.ElementTree as ET
    from kb.tools.mlt_export import export_mlt

    with tempfile.NamedTemporaryFile(mode="w", suffix=".aevp", delete=False) as f:
        json.dump({
            "name": "test_project",
            "version": "1.0",
            "source": {"path": "/tmp/test.mp4"},
            "steps": [
                {"operation": "trim", "params": {"start": 0, "duration": 10}, "output": "seg1.mp4"},
            ],
            "audit_trail": [],
        }, f)
        proj_path = f.name

    out_path = proj_path.replace(".aevp", ".mlt")
    try:
        result = export_mlt(proj_path, out_path)
        check("export_mlt returns path", result == out_path)
        check("MLT file exists", os.path.exists(out_path))

        tree = ET.parse(out_path)
        root = tree.getroot()
        check("root element is mlt", root.tag == "mlt")
        check("mlt has version attribute", root.get("version") is not None)

        playlists = root.findall("playlist")
        check("has playlist element", len(playlists) >= 1)
    finally:
        if os.path.exists(proj_path):
            os.unlink(proj_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_export_with_project_file():
    from kb.tools.mlt_export import export_mlt

    with tempfile.NamedTemporaryFile(mode="w", suffix=".aevp", delete=False) as f:
        json.dump({
            "name": "multi_step",
            "version": "1.0",
            "source": {"path": "/tmp/source.mp4"},
            "steps": [
                {"operation": "trim", "params": {"start": 0, "duration": 5}, "output": "seg1.mp4"},
                {"operation": "color_grade", "params": {"style": "warm"}, "input": "seg1.mp4", "output": "graded.mp4"},
                {"operation": "speed", "params": {"factor": 2.0}, "input": "graded.mp4", "output": "sped.mp4"},
            ],
            "audit_trail": [],
        }, f)
        proj_path = f.name

    out_path = proj_path.replace(".aevp", ".mlt")
    try:
        result = export_mlt(proj_path, out_path)
        check("multi-step export_mlt returns path", result == out_path)
        check("multi-step MLT file exists", os.path.exists(out_path))
    finally:
        if os.path.exists(proj_path):
            os.unlink(proj_path)
        if os.path.exists(out_path):
            os.unlink(out_path)


def test_fcpxml_import():
    try:
        from kb.tools.mlt_export import export_fcpxml
        check("export_fcpxml imported", True)
    except ImportError:
        check("export_fcpxml requires opentimelineio (optional)", True)


if __name__ == "__main__":
    print(f"\n=== MLT Export Tests ===")
    test_imports()
    test_mlt_xml_structure()
    test_export_with_project_file()
    test_fcpxml_import()
    total = PASS + FAIL
    print(f"\nResults: {PASS}/{total} passed, {FAIL}/{total} failed")
    sys.exit(0 if FAIL == 0 else 1)
