#!/usr/bin/env python
"""Build the LCA map: every carbon term, inventory, exchange, source and gap.

    python scripts/build_lca_map.py              # map JSON + optimisation_outputs/lca_map.html
    python scripts/build_lca_map.py --html-only  # re-wrap the page around the last map

The tree runs top-down the way the carbon objective is assembled:

    the study (method, boundary)
      -> the LP's carbon objective, term by term (the number the solver sees)
        -> the coefficient module that turns an inventory into that number
          -> the foreground inventory (optimiser_lca/), activity by activity
            -> every exchange: foreground links expand, ecoinvent ones are
               leaves scored on ecoinvent 3.9.1 apos (key generation and grid
               datasets are opened one level)
      -> the data gap register, every row, linked back to the terms it touches

Every node carries its provenance: the module it lives in, the source it was
transcribed or derived from, a grade, and the score it contributes. Scores are
IPCC 2021 GWP100 (with long-term emissions), the study's method. Needs the
Brightway project; takes a few minutes, cached per input activity.
"""
from __future__ import annotations

import ast
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "optimisation_outputs" / "lca_map.json"
EI_DB = "ecoinvent-3.9.1-apos"

_ids = 0


def nid(prefix="n"):
    global _ids
    _ids += 1
    return f"{prefix}{_ids}"


def node(name, kind, **kw):
    d = {"id": nid(), "name": name, "kind": kind}
    d.update({k: v for k, v in kw.items() if v not in (None, "", [], {})})
    return d


# The LP's carbon terms, one box each under "How the LP organises it", named in
# lp_terms.py so the energy tab links to the same names. Each box carries the
# dc_model.objective_terms key it stands for; check_lca_map.py asserts the two
# sets match and every coefficient equals build_tech's.
from lp_terms import (T_WIND, T_SOLAR, T_TX_WIND, T_TX_SOLAR, T_GRID_CONN, T_BATT_E, T_BATT_P, T_ELY,  # noqa: E402
                      T_TANK, T_FC_STACK, T_FC_BOP, T_IMPORT, T_ELY_CONS, T_FC_MAINT, T_LEAK, T_VOLL,
                      T_DC_IT, T_DC_ENERGY, T_BOUGHT, T_TX_BATT, T_TX_FC)


# =============================================================================
# Grades from free text
# =============================================================================
def grade_from(*texts, default="transcribed"):
    t = " ".join(x for x in texts if x).lower()
    if "assumed" in t:
        return "assumed"
    if "proxy" in t or "stands in" in t or "stand-in" in t:
        return "proxy"
    if "derived" in t or "computed" in t or "interpolat" in t:
        return "derived"
    return default


def first_para(doc: str | None) -> str:
    if not doc:
        return ""
    paras = [p.strip() for p in doc.strip().split("\n\n") if p.strip()]
    out = []
    for p in paras:
        if set(p.replace("\n", "")) <= set("=-"):
            continue
        out.append(p)
        if len(" ".join(out)) > 300:
            break
    return "\n\n".join(out[:2])


def module_doc(path: Path) -> str:
    try:
        return ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    except Exception:
        return ""


# =============================================================================
# Registers: DATA_GAPS.md, SOURCES.md, TODO.md, tests
# =============================================================================
def parse_data_gaps():
    text = (ROOT / "optimisation" / "DATA_GAPS.md").read_text(encoding="utf-8")
    status_of = {
        "Closed": "closed", "Closed since the register was opened": "closed",
        "Open — public source identified, not yet pulled": "open-source-known",
        "Open — no public source": "open-no-source",
        "Checked and confirmed absent": "confirmed-absent",
        "Not applicable": "not-applicable",
    }
    rows, section = [], None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("| ") or line.startswith("|---") or section is None:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if cells[0] in ("Input",) or not cells[0]:
            continue
        name = re.sub(r"\*\*", "", cells[0]).strip()
        rows.append({"id": f"gap{len(rows) + 1}", "name": name, "section": section,
                     "status": status_of.get(section, "other"),
                     "cells": cells[1:]})
    return rows


def parse_md_sections(path: Path, levels=("## ", "### ")):
    text = path.read_text(encoding="utf-8")
    out, title, buf = {}, None, []
    for line in text.splitlines():
        hit = next((lv for lv in levels if line.startswith(lv)), None)
        if hit:
            if title:
                out[title] = "\n".join(buf).strip()
            title, buf = line[len(hit):].strip(), [line]
        elif title:
            buf.append(line)
    if title:
        out[title] = "\n".join(buf).strip()
    return out


def parse_todo():
    text = (ROOT / "TODO.md").read_text(encoding="utf-8")
    items, section, cur = [], None, None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        if line.startswith("- [ ]"):
            cur = {"section": section, "text": line[5:].strip()}
            items.append(cur)
        elif cur and line.startswith("      "):
            cur["text"] += " " + line.strip()
        else:
            cur = None if not line.startswith("- [ ]") else cur
    for it in items:
        m = re.match(r"\*\*(.+?)\*\*\s*(.*)", it["text"])
        it["name"], it["body"] = (m.group(1), m.group(2)) if m else (it["text"][:80], it["text"])
    return items


def parse_tests():
    out = []
    for p in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for n in tree.body:
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
                doc = (ast.get_docstring(n) or "").split("\n")[0]
                out.append({"file": f"tests/{p.name}", "name": n.name, "doc": doc})
    return out


# =============================================================================
# Brightway scoring, cached
# =============================================================================
class Scorer:
    def __init__(self):
        import bw2data as bd
        import lca_helpers as H
        from optimisation import baseline_grid as bg
        H.setup_brightway()
        self.bd, self.H = bd, H
        self.method = bg.gwp_method()
        self.cache = {}
        self.cfs = {}
        for key, cf in bd.Method(self.method).load():
            k = key if not isinstance(key, int) else bd.get_node(id=key).key
            self.cfs[tuple(k)] = cf
        self.n = 0

    def score(self, act) -> float:
        k = tuple(act.key)
        if k not in self.cache:
            try:
                self.cache[k] = float(self.H.run_lca_score(act, self.method))
            except Exception as e:                           # noqa: BLE001
                print("  could not score", act, e)
                self.cache[k] = None
            self.n += 1
            if self.n % 50 == 0:
                print(f"  scored {self.n} activities")
        return self.cache[k]

    def cf(self, flow) -> float:
        return float(self.cfs.get(tuple(flow.key), 0.0))


# =============================================================================
# Foreground inventories, expanded
# =============================================================================
class Foreground:
    def __init__(self, scorer: Scorer):
        from optimiser_lca import build, registry as R
        from optimiser_lca.common import resolve
        self.S, self.R = scorer, R
        self.invs = {}          # db -> (module name, inv, resolved)
        self.acts = {}          # (db, code) -> (module name, inv, Activity)
        for name, inv in build.inventories():
            print(f"resolving {name} ...")
            resolved = resolve(inv, strict_search=False)
            self.invs[inv.database] = (name, inv, resolved)
            for a in inv.activities:
                self.acts[(inv.database, a.code)] = (name, inv, a)
        self.docs = {n: module_doc(ROOT / "optimiser_lca" / f"{n}.py")
                     for n, _ in build.MODULES}

    def bw(self, db, code):
        return self.S.bd.get_activity((db, code))

    def activity_node(self, db, code, *, path=(), exchange=None):
        mod, inv, a = self.acts[(db, code)]
        act = self.bw(db, code)
        total = self.S.score(act)
        # Inventories per a batch (Smith's silica sand per 92,500 t, iron phosphate
        # per 0.91 kg) are shown per ONE unit of output, like everything else; the
        # batch figure is kept as the printed amount.
        per = float(a.production_amount) or 1.0
        n = node(a.name, "foreground",
                 module=f"optimiser_lca/{mod}.py", database=db, code=code,
                 unit=a.unit, location=a.location, product=a.reference_product,
                 comment=a.comment, score_per_unit=total,
                 production_amount=(per if per != 1.0 else None),
                 source=first_para(self.docs.get(mod)),
                 grade=grade_from(a.comment, a.scale_note, default="transcribed"),
                 scale=(a.scale if a.scale != 1.0 else None),
                 scale_note=a.scale_note or None,
                 exchange=exchange)
        if (db, code) in path:
            n["note"] = "already open above (loop guard)"
            return n
        path = path + ((db, code),)
        kids = []
        for row in a.technosphere:
            pkey, amount, unit, note = (list(row) + [None] * 4)[:4]
            amt = amount * a.scale / per
            printed = amount if (a.scale != 1.0 or per != 1.0) else None
            from optimiser_lca.common import FG
            if isinstance(pkey, FG):
                tdb = pkey.database or db
                tact = self.bw(tdb, pkey.code)
                ex = {"amount": amt, "unit": unit, "note": note,
                      "contribution": _mul(self.S.score(tact), amt),
                      "printed_amount": printed}
                child = self.activity_node(tdb, pkey.code, path=path, exchange=ex)
                if note and "replacement" in note.lower():
                    child["role"] = "replacement"
                kids.append(child)
                continue
            proc = inv.processes[pkey]
            res = self.invs[db][2][pkey]
            ex = {"amount": amt, "unit": unit, "note": note,
                  "contribution": _mul(self.S.score(res), amt),
                  "printed_amount": printed}
            if res["database"] != EI_DB and (res["database"], res["code"]) in self.acts:
                kids.append(self.activity_node(res["database"], res["code"],
                                               path=path, exchange=ex))
            else:
                kids.append(self.ecoinvent_node(res, ex, key=pkey, proc=proc))
        for row in a.biosphere:
            fkey, amount, unit, note = (list(row) + [None] * 4)[:4]
            fl = self.invs[db][2][fkey]
            amt = amount * a.scale / per
            flow_def = inv.flows.get(fkey)
            kids.append(node(
                fl["name"], "biosphere", compartment=" / ".join(fl.get("categories") or ()),
                exchange={"amount": amt, "unit": unit, "note": note,
                          "contribution": self.S.cf(fl) * amt,
                          "printed_amount": amount if (a.scale != 1.0 or per != 1.0) else None},
                cf=self.S.cf(fl), why=getattr(flow_def, "why", None),
                grade=grade_from(note, getattr(flow_def, "why", ""), default="transcribed"),
                source="ecoinvent 3.9.1 biosphere; IPCC 2021 GWP100 characterisation"))
        kids.sort(key=lambda k: -abs((k.get("exchange") or {}).get("contribution") or 0))
        n["children"] = kids
        return n

    def ecoinvent_node(self, act, ex, key=None, proc=None, open_one_level=False):
        n = node(act["name"], "ecoinvent", location=act.get("location"),
                 product=act.get("reference product"), unit=act.get("unit"),
                 database=act["database"], exchange=ex, score_per_unit=self.S.score(act),
                 process_key=key, why=getattr(proc, "why", None),
                 query=getattr(proc, "query", None),
                 grade=grade_from(ex.get("note") if ex else "", getattr(proc, "why", ""),
                                  default="transcribed"),
                 source="ecoinvent 3.9.1 apos background — resolved by exact identity "
                        "(name, location, reference product)")
        if open_one_level:
            n["children"] = background_children(self.S, act)
        return n


