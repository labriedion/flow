"""The swarm — drifting grains, one rule: split when you grow past a threshold.

Each grain wanders (a slightly wobbly heading), feeds, and — the entire rule —
splits in two when its mass passes the threshold, each child taking half and
veering off the parent's heading in opposite directions. Feeding is throttled
by crowding: a grain packed in with neighbours grows slowly, a grain on open
ground grows fast. That one coupling is where the shape comes from. Nobody
plans a colony; the interior starves itself quiet, the frontier keeps
splitting, and what crawls out is a branching, lichen-like front that — the
brief's twist — wraps the boundary, because the world is a torus and there is
no edge for it to die against.

Every split conserves mass exactly (the children share the parent's), so the
only way the swarm gains mass is feeding — the tests pin both down. Grains
remember their trails; a parent's trail is archived as a relic when it splits,
which is what the SVG draws: the whole family tree, laid on the ground.

Pure stdlib, deterministic by seed, no rendering in here — render.py reads
the relics and draws; the terminal preview lives in cli.py.
"""

import math
import random


class Grain:
    __slots__ = ("x", "y", "heading", "mass", "gen", "trail")

    def __init__(self, x, y, heading, mass, gen):
        self.x = x
        self.y = y
        self.heading = heading
        self.mass = mass
        self.gen = gen
        # A trail is a list of polyline segments; a new segment opens whenever
        # the grain wraps, so no drawn line ever crosses the whole world.
        self.trail = [[(x, y)]]


class Swarm:
    def __init__(self, width=420.0, height=280.0, seed=7001, *,
                 threshold=2.0, grow=0.16, speed=1.4, wiggle=0.22,
                 split_angle=0.85, crowd_radius=12.0, cap=192):
        self.width = float(width)
        self.height = float(height)
        self.seed = seed
        self.rng = random.Random(seed)

        self.threshold = threshold      # split past this mass
        self.grow = grow                # feeding rate on open ground
        self.speed = speed              # drift per step
        self.wiggle = wiggle            # heading wobble (radians, stddev)
        self.split_angle = split_angle  # how hard children veer apart
        self.crowd_radius = crowd_radius  # binning scale for crowd counts
        # Safety bound on the population. The first grain always exists, so a
        # cap below 1 couldn't be honoured — clamp rather than overpromise.
        self.cap = max(1, cap)

        # One grain, mid-world, pointed wherever the seed says.
        first = Grain(self.width / 2, self.height / 2,
                      self.rng.uniform(0, 2 * math.pi), 1.0, 0)
        self.grains = [first]
        self.relics = []                # archived (gen, trail) of split parents
        self.tick = 0

    # ---- the torus ----------------------------------------------------------

    def _wrap(self, v, span):
        # Float modulo can return span itself for a tiny negative v
        # ((-1e-18) % 420.0 == 420.0), which would put a grain just off the
        # world. Fold that hair's-breadth case back to zero.
        v %= span
        return v if v < span else 0.0

    def _crowd_counts(self):
        """Grains per coarse bin — the only thing a grain knows about others."""
        counts = {}
        r = self.crowd_radius
        for g in self.grains:
            key = (int(g.x / r), int(g.y / r))
            counts[key] = counts.get(key, 0) + 1
        return counts

    # ---- one step of the rule -------------------------------------------------

    def step(self):
        counts = self._crowd_counts()
        r = self.crowd_radius
        born = []

        for g in self.grains:
            # Crowding is the one thing a grain feels about the others, and it
            # throttles everything: a starved grain barely moves and barely
            # grows — the interior crystallizes — while a grain on open ground
            # feasts and crawls at full stride. The dendrites come from here.
            crowd = counts.get((int(g.x / r), int(g.y / r)), 1) - 1
            vigour = 1.0 / (1.0 + crowd)

            # drift: wobble the heading, take a step, wrap — no edge anywhere
            g.heading += self.rng.gauss(0.0, self.wiggle)
            nx = self._wrap(g.x + math.cos(g.heading) * self.speed * vigour, self.width)
            ny = self._wrap(g.y + math.sin(g.heading) * self.speed * vigour, self.height)
            # a wrap jump opens a fresh trail segment instead of a world-long line
            if (abs(nx - g.x) > self.width / 2) or (abs(ny - g.y) > self.height / 2):
                g.trail.append([])
            g.x, g.y = nx, ny
            g.trail[-1].append((g.x, g.y))

            # feed — but the threshold is a ceiling only splitting passes:
            # grow up to it, never through it by feeding alone.
            if g.mass < self.threshold:
                g.mass = min(self.threshold, g.mass + self.grow * vigour)

            # the rule: grown past the threshold? split in two.
            if g.mass >= self.threshold and len(self.grains) + len(born) < self.cap:
                born.append(g)

        survivors = []
        for g in self.grains:
            if g not in born:
                survivors.append(g)
                continue
            # The parent becomes a relic; two children take half its mass each
            # and veer off to either side. Mass is conserved to the bit.
            self.relics.append((g.gen, g.trail))
            half = g.mass / 2.0
            for side in (-1.0, 1.0):
                h = g.heading + side * self.split_angle + self.rng.gauss(0.0, 0.1)
                survivors.append(Grain(g.x, g.y, h, half, g.gen + 1))

        self.grains = survivors
        self.tick += 1

    def run(self, steps):
        for _ in range(steps):
            self.step()
        return self

    # ---- inspection ----------------------------------------------------------

    def population(self):
        return len(self.grains)

    def total_mass(self):
        return sum(g.mass for g in self.grains)

    def all_trails(self):
        """Every trail, dead and alive: (generation, segments) pairs."""
        return self.relics + [(g.gen, g.trail) for g in self.grains]
