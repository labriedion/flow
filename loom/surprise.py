"""A surprise proxy — a measurable, falsifiable stand-in for emergence.

Emergence has a signature you can actually weigh: a *small* rule producing a
*richly complex* output. We approximate each side with compression, which is a
practical lower bound on Kolmogorov complexity:

  - rule_bytes   = compressed size of the source files that ARE the rule
  - output_bytes = compressed size of the artifact that fell out of it

  amplification = output_bytes / rule_bytes
      how much incompressible structure the rule blew up into. High = a tiny
      law that yields a lot. This is the headline number.

  richness = output_bytes / raw_output_bytes   (0..1)
      how non-trivial the output is on its own. A blank frame -> ~0.

HONEST LIMITS — read this before trusting the number:
  * This is a proxy for emergence, NOT a judgment of taste, beauty, or whether
    anyone was actually surprised. That subjective question is unsolved, and
    pretending otherwise would betray the thing this repo is about.
  * Amplification rewards *amount* of structure. It cannot tell structured
    emergence from pure noise (random output also fails to compress). The
    famous edge-of-chaos distinction is exactly what byte-counting misses.
  * It is blind to structural cleverness with small output: a regex VM or an
    expression parser will score low here even though their surprise is real.
    The proxy favours the generative-visual systems. We report the number
    anyway, and say so, rather than fudge it.
"""

import zlib

from . import registry


def _compressed_len(data):
    return len(zlib.compress(data, 9))


def _read_concat(paths):
    chunks = []
    for rel in paths:
        with open(registry.resolve(rel), "rb") as fh:
            chunks.append(fh.read())
    return b"".join(chunks)


def score(mission):
    """Return a score dict for a built mission, or None if it can't be scored."""
    program = mission.get("program")
    artifact = mission.get("artifact")
    if not program or not artifact:
        return None

    try:
        rule_raw = _read_concat(program)
        with open(registry.resolve(artifact), "rb") as fh:
            out_raw = fh.read()
    except OSError:
        return None

    rule_bytes = _compressed_len(rule_raw) or 1
    out_bytes = _compressed_len(out_raw) or 1
    raw_out = len(out_raw) or 1

    amplification = out_bytes / rule_bytes
    # capped at 1.0: an already-compressed artifact (PNG/WAV) can make zlib add a
    # few bytes of overhead, but output is at most fully incompressible.
    richness = min(1.0, out_bytes / raw_out)

    return {
        "id": mission["id"],
        "rule_src_bytes": len(rule_raw),
        "rule_bytes": rule_bytes,
        "output_raw_bytes": raw_out,
        "output_bytes": out_bytes,
        "amplification": amplification,
        "richness": richness,
    }


def score_all(missions):
    """Score every built mission; returns list of score dicts (skips unscored)."""
    out = []
    for m in registry.built(missions):
        s = score(m)
        if s:
            out.append(s)
    return out


def fmt_amplification(amp):
    """Compact human label for a card/table badge."""
    if amp >= 10:
        return f"{amp:.0f}×"
    return f"{amp:.1f}×"
