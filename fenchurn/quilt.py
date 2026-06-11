"""The quilt — a grid of tiles, four edge values each, one rule, one rebel.

Every tile carries four numbers, one per edge (N, E, S, W). The single local
rule is *average yourself toward your neighbours*, applied in two strictly
local moves each step:

  - every seam (a pair of facing edges) pulls both edges toward their shared
    midpoint — neighbours negotiating;
  - every tile pulls its own four edges toward their own mean — a tile keeping
    itself in one piece.

Nothing here imposes edge-matching. It *emerges*: seams negotiate themselves
shut, and the heap of clashing tiles becomes one continuous quilt. Except —
the brief demands it — **one cell disobeys**. The rebel never averages. Its
edges never move. And because everyone else keeps politely meeting it halfway,
the rebel's colour leaks across every seam it touches and, given long enough,
recolours the entire quilt. The cell that refused to average ends up averaging
everyone.

Both moves conserve the total (each seam move preserves the pair's sum, each
settle move preserves the tile's sum), so with no rebel the quilt's mean is an
invariant — the tests pin that down. The rebel is the only way value enters or
leaves, which is exactly why it wins.

Pure stdlib, deterministic by seed, no rendering in here — render.py reads the
grid and draws; the terminal preview lives in cli.py.
"""

import random

# Edge indices, clockwise from the top.
N, E, S, W = 0, 1, 2, 3


class Quilt:
    def __init__(self, width=24, height=16, seed=7000, rebel="center",
                 rebel_value=1.0):
        if width < 2 or height < 2:
            raise ValueError("the heap needs at least 2x2 tiles")
        self.width = width
        self.height = height
        self.seed = seed
        self.rng = random.Random(seed)

        # tiles[y][x] is a list of four edge values in [0, 1).
        self.tiles = [
            [[self.rng.random() for _ in range(4)] for _ in range(width)]
            for _ in range(height)
        ]

        # The disobedient cell. "center" puts it mid-heap; None removes it
        # entirely (useful for proving conservation); an (x, y) pair places it.
        if rebel == "center":
            rebel = (width // 2, height // 2)
        self.rebel = rebel
        self.rebel_value = rebel_value
        if rebel is not None:
            rx, ry = rebel
            self.tiles[ry][rx] = [rebel_value] * 4

        self.tick = 0

    # ---- the one local rule -------------------------------------------------

    def _is_rebel(self, x, y):
        return self.rebel is not None and (x, y) == self.rebel

    def step(self, rate=0.5, settle=0.25):
        """One round of averaging. Each edge belongs to exactly one seam and
        each tile settles independently, so neither pass depends on sweep
        order — the rule is honestly local."""
        tiles = self.tiles

        # Seams: facing edges move toward their midpoint. A rebel edge holds
        # still; its neighbour keeps meeting it halfway anyway, which is the
        # leak the whole story turns on.
        for y in range(self.height):
            for x in range(self.width):
                if x + 1 < self.width:
                    self._pull(x, y, E, x + 1, y, W, rate)
                if y + 1 < self.height:
                    self._pull(x, y, S, x, y + 1, N, rate)

        # Settling: each tile draws its own edges toward its own mean, so a
        # tile stays one colour instead of four. The rebel doesn't settle —
        # it is already entirely of one mind.
        for y in range(self.height):
            for x in range(self.width):
                if self._is_rebel(x, y):
                    continue
                t = tiles[y][x]
                m = sum(t) / 4.0
                for i in range(4):
                    t[i] += settle * (m - t[i])

        self.tick += 1

    def _pull(self, ax, ay, ae, bx, by, be, rate):
        a = self.tiles[ay][ax]
        b = self.tiles[by][bx]
        mid = (a[ae] + b[be]) / 2.0
        if not self._is_rebel(ax, ay):
            a[ae] += rate * (mid - a[ae])
        if not self._is_rebel(bx, by):
            b[be] += rate * (mid - b[be])

    def run(self, steps, rate=0.5, settle=0.25):
        for _ in range(steps):
            self.step(rate=rate, settle=settle)
        return self

    # ---- inspection ----------------------------------------------------------

    def value(self, x, y):
        """A tile's colour: the mean of its four edges."""
        return sum(self.tiles[y][x]) / 4.0

    def mean(self):
        """The whole quilt's mean edge value."""
        total = 0.0
        for row in self.tiles:
            for t in row:
                total += sum(t)
        return total / (4.0 * self.width * self.height)

    def seam_mismatch(self, ax, ay, bx, by):
        """How far apart two facing edges still are."""
        if ax == bx and by == ay + 1:
            return abs(self.tiles[ay][ax][S] - self.tiles[by][bx][N])
        if ay == by and bx == ax + 1:
            return abs(self.tiles[ay][ax][E] - self.tiles[by][bx][W])
        raise ValueError("tiles are not adjacent")

    def total_mismatch(self):
        """The sum of every seam's disagreement — the heap's unrest."""
        total = 0.0
        for y in range(self.height):
            for x in range(self.width):
                if x + 1 < self.width:
                    total += self.seam_mismatch(x, y, x + 1, y)
                if y + 1 < self.height:
                    total += self.seam_mismatch(x, y, x, y + 1)
        return total
