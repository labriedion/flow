"""Render audio artifacts for driftwave/examples/: a short generative ambient
WAV clip plus a waveform PNG. Mirrors the browser engine's voices (detuned-saw
pads + probabilistic plucks) using only the standard library.
"""

import math
import os
import random
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(__file__))
from pngcanvas import write_rgb_png

RATE = 22050
DURATION = 16.0
TEMPO = 76
DENSITY = 0.6
SEED = 7

SCALE = [0, 2, 4, 7, 9]          # major pentatonic
ROOT_MIDI = 12 * (4 + 1) + 9     # A4-ish base
N = int(RATE * DURATION)
buf = [0.0] * N


def midi_to_freq(m):
    return 440.0 * (2 ** ((m - 69) / 12))


def degree_to_midi(degree):
    octs = degree // len(SCALE)
    idx = degree % len(SCALE)
    return ROOT_MIDI + SCALE[idx] + 12 * octs


def add(sample_index, value):
    if 0 <= sample_index < N:
        buf[sample_index] += value


def play_pad(freq, t0, dur):
    start = int(t0 * RATE)
    length = int(dur * RATE)
    attack = int(length * 0.4)
    for s in range(length):
        i = start + s
        if i >= N:
            break
        # Slow swell envelope.
        if s < attack:
            env = (s / attack) * 0.10
        else:
            env = (1 - (s - attack) / (length - attack)) * 0.10
        t = s / RATE
        # Three detuned saws (additive, 4 harmonics each).
        v = 0.0
        for detune in (-0.04, 0.0, 0.04):
            f = freq * (2 ** (detune / 12))
            for k in range(1, 5):
                v += math.sin(2 * math.pi * f * k * t) / k
        add(i, env * v * 0.18)


def play_pluck(freq, t0):
    start = int(t0 * RATE)
    length = int(1.6 * RATE)
    for s in range(length):
        i = start + s
        if i >= N:
            break
        t = s / RATE
        env = 0.22 * math.exp(-t * 3.0)
        # Triangle-ish: fundamental + soft third harmonic.
        v = math.sin(2 * math.pi * freq * t) + 0.15 * math.sin(2 * math.pi * freq * 3 * t)
        add(i, env * v)


def main():
    rng = random.Random(SEED)
    beat = 60 / TEMPO
    step = beat / 2
    steps = int(DURATION / step)
    last_degree = 4
    for s in range(steps):
        t = s * step
        if s % 8 == 0:
            base = degree_to_midi(rng.choice([0, 3, 4, 5]))
            play_pad(midi_to_freq(base - 12), t, beat * 4)
            play_pad(midi_to_freq(base - 12 + 7), t, beat * 4)
        if rng.random() < DENSITY:
            move = rng.choice([-2, -1, -1, 0, 1, 1, 2])
            last_degree = max(0, min(len(SCALE) * 2 - 1, last_degree + move))
            play_pluck(midi_to_freq(degree_to_midi(last_degree)), t)

    # Soft-limit and normalize.
    peak = max(1e-6, max(abs(v) for v in buf))
    norm = 0.9 / peak
    pcm = bytearray()
    for v in buf:
        x = math.tanh(v * norm * 1.2)
        pcm += struct.pack("<h", int(max(-1, min(1, x)) * 32767))

    base_dir = os.path.join(os.path.dirname(__file__), "..", "driftwave", "examples")
    wav_path = os.path.abspath(os.path.join(base_dir, "driftwave-sample.wav"))
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(bytes(pcm))
    print("wrote", wav_path)

    render_waveform(buf, norm, os.path.join(base_dir, "waveform.png"))


def render_waveform(samples, norm, out_path):
    W, H = 900, 220
    bg = (10, 11, 20)
    buf = bytearray(bg * (W * H))

    def setpx(x, y, col):
        if 0 <= x < W and 0 <= y < H:
            o = (y * W + x) * 3
            buf[o], buf[o + 1], buf[o + 2] = col

    # Per-column min/max envelope, filled with a vertical gradient stroke.
    per = max(1, len(samples) // W)
    mid = H // 2
    for x in range(W):
        chunk = samples[x * per:(x + 1) * per]
        if not chunk:
            continue
        lo = min(chunk) * norm
        hi = max(chunk) * norm
        y0 = int(mid - hi * (H * 0.45))
        y1 = int(mid - lo * (H * 0.45))
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(y0, y1 + 1):
            f = (y - y0) / max(1, y1 - y0)
            col = (int(185 - 90 * f), int(140 + 30 * f), int(255 - 18 * f))
            setpx(x, y, col)

    write_rgb_png(os.path.abspath(out_path), W, H, buf)
    print("wrote", os.path.abspath(out_path))


if __name__ == "__main__":
    main()
