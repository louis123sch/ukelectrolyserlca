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
# Slack on the second-stage carbon cap, so floating point cannot make "the same
# carbon" infeasible. Far tighter than anything that moves a result.
LEX_TOL = 1e-6

CAPACITY_VARS = ("cap_wind", "cap_offshore", "cap_solar", "cap_batt_p",
                 "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_grid")

# Energy through each sized asset over a year, reported alongside the capacity
# that carries it, because a capacity alone cannot say whether it was sized by
# energy or by a handful of peak hours. Measured on the 300 MW Highland run:
# the min-GWP connection is 868 MW carrying 246,749 MWh, a 3.2 % load factor,
# against 37.7 % at min cost. Six hours out of 8,675 sit above 99 % of it, and
# the peak is demand plus the battery charging at full power in one hour. That
# is a real property of the cleanest build, not a solver artefact — a
# lexicographic re-solve (min cost subject to the same carbon) recovers only
# 3.3 MW — but it is invisible in a capacity column on its own.
# Keyed by the capacity variable so the UI can pair them without a second map.
ENERGY_VARS = {
    "cap_wind": "p_wind", "cap_offshore": "p_offshore", "cap_solar": "p_solar",
    "cap_batt_p": "dis",            # discharge; cap_batt_e shares this flow
    "cap_ely": "p_ely", "cap_fc": "p_fc", "cap_grid": "imp",
}
# cap_batt_e and cap_tank have no MWh of their own: the battery's energy rating
# shares the power rating's flow, and the tank is sized in kg of stock, not MWh
# of throughput. Both are left blank rather than given a number that would
# invite a comparison it cannot support.

# Hydrogen mass through each stream over a year, in kg. Bought hydrogen is a
# flow with no capacity behind it, so it appears in neither table above — and
# without these it was possible to solve a build that buys two colours and
# find no number anywhere saying how much of each it bought, which is the only
# reason for offering two. Every one of these is already a per-step mass in the
# LP, so the conversion is the annual scale and nothing else.
MASS_VARS = {
    "h2_bought_kg_per_year": "h2_buy",
    "h2_bought_2_kg_per_year": "h2_buy_2",
    "h2_to_fuel_cell_kg_per_year": "h2_fc",
}


def _energy(V, series, name):
    """Annualised MWh through one flow variable."""
    return float(V[name].solution.sum()) * series.dt_hours * series.annual_scale


def _extract(V, obj, series, tag):
    tot = M.totals(obj)
    row = {"point": tag}
    row.update({k: float(V[k].solution) for k in CAPACITY_VARS})
    row.update({f"{k}_MWh_per_year": _energy(V, series, flow)
                for k, flow in ENERGY_VARS.items()})
    row.update({k: float(V[flow].solution.sum()) * series.annual_scale
                for k, flow in MASS_VARS.items()})
    mwh = float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale
    row.update({
        "cost_GBP_per_year": tot["cost_GBP_per_year"],
        "gwp_kgco2e_per_year": tot["gwp_kgco2e_per_year"],
        "gwp_g_per_kWh": tot["gwp_kgco2e_per_year"] / mwh,
        "cost_GBP_per_MWh": tot["cost_GBP_per_year"] / mwh,
        "import_MWh_per_year": _energy(V, series, "imp"),
        "export_MWh_per_year": _energy(V, series, "exp"),
        "unserved_MWh_per_year": _energy(V, series, "unserved"),
    })
    return row


_LIMIT = {"cost": "cost_limit", "gwp": "gwp_limit"}
_TOTAL = {"cost": "cost_GBP_per_year", "gwp": "gwp_kgco2e_per_year"}


def _tie_break(solve_one, series, anchor, progress, *, first, second, capture=None):
    """Settle an anchor that its own objective leaves partly undetermined.

    Stage 1 has already minimised ``first``. Stage 2 minimises ``second`` while
    holding ``first`` at its optimum, which chooses between systems the first
    objective could not tell apart. Stage 3 then minimises the grid connection
    with both held, because neither objective necessarily prices it: cost does
    not in a floored TNUoS zone, and carbon prices it only lightly. The result
    is the smallest connection among the systems that are optimal on both.

    Refinement, never a gate — if an epsilon solve is infeasible at this
    tolerance, the best answer so far stands.
    """
    tag = anchor["point"]
    f_opt = anchor[_TOTAL[first]]
    try:
        if progress: progress(f"{tag} — {second} tie-break")
        lim = {_LIMIT[first]: f_opt * (1 + LEX_TOL)}
        V, obj = solve_one(second, **lim)
        anchor = _extract(V, obj, series, tag)
        if capture: capture(tag, V)

        if progress: progress(f"{tag} — connection tie-break")
        lim[_LIMIT[second]] = anchor[_TOTAL[second]] * (1 + LEX_TOL)
        V, obj = solve_one("connection", **lim)
        anchor = _extract(V, obj, series, tag)
        if capture: capture(tag, V)
    except RuntimeError:
        pass
    return anchor


