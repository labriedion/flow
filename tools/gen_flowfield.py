"""Render an example flow-field image for flowfield/examples/ in pure Python,
mirroring the browser project: particles drift through a 3D simplex-noise field,
accumulating additive color trails which are then tone-mapped.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pngcanvas import write_rgb_png

W, H = 800, 500
PARTICLES = 2600
STEPS = 420
SPEED = 1.3
NOISE_SCALE = 0.0019
CURL = 2.6
TIME_WARP = 0.0016
SEED = 20240602

TAU = math.pi * 2

# "Aurora" palette (matches a project preset): bg + gradient stops.
BG = (5, 7, 13)
STOPS = [(0, 57, 115), (10, 133, 237), (33, 212, 253), (67, 233, 123), (184, 255, 159)]


# ---- Simplex noise (port of noise.js) ------------------------------------
GRAD3 = [
    [1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0],
    [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
    [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1],
]
F3 = 1.0 / 3.0
G3 = 1.0 / 6.0


def mulberry32(seed):
    a = seed & 0xFFFFFFFF

    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = (t ^ (t >> 15)) * (1 | t) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) & 0xFFFFFFFF ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rnd


class Simplex:
    def __init__(self, seed):
        rnd = mulberry32(seed)
        p = list(range(256))
        for i in range(255, 0, -1):
            n = int(rnd() * (i + 1))
            p[i], p[n] = p[n], p[i]
        self.perm = [p[i & 255] for i in range(512)]
        self.pm12 = [self.perm[i] % 12 for i in range(512)]

    def noise3(self, x, y, z):
        perm, pm12 = self.perm, self.pm12
        s = (x + y + z) * F3
        i = math.floor(x + s); j = math.floor(y + s); k = math.floor(z + s)
        t = (i + j + k) * G3
        x0 = x - (i - t); y0 = y - (j - t); z0 = z - (k - t)
        if x0 >= y0:
            if y0 >= z0:
                i1, j1, k1, i2, j2, k2 = 1, 0, 0, 1, 1, 0
            elif x0 >= z0:
                i1, j1, k1, i2, j2, k2 = 1, 0, 0, 1, 0, 1
            else:
                i1, j1, k1, i2, j2, k2 = 0, 0, 1, 1, 0, 1
        else:
            if y0 < z0:
                i1, j1, k1, i2, j2, k2 = 0, 0, 1, 0, 1, 1
            elif x0 < z0:
                i1, j1, k1, i2, j2, k2 = 0, 1, 0, 0, 1, 1
            else:
                i1, j1, k1, i2, j2, k2 = 0, 1, 0, 1, 1, 0
        x1, y1, z1 = x0 - i1 + G3, y0 - j1 + G3, z0 - k1 + G3
        x2, y2, z2 = x0 - i2 + 2 * G3, y0 - j2 + 2 * G3, z0 - k2 + 2 * G3
        x3, y3, z3 = x0 - 1 + 3 * G3, y0 - 1 + 3 * G3, z0 - 1 + 3 * G3
        ii, jj, kk = i & 255, j & 255, k & 255
        n = 0.0
        for (xo, yo, zo, io, jo, ko) in (
            (x0, y0, z0, 0, 0, 0), (x1, y1, z1, i1, j1, k1),
            (x2, y2, z2, i2, j2, k2), (x3, y3, z3, 1, 1, 1),
        ):
            tt = 0.6 - xo * xo - yo * yo - zo * zo
            if tt >= 0:
                gi = pm12[ii + io + perm[jj + jo + perm[kk + ko]]]
                g = GRAD3[gi]
                tt *= tt
                n += tt * tt * (g[0] * xo + g[1] * yo + g[2] * zo)
        return 32 * n


def build_ramp():
    ramp = []
    segs = len(STOPS) - 1
    for i in range(256):
        f = (i / 255) * segs
        idx = min(int(f), segs - 1)
        local = f - idx
        a, b = STOPS[idx], STOPS[idx + 1]
        ramp.append(tuple(a[c] + (b[c] - a[c]) * local for c in range(3)))
    return ramp


def main():
    rng = mulberry32(SEED ^ 0x9E3779B9)
    noise = Simplex(SEED)
    ramp = build_ramp()
    acc = [0.0] * (W * H * 3)  # additive accumulation buffer

    def add(px, py, col, w):
        if 0 <= px < W and 0 <= py < H:
            o = (py * W + px) * 3
            acc[o] += col[0] * w
            acc[o + 1] += col[1] * w
            acc[o + 2] += col[2] * w

    z = 0.0
    for _ in range(PARTICLES):
        x = rng() * W
        y = rng() * H
        life = int(60 + rng() * STEPS)
        for _s in range(min(life, STEPS)):
            n = noise.noise3(x * NOISE_SCALE, y * NOISE_SCALE, z)
            angle = n * TAU * CURL
            nx = x + math.cos(angle) * SPEED
            ny = y + math.sin(angle) * SPEED
            ci = ((angle % TAU) + TAU) % TAU / TAU
            col = ramp[min(int(ci * 256), 255)]
            # Deposit a soft additive dab at the segment endpoint.
            ix, iy = int(nx), int(ny)
            add(ix, iy, col, 0.05)
            add(ix + 1, iy, col, 0.025)
            add(ix, iy + 1, col, 0.025)
            x, y = nx, ny
            if x < 0 or x >= W or y < 0 or y >= H:
                break
        z += TIME_WARP * 0.25

    # Tone-map the accumulation over the background.
    buf = bytearray(W * H * 3)
    for i in range(W * H):
        o = i * 3
        for c in range(3):
            v = BG[c] + 255 * (1 - math.exp(-acc[o + c] / 255 * 1.6))
            buf[o + c] = 0 if v < 0 else (255 if v > 255 else int(v))

    out = os.path.join(os.path.dirname(__file__), "..", "flowfield", "examples", "flowfield.png")
    write_rgb_png(os.path.abspath(out), W, H, buf)
    print("wrote", os.path.abspath(out))


if __name__ == "__main__":
    main()
