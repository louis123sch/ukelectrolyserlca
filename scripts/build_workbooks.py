"""
The cost and carbon workbooks: how every figure reaches the optimiser, and how
a saved run's result breaks down into its parts, as live Excel formulas.
=============================================================================

Generated from the code the way the maps are. A saved run (``optimisation/
dc_runner``'s folder: config.json, summary.json, pareto.parquet,
dispatch.parquet) is read; its inputs are rebuilt with the same function the
run used (``dc_runner.load_inputs``) inside ``optimisation.trace.recording()``,
so every ``T.step`` / ``T.cost`` the coefficient modules record becomes a row.

Each row is one of:

* **an input** - a figure read from a source (transcribed, assumed, proxy), a
  constant written in the code, or an ecoinvent/biosphere score from Brightway.
  A plain number, with its document, page and note.
* **a live formula** - the step's own recorded expression, each name in it
  linked to the cell it came from by the value the trace recorded for it
  ("read from the code"); a helper written out in Excel (capital recovery,
  building finance); or, where the code cannot be read that way, the same
  value rebuilt exactly from the step's own used figures ("rebuilt by
  matching values", said so in a cell comment). Every formula is checked here
  against the model's value before it is written, and in Excel by
  ``scripts/check_workbooks.py``.
* **a fixed number** - computed in code in a way Excel cannot follow (a mean
  over the half-hourly year, a fit, a table lookup). Its note says where.

Then the optimiser's own figures (every ``dc_model.Tech`` field and each
connection option), and one sheet per point of the run - the knee, lowest
cost and lowest carbon - where each part of the bill is figure x amount built,
read from ``dc_model.objective_terms`` itself on symbols that write Excel. The
hourly parts (grid imports, export) are SUMPRODUCTs over an hourly sheet of
the run's own saved series. Nothing is optimised in the workbook: the amounts
are the run's.

    python scripts/build_workbooks.py                 # the latest finished run
    python scripts/build_workbooks.py --run <folder>  # a named run

Writes optimisation_outputs/cost_workbook.xlsx and carbon_workbook.xlsx, and
<name>.expected.json beside each (every named cell's model value) for the
checker.
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import itertools
import json
import math
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT = ROOT / "optimisation_outputs"
LCA_MAP = OUT / "lca_map.json"
POINTS = (("knee", "Knee", "Knee point"), ("min_cost", "Lowest cost", "Lowest cost"),
          ("min_gwp", "Lowest carbon", "Lowest carbon"))
PT_PREFIX = {"knee": "knee", "min_cost": "low_cost", "min_gwp": "low_carbon"}
INPUT_GRADES = ("transcribed", "assumed", "proxy")
REL = 1e-9
# A figure the code cached from a Brightway score, matched to the same activity's score in the
# LCA map: two solves, which agree to about one part in ten million, not exactly.
INVENTORY_REL = 1e-6


def same(a, b, rel=REL) -> bool:
    if a is None or b is None:
        return False
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


def num(v) -> str:
    """A float as Excel reads it."""
    v = float(v)
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(v).upper()


# =============================================================================
# Excel names
# =============================================================================
class Names:
    """Step keys to valid, unique Excel defined names."""

    def __init__(self):
        self.by_key: dict[str, str] = {}
        self.used: set[str] = set()

    def get(self, key: str) -> str:
        if key in self.by_key:
            return self.by_key[key]
        s = re.sub(r"[^A-Za-z0-9_.]", "_", key)
        s = re.sub(r"_+", "_", s)
        if not re.match(r"[A-Za-z_]", s) or re.match(r"^[A-Za-z]{1,3}\d+(\.|_|$)", s) \
                or re.match(r"^[rRcC](\d|$|\.|_)", s):
            s = "_" + s
        base, n = s[:240], 2
        while base.lower() in self.used:
            base, n = f"{s[:235]}_{n}", n + 1
        self.used.add(base.lower())
        self.by_key[key] = base
        return base


# =============================================================================
# Cells
# =============================================================================
@dataclasses.dataclass
class Cell:
    key: str
    title: str
    value: float | None
    unit: str = ""
    kind: str = "input"           # input / formula / fixed
    how: str = ""                 # how the formula was made, or why it is fixed
    formula: str | None = None    # Excel, without "=", over defined names
    grade: str = ""
    source: str = ""
    at: str = ""
    note: str = ""
    where: str = ""
    code: str = ""
    refs: tuple = ()              # keys this formula reads
    sheet: str = ""


# =============================================================================
# Reading a step's code as an Excel formula
# =============================================================================
def _crf(r, n):
    r, n = float(r), float(n)
    return 1.0 / n if r == 0 else r * (1 + r) ** n / ((1 + r) ** n - 1)


def _bff(r, y):
    r, y = float(r), int(round(float(y)))
    return sum((1.0 + r) ** (y - i - 0.5) for i in range(y)) / y


HELPERS = {
    # name in the code: (Excel template over {0}, {1}, ..., python twin)
    "capital_recovery_factor": ("IF({0}=0,1/{1},{0}*(1+{0})^{1}/((1+{0})^{1}-1))", _crf),
    "building_finance_factor": ("IF({0}=0,1,(1+{0})^0.5*((1+{0})^ROUND({1},0)-1)/{0}/ROUND({1},0))", _bff),
    "_finance_factor": ("IF({0}=0,1,(1+{0})^0.5*((1+{0})^ROUND({1},0)-1)/{0}/ROUND({1},0))", _bff),
}
PLAIN = {"float": None, "int": None, "min": "MIN", "max": "MAX", "abs": "ABS"}
FACTORS = ((1000.0, "*1000"), (0.001, "/1000"))


class Untranslatable(Exception):
    pass


class Workbook:
    """The rows of one workbook, before they are written."""

    def __init__(self, side: str, steps: dict, names: Names, activities: dict):
        self.side = side                      # "cost" or "carbon"
        self.steps = steps                    # every recorded step, by key
        self.names = names
        self.activities = activities          # activity ref -> inventory cell key
        self.cells: dict[str, Cell] = {}
        self.extra_inputs: dict[str, Cell] = {}

    # ---- leaves -----------------------------------------------------------
    def _uses(self, s):
        return [u for u in s.uses if isinstance(u, str) and u in self.steps
                and self.steps[u].value is not None]

    def _activity_uses(self, s):
        out = []
        for u in s.uses:
            if isinstance(u, dict):
                k = activity_key(u)
                if k in self.activities:
                    out.append(self.activities[k])
        return out

    def link(self, src: str, v: float, s) -> tuple[str, float, str, list]:
        """(excel, value, how, refs) for one name in a step's code."""
        tokens = set(re.findall(r"[a-z]+", src.lower()))

        def score(key):
            return len(tokens & set(re.findall(r"[a-z]+", key.lower())))
        uses = self._uses(s)
        hits = [u for u in uses if same(self.steps[u].value, v)]
        if hits:
            u = max(hits, key=score)
            return self.names.get(u), v, "", [u]
        for k, iv in (s.inputs or {}).items():
            if isinstance(iv, (int, float)) and same(float(iv), v):
                key = self.step_input(s, k, float(iv))
                return self.names.get(key), v, "", [key]
        for f, txt in FACTORS:
            hits = [u for u in uses if same(self.steps[u].value * f, v)]
            if hits:
                u = max(hits, key=score)
                return f"({self.names.get(u)}{txt})", v, "unit factor", [u]
        for a in self._activity_uses(s):
            sc = self.cells_value(a)
            for f, txt in ((1.0, ""),) + FACTORS:
                if sc is not None and same(sc * f, v, INVENTORY_REL):
                    return (f"({self.names.get(a)}{txt})" if txt else self.names.get(a)), v, "", [a]
        last = src.split(".")[-1].split("[")[0]
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", last) or re.fullmatch(r"[A-Z][A-Z0-9_]*\[.*\]", src.split(".")[-1]):
            key = self.code_constant(s, src, v)
            return self.names.get(key), v, "", [key]
        raise Untranslatable(f"{src} = {v:.6g} matches nothing {s.key} uses")

    def cells_value(self, key):
        c = self.cells.get(key) or self.extra_inputs.get(key)
        return c.value if c else None

    def step_input(self, s, name, value) -> str:
        key = f"{s.key}.{name}"
        if key not in self.extra_inputs:
            self.extra_inputs[key] = Cell(key, f"{name}, recorded with {s.key}", value, kind="input",
                                          grade="recorded with the step",
                                          note=f"Recorded as an input of {s.key} (its 'inputs=')",
                                          where=s.where)
        return key

    def code_constant(self, s, src, value) -> str:
        module = Path(s.where.split(":")[0]).stem if s.where else "code"
        key = f"{module}.{src}"
        if key not in self.extra_inputs:
            self.extra_inputs[key] = Cell(key, f"{src}, a constant in {module}.py", value, kind="input",
                                          grade="constant in code", note=f"Written in the code; read by {s.key}",
                                          where=s.where.split(":")[0] if s.where else "")
        return key

    # ---- the expression ---------------------------------------------------
    def conv(self, n, s, how: set, refs: list):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return num(n.value), float(n.value), 9
        if isinstance(n, ast.BinOp):
            ops = {ast.Add: ("+", 5), ast.Sub: ("-", 5), ast.Mult: ("*", 7), ast.Div: ("/", 7),
                   ast.Pow: ("^", 8)}
            if type(n.op) not in ops:
                raise Untranslatable(f"operator {type(n.op).__name__}")
            op, p = ops[type(n.op)]
            a, av, ap = self.conv(n.left, s, how, refs)
            b, bv, bp = self.conv(n.right, s, how, refs)
            a = f"({a})" if ap < p or (op == "^" and ap <= p) else a
            b = f"({b})" if bp < p or (bp == p and op in ("-", "/", "^")) else b
            try:
                val = (av + bv if op == "+" else av - bv if op == "-" else av * bv if op == "*"
                       else (av / bv if bv else math.inf) if op == "/" else float(av ** bv))
            except (OverflowError, ZeroDivisionError, TypeError) as e:
                raise Untranslatable(f"arithmetic: {e}")
            return f"{a}{op}{b}", val, p
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            a, av, ap = self.conv(n.operand, s, how, refs)
            a = f"({a})" if ap < 8 else a
            return (f"-{a}", -av, 8) if isinstance(n.op, ast.USub) else (a, av, ap)
        if isinstance(n, ast.Call):
            fname = ast.unparse(n.func).split(".")[-1]
            if n.keywords:
                raise Untranslatable(f"{fname}() with keyword arguments")
            args = [self.conv(a, s, how, refs) for a in n.args]
            if fname in PLAIN:
                if PLAIN[fname] is None:
                    if len(args) != 1:
                        raise Untranslatable(fname)
                    if fname == "int" and args[0][1] != int(args[0][1]):
                        raise Untranslatable("int() truncates")
                    return args[0]
                f = {"MIN": min, "MAX": max, "ABS": abs}[PLAIN[fname]]
                return f"{PLAIN[fname]}({','.join(a[0] for a in args)})", f(*[a[1] for a in args]), 9
            if fname in HELPERS:
                tpl, py = HELPERS[fname]
                how.add("helper")
                return tpl.format(*[f"({a[0]})" if a[2] < 9 else a[0] for a in args]), py(*[a[1] for a in args]), 9
            raise Untranslatable(f"calls {fname}()")
        if isinstance(n, (ast.Name, ast.Attribute, ast.Subscript)):
            src = ast.unparse(n)
            if src not in (s.leaves or {}):
                raise Untranslatable(f"{src} has no recorded value")
            x, v, h, r = self.link(src, s.leaves[src], s)
            refs += r
            if h:
                how.add(h)
            return x, v, 9
        raise Untranslatable(type(n).__name__)

    def from_code(self, s):
        tree = ast.parse(s.code, mode="eval")
        how, refs = set(), []
        x, v, _ = self.conv(tree.body, s, how, refs)
        if not same(v, s.value):
            raise Untranslatable(f"reads as {v:.9g}, the step is {s.value:.9g}")
        return x, refs, how

    def rebuilt(self, s):
        """The value from the step's own used figures, inputs and code
        constants, with up to three of + - * /, exactly."""
        pool = [(self.names.get(u), self.steps[u].value, [u]) for u in self._uses(s)]
        for k, iv in (s.inputs or {}).items():
            if isinstance(iv, (int, float)) and not isinstance(iv, bool):
                pool.append((None, float(iv), ("input", k)))
        try:
            consts = {float(c.value) for c in ast.walk(ast.parse(s.code or "0", mode="eval"))
                      if isinstance(c, ast.Constant) and isinstance(c.value, (int, float))
                      and not isinstance(c.value, bool)}
        except SyntaxError:
            consts = set()
        pool += [(num(c), c, []) for c in sorted(consts) if c not in (0.0,)]
        for a in self._activity_uses(s):
            if self.cells_value(a) is not None:
                pool.append((self.names.get(a), self.cells_value(a), [a]))
        pool = pool[:10]

        def text(p):
            if p[0] is None:
                key = self.step_input(s, p[2][1], p[1])
                return self.names.get(key), [key]
            return p[0], list(p[2])
        for p in pool:
            if same(p[1], s.value):
                t, r = text(p)
                return t, r
        for r_ in (2, 3):
            for combo in itertools.permutations(pool, r_):
                for ops in itertools.product("*/+-", repeat=r_ - 1):
                    acc = combo[0][1]
                    ok = True
                    for o, c in zip(ops, combo[1:]):
                        if o == "/" and c[1] == 0:
                            ok = False
                            break
                        acc = {"*": acc * c[1], "/": acc / c[1] if c[1] else 0, "+": acc + c[1], "-": acc - c[1]}[o]
                    if ok and same(acc, s.value):
                        t0, refs = text(combo[0])
                        x = t0
                        for o, c in zip(ops, combo[1:]):
                            t, r = text(c)
                            refs += r
                            x = f"({x}){o}{t}" if ("+" in x or "-" in x[1:]) and o in "*/" else f"{x}{o}{t}"
                        return x, refs
        raise Untranslatable("no combination of the used figures gives the value")

    def from_inventory(self, s):
        for a in self._activity_uses(s):
            sc = self.cells_value(a)
            for f, txt in ((1.0, ""),) + FACTORS:
                if sc is not None and same(sc * f, s.value, INVENTORY_REL):
                    return (f"{self.names.get(a)}{txt}", [a])
        raise Untranslatable("no inventory activity it uses has this value")

    # ---- every step -------------------------------------------------------
    def add_step(self, s):
        c = Cell(s.key, s.title, s.value, unit=s.unit, grade=s.grade, where=s.where, code=s.code,
                 note=s.note or "", source=s.source or "")
        if s.cites:
            c.source = "; ".join(x["source"] for x in s.cites)
            c.at = "; ".join(x.get("at", "") for x in s.cites)
        if s.value is None:
            c.kind, c.how = "fixed", "not a single number"
        elif s.grade in INPUT_GRADES:
            c.kind = "input"
        else:
            tries = []
            if s.code:
                tries.append(("read from the code", self.from_code))
            if self.side == "carbon" or self._activity_uses(s):
                tries.append(("from the inventory", lambda s_: (*self.from_inventory(s_), set())))
            tries.append(("rebuilt by matching values", lambda s_: (*self.rebuilt(s_), set())))
            why = []
            for label, fn in tries:
                try:
                    x, refs, how = fn(s)
                    if re.fullmatch(r"-?[0-9.E+-]+", x):         # the code writes the number itself
                        c.kind, c.grade, c.note = "input", "constant in code", (c.note or "Written in the code")
                        break
                    c.kind, c.formula, c.refs = "formula", x, tuple(dict.fromkeys(refs))
                    if label.startswith("rebuilt") and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", x):
                        label = "the figure it uses, unchanged"
                    c.how = label + (" (" + ", ".join(sorted(how)) + ")" if how else "")
                    break
                except Untranslatable as e:
                    why.append(f"{label}: {e}")
            else:
                c.kind = "fixed"
                c.how = f"computed in code at {s.where}"
                c.note = (c.note + " " if c.note else "") + "Why not a formula: " + why[0]
        self.cells[s.key] = c
        return c


