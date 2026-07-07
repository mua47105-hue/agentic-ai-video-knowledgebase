# Bundled Professional Fonts

All fonts are **OFL 1.1 (SIL Open Font License)** — free for commercial use, bundlable, modifiable.

## Montserrat (variable font, all weights)
- **Source:** https://fonts.google.com/specimen/Montserrat
- **Use:** MrBeast-style titles, box-background captions (Default + Highlight styles)
- **Weight:** Bold (700) for captions; ExtraBold (800) for titles
- **Why:** Geometric, modern, reads well at all sizes. The MrBeast signature look.

## Inter (variable font, all weights)
- **Source:** https://fonts.google.com/specimen/Inter
- **Use:** Apple-keynote-style body text (Apple style)
- **Weight:** Bold (700) for captions
- **Why:** 88% visual match to SF Pro (Apple's proprietary font). Designed for screen readability. The closest free alternative to Apple's system font.

## Why these fonts?
Per motion-design research:
- **Arial** (the previous default) is the #1 amateur tell — it reads as "first PowerPoint tutorial"
- **SF Pro** is Apple-proprietary — cannot be bundled
- **Inter** is the recommended SF Pro replacement (88% match per fontalternatives.com)
- **Montserrat** is the MrBeast/TikTok standard for kinetic typography
- Both are **OFL licensed** — safe for any commercial use

## Usage
The `caption_presets.text_subtitles_animated()` function automatically passes `fontsdir=kb/assets/fonts` to FFmpeg's `subtitles` filter, so libass finds these fonts. No configuration needed.

If you want to use a system font instead, delete the fonts from this directory — libass will fall back to system fonts via fontconfig.
