#!/usr/bin/env python
"""Build the cost map from the model itself: nothing in it is written by hand.

    python scripts/build_cost_map.py              # map JSON + optimisation_outputs/cost_map.html
    python scripts/build_cost_map.py --html-only  # re-wrap the page around the last map

The cost twin of ``build_lca_map.py``, and built the same way: one box per
thing, read off the code four ways.

1. **The LP's cost terms.** ``dc_model.objective_terms``'s ``cost_capital``
   and ``cost_operational`` groups, evaluated on symbols, so each term's
   expression and the coefficients it multiplies are read from the function
   the LP is built with. With connection options on the Tech (COST_PLAN §1.11)
   the grid terms are read over the options: one coefficient per price list.
2. **How each number is made.** ``build_series`` and ``build_tech`` run inside
   ``optimisation.trace.recording()``. Every ``T.cost(...)`` the cost modules
   call is a box: value, unit, grade, what it used, the file, line and
   expression that computed it, and where it was read (``cites``).
3. **The sources.** Every citation is a key of
   ``optimisation.source_register.SOURCES``; each source is a box, with every
   number that cites it.
4. **One solve.** The reference run, cost-optimal with every asset on offer and
   the optimiser choosing its price list, so each term shows the pounds it
   came to — "which box is most of the bill" is what a cost map answers.

Variants as the LCA map does them (the other bought colours, AE and SOEC): a
step whose number differs gets its own box, labelled. The low and high cost
cases are recorded too and shown on each box's datasheet rather than as boxes.

The build refuses to write a map that disagrees with the model: a cost
coefficient the trace does not reach, a link to nothing, a citation to no
registered source, a transcribed number with no source, an import price whose
parts do not add back, solved terms that do not add to the solve's total.
``check_cost_map.py`` re-reads the written map for the same things.
"""
from __future__ import annotations

import dataclasses
import json
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_lca_map import (Graph, Quantities, Sym, _reachable, chain_of, merge,  # noqa: E402
                           parse_data_gaps, parse_md_sections)

OUT = ROOT / "optimisation_outputs" / "cost_map.json"
HTML_TEMPLATE = Path(__file__).with_name("cost_map_template.html")
HTML_OUT = ROOT / "optimisation_outputs" / "cost_map.html"

# The run the map shows: the LCA map's — London, the 2025 window, 100 MW IT,
# green hydrogen bought, PEM — solved for least cost with every asset on offer
# and the optimiser choosing the grid's price list (the default "room" mode).
SITE, START, END, SIZE_MW_IT = "london", "2025-01-01", "2025-12-29", 100.0
MAIN = {"h2_colour": "green"}
VARIANTS = [("grey hydrogen", {"h2_colour": "grey"}), ("blue hydrogen", {"h2_colour": "blue"}),
            ("turquoise hydrogen", {"h2_colour": "turquoise"}),
            ("AE electrolyser", {"h2_colour": "green", "ely_tech": "AE operation"}),
            ("SOEC electrolyser", {"h2_colour": "green", "ely_tech": "SOEC operation"})]
CASES = ("low", "high")
# The solve's time step. A year at 30 minutes with every asset and the price-list
# switches did not finish in 30 minutes (30 Oct 2026); dc_inputs.resample
# measured 2 h at -0.2 % on cost. Every number on the map is still recorded
# from the half-hourly build; only the pounds per term come from this solve.
SOLVE_HOURS = 2.0
SIDES = ("cost_capital", "cost_operational")
NEEDS_SOURCE = ("transcribed", "proxy")
TERM_NAMES = {
    "wind": "Onshore wind", "offshore wind": "Offshore wind", "solar": "Solar PV",
    "battery": "Battery (power and energy)", "electrolyser": "Electrolyser",
    "H2 tank": "Hydrogen tank", "fuel cell": "Fuel cell, with stack and balance-of-plant replacements",
    "grid connection": "Grid connection, per MW (local capacity charge and build cost)",
    "grid connection fixed charges": "Grid connection, per year (residual and fixed charges, cable)",
    "connection fixed": "Grid connection, per year (residual and fixed charges, cable)",
    "grid winter-peak charge": "National grid locational charge, on winter-peak demand",
    "grid energy + network": "Grid imports (half-hourly price, every part)",
    "electrolyser stacks and water": "Electrolyser stacks and water", "unserved (VoLL)": "Unserved load (penalty)",
    "export credit": "Export credit",
}
TERM_STEPS = {"unserved (VoLL)": ["cost.unserved.voll_per_MWh"]}


