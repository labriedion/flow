"""loom command line.

  python -m loom missions              list the registry
  python -m loom propose [--seed N] [--count K] [--save]
                                       dream up new missions (deterministic by seed)
  python -m loom score [--id X]        weigh the surprise proxy for built missions
  python -m loom gallery [--write]     regenerate index.html + README table
"""

import argparse
import sys

from . import gallery, propose as proposer, registry, surprise


def _cmd_missions(args):
    missions = registry.load()
    built = registry.built(missions)
    prop = registry.proposed(missions)
    print(f"{len(missions)} missions — {len(built)} built, {len(prop)} on the loom\n")
    for m in built:
        seeded = f"  (grew out of {m['seeded_by']})" if m.get("seeded_by") else ""
        print(f"  · {m['id']:<11} {m['provenance']:<6} {m.get('date','')}{seeded}")
        if m.get("reflection"):
            print(f"      ↳ {m['reflection']}")
    for m in prop:
        print(f"  ◦ {m['id']:<11} loom   (proposed, seed {m.get('seed')})")
    return 0


def _cmd_propose(args):
    missions = registry.load()
    existing = [m["id"] for m in missions]
    batch = proposer.propose_many(args.seed, args.count, existing_ids=existing)
    for m in batch:
        seeded = f"  · seeded by {m['seeded_by']}" if m.get("seeded_by") else ""
        print(f"\n┌─ {m['id']}{seeded}")
        # wrap the prompt to a readable width
        print(f"│  {m['prompt']}")
    print()
    if args.save:
        missions.extend(batch)
        registry.save(missions)
        print(f"saved {len(batch)} proposed mission(s) to the registry.")
    else:
        print("(dry run — pass --save to add these to the registry)")
    return 0


def _cmd_score(args):
    missions = registry.load()
    scores = surprise.score_all(missions)
    if args.id:
        scores = [s for s in scores if s["id"] == args.id]
        if not scores:
            print(f"no scorable built mission named {args.id!r}", file=sys.stderr)
            return 1
    scores.sort(key=lambda s: s["amplification"], reverse=True)
    print(f"{'mission':<12} {'rule':>9} {'output':>10} {'amp':>8} {'richness':>9}")
    print(f"{'':<12} {'(comp B)':>9} {'(comp B)':>10} {'out/rule':>8} {'out/raw':>9}")
    print("-" * 52)
    for s in scores:
        print(
            f"{s['id']:<12} {s['rule_bytes']:>9} {s['output_bytes']:>10} "
            f"{surprise.fmt_amplification(s['amplification']):>8} "
            f"{s['richness']:>8.2f}"
        )
    print(
        "\namp = how much incompressible structure the rule blew up into "
        "(higher = more emergent).\nA proxy, not a verdict — see loom/surprise.py "
        "for what it can and can't see."
    )
    return 0


def _cmd_gallery(args):
    missions = registry.load()
    if args.write:
        ip = gallery.write_index(missions)
        rp = gallery.update_readme(missions)
        print(f"wrote {ip}")
        print(f"updated table in {rp}")
    else:
        html = gallery.build_index(missions)
        print(html)
        print(
            f"\n[dry run] {len(html)} bytes of index.html above; "
            "pass --write to update index.html and README.",
            file=sys.stderr,
        )
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="loom", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("missions", help="list the registry")

    p = sub.add_parser("propose", help="dream up new missions")
    p.add_argument("--seed", type=int, default=1, help="reproducible seed")
    p.add_argument("--count", type=int, default=3, help="how many to propose")
    p.add_argument("--save", action="store_true", help="append them to the registry")

    p = sub.add_parser("score", help="weigh the surprise proxy")
    p.add_argument("--id", help="just this mission")

    p = sub.add_parser("gallery", help="regenerate index.html + README table")
    p.add_argument("--write", action="store_true", help="write files (else dry run)")

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    return {
        "missions": _cmd_missions,
        "propose": _cmd_propose,
        "score": _cmd_score,
        "gallery": _cmd_gallery,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
