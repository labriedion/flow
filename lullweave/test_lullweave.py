"""Tests for the lullweave: the wiring, the pull, and the edge it holds.

The heart of the suite is the three-way split the brief demanded: grip pinned
tight is one big flash, no grip at all is static, and the homeostat — the
actual rule — holds the weave in between and never lets it settle.
"""

import math
import xml.etree.ElementTree as ET

from .render import GLYPHS, glyph_frame, render_svg
from .weave import TAU, Weave


def _r_samples(weave, n=8, gap=75):
    out = []
    for _ in range(n):
        weave.run(gap)
        out.append(weave.order())
    return out


def test_same_seed_same_weave():
    a = Weave(32, 16, seed=99).run(150)
    b = Weave(32, 16, seed=99).run(150)
    assert a.phase == b.phase
    assert a.gain == b.gain
    assert a.shortcuts == b.shortcuts


def test_different_seeds_drift_apart():
    a = Weave(32, 16, seed=1).run(50)
    b = Weave(32, 16, seed=2).run(50)
    assert a.phase != b.phase


def test_the_wiring_is_an_honest_graph():
    w = Weave(32, 16, seed=11001)
    # every wire runs both ways, nobody is wired to themselves
    for i, adj in enumerate(w.edges):
        assert i not in adj
        assert len(set(adj)) == len(adj)
        for j in adj:
            assert i in w.edges[j]
    # four grid wires each, plus whatever shortcuts landed on you
    assert all(d >= 4 for d in w.degree)
    assert len(w.shortcuts) > 0
    # a shortcut must actually be one: at least a quarter-world apart on the torus
    for a, b in w.shortcuts:
        ax, ay = a % w.width, a // w.width
        bx, by = b % w.width, b // w.width
        dx = min(abs(ax - bx), w.width - abs(ax - bx))
        dy = min(abs(ay - by), w.height - abs(ay - by))
        assert dx + dy >= (w.width + w.height) // 8


def test_clocks_stay_on_the_circle_and_loudness_in_bounds():
    w = Weave(24, 12, seed=5).run(300)
    assert all(0.0 <= p < TAU for p in w.phase)
    assert all(0.0 <= t <= 1.0 for t in w.loudnesses())
    assert not any(math.isnan(p) for p in w.phase)


def test_grip_pinned_tight_is_one_big_flash():
    """Homeostat off, gain pinned high: the graph locks into near-total sync."""
    w = Weave(32, 16, seed=11001, learn=0.0, gain0=4.0).run(600)
    assert w.order() > 0.8


def test_no_grip_is_static():
    """Homeostat off, gain zero: every clock wanders alone; coherence ~ 0."""
    w = Weave(32, 16, seed=11001, learn=0.0, gain0=0.0).run(600)
    assert w.order() < 0.15


def test_the_homeostat_holds_the_edge():
    """The actual rule: with every node tuning its own grip by ear, global
    coherence sits between the two extremes above — and never settles."""
    for seed in (11001, 7):
        w = Weave(32, 16, seed=seed)
        w.run(150)  # let the opening transient pass
        rs = _r_samples(w)
        mean_r = sum(rs) / len(rs)
        assert 0.1 < mean_r < 0.7
        assert max(rs) < 0.85
        # never freezes: coherence keeps breathing, sample to sample
        assert max(rs) - min(rs) > 0.05
        # and the gains found their own level, away from both walls
        assert 0.2 < w.mean_gain() < w.gain_max - 0.2


def test_gain_stays_clamped():
    w = Weave(24, 12, seed=3, learn=8.0)  # absurdly twitchy tuner
    w.run(400)
    assert all(0.0 <= g <= w.gain_max for g in w.gain)


def test_glyph_frame_is_the_right_shape():
    w = Weave(20, 9, seed=2).run(50)
    lines = glyph_frame(w).split("\n")
    assert len(lines) == 9
    assert all(len(line) == 20 for line in lines)
    assert all(c in GLYPHS for line in lines for c in line)


def test_svg_is_wellformed_and_draws_every_node():
    w = Weave(20, 9, seed=11001).run(120)
    root = ET.fromstring(render_svg(w))
    assert root.tag.endswith("svg")
    circles = [el for el in root.iter() if el.tag.endswith("circle")]
    paths = [el for el in root.iter() if el.tag.endswith("path")]
    assert len(circles) >= w.n  # a body per node; the loud wear halos too
    assert len(paths) == len(w.shortcuts)
