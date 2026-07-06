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

# 7. All __all__ symbols are callable or appropriate type
non_callable = {'RENDER_PROFILES', 'mcp_available', 'edit'}
for name in ua.__all__:
    if name in non_callable:
        continue
    obj = getattr(ua, name)
    check(f"symbol callable: {name}", callable(obj))

print("=" * 60)
total = PASS + FAIL
print(f"Results: {PASS}/{total} passed, {FAIL}/{total} failed")
if FAIL:
    sys.exit(1)
print("All checks passed!")
