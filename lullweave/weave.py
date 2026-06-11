"""The weave — wired-up nodes, one rule: pull toward whoever is loudest nearby.

Every node is a tiny oscillator working its way round its own cycle: dark,
brightening, a flash at the top, dark again. Its loudness is how close to the
flash it is. The entire rule is that each node leans its own clock toward its
neighbours' clocks, *harder toward the loud ones* — whoever is shining right
now gets the pull. Nobody hears the whole graph; every node knows only the
handful of wires it owns.

The wires: nodes sit on a grid (that's just where they stand — the terminal
draws them there) and are wired to their four grid neighbours, the world
wrapped so no node is special. A sprinkle of long-range shortcuts is then
thrown across the graph, so a flash can leap to somewhere far away that the
glyphs give you no warning of. Small world, hidden wires.

The brief's twist — *tuned to sit right at the edge of chaos* — is not a dial
we set; it's the second half of the rule, and it's local too. Each node keeps
its own coupling gain and adjusts it by ear: surrounded by lockstep consensus,
it gets bored and loosens its grip; lost in incoherent noise, it tightens.
Every node homeostats its own neighbourhood toward half-coherence, and what
falls out globally is a weave that never freezes into one big flash and never
boils into static — patches of synchrony knit, fray, and re-knit forever,
waves of light chasing the hidden shortcuts. The tests pin all three claims:
gain pinned high syncs, gain pinned at zero is noise, the homeostat holds the
middle.

Pure stdlib, deterministic by seed: the rng wires the graph and deals the
clocks, then the dynamics are arithmetic — same seed, same weave, forever.
Rendering lives in render.py; the terminal animation in cli.py.
"""

import cmath
import math
import random

TAU = 2.0 * math.pi


class Weave:
    def __init__(self, width=72, height=28, seed=11001, *,
                 shortcut_frac=0.08, omega=0.35, omega_spread=0.08,
                 glare=4.0, r_target=0.55, learn=0.6, gain0=1.0,
                 gain_max=4.0, dt=0.12):
        self.width = int(width)
        self.height = int(height)
        self.n = self.width * self.height
        self.seed = seed
        rng = random.Random(seed)

        self.glare = glare            # how sharply loudness peaks at the flash
        self.r_target = r_target      # the half-coherence every node homeostats toward
        self.learn = learn            # how fast a node retunes its gain
        self.gain_max = gain_max      # a grip can only get so tight
        self.dt = dt

        # ---- the wiring: grid neighbours plus hidden long-range shortcuts ----
        self.edges = self._wire(rng, shortcut_frac)
        self.degree = [len(adj) for adj in self.edges]

        # ---- the nodes: a clock, a temperament, a grip --------------------------
        self.phase = [rng.uniform(0.0, TAU) for _ in range(self.n)]
        self.omega = [rng.gauss(omega, omega_spread) for _ in range(self.n)]
        self.gain = [gain0] * self.n
        self.tick = 0

    def _wire(self, rng, shortcut_frac):
        """Four grid wires each (the world wraps), then the shortcuts.

        Shortcuts are extra edges thrown between far-apart nodes — far in grid
        distance, so each one genuinely stitches together two places the local
        wiring would take many hops to connect.
        """
        w, h = self.width, self.height
        edges = [[] for _ in range(self.n)]

        def idx(x, y):
            return (y % h) * w + (x % w)

        for y in range(h):
            for x in range(w):
                i = idx(x, y)
                edges[i].append(idx(x + 1, y))
                edges[i].append(idx(x - 1, y))
                edges[i].append(idx(x, y + 1))
                edges[i].append(idx(x, y - 1))

        self.shortcuts = []
        want = round(shortcut_frac * self.n)
        guard = 0
        while len(self.shortcuts) < want and guard < want * 50:
            guard += 1
            a = rng.randrange(self.n)
            b = rng.randrange(self.n)
            ax, ay = a % w, a // w
            bx, by = b % w, b // w
            dx = min(abs(ax - bx), w - abs(ax - bx))
            dy = min(abs(ay - by), h - abs(ay - by))
            # a shortcut must actually be one: at least a quarter-world apart
            if dx + dy < (w + h) // 8 or b in edges[a]:
                continue
            edges[a].append(b)
            edges[b].append(a)
            self.shortcuts.append((a, b))
        return edges

    # ---- loudness: how close to the flash a clock is ----------------------------

    def loudness(self, i):
        """0 in the dark, 1 mid-flash, peaked hard by glare."""
        return ((1.0 + math.cos(self.phase[i])) / 2.0) ** self.glare

    def loudnesses(self):
        g = self.glare
        return [((1.0 + math.cos(p)) / 2.0) ** g for p in self.phase]

    # ---- one step of the rule ------------------------------------------------------

    def step(self):
        """Every node leans toward whoever is loudest nearby, then retunes its
        grip by how coherent the neighbourhood already sounds. All of it from
        the same snapshot, so order never matters."""
        phase, gain, dt = self.phase, self.gain, self.dt
        loud = self.loudnesses()

        new_phase = [0.0] * self.n
        new_gain = list(gain)
        for i in range(self.n):
            pi = phase[i]
            pull = 0.0
            # the neighbourhood's clock-hands, mine included, summed as one arrow:
            # how long that arrow is, is how coherent we already sound
            arrow = cmath.exp(1j * pi)
            for j in self.edges[i]:
                pull += loud[j] * math.sin(phase[j] - pi)
                arrow += cmath.exp(1j * phase[j])
            deg = self.degree[i]
            new_phase[i] = (pi + dt * (self.omega[i] + gain[i] * pull / deg)) % TAU

            # the homeostat: bored by consensus -> loosen; lost in noise -> tighten
            r_here = abs(arrow) / (deg + 1)
            g = gain[i] + dt * self.learn * (self.r_target - r_here)
            new_gain[i] = min(self.gain_max, max(0.0, g))

        self.phase = new_phase
        self.gain = new_gain
        self.tick += 1

    def run(self, steps):
        for _ in range(steps):
            self.step()
        return self

    # ---- inspection ------------------------------------------------------------------

    def order(self):
        """Global coherence r in [0, 1]: 0 is static, 1 is one big flash.
        Nothing in the weave can see this number — that's the point."""
        return abs(sum(cmath.exp(1j * p) for p in self.phase)) / self.n

    def mean_gain(self):
        return sum(self.gain) / self.n
