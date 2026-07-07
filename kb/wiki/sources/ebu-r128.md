---
title: EBU R128 — Loudness Normalisation and Permitted Maximum Level of Audio Signals
type: source
tags: [standard, loudness, broadcast, ebu]
created: 2026-07-08
updated: 2026-07-08
related: [compliance-reporter, mcp-video]
---

# EBU R128

## Citation
European Broadcasting Union. "EBU R128 — Loudness Normalisation and Permitted Maximum Level of Audio Signals." EBU Recommendation R128, 2010 (latest revision: R128-2020). https://www.ebu.ch/publications/r128

## Key claims
- Programme loudness should normalize to **-23.0 LUFS** (±0.5 LU) for broadcast delivery.
- Maximum true-peak level must not exceed **-1 dBTP**.
- Loudness range (LRA) should be measured but not mandated to a fixed value; values of 5-20 LU are typical.
- Measurement uses the ITU-R BS.1770-4 algorithm; EBU R128 is a *recommendation* built on top of that *standard*.
- The "EBU Mode" measurement preset specifies integrated, short-term, and momentary loudness measurement windows.

## How this connects to the wiki
- **compliance-reporter**: The `compliance.py` `ebu_r128` spec implements these exact thresholds (-23 LUFS, -1 dBTP). This source documents *why* those numbers.
- **Hard Rule #1**: Two-pass loudnorm is mandated because single-pass loudnorm doesn't converge to the integrated target reliably — a finding consistent with EBU R128's measurement protocol.
- **Hard Rule #17**: True-peak limiting at -1 dBTP is required for streaming delivery because EBU R128 (and ATSC A/85) both cap at this level.

## Contradictions with existing pages
- (none — current wiki content is consistent with R128)

## Notes
- EBU R128 is a *recommendation*, not a standard. ITU-R BS.1770-4 is the underlying *standard*.
- R128-2020 is the latest revision. Earlier revisions (R128-2014) had slightly different gating behavior.
- The wiki's `compliance.py` uses ffmpeg's `ebur128` filter, which implements the EBU R128 measurement spec.
