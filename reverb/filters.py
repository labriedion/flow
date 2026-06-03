"""DSP primitives for a Schroeder/Freeverb-style reverb — built from the math.

A reverb is, at bottom, a pile of delays feeding back on themselves. Two little
filters do all the work:

  * a **feedback comb filter** — a delay line whose output is fed back to its
    input, scaled by `feedback`. Hit it with a single click and you hear a train
    of echoes spaced `delay` samples apart, each quieter than the last by a
    factor of `feedback`. That geometric decay is the body of a reverb tail.
    Adding `damping` puts a one-pole lowpass in the feedback path, so each pass
    around the loop loses a little treble — exactly what real rooms do, where
    high frequencies are soaked up by the air and the walls faster than lows.

  * a **Schroeder allpass filter** — same delay line, but arranged so its
    *magnitude* response is flat (it passes every frequency equally) while its
    *phase* is scrambled. On its own it sounds almost like nothing; in series
    after the combs it smears the echoes together, thickening the discrete pings
    into a smooth wash without colouring the tone.

Everything here works on plain sequences of floats (lists or `array('d')`) and
returns a new `array('d')`. Standard library only.

    >>> from reverb.filters import comb
    >>> x = [1.0] + [0.0] * 9          # a unit impulse
    >>> y = comb(x, delay=3, feedback=0.5)
    >>> [round(v, 3) for v in y[:10]]
    [1.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.25, 0.0, 0.0, 0.125]

The echoes land at samples 0, 3, 6, 9 … with amplitudes 1, ½, ¼, ⅛ — the
geometric series `feedback ** k`.
"""

from __future__ import annotations

from array import array
from collections.abc import Sequence


def comb(
    samples: Sequence[float],
    delay: int,
    feedback: float,
    damping: float = 0.0,
) -> array:
    """A feedback comb filter, optionally with lowpass damping (Freeverb style).

    The recurrence is::

        y[n] = x[n] + feedback * z[n - delay]

    where `z` is the (possibly damped) feedback signal. With `damping == 0`,
    `z == y` and a unit impulse produces clean echoes of amplitude
    `feedback ** k` at samples `k * delay`. With `0 < damping < 1` a one-pole
    lowpass smooths the feedback::

        lp[n] = (1 - damping) * y[n] + damping * lp[n - 1]
        z[n]  = lp[n]

    so the loop loses high frequencies on every pass and bright echoes die away
    faster than dull ones.

    `feedback` should satisfy `abs(feedback) < 1` for a decaying (stable) tail.
    `delay` must be a positive integer number of samples.
    """
    if delay <= 0:
        raise ValueError(f"delay must be a positive integer, got {delay!r}")
    if not 0.0 <= damping < 1.0:
        raise ValueError(f"damping must be in [0, 1), got {damping!r}")

    n = len(samples)
    out = array("d", bytes(8 * n))
    buf = array("d", bytes(8 * delay))   # circular delay line of feedback signal
    pos = 0
    lp = 0.0                              # one-pole lowpass state
    keep = 1.0 - damping
    for i in range(n):
        delayed = buf[pos]
        y = samples[i] + feedback * delayed
        out[i] = y
        # Lowpass the signal we feed back around the loop.
        lp = keep * y + damping * lp
        buf[pos] = lp
        pos += 1
        if pos == delay:
            pos = 0
    return out


def allpass(samples: Sequence[float], delay: int, feedback: float) -> array:
    """A Schroeder allpass filter.

    Flat magnitude response, scrambled phase. The standard difference equation::

        z[n]      = x[n] + feedback * z[n - delay]
        y[n]      = -feedback * z[n] + z[n - delay]

    Used in series after the comb bank to diffuse the echoes into a smooth tail
    without changing the overall tone. `abs(feedback) < 1` keeps it stable; the
    classic value is around 0.5.
    """
    if delay <= 0:
        raise ValueError(f"delay must be a positive integer, got {delay!r}")

    n = len(samples)
    out = array("d", bytes(8 * n))
    buf = array("d", bytes(8 * delay))
    pos = 0
    for i in range(n):
        delayed = buf[pos]
        z = samples[i] + feedback * delayed
        out[i] = -feedback * z + delayed
        buf[pos] = z
        pos += 1
        if pos == delay:
            pos = 0
    return out


def mix(dry: Sequence[float], wet: Sequence[float], wet_amount: float) -> array:
    """Linearly blend a dry and a wet signal: `(1 - wet) * dry + wet * wet`.

    The two sequences may differ in length (a reverb tail outlives its input);
    the result is as long as the longer one, with the shorter treated as zero
    past its end.
    """
    n = max(len(dry), len(wet))
    out = array("d", bytes(8 * n))
    dry_amount = 1.0 - wet_amount
    nd, nw = len(dry), len(wet)
    for i in range(n):
        d = dry[i] if i < nd else 0.0
        w = wet[i] if i < nw else 0.0
        out[i] = dry_amount * d + wet_amount * w
    return out


def pad(samples: Sequence[float], length: int) -> array:
    """Return `samples` as an `array('d')` of exactly `length`, zero-filled or
    truncated as needed."""
    out = array("d", bytes(8 * length))
    n = min(len(samples), length)
    for i in range(n):
        out[i] = samples[i]
    return out


def delay_samples(samples: Sequence[float], shift: int) -> array:
    """Shift a signal later in time by `shift` samples (pre-delay).

    The output is `shift` samples longer; the leading `shift` samples are zero.
    A non-positive `shift` returns a plain copy.
    """
    if shift <= 0:
        return array("d", samples)
    out = array("d", bytes(8 * (len(samples) + shift)))
    for i in range(len(samples)):
        out[shift + i] = samples[i]
    return out
