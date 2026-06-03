"""reverb — a Schroeder/Freeverb-style reverb built from the math, in pure Python.

Parallel comb filters lay down a geometric train of echoes; series allpass
filters smear them into a smooth tail; Freeverb-style damping darkens the tail as
it decays. It processes 16-bit PCM WAV files (or synthesized test signals) using
nothing but the standard library — a "from the math" companion to the repo's
`driftwave` Web Audio project.
"""

from .engine import reverberate
from .filters import allpass, comb, delay_samples, mix, pad
from .synth import arpeggio, click, pluck
from .wavefile import read_wav, write_wav

__all__ = [
    "reverberate",
    "comb",
    "allpass",
    "mix",
    "pad",
    "delay_samples",
    "click",
    "pluck",
    "arpeggio",
    "read_wav",
    "write_wav",
]
