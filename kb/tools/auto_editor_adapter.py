"""auto-editor adapter — auto silence/motion cut via subprocess.

auto-editor is a CLI tool (Rust binary distributed via PyPI launcher).
Wraps the binary for Python use. MIT licensed.
"""
from __future__ import annotations
import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional


def is_available() -> bool:
    try:
        r = subprocess.run(["auto-editor", "--version"], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def auto_edit(input_path: str, output_path: str, margin: float = 0.3,
              no_noise: bool = False, no_silence: bool = False,
              edit_speed: Optional[float] = None, silent_speed: Optional[float] = None,
              frame_margin: Optional[int] = None, export: Optional[str] = None) -> str:
    if not is_available():
        raise RuntimeError("auto-editor not installed. Install with: pip install auto-editor")
    cmd = ["auto-editor", input_path, "-o", output_path]
    if margin != 0.3: cmd.extend(["--margin", str(margin)])
    if no_noise: cmd.append("--no-noise")
    if no_silence: cmd.append("--no-silence")
    if edit_speed is not None: cmd.extend(["--edit-speed", str(edit_speed)])
    if silent_speed is not None: cmd.extend(["--silent-speed", str(silent_speed)])
    if frame_margin is not None: cmd.extend(["--frame-margin", str(frame_margin)])
    if export: cmd.extend(["--export", export])
    subprocess.run(cmd, check=True)
    return output_path


def auto_edit_analyze(input_path: str) -> dict:
    if not is_available():
        raise RuntimeError("auto-editor not installed")
    cmd = ["auto-editor", input_path, "--export", "json", "--no-open"]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    sidecar = Path(input_path).with_suffix(".json")
    if sidecar.exists():
        data = json.loads(sidecar.read_text())
        sidecar.unlink()
        return data
    return json.loads(r.stdout) if r.stdout else {}


def auto_edit_to_edl(input_path: str, edl_path: str, target_nle: str = "premiere") -> str:
    valid = {"premier", "resolve", "final-cut-pro", "shotcut", "kdenlive"}
    if target_nle not in valid:
        raise ValueError(f"target_nle must be one of {valid}")
    return auto_edit(input_path, edl_path, export=target_nle)

__all__ = ["is_available", "auto_edit", "auto_edit_analyze", "auto_edit_to_edl"]
