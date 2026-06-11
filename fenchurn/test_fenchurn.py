"""Tests for the fenchurn quilt: the rule, its invariant, and the rebel's win."""

import xml.etree.ElementTree as ET

from .quilt import Quilt
from .render import render_svg


def test_same_seed_same_quilt():
    a = Quilt(16, 12, seed=99).run(150)
    b = Quilt(16, 12, seed=99).run(150)
    assert a.tiles == b.tiles


def test_averaging_settles_the_heap():
    """A short run melts almost all of the initial disagreement away."""
    q = Quilt(20, 14, seed=7)
    before = q.total_mismatch()
    q.run(200)
    assert q.total_mismatch() < before * 0.05


def test_the_scar_marks_the_rebel():
    """Mid-run, the widest seam on the quilt touches the disobedient cell:
    everyone else's stitches fade first."""
    q = Quilt(12, 10, seed=3).run(80)
    rx, ry = q.rebel
    widest, where = -1.0, None
    for y in range(q.height):
        for x in range(q.width):
            if x + 1 < q.width:
                gap = q.seam_mismatch(x, y, x + 1, y)
                if gap > widest:
                    widest, where = gap, {(x, y), (x + 1, y)}
            if y + 1 < q.height:
                gap = q.seam_mismatch(x, y, x, y + 1)
                if gap > widest:
                    widest, where = gap, {(x, y), (x, y + 1)}
    assert (rx, ry) in where, f"widest seam {where} should touch the rebel {(rx, ry)}"


def test_rebel_never_budges():
    q = Quilt(10, 8, seed=5, rebel=(4, 4), rebel_value=0.75)
    q.run(300)
    assert q.tiles[4][4] == [0.75] * 4


def test_the_rebel_wins():
    """One disobedient cell recolours the entire quilt — edge-matching included:
    at the end every seam has closed around the rebel's own value."""
    q = Quilt(8, 6, seed=11, rebel_value=1.0)
    start_gap = abs(q.mean() - 1.0)
    q.run(4000)
    end_gap = abs(q.mean() - 1.0)
    assert end_gap < start_gap / 10
    assert end_gap < 0.05
    # Not just on average: every single tile has come around...
    for y in range(q.height):
        for x in range(q.width):
            assert q.value(x, y) > 0.9
    # ...and the quilt is continuous: no seam still gapes.
    for y in range(q.height):
        for x in range(q.width):
            if x + 1 < q.width:
                assert q.seam_mismatch(x, y, x + 1, y) < 0.01
            if y + 1 < q.height:
                assert q.seam_mismatch(x, y, x, y + 1) < 0.01


def test_without_a_rebel_the_mean_is_conserved():
    """Both moves conserve their sums, so consensus lands on the average."""
    q = Quilt(8, 6, seed=21, rebel=None)
    before = q.mean()
    q.run(2000)
    assert abs(q.mean() - before) < 1e-9
    # ...and consensus really was reached: the heap settled on its average.
    assert q.total_mismatch() < 1e-4
    for y in range(q.height):
        for x in range(q.width):
            assert abs(q.value(x, y) - before) < 0.01


def test_svg_is_wellformed_and_complete():
    q = Quilt(9, 7, seed=2).run(60)
    svg = render_svg(q)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    rects = [el for el in root.iter() if el.tag.endswith("rect")]
    # one background + one per tile
    assert len(rects) == 1 + q.width * q.height
