#!/usr/bin/env python
"""Check the written cost map against the model it is generated from.

    python scripts/check_cost_map.py           # every section, the live re-record included
    python scripts/check_cost_map.py --quick   # what tests/test_cost_map.py runs

``build_cost_map.py`` refuses to call a map clean that disagrees with the model
and writes what it found into ``cost_map.json["problems"]``. This re-reads the
written map and holds it to the live code, so a map built before an edit is
caught:

1  the fingerprint of what it was built from (the traced code, the source
   register) against what is live now
2  the build's own problem list is empty
3  the graph: every link joins two boxes, every box is reachable from the study
4  the LP's cost terms: the map's set and expressions against dc_model, now
5  the sources: every citation is a live register key, every source box says
   what the register says, every transcribed number cites something
6  the page carries the JSON
7  (live) every step re-recorded now, at the value the map shows

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

MAP = ROOT / "optimisation_outputs" / "cost_map.json"
HTML = ROOT / "optimisation_outputs" / "cost_map.html"
OPTION_ONLY = {"grid connection fixed charges"}     # a term only once the optimiser chooses the price list
problems: list[str] = []
checked = 0


def bad(msg):
    problems.append(msg)
    print("  FAIL", msg)


def ok(n=1):
    global checked
    checked += n


def main(live: bool = True) -> int:
    problems.clear()
    if not MAP.exists():
        bad("no cost_map.json — run scripts/build_cost_map.py")
        return 1
    m = json.loads(MAP.read_text(encoding="utf-8"))
    nodes, edges = m["nodes"], m["edges"]

    print("1. fingerprint")
    import map_fingerprint as F
    from optimisation import source_register as SR
    stamped = (m.get("meta") or {}).get("fingerprint") or {}
    now = {"trace_code": F.trace_code_digest(),
           "source_register": F._digest({k: dataclasses.asdict(s) for k, s in SR.SOURCES.items()})}
    for k, v in now.items():
        if stamped.get(k) != v:
            bad(f"stale map — {k}: map {stamped.get(k)} vs live {v}")
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

    print("4. the LP's cost terms")
    from build_cost_map import MAIN, term_table
    from optimisation import dc_model as M
    zero = {f.name: 0.0 for f in dataclasses.fields(M.Tech)
            if f.name != "labels" and f.default is dataclasses.MISSING}
    tech = M.Tech(**zero, labels={"h2_colour": MAIN.get("h2_colour")})
    fresh = term_table(tech)
    mapped = {n["key"]: n for n in nodes.values() if n["kind"] == "term" and not n.get("variant")}
    for k, t in fresh.items():
        if k not in mapped:
            bad(f"LP cost term {k!r} is not in the map")
        elif not any(w in mapped[k]["expr"] for w in ("option", "price[")) and mapped[k]["expr"] != t["expr"]:
            # (written over the price lists and voltage groups when the optimiser chooses: not comparable)
            bad(f"LP cost term {k!r}: map has {mapped[k]['expr']!r}, dc_model now gives {t['expr']!r}")
        ok()
    for k in mapped:
        if k not in fresh and k not in OPTION_ONLY and k not in ("connection fixed", "major-hazard compliance"):
            bad(f"the map shows a cost term {k!r} that dc_model no longer has")

    print("5. the sources")
    for nid, n in nodes.items():
        if n["kind"] == "source":
            live_src = SR.SOURCES.get(n["key"])
            if live_src is None:
                bad(f"source box {n['key']} is no longer in the register")
            elif (n["name"], n.get("link") or "") != (live_src.title, live_src.link):
                bad(f"source box {n['key']} differs from the register")
            ok()
        if n["kind"] != "step" or n.get("side") != "cost":
            continue
        for c in n.get("cites") or []:
            if c["source"] not in SR.SOURCES:
                bad(f"{n['key']} cites {c['source']!r}, which the register does not have")
            ok()
        if n.get("grade") in ("transcribed", "proxy") and not (n.get("cites") or n.get("source")):
            bad(f"{n['key']} is graded {n['grade']} and cites nothing")
        if n.get("grade") == "assumed" and not (n.get("note") or n.get("cites") or n.get("source")):
            bad(f"{n['key']} is assumed with no note saying why")
        ok()

    print("6. the page")
    page = HTML.read_text(encoding="utf-8") if HTML.exists() else ""
    blob = MAP.read_text(encoding="utf-8").replace("</", "<\\/")
    if blob not in page:
        bad("cost_map.html does not carry cost_map.json — rerun with --html-only")
    ok()

    if live:
        print("7. every step, re-recorded now")
        from build_cost_map import merge, record
        from optimisation.trace import _same
        runs, _cases, _s, _m = record()
        steps, _r, _p = merge(runs)
        shown = {n["key"]: n for n in nodes.values() if n["kind"] == "step"}
        for k, n in shown.items():
            s = steps.get(k)
            if s is None:
                bad(f"step {k} is in the map but not recorded now")
            elif not _same(n.get("value"), s.get("value")):
                bad(f"step {k}: map {n.get('value')!r}, live {s.get('value')!r}")
            ok()
        for k, s in steps.items():
            if s.get("side") == "cost" and k not in shown:
                bad(f"cost step {k} is recorded now but not in the map")

    print(f"\n{checked:,} checks, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(live="--quick" not in sys.argv))
