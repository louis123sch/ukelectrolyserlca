"""
Bands, not points — every ASSUMED input swept on one reference case.
=============================================================================

``thresholds.py`` finds the value of one input at which an answer flips, by
bisection. This module answers the other question: across the range an assumed
input could plausibly take, how far do the two anchors move, and does anything
flip? It is what ``DATA_GAPS.md`` means by "bounded by sweep".

Every override is a keyword ``dc_inputs.build_tech`` already takes, so a sweep
cannot reach anything the model would not let a caller set. The series, the
network charges and the asset bounds are built once per case; only ``Tech``
is rebuilt per variant.

Each variant is solved at both anchors with the same lexicographic tie-breaks
``dc_pareto.front`` uses, so a row here is the same point a full run would
report as ``min_cost`` or ``min_gwp``. With ``points=`` a variant is solved as a
whole frontier instead and the knee is reported beside the anchors.

The price lists (5 Nov 2026). When the site's connection is a choice of lists
(COST_PLAN §1.11, switches in the model) a solve at the tight gap can take
hours, and a sweep re-proves the same list once per variant: the overnight run
of 4 Nov spent 8.8 hours on twelve North Norfolk variants that all chose the
same 24.5 MW list, one of them 4.9 hours. ``list_choice`` says how a sweep
treats them:

``fixed`` (the default)
    the central variant is solved with every list at the loose gap (0.1 %,
    ``dc_model.LOOSE_MIP_REL_GAP``; it matched the tight answer to the pound
    on the London year), and every other variant is solved on the list(s) the
    central anchors chose — one list is an ordinary linear programme, minutes
    not hours. Right for knobs that do not move the connection's price.
``pruned``
    each variant prices every list on its own at both anchors (linear,
    ``dc_pareto.prune_options``), keeps those within 2 % plus the rule's own,
    and solves the frontier over the survivors at the loose gap. For the
    connection sweep, where the list is the thing under test.
``full``
    every list at the tight gap for every variant, the old behaviour; for a
    headline figure, not a sweep.

A case with one list (islanded, a picked substation) is the same under all three.

The time step (user, 5 Nov 2026). A sweep is a testing rig: it runs the whole year
in 4-hour steps (``SWEEP_HOURS``), since the tank works across seasons and a short
window would misjudge it, and writes ``sensitivity_<name>_4h.csv``. A figure to
report or a verdict to judge is solved with ``--hours=1`` and written to
``sensitivity_<name>.csv``, the file the judges read. The two never share a file,
so a resumed run cannot mix steps. docs/TESTING.md is the rule: the rig while
working, the hourly sign-off to finish.

Run:  python -m optimisation.sensitivity carbon
      python -m optimisation.sensitivity connection norfolk_150_single
      python -m optimisation.sensitivity cost_cutoff          # the cost cut-off's rule 3
      python -m optimisation.sensitivity assumptions          # the cost side's assumptions at their ranges
      python -m optimisation.sensitivity assumptions norfolk_grid --lists=full
      python -m optimisation.sensitivity connection norfolk_150_room --hours=1
"""
from __future__ import annotations

import itertools
import math
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_architectures as A
from optimisation import dc_model as M
from optimisation import dc_pareto as P
from optimisation import trace as T

OUT_DIR = ROOT / "optimisation_outputs"

# The testing rig's time step (module docstring). The figures quoted against the
# cases below, £146.39 m and the rest, are hourly: reproduce them with --hours=1.
SWEEP_HOURS = 4.0


@dataclass(frozen=True)
class Case:
    """One reference configuration a sweep is run on."""
    name: str
    site: object                       # anything sites.get accepts
    architecture: str
    flags: dict | None = None          # only for architecture == "custom"
    size_mw_it: float = 100.0
    pue: float = 1.5
    start: str = "2025-01-01"
    end: str = "2025-12-29"
    resample_hours: float = SWEEP_HOURS
    ely_tech: str = "PEM operation"
    h2_colour: str | None = None
    unserved_fraction: float = 0.0
    tech_kwargs: dict = field(default_factory=dict)
    series_kwargs: dict = field(default_factory=dict)
    # Fields to set on the site once resolved: a picked substation, say.
    site_kwargs: dict = field(default_factory=dict)
    # How bought hydrogen arrives where the case buys it (dc_architectures.H2_SUPPLIES):
    # "none" by default since 20 Nov 2026 (nothing bought); "jit" (pipeline stand-in)
    # and "steady" (trucked stand-in) are the options.
    h2_supply: str = "none"


