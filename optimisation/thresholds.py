"""
The tipping point — at what input price does hydrogen enter the build?
=============================================================================

Every grid-connected configuration in the study answers "how much hydrogen?"
with **none**. Not only at min cost: ``grid_h2`` is degenerate, so the min-GWP
anchor builds none either, and ``res_h2_grid`` — everything available — returns
the same system as ``grid_res_battery`` to the decimal. That is the honest
result, and it leaves exactly one question worth asking next: *how far from
viable is it?*

This module answers that by bisection on a re-solve. Move one input, re-solve,
look at how much of the load the fuel cell served, and home in on the value
where hydrogen first carries a stated share.

Why not read it off the solver
------------------------------
The tempting shortcut is the reduced cost of ``cap_ely`` at the optimum: the LP
already knows how far that variable is from entering the basis. It is the wrong
tool here, and the reason is structural rather than numerical.

Hydrogen is not one asset. Electricity becomes hydrogen in the electrolyser,
waits in the tank and comes back through the fuel cell, and **none of the three
is worth anything without the other two**. So at a solution where the chain is
unbuilt, every link is individually unattractive and every reduced cost is
positive — including at prices where the chain as a whole would clear. A reduced
cost prices a single variable entering alone, which is not the move on offer.
Re-solving prices the whole chain entering together, which is.

The same argument rules out any one-at-a-time first-order sensitivity around the
base case. It is why this module costs LP solves instead of being free.

Monotonicity, which is what makes bisection legal
-------------------------------------------------
Lower the annualised cost of an asset and the optimal build uses weakly more of
it — standard parametric LP, and it holds for each of ``cost_ely``,
``cost_tank``, ``cost_fc`` and ``bought_h2_gbp_per_kg`` separately. Hydrogen's
share of the load is therefore a monotone step function of each knob, and the
bracket-then-bisect below converges on the single step.

Two knobs run the other way, and are declared ``sense="up"``: making the battery
dearer and widening the price spread both help hydrogen. ``grid_price`` as a
*level* is deliberately absent — raising it makes the electrolyser's input dearer
and the fuel cell's output more valuable at the same time, so it is not monotone
and a bisection on it would converge on nothing meaningful. Spread is the knob
that actually drives arbitrage; see ``PRICE_SPREAD_NOTE``.

Every bracket is checked against its own sense before bisecting, so a knob that
turns out non-monotone reports ``non_monotone`` rather than a confident wrong
number.

Why "share of load" and not "capacity > 0"
------------------------------------------
The first MW enters at zero volume: there is a range of prices where the LP is
indifferent and builds an electrolyser that runs almost never. Bisecting on
``cap_ely > 0`` therefore converges on a numerically fuzzy boundary and reports a
system nobody would build. ``ENTRY_SHARE`` — hydrogen serving 1 % of annual load
through the fuel cell — bisects cleanly and is a sentence that can go in a
write-up. It is a parameter, not a constant of nature.

The fuel cell is the right meter for it because every pathway here ends there,
whether the hydrogen was made on site or bought.

What it costs
-------------
One solve is ~4 s at hourly resampling. Bracketing takes up to ~10 and the
bisection ~12, so a knob is ~90 s and the whole default set is a few minutes.
The full Pareto sweep is *not* run — a threshold needs the min-cost anchor only,
or that anchor under a carbon cap.

Cache, and the trap it avoids
-----------------------------
``dc_runner``'s cache is keyed on what the user typed and the coefficient files'
hashes. It cannot see a coefficient this module overrode in memory, so reusing it
would serve base-case answers for perturbed runs — authoritative-looking and
wrong. This module keeps its own cache instead, hashed over the knob and its own
source as well, and never writes into ``dc_runs/``.

Run:  python optimisation/thresholds.py
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_ROOT = ROOT / "optimisation_outputs" / "dc_thresholds"

from optimisation import dc_architectures as A
from optimisation import dc_model as M
from optimisation import dc_pareto as P
from optimisation import dc_runner, sites

# Hydrogen "enters" when the fuel cell carries this share of annual demand.
# 1 % is above the indifference band where the LP builds a token electrolyser
# and below anything that could be called a design choice.
ENTRY_SHARE = 0.01

# Bisection stops when the bracket is this wide relative to its upper end.
REL_TOL = 0.02

PRICE_SPREAD_NOTE = (
    "Multiplies each half-hour's deviation from the window mean, holding the "
    "mean fixed: p -> mean + k x (p - mean). This is the transform that isolates "
    "arbitrage value from price level, which is the thing a level shift confounds. "
    "Network volumetric charges are already inside grid_price_per_mwh when the "
    "series is built, so they are widened too — a known overstatement of k, since "
    "the DUoS element is banded by time of day rather than by price.")


# --------------------------------------------------------------------------
#                                  the knobs
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Knob:
    """One input the threshold can be found in.

    ``mode`` is "multiplier" (1.0 is today's value) or "absolute" (the value is
    the coefficient itself, in ``unit``). ``sense`` says which direction helps
    hydrogen, and is what the bracket search is checked against.
    """
    name: str
    label: str
    unit: str
    fields: tuple[str, ...]     # Tech fields, or ("__price_spread__",)
    mode: str                   # "multiplier" | "absolute"
    sense: str                  # "down" | "up"
    floor: float
    ceiling: float
    needs: tuple[str, ...]      # asset flags this knob is meaningless without
    # How to say the move in a sentence. "4.6x dearer" is right for a battery
    # and wrong for a price spread, and a threshold that reads wrong gets
    # quoted wrong.
    direction_word: str = "cheaper"
    note: str = ""


KNOBS: dict[str, Knob] = {k.name: k for k in (
    Knob("h2_price", "Bought hydrogen price", "GBP/kg",
         ("bought_h2_gbp_per_kg",), "absolute", "down", 0.05, 40.0, ("buy_h2",),
         note="Price only. The carbon intensity of bought hydrogen stays on its "
              "colour's own foreground activity — sweeping the price must not "
              "silently make the hydrogen cleaner too."),
    Knob("ely_capex", "Electrolyser annualised cost", "x today",
         ("cost_ely",), "multiplier", "down", 0.01, 1.0, ("electrolyser",)),
    Knob("fc_capex", "Fuel cell annualised cost", "x today",
         ("cost_fc", "cost_fc_stack_per_mw"), "multiplier", "down", 0.01, 1.0,
         ("fuel_cell",),
         note="Moves the stack replacement cost with the unit, because a fuel "
              "cell that got cheaper to buy did not stay expensive to re-stack."),
    Knob("tank_capex", "Hydrogen store annualised cost", "x today",
         ("cost_tank",), "multiplier", "down", 0.01, 1.0, ("tank",)),
    Knob("h2_chain", "Whole H2 chain annualised cost", "x today",
         ("cost_ely", "cost_tank", "cost_fc", "cost_fc_stack_per_mw"),
         "multiplier", "down", 0.01, 1.0, ("electrolyser", "fuel_cell"),
         note="The headline knob: how much cheaper the make-store-burn chain has "
              "to get as a whole. Reporting the links separately understates the "
              "gap, since no single link carries the chain on its own."),
    Knob("batt_capex", "Battery annualised cost", "x today",
         ("cost_batt_p", "cost_batt_e"), "multiplier", "up", 1.0, 50.0,
         ("battery",), direction_word="dearer",
         note="The competitive threshold rather than the absolute one — it asks "
              "what the battery would have to cost before hydrogen is the better "
              "store. Only meaningful where the battery is unlocked."),
    Knob("price_spread", "Wholesale price spread", "x today",
         ("__price_spread__",), "multiplier", "up", 1.0, 20.0, (),
         direction_word="wider", note=PRICE_SPREAD_NOTE),
)}

DEFAULT_KNOBS = ("h2_chain", "ely_capex", "fc_capex", "tank_capex", "price_spread")


def _search_identity(knob: Knob) -> dict:
    """Fingerprint what determines a threshold's *value*, and nothing else.

    ``dc_runner`` hashes whole model files, and is right to: any edit there can
    move a number. Here the file also holds ``describe`` and ``table``, which
    only format a result that is already on disk. Hashing them would throw away
    hours of solving to reword a sentence, so the fingerprint is the knob's own
    definition plus the three functions that actually steer the search.

    The cost of the precision is that it must be maintained: a new function that
    influences a probe has to be added to ``_STEERS``.
    """
    src = "".join(inspect.getsource(f) for f in _STEERS)
    return {"code": hashlib.sha256(src.encode()).hexdigest()[:12],
            "knob": [knob.fields, knob.mode, knob.sense, knob.floor, knob.ceiling]}


def run_key(site, size_mw_it: float, start: str) -> str:
    """Folder name for one site/size/window, matching ``dc_runner``'s own."""
    return f"{sites.get(site).key}_{size_mw_it:g}MW_{start[:4]}"


