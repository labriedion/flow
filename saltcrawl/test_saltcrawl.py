"""Tests for the saltcrawl swarm: drift, growth, the split, and the torus."""

import xml.etree.ElementTree as ET

from .swarm import Grain, Swarm
from .render import render_svg


def _snapshot(swarm):
    return [(g.x, g.y, g.heading, g.mass, g.gen) for g in swarm.grains]


def test_same_seed_same_crawl():
    a = Swarm(seed=99).run(250)
    b = Swarm(seed=99).run(250)
    assert _snapshot(a) == _snapshot(b)
    assert len(a.relics) == len(b.relics)


def test_the_colony_grows_from_one_grain():
    s = Swarm(seed=7001)
    assert s.population() == 1
    s.run(300)
    assert s.population() > 20
    assert max(g.gen for g in s.grains) >= 3


def test_a_split_conserves_mass_exactly():
    """Switch feeding off, start fat: one step later there are two grains
    carrying exactly the parent's mass between them."""
    s = Swarm(seed=5, grow=0.0)
    s.grains[0].mass = 3.0
    s.step()
    assert s.population() == 2
    assert s.total_mass() == 3.0
    assert all(g.mass == 1.5 for g in s.grains)
    assert all(g.gen == 1 for g in s.grains)
    # The parent's walk was archived, not lost.
    assert len(s.relics) == 1


def test_mass_only_enters_by_feeding():
    """With feeding off, total mass is invariant no matter how the swarm
    drifts and splits."""
    s = Swarm(seed=13, grow=0.0)
    for g in s.grains:
        g.mass = 2.5
    before = s.total_mass()
    s.run(200)
    assert abs(s.total_mass() - before) < 1e-9


def test_crowding_starves_the_interior():
    """A packed grain grows far slower than a lone grain on open ground.
    Speed 0 keeps both groups where they were put, so the comparison is
    purely about the crowd."""
    lone = Swarm(seed=1, speed=0.0)
    lone.run(5)
    lone_gain = lone.total_mass() - 1.0

    packed = Swarm(seed=2, speed=0.0)
    g0 = packed.grains[0]
    packed.grains = [Grain(g0.x, g0.y, 0.0, 1.0, 0) for _ in range(64)]
    packed.run(5)
    packed_gain = (packed.total_mass() - 64) / 64
    assert packed_gain < lone_gain / 4


def test_feeding_never_passes_the_threshold():
    """Only the split crosses the line: no grain's mass ever exceeds what it
    was handed at birth or the threshold, however long the crawl runs."""
    s = Swarm(seed=17, cap=32)  # a tight cap, so grains sit at the ceiling
    s.run(400)
    assert all(g.mass <= s.threshold + 1e-9 for g in s.grains)


def test_the_world_is_a_torus():
    s = Swarm(seed=42)
    s.run(500)
    for g in s.grains:
        assert 0 <= g.x < s.width
        assert 0 <= g.y < s.height
    # Trails never draw across the world: every step inside a segment is small.
    for _, trail in s.all_trails():
        for seg in trail:
            for (x0, y0), (x1, y1) in zip(seg, seg[1:]):
                assert abs(x1 - x0) <= s.width / 2
                assert abs(y1 - y0) <= s.height / 2


def test_population_respects_the_cap():
    s = Swarm(seed=8, cap=40)
    s.run(600)
    assert s.population() <= 40
    # A cap below 1 can't be honoured (the first grain exists); it clamps to
    # one lone grain that never splits.
    lone = Swarm(seed=8, cap=0)
    lone.run(200)
    assert lone.population() == 1


def test_svg_is_wellformed_and_draws_the_trails():
    s = Swarm(seed=3).run(300)
    svg = render_svg(s)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    polylines = [el for el in root.iter() if el.tag.endswith("polyline")]
    circles = [el for el in root.iter() if el.tag.endswith("circle")]
    assert len(polylines) >= s.population()  # at least every living walk
    assert len(circles) == s.population()
