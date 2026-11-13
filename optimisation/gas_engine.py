"""
Gas engines — the coefficients the LP charges, carbon and cost.
=============================================================================

The decision record is ``docs/GAS_ENGINE_PLAN.md``; the inventory is
``optimiser_lca/gas_engine.py`` (ecoinvent's 1 MW lean-burn gas engine set on British gas).

Carbon, split by what each part scales with (the fuel cell's pattern):

| term | scales with |
|---|---|
| running: gas supply chain, burning, exhaust, oil | MWh made |
| maintenance | MWh made (the set's maintenance over its 100,000 running hours) |
| the plant: engines, generators, controls, pads, hall | replacements, max(25 calendar years, 100,000 h) |

Cost, from DESNZ's *Unabated gas: electricity generation cost study* (CEPA and GHD, 14 Jan 2026),
Generation Option 5, reciprocating engines, 2024 prices: capital and development (land included)
on the same replacement count, with the hurdle rate carried over the build and a capital recovery
factor over 25 years; the fixed fee, the fixed part of the variable fee, insurance and business
rates per MW-year; the per-MWh part of the variable fee, the gas and the carbon price per MWh.

``ge_units >= max(cap_ge / 25, MWh / 100,000)``; the LP charges
``A (finance x CRF - 1/25) cap_ge + opex cap_ge + A ge_units`` — at the calendar floor exactly the
annuity, and the replacements when the engines run more than 4,000 h a year (the fuel cell's
balance-of-plant rule, ``h2_capex.fuel_cell_cost``).

Run:  python optimisation/gas_engine.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"

from optimisation import price_base as P  # noqa: E402
from optimisation import tech_costs as tc  # noqa: E402
from optimisation import trace as T  # noqa: E402

CACHE_PATH = OUT_DIR / "gas_engine_decomposition_cache.json"
_MEMO: dict | None = None

CASES = ("low", "central", "high")

# --- DESNZ 2026, Generation Option 5, reciprocating engines, 2024 prices ---------
PRICE_YEAR = 2024
CALENDAR_YEARS = 25.0                                        # Table 3.23, operation, medium
CAPEX_GBP_PER_KW = {"low": 450.0, "central": 529.0, "high": 609.0}          # Table 3.25, capital cost
DEV_GBP_PER_KW = {"low": 12.7, "central": 29.5, "high": 34.6}     # Table 3.25 / 5.4, development, land included
FIXED_FEE_GBP_PER_MW_YEAR = {"low": 12_400.0, "central": 14_630.0, "high": 16_820.0}  # Table 3.27
VARIABLE_500H_GBP_PER_MWH = {"low": 5.72, "central": 6.73, "high": 7.74}     # Table 3.27, 500 h
VARIABLE_1500H_GBP_PER_MWH = {"low": 3.45, "central": 4.06, "high": 4.67}    # Table 3.28, 1,500 h
INSURANCE_FRAC_OF_CAPITAL = {"low": 0.003, "central": 0.004, "high": 0.005}  # Tables 3.27-3.28
BUILD_YEARS = {"low": 0.4, "central": 1.0, "high": 1.3}                     # Table 3.23, construction
# CEPA for DESNZ 2025, Table E.1, "Gas generation - unabated" (its glossary: CCGT, OCGT and gas
# reciprocating engines), 8.90 %, pre-tax real.
DISCOUNT_RATE = 0.089


def variable_fee_split(case: str) -> tuple[float, float]:
    """(GBP per MW-year, GBP per MWh): the line through the study's 500 h and 1,500 h rows.

    The study prices the variable fee per MWh at 500 h and at 1,500 h a year, lower at the higher
    hours; a fixed part plus a per-MWh part reproduces both rows exactly, and is extrapolated beyond
    1,500 h when the engines run more."""
    e500, e1500 = 500.0 * VARIABLE_500H_GBP_PER_MWH[case], 1500.0 * VARIABLE_1500H_GBP_PER_MWH[case]
    per_mwh = (e1500 - e500) / 1000.0
    return e500 - per_mwh * 500.0, per_mwh


# =============================================================================
# Carbon
# =============================================================================
def _gwp_method(bd):
    return next(m for m in bd.methods
                if m[1] == "IPCC 2021" and m[2] == "climate change"
                and "GWP100" in str(m) and "no LT" not in str(m))


def _method(H, bd):
    """The method lca_helpers scores with, after its setup has set the project.

    Not a fresh search of ``bd.methods``: a test that left Brightway on another project made that
    search return a method whose factors keyed different flows (the reconciliation read 8.7 kg/m3)."""
    return getattr(H, "method", None) or _gwp_method(bd)


def _factors(bd, method) -> dict:
    return {k if not isinstance(k, list) else tuple(k): v for k, v in bd.Method(method).load()}


def _cf(cf: dict, flow) -> float:
    """The method's factor for a biosphere flow, by node id or by key, whichever the method stores."""
    return float(cf.get(flow.id, cf.get(flow.key, 0.0)))


