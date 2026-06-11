"""fenchurn — a heap of edge-matching tiles that averages itself into a quilt.

One local rule (average yourself toward your neighbours), one cell that
disobeys, and the disobedience wins: the whole heap slowly takes the rebel's
colour. Proposed by loom (seed 7000); see README.md for the brief.
"""

from .quilt import Quilt

__all__ = ["Quilt"]
