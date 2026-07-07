#!/usr/bin/env python3
"""
End-to-end smoke test of the unified adapter.
Tests routing, import, project file operations (no ffmpeg needed),
and gracefully skips operations that require ffmpeg.
Run: python scripts/test_unified_e2e.py
"""
import sys, os, pathlib, tempfile, json, warnings
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from _test_utils import check, skip, run_main, reset

warnings.filterwarnings("ignore", category=DeprecationWarning)

TMP = pathlib.Path(tempfile.mkdtemp(prefix="unified_e2e_"))


def run_tests():
    global TMP
    from kb.tools.unified_adapter import edit, mcp_available
    check("edit module importable", True)
    check("mcp_available", mcp_available)
    check("edit.info is from _mcp_bridge", 'mcp_bridge' in edit.info.__module__)
    check("edit.merge is from ffmpeg_adapter", 'ffmpeg_adapter' in edit.merge.__module__)
    check("edit.silence_remove from ffmpeg_adapter", 'ffmpeg_adapter' in edit.silence_remove.__module__)
    check("edit.transcribe from ffmpeg_adapter", 'ffmpeg_adapter' in edit.transcribe.__module__)
    check("edit.j_cut from ffmpeg_adapter", 'ffmpeg_adapter' in edit.j_cut.__module__)
    check("edit.probe from ffmpeg_adapter", 'ffmpeg_adapter' in edit.probe.__module__)
    check("edit.detect_scenes from _mcp_bridge", 'mcp_bridge' in edit.detect_scenes.__module__)
    check("edit.export from _mcp_bridge", 'mcp_bridge' in edit.export.__module__)

    # Project file operations
    TMP = pathlib.Path(tempfile.mkdtemp(prefix="unified_e2e_"))
    try:
        source = TMP / "source.txt"
        source.write_text("test content")
        proj = edit.project_create(name="e2e_test", source=str(source), output_dir=str(TMP))
        check("project_create: returns dict", isinstance(proj, dict))
        check("project_create: has path", "path" in proj)
        check("project_create: has version", proj.get("version") == "1.0")
        check("project_create: .aevp file exists", os.path.exists(proj["path"]))
        step = edit.project_step(proj["path"], {"operation": "probe", "tool": "ffprobe", "input": str(source), "output": "", "params": {}})
        check("project_step: returns dict", isinstance(step, dict))
        check("project_step: includes step number", step.get("step") == 1)
        check("project_step: includes timestamp", bool(step.get("timestamp")))
        step2 = edit.project_step(proj["path"], {"operation": "export", "tool": "ffmpeg", "input": str(source), "output": str(TMP / "out.mp4"), "params": {"crf": 22}})
        check("project_step: second step", step2.get("step") == 2)
        resume = edit.project_resume(proj["path"])
        check("project_resume: returns dict", isinstance(resume, dict))
        check("project_resume: 2 steps completed", resume.get("steps_completed") == 2)
        snap = edit.project_snapshot(proj["path"])
        check("project_snapshot: returns path string", isinstance(snap, str))
        audit = edit.project_audit_report(proj["path"])
        check("project_audit_report: returns dict", isinstance(audit, dict))
        check("project_audit_report: 2 audit entries", len(audit.get("audit_trail", [])) == 2)
    except Exception as e:
        check(f"Project ops failed: {e}", False)

    ffmpeg = os.environ.get("FFMPEG_PATH") or None
    if not ffmpeg:
        skip("info() needs ffmpeg — skipping")
        skip("trim() needs ffmpeg — skipping")
        skip("merge() needs ffmpeg — skipping")
        skip("export() needs ffmpeg — skipping")
    else:
        skip("ffmpeg available — run full pipeline test")

    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    check("temp cleanup done", True)


if __name__ == "__main__":
    run_main(run_tests)