def activity_key(ref: dict) -> str:
    if "ecoinvent" in ref:
        name, loc, prod = (list(ref["ecoinvent"]) + [None, None, None])[:3]
        return f"ei|{name}|{loc}|{prod}"
    return f"fg|{ref.get('database')}|{ref.get('code')}"


# =============================================================================
# The optimiser's terms, on symbols that write Excel
# =============================================================================
class XS:
    """A number that remembers its Excel text. ``hourly`` holds the hourly
    factors (named ranges and their arrays) of a per-step product, folded into
    one SUMPRODUCT by ``.sum()``."""
    __array_priority__ = 1000

    def __init__(self, text, val, prec=9, hourly=(), refs=()):
        self.text, self.val, self.prec, self.hourly, self.refs = text, float(val), prec, tuple(hourly), set(refs)

    @staticmethod
    def of(x):
        return x if isinstance(x, XS) else XS(num(x), float(x))

    def __float__(self):
        if self.hourly:
            raise TypeError("an hourly quantity is not one number")
        return self.val

    def _w(self, p):
        return f"({self.text})" if self.prec < p else self.text

    def _bin(self, o, op, rev=False):
        a, b = (XS.of(o), self) if rev else (self, XS.of(o))
        p = 5 if op in "+-" else 7
        if op in "+-" and (a.hourly or b.hourly):
            raise TypeError("adding hourly quantities before summing them")
        if op == "/" and b.hourly:
            raise TypeError("dividing by an hourly quantity")
        right = p + (1 if op in "-/" else 0)
        if op == "*" and a.text == "1":
            text, prec = b.text, b.prec
        elif op == "*" and b.text == "1":
            text, prec = a.text, a.prec
        else:
            text, prec = f"{a._w(p)}{op}{b._w(right)}", p
        val = {"+": a.val + b.val, "-": a.val - b.val, "*": a.val * b.val,
               "/": a.val / b.val if b.val else 0.0}[op]
        return XS(text, val, prec, a.hourly + b.hourly, a.refs | b.refs)

    def __add__(self, o): return self._bin(o, "+")
    def __radd__(self, o): return self if (not isinstance(o, XS) and o == 0) else self._bin(o, "+", True)
    def __sub__(self, o): return self._bin(o, "-")
    def __rsub__(self, o): return self._bin(o, "-", True)
    def __mul__(self, o): return self._bin(o, "*")
    def __rmul__(self, o): return self._bin(o, "*", True)
    def __truediv__(self, o): return self._bin(o, "/")
    def __rtruediv__(self, o): return self._bin(o, "/", True)
    def __neg__(self): return XS(f"-{self._w(8)}", -self.val, 8, self.hourly, self.refs)
    def __gt__(self, o): return self.val > float(o)

    def sum(self):
        if not self.hourly:
            raise TypeError("summing a single number over time")
        arr = np.prod([h[1] for h in self.hourly], axis=0)
        ranges = ",".join(h[0] for h in self.hourly)
        s = f"SUMPRODUCT({ranges})" if len(self.hourly) > 1 else f"SUM({ranges})"
        text = s if self.text == "1" else f"{self._w(7)}*{s}"
        return XS(text, self.val * float(arr.sum()), 7 if self.text != "1" else 9, (),
                  self.refs | {h[0] for h in self.hourly})


