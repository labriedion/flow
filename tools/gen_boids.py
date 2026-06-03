"""Render an example still for boids/examples/ — a pure-Python reimplementation
of the same three flocking rules as the browser project (separation, alignment,
cohesion), rendered to a PNG with no third-party libraries.

We run the flock for a while so structure emerges, recording a short tail of each
boid's recent positions, then draw those tails as fading streaks coloured by
speed. Additive blending over a dark background gives the lanes their glow.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pngcanvas import write_rgb_png

W, H = 900, 560
COUNT = 900
STEPS = 320
TAIL = 14                      # how many recent positions form each streak
SEED = 7

PERCEPTION = 60.0
SEPARATION = 22.0
MAX_SPEED = 3.2
MAX_FORCE = 0.07
SEP_W, ALIGN_W, COH_W = 1.5, 1.1, 0.9

BG = (7, 9, 16)
# "Starling" gradient (matches a palette in the browser project), by speed.
STOPS = [(27, 42, 107), (58, 109, 240), (122, 215, 255), (223, 246, 255)]


def sample(stops, t):
    t = max(0.0, min(0.9999, t)) * (len(stops) - 1)
    i = int(t)
    f = t - i
    a, b = stops[i], stops[i + 1]
    return (a[0] + (b[0] - a[0]) * f,
            a[1] + (b[1] - a[1]) * f,
            a[2] + (b[2] - a[2]) * f)


def limit(x, y, m):
    n = math.hypot(x, y)
    if n > m and n > 0:
        return x / n * m, y / n * m
    return x, y


def steer(dx, dy, vx, vy):
    n = math.hypot(dx, dy)
    if n == 0:
        return 0.0, 0.0
    dvx = dx / n * MAX_SPEED - vx
    dvy = dy / n * MAX_SPEED - vy
    return limit(dvx, dvy, MAX_FORCE)


def simulate():
    rng = random.Random(SEED)
    boids = []
    for _ in range(COUNT):
        a = rng.random() * math.tau
        sp = MAX_SPEED * (0.5 + rng.random() * 0.5)
        boids.append([rng.random() * W, rng.random() * H,
                      math.cos(a) * sp, math.sin(a) * sp])
    tails = [[] for _ in range(COUNT)]
    cell = max(PERCEPTION, SEPARATION)        # grid covers the larger radius
    perc2, sep2 = PERCEPTION ** 2, SEPARATION ** 2
    max2 = max(perc2, sep2)

    for step in range(STEPS):
        # Spatial hash so neighbour search is near O(n).
        grid = {}
        for i, b in enumerate(boids):
            key = (int(b[0] // cell), int(b[1] // cell))
            grid.setdefault(key, []).append(i)

        for i, me in enumerate(boids):
            cx, cy = int(me[0] // cell), int(me[1] // cell)
            ax = ay = cxs = cys = sx = sy = 0.0
            an = cn = 0
            for gx in (cx - 1, cx, cx + 1):
                for gy in (cy - 1, cy, cy + 1):
                    for j in grid.get((gx, gy), ()):
                        if j == i:
                            continue
                        o = boids[j]
                        dx, dy = o[0] - me[0], o[1] - me[1]
                        d2 = dx * dx + dy * dy
                        if d2 > max2 or d2 == 0:
                            continue
                        if d2 < perc2:        # alignment + cohesion
                            ax += o[2]; ay += o[3]; an += 1
                            cxs += o[0]; cys += o[1]; cn += 1
                        if d2 < sep2:          # separation (own radius)
                            d = math.sqrt(d2)
                            sx -= dx / d / d
                            sy -= dy / d / d
            fx = fy = 0.0
            if an:
                s = steer(ax / an, ay / an, me[2], me[3])
                fx += s[0] * ALIGN_W; fy += s[1] * ALIGN_W
            if cn:
                s = steer(cxs / cn - me[0], cys / cn - me[1], me[2], me[3])
                fx += s[0] * COH_W; fy += s[1] * COH_W
            if sx or sy:
                s = steer(sx, sy, me[2], me[3])
                fx += s[0] * SEP_W; fy += s[1] * SEP_W
            me[2] += fx; me[3] += fy
            me[2], me[3] = limit(me[2], me[3], MAX_SPEED)
            # Match boids.js: keep a small minimum speed so nobody stalls.
            sp = math.hypot(me[2], me[3])
            if 0 < sp < MAX_SPEED * 0.25:
                t = (MAX_SPEED * 0.25) / sp
                me[2] *= t; me[3] *= t

        for i, me in enumerate(boids):
            me[0] = (me[0] + me[2]) % W
            me[1] = (me[1] + me[3]) % H
            if step >= STEPS - TAIL:
                tails[i].append((me[0], me[1], math.hypot(me[2], me[3])))
        if step % 80 == 0:
            print(f"  step {step}/{STEPS}", file=sys.stderr)
    return tails


def add_pixel(buf, x, y, color, a):
    if 0 <= x < W and 0 <= y < H:
        p = (y * W + x) * 3
        for k in range(3):
            v = buf[p + k] + color[k] * a
            buf[p + k] = 255 if v > 255 else int(v)


def draw_line(buf, x0, y0, x1, y1, color, a):
    # Wrapped tails can jump across the torus seam; skip those long segments.
    if abs(x1 - x0) > W / 2 or abs(y1 - y0) > H / 2:
        return
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for s in range(steps + 1):
        t = s / steps
        add_pixel(buf, int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), color, a)


def main():
    tails = simulate()
    buf = bytearray(BG * (W * H))
    for tail in tails:
        for k in range(1, len(tail)):
            x0, y0, _ = tail[k - 1]
            x1, y1, sp = tail[k]
            color = sample(STOPS, sp / MAX_SPEED)
            alpha = 0.34 * (k / len(tail))        # brighter towards the head
            draw_line(buf, x0, y0, x1, y1, color, alpha)
        if tail:
            hx, hy, sp = tail[-1]
            head = sample(STOPS, min(1.0, sp / MAX_SPEED + 0.2))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    add_pixel(buf, int(hx) + dx, int(hy) + dy, head, 0.5)

    out = os.path.join(os.path.dirname(__file__), "..", "boids", "examples", "boids.png")
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_rgb_png(out, W, H, buf)
    print("wrote", out)


if __name__ == "__main__":
    main()