_EVERY_ASSET = dict(grid=True, wind=True, solar=True, battery=True, electrolyser=True,
                    tank=True, fuel_cell=True)

CASES = {
    # The storage-loss reference case (DATA_GAPS.md, *Battery cooling and control load*):
    # the one architecture where battery and hydrogen actually compete, and the
    # only one that builds every hydrogen asset, so every fuel-cell knob bites.
    "islanded_h2": Case(
        name="islanded_h2", site=(52.85, 1.04), architecture="custom",
        flags=dict(wind=True, solar=True, battery=True, electrolyser=True,
                   tank=True, fuel_cell=True)),
    # North Norfolk is the reference and test site (user: never test on London,
    # 9 Nov 2026; the London cases london_grid, london_150_single and
    # london_150_leicester_sq(_cap) were replaced that day by the Norfolk ones
    # below). The same coordinate as the islanded reference case, grid-connected,
    # the optimiser choosing the price list with each option capped at its
    # substation's published room.
    "norfolk_grid": Case(
        name="norfolk_grid", site=(52.85, 1.04), architecture="res_h2_grid",
        series_kwargs={"connection_mode": "room"}),
    "norfolk_150_room": Case(
        name="norfolk_150_room", site=(52.85, 1.04), architecture="custom",
        flags=_EVERY_ASSET, size_mw_it=150.0, pue=1.2,
        series_kwargs={"connection_mode": "room"}),
    # Grid-connected with every asset and bought green hydrogen on offer: where
    # the published figures' kind of answer comes from (was london_grid). Since 13 Nov
    # 2026 the gas engines too ("everything on the table", user), so the sign-off's
    # cut-off and screened-input tests reach their figures; res_h2_grid until then.
    "norfolk_grid_green": Case(
        name="norfolk_grid_green", site=(52.85, 1.04), architecture="custom",
        flags={**_EVERY_ASSET, "buy_h2": True, "gas_engine": True},
        h2_colour="green", series_kwargs={"connection_mode": "room"}),
    # One price list fixed by the rule before solving (was london_150_single).
    "norfolk_150_single": Case(
        name="norfolk_150_single", site="52.85,1.04", architecture="custom",
        flags=_EVERY_ASSET, size_mw_it=150.0, pue=1.2,
        series_kwargs={"connection_mode": "single"}),
    # A substation picked by the user, at 132 kV on the local network, capped at
    # the room it publishes (SALL GRID 132/33kV, 24.5 MW, 11 km away; was
    # london_150_leicester_sq).
    "norfolk_150_sall": Case(
        name="norfolk_150_sall", site="52.85,1.04", architecture="custom",
        flags=_EVERY_ASSET, size_mw_it=150.0, pue=1.2,
        site_kwargs={"connection_substation": "SALL GRID 132/33kV",
                     "connection_substation_voltage": "132 kV"}),
    # The same substation with room ignored, capped at 1.43x the load: the one
    # case where the connection's size is free to move both ways (was
    # london_150_leicester_sq_cap).
    "norfolk_150_sall_cap": Case(
        name="norfolk_150_sall_cap", site="52.85,1.04", architecture="custom",
        flags=_EVERY_ASSET, size_mw_it=150.0, pue=1.2,
        series_kwargs={"connection_mode": "cap"},
        site_kwargs={"connection_substation": "SALL GRID 132/33kV",
                     "connection_substation_voltage": "132 kV"}),
}


# Knobs that change the series rather than the coefficients. A variant moving
# one of these rebuilds the series for itself.
SERIES_KNOBS = ("wind_net_factor", "network_charges_scale", "pv_system_loss")


def prepare(case: Case, **series_kwargs):
    """(site, series, meta, assets) for a case — built once, shared by variants."""
    from optimisation import dc_inputs as I
    from optimisation import sites
    site = sites.get(case.site)
    if case.site_kwargs:
        site = replace(site, **case.site_kwargs)
    series, meta = I.build_series(site, case.start, case.end, case.size_mw_it, pue=case.pue,
                                  grid=A.architecture(case.architecture, flags=case.flags).grid,
                                  **{**case.series_kwargs, **series_kwargs})
    if case.resample_hours:
        series = I.resample(series, case.resample_hours)
    assets = A.architecture(case.architecture,
                            grid_limit_mw=meta["connection_limit_mw"],
                            grid_floor_mw=meta.get("connection_floor_mw", 0.0), flags=case.flags)
    if case.h2_colour is None and assets.buy_h2:
        assets = replace(assets, buy_h2=False)
    if case.h2_supply not in A.H2_SUPPLIES:
        raise ValueError(f"h2_supply must be one of {A.H2_SUPPLIES}, got {case.h2_supply!r}")
    if case.h2_supply == "none":
        assets = replace(assets, buy_h2=False, buy_h2_2=False)
    if case.h2_supply == "steady" and assets.buy_h2:
        assets = replace(assets, h2_buy_steady=True)
    return site, series, meta, assets