def baseline_value(knob: Knob, tech: M.Tech) -> float:
    """The value of this knob in the unperturbed study."""
    if knob.mode == "multiplier":
        return 1.0
    return float(getattr(tech, knob.fields[0]))


def apply(knob: Knob, value: float, tech: M.Tech, series: M.Series):
    """Return (tech, series) with this knob moved to ``value``. Pure."""
    if knob.fields == ("__price_spread__",):
        p = np.asarray(series.grid_price_per_mwh, dtype=float)
        mean = float(p.mean())
        return tech, replace(series, grid_price_per_mwh=mean + value * (p - mean))
    if knob.mode == "multiplier":
        return replace(tech, **{f: float(getattr(tech, f)) * value
                                for f in knob.fields}), series
    return replace(tech, **{f: float(value) for f in knob.fields}), series


# --------------------------------------------------------------------------
#                              one probe, one solve
# --------------------------------------------------------------------------
def _probe(series, assets, tech, knob, value, *, strategy, unserved_fraction,
           gwp_limit):
    """Solve at one knob value and report what hydrogen did."""
    tech_v, series_v = apply(knob, value, tech, series)
    m, V, obj = M.build_model(series_v, assets, tech_v, objective="cost",
                              gwp_limit=gwp_limit,
                              unserved_fraction=unserved_fraction,
                              ely_strategy=strategy)
    M.solve(m)
    # _extract is dc_pareto's own reader for a solved model. Reusing it is
    # deliberate: a threshold row and a Pareto row must report capacities the
    # same way or they cannot be put in the same table.
    row = P._extract(V, obj, series_v, "probe")
    demand_mwh = float(series_v.demand_mw.sum() * series_v.dt_hours) * series_v.annual_scale
    fc_mwh = row.get("cap_fc_MWh_per_year", 0.0)
    row.update({
        "value": float(value),
        "h2_share_of_load": max(fc_mwh / demand_mwh, 0.0) if demand_mwh else 0.0,
        "h2_bought_kg_per_year": float(V["h2_buy"].solution.sum()) * series_v.annual_scale,
        "h2_made_kg_per_year": (
            float(V["p_ely"].solution.sum()) * series_v.dt_hours * series_v.annual_scale
            * 1000.0 / (tech_v.ely_kwh_per_kg + tech_v.tank_compression_kwh_per_kg)),
    })
    row.pop("point", None)
    return row


