"""The mission registry — load/save the JSON spine of flow.

A *mission* is a brief sent to Claude Code and what came back. The registry is
the single source of truth: the surprise proxy reads the missions to score
their outputs, and the gallery is regenerated from them. Nothing downstream is
hand-maintained.
"""

import json
import os

# repo root is the parent of this package directory
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(ROOT, "loom", "missions.json")


def load(path=REGISTRY_PATH):
    """Return the list of mission dicts, in registry (curated) order."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("missions", [])


def save(missions, path=REGISTRY_PATH):
    """Write missions back, preserving the leading `_about` note."""
    about = (
        "The mission registry — the spine of flow. Each entry is a brief sent "
        "to Claude Code and what came back. loom reads this to score the outputs "
        "and regenerate the gallery; nothing here is hand-rendered downstream. "
        "Built missions carry the source files that ARE the rule (for the "
        "surprise proxy) and the example artifact that fell out of it."
    )
    payload = {"_about": about, "missions": missions}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def built(missions):
    """Missions that have been built (and so can be scored and shown)."""
    return [m for m in missions if m.get("status") == "built"]


def proposed(missions):
    """Missions the loom has dreamed up but nobody has built yet."""
    return [m for m in missions if m.get("status") == "proposed"]


def resolve(rel_path):
    """Resolve a registry-relative path (e.g. 'flowfield/noise.js') to disk."""
    return os.path.join(ROOT, rel_path)