def decompose(use_cache: bool = True, refresh: bool = False) -> dict:
    """Score the three activities: running and maintenance per MWh, the plant per MW."""
    global _MEMO
    if refresh:
        _MEMO = None
        CACHE_PATH.unlink(missing_ok=True)
    if _MEMO is None and use_cache and CACHE_PATH.exists():
        try:
            _MEMO = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            _MEMO = None
    if _MEMO is None:
        _MEMO = _score()
        OUT_DIR.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(_MEMO, indent=2), encoding="utf-8")
    _with_constants(_MEMO)
    if T.active():
        _trace(_MEMO)
    return _MEMO


def _with_constants(d: dict) -> dict:
    """Overlay the inventory module's constants on the cache, as ``fuel_cell._with_calendar_lives`` does:
    they are parameters, not scores, so an edited constant must reach both objectives without a rescore."""
    from optimiser_lca import gas_engine as inv
    d["duty_hours"] = inv.GE_UNIT_LIFE_H
    d["gas_m3_per_MWh"] = inv.GE_GAS_M3_PER_KWH * 1000.0
    d["gas_MWh_HHV_per_MWh"] = inv.GE_GAS_MWH_HHV_PER_MWH
    d["co2_kg_per_MWh"] = inv.GE_CO2_KG_PER_KWH * 1000.0
    return d


def _score() -> dict:
    import bw2data as bd
    import lca_helpers as H
    from optimiser_lca import gas_engine as inv
    from optimiser_lca import registry as R

    H.setup_brightway()
    method = _method(H, bd)
    cf = _factors(bd, method)
    op = bd.get_activity((R.GAS_ENGINE_DB, R.GE_OP))
    maint = bd.get_activity((R.GAS_ENGINE_DB, R.GE_MAINT))
    plant = bd.get_activity((R.GAS_ENGINE_DB, R.GE_PLANT))

    parts = {"gas supply chain": 0.0, "burning and exhaust": 0.0, "oil": 0.0}
    for e in op.technosphere():
        score = H.run_lca_score(e.input, method) * float(e["amount"])
        parts["gas supply chain" if "natural gas" in e.input["name"] else "oil"] += score
    for e in op.biosphere():
        parts["burning and exhaust"] += _cf(cf, e.input) * float(e["amount"])
    plant_parts = {}
    for e in plant.technosphere():
        plant_parts[e.input["name"]] = H.run_lca_score(e.input, method) * float(e["amount"])
    out = {
        "running_kgco2e_per_MWh": H.run_lca_score(op, method) * 1000.0,
        "running_parts_kgco2e_per_MWh": {k: v * 1000.0 for k, v in parts.items()},
        "maintenance_kgco2e_per_MWh": H.run_lca_score(maint, method) * 1000.0,
        "plant_kgco2e_per_MW": H.run_lca_score(plant, method),
        "plant_parts_kgco2e_per_MW": plant_parts,
        "gas_m3_per_MWh": inv.GE_GAS_M3_PER_KWH * 1000.0,
        "gas_MWh_HHV_per_MWh": inv.GE_GAS_MWH_HHV_PER_MWH,
        "co2_kg_per_MWh": inv.GE_CO2_KG_PER_KWH * 1000.0,
        "duty_hours": inv.GE_UNIT_LIFE_H,
        # ecoinvent's engine as published, then each edit, kg CO2e per m3 (``reconcile``), scored with the rest
        "reconciliation_kgco2e_per_m3": reconcile(),
    }
    return out