# --------------------------------------------------------------------------
#                                  bisection
# --------------------------------------------------------------------------
def _bracket_and_bisect(f, knob, base, *, target, rel_tol, max_expand, progress):
    """Find where ``f`` first reaches ``target``, and return it with its curve.

    ``f(value) -> share``. Bracketing walks the helping direction by factors of
    two from the base case until hydrogen appears; the bisection then closes on
    the step between the last value that failed and the first that worked.

    ``curve`` keeps every probe. The trajectory on the way to the threshold is
    worth as much as the threshold itself — it is what says whether hydrogen
    arrives gradually or all at once — and the solves are already paid for.
    """
    helping_down = knob.sense == "down"
    limit = knob.floor if helping_down else knob.ceiling
    curve = []

    def probe(x):
        row = f(x)
        curve.append(row)
        if progress:
            progress(f"{knob.name} @ {x:.4g} -> H2 {row['h2_share_of_load'] * 100:.2f} % of load")
        return row["h2_share_of_load"]

    if probe(base) >= target:
        return {"status": "already_viable", "threshold": base,
                "bracket": [base, base], "curve": curve}

    # Bracket: step towards the helping end until hydrogen appears. ``bad`` is
    # always the last value known to fail, which is what the bisection needs —
    # inferring it as "twice the hit" is wrong on the step that clamps at the
    # limit, and that is exactly the step a marginal knob lands on.
    bad, good = base, None
    for _ in range(max_expand):
        x = max(bad * 0.5, limit) if helping_down else min(bad * 2.0, limit)
        if x == bad:                      # already at the limit, nowhere to go
            break
        if probe(x) >= target:
            good = x
            break
        bad = x
    if good is None:
        # Report the value actually reached, not the configured limit: with a
        # tight ``max_expand`` the search stops short of it, and saying "even at
        # the floor" when the floor was never probed is a lie in the write-up.
        return {"status": "not_reached", "threshold": None,
                "bracket": sorted([bad, base]), "limit_tried": bad,
                "limit_is_floor": bad == limit, "curve": curve}

    # Bisect. ``good`` is always viable and ``bad`` never is, so the interval
    # between them brackets the step no matter which way the knob runs.
    while abs(bad - good) / max(abs(bad), abs(good), 1e-12) > rel_tol:
        mid = 0.5 * (good + bad)
        if probe(mid) >= target:
            good = mid
        else:
            bad = mid
    return {"status": "found", "threshold": good,
            "bracket": sorted([good, bad]), "curve": curve}


