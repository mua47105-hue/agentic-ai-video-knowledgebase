#!/usr/bin/env python3
"""
Test faster-whisper integration through ffmpeg_adapter.
Generates a synthetic test clip, transcribes it, and verifies SRT+JSON output.

Usage:
    python scripts/test_transcribe.py [--model tiny]
"""
import sys, os, pathlib, tempfile, argparse, subprocess, json, warnings, shutil
warnings.filterwarnings("ignore", message=".*ffmpeg_adapter is deprecated.*", category=DeprecationWarning)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kb.tools import ffmpeg_adapter as edit
from _test_utils import check, summary

TMP = pathlib.Path(tempfile.mkdtemp(prefix="transcribe_test_"))

def _gen_speech_clip(path: str, text: str = "Hello world this is a test of the whisper transcription system"):
    espeak = shutil.which("espeak")
    wav_path = path + ".wav"
    if espeak:
        subprocess.check_call([espeak, "-w", wav_path, text], stdout=subprocess.DEVNULL)
    else:
        subprocess.check_call([
            "ffmpeg", "-f", "lavfi", "-i",
            "aevalsrc=sin(440*sin(2*PI*t)):d=4:c=1",
            "-acodec", "pcm_s16le", "-ar", "16000", wav_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call([
        "ffmpeg", "-f", "lavfi", "-i", f"color=c=black:s=640x360:r=10:d=4",
        "-i", wav_path, "-shortest", path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(wav_path):
        os.unlink(wav_path)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="tiny",
                        choices=["tiny", "base", "small", "medium", "large-v3"])
    args = parser.parse_args()

    clip = str(TMP / "speech.mp4")
    _gen_speech_clip(clip)

    srt_out = str(TMP / "out.srt")
    json_out = str(TMP / "out.json")

    print(f"Transcribing with model='{args.model}' ...")
    try:
        result = edit.transcribe(clip, model=args.model, output_srt=srt_out)
    except ImportError:
        print("FAIL: faster-whisper not installed: pip install faster-whisper")
        sys.exit(1)
    except RuntimeError as e:
        print(f"FAIL: {e}")
        sys.exit(1)

    with open(json_out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  Language: {result.get('language', '?')}")
    print(f"  Segments: {len(result.get('segments', []))}")
    print(f"  SRT size: {len(result.get('srt', ''))} chars")

    check("language detected", bool(result.get("language")))
    check("has segments", bool(result.get("segments")))
    check("SRT file created", os.path.exists(srt_out) and os.path.getsize(srt_out) > 0)

    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(summary())


if __name__ == "__main__":
    main()
