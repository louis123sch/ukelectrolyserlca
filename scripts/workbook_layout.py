"""
How the cost and carbon workbooks are laid out: one sheet per technology.
=============================================================================

``scripts/build_workbooks.py`` decides what every cell holds: an input, a live
formula, or a fixed number. This module decides where each cell goes, so a
person can read the workbook the way they read the maps:

* **Summary** - each technology's part of the run's total at the knee, lowest
  cost and lowest carbon, linked to its sheet, the grand total, and the run's
  own total beside it.
* **One sheet per technology** (wind, solar, battery, ...), top to bottom:
  what it adds to the total at each point (figure x what was built), what the
  run built, then how each figure the optimiser uses is made, one indented
  line per step, down to the inputs and their sources.
* **Shared figures** - figures more than one technology uses (inflation
  factors, discount rates, the grid's import price), each written once.
* **Other figures** - figures the code records that this run's total does not
  use.
* **Hourly** - the run's hourly series the hourly parts add up.
* **Inventory** and **Ecoinvent scores** (carbon only), and **Sources**.

Formulas are written with plain cell references (``=B14*B15``, or
``='Shared figures'!B5``), so Excel's own tools work: select a number and press
Ctrl+[ to jump to what it is made from. Every cell also keeps its name (Formulas
> Name Manager), which ``scripts/check_workbooks.py`` reads.
"""
from __future__ import annotations

import json
import re
import time

CHAIN_NAMES = {"wind": "Wind", "solar": "Solar", "battery": "Battery", "electrolyser": "Electrolyser",
               "hydrogen tank": "Hydrogen tank", "fuel cell": "Fuel cell", "bought hydrogen": "Bought hydrogen",
               "grid": "Grid", "data centre": "Data centre", "unserved load": "Unserved load", "other": "Other parts"}
CHAIN_ORDER = list(CHAIN_NAMES)
SHARED, OTHER, HOURLY, SUMMARY = "Shared figures", "Other figures", "Hourly", "Summary"
POINT_LABEL = {"knee": "Knee", "min_cost": "Lowest cost", "min_gwp": "Lowest carbon"}

TERM_NAMES = {
    "gas engines": "Gas engines (plant, per replacement)", "gas burned": "Gas burned in the engines",
    "gas engine maintenance": "Gas engine maintenance", "gas": "Gas for the engines",
    "gas carbon price": "Carbon price on the engines' CO2", "gas engine running maintenance": "Gas engine running maintenance",
    "wind": "Onshore wind", "solar": "Solar panels",
    "wind step-up transformers": "Wind step-up transformers", "solar step-up transformers": "Solar step-up transformers",
    "battery": "Battery (power and energy)", "battery cells and container": "Battery cells and container",
    "battery power conversion": "Battery power conversion", "battery step-up transformers": "Battery step-up transformers",
    "electrolyser": "Electrolyser", "electrolyser stack replacements": "Electrolyser stack replacements",
    "electrolyser consumables": "Electrolyser water and consumables",
    "electrolyser stacks and water": "Electrolyser stacks and water",
    "H2 tank": "Hydrogen tank", "H2 leaked from tank": "Hydrogen leaked from the tank",
    "major-hazard compliance": "Major-hazard compliance",
    "fuel cell": "Fuel cell, with stack and balance-of-plant replacements",
    "fuel cell stack replacements": "Fuel cell stack replacements",
    "fuel cell BoP replacements": "Fuel cell balance-of-plant replacements",
    "fuel cell maintenance": "Fuel cell servicing", "fuel cell step-up transformers": "Fuel cell step-up transformers",
    "grid connection": "Grid connection, per MW", "grid connection fixed charges": "Grid connection, fixed charges per year",
    "connection fixed": "Grid connection, fixed charges per year", "grid connection cable": "Cable to the substation",
    "grid winter-peak charge": "National grid charge on winter-peak imports",
    "grid energy + network": "Electricity imported (price each hour x imports)",
    "grid import": "Electricity imported (grid carbon each hour x imports)",
    "export credit": "Electricity exported (credit)", "unserved (VoLL)": "Load not served (penalty)",
    "data centre, IT capacity": "Data centre building and IT kit", "data centre, cooling consumables": "Data centre cooling consumables",
}
AMOUNTS = {
    "cap_wind": "Onshore wind built (MW)", "cap_solar": "Solar built (MWp)",
    "cap_batt_p": "Battery power (MW)", "cap_batt_e": "Battery energy (MWh)", "cap_ely": "Electrolyser (MW)",
    "cap_tank": "Hydrogen tank (kg it holds)", "cap_fc": "Fuel cell (MW)", "cap_ge": "Gas engines (MW)",
    "cap_grid": "Grid connection (MW)", "ge_units": "Gas engine plant replaced per year (MW)",
    "fc_stack_units": "Fuel cell stacks replaced per year (MW)", "fc_bop_units": "Fuel cell balance of plant replaced per year (MW)",
    "ely_stack_units": "Electrolyser stacks replaced per year (MW)", "triad_mw": "Import at the winter peak (MW)",
    "grid_on": "Grid connected (1 = yes)",
}
HOURLY_NAMES = {"imp": "Imports (MW)", "exp": "Exports (MW)", "p_ely": "Electrolyser power (MW)",
                "p_fc": "Fuel cell output (MW)", "p_ge": "Gas engine output (MW)", "h2_buy": "Hydrogen bought (kg)", "h2_buy_2": "Second hydrogen bought (kg)",
                "tank": "Hydrogen in the tank (kg)", "unserved": "Load not served (MW)", "demand": "Data centre demand (MW)",
                "price": "Import price (£/MWh)", "ci": "Grid carbon (kg CO2e/MWh)"}
