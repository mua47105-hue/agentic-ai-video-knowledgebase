---
title: Compliance Reporter
type: entity
tags: [tool, compliance, broadcast, streaming, lufs]
created: 2026-07-07
updated: 2026-07-07
sources: [ebu-r128, itu-r-bs-1770-4, netflix-sound-mix-spec]
related: [free-ai-video-editing-stack, ffmpeg-command-reference]
---

# Compliance Reporter

Checks videos against named broadcast and streaming delivery specs. Wraps existing `quality_full_qc()` and `quality_audio()` functions.

## Location

`kb/tools/compliance.py`

## Usage

```python
from kb.tools.compliance import compliance_report, list_specs

# List available specs
print(list_specs())

# Check against YouTube streaming spec
report = compliance_report("output.mp4", "youtube_streaming")
print("Passed:", report["passed"])
for check in report["checks"]:
    print(f"  {check['name']}: {'✅' if check['passed'] else '❌'}")

# Check against Netflix Sound Mix (with reference for VMAF)
report = compliance_report("output.mp4", "netflix_sound_mix", reference="source.mp4")
```

## Supported specs

| Spec Key | Name | LUFS | True Peak | LRA |
|----------|------|------|-----------|-----|
| `ebu_r128` | EBU R128 (European broadcast) | -23 LUFS | -1.0 dBTP | ≤ 7 |
| `atsc_a85` | ATSC A/85 (US broadcast) | -24 LUFS | -2.0 dBTP | ≤ 20 |
| `netflix_sound_mix` | Netflix Sound Mix | -27 LUFS | -2.0 dBTP | ≤ 18 |
| `bbc_delivery` | BBC Delivery Spec | -23 LUFS | -1.0 dBTP | ≤ 7 |
| `youtube_streaming` | YouTube streaming | -14 LUFS | -1.0 dBTP | ≤ 14 |
| `tiktok_streaming` | TikTok / Instagram Reels | -14 LUFS | -1.0 dBTP | ≤ 14 |

## Output formats

Reports can be generated as `markdown` (default) or `json`. Markdown reports include a check table and list of failures.

## Zero-dependency

Wraps existing `quality_audio()`, `quality_full_qc()`, and `verify()` from the unified adapter. No new dependencies.
