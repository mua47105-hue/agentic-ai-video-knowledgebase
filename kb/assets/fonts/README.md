# Bundled Professional Fonts

Fonts are **fetched on first run** from Google Fonts (OFL 1.1) to `~/.cache/kb_fonts/`.
This keeps the repo small (~1.5MB savings vs vendoring).

## Montserrat (variable font, all weights)
- **Source:** https://fonts.google.com/specimen/Montserrat
- **Use:** MrBeast-style titles, box-background captions (Default + Highlight styles)
- **Weight:** Bold (700) for captions; ExtraBold (800) for titles

## Inter (variable font, all weights)
- **Source:** https://fonts.google.com/specimen/Inter
- **Use:** Apple-keynote-style body text (Apple style)
- **Weight:** Bold (700) for captions
- **Why:** 88% visual match to SF Pro (Apple's proprietary font)

## How it works
`caption_presets.text_subtitles_animated()` calls `_ensure_fonts()` on first run,
which downloads the fonts to `~/.cache/kb_fonts/` and passes `fontsdir=` to libass.
If the download fails (offline), libass falls back to system fonts via fontconfig.

To pre-install: `python3 -c "from kb.tools.caption_presets import _ensure_fonts; _ensure_fonts()"`
