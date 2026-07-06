#!/usr/bin/env python3
"""
End-to-end test of the ffmpeg_adapter pipeline:
  probe → trim → silence_remove → color_grade → loudnorm
  → transcribe → text_subtitles → resize → merge → pip → verify

Generates synthetic test media.  Run with 'python scripts/test_ffmpeg_adapter.py'.
"""

import sys, os, pathlib, shutil, tempfile, json, warnings
# Suppress deprecation — this is the legacy test suite
warnings.filterwarnings("ignore", message=".*ffmpeg_adapter is deprecated.*", category=DeprecationWarning)
# Ensure ffmpeg_adapter importable even when running from repo root
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kb.tools import ffmpeg_adapter as edit

TMP = pathlib.Path(tempfile.mkdtemp(prefix="ffmpeg_test_"))
PASS = 0
FAIL = 0

def _gen_test_clip(name: str, duration: float = 3.0, color: str = "red",
                    resolution: str = "1280x720", rate: str = "30",
                    tone: str = "440") -> str:
    """Create a synthetic test video."""
    path = str(TMP / name)
    cmd = ["ffmpeg", "-f", "lavfi", "-i",
           f"color=c={color}:s={resolution}:r={rate}:d={duration}",
           "-f", "lavfi", "-i", f"aevalsrc=sin({tone}):d={duration}",
           "-shortest", path]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path

import subprocess as subprocess_module
subprocess = subprocess_module


def check(label: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  {detail}")


def test_pipeline():
    print("=" * 60)
    print("ffmpeg_adapter E2E Pipeline Test")
    print("=" * 60)

    # 1. Generate test clips
    clip1 = _gen_test_clip("clip1.mp4", duration=3.0, color="red", tone="440")
    clip2 = _gen_test_clip("clip2.mp4", duration=3.0, color="blue", tone="660")
    clip3 = _gen_test_clip("clip3.mp4", duration=3.0, color="green", tone="880")

    # 2. probe
    info = edit.info(clip1)
    check("probe: info() returns dict", isinstance(info, dict))
    check("probe: has width", info.get("width") == 1280)

    # 3. trim
    trimmed = str(TMP / "trimmed.mp4")
    edit.trim(clip1, trimmed, duration="1.0", accurate=True)
    ti = edit.info(trimmed)
    check("trim: duration ~1s", abs(ti["duration"] - 1.0) < 0.1, f"got {ti['duration']}")

    # 4. silence_remove (on tone it should remove near-nothing)
    silenced = str(TMP / "silenced.mp4")
    edit.silence_remove(clip1, silenced, threshold=-50)
    si = edit.info(silenced)
    check("silence_remove: duration sanity", si["duration"] > 0)

    # 5. color_grade
    graded = str(TMP / "graded.mp4")
    edit.color_grade(clip1, graded, style="warm")
    gi = edit.info(graded)
    check("color_grade: warm style", gi["duration"] > 0)

    # 6. loudnorm
    normed = str(TMP / "loudnorm.mp4")
    edit.loudnorm(clip1, normed)
    ni = edit.info(normed)
    check("loudnorm: output valid", ni["duration"] > 0)

    # 7. speed
    sped = str(TMP / "sped.mp4")
    edit.speed(clip1, sped, factor=2.0)
    spi = edit.info(sped)
    check("speed 2x: duration halved", abs(spi["duration"] - 1.5) < 0.2, f"got {spi['duration']}")

    # 8. resize
    resized = str(TMP / "resized.mp4")
    edit.resize(clip1, resized, width=640)
    ri = edit.info(resized)
    check("resize: width=640", ri.get("width") == 640)

    # 9. merge with xfade
    merged = str(TMP / "merged.mp4")
    edit.merge([clip1, clip2], merged, transition="fade", transition_duration=0.5)
    mi = edit.info(merged)
    check("merge: duration covers both clips", mi["duration"] > 5.0)

    # 10. pip
    pipd = str(TMP / "pip.mp4")
    edit.pip(clip1, clip2, pipd)
    pi = edit.info(pipd)
    check("pip: output valid", pi["duration"] > 0)

    # 11. transcribe (needs faster-whisper)
    try:
        tr = edit.transcribe(clip1, model="base", output_srt=str(TMP / "subs.srt"))
        check("transcribe: got language", bool(tr.get("language")))
        check("transcribe: has segments", len(tr.get("segments", [])) > 0)
        check("transcribe: SRT file written", os.path.exists(str(TMP / "subs.srt")))
    except ImportError:
        print("  ~ transcribe: faster-whisper not installed, skipping")

    # 12. subtitle burn (if SRT exists)
    srt_path = str(TMP / "subs.srt")
    if os.path.exists(srt_path):
        subd = str(TMP / "subbed.mp4")
        edit.text_subtitles(clip1, subd, srt_path)
        sui = edit.info(subd)
        check("text_subtitles: output valid", sui["duration"] > 0)

    # 13. verify
    v = edit.verify(clip1)
    check("verify: ok", v.get("ok") is True)
    check("verify: has streams", len(v.get("streams", [])) > 0)

    # 14. scene_detect
    scenes = edit.scene_detect(clip1)
    check("scene_detect: returns list", isinstance(scenes, list))

    # 15. stabilize
    stab = str(TMP / "stab.mp4")
    edit.stabilize(clip1, stab)
    sti = edit.info(stab)
    check("stabilize: output valid", sti["duration"] > 0)


    print("=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL}/{total} failed")
    print(f"Temp files: {TMP}")
    if FAIL:
        sys.exit(1)
    print("All tests passed!")


if __name__ == "__main__":
    test_pipeline()
