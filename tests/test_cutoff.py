"""The cut-off register and the rule it is tested against.

The register (``optimiser_lca/exclusions.py``) is well-formed and names, for
every exclusion a module states in a scope dict or docstring, where that
statement is — so a new exclusion cannot be written without a register row.
``optimisation/cutoff.py`` then divides every still-excluded flow by its
technology's live coefficient: the last test is red while any flow with
status ``excluded`` breaks rule 1 or rule 2, and goes green when each has been
included (CUTOFF_RULE_PLAN.md step 5) — that red is the point.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimiser_lca import build, exclusions as X  # noqa: E402

MODULES = [n for n, _ in build.MODULES]


def test_register_is_well_formed():
    assert X.check().startswith("OK")


def test_every_stated_exclusion_is_registered():
    """Every scope-dict value that says EXCLUDED (and is not merely charged elsewhere)
    is named by an entry's `where`; every `where` resolves to something real."""
    wheres = {loc for e in X.REGISTER for loc in e.locations()}
    missing = []
    for name in MODULES:
        mod = build.load(name)
        for attr in dir(mod):
            if not attr.endswith("_SCOPE"):
                continue
            for key, text in getattr(mod, attr).items():
                if "EXCLUDED" in text and "charged" not in text and (name, attr, key) not in wheres:
                    missing.append(f"{name}.{attr}[{key!r}]: {text[:70]}")
    assert not missing, "stated exclusions with no register row:\n  " + "\n  ".join(missing)
    bad = []
    for w in wheres:
        mod_name, attr, key = w
        if mod_name not in MODULES:
            bad.append(f"{w}: {mod_name!r} is not an inventory module")
            continue
        mod = build.load(mod_name)
        src = (ROOT / "optimiser_lca" / f"{mod_name}.py").read_text(encoding="utf-8")
        if attr == "docstring":
            if key.lower() not in src.lower():
                bad.append(f"{w}: phrase not in {mod_name}.py")
        elif not hasattr(mod, attr) or key not in getattr(mod, attr):
            bad.append(f"{w}: no {attr}[{key!r}] in {mod_name}.py")
    assert not bad, "register 'where' that resolves to nothing:\n  " + "\n  ".join(bad)


def test_battery_break_even_arithmetic():
    from types import SimpleNamespace
    from optimisation import cutoff
    tech = SimpleNamespace(gwp_wind=1e4, gwp_tx_wind_per_mw=0, gwp_solar=1e4, gwp_tx_solar_per_mwp=0,
                           gwp_batt_p=3_000.0, gwp_tx_batt_per_mw=0.0, gwp_batt_e=7_000.0, gwp_ely=1e4,
                           gwp_tank=70.0, gwp_fc_bop_per_mw=5e4, gwp_fc_stack_per_mw=1e5, gwp_tx_fc_per_mw=0,
                           fc_bop_calendar_years=20, fc_stack_calendar_years=10, gwp_grid_per_mw=140.0,
                           bought_h2_gwp_per_kg=1.0, dc_fixed_gwp_per_year=1e7)
    den = cutoff.denominators(tech)
    g = X.Exclusion("battery", "x", "cutoff", side="power", method="assumed", central=100.0, upper=140.0, where=("bess",))
    share, h_star = cutoff._share(g, den, "upper", 1.0)
    assert h_star == pytest.approx((140 / 0.01 - 3_000) / 7_000)        # 1.571 h
    assert share == pytest.approx(140 / (3_000 + 7_000 * 1.0))
    f = X.Exclusion("battery", "y", "cutoff", side="energy", method="assumed", central=10.0, upper=70.0, where=("bess",))
    assert cutoff._share(f, den, "upper", 1.0) == (pytest.approx(0.01), None)
    assert den["fuel cell"]["value"] == pytest.approx(5e4 / 20 + 1e5 / 10)


def test_no_excluded_flow_breaks_the_rule():
    """Red until every failing flow is included (CUTOFF_RULE_PLAN.md step 5)."""
    from optimisation import cutoff, dc_inputs as I
    meta = {"capacity_GBP_per_MW_year": 0.0, "fixed_GBP_per_year": 0.0}
    tech = I.build_tech("london", meta, h2_colour="green")
    fails = cutoff.failures(tech)
    assert not fails, "the cut-off rule is broken by:\n  " + "\n  ".join(fails)