# --------------------------------------------------------------------------
#                             the public entry point
# --------------------------------------------------------------------------
def find(scenario, knob_name: str, *, site=sites.DEFAULT_PRESET,
         start: str = "2025-01-01", end: str = "2025-12-29",
         size_mw_it: float = 7.31, pue: float = 1.0,
         resample_hours: float | None = 1.0, cost_case: str = "central",
         horizon_years: float = 25.0, unserved_fraction: float = 0.0,
         connection_headroom: float | None = None,
         h2_colour: str | None = None,
         gwp_limit_kg_per_year: float | None = None,
         target_share: float = ENTRY_SHARE, rel_tol: float = REL_TOL,
         max_expand: int = 12, out_root: Path | None = None,
         refresh: bool = False, progress=None, notice=None,
         _prepared=None) -> dict:
    """Find the value of one input at which hydrogen enters one scenario's build.

    ``scenario`` is a ``dc_architectures.Scenario``. ``h2_colour`` overrides the
    scenario's own colour, which is what lets a price threshold be found on an
    architecture that may buy hydrogen but was never given one — the colour
    supplies the *carbon* intensity while the knob sweeps the price.

    ``gwp_limit_kg_per_year`` caps annual carbon, so the question becomes "at a
    stated carbon target, when does hydrogen enter" rather than "when is it
    cheapest outright". Left off, the probe is a pure min-cost solve.
    """
    knob = KNOBS[knob_name]
    site = sites.get(site)
    # Scoped by site, size and year exactly as dc_runner scopes dc_runs. Keying
    # on the scenario alone would have two sites' answers to the same question
    # overwrite one another, and each would look authoritative on arrival.
    out_root = Path(out_root) if out_root else OUT_ROOT / run_key(
        site, size_mw_it, start)
    colour = h2_colour or scenario.h2_colour

    cfg = {
        "scenario": {"key": scenario.key, "architecture": scenario.architecture,
                     "ely_tech": scenario.ely_tech, "strategy": scenario.strategy,
                     "tank_design": scenario.tank_design, "assets": scenario.assets},
        "h2_colour": colour,
        "site": {"key": site.key, "lat": site.lat, "lon": site.lon,
                 "tnuos_zone": site.tnuos_zone, "tdr_band": site.tdr_band,
                 "connection_limit_mw": site.connection_limit_mw},
        "start": start, "end": end, "size_mw_it": size_mw_it, "pue": pue,
        "resample_hours": resample_hours, "cost_case": cost_case,
        "horizon_years": horizon_years, "unserved_fraction": unserved_fraction,
        "connection_headroom": connection_headroom,
        "gwp_limit_kg_per_year": gwp_limit_kg_per_year,
        "knob": knob.name, "target_share": target_share, "rel_tol": rel_tol,
        "coefficients": dc_runner._coefficient_identity(),
        "search": _search_identity(knob),
    }
    h = dc_runner.config_hash(cfg)
    folder = out_root / scenario.key
    path = folder / f"{knob.name}.json"
    if path.exists() and not refresh:
        try:
            cached = json.loads(path.read_text())
            if cached.get("config_hash") == h:
                cached["cached"] = True
                return cached
        except Exception:
            pass

    t0 = time.time()
    series, assets, tech, meta = (_prepared or prepare(
        scenario, site=site, start=start, end=end, size_mw_it=size_mw_it, pue=pue,
        resample_hours=resample_hours, cost_case=cost_case,
        horizon_years=horizon_years, connection_headroom=connection_headroom,
        h2_colour=colour, notice=notice))

    missing = [f for f in knob.needs if not getattr(assets, f)]
    if missing:
        result = {"status": "not_applicable",
                  "reason": f"{scenario.key} cannot build {', '.join(missing)}, "
                            f"so {knob.name} cannot change its answer.",
                  "threshold": None, "curve": []}
    else:
        base = baseline_value(knob, tech)
        def f(value):
            return _probe(series, assets, tech, knob, value,
                          strategy=scenario.strategy,
                          unserved_fraction=unserved_fraction,
                          gwp_limit=gwp_limit_kg_per_year)
        result = _bracket_and_bisect(f, knob, base, target=target_share,
                                     rel_tol=rel_tol, max_expand=max_expand,
                                     progress=progress)
        result["baseline_value"] = base
        if result.get("threshold") is not None and knob.mode == "absolute":
            result["baseline_unit"] = knob.unit
        result["monotone"] = _check_monotone(result["curve"], knob)

    thr = result.get("threshold")
    base = result.get("baseline_value")
    result.update({
        "scenario": scenario.key, "label": scenario.label,
        "knob": knob.name, "knob_label": knob.label, "unit": knob.unit,
        "sense": knob.sense, "direction_word": knob.direction_word,
        "knob_note": knob.note,
        "site": site.key, "site_name": site.name, "start": start, "end": end,
        "size_mw_it": size_mw_it, "pue": pue, "cost_case": cost_case,
        "resample_hours": resample_hours,
        "gwp_limit_kg_per_year": gwp_limit_kg_per_year,
        "target_share": target_share,
        "h2_colour": colour,
        "ratio_to_today": (thr / base if thr is not None and base else None),
        "solves": len(result.get("curve", [])),
        "solve_seconds": time.time() - t0,
        "perfect_foresight": True,
        "config_hash": h, "cached": False,
    })
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, default=str))
    return result