def _trace(d: dict) -> None:
    """Record the decomposed figures for the LCA map (``optimisation.trace``)."""
    from optimiser_lca import gas_engine as inv
    from optimiser_lca import registry as R
    op, maint, plant = (T.activity(R.GAS_ENGINE_DB, R.GE_OP), T.activity(R.GAS_ENGINE_DB, R.GE_MAINT),
                        T.activity(R.GAS_ENGINE_DB, R.GE_PLANT))
    T.step("gas_engine.running_per_MWh", d["running_kgco2e_per_MWh"], "kg CO2e per MWh",
           "Running the engines: British gas's supply chain, burning, exhaust and oil, per MWh made",
           uses=[op], scores=op, factor=1000.0, grade="derived",
           inputs={"gas_m3_per_MWh": d["gas_m3_per_MWh"], "efficiency_net": inv.GE_ETA_NET_LHV},
           source="ecoinvent 3.9.1 lean-burn 1 MW engine on GB high-pressure gas; DESNZ 2026 Table 3.24")
    T.step("gas_engine.maintenance_per_MWh", d["maintenance_kgco2e_per_MWh"], "kg CO2e per MWh",
           "The engine set's maintenance over its 100,000 running hours, per MWh made",
           uses=[maint], scores=maint, factor=1000.0, grade="derived")
    T.step("gas_engine.plant_per_MW", d["plant_kgco2e_per_MW"], "kg CO2e per MW",
           "One MW of engines, generators, controls, pads and steel hall, built", uses=[plant], scores=plant,
           grade="derived", inputs={"hall_m2_per_MW": inv.GE_HALL_M2_PER_MW})
    T.step("gas_engine.calendar_years", CALENDAR_YEARS, "years", "Engine plant calendar life",
           grade="transcribed", source="DESNZ 2026 unabated gas study, Table 3.23, operation, medium")
    T.step("gas_engine.duty_hours", d["duty_hours"], "hours", "Engine running life",
           grade="transcribed", source="ecoinvent Jakobsberg comments '100'000 h'; DESNZ 2026 §3.5 ~100,000 h")


def burden_kgco2e_per_year(cap_mw: float, mwh_per_year: float) -> dict:
    """Carbon of a plant of ``cap_mw`` making ``mwh_per_year``, on the max(calendar, duty) rule."""
    d = decompose()
    h = mwh_per_year / cap_mw if cap_mw else 0.0
    units = cap_mw * max(1.0 / CALENDAR_YEARS, h / d["duty_hours"])
    return {"plant": d["plant_kgco2e_per_MW"] * units,
            "running": d["running_kgco2e_per_MWh"] * mwh_per_year,
            "maintenance": d["maintenance_kgco2e_per_MWh"] * mwh_per_year,
            "units_per_year": units, "binding": "duty" if h > d["duty_hours"] / CALENDAR_YEARS else "calendar"}


def reconcile() -> list[tuple[str, float]]:
    """ecoinvent's lean-burn engine, per m3 of gas burned (no construction), edit by edit to ours.

    Each row is kg CO2e per m3 after that edit; the last equals the running activity per m3."""
    import bw2data as bd
    import lca_helpers as H
    from optimiser_lca import gas_engine as inv

    H.setup_brightway()
    method = _method(H, bd)
    cf = _factors(bd, method)
    ei = bd.Database(H.EI_DB_NAME) if hasattr(H, "EI_DB_NAME") else next(
        bd.Database(n) for n in bd.databases if "ecoinvent" in n and "biosphere" not in n)
    # By name, location AND product: ecoinvent has a heat and an electricity activity under this name and
    # location, and which one a name-only search meets first depends on the database's iteration order.
    lb = [a for a in ei if a["name"] == "heat and power co-generation, natural gas, 1MW electrical, lean burn"
          and a["location"] == "Europe without Switzerland"
          and a["reference product"] == "heat, district or industrial, natural gas"]
    assert len(lb) == 1, f"lean-burn engine (heat) should match once, matched {len(lb)}"
    lb = lb[0]
    gas_m3 = inv.LB_GAS_M3_PER_MJ
    bio = {}
    for e in lb.biosphere():
        bio.setdefault(e.input["name"], []).append((float(e["amount"]) / gas_m3, _cf(cf, e.input)))
    tech = {e.input["name"]: (e.input, float(e["amount"]) / gas_m3) for e in lb.technosphere()
            if "construction" not in e.input["name"]}
    eu_gas = H.run_lca_score(tech["market group for natural gas, high pressure"][0], method)
    oil = sum(H.run_lca_score(a, method) * amt for n, (a, amt) in tech.items() if "oil" in n)
    burn = sum(a * f for rows in bio.values() for a, f in rows)
    gb = next(a for a in ei if a["name"] == "market for natural gas, high pressure" and a["location"] == "GB"
              and a["reference product"] == "natural gas, high pressure")
    gb_gas = H.run_lca_score(gb, method)
    co2_f = next(f for a, f in bio["Carbon dioxide, fossil"])
    co2_lb = sum(a for a, _ in bio["Carbon dioxide, fossil"])
    co2_ours = inv.GE_CO2_KG_PER_KWH / inv.GE_GAS_M3_PER_KWH
    net_ch4 = inv.LB_CH4_NETWORK_PER_MJ / gas_m3 * next(f for a, f in bio["Methane, fossil"])
    rows = [("ecoinvent lean-burn engine, as published (European gas)", eu_gas + burn + oil)]
    rows.append(("British high-pressure gas for European", rows[-1][1] - eu_gas + gb_gas))
    rows.append(("CO2 from the gas's carbon balance", rows[-1][1] + (co2_ours - co2_lb) * co2_f))
    rows.append(("low-pressure network methane out", rows[-1][1] - net_ch4))
    return rows