def hourly(name, arr):
    return XS("1", 1.0, 9, ((name, np.asarray(arr, dtype=float)),))


# =============================================================================
# The run
# =============================================================================
def point_quantities(row: pd.Series, disp: pd.DataFrame, series, tech, assets) -> tuple[dict, dict, dict]:
    """(scalars, hourly arrays, notes) for one point: what objective_terms reads."""
    from optimisation import dc_model as M
    dt, scale = series.dt_hours, series.annual_scale
    sc, notes = {}, {}
    for k in ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_p", "cap_batt_e", "cap_ely",
              "cap_tank", "cap_fc", "cap_grid"):
        sc[k] = float(row.get(k, 0.0) or 0.0)
        notes[k] = "built, from the run (pareto.parquet)"
    hr = {k: disp[k].to_numpy(dtype=float) for k in disp.columns
          if k not in ("t", "point") and pd.api.types.is_numeric_dtype(disp[k])}
    fc_mwh = float(hr["p_fc"].sum() * dt * scale)
    ely_mwh = float(hr["p_ely"].sum() * dt * scale)
    sc["fc_stack_units"] = max(sc["cap_fc"] / tech.fc_stack_calendar_years, fc_mwh / tech.fc_stack_duty_hours)
    sc["fc_bop_units"] = max(sc["cap_fc"] / tech.fc_bop_calendar_years, fc_mwh / tech.fc_bop_duty_hours)
    sc["ely_stack_units"] = max(sc["cap_ely"] / tech.ely_stack_calendar_years, ely_mwh / tech.ely_stack_duty_hours)
    for k, (cal, duty) in {"fc_stack_units": ("fc_stack_calendar_years", "fc_stack_duty_hours"),
                           "fc_bop_units": ("fc_bop_calendar_years", "fc_bop_duty_hours"),
                           "ely_stack_units": ("ely_stack_calendar_years", "ely_stack_duty_hours")}.items():
        notes[k] = (f"replacements per year, from the run: the larger of capacity / {cal} and "
                    f"energy / {duty} (dc_model.build_model's constraints, tight at the optimum)")
    window = (np.ones(series.n, dtype=bool) if series.triad_window is None
              else np.asarray(series.triad_window, dtype=bool))
    sc["triad_mw"] = float(hr["imp"][window].max()) if window.any() else 0.0
    notes["triad_mw"] = "largest import in a winter-peak candidate step, from the run's hourly imports"
    sc["grid_on"] = 1.0 if assets.grid else 0.0
    notes["grid_on"] = "1 while the grid is allowed"
    opts = M.connection_options_of(tech)
    if opts:
        chosen = row.get("connection_option")
        idx = next((i for i, o in enumerate(opts) if o.key == chosen), None)
        for i, o in enumerate(opts):
            sc[f"on_{i}"] = 1.0 if i == idx else 0.0
            sc[f"cap_conn_{i}"] = sc["cap_grid"] if i == idx else 0.0
            notes[f"on_{i}"] = f"1 if the run chose option {i + 1} ({o.key})"
            notes[f"cap_conn_{i}"] = f"connection on option {i + 1}: the built connection if chosen"
    return sc, hr, notes


