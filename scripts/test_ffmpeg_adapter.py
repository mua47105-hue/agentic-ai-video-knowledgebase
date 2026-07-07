#!/usr/bin/env python3
"""
End-to-end test of the ffmpeg_adapter pipeline:
  probe -> trim -> silence_remove -> color_grade -> loudnorm
  -> transcribe -> text_subtitles -> resize -> merge -> pip -> verify

Generates synthetic test media.  Run with 'python scripts/test_ffmpeg_adapter.py'.
"""
import sys, os, pathlib, shutil, tempfile, json, warnings, atexit
warnings.filterwarnings("ignore", message=".*ffmpeg_adapter is deprecated.*", category=DeprecationWarning)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kb.tools import ffmpeg_adapter as edit
from _test_utils import check, run_main

TMP = pathlib.Path(tempfile.mkdtemp(prefix="ffmpeg_test_"))


@atexit.register
def _cleanup():
    shutil.rmtree(TMP, ignore_errors=True)


def _gen_test_clip(name: str, duration: float = 3.0, color: str = "red",
                    resolution: str = "1280x720", rate: str = "30",
                    tone: str = "440") -> str:
    import subprocess
    path = str(TMP / name)
    cmd = ["ffmpeg", "-f", "lavfi", "-i",
           f"color=c={color}:s={resolution}:r={rate}:d={duration}",
           "-f", "lavfi", "-i", f"aevalsrc=sin({tone}):d={duration}",
           "-shortest", path]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return path


def test_pipeline():
    import subprocess
    print("=" * 60)
    print("ffmpeg_adapter E2E Pipeline Test")
    print("=" * 60)

    clip1 = _gen_test_clip("clip1.mp4", duration=3.0, color="red", tone="440")
    clip2 = _gen_test_clip("clip2.mp4", duration=3.0, color="blue", tone="660")

    info = edit.info(clip1)
    check("probe: info() returns dict", isinstance(info, dict))
    check("probe: has width", info.get("width") == 1280)

    trimmed = str(TMP / "trimmed.mp4")
    edit.trim(clip1, trimmed, duration="1.0", accurate=True)
    ti = edit.info(trimmed)
    check("trim: duration ~1s", abs(ti["duration"] - 1.0) < 0.1, f"got {ti['duration']}")

    silenced = str(TMP / "silenced.mp4")
    edit.silence_remove(clip1, silenced, threshold=-50)
    si = edit.info(silenced)
    check("silence_remove: duration sanity", si["duration"] > 0)

    graded = str(TMP / "graded.mp4")
    edit.color_grade(clip1, graded, style="warm")
    gi = edit.info(graded)
    check("color_grade: warm style", gi["duration"] > 0)

    normed = str(TMP / "loudnorm.mp4")
    edit.loudnorm(clip1, normed)
    ni = edit.info(normed)
    check("loudnorm: output valid", ni["duration"] > 0)

    sped = str(TMP / "sped.mp4")
    edit.speed(clip1, sped, factor=2.0)
    spi = edit.info(sped)
    check("speed 2x: duration halved", abs(spi["duration"] - 1.5) < 0.2, f"got {spi['duration']}")

    resized = str(TMP / "resized.mp4")
    edit.resize(clip1, resized, width=640)
    ri = edit.info(resized)
    check("resize: width=640", ri.get("width") == 640)

    merged = str(TMP / "merged.mp4")
    edit.merge([clip1, clip2], merged, transition="fade", transition_duration=0.5)
    mi = edit.info(merged)
    check("merge: duration covers both clips", mi["duration"] > 5.0)

    pipd = str(TMP / "pip.mp4")
    edit.pip(clip1, clip2, pipd)
    pi = edit.info(pipd)
    check("pip: output valid", pi["duration"] > 0)

    try:
        tr = edit.transcribe(clip1, model="base", output_srt=str(TMP / "subs.srt"))
        check("transcribe: got language", bool(tr.get("language")))
        check("transcribe: has segments", len(tr.get("segments", [])) > 0)
        check("transcribe: SRT file written", os.path.exists(str(TMP / "subs.srt")))
    except ImportError:
        print("  SKIP: transcribe: faster-whisper not installed, skipping")

    srt_path = str(TMP / "subs.srt")
    if os.path.exists(srt_path):
        subd = str(TMP / "subbed.mp4")
        edit.text_subtitles(clip1, subd, srt_path)
        sui = edit.info(subd)
        check("text_subtitles: output valid", sui["duration"] > 0)

    v = edit.verify(clip1)
    check("verify: ok", v.get("ok") is True)
    check("verify: has streams", len(v.get("streams", [])) > 0)

    scenes = edit.scene_detect(clip1)
    check("scene_detect: returns list", isinstance(scenes, list))

    stab = str(TMP / "stab.mp4")
    edit.stabilize(clip1, stab)
    sti = edit.info(stab)
    check("stabilize: output valid", sti["duration"] > 0)


if __name__ == "__main__":
    run_main(test_pipeline)
