"""Tests for the reverb. Run: python -m pytest reverb/ -q

Where we can, we check the DSP against ground truth rather than against itself:

  * A feedback comb filter fed a unit impulse must produce a clean geometric
    train of echoes — sample `k * delay` equals `feedback ** k` exactly, and
    every off-grid sample is zero. Damping must make the *late* echoes decay
    faster than the undamped case.
  * A Schroeder allpass has unity magnitude response, so the total energy it
    passes equals the energy in — we check Parseval's identity numerically.
  * The full reverb must be stable (finite, bounded) for feedback < 1, must
    extend the signal with a tail, and must return the dry signal when wet=0.
  * WAV files must round-trip within 16-bit quantization, mono and stereo, with
    the sample rate preserved. Same input + params must give identical output.
"""

import math
import os

import pytest

from .engine import reverberate
from .filters import allpass, comb, delay_samples, mix, pad
from .synth import arpeggio, click, pluck
from .wavefile import read_wav, write_wav


def _impulse(n: int) -> list[float]:
    x = [0.0] * n
    x[0] = 1.0
    return x


def _finite_bounded(seq, limit=100.0) -> bool:
    return all(math.isfinite(v) and abs(v) <= limit for v in seq)


# --------------------------------------------------------------------------
# Comb filter — geometric echo train
# --------------------------------------------------------------------------

