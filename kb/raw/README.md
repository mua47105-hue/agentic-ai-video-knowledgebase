# Raw Asset Drop Zone

Place source video/audio files here before processing. This directory is
gitignored — large media files are not committed to the repo.

## Conventions

- **`assets/`** — small test clips, icons, overlays, watermarks (`.gitkeep` ensures
  the directory stays in version control).
- Root of `raw/` — working copies for active edits. Delete when done.
- Use `kb/wiki/charts/` for generated chart images.

## Workflow

1. Drop `input.mp4` (and any overlay images, music, etc.) into `raw/`.
2. Run edits via SKILL.md / ffmpeg_adapter.
3. Output goes to `raw/output.mp4` or a path of your choice.
4. Clean up raw files when the project is complete.

> **Note:** This KB is about *editing* footage, not generating it. Raw files
> should be real recordings or screen captures, not AI-generated clips.