def evaluate_terms(tech, series, sc, hr, pt, wb_cells, assets):
    """Every term of dc_model.objective_terms (+ constants and facility terms)
    as XS: Excel text over defined names, and its value."""
    from optimisation import dc_model as M
    pre = PT_PREFIX[pt]
    fields = {f.name for f in dataclasses.fields(tech)} - {"labels", "connection_options"}
    coef = {}
    for f in fields:
        v = getattr(tech, f)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            coef[f] = XS(f"LP.{f}", float(v), refs={f"LP.{f}"})
    opts = M.connection_options_of(tech) or ()
    xopts = []
    for i, o in enumerate(opts):
        rep = {}
        for f in ("cost_per_mw_year", "cost_fixed_per_year", "gwp_per_mw_year", "gwp_fixed_per_year"):
            v = getattr(o, f)
            if v is not None:
                rep[f] = XS(f"LP.option{i + 1}.{f}", float(v), refs={f"LP.option{i + 1}.{f}"})
        xopts.append(dataclasses.replace(o, **rep))
    xtech = dataclasses.replace(tech, **coef, connection_options=tuple(xopts) if xopts else tech.connection_options)
    q = {k: XS(f"{pre}.{k}", v, refs={f"{pre}.{k}"}) for k, v in sc.items()}
    for k in ("imp", "exp", "p_ely", "p_fc", "h2_buy", "h2_buy_2", "tank", "unserved", "demand"):
        q[k] = hourly(f"{pre}.h.{k}", hr[k])
    groups = sorted({o.group for o in opts})
    gs = {}
    for g in groups:
        v = M.group_import_var(g)
        tag = v[len("imp_"):]
        q[v] = hourly(f"{pre}.h.{v}", hr[v])
        gs[g] = (hourly(f"{pre}.h.price_{tag}", hr[f"price_per_mwh_{tag}"]),
                 hourly(f"{pre}.h.ci_{tag}", hr[f"grid_gwp_per_mwh_{tag}"]))
    xs_series = SimpleNamespace(dt_hours=XS("run.dt_hours", series.dt_hours, refs={"run.dt_hours"}),
                                annual_scale=XS("run.annual_scale", series.annual_scale, refs={"run.annual_scale"}),
                                grid_groups=None, n=series.n)
    terms = M.objective_terms(q, xs_series, xtech, price=hourly(f"{pre}.h.price", hr["price_per_mwh"]),
                              ci=hourly(f"{pre}.h.ci", hr["grid_gwp_per_mwh"]), group_series=gs or None)
    demand = (q["demand"] * xs_series.dt_hours).sum() * xs_series.annual_scale
    out = {side: {k: XS.of(v) for k, v in d.items()} for side, d in terms.items()}
    # the parts no decision moves (dc_model.objective_constants), written out
    const = {}
    if assets.grid and not opts:
        const["connection fixed"] = coef["cost_grid_fixed_per_year"]
    if assets.tank:
        const["major-hazard compliance"] = coef["cost_major_hazard_per_year"]
    out["cost_constant"] = const
    out["gwp_facility"] = {k: XS.of(v) for k, v in M.facility_terms(xtech, demand).items()}
    return out, demand