def front(series, assets, tech, *, points: int = DEFAULT_POINTS,
          ely_strategy: str = "free", unserved_fraction: float = 0.0,
          gwp_target: float | None = None, progress=None,
          keep_dispatch: bool = False) -> dict:
    """Solve the exact cost/carbon frontier for one configuration.

    ``keep_dispatch`` also returns the half-hourly dispatch behind the three
    points the UI shows. It is off by default because it costs no solving but a
    lot of memory: one frame per solved point, held until the knee is known —
    which it is not until the sweep is finished, since the knee is chosen from
    the front rather than solved for.
    """
    frames: dict[str, pd.DataFrame] = {}

    def capture(tag, V):
        if keep_dispatch:
            # Later solves of the same tag are refinements of it (the anchor
            # tie-breaks), so the last one written is the one that is reported.
            frames[tag] = M.dispatch_frame(V, series)

    def solve_one(objective, gwp_limit=None, cost_limit=None):
        m, V, obj = M.build_model(series, assets, tech, objective=objective,
                                  gwp_limit=gwp_limit, cost_limit=cost_limit,
                                  unserved_fraction=unserved_fraction,
                                  ely_strategy=ely_strategy)
        M.solve(m)
        return V, obj

    # Both anchors get the same lexicographic treatment, for the same reason and
    # in mirror image. A single-objective solve pins only what its own objective
    # can see, and each objective is blind to something: cost cannot see the
    # connection at a transmission site in a floored TNUoS zone, where it is
    # genuinely £0.00/kW, and carbon cannot see anything priced but unburdened.
    #
    # Measured, before this existed: across 14 regions on a flat 120 MW load,
    # min_cost reported a 180 MW connection — the ceiling — in exactly the seven
    # zones whose locational tariff is floored to zero, and the correct 120 MW
    # in the seven that pay something. The epsilon points were never affected,
    # because a binding carbon cap makes cap_grid's embodied carbon count.
    if progress: progress("min_cost")
    V, obj = solve_one("cost")
    anchor_cost = _extract(V, obj, series, "min_cost")
    capture("min_cost", V)
    anchor_cost = _tie_break(solve_one, series, anchor_cost, progress,
                             first="cost", second="gwp", capture=capture)

    # Minimum carbon, then the cheapest system that achieves it. The second
    # stage is not cosmetic: once a transmission-connected site pays no DUoS and
    # sits in a floored TNUoS zone, cap_grid has a zero coefficient in *both*
    # objectives, so a carbon-only solve is free to return any connection at all
    # that fits the dispatch. Re-solving for cost at the same carbon pins it.
    # Every other point on the front is already a min-cost solve, so this also
    # makes the anchor mean the same thing as its neighbours.
    if progress: progress("min_gwp")
    V, obj = solve_one("gwp")
    anchor_gwp = _extract(V, obj, series, "min_gwp")
    capture("min_gwp", V)
    anchor_gwp = _tie_break(solve_one, series, anchor_gwp, progress,
                            first="gwp", second="cost", capture=capture)

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
            capture(f"eps_{k}", V)

    df = pd.DataFrame(rows).sort_values("gwp_kgco2e_per_year").reset_index(drop=True)
    out = {
        "front": df,
        "degenerate": bool(degenerate),
        "min_cost": anchor_cost,
        "min_gwp": anchor_gwp,
        **special_points(df, degenerate),
    }
    if gwp_target is not None:
        out.update(_target_point(solve_one, series, gwp_target, g_lo, g_hi,
                                 anchor_cost, progress, capture=capture))
    if keep_dispatch:
        # Keyed by the *name of the point* rather than its tag, because the knee
        # is whichever epsilon solve turned out to be closest to the corner —
        # a caller asking for "the knee's dispatch" cannot know it was eps_7.
        out["dispatch"] = {name: frames[out[name]["point"]]
                           for name in ("min_cost", "min_gwp", "knee", "target")
                           if out.get(name) and out[name]["point"] in frames}
    return out


def _target_point(solve_one, series, target: float, g_lo: float, g_hi: float,
                  anchor_cost: dict, progress=None, capture=None) -> dict:
    """Cheapest system that emits no more than ``target`` kg CO2e per year.

    One extra epsilon-constrained solve rather than a read off the sampled
    front, so the answer is exact at the number the user actually typed instead
    of at whichever sweep point happens to sit nearest it.

    Two cases are answered without solving. Below ``g_lo`` there is no system:
    the target is under what this kit can achieve at any price. At or above the
    min-cost point's own emissions the constraint does not bind, so the answer
    is the min-cost system and saying so is more useful than re-deriving it.
    """
    if target < g_lo * (1 - 1e-9):
        return {"target": None, "target_gwp_kgco2e_per_year": target,
                "target_note": (
                    f"unreachable — the cleanest system this combination can "
                    f"build still emits {g_lo / 1000:,.0f} t CO2e/yr")}
    if target >= g_hi:
        return {"target": dict(anchor_cost, point="target"),
                "target_gwp_kgco2e_per_year": target,
                "target_note": ("not binding — the cheapest system already comes "
                                f"in at {g_hi / 1000:,.0f} t CO2e/yr")}
    if progress: progress("target")
    V, obj = solve_one("cost", gwp_limit=target)
    if capture: capture("target", V)
    return {"target": _extract(V, obj, series, "target"),
            "target_gwp_kgco2e_per_year": target, "target_note": ""}


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
