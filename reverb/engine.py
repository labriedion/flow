"""A Schroeder/Freeverb-style reverb, assembled from the primitives in `filters`.

Manfred Schroeder's 1962 recipe still underlies most algorithmic reverbs: run
the signal through several **parallel comb filters** with mutually prime delays
(so their echo trains interleave instead of lining up into a flutter), sum them,
then push the sum through a couple of **series allpass filters** to diffuse the
echoes into a smooth wash. Freeverb adds one twist — lowpass *damping* inside
each comb's feedback loop — so the tail darkens as it decays, the way real rooms
do.

`reverberate` ties it together for mono or stereo:

    >>> from reverb.engine import reverberate
    >>> dry = [1.0] + [0.0] * 999          # a click
    >>> wet = reverberate(dry, 22050, room=0.8, wet=0.4)
    >>> len(wet) > len(dry)                # the tail outlives the input
    True

Knobs:
  * `room`    0..1   — bigger = longer delays and higher feedback (a larger,
                       more reverberant space).
  * `damping` 0..1   — how fast the high frequencies die in the tail.
  * `wet`     0..1   — dry/wet balance; `wet=0` returns the dry signal.
  * `predelay_ms`    — silence before the wet signal starts, in milliseconds:
                       the gap between the direct sound and the first reflection.
  * `width`   0..1   — for stereo, how far the two channels are decorrelated.

Standard library only.
"""

from __future__ import annotations

from array import array
from collections.abc import Sequence

from .filters import allpass, comb, delay_samples, mix, pad

# Freeverb's comb and allpass delays, in samples, tuned for 44.1 kHz. We scale
# them by the sample rate and by `room` so the character holds at other rates.
# The eight comb delays are mutually offset to avoid coincident echoes; the
# allpass delays are short and diffusive.
_COMB_TUNING = (1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617)
_ALLPASS_TUNING = (556, 441, 341, 225)
_REFERENCE_RATE = 44100
_STEREO_SPREAD = 23          # samples added to the right channel's delays


def _scaled(delays: Sequence[int], sample_rate: int, room: float,
            spread: int = 0) -> list[int]:
    """Scale the reference delays to this sample rate and room size."""
    # room in [0, 1] maps to a delay multiplier in roughly [0.5, 1.3], so a
    # small room has short, tight reflections and a big one long, lush ones.
    factor = (0.5 + 0.8 * room) * (sample_rate / _REFERENCE_RATE)
    out = []
    for d in delays:
        scaled = int(round(d * factor)) + spread
        out.append(max(1, scaled))
    return out


def _reverb_one(channel: Sequence[float], sample_rate: int, room: float,
                damping: float, spread: int) -> array:
    """The wet signal for a single channel: parallel combs -> series allpasses.

    Returns a tail-length array (longer than the input) at unity level; the
    caller does the dry/wet mix and pre-delay.
    """
    # Higher `room` -> higher feedback -> longer decay. Cap below 1 for stability.
    feedback = 0.7 + 0.28 * room          # 0.70 .. 0.98
    feedback = min(feedback, 0.98)

    comb_delays = _scaled(_COMB_TUNING, sample_rate, room, spread)
    allpass_delays = _scaled(_ALLPASS_TUNING, sample_rate, room=0.0, spread=spread)

    # Extend the input with silence so the tail has room to ring out. The
    # longest comb echo decays to ~ -60 dB after this many samples.
    longest = max(comb_delays)
    if feedback < 1.0:
        # samples for feedback**k to fall to 0.001  ->  k = ln(0.001)/ln(fb)
        from math import log
        n_echoes = log(0.001) / log(feedback)
        tail = int(longest * (n_echoes + 4))
    else:                                  # pragma: no cover - guarded above
        tail = longest * 50
    tail = min(tail, sample_rate * 8)      # never more than 8 s of ring-out
    work = pad(channel, len(channel) + tail)

    # Parallel comb bank: sum the eight damped combs.
    acc = array("d", bytes(8 * len(work)))
    for d in comb_delays:
        c = comb(work, d, feedback, damping=damping)
        for i in range(len(acc)):
            acc[i] += c[i]
    inv = 1.0 / len(comb_delays)
    for i in range(len(acc)):
        acc[i] *= inv

    # Series allpass diffusers.
    out: array = acc
    for d in allpass_delays:
        out = allpass(out, d, 0.5)
    return out


def reverberate(
    samples,
    sample_rate: int,
    room: float = 0.7,
    damping: float = 0.5,
    wet: float = 0.3,
    predelay_ms: float = 0.0,
    width: float = 1.0,
):
    """Apply reverb to mono or stereo audio.

    `samples` is either a flat sequence of floats (mono) or a list of channels
    (`[left, right]`, each a sequence of floats). The return type matches: a
    single `array('d')` for mono input, a list of channel arrays for stereo.

    The wet (reverberated) signal is mixed with the dry signal by `wet`
    (`wet=0` returns the dry signal unchanged, `wet=1` is fully wet). The output
    is longer than the input by the reverb tail plus any pre-delay, so the room
    is heard ringing out after the sound stops.
    """
    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate!r}")
    if not 0.0 <= room <= 1.0:
        raise ValueError(f"room must be in [0, 1], got {room!r}")
    if not 0.0 <= damping < 1.0:
        raise ValueError(f"damping must be in [0, 1), got {damping!r}")
    if not 0.0 <= wet <= 1.0:
        raise ValueError(f"wet must be in [0, 1], got {wet!r}")
    if not 0.0 <= width <= 1.0:
        raise ValueError(f"width must be in [0, 1], got {width!r}")

    is_stereo = bool(samples) and isinstance(samples[0], (list, array))
    if is_stereo:
        channels = [list(ch) for ch in samples]
    else:
        channels = [list(samples)]

    # Empty input has nothing to ring out: return an empty result of the same
    # shape (no tail, no allocation).
    if all(len(ch) == 0 for ch in channels):
        empty = [array("d") for _ in channels]
        return empty if is_stereo else empty[0]

    predelay = int(round(predelay_ms * 0.001 * sample_rate))

    out_channels: list[array] = []
    for idx, ch in enumerate(channels):
        # Decorrelate the right channel with a small delay spread for width.
        spread = int(round(_STEREO_SPREAD * width)) if (is_stereo and idx == 1) else 0
        if wet <= 0.0:
            # Pure dry: skip the (expensive) reverb entirely.
            out_channels.append(array("d", ch))
            continue
        wet_sig = _reverb_one(ch, sample_rate, room, damping, spread)
        wet_sig = delay_samples(wet_sig, predelay)
        out_channels.append(mix(ch, wet_sig, wet))

    if is_stereo:
        return out_channels
    return out_channels[0]
