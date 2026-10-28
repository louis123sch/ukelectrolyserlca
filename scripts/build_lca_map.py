#!/usr/bin/env python
"""Build the LCA map from the model itself: nothing in it is written by hand.

    python scripts/build_lca_map.py              # map JSON + optimisation_outputs/lca_map.html
    python scripts/build_lca_map.py --html-only  # re-wrap the page around the last map

The map is a graph, one box per thing, assembled from three readings of the code:

1. **The LP's terms.** ``dc_model.objective_terms`` and ``facility_terms`` are
   evaluated on symbols instead of numbers, so each term's expression and the
   ``Tech`` coefficients it multiplies are read from the function the LP is
   built with. ``dc_model.CHAINS`` groups them by technology.
2. **How each coefficient is made.** ``build_tech`` (and the grid series) run
   inside ``optimisation.trace.recording()``. Every ``T.step`` the coefficient
   modules call is a box: its value, unit, grade, what it used, and the file,
   line and expression that computed it.
3. **The inventories.** Every activity of every foreground database, with
   every exchange, read from Brightway; every ecoinvent dataset they touch,
   scored, with its direct inputs one level down. All scores come from one
   sparse solve over the whole technosphere (IPCC 2021 GWP100, the study's
   method).

Variants the LP can be run on (the other bought-hydrogen colours, AE and SOEC)
are recorded too; a step whose number differs in a variant gets its own box,
labelled with the variant.

The build refuses to write a map that disagrees with the model: a coefficient
the trace does not reach, a link to nothing, a pinned figure that has drifted
from its activity's score, a foreground exchange not drawn. ``check_lca_map.py``
re-reads the written map for the same things, without Brightway.
"""
from __future__ import annotations

import ast
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

OUT = ROOT / "optimisation_outputs" / "lca_map.json"
HTML_TEMPLATE = Path(__file__).with_name("lca_map_template.html")
HTML_OUT = ROOT / "optimisation_outputs" / "lca_map.html"

# The run the map shows: the London site over the 2025 window the grid series
# is cached for, a 100 MW IT facility, green hydrogen bought, PEM electrolysis.
SITE, START, END, SIZE_MW_IT = "london", "2025-01-01", "2025-12-29", 100.0
MAIN = {"h2_colour": "green"}
VARIANTS = [("grey hydrogen", {"h2_colour": "grey"}), ("blue hydrogen", {"h2_colour": "blue"}),
            ("turquoise hydrogen", {"h2_colour": "turquoise"}),
            ("AE electrolyser", {"h2_colour": "green", "ely_tech": "AE operation"}),
            ("SOEC electrolyser", {"h2_colour": "green", "ely_tech": "SOEC operation"})]
META_CHARGES = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}
DRILL_BIOSPHERE_ZERO_CF = False      # ecoinvent drill: uncharacterised flows are counted, not drawn


# =============================================================================
# Registers read for the panel: DATA_GAPS.md, ASSUMPTIONS.md
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
                     "status": status_of.get(section, "other"), "cells": cells[1:]})
    return rows


def parse_md_sections(path: Path, levels=("## ", "### ")):
    out, title, buf = {}, None, []
    for line in path.read_text(encoding="utf-8").splitlines():
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


def module_doc(path: Path) -> str:
    try:
        return ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
    except Exception:                                   # noqa: BLE001
        return ""


def first_para(doc: str) -> str:
    """The opening of a module docstring, without its underline rules."""
    lines = [ln for ln in (doc or "").splitlines() if not ln.strip() or not set(ln.strip()) <= set("=-~")]
    paras = [p.strip() for p in "\n".join(lines).strip().split("\n\n") if p.strip()]
    return "\n\n".join(paras[:2])


def grade_from(*texts, default="transcribed"):
    """A grade for an inventory activity or exchange, from the words its author used."""
    t = " ".join(x for x in texts if x).lower()
    if "assumed" in t:
        return "assumed"
    if "proxy" in t or "stands in" in t or "stand-in" in t:
        return "proxy"
    if "derived" in t or "computed" in t or "interpolat" in t:
        return "derived"
    return default


