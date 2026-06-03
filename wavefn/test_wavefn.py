"""Tests for the tiled Wave Function Collapse solver. Run: python -m pytest wavefn/

The headline property is *correctness of the output*, checked against the ground
truth of the adjacency rule rather than against the solver's own machinery: in a
fully collapsed grid every pair of neighbours must agree on its shared edge
socket. We assert that across several seeds and both tilesets. The rest pins
down the adjacency relation's symmetry, that propagation really removes options,
determinism under a seed, contradiction handling on an over-constrained set, and
the renderers' shape and content.
"""

import random

import pytest

from .render import stamp, to_half_blocks, to_svg, to_text
from .solver import Contradiction, Solver, build_adjacency, solve
from .tilesets import (
    EAST,
    NORTH,
    SOUTH,
    WEST,
    Tile,
    Tileset,
    get,
    names,
    palette,
    rotations,
)

_OPPOSITE = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST}
_DELTA = {NORTH: (0, -1), EAST: (1, 0), SOUTH: (0, 1), WEST: (-1, 0)}


# --------------------------------------------------------------------------
# Tilesets and rotations
# --------------------------------------------------------------------------

def test_builtin_tilesets_present():
    assert names() == ["pipes", "terrain"]
    for name in names():
        tiles = get(name)
        assert len(tiles) >= 4
        assert all(len(t.sockets) == 4 for t in tiles)
        # All tiles in a set share a (square) pattern size.
        sizes = {t.size for t in tiles}
        assert len(sizes) == 1


def test_tile_validates_its_shape():
    with pytest.raises(ValueError):
        Tile("bad", ("a", "b"), ("00",))            # wrong socket count
    with pytest.raises(ValueError):
        Tile("bad", ("a", "b", "c", "d"), ("00", "0"))   # ragged pattern
    with pytest.raises(ValueError):
        Tile("bad", ("a", "b", "c", "d"), ("00",), weight=0)  # bad weight


def test_rotation_turns_sockets_and_pixels_together():
    # A corner opening north+east, drawn as an L, rotated once becomes
    # east+south. Sockets and pixels must rotate in lock-step.
    corner = rotations("corner", ("o", "o", ".", "."),
                       (" █ ", " ██", "   "))
    assert len(corner) == 4                       # no symmetry, four distinct
    first, second = corner[0], corner[1]
    # Clockwise quarter turn: (n,e,s,w) -> (w,n,e,s).
    assert second.sockets == (".", "o", "o", ".")


def test_rotation_dedupes_symmetric_tiles():
    # A 4-fold symmetric cross collapses to a single tile.
    cross = rotations("cross", ("o", "o", "o", "o"),
                      (" █ ", "███", " █ "))
    assert len(cross) == 1


def test_palette_lookup():
    pal = palette("pipes")
    assert isinstance(pal, dict) and pal
    with pytest.raises(KeyError):
        get("nope")


# --------------------------------------------------------------------------
# Adjacency relation — ground truth
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", names())
def test_adjacency_is_symmetric(name):
    tiles = get(name)
    adj = build_adjacency(tiles)
    # If b may sit east of a, then a may sit west of b (and similarly N/S).
    for a in range(len(tiles)):
        for side in (NORTH, EAST, SOUTH, WEST):
            opp = _OPPOSITE[side]
            for b in adj[a][side]:
                assert a in adj[b][opp], (name, a, b, side)


@pytest.mark.parametrize("name", names())
def test_adjacency_matches_socket_equality(name):
    # The relation is exactly "shared sockets are equal" — nothing more.
    tiles = get(name)
    adj = build_adjacency(tiles)
    for a in range(len(tiles)):
        for b in range(len(tiles)):
            for side in (NORTH, EAST, SOUTH, WEST):
                expected = tiles[a].sockets[side] == tiles[b].sockets[_OPPOSITE[side]]
                assert (b in adj[a][side]) == expected


# --------------------------------------------------------------------------
# The key invariant: a collapsed grid honours every adjacency
# --------------------------------------------------------------------------

def _assert_grid_consistent(grid, tiles):
    h = len(grid)
    w = len(grid[0])
    for y in range(h):
        for x in range(w):
            a = tiles[grid[y][x]]
            # East neighbour: a's east socket equals its west socket.
            if x + 1 < w:
                b = tiles[grid[y][x + 1]]
                assert a.sockets[EAST] == b.sockets[WEST], (x, y, "E")
            # South neighbour: a's south socket equals its north socket.
            if y + 1 < h:
                b = tiles[grid[y + 1][x]]
                assert a.sockets[SOUTH] == b.sockets[NORTH], (x, y, "S")


@pytest.mark.parametrize("name", names())
@pytest.mark.parametrize("seed", [0, 1, 2, 7, 42, 123])
def test_collapsed_grid_satisfies_all_adjacencies(name, seed):
    tiles = get(name)
    grid = solve(tiles, 14, 10, seed=seed)
    assert len(grid) == 10 and all(len(r) == 14 for r in grid)
    # Every cell is decided to exactly one valid tile index.
    assert all(0 <= idx < len(tiles) for row in grid for idx in row)
    _assert_grid_consistent(grid, tiles)


# --------------------------------------------------------------------------
# Propagation actually removes options
# --------------------------------------------------------------------------