def prepare(scenario, *, site, start, end, size_mw_it, pue, resample_hours,
            cost_case, horizon_years, connection_headroom, h2_colour, notice=None):
    """Series, assets, tech and meta for one scenario — built once, swept many.

    Split out because every knob on a scenario shares them, and rebuilding the
    coefficients per knob would cost more than the solves do.
    """
    from optimisation import dc_inputs as I

    site = sites.get(site)
    series, meta = I.build_series(site, start, end, size_mw_it, pue=pue,
                                  connection_headroom=connection_headroom,
                                  on_progress=notice)
    if resample_hours:
        series = I.resample(series, resample_hours)
    tech = I.build_tech(site, meta, ely_tech=scenario.ely_tech or "PEM operation",
                        tank_design=scenario.tank_design, h2_colour=h2_colour,
                        cost_case=cost_case, horizon_years=horizon_years,
                        size_mw_it=size_mw_it, pue=pue)
    assets = A.architecture(scenario.architecture, offshore=site.offshore_wind,
                            grid_limit_mw=meta["connection_limit_mw"],
                            flags=scenario.assets)
    # Same guard dc_runner applies, for the same reason: an architecture that
    # may buy hydrogen with no colour priced would buy it free and carbon-free.
    # Supplying a colour is what unlocks it — see find(h2_colour=...).
    if h2_colour is None and assets.buy_h2:
        assets = replace(assets, buy_h2=False)
    return series, assets, tech, meta


def _check_monotone(curve, knob) -> bool:
    """Did hydrogen's share actually move the way the knob's sense claims?

    A false here does not mean the bisection crashed — it means the threshold it
    converged on is one step among several and should not be quoted as *the*
    tipping point.
    """
    if len(curve) < 3:
        return True
    df = pd.DataFrame(curve).sort_values("value")
    share = df["h2_share_of_load"].to_numpy()
    d = np.diff(share)
    tol = 1e-6
    return bool((d <= tol).all() if knob.sense == "down" else (d >= -tol).all())


# Every function whose edit could move a threshold. Reporting is deliberately
# absent — see _search_identity.
_STEERS = (apply, _probe, _bracket_and_bisect)


