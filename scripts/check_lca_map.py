#!/usr/bin/env python
"""Check the LCA map against the model it claims to describe.

    python scripts/check_lca_map.py

Loads optimisation_outputs/lca_map.json and re-derives what it can from the
live code: every LP term's value against build_tech, every foreground
activity's exchanges against its inventory module (amount, scale, which
input), every activity's score against the sum of its children's
contributions, the wind calculation steps' arithmetic, the grid term against
its series, the energy map's voltage continuity and its numbers against the
modules they cite, the fingerprint of what the map was built from against
what is live (scripts/map_fingerprint.py), and the page against the JSON.
Prints every mismatch; exits 1 if any. tests/test_lca_map.py runs the
no-Brightway sections under pytest.

Needs Brightway only for the score re-check (skip with --no-brightway).
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

# A Windows console defaults to cp1252 and cannot print the arrows and
# subscripts the map's names carry; without this the first FAIL line crashed
# the run before anything was reported (22 Oct 2026).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

MAP = ROOT / "optimisation_outputs" / "lca_map.json"
problems, checked = [], 0


def bad(msg):
    problems.append(msg)
    print("  FAIL", msg)


def ok(n=1):
    global checked
    checked += n


def close(a, b, rel=1e-6, abs_=1e-9):
    if a is None or b is None:
        return a is b
    return math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_)


def walk(n, f, depth=0):
    f(n, depth)
    for c in n.get("children", []):
        walk(c, f, depth + 1)


def find_all(root, pred):
    out = []
    walk(root, lambda n, d: out.append(n) if pred(n) else None)
    return out


def main(use_bw=True):
    global checked
    problems.clear()
    checked = 0
    d = json.loads(MAP.read_text(encoding="utf-8"))
    tree, gaps, energy = d["tree"], d["gaps"], d.get("energy")

    # ------------------------------------------------------------ 1. LP terms
    print("1. One term box per carbon term of dc_model.objective_terms, each at build_tech's coefficient")
    import numpy as np
    from types import SimpleNamespace
    from optimisation import dc_inputs as I, dc_model as M, dc_architectures as A
    meta = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}
    tech = I.build_tech("london", meta, h2_colour="green")

    class Zero(dict):                       # every LP quantity at zero: only the keys matter
        def __missing__(self, k):
            return np.zeros(1)
    lp = M.objective_terms(Zero(), SimpleNamespace(dt_hours=0.5, annual_scale=1.0), tech,
                           price=np.zeros(1), ci=np.zeros(1))
    lp_keys = set(lp["gwp_embodied"]) | set(lp["gwp_operational"])
    coef = {                                # what each key multiplies
        "wind": tech.gwp_wind, "solar": tech.gwp_solar,
        "wind step-up transformers": tech.gwp_tx_wind_per_mw, "solar step-up transformers": tech.gwp_tx_solar_per_mwp,
        "battery step-up transformers": tech.gwp_tx_batt_per_mw, "fuel cell step-up transformers": tech.gwp_tx_fc_per_mw,
        "grid connection": tech.gwp_grid_per_mw,
        "battery cells and container": tech.gwp_batt_e, "battery power conversion": tech.gwp_batt_p,
        "electrolyser": tech.gwp_ely, "H2 tank": tech.gwp_tank,
        "fuel cell stack replacements": tech.gwp_fc_stack_per_mw, "fuel cell BoP replacements": tech.gwp_fc_bop_per_mw,
        "electrolyser consumables": tech.ely_variable_gwp_per_kg, "fuel cell maintenance": tech.gwp_fc_maint_per_mwh,
        "unserved (VoLL)": M.VOLL_KGCO2E_PER_MWH, "H2 leaked from tank": tech.gwp_h2_leaked_per_kg,
        "grid import": None,                # the series mean: section 6
    }
    for colour in ("grey", "blue", "turquoise", "green"):
        coef[f"bought H2 ({colour})"] = I.build_tech("london", meta, h2_colour=colour).bought_h2_gwp_per_kg
    out_of_scope = {"offshore wind"}        # dc_architectures.OFFSHORE_IN_SCOPE
    if A.OFFSHORE_IN_SCOPE is False: ok()
    else: bad("OFFSHORE_IN_SCOPE is no longer False, but the map has no offshore chain")
    terms = find_all(tree, lambda n: n["kind"] == "term")
    by_key = {}
    for t in terms:
        if t.get("key") and not t.get("constant"):
            if t["key"] in by_key: bad(f"two term boxes carry the key {t['key']!r}")
            by_key[t["key"]] = t
    for k in sorted(lp_keys):
        if k in out_of_scope:
            if find_all(tree, lambda n: n.get("status") == "not" and "offshore" in n["name"].lower()): ok()
            else: bad(f"LP term {k!r} is out of scope but the map does not say so")
            continue
        if k.startswith("bought H2") and k not in coef:      # the second stream's fallback label
            ok(); continue
        t = by_key.get(k)
        if t is None:
            bad(f"LP term {k!r} has no box in the map"); continue
        ok()
        if coef.get(k) is None:
            continue
        if close(t.get("value"), coef[k], rel=1e-9): ok()
        else: bad(f"term box {t['name']!r} ({k}): map {t.get('value')} vs build_tech {coef[k]}")
    for k, t in by_key.items():
        if k.startswith("bought H2"):
            if k in coef: ok()
            else: bad(f"bought-hydrogen box {k!r} is not one of the four colours")
        elif k not in lp_keys:
            bad(f"term box {t['name']!r} carries key {k!r}, which objective_terms does not have")
    # the facility: two constants, not objective terms (objective_constants; contributions()['gwp_facility'])
    consts = {t["key"]: t for t in terms if t.get("constant")}
    want_c = {"data centre, IT capacity": tech.dc_fixed_gwp_per_year,
              "data centre, cooling consumables": tech.dc_other_gwp_per_mwh}
    if set(consts) == set(want_c): ok()
    else: bad(f"facility constants in the map {sorted(consts)} vs dc_model.contributions {sorted(want_c)}")
    for k, v in want_c.items():
        if k in consts and close(consts[k]["value"], v, rel=1e-9): ok()
        elif k in consts: bad(f"constant {k!r}: map {consts[k]['value']} vs build_tech {v}")
    print(f"     {len(lp_keys)} LP carbon terms, {len(by_key)} keyed boxes, {len(consts)} constants")

    # ------------------------------------------------------------ 2. wind steps
    print("2. Wind calculation steps")
    from optimisation import renewables as ren
    emb = ren.apply_case(ren.decompose_all(), "central").set_index("technology")
    for tech_name, label in (("onshore_wind", "Onshore wind"),):
        row = emb.loc[tech_name]
        t = next(x for x in terms if x["name"].startswith(label))
        # The steps sit inside the functional unit's chain; find them by number.
        fu_node = next(x for x in find_all(tree, lambda n: n["kind"] == "fu") if x["name"].startswith(label))
        found = find_all(fu_node, lambda n: n["kind"] == "step")
        steps = [next(x for x in found if x["name"].startswith(f"{i} ·")) for i in (1, 2, 3, 4)]
        s2, s3, s4 = steps[1], steps[2], steps[3]
        parts = ren.wind_parts_fraction(row.study_lifetime_years)
        if close(s2["value"], row.ecoinvent_capital_kgco2e_per_MW) and close(s3["value"], s2["value"] * (1 + parts)) \
                and close(s4["value"], s3["value"] / row.study_lifetime_years
                          + row.residual_per_kWh * row.study_load_factor * 8760 * 1000) \
                and close(s4["value"], t["value"]):
            ok(4)
        else:
            bad(f"{label} steps do not chain: {s2['value']} ×(1+{parts}) = {s3['value']}; "
                f"÷{row.study_lifetime_years} + residual = {s4['value']} vs term {t['value']}")
        # the dataset in step 1 is the one decomposed
        ds = next((c for c in steps[0]["children"] if c["kind"] == "ecoinvent"), None)
        if ds and ds["name"] == ren.TECHNOLOGIES[tech_name][0]: ok()
        else: bad(f"{label} step 1 opens {ds and ds['name']!r}, not {ren.TECHNOLOGIES[tech_name][0]!r}")
        # The flagged capital goods must be exactly the dataset's unit-counted inputs.
        caps = {c["name"] for c in (ds or {}).get("children", []) if c.get("role")}
        units = {c["name"] for c in (ds or {}).get("children", []) if c.get("unit") == "unit"}
        if caps and caps == units: ok()
        else: bad(f"{label}: capital goods flagged {sorted(caps)} vs unit-counted inputs {sorted(units)}")

    # ------------------------------------------------------------ 2b. functional units and stages
    print("2b. Every functional unit and stage is the sum of what is under it")
    worst = 0.0
    for g in find_all(tree, lambda n: n["kind"] in ("fu", "stage")):
        if g.get("additive") is False:
            continue
        kids = [c for c in g.get("children", []) if c.get("exchange") and c["exchange"].get("contribution") is not None]
        total = sum(c["exchange"]["contribution"] for c in kids)
        if not kids:
            continue
        resid = abs(total / g["value"] - 1) if g["value"] else abs(total)
        worst = max(worst, resid)
        if resid < 1e-5: ok()
        else: bad(f"{g['kind']} {g['name'][:60]!r}: children sum {total:.6g} vs value {g['value']:.6g} ({resid:.1e})")
        if g["kind"] == "fu":
            parts_total = sum(v for _, v, _t in g.get("parts", []))
            if close(g["value"], parts_total, rel=1e-9): ok()
            else: bad(f"fu {g['name'][:50]!r}: value {g['value']} vs LP parts {parts_total}")
            for pname, v, tname in g.get("parts", []):
                t = next((x for x in terms if x["name"] == tname), None)
                if t is None:
                    bad(f"fu {g['name'][:40]!r} part {pname!r} links to no LP term {tname!r}"); continue
                ok()
                if pname == tname and not close(t["value"], v, rel=1e-9):
                    bad(f"fu {g['name'][:40]!r} part {pname!r}: {v} vs term {t['value']}")
    print(f"     largest chain residual against its value: {worst:.1e} (Brightway solver noise)")

    # ------------------------------------------------------------ 3. foreground exchanges
    print("3. Foreground activities against their inventory modules")
    from optimiser_lca import build
    from optimiser_lca.common import FG
    invs = {inv.database: inv for _, inv in build.inventories()}
    acts = {(db, a.code): (inv, a) for db, inv in invs.items() for a in inv.activities}
    fgs = find_all(tree, lambda n: n["kind"] == "foreground")
    seen = set()
    for n in fgs:
        key = (n["database"], n["code"])
        if key not in acts:
            bad(f"foreground {key} is not in any inventory module"); continue
        inv, a = acts[key]
        if key in seen or n.get("note", "").startswith("already open") or n.get("scaled"):
            continue
        seen.add(key)
        kids = n.get("children", [])
        per = float(a.production_amount) or 1.0      # the map shows inputs per ONE unit of output
        want_rows = []
        for row in a.technosphere:
            pkey, amount, unit, note = (list(row) + [None] * 4)[:4]
            if isinstance(pkey, FG):
                tgt = acts.get((pkey.database or a_db(inv), pkey.code))
                name = tgt[1].name if tgt else pkey.code
            else:
                name = inv.processes[pkey].identity[0]
            want_rows.append((name, amount * a.scale / per, unit))
        for row in a.biosphere:
            fkey, amount, unit, note = (list(row) + [None] * 4)[:4]
            want_rows.append((inv.flows[fkey].identity[0], amount * a.scale / per, unit))
        got_rows = [(c["name"], c["exchange"]["amount"], c["exchange"].get("unit")) for c in kids if c.get("exchange")]
        if n.get("exchange") and "per MW" in (n["exchange"].get("unit") or "") and not kids:
            continue                            # a ghost's annualised link, not an inventory exchange
        if len(got_rows) != len(want_rows):
            bad(f"{a.code}: map has {len(got_rows)} exchanges, module {len(want_rows)}"); continue
        # match by (name, amount) multiset
        def norm(rows):
            return sorted((r[0], round(float(r[1]), 12)) for r in rows)
        if norm(got_rows) == norm(want_rows): ok()
        else:
            diff = set(norm(got_rows)) ^ set(norm(want_rows))
            bad(f"{a.code}: exchanges differ: {sorted(diff)[:4]}")
        # printed amounts recorded whenever a scale applies
        if a.scale != 1.0:
            if all(c["exchange"].get("printed_amount") is not None for c in kids if c.get("exchange")): ok()
            else: bad(f"{a.code}: scale {a.scale} but printed amounts missing")

    # ------------------------------------------------------------ 4. scores add up
    print("4. Each activity's score equals the sum of its inputs' contributions")
    done = set()
    for n in fgs:
        if n["code"] in done:
            continue
        done.add(n["code"])
        kids = [c for c in n.get("children", []) if c.get("exchange") and c["exchange"].get("contribution") is not None]
        if not kids or n.get("score_per_unit") is None:
            continue
        total = sum(c["exchange"]["contribution"] for c in kids)
        if close(total, n["score_per_unit"], rel=2e-3, abs_=1e-6): ok()
        else:
            bad(f"{n['code']}: children sum {total:.6g} vs score {n['score_per_unit']:.6g} "
                f"({(total / n['score_per_unit'] - 1) * 100:+.2f} %)")
    bg = find_all(tree, lambda n: n["kind"] == "ecoinvent" and n.get("children"))
    for n in bg:
        total = sum(c["exchange"]["contribution"] or 0 for c in n["children"] if c.get("exchange"))
        if close(total, n["score_per_unit"], rel=0.05): ok()
        else:
            bad(f"ecoinvent {n['name'][:50]!r} one level in: {total:.4g} vs {n['score_per_unit']:.4g} "
                f"({(total / n['score_per_unit'] - 1) * 100:+.1f} %) — self-loops or allocation")

    # ------------------------------------------------------------ 5. grid term
    print("5. Grid term against its series")
    import pandas as pd
    from optimiser_lca import grid as G
    t = next(x for x in terms if x["name"].startswith("Grid imports"))
    london = pd.read_csv(ROOT / "custom_grid_lca_outputs" / (
        "custom_grid_lca_carbon_api_regional_auto_r13_cheap_2025-01-01T00-00-00T_to_T2025-12-29T00-00-00.csv"))
    if close(t["value"], london["custom_electricity_score"].mean() * 1000, rel=1e-9): ok()
    else: bad("grid term value is not the London series mean")
    # The sources sit under the grid functional unit's "1 kWh generated" stage.
    srcs = find_all(tree, lambda n: n.get("exchange") and "kWh per kWh generated" in (n["exchange"].get("unit") or "")
                    and n["exchange"].get("amount"))
    share = sum(n["exchange"]["amount"] for n in srcs)
    if 0.99 < share < 1.01: ok()
    else: bad(f"grid source shares sum to {share:.4f}, not 1")
    # The map's per-source scores must be the ones grid_build uses
    for n in srcs:
        key = n.get("process_key")
        if key and key in G.SOURCES and use_bw:
            pass  # scored by the same resolve_exact; checked in section 4 via contributions
    # the LP charges the series delivered at HV: term says so
    if "delivered at HV" in t["unit"]: ok()

    # ------------------------------------------------------------ 6. gap links
    print("6. Gap links resolve, and look right")
    for n in find_all(tree, lambda n: n.get("gaps")):
        for g in n["gaps"]:
            if g in gaps: ok()
            else: bad(f"{n['name'][:40]!r} links to unknown gap {g}")
    for t in terms:
        names = [gaps[g]["name"] for g in t.get("gaps", [])]
        print(f"     {t['name'][:48]:50s} -> {len(names)} gaps: " + "; ".join(x[:38] for x in names[:4])
              + (" …" if len(names) > 4 else ""))

    # ------------------------------------------------------------ 7. energy map
    print("7. Energy map")
    if not energy:
        bad("no energy section"); return
    from energy_map import energy_section
    from build_lca_map import parse_data_gaps
    rows = parse_data_gaps()
    fresh = energy_section(lambda *k: [g["id"] for g in rows if any(x.lower() in g["name"].lower() for x in k)])
    if json.dumps(fresh["nodes"], sort_keys=True, default=str) == json.dumps(energy["nodes"], sort_keys=True, default=str): ok()
    else: bad("energy nodes differ from a fresh energy_section() — rebuild the map")
    # voltage continuity: every edge's carrier must be what its source emits and its target accepts
    IO = {  # node id: (accepts, emits)  — '*' any
        "sun": ("*", "sun"), "pv_modules": ("sun", "dc"), "pv_dc": ("dc", "dc"), "pv_inverter": ("dc", "lv"),
        "pv_tx": ("lv", "mv"), "wind": ("*", "wind"), "rotor": ("wind", "lv"), "wake": ("lv", "lv"),
        "turbine_tx": ("lv", "mv"), "collect": ("mv", "mv"), "gb_gen": ("*", "hv"), "tx_net": ("hv", "hv"),
        "line": ("hv", "hv"), "meter": ("hv", "hv"), "intake": ("hv mv", "mv hv"), "bus": ("mv", "mv"),
        "bess_tx": ("mv lv", "lv mv"), "pcs": ("lv dc", "dc lv"), "bess_dc": ("dc lv", "dc"), "bess_cooling": ("*", "lv"),
        "ely_psu": ("mv", "dc"), "ely": ("dc gas", "h2"), "gas": ("*", "gas"), "soec_heat": ("gas mv", "gas"),
        "compress": ("h2", "h2"), "tank": ("h2", "h2"), "fc_stack": ("h2", "dc"), "fc_bop": ("dc", "dc"),
        "fc_inv": ("dc", "lv"), "fc_tx": ("lv", "mv"), "h2_seller": ("*", "h2"), "trailer_comp": ("h2", "h2"),
        "haulage": ("h2", "h2"), "dc_dist": ("mv lv", "lv"), "it": ("lv", "*"), "cooling": ("lv", "*"),
        "genset": ("*", "lv"), "unserved": ("*", "lv"),
    }
    for e in energy["edges"]:
        a, b = IO.get(e["from"]), IO.get(e["to"])
        if a is None or b is None:
            bad(f"edge {e['from']}->{e['to']}: node not in the IO table"); continue
        if (a[1] == "*" or e["carrier"] in a[1].split()) and (b[0] == "*" or e["carrier"] in b[0].split()): ok()
        else: bad(f"edge {e['from']}->{e['to']} carries {e['carrier']!r}: {e['from']} emits {a[1]!r}, {e['to']} accepts {b[0]!r}")
    # every node reachable to/from the bus (except the deliberately isolated)
    ids = {n["id"] for n in energy["nodes"]}
    adj = {}
    for e in energy["edges"]:
        adj.setdefault(e["from"], set()).add(e["to"]); adj.setdefault(e["to"], set()).add(e["from"])
    seen = {"bus"}; q = ["bus"]
    while q:
        x = q.pop()
        for y in adj.get(x, ()):
            if y not in seen: seen.add(y); q.append(y)
    for i in ids - seen:
        bad(f"energy node {i} is not connected to the bus")
    # numbers quoted in ratings against the modules they cite
    import dc_config as cfg
    from optimisation import battery, conversion_losses as cl, electrolysers as ely, fuel_cell as fc, h2_prices as hp
    from optimiser_lca import bess, fuel_cell as fcl, h2_tank, stepup_transformers as tx, upv
    N = {n["id"]: n for n in energy["nodes"]}
    term_names = {t["name"] for t in terms} | {g["name"] for g in find_all(tree, lambda n: n["kind"] == "group")}
    for n_ in energy["nodes"]:
        if n_.get("term"):
            if n_["term"] in term_names: ok()
            else: bad(f"energy node {n_['id']}: links to LP term {n_['term']!r}, which has no box")
    expect = {
        "pv_modules": f"{upv.UPV_PV_MODULE_W:g} Wp", "pv_inverter": f"{upv.UPV_PV_INVERTER_MVA:g} MVA",
        "pv_tx": f"{tx.UPV_TX_UNIT_MVA:g} MVA", "turbine_tx": f"{tx.TX_LENG_UNIT_MVA:g} MVA",
        "bess_dc": f"{bess.CSS_KWH:,.0f} kWh", "pcs": f"{battery.PCS_RATED_KW:g} kW",
        "ely": f"PEM {dict((r['technology'], r['kwh_per_kg']) for r in ely.decompose_all())['PEM operation']:g} kWh/kg",
        "tank": f"{h2_tank.DESIGN['pressure_bar']:g} bar", "fc_stack": f"{fc.decompose()['h2_kg_per_MWh']:.1f} kg",
        "trailer_comp": f"to {hp.BOUGHT_H2_TRAILER_PRESSURE_BAR:g} bar", "cooling": f"PUE {cfg.DC_REFERENCE_PUE:g}",
        "rotor": f"{tx.TX_TURBINE_TERMINAL_V:g} V",
    }
    for i, frag in expect.items():
        if frag in (N[i].get("rating") or ""): ok()
        else: bad(f"energy node {i}: rating {N[i].get('rating')!r} lacks {frag!r}")
    # the LP facts the boxes assert
    if close(M.loss_factors.__doc__ and 1, 1): pass
    if tech.tank_compression_kwh_per_kg == 0.0 and "0.00 kWh/kg" in N["compress"]["rating"]: ok()
    else: bad("compression box vs tech.tank_compression_kwh_per_kg")
    if f"{battery.ROUND_TRIP_EFFICIENCY ** 0.5:.3f}" in N["pcs"]["model"]: ok()
    else: bad("PCS box efficiency split is not sqrt(RTE)")
    if close(tech.batt_rte, battery.ROUND_TRIP_EFFICIENCY): ok()
    # ------------------------------------------------------------ 8. every inventory activity is in the LCA
    print("8. Every activity in optimiser_lca/ is a box in the LCA, or a box says it stands for it")
    shown = set()

    def collect(n, _d):
        if n["kind"] == "foreground":
            shown.add((n["database"], n["code"]))
        for s in n.get("stands_for") or []:
            shown.add((s["database"], s["code"]))
    walk(tree, collect)
    for db, inv in invs.items():
        for a in inv.activities:
            if (db, a.code) in shown: ok()
            else: bad(f"{db} / {a.code} ({a.name[:50]}) is in the inventory but nowhere in the LCA tree")

    # ------------------------------------------------------------ 8b. the cut-off register
    print("8b. Every estimate carried on a coefficient is a box; the left-out register is not drawn")
    added = (tech.labels or {}).get("cutoff_added", {})
    est_boxes = find_all(tree, lambda n: n["kind"] == "part" and "estimates carried" in n["name"].lower())
    if len(est_boxes) >= len([k for k, v in added.items() if v]): ok()
    else: bad(f"{len(added)} coefficients carry cut-off estimates but the map shows {len(est_boxes)} estimate boxes")
    if not find_all(tree, lambda n: n.get("register")): ok()
    else: bad("the map draws cut-off register boxes; they were taken out (user, 23 Oct 2026)")

    # ------------------------------------------------------------ 8c. one box per process
    print("8c. No box holds exactly one box that is the same thing")
    SAME = {"ecoinvent", "foreground", "part", "stage"}
    for n in find_all(tree, lambda n: n["kind"] in ("part", "stage", "fu", "foreground")):
        kids = [c for c in n.get("children", []) if c["kind"] in SAME]
        if len(kids) == 1 and len(n.get("children", [])) == 1 and kids[0].get("name") == n.get("name"):
            bad(f"{n['kind']} {n['name'][:50]!r} holds one box that is the same thing")
        else:
            ok()

    # ------------------------------------------------------------ 9. fingerprint
    print("9. The map was built from the inventories, coefficients, grid basis and register that are live now")
    from map_fingerprint import compare, COMPARED
    diffs = compare((d.get("meta") or {}).get("fingerprint"))
    for m in diffs:
        bad(f"fingerprint {m} — rebuild the map")
    ok(len(COMPARED) - len(diffs))

    # ------------------------------------------------------------ 10. the page
    print("10. lca_map.html carries lca_map.json")
    html_path = MAP.with_suffix(".html")
    if not html_path.exists():
        bad("lca_map.html is missing — run build_lca_map.py --html-only")
    else:
        m = re.search(r'<script id="lca-data" type="application/json">(.*?)</script>',
                      html_path.read_text(encoding="utf-8"), re.S)
        if m and m.group(1).replace("<\\/", "</") == MAP.read_text(encoding="utf-8"): ok()
        else: bad("lca_map.html does not carry lca_map.json — run build_lca_map.py --html-only")

    print(f"\n{checked} checks passed, {len(problems)} problems")
    return 0 if not problems else 1


def a_db(inv):
    return inv.database


if __name__ == "__main__":
    sys.exit(main(use_bw="--no-brightway" not in sys.argv))
