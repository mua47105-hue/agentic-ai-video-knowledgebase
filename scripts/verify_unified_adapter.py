#!/usr/bin/env python3
"""
Verify unified adapter: 32 checks covering availability, routing, and signatures.
Run: python scripts/verify_unified_adapter.py
"""
import sys, inspect
sys.path.insert(0, '.')

PASS = 0
FAIL = 0

def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  {detail}")

print("=" * 60)
print("Unified Adapter Verification Suite")
print("=" * 60)

# 1. Import
import kb.tools.unified_adapter as ua
check("unified_adapter importable", True)

# 2. edit convenience module
check("edit module exists", hasattr(ua, 'edit'))
check("edit is ModuleType", isinstance(ua.edit, type(ua)))

# 3. Routing correctness (mcp_video for safe functions)
check("info from _mcp_bridge", 'mcp_bridge' in ua.info.__module__)
check("trim from _mcp_bridge", 'mcp_bridge' in ua.trim.__module__)
check("color_grade from _mcp_bridge", 'mcp_bridge' in ua.color_grade.__module__)
check("resize from _mcp_bridge", 'mcp_bridge' in ua.resize.__module__)
check("speed from _mcp_bridge", 'mcp_bridge' in ua.speed.__module__)
check("stabilize from _mcp_bridge", 'mcp_bridge' in ua.stabilize.__module__)
check("text_subtitles from _mcp_bridge", 'mcp_bridge' in ua.text_subtitles.__module__)
check("export from _mcp_bridge", 'mcp_bridge' in ua.export.__module__)
check("detect_scenes from _mcp_bridge", 'mcp_bridge' in ua.detect_scenes.__module__)
check("audio_waveform from _mcp_bridge", 'mcp_bridge' in ua.audio_waveform.__module__)

# 4. Routing correctness (ffmpeg_adapter for audited/unique)
check("merge from ffmpeg_adapter", 'ffmpeg_adapter' in ua.merge.__module__)
check("silence_remove from ffmpeg_adapter", 'ffmpeg_adapter' in ua.silence_remove.__module__)
check("transcribe from ffmpeg_adapter", 'ffmpeg_adapter' in ua.transcribe.__module__)
check("j_cut from ffmpeg_adapter", 'ffmpeg_adapter' in ua.j_cut.__module__)
check("l_cut from ffmpeg_adapter", 'ffmpeg_adapter' in ua.l_cut.__module__)
check("loudnorm from ffmpeg_adapter", 'ffmpeg_adapter' in ua.loudnorm.__module__)
check("probe from ffmpeg_adapter", 'ffmpeg_adapter' in ua.probe.__module__)
check("verify from ffmpeg_adapter", 'ffmpeg_adapter' in ua.verify.__module__)
check("render from ffmpeg_adapter", 'ffmpeg_adapter' in ua.render.__module__)
check("project_create from ffmpeg_adapter", 'ffmpeg_adapter' in ua.project_create.__module__)
check("quality_vmaf from ffmpeg_adapter", 'ffmpeg_adapter' in ua.quality_vmaf.__module__)
check("scope_waveform from ffmpeg_adapter", 'ffmpeg_adapter' in ua.scope_waveform.__module__)

# 5. mcp_available flag
check("mcp_available is True", ua.mcp_available is True)

# 6. edit.XXX works for each category
check("edit.info works", 'mcp_bridge' in ua.edit.info.__module__)
check("edit.merge works", 'ffmpeg_adapter' in ua.edit.merge.__module__)
check("edit.silence_remove works", 'ffmpeg_adapter' in ua.edit.silence_remove.__module__)
check("edit.j_cut works", 'ffmpeg_adapter' in ua.edit.j_cut.__module__)
check("edit.hyperframes_init works", hasattr(ua.edit, 'hyperframes_init'))

# 7. New module routing checks
check("compliance_report from compliance", 'compliance' in ua.compliance_report.__module__)
check("list_specs from compliance", 'compliance' in ua.list_specs.__module__)
check("export_mlt from mlt_export", 'mlt_export' in ua.export_mlt.__module__)
check("render_mlt from mlt_export", 'mlt_export' in ua.render_mlt.__module__)
check("run_recipe from recipe_runner", 'recipe_runner' in ua.run_recipe.__module__)
check("lut_list from content_adapter", 'content_adapter' in ua.lut_list.__module__)
check("footage module exists", hasattr(ua, 'footage'))
check("sfx module exists", hasattr(ua, 'sfx'))
check("vlm module exists", hasattr(ua, 'vlm'))
check("footage.search callable", callable(ua.footage.search))
check("sfx.search callable", callable(ua.sfx.search))
check("vlm.describe_frame callable", callable(ua.vlm.describe_frame))
check("vlm.find_moment callable", callable(ua.vlm.find_moment))
check("vlm.verify_claim callable", callable(ua.vlm.verify_claim))

