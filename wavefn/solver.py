"""The tiled Wave Function Collapse solver.

Wave Function Collapse borrows its name from physics, but the idea is plain
constraint propagation. Start with a grid where every cell is *undecided* — it
could still be any tile. Then repeat two steps until the grid is fully decided:

1. **Observe.** Find the undecided cell with the lowest *entropy* (the fewest,
   least-certain remaining options), break ties at random, and **collapse** it
   to a single tile chosen by weight.
2. **Propagate.** That choice rules out some neighbours. Walk the consequences
   outward — AC-3 / worklist style — removing tiles that can no longer match any
   surviving neighbour, until nothing changes.

If a cell ever loses *all* its options, the grid has contradicted itself; we
throw it away and retry from a fresh derived seed a few times before giving up
with a clear error. Adjacency is decided purely by edge sockets (see
``tilesets.py``): two tiles may sit side by side iff their touching sockets are
equal.

Usage:

    from wavefn.solver import Solver
    from wavefn.tilesets import get

    grid = Solver(get("pipes"), width=24, height=16, seed=7).run()
    # grid[y][x] is a tile index into the tileset.

Everything here is pure standard-library Python.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .tilesets import EAST, NORTH, SOUTH, WEST, Tile

# Side -> opposite side, and the (dx, dy) step toward a neighbour on that side.
_OPPOSITE = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}
_DELTA = {NORTH: (0, -1), EAST: (1, 0), SOUTH: (0, 1), WEST: (-1, 0)}


class Contradiction(Exception):
    """Raised internally when a cell runs out of options during propagation."""


def build_adjacency(tiles: list[Tile]) -> dict[int, list[set[int]]]:
    """Precompute, for each tile and each side, which tiles may sit there.

    Returns a mapping ``tile_index -> [allowed_north, allowed_east,
    allowed_south, allowed_west]`` where each entry is the set of tile indices
    permitted on that side. A tile `b` may sit on side `d` of tile `a` iff
    `a`'s socket on side `d` equals `b`'s socket on the opposite side.

    The relation is symmetric by construction: if `b` is allowed east of `a`
    then `a` is allowed west of `b`, because both reduce to the same socket
    equality.
    """
    n = len(tiles)
    allowed: dict[int, list[set[int]]] = {
        a: [set(), set(), set(), set()] for a in range(n)
    }
    for a in range(n):
        for b in range(n):
            for side in (NORTH, EAST, SOUTH, WEST):
                if tiles[a].sockets[side] == tiles[b].sockets[_OPPOSITE[side]]:
                    allowed[a][side].add(b)
    return allowed


def _entropy(options: set[int], weights: list[float]) -> float:
    """Shannon entropy of a cell's remaining options, weighted by tile weight.

    A small noise-free value: lower means more decided. A cell with one option
    has entropy 0. We use this (not just the option count) so that heavily
    weighted choices are treated as more certain.
    """
    total = sum(weights[i] for i in options)
    return math.log(total) - sum(
        weights[i] * math.log(weights[i]) for i in options
    ) / total


@dataclass
class Solver:
    """A Wave Function Collapse run over a `width` x `height` grid of tiles.

    `tiles` is the tileset; `seed` makes a run reproducible. `attempts` is how
    many times to retry from a derived seed after a contradiction before
    raising. Call :meth:`run` to get back a 2-D grid of tile indices.
    """

    tiles: list[Tile]
    width: int
    height: int
    seed: int | None = None
    attempts: int = 12

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if not self.tiles:
            raise ValueError("tileset must contain at least one tile")
        self.weights = [t.weight for t in self.tiles]
        self.adjacency = build_adjacency(self.tiles)

    def run(self) -> list[list[int]]:
        """Solve the grid, returning ``grid[y][x] = tile_index``.

        Retries from a derived seed on contradiction up to ``attempts`` times,
        then raises :class:`RuntimeError` with a clear message.
        """
        base = self.seed if self.seed is not None else random.randrange(1 << 30)
        for attempt in range(self.attempts):
            rng = random.Random(base + attempt * 0x9E3779B1)
            try:
                return self._attempt(rng)
            except Contradiction:
                continue
        raise RuntimeError(
            f"wavefn: could not solve a {self.width}x{self.height} grid after "
            f"{self.attempts} attempts (the tileset may be over-constrained)"
        )

    def _attempt(self, rng: random.Random) -> list[list[int]]:
        """One full collapse pass; raises Contradiction if it paints itself in."""
        n_tiles = len(self.tiles)
        all_tiles = set(range(n_tiles))
        # cells[y][x] is the set of still-possible tile indices for that cell.
        cells = [[set(all_tiles) for _ in range(self.width)]
                 for _ in range(self.height)]

        undecided = sum(
            1 for row in cells for opts in row if len(opts) != 1
        )
        while undecided:
            x, y = self._lowest_entropy(cells, rng)
            self._collapse(cells, x, y, rng)
            self._propagate(cells, x, y)
            undecided = sum(
                1 for row in cells for opts in row if len(opts) != 1
            )

        return [[next(iter(cells[y][x])) for x in range(self.width)]
                for y in range(self.height)]

    def _lowest_entropy(
        self, cells: list[list[set[int]]], rng: random.Random
    ) -> tuple[int, int]:
        """Pick the undecided cell with the least entropy, ties broken randomly."""
        best: tuple[int, int] | None = None
        best_score = math.inf
        for y in range(self.height):
            for x in range(self.width):
                opts = cells[y][x]
                if len(opts) <= 1:
                    continue
                # Tiny random jitter breaks ties without changing the ordering
                # of genuinely different entropies.
                score = _entropy(opts, self.weights) + rng.random() * 1e-6
                if score < best_score:
                    best_score = score
                    best = (x, y)
        assert best is not None  # caller only loops while something is undecided
        return best

    def _collapse(
        self, cells: list[list[set[int]]], x: int, y: int, rng: random.Random
    ) -> None:
        """Reduce one cell to a single tile, chosen by weight."""
        opts = sorted(cells[y][x])
        weights = [self.weights[i] for i in opts]
        choice = rng.choices(opts, weights=weights, k=1)[0]
        cells[y][x] = {choice}

    def _propagate(self, cells: list[list[set[int]]], x: int, y: int) -> None:
        """Remove now-impossible options outward from (x, y) until stable.

        Classic AC-3 worklist: whenever a cell's option set shrinks, revisit its
        neighbours, since they may have lost the support that justified some of
        their options. An emptied cell means the choices so far can't be
        completed — a contradiction.
        """
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            current = cells[cy][cx]
            for side, (dx, dy) in _DELTA.items():
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                # The tiles permitted on `side` of *any* option still in (cx,cy).
                supported: set[int] = set()
                for t in current:
                    supported |= self.adjacency[t][side]
                neighbour = cells[ny][nx]
                pruned = neighbour & supported
                if pruned != neighbour:
                    if not pruned:
                        raise Contradiction((nx, ny))
                    cells[ny][nx] = pruned
                    stack.append((nx, ny))


def solve(
    tiles: list[Tile],
    width: int,
    height: int,
    seed: int | None = None,
    attempts: int = 12,
) -> list[list[int]]:
    """Convenience wrapper: build a :class:`Solver` and run it."""
    return Solver(tiles, width, height, seed=seed, attempts=attempts).run()
