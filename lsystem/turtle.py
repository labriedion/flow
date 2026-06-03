"""The drawing half of an L-system — read a symbol string as turtle graphics.

A *turtle* sits at a position with a heading and obeys single-character
commands. Walk an expanded L-system string left to right and you trace out a
figure. The standard alphabet:

  =======  ==================================================
  symbol   action
  =======  ==================================================
  ``F``    move forward by one step, drawing a line
  ``G``    move forward by one step, drawing a line (alias)
  ``f``    move forward without drawing (a pen-up jump)
  ``+``    turn left by the system's angle
  ``-``    turn right by the system's angle
  ``|``    turn around (180 degrees)
  ``[``    push the current position and heading onto a stack
  ``]``    pop them back — return to a remembered branch point
  =======  ==================================================

Any other symbol (``A``, ``B``, ``X``, ``Y``, ...) is a no-op for drawing: such
letters only steer the rewriting. The stack is what makes branching plants
possible — ``[`` saves where you are, ``]`` teleports you back.

The result is a list of line segments (each ``((x0, y0), (x1, y1))``)::

    >>> segs = interpret("F+F", step=10, angle=90)
    >>> len(segs)
    2
    >>> bounding_box(segs)
    (0.0, 0.0, 10.0, 10.0)

Only the standard library is used.
"""

from __future__ import annotations

import math

Point = "tuple[float, float]"
Segment = "tuple[Point, Point]"


def interpret(
    string: str,
    step: float = 10.0,
    angle: float = 90.0,
    start: tuple[float, float] = (0.0, 0.0),
    heading: float = 0.0,
    draw: str = "FG",
) -> list:
    """Turn a command `string` into a list of line segments.

    `step` is the forward distance, `angle` the turn (in degrees), `start` the
    initial position and `heading` the initial direction (degrees, 0 = +x axis,
    increasing counter-clockwise). `draw` lists the symbols that draw a line
    when moving forward; symbols `f` always move without drawing.

    Returns a list of ``((x0, y0), (x1, y1))`` segments. Coordinates use a
    conventional math orientation (y grows upward, left turns are positive);
    the SVG renderer flips y so the picture comes out upright.
    """
    x, y = start
    theta = math.radians(heading)
    delta = math.radians(angle)
    stack: list[tuple[float, float, float]] = []
    segments: list = []

    for symbol in string:
        if symbol in draw or symbol == "f":
            nx = x + step * math.cos(theta)
            ny = y + step * math.sin(theta)
            if symbol != "f":
                segments.append(((x, y), (nx, ny)))
            x, y = nx, ny
        elif symbol == "+":
            theta += delta
        elif symbol == "-":
            theta -= delta
        elif symbol == "|":
            theta += math.pi
        elif symbol == "[":
            stack.append((x, y, theta))
        elif symbol == "]":
            if not stack:
                raise ValueError("unbalanced ']' — pop from an empty stack")
            x, y, theta = stack.pop()
        # everything else is a constant: no drawing effect.

    return segments


def bounding_box(segments: list) -> tuple:
    """The ``(min_x, min_y, max_x, max_y)`` box enclosing every segment.

    Returns ``(0.0, 0.0, 0.0, 0.0)`` for an empty list.
    """
    if not segments:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [c for (a, b) in segments for c in (a[0], b[0])]
    ys = [c for (a, b) in segments for c in (a[1], b[1])]
    return (min(xs), min(ys), max(xs), max(ys))
