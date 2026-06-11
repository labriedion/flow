"""lullweave command line.

  python -m lullweave.cli                      # watch the weave, live glyphs
  python -m lullweave.cli --steps 2000         # let it run longer
  python -m lullweave.cli --once --steps 300   # one still frame, no animation
  python -m lullweave.cli -o weave.svg         # the standalone SVG, wires and all
  python -m lullweave.cli --shortcuts 0        # cut the hidden wires; waves only crawl

Watch for the two things the rule never asks for: waves of light rolling
across the field, and far corners flashing in step because a hidden shortcut
wired them together. The status line reports the global coherence r — a
number no node in the weave can see.
"""

import argparse
import sys
import time

from .render import glyph_frame, render_svg
from .weave import Weave

_HOME = "\x1b[H\x1b[J"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="lullweave", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--width", type=int, default=72, help="nodes across")
    parser.add_argument("--height", type=int, default=28, help="nodes down")
    parser.add_argument("--steps", type=int, default=600,
                        help="steps to run (animation length, or lead-in)")
    parser.add_argument("--seed", type=int, default=11001,
                        help="reproducible seed (11001 is the loom proposal's)")
    parser.add_argument("--shortcuts", type=float, default=0.08,
                        help="long-range wires as a fraction of node count")
    parser.add_argument("--fps", type=float, default=24.0,
                        help="animation frames per second")
    parser.add_argument("--once", action="store_true",
                        help="run the steps silently, print a single frame")
    parser.add_argument("-o", "--svg", metavar="FILE",
                        help="write a standalone SVG instead of glyphs")
    parser.add_argument("--px", type=int, default=18, help="SVG pixels per node")
    args = parser.parse_args(argv)

    weave = Weave(args.width, args.height, seed=args.seed,
                  shortcut_frac=args.shortcuts)

    if args.svg:
        weave.run(args.steps)
        with open(args.svg, "w", encoding="utf-8") as fh:
            fh.write(render_svg(weave, px=args.px))
        print(f"wrote {args.svg}", file=sys.stderr)
    elif args.once:
        weave.run(args.steps)
        print(glyph_frame(weave))
    else:
        delay = 1.0 / max(args.fps, 0.1)
        try:
            for _ in range(args.steps):
                weave.step()
                sys.stdout.write(
                    f"{_HOME}{glyph_frame(weave)}\n"
                    f"step {weave.tick}  ·  r {weave.order():.2f}  ·  "
                    f"mean gain {weave.mean_gain():.2f}\n")
                sys.stdout.flush()
                time.sleep(delay)
        except KeyboardInterrupt:
            pass

    print(
        f"{args.width}x{args.height} nodes, seed {args.seed}, "
        f"{len(weave.shortcuts)} shortcuts, {weave.tick} steps · "
        f"r {weave.order():.3f} · mean gain {weave.mean_gain():.3f}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