# =============================================================================
# Building
# =============================================================================
def record_run(folder: Path):
    """The run's inputs rebuilt inside a trace recording: (recorder, inputs)."""
    from optimisation import dc_runner as R, trace as T
    with T.recording() as rec:
        L = R.load_inputs(folder)
    return rec, L


def choose_run(arg=None) -> Path | None:
    """A run folder: the one named, else the newest finished run, else None."""
    from optimisation import dc_runner as R
    if arg:
        return Path(arg)
    runs = R.finished_runs()
    return runs[0] if runs else None


def run_points(folder: Path, L, problems: list) -> dict:
    """The run's three points, each with its amounts and every part of both
    totals (objective_terms on the run's numbers), checked against the run's
    own totals and its saved prices."""
    from optimisation import dc_model as M
    folder = Path(folder)
    pareto = pd.read_parquet(folder / "pareto.parquet")
    disp = pd.read_parquet(folder / "dispatch.parquet")
    series, tech, assets, summary = L.series, L.tech, L.assets, L.summary
    pts = {}
    for pt, sheet, label in POINTS:
        prow = summary.get(pt) or {}
        tag = prow.get("point")
        sel = pareto[pareto["point"] == tag]
        if sel.empty:
            problems.append(f"{label}: point {tag!r} is not in pareto.parquet")
            continue
        row = sel.iloc[0]
        d = disp[disp["point"] == pt]
        if len(d) != series.n:
            problems.append(f"{label}: dispatch has {len(d)} steps, the rebuilt series {series.n}")
            continue
        sc, hr, notes = point_quantities(row, d, series, tech, assets)
        terms, demand = evaluate_terms(tech, series, sc, hr, pt, None, assets)
        for g, gd in (series.grid_groups or {}).items():
            tagg = M.group_import_var(g)[len("imp_"):]
            col = f"price_per_mwh_{tagg}"
            if col in d and not np.allclose(np.asarray(gd["price_per_mwh"], dtype=float), d[col].to_numpy(),
                                            rtol=1e-9, atol=1e-9):
                problems.append(f"{label}: the rebuilt {g} price is not the price the run saved")
        cost = sum(v.val for s_ in ("cost_capital", "cost_operational", "cost_constant") for v in terms[s_].values())
        gwp = sum(v.val for s_ in ("gwp_embodied", "gwp_operational", "gwp_facility") for v in terms[s_].values())
        for what, mine, theirs in (("cost", cost, row["cost_GBP_per_year"]),
                                   ("carbon", gwp, row["gwp_kgco2e_per_year"])):
            if not same(mine, float(theirs), 1e-6):
                problems.append(f"{label}: the parts add to {mine:,.2f}, the run's {what} total is {float(theirs):,.2f}")
        opts = M.connection_options_of(tech) or ()
        idx = next((i for i, o in enumerate(opts) if o.key == row.get("connection_option")), None)
        pts[pt] = dict(row=row, sc=sc, hr=hr, notes=notes, terms=terms, demand=demand, label=label, sheet=sheet,
                       cost=float(row["cost_GBP_per_year"]), gwp=float(row["gwp_kgco2e_per_year"]),
                       served=float(row.get("served_MWh_per_year") or 0.0), connection_index=idx,
                       connection=row.get("connection_option"),
                       build={k: float(row[k]) for k in ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_p",
                                                         "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_grid")
                              if k in row})
    return pts


