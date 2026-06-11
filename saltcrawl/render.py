"""Render a Swarm's trails to a standalone SVG.

The drawing is the family tree laid on the ground: every trail ever walked,
generation by generation. Early generations are thick and dim — the trunk of
the crawl — and each split thins and brightens the line, out to the pale
live frontier. Trails are split into segments wherever the grain wrapped, so
nothing ever streaks across the whole image; the crawl just leaves one side
and carries on from the other, edgeless.
"""

# Generation ramp: from deep brine to white salt.
_STOPS = [
    (0.0, (38, 66, 84)),     # deep brine — the oldest walks
    (0.45, (94, 158, 162)),  # verdigris
    (0.75, (167, 216, 209)), # frost
    (1.0, (240, 250, 248)),  # fresh salt — the live frontier
]


def _colour(t):
    t = max(0.0, min(1.0, t))
    lo, hi = _STOPS[0], _STOPS[-1]
    for i in range(len(_STOPS) - 1):
        if _STOPS[i][0] <= t <= _STOPS[i + 1][0]:
            lo, hi = _STOPS[i], _STOPS[i + 1]
            break
    f = (t - lo[0]) / max(1e-9, hi[0] - lo[0])
    r, g, b = (round(a + (b_ - a) * f) for a, b_ in zip(lo[1], hi[1]))
    return f"#{r:02x}{g:02x}{b:02x}"


def _thin(points, stride):
    """Every stride-th point, but always the first and the last — enough for
    a wobbly walk, and it keeps the artifact a sane size."""
    if len(points) <= 2 or stride <= 1:
        return points
    kept = points[::stride]
    if kept[-1] != points[-1]:
        kept.append(points[-1])
    return kept


def render_svg(swarm, scale=2.0, stride=3):
    """Return the swarm's trails as a standalone SVG string."""
    w = swarm.width * scale
    h = swarm.height * scale
    trails = swarm.all_trails()
    max_gen = max((gen for gen, _ in trails), default=0) or 1

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
        f'viewBox="0 0 {w:.0f} {h:.0f}">',
        f'  <rect width="{w:.0f}" height="{h:.0f}" fill="#070910"/>',
        f'  <!-- saltcrawl: seed {swarm.seed}, {swarm.tick} steps, '
        f'{swarm.population()} grains alive, gen 0..{max_gen}; '
        f'the world is a torus -->',
    ]

    # Oldest trails first so the frontier draws on top of the trunk.
    for gen, trail in sorted(trails, key=lambda t: t[0]):
        t = gen / max_gen
        colour = _colour(t)
        width = max(0.6, 3.2 * (0.82 ** gen))
        opacity = 0.42 + 0.5 * t
        for seg in trail:
            pts = _thin(seg, stride)
            if len(pts) < 2:
                continue
            path = " ".join(f"{x * scale:.1f},{y * scale:.1f}" for x, y in pts)
            out.append(
                f'  <polyline points="{path}" fill="none" stroke="{colour}" '
                f'stroke-width="{width:.2f}" stroke-opacity="{opacity:.2f}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
            )

    # The living grains themselves: salt on the tip of every branch.
    for g in swarm.grains:
        out.append(
            f'  <circle cx="{g.x * scale:.1f}" cy="{g.y * scale:.1f}" '
            f'r="{(1.0 + g.mass) * scale * 0.45:.2f}" fill="#f0faf8" '
            f'fill-opacity="0.85"/>'
        )

    out.append("</svg>")
    return "\n".join(out)
