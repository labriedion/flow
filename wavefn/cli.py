"""Command-line interface for the tiled Wave Function Collapse solver.

Examples:
    python -m wavefn.cli                                   # a default pipes grid
    python -m wavefn.cli --tileset pipes --width 24 --height 16 --seed 7
    python -m wavefn.cli --tileset terrain --seed 3        # a little coastline
    python -m wavefn.cli --list                            # show the tilesets
    python -m wavefn.cli --tileset pipes --svg out.svg     # write an SVG instead
    python -m wavefn.cli --plain                           # full-size, one row/line

It collapses a `width` x `height` grid of tiles so that every neighbouring pair
agrees on its shared edge, then stamps each tile's pixel pattern and prints the
result with compact half-block characters (two pixel rows per line). A `--seed`
makes the run reproducible.
"""

from __future__ import annotations

import argparse
import sys

from .render import stamp, to_half_blocks, to_svg, to_text
from .solver import Solver
from .tilesets import TILESETS, names


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wavefn",
        description="Collapse a grid of tiles and draw the result.",
    )
    p.add_argument("--tileset", choices=names(), default="pipes",
                   help="which built-in tileset to use (default: pipes)")
    p.add_argument("--width", type=int, default=24,
                   help="grid width in tiles (default: 24)")
    p.add_argument("--height", type=int, default=16,
                   help="grid height in tiles (default: 16)")
    p.add_argument("--seed", type=int, default=None,
                   help="seed for a reproducible run")
    p.add_argument("--attempts", type=int, default=12,
                   help="retries from a derived seed on contradiction (default: 12)")
    p.add_argument("--plain", action="store_true",
                   help="render full-size, one pixel row per line (no half-blocks)")
    p.add_argument("--list", action="store_true",
                   help="list the available tilesets and exit")
    p.add_argument("--svg", metavar="PATH",
                   help="write the result to an SVG file instead of the terminal")
    p.add_argument("--cell", type=int, default=8,
                   help="SVG pixel size in units (default: 8)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        for name in names():
            ts = TILESETS[name]
            print(f"{name:<10} {len(ts.tiles):>3} tiles")
        return 0

    if args.width <= 0 or args.height <= 0:
        print("wavefn: width and height must be positive", file=sys.stderr)
        return 2
    if args.attempts <= 0:
        print("wavefn: attempts must be positive", file=sys.stderr)
        return 2

    ts = TILESETS[args.tileset]
    try:
        grid = Solver(
            ts.tiles, args.width, args.height,
            seed=args.seed, attempts=args.attempts,
        ).run()
    except (ValueError, RuntimeError) as exc:
        msg = str(exc)
        print(msg if msg.startswith("wavefn:") else f"wavefn: {msg}",
              file=sys.stderr)
        return 1

    field = stamp(grid, ts.tiles)

    if args.svg:
        svg = to_svg(field, cell=args.cell, palette=ts.palette)
        try:
            with open(args.svg, "w", encoding="utf-8") as f:
                f.write(svg)
        except OSError as exc:
            print(f"wavefn: could not write {args.svg}: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {args.svg} ({args.width}×{args.height} tiles, {args.tileset})")
        return 0

    print(to_text(field) if args.plain else to_half_blocks(field))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