KIND_WORDS = {"transcribed": "from a source", "assumed": "assumption", "proxy": "stand-in estimate",
              "constant in code": "written in the code", "recorded with the step": "written in the code",
              "Brightway": "ecoinvent score (Brightway)"}

TOKEN = re.compile(r"(?<![0-9.A-Za-z_$'!])([A-Za-z_][A-Za-z0-9_.]*)(?![A-Za-z0-9_.(])")


def chain_of(key: str) -> str:
    from optimisation import dc_model as M
    for c, keys in M.CHAINS.items():
        if key in keys:
            return c
    for c, pre in M.CHAIN_PREFIXES.items():
        if key.startswith(pre):
            return c
    if key.startswith("data centre"):
        return "data centre"
    return "other"


def amount_label(var: str, tech=None) -> str:
    m = re.fullmatch(r"(on|cap_conn)_(\d+)", var)
    if m:
        i = int(m.group(2))
        o = (getattr(tech, "connection_options", None) or ())[i] if tech is not None else None
        what = f"price list {i + 1}" + (f" ({o.key})" if o is not None else "")
        return f"Chose {what} (1 = yes)" if m.group(1) == "on" else f"Connection on {what} (MW)"
    return AMOUNTS.get(var, var)


def hourly_label(col: str) -> str:
    m = re.fullmatch(r"(imp|price|ci)_(\w+)", col)
    if m:
        base = HOURLY_NAMES[m.group(1)].split(" (")
        return f"{base[0]} at {m.group(2).replace('kV', ' kV')} ({base[1]}"
    return HOURLY_NAMES.get(col, col)


def xl_col(j: int) -> str:
    s, j = "", j + 1
    while j:
        j, r = divmod(j - 1, 26)
        s = chr(65 + r) + s
    return s


def short(text: str, n: int = 70) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