# --------------------------------------------------------------------------
#                        inheriting a solved run's settings
# --------------------------------------------------------------------------
def from_run(run_folder) -> dict:
    """The scenario and settings that produced a solved front, ready for ``find``.

    A threshold only means anything *against a particular answer* — this site,
    this year, this size, this kit. Retyping those settings is how you end up
    quoting a 7 MW London threshold against a 100 MW Highland front, so the
    settings are read back from the run's own ``config.json`` rather than
    supplied a second time.

    Two of them are read back in their **derived** form on purpose. ``run_one``
    overwrites ``tdr_band`` and ``connection_limit_mw`` in the config with what
    the run was actually charged and held to, so passing them straight into a
    pinned ``Site`` reproduces the run exactly instead of re-deriving something
    close to it.

    ``stale`` says the coefficient tables or the model source have moved since
    that front was solved. The threshold would still compute, and it would be
    annotating a result that no longer exists — so the flag is returned rather
    than swallowed, and the caller decides whether to say so or refuse.
    """
    folder = Path(run_folder)
    cfg = json.loads((folder / "config.json").read_text())
    sc, site_cfg = dict(cfg["scenario"]), cfg["site"]

    # Scenario grew fields after some runs were written, and will again. Drop
    # what this version does not know rather than failing on an old folder.
    known = {f for f in A.Scenario.__dataclass_fields__}
    scenario = A.Scenario(**{k: v for k, v in sc.items() if k in known})

    site = sites.resolve(
        site_cfg["lat"], site_cfg["lon"], name=site_cfg.get("name"),
        carbon_api_region=site_cfg.get("carbon_api_region"),
        tdr_band=site_cfg.get("tdr_band"),
        connection_limit_mw=site_cfg.get("connection_limit_mw"),
        transmission_connected=site_cfg.get("transmission_connected"))

    now = dc_runner._coefficient_identity()
    was = cfg.get("coefficients") or {}
    moved = sorted(k for k in set(now) | set(was) if now.get(k) != was.get(k))

    return {
        "scenario": scenario,
        "kwargs": {
            "site": site,
            "start": cfg["start"], "end": cfg["end"],
            "size_mw_it": cfg["size_mw_it"], "pue": cfg["pue"],
            "resample_hours": cfg.get("resample_hours"),
            "cost_case": cfg["cost_case"],
            "horizon_years": cfg["horizon_years"],
            "unserved_fraction": cfg.get("unserved_fraction", 0.0),
            "connection_headroom": site_cfg.get("connection_headroom"),
            "h2_colour": scenario.h2_colour,
        },
        "config": cfg,
        "stale": bool(moved),
        "stale_keys": moved,
    }


def applicable_knobs(scenario) -> list[str]:
    """The knobs that can change *this* configuration's answer.

    An architecture with no battery cannot be told the battery got dearer, and
    one that cannot buy hydrogen has no purchase price to sweep. Offering those
    anyway costs a solve each to be told ``not_applicable``.
    """
    assets = A.architecture(scenario.architecture, flags=scenario.assets,
                            offshore=True)
    # Buying needs a priced colour, exactly as prepare() enforces.
    can = {f: bool(getattr(assets, f)) for f in
           ("battery", "electrolyser", "tank", "fuel_cell")}
    can["buy_h2"] = bool(assets.buy_h2 and scenario.h2_colour)
    return [name for name, k in KNOBS.items()
            if all(can.get(f, False) for f in k.needs)]


def estimate_solves(knobs) -> int:
    """Rough LP count for a set of knobs — for a page that must warn before it runs.

    Measured over the 15 searches behind the London study: 8.2 solves each,
    ranging 6 to 10. Rounded up, because a page that under-promises a wait is
    worse than one that over-promises it.
    """
    return 9 * len([k for k in knobs])


# --------------------------------------------------------------------------
#                                  the sweep
# --------------------------------------------------------------------------
def sweep(scenario, knobs=DEFAULT_KNOBS, *, progress=None, **kw) -> list[dict]:
    """Every knob on one scenario, sharing one build of the coefficients."""
    site = sites.get(kw.get("site", sites.DEFAULT_PRESET))
    prep = prepare(
        scenario, site=site,
        start=kw.get("start", "2025-01-01"), end=kw.get("end", "2025-12-29"),
        size_mw_it=kw.get("size_mw_it", 7.31), pue=kw.get("pue", 1.0),
        resample_hours=kw.get("resample_hours", 1.0),
        cost_case=kw.get("cost_case", "central"),
        horizon_years=kw.get("horizon_years", 25.0),
        connection_headroom=kw.get("connection_headroom"),
        h2_colour=kw.get("h2_colour") or scenario.h2_colour,
        notice=kw.get("notice"))
    out = []
    for name in knobs:
        if progress:
            progress(f"{scenario.key}: {name}")
        out.append(find(scenario, name, progress=progress, _prepared=prep, **kw))
    return out