def one_at_a_time(knobs: dict[str, list]) -> list[dict]:
    """The central case, then each knob moved alone to each of its values.

    ``None`` in a knob's list means its default and is skipped, since the
    central row already is that point.
    """
    out = [{}]
    for k, values in knobs.items():
        out += [{k: v} for v in values if v is not None]
    return out


def grid(knobs: dict[str, list]) -> list[dict]:
    """Every combination — for knobs that interact, like the two storage losses."""
    keys = list(knobs)
    return [dict(zip(keys, combo)) for combo in itertools.product(*knobs.values())]


LIST_CHOICES = ("fixed", "pruned", "full")


def _restrict(tech, keys):
    """The Tech on only the price lists named, in their order; unchanged when
    it has no choice of lists or every list is named."""
    opts = M.connection_options_of(tech)
    if not opts:
        return tech
    kept = [o for o in opts if o.key in set(keys)]
    if not kept or len(kept) == len(opts):
        return tech
    return replace(tech, connection_options=tuple(kept))


def _lists_chosen(rows: list[dict]) -> list[str]:
    """The price lists the rows' points chose, in first-seen order."""
    out = []
    for r in rows:
        k = r.get("connection_option")
        if isinstance(k, str) and k and k not in out:
            out.append(k)
    return out


def _gap(tech, list_choice: str) -> float | None:
    """The branching gap for a Tech under a list choice: the loose gap when
    there is a choice of lists and the choice is a sweep's, None (dc_model's
    tight default) otherwise. One list has no switches, so no gap applies."""
    opts = M.connection_options_of(tech)
    if not opts or len(opts) < 2:
        return None
    return M.LOOSE_MIP_REL_GAP if list_choice != "full" else None


def _anchor(series, assets, tech, case, objective, mip_rel_gap: float | None = None):
    """One anchor, settled the way dc_pareto.front settles it."""
    def solve_one(obj, gwp_limit=None, cost_limit=None):
        m, V, o = M.build_model(series, assets, tech, objective=obj,
                                gwp_limit=gwp_limit, cost_limit=cost_limit,
                                unserved_fraction=case.unserved_fraction)
        M.solve(m, **({} if mip_rel_gap is None else {"mip_rel_gap": float(mip_rel_gap)}))
        return V, o

    held = {}

    def capture(_tag, V):
        held["V"] = V

    V, obj = solve_one(objective)
    held["V"], held["obj"] = V, obj
    tag = "min_cost" if objective == "cost" else "min_gwp"
    first, second = ("cost", "gwp") if objective == "cost" else ("gwp", "cost")
    row = P._extract(V, obj, series, tag)
    settled = P._tie_break(solve_one, series, row, None,
                           first=first, second=second, capture=capture)
    return settled, held["V"]


