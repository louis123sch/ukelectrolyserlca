"""
The cost/carbon Pareto front, and what "the intersection" means.
=============================================================================

Both objectives are linear in the same decision variables, which is a gift: the
Pareto front is **exact** rather than sampled, and every point on it is a genuine
optimum rather than the best a heuristic found.

The sweep
---------
1. ``min COST``  -> (C_min, G_at_Cmin)
2. ``min GWP``   -> (C_at_Gmin, G_min)
3. epsilon-constraint: for k = 1..N-1, ``min COST subject to GWP <= G_min + k/N x (G_at_Cmin - G_min)``

Step 3 is why the front is exact: each solve returns the cheapest system that
achieves a stated carbon level, so the curve traced is the true frontier.

"The intersection of the two"
-----------------------------
That phrase needs a defined operator, and there are three defensible ones. All
are computed; the knee is the default.

* **Knee point** — normalise both axes to [0,1] across the front and take the
  point closest to the utopia corner. Needs no carbon price, so it makes no
  policy assumption. **Default.**
* **Carbon price** — ``min COST + lambda x GWP``, with lambda the FES 2025 GB
  carbon price the study already loads in ``h2_prices.py`` (£78.96/tCO2 in 2025)
  rather than an invented figure. Policy-relevant, and the lambda is a slider.
* **Max curvature** — the geometric elbow. Included for completeness, not
  defaulted to: it is sensitive to how the front is sampled in a way the knee
  is not.

A degenerate front is a result, not a failure
---------------------------------------------
When min-cost and min-GWP return the same system — as ``grid_h2`` does at the
London site, because grid-charged hydrogen arbitrage cannot beat a 3.41x
round-trip penalty against a 3.12x carbon spread — the front collapses to a
point. That is the honest answer, and ``degenerate`` flags it rather than
returning twelve copies of the same row.

Run:  python optimisation/dc_pareto.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_model as M

DEFAULT_POINTS = 12
DEGENERATE_REL_TOL = 1e-6

CAPACITY_VARS = ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_p",
                 "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_grid")


def _extract(V, obj, series, tag):
    tot = M.totals(obj)
    row = {"point": tag}
    row.update({k: float(V[k].solution) for k in CAPACITY_VARS})
    mwh = float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale
    row.update({
        "cost_GBP_per_year": tot["cost_GBP_per_year"],
        "gwp_kgco2e_per_year": tot["gwp_kgco2e_per_year"],
        "gwp_g_per_kWh": tot["gwp_kgco2e_per_year"] / mwh,
        "cost_GBP_per_MWh": tot["cost_GBP_per_year"] / mwh,
        "import_MWh_per_year": float((V["imp"].solution.sum())) * series.dt_hours * series.annual_scale,
        "unserved_MWh_per_year": float((V["unserved"].solution.sum())) * series.dt_hours * series.annual_scale,
    })
    return row


def front(series, assets, tech, *, points: int = DEFAULT_POINTS,
          ely_strategy: str = "free", unserved_fraction: float = 0.0,
          progress=None) -> dict:
    """Solve the exact cost/carbon frontier for one configuration."""
    def solve_one(objective, gwp_limit=None):
        m, V, obj = M.build_model(series, assets, tech, objective=objective,
                                  gwp_limit=gwp_limit,
                                  unserved_fraction=unserved_fraction,
                                  ely_strategy=ely_strategy)
        M.solve(m)
        return V, obj

    if progress: progress("min_cost")
    V, obj = solve_one("cost")
    anchor_cost = _extract(V, obj, series, "min_cost")

    if progress: progress("min_gwp")
    V, obj = solve_one("gwp")
    anchor_gwp = _extract(V, obj, series, "min_gwp")

    g_hi = anchor_cost["gwp_kgco2e_per_year"]
    g_lo = anchor_gwp["gwp_kgco2e_per_year"]
    span = g_hi - g_lo
    degenerate = span <= DEGENERATE_REL_TOL * max(abs(g_hi), 1.0)

    rows = [anchor_gwp, anchor_cost]
    if not degenerate:
        for k in range(1, points):
            limit = g_lo + (k / points) * span
            if progress: progress(f"eps {k}/{points}")
            V, obj = solve_one("cost", gwp_limit=limit)
            rows.append(_extract(V, obj, series, f"eps_{k}"))

    df = pd.DataFrame(rows).sort_values("gwp_kgco2e_per_year").reset_index(drop=True)
    return {
        "front": df,
        "degenerate": bool(degenerate),
        "min_cost": anchor_cost,
        "min_gwp": anchor_gwp,
        **special_points(df, degenerate),
    }


def special_points(df: pd.DataFrame, degenerate: bool) -> dict:
    """Knee, carbon-price optimum and max-curvature elbow."""
    if degenerate or len(df) < 3:
        row = df.iloc[0].to_dict()
        return {"knee": row, "carbon_price": row, "max_curvature": row,
                "knee_note": "front is a single point — min cost and min GWP coincide"}

    c = df["cost_GBP_per_year"].to_numpy()
    g = df["gwp_kgco2e_per_year"].to_numpy()
    cn = (c - c.min()) / max(c.ptp(), 1e-12)
    gn = (g - g.min()) / max(g.ptp(), 1e-12)

    knee_i = int(np.argmin(np.hypot(cn, gn)))

    lam = _carbon_price_gbp_per_kg()
    cp_i = int(np.argmin(c + lam * g))

    # discrete curvature on the normalised front
    curv = np.full(len(df), -np.inf)
    for i in range(1, len(df) - 1):
        a = np.array([cn[i - 1] - cn[i], gn[i - 1] - gn[i]])
        b = np.array([cn[i + 1] - cn[i], gn[i + 1] - gn[i]])
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na > 0 and nb > 0:
            curv[i] = np.pi - np.arccos(np.clip(a @ b / (na * nb), -1, 1))
    elbow_i = int(np.argmax(curv))

    return {
        "knee": df.iloc[knee_i].to_dict(),
        "carbon_price": df.iloc[cp_i].to_dict(),
        "max_curvature": df.iloc[elbow_i].to_dict(),
        "carbon_price_GBP_per_tCO2": lam * 1000.0,
        "knee_note": "closest point to the utopia corner on the normalised front",
    }


def _carbon_price_gbp_per_kg(year: int = 2025) -> float:
    """FES 2025 GB carbon price, reused rather than invented."""
    from optimisation import h2_prices
    return h2_prices.carbon_gbp_per_t(year) / 1000.0


def summarise(result: dict) -> str:
    df = result["front"]
    if result["degenerate"]:
        r = df.iloc[0]
        return (f"front collapses to a point: £{r.cost_GBP_per_year / 1e6:.2f} m/yr, "
                f"{r.gwp_kgco2e_per_year / 1000:,.0f} t CO2e/yr "
                f"({r.gwp_g_per_kWh:.1f} g/kWh) — min cost and min GWP agree")
    lo, hi = df.iloc[0], df.iloc[-1]
    knee = result["knee"]
    return (f"{len(df)} points | cheapest £{hi.cost_GBP_per_year / 1e6:.2f} m at "
            f"{hi.gwp_kgco2e_per_year / 1000:,.0f} t | cleanest "
            f"£{lo.cost_GBP_per_year / 1e6:.2f} m at {lo.gwp_kgco2e_per_year / 1000:,.0f} t "
            f"| knee £{knee['cost_GBP_per_year'] / 1e6:.2f} m at "
            f"{knee['gwp_kgco2e_per_year'] / 1000:,.0f} t")
