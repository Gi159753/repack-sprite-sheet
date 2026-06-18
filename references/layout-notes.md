# Sprite Sheet Layout Notes

## Detection choice

Use grid mode when the original image is already a regular sprite sheet, even if each frame has extra transparent space. Grid mode best preserves intended frame count and timing.

Use auto mode when the source image is a loose sequence of poses separated by fully transparent rows or columns. Auto mode detects transparent gutters first and falls back to connected components.

Avoid connected-component-only detection for characters with detached weapons, particles, shadows, or separated body parts because one animation frame may become several frames.

## Alignment choice

Use `bottom-center` for characters, enemies, pickups, and anything that touches the ground. Use `center` for projectiles, VFX bursts, icons, and UI sprites. Use explicit `--cell-width` and `--cell-height` when the game engine expects exact frame dimensions.

## Metadata

The script metadata includes source bounds, trimmed bounds, output rectangles, cell size, output columns, output rows, and frame count. Use it to configure Godot `SpriteFrames`, `AnimatedSprite2D`, `AtlasTexture`, Unity sprite slicing, or custom runtime atlases.
