"""Tiny test-signal synthesizers, so the reverb is usable with no input file.

Reverb only reveals itself when you feed it something — a sharp transient to
hear the echo train, or a musical pluck to hear the tail bloom. These generators
make dry material to pour into `reverberate`, all from the standard library.

    >>> from reverb.synth import click, pluck, arpeggio
    >>> len(click())                       # a one-sample impulse, padded
    22050
    >>> tone = pluck(220.0, 0.5, 22050)    # a half-second decaying note
    >>> max(abs(s) for s in tone) <= 1.0
    True

`click` is a unit impulse — the cleanest way to see a comb filter's geometric
echoes. `pluck` is a Karplus-Strong string, which sounds like a plucked guitar.
`arpeggio` strings several plucks together into a little phrase, which is what
`--demo` reverberates.
"""

from __future__ import annotations

import random
from array import array
from math import pi, sin


def click(sample_rate: int = 22050, length_samples: int | None = None) -> array:
    """A unit impulse: a single 1.0 followed by silence.

    Fed to a comb filter, this exposes the raw echo train; fed to the reverb, it
    is the room's *impulse response*. Defaults to one second of buffer so the
    tail has somewhere to land.
    """
    n = length_samples if length_samples is not None else sample_rate
    if n <= 0:
        raise ValueError("length must be positive")
    out = array("d", bytes(8 * n))
    out[0] = 1.0
    return out


def pluck(freq: float, dur: float, sample_rate: int = 22050,
          seed: int | None = 0) -> array:
    """A plucked-string tone via Karplus-Strong synthesis.

    A short burst of noise is loaded into a delay line of length
    `sample_rate / freq`; each sample is replaced by the average of itself and
    its neighbour, which both sustains a pitch at `freq` and gently lowpasses the
    sound so it decays from bright to dull — exactly like a real string. The
    result is normalised to a peak of about 0.9. Deterministic for a given seed.
    """
    if freq <= 0:
        raise ValueError("freq must be positive")
    if dur <= 0:
        raise ValueError("dur must be positive")

    n = int(dur * sample_rate)
    period = max(2, int(round(sample_rate / freq)))
    rng = random.Random(seed)
    buf = [rng.uniform(-1.0, 1.0) for _ in range(period)]

    out = array("d", bytes(8 * n))
    pos = 0
    for i in range(n):
        cur = buf[pos]
        nxt = buf[(pos + 1) % period]
        out[i] = cur
        # Karplus-Strong lowpass-feedback: slight decay each pass.
        buf[pos] = 0.498 * (cur + nxt)
        pos = (pos + 1) % period

    # Apply a short fade-out envelope tail and normalise.
    peak = max((abs(s) for s in out), default=0.0)
    if peak > 0:
        scale = 0.9 / peak
        for i in range(n):
            out[i] *= scale
    return out


def arpeggio(sample_rate: int = 22050, note_dur: float = 0.35,
             root: float = 220.0) -> array:
    """A short ascending arpeggio of plucks — the default `--demo` material.

    Plays root, major third, fifth and octave (a major chord, rolled), each a
    `pluck`, concatenated. Deterministic.
    """
    # Equal-temperament ratios for a major triad plus the octave.
    ratios = (1.0, 5 / 4, 3 / 2, 2.0)
    out = array("d")
    for k, r in enumerate(ratios):
        note = pluck(root * r, note_dur, sample_rate, seed=k)
        out.extend(note)
    return out
