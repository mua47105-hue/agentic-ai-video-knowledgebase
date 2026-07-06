#!/usr/bin/env python3
"""
Test faster-whisper integration through ffmpeg_adapter.
Generates a synthetic test clip, transcribes it, and verifies SRT+JSON output.

Usage:
    python scripts/test_transcribe.py [--model tiny]
"""

import sys, os, pathlib, tempfile, argparse, subprocess, json, warnings
warnings.filterwarnings("ignore", message=".*ffmpeg_adapter is deprecated.*", category=DeprecationWarning)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from kb.tools import ffmpeg_adapter as edit

TMP = pathlib.Path(tempfile.mkdtemp(prefix="transcribe_test_"))

def _gen_speech_clip(path: str, text: str = "Hello world this is a test of the whisper transcription system"):
    """Generate a video with TTS audio using FFmpeg speech synth."""
    # Use FFmpeg's anullsrc + atempo trick or just use a simple tone
    # Better: use espeak if available, fall back to lavfi tone
    espeak = shutil.which("espeak")
    wav_path = path + ".wav"
    if espeak:
        subprocess.check_call([espeak, "-w", wav_path, text], stdout=subprocess.DEVNULL)
    else:
        # Fallback: generate a tone + silence pattern mimicking speech energy
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

import shutil as shutil_mod
shutil = shutil_mod


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
        print("✗ faster-whisper not installed: pip install faster-whisper")
        sys.exit(1)
    except RuntimeError as e:
        print(f"✗ {e}")
        sys.exit(1)

    # Save JSON
    with open(json_out, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  Language: {result.get('language', '?')}")
    print(f"  Segments: {len(result.get('segments', []))}")
    print(f"  SRT size: {len(result.get('srt', ''))} chars")
    print(f"  SRT file: {srt_out} ({os.path.getsize(srt_out)} bytes)")
    print(f"  JSON file: {json_out}")

    # Verify
    errors = []
    if not result.get("language"):
        errors.append("no language detected")
    if not result.get("segments"):
        errors.append("no segments")
    if not os.path.exists(srt_out) or os.path.getsize(srt_out) == 0:
        errors.append("SRT file missing or empty")

    if errors:
        print(f"✗ TRANSCRIPTION TEST FAILED: {', '.join(errors)}")
        sys.exit(1)
    else:
        print("✓ TRANSCRIPTION TEST PASSED")

    # Cleanup
    shutil.rmtree(TMP)


if __name__ == "__main__":
    main()
