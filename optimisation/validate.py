"""
Benchmarks — does the optimiser produce numbers we can defend?
=============================================================================

An optimiser that silently produces plausible-looking wrong numbers is worse
than no optimiser, because it is believed. ``tests/`` covers the model's
internal invariants — energy balances, storage is bounded, hydrogen mass is
conserved. This module covers the harder question: do the answers agree with
things established independently of the LP?

Each benchmark states what it expects and *why*, runs it, and reports pass or
fail with the numbers. ``run()`` writes ``optimisation/VALIDATION.md`` so the
table in the write-up is generated rather than transcribed.

Run:  python optimisation/validate.py
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_architectures as A
from optimisation import dc_model as M

DOC = Path(__file__).with_name("VALIDATION.md")


@dataclass
class Check:
    name: str
    expectation: str
    why: str
    passed: bool | None = None
    observed: str = ""
    detail: str = ""


CHECKS: list[Check] = []


def record(name, expectation, why, passed, observed, detail=""):
    c = Check(name, expectation, why, passed, observed, detail)
    CHECKS.append(c)
    mark = "PASS" if passed else ("SKIP" if passed is None else "FAIL")
    print(f"  [{mark}] {name}\n         {observed}")
    if detail:
        print(f"         {detail}")
    return c


# =============================================================================
def check_baseline_reproduction(series, tech):
    """grid_only must reproduce the study's own published baseline.

    baseline_grid.py computes 16,006 t CO2e/yr by a completely different route —
    a direct fixed + sum(kWh x EF) accumulation with no optimiser involved. If
    the LP disagrees, one of them is wrong, and this is the cheapest place to
    find out.
    """
    m, V, obj = M.build_model(series, A.architecture("grid_only"), tech,
                              objective="cost")
    M.solve(m)
    tot = M.totals(obj)
    mwh = float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale
    got_t = tot["gwp_kgco2e_per_year"] / 1000.0
    got_g = tot["gwp_kgco2e_per_year"] / mwh

    ref = pd.read_csv(ROOT / "optimisation_outputs" / "option_summary.csv").iloc[0]
    ref_t = float(ref.total_tco2e_yr)
    # The LP is driven from the size the user typed; baseline_grid uses the
    # foreground's own 7.3062 MW. Scale the reference to compare like with like.
    scaled = float(ref.embodied_tco2e_yr) + float(ref.operational_tco2e_yr) * (
        series.demand_mw[0] / float(ref.dc_power_kw) * 1000.0)
    err = abs(got_t - scaled) / scaled
    return record(
        "grid_only reproduces baseline_grid.py",
        "within 0.5 % of the independently computed baseline",
        "Two unrelated routes to the same number; disagreement means one is wrong.",
        err < 0.005,
        f"LP {got_t:,.0f} t/yr ({got_g:.1f} g/kWh) vs baseline {scaled:,.0f} t/yr "
        f"— {err:.3%} apart",
        f"Published baseline is {ref_t:,.0f} t/yr at {float(ref.dc_power_kw)/1000:.4f} MW.")


def check_h2_round_trip(tech):
    """The electrolyser-storage-fuel cell round trip should land near 30 %.

    A widely reported figure for a PEM-to-PEMFC chain. Well outside 25-45 %
    means an efficiency or a unit conversion is wrong somewhere in the chain,
    and every hydrogen result would inherit the error.
    """
    kwh_in_per_kg = tech.ely_kwh_per_kg + tech.tank_compression_kwh_per_kg
    kwh_out_per_kg = 1000.0 / tech.fc_kg_h2_per_mwh
    rt = kwh_out_per_kg / kwh_in_per_kg
    return record(
        "hydrogen round-trip efficiency",
        "25-45 %, and consistent with notebook 4.3",
        "A chain-wide sanity check on the efficiencies and unit conversions.",
        0.25 <= rt <= 0.45,
        f"{rt:.1%} — {kwh_in_per_kg:.1f} kWh in per kg, {kwh_out_per_kg:.1f} kWh out",
        f"{1/rt:.2f} kWh in per kWh out. This is the number that decides whether "
        "grid-charged hydrogen arbitrage can pay.")


def check_carbon_arbitrage_threshold(series, tech):
    """Grid-charged hydrogen should not pay on carbon at a GB-like site.

    Round-tripping only lowers emissions if the discharge half-hour is dirtier
    than the charge half-hour by more than the round-trip penalty. If the LP
    builds a large hydrogen chain in a min-GWP grid_h2 run despite the spread
    being below that threshold, something is wrong.
    """
    kwh_in_per_kg = tech.ely_kwh_per_kg + tech.tank_compression_kwh_per_kg
    penalty = kwh_in_per_kg * tech.fc_kg_h2_per_mwh / 1000.0
    ci = series.grid_gwp_per_mwh
    spread = np.percentile(ci, 90) / np.percentile(ci, 10)

    m, V, obj = M.build_model(series, A.architecture("grid_h2"), tech,
                              objective="gwp", ely_strategy="free")
    M.solve(m)
    built = float(V["cap_ely"].solution)
    consistent = (spread < penalty and built < 0.05) or (spread >= penalty)
    return record(
        "grid-charged hydrogen arbitrage",
        "the optimiser declines to build when the carbon spread is below the "
        "round-trip penalty",
        "An analytic prediction the LP can confirm or contradict independently.",
        consistent,
        f"penalty {penalty:.2f}x, grid p90/p10 spread {spread:.2f}x, "
        f"electrolyser built {built:.3f} MW",
        "Spread below penalty and nothing built — the prediction and the "
        "optimiser agree." if spread < penalty else
        "Spread exceeds the penalty here, so building is legitimate.")


def check_pareto_ordering(series, tech):
    """min_gwp must be cleaner than min_cost, and min_cost cheaper.

    If this fails the Pareto code is wrong. Non-negotiable.
    """
    assets = A.architecture("grid_res_battery")
    _, cheap = _solved(series, assets, tech, "cost")
    _, clean = _solved(series, assets, tech, "gwp")
    c, g = M.totals(cheap), M.totals(clean)
    ok = (g["gwp_kgco2e_per_year"] <= c["gwp_kgco2e_per_year"] + 1
          and c["cost_GBP_per_year"] <= g["cost_GBP_per_year"] + 1)
    return record(
        "Pareto ordering",
        "min_gwp GWP <= min_cost GWP, and min_cost cost <= min_gwp cost",
        "The defining property of the two anchors. Failure means the sweep is wrong.",
        ok,
        f"cheapest £{c['cost_GBP_per_year']/1e6:.2f} m / "
        f"{c['gwp_kgco2e_per_year']/1000:,.0f} t; cleanest "
        f"£{g['cost_GBP_per_year']/1e6:.2f} m / {g['gwp_kgco2e_per_year']/1000:,.0f} t")


def check_islanded_without_renewables_is_impossible(series, tech):
    """No grid and no generation cannot serve load.

    A degenerate case that must not quietly succeed. With unserved allowed the
    LP should serve nothing; the VoLL penalty makes that visible as cost rather
    than as a solver failure.
    """
    assets = M.Assets(grid=False, grid_limit_mw=0.0)
    m, V, obj = M.build_model(series, assets, tech, objective="cost",
                              unserved_fraction=1.0)
    M.solve(m)
    unserved = float(V["unserved"].solution.values.sum()) * series.dt_hours
    total = float(series.demand_mw.sum()) * series.dt_hours
    return record(
        "islanded with no generation",
        "all demand unserved, surfaced as cost rather than a solver crash",
        "A degenerate case that must fail loudly and legibly.",
        abs(unserved - total) / total < 1e-6,
        f"{unserved:,.0f} of {total:,.0f} MWh unserved "
        f"({unserved/total:.1%})")


def check_cheap_clean_grid_builds_nothing(series, tech):
    """Given a free, zero-carbon grid, the optimiser must build nothing else.

    The other degenerate direction. Anything built would mean a cost or carbon
    term is mis-signed.
    """
    import copy
    s2 = copy.copy(series)
    s2.grid_price_per_mwh = np.zeros_like(series.grid_price_per_mwh)
    s2.grid_gwp_per_mwh = np.zeros_like(series.grid_gwp_per_mwh)
    t2 = copy.copy(tech)
    t2.cost_grid_per_mw_year = 0.0
    # buy_h2 locked off: this check is about whether a free clean grid causes
    # anything to be *built*, and an unpriced colour is refused outright by
    # build_model — correctly, since free hydrogen would dominate everything.
    import dataclasses
    assets = dataclasses.replace(A.architecture("res_h2_grid"), buy_h2=False)
    m, V, obj = M.build_model(s2, assets, t2, objective="cost")
    M.solve(m)
    built = {k: float(V[k].solution) for k in
             ("cap_wind", "cap_solar", "cap_batt_e", "cap_ely", "cap_tank", "cap_fc")}
    worst = max(built.values())
    return record(
        "free zero-carbon grid",
        "nothing else is built",
        "The opposite degenerate case. Anything built means a term is mis-signed.",
        worst < 1e-4,
        f"largest capacity built {worst:.2e} "
        f"({max(built, key=built.get)})")


def check_electrolyser_embodied_against_source(tech):
    """The per-MW electrolyser figure must re-amortise to the foreground's own.

    Delegated to electrolysers.check_reconstruction, but recorded here so the
    validation table shows the whole chain rather than only the LP.
    """
    from optimisation import electrolysers as ely
    try:
        msg = ely.check_reconstruction(ely.decompose_all())
        return record("electrolyser embodied carbon", "reconstructs the foreground",
                      "Guards the decomposition every hydrogen result depends on.",
                      True, msg)
    except AssertionError as exc:
        return record("electrolyser embodied carbon", "reconstructs the foreground",
                      "Guards the decomposition every hydrogen result depends on.",
                      False, str(exc)[:200])


def check_lcoe_is_plausible(series, tech):
    """Cost per MWh delivered should land in a defensible range for GB.

    Not a precise benchmark — a smell test. A delivered cost far outside
    £60-250/MWh would mean an annualisation or a unit error.
    """
    _, obj = _solved(series, A.architecture("grid_res_battery"), tech, "cost")
    tot = M.totals(obj)
    mwh = float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale
    per_mwh = tot["cost_GBP_per_year"] / mwh
    return record(
        "delivered cost per MWh",
        "£60-250/MWh for grid + renewables + battery at min cost",
        "A units and annualisation smell test, not a precise benchmark.",
        60 <= per_mwh <= 250,
        f"£{per_mwh:.2f}/MWh delivered to IT load",
        "Grid-only delivered is £103.09/MWh including network charges.")


def check_superset_control_is_no_worse(run_dir: Path):
    """The 'everything available' control cannot be beaten by a sub-architecture.

    res_h2_grid unlocks every asset the other architectures unlock, so its
    feasible set contains theirs. At the same objective it must therefore be at
    least as good as every one of them. If a narrower architecture beats it, the
    two are not solving the same problem — a bound, a strategy or a coefficient
    differs where it should not.

    This is checked against a completed matrix rather than by solving fresh,
    because it is a property of the *set* of runs.
    """
    from optimisation import dc_runner
    if not run_dir.exists():
        return record("superset control", "control >= every sub-architecture",
                      "Catches divergent bounds or coefficients between architectures.",
                      None, f"no matrix at {run_dir.name} — run scripts/run_dc_scenarios.py")
    summaries = dc_runner.load_results(run_dir)
    df = dc_runner.comparison_table(summaries)
    ctl = df[(df.architecture == "res_h2_grid") & (df.point == "min_cost")]
    if ctl.empty:
        return record("superset control", "control >= every sub-architecture",
                      "Catches divergent bounds or coefficients between architectures.",
                      None, "scenario 21 not in the matrix")
    ctl_cost = float(ctl.cost_m_GBP_per_year.iloc[0])
    others = df[(df.point == "min_cost") & (df.architecture != "res_h2_grid")]
    # res_h2 is islanded by construction, so it is not a subset of the control.
    others = others[others.architecture != "res_h2"]
    best = others.cost_m_GBP_per_year.min()
    who = others.loc[others.cost_m_GBP_per_year.idxmin(), "label"]
    return record(
        "superset control is no worse",
        "res_h2_grid min-cost <= every non-islanded architecture's min-cost",
        "Its feasible set contains theirs, so anything else winning means the "
        "architectures disagree about a bound or a coefficient.",
        ctl_cost <= best + 1e-3,
        f"control £{ctl_cost:.3f} m vs best sub-architecture £{best:.3f} m ({who})",
        "Equality is the expected outcome — the control converges on whichever "
        "sub-architecture is genuinely best.")


def _solved(series, assets, tech, objective, **kw):
    m, V, obj = M.build_model(series, assets, tech, objective=objective, **kw)
    M.solve(m)
    return V, obj


# =============================================================================
def run(site=None, start="2025-01-01", end="2025-12-29",
        size_mw=7.31, resample_hours=1.0):
    """``site`` is anything sites.get accepts — a coordinate, a pair, a preset."""
    from optimisation import dc_inputs as I
    from optimisation import sites

    site = sites.get(site if site is not None else sites.DEFAULT_PRESET)

    print("=" * 100)
    print("VALIDATION — benchmarks the optimiser must agree with")
    print("=" * 100)
    t0 = time.time()
    series, meta = I.build_series(site, start, end, size_mw, pue=1.0)
    if resample_hours:
        series = I.resample(series, resample_hours)
    tech = I.build_tech(site, meta, size_mw_it=size_mw, pue=1.0)
    print(f"  {site.describe()}")
    print(f"  {start} to {end}, {series.n:,} steps of "
          f"{series.dt_hours:g} h, {size_mw} MW\n")

    check_electrolyser_embodied_against_source(tech)
    check_h2_round_trip(tech)
    check_baseline_reproduction(series, tech)
    check_pareto_ordering(series, tech)
    check_carbon_arbitrage_threshold(series, tech)
    check_islanded_without_renewables_is_impossible(series, tech)
    check_cheap_clean_grid_builds_nothing(series, tech)
    check_lcoe_is_plausible(series, tech)
    check_superset_control_is_no_worse(
        ROOT / "optimisation_outputs" / "dc_runs" / f"{site.key}_{size_mw:g}MW_{start[:4]}")

    passed = sum(1 for c in CHECKS if c.passed)
    failed = [c for c in CHECKS if c.passed is False]
    print(f"\n  {passed}/{len(CHECKS)} passed in {time.time() - t0:.0f} s")
    for c in failed:
        print(f"    FAILED: {c.name} — {c.observed}")

    write_doc(site.name, start, end, size_mw, series)
    print(f"\nWrote:\n  {DOC.relative_to(ROOT)}")
    return CHECKS


def write_doc(site, start, end, size_mw, series):
    passed = sum(1 for c in CHECKS if c.passed)
    lines = [
        "# Validation",
        "",
        "Generated by `optimisation/validate.py` — do not edit by hand.",
        "",
        f"Run: **{site}**, {start} to {end}, {series.n:,} steps of "
        f"{series.dt_hours:g} h, {size_mw} MW IT load.  ",
        f"Built {datetime.now(timezone.utc).isoformat(timespec='seconds')}.  ",
        f"**{passed} of {len(CHECKS)} benchmarks passed.**",
        "",
        "`tests/` covers the model's internal invariants — energy balances, storage",
        "stays bounded, hydrogen mass is conserved. These are the harder question:",
        "do the answers agree with things established independently of the LP?",
        "",
        "| Benchmark | Expected | Observed | |",
        "|---|---|---|---|",
    ]
    for c in CHECKS:
        mark = "PASS" if c.passed else ("SKIP" if c.passed is None else "**FAIL**")
        lines.append(f"| {c.name} | {c.expectation} | {c.observed} | {mark} |")
    lines += ["", "## Why each one is here", ""]
    for c in CHECKS:
        lines.append(f"**{c.name}** — {c.why}")
        if c.detail:
            lines.append(f"  {c.detail}")
        lines.append("")
    lines += [
        "## What these do not cover",
        "",
        "* **Perfect foresight.** Every result assumes the whole window is known in",
        "  advance. The numbers are an upper bound on achievable performance, not a",
        "  forecast. Running one configuration against notebook 4.3's myopic merit",
        "  order would bracket the truth; that has not been done.",
        "* **Cost inputs for the hydrogen chain.** Fuel cell and vessel capex are",
        "  assumed with no UK source and spreads of 4.5x and 2x. No benchmark here",
        "  can validate them — see `DATA_GAPS.md`.",
        "* **One site, one year.** Only the London grid series is cached. Scotland and",
        "  East England need a grid build for their regions before their results mean",
        "  anything.",
        "* **No unit commitment.** The LP may run an electrolyser at 1 % of rating.",
    ]
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