def _row(case, variant, objective, point, q, series, tech, assets, seconds, mip_rel_gap=None):
    terms = M.score(q, series, tech)
    dt, scale = series.dt_hours, series.annual_scale
    batt_out = float(q["dis"].sum()) * dt * scale
    fc_out = float(q["p_fc"].sum()) * dt * scale
    stored = batt_out + fc_out
    r = {"case": case.name,
         "variant": ", ".join(f"{k}={v}" for k, v in variant.items()) or "central",
         **{f"knob:{k}": v for k, v in variant.items()},
         "objective": objective,
         "cost_m_GBP_per_year": point["cost_GBP_per_year"] / 1e6,
         "gwp_t_per_year": point["gwp_kgco2e_per_year"] / 1e3,
         "gwp_g_per_kWh": point["gwp_g_per_kWh"],
         "gwp_supply_g_per_kWh": point.get("gwp_supply_g_per_kWh", float("nan")),
         **{k: point[k] for k in P.CAPACITY_VARS},
         "battery_share_of_storage_output": (batt_out / stored) if stored else float("nan"),
         "unserved_MWh_per_year": point["unserved_MWh_per_year"],
         "solve_s": seconds,
         "step_hours": dt,
         "grid_floor_mw": assets.grid_floor_mw, "grid_ceiling_mw": assets.grid_limit_mw,
         # The price list this point chose, how many it chose among, and the
         # branching gap it was solved at (None: one list, no switches).
         "connection_option": point.get("connection_option"),
         "connection_lists_solved": len(M.connection_options_of(tech) or ()),
         "mip_rel_gap": mip_rel_gap,
         "solver": M.current_solver()}
    for group in ("gwp_embodied", "gwp_operational"):
        for k, v in terms[group].items():
            r[f"gwp_t:{k}"] = v / 1e3
    # Constants in the model (the fixed charges with one price list, the
    # facility's carbon), so outside objective_terms; the columns make the terms
    # add up to the totals.
    fixed_cost, fixed_gwp = M.objective_constants(series, tech, grid=assets.grid, tank=assets.tank)
    hazard = M.major_hazard_cost(tech, tank=assets.tank)
    r["gwp_t:constant"] = fixed_gwp / 1e3
    r["cost_m:fixed charges and cable"] = (fixed_cost - hazard) / 1e6
    r["cost_m:major-hazard compliance"] = hazard / 1e6
    for group in ("cost_capital", "cost_operational"):
        for k, v in terms[group].items():
            r[f"cost_m:{k}"] = v / 1e6
    return r


def _frontier_rows(case, variant, series, assets, tech, points, mip_rel_gap=None):
    """min_cost, knee and min_gwp of one variant's frontier, as rows."""
    solved = {}
    t0 = time.time()
    res = P.front(series, assets, tech, points=points, unserved_fraction=case.unserved_fraction,
                  mip_rel_gap=mip_rel_gap,
                  on_solution=lambda tag, V: solved.__setitem__(tag, M.solution_quantities(V)))
    seconds = time.time() - t0
    return [_row(case, variant, name, res[name], solved[res[name]["point"]], series, tech, assets, seconds,
                 mip_rel_gap)
            for name in ("min_cost", "knee", "min_gwp")]


def _with_changes(rows: list[dict]) -> pd.DataFrame:
    """The rows as a frame, with each one's change from its central row."""
    df = pd.DataFrame(rows)
    central = df[df.variant == "central"].set_index("objective")
    for col in ("cost_m_GBP_per_year", "gwp_t_per_year"):
        df[f"d_{col}_pct"] = 100.0 * (df[col] / df.objective.map(central[col]) - 1.0)
    return df


def _out_path(name: str, case: Case) -> Path:
    """Where a sweep writes: hourly on the plain name, any other step on its own."""
    step = "" if case.resample_hours == 1.0 else f"_{case.resample_hours:g}h"
    return OUT_DIR / f"sensitivity_{name}{step}.csv"