def test_propagation_constrains_neighbours():
    # Collapse one cell, propagate, and confirm at least one neighbour lost
    # options it could not possibly support.
    tiles = get("pipes")
    s = Solver(tiles, 3, 3, seed=1)
    all_tiles = set(range(len(tiles)))
    cells = [[set(all_tiles) for _ in range(3)] for _ in range(3)]
    cells[1][1] = {0}  # force the centre to a single tile
    s._propagate(cells, 1, 1)
    centre = tiles[0]
    # Each orthogonal neighbour must now only contain tiles whose facing socket
    # matches the centre's, and the set must have genuinely shrunk.
    for side, (dx, dy) in _DELTA.items():
        nx, ny = 1 + dx, 1 + dy
        opts = cells[ny][nx]
        assert opts < all_tiles
        for t in opts:
            assert tiles[t].sockets[_OPPOSITE[side]] == centre.sockets[side]


# --------------------------------------------------------------------------
# Determinism
# --------------------------------------------------------------------------

def test_same_seed_same_grid():
    a = solve(get("pipes"), 16, 12, seed=99)
    b = solve(get("pipes"), 16, 12, seed=99)
    assert a == b


def test_different_seeds_usually_differ():
    grids = [tuple(tuple(r) for r in solve(get("pipes"), 16, 12, seed=s))
             for s in range(6)]
    # Not all six runs should be identical.
    assert len(set(grids)) > 1


# --------------------------------------------------------------------------
# Contradiction handling
# --------------------------------------------------------------------------

def test_overconstrained_tileset_raises_clearly():
    # Two tiles whose only horizontal neighbour is themselves but which clash
    # vertically: 'a' wants 'a' above/below, 'b' wants 'b', and neither can sit
    # next to the other in any direction -> a 2x1 grid solves but a tile that
    # can never tile leads to a contradiction. Here we build a set with no legal
    # vertical pairing at all, so a 1x2 grid is impossible.
    impossible = [
        Tile("top", ("x", "m", "y", "m"), ("0",)),     # south socket 'y'
        Tile("bot", ("z", "m", "w", "m"), ("1",)),     # north socket 'z' != 'y'
    ]
    # top's south 'y' matches nothing's north ('x','z'); bot's south 'w' likewise.
    # A 1x2 grid needs a vertical pair, which cannot be satisfied.
    with pytest.raises(RuntimeError) as err:
        solve(impossible, 1, 2, seed=1, attempts=3)
    assert "wavefn:" in str(err.value)


def test_trivial_single_tile_always_solves():
    # One self-compatible tile tiles any grid with no contradiction.
    one = [Tile("o", ("m", "m", "m", "m"), ("█",))]
    grid = solve(one, 4, 3, seed=5)
    assert grid == [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]


def test_solver_rejects_bad_dimensions():
    with pytest.raises(ValueError):
        Solver(get("pipes"), 0, 5)
    with pytest.raises(ValueError):
        Solver([], 5, 5)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def test_stamp_expands_to_pixel_field():
    tiles = get("pipes")
    grid = solve(tiles, 5, 4, seed=2)
    tw, th = tiles[0].size
    field = stamp(grid, tiles)
    assert len(field) == 4 * th
    assert all(len(line) == 5 * tw for line in field)


def test_text_and_halfblock_dimensions():
    field = ["##", "..", "#.", ".#"]
    assert to_text(field) == "##\n..\n#.\n.#"
    # Half-blocks pack two rows per line: 4 rows -> 2 lines, width preserved.
    hb = to_half_blocks(field)
    lines = hb.split("\n")
    assert len(lines) == 2
    assert all(len(line) == 2 for line in lines)


def test_halfblock_glyph_mapping():
    # A pixel is "lit" when it is not a space. top "█ ", bottom " █" -> ▀ then ▄
    out = to_half_blocks(["█ ", " █"])
    assert out == "▀▄"
    # Both lit -> █, neither lit -> space.
    assert to_half_blocks(["██", "██"]) == "██"
    assert to_half_blocks(["  ", "  "]) == "  "
    assert to_half_blocks([]) == ""


def test_svg_dimensions_and_content():
    field = ["█ ", " █"]
    svg = to_svg(field, cell=10, palette={"█": "#abcdef"})
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert 'width="20"' in svg and 'height="20"' in svg
    assert "<path" in svg
    assert "#abcdef" in svg
    # An all-blank field draws a background but no cell path.
    blank = to_svg(["  ", "  "], cell=10)
    assert "<path" not in blank


def test_full_pipeline_svg_nonempty():
    tiles = get("pipes")
    grid = solve(tiles, 8, 6, seed=11)
    field = stamp(grid, tiles)
    svg = to_svg(field, cell=6, palette=palette("pipes"))
    assert "<svg" in svg and len(svg) > 100


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_cli_prints_art(capsys):
    from .cli import main
    rc = main(["--tileset", "pipes", "--width", "10", "--height", "6", "--seed", "7"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_cli_list(capsys):
    from .cli import main
    rc = main(["--list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "pipes" in out and "terrain" in out


def test_cli_writes_svg(tmp_path, capsys):
    from .cli import main
    path = tmp_path / "out.svg"
    rc = main(["--tileset", "terrain", "--width", "6", "--height", "5",
               "--seed", "3", "--svg", str(path)])
    assert rc == 0
    text = path.read_text(encoding="utf-8")
    assert text.startswith("<svg")


def test_cli_rejects_bad_dimensions(capsys):
    from .cli import main
    rc = main(["--width", "0"])
    assert rc == 2
    err = capsys.readouterr().err
    assert err.startswith("wavefn:")
