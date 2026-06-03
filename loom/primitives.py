"""The raw vocabulary the loom composes missions from.

The whole bet of flow is that simple local rules, faithfully followed, bloom
into a surprising whole. The mission generator is itself an instance of that
bet: a handful of primitives and one combining rule produce a space of briefs
far larger and stranger than the parts. Emergence, applied to its own seeding.

Every list here is small and hand-picked; the surprise lives in the product.
"""

# What the rule runs on.
SUBSTRATES = [
    "a grid of cells",
    "a swarm of drifting particles",
    "a single string of symbols",
    "a graph of wired-up nodes",
    "a field of little arrows",
    "a heap of edge-matching tiles",
    "a buffer of audio samples",
    "a row of pixels through time",
    "a lattice of coupled springs",
    "a colony of wandering agents",
    "a stack of stacked layers",
    "a ring of oscillators",
]

# The single local law each part obeys. No global plan, ever.
RULES = [
    "average yourself toward your neighbours",
    "rewrite yourself by one fixed table",
    "switch on if too crowded, off if too lonely",
    "fall whenever the space below is empty",
    "steer along the slope you can feel locally",
    "collapse to whatever still fits your neighbours",
    "flee the close, match the middling, chase the far",
    "stay or escape by one map iterated",
    "react and diffuse with the chemical beside you",
    "fire when enough of your neighbours just fired",
    "pull toward whoever is loudest nearby",
    "split in two whenever you grow past a threshold",
]

# Where the bloom is rendered.
MEDIA = [
    "an HTML canvas you can poke with the mouse",
    "the terminal, in glyphs",
    "a standalone SVG",
    "a WAV you can actually play",
    "a single PNG frame, tone-mapped",
]

# Optional perturbations — sometimes the most interesting part.
TWISTS = [
    None,
    None,
    "but in two dimensions",
    "but run the whole thing backwards",
    "but let the viewer edit the rule while it runs",
    "but wrap the boundary so it has no edge",
    "but let two rival rules compete for the same space",
    "but tuned to sit right at the edge of chaos",
    "but seeded from {other}'s output",
    "but with one cell that disobeys",
]

# Word bank for naming — two seeded picks slugged together, in the house style
# of driftwave / reggie / amaze: short, evocative, faintly physical.
_NAME_A = [
    "drift", "tide", "ash", "ember", "salt", "loom", "murmur", "fen", "rime",
    "glint", "husk", "moss", "verge", "knot", "spindle", "brack", "lull", "fray",
]
_NAME_B = [
    "wave", "field", "grid", "weave", "fall", "bloom", "swarm", "tangle", "drift",
    "lace", "wash", "crawl", "spill", "churn", "veil", "knit", "haze", "sprawl",
]
