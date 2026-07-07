#!/usr/bin/env python3
"""
Verify unified adapter: 32 checks covering availability, routing, and signatures.
Run: python scripts/verify_unified_adapter.py
"""
import sys, inspect, os, json, tempfile, xml.etree.ElementTree as ET
sys.path.insert(0, '.')
from _test_utils import check, run_main

print("=" * 60)
print("Unified Adapter Verification Suite")
print("=" * 60)

def run_tests():
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
    non_callable = {'RENDER_PROFILES', 'COMPLIANCE_SPECS', 'mcp_available', 'edit', 'music', 'footage', 'sfx', 'vlm', 'PLATFORM_SPECS', 'PACING_PRESETS', 'REFRAME_AVAILABLE'}
    for name in ua.__all__:
        if name in non_callable:
            continue
        obj = getattr(ua, name)
        check(f"symbol callable: {name}", callable(obj))

    # 9. Recipe runner checks
    from kb.tools.recipe_runner import _substitute, _find_engaging_segments, _segment_by_topic, _find_best_shots
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

    # 13. Caption presets
    from kb.tools.caption_presets import caption_ass, text_subtitles_animated
    check("caption_ass callable", callable(caption_ass))
    check("text_subtitles_animated callable", callable(text_subtitles_animated))

    # 14. Word-level timestamps check (fixed: checks the function signature, not a tautology)
    from kb.tools.ffmpeg_adapter import transcribe
    sig = inspect.signature(transcribe)
    has_word_ts = "word_timestamps" in sig.parameters
    check("transcribe word_timestamps param", has_word_ts,
          f"params: {list(sig.parameters)}")

    # 15. Snap-to-beats
    from kb.tools.recipe_runner import snap_to_beats, remove_filler_words
    check("snap_to_beats callable", callable(snap_to_beats))
    _segs = [{"start": 5.0, "duration": 3.0}, {"start": 15.0, "duration": 4.0}]
    _beats = {"beats": [5.12, 8.0, 15.08, 19.0], "downbeats": [5.12, 15.08]}
    _snapped = snap_to_beats(_segs, _beats, snap_tolerance=0.15)
    check("snap_to_beats nudges first segment", _snapped[0]["start"] == 5.12)
    check("snap_to_beats nudges second segment", _snapped[1]["start"] == 15.08)
    check("remove_filler_words callable", callable(remove_filler_words))

    # 16. Smarter segment scoring
    from kb.tools.recipe_runner import _segment_score
    check("_segment_score callable", callable(_segment_score))
    _score = _segment_score("This is the best top secret ever", [])
    check("_segment_score returns > 0", _score > 0)

    # 17. Platform specs + pacing presets
    check("PLATFORM_SPECS in ua", hasattr(ua, 'PLATFORM_SPECS'))
    check("PACING_PRESETS in ua", hasattr(ua, 'PACING_PRESETS'))
    check("tiktok in PLATFORM_SPECS", "tiktok" in ua.PLATFORM_SPECS)
    check("punchy_shorts in PACING_PRESETS", "punchy_shorts" in ua.PACING_PRESETS)

    # 18. Smart reframe (gated — just check availability)
    check("REFRAME_AVAILABLE in ua", hasattr(ua, 'REFRAME_AVAILABLE'))
    check("smart_reframe in ua", hasattr(ua, 'smart_reframe'))

    # 19. Color grade preset expansion
    from kb.tools.ffmpeg_adapter import _COLOR_STYLES
    check("cinematic color preset exists", "cinematic" in _COLOR_STYLES)
    check("vlog color preset exists", "vlog" in _COLOR_STYLES)
    check("moody color preset exists", "moody" in _COLOR_STYLES)
    check("vibrant color preset exists", "vibrant" in _COLOR_STYLES)

    # 20. Shorts-punchy recipe exists
    check("shorts-punchy.yaml exists", os.path.exists("recipes/shorts-punchy.yaml"))


if __name__ == "__main__":
    run_main(run_tests)
