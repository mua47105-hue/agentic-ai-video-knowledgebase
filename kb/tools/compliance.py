"""
Compliance reporter: check videos against named broadcast/streaming delivery specs.

Usage:
    from kb.tools.compliance import compliance_report
    report = compliance_report("video.mp4", "ebu_r128")
    report = compliance_report("video.mp4", "netflix_sound_mix", output_format="json")
"""

from __future__ import annotations

import json
import os
import pathlib
import typing as t

COMPLIANCE_SPECS: dict[str, dict] = {
    "ebu_r128": {
        "loudness_lufs": -23.0,
        "true_peak_db": -1.0,
        "lra_max": 7.0,
        "name": "EBU R128 (European broadcast)",
    },
    "atsc_a85": {
        "loudness_lufs": -24.0,
        "true_peak_db": -2.0,
        "lra_max": 20.0,
        "name": "ATSC A/85 (US broadcast)",
    },
    "netflix_sound_mix": {
        "loudness_lufs": -27.0,
        "true_peak_db": -2.0,
        "lra_max": 18.0,
        "dialogue_lufs": -27.0,
        "name": "Netflix Sound Mix Spec",
    },
    "bbc_delivery": {
        "loudness_lufs": -23.0,
        "true_peak_db": -1.0,
        "lra_max": 7.0,
        "name": "BBC Delivery Spec",
    },
    "youtube_streaming": {
        "loudness_lufs": -14.0,
        "true_peak_db": -1.0,
        "lra_max": 14.0,
        "name": "YouTube streaming",
    },
    "tiktok_streaming": {
        "loudness_lufs": -14.0,
        "true_peak_db": -1.0,
        "lra_max": 14.0,
        "name": "TikTok / Instagram Reels",
    },
}


def compliance_report(
    video_path: str,
    spec: str,
    *,
    output_format: str = "markdown",
    reference: str = "",
) -> dict:
    """Check a video against a named delivery spec.

    Runs quality_audio() for LUFS/true-peak/LRA, quality_full_qc() for
    visual integrity, and verify() for stream integrity.

    Returns a structured report with pass/fail per check.
    """
    if spec not in COMPLIANCE_SPECS:
        raise ValueError(f"unknown spec: {spec}. Known: {list(COMPLIANCE_SPECS)}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"video not found: {video_path}")

    spec_def = COMPLIANCE_SPECS[spec]

    from kb.tools.unified_adapter import edit

    audio = edit.quality_audio(video_path)
    integrity = edit.verify(video_path)
    full_qc = edit.quality_full_qc(video_path, reference=reference) if reference else edit.quality_full_qc(video_path)

    checks: list[dict] = []
    failures: list[dict] = []

    # LUFS check
    lufs_measured = audio.get("lufs", 0)
    lufs_target = spec_def["loudness_lufs"]
    lufs_passed = abs(lufs_measured - lufs_target) <= 1.0
    checks.append({
        "name": "integrated_lufs",
        "target": lufs_target,
        "measured": lufs_measured,
        "passed": lufs_passed,
        "tolerance": "±1 LU",
    })
    if not lufs_passed:
        failures.append(f"LUFS {lufs_measured:.1f} outside tolerance ({lufs_target:.1f} ±1)")

    # True peak check
    tp_measured = audio.get("true_peak_db", 0)
    tp_target = spec_def["true_peak_db"]
    tp_passed = tp_measured <= tp_target
    checks.append({
        "name": "true_peak_db",
        "target": tp_target,
        "measured": tp_measured,
        "passed": tp_passed,
        "tolerance": f"≤ {tp_target} dBTP",
    })
    if not tp_passed:
        failures.append(f"True peak {tp_measured:.1f} dBTP exceeds limit {tp_target} dBTP")

    # LRA check
    lra_measured = audio.get("lra", 0)
    lra_max = spec_def.get("lra_max", 20)
    lra_passed = lra_measured <= lra_max
    checks.append({
        "name": "lra",
        "target": lra_max,
        "measured": lra_measured,
        "passed": lra_passed,
        "tolerance": f"≤ {lra_max} LU",
    })
    if not lra_passed:
        failures.append(f"LRA {lra_measured:.1f} exceeds max {lra_max}")

    # Duration check
    dur_measured = integrity.get("duration", 0)
    dur_passed = dur_measured > 0
    checks.append({
        "name": "duration",
        "target": "> 0",
        "measured": dur_measured,
        "passed": dur_passed,
    })
    if not dur_passed:
        failures.append(f"Duration {dur_measured:.1f}s is zero or unreadable")

    # Stream integrity
    streams = integrity.get("streams", [])
    has_video = "video" in streams
    has_audio = "audio" in streams
    checks.append({
        "name": "has_video_stream",
        "target": True,
        "measured": has_video,
        "passed": has_video,
    })
    checks.append({
        "name": "has_audio_stream",
        "target": True,
        "measured": has_audio,
        "passed": has_audio,
    })
    if not has_video:
        failures.append("No video stream detected")
    if not has_audio:
        failures.append("No audio stream detected")

    # VMAF (if reference provided)
    if reference and os.path.exists(reference):
        vmaf = full_qc.get("vmaf", {})
        vmaf_score = vmaf.get("score", 0)
        vmaf_passed = vmaf.get("passed", False)
        checks.append({
            "name": "vmaf",
            "target": "≥ 80",
            "measured": vmaf_score,
            "passed": vmaf_passed,
        })
        if not vmaf_passed:
            failures.append(f"VMAF {vmaf_score} < 80")

    overall_passed = all(c["passed"] for c in checks)

    report = {
        "spec": spec,
        "spec_name": spec_def["name"],
        "passed": overall_passed,
        "checks": checks,
        "failures": failures,
    }

    if output_format == "markdown":
        report["report_path"] = _write_markdown_report(video_path, report)
    elif output_format == "json":
        report_path = str(pathlib.Path(video_path).with_suffix(".compliance.json"))
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        report["report_path"] = report_path

    return report


def _write_markdown_report(video_path: str, report: dict) -> str:
    output_path = str(pathlib.Path(video_path).with_suffix(".compliance.md"))

    lines = [
        f"# Compliance Report: {pathlib.Path(video_path).name}",
        "",
        f"**Spec:** {report['spec_name']} ({report['spec']})",
        f"**Status:** {'✅ PASSED' if report['passed'] else '❌ FAILED'}",
        "",
        "## Checks",
        "",
        "| Check | Target | Measured | Status |",
        "|-------|--------|----------|--------|",
    ]
    for c in report["checks"]:
        status = "✅" if c["passed"] else "❌"
        lines.append(f"| {c['name']} | {c['target']} | {c['measured']} | {status} |")

    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        for f in report["failures"]:
            lines.append(f"- {f}")

    lines.append("")
    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    return output_path


def list_specs() -> dict[str, str]:
    """Return available compliance specs and their names."""
    return {k: v["name"] for k, v in COMPLIANCE_SPECS.items()}
