"""The equations page must keep up with the code (19 Nov 2026).

docs/model_equations_explorer.html is written by hand. The 19 Nov code check
went from the page to the code, which can't find a term the page never shows:
the connection options' own prices had been in the objective since 30 Oct
without the page saying so. These checks go the other way, from the code to
the page:

1. Every cost and carbon breakdown line dc_model reports, with connection
   options off and on, is listed in the page's TERMKEYS against the symbols
   that write it, and those symbols are in an equation on the same side.
2. Every coefficient those breakdowns read (Tech fields, ConnectionOption
   fields, the voltage-group series and Series fields) is named in some
   symbol's "In the code" field.
3. The numbers the Pareto text quotes (default steps, the loose gap) match.

Nothing here solves a model: the breakdown is evaluated on zeros.
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from optimisation import dc_model as M              # noqa: E402
from optimisation import dc_pareto as P             # noqa: E402
# The toy series, Tech and two options of the connection-choice tests.
from test_connection_choice import GROUPS, LARGE, SMALL, _series, _tech  # noqa: E402

PAGE = ROOT / "docs" / "model_equations_explorer.html"
SIDES = {"cost": ("cost_capital", "cost_operational"),
         "gwp": ("gwp_embodied", "gwp_operational", "gwp_facility")}
# Fields that pick or label rather than price anything.
NOT_COEFFICIENTS = {"labels", "group", "n"}


@pytest.fixture(scope="module")
def page() -> str:
    return PAGE.read_text(encoding="utf-8")


def _json_const(page: str, name: str):
    m = re.search(rf"const {name} = (\{{.*?\}});\n", page)
    assert m, f"the page has no one-line `const {name} = {{...}};`"
    return json.loads(m.group(1))


def _terms(page: str) -> dict:
    """TERMS: symbol key -> its "In the code" text."""
    block = page.split("const TERMS = {", 1)[1].split("\n};", 1)[0]
    return {k: c for k, c in re.findall(r"^\s*(\w+):\{s:.*?,c:'((?:[^'\\]|\\.)*)'", block, re.M)}


def _equations(page: str) -> dict:
    """EQ: equation key -> its source text."""
    block = page.split("const EQ = {", 1)[1].split("\n};", 1)[0]
    return dict(re.findall(r"^ (\w+): R`(.*)`,?$", block, re.M))


def _side_of_eq(page: str) -> dict:
    block = re.search(r"const SIDE_OF_EQ = \{(.*?)\};", page, re.S).group(1)
    return {k: {"lca": "gwp"}.get(v, v) for k, v in re.findall(r"(\w+):'(cost|lca)'", block)}


class _Zeros(dict):
    """Every LP variable objective_terms asks for, as a zero series."""
    def __init__(self, n, **kw):
        super().__init__(**kw)
        self.n = n

    def __missing__(self, key):
        return np.zeros(self.n)


def _breakdown_keys() -> dict:
    """{side: every line name the cost and carbon breakdowns can report}."""
    keys = {side: set() for side in SIDES}
    single = (_series(), _tech())
    s = _series(7.31, GROUPS)
    t = _tech(connection_options=(SMALL, LARGE))
    options = (s, t)
    for series, tech in (single, options):
        q = _Zeros(series.n)
        if M.connection_options_of(tech):
            q.update({f"on_{i}": 0.0 for i in range(2)})
        terms = M.objective_terms(q, series, tech, price=np.asarray(series.grid_price_per_mwh),
                                  ci=np.asarray(series.grid_gwp_per_mwh))
        for side, groups in SIDES.items():
            for g in groups:
                keys[side] |= set(terms.get(g, {}))
    keys["gwp"] |= set(M.facility_terms(single[1], 1.0))
    # Lines contributions() adds for the constants (the fixed connection charge
    # with one price list, major-hazard compliance), read from its source.
    for group, key in re.findall(r'terms\["(\w+)"\]\["([^"]+)"\]\s*=', inspect.getsource(M.contributions)):
        keys["cost" if group.startswith("cost") else "gwp"].add(key)
    return keys


def test_every_breakdown_line_is_on_the_page(page):
    termkeys = _json_const(page, "TERMKEYS")
    code = _breakdown_keys()
    for side in SIDES:
        missing = sorted(code[side] - set(termkeys[side]))
        stale = sorted(set(termkeys[side]) - code[side])
        assert not missing, f"{side} lines the code reports but the page's TERMKEYS lacks: {missing}"
        assert not stale, f"{side} lines in the page's TERMKEYS the code no longer reports: {stale}"


def test_each_line_is_written_by_symbols_in_an_equation_on_its_side(page):
    termkeys = _json_const(page, "TERMKEYS")
    terms, eqs, side_of = _terms(page), _equations(page), _side_of_eq(page)
    for side, lines in termkeys.items():
        text = " ".join(src for k, src in eqs.items() if side_of.get(k) == side)
        for line, symbols in lines.items():
            assert symbols, f"{side} line {line!r} names no symbol"
            for sym in symbols:
                assert sym in terms, f"{side} line {line!r}: symbol {sym!r} is not in TERMS"
                assert f"T('{sym}'" in text, (
                    f"{side} line {line!r}: symbol {sym!r} is in no {side} equation")


def _coefficients() -> set:
    """Fields the breakdowns read: tech.X, o.X (an option), d["X"] (a voltage group), series.X."""
    src = "\n".join(inspect.getsource(f) for f in (
        M.objective_terms, M.objective_constants, M.major_hazard_cost, M.facility_terms))
    src = "\n".join(line.split("#", 1)[0] for line in src.splitlines())      # code, not comments
    names = set(re.findall(r"\btech\.(\w+)", src)) | set(re.findall(r"\bo\.(\w+)", src))
    names |= set(re.findall(r'\bd\["(\w+)"\]', src)) | set(re.findall(r"\bseries\.(\w+)", src))
    return names - NOT_COEFFICIENTS


def test_every_coefficient_is_named_in_the_code_fields(page):
    code_text = " ".join(_terms(page).values())
    missing = sorted(n for n in _coefficients() if not re.search(rf"\b{n}\b", code_text))
    assert not missing, f"read by the objective but named in no symbol's 'In the code' field: {missing}"


def test_the_option_prices_are_covered(page):
    # The reason this file exists: the four per-option prices and the two
    # voltage-group series must stay findable on the page.
    code_text = " ".join(_terms(page).values())
    for name in ("cost_per_mw_year", "cost_fixed_per_year", "gwp_per_mw_year", "gwp_fixed_per_year",
                 "grid_groups", "price_per_mwh", "gwp_per_mwh"):
        assert re.search(rf"\b{name}\b", code_text), name
    assert {"cost_per_mw_year", "cost_fixed_per_year", "gwp_fixed_per_year"} <= _coefficients()


def test_the_pareto_text_quotes_the_code(page):
    assert f"{P.DEFAULT_POINTS} by default" in page
    gap = f"{M.LOOSE_MIP_REL_GAP * 100:g} %"
    assert gap in page and "LOOSE_MIP_REL_GAP" in page, gap
    assert "eps_fracs" in page
    # The connection tie-break runs at the two ends only.
    src = inspect.getsource(P.front)
    assert src.count("_tie_break(") == 2, "dc_pareto.front's tie-breaks changed: re-read the page's Step 1 and 2"
