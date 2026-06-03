"""Rendering: turn turtle line segments into a standalone SVG string.

The turtle in `turtle.py` produces a list of ``((x0, y0), (x1, y1))`` segments
in math orientation (y up). This module fits a viewBox snugly around them (with
a margin), flips y so the picture is upright in a browser, and emits the whole
figure as a single compact ``<path>`` — far smaller than one element per line.

    >>> from .turtle import interpret
    >>> svg = to_svg(interpret("F+F", step=10, angle=90))
    >>> svg.startswith("<svg")
    True

Pass ``gradient=True`` to colour the stroke from start to end (handy for seeing
the draw order of a space-filling curve). Only the standard library is used.
"""

from __future__ import annotations

from .turtle import bounding_box


def _fmt(value: float) -> str:
    """Format a coordinate compactly: trim trailing zeros, avoid `-0`."""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def to_path_string(segments: list, flip_y: float | None = None) -> str:
    """Build the SVG path `d` data for `segments`.

    Consecutive segments that share an endpoint are joined into one polyline
    (a single `M` followed by `L`s) so the data stays small; a gap starts a
    fresh `M`. If `flip_y` is given, y becomes ``flip_y - y`` for each point so
    the math-oriented (y-up) geometry renders upright in SVG (y-down).
    """
    def fy(y: float) -> float:
        return y if flip_y is None else flip_y - y

    parts: list[str] = []
    prev: tuple[float, float] | None = None
    for (x0, y0), (x1, y1) in segments:
        if prev is None or (abs(x0 - prev[0]) > 1e-9 or abs(y0 - prev[1]) > 1e-9):
            parts.append(f"M{_fmt(x0)} {_fmt(fy(y0))}")
        parts.append(f"L{_fmt(x1)} {_fmt(fy(y1))}")
        prev = (x1, y1)
    return "".join(parts)


def to_svg(
    segments: list,
    margin: float = 10.0,
    stroke: str = "#111111",
    stroke_width: float = 1.0,
    background: str = "#ffffff",
    gradient: bool = False,
    gradient_from: str = "#1d3f72",
    gradient_to: str = "#39b87a",
) -> str:
    """Render `segments` as a standalone SVG string, auto-fitting the viewBox.

    The viewBox hugs the geometry's bounding box plus `margin` on every side.
    `stroke`/`stroke_width`/`background` style the line and canvas. With
    `gradient=True` the stroke runs along a diagonal colour ramp from
    `gradient_from` to `gradient_to`, which makes the path's progression legible.
    """
    if not segments:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"/>'

    min_x, min_y, max_x, max_y = bounding_box(segments)
    width = (max_x - min_x) + 2 * margin
    height = (max_y - min_y) + 2 * margin

    # Shift x so the box starts at `margin`; y is flipped about `max_y + margin`
    # so a point at world-y `max_y` lands at margin and `min_y` at height-margin.
    def fx(x: float) -> float:
        return x - min_x + margin

    shifted = [((fx(a[0]), a[1]), (fx(b[0]), b[1])) for (a, b) in segments]
    path = to_path_string(shifted, flip_y=max_y + margin)

    vb_w = _fmt(width)
    vb_h = _fmt(height)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb_w}" '
        f'height="{vb_h}" viewBox="0 0 {vb_w} {vb_h}">',
        f'<rect width="{vb_w}" height="{vb_h}" fill="{background}"/>',
    ]

    if gradient:
        parts.append(
            '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{gradient_from}"/>'
            f'<stop offset="1" stop-color="{gradient_to}"/>'
            "</linearGradient></defs>"
        )
        line_stroke = "url(#g)"
    else:
        line_stroke = stroke

    parts.append(
        f'<path fill="none" stroke="{line_stroke}" '
        f'stroke-width="{_fmt(stroke_width)}" stroke-linecap="round" '
        f'stroke-linejoin="round" d="{path}"/>'
    )
    parts.append("</svg>")
    return "".join(parts)