def _mul(a, b):
    return None if a is None or b is None else a * b


def background_children(S, act, top=14):
    """One level into an ecoinvent dataset: its direct exchanges, scored."""
    kids = []
    for e in act.technosphere():
        inp = e.input
        if inp.key == act.key:
            continue
        sc = S.score(inp)
        kids.append(node(inp["name"], "ecoinvent", location=inp.get("location"),
                         product=inp.get("reference product"), unit=inp.get("unit"),
                         database=inp["database"], score_per_unit=sc,
                         exchange={"amount": float(e["amount"]), "unit": inp.get("unit"),
                                   "contribution": _mul(sc, float(e["amount"]))},
                         grade="transcribed", background=True,
                         role=("capital good — counted per unit" if inp.get("unit") == "unit" else None),
                         source="ecoinvent 3.9.1 apos — a direct input of the dataset above"))
    for e in act.biosphere():
        cf = S.cf(e.input)
        if cf:
            kids.append(node(e.input["name"], "biosphere", background=True,
                             compartment=" / ".join(e.input.get("categories") or ()),
                             exchange={"amount": float(e["amount"]), "unit": e.input.get("unit"),
                                       "contribution": cf * float(e["amount"])},
                             cf=cf, grade="transcribed",
                             source="ecoinvent 3.9.1 apos — a direct emission of the dataset above"))
    kids.sort(key=lambda k: -abs(k["exchange"]["contribution"] or 0))
    if len(kids) > top:
        rest = kids[top:]
        kids = kids[:top] + [node(f"{len(rest)} smaller exchanges", "note",
                                  exchange={"contribution": sum((k["exchange"]["contribution"] or 0)
                                                                for k in rest)},
                                  note=", ".join(k["name"] for k in rest[:30]))]
    return kids


