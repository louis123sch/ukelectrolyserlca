"""
The other bound — dispatch with no foresight at all.
=============================================================================

Every LP result assumes the whole window is known in advance. The optimiser
electrolyses in March surplus *because* it knows a November lull is coming. No
operator has that forecast, so the LP is an **upper bound** on what a build can
achieve, not a prediction of what it will.

This module is the opposite bound: the same installed capacities dispatched by
a fixed merit order that sees only the current step, which is what
``4.3.wind_h2_storage_system.ipynb`` does. Run a configuration both ways and the
truth is bracketed — the LP above, the merit order below, and a real operator
with a decent day-ahead forecast somewhere in between.

The merit order, unchanged from notebook 4.3
--------------------------------------------
Per step:

1. renewables serve the data centre first
2. surplus charges the battery, then makes hydrogen, then is curtailed
3. shortfall is covered by the battery, then the fuel cell, then the grid
4. anything left is unserved

That is what a price-taking plant with a fixed load and no forecast actually
does. It is not a strawman — it is the incumbent method in this repo, and the
gap between it and the LP is the value of foresight, expressed in tonnes and
pounds.

**This does not re-size anything.** Capacities come in fixed, from an LP
solution, so the comparison isolates *dispatch* rather than confounding it with
a different build.

Run:  python optimisation/myopic.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_model as M


def dispatch(series: M.Series, tech: M.Tech, caps: dict,
             initial_soc_frac: float = 0.5,
             initial_tank_frac: float = 0.5,
             buy_h2: bool = False) -> pd.DataFrame:
    """Chronological merit-order dispatch of a fixed build. No foresight.

    Storage starts part-full because a myopic operator has no reason to start
    empty and no way to plan a cyclic year. That is a real difference from the
    LP, which enforces a cyclic constraint, and it is stated rather than hidden:
    the myopic run is allowed to end the year emptier than it started, which
    flatters it slightly. The bracket is still valid — it makes the lower bound
    a little generous, not a little harsh.

    ``buy_h2``: the build may buy hydrogen (first stream). A fuel cell short of
    stored hydrogen buys the rest at the gate, as an operator with a supply
    contract would; nothing is bought to fill the tank ahead of need, since
    that would take a forecast.
    """
    dt = series.dt_hours
    n = series.n
    eta = float(np.sqrt(tech.batt_rte))
    kg_per_mwh_in = 1000.0 / (tech.ely_kwh_per_kg + tech.tank_compression_kwh_per_kg)
    # The same standing losses the LP applies, per step on the stock held.
    keep_b = 1.0 - tech.batt_leakage_per_hour * dt
    keep_h = 1.0 - tech.tank_leakage_per_hour * dt

    cap_w = caps.get("cap_wind", 0.0) + caps.get("cap_offshore", 0.0)
    cap_s = caps.get("cap_solar", 0.0)
    cap_bp, cap_be = caps.get("cap_batt_p", 0.0), caps.get("cap_batt_e", 0.0)
    cap_ely, cap_tank = caps.get("cap_ely", 0.0), caps.get("cap_tank", 0.0)
    cap_fc, cap_grid = caps.get("cap_fc", 0.0), caps.get("cap_grid", 0.0)

    # The same transformer losses the LP applies: generation delivered net of
    # its step-up, imports net of the intake, the battery's and fuel cell's
    # output net of their container units (the battery's charge drawn grossed
    # up by its), and every unit's no-load loss added to what the site must
    # serve — the fuel cell's unit included, energised on standby.
    lf = M.loss_factors(series, tech)
    avail = ((1.0 - lf["wind"]) * series.cf_wind * cap_w
             + (1.0 - lf["solar"]) * series.cf_solar * cap_s)
    noload = (tech.loss_wind_noload * cap_w + tech.loss_solar_noload * cap_s
              + tech.loss_grid_noload * cap_grid
              + tech.loss_batt_noload * cap_bp + tech.loss_fc_noload * cap_fc)
    demand = series.demand_mw + noload
    eta_imp = 1.0 - lf["grid"]
    eta_bt, eta_ft = 1.0 - lf["battery"], 1.0 - lf["fc"]

    soc = initial_soc_frac * cap_be
    tank = initial_tank_frac * cap_tank
    out = {k: np.zeros(n) for k in
           ("direct", "ch", "dis", "soc", "p_ely", "tank", "p_fc", "h2_buy",
            "imp", "unserved", "curtailed")}

    for i in range(n):
        soc *= keep_b
        tank *= keep_h
        gen = avail[i]
        need = demand[i]

        direct = min(gen, need)
        surplus = gen - direct
        short = need - direct

        # 2. surplus: battery, then hydrogen, then curtail
        ch = 0.0
        if surplus > 0 and cap_be > 0:
            ch = min(surplus * eta_bt, cap_bp, (cap_be - soc) / eta / dt)
            soc += ch * eta * dt
            surplus -= ch / eta_bt
        p_ely = 0.0
        if surplus > 0 and cap_ely > 0 and cap_tank > 0:
            room_kg = cap_tank - tank
            p_ely = min(surplus, cap_ely, room_kg / kg_per_mwh_in / dt)
            tank += p_ely * kg_per_mwh_in * dt
            surplus -= p_ely

        # 3. shortfall: battery, then fuel cell, then grid
        dis = 0.0
        if short > 0 and cap_be > 0:
            dis = min(short / eta_bt, cap_bp, soc * eta / dt)
            soc -= dis / eta * dt
            short -= dis * eta_bt
        p_fc = h2_buy = 0.0
        if short > 0 and cap_fc > 0:
            if buy_h2:
                p_fc = min(short / eta_ft, cap_fc)
                need_kg = p_fc * tech.fc_kg_h2_per_mwh * dt
                from_tank = min(tank, need_kg)
                h2_buy = need_kg - from_tank
                tank -= from_tank
            else:
                p_fc = min(short / eta_ft, cap_fc, tank / tech.fc_kg_h2_per_mwh / dt)
                tank -= p_fc * tech.fc_kg_h2_per_mwh * dt
            short -= p_fc * eta_ft
        imp = min(short / eta_imp, cap_grid) if short > 0 else 0.0
        short -= imp * eta_imp

        out["direct"][i] = direct; out["ch"][i] = ch; out["dis"][i] = dis
        out["p_ely"][i] = p_ely; out["p_fc"][i] = p_fc; out["imp"][i] = imp
        out["h2_buy"][i] = h2_buy
        out["unserved"][i] = max(0.0, short); out["curtailed"][i] = surplus
        out["soc"][i] = soc; out["tank"][i] = tank

    df = pd.DataFrame(out, index=series.index)
    df["demand"] = series.demand_mw
    served = df.direct + eta_bt * df.dis + eta_ft * df.p_fc + eta_imp * df.imp + df.unserved
    if not np.allclose(served, demand, atol=1e-6):
        raise AssertionError("myopic dispatch broke the demand balance")
    return df


CAPACITIES = ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_p", "cap_batt_e",
              "cap_ely", "cap_tank", "cap_fc", "cap_grid")
# Every per-step quantity the shared objective reads. A dispatch that has no
# column for one (the merit order never exports, nor buys on a second stream)
# scores it as zero.
FLOWS = ("imp", "exp", "p_ely", "p_fc", "h2_buy", "h2_buy_2", "unserved",
         "soc", "tank")


def evaluate(df: pd.DataFrame, series: M.Series, tech: M.Tech, caps: dict,
             grid: bool | None = None) -> dict:
    """Annualised cost and carbon of a dispatch, on the LP's own basis.

    Scored by ``dc_model.objective_terms`` — the very terms the LP minimises —
    so any difference between the two is dispatch and nothing else. The fuel
    cell replacement rule is applied the same way, max(calendar, duty).

    ``grid``: whether the build has a grid connection, which decides the fixed
    connection charge. Defaults to "it has a non-zero ``cap_grid``"; pass the
    architecture's own flag where it is known, as the LP uses that.
    """
    dt, scale = series.dt_hours, series.annual_scale
    cap_fc = caps.get("cap_fc", 0.0)
    fc_mwh = float((df.p_fc * dt).sum()) * scale if "p_fc" in df else 0.0
    bop_units = max(cap_fc / tech.fc_bop_calendar_years, fc_mwh / tech.fc_bop_duty_hours)
    stack_units = max(cap_fc / tech.fc_stack_calendar_years, fc_mwh / tech.fc_stack_duty_hours)

    q = {k: float(caps.get(k, 0.0)) for k in CAPACITIES}
    q.update({k: (df[k].to_numpy(dtype=float) if k in df else np.zeros(series.n))
              for k in FLOWS})
    q["fc_bop_units"], q["fc_stack_units"] = bop_units, stack_units
    terms = M.score(q, series, tech)
    if grid is None:
        grid = caps.get("cap_grid", 0.0) > 0
    cost_const, gwp_const = M.objective_constants(series, tech, grid=grid)

    gwp = sum(terms["gwp_embodied"].values()) + sum(terms["gwp_operational"].values()) \
        + gwp_const
    cost = sum(terms["cost_capital"].values()) + sum(terms["cost_operational"].values()) \
        + cost_const
    mwh = float(series.demand_mw.sum() * dt) * scale
    unserved = float((df.unserved * dt).sum()) * scale
    return {
        "cost_GBP_per_year": cost, "gwp_kgco2e_per_year": gwp,
        **M.intensities(cost, gwp, unserved, mwh),
        "import_MWh_per_year": float((df.imp * dt).sum()) * scale,
        "unserved_MWh_per_year": unserved,
        "curtailed_MWh_per_year": (float((df.curtailed * dt).sum()) * scale
                                   if "curtailed" in df else float("nan")),
        "soc_end_frac": (df.soc.iloc[-1] / caps["cap_batt_e"]) if caps.get("cap_batt_e") else float("nan"),
        "tank_end_frac": (df.tank.iloc[-1] / caps["cap_tank"]) if caps.get("cap_tank") else float("nan"),
    }


def bracket(series, tech, caps, lp_totals, lp_vars=None, assets=None) -> pd.DataFrame:
    """LP against merit order for the same build — the value of foresight.

    Report unserved energy alongside cost, because cost alone is misleading
    here: a myopic dispatch that fails to serve load is charged VoLL — in both
    objectives since 14 Oct — which is a diagnostic penalty rather than a price
    anyone pays or a tonne anyone emits. £33 m of "cost" difference is really
    332 MWh of lost load wearing a price tag. ``*_excl_VoLL`` take it off.

    ``assets``: the architecture, so the merit order may buy hydrogen when the
    LP could, and the connection charge follows the same flag.
    """
    dis = dispatch(series, tech, caps, buy_h2=bool(assets and assets.buy_h2))
    myo = evaluate(dis, series, tech, caps,
                   grid=(assets.grid if assets is not None else None))
    dt, scale = series.dt_hours, series.annual_scale
    mwh = float(series.demand_mw.sum() * dt) * scale

    lp_unserved = 0.0
    if lp_vars is not None:
        lp_unserved = float(lp_vars["unserved"].solution.values.sum()) * dt * scale

    rows = [
        {"dispatch": "LP (perfect foresight)",
         "cost_m_GBP_per_year": lp_totals["cost_GBP_per_year"] / 1e6,
         "gwp_t_per_year": lp_totals["gwp_kgco2e_per_year"] / 1000.0,
         "unserved_MWh_per_year": lp_unserved,
         "unserved_pct": 100.0 * lp_unserved / mwh},
        {"dispatch": "merit order (no foresight)",
         "cost_m_GBP_per_year": myo["cost_GBP_per_year"] / 1e6,
         "gwp_t_per_year": myo["gwp_kgco2e_per_year"] / 1000.0,
         "unserved_MWh_per_year": myo["unserved_MWh_per_year"],
         "unserved_pct": 100.0 * myo["unserved_MWh_per_year"] / mwh},
    ]
    df = pd.DataFrame(rows)
    voll_m = M.VOLL_GBP_PER_MWH * df.unserved_MWh_per_year / 1e6
    df["cost_excl_VoLL_m"] = df.cost_m_GBP_per_year - voll_m
    voll_t = M.VOLL_KGCO2E_PER_MWH * df.unserved_MWh_per_year / 1e3
    df["gwp_excl_VoLL_t"] = df.gwp_t_per_year - voll_t
    return df


if __name__ == "__main__":
    from optimisation import dc_architectures as A
    from optimisation import dc_inputs as I

    import dc_config as cfg
    # Zhang's 7.31 MW is facility draw; at Zhang's PUE that is 5.22 MW of IT.
    pue = float(cfg.DC_REFERENCE_PUE)
    base, meta = I.build_series("london", "2025-01-01", "2025-12-29", 7.31 / pue, pue=pue)
    series = I.resample(base, 1.0)
    tech = I.build_tech("london", meta, size_mw_it=7.31 / pue, pue=pue)
    assets = A.architecture("grid_res_battery")
    m, V, obj = M.build_model(series, assets, tech, objective="cost")
    M.solve(m)
    caps = {k: float(V[k].solution) for k in
            ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_p", "cap_batt_e",
             "cap_ely", "cap_tank", "cap_fc", "cap_grid")}
    print("=" * 88)
    print("THE VALUE OF FORESIGHT — same build, two dispatch rules")
    print("=" * 88)
    print("  build: " + ", ".join(f"{k[4:]} {v:.2f}" for k, v in caps.items() if v > 0.01))
    print()
    b = bracket(series, tech, caps, M.totals(obj), V, assets=assets)
    print(b.round(3).to_string(index=False))
    lost = b.unserved_MWh_per_year.iloc[1]
    print(f"\n  The merit order leaves {lost:,.0f} MWh unserved "
          f"({b.unserved_pct.iloc[1]:.2f} % of demand) on a build the LP sized")
    print("  to have none. Excluding the VoLL penalty the two dispatches cost")
    print(f"  £{b.cost_excl_VoLL_m.iloc[0]:.2f} m and £{b.cost_excl_VoLL_m.iloc[1]:.2f} m — "
          "so the real finding is not that")
    print("  myopic dispatch is expensive, it is that **an LP-sized build is not")
    print("  robust to imperfect foresight**. The grid connection was sized on the")
    print("  assumption of knowing when the battery would be needed.")
    print("\n  The LP is an upper bound on what this build can achieve; the merit")
    print("  order is a lower one. A real operator with a day-ahead forecast sits")
    print("  between them. Neither is 'the answer' on its own.")