def run(case: Case | str, variants: list[dict], *, name: str,
        objectives=("cost", "gwp"), progress=print, points: int | None = None,
        resume: bool = False, list_choice: str = "fixed") -> pd.DataFrame:
    """Solve every variant at each anchor and write ``sensitivity_<name>_4h.csv``
    (``sensitivity_<name>.csv`` for an hourly case).

    Percent changes are against the case's central row (the empty variant),
    which is added if the list leaves it out, and solved first.

    ``points`` solves each variant as a frontier of that many points instead
    (``dc_pareto.front``, 40 minutes a variant on a full hourly year) and reports
    min_cost, the knee and min_gwp. The file is rewritten after every variant,
    and ``resume`` keeps the variants an earlier run of the same name finished.

    ``list_choice`` (module docstring) says how a choice of price lists is
    solved: ``fixed`` solves the central variant with every list at the loose
    gap and the rest on the list(s) its points chose; ``pruned`` prices the
    lists one by one per variant and keeps the survivors; ``full`` is every
    list at the tight gap. Each row records ``connection_option``,
    ``connection_lists_solved`` and ``mip_rel_gap``; a pruned row also records
    ``connection_lists_dropped``.
    """
    from optimisation import dc_inputs as I
    if list_choice not in LIST_CHOICES:
        raise ValueError(f"list_choice must be one of {LIST_CHOICES}, got {list_choice!r}")
    case = CASES[case] if isinstance(case, str) else case
    variants = [{}] + [v for v in variants if v]       # the central variant first: it may fix the list
    site, series0, meta0, assets = prepare(case)
    ref_key = (meta0.get("connection_reference") or {}).get("key")
    OUT_DIR.mkdir(exist_ok=True)
    path = _out_path(name, case)
    rows, finished = [], set()
    if resume and path.exists():
        rows = pd.read_csv(path).to_dict("records")
        finished = {r["variant"] for r in rows}
    fixed_keys: list[str] | None = None
    for i, variant in enumerate(variants, 1):
        label = ", ".join(f"{k}={v}" for k, v in variant.items()) or "central"
        if label in finished:
            if not variant and list_choice == "fixed":
                fixed_keys = _lists_chosen([r for r in rows if r["variant"] == "central"])
            continue
        s_kw = {k: v for k, v in variant.items() if k in SERIES_KNOBS}
        series, meta = (prepare(case, **s_kw)[1:3] if s_kw else (series0, meta0))
        kwargs = {**case.tech_kwargs,
                  **{k: v for k, v in variant.items() if k not in SERIES_KNOBS and k != "push"}}
        push_key, push_factor = parse_push(variant["push"]) if "push" in variant else ("", 1.0)
        with T.pushed(push_key, push_factor) as hits:
            tech = I.build_tech(site, meta, ely_tech=case.ely_tech, h2_colour=case.h2_colour,
                                size_mw_it=case.size_mw_it, pue=case.pue, **kwargs)
        if push_key and not any(hits):
            raise ValueError(f"push {variant['push']!r}: no step {push_key!r} that the code reads back "
                             f"ran while building {case.name}'s coefficients")
        dropped = None
        if variant and list_choice == "fixed" and fixed_keys:
            tech = _restrict(tech, fixed_keys)
        elif list_choice == "pruned":
            if progress and (M.connection_options_of(tech) or ()) and len(M.connection_options_of(tech)) > 1:
                progress(f"[{case.name} {i}/{len(variants)}] pricing each list alone {label}")
            tech, report = P.prune_options(series, assets, tech, keep_keys=[k for k in (ref_key,) if k],
                                           unserved_fraction=case.unserved_fraction)
            dropped = report["dropped"]
        gap = _gap(tech, list_choice)
        new = []
        if points:
            if progress:
                progress(f"[{case.name} {i}/{len(variants)}] frontier {label}")
            new = _frontier_rows(case, variant, series, assets, tech, points, gap)
        else:
            for objective in objectives:
                t0 = time.time()
                if progress:
                    progress(f"[{case.name} {i}/{len(variants)}] min_{objective} {label}")
                point, V = _anchor(series, assets, tech, case, objective, gap)
                new.append(_row(case, variant, f"min_{objective}", point, M.solution_quantities(V),
                                series, tech, assets, time.time() - t0, gap))
        for r in new:
            r["list_choice"] = list_choice
            r["connection_lists_dropped"] = ", ".join(dropped) if dropped else None
        rows += new
        if not variant and list_choice == "fixed":
            fixed_keys = _lists_chosen(new)
            if progress and fixed_keys and (M.connection_options_of(tech) or ()) and len(M.connection_options_of(tech)) > 1:
                progress(f"[{case.name}] the central points chose {', '.join(fixed_keys)}; "
                         f"the other variants are solved on {'that list' if len(fixed_keys) == 1 else 'those lists'}")
        pd.DataFrame(rows).to_csv(path, index=False)
    df = _with_changes(rows)
    df.to_csv(path, index=False)
    if progress:
        progress(f"wrote {path.relative_to(ROOT)}")
    return df


# --------------------------------------------------------------------------
#                       the study's carbon-side sweeps
# --------------------------------------------------------------------------
# Central values are the module defaults; each list is the band DATA_GAPS.md
# or CARBON_PLAN.md phase 4 names for it.
CARBON_KNOBS = {
    "fc_stack_calendar_years": [5.0, 15.0],
    "fc_bop_calendar_years": [15.0, 25.0],
    "fc_kw_per_container": [500.0, 2000.0],
    "batt_usable_fraction": [0.85, 0.95],
    "green_h2_grid_share": [0.0, 1.0],
    "tank_leakage_per_hour": [0.0, 0.01 / 100],     # none, and Frazer-Nash's high end
    # Since 11 Nov 2026 a percentage change, not a swap of source or basis (user):
    # wind's life-extension parts and the fuel cell stack's carbon at x0.5 / x1.5. The
    # battery cell swap is dropped; the battery's own push covers it (SHAKY_KNOBS).
    "push": [f"{k}*{f}" for k in ("onshore_wind.parts_fraction", "coefficient.gwp_fc_stack_per_mw")
             for f in (0.5, 1.5)],
    "wind_net_factor": [1.0],
    # The container step-ups' ASSUMED loadings, and a standby fuel cell's unit
    # de-energised (conversion_losses.py, 15 Oct).
    "batt_tx_x_eff": [1.0],
    "fc_tx_x_eff": [0.5],
    "fc_tx_energised": [False],
    # The cut-off rule's rule 3 (CUTOFF_RULE_PLAN.md, dc_inputs.with_cutoff): every
    # still-excluded flow added at its upper estimate, and the pre-22-Oct model
    # with no estimates at all.
    "cutoff": ["upper", "none"],
}


