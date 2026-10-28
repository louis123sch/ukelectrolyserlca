#!/usr/bin/env python
"""Check the written LCA map against the model it is generated from.

    python scripts/check_lca_map.py                 # every section, Brightway included
    python scripts/check_lca_map.py --no-brightway  # what tests/test_lca_map.py runs

``build_lca_map.py`` refuses to call a map clean that disagrees with the model
(a coefficient the trace does not reach, a link to nothing, a pinned figure off
its activity's score, an exchange not drawn) and writes what it found into
``lca_map.json["problems"]``. This re-reads the written map and holds it to the
live code, so a map built before an edit is caught:

1  the fingerprint of what it was built from against what is live now
2  the build's own problem list is empty
3  the graph: every link joins two boxes, every box is reachable from the study
4  the LP's terms: the map's set and expressions against dc_model, evaluated now
5  every activity every inventory module declares is a box, with all its exchanges
6  the energy tab against a fresh energy_section(), and the page against the JSON
7  (Brightway) every trace step re-recorded now, at the value the map shows

Prints every mismatch; exits 1 if any.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

MAP = ROOT / "optimisation_outputs" / "lca_map.json"
HTML = ROOT / "optimisation_outputs" / "lca_map.html"
problems: list[str] = []
checked = 0


def bad(msg):
    problems.append(msg)
    print("  FAIL", msg)


def ok(n=1):
    global checked
    checked += n


def main(use_bw: bool = True) -> int:
    problems.clear()
    if not MAP.exists():
        bad("no lca_map.json — run scripts/build_lca_map.py")
        return 1
    m = json.loads(MAP.read_text(encoding="utf-8"))
    nodes, edges = m["nodes"], m["edges"]

    print("1. fingerprint")
    import map_fingerprint as F
    diffs = F.compare((m.get("meta") or {}).get("fingerprint"))
    for d in diffs:
        bad("stale map — " + d)
    ok()

    print("2. the build's own checks")
    for p in m.get("problems", []):
        bad("build reported: " + p)
    ok()

    print("3. the graph")
    kids = {}
    for p, c, _d in edges:
        if p not in nodes or c not in nodes:
            bad(f"link {p} -> {c} joins a box that does not exist")
        kids.setdefault(p, []).append(c)
        ok()
    seen, stack = set(), [m["root"]]
    while stack:
        n = stack.pop()
        if n not in seen:
            seen.add(n)
            stack.extend(kids.get(n, []))
    for n in nodes:
        if n not in seen:
            bad(f"box {n} is not reachable from the study")
    ok(len(nodes))

    print("4. the LP's terms")
    from build_lca_map import MAIN, term_table
    from optimisation import dc_model as M
    zero = {f.name: 0.0 for f in dataclasses.fields(M.Tech)
            if f.name != "labels" and f.default is dataclasses.MISSING}
    tech = M.Tech(**zero, labels={"h2_colour": MAIN.get("h2_colour")})
    live = term_table(tech)
    mapped = {n["key"]: n for n in nodes.values() if n["kind"] == "term" and not n.get("variant")}
    for k, t in live.items():
        if k not in mapped:
            bad(f"LP term {k!r} is not in the map")
        elif mapped[k]["expr"] != t["expr"]:
            bad(f"LP term {k!r}: map has {mapped[k]['expr']!r}, dc_model now gives {t['expr']!r}")
        ok()
    for k in mapped:
        if k not in live:
            bad(f"the map shows a term {k!r} that dc_model no longer has")

    print("5. every inventory activity and exchange")
    from optimiser_lca import build as fg_build
    shown = {(n.get("database"), n.get("code")): nid for nid, n in nodes.items() if n["kind"] == "foreground"}
    out_links = {}
    for p, c, _d in edges:
        out_links[p] = out_links.get(p, 0) + 1
    for _name, inv in fg_build.inventories():
        for a in inv.activities:
            nid = shown.get((inv.database, a.code))
            if nid is None:
                bad(f"{inv.database}/{a.code} is declared but not in the map")
                continue
            want = len(a.technosphere) + len(a.biosphere)
            if out_links.get(nid, 0) != want:
                bad(f"{inv.database}/{a.code}: {want} rows in the module, {out_links.get(nid, 0)} drawn")
            ok()

    print("6. energy tab and page")
    from build_lca_map import add_energy
    fresh = add_energy({})["energy"]
    if json.loads(json.dumps(fresh, default=str)) != m.get("energy"):
        bad("the energy tab differs from a fresh energy_section() — rerun with --html-only")
    ok()
    page = HTML.read_text(encoding="utf-8") if HTML.exists() else ""
    blob = MAP.read_text(encoding="utf-8").replace("</", "<\\/")
    if blob not in page:
        bad("lca_map.html does not carry lca_map.json — rerun with --html-only")
    ok()

    if use_bw:
        print("7. every trace step, re-recorded now")
        from build_lca_map import merge, record
        from optimisation.trace import _same
        steps, _r, _p = merge(record())
        mapped_steps = {n["key"]: n for n in nodes.values() if n["kind"] == "step"}
        for k, s in steps.items():
            n = mapped_steps.get(k)
            if n is None:
                bad(f"trace step {k} is recorded now but not in the map")
            elif not _same(n.get("value"), s.get("value")):
                bad(f"trace step {k}: map {n.get('value')!r}, live {s.get('value')!r}")
            ok()
        for k in mapped_steps:
            if k not in steps:
                bad(f"the map shows a step {k} the code no longer records")

    print(f"\n{checked} checks, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(use_bw="--no-brightway" not in sys.argv))
