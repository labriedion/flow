"""Tests for loom — the engine that turns flow into its own emergent system.

These check the engine against behaviour we can state independently of the
implementation: the registry is well-formed and points at real files, proposals
are deterministic and structurally valid, the surprise proxy actually weighs the
built artifacts, and the generated gallery is well-formed and complete.
"""

import os

import pytest

from loom import gallery, primitives, propose, registry, surprise


# ---- registry -------------------------------------------------------------

def test_registry_loads_and_is_nonempty():
    missions = registry.load()
    assert len(missions) >= 13
    assert all("id" in m and "status" in m for m in missions)


def test_ids_are_unique():
    ids = [m["id"] for m in registry.load()]
    assert len(ids) == len(set(ids))


def test_built_missions_point_at_real_files():
    for m in registry.built(registry.load()):
        for rel in m["program"]:
            assert os.path.exists(registry.resolve(rel)), f"missing rule file {rel}"
        assert os.path.exists(registry.resolve(m["artifact"])), m["artifact"]


def test_built_missions_have_required_fields():
    for m in registry.built(registry.load()):
        for field in ("id", "blurb", "summary", "built_with", "tag", "href", "medium"):
            assert m.get(field), f"{m['id']} missing {field}"
        assert m["medium"] in ("browser", "terminal")


# ---- propose --------------------------------------------------------------

def test_propose_is_deterministic():
    a = propose.propose(42)
    b = propose.propose(42)
    assert a == b


def test_propose_varies_with_seed():
    prompts = {propose.propose(s)["prompt"] for s in range(12)}
    assert len(prompts) > 1


def test_propose_structure():
    m = propose.propose(7)
    assert m["provenance"] == "loom"
    assert m["status"] == "proposed"
    assert m["prompt"].startswith("Take ")
    # the brief names a substrate and a rule drawn from the vocabulary
    assert any(s in m["prompt"] for s in primitives.SUBSTRATES)


def test_propose_many_unique_ids():
    batch = propose.propose_many(3, 8)
    ids = [m["id"] for m in batch]
    assert len(ids) == len(set(ids))


def test_propose_avoids_existing_ids():
    existing = [m["id"] for m in registry.load()]
    batch = propose.propose_many(99, 10, existing_ids=existing)
    assert not (set(m["id"] for m in batch) & set(existing))


# ---- surprise proxy -------------------------------------------------------

def test_score_returns_positive_numbers_for_built():
    for m in registry.built(registry.load()):
        s = surprise.score(m)
        assert s is not None, m["id"]
        assert s["amplification"] > 0
        assert 0 < s["richness"] <= 1.0001


def test_score_all_covers_every_built_mission():
    missions = registry.load()
    scored = {s["id"] for s in surprise.score_all(missions)}
    built = {m["id"] for m in registry.built(missions)}
    assert scored == built


def test_amplification_orders_generative_above_parser():
    """A generative-visual system should amplify its rule far more than a parser.

    This is the proxy's intended bias, stated as a check: the Mandelbrot image
    is a tiny rule blown up into a rich field; calc's session is not.
    """
    scores = {s["id"]: s["amplification"] for s in surprise.score_all(registry.load())}
    assert scores["fractal"] > scores["calc"]


# ---- gallery --------------------------------------------------------------

def test_build_index_is_wellformed_and_complete():
    missions = registry.load()
    html = gallery.build_index(missions)
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    # every built mission appears as a card, with a score badge
    built = registry.built(missions)
    for m in built:
        assert f'href="{m["href"]}"' in html
    assert html.count('class="card"') == len(built)
    assert html.count('class="score"') == len(built)
    # the live flow-field hero is preserved
    assert 'id="field"' in html
    assert "requestAnimationFrame" in html


def test_index_escapes_ampersands():
    # fractal's blurb contains "Mandelbrot & Julia"
    html = gallery.build_index(registry.load())
    assert "Mandelbrot &amp; Julia" in html
    assert "Mandelbrot & Julia" not in html


def test_readme_table_has_every_built_mission():
    missions = registry.load()
    table = gallery.build_readme_table(missions)
    for m in registry.built(missions):
        assert f"[**{m['id']}**](./{m['id']})" in table


def test_gallery_renders_proposed_missions(tmp_path):
    missions = registry.load()
    missions = missions + [propose.propose(1234)]
    html = gallery.build_index(missions)
    assert "On the loom" in html
    assert "loom-item" in html


def test_update_readme_roundtrips_markers(tmp_path):
    # a minimal README with the markers; update should replace between them only
    p = tmp_path / "README.md"
    p.write_text(
        "intro\n\n"
        f"{gallery.TABLE_START}\nOLD TABLE\n{gallery.TABLE_END}\n\nfooter\n",
        encoding="utf-8",
    )
    gallery.update_readme(registry.load(), path=str(p))
    out = p.read_text(encoding="utf-8")
    assert out.startswith("intro")
    assert out.rstrip().endswith("footer")
    assert "OLD TABLE" not in out
    assert "| Project | What it is | Built with |" in out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