# The supervisor's test of the grid connection's price (email of 4 Nov 2026): "if
# you vary the connection cost by +/-50 % and the design doesn't change, there's
# no need to go further on it for now." The one-off build cost and the yearly
# network charges are separate knobs because they behave differently. Central is
# 1.0. Judge the result with scripts/connection_sensitivity.py.
CONNECTION_KNOBS = {
    "connection_build_scale": [0.5, 1.5],
    "network_charges_scale": [0.5, 1.5],
}


CONNECTION_CASES = ("norfolk_150_single", "norfolk_150_sall", "norfolk_150_sall_cap", "norfolk_150_room")


def connection(cases=CONNECTION_CASES, points: int = 3, resume: bool = True,
               list_choice: str = "pruned"):
    """Each connection knob at 0.5x and 1.5x, a full frontier per variant
    (sensitivity_connection_<case>.csv with --hours=1, which is what the judge
    reads). About 40 minutes a variant on one list on an hourly year, so one
    process per case; a stopped run carries on where it left off.
    The price list is the thing under test here, so each variant prices every
    list alone and keeps the survivors (``pruned``) rather than fixing the
    central one."""
    return pd.concat([run(c, one_at_a_time(CONNECTION_KNOBS), name=f"connection_{c}",
                          points=points, resume=resume, list_choice=list_choice)
                      for c in cases], ignore_index=True)


# The cost side's assumptions with no sourced figure behind them, each at its
# stated range (docs/COST_BEST_SOURCE_PLAN.md, *The gaps: filled, or assumed*):
# the cost cases carry the tank's price level, the battery's current price and
# the fuel cell's stack share and capital; the tank design is the carbon side's
# vessel substitution; the fuel cell's lives are its weakest inputs. The last two
# are scope readings: wind and solar without their own grid connection, and the
# tank paying insurance and rates outside its running cost (wind's ratio). The
# battery's cap is the longest duration its UK price covers (battery.py).
# Since 11 Nov 2026 the tank's test is its own carbon (the carbon-steel vessel) at
# x0.5 and x1.5, like every other unsourced range (user: a percentage change where
# possible), in place of the switch to Gandiglio's stainless buffer, which stays in
# h2_tank.TANK_DESIGNS but is no longer tested.
TANK_PUSH = ["coefficient.gwp_tank*0.5", "coefficient.gwp_tank*1.5"]
ASSUMPTION_KNOBS = {
    "cost_case": ["low", "high"],
    "push": TANK_PUSH,
    "fc_bop_calendar_years": [15.0, 25.0],
    "fc_stack_calendar_years": [5.0, 15.0],
    "fc_stack_duty_hours": [20_000.0, 40_000.0],
    "generator_connection_out": [True],
    "tank_insurance_frac": [0.0099],
    "batt_max_duration_hours": [9.0],
}


def assumptions(cases=("islanded_h2", "norfolk_grid"), list_choice: str = "fixed"):
    """The cost-side assumptions in ASSUMPTION_KNOBS at their ranges, one at a time, on the reference cases."""
    return pd.concat([run(c, one_at_a_time(ASSUMPTION_KNOBS), name=f"assumptions_{c}",
                          list_choice=list_choice) for c in cases],
                     ignore_index=True)


def carbon(cases=("islanded_h2", "norfolk_grid_green"), knobs=None):
    """CARBON_PLAN.md phase 4: every carbon-side knob, one at a time."""
    knobs = dict(knobs or CARBON_KNOBS)
    out = []
    for c in cases:
        k = dict(knobs)
        if CASES[c].h2_colour != "green":
            k.pop("green_h2_grid_share", None)
        out.append(run(c, one_at_a_time(k), name=f"carbon_{c}"))
    return pd.concat(out, ignore_index=True)


