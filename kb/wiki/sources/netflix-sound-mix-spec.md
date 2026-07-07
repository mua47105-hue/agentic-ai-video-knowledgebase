---
title: Netflix Sound Mix Specification
type: source
tags: [standard, loudness, streaming, netflix]
created: 2026-07-08
updated: 2026-07-08
related: [compliance-reporter, ebu-r128, itu-r-bs-1770-4]
---

# Netflix Sound Mix Specification

## Citation
Netflix. "Netflix Sound Mix Specification and Best Practices." Netflix Partner Help Center, 2024 revision. https://partnerhelp.netflixstudios.com/hc/en-us/articles/360000624587-Sound-Mix-Specification

## Key claims
- **Dialogue loudness**: Normalize dialogue to **-27 LUFS** (±2 LU) — significantly quieter than broadcast (-23 LUFS) or streaming (-14 LUFS) standards.
- **True-peak**: Maximum true-peak level of **-2 dBTP** for the final mix.
- **Loudness range (LRA)**: No strict limit, but dialogue must remain intelligible across the range. LRA values above 20 LU may trigger review.
- **Delivery format**: Broadcast WAV at 48 kHz / 24-bit, 5.1 surround or stereo.
- **Dynamic range**: Dialogue must sit at -27 LUFS while effects and music can be significantly louder (creates Netflix's signature "intimate dialogue + explosive action" dynamic).
- **Dialogue intelligibility**: Dialogue must be at least 6 dB above background elements at all times.

## How this connects to the wiki
- **compliance-reporter**: The `compliance.py` `netflix` check implements -27 LUFS target and -2 dBTP ceiling from this spec.
- **Hard Rule #1**: The two-pass loudnorm requirement applies to all targets including Netflix, but the *target* LUFS changes per spec.
- **content_adapter**: When mixing music under dialogue, the EBU R128 music-to-voice offset (-6 LUFS) interacts with Netflix's dialogue-centric spec.

## Contradictions with existing pages
- (none)

## Notes
- Netflix's -27 LUFS target is often surprising: most common target specs are -23 (broadcast), -14 (streaming), or -16 (talking-head). Netflix prioritizes dialogue clarity over loudness.
- The spec emphasizes dialogue intelligibility over raw loudness normalization. This means a simple `loudnorm` pass to -27 may not satisfy Netflix review if action scenes clip or dialogue is buried.
- The wiki's compliance reporter addresses this with a dedicated `netflix` spec that checks both the -27 dialogue LUFS and the -2 dBTP ceiling.