def test_comb_impulse_is_geometric_series():
    delay, fb = 7, 0.6
    y = comb(_impulse(300), delay, fb)
    # Echo k lands at sample k*delay with amplitude fb**k, exactly.
    for k in range(len(y) // delay):
        assert y[k * delay] == pytest.approx(fb ** k, abs=1e-9)
    # Every sample not on the delay grid is silence.
    for i in range(len(y)):
        if i % delay != 0:
            assert y[i] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("delay,fb", [(3, 0.5), (11, 0.3), (50, 0.9)])
def test_comb_first_echo_and_dc(delay, fb):
    y = comb(_impulse(delay * 6), delay, fb)
    assert y[0] == pytest.approx(1.0)            # the direct (input) sample
    assert y[delay] == pytest.approx(fb)         # first echo
    assert y[2 * delay] == pytest.approx(fb * fb)


def test_comb_damping_attenuates_late_echoes_more():
    delay, fb = 5, 0.85
    x = _impulse(400)
    undamped = comb(x, delay, fb, damping=0.0)
    damped = comb(x, delay, fb, damping=0.6)
    # The very first echo is already quieter with damping...
    assert damped[delay] < undamped[delay]
    # ...and the gap widens for later echoes: damping compounds each pass.
    early_ratio = damped[delay] / undamped[delay]
    late_ratio = damped[20 * delay] / undamped[20 * delay]
    assert late_ratio < early_ratio


def test_comb_stable_for_feedback_below_one():
    # A long noisy input through a high-feedback comb must stay bounded.
    import random
    rng = random.Random(0)
    x = [rng.uniform(-1, 1) for _ in range(2000)]
    y = comb(x, 31, 0.97, damping=0.4)
    assert _finite_bounded(y)


def test_comb_rejects_bad_args():
    with pytest.raises(ValueError):
        comb(_impulse(10), 0, 0.5)
    with pytest.raises(ValueError):
        comb(_impulse(10), -3, 0.5)
    with pytest.raises(ValueError):
        comb(_impulse(10), 3, 0.5, damping=1.0)


# --------------------------------------------------------------------------
# Allpass — flat magnitude (energy preserving) and stable
# --------------------------------------------------------------------------

def test_allpass_preserves_energy():
    # Unity magnitude response => same total energy out as in (Parseval).
    import random
    rng = random.Random(1)
    x = [rng.uniform(-1, 1) for _ in range(4000)]
    # Run long enough that the tail has fully decayed back into the output.
    y = allpass(x + [0.0] * 4000, 113, 0.5)
    energy_in = sum(v * v for v in x)
    energy_out = sum(v * v for v in y)
    assert energy_out == pytest.approx(energy_in, rel=1e-6)


def test_allpass_stable_and_bounded():
    import random
    rng = random.Random(2)
    x = [rng.uniform(-1, 1) for _ in range(2000)]
    y = allpass(x, 47, 0.7)
    assert _finite_bounded(y)


def test_allpass_rejects_bad_delay():
    with pytest.raises(ValueError):
        allpass(_impulse(10), 0, 0.5)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def test_mix_blends_and_lengthens():
    dry = [1.0, 1.0, 1.0]
    wet = [0.0, 0.0, 0.0, 2.0, 2.0]
    out = mix(dry, wet, 0.5)
    assert len(out) == 5
    assert out[0] == pytest.approx(0.5)          # 0.5*1 + 0.5*0
    assert out[3] == pytest.approx(1.0)          # 0.5*0 + 0.5*2 (dry ran out)


def test_pad_truncates_and_extends():
    assert list(pad([1, 2, 3], 5)) == [1, 2, 3, 0, 0]
    assert list(pad([1, 2, 3], 2)) == [1, 2]


def test_delay_samples_shifts_later():
    out = delay_samples([1.0, 2.0], 3)
    assert list(out) == [0.0, 0.0, 0.0, 1.0, 2.0]
    assert list(delay_samples([1.0, 2.0], 0)) == [1.0, 2.0]


# --------------------------------------------------------------------------
# Reverb engine
# --------------------------------------------------------------------------

def test_reverb_extends_signal_with_a_tail():
    dry = _impulse(1000)
    wet = reverberate(dry, 22050, room=0.8, wet=0.4)
    assert len(wet) > len(dry)


def test_reverb_is_stable_and_bounded():
    import random
    rng = random.Random(3)
    dry = [rng.uniform(-0.5, 0.5) for _ in range(2000)]
    wet = reverberate(dry, 22050, room=1.0, damping=0.3, wet=0.5)
    assert _finite_bounded(wet, limit=10.0)


def test_reverb_wet_zero_returns_dry():
    dry = pluck(220.0, 0.3, 22050)
    wet = reverberate(dry, 22050, wet=0.0)
    assert len(wet) == len(dry)
    for a, b in zip(dry, wet):
        assert a == pytest.approx(b, abs=1e-9)


def test_reverb_deterministic():
    dry = arpeggio(22050)
    a = reverberate(dry, 22050, room=0.7, damping=0.5, wet=0.3, predelay_ms=10)
    b = reverberate(dry, 22050, room=0.7, damping=0.5, wet=0.3, predelay_ms=10)
    assert list(a) == list(b)


def test_reverb_predelay_lengthens_tail():
    dry = _impulse(500)
    no_pre = reverberate(dry, 22050, wet=0.5, predelay_ms=0)
    with_pre = reverberate(dry, 22050, wet=0.5, predelay_ms=50)
    assert len(with_pre) > len(no_pre)


def test_reverb_stereo_returns_two_channels():
    left = pluck(220.0, 0.2, 22050, seed=1)
    right = pluck(330.0, 0.2, 22050, seed=2)
    out = reverberate([left, right], 22050, room=0.6, wet=0.4, width=1.0)
    assert isinstance(out, list) and len(out) == 2
    assert all(_finite_bounded(ch, limit=10.0) for ch in out)
    # Width decorrelates the channels, so they must not be identical.
    assert list(out[0]) != list(out[1])


def test_reverb_handles_empty_and_short_input():
    assert len(reverberate([], 22050, wet=0.4)) == 0
    short = reverberate([0.5, -0.5], 22050, wet=0.4)
    assert len(short) >= 2 and _finite_bounded(short, limit=10.0)


def test_reverb_rejects_bad_params():
    for kw in ({"room": 1.5}, {"wet": -0.1}, {"damping": 1.0}, {"width": 2.0}):
        with pytest.raises(ValueError):
            reverberate([0.0, 0.0], 22050, **kw)
    with pytest.raises(ValueError):
        reverberate([0.0], 0)


# --------------------------------------------------------------------------
# Synth signals
# --------------------------------------------------------------------------

def test_click_is_a_unit_impulse():
    c = click(22050)
    assert len(c) == 22050
    assert c[0] == pytest.approx(1.0)
    assert all(v == 0.0 for v in c[1:])


def test_pluck_is_pitched_and_normalised():
    tone = pluck(220.0, 0.5, 22050)
    assert len(tone) == int(0.5 * 22050)
    assert max(abs(s) for s in tone) == pytest.approx(0.9, abs=1e-6)
    # Deterministic for a given seed.
    assert list(tone) == list(pluck(220.0, 0.5, 22050))


def test_pluck_rejects_bad_args():
    with pytest.raises(ValueError):
        pluck(0.0, 0.5)
    with pytest.raises(ValueError):
        pluck(220.0, 0.0)


def test_arpeggio_concatenates_notes():
    sr = 22050
    arp = arpeggio(sr, note_dur=0.2)
    assert len(arp) == 4 * int(0.2 * sr)
    assert max(abs(s) for s in arp) <= 1.0


# --------------------------------------------------------------------------
# WAV round-trip
# --------------------------------------------------------------------------

def test_wav_mono_round_trip(tmp_path):
    sr = 22050
    src = [math.sin(2 * math.pi * 220 * i / sr) * 0.7 for i in range(1000)]
    path = str(tmp_path / "mono.wav")
    write_wav(path, [src], sr)
    channels, rate = read_wav(path)
    assert rate == sr
    assert len(channels) == 1
    for a, b in zip(src, channels[0]):
        assert a == pytest.approx(b, abs=1.0 / 32768)


def test_wav_stereo_round_trip(tmp_path):
    sr = 44100
    left = [math.sin(2 * math.pi * 220 * i / sr) * 0.5 for i in range(500)]
    right = [math.sin(2 * math.pi * 330 * i / sr) * 0.5 for i in range(500)]
    path = str(tmp_path / "stereo.wav")
    write_wav(path, [left, right], sr)
    channels, rate = read_wav(path)
    assert rate == sr
    assert len(channels) == 2
    for a, b in zip(left, channels[0]):
        assert a == pytest.approx(b, abs=1.0 / 32768)
    for a, b in zip(right, channels[1]):
        assert a == pytest.approx(b, abs=1.0 / 32768)


def test_wav_clips_out_of_range(tmp_path):
    path = str(tmp_path / "clip.wav")
    write_wav(path, [[2.0, -2.0, 0.0]], 22050)
    channels, _ = read_wav(path)
    # Values outside [-1, 1] are clipped, not wrapped.
    assert channels[0][0] == pytest.approx(1.0, abs=1.0 / 32768)
    assert channels[0][1] == pytest.approx(-1.0, abs=1.0 / 32768)


def test_wav_rejects_empty_channels(tmp_path):
    with pytest.raises(ValueError):
        write_wav(str(tmp_path / "x.wav"), [], 22050)


def test_read_wav_rejects_non_wav(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"this is not a wav file at all")
    with pytest.raises(ValueError):
        read_wav(str(bad))


def test_full_pipeline_round_trip(tmp_path):
    # Synthesize -> reverberate -> write -> read back, end to end.
    sr = 22050
    dry = arpeggio(sr, note_dur=0.15)
    wet = reverberate(dry, sr, room=0.7, wet=0.35, predelay_ms=15)
    path = str(tmp_path / "wet.wav")
    write_wav(path, [wet], sr)
    channels, rate = read_wav(path)
    assert rate == sr
    assert len(channels[0]) == len(wet)
    assert os.path.getsize(path) > 0