# 8. All __all__ symbols are callable or appropriate type
non_callable = {'RENDER_PROFILES', 'COMPLIANCE_SPECS', 'mcp_available', 'edit', 'music', 'footage', 'sfx', 'vlm'}
for name in ua.__all__:
    if name in non_callable:
        continue
    obj = getattr(ua, name)
    check(f"symbol callable: {name}", callable(obj))

# 9. Recipe runner checks
from kb.tools.recipe_runner import _substitute, _find_engaging_segments, _segment_by_topic, _find_best_shots
import os
_recipe_dir = os.path.join(os.path.dirname(__file__), "..", "recipes")
for _r in ["podcast-to-shorts.yaml", "wedding-highlights.yaml",
           "sports-highlights.yaml", "documentary-assembly.yaml",
           "tutorial-editing.yaml", "vlog-assembly.yaml"]:
    check(f"recipe exists: {_r}", os.path.exists(os.path.join(_recipe_dir, _r)))

_context = {"segment": {"start": 10.0, "duration": 30.0}, "title": "test"}
check("recipe _substitute simple", _substitute("$segment.start", _context) == "10.0")
check("recipe _substitute nested", _substitute("$segment.duration", _context) == "30.0")
check("recipe _substitute dict", _substitute({"s": "$segment.start", "d": "$segment.duration"}, _context) == {"s": "10.0", "d": "30.0"})

_transcript = {"segments": [
    {"start": 0, "end": 35, "text": "hello world this is a test with enough words"},
    {"start": 35, "end": 75, "text": "more content here for the second segment"},
]}
check("_find_engaging_segments returns list", isinstance(_find_engaging_segments(_transcript), list))
check("_segment_by_topic returns list", isinstance(_segment_by_topic(_transcript), list))
check("_find_best_shots returns list", isinstance(_find_best_shots(max_clips=5), list))

# 10. Compliance reporter checks
from kb.tools.compliance import COMPLIANCE_SPECS, list_specs
check("COMPLIANCE_SPECS has 6 specs", len(COMPLIANCE_SPECS) == 6)
_specs = list_specs()
check("list_specs returns dict", isinstance(_specs, dict))
check("ebu_r128 in specs", "ebu_r128" in _specs)
check("netflix_sound_mix in specs", "netflix_sound_mix" in _specs)
check("youtube_streaming in specs", "youtube_streaming" in _specs)
check("tiktok_streaming in specs", "tiktok_streaming" in _specs)
check("ebu_r128 loudness -23", COMPLIANCE_SPECS["ebu_r128"]["loudness_lufs"] == -23.0)
check("youtube loudness -14", COMPLIANCE_SPECS["youtube_streaming"]["loudness_lufs"] == -14.0)
check("netflix has dialogue_lufs", "dialogue_lufs" in COMPLIANCE_SPECS["netflix_sound_mix"])

# 11. MLT export checks
from kb.tools.mlt_export import export_mlt, render_mlt, export_fcpxml
check("export_mlt callable", callable(export_mlt))
check("render_mlt callable", callable(render_mlt))
check("export_fcpxml callable", callable(export_fcpxml))
import json, tempfile, xml.etree.ElementTree as ET
with tempfile.NamedTemporaryFile(mode="w", suffix=".aevp", delete=False) as _f:
    json.dump({"name": "test", "version": "1.0", "source": {"path": "/tmp/test.mp4"},
               "steps": [{"operation": "trim", "params": {"start": 0, "duration": 10}, "output": "seg1.mp4"}],
               "audit_trail": []}, _f)
    _proj = _f.name
_out = _proj.replace(".aevp", ".mlt")
try:
    _mlt = export_mlt(_proj, _out)
    check("export_mlt returns path", _mlt == _out)
    check("MLT file exists", os.path.exists(_out))
    _root = ET.parse(_out).getroot()
    check("MLT root is <mlt>", _root.tag == "mlt")
    check("MLT has version", _root.get("version") is not None)
finally:
    for _p in (_proj, _out):
        if os.path.exists(_p):
            os.unlink(_p)

# 12. License sidecar sharing
from kb.tools.music_adapter import write_license_sidecar
check("write_license_sidecar callable", callable(write_license_sidecar))

print("=" * 60)
total = PASS + FAIL
print(f"Results: {PASS}/{total} passed, {FAIL}/{total} failed")
if FAIL:
    sys.exit(1)
print("All checks passed!")
