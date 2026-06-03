"""A library of well-known, ready-to-draw L-systems.

Each entry is a :class:`Preset` bundling everything the engine needs — the
axiom, the production rules, the turtle's turn `angle`, a forward `step`, a
suggested number of `iterations` to look good, and a one-line `description`.
These are the classics from the L-system literature (Prusinkiewicz &
Lindenmayer's *The Algorithmic Beauty of Plants* and the usual fractal canon),
with their canonical rules.

    >>> from .presets import PRESETS
    >>> sorted(PRESETS)[:3]
    ['algae', 'bush', 'dragon']
    >>> PRESETS["koch"].angle
    90.0

Use :func:`get` to fetch one by name (raising a helpful error otherwise) and
:func:`make` to turn a preset into a ready :class:`~lsystem.grammar.LSystem`.
Only the standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import LSystem


@dataclass(frozen=True)
class Preset:
    """A named, self-contained L-system recipe ready for the turtle."""

    axiom: str
    rules: dict
    angle: float
    step: float = 10.0
    iterations: int = 4
    heading: float = 0.0
    description: str = ""

    def system(self) -> LSystem:
        return LSystem(self.axiom, dict(self.rules))


PRESETS: dict[str, Preset] = {
    # Lindenmayer's original algae model — string length follows Fibonacci.
    "algae": Preset(
        axiom="A",
        rules={"A": "AB", "B": "A"},
        angle=0.0,
        iterations=7,
        description="Lindenmayer's algae; string length is the Fibonacci sequence",
    ),
    # Koch curve: replace each F with a bump. Angle 90 gives the square Koch.
    "koch": Preset(
        axiom="F",
        rules={"F": "F+F-F-F+F"},
        angle=90.0,
        step=10.0,
        iterations=4,
        description="square Koch curve — each segment grows a square bump",
    ),
    # Koch snowflake: three 60-degree Koch curves around a triangle.
    "snowflake": Preset(
        axiom="F++F++F",
        rules={"F": "F-F++F-F"},
        angle=60.0,
        step=10.0,
        iterations=4,
        description="Koch snowflake — a closed curve of infinite perimeter",
    ),
    # Sierpinski triangle: F and G both draw forward; the 120-degree turns and
    # the F=F-G+F+G-F / G=GG productions carve out the gasket.
    "sierpinski": Preset(
        axiom="F-G-G",
        rules={"F": "F-G+F+G-F", "G": "GG"},
        angle=120.0,
        step=10.0,
        iterations=6,
        description="Sierpinski triangle (gasket) — drawn in one continuous stroke",
    ),
    # Heighway dragon curve.
    "dragon": Preset(
        axiom="F",
        rules={"F": "F+G", "G": "F-G"},
        angle=90.0,
        step=10.0,
        iterations=12,
        description="Heighway dragon — a self-similar fold-the-paper curve",
    ),
    # Hilbert space-filling curve.
    "hilbert": Preset(
        axiom="A",
        rules={"A": "+BF-AFA-FB+", "B": "-AF+BFB+FA-"},
        angle=90.0,
        step=10.0,
        iterations=5,
        description="Hilbert curve — fills the square without crossing itself",
    ),
    # Levy C curve.
    "levy": Preset(
        axiom="F",
        rules={"F": "+F--F+"},
        angle=45.0,
        step=10.0,
        iterations=12,
        description="Levy C curve — a fractal of 45-degree turns",
    ),
    # The classic branching plant / bush (ABOP, figure 1.24f).
    "plant": Preset(
        axiom="X",
        rules={"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"},
        angle=25.0,
        step=10.0,
        iterations=5,
        heading=90.0,  # grow upward
        description="branching plant — the iconic fractal weed",
    ),
    # A bushier, more symmetric plant.
    "bush": Preset(
        axiom="F",
        rules={"F": "FF-[-F+F+F]+[+F-F-F]"},
        angle=22.5,
        step=10.0,
        iterations=4,
        heading=90.0,
        description="symmetric bush with paired offshoots",
    ),
    # A stochastic plant: F either lengthens or sprouts a branch, by chance.
    "weed": Preset(
        axiom="F",
        rules={
            "F": [
                ("F[+F]F[-F]F", 1.0),
                ("F[+F]F", 1.0),
                ("F[-F]F", 1.0),
            ]
        },
        angle=25.0,
        step=10.0,
        iterations=5,
        heading=90.0,
        description="stochastic weed — each F branches differently (use --seed)",
    ),
}


def get(name: str) -> Preset:
    """Return the preset called `name`, or raise ValueError listing the choices."""
    try:
        return PRESETS[name]
    except KeyError:
        choices = ", ".join(sorted(PRESETS))
        raise ValueError(f"unknown preset {name!r}; choose from: {choices}") from None


def make(name: str) -> LSystem:
    """Build the :class:`~lsystem.grammar.LSystem` for the named preset."""
    return get(name).system()
