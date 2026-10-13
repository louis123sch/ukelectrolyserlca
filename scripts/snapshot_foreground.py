"""Freeze every foreground database to JSON, and diff two such freezes.

The acceptance test for any change to how the inventories are *held* is that
what gets written to Brightway does not change. This dumps each foreground
activity — name, reference product, unit, location, and every exchange's input
key, amount, unit and type — in a canonical order, so two dumps can be diffed.

    python scripts/snapshot_foreground.py                  # -> optimisation_outputs/foreground_snapshot.json
    python scripts/snapshot_foreground.py --out before.json
    python scripts/snapshot_foreground.py --compare before.json after.json

Comments are recorded but compared separately: they are documentation, and a
reworded comment is not a changed inventory.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "optimisation_outputs" / "foreground_snapshot.json"


def snapshot() -> dict:
    import bw2data as bd
    import lca_helpers as H
    from optimiser_lca import registry

    H.setup_brightway()
    out = {}
    for db_name in registry.DATABASES:
        if db_name not in bd.databases:
            out[db_name] = None
            continue
        db = bd.Database(db_name)
        acts = {}
        for a in db:
            exchanges = []
            for e in a.exchanges():
                exchanges.append({
                    "input": list(e.input.key),
                    "amount": float(e["amount"]),
                    "unit": e.get("unit", ""),
                    "type": e["type"],
                    "comment": e.get("comment", ""),
                })
            exchanges.sort(key=lambda x: (x["type"], x["input"], x["amount"]))
            acts[a["code"]] = {
                "name": a["name"],
                "reference product": a.get("reference product"),
                "unit": a.get("unit"),
                "location": a.get("location"),
                "comment": a.get("comment", ""),
                "exchanges": exchanges,
            }
        out[db_name] = dict(sorted(acts.items()))
    return out


def _strip_comments(snap: dict) -> dict:
    out = {}
    for db, acts in snap.items():
        if acts is None:
            out[db] = None
            continue
        out[db] = {}
        for code, a in acts.items():
            out[db][code] = {k: v for k, v in a.items() if k != "comment"}
            out[db][code]["exchanges"] = [
                {k: v for k, v in e.items() if k != "comment"} for e in a["exchanges"]]
    return out


def compare(before: dict, after: dict, rel_tol: float = 1e-12) -> list[str]:
    """Human-readable list of differences in the inventory proper."""
    problems, notes = [], []
    b, a = _strip_comments(before), _strip_comments(after)
    for db in sorted(set(b) | set(a)):
        if b.get(db) is None or a.get(db) is None:
            if b.get(db) != a.get(db):
                problems.append(f"{db}: present in one snapshot only")
            continue
        for code in sorted(set(b[db]) | set(a[db])):
            if code not in b[db]:
                problems.append(f"{db}/{code}: new activity")
                continue
            if code not in a[db]:
                problems.append(f"{db}/{code}: activity missing")
                continue
            x, y = b[db][code], a[db][code]
            for field in ("name", "reference product", "unit", "location"):
                if x[field] != y[field]:
                    problems.append(f"{db}/{code}: {field} {x[field]!r} -> {y[field]!r}")
            ex, ey = x["exchanges"], y["exchanges"]
            if len(ex) != len(ey):
                problems.append(f"{db}/{code}: {len(ex)} -> {len(ey)} exchanges")
            # Match exchanges by (type, input); amounts compared with a tolerance.
            # The unit label on an exchange is documentation (the input's own
            # unit is what Brightway uses), so a changed label is reported as a
            # note, not a difference.
            def keyed(exs):
                d = {}
                for e in exs:
                    d.setdefault((e["type"], tuple(e["input"])), []).append(e["amount"])
                return d
            ux = {(e["type"], tuple(e["input"])): e["unit"] for e in ex}
            uy = {(e["type"], tuple(e["input"])): e["unit"] for e in ey}
            for k in sorted(set(ux) & set(uy), key=str):
                if ux[k] != uy[k]:
                    notes.append(f"{db}/{code}: {k}: unit label {ux[k]!r} -> {uy[k]!r}")
            kx, ky = keyed(ex), keyed(ey)
            for k in sorted(set(kx) | set(ky), key=str):
                ax, ay = sorted(kx.get(k, [])), sorted(ky.get(k, []))
                if len(ax) != len(ay):
                    problems.append(f"{db}/{code}: {k}: {ax} -> {ay}")
                    continue
                for p, q in zip(ax, ay):
                    if abs(p - q) > rel_tol * max(abs(p), abs(q), 1e-300):
                        problems.append(f"{db}/{code}: {k}: amount {p!r} -> {q!r}")
    return problems, notes


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = ap.parse_args(argv)
    if args.compare:
        before = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))
        after = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))
        problems, notes = compare(before, after)
        for n in notes:
            print("  note: " + n)
        if problems:
            print(f"{len(problems)} difference(s):")
            for p in problems:
                print("  " + p)
            return 1
        print("Inventories identical (comments not compared).")
        return 0
    snap = snapshot()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(snap, indent=1), encoding="utf-8")
    n = sum(len(v) for v in snap.values() if v)
    print(f"Wrote {args.out} — {n} activities in {sum(1 for v in snap.values() if v)} databases.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
