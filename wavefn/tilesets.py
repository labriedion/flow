"""Built-in tilesets for the tiled Wave Function Collapse solver.

A *tile* in this model is four edge labels — its **sockets**, one per side
(north, east, south, west) — together with a little pixel pattern used for
drawing and a `weight` for weighted random choice. Two tiles may sit next to
each other only when their touching sockets carry the same label: the left
tile's *east* socket must equal the right tile's *west* socket, and the top
tile's *south* socket must equal the bottom tile's *north* socket.

That single rule is what makes the output *coherent*. In the "pipes" set, for
instance, a socket is either ``"-"`` (an open pipe end) or ``" "`` (a flat
wall). Pipe ends only ever meet other pipe ends and walls only ever meet walls,
so the collapsed grid is always a network of pipes that actually connect.

A tileset is just a list of :class:`Tile`. Many tiles are the same shape turned
a quarter-turn, so :func:`rotations` stamps out the distinct rotations of a base
tile for you — rotating both the socket labels and the pixel pattern together,
so a rotated tile stays consistent.

Usage:

    from wavefn.tilesets import TILESETS, get

    tiles = get("pipes")          # a list[Tile]
    print(TILESETS.keys())        # the available set names

Only the standard library is used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Sockets are indexed by side, in clockwise order starting at the top.
NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3


@dataclass(frozen=True)
class Tile:
    """One placeable tile.

    * ``name``     — a short human label (handy in errors and tests).
    * ``sockets``  — four edge labels ``(north, east, south, west)``. Adjacency
      compares these: tiles touch legally iff the shared sockets are equal.
    * ``pattern``  — the pixel art, a list of equal-length strings of single
      characters (``"0"``/``"1"`` or any palette key) stamped when rendering.
    * ``weight``   — relative likelihood of being chosen when a cell collapses.
    """

    name: str
    sockets: tuple[str, str, str, str]
    pattern: tuple[str, ...]
    weight: float = 1.0

    def __post_init__(self) -> None:
        if len(self.sockets) != 4:
            raise ValueError(f"{self.name}: need exactly 4 sockets")
        if not self.pattern:
            raise ValueError(f"{self.name}: pattern must be non-empty")
        w = len(self.pattern[0])
        if any(len(r) != w for r in self.pattern):
            raise ValueError(f"{self.name}: pattern rows must be equal length")
        if self.weight <= 0:
            raise ValueError(f"{self.name}: weight must be positive")

    @property
    def size(self) -> tuple[int, int]:
        """The pattern's ``(width, height)`` in pixels."""
        return len(self.pattern[0]), len(self.pattern)


def _rotate_pattern(pattern: tuple[str, ...]) -> tuple[str, ...]:
    """Rotate a square pixel pattern 90° clockwise."""
    h = len(pattern)
    w = len(pattern[0])
    return tuple(
        "".join(pattern[h - 1 - c][r] for c in range(h)) for r in range(w)
    )


def _rotate_sockets(sockets: tuple[str, str, str, str]) -> tuple[str, str, str, str]:
    """Rotate sockets 90° clockwise: the old west becomes the new north, etc."""
    n, e, s, w = sockets
    return (w, n, e, s)


def rotations(
    name: str,
    sockets: tuple[str, str, str, str],
    pattern: tuple[str, ...],
    weight: float = 1.0,
    turns: int = 4,
) -> list[Tile]:
    """Generate the distinct quarter-turn rotations of a base tile.

    Returns between 1 and `turns` tiles: each successive rotation turns the
    pixel pattern *and* its sockets a quarter-turn clockwise so they stay in
    sync. Rotations that come out identical to one already produced (e.g. a
    4-fold symmetric cross) are dropped, so a symmetric tile contributes only
    once and doesn't get an unfair weight boost.

    The pattern must be square for rotation to make sense.
    """
    w, h = len(pattern[0]), len(pattern)
    if w != h:
        raise ValueError(f"{name}: rotation needs a square pattern, got {w}x{h}")
    out: list[Tile] = []
    seen: set[tuple] = set()
    sk, pat = sockets, pattern
    for t in range(turns):
        key = (sk, pat)
        if key not in seen:
            seen.add(key)
            label = name if t == 0 else f"{name}@{t * 90}"
            out.append(Tile(label, sk, pat, weight))
        sk = _rotate_sockets(sk)
        pat = _rotate_pattern(pat)
    return out