# =============================================================================
# 1. The LP's terms, read by evaluating its own functions on symbols
# =============================================================================
class Sym:
    """A symbolic number: remembers the expression and the names inside it."""
    __array_priority__ = 1000

    def __init__(self, text, names=(), prec=9):
        self.text, self.names, self.prec = text, frozenset(names), prec

    @staticmethod
    def of(x):
        return x if isinstance(x, Sym) else Sym(f"{float(x):.6g}")

    def _wrap(self, prec):
        return f"({self.text})" if self.prec < prec else self.text

    def _bin(self, other, op, prec, rev=False):
        a, b = (Sym.of(other), self) if rev else (self, Sym.of(other))
        right_prec = prec + (1 if op in ("−", "/") else 0)
        return Sym(f"{a._wrap(prec)} {op} {b._wrap(right_prec)}", a.names | b.names, prec)

    def __add__(self, o): return self._bin(o, "+", 5)
    def __radd__(self, o): return self if o == 0 else self._bin(o, "+", 5, rev=True)
    def __sub__(self, o): return self._bin(o, "−", 5)
    def __rsub__(self, o): return self._bin(o, "−", 5, rev=True)
    def __mul__(self, o): return self._bin(o, "×", 7)
    def __rmul__(self, o): return self._bin(o, "×", 7, rev=True)
    def __truediv__(self, o): return self._bin(o, "/", 7)
    def __rtruediv__(self, o): return self._bin(o, "/", 7, rev=True)
    def __neg__(self): return Sym(f"−{self._wrap(8)}", self.names, 8)

    def sum(self):
        return Sym(f"Σₜ[{self.text}]", self.names, 9)


class Quantities(dict):
    """The LP's variables, as symbols, for whatever name objective_terms asks for."""
    def __missing__(self, k):
        self[k] = Sym(k, {("var", k)})
        return self[k]

    def get(self, k, default=None):
        return self[k]


def term_table(tech):
    """{term key: {side, expr, fields, vars, series}}, read from dc_model's own term functions."""
    from optimisation import dc_model as M
    coef = {f.name: Sym(f.name, {("coef", f.name)}) for f in dataclasses.fields(tech) if f.name != "labels"}
    sym_tech = dataclasses.replace(tech, **coef)
    series = SimpleNamespace(dt_hours=Sym("Δt", {("series", "dt")}),
                             annual_scale=Sym("annual_scale", {("series", "annual_scale")}))
    terms = M.objective_terms(Quantities(), series, sym_tech,
                              price=Sym("price", {("series", "price")}),
                              ci=Sym("ci", {("series", "ci")}))
    groups = [(side, terms[side]) for side in ("gwp_embodied", "gwp_operational")]
    groups.append(("gwp_facility", M.facility_terms(sym_tech, Sym("demand_MWh", {("series", "demand_MWh")}))))
    out = {}
    for side, d in groups:
        for k, s in d.items():
            s = Sym.of(s)
            out[k] = {"side": side, "expr": s.text,
                      "fields": sorted(n for kind, n in s.names if kind == "coef"),
                      "vars": sorted(n for kind, n in s.names if kind == "var"),
                      "series": sorted(n for kind, n in s.names if kind == "series")}
    return out


def chain_of(key):
    from optimisation import dc_model as M
    for chain, keys in M.CHAINS.items():
        if key in keys:
            return chain
    for chain, prefix in M.CHAIN_PREFIXES.items():
        if key.startswith(prefix):
            return chain
    if key.startswith("data centre"):
        return "facility"
    return None


def field_default_where(field):
    """file:line of a Tech field's default in dc_model.py, for an untraced constant."""
    path = ROOT / "optimisation" / "dc_model.py"
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(rf"\s+{re.escape(field)}\s*:", line):
            return f"optimisation/dc_model.py:{i}", line.strip()
    return "optimisation/dc_model.py", ""


# =============================================================================
# 2. The trace, main run and variants merged
# =============================================================================
def record():
    from optimisation import dc_inputs as I, trace as T
    with T.recording() as rec:
        tech = I.build_tech(SITE, META_CHARGES, **MAIN)
        I.build_series(SITE, START, END, SIZE_MW_IT)
    runs = [("", rec, tech)]
    for label, kw in VARIANTS:
        with T.recording() as r:
            t = I.build_tech(SITE, META_CHARGES, **kw)
        runs.append((label, r, t))
    return runs