def inventory_from_map(problems: list) -> tuple[dict, list, dict]:
    """The inventory from lca_map.json: every foreground activity, its exchanges,
    and the Brightway score of each thing it draws on. Returns (cells by key,
    exchange rows, activity ref -> cell key)."""
    from map_fingerprint import inventories_digest
    d = json.loads(LCA_MAP.read_text(encoding="utf-8"))
    built = (d.get("meta", {}).get("fingerprint") or {}).get("inventories")
    if built and built != inventories_digest():
        problems.append("the LCA map was built from different inventories; rebuild it (scripts/build_lca_map.py)")
    N = d["nodes"]
    out_edges = {}
    for a, b, e in d["edges"]:
        out_edges.setdefault(a, []).append((b, e))
    cells, rows, refs = {}, [], {}
    for nid, n in N.items():
        if n["kind"] == "foreground":
            refs[f"fg|{n.get('database')}|{n.get('code')}"] = f"act.{n.get('database')}.{n.get('code')}"
        elif n["kind"] == "ecoinvent":
            refs[f"ei|{n.get('name')}|{n.get('location')}|{n.get('product')}"] = f"ei.{nid[3:]}"

    def key_of(nid):
        n = N[nid]
        if n["kind"] == "foreground":
            return f"act.{n.get('database')}.{n.get('code')}"
        if n["kind"] == "ecoinvent":
            return f"ei.{nid[3:]}"
        if n["kind"] == "biosphere":
            return f"bio.{nid.split(':', 1)[1]}"
        return None
    for nid, n in N.items():
        if n["kind"] != "foreground":
            continue
        k = key_of(nid)
        parts = []
        for b, e in out_edges.get(nid, []):
            if e.get("amount") is None or b not in N:
                continue
            m = N[b]
            mk = key_of(b)
            if mk is None:
                continue
            if mk not in cells and m["kind"] in ("ecoinvent", "biosphere"):
                cells[mk] = upstream_cell(mk, m)
            parts.append((mk, float(e["amount"]), e.get("unit") or "", e.get("note") or m.get("name")))
        rows.append((k, n, parts))
        cells[k] = Cell(k, f"{n['name']}", n.get("score"), unit=f"kg CO2e per {n.get('unit')}",
                        kind="formula", how="sum of amount x score over its inputs",
                        note=(n.get("comment") or "")[:400], where=n.get("module") or "")
    # an ecoinvent activity a step reads directly, not through our inventory
    pool = {key_of(nid): upstream_cell(key_of(nid), n) for nid, n in N.items() if n["kind"] == "ecoinvent"}
    return cells, rows, refs, pool