def parse_push(spec: str) -> tuple[str, float]:
    """``"<step key>*<factor>"`` -> (key, factor). The key is a recorded step's
    (``T.step`` / ``T.cost``); the factor multiplies it inside build_tech."""
    key, sep, factor = str(spec).rpartition("*")
    if not sep or not key:
        raise ValueError(f"a push is '<step key>*<factor>', got {spec!r}")
    f = float(factor)
    if not (f > 0 and f == f and f != float("inf")):
        raise ValueError(f"a push factor must be a positive number, got {spec!r}")
    return key, f


# The +/-30-50 % runs the supervisor asked for (19 Oct, point 6), on the inputs
# the screen picked (scripts/screen_inputs.py, optimisation_outputs/input_screen.md,
# 10 Nov 2026): unsure and moving a total by 1 % or more at +/-50 %, plus those
# that act through how the plant runs and need a solve to judge. Inputs with a
# published range are swept on it; those without are pushed to x0.5 and x1.5.
# The discount rates are influential but a method choice from government
# guidance, stated in the report and not swept (user, 10 Nov 2026).
_STANDING = -math.log(0.8) / 1560.0     # battery.STANDING_LOSS_PER_HOUR: 80 % after 1,560 h (BEIS 2018)
SHAKY_KNOBS = {
    # unsure and influential
    "push": [f"{k}*{f}" for k in ("cost.fuel_cell.capex_per_kW",        # one plant (Baringa), thin evidence
                                  "battery.energy_per_usable_kWh",      # battery carbon (supervisor)
                                  "coefficient.cost_ely",               # NESO electrolyser, no range
                                  "cost.bought_h2.green.delivered",     # bought hydrogen price (supervisor)
                                  "coefficient.gwp_tank",               # tank carbon, since 11 Nov 2026 (TANK_PUSH)
                                  # since 11 Nov 2026 in place of swaps (user): wind's life-extension
                                  # parts and the stack's carbon; the battery cell swap is dropped
                                  "onshore_wind.parts_fraction",
                                  "coefficient.gwp_fc_stack_per_mw",
                                  # since 12 Nov 2026: battery sized to end of life, calendar rate assumed
                                  "battery.capacity_fade_at_end_of_life",
                                  # since 13 Nov 2026: the gas engine plant's carbon (ecoinvent v2 set,
                                  # the hall a stand-in)
                                  "coefficient.gwp_ge_per_mw",
                                  # since 20 Nov 2026 (docs/COMPARISON_FIXES_PLAN.md): the electrolyser
                                  # stack's share of the price (Danish; Rozzi's ~21 % inside the range),
                                  # the tank's capital (Rozzi's large low-pressure tanks near x0.5) and
                                  # the fuel cell's maintenance (about three times Rozzi's; covers the
                                  # low case's cheap plant on a dearer unit's maintenance, stated)
                                  "cost.electrolyser.stack_cost_fraction",
                                  "cost.h2_tank.capex_per_kg",
                                  "cost.fuel_cell.maintenance_per_kW_year",
                                  # since 20 Nov 2026 (REopt comparison #2): the spare power an
                                  # islanded site holds, shares of load and of wind (REopt's
                                  # defaults; no UK figure). They bite only off grid.
                                  "reserve.load_fraction",
                                  "reserve.wind_fraction",
                                  # since 25 Nov 2026 (docs/SELL_OFF_PLAN.md): Terlouw's 75 % resale
                                  # share for wind, solar and the grid connection at the data
                                  # centre's end, his assumption with no source of its own
                                  "cost.sell_off.resale_share")
             for f in (0.5, 1.5)],
    # since 20 Nov 2026 (REopt comparison #3): the solar array's other losses, ninja's
    # 10 % default (assumed) at x0.5 and x1.5; REopt's own total is about 17 %
    "pv_system_loss": [0.05, 0.15],
    "green_h2_grid_share": [0.0, 1.0],          # the electricity the seller runs on
    # since 13 Nov 2026: DESNZ's published gas range (low / high over central), now that the
    # engines make gas a fuel the optimiser chooses
    "gas_price_case": ["low", "high"],
    # act through how the plant runs: only a solve can judge them
    "fc_stack_calendar_years": [5.0, 15.0],
    "fc_stack_duty_hours": [20_000.0, 40_000.0],
    "tank_leakage_per_hour": [0.0, 0.01 / 100],
    "batt_standing_loss_per_hour": [0.0, 2 * _STANDING],
    "batt_tx_x_eff": [1.0],
    "fc_tx_x_eff": [0.5],
}
# Knobs that only bite where hydrogen is bought.
_BOUGHT_H2_ONLY = ("green_h2_grid_share", "cost.bought_h2.green.delivered")
# Knobs that only bite with no grid: the spare-power rule (dc_model (10b)).
_OFF_GRID_ONLY = ("reserve.",)