# =============================================================================
# 1. The trace: main run, variants, and the cost cases
# =============================================================================
def record():
    from optimisation import dc_inputs as I, trace as T
    with T.recording() as rec:
        series, meta = I.build_series(SITE, START, END, SIZE_MW_IT)
        tech = I.build_tech(SITE, meta, **MAIN)
    runs = [("", rec, tech)]
    for label, kw in VARIANTS:
        with T.recording() as r:
            t = I.build_tech(SITE, meta, **kw)
        runs.append((label, r, t))
    cases = {}
    for case in CASES:
        with T.recording() as r:
            I.build_tech(SITE, meta, cost_case=case, **MAIN)
        cases[case] = r
    return runs, cases, series, meta


def slug(key: str) -> str:
    """An option's trace slug, as ``dc_inputs.with_connection_options`` makes it."""
    return re.sub(r"\W+", "_", key).strip("_")


# =============================================================================
# 2. The LP's cost terms, on symbols
# =============================================================================
def term_table(tech) -> dict:
    """{term key: {side, expr, fields, options, vars, series}} from dc_model's own term function."""
    from optimisation import dc_model as M
    opts = M.connection_options_of(tech) or ()
    skip = {"labels", "connection_options"}
    coef = {f.name: Sym(f.name, {("coef", f.name)}) for f in dataclasses.fields(tech) if f.name not in skip}
    sym_opts = tuple(dataclasses.replace(
        o, cost_per_mw_year=Sym(f"option{i}.per_MW_year", {("opt", f"{i}:cost_per_MW_year")}),
        cost_fixed_per_year=Sym(f"option{i}.fixed_per_year", {("opt", f"{i}:cost_fixed_per_year")}))
        for i, o in enumerate(opts))
    sym_tech = dataclasses.replace(tech, **coef, connection_options=sym_opts or tech.connection_options)
    q = Quantities()
    for i in range(len(opts)):
        q[f"on_{i}"]                                   # the switches: objective_terms reads the options
    groups = sorted({o.group for o in opts})
    gs = {g: (Sym(f"price[{g}]", {("series", f"price:{g}")}), Sym(f"ci[{g}]", {("series", f"ci:{g}")}))
          for g in groups}
    series = SimpleNamespace(dt_hours=Sym("Δt", {("series", "dt")}),
                             annual_scale=Sym("annual_scale", {("series", "annual_scale")}), grid_groups=None)
    terms = M.objective_terms(q, series, sym_tech, price=Sym("price", {("series", "price")}),
                              ci=Sym("ci", {("series", "ci")}), group_series=gs or None)
    out = {}
    for side in SIDES:
        for k, s in terms[side].items():
            s = Sym.of(s)
            out[k] = {"side": side, "expr": s.text,
                      "fields": sorted(n for kind, n in s.names if kind == "coef"),
                      "options": sorted({n for kind, n in s.names if kind == "opt"}),
                      "vars": sorted(n for kind, n in s.names if kind == "var"),
                      "series": sorted(n for kind, n in s.names if kind == "series")}
    return out


# =============================================================================
# 3. One solve of the reference run
# =============================================================================
def solve(series, meta, tech):
    from optimisation import dc_architectures as A, dc_inputs as I, dc_model as M
    series = I.resample(series, SOLVE_HOURS)
    flags = {f: True for f in A.ASSET_FLAGS}
    flags["buy_h2_2"] = False                      # one bought colour, as the run is labelled
    assets = A.custom(flags, grid_limit_mw=meta["connection_limit_mw"],
                      grid_floor_mw=meta.get("connection_floor_mw", 0.0))
    t = time.time()
    m, V, obj = M.build_model(series, assets, tech, objective="cost")
    M.solve(m)
    q = M.solution_quantities(V)
    sc = M.score(q, series, tech)
    tot = M.totals(obj)
    served = float(((series.demand_mw - q["unserved"]) * series.dt_hours).sum()) * series.annual_scale \
        if hasattr(q["unserved"], "__len__") else float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale
    build = {k: float(v) for k, v in q.items() if k.startswith("cap_") and not hasattr(v, "__len__")}
    return {"terms": {s: sc[s] for s in SIDES}, "totals": tot, "served_MWh": served,
            "connection": M.connection_status(V, M.connection_options_of(tech)),
            "build": build, "seconds": round(time.time() - t)}


