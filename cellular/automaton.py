"""Elementary cellular automata — Wolfram's one-dimensional rules.

An *elementary* cellular automaton is about the simplest computer you can build.
A row of cells, each 0 or 1. To make the next row, look at every cell together
with its two neighbours — three bits, so eight possible neighbourhoods — and
decide whether the cell becomes 0 or 1. A "rule" is just a choice of output for
each of those eight cases, which packs neatly into one byte: the *rule number*
0–255. Rule 30 is famously chaotic (it seeded a random-number generator in
Mathematica); Rule 90 draws a Sierpinski triangle; Rule 110 is Turing-complete.

This module is the engine: turn a rule number into a transition table, evolve a
row, and stack the rows into a grid. Rendering lives in `render.py`. Only the
standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass


def rule_table(rule: int) -> tuple[int, ...]:
    """Expand a rule number (0–255) into its 8-entry transition table.

    The table is indexed by the 3-bit neighbourhood `(left, centre, right)` read
    as a number 0–7, matching Wolfram's convention: bit `n` of the rule number
    is the output for neighbourhood `n`. So for Rule 30 (0b00011110), the
    neighbourhood `100` (= 4) maps to bit 4 = 1.
    """
    if not isinstance(rule, int) or not 0 <= rule <= 255:
        raise ValueError(f"rule must be an integer 0–255, got {rule!r}")
    return tuple((rule >> n) & 1 for n in range(8))


@dataclass
class Automaton:
    """An elementary cellular automaton with a fixed rule and boundary handling.

    `boundary` controls what lies just off the ends of the row:
      * "wrap"  — the row is a ring; the left edge sees the right edge.
      * "zero"  — everything off the edge is 0 (an empty void).
      * "one"   — everything off the edge is 1.
    """

    rule: int
    boundary: str = "wrap"

    def __post_init__(self) -> None:
        self.table = rule_table(self.rule)
        if self.boundary not in ("wrap", "zero", "one"):
            raise ValueError(
                f"boundary must be 'wrap', 'zero', or 'one', got {self.boundary!r}"
            )

    def step(self, row: list[int]) -> list[int]:
        """Advance one row to the next according to the rule."""
        n = len(row)
        if n == 0:
            return []
        if self.boundary == "wrap":
            left_of = lambda i: row[(i - 1) % n]
            right_of = lambda i: row[(i + 1) % n]
        else:
            edge = 0 if self.boundary == "zero" else 1
            left_of = lambda i: row[i - 1] if i > 0 else edge
            right_of = lambda i: row[i + 1] if i < n - 1 else edge
        table = self.table
        out = [0] * n
        for i in range(n):
            idx = (left_of(i) << 2) | (row[i] << 1) | right_of(i)
            out[i] = table[idx]
        return out

    def evolve(self, initial: list[int], generations: int) -> list[list[int]]:
        """Run for `generations` steps, returning every row including the start.

        The result has `generations + 1` rows (row 0 is `initial`).
        """
        if generations < 0:
            raise ValueError("generations must be non-negative")
        rows = [list(initial)]
        for _ in range(generations):
            rows.append(self.step(rows[-1]))
        return rows


def single_cell(width: int) -> list[int]:
    """A starting row that is all 0 except one lit cell in the middle — the
    classic seed that grows the iconic triangular patterns."""
    if width <= 0:
        raise ValueError("width must be positive")
    row = [0] * width
    row[width // 2] = 1
    return row


def random_row(width: int, seed: int | None = None, density: float = 0.5) -> list[int]:
    """A random starting row, with roughly `density` fraction of cells lit.

    Deterministic for a given `seed`, so runs are reproducible."""
    import random

    if width <= 0:
        raise ValueError("width must be positive")
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be between 0 and 1")
    rng = random.Random(seed)
    return [1 if rng.random() < density else 0 for _ in range(width)]