def merge(runs):
    """One step table: the main run's keys, and a variant's step under
    ``key [variant]`` wherever its number, or anything below it, differs."""
    from optimisation.trace import _same
    _label, main, _t = runs[0]
    steps = {k: s.as_dict() for k, s in main.steps.items()}
    problems = [f"trace: {k} recorded with two values in the main run" for k in main.conflicts]
    renames = [{k: k for k in main.steps}]
    for label, rec, _t in runs[1:]:
        problems += [f"trace: {k} recorded with two values ({label})" for k in rec.conflicts]
        name = {}

        def resolve(k, seen=()):
            if k in name:
                return name[k]
            s = rec.steps.get(k)
            if s is None or k in seen:
                return k
            kids = [resolve(u, seen + (k,)) for u in s.uses if isinstance(u, str)]
            unchanged = all(c == u for c, u in zip(kids, [u for u in s.uses if isinstance(u, str)]))
            if k not in main.steps or (_same(main.steps[k].value, s.value) and unchanged):
                name[k] = k
            else:
                name[k] = f"{k} [{label}]"
            return name[k]

        for k in rec.steps:
            resolve(k)
        for k, s in rec.steps.items():
            nk = name[k]
            if nk in steps:
                continue
            d = s.as_dict()
            d["key"] = nk
            d["uses"] = [name.get(u, u) if isinstance(u, str) else u for u in s.uses]
            if nk != k:
                d["variant"] = label
            steps[nk] = d
        renames.append(name)
    return steps, renames, problems


# =============================================================================
# 3. Brightway: every foreground activity and exchange, every score in one solve
# =============================================================================
class Brightway:
    def __init__(self):
        import bw2data as bd
        import lca_helpers as H
        from optimisation import baseline_grid as bg
        from optimiser_lca import registry as R
        H.setup_brightway()
        self.bd, self.H, self.R = bd, H, R
        self.method = bg.gwp_method()
        self.fg_dbs = [db for db in R.DATABASES if db in bd.databases]
        self.fg_acts = [a for db in self.fg_dbs for a in bd.Database(db)]
        t = time.time()
        import bw2calc as bc
        fu, data_objs, _ = bd.prepare_lca_inputs({a: 1 for a in self.fg_acts}, method=self.method)
        lca = bc.LCA(demand=fu, data_objs=data_objs)
        lca.load_lci_data()
        lca.load_lcia_data()
        self.lca = lca
        self.A = lca.technosphere_matrix.tocsc()
        cb = lca.characterization_matrix @ lca.biosphere_matrix
        g = __import__("numpy").asarray(cb.sum(axis=0)).ravel()
        from scipy.sparse.linalg import spsolve
        self.x = spsolve(self.A.T.tocsc(), g)       # x[product row] = score of one unit
        self.cf = lca.characterization_matrix.diagonal()
        print(f"scored every activity in one solve ({self.A.shape[0]:,} products, {time.time() - t:.0f} s)")
        self.meta = {}

    def score(self, node_id):
        r = self.lca.dicts.product.get(node_id)
        return None if r is None else float(self.x[r])

    def cf_of(self, flow_id):
        r = self.lca.dicts.biosphere.get(flow_id)
        return 0.0 if r is None else float(self.cf[r])

    def load_meta(self, ids):
        from bw2data.backends import ActivityDataset as AD
        need = [i for i in ids if i not in self.meta]
        for k in range(0, len(need), 900):
            for row in AD.select().where(AD.id << need[k:k + 900]):
                d = row.data or {}
                self.meta[row.id] = {"name": row.name, "location": row.location,
                                     "product": row.product, "database": row.database,
                                     "code": row.code, "unit": d.get("unit"),
                                     "categories": d.get("categories"), "type": row.type}

    def resolve(self, ref):
        """A trace reference -> Brightway node id."""
        if "code" in ref:
            return self.bd.get_activity((ref["database"], ref["code"])).id
        name, loc, product = (list(ref["ecoinvent"]) + [None] * 3)[:3]
        return self.H.resolve_exact(name, loc, product, database=ref.get("database")).id

    def column(self, node_id):
        """Direct inputs of an activity from the matrices: [(input id, amount per unit output)]."""
        col = self.lca.dicts.activity[node_id]
        row_self = self.lca.dicts.product[node_id]
        diag = float(self.A[row_self, col])
        a = self.A[:, col]
        rev_p = self.lca.dicts.product.reversed
        tech = [(rev_p[r], -float(v) / diag) for r, v in zip(a.indices, a.data) if r != row_self]
        b = self.lca.biosphere_matrix.tocsc()[:, col]
        rev_b = self.lca.dicts.biosphere.reversed
        bio = [(rev_b[r], float(v) / diag) for r, v in zip(b.indices, b.data)]
        return tech, bio, diag


