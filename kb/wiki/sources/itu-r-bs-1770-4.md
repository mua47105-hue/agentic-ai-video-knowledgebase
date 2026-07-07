---
title: ITU-R BS.1770-4 — Algorithms to Measure Audio Programme Loudness and True-Peak Audio Level
type: source
tags: [standard, loudness, measurement, itu]
created: 2026-07-08
updated: 2026-07-08
related: [compliance-reporter, ebu-r128]
---

# ITU-R BS.1770-4

## Citation
International Telecommunication Union. "ITU-R BS.1770-4 — Algorithms to measure audio programme loudness and true-peak audio level." ITU-R Recommendation, October 2015 (latest revision). https://www.itu.int/rec/R-REC-BS.1770-4

## Key claims
- Defines the **LKFS/LUFS** loudness measurement algorithm: pre-filtering (modified B-weighting) → mean square per channel → weighted sum (1.0 L + 1.0 R + 1.0 C + 1.0 LFE × 0).
- Defines **true-peak** measurement: 4× oversampling + inter-sample peak detection.
- Measurement gate: a "speech gate" (-70 LUFS threshold, 8-second block) was added in BS.1770-3 to handle silent passages — only blocks above threshold contribute to integrated loudness.
- The algorithm is frequency-weighting and channel-weighting independent: stereo (L+R) uses 1.0 each; 5.1 adds 1.0 for center and 0 for LFE.
- BS.1770-4 is the latest revision (2015). It updated the true-peak measurement bandwidth to 4× oversampling and clarified gating behavior.

## How this connects to the wiki
- **compliance-reporter**: All compliance specs (EBU R128, ATSC A/85, Netflix, YouTube) build on BS.1770-4's measurement algorithm.
- **Hard Rule #1**: Two-pass loudnorm uses the BS.1770-4 measurement algorithm internally. The first pass measures integrated LUFS with gating; the second pass applies the gain.
- **music_adapter**: The `_measure_loudness` helper runs ffmpeg's loudnorm filter which wraps BS.1770-4 measurement.

## Contradictions with existing pages
- (none)

## Notes
- BS.1770-4 is the *measurement* standard. EBU R128 and ATSC A/85 are *target specifications* that reference it.
- ffmpeg's `ebur128` filter and `loudnorm` filter both implement BS.1770-4 measurement (the former for analysis, the latter for correction).
- The -70 LUFS speech gate is a common source of confusion: very quiet content may show *no* integrated loudness because all blocks fall below the gate threshold.
