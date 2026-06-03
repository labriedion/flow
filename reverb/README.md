# reverb

A **reverb built from the math** — Schroeder's 1962 recipe with Freeverb's
damping — in pure Python, processing 16-bit WAV files. No numpy, no scipy, no
anything: just the standard library's `wave`, `array`, `struct` and `math`. It's
the "from the math" companion to the repo's [`driftwave`](../driftwave), which
gets its reverb for free from a browser `ConvolverNode`.

Strip a reverb down and it's just a pile of delays feeding back on themselves.
Two little filters do all the work:

- A **feedback comb filter** is a delay line whose output is summed back into its
  input, scaled by `feedback`. Hit it with a single click and you hear a train of
  echoes spaced `delay` samples apart, each quieter than the last by a factor of
  `feedback` — a geometric decay, `feedback ** k`. That train is the body of a
  reverb tail. Put a one-pole lowpass in the feedback path (Freeverb's *damping*)
  and each pass loses a little treble, exactly like a real room where the air and
  walls soak up highs faster than lows.

- A **Schroeder allpass filter** passes every frequency at equal *magnitude* but
  scrambles the *phase*. Alone it sounds like almost nothing; in series after the
  combs it smears the discrete echoes into a smooth wash without colouring the
  tone.

```
A unit click into a comb filter (delay 3, feedback ½):

  1.0
  │
  │        0.5
  │        │        0.25
  │        │        │        0.125
  └────────┴────────┴────────┴──────────►  samples 0, 3, 6, 9 …
```

Run several combs with mutually offset delays in *parallel* (so their echo trains
interleave instead of lining up into a flutter), sum them, then push the sum
through a couple of allpasses in *series*. That's a reverb.

*🎧 **Listen:** [`examples/demo_dry.wav`](examples/demo_dry.wav) is a dry
arpeggio of plucked-string notes;
[`examples/demo_wet.wav`](examples/demo_wet.wav) is the same arpeggio after the
reverb, blooming into a three-second tail. Both were made by the `--demo` path
below.*

## Run it

```bash
# reverberate a WAV file
python -m reverb.cli in.wav out.wav --room 0.8 --wet 0.35 --damping 0.5 --predelay 20

# no input file? synthesize a dry signal, reverberate it, write the wet WAV
python -m reverb.cli --demo out.wav                 # an arpeggio of plucks
python -m reverb.cli --demo out.wav --signal pluck  # a single plucked note
python -m reverb.cli --demo out.wav --signal click  # a unit impulse (the room's IR)
```

With `--demo` the dry source is written alongside the output (`out_dry.wav`) so
you can A/B the effect. Mono and stereo files both work.

| flag | meaning |
| --- | --- |
| `--room N` | room size 0–1: bigger = longer delays, higher feedback, lusher tail (default 0.7) |
| `--damping N` | treble damping 0–1: how fast the highs die in the tail (default 0.5) |
| `--wet N` | dry/wet mix 0–1; `0` is dry, `1` is fully wet (default 0.3) |
| `--predelay MS` | silence before the wet signal, in milliseconds (default 0) |
| `--width N` | stereo width 0–1: how far the two channels are decorrelated (default 1.0) |
| `--demo` | synthesize a dry test signal instead of reading an input file |
| `--signal` | what `--demo` makes: `arp` (default), `pluck`, or `click` |

## How it works

```
reverb/
  filters.py    # the DSP primitives: comb, allpass, mix, pre-delay
  engine.py     # the Schroeder/Freeverb network: parallel combs -> series allpasses
  wavefile.py   # 16-bit PCM WAV read/write via the stdlib `wave` module
  synth.py      # test signals (click, Karplus-Strong pluck, arpeggio) for --demo
  cli.py        # the command-line front end
```

`comb` and `allpass` are short recurrences over an `array('d')` delay line.
`reverberate` scales Freeverb's eight comb delays and four allpass delays by the
sample rate and by `room`, runs the parallel comb bank, diffuses through the
allpasses, then mixes the wet tail against the dry signal by `wet` and shifts it
by the pre-delay. The output runs longer than the input — that's the room
ringing out after the sound stops.

## Use it as a library

```python
from reverb import reverberate, read_wav, write_wav

channels, rate = read_wav("dry.wav")
wet = reverberate(channels[0], rate, room=0.85, damping=0.4, wet=0.4)
write_wav("wet.wav", [wet], rate)
```

## Test it

```bash
python -m pytest reverb/ -q
```

The interesting tests check the DSP against *mathematics*, not against itself. A
comb fed a unit impulse must produce echoes of amplitude `feedback ** k` at
sample `k * delay` exactly, with silence everywhere off the grid; damping must
make the late echoes decay faster than the undamped case. A Schroeder allpass has
unity magnitude response, so we assert it conserves signal energy (Parseval's
identity) to within rounding. The rest pins down stability (finite, bounded
output for feedback < 1), the tail outliving the input, `wet=0` returning the dry
signal, determinism, WAV round-tripping within 16-bit quantization (mono and
stereo, sample rate preserved), and the empty/short-input edge cases.
