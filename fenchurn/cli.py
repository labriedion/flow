"""fenchurn command line.

  python -m fenchurn.cli                          # terminal quilt, defaults
  python -m fenchurn.cli --steps 40               # earlier in the argument
  python -m fenchurn.cli --no-rebel               # everyone averages; consensus
  python -m fenchurn.cli -o quilt.svg             # write the SVG instead

The terminal view shades each tile by value (' ' dark through '@' bright) and
marks the rebel with '!'. Watch the steps climb: the quilt smooths, then —
slowly, from the middle out — turns the rebel's colour.
"""

import argparse
import sys

from .quilt import Quilt
from .render import render_svg

CHARSET = " .:-=+*#%@"


def ascii_quilt(quilt):
    lines = []
    for y in range(quilt.height):
        row = []
        for x in range(quilt.width):
            if quilt.rebel == (x, y):
                row.append("!")
                continue
            t = max(0.0, min(1.0, quilt.value(x, y)))
            row.append(CHARSET[min(len(CHARSET) - 1, int(t * len(CHARSET)))])
        lines.append("".join(row))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fenchurn", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--width", type=int, default=48, help="tiles across")
    parser.add_argument("--height", type=int, default=24, help="tiles down")
    parser.add_argument("--steps", type=int, default=120,
                        help="rounds of averaging before the snapshot")
    parser.add_argument("--seed", type=int, default=7000,
                        help="reproducible seed (7000 is the loom proposal's)")
    parser.add_argument("--rebel", type=int, nargs=2, metavar=("X", "Y"),
                        default=None, help="place the disobedient cell (default: center)")
    parser.add_argument("--no-rebel", action="store_true",
                        help="nobody disobeys; the heap finds plain consensus")
    parser.add_argument("--rebel-value", type=float, default=1.0,
                        help="the value the rebel refuses to budge from")
    parser.add_argument("-o", "--svg", metavar="FILE",
                        help="write a standalone SVG instead of terminal art")
    parser.add_argument("--px", type=int, default=28, help="SVG pixels per tile")
    args = parser.parse_args(argv)

    rebel = None if args.no_rebel else (tuple(args.rebel) if args.rebel else "center")
    quilt = Quilt(args.width, args.height, seed=args.seed, rebel=rebel,
                  rebel_value=args.rebel_value)
    quilt.run(args.steps)

    if args.svg:
        with open(args.svg, "w", encoding="utf-8") as fh:
            fh.write(render_svg(quilt, px=args.px))
        print(f"wrote {args.svg}", file=sys.stderr)
    else:
        print(ascii_quilt(quilt))
        print(
            f"\n{quilt.width}x{quilt.height} tiles, seed {args.seed}, "
            f"{args.steps} steps · mean {quilt.mean():.3f} · "
            f"unrest {quilt.total_mismatch():.3f}"
            + ("" if args.no_rebel else " · '!' never averages"),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
