"""saltcrawl command line.

  python -m saltcrawl.cli                       # terminal crawl, defaults
  python -m saltcrawl.cli --steps 600           # let it crawl further
  python -m saltcrawl.cli -o crawl.svg          # the standalone SVG
  python -m saltcrawl.cli --seed 3 --cap 96     # a smaller colony

The terminal view shades each cell by how often any grain ever walked it —
the crawl's whole history at a glance. Live grains print as 'o'. The world
wraps: watch a branch leave the right edge and carry on from the left.
"""

import argparse
import sys

from .swarm import Swarm
from .render import render_svg

CHARSET = " .:-=+*#%@"


def ascii_crawl(swarm, cols=72, rows=28):
    """Bin every trail point ever walked onto a character grid."""
    visits = [[0] * cols for _ in range(rows)]
    for _, trail in swarm.all_trails():
        for seg in trail:
            for x, y in seg:
                c = min(cols - 1, int(x / swarm.width * cols))
                r = min(rows - 1, int(y / swarm.height * rows))
                visits[r][c] += 1
    peak = max((v for row in visits for v in row), default=1) or 1
    grid = [
        [CHARSET[min(len(CHARSET) - 1, int((v / peak) ** 0.5 * len(CHARSET)))]
         for v in row]
        for row in visits
    ]
    for g in swarm.grains:
        c = min(cols - 1, int(g.x / swarm.width * cols))
        r = min(rows - 1, int(g.y / swarm.height * rows))
        grid[r][c] = "o"
    return "\n".join("".join(row) for row in grid)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="saltcrawl", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--steps", type=int, default=420,
                        help="how long the colony crawls")
    parser.add_argument("--seed", type=int, default=7001,
                        help="reproducible seed (7001 is the loom proposal's)")
    parser.add_argument("--threshold", type=float, default=2.0,
                        help="split in two past this mass")
    parser.add_argument("--cap", type=int, default=192,
                        help="safety bound on the population")
    parser.add_argument("-o", "--svg", metavar="FILE",
                        help="write a standalone SVG instead of terminal art")
    parser.add_argument("--scale", type=float, default=2.0,
                        help="SVG pixels per world unit")
    args = parser.parse_args(argv)

    swarm = Swarm(seed=args.seed, threshold=args.threshold, cap=args.cap)
    swarm.run(args.steps)

    if args.svg:
        with open(args.svg, "w", encoding="utf-8") as fh:
            fh.write(render_svg(swarm, scale=args.scale))
        print(f"wrote {args.svg}", file=sys.stderr)
    else:
        print(ascii_crawl(swarm))
        gens = max(g.gen for g in swarm.grains)
        print(
            f"\nseed {args.seed}, {args.steps} steps · {swarm.population()} grains "
            f"alive (gen up to {gens}) · total mass {swarm.total_mass():.1f} · "
            f"the world wraps",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
