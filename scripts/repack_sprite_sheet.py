#!/usr/bin/env python3
"""Repack transparent sprite sheets into clean, uniform grids."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "Pillow is required. Use the Codex bundled Python runtime or install Pillow with `python3 -m pip install pillow`."
    ) from exc


def has_visible(alpha, threshold: int) -> bool:
    return alpha.getbbox() is not None and alpha.point(lambda p: 255 if p > threshold else 0).getbbox() is not None


def threshold_alpha(image: Image.Image, threshold: int) -> Image.Image:
    return image.getchannel("A").point(lambda p: 255 if p > threshold else 0)


def bbox_for(image: Image.Image, threshold: int):
    return threshold_alpha(image, threshold).getbbox()


def contiguous_runs(flags):
    runs = []
    start = None
    for i, flag in enumerate(flags):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(flags)))
    return runs


def grid_frames(image, args):
    w, h = image.size
    fw, fh = args.source_frame_width, args.source_frame_height
    if not fw or not fh:
        raise ValueError("grid mode requires --source-frame-width and --source-frame-height")
    cols = args.source_columns or (w // fw)
    rows = args.source_rows or (h // fh)
    frames = []
    for row in range(rows):
        for col in range(cols):
            left, top = col * fw, row * fh
            if left >= w or top >= h:
                continue
            crop = image.crop((left, top, min(left + fw, w), min(top + fh, h)))
            if not args.keep_empty and not has_visible(crop.getchannel("A"), args.alpha_threshold):
                continue
            frames.append({"image": crop, "source_rect": [left, top, left + crop.width, top + crop.height]})
    return frames, cols


def gutter_frames(image, args):
    alpha = threshold_alpha(image, args.alpha_threshold)
    w, h = image.size
    row_has = [alpha.crop((0, y, w, y + 1)).getbbox() is not None for y in range(h)]
    row_runs = contiguous_runs(row_has)
    frames = []
    max_cols = 0
    for y1, y2 in row_runs:
        band = alpha.crop((0, y1, w, y2))
        col_has = [band.crop((x, 0, x + 1, y2 - y1)).getbbox() is not None for x in range(w)]
        col_runs = contiguous_runs(col_has)
        max_cols = max(max_cols, len(col_runs))
        for x1, x2 in col_runs:
            crop = image.crop((x1, y1, x2, y2))
            frames.append({"image": crop, "source_rect": [x1, y1, x2, y2]})
    return frames, max_cols or None


def component_frames(image, args):
    alpha = threshold_alpha(image, args.alpha_threshold)
    w, h = image.size
    pix = alpha.load()
    seen = bytearray(w * h)
    frames = []
    for y in range(h):
        for x in range(w):
            idx = y * w + x
            if seen[idx] or pix[x, y] == 0:
                continue
            q = deque([(x, y)])
            seen[idx] = 1
            minx = maxx = x
            miny = maxy = y
            while q:
                cx, cy = q.popleft()
                minx, maxx = min(minx, cx), max(maxx, cx)
                miny, maxy = min(miny, cy), max(maxy, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        nidx = ny * w + nx
                        if not seen[nidx] and pix[nx, ny] != 0:
                            seen[nidx] = 1
                            q.append((nx, ny))
            if (maxx - minx + 1) * (maxy - miny + 1) >= args.min_component_area:
                rect = [minx, miny, maxx + 1, maxy + 1]
                frames.append({"image": image.crop(rect), "source_rect": rect})
    frames.sort(key=lambda f: (f["source_rect"][1], f["source_rect"][0]))
    return frames, None


def auto_frames(image, args):
    frames, cols = gutter_frames(image, args)
    if len(frames) <= 1:
        frames, cols = component_frames(image, args)
    return frames, cols


def trim_frame(frame, threshold: int):
    bbox = bbox_for(frame["image"], threshold)
    if bbox is None:
        frame["trimmed"] = frame["image"]
        frame["trim_rect"] = [0, 0, frame["image"].width, frame["image"].height]
    else:
        frame["trimmed"] = frame["image"].crop(bbox)
        frame["trim_rect"] = list(bbox)
    return frame


def paste_position(cell_w, cell_h, sprite_w, sprite_h, align):
    if align == "center":
        return (cell_w - sprite_w) // 2, (cell_h - sprite_h) // 2
    if align == "top-left":
        return 0, 0
    if align == "bottom-center":
        return (cell_w - sprite_w) // 2, cell_h - sprite_h
    raise ValueError(f"unknown alignment: {align}")


def repack(image, args):
    if args.detect == "grid" or args.source_frame_width or args.source_frame_height:
        frames, inferred_cols = grid_frames(image, args)
    elif args.detect == "components":
        frames, inferred_cols = component_frames(image, args)
    else:
        frames, inferred_cols = auto_frames(image, args)

    if not frames:
        raise ValueError("no visible frames detected")

    for frame in frames:
        trim_frame(frame, args.alpha_threshold)

    max_w = max(f["trimmed"].width for f in frames)
    max_h = max(f["trimmed"].height for f in frames)
    cell_w = args.cell_width or (max_w + args.padding * 2)
    cell_h = args.cell_height or (max_h + args.padding * 2)
    if cell_w < max_w or cell_h < max_h:
        raise ValueError(f"cell size {cell_w}x{cell_h} is smaller than largest frame {max_w}x{max_h}")

    columns = args.columns or inferred_cols or math.ceil(math.sqrt(len(frames)))
    rows = math.ceil(len(frames) / columns)
    output = Image.new("RGBA", (columns * cell_w, rows * cell_h), (0, 0, 0, 0))
    metadata = {
        "frame_count": len(frames),
        "columns": columns,
        "rows": rows,
        "cell_width": cell_w,
        "cell_height": cell_h,
        "padding": args.padding,
        "alignment": args.align,
        "frames": [],
    }

    for i, frame in enumerate(frames):
        col = i % columns
        row = i // columns
        cell_x, cell_y = col * cell_w, row * cell_h
        sprite = frame["trimmed"]
        px, py = paste_position(cell_w, cell_h, sprite.width, sprite.height, args.align)
        output.alpha_composite(sprite, (cell_x + px, cell_y + py))
        metadata["frames"].append({
            "index": i,
            "source_rect": frame["source_rect"],
            "trim_rect_in_source_frame": frame["trim_rect"],
            "output_cell": [cell_x, cell_y, cell_x + cell_w, cell_y + cell_h],
            "sprite_rect_in_output": [cell_x + px, cell_y + py, cell_x + px + sprite.width, cell_y + py + sprite.height],
        })
    return output, metadata


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--detect", choices=["auto", "grid", "components"], default="auto")
    parser.add_argument("--source-frame-width", type=int)
    parser.add_argument("--source-frame-height", type=int)
    parser.add_argument("--source-columns", type=int)
    parser.add_argument("--source-rows", type=int)
    parser.add_argument("--columns", type=int, help="output columns")
    parser.add_argument("--cell-width", type=int)
    parser.add_argument("--cell-height", type=int)
    parser.add_argument("--padding", type=int, default=2)
    parser.add_argument("--align", choices=["bottom-center", "center", "top-left"], default="bottom-center")
    parser.add_argument("--alpha-threshold", type=int, default=0)
    parser.add_argument("--min-component-area", type=int, default=4)
    parser.add_argument("--keep-empty", action="store_true")
    parser.add_argument("--metadata", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    image = Image.open(args.input).convert("RGBA")
    output, metadata = repack(image, args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.output)
    if args.metadata:
        args.metadata.parent.mkdir(parents=True, exist_ok=True)
        args.metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(
        f"wrote {args.output} ({output.width}x{output.height}), "
        f"{metadata['frame_count']} frames, {metadata['columns']} columns, cell {metadata['cell_width']}x{metadata['cell_height']}"
    )


if __name__ == "__main__":
    main()
