"""Propose new missions.

Pick a substrate, a single local rule, a medium, maybe a twist — and phrase it
as a brief in the collection's own voice. Fully deterministic given a seed, so
any proposal is reproducible (the repo's standing promise). The generator is
small; the space it opens is not.
"""

import random

from . import primitives as P
from . import registry


def _name(rng):
    """A short, evocative slug — two seeded picks from the word bank."""
    a = rng.choice(P._NAME_A)
    b = rng.choice(P._NAME_B)
    if a == b:  # avoid e.g. "driftdrift"
        b = rng.choice([w for w in P._NAME_B if w != a])
    return a + b


def propose(seed, existing_ids=None):
    """Compose one mission dict from a seed. Pure function of (seed, repo)."""
    rng = random.Random(seed)
    existing_ids = set(existing_ids or [])

    substrate = rng.choice(P.SUBSTRATES)
    rule = rng.choice(P.RULES)
    medium = rng.choice(P.MEDIA)
    twist = rng.choice(P.TWISTS)

    seeded_by = None
    if twist and "{other}" in twist:
        # cross-wire with one of the already-built systems
        built_ids = [m["id"] for m in registry.built(registry.load())]
        if built_ids:
            seeded_by = rng.choice(built_ids)
            twist = twist.format(other=seeded_by)
        else:
            twist = None

    # a unique-ish id
    title = _name(rng)
    base = title
    n = 2
    while title in existing_ids:
        title = f"{base}{n}"
        n += 1

    twist_clause = f", {twist}" if twist else ""
    prompt = (
        f"Take {substrate}. Give every part one local rule — {rule} — and no "
        f"global plan. Render it to {medium}{twist_clause}. Keep the rule tiny; "
        f"let the whole thing fall out of it, and surprise yourself."
    )

    return {
        "id": title,
        "title": title,
        "date": None,
        "provenance": "loom",
        "seeded_by": seeded_by,
        "status": "proposed",
        "seed": seed,
        "substrate": substrate,
        "rule": rule.split(",")[0],
        "medium_hint": medium,
        "twist": twist,
        "prompt": prompt,
    }


def propose_many(seed, count, existing_ids=None):
    """A reproducible batch. Each mission gets a distinct derived seed."""
    existing = set(existing_ids or [])
    out = []
    for i in range(count):
        m = propose(seed * 1000 + i, existing_ids=existing)
        existing.add(m["id"])
        out.append(m)
    return out