# =============================================================================
# Cost
# =============================================================================
def cost(case: str) -> dict:
    """One case, each number recorded for the cost map, in 2025 pounds."""
    from optimisation import h2_capex as hc
    if case not in CASES:
        raise ValueError(f"case must be one of {CASES}, got {case!r}")
    loc = "Generation Option 5, reciprocating engines"
    cite = "desnz_unabated_gas_2026"
    capex = T.cost("cost.gas_engine.capex_per_kW", CAPEX_GBP_PER_KW[case], "GBP per kW (2024)",
                   "Capital cost of a 20 MW gas engine plant, turnkey, excluding connections", grade="transcribed",
                   cites=[(cite, f"Table 3.25, {loc}, capital cost, {case}; Table 5.4 excl. connections")])
    dev = T.cost("cost.gas_engine.development_per_kW", DEV_GBP_PER_KW[case], "GBP per kW (2024)",
                 "Development cost, land included", grade="transcribed",
                 cites=[(cite, f"Table 3.25, project development, {case}; Table 5.4, development costs (incl. land)")],
                 note="Land is sourced here, so it is in (the cost rule; user, 13 Nov 2026): about GBP 4-22/kW of it. "
                      "Spread over 25 years with the capital, as the study's own cost basis does, though land does "
                      "not wear out")
    to25 = P.to_2025(PRICE_YEAR)
    life = T.cost("cost.gas_engine.life_years", CALENDAR_YEARS, "years",
                  "Engine plant calendar life, the life the carbon side replaces it on", grade="transcribed",
                  cites=[(cite, "Table 3.23, operation, medium 25 years")])
    rate = T.cost("cost.gas_engine.discount_rate", DISCOUNT_RATE, "fraction per year",
                  "CEPA's hurdle rate for unabated gas generation, pre-tax real", grade="transcribed",
                  cites=[("cepa_hurdle_rates_2025", "Table E.1, gas generation - unabated, 8.90 %")],
                  note="CEPA's glossary defines the row as CCGT, OCGT and gas reciprocating engines")
    crf = T.cost("cost.gas_engine.crf", tc.capital_recovery_factor(rate, life), "per year",
                 "Capital recovery factor over the plant's life",
                 uses=["cost.gas_engine.discount_rate", "cost.gas_engine.life_years"])
    build = T.cost("cost.gas_engine.construction_years", BUILD_YEARS[case], "years", "Construction period",
                   grade="transcribed", cites=[(cite, f"Table 3.23, construction, {case}")])
    finance = T.cost("cost.gas_engine.building_finance_factor", tc.building_finance_factor(rate, max(build, 1.0)),
                     "multiplier", "Capital carried at the rate over the build",
                     uses=["cost.gas_engine.discount_rate", "cost.gas_engine.construction_years"],
                     note="A build under a year is carried as one, the shortest the study's finance factor takes")
    fixed_fee = T.cost("cost.gas_engine.fixed_fee_per_MW_year", FIXED_FEE_GBP_PER_MW_YEAR[case],
                       "GBP per MW per year (2024)", "Fixed fee: core engine and generator costs", grade="transcribed",
                       cites=[(cite, f"Table 3.27, fixed fee, {case}")],
                       note="The study's fee covers the engines and generators only (p. 32), not staffing or site upkeep")
    var_fixed, var_mwh = variable_fee_split(case)
    var_fixed = T.cost("cost.gas_engine.variable_fee_fixed_part", var_fixed, "GBP per MW per year (2024)",
                       "Fixed part of the variable fee: the line through the 500 h and 1,500 h rows", grade="derived",
                       cites=[(cite, f"Tables 3.27 and 3.28, variable fee, {case}")])
    var_mwh = T.cost("cost.gas_engine.variable_fee_per_MWh", var_mwh, "GBP per MWh (2024)",
                     "Per-MWh part of the variable fee: the line through the 500 h and 1,500 h rows", grade="derived",
                     cites=[(cite, f"Tables 3.27 and 3.28, variable fee, {case}")],
                     note="Extrapolated beyond the study's 1,500 h when the engines run more")
    insurance = T.cost("cost.gas_engine.insurance_frac", INSURANCE_FRAC_OF_CAPITAL[case],
                       "fraction of capital per year", "Insurance", grade="transcribed",
                       cites=[(cite, f"Table 3.27, insurance, {case}")])
    rates = hc.rates_frac()
    a_kw = (capex + dev) * to25
    a = T.cost("cost.gas_engine.capital_per_MW", a_kw * 1000.0, "GBP per MW replaced",
               "Capital and development, 2025 pounds, charged per replacement",
               uses=["cost.gas_engine.capex_per_kW", "cost.gas_engine.development_per_kW", f"price_base.{PRICE_YEAR}_to_2025"])
    opex = T.cost("cost.gas_engine.fixed_opex_per_MW_year",
                  (fixed_fee + var_fixed) * to25 + (insurance + rates) * a, "GBP per MW per year",
                  "Fixed fee, the variable fee's fixed part, insurance and business rates",
                  uses=["cost.gas_engine.fixed_fee_per_MW_year", "cost.gas_engine.variable_fee_fixed_part",
                        "cost.gas_engine.insurance_frac", "cost.hydrogen_plant.rates_frac",
                        "cost.gas_engine.capital_per_MW", f"price_base.{PRICE_YEAR}_to_2025"])
    annual = T.cost("cost.gas_engine.annual_per_MW", a * (finance * crf - 1.0 / life) + opex, "GBP per MW per year",
                    "Capital recovery (the first build carrying its finance) and fixed opex, less the calendar "
                    "replacement the LP charges per replacement",
                    uses=["cost.gas_engine.capital_per_MW", "cost.gas_engine.crf", "cost.gas_engine.building_finance_factor",
                          "cost.gas_engine.fixed_opex_per_MW_year", "cost.gas_engine.life_years"])
    var = T.cost("cost.gas_engine.maintenance_per_MWh", var_mwh * to25, "GBP per MWh",
                 "Running maintenance per MWh, 2025 pounds",
                 uses=["cost.gas_engine.variable_fee_per_MWh", f"price_base.{PRICE_YEAR}_to_2025"])
    return {"asset": "gas_engine", "case": case, "capital_GBP_per_MW": a, "annual_GBP_per_MW_year": annual,
            "maintenance_GBP_per_MWh": var, "lifetime_years": life, "discount_rate": rate}


def costs():
    import pandas as pd
    with T.quiet():
        return pd.DataFrame([cost(c) for c in CASES])


def run():
    d = decompose()
    print("GAS ENGINES - carbon, split by what it scales with")
    print(f"  running      {d['running_kgco2e_per_MWh']:8.1f} kg CO2e/MWh  "
          + ", ".join(f"{k} {v:.1f}" for k, v in d["running_parts_kgco2e_per_MWh"].items()))
    print(f"  maintenance  {d['maintenance_kgco2e_per_MWh']:8.2f} kg CO2e/MWh")
    print(f"  plant        {d['plant_kgco2e_per_MW'] / 1000:8.1f} t CO2e/MW, on max({CALENDAR_YEARS:.0f} y, "
          f"{d['duty_hours']:,.0f} h)")
    for k, v in d["plant_parts_kgco2e_per_MW"].items():
        print(f"      {v / 1000:8.2f} t  {k}")
    print("\nReconciliation, kg CO2e per m3 of gas burned")
    for name, v in reconcile():
        print(f"  {v:8.4f}  {name}")
    print("\nCost, 2025 pounds")
    print(costs().to_string(index=False))


if __name__ == "__main__":
    run()