def table(results) -> pd.DataFrame:
    """One row per threshold, in the shape a write-up wants."""
    rows = []
    for r in results:
        thr, ratio = r.get("threshold"), r.get("ratio_to_today")
        rows.append({
            "scenario": r["scenario"], "knob": r["knob"],
            "knob_label": r.get("knob_label"), "unit": r.get("unit"),
            "status": r["status"], "today": r.get("baseline_value"),
            "threshold": thr, "ratio_to_today": ratio,
            "needs": (None if ratio is None else
                      (f"{(1 - ratio) * 100:.0f} % {r.get('direction_word', 'cheaper')}"
                       if r.get("sense") == "down"
                       else f"{ratio:.1f}x {r.get('direction_word', 'dearer')}")),
            "monotone": r.get("monotone"), "solves": r.get("solves"),
            "seconds": round(r.get("solve_seconds", 0.0), 1),
        })
    return pd.DataFrame(rows)


def records(results) -> list[dict]:
    """``table`` as JSON-safe dicts — pandas turns a missing threshold into NaN.

    ``json.dumps`` writes that as bare ``NaN``, which Python reads back and most
    other readers reject. A threshold that was never found is *absent*, not
    not-a-number, so it goes out as null.
    """
    df = table(results)
    return [{k: (None if pd.isna(v) else v) for k, v in row.items()}
            for row in df.to_dict("records")]


def load_run(out_root, scenario_key: str | None = None) -> list[dict]:
    """Every threshold on disk under one results folder, newest schema first.

    Reading from disk rather than from a job's summary is deliberate: the page
    must show a sweep that finished in a browser session that has since closed.
    """
    root = Path(out_root)
    pattern = f"{scenario_key}/*.json" if scenario_key else "*/*.json"
    out = []
    for f in sorted(root.glob(pattern)):
        if f.name in ("config.json", "status.json", "request.json", "summary.json"):
            continue
        try:
            r = json.loads(f.read_text())
        except Exception:
            continue
        if "knob" in r and "status" in r:
            out.append(r)
    return out


def curve_frame(result) -> pd.DataFrame:
    """Every probe behind one threshold, sorted by knob value."""
    if not result.get("curve"):
        return pd.DataFrame()
    return (pd.DataFrame(result["curve"]).sort_values("value")
            .reset_index(drop=True))


def describe(r: dict) -> str:
    """One paragraph a reader can act on."""
    if r["status"] == "not_applicable":
        return f"{r['knob']}: not applicable — {r['reason']}"
    unit, share = r.get("unit", ""), r.get("target_share", ENTRY_SHARE) * 100
    if r["status"] == "already_viable":
        return (f"{r['knob_label']}: hydrogen already carries {share:.0f} % of load "
                f"at today's {r['baseline_value']:.4g} {unit} — no threshold to find.")
    if r["status"] == "not_reached":
        return (f"{r['knob_label']}: hydrogen never reaches {share:.0f} % of load, "
                f"even at {r['limit_tried']:.4g} {unit} ({r['solves']} solves"
                f"{'' if r.get('limit_is_floor') else ', search limit not the floor'}"
                f"). This input alone cannot get there.")
    lo, hi = r["bracket"]
    ratio = r.get("ratio_to_today")
    word = r.get("direction_word", "cheaper" if r.get("sense") == "down" else "dearer")
    move = ("" if ratio is None else
            f", which is {(1 - ratio) * 100:.0f} % {word} than today"
            if r.get("sense") == "down" else
            f", which is {ratio:.1f}x {word} than today")
    warn = "" if r.get("monotone", True) else \
        "  NON-MONOTONE — quote the curve, not this number."
    return (f"{r['knob_label']}: hydrogen reaches {share:.0f} % of load at "
            f"{r['threshold']:.4g} {unit} (today {r['baseline_value']:.4g}; "
            f"bracket {lo:.4g}-{hi:.4g}){move}.{warn}")


def run():
    """The headline case: the everything-available control at the London site."""
    scen = next(s for s in A.core_matrix() if s.architecture == "res_h2_grid")
    print("=" * 78)
    print("HYDROGEN ENTRY THRESHOLDS —", scen.label)
    print("=" * 78)
    res = sweep(scen, ("h2_chain",), progress=lambda s: print("   ", s))
    print()
    for r in res:
        print(" ", describe(r))
    print()
    print(table(res).to_string(index=False))


if __name__ == "__main__":
    run()
