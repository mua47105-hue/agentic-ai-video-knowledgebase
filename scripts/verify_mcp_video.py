#!/usr/bin/env python3
"""
Verify mcp_video 1.5.1 capabilities.
28 checks: 12 safe, 4 buggy, 2 inferior, 10 availability.
Run: python scripts/verify_mcp_video.py
"""
import sys, inspect
sys.path.insert(0, '.')
from _test_utils import check, skip, run_main

print("=" * 60)
print("mcp_video 1.5.1 Verification Suite")
print("=" * 60)

def run_tests():
    try:
        from mcp_video import Client, models
        from mcp_video import __version__ as mcp_ver
        check("mcp_video importable", True)
        check(f"version {mcp_ver}", mcp_ver == "1.5.1", f"got {mcp_ver}")
    except ImportError as e:
        check("mcp_video importable", False, str(e))
        return

    c = Client()

    expected_methods = [
        'info', 'trim', 'merge', 'color_grade', 'export', 'normalize_audio',
        'audio_compose', 'detect_scenes', 'quality_check', 'analyze_video',
        'audio_waveform', 'repurpose', 'hls_segment', 'pipeline',
        'text_subtitles', 'layout_pip', 'speed', 'stabilize',
        'resize', 'crop', 'rotate', 'reverse', 'fade', 'blur', 'chroma_key',
        'watermark', 'overlay_video', 'layout_grid', 'split_screen',
        'extract_audio', 'extract_frame', 'export_frames', 'thumbnail',
        'storyboard', 'convert', 'subtitles', 'generate_subtitles',
        'subtitles_styled', 'add_text', 'text_animated', 'audio_effects',
        'audio_preset', 'audio_sequence', 'audio_spatial', 'audio_synthesize',
        'add_audio', 'add_generated_audio', 'effect_chromatic_aberration',
        'effect_glow', 'effect_noise', 'effect_scanlines', 'effect_vignette',
        'transition_glitch', 'transition_morph', 'transition_pixelate',
        'filter', 'auto_chapters', 'batch', 'preview', 'video_info_detailed',
        'inspect', 'read_metadata', 'write_metadata', 'extract_colors',
        'generate_palette', 'ai_scene_detect', 'ai_stem_separation',
        'ai_upscale', 'ai_color_grade', 'ai_remove_silence', 'ai_transcribe',
        'analyze_product', 'luma_key', 'shape_mask', 'apply_mask',
        'repurpose_plan', 'fix_design_issues', 'assert_quality',
        'compare_quality', 'design_quality_check', 'search_tools',
    ]
    for name in expected_methods:
        ok = hasattr(c, name) and callable(getattr(c, name))
        check(f"method: {name}", ok)

    model_types = ['VideoInfo', 'EditResult', 'SceneDetectionResult', 'WaveformResult',
                   'QualityMetricsResult', 'SubtitleResult', 'ThumbnailResult',
                   'StoryboardResult', 'ImageSequenceResult']
    for mt in model_types:
        check(f"model: {mt}", hasattr(models, mt))

    check("info returns VideoInfo",
          'VideoInfo' in str(inspect.signature(c.info).return_annotation))
    check("trim returns EditResult",
          'EditResult' in str(inspect.signature(c.trim).return_annotation))
    check("detect_scenes returns SceneDetectionResult",
          'SceneDetectionResult' in str(inspect.signature(c.detect_scenes).return_annotation))
    check("quality_check returns dict",
          'dict' in str(inspect.signature(c.quality_check).return_annotation))

    pipeline_sig = inspect.signature(c.pipeline)
    check("pipeline: steps param exists", 'steps' in pipeline_sig.parameters)

    check("BaseModel has model_dump", hasattr(models.VideoInfo, 'model_dump'))
    check("BaseModel has model_fields", hasattr(models.VideoInfo, 'model_fields'))


if __name__ == "__main__":
    run_main(run_tests)
