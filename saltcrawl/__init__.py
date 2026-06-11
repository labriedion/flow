"""saltcrawl — a swarm of drifting grains that splits its way across a torus.

One local rule (split in two whenever you grow past a threshold), no edge to
die against, and the crawl organises itself: crowding starves the interior,
so the splitting — and the story — happens at the frontier. Proposed by loom
(seed 7001); see README.md for the brief.
"""

from .swarm import Swarm

__all__ = ["Swarm"]