# =============================================================================
# The graph
# =============================================================================
class Graph:
    def __init__(self):
        self.nodes, self.edges = {}, []

    def add(self, nid, **d):
        if nid not in self.nodes:
            self.nodes[nid] = {k: v for k, v in d.items() if v not in (None, "", [], {})}
        return nid

    def link(self, parent, child, **d):
        self.edges.append([parent, child, {k: v for k, v in d.items() if v not in (None, "")}])


def build():
    from optimisation import dc_architectures, dc_model as M
    from optimiser_lca import build as fg_build, exclusions as X, grid as G
    from lp_terms import KEY_TO_NAME, CONSTANTS
    from map_fingerprint import fingerprint

    t0 = time.time()
    problems = []
    runs = record()
    steps, renames, p = merge(runs)
    problems += p
    BW = Brightway()
    gr = Graph()

    # ---- the inventories, as the modules declare them (for each process's "why")
    module_of = {db: n for n, db in fg_build.MODULES}
    why = {}
    for n, inv in fg_build.inventories():
        for key, proc in inv.processes.items():
            if proc.identity:
                why[(inv.database,) + tuple(proc.identity[:2])] = {
                    "key": key, "why": proc.why, "query": proc.query}
    docs = {n: first_para(module_doc(ROOT / "optimiser_lca" / f"{n}.py")) for n, _ in fg_build.MODULES}

    # ---- Brightway nodes ---------------------------------------------------------
    fg_ids = {a.id for a in BW.fg_acts}
    BW.load_meta(fg_ids)

    def bw_id(node_id):
        return f"bw:{node_id}"

    drilled = set()

    def bw_node(node_id, depth_hint="ref"):
        """Add a Brightway activity; foreground ones open fully, ecoinvent ones one level."""
        nid = bw_id(node_id)
        if nid in gr.nodes:
            return nid
        BW.load_meta([node_id])
        m = BW.meta[node_id]
        if m["database"] in BW.fg_dbs:
            act = BW.bd.get_node(id=node_id)
            mod = module_of.get(m["database"])
            gr.add(nid, kind="foreground", name=m["name"], unit=m["unit"], location=m["location"],
                   product=m["product"], database=m["database"], code=m["code"],
                   module=f"optimiser_lca/{mod}.py" if mod else None, comment=act.get("comment"),
                   source=docs.get(mod), score=BW.score(node_id),
                   grade=grade_from(act.get("comment"), default="transcribed"))
            prod = sum(float(e["amount"]) for e in act.production()) or 1.0
            if prod != 1.0:
                gr.nodes[nid]["production_amount"] = prod
            for e in act.technosphere():
                inp = e.input
                child = bw_node(inp.id)
                amt = float(e["amount"]) / prod
                sc = BW.score(inp.id)
                w = why.get((m["database"], inp["name"], inp.get("location")))
                gr.link(nid, child, amount=amt, unit=e.get("unit") or inp.get("unit"),
                        contribution=None if sc is None else amt * sc, note=e.get("comment"),
                        why=w and w["why"], process_key=w and w["key"])
            for e in act.biosphere():
                fl = e.input
                fid = f"bio:{fl.id}"
                cf = BW.cf_of(fl.id)
                gr.add(fid, kind="biosphere", name=fl["name"], unit=fl.get("unit"),
                       compartment=" / ".join(fl.get("categories") or ()), cf=cf)
                amt = float(e["amount"]) / prod
                gr.link(nid, fid, amount=amt, unit=e.get("unit") or fl.get("unit"),
                        contribution=amt * cf, note=e.get("comment"))
        else:
            gr.add(nid, kind="ecoinvent", name=m["name"], unit=m["unit"], location=m["location"],
                   product=m["product"], database=m["database"], score=BW.score(node_id))
        return nid

    def drill(node_id):
        """One level into an ecoinvent dataset: every direct input, scored."""
        nid = bw_id(node_id)
        if node_id in drilled or gr.nodes[nid]["kind"] != "ecoinvent":
            return
        drilled.add(node_id)
        tech, bio, _diag = BW.column(node_id)
        BW.load_meta([i for i, _ in tech] + [i for i, _ in bio])
        for i, amt in tech:
            m = BW.meta[i]
            cid = bw_id(i)
            if cid not in gr.nodes:
                gr.add(cid, kind="ecoinvent", name=m["name"], unit=m["unit"], location=m["location"],
                       product=m["product"], database=m["database"], score=BW.score(i))
            sc = gr.nodes[cid].get("score")
            gr.link(nid, cid, amount=amt, unit=m["unit"], contribution=None if sc is None else amt * sc)
        uncharacterised = 0
        for i, amt in bio:
            cf = BW.cf_of(i)
            if not cf and not DRILL_BIOSPHERE_ZERO_CF:
                uncharacterised += 1
                continue
            m = BW.meta[i]
            fid = f"bio:{i}"
            gr.add(fid, kind="biosphere", name=m["name"], unit=m["unit"],
                   compartment=" / ".join(m.get("categories") or ()), cf=cf)
            gr.link(nid, fid, amount=amt, unit=m["unit"], contribution=amt * cf)
        gr.nodes[nid]["drilled"] = True
        if uncharacterised:
            gr.nodes[nid]["uncharacterised_flows"] = uncharacterised

    for a in BW.fg_acts:
        bw_node(a.id)
    first_level = [int(n[3:]) for n, d in list(gr.nodes.items())
                   if n.startswith("bw:") and d["kind"] == "ecoinvent"]

    # ---- trace steps ---------------------------------------------------------------
    for k, s in steps.items():
        gr.add(f"step:{k}", kind="step", name=s["title"], key=k, value=s.get("value"), unit=s.get("unit"),
               grade=s.get("grade"), source=s.get("source"), note=s.get("note"), inputs=s.get("inputs"),
               where=s.get("where"), function=s.get("function"), code=s.get("code"),
               variant=s.get("variant"))
    for k, s in steps.items():
        for u in s.get("uses", []):
            if isinstance(u, str):
                if u not in steps:
                    problems.append(f"trace: {k} uses {u!r}, which no step recorded")
                    continue
                gr.link(f"step:{k}", f"step:{u}")
            else:
                try:
                    i = BW.resolve(u)
                except Exception as e:                           # noqa: BLE001
                    problems.append(f"trace: {k} uses {u}, which does not resolve ({e})")
                    continue
                child = bw_node(i)
                if gr.nodes[child]["kind"] == "ecoinvent":
                    first_level.append(i)
                gr.link(f"step:{k}", child)
        if s.get("scores"):
            try:
                i = BW.resolve(s["scores"])
                want = BW.score(i) * s.get("factor", 1.0)
                gr.nodes[f"step:{k}"]["rescored"] = want
                if s.get("value") is not None and abs(want - s["value"]) > 1e-3 * max(abs(want), 1e-12):
                    problems.append(f"pinned figure drifted: {k} = {s['value']:.6g}, "
                                    f"its activity scores {want:.6g}")
            except Exception as e:                               # noqa: BLE001
                problems.append(f"trace: {k} scores {s['scores']}, which does not resolve ({e})")
    for i in sorted(set(first_level)):
        drill(i)

    # ---- the LP's terms --------------------------------------------------------------
    main_tech = runs[0][2]
    tech_fields = {f.name for f in dataclasses.fields(main_tech)}
    added = (main_tech.labels or {}).get("cutoff_added", {})
    terms_seen = {}

    def coefficient_node(field, tech, rename, label):
        """The LP coefficient a term multiplies: its trace step, plus any cut-off
        estimate the register adds on top of it."""
        key = rename.get(f"coefficient.{field}", f"coefficient.{field}")
        value = getattr(tech, field)
        if key not in steps:
            default = next(f.default for f in dataclasses.fields(tech) if f.name == field)
            if default is dataclasses.MISSING or float(value) != float(default):
                problems.append(f"coefficient {field} has no trace step: wrap it in T.step where "
                                "build_tech sets it")
            where, line = field_default_where(field)
            nid = gr.add(f"const:{field}", kind="constant", name=f"{field} (a default in dc_model.Tech)",
                         value=float(value), where=where, code=line, grade="transcribed")
            return nid
        cut = rename.get(f"cutoff.{field}", f"cutoff.{field}")
        lab_added = (tech.labels or {}).get("cutoff_added", {})
        base = steps[key]["value"]
        if field in lab_added:
            nid = f"lp:{field}" + (f" [{label}]" if label and key.endswith("]") else "")
            gr.add(nid, kind="coefficient", name=f"{field}: the coefficient with its cut-off estimates",
                   value=float(value), unit=steps[key].get("unit"), grade="derived")
            gr.link(nid, f"step:{key}")
            if cut in steps:
                gr.link(nid, f"step:{cut}")
            total = base + (steps[cut]["value"] if cut in steps else 0.0)
        else:
            nid, total = f"step:{key}", base
        if abs(total - float(value)) > 1e-9 * max(1.0, abs(float(value))):
            problems.append(f"coefficient {field}{' [' + label + ']' if label else ''}: the trace gives "
                            f"{total:.9g}, build_tech gives {float(value):.9g}")
        return nid

    study = gr.add("study", kind="study", name="The study: carbon of a year of data-centre demand served",
                   note="IPCC 2021 GWP100 with long-term emissions, ecoinvent 3.9.1 apos background. "
                        f"Shown for {SITE}, {START} to {END}, {SIZE_MW_IT:g} MW IT.")
    lp_root = gr.add("lp", kind="group", name="The LP's carbon objective, by technology",
                     note="Terms read from dc_model.objective_terms and facility_terms; grouped by "
                          "dc_model.CHAINS.")
    gr.link(study, lp_root)
    chain_nodes = {}

    for (label, _rec, tech), rename in zip(runs, renames):
        for key, t in term_table(tech).items():
            uses = [coefficient_node(f, tech, rename, label) for f in t["fields"]]
            if "ci" in t["series"]:
                uses.append("step:grid.delivered_mean")
            sig = tuple(sorted(uses))
            if key in terms_seen and terms_seen[key] == sig:
                continue
            name = KEY_TO_NAME.get(key) or CONSTANTS.get(key) or key
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
            note = None
            if key == "offshore wind" and not dc_architectures.OFFSHORE_IN_SCOPE:
                note = "dc_architectures.OFFSHORE_IN_SCOPE is False: cap_offshore is held at zero."
            gr.add(tid, kind="term", name=name, key=key, side=t["side"], expr=t["expr"],
                   variables=t["vars"], variant=label or None, note=note,
                   series=[s for s in t["series"] if s not in ("dt", "annual_scale")])
            gr.link(chain_nodes[chain], tid)
            for u in uses:
                gr.link(tid, u)
            for f in t["fields"]:
                if f not in tech_fields:
                    problems.append(f"term {key!r} multiplies {f}, which Tech does not have")

    # ---- every foreground database, so nothing hangs unreached -----------------------
    inv_root = gr.add("inventories", kind="group", name="Every foreground inventory, by database",
                      note="One database per source, written by optimiser_lca/ (python -m optimiser_lca.build).")
    gr.link(study, inv_root)
    for db in BW.fg_dbs:
        mod = module_of.get(db)
        dbn = gr.add(f"db:{db}", kind="database", name=db, module=f"optimiser_lca/{mod}.py" if mod else None,
                     source=docs.get(mod))
        gr.link(inv_root, dbn)
        for a in BW.fg_acts:
            if a["database"] == db:
                gr.link(dbn, bw_id(a.id))

    # ---- completeness: every foreground exchange drawn --------------------------------
    drawn = {}
    for p_, c_, _d in gr.edges:
        drawn[p_] = drawn.get(p_, 0) + 1
    for a in BW.fg_acts:
        n_ex = sum(1 for _ in a.technosphere()) + sum(1 for _ in a.biosphere())
        if drawn.get(bw_id(a.id), 0) != n_ex:
            problems.append(f"{a['database']}/{a['code']}: {n_ex} exchanges, {drawn.get(bw_id(a.id), 0)} drawn")

    # ---- method, registers ----------------------------------------------------------
    assumptions = parse_md_sections(ROOT / "optimisation" / "ASSUMPTIONS.md")
    gaps = parse_data_gaps()
    for c, nid in chain_nodes.items():
        words = [w for w in re.findall(r"[a-z]{4,}", c.lower()) if w not in ("load", "unserved")]
        hits = [g["id"] for g in gaps if any(w in g["name"].lower() for w in words)]
        if hits:
            gr.nodes[nid]["gaps"] = hits
    # Steps the code recorded that no objective term reaches: the inputs to the
    # LP's constraints (replacement counts, the hydrogen balance) and the
    # sensitivity bases recorded beside the default. Shown, not dropped.
    reachable = _reachable(gr, "study")
    side = [n for n in gr.nodes if n.startswith("step:") and n not in reachable]
    if side:
        grp = gr.add("off-objective", kind="group", name="Recorded, but outside the carbon objective",
                     note="Numbers the coefficient code computes that no carbon term multiplies: inputs to "
                          "the LP's constraints (replacement counts, the hydrogen balance) and sensitivity "
                          "bases recorded beside the default.")
        gr.link(study, grp)
        for n in side:
            if not any(c == n for p, c, _d in gr.edges if p.startswith("step:") and p in side):
                gr.link(grp, n)
    reachable = _reachable(gr, "study")
    unreached = [n for n in gr.nodes if n not in reachable]
    if unreached:
        problems.append(f"{len(unreached)} boxes not reachable from the study, e.g. {unreached[:3]}")

    out = {
        "nodes": gr.nodes, "edges": gr.edges, "root": "study",
        "gaps": {g["id"]: g for g in gaps},
        "method": {"lcia": " / ".join(BW.method), "background": BW.H.ecoinvent_name(),
                   "grid_method": G.METHOD_LABEL,
                   "cutoff_rule": f"A sourced in-boundary flow is always in; an unsourced one stays out only "
                                  f"under {X.CUTOFF_FLOW_SHARE:.0%} of its technology's carbon, all together "
                                  f"under {X.CUTOFF_TECHNOLOGY_SHARE:.0%}, and without changing the best design.",
                   "assumptions": assumptions},
        "problems": problems,
        "meta": {"generated": time.strftime("%Y-%m-%d %H:%M"), "seconds": round(time.time() - t0),
                 "nodes": len(gr.nodes), "edges": len(gr.edges), "steps": len(steps),
                 "foreground_activities": len(BW.fg_acts), "ecoinvent_drilled": len(drilled),
                 "run": {"site": SITE, "start": START, "end": END, "size_mw_it": SIZE_MW_IT, **MAIN},
                 "variants": [v for v, _ in VARIANTS], "cutoff_added": added,
                 "fingerprint": fingerprint()},
    }
    return out