def upstream_cell(mk, m) -> Cell:
    if m["kind"] == "ecoinvent":
        return Cell(mk, f"{m['name']} | {m.get('location')} | {m.get('product')}",
                    m.get("score"), unit=f"kg CO2e per {m.get('unit')}", kind="input",
                    grade="Brightway", source=m.get("database", ""),
                    note="Score of one unit, scored by Brightway (IPCC 2021 GWP100) from the "
                         "whole ecoinvent supply chain: not something a spreadsheet can redo")
    return Cell(mk, f"{m['name']} ({m.get('compartment')})", m.get("cf"),
                unit=f"kg CO2e per {m.get('unit')}", kind="input", grade="Brightway",
                source="IPCC 2021 GWP100", note="Characterisation factor")


def build(run: Path | None = None, out_dir: Path | None = None) -> dict:
    from optimisation import dc_model as M, dc_runner as R, source_register as SR
    from map_fingerprint import trace_code_digest
    t0 = time.time()
    problems: list[str] = []
    run = choose_run(run)
    if run is None:
        raise SystemExit("no finished run in optimisation_outputs/dc_runs: run one first")
    print(f"run: {run}")
    rec, L = record_run(run)
    cfg, summary, series, tech = L.cfg, L.summary, L.series, L.tech
    for k, v in rec.conflicts.items():
        problems.append(f"trace: {k} was recorded with {len(v)} different values")
    steps = rec.steps
    names = Names()
    inv_cells, inv_rows, act_refs, ei_pool = inventory_from_map(problems)

    books = {}
    for side in ("cost", "carbon"):
        wb = Workbook(side, steps, names, act_refs)
        if side == "carbon":
            for k, c in inv_cells.items():
                wb.cells[k] = c
            for s in steps.values():
                for u in s.uses:
                    if isinstance(u, dict):
                        k = act_refs.get(activity_key(u))
                        if k in ei_pool and k not in wb.cells:
                            wb.cells[k] = ei_pool[k]
        books[side] = wb

    # ---- terms per point, first: they say which optimiser figures each book needs
    pts = run_points(run, L, problems)
    run_note = freshness(cfg, problems)
    if run_note:
        print("NOTE:", run_note)

    # ---- the optimiser's figures each book uses
    lp = {}
    for side, groups in (("cost", ("cost_capital", "cost_operational", "cost_constant")),
                         ("carbon", ("gwp_embodied", "gwp_operational", "gwp_facility"))):
        need = set()
        for p in pts.values():
            for g in groups:
                for v in p["terms"][g].values():
                    need |= {r for r in v.refs if r.startswith("LP.")}
        lp[side] = sorted(need)

    opts = M.connection_options_of(tech) or ()

    def lp_cell(ref):
        """An optimiser figure: linked to its trace step, or a default in dc_model.Tech."""
        f = ref[3:]
        if f.startswith("option"):
            i, attr = f[len("option"):].split(".", 1)
            o = opts[int(i) - 1]
            v = float(getattr(o, attr))
            slug = re.sub(r"\W+", "_", o.key).strip("_")
            want = {"cost_per_mw_year": "cost_per_MW_year", "cost_fixed_per_year": "cost_fixed_per_year",
                    "gwp_per_mw_year": "gwp_per_MW_year", "gwp_fixed_per_year": "gwp_fixed_per_year"}[attr]
            cands = [k for k in steps if k.startswith(f"connection.{slug}.") and same(steps[k].value, v)]
            exact = [k for k in cands if k.lower().endswith(want.lower())]
            key = (exact or cands or [None])[0]
            title = f"Option {i}, {o.key}: {attr.replace('_', ' ')}"
            unit = "GBP per MW per year" if attr == "cost_per_mw_year" else (
                "GBP per year" if attr == "cost_fixed_per_year" else
                "kg CO2e per MW per year" if attr == "gwp_per_mw_year" else "kg CO2e per year")
        else:
            v = float(getattr(tech, f))
            key = f"coefficient.{f}" if f"coefficient.{f}" in steps else None
            cut = f"cutoff.{f}" if f"cutoff.{f}" in steps else None
            if key:
                total = steps[key].value + (steps[cut].value if cut else 0.0)
                if not same(total, v):
                    problems.append(f"optimiser figure {f}: the trace gives {total:.9g}, build_tech {v:.9g}")
                    key = None
            title = steps[key].title if key else f"{f} (a default in dc_model.Tech)"
            unit = steps[key].unit if key else ""
            if key and cut:
                return Cell(ref, title + ", with its cut-off estimates", v, unit=unit, kind="formula",
                            formula=f"{names.get(key)}+{names.get(cut)}", refs=(key, cut),
                            how="the step that makes it, plus the cut-off register's estimate")
        if key is None and f.startswith("option"):
            problems.append(f"{ref}: no trace step has this connection option's value")
        if key:
            return Cell(ref, title, v, unit=unit, kind="formula", formula=names.get(key), refs=(key,),
                        how="the step that makes it")
        return Cell(ref, title, v, unit=unit, kind="input", grade="constant in code",
                    note="A default written in dc_model.Tech; no step records it", where="optimisation/dc_model.py")

    # ---- the steps each book shows: its side, everything those use, and what its figures read
    for side, wb in books.items():
        roots = [k for k, s in steps.items() if (s.side == "cost") == (side == "cost")]
        lpcells = {r: lp_cell(r) for r in lp[side]}
        roots += [k for c in lpcells.values() for k in c.refs]
        todo, seen = list(roots), set()
        while todo:
            k = todo.pop()
            if k in seen or k not in steps:
                continue
            seen.add(k)
            c = wb.add_step(steps[k])
            todo += [u for u in steps[k].uses if isinstance(u, str)]
            todo += [r for r in c.refs if r in steps]
        wb.lp = lpcells
        wb.order = _order(wb, seen)

    # ---- write
    paths = {}
    for side, wb in books.items():
        wb.tech = tech
        path = Path(out_dir or OUT) / f"{side}_workbook.xlsx"
        expected = write_book(path, wb, side, run, cfg, summary, pts, series, problems, SR, inv_rows, run_note,
                              trace_code_digest())
        paths[side] = path
        print(f"wrote {path}: {_counts(wb)}")
    for p in problems:
        print("PROBLEM:", p)
    print(f"built in {time.time() - t0:.0f} s")
    return {"paths": paths, "problems": problems, "books": books}