def shaky_variants(case: Case) -> list[dict]:
    """SHAKY_KNOBS one at a time for ``case``, without the bought-hydrogen ones
    where the case buys none."""
    knobs = {k: list(v) for k, v in SHAKY_KNOBS.items()}
    if case.h2_colour is None or case.h2_supply == "none":
        knobs.pop("green_h2_grid_share", None)
        knobs["push"] = [p for p in knobs["push"] if not p.startswith(_BOUGHT_H2_ONLY)]
    if A.architecture(case.architecture, flags=case.flags).grid:
        knobs["push"] = [p for p in knobs["push"] if not p.startswith(_OFF_GRID_ONLY)]
    return one_at_a_time(knobs)


def variant_label(variant: dict) -> str:
    """The label a row carries in its ``variant`` column."""
    return ", ".join(f"{k}={v}" for k, v in variant.items()) or "central"


def shaky(cases=("islanded_h2", "norfolk_grid_green"), list_choice: str = "fixed", only=None):
    """The screened inputs at their ranges, one at a time (sensitivity_shaky_<case>[_4h].csv).
    ``only`` keeps the variants with those labels (the central one always)."""
    out = []
    for c in cases:
        vs = shaky_variants(CASES[c])
        if only is not None:
            vs = [v for v in vs if not v or variant_label(v) in only]
        out.append(run(CASES[c], vs, name=f"shaky_{c}", list_choice=list_choice))
    return pd.concat(out, ignore_index=True)


def cutoff(cases=("islanded_h2", "norfolk_grid_green")):
    """The cut-off rule's rule 3: central and every still-excluded flow at its upper estimate, at both
    anchors (sensitivity_cutoff_<case>.csv). Judge it with scripts/cutoff_rule3.py."""
    return pd.concat([run(c, [{}, {"cutoff": "upper"}], name=f"cutoff_{c}") for c in cases],
                     ignore_index=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith(("--lists=", "--hours=", "--only="))]
    # --only=<file>: solve only the variants whose labels the file lists, one a line
    # (the hourly confirmations scripts/shaky_judge.py pick writes); central always.
    only = next((Path(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--only=")), None)
    only_labels = ({ln.strip() for ln in only.read_text(encoding="utf-8").splitlines() if ln.strip()}
                   if only else None)
    # --lists=fixed|pruned|full overrides each sweep's own default (module docstring).
    lists = {a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--lists=")}
    choice = lists.pop() if lists else None
    # --hours=1 solves the sweep hourly, for a verdict or a reported figure (module docstring).
    for a in sys.argv[1:]:
        if a.startswith("--hours="):
            CASES = {k: replace(c, resample_hours=float(a.split("=", 1)[1])) for k, c in CASES.items()}
    what = args[0] if args else "carbon"
    cases = args[1:]
    if what == "carbon":
        carbon(cases or ("islanded_h2", "norfolk_grid_green"))
    elif what == "cutoff":
        cutoff(cases or ("islanded_h2", "norfolk_grid_green"))
    elif what == "cost_cutoff":
        # Rule 3 of optimisation/cost_exclusions.py: the same frontier with every
        # cost left out added back at its upper estimate.
        for c in cases or ("islanded_h2", "norfolk_grid"):
            run(c, [{}, {"cost_cutoff": "upper"}], name=f"cost_cutoff_{c}", list_choice=choice or "fixed")
    elif what == "connection":
        connection(cases or CONNECTION_CASES, list_choice=choice or "pruned")
    elif what == "assumptions":
        assumptions(cases or ("islanded_h2", "norfolk_grid"), list_choice=choice or "fixed")
    elif what == "shaky":
        shaky(cases or ("islanded_h2", "norfolk_grid_green"), list_choice=choice or "fixed", only=only_labels)
    else:
        raise SystemExit(f"unknown sweep {what!r}; try: carbon, cutoff, cost_cutoff, connection, assumptions, shaky")