# =============================================================================
def write_book(path, wb, side, run, cfg, summary, pts, series, problems, SR, inv_rows, run_note, digest):
    import xlsxwriter
    import build_workbooks as B

    groups = (("cost_capital", "cost_operational", "cost_constant") if side == "cost"
              else ("gwp_embodied", "gwp_operational", "gwp_facility"))
    total_col = "cost_GBP_per_year" if side == "cost" else "gwp_kgco2e_per_year"
    unit_year = "£ per year" if side == "cost" else "kg CO2e per year"
    point_keys = [pt for pt, *_ in B.POINTS if pt in pts]
    first = point_keys[0]
    tech = getattr(wb, "tech", None)

    # ---- the parts of the total, by technology
    term_chain, chains = {}, {}
    for g in groups:
        for k in pts[first]["terms"][g]:
            c = chain_of(k)
            term_chain[k] = (g, c)
            chains.setdefault(c, []).append(k)
    chain_list = [c for c in CHAIN_ORDER if c in chains]

    # ---- the optimiser's figures: a figure that only points at its step is that step
    alias = {}
    for k, c in wb.lp.items():
        if c.kind == "formula" and len(c.refs) == 1 and c.formula == wb.names.get(c.refs[0]):
            alias[k] = c.refs[0]

    def cell(k):
        return wb.lp.get(k) or wb.cells.get(k) or wb.extra_inputs.get(k)

    def is_inventory(k):
        return k.startswith(("act.", "ei.", "bio."))

    def kids(k):
        c = cell(k)
        if c is None:
            return []
        if c.kind == "formula":
            out = list(c.refs)
        else:
            st = wb.steps.get(k)
            out = [u for u in (st.uses if st else []) if isinstance(u, str) and u in wb.cells]
        return [alias.get(r, r) for r in out if cell(alias.get(r, r)) is not None]

    def roots_of(chain):
        out = []
        for t in chains[chain]:
            g = term_chain[t][0]
            for pt in point_keys:
                for r in sorted(pts[pt]["terms"][g][t].refs):
                    if r.startswith("LP."):
                        out.append(alias.get(r, r))
        return list(dict.fromkeys(out))

    reach = {}
    for ch in chain_list:
        stack = roots_of(ch)
        seen = set()
        while stack:
            k = stack.pop()
            if k in seen or is_inventory(k):
                continue
            seen.add(k)
            reach.setdefault(k, set()).add(ch)
            stack += kids(k)
    owner = {k: (next(iter(s)) if len(s) == 1 else SHARED) for k, s in reach.items()}
    rooted = {r for ch in chain_list for r in roots_of(ch)}

    # ---- rows of each sheet, before anything is written
    sheets = {}            # sheet name -> list of row specs
    addr = {}              # Excel name -> (sheet, row, col)
    amount_home = {}       # amount var -> sheet

    def sname(ch):
        return CHAIN_NAMES.get(ch, ch.title())[:31]

    def tree(sheet, starts, belongs):
        rows, seen = [], set()

        def visit(k, depth):
            if k in seen or not belongs(k):
                return
            seen.add(k)
            rows.append(("figure", k, depth))
            for c in kids(k):
                if not is_inventory(c):
                    visit(c, depth + 1)
        for s in starts:
            visit(s, 0)
        return rows

    for ch in chain_list:
        sh = sname(ch)
        rows = [("title", CHAIN_NAMES.get(ch, ch)),
                ("text", "Each part below is a figure the optimiser uses x what the run built. Further down: how "
                         "each figure is made, one line per step, down to the inputs and their sources. Blue: an "
                         "input; black: a formula; shaded: worked out in the code, not as a formula. Select a number "
                         "and press Ctrl+[ to jump to what it is made from."),
                ("blank",), ("section", "What it adds to the total"),
                ("header", ["Part"] + [POINT_LABEL[p] for p in point_keys] + ["Unit", "How it is made"])]
        rows += [("term", t) for t in chains[ch]]
        rows += [("total", ch), ("blank",)]
        used = []
        for t in chains[ch]:
            g = term_chain[t][0]
            for r in sorted(pts[first]["terms"][g][t].refs):
                var = r[len(B.PT_PREFIX[first]) + 1:] if r.startswith(B.PT_PREFIX[first] + ".") else None
                if var and not var.startswith("h.") and var not in amount_home:
                    amount_home[var] = sh
                    used.append(var)
        if used:
            rows += [("section", "What the run built"),
                     ("header", ["Amount"] + [POINT_LABEL[p] for p in point_keys] + ["", "Note"])]
            rows += [("amount", v) for v in used] + [("blank",)]
        if any(".h." in r for t in chains[ch] for r in pts[first]["terms"][term_chain[t][0]][t].refs):
            rows += [("text", "The hourly parts add up the run's hourly series, on the Hourly sheet."), ("blank",)]
        rows += [("section", "How each figure is made"),
                 ("header", ["Figure", "Value", "Unit", "Made from", "Source, and where in it", "Note", "Kind", "Name"])]
        rows += tree(sh, roots_of(ch), lambda k, ch=ch: owner.get(k) == ch)
        sheets[sh] = rows

    shared_roots = [k for ch in chain_list for k in _walk(roots_of(ch), kids, is_inventory)
                    if owner.get(k) == SHARED and not any(owner.get(p) == SHARED for p in _parents(k, reach, kids))]
    if any(v == SHARED for v in owner.values()):
        sheets[SHARED] = [("title", "Shared figures"),
                          ("text", "Figures more than one technology uses, written once. Each technology's sheet points here."),
                          ("blank",),
                          ("header", ["Figure", "Value", "Unit", "Made from", "Source, and where in it", "Note", "Kind", "Name"])]
        sheets[SHARED] += tree(SHARED, list(dict.fromkeys(shared_roots)), lambda k: owner.get(k) == SHARED)
    others = [k for k in wb.order if k not in owner and not is_inventory(k)] + \
             [k for k in sorted(wb.extra_inputs) if k not in owner]
    if others:
        sheets[OTHER] = [("title", "Other figures"),
                         ("text", "Figures the code records that this run's total does not use: price lists not "
                                  "chosen, references kept beside the default, inputs to the optimiser's limits."),
                         ("blank",),
                         ("header", ["Figure", "Value", "Unit", "Made from", "Source, and where in it", "Note", "Kind", "Name"])]
        sheets[OTHER] += tree(OTHER, others, lambda k: k not in owner and not is_inventory(k))

    # assign rows and addresses
    for sh, rows in sheets.items():
        terms_rows = []
        for i, spec in enumerate(rows):
            if spec[0] == "figure":
                k = spec[1]
                nm = wb.names.get(k) if k not in wb.lp else k
                addr[nm] = (sh, i, 1)
                for a, s in alias.items():
                    if s == k:
                        addr[a] = (sh, i, 1)
            elif spec[0] == "term":
                terms_rows.append(i)
                for j, pt in enumerate(point_keys):
                    addr[f"__term.{pt}.{spec[1]}"] = (sh, i, 1 + j)
            elif spec[0] == "total":
                for j, pt in enumerate(point_keys):
                    addr[f"__total.{pt}.{spec[1]}"] = (sh, i, 1 + j)
            elif spec[0] == "amount":
                for j, pt in enumerate(point_keys):
                    addr[f"{B.PT_PREFIX[pt]}.{spec[1]}"] = (sh, i, 1 + j)
        sheets[sh] = rows

    # inventory and ecoinvent (carbon)
    inv_layout = []
    if side == "carbon":
        r = 1
        for k, n, parts in inv_rows:
            addr[wb.names.get(k)] = ("Inventory", r, 2)
            inv_layout.append((r, k, parts))
            r += len(parts) + 2
        ei_keys = sorted(k for k in wb.cells if k.startswith(("ei.", "bio.")))
        for i, k in enumerate(ei_keys, 1):
            addr[wb.names.get(k)] = ("Ecoinvent scores", i, 2)

    # summary
    summ = [("title", ("Cost" if side == "cost" else "Carbon") + " workbook: the run's total, and how every figure reaches it"),
            ("text", f"Run: {summary.get('site_name') or cfg['site'].get('name')}, {cfg['start']} to {cfg['end']}, "
                     f"{cfg['size_mw_it']:g} MW of IT load, {summary.get('label', '')}; {summary.get('cost_case', '')} "
                     f"costs; {summary.get('resample_hours') or 0.5:g}-hour steps."),
            ("text", "Start here. Each technology's line links to its sheet, which shows the parts of its total at "
                     "each point and how every figure in them is made, down to the sources. Nothing is optimised "
                     "in this workbook: what was built is the run's result, so changing an input moves the totals, "
                     "not the design."),
            ("text", "Blue numbers are inputs; black are formulas; shaded are worked out in the code, with a note "
                     "saying where. Select a number and press Ctrl+[ to jump to what it is made from."),
            ("blank",), ("header", ["Technology"] + [POINT_LABEL[p] for p in point_keys] + ["Unit"])]
    summ += [("chainrow", ch) for ch in chain_list]
    summ += [("grand",), ("runtotal",), ("diff",), ("blank",), ("section", "About the run"),
             ("runfig", "run.dt_hours", "Hours per step of the run", series.dt_hours),
             ("runfig", "run.annual_scale", "Scales the run's dates to a whole year", series.annual_scale),
             ("text", f"Run folder: {run}"),
             ("text", f"Built {time.strftime('%Y-%m-%d %H:%M')} by scripts/build_workbooks.py from the code at "
                      f"trace digest {digest}; checked by scripts/check_workbooks.py.")]
    if side == "carbon":
        summ.append(("text", "Our own inventory activities are added up from their inputs' ecoinvent scores. "
                             "Brightway scores every activity in one solve, good to about one part in ten million, "
                             "so figures built on them agree with the model to that precision."))
    if run_note:
        summ += [("blank",), ("section", "Note on the run"), ("text", run_note[0].upper() + run_note[1:] + ".")]
    if problems:
        summ += [("blank",), ("section", "Problems found while building")] + [("text", p) for p in problems]
    for i, spec in enumerate(summ):
        if spec[0] == "grand":
            for j, pt in enumerate(point_keys):
                addr[f"{B.PT_PREFIX[pt]}.{side}.total"] = (SUMMARY, i, 1 + j)
        elif spec[0] == "runfig":
            addr[spec[1]] = (SUMMARY, i, 1)

    # hourly
    hourly_cols = []
    for pt in point_keys:
        pre = B.PT_PREFIX[pt]
        refs = sorted({r for g in groups for v in pts[pt]["terms"][g].values() for r in v.refs
                       if r.startswith(f"{pre}.h.")})
        for r in refs:
            hourly_cols.append((pt, r))
    n_steps = len(pts[first]["hr"]["imp"])
    for j, (pt, r) in enumerate(hourly_cols, 1):
        addr[r] = (HOURLY, None, j)

    # ---- formula text: names to cell references
    def where(name, here):
        s, row, col = addr[name]
        if row is None:
            a = f"${xl_col(col)}$3:${xl_col(col)}${n_steps + 2}"
        else:
            a = f"{xl_col(col)}{row + 1}"
        return a if s == here else f"'{s}'!{a}"

    def to_refs(text, here):
        return TOKEN.sub(lambda m: where(m.group(1), here) if m.group(1) in addr else m.group(1), text)

    def made_from(k, here):
        parts = []
        for c in kids(k):
            nm = c if c in wb.lp else wb.names.get(c)
            if nm not in addr:
                continue
            s, row, _col = addr[nm]
            loc = f"row {row + 1}" if s == here else f"{s} row {row + 1}"
            parts.append(f"{loc} ({short(cell(c).title, 40)})")
        if not parts:
            return ""
        text = "; ".join(parts[:5]) + (f"; and {len(parts) - 5} more" if len(parts) > 5 else "")
        c = cell(k)
        return ("Worked out in the code from: " + text) if c.kind == "fixed" else text

    def words(text):
        def lab(m):
            t = m.group(1)
            if t in ("run.annual_scale",):
                return "[year scale]"
            if t == "run.dt_hours":
                return "[hours per step]"
            if t.startswith("LP."):
                c = cell(alias.get(t, t))
                return f"[{short(c.title, 45)}]" if c else t
            pre = B.PT_PREFIX[first] + "."
            if t.startswith(pre + "h."):
                return f"[hourly {hourly_label(t[len(pre) + 2:]).lower()}]"
            if t.startswith(pre):
                return f"[{amount_label(t[len(pre):], tech).lower()}]"
            return t
        s = TOKEN.sub(lab, text)
        return s.replace("SUMPRODUCT", "sum over the hours of").replace("SUM(", "sum over the hours of (").replace("*", " x ")

    # ---- write
    book = xlsxwriter.Workbook(str(path), {"strings_to_numbers": False, "strings_to_formulas": False})
    fmts = {}

    def F(kind="wrap", indent=0, bold=False):
        key = (kind, indent, bold)
        if key not in fmts:
            base = {"text_wrap": True, "valign": "top"}
            spec = {
                "wrap": {}, "small": {"font_color": "#555555"},
                "in": {"font_color": "#1F4E9E", "num_format": "#,##0.######"},
                "f": {"num_format": "#,##0.######"},
                "fx": {"bg_color": "#FCE9C8", "num_format": "#,##0.######"},
                "money": {"num_format": "#,##0"}, "moneyb": {"num_format": "#,##0", "bold": True, "top": 1},
                "amt": {"font_color": "#1F4E9E", "num_format": "#,##0.###"},
                "title": {"bold": True, "font_size": 14, "text_wrap": False},
                "section": {"bold": True, "font_size": 12, "text_wrap": False},
                "h": {"bold": True, "bg_color": "#DDE3EA", "border": 1},
                "link": {"font_color": "#1F4E9E", "underline": 1},
            }[kind]
            fm = {**base, **spec}
            if indent:
                fm["indent"] = indent
            if bold:
                fm["bold"] = True
            fmts[key] = book.add_format(fm)
        return fmts[key]

    expected = {}
    defined = []

    def define(name, sheet, row, col):
        defined.append((name, f"='{sheet}'!${xl_col(col)}${row + 1}"))

    def setup(ws, sheet):
        ws.set_column(0, 0, 62)
        ws.set_column(1, 3, 17)
        ws.set_column(4, 4, 38)
        ws.set_column(5, 5, 44)
        ws.set_column(6, 6, 22)
        ws.set_column(7, 7, 34)

    def write_rows(ws, sh, rows):
        setup(ws, sh)
        term_rows = []
        for i, spec in enumerate(rows):
            kind = spec[0]
            if kind == "title":
                ws.write(i, 0, spec[1], F("title"))
            elif kind == "section":
                ws.write(i, 0, spec[1], F("section"))
            elif kind == "text":
                ws.merge_range(i, 0, i, 5, spec[1], F("small"))
                ws.set_row(i, 30 if len(spec[1]) > 120 else None)
            elif kind == "header":
                for j, h in enumerate(spec[1]):
                    ws.write(i, j, h, F("h"))
            elif kind == "term":
                t = spec[1]
                g = term_chain[t][0]
                ws.write(i, 0, TERM_NAMES.get(t, t[:1].upper() + t[1:]), F("wrap"))
                for j, pt in enumerate(point_keys):
                    v = pts[pt]["terms"][g][t]
                    ws.write_formula(i, 1 + j, "=" + to_refs(v.text, sh), F("money"), v.val)
                    nm = B.Names().get(f"{B.PT_PREFIX[pt]}.{side}.{t}")
                    define(nm, sh, i, 1 + j)
                    expected[nm] = v.val
                ws.write(i, 1 + len(point_keys), unit_year, F("small"))
                ws.write(i, 2 + len(point_keys), words(pts[first]["terms"][g][t].text), F("small"))
                term_rows.append(i)
            elif kind == "total":
                ws.write(i, 0, f"{CHAIN_NAMES.get(spec[1], spec[1])}, total", F("wrap", bold=True))
                for j, pt in enumerate(point_keys):
                    col = xl_col(1 + j)
                    rng = f"{col}{term_rows[0] + 1}:{col}{term_rows[-1] + 1}"
                    val = sum(pts[pt]["terms"][term_chain[t][0]][t].val for t in chains[spec[1]])
                    ws.write_formula(i, 1 + j, f"=SUM({rng})", F("moneyb"), val)
                ws.write(i, 1 + len(point_keys), unit_year, F("small"))
            elif kind == "amount":
                var = spec[1]
                ws.write(i, 0, amount_label(var, tech), F("wrap"))
                for j, pt in enumerate(point_keys):
                    v = pts[pt]["sc"][var]
                    ws.write_number(i, 1 + j, v, F("amt"))
                    nm = f"{B.PT_PREFIX[pt]}.{var}"
                    define(nm, sh, i, 1 + j)
                    expected[nm] = v
                ws.write(i, 2 + len(point_keys), pts[first]["notes"].get(var, ""), F("small"))
            elif kind == "figure":
                k, depth = spec[1], spec[2]
                c = cell(k)
                nm = k if k in wb.lp else wb.names.get(k)
                root = k in rooted
                title = c.title + ("  — used by the optimiser" if root else "")
                ws.write(i, 0, title, F("wrap", indent=min(depth, 8), bold=root))
                if c.kind == "formula" and c.formula:
                    ws.write_formula(i, 1, "=" + to_refs(c.formula, sh), F("f"), c.value if c.value is not None else 0)
                    if c.how.startswith("rebuilt"):
                        ws.write_comment(i, 1, "Rebuilt by matching values: the code could not be read as a "
                                               "formula, but this gives the model's value exactly from the figures "
                                               "the step uses.")
                elif c.value is not None:
                    ws.write_number(i, 1, c.value, F("in") if c.kind == "input" else F("fx"))
                else:
                    ws.write(i, 1, "(not one number)", F("small"))
                ws.write(i, 2, c.unit or "", F("small"))
                ws.write(i, 3, made_from(k, sh), F("small"))
                src = c.source
                if src in SR.SOURCES:
                    s_ = SR.SOURCES[src]
                    src = f"{s_.title} ({s_.publisher}, {s_.date})"
                elif ";" in (src or ""):
                    src = "; ".join(SR.SOURCES[x].title if x in SR.SOURCES else x for x in src.split("; "))
                ws.write(i, 4, "; ".join(x for x in (short(src, 160), c.at) if x), F("small"))
                note = c.note or ""
                if c.kind == "fixed":
                    note = (f"Worked out in the code at {c.where}, not as a formula. " + note).strip()
                ws.write(i, 5, short(note, 400), F("small"))
                kind_words = (KIND_WORDS.get(c.grade, c.grade or "input") if c.kind == "input" else
                              "formula, matched by value" if c.how.startswith("rebuilt") else
                              "formula" if c.kind == "formula" else "worked out in the code")
                ws.write(i, 6, kind_words, F("small"))
                ws.write(i, 7, nm, F("small"))
                define(nm, sh, i, 1)
                for a, s in alias.items():
                    if s == k:
                        define(a, sh, i, 1)
                        expected[a] = c.value
                if c.value is not None:
                    expected[nm] = c.value
        ws.freeze_panes(0, 1)

    # Summary
    ws = book.add_worksheet(SUMMARY)
    ws.set_column(0, 0, 56)
    ws.set_column(1, 3, 18)
    ws.set_column(4, 5, 30)
    chain_rows = []
    for i, spec in enumerate(summ):
        kind = spec[0]
        if kind == "title":
            ws.write(i, 0, spec[1], F("title"))
        elif kind == "section":
            ws.write(i, 0, spec[1], F("section"))
        elif kind == "text":
            ws.merge_range(i, 0, i, 5, spec[1], F("small"))
            ws.set_row(i, 30 if len(spec[1]) > 110 else None)
        elif kind == "header":
            for j, h in enumerate(spec[1]):
                ws.write(i, j, h, F("h"))
        elif kind == "chainrow":
            ch = spec[1]
            ws.write_url(i, 0, f"internal:'{sname(ch)}'!A1", F("link"), string=CHAIN_NAMES.get(ch, ch))
            for j, pt in enumerate(point_keys):
                val = sum(pts[pt]["terms"][term_chain[t][0]][t].val for t in chains[ch])
                ws.write_formula(i, 1 + j, "=" + where(f"__total.{pt}.{ch}", SUMMARY), F("money"), val)
            ws.write(i, 1 + len(point_keys), unit_year, F("small"))
            chain_rows.append(i)
        elif kind == "grand":
            ws.write(i, 0, "Total, the parts added", F("wrap", bold=True))
            for j, pt in enumerate(point_keys):
                col = xl_col(1 + j)
                val = sum(v.val for g in groups for v in pts[pt]["terms"][g].values())
                ws.write_formula(i, 1 + j, f"=SUM({col}{chain_rows[0] + 1}:{col}{chain_rows[-1] + 1})", F("moneyb"), val)
                nm = f"{B.PT_PREFIX[pt]}.{side}.total"
                define(nm, SUMMARY, i, 1 + j)
                expected[nm] = float(pts[pt]["row"][total_col])
            grand_row = i
        elif kind == "runtotal":
            ws.write(i, 0, "The run's own total", F("wrap"))
            for j, pt in enumerate(point_keys):
                ws.write_number(i, 1 + j, float(pts[pt]["row"][total_col]), F("money"))
        elif kind == "diff":
            ws.write(i, 0, "Difference", F("wrap"))
            for j, pt in enumerate(point_keys):
                col = xl_col(1 + j)
                ws.write_formula(i, 1 + j, f"={col}{grand_row + 1}-{col}{grand_row + 2}", F("money"), 0.0)
        elif kind == "runfig":
            ws.write(i, 0, spec[2], F("wrap"))
            ws.write_number(i, 1, spec[3], F("in"))
            define(spec[1], SUMMARY, i, 1)
            expected[spec[1]] = spec[3]
    ws.freeze_panes(0, 1)

    for sh, rows in sheets.items():
        if sh in (SHARED, OTHER):
            continue
        write_rows(book.add_worksheet(sh), sh, rows)
    for sh in (SHARED, OTHER):
        if sh in sheets:
            write_rows(book.add_worksheet(sh), sh, sheets[sh])

    # Inventory (carbon)
    if side == "carbon":
        ws = book.add_worksheet("Inventory")
        hdr = ["Activity, and what goes into it", "", "Carbon per unit", "Unit", "", "Amount", "Unit of amount",
               "Carbon per unit of the input", "Amount x carbon"]
        for j, h in enumerate(hdr):
            ws.write(0, j, h, F("h"))
        ws.set_column(0, 0, 62)
        ws.set_column(1, 1, 2)
        ws.set_column(2, 3, 18)
        ws.set_column(4, 4, 2)
        ws.set_column(5, 8, 16)
        ws.freeze_panes(1, 0)
        for r, k, parts in inv_layout:
            c = wb.cells[k]
            name = wb.names.get(k)
            ws.write(r, 0, c.title, F("wrap", bold=True))
            ws.write(r, 3, c.unit, F("small"))
            rr = r
            for mk, amt, unit, label in parts:
                rr += 1
                ws.write(rr, 0, label, F("small", indent=1))
                ws.write_number(rr, 5, amt, F("in"))
                ws.write(rr, 6, unit, F("small"))
                ws.write_formula(rr, 7, "=" + to_refs(wb.names.get(mk), "Inventory"), F("f"), wb.cells[mk].value or 0)
                ws.write_formula(rr, 8, f"=F{rr + 1}*H{rr + 1}", F("f"), amt * (wb.cells[mk].value or 0))
            ws.write_formula(r, 2, f"=SUM(I{r + 2}:I{rr + 1})" if rr > r else "=0", F("f", bold=True), c.value or 0)
            define(name, "Inventory", r, 2)
            expected[name] = c.value
        ws = book.add_worksheet("Ecoinvent scores")
        for j, h in enumerate(["Activity or flow", "", "Carbon per unit", "Unit", "Kind", "Database", "Note"]):
            ws.write(0, j, h, F("h"))
        ws.set_column(0, 0, 80)
        ws.set_column(1, 1, 2)
        ws.set_column(2, 3, 18)
        ws.set_column(4, 6, 30)
        for i, k in enumerate(sorted(x for x in wb.cells if x.startswith(("ei.", "bio."))), 1):
            c = wb.cells[k]
            ws.write(i, 0, c.title, F("wrap"))
            ws.write_number(i, 2, c.value if c.value is not None else 0.0, F("in"))
            ws.write(i, 3, c.unit, F("small"))
            ws.write(i, 4, KIND_WORDS.get(c.grade, c.grade), F("small"))
            ws.write(i, 5, c.source, F("small"))
            ws.write(i, 6, c.note, F("small"))
            nm = wb.names.get(k)
            define(nm, "Ecoinvent scores", i, 2)
            if c.value is not None:
                expected[nm] = c.value
        ws.freeze_panes(1, 0)

    # Hourly
    if hourly_cols:
        ws = book.add_worksheet(HOURLY)
        ws.write(0, 0, "Point", F("h"))
        ws.write(1, 0, "Step", F("h"))
        ws.set_column(0, 0, 8)
        ws.set_column(1, len(hourly_cols), 20)
        for i in range(n_steps):
            ws.write_number(i + 2, 0, i + 1)
        for j, (pt, r) in enumerate(hourly_cols, 1):
            col = r[len(B.PT_PREFIX[pt]) + 3:]
            ws.write(0, j, POINT_LABEL[pt], F("h"))
            ws.write(1, j, hourly_label(col), F("h"))
            ws.write_column(2, j, [float(x) for x in B._hourly_array(pts[pt]["hr"], col)], F("in"))
            defined.append((r, f"='{HOURLY}'!${xl_col(j)}$3:${xl_col(j)}${n_steps + 2}"))
        ws.freeze_panes(2, 1)

    # Sources
    ws = book.add_worksheet("Sources")
    hdr = ["Key", "Title", "Publisher", "Date", "Kind", "Link", "Held", "Price basis", "Note"]
    for j, h in enumerate(hdr):
        ws.write(0, j, h, F("h"))
    cited = set()
    for c in list(wb.cells.values()) + list(wb.extra_inputs.values()):
        for src in (c.source or "").split("; "):
            if src in SR.SOURCES:
                cited.add(src)
    for i, key in enumerate(sorted(cited), 1):
        s = SR.SOURCES[key]
        for j, v in enumerate([key, s.title, s.publisher, s.date, s.kind, s.link, s.held, s.basis, s.note]):
            ws.write(i, j, v, F("small"))
    ws.set_column(0, 0, 28)
    ws.set_column(1, 1, 60)
    ws.set_column(2, 8, 24)
    ws.freeze_panes(1, 0)

    for name, ref in defined:
        book.define_name(name, ref)
    book.close()
    path.with_suffix(".expected.json").write_text(json.dumps(expected, indent=0), encoding="utf-8")
    return expected


def _walk(starts, kids, skip):
    out, seen, stack = [], set(), list(reversed(starts))
    while stack:
        k = stack.pop()
        if k in seen or skip(k):
            continue
        seen.add(k)
        out.append(k)
        stack += list(reversed(kids(k)))
    return out


def _parents(k, reach, kids):
    return [p for p in reach if k in kids(p)]
