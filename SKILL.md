---
name: repack-sprite-sheet
description: Repack transparent sprite sheets and sprite sequence images into cleaner engine-ready grids. Use when Codex needs to process uploaded PNG/WebP sprite sheets with transparent backgrounds, split or trim animation frames, preserve frame order, normalize frame canvas size, add padding, choose output columns, export metadata, or make a sprite sequence easier to import into Godot, Unity, Phaser, or other game tools.
---

# Repack Sprite Sheet

## Workflow

1. Identify the source layout before editing pixels.
   - If the user provides frame width/height, source columns/rows, or engine import settings, use grid mode.
   - If frames are separated by transparent gutters, use auto mode first.
   - If auto detection may split one pose into multiple pieces, ask for frame size or use grid mode.
2. Run `scripts/repack_sprite_sheet.py` rather than rewriting image code.
3. Preserve animation order left-to-right, top-to-bottom unless the user says otherwise.
4. Output a transparent PNG plus JSON metadata when useful.
5. Verify the resulting dimensions, frame count, cell size, and visible bounding boxes before responding.

## Quick Commands

Use the bundled Codex Python runtime when available because it includes Pillow:

```bash
/Users/lanjian/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/repack_sprite_sheet.py input.png output.png --columns 6 --padding 2 --metadata output.json
```

Use explicit grid slicing when the original sheet has fixed cells:

```bash
python3 scripts/repack_sprite_sheet.py input.png output.png --source-frame-width 64 --source-frame-height 64 --columns 8 --padding 2 --metadata output.json
```

Use auto detection for transparent-gutter sheets:

```bash
python3 scripts/repack_sprite_sheet.py input.png output.png --detect auto --columns 5 --padding 4 --metadata output.json
```

## Defaults

- Trim each frame to its non-transparent bounds, then place it onto a consistent output cell.
- Default output cell size is the largest trimmed frame plus `padding * 2`.
- Default alignment is `bottom-center`, which usually keeps feet/contact points stable.
- Default output columns are inferred from source columns when grid mode is used, otherwise `ceil(sqrt(frame_count))`.
- Empty fully transparent source cells are skipped unless `--keep-empty` is set.

## Decision Notes

Read `references/layout-notes.md` when choosing detection mode, alignment, or metadata format for a tricky sheet.