# =============================================================================
# The tree
# =============================================================================
def build():
    import dc_config as cfg
    import pandas as pd
    from optimisation import (battery, conversion_losses as cl, dc_inputs as I, dc_model as M,
                              electrolysers as ely, fuel_cell as fc, grid_connection as gc,
                              h2_prices as hp, h2_storage as h2s, profiles, renewables as ren,
                              transformers as tx)
    from optimiser_lca import gb_grid, grid as G, registry as R, stepup_transformers as stx, upv
    from optimiser_lca import fuel_cell as fcl, h2_tank
    from optimisation import h2_storage as h2s

    t0 = time.time()
    S = Scorer()
    F = Foreground(S)
    gaps = parse_data_gaps()
    sources = parse_md_sections(ROOT / "optimisation" / "SOURCES.md")
    assumptions = parse_md_sections(ROOT / "optimisation" / "ASSUMPTIONS.md")
    todo = parse_todo()
    tests = parse_tests()
    odoc = {m: module_doc(ROOT / "optimisation" / f"{m}.py") for m in (
        "renewables", "battery", "electrolysers", "fuel_cell", "h2_storage", "transformers",
        "grid_connection", "h2_prices", "conversion_losses", "dc_model", "baseline_grid",
        "dc_inputs", "profiles", "grid_build", "sensitivity", "audit", "myopic")}

    meta = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}
    tech = I.build_tech("london", meta, h2_colour="green")
    colours = {c: I.build_tech("london", meta, h2_colour=c) for c in ("grey", "blue", "turquoise")}
    colours["green"] = tech

    def gap_ids(*keys):
        ks = [k.lower() for k in keys]
        return [g["id"] for g in gaps if any(k in g["name"].lower() for k in ks)]

    def todo_for(*keys):
        ks = [k.lower() for k in keys]
        return [{"section": t["section"], "name": t["name"], "body": t["body"]}
                for t in todo if any(k in (t["name"] + " " + t["body"]).lower() for k in ks)]

    def tests_for(*keys):
        ks = [k.lower() for k in keys]
        return [f"{t['file']}::{t['name']}" + (f" — {t['doc']}" if t["doc"] else "")
                for t in tests if any(k in t["name"].lower() for k in ks)]

    def src(*titles):
        out = {}
        for t in titles:
            for k, v in sources.items():
                if t.lower() in k.lower():
                    out[k] = v
        return out

    def term(name, symbol, value, unit, *, module, grade, source, children=(), gap_keys=(),
             todo_keys=(), test_keys=(), source_titles=(), note=None, lp=None, key=None, constant=None):
        return node(name, "term", symbol=symbol, value=value, unit=unit, module=module,
                    grade=grade, source=source, note=note, lp=lp, key=key, constant=constant,
                    gaps=gap_ids(*gap_keys), todo=todo_for(*todo_keys),
                    tests=tests_for(*test_keys), sources_md=src(*source_titles),
                    module_doc=odoc.get(Path(module).stem) if module.startswith("optimisation/") else None,
                    children=list(children))

    def fg(code, db, ex=None):
        return F.activity_node(db, code, exchange=ex)

    def jump(target, why):
        """A link to another LP term, for a technology charged in two places."""
        return node(f"See also: {target}", "jump", target=target, note=why)

    GHOST_WHY = ("Illustrative. This is where a traditional LCA (SimaPro, a unit process per "
                 "technology) would place the functional unit, with the technology's own "
                 "electrical infrastructure and consumables inside it. The LP does not have this "
                 "term: it charges each part below separately, because they scale with different "
                 "decision variables (a transformer with capacity built, consumables with output). "
                 "The value is the sum of those real terms at the stated utilisation, so it cannot "
                 "disagree with the model; the real terms stay where they are.")

    def ghost(name, value, unit, parts, children, note=""):
        """The traditional functional unit, greyed, assembled from real LP terms.

        ``parts`` are (label, value in the ghost's own unit, LP term name). The
        values sum to the ghost's value; the term name is a link, and the checker
        tests equality only where label == term name (the same quantity).
        """
        return node(name, "ghost", value=value, unit=unit, grade="derived",
                    parts=[[p, v, t] for p, v, t in parts], note=(note + " " + GHOST_WHY).strip(),
                    children=children)

    WHY_SPLIT = ("The LP charges each technology once per **thing it scales with**. Building "
                 "an electrolyser or a fuel cell is charged per MW (capacity, here). Running it is "
                 "charged per kg made or per MWh delivered (flow, under Operational). They have "
                 "to stay separate terms because the optimiser trades them differently: a "
                 "capacity term pushes it to build less kit, a flow term to run it less. Stack "
                 "and balance-of-plant replacements sit with capacity because they are counted "
                 "in MW replaced, on max(calendar life, running hours).")

    # ---------------------------------------------------------------- method
    method = node("Method, boundary and system model", "group", children=[
        node("LCIA method: IPCC 2021 GWP100, with long-term emissions", "note",
             source="ecoinvent 3.9.1 implementation; the grid and every asset share it since 13 Oct",
             grade="transcribed", note=G.METHOD_LABEL),
        node("Background: ecoinvent 3.9.1, allocation at the point of substitution (apos)", "note",
             grade="transcribed", note="Every foreground in optimiser_lca/ is scored on it; "
             "Smith's PV and Voß's cell are rebuilt on it rather than transcribed off another background."),
        node("Boundary: cradle-to-gate capital + operation; no end-of-life credits", "note",
             grade="assumed", sources_md={k: v for k, v in assumptions.items()
                                         if "boundary" in k.lower() or "cradle" in k.lower()}),
        node("Attributional, average grid (not marginal)", "note", grade="assumed",
             sources_md={k: v for k, v in assumptions.items() if "average" in k.lower()}),
        node("Functional unit of the LP: one year of a data centre's demand served", "note",
             grade="assumed", note="Each capacity's embodied carbon is annualised over its life; "
             "flows are scaled from the window to a year (dc_model.Series.annual_scale)."),
        node("Assumptions register (ASSUMPTIONS.md)", "group",
             children=[node(k, "note", sources_md={k: v}) for k, v in assumptions.items()]),
    ])

    # ---------------------------------------------------------------- the LCA, by technology
    # The map's spine. Each technology is a functional unit delivered at the
    # 20 kV site bus, nested stage by stage down the power chain, exactly as a
    # unit-process LCA would chain it. The LP's terms are an organising layer
    # on top (next section): every stage says which term charges it.
    import copy as _copy
    emb = ren.apply_case(ren.decompose_all(), "central").set_index("technology")
    wind, sol = emb.loc["onshore_wind"], emb.loc["solar_pv"]
    lw, ls, lgrid = cl.stepup("onshore_wind"), cl.stepup("solar_pv"), cl.grid_intake()
    hv = G.DELIVERY["high"]

    def ei_act(name, loc, product=None):
        return S.H.resolve_exact(name, loc, product) if product else S.H.resolve_exact(name, loc)

    wind_ei = ei_act(*ren.TECHNOLOGIES["onshore_wind"][:2])
    pv_ei = ei_act(*ren.TECHNOLOGIES["solar_pv"][:2])

    def reid(n):
        n["id"] = nid()
        for c in n.get("children", []):
            reid(c)
        return n

    def rescaled(n, factor, unit, note=None, role=None, name=None):
        """A copy of a node with its exchange re-expressed per the chain's
        functional unit. Only its own exchange is scaled; what it is made of
        (its children) stays per unit of itself."""
        c = reid(_copy.deepcopy(n))
        ex = dict(c.get("exchange") or {})
        ex["amount"] = (ex.get("amount") or 0.0) * factor
        ex["contribution"] = (ex.get("contribution") or 0.0) * factor
        ex["unit"] = unit
        if note:
            ex["note"] = note
        c["exchange"], c["scaled"] = ex, factor
        if role:
            c["role"] = role
        if name:
            c["inventory_name"], c["name"] = c["name"], name
        return c

    def fgn(code, db, ex=None, name=None, **extra):
        n = F.activity_node(db, code, exchange=ex)
        if name:
            n["inventory_name"], n["name"] = n["name"], name
        n.update({k: v for k, v in extra.items() if v})
        return n

    def by_code(n, code):
        return next(c for c in n["children"] if c.get("code") == code)

    def stands(db, code, why):
        """Names the inventory activity a box stands for when the activity's own
        box would only repeat it (an operation activity with its electricity taken
        out, a per-kWh wrapper). The checker counts it as showing that activity."""
        a = next(x for x in F.invs[db][1].activities if x.code == code)
        return [{"database": db, "code": code, "name": a.name, "why": why}]

    def part(name, contribution, unit, *, grade="derived", source=None, note=None, lp=None,
             children=(), gaps=(), stands_for=None):
        return node(name, "part", grade=grade, source=source, note=note, lp=lp, stands_for=stands_for,
                    exchange={"contribution": contribution, "unit": unit},
                    gaps=gap_ids(*gaps), children=list(children))

    def stage(name, value, unit, children, *, lp=None, loss=None, note=None, source=None):
        """One stage of a chain: its own inputs, plus the stage upstream of it."""
        return node(name, "stage", value=value, unit=unit, lp=lp, loss=loss, note=note,
                    source=source,
                    exchange={"contribution": value, "unit": unit, "note": "the stage upstream"},
                    children=list(children))

    def fu(name, value, unit, *, lp, lp_terms, children, module, grade="derived", source=None,
           note=None, gap_keys=(), todo_keys=(), test_keys=(), source_titles=(), additive=True,
           stands_for=None):
        return node(name, "fu", value=value, unit=unit, lp=lp, module=module, grade=grade,
                    source=source, note=note, additive=additive, stands_for=stands_for,
                    parts=[[l, v, t] for l, v, t in lp_terms],
                    gaps=gap_ids(*gap_keys), todo=todo_for(*todo_keys), tests=tests_for(*test_keys),
                    sources_md=src(*source_titles),
                    module_doc=odoc.get(Path(module).stem) if module.startswith("optimisation/") else None,
                    children=list(children))

    def not_modelled(name, why, gaps=()):
        return node(name, "note", status="not", grade="assumed", note="Not modelled. " + why,
                    gaps=gap_ids(*gaps))

    def pc(x, d=2):
        return f"{x * 100:.{d}f} %"

    # ---- wind ------------------------------------------------------------------
    def restate_steps(row, ei, label, rated_mw):
        """How a wind coefficient is built, as the numbered steps renewables.py takes."""
        parts = row.get("life_extension_fraction", 0.0) or 0.0
        cap0 = row.ecoinvent_capital_kgco2e_per_MW
        cap1 = cap0 * (1 + parts)
        life, lf = row.study_lifetime_years, row.study_load_factor
        resid = row.get("residual_per_kWh", 0.0) or 0.0
        annual = row.annual_kgco2e_per_MW
        return [
            node(f"1 · Start from ecoinvent's per-kWh {label} dataset", "step", grade="transcribed",
                 value=S.score(ei) * 1000, unit="g CO₂e per kWh as ecoinvent amortises it",
                 note=("ecoinvent does not sell a wind farm per MW: it models **electricity per kWh**, "
                       "and puts the farm inside that kWh as a fraction of one turbine. Its inputs "
                       "counted in *units* — the turbine and its network connection — are the "
                       "**capital goods** (marked below). Every other input (lubricating oil, "
                       "maintenance, transport) is the per-kWh **residual**."),
                 children=[F.ecoinvent_node(ei, {"note": "the per-kWh dataset the coefficient is decomposed from"},
                                            open_one_level=True)]),
            node(f"2 · Take out the capital: {cap0:,.0f} kg CO₂e per MW", "step", grade="derived",
                 value=cap0, unit="kg CO₂e per MW of turbine",
                 note=(f"The unit-counted inputs from step 1, summed per kWh, scaled up to one whole "
                       f"turbine and divided by its {rated_mw:g} MW rating. No longer tied to "
                       f"ecoinvent's own load factor or 20-year life. The rest, {resid * 1000:.2f} g "
                       "per kWh, is kept as the residual. renewables.check_reconstruction re-amortises "
                       "it at ecoinvent's own life and yield and rebuilds the dataset exactly.")),
            node(f"3 · Add the parts to reach a {life:.0f}-year life: ×{1 + parts:.3f}", "step",
                 grade="assumed", value=cap1, unit="kg CO₂e per MW",
                 note=(f"ecoinvent's turbine lasts 20 years with no replacements; this study runs it "
                       f"{life:.0f} (DESNZ/Arup 2024). Servicing 4 % of capital per 20 years, pro rata "
                       "(Vestas V136/V162 LCAs, Siemens Gamesa EPD), plus one gearbox, main-shaft and "
                       f"blade overhaul (20.5 %) once past a 25-year design life. Basis: "
                       f"{row.get('life_extension_basis', 'none')}.")),
            node(f"4 · Annualise: {annual:,.0f} kg CO₂e per MW per year", "step", grade="derived",
                 value=annual, unit="kg CO₂e per MW per year — the LP coefficient",
                 note=(f"Capital ÷ {life:.0f} years, plus the residual at this study's yield (net load "
                       f"factor {lf:.1%}, DESNZ/Arup 2024 central). Per kWh: "
                       f"{row.restated_kgco2e_per_kWh * 1000:.2f} g CO₂e.")),
        ]

    def capital_goods(ei, rated_mw, life):
        """ecoinvent's unit-counted inputs of a per-kWh dataset, each per MW-year of plant:
        the same selection and arithmetic as renewables.decompose."""
        units = [e for e in ei.technosphere() if e.input.get("unit") == "unit"]
        units_per_kwh = max(float(e["amount"]) for e in units)
        out = []
        for e in units:
            per_mw_yr = float(e["amount"]) / units_per_kwh / rated_mw / life
            n = F.ecoinvent_node(e.input, {"amount": per_mw_yr, "unit": "units per MW per year",
                                           "contribution": S.score(e.input) * per_mw_yr,
                                           "note": f"{float(e['amount']) / units_per_kwh:g} per turbine ÷ "
                                                   f"{rated_mw:g} MW ÷ {life:.0f} years"},
                                 open_one_level=True)
            n["role"] = "capital good — counted per unit"
            out.append(n)
        return out

    def turbine_components(row, ei, label, rated_mw, term_name, var):
        """The turbine's own carbon, per MW-year, as the components the LP term is made of."""
        cap0 = row.ecoinvent_capital_kgco2e_per_MW
        parts = row.get("life_extension_fraction", 0.0) or 0.0
        life, lf = row.study_lifetime_years, row.study_load_factor
        resid = (row.get("residual_per_kWh", 0.0) or 0.0) * lf * 8760 * 1000
        u = "kg CO₂e per MW per year"
        lp_ = f"gwp_{var} × cap_{var} — LP term '{term_name}'"
        return [
                part(f"Turbine and its network connection, generating at {stx.TX_TURBINE_TERMINAL_V:g} V — "
                     f"ecoinvent's capital goods ÷ {life:.0f} years",
                     cap0 / life, u, grade="transcribed", lp=lp_,
                     source="ecoinvent 3.9.1 apos, the unit-counted inputs of the per-kWh dataset, decomposed",
                     note="The two capital goods ecoinvent counts per unit, each per MW-year of turbine. The "
                          "per-kWh dataset they are taken out of is under 'How renewables.py derives these numbers'.",
                     children=capital_goods(ei, rated_mw, life)),
                part(f"Replacement parts to last {life:.0f} years: ×{parts:.3f} of the capital",
                     cap0 * parts / life, u, grade="assumed", gaps=("wind life extension",), lp=lp_,
                     source="Vestas V136/V162 LCAs (servicing ~4 % per 20 y); V136/V162 Fig 7 shares for "
                            "a gearbox, main-shaft and blade overhaul (20.5 %) past a 25-y design life",
                     note="ecoinvent's turbine is a 20-year machine with no replacements; this is what it "
                          "takes to run it for the DESNZ life."),
                part(f"Operation — lubricating oil, maintenance transport: ecoinvent's per-kWh residual "
                     f"at {lf:.1%} load factor", resid, u, grade="transcribed", lp=lp_,
                     source="the non-capital inputs of the same dataset, per kWh × this study's yield"),
                node("How renewables.py derives these numbers", "group",
                     children=restate_steps(row, ei, label, rated_mw)),
        ]

    def tx_node(code, db, name, amount, unit, contribution, note, lp, loss):
        return fgn(code, db, {"amount": amount, "unit": unit, "contribution": contribution, "note": note},
                   name=name, lp=lp, loss=loss)

    wind_fu = fu(
        "Onshore wind — 1 MW-year delivered at the 20 kV bus",
        tech.gwp_wind + tech.gwp_tx_wind_per_mw, "kg CO₂e per MW per year",
        lp="(gwp_wind + gwp_tx_wind_per_mw) × cap_wind: two LP terms on one variable",
        lp_terms=[("Onshore wind", tech.gwp_wind, "Onshore wind"),
                  (T_TX_WIND, tech.gwp_tx_wind_per_mw, T_TX_WIND)],
        module="optimisation/renewables.py",
        source="ecoinvent 3.9.1 GB onshore 1-3 MW turbine, capital decomposed and restated at DESNZ/Arup 2024 "
               "life and load factor; parts from Vestas/SGRE LCAs; step-ups from Leng et al. 2026",
        note=f"Per kWh at the study's {wind.study_load_factor:.1%} net load factor: "
             f"{(tech.gwp_wind + tech.gwp_tx_wind_per_mw) / (wind.study_load_factor * 8760 * 1000) * 1000:.2f} g CO₂e.",
        gap_keys=("wind",), todo_keys=("wind",), test_keys=("wind",),
        source_titles=("Renewable generation", "Carbon-side fixes", "Generation step-up"),
        children=[
            tx_node(R.TX_WIND, R.TRANSFORMER_DB,
                    f"Step-up transformers, {stx.TX_TURBINE_TERMINAL_V / 1000:g} → {stx.TX_SITE_COLLECTION_KV:g} kV, "
                    f"one per turbine ({stx.TX_LENG_UNIT_MVA:g} MVA)",
                    1.0 / wind.study_lifetime_years, "MW of step-ups per MW per year", tech.gwp_tx_wind_per_mw,
                    f"one MW of turbine step-ups over the turbine's {wind.study_lifetime_years:.0f}-year life",
                    f"gwp_tx_wind_per_mw × cap_wind — LP term '{T_TX_WIND}'",
                    f"no-load {pc(lw['noload_mw_per_mw'], 3)} of capacity; load "
                    f"{pc(lw['load_loss_per_mw_at_full_loading'])} of output at full loading (energy, not carbon)"),
            *turbine_components(wind, wind_ei, "onshore wind", ren.TECHNOLOGIES["onshore_wind"][2] / 1000,
                                "Onshore wind", "wind"),
            node(f"Dispatch: Renewables.ninja V90 at 80 m × net factor {profiles.WIND_NET_FACTOR:.3f}",
                 "note", grade="derived", source="Staffell & Pfenninger 2016; Arup 2024 §5.8; Vestas LCAs",
                 note=("Not part of the carbon: this sets how much the built MW generate each hour. "
                       "Array cable losses sit in the electrical term. Components: "
                       + ", ".join(f"{k} {v}" for k, v in profiles.WIND_NET_COMPONENTS.items()))),
        ])

    # ---- solar ------------------------------------------------------------------
    plant = F.activity_node(R.SOLAR_DB, R.UPV_CAPITAL)
    om = F.activity_node(R.SOLAR_DB, R.UPV_OM30)
    life_s, lf_s = sol.study_lifetime_years, sol.study_load_factor
    us = "kg CO₂e per MWp per year"
    inv_cap = rescaled(by_code(plant, R.UPV_INVERTER), 1.0 / life_s, "units per MWp per year",
                       note=f"Smith A10: one 2.7 MWac inverter per {upv.UPV_PV_INVERTER_MVA * upv.UPV_PV_ILR:.2f} MWp, "
                            f"over the plant's {life_s:.0f}-year life",
                       name="Inverters, DC → 0.4 kV AC, 2.7 MWac (Smith A10)")
    inv_rep = rescaled(by_code(om, R.UPV_INVERTER), 1.0 / upv.UPV_PV_OM_REFERENCE_YEARS, "units per MWp per year",
                       note=f"replacement: {upv.UPV_PV_OM_REPLACEMENT_FRACTION:.0%} of the installed count over 30 years (Smith A15)",
                       role="replacement", name="Inverter replacements (Smith A15)")
    array_items = ([rescaled(c, 1.0 / life_s, us, note=f"plant capital over its {life_s:.0f}-year life")
                    for c in plant["children"] if c.get("code") != R.UPV_INVERTER]
                   + [rescaled(c, 1.0 / upv.UPV_PV_OM_REFERENCE_YEARS, us,
                               note="operation and maintenance, at Smith's 30-year rate",
                               role=("replacement" if c.get("code") == R.UPV_MODULE else None))
                      for c in om["children"] if c.get("code") != R.UPV_INVERTER])
    array_val = sum(c["exchange"]["contribution"] for c in array_items)
    inv_val = inv_cap["exchange"]["contribution"] + inv_rep["exchange"]["contribution"]
    array_stage = stage(
        "The array, DC side — modules, mounting, DC balance of system, fence, installation, their O&M", array_val, us,
        children=array_items,
        lp="inside gwp_solar × cap_solar — LP term 'Solar PV'",
        loss=f"DC cabling and combiner losses are inside Renewables.ninja's flat {cfg.PV_SYSTEM_LOSS:.0%} system loss (ASSUMED)",
        note="Modules, mounting, DC electrical balance of system (Smith A12), fence and installation from the "
             "plant; replacement panels and vegetation management from 30 years of O&M, rescaled to the study life.")
    for n_ in (inv_cap, inv_rep):
        n_["lp"] = "inside gwp_solar × cap_solar — LP term 'Solar PV' (the inverter is part of Smith's plant)"
        n_["loss"] = f"conversion and clipping at DC/AC ratio {upv.UPV_PV_ILR:g}: inside the {cfg.PV_SYSTEM_LOSS:.0%} system loss"
    solar_fu = fu(
        "Solar PV — 1 MWp-year delivered at the 20 kV bus",
        tech.gwp_solar + tech.gwp_tx_solar_per_mwp, us,
        lp="(gwp_solar + gwp_tx_solar_per_mwp) × cap_solar: two LP terms on one variable",
        lp_terms=[("Solar PV (utility, fixed tilt 20°)", tech.gwp_solar, "Solar PV (utility, fixed tilt 20°)"),
                  (T_TX_SOLAR, tech.gwp_tx_solar_per_mwp, T_TX_SOLAR)],
        module="optimisation/renewables.py",
        source="Smith et al. 2024, NREL/TP-7A40-87372 Appendix A, rescored on ecoinvent 3.9.1 apos "
               "(optimiser_lca/upv.py); DESNZ/Arup 2024 life and load factor; step-ups IEA PVPS T12-33:2026",
        note=f"Per kWh at the study's {lf_s:.1%} net load factor: "
             f"{(tech.gwp_solar + tech.gwp_tx_solar_per_mwp) / (lf_s * 8760 * 1000) * 1000:.2f} g CO₂e. "
             "Not shown: ecoinvent's own GB PV dataset (a 2008 plant, El Tesoro) is kept selectable as "
             "solar_basis='ecoinvent' only to reproduce runs from before Smith 2024 replaced it.",
        gap_keys=("solar", "pv "), todo_keys=("solar",), test_keys=("solar", "upv"),
        source_titles=("Solar is not scored on ecoinvent", "rebuild rather than a citation", "Solar's inverter-station"),
        children=[
            tx_node(R.TX_SOLAR, R.TRANSFORMER_DB,
                    f"Step-up transformer, 0.4 → {stx.UPV_TX_PRIMARY_KV:g} kV, at the inverter station "
                    f"({stx.UPV_TX_UNIT_MVA:g} MVA, {stx.UPV_TX_UNITS_PER_PLANT} per {stx.UPV_TX_REFERENCE_MWP:g} MWp)",
                    1.0 / life_s, "MWp of step-ups per MWp per year", tech.gwp_tx_solar_per_mwp,
                    f"one MWp of inverter-station step-ups over the plant's {life_s:.0f}-year life. A transformer, "
                    "not an inverter: it stands beside the inverter and steps its 0.4 kV output up to 20 kV",
                    f"gwp_tx_solar_per_mwp × cap_solar — LP term '{T_TX_SOLAR}'",
                    f"no-load {pc(ls['noload_mw_per_mw'], 3)} of capacity; load "
                    f"{pc(ls['load_loss_per_mw_at_full_loading'])} of output at full loading (energy, not carbon)"),
            inv_cap, inv_rep, array_stage,
        ])
    print(f"  solar chain residual vs LP: {(array_val + inv_val) / tech.gwp_solar - 1:+.2e}")

    # ---- grid ------------------------------------------------------------------
    import pandas as _pd
    london = _pd.read_csv(ROOT / "custom_grid_lca_outputs" / (
        "custom_grid_lca_carbon_api_regional_auto_r13_cheap_2025-01-01T00-00-00T_to_T2025-12-29T00-00-00.csv"))
    mix_cols = [c for c in london.columns if c.endswith("_perc") and c != "api_total_perc"]
    mix = {c[:-5]: london[c].mean() / 100 for c in mix_cols}
    imp_split = {c: (london["IMPORTS_perc"] * london[f"imp_{c}"]).mean() / 100 for c in G.COUNTRIES}
    gen_mean = float(london["generation_kgco2e_per_kwh"].mean() * 1000)
    deliv_mean = float(london["custom_electricity_score"].mean() * 1000)
    ug = "g CO₂e per kWh"

    def grid_source_node(key, share):
        p = G.SOURCES[key]
        act = S.H.resolve_exact(*p.identity, database=p.database) if p.database else S.H.resolve_exact(*p.identity)
        sc = S.score(act)
        ex = {"amount": share, "unit": "kWh per kWh generated (London 2025 mean share)", "note": p.why,
              "contribution": _mul(sc, share * 1000.0)}
        if p.database and (act["database"], act["code"]) in F.acts:
            return F.activity_node(act["database"], act["code"], exchange=ex)
        return F.ecoinvent_node(act, ex, key=key, proc=p, open_one_level=True)

    src_kids = []
    for k, v in mix.items():
        if v <= 0:
            continue
        if k == "WIND":
            src_kids.append(part(f"Wind {v:.1%} — split by ecoinvent's GB market", 0.0, ug, grade="transcribed",
                                 children=[grid_source_node(w, v * f) for w, f in G.WIND_GROUP_WEIGHTS.items()]))
            src_kids[-1]["exchange"]["contribution"] = sum(c["exchange"]["contribution"] for c in src_kids[-1]["children"])
        elif k == "IMPORTS":
            kids = [grid_source_node(G.COUNTRY_SOURCE[c], s) for c, s in imp_split.items() if s > 0]
            src_kids.append(part(f"Imports {v:.1%} — split by interconnector flows (fitted per region)",
                                 sum(c["exchange"]["contribution"] for c in kids), ug, grade="derived",
                                 source="Elexon FUELHH flows, NNLS fit to NESO's regional import share "
                                        "(grid_build.fit_import_attribution)", children=kids))
        elif k in G.SOURCES:
            src_kids.append(grid_source_node(k, v))
    gen_stage = stage("1 kWh generated — the site's regional mix, each half-hour (shown: London, 2025 mean)",
                      gen_mean, ug, children=src_kids,
                      lp="ci[t] before delivery (grid_build.score_row, each half-hour of the run's own series)",
                      source="NESO Carbon Intensity API regional mix; each fuel on its optimiser_lca.grid activity",
                      note="The LP never uses one mix: every run reads its own site's Carbon Intensity region, "
                           "half-hour by half-hour, for the window it is solved over (all 14 regions are cached; a "
                           "missing window is built on demand, and sites.require_grid_region refuses another "
                           "region's series). The shares and figures here are the time-mean for the London 2025 "
                           "reference, so that one number can be shown per fuel.")
    delivery_items = [
            part(f"Transmission losses on the way to the connection point: {pc(hv['gross_up'] - 1)} more generated "
                 "than delivered at high voltage", (hv["gross_up"] - 1) * gen_mean, ug, grade="derived",
                 lp="inside ci[t] × imp[t] — LP term 'Grid imports' (the series is delivered at the site's voltage)",
                 source="optimiser_lca.grid.DELIVERY, from ecoinvent's GB voltage chain (grid.derive_delivery)",
                 note="The generation mix's carbon on the kWh that never arrive."),
            part("The transmission network's own embodied carbon — lines, cables, transformers, SF₆, N₂O from corona "
                 "discharge", hv["network_gco2e_per_kwh"], ug, grade="derived",
                 lp="inside ci[t] × imp[t] — LP term 'Grid imports'",
                 source="ecoinvent 3.9.1 GB high-voltage market, electricity inputs removed",
                 children=[node(f"{v}: ×{d['gross_up']:.4f} losses + {d['network_gco2e_per_kwh']:.2f} g/kWh network "
                                "(not used: every site here connects at high voltage)", "note", grade="derived")
                           for v, d in G.DELIVERY.items() if v != "high"]),
    ]
    intake_per_kwh = tech.gwp_grid_per_mw / 8760.0
    grid_fu = fu(
        "Grid imports — 1 kWh delivered at the 20 kV bus (the site's region, each half-hour; shown: London 2025 mean)",
        deliv_mean + intake_per_kwh, ug,
        lp="Σ ci[t] × imp[t] + gwp_grid_per_mw × cap_grid",
        lp_terms=[("Grid imports (half-hourly, regional)", deliv_mean, "Grid imports (half-hourly, regional)"),
                  ("Intake transformers per kWh at 100 % connection utilisation (kg per MW-year ÷ 8,760 h)",
                   intake_per_kwh, "Grid connection (intake transformers, N-1)")],
        module="optimisation/grid_build.py",
        source="NESO Carbon Intensity API regional generation mix, each fuel scored on its own life-cycle "
               "activity (optimiser_lca/grid.py); delivered at the site's voltage; intake from Leng et al. 2026",
        note="The intake is per MW of connection in the LP; per kWh it is shown at 100 % utilisation, the "
             "least it can be. At the LP's real loading it is larger per kWh but still well under 0.1 g.",
        gap_keys=("grid", "import"), todo_keys=("grid", "import", "118"), test_keys=("grid",),
        source_titles=("Baseline 1", "The grid intake"),
        children=[
            node("Which mix the LP reads", "note", grade="transcribed",
                 note="imp[t] × ci[t], where ci[t] is the site's own Carbon Intensity region in that half-hour, "
                      "scored on optimiser_lca.grid.SOURCES and delivered at the site's connection voltage. London "
                      "2025 is shown because this map is built for the London reference case; a run at Inverness "
                      "reads region 1's series, and the region id is recorded in every series file.",
                 source="dc_inputs.build_series; profiles.build; sites.require_grid_region"),
            tx_node(R.TX_GRID, R.TRANSFORMER_DB,
                    f"Intake transformers, 110/132 → {stx.TX_SITE_COLLECTION_KV:g} kV, N-1 "
                    f"({gc.TRANSFORMER_REDUNDANCY / gc.POWER_FACTOR:g} MVA per MW of connection)",
                    gc.TRANSFORMER_REDUNDANCY / gc.POWER_FACTOR / gc.ASSET_LIFE_YEARS / 8760.0,
                    "MVA per kWh at 100 % utilisation", intake_per_kwh,
                    f"{gc.TRANSFORMER_REDUNDANCY:g} MVA per MW (N-1) over {gc.ASSET_LIFE_YEARS:g} years, "
                    "spread over 8,760 h; charged per MVA on Leng's 100 MVA, 110 kV unit",
                    "gwp_grid_per_mw × cap_grid — LP term 'Grid connection'",
                    f"no-load {pc(lgrid['noload_mw_per_mw'], 3)} of the connection; load "
                    f"{pc(lgrid['load_loss_fraction'], 3)} of imports (energy, not carbon)"),
            *delivery_items, gen_stage,
            node("Grid basis id: " + G.sources_id(), "note", note="Every series records it; a series "
                 "scored on another basis is ignored (profiles.grid_file_is_current)."),
        ])

    # ---- battery ----------------------------------------------------------------
    thr, life_b = battery.lifetime_throughput_mwh_per_mwh(), battery.ASSET_LIFE_YEARS
    ub = "kg CO₂e per MWh delivered"
    e_per_mwh = tech.gwp_batt_e * life_b / thr
    p_per_mwh = tech.gwp_batt_p / 4 * life_b / thr
    block = F.activity_node(R.BESS_DB, R.BESS_DC_BLOCK_KWH)
    f_block = 1000.0 / battery.USABLE_FRACTION / thr
    (container,) = block["children"]          # the per-kWh activity holds one input: the container
    dc_block = rescaled(container, f_block, ub,
                        note=f"per nameplate kWh ÷ {battery.USABLE_FRACTION:.0%} usable, "
                             f"over {thr:,.0f} MWh delivered per MWh installed",
                        name="Cells, modules, racks and container — the DC block, per MWh delivered")
    dc_block.update({
        "lp": f"gwp_batt_e × cap_batt_e — LP term '{T_BATT_E}' (per usable MWh of capacity per year)",
        "stands_for": stands(R.BESS_DB, R.BESS_DC_BLOCK_KWH,
                             f"what battery.py scores: {container['exchange']['amount']:.3e} of this container per "
                             f"nameplate kWh, one per {1 / container['exchange']['amount']:,.0f} kWh"),
        "loss": f"usable {battery.USABLE_FRACTION:.0%} of nameplate (ASSUMED); standing loss "
                f"{battery.STANDING_LOSS_PER_HOUR:g} /h by default (swept)",
        "source": "Jasper et al. 2026 liquid-cooled LFP container; Voß et al. 2025 cell, made in China"})
    pcs = ei_act(*battery.PCS_ACTIVITY)
    eta_b = battery.ROUND_TRIP_EFFICIENCY ** 0.5
    pcs_node = F.ecoinvent_node(pcs, {"amount": 1000.0 / battery.PCS_RATED_KW / (4 * thr),
                                      "unit": "units per MWh delivered (4-hour battery)",
                                      "contribution": p_per_mwh,
                                      "note": f"{battery.PCS_RATED_KW:.0f} kW units, 2 per MW, over 15 y of Modo cycling"},
                                open_one_level=True)
    pcs_node.update({"name": "Power conversion system, DC ↔ AC, 500 kW inverters", "inventory_name": pcs["name"],
                     "lp": f"gwp_batt_p × cap_batt_p — LP term '{T_BATT_P}'",
                     "loss": f"round trip {battery.ROUND_TRIP_EFFICIENCY:.0%} (Modo), ×{eta_b:.3f} each way"})
    # The container's own LV → 20 kV step-up (Jasper's unit on the IEA composition), per MW
    # of PCS over the battery's life, shown per MWh delivered like the power term.
    lb = cl.container_stepup("battery")
    tx_b_per_mwh = tech.gwp_tx_batt_per_mw / 4 * life_b / thr
    batt_tx = tx_node(R.TX_LV_CONTAINER, R.TRANSFORMER_DB,
                      f"Step-up transformer, 0.4 → {stx.TX_SITE_COLLECTION_KV:g} kV, one per container "
                      f"({cl.BATTERY_UNIT_KVA / 1000:g} MVA per {cl.BATTERY_UNIT_KVA / 1000:g} MW of PCS)",
                      0.25 / thr, "MW of step-up per MWh delivered (4-hour battery)", tx_b_per_mwh,
                      f"one MW of container step-up per MW of PCS, over the battery's {life_b} years and "
                      f"{thr:,.0f} MWh delivered per MWh installed",
                      f"gwp_tx_batt_per_mw × cap_batt_p — LP term '{T_TX_BATT}'",
                      f"no-load {pc(lb['noload_mw_per_mw'], 3)} of PCS rating, always; load "
                      f"{pc(lb['load_loss_fraction'], 2)} of power through it, both ways "
                      f"(x_eff {lb['x_eff']:g}, ASSUMED)")
    batt_fu = fu(
        "Battery — 1 MWh discharged at the bus (4-hour battery, Modo cycling)",
        e_per_mwh + p_per_mwh + tx_b_per_mwh, ub,
        lp="gwp_batt_e × cap_batt_e + (gwp_batt_p + gwp_tx_batt_per_mw) × cap_batt_p — per capacity, because the "
           "LP decides the cycling",
        lp_terms=[("Cells, modules, racks, container — per MWh delivered", e_per_mwh, T_BATT_E),
                  ("Power conversion — per MWh delivered", p_per_mwh, T_BATT_P),
                  ("Step-up transformer — per MWh delivered", tx_b_per_mwh, T_TX_BATT)],
        module="optimisation/battery.py",
        source="Jasper et al. 2026 + Voß et al. 2025 on ecoinvent 3.9.1; PCS ecoinvent 500 kW inverter; "
               f"Modo: {life_b} y, {battery.WARRANTED_CYCLES:,} cycles to {battery.CAPACITY_AT_END_OF_LIFE:.0%}",
        note=f"A 4-hour battery delivers {thr:,.0f} MWh per MWh installed over its life.",
        gap_keys=("battery",), todo_keys=("battery",), test_keys=("batt", "bess"),
        source_titles=("Battery storage", "grid battery's energy term"),
        children=[
            batt_tx, pcs_node, dc_block,
            node("Cell sensitivity bases (battery.CELL_KGCO2E_PER_KWH)", "group", children=[
                fgn(R.BESS_CELL_DE, R.BESS_DB, status="option",
                    note="Alternative cell basis, built but not the default (bess.CELL_FACTORY is CN): Voß's cell "
                         "on German electricity and heat.")] + [
                node(f"{k}: {v} kg CO₂e/kWh of cells", "note",
                     grade=("derived" if k != "jasper_fig4_311" else "transcribed"))
                for k, v in battery.CELL_KGCO2E_PER_KWH.items()]),
        ])

    # ---- electrolysers: three technologies, each its own functional unit ---------
    ely_rows = {r["technology"]: r for r in ely.decompose_all()}
    pem = ely_rows["PEM operation"]
    uh = "kg CO₂e per kg H₂"
    ELY = (("PEM operation", R.PEM_OP, R.PEM_UNIT, "PEM"),
           ("AE operation", R.AE_OP, R.AE_UNIT, "alkaline"),
           ("SOEC operation", R.SOEC_OP, R.SOEC_UNIT, "SOEC"))
    ely_fus = []
    for label, op_code, unit_code, short in ELY:
        row = ely_rows[label]
        t_e = I.build_tech("london", meta, ely_tech=label)
        op = F.activity_node(R.HYDROGEN_DB, op_code)
        cap_box = reid(_copy.deepcopy(by_code(op, unit_code)))
        elec = [c for c in op["children"] if "electricity" in c["name"].lower()]
        cons = [reid(_copy.deepcopy(c)) for c in op["children"] if c.get("code") != unit_code and c not in elec]
        cons_val = sum(c["exchange"]["contribution"] for c in cons)
        pressure = ely.DELIVERY_PRESSURE_BAR[label]
        comp = h2s.compression_kwh_per_kg(pressure, h2_tank.DESIGN["pressure_bar"])
        cf_ = row["implied_capacity_factor"]
        heat = " Its 5.24 kWh/kg of external heat comes from a gas boiler and is inside the consumables." if short == "SOEC" else ""
        pressure_note = " (ASSUMED: the inventory does not state it)" if label in ely.DELIVERY_PRESSURE_ASSUMED else ""
        cap_box.update({
            "name": f"Stack, power supply and plant — the {short} capital good, per kg at {cf_:.0%} utilisation",
            "inventory_name": cap_box["name"],
            "lp": f"gwp_ely × cap_ely — LP term 'Electrolyser capital': {t_e.gwp_ely:,.0f} kg CO₂e per MW per year "
                  f"when {short} is selected (per MW over {ely.PLANT_LIFETIME_YEARS:g} y; the LP sets the utilisation)",
            "loss": f"{row['kwh_per_kg']:g} kWh per kg of electricity (system; rectifier taken as inside — not verified "
                    f"at source)" + (f"; plus 5.24 kWh/kg of heat" if short == "SOEC" else ""),
            "note": "Hermesmann's capital good is one monolithic activity: no stack/BoP split, so stack replacement "
                    "cannot be charged separately (open gap).",
        })
        ely_fus.append(fu(
            f"Electrolyser, {short} — 1 kg H₂ at {pressure:g} bar{pressure_note}, electricity excluded, at Hermesmann's "
            f"{cf_:.0%} utilisation" + (" (gas-boiler heat included)" if short == "SOEC" else ""),
            row["foreground_fixed_kgco2e_per_kg"], uh,
            lp=f"gwp_ely × cap_ely + ely_variable_gwp_per_kg × kg made, with ely_tech='{label}' — the LP splits "
               "capital from consumables because it decides the utilisation",
            lp_terms=[(f"{short} capital per kg at {cf_:.0%} utilisation",
                       row["foreground_fixed_kgco2e_per_kg"] - t_e.ely_variable_gwp_per_kg,
                       "Electrolyser capital (PEM default; AE, SOEC selectable)"),
                      (f"{short} consumables per kg", t_e.ely_variable_gwp_per_kg,
                       "Electrolyser consumables (water, heat)")],
            module="optimisation/electrolysers.py",
            source=f"Hermesmann & Müller 2022, {label} and its capital good (SimaPro exports), on ecoinvent 3.9.1"
                   + ("; heat on a gas boiler, Mehmeti et al. 2018" if short == "SOEC" else ""),
            note=f"The inventory's own functional unit ({op_code}) with its electricity taken out: the LP supplies "
                 f"that at the dispatch's own carbon.{heat}",
            gap_keys=("electrolyser", "soec", "alkaline", "consumables"), todo_keys=("soec", "electrolyser"),
            test_keys=("electrolyser", "consumable"), source_titles=("Electrolysers",),
            stands_for=stands(R.HYDROGEN_DB, op_code, "the inventory's own functional unit, with its electricity taken out"),
            children=[
                node(f"Electricity excluded: {row['kwh_per_kg']:g} kWh per kg, plus {comp:.2f} kWh/kg of compression "
                     f"from {pressure:g} to {h2_tank.DESIGN['pressure_bar']:g} bar", "note", status="option",
                     note="The inventory links its electricity to ecoinvent's GB grid; the study strips it and the LP "
                          "charges p_ely[t] at whatever supplies the bus in that half-hour."),
                part("Water, heat and waste — the consumables", cons_val, uh, grade="transcribed", children=cons,
                     lp=f"ely_variable_gwp_per_kg × kg made — LP term 'Electrolyser consumables' "
                        f"({t_e.ely_variable_gwp_per_kg:.3f} kg per kg for {short})",
                     source="the non-electricity, non-capital inputs of the operation activity"),
                cap_box,
            ]))
    ely_group = node("Electrolysers — 1 kg H₂, by technology (PEM is the default; alkaline and SOEC are selectable)",
                     "group", children=ely_fus)

    # ---- fuel cell -------------------------------------------------------------
    d_fc = fc.decompose()
    bop = F.activity_node(R.FUEL_CELL_DB, R.FC_BOP)
    inv_child = next(c for c in bop["children"] if "inverter" in c["name"].lower())
    f_bop = fcl.FC_BOP_PER_KWH * 1000.0
    uf = "g CO₂e per kWh AC"
    inv_node = rescaled(inv_child, f_bop, uf, note="the balance of plant's inverter, over 80,000 h of BoP life",
                        name="Inverter, DC → AC, 500 kW units (inside the balance of plant)")
    inv_node["lp"] = f"inside gwp_fc_bop_per_mw × fc_bop_units — LP term '{T_FC_BOP}'"
    loops = [rescaled(c, f_bop, uf, note="balance of plant over 80,000 h") for c in bop["children"] if c is not inv_child]
    loops_val = sum(c["exchange"]["contribution"] for c in loops)
    stack_node = fgn(R.FC_STACK, R.FUEL_CELL_DB,
                     {"amount": fcl.FC_STACK_PER_KWH, "unit": "kW of stack per kWh AC",
                      "contribution": d_fc["_per_kwh"]["stack"] * 1000.0,
                      "note": f"one kW of stack over {d_fc['stack_lifetime_hours']:,.0f} running hours"},
                     lp=f"gwp_fc_stack_per_mw × fc_stack_units — LP term '{T_FC_STACK}'")
    service_node = fgn(R.FC_SERVICE, R.FUEL_CELL_DB,
                       {"amount": fcl.FC_SERVICE_PER_KWH, "unit": "services per kWh AC",
                        "contribution": d_fc["_per_kwh"]["maint"] * 1000.0,
                        "note": f"an air filter and coolant every {fcl.FC_SERVICE_INTERVAL_H:,} h (ASSUMED)"},
                       lp="gwp_fc_maint_per_mwh × p_fc — LP term 'Fuel cell service'")
    # The container's LV → 20 kV step-up, per MW of cap_fc over the BoP calendar life, shown
    # per kWh at the BoP's own running hours like the BoP itself.
    lfc = cl.container_stepup("fuel_cell")
    tx_fc_per_kwh = tech.gwp_tx_fc_per_mw * tech.fc_bop_calendar_years / d_fc["bop_duty_lifetime_hours"]
    fc_tx = tx_node(R.TX_LV_CONTAINER, R.TRANSFORMER_DB,
                    f"Step-up transformer, 0.4 → {stx.TX_SITE_COLLECTION_KV:g} kV, one per container "
                    f"({cl.FC_UNIT_KVA / 1000:g} MVA per {fcl.FC_KW_PER_CONTAINER / 1000:g} MW)",
                    1.0 / (d_fc["bop_duty_lifetime_hours"] * 1000.0), "MW of step-up per kWh AC over the BoP's life",
                    tx_fc_per_kwh,
                    f"one MW of container step-up per MW of fuel cell, over the BoP's "
                    f"{tech.fc_bop_calendar_years:g}-year calendar life and {d_fc['bop_duty_lifetime_hours']:,.0f} "
                    "running hours",
                    f"gwp_tx_fc_per_mw × cap_fc — LP term '{T_TX_FC}'",
                    f"no-load {pc(lfc['noload_mw_per_mw'], 3)} of cap_fc every hour — kept energised on standby "
                    f"(decision, 15 Oct); load {pc(lfc['load_loss_fraction'], 2)} of output "
                    f"(x_eff {lfc['x_eff']:g}, ASSUMED)")
    dc_val = stack_node["exchange"]["contribution"] + loops_val + service_node["exchange"]["contribution"]
    fc_dc_stage = stage(
        "DC electricity from the stack — 1 kWh", dc_val, uf,
        lp="stack and BoP per MW replaced, service per MWh",
        loss=f"net efficiency {fcl.FC_ETA_NET_MEAN:.1%} LHV, lifetime mean (BOL {fcl.FC_ETA_NET_BOL:.0%} × "
             f"degradation {fcl.FC_DEGRADATION_DERATE}); parasitic loads of the loops are inside it",
        children=[
            stack_node,
            part("Balance of plant — air, water, heat and fuel loops, controller, wiring, frame, container",
                 loops_val, uf, grade="derived", children=loops,
                 lp=f"gwp_fc_bop_per_mw × fc_bop_units — LP term '{T_FC_BOP}'",
                 stands_for=stands(R.FUEL_CELL_DB, R.FC_BOP, "1 kW of balance of plant, shown per kWh AC over its 80,000 h"),
                 source="Usai et al. 2021 SI Table 1 process loops; Jasper 2026 container at one per MW (ASSUMED)"),
            service_node,
            node(f"Stack sensitivity: gramc_2025 — {d_fc['stack_kgco2e_per_MW_gramc_2025']:,.0f} kg/MW against "
                 f"Babatunde's {d_fc['stack_kgco2e_per_MW']:,.0f}", "group",
                 children=[fg(R.FC_STACK_GRAMC, R.FUEL_CELL_DB)]),
        ])
    fc_fu = fu(
        "Fuel cell — 1 kWh AC at the bus, fuel excluded",
        (d_fc["_foreground_total_per_kWh"] - d_fc["_per_kwh"]["fuel"]) * 1000.0 + tx_fc_per_kwh, uf,
        lp="gwp_fc_stack_per_mw × fc_stack_units + gwp_fc_bop_per_mw × fc_bop_units + gwp_fc_maint_per_mwh × p_fc "
           "+ gwp_tx_fc_per_mw × cap_fc",
        lp_terms=[(f"Stack, per kWh at {d_fc['stack_lifetime_hours']:,.0f} h", d_fc["_per_kwh"]["stack"] * 1000,
                   T_FC_STACK),
                  (f"Balance of plant, per kWh at {d_fc['bop_duty_lifetime_hours']:,.0f} h", d_fc["_per_kwh"]["bop"] * 1000,
                   T_FC_BOP),
                  ("Service, per kWh", d_fc["_per_kwh"]["maint"] * 1000, "Fuel cell service"),
                  (f"Step-up transformer, per kWh at the BoP's {d_fc['bop_duty_lifetime_hours']:,.0f} h",
                   tx_fc_per_kwh, T_TX_FC)],
        module="optimisation/fuel_cell.py", grade="assumed",
        source="Babatunde et al. 2024 stack (default); Usai et al. 2021 BoP + 500 kW inverter + container; "
               "calendar lives 10 y stack / 20 y BoP ASSUMED",
        note="The inventory's own functional unit (pemfc_op_1kwh_h2) without its hydrogen: the fuel's carbon "
             "is whatever filled the tank. In the LP, stack and BoP are charged per MW replaced on "
             "max(calendar, running hours), so a backup unit running 200 h a year is not charged as if it ran 30,000.",
        gap_keys=("fuel cell",), todo_keys=("fuel cell",), test_keys=("fuel_cell", "fc_"),
        source_titles=("PEM fuel cell",),
        stands_for=stands(R.FUEL_CELL_DB, R.FC_OP, "the inventory's own functional unit, with its hydrogen taken out"),
        children=[
            fc_tx, inv_node, fc_dc_stage,
            node(f"Fuel excluded: {d_fc['h2_kg_per_MWh']:.1f} kg H₂ per MWh", "note", status="option",
                 note="h2_fc[t] drains the tank; its carbon was charged when it was made or bought."),
            node(f"Lives: stack {tech.fc_stack_calendar_years:g} y / {tech.fc_stack_duty_hours:,.0f} h; "
                 f"BoP {tech.fc_bop_calendar_years:g} y / {tech.fc_bop_duty_hours:,.0f} h", "note", grade="assumed"),
        ])

    # ---- tank ------------------------------------------------------------------
    tank_node = F.activity_node(R.H2_STORAGE_DB, R.H2_TANK)
    life_t = float(cfg.TANK_LIFETIME_YEARS)
    ut = "kg CO₂e per kg of capacity per year"
    tank_items = [rescaled(c, 1.0 / life_t, ut, note=f"the vessel over {life_t:.0f} years") for c in tank_node["children"]]
    tank_fu = fu(
        "Hydrogen tank — 1 kg of H₂ storage capacity for one year", tech.gwp_tank, ut,
        lp="gwp_tank × cap_tank", lp_terms=[("Hydrogen tank (Gandiglio 28 bar vessel)", tech.gwp_tank,
                                              "Hydrogen tank (Gandiglio 28 bar vessel)")],
        module="optimisation/h2_storage.py", grade="transcribed",
        source=f"Gandiglio et al. 2022 Table 3 (15,652 kg stainless, 21.6 m³, 28 bar); frame and pad from first "
               f"principles (ASSUMED); {life_t:.0f} y",
        gap_keys=("tank",), todo_keys=("tank",), test_keys=("tank", "storage"), source_titles=("Hydrogen storage",),
        stands_for=stands(R.H2_STORAGE_DB, R.H2_TANK, "per kg of capacity: the vessel, frame and pad below, over the tank's life"),
        children=tank_items + [
            node(f"Leakage: {h2s.LEAKAGE_FRAC_PER_HOUR:g} per hour by default (swept); leaked H₂ charged at GWP100 "
                 f"{M.H2_GWP100}", "note", grade="assumed", gaps=gap_ids("leakage"),
                 lp="tank_leakage × dt × stock × gwp_h2_leaked — LP term 'Hydrogen leaked from the tank'")])

    # ---- bought hydrogen ---------------------------------------------------------
    colour_act = {"grey": R.SMR, "blue": R.SMR_CCS, "turquoise": R.MP_E}
    h2_fus = []
    for c in ("grey", "blue", "turquoise", "green"):
        t = colours[c]
        comp = hp.bought_h2_compression_kgco2e_per_kg(c)
        comp_part = part(f"Compression onto a tube trailer, to {hp.BOUGHT_H2_TRAILER_PRESSURE_BAR:g} bar", comp, uh,
                         grade="derived", source=f"{hp.bought_h2_compression_kwh_per_kg(c):.2f} kWh/kg × "
                         f"{hp.bought_h2_compression_gco2e_per_kwh(c):.1f} g/kWh (h2_prices.bought_h2_compression_*)",
                         gaps=("outlet pressure", "loading compressor"))
        if c in colour_act:
            prod = fgn(colour_act[c], R.HYDROGEN_DB, {"amount": 1.0, "unit": "kg H₂ at the seller's gate",
                                                      "contribution": t.bought_h2_gwp_per_kg - comp,
                                                      "note": "production, on the study's GB grid"})
            kids = [prod, comp_part]
        else:
            row = pem
            I_g = hp.green_h2_electricity_gco2e_per_kwh(None, grid_share=None)
            op_g = F.activity_node(R.HYDROGEN_DB, R.PEM_OP)
            kids = [part("Seller's PEM plant and consumables, electricity excluded",
                         row["foreground_fixed_kgco2e_per_kg"], uh, grade="derived",
                         source="Hermesmann & Müller 2022 PEM operation with its electricity taken out (the next box)",
                         children=[reid(_copy.deepcopy(c)) for c in op_g["children"]
                                   if "electricity" not in c["name"].lower()]),
                    part(f"{row['kwh_per_kg']:g} kWh of renewable electricity at {I_g:.2f} g/kWh "
                         f"({hp.GREEN_H2_ELECTRICITY_BASIS}, grid share {hp.GREEN_H2_GRID_SHARE} delivered at HV)",
                         row["kwh_per_kg"] * I_g / 1000.0, uh, grade="assumed",
                         source="h2_prices.GREEN_H2_ELECTRICITY_BASES; grid share ASSUMED",
                         children=[node(f"{k}: {v['gco2e_per_kwh']:.2f} g/kWh — {v['label']}", "note",
                                        grade=v["grade"], note=v["note"])
                                   for k, v in hp.GREEN_H2_ELECTRICITY_BASES.items()]),
                    comp_part]
        name = f"{c.title()}: {t.bought_h2_gwp_per_kg:.2f} kg CO₂e/kg delivered, £{t.bought_h2_gbp_per_kg:.2f}/kg"
        h2_fus.append(fu(f"Bought {c} hydrogen — 1 kg delivered to the tank", t.bought_h2_gwp_per_kg, uh,
                         lp=f"bought_h2_gwp_per_kg × h2_buy[t] — LP term '{name}'",
                         lp_terms=[(name, t.bought_h2_gwp_per_kg, name)], module="optimisation/h2_prices.py",
                         source="Hermesmann & Müller 2022 routes on ecoinvent 3.9.1; fossil routes on the study's GB "
                                "grid (gb_grid.py), gas carbon balance closed",
                         gap_keys=("bought", "h2 price", "turquoise", "co2 transport", "green h"),
                         children=kids))
    h2_group = node("Bought hydrogen — 1 kg delivered to the tank, by colour", "group", children=h2_fus)

    # ---- the facility --------------------------------------------------------------
    dcc = I.data_centre_coefficients()
    facility_fu = fu(
        "The facility — one year at 100 MW IT", tech.dc_fixed_gwp_per_year,
        f"kg CO₂e per year, IT-driven; plus {tech.dc_other_gwp_per_mwh:.3f} kg per MWh delivered",
        lp="dc_fixed + dc_other × demand — constant across options", additive=False,
        lp_terms=[(T_DC_IT, tech.dc_fixed_gwp_per_year, T_DC_IT)],
        module="optimisation/baseline_grid.py", grade="transcribed",
        source="Zhang et al. 2025, Cleaner Energy Systems 12:100223, Table 1/S1; split by driver: IT capacity / "
               "delivered energy / standby genset (excluded)",
        gap_keys=("data centre", "facility"), test_keys=("facility", "data_centre", "refrigerant"),
        source_titles=("Baseline 1",),
        children=[
            node(f"IT-driven {dcc['it_kgco2e_per_mw_it_year'] / 1000:,.1f} t per MW IT per year; energy-driven "
                 f"{dcc['energy_kgco2e_per_mwh']:.3f} kg/MWh; genset {dcc['backup_kgco2e_per_year_excluded'] / 1000:,.1f} "
                 "t/yr excluded", "note", grade="derived"),
            part("Energy-driven: cooling consumables and the like, per MWh delivered", tech.dc_other_gwp_per_mwh,
                 "kg CO₂e per MWh delivered", grade="transcribed",
                 lp="dc_other_gwp_per_mwh × Σ demand — a constant: the LP's demand is fixed (dc_model.objective_constants)",
                 source="Zhang et al. 2025, the energy-driven items of Table 1/S1 (dc_inputs.data_centre_coefficients)"),
            fg(R.DATA_CENTRE, R.DATA_CENTRE_DB)])

    lca = node("The LCA — functional units by technology, delivered at the 20 kV site bus", "group",
               note="Each technology is one functional unit, nested stage by stage down the power chain: the "
                    "step-up or intake that delivers at the bus, the conversion behind it, the resource. "
                    "Every stage says which LP term charges it.",
               children=[wind_fu, solar_fu, grid_fu, batt_fu, ely_group, tank_fu, fc_fu, h2_group,
                         facility_fu])

    # ---------------------------------------------------------------- how the LP organises it
    def lp_term(name, symbol, value, unit, targets, *, module, grade, source=None, note=None,
                gap_keys=(), test_keys=(), extra=(), key=None, constant=None):
        return term(name, symbol, value, unit, module=module, grade=grade, source=source, note=note,
                    gap_keys=gap_keys, test_keys=test_keys, key=key, constant=constant,
                    children=[jump(t, "Where this term's numbers come from in the LCA.") for t in targets]
                    + list(extra))

    cap_terms = node("Charged per unit of capacity built", "group", children=[
        lp_term(T_WIND, "gwp_wind × cap_wind", tech.gwp_wind, "kg CO₂e per MW per year",
                [wind_fu["name"]], key="wind", module="optimisation/renewables.py", grade="derived", gap_keys=("wind",)),
        lp_term(T_SOLAR, "gwp_solar × cap_solar", tech.gwp_solar, us,
                [solar_fu["name"]], key="solar", module="optimisation/renewables.py", grade="derived",
                gap_keys=("solar", "pv ")),
        node("Offshore wind: not in the study", "note", status="not", grade="derived",
             note="A term exists in the LP (gwp_offshore × cap_offshore) but dc_architectures.OFFSHORE_IN_SCOPE "
                  "is False, so cap_offshore is locked at zero: every site is on land, and there is no offshore "
                  "profile. Not shown in the LCA."),
        lp_term(T_TX_WIND, "gwp_tx_wind_per_mw × (cap_wind + cap_offshore)", tech.gwp_tx_wind_per_mw,
                "kg CO₂e per MW per year", [wind_fu["name"]], key="wind step-up transformers",
                module="optimisation/transformers.py", grade="derived",
                note="Its own term rather than folded into the turbine, so the audit can check the transformer's "
                     "life against its generator; on the same capacity variable as the turbine.",
                gap_keys=("transformer",), test_keys=("transformer", "step")),
        lp_term(T_TX_SOLAR, "gwp_tx_solar_per_mwp × cap_solar", tech.gwp_tx_solar_per_mwp,
                "kg CO₂e per MWp per year", [solar_fu["name"]], key="solar step-up transformers",
                module="optimisation/transformers.py", grade="derived",
                note="Per MWp against an AC-rated asset: the coefficient already carries the DC:AC ratio.",
                gap_keys=("transformer",), test_keys=("transformer", "step")),
        lp_term(T_TX_BATT, "gwp_tx_batt_per_mw × cap_batt_p", tech.gwp_tx_batt_per_mw,
                "kg CO₂e per MW of PCS per year (over the battery's 15 y)", [batt_fu["name"]],
                key="battery step-up transformers", module="optimisation/transformers.py", grade="derived",
                note="Jasper 2026's 5,500 kg container transformer on the IEA PVPS composition. Closed as "
                     "negligible on 4 Sep, modelled on 15 Oct: with the inventory and loss model in place, "
                     "leaving it out was a one-way bias against the generation chains.",
                gap_keys=("balance of plant",), test_keys=("transformer", "container")),
        lp_term(T_TX_FC, "gwp_tx_fc_per_mw × cap_fc", tech.gwp_tx_fc_per_mw,
                "kg CO₂e per MW of fuel cell per year (over the BoP calendar life)", [fc_fu["name"]],
                key="fuel cell step-up transformers", module="optimisation/transformers.py", grade="derived",
                note="The same container unit as the battery's, one per FC_KW_PER_CONTAINER. Its no-load loss "
                     "is drawn every hour because a standby unit's transformer stays energised (decision, 15 Oct).",
                gap_keys=("balance of plant",), test_keys=("transformer", "container")),
        lp_term(T_GRID_CONN, "gwp_grid_per_mw × cap_grid", tech.gwp_grid_per_mw,
                "kg CO₂e per MW per year", [grid_fu["name"]], key="grid connection",
                module="optimisation/grid_connection.py", grade="derived",
                gap_keys=("grid-intake", "transmission connection"), test_keys=("connection",)),
        lp_term(T_BATT_E, "gwp_batt_e × cap_batt_e", tech.gwp_batt_e, "kg CO₂e per usable MWh of capacity per year",
                [batt_fu["name"]], key="battery cells and container",
                module="optimisation/battery.py", grade="derived", gap_keys=("battery",), test_keys=("batt", "bess")),
        lp_term(T_BATT_P, "gwp_batt_p × cap_batt_p", tech.gwp_batt_p, "kg CO₂e per MW per year",
                [batt_fu["name"]], key="battery power conversion",
                module="optimisation/battery.py", grade="derived", gap_keys=("battery",), test_keys=("batt", "bess")),
        lp_term(T_ELY, "gwp_ely × cap_ely", tech.gwp_ely,
                "kg CO₂e per MW per year (PEM shown)", [f["name"] for f in ely_fus], key="electrolyser",
                module="optimisation/electrolysers.py", grade="derived",
                gap_keys=("electrolyser", "soec", "alkaline"), test_keys=("electrolyser",)),
        lp_term(T_TANK, "gwp_tank × cap_tank", tech.gwp_tank, ut, [tank_fu["name"]], key="H2 tank",
                module="optimisation/h2_storage.py", grade="transcribed", gap_keys=("tank",), test_keys=("tank", "storage")),
        lp_term(T_FC_STACK, "gwp_fc_stack_per_mw × fc_stack_units", tech.gwp_fc_stack_per_mw,
                "kg CO₂e per MW of stack replaced", [fc_fu["name"]], key="fuel cell stack replacements",
                module="optimisation/fuel_cell.py", grade="assumed", gap_keys=("fuel cell",),
                test_keys=("fuel_cell", "fc_"), note=fc.REPLACEMENT_LP_NOTE),
        lp_term(T_FC_BOP, "gwp_fc_bop_per_mw × fc_bop_units", tech.gwp_fc_bop_per_mw,
                "kg CO₂e per MW of balance of plant replaced", [fc_fu["name"]], key="fuel cell BoP replacements",
                module="optimisation/fuel_cell.py", grade="assumed", gap_keys=("fuel cell", "balance of plant"),
                test_keys=("fuel_cell", "fc_"), note=fc.REPLACEMENT_LP_NOTE),
    ])
    colour_terms = [lp_term(f["parts"][0][0], "bought_h2_gwp_per_kg × h2_buy", f["value"], uh, [f["name"]],
                            key=f"bought H2 ({c})", module="optimisation/h2_prices.py", grade="derived")
                    for c, f in zip(("grey", "blue", "turquoise", "green"), h2_fus)]
    flow_terms = node("Charged per unit of flow", "group", children=[
        lp_term(T_IMPORT, "Σ ci[t] × imp[t]", deliv_mean,
                "g CO₂e per kWh delivered at HV (London 2025 mean)", [grid_fu["name"]], key="grid import",
                module="optimisation/grid_build.py", grade="derived", gap_keys=("grid", "import"), test_keys=("grid",),
                extra=[node(f"Site intake transformer losses: {lgrid['load_loss_fraction']:.3%} of imports + "
                            f"{lgrid['noload_mw_per_mw']:.4%} of the connection, no-load", "note", grade="derived",
                            source=cl.SOURCE)]),
        node(T_BOUGHT, "group",
             module="optimisation/h2_prices.py", children=colour_terms,
             gaps=gap_ids("bought", "loading compressor", "outlet pressure", "co2 transport", "green h"),
             tests=tests_for("bought", "compression", "gas_routes")),
        lp_term(T_ELY_CONS, "ely_variable_gwp_per_kg × kg made", tech.ely_variable_gwp_per_kg,
                "kg CO₂e per kg H₂ made (PEM shown)", [f["name"] for f in ely_fus], key="electrolyser consumables",
                module="optimisation/electrolysers.py", grade="derived", gap_keys=("consumables",),
                test_keys=("consumable", "soec")),
        lp_term(T_FC_MAINT, "gwp_fc_maint_per_mwh × MWh", tech.gwp_fc_maint_per_mwh, "kg CO₂e per MWh delivered",
                [fc_fu["name"]], key="fuel cell maintenance", module="optimisation/fuel_cell.py", grade="assumed"),
        lp_term(T_LEAK, "tank_leakage × dt × stock × GWP", M.H2_GWP100, "kg CO₂e per kg H₂ leaked",
                [tank_fu["name"]], key="H2 leaked from tank", module="optimisation/dc_model.py", grade="transcribed",
                source=M.H2_GWP100_SOURCE + "; not characterised in IPCC 2021 as implemented — a stated extension",
                gap_keys=("leakage",), test_keys=("leak",)),
        lp_term(T_VOLL, "VOLL_KGCO2E_PER_MWH × unserved", M.VOLL_KGCO2E_PER_MWH,
                "kg CO₂e per MWh shed", [], key="unserved (VoLL)", module="optimisation/dc_model.py", grade="assumed",
                source=f"VoLL £{M.VOLL_GBP_PER_MWH:,.0f}/MWh at FES 2025 CP2 £{M.VOLL_CARBON_PRICE_GBP_PER_T}/t; "
                       "reported totals carry it, intensities do not", test_keys=("unserved", "voll", "shed")),
    ])
    facility_term = node("The facility — constants no decision moves (dc_model.objective_constants; reported as "
                         "contributions()['gwp_facility'])", "group", children=[
        lp_term(T_DC_IT, "dc_fixed_gwp_per_year", tech.dc_fixed_gwp_per_year,
                "kg CO₂e per year at 100 MW IT", [facility_fu["name"]], key="data centre, IT capacity", constant=True,
                module="optimisation/baseline_grid.py", grade="transcribed"),
        lp_term(T_DC_ENERGY, "dc_other_gwp_per_mwh × Σ demand", tech.dc_other_gwp_per_mwh,
                "kg CO₂e per MWh delivered", [facility_fu["name"]], key="data centre, cooling consumables",
                constant=True, module="optimisation/baseline_grid.py", grade="transcribed",
                note="Demand is fixed in the LP, so this is a constant too: the per-MWh part of the facility."),
    ])
    energy_only = node("Energy terms with no coefficient of their own (they move how much is built)", "group",
                       children=[
        node("Transformer conversion losses (Reg. (EU) 548/2014 Tier 2)", "term", grade="transcribed",
             module="optimisation/conversion_losses.py", source=cl.SOURCE,
             module_doc=odoc["conversion_losses"], children=[
                 node(f"Wind step-up: no-load {lw['noload_mw_per_mw']:.4%} of capacity; load "
                      f"{lw['load_loss_per_mw_at_full_loading']:.3%} at full loading", "note", grade="derived"),
                 node(f"Solar step-up: no-load {ls['noload_mw_per_mw']:.4%}; load "
                      f"{ls['load_loss_per_mw_at_full_loading']:.3%}", "note", grade="derived"),
                 node(f"Grid intake: no-load {lgrid['noload_mw_per_mw']:.4%}; load {lgrid['load_loss_fraction']:.3%} "
                      f"(k_PEI {cl.LARGE_TX_K_PEI}, x_eff {cl.GRID_INTAKE_X_EFF} ASSUMED)", "note", grade="assumed")]),
        node(f"Wind gross → net factor {profiles.WIND_NET_FACTOR:.3f}", "term", grade="derived",
             module="optimisation/profiles.py", gaps=gap_ids("wind life extension")),
        node("Storage standing losses (battery, tank) — zero by default, swept", "term", grade="assumed",
             gaps=gap_ids("standing loss", "leakage")),
        node("Electrolyser and tank compression electricity", "term", grade="derived",
             module="optimisation/h2_storage.py",
             note="Charged as site electricity; its carbon is whatever the LP supplies it with."),
        node(f"PUE: demand = IT × PUE; default {cfg.DC_REFERENCE_PUE} (Zhang's)", "term", grade="transcribed"),
    ])
    objective = node("How the LP organises it — the carbon objective (dc_model.objective_terms)", "group",
                     symbol="minimise Σ gwp", module="optimisation/dc_model.py", module_doc=odoc["dc_model"],
                     note="The LP is an organising framework over the LCA above: it charges each functional unit's "
                          "parts separately, by what each scales with — capacity built, or energy and hydrogen "
                          "flowing — so the optimiser can size and dispatch. Every term here points at the chain "
                          "its numbers come from. The sum over a solved year is the carbon objective.",
                     children=[cap_terms, flow_terms, facility_term, energy_only])

    # ---------------------------------------------------------------- foreground index
    fg_index = node("Every foreground database (optimiser_lca/)", "group", children=[
        node(f"{db} — {F.invs[db][0]}.py", "group", module=f"optimiser_lca/{F.invs[db][0]}.py",
             source=first_para(F.docs.get(F.invs[db][0])), module_doc=F.docs.get(F.invs[db][0]),
             children=[node(f"{a.name}", "pointer", code=a.code, database=db,
                            score_per_unit=S.score(F.bw(db, a.code)), unit=a.unit)
                       for a in F.invs[db][1].activities])
        for db in R.DATABASES])

    # ---------------------------------------------------------------- gap register
    status_label = {"closed": "Closed", "open-source-known": "Open — public source identified",
                    "open-no-source": "Open — no public source", "confirmed-absent": "Checked and confirmed absent",
                    "not-applicable": "Not applicable"}
    gap_groups = []
    for st, label in status_label.items():
        rows = [g for g in gaps if g["status"] == st]
        gap_groups.append(node(f"{label} ({len(rows)})", "group", status=st, children=[
            node(g["name"], "gap", gap_id=g["id"], status=st, section=g["section"],
                 cells=g["cells"]) for g in rows]))
    todo_groups = []
    for sec in dict.fromkeys(t["section"] for t in todo):
        todo_groups.append(node(sec, "group", children=[
            node(t["name"], "todo", note=t["body"]) for t in todo if t["section"] == sec]))
    register = node("Data gaps and worklist", "group", children=[
        node("DATA_GAPS.md — the register", "group", children=gap_groups),
        node("TODO.md — the worklist (open items)", "group", children=todo_groups)])

    root = node("UK data-centre power optimiser — LCA", "root",
                note="IPCC 2021 GWP100 · ecoinvent 3.9.1 apos · London reference site, 100 MW IT, "
                     "central cost case · generated " + time.strftime("%Y-%m-%d %H:%M"),
                children=[method, lca, objective, fg_index, register])
    out = {"tree": root, "gaps": {g["id"]: g for g in gaps},
           "meta": {"activities_scored": len(S.cache), "seconds": round(time.time() - t0),
                    "generated": time.strftime("%Y-%m-%d %H:%M"),
                    "grid_sources_id": G.sources_id(), "gb_grid_gco2e": gb_grid.GB_GRID_2025_HV_GCO2E_PER_KWH}}
    return out