def _reachable(gr, root):
    kids = {}
    for p, c, _d in gr.edges:
        kids.setdefault(p, []).append(c)
    seen, stack = set(), [root]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(kids.get(n, []))
    return seen


def write_html(blob: str) -> Path:
    """The interactive page: the template with the map inlined (``</`` escaped
    so no string in the data can close the script tag)."""
    page = HTML_TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", blob.replace("</", "<\\/"))
    HTML_OUT.write_text(page, encoding="utf-8")
    return HTML_OUT


def add_energy(out: dict) -> dict:
    """The energy-flow tab (scripts/energy_map.py). No Brightway, so rebuilt every run."""
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
        m = out["meta"]
        print(f"built the map: {m['nodes']:,} boxes, {m['edges']:,} links, {m['steps']} trace steps, "
              f"{m['ecoinvent_drilled']} ecoinvent datasets opened, {m['seconds']} s")
        if out["problems"]:
            print(f"\n{len(out['problems'])} PROBLEMS — the map disagrees with the model:")
            for p in out["problems"]:
                print("  -", p)
    out = add_energy(out)
    blob = json.dumps(out, default=lambda o: float(o) if hasattr(o, "__float__") else str(o),
                      separators=(",", ":"))
    OUT.write_text(blob, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {OUT.stat().st_size / 1e6:.2f} MB")
    page = write_html(blob)
    print(f"wrote {page.relative_to(ROOT)}: {page.stat().st_size / 1e6:.2f} MB")
    sys.exit(1 if out.get("problems") else 0)