# ---------------------------------------------------------------------------
# pipes — a connected-pipe network. Socket "-" is an open pipe end, " " a wall.
# Each pattern is 3x3; the centre is always lit, with arms reaching the sides
# that carry a "-" socket. Rotations make the corners and tees for free.
# ---------------------------------------------------------------------------

def _pipes() -> list[Tile]:
    O, W = "-", " "  # open pipe end / flat wall
    tiles: list[Tile] = []
    # blank: a wall on all four sides, nothing drawn.
    tiles += rotations(
        "blank", (W, W, W, W),
        ("   ",
         "   ",
         "   "),
        weight=1.4,
    )
    # straight: pipe runs north<->south (rotation gives east<->west too).
    tiles += rotations(
        "straight", (O, W, O, W),
        (" █ ",
         " █ ",
         " █ "),
        weight=1.0,
    )
    # corner: connects north and east.
    tiles += rotations(
        "corner", (O, O, W, W),
        (" █ ",
         " ██",
         "   "),
        weight=1.0,
    )
    # tee: three arms (north, east, south); west is a wall.
    tiles += rotations(
        "tee", (O, O, O, W),
        (" █ ",
         " ██",
         " █ "),
        weight=0.7,
    )
    # cross: all four arms (4-fold symmetric, so only one survives).
    tiles += rotations(
        "cross", (O, O, O, O),
        (" █ ",
         "███",
         " █ "),
        weight=0.4,
    )
    return tiles


# ---------------------------------------------------------------------------
# terrain — water / coast / land. Sockets: "w" water edge, "l" land edge.
# Coast tiles bridge the two with a diagonal, but only across matching edges,
# so water bodies stay connected and never touch land without a coastline.
# ---------------------------------------------------------------------------

def _terrain() -> list[Tile]:
    w, l = "w", "l"
    tiles: list[Tile] = []
    # deep water: water on all sides.
    tiles += rotations(
        "water", (w, w, w, w),
        ("~~~~",
         "~~~~",
         "~~~~",
         "~~~~"),
        weight=1.3,
    )
    # land: land on all sides.
    tiles += rotations(
        "land", (l, l, l, l),
        ("####",
         "####",
         "####",
         "####"),
        weight=1.3,
    )
    # coast-straight: water to the north, land to the south.
    tiles += rotations(
        "coast", (w, w, l, l),
        ("~~~~",
         "~~~~",
         "####",
         "####"),
        weight=0.8,
    )
    # cape: land in the south-east corner, water elsewhere.
    tiles += rotations(
        "cape", (w, l, l, w),
        ("~~~~",
         "~~~#",
         "~~##",
         "~###"),
        weight=0.5,
    )
    # bay: water in the south-east corner, land elsewhere.
    tiles += rotations(
        "bay", (l, w, w, l),
        ("####",
         "###~",
         "##~~",
         "#~~~"),
        weight=0.5,
    )
    return tiles


# Each tileset is built once on import. A palette maps pattern characters to
# colours for the SVG renderer; missing characters fall back to a default.
@dataclass
class Tileset:
    name: str
    tiles: list[Tile]
    palette: dict[str, str] = field(default_factory=dict)


TILESETS: dict[str, Tileset] = {
    "pipes": Tileset(
        "pipes", _pipes(),
        palette={" ": "#0d1b2a", "█": "#48cae4"},
    ),
    "terrain": Tileset(
        "terrain", _terrain(),
        palette={"~": "#1d4e89", "#": "#3a7d44"},
    ),
}


def names() -> list[str]:
    """The available tileset names, sorted."""
    return sorted(TILESETS)


def get(name: str) -> list[Tile]:
    """Look up a built-in tileset's tiles by name, or raise ``KeyError``."""
    if name not in TILESETS:
        raise KeyError(name)
    return TILESETS[name].tiles


def palette(name: str) -> dict[str, str]:
    """The colour palette for a built-in tileset."""
    if name not in TILESETS:
        raise KeyError(name)
    return TILESETS[name].palette