# =============================================================================
# The graph
# =============================================================================
def build():
    from optimisation import dc_model as M, source_register as SR
    from map_fingerprint import trace_code_digest, git_head, _digest

    t0 = time.time()
    problems = []
    runs, cases, series, meta = record()
    steps, renames, p = merge(runs)
    problems += p
    main_tech = runs[0][2]
    opts = M.connection_options_of(main_tech) or ()
    solved = solve(series, meta, main_tech)
    print(f"solved the reference run in {solved['seconds']} s")
    gr = Graph()

    # ---- the cost cases, on each box of the main run
    for k, s in steps.items():
        if "variant" in s:
            continue
        vals = {c: cases[c].steps[k].value for c in CASES if k in cases[c].steps}
        if any(v is not None and s.get("value") is not None and abs(v - s["value"]) > 1e-9 * max(1.0, abs(v))
               for v in vals.values()):
            s["cases"] = {"low": vals.get("low"), "central": s.get("value"), "high": vals.get("high")}

    # ---- every recorded step a box; links by "uses"
    for k, s in steps.items():
        gr.add(f"step:{k}", kind="step", name=s["title"], key=k, value=s.get("value"), unit=s.get("unit"),
               grade=s.get("grade"), source=s.get("source"), note=s.get("note"), inputs=s.get("inputs"),
               where=s.get("where"), function=s.get("function"), code=s.get("code"), side=s.get("side"),
               variant=s.get("variant"), cases=s.get("cases"), cites=s.get("cites"))
    for k, s in steps.items():
        for u in s.get("uses", []):
            if isinstance(u, str):
                if u not in steps:
                    problems.append(f"trace: {k} uses {u!r}, which no step recorded")
                    continue
                gr.link(f"step:{k}", f"step:{u}")

    # ---- the sources: a box each, linked from every number that cites it
    cited = {}
    for k, s in steps.items():
        for c in s.get("cites") or []:
            key = c.get("source")
            if key not in SR.SOURCES:
                problems.append(f"source: {k} cites {key!r}, which source_register.SOURCES does not have")
                continue
            src = SR.SOURCES[key]
            gr.add(f"src:{key}", kind="source", name=src.title, key=key, publisher=src.publisher, date=src.date,
                   source_kind=src.kind, link=src.link, held=src.held, basis=src.basis, note=src.note)
            gr.link(f"step:{k}", f"src:{key}", note=c.get("at"))
            cited.setdefault(key, []).append(k)
        g = s.get("grade")
        if g in NEEDS_SOURCE and not (s.get("cites") or s.get("source")) and s.get("side") == "cost":
            problems.append(f"unsourced: {k} is graded {g} and cites nothing")
        if g == "assumed" and not (s.get("note") or s.get("cites") or s.get("source")) and s.get("side") == "cost":
            problems.append(f"unexplained: {k} is assumed with no note saying so")
        if g == "derived" and not (s.get("uses") or s.get("cites") or s.get("note")) and s.get("side") == "cost":
            problems.append(f"unaccounted: {k} is derived from nothing recorded")

    # ---- the import price: its parts must add back to its mean
    for k, s in steps.items():
        if k.startswith("cost.import_price.") and k.endswith(".mean"):
            parts = [steps[u]["value"] for u in s["uses"] if u in steps]
            if abs(sum(parts) - s["value"]) > 1e-9 * max(1.0, abs(s["value"])):
                problems.append(f"import price {k}: parts add to {sum(parts):.9g}, the series mean is {s['value']:.9g}")

    # ---- the LP's cost terms
    tot = solved["totals"]
    study = gr.add("study", kind="study", name="The study: cost of a year of data-centre demand served",
                   score=tot["cost_GBP_per_year"],
                   note=f"Real 2025 £ unless a box says otherwise. Shown for {SITE}, {START} to {END}, "
                        f"{SIZE_MW_IT:g} MW IT, {MAIN['h2_colour']} hydrogen bought, solved for least cost with "
                        "every asset on offer and the optimiser choosing the grid's price list. Pounds per term "
                        f"come from that solve at {SOLVE_HOURS:g}-hour steps (about 0.2 % off the half-hourly "
                        "cost, dc_inputs.resample); every other number is the half-hourly build's.")
    lp_root = gr.add("lp", kind="group", name="The LP's cost objective, by technology",
                     score=tot["cost_GBP_per_year"] - tot["cost_const_GBP_per_year"],
                     note="Terms read from dc_model.objective_terms (cost_capital, cost_operational); grouped by "
                          "dc_model.CHAINS. Pounds per year in the reference run.")
    gr.link(study, lp_root, contribution=tot["cost_GBP_per_year"] - tot["cost_const_GBP_per_year"])
    chain_nodes, terms_seen, chain_sum = {}, {}, {}
    amounts = {k: v for side in SIDES for k, v in solved["terms"][side].items()}
    tech_fields = {f.name for f in dataclasses.fields(main_tech)}
    chosen = (solved.get("connection") or {}).get("index")
    ref_group = meta.get("connection_voltage")

    def coefficient_node(field, tech, rename, label):
        key = rename.get(f"coefficient.{field}", f"coefficient.{field}")
        if key not in steps:
            default = next(f.default for f in dataclasses.fields(tech) if f.name == field)
            if default is dataclasses.MISSING or float(getattr(tech, field)) != float(default):
                problems.append(f"coefficient {field} has no trace step: wrap it in T.cost where build_tech sets it")
            return gr.add(f"const:{field}", kind="constant", name=f"{field} (a default in dc_model.Tech)",
                          value=float(getattr(tech, field)), grade="assumed")
        if abs(steps[key]["value"] - float(getattr(tech, field))) > 1e-9 * max(1.0, abs(float(getattr(tech, field)))):
            problems.append(f"coefficient {field}{' [' + label + ']' if label else ''}: the trace gives "
                            f"{steps[key]['value']:.9g}, build_tech gives {float(getattr(tech, field)):.9g}")
        return f"step:{key}"

    def option_node(spec, tech):
        i, what = spec.split(":")
        o = tech.connection_options[int(i)]
        key = f"connection.{slug(o.key)}.{what}"
        if key not in steps:
            problems.append(f"connection option {o.key}: {what} has no trace step")
            return None
        want = getattr(o, what.replace("cost_per_MW_year", "cost_per_mw_year"))
        if abs(steps[key]["value"] - float(want)) > 1e-9 * max(1.0, abs(float(want))):
            problems.append(f"connection option {o.key}: the trace gives {steps[key]['value']:.9g}, the option {want:.9g}")
        if int(i) == chosen:
            gr.nodes[f"step:{key}"]["chosen"] = True
        return f"step:{key}"

    def series_node(name):
        if name in ("dt", "annual_scale"):
            return None
        if name.startswith("price:"):
            return f"step:cost.import_price.group.{name[6:]}.mean"
        if name == "price":
            return (f"step:cost.import_price.group.{ref_group}.mean" if opts
                    else "step:cost.import_price.reference.mean")
        return None

    for (label, _rec, tech), rename in zip(runs, renames):
        for key, t in term_table(tech).items():
            uses = [coefficient_node(f, tech, rename, label) for f in t["fields"]]
            uses += [option_node(o, tech) for o in t["options"]]
            uses += [series_node(s) for s in t["series"]]
            uses += [f"step:{k}" for k in TERM_STEPS.get(key, []) if k in steps]
            uses = [u for u in uses if u]
            sig = tuple(sorted(uses))
            if key in terms_seen and terms_seen[key] == sig:
                continue
            name = TERM_NAMES.get(key) or (f"Bought hydrogen ({key[11:-1]})" if key.startswith("bought H2 (") else key)
            tid = f"term:{key}" + (f" [{label}]" if key in terms_seen else "")
            if key in terms_seen:
                name += f" [{label}]"
            terms_seen.setdefault(key, sig)
            chain = chain_of(key)
            if chain is None:
                problems.append(f"term {key!r} belongs to no dc_model.CHAINS chain")
                chain = "other"
            if chain not in chain_nodes:
                chain_nodes[chain] = gr.add(f"chain:{chain}", kind="chain", name=chain.capitalize())
                gr.link(lp_root, chain_nodes[chain])
            amount = amounts.get(key) if not label else None
            gr.add(tid, kind="term", name=name, key=key, side=t["side"], expr=t["expr"], variables=t["vars"],
                   variant=label or None, score=amount,
                   series=[s for s in t["series"] if s not in ("dt", "annual_scale")])
            if amount is not None:
                chain_sum[chain] = chain_sum.get(chain, 0.0) + amount
            gr.link(chain_nodes[chain], tid, contribution=amount)
            for u in uses:
                gr.link(tid, u)
            for f in t["fields"]:
                if f not in tech_fields:
                    problems.append(f"term {key!r} multiplies {f}, which Tech does not have")
            if key == "unserved (VoLL)" and not any(u.startswith("step:cost.unserved") for u in uses):
                problems.append("the value of lost load has no trace step")
    for chain, nid in chain_nodes.items():
        gr.nodes[nid]["score"] = chain_sum.get(chain, 0.0)
    for e in gr.edges:
        if e[0] == lp_root and e[1] in gr.nodes:
            e[2]["contribution"] = gr.nodes[e[1]].get("score")
    if tot["cost_const_GBP_per_year"]:
        cid = gr.add("term:connection fixed", kind="term", name=TERM_NAMES["connection fixed"], key="connection fixed",
                     side="constant", expr="cost_grid_fixed_per_year", score=tot["cost_const_GBP_per_year"],
                     note="A constant of the single-price-list model (dc_model.objective_constants)")
        gr.link(study, cid, contribution=tot["cost_const_GBP_per_year"])
        gr.link(cid, coefficient_node("cost_grid_fixed_per_year", main_tech, renames[0], ""))

    # every cost coefficient on the Tech reached by a term
    lp_fields = {f for t in term_table(main_tech).values() for f in t["fields"]}
    for f in tech_fields:
        if (f.startswith("cost_") or f.endswith("_gbp_per_kg")) and f not in lp_fields \
                and not (f == "cost_grid_fixed_per_year" and tot["cost_const_GBP_per_year"]):
            if opts and f in ("cost_grid_per_mw_year", "cost_grid_fixed_per_year"):
                continue                 # replaced by the options' own coefficients in the LP
            problems.append(f"Tech.{f} is a cost coefficient no cost term multiplies")

    # solved terms add back to the solve's total
    total_terms = sum(amounts.values()) + tot["cost_const_GBP_per_year"]
    if abs(total_terms - tot["cost_GBP_per_year"]) > 1e-6 * max(1.0, abs(tot["cost_GBP_per_year"])):
        problems.append(f"solve: the terms add to £{total_terms:,.2f}, the objective is £{tot['cost_GBP_per_year']:,.2f}")

    # ---- the sources group, so the tab and the graph agree
    src_root = gr.add("sources", kind="group", name="Sources: every document and data feed cited",
                      note="Each source is a key of optimisation/source_register.py; the numbers that cite it are "
                           "listed under Used by.")
    gr.link(study, src_root)
    for key in sorted(cited):
        gr.link(src_root, f"src:{key}")

    # ---- steps recorded on the cost side that no cost term reaches
    reachable = _reachable(gr, "study")
    side = [n for n in gr.nodes if n.startswith("step:") and n not in reachable
            and gr.nodes[n].get("side") == "cost"]
    if side:
        grp = gr.add("off-objective", kind="group", name="Recorded, but outside the cost objective",
                     note="Pound figures the cost code computes that no term in this run multiplies: the import "
                          "price on the single price list the load's size gives, which the optimiser's own choice "
                          "replaces; parts used only in a variant.")
        gr.link(study, grp)
        for n in side:
            if not any(c == n for p_, c, _d in gr.edges if p_ in side):
                gr.link(grp, n)
    # carbon-side steps no cost box reaches are the LCA map's, not this one's
    reachable = _reachable(gr, "study")
    for n in [n for n in gr.nodes if n not in reachable]:
        if n.startswith("step:") and gr.nodes[n].get("side") != "cost":
            del gr.nodes[n]
    gr.edges = [e for e in gr.edges if e[0] in gr.nodes and e[1] in gr.nodes]
    unreached = [n for n in gr.nodes if n not in _reachable(gr, "study")]
    if unreached:
        problems.append(f"{len(unreached)} boxes not reachable from the study, e.g. {unreached[:3]}")

    # ---- gaps: the register's rows, by chain, as the LCA map matches them
    gaps = parse_data_gaps()
    for c, nid in chain_nodes.items():
        words = [w for w in re.findall(r"[a-z]{4,}", c.lower()) if w not in ("load", "unserved")]
        hits = [g["id"] for g in gaps if any(w in g["name"].lower() for w in words)]
        if hits:
            gr.nodes[nid]["gaps"] = hits

    sources = {}
    for key, src in SR.SOURCES.items():
        users = sorted(set(cited.get(key, [])))
        sources[key] = {**dataclasses.asdict(src), "used_by": users,
                        "grades": {g: sum(1 for u in users if steps[u].get("grade") == g)
                                   for g in ("transcribed", "derived", "assumed", "proxy")}}
    served = solved["served_MWh"]
    out = {
        "nodes": gr.nodes, "edges": gr.edges, "root": "study", "sources": sources,
        "gaps": {g["id"]: g for g in gaps},
        "method": {"assumptions": parse_md_sections(ROOT / "optimisation" / "ASSUMPTIONS.md"),
                   "price_basis": "Real 2025 £ throughout unless a box says otherwise; currency conversions at the "
                                  "FES 2025 Data Workbook's 2025 cross-rates."},
        "problems": problems,
        "meta": {"generated": time.strftime("%Y-%m-%d %H:%M"), "seconds": round(time.time() - t0),
                 "nodes": len(gr.nodes), "edges": len(gr.edges),
                 "steps": sum(1 for n in gr.nodes.values() if n["kind"] == "step"),
                 "sources_cited": len(cited), "sources_registered": len(SR.SOURCES),
                 "run": {"site": SITE, "start": START, "end": END, "size_mw_it": SIZE_MW_IT, **MAIN,
                         "objective": "least cost", "connection_mode": meta.get("connection_mode")},
                 "variants": [v for v, _ in VARIANTS], "cases": list(CASES),
                 "solve": {"cost_GBP_per_year": tot["cost_GBP_per_year"], "served_MWh_per_year": served,
                           "GBP_per_MWh_served": tot["cost_GBP_per_year"] / served if served else None,
                           "connection": solved["connection"], "build": solved["build"],
                           "seconds": solved["seconds"], "step_hours": SOLVE_HOURS},
                 "fingerprint": {"trace_code": trace_code_digest(),
                                 "source_register": _digest({k: dataclasses.asdict(s) for k, s in SR.SOURCES.items()}),
                                 "git_head": git_head()}},
    }
    return out


def write_html(blob: str) -> Path:
    """The page: the template with the map inlined (``</`` escaped so no string
    in the data can close the script tag)."""
    page = HTML_TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", blob.replace("</", "<\\/"))
    HTML_OUT.write_text(page, encoding="utf-8")
    return HTML_OUT


if __name__ == "__main__":
    if "--html-only" in sys.argv:
        out = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        out = build()
        m = out["meta"]
        print(f"built the cost map: {m['nodes']:,} boxes, {m['edges']:,} links, {m['steps']} steps, "
              f"{m['sources_cited']} of {m['sources_registered']} sources cited, {m['seconds']} s")
        if out["problems"]:
            print(f"\n{len(out['problems'])} PROBLEMS — the map disagrees with the model:")
            for p in out["problems"]:
                print("  -", p)
    blob = json.dumps(out, default=lambda o: float(o) if hasattr(o, "__float__") else str(o),
                      separators=(",", ":"))
    OUT.write_text(blob, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1e6:.2f} MB")
    page = write_html(blob)
    print(f"wrote {page.relative_to(ROOT)}: {page.stat().st_size / 1e6:.2f} MB")
    sys.exit(1 if out.get("problems") else 0)