def _stale(cfg) -> list[str]:
    """Which coefficient files changed since the run (its own identity record).

    A file that differs only in line endings (a run made in another checkout,
    which wrote Windows line endings where this one has Unix ones, or the
    reverse) has not changed."""
    import hashlib
    from optimisation import dc_runner as R
    then = cfg.get("coefficients") or {}
    now = R._coefficient_identity()
    out = []
    for k in then:
        if k not in now or then[k] == now[k]:
            continue
        hits = [p for p in (ROOT / "optimisation" / k, ROOT / "optimisation_outputs" / k, ROOT / k) if p.exists()]
        if hits:
            lf = hits[0].read_bytes().replace(b"\r\n", b"\n")
            if then[k] in {hashlib.sha256(b).hexdigest()[:12] for b in (lf, lf.replace(b"\n", b"\r\n"))}:
                continue
        out.append(k)
    return sorted(out)


RUN_MISMATCH = ("parts add to", "price is not the price", "is not in pareto", "dispatch has", "terms add to")


def freshness(cfg, problems: list) -> str | None:
    """Whether the run was made on today's figures. A file changed since the run
    is a problem unless the rebuilt figures reproduce the run's own totals at
    every point and its saved prices; then it cannot have moved anything the
    run used, and it is returned as a note instead."""
    stale = _stale(cfg)
    if not stale:
        return None
    msg = "the run's record of " + ", ".join(stale) + " differs from today's files"
    if any(m in p for p in problems for m in RUN_MISMATCH):
        problems.append(msg + ", and the rebuilt figures do not reproduce the run: re-run it")
        return None
    return (msg + "; the rebuilt figures still reproduce the run's totals at every point and its hourly "
            "prices, so nothing the run used has moved")


def _order(wb, keys) -> list[str]:
    """Steps by how deep their uses go, so a formula reads cells above it."""
    depth = {}

    def d(k, stack=()):
        if k in depth:
            return depth[k]
        if k in stack or k not in wb.steps:
            return 0
        s = wb.steps[k]
        deps = [u for u in s.uses if isinstance(u, str) and u in keys] + \
               [r for r in wb.cells[k].refs if r in keys]
        depth[k] = 1 + max([d(u, stack + (k,)) for u in deps], default=0)
        return depth[k]
    return sorted(keys, key=lambda k: (d(k), k))


def _counts(wb) -> str:
    cs = [c for k, c in wb.cells.items() if k in wb.steps]
    kinds = {}
    for c in cs:
        kinds[c.kind] = kinds.get(c.kind, 0) + 1
    der = [c for c in cs if c.grade not in INPUT_GRADES]
    live = sum(1 for c in der if c.kind == "formula")
    return (f"{len(cs)} steps ({kinds.get('input', 0)} inputs; {live} of {len(der)} worked-out figures live, "
            f"{sum(1 for c in der if c.kind == 'fixed')} fixed)")


# =============================================================================
# Writing: the layout lives in scripts/workbook_layout.py
# =============================================================================
def write_book(*args, **kw):
    from workbook_layout import write_book as _write
    return _write(*args, **kw)


def _hourly_array(hr, col):
    m = {"price": "price_per_mwh", "ci": "grid_gwp_per_mwh"}
    if col in m:
        return hr[m[col]]
    if col.startswith("price_"):
        return hr["price_per_mwh_" + col[6:]]
    if col.startswith("ci_"):
        return hr["grid_gwp_per_mwh_" + col[3:]]
    return hr[col]


def xl_col(j: int) -> str:
    s = ""
    j += 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--run", help="a run folder (default: the latest finished run)")
    ap.add_argument("--out", help="the folder to write to (default: optimisation_outputs)")
    a = ap.parse_args()
    out = build(Path(a.run) if a.run else None, Path(a.out) if a.out else None)
    sys.exit(0)


if __name__ == "__main__":
    main()
