"""Command-line interface for the reverb engine.

Examples:
    python -m reverb.cli in.wav out.wav                 # reverb a file, defaults
    python -m reverb.cli in.wav out.wav --room 0.8 --wet 0.35 --damping 0.5
    python -m reverb.cli in.wav out.wav --predelay 20   # 20 ms pre-delay
    python -m reverb.cli --demo out.wav                 # synthesize + reverb, no input
    python -m reverb.cli --demo out.wav --signal click  # use a click instead

With an input file it reads 16-bit PCM WAV, applies the reverb and writes the
wet result. With `--demo` it synthesizes a dry test signal (an arpeggio of
plucks, a single pluck, or a click), reverberates it, and writes that — no input
file needed. The dry counterpart is written alongside when you pass `--demo`.
"""

from __future__ import annotations

import argparse
import sys

from .engine import reverberate
from .synth import arpeggio, click, pluck
from .wavefile import read_wav, write_wav

_DEMO_RATE = 22050


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reverb",
        description="A Schroeder/Freeverb-style reverb, built from the math, on WAV audio.",
    )
    p.add_argument("input", nargs="?",
                   help="input WAV file (omit with --demo)")
    p.add_argument("output",
                   help="output WAV file to write the reverberated audio to")
    p.add_argument("--room", type=float, default=0.7,
                   help="room size 0–1: bigger = longer, lusher tail (default: 0.7)")
    p.add_argument("--damping", type=float, default=0.5,
                   help="treble damping 0–1: how fast highs die in the tail (default: 0.5)")
    p.add_argument("--wet", type=float, default=0.3,
                   help="dry/wet mix 0–1; 0 is dry, 1 is fully wet (default: 0.3)")
    p.add_argument("--predelay", type=float, default=0.0, metavar="MS",
                   help="pre-delay before the wet signal, in milliseconds (default: 0)")
    p.add_argument("--width", type=float, default=1.0,
                   help="stereo width 0–1: channel decorrelation (default: 1.0)")
    p.add_argument("--demo", action="store_true",
                   help="synthesize a dry test signal instead of reading an input file")
    p.add_argument("--signal", choices=["arp", "pluck", "click"], default="arp",
                   help="which signal --demo synthesizes (default: arp)")
    return p


def _synthesize(signal: str):
    """Return (channels, sample_rate) for a synthesized demo signal."""
    if signal == "click":
        dry = click(_DEMO_RATE)
    elif signal == "pluck":
        dry = pluck(220.0, 1.2, _DEMO_RATE)
    else:
        dry = arpeggio(_DEMO_RATE)
    return [dry], _DEMO_RATE


def _dry_path(output: str) -> str:
    """Sibling path for the dry counterpart written alongside a --demo output."""
    if output.lower().endswith(".wav"):
        return output[:-4] + "_dry.wav"
    return output + "_dry.wav"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.demo and args.input is None:
        print("reverb: need an input WAV file (or pass --demo to synthesize one)",
              file=sys.stderr)
        return 2
    if args.demo and args.input is not None:
        print("reverb: --demo synthesizes its own signal; do not also give an input file",
              file=sys.stderr)
        return 2

    # Gather the dry signal: either synthesized or read from disk.
    if args.demo:
        channels, sample_rate = _synthesize(args.signal)
    else:
        try:
            channels, sample_rate = read_wav(args.input)
        except (ValueError, OSError) as exc:
            print(f"reverb: could not read {args.input}: {exc}", file=sys.stderr)
            return 2

    # Reverberate each channel (stereo if the file had two).
    try:
        if len(channels) == 1:
            wet = reverberate(
                channels[0], sample_rate,
                room=args.room, damping=args.damping, wet=args.wet,
                predelay_ms=args.predelay, width=args.width,
            )
            out_channels = [wet]
        else:
            wet = reverberate(
                channels[:2], sample_rate,
                room=args.room, damping=args.damping, wet=args.wet,
                predelay_ms=args.predelay, width=args.width,
            )
            out_channels = wet
    except ValueError as exc:
        print(f"reverb: {exc}", file=sys.stderr)
        return 2

    # On --demo, write the dry source too so you can A/B the effect.
    if args.demo:
        dry_path = _dry_path(args.output)
        try:
            write_wav(dry_path, channels, sample_rate)
        except OSError as exc:
            print(f"reverb: could not write {dry_path}: {exc}", file=sys.stderr)
            return 1

    try:
        write_wav(args.output, out_channels, sample_rate)
    except OSError as exc:
        print(f"reverb: could not write {args.output}: {exc}", file=sys.stderr)
        return 1

    frames = max(len(ch) for ch in out_channels)
    secs = frames / sample_rate
    chans = "stereo" if len(out_channels) == 2 else "mono"
    print(f"wrote {args.output} ({secs:.2f}s {chans} @ {sample_rate} Hz, "
          f"room {args.room}, wet {args.wet})")
    if args.demo:
        print(f"wrote {_dry_path(args.output)} (the dry source)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
