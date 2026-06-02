"""Render an example Mandelbrot image for fractal/examples/ using the same
escape-time + smooth-coloring math as the browser project, in pure Python.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pngcanvas import write_rgb_png

W, H = 640, 400
MAX_ITER = 600

# A zoomed view into the "seahorse valley" — spirals and filaments.
CX, CY = -0.74364, 0.13182
SCALE = 0.0055         # vertical half-height in the complex plane
DENSITY = 34
SHIFT = 80

# "Inferno" cosine palette (matches the project preset).
TAU = math.pi * 2
FREQ = (1.0, 1.0, 1.0)
PHASE = (0.0, 0.15, 0.30)
BIAS = (0.5, 0.35, 0.2)
PSIZE = 1024


def build_palette():
    pal = []
    for i in range(PSIZE):
        t = i / PSIZE
        r = 255 * (BIAS[0] + 0.5 * math.cos(TAU * (FREQ[0] * t + PHASE[0])))
        g = 255 * (BIAS[1] + 0.5 * math.cos(TAU * (FREQ[1] * t + PHASE[1])))
        b = 255 * (BIAS[2] + 0.5 * math.cos(TAU * (FREQ[2] * t + PHASE[2])))
        pal.append((_clamp(r), _clamp(g), _clamp(b)))
    return pal


def _clamp(v):
    return 0 if v < 0 else (255 if v > 255 else int(v))


def main():
    pal = build_palette()
    aspect = W / H
    re_span = SCALE * aspect
    im_span = SCALE
    escape = 64.0
    log_escape = math.log(math.log(math.sqrt(escape)))
    log2 = math.log(2)
    buf = bytearray(W * H * 3)

    p = 0
    for py in range(H):
        im0 = CY + (py / H - 0.5) * 2 * im_span
        for px in range(W):
            re0 = CX + (px / W - 0.5) * 2 * re_span
            zr = zi = 0.0
            zr2 = zi2 = 0.0
            n = 0
            while zr2 + zi2 <= escape and n < MAX_ITER:
                zi = 2 * zr * zi + im0
                zr = zr2 - zi2 + re0
                zr2 = zr * zr
                zi2 = zi * zi
                n += 1
            if n >= MAX_ITER:
                buf[p] = buf[p + 1] = buf[p + 2] = 0
            else:
                mag = math.sqrt(zr2 + zi2)
                mu = n + 1 - (math.log(math.log(mag)) - log_escape) / log2
                idx = int((mu * DENSITY + SHIFT) % PSIZE)
                r, g, b = pal[idx]
                buf[p] = r
                buf[p + 1] = g
                buf[p + 2] = b
            p += 3
        if py % 40 == 0:
            print(f"  row {py}/{H}", file=sys.stderr)

    out = os.path.join(os.path.dirname(__file__), "..", "fractal", "examples", "mandelbrot.png")
    write_rgb_png(os.path.abspath(out), W, H, buf)
    print("wrote", os.path.abspath(out))


if __name__ == "__main__":
    main()