HTML_TEMPLATE = Path(__file__).with_name("lca_map_template.html")
HTML_OUT = ROOT / "optimisation_outputs" / "lca_map.html"


def write_html(blob: str) -> Path:
    """The interactive page: the template with the map inlined (``</`` escaped
    so no string in the data can close the script tag)."""
    page = HTML_TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", blob.replace("</", "<\\/"))
    HTML_OUT.write_text(page, encoding="utf-8")
    return HTML_OUT


def add_energy(out: dict) -> dict:
    """The energy-flow tab (scripts/energy_map.py). No Brightway, so rebuilt every run."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from energy_map import energy_section
    gaps = parse_data_gaps()

    def gap_ids(*keys):
        ks = [k.lower() for k in keys]
        return [g["id"] for g in gaps if any(k in g["name"].lower() for k in ks)]

    out["energy"] = energy_section(gap_ids)
    return out


if __name__ == "__main__":
    if "--html-only" in sys.argv:          # re-wrap an existing map, no Brightway
        out = json.loads(OUT.read_text(encoding="utf-8"))
    else:
        out = build()
        print(f"built the tree: {out['meta']['activities_scored']} activities scored in "
              f"{out['meta']['seconds']} s")
    out = add_energy(out)
    blob = json.dumps(out, default=lambda o: float(o) if hasattr(o, "__float__") else str(o))
    OUT.write_text(blob, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1e6:.2f} MB")
    page = write_html(blob)
    print(f"wrote {page.relative_to(ROOT)}: {page.stat().st_size / 1e6:.2f} MB")
