"""The rewriting half of an L-system — an axiom and a set of production rules.

A *Lindenmayer system* grows a string by rewriting. You start with a short
`axiom` and a set of `rules` saying how to replace each symbol; on every
iteration every symbol is replaced *simultaneously* by its production (a symbol
with no rule is left alone). Run that a few times and a tiny seed blossoms into
a long string, which `turtle.py` then reads as drawing commands.

A deterministic, context-free system is just a dict of `symbol -> production`::

    >>> algae = LSystem("A", {"A": "AB", "B": "A"})
    >>> algae.expand(0)
    'A'
    >>> [len(algae.expand(n)) for n in range(7)]
    [1, 2, 3, 5, 8, 13, 21]

— the Fibonacci numbers, which is the textbook behaviour of Lindenmayer's
original algae model.

Rules may also be *stochastic*: map a symbol to several candidate productions,
each with a weight, and one is chosen at random per occurrence. Pass a ``seed``
to :meth:`LSystem.expand` (or construct with one) to keep it reproducible::

    >>> bush = LSystem("F", {"F": [("FF", 1.0), ("F[+F]F", 2.0)]})
    >>> bush.expand(3, seed=7) == bush.expand(3, seed=7)
    True

Only the standard library is used.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

# A production is either a single replacement string (deterministic) or a list
# of (replacement, weight) options to be chosen between (stochastic).
Production = "str | list[tuple[str, float]]"


@dataclass
class LSystem:
    """An L-system: an axiom string plus per-symbol production rules.

    `rules` maps a single-character symbol to its production. A production is
    either:

      * a plain string — the symbol is always rewritten to it (deterministic);
      * a list of ``(replacement, weight)`` pairs — one replacement is drawn at
        random, with probability proportional to its weight (stochastic).

    Symbols with no rule are constants and rewrite to themselves. A `seed` makes
    stochastic expansion reproducible; it can be set here or per :meth:`expand`.
    """

    axiom: str
    rules: dict = field(default_factory=dict)
    seed: int | None = None

    def __post_init__(self) -> None:
        for symbol, production in self.rules.items():
            if not isinstance(symbol, str) or len(symbol) != 1:
                raise ValueError(
                    f"rule keys must be single characters, got {symbol!r}"
                )
            if isinstance(production, list):
                if not production:
                    raise ValueError(f"rule {symbol!r} has no options")
                for option in production:
                    if (
                        not isinstance(option, tuple)
                        or len(option) != 2
                        or not isinstance(option[0], str)
                    ):
                        raise ValueError(
                            f"stochastic rule {symbol!r} options must be "
                            f"(replacement, weight) pairs, got {option!r}"
                        )
                    if option[1] < 0:
                        raise ValueError(
                            f"rule {symbol!r} has a negative weight: {option[1]}"
                        )
                if sum(w for _, w in production) <= 0:
                    raise ValueError(f"rule {symbol!r} weights sum to zero")
            elif not isinstance(production, str):
                raise ValueError(
                    f"rule {symbol!r} must map to a string or a list of "
                    f"(string, weight) pairs, got {production!r}"
                )

    @property
    def is_stochastic(self) -> bool:
        """True if any rule offers a choice of productions."""
        return any(isinstance(p, list) for p in self.rules.values())

    def _replacement(self, symbol: str, rng: random.Random) -> str:
        production = self.rules.get(symbol)
        if production is None:
            return symbol
        if isinstance(production, str):
            return production
        # Stochastic: weighted choice among the options.
        choices, weights = zip(*production)
        return rng.choices(choices, weights=weights, k=1)[0]

    def step(self, string: str, rng: random.Random) -> str:
        """Apply every rule once across `string` (one rewriting pass)."""
        return "".join(self._replacement(c, rng) for c in string)

    def expand(self, iterations: int, seed: int | None = None) -> str:
        """Rewrite the axiom `iterations` times and return the resulting string.

        ``iterations=0`` returns the axiom unchanged. For stochastic systems,
        `seed` (falling back to the instance `seed`) fixes the random draws so
        the same seed always yields the same string.
        """
        if iterations < 0:
            raise ValueError("iterations must be non-negative")
        rng = random.Random(self.seed if seed is None else seed)
        string = self.axiom
        for _ in range(iterations):
            string = self.step(string, rng)
        return string
