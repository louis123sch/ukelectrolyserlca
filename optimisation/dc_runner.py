"""
Running the matrix — caching, parallelism, and results on disk.
=============================================================================

25 configurations x a 13-point Pareto sweep is 325 LP solves. At half-hourly
resolution that is hours; hourly resampling and eight cores brings it to
minutes. This module owns that arithmetic so neither the CLI nor the Streamlit
page has to.

What it writes, per scenario
----------------------------
``<out>/<scenario key>/``

``config.json``      everything needed to reproduce the run, including a hash
``pareto.parquet``   the full front, one row per point, with the capacity mix
``summary.json``     the atom the UI and the comparison plots read
``dispatch.parquet`` the half-hourly dispatch behind the shown points only —
                     written when ``save_dispatch`` is set, which the Streamlit
                     page always does because it charts it

Caching is on the **config hash**, which covers the scenario, the site, the
window, the size, the resolution and the coefficient tables' own identity. Change
a coefficient and re-run and the cache correctly misses; re-run unchanged and it
costs nothing. ``--refresh`` forces recomputation.

Parallelism
-----------
Over scenarios, not over Pareto points, because the epsilon sweep inside a
scenario is inherently sequential — each limit is set from the two anchors. Each
worker builds its own model; the series and coefficients are cheap to rebuild
from cache and expensive to pickle, so they are rebuilt per worker rather than
passed.

Run:  python scripts/run_dc_scenarios.py --help
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_ROOT = ROOT / "optimisation_outputs" / "dc_runs"

from optimisation import dc_architectures as A
from optimisation import sites
from optimisation import dc_model as M
from optimisation import dc_pareto as P


def config_hash(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def _coefficient_identity() -> dict:
    """Fingerprint the inputs *and the model code* so a cache cannot outlive them.

    The coefficient tables are the obvious half. The model source is the other
    half, and it was learned the hard way: a fix to the surplus-only constraint
    silently left three stale scenario folders on disk, because the config hash
    covered only what the user typed. A cached result that predates a
    formulation change is worse than no cache, since it looks authoritative.
    """
    def digest(f: Path):
        return hashlib.sha256(f.read_bytes()).hexdigest()[:12] if f.exists() else None

    out = {}
    # What build_tech actually reads: the recommended H2 prices and every
    # decomposition cache. h2_capex.csv is deliberately absent — nothing reads
    # it; h2_capex.py is computed live and is fingerprinted below instead.
    outputs = ROOT / "optimisation_outputs"
    for f in [outputs / "tech_lca_coefficients.csv", outputs / "h2_prices_recommended.csv",
              outputs / "bought_h2_gwp_cache.json",
              *sorted(outputs.glob("*_decomposition*_cache.json"))]:
        out[f.name] = digest(f)
    # The model, and every module that turns a source into a coefficient. The
    # constants live in code (calendar lives, capex, discount rates), so a
    # cache keyed on the tables alone reused runs across a coefficient change.
    # grid_build/profiles/network_charges decide what the series *mean* (the
    # UTC clock fix changed every grid file under an unchanged file name).
    for name in ("dc_model.py", "dc_pareto.py", "dc_inputs.py", "dc_architectures.py",
                 "grid_build.py", "profiles.py", "network_charges.py",
                 "battery.py", "tech_costs.py", "renewables.py", "transformers.py",
                 "h2_prices.py", "h2_capex.py", "h2_storage.py", "fuel_cell.py",
                 "electrolysers.py", "grid_connection.py", "sites.py",
                 "conversion_losses.py"):
        out[name] = digest(ROOT / "optimisation" / name)
    out["dc_config.py"] = digest(ROOT / "dc_config.py")
    return out


def run_one(scenario: A.Scenario, *, site, start: str, end: str,
            connection_headroom: float | None = None,
            connection_mode: str | None = None,
            size_mw_it: float, pue: float, resample_hours: float | None,
            points: int, cost_case: str, horizon_years: float,
            unserved_fraction: float, out_root: Path,
            gwp_target_kg_per_year: float | None = None,
            green_h2_grid_share: float | None = None,
            batt_standing_loss_per_hour: float | None = None,
            tank_leakage_per_hour: float | None = None,
            save_dispatch: bool = False, refresh: bool = False,
            progress=None, notice=None) -> dict:
    """Solve one configuration's Pareto front and write it to disk.

    ``progress`` is called with a short tag per LP ("min_cost", "eps 3/12").
    Only the single-configuration path uses it — across the matrix, progress is
    reported per scenario by ``run_matrix`` instead, since the workers are in
    other processes.

    ``notice`` is the same idea for the step before the LPs: it is called if
    the window's grid series has to be built first, which is minutes to hours
    of notebook, and is otherwise the one stretch of a run that reports
    nothing.
    """
    from optimisation import dc_inputs as I
    import dc_config

    if pue is None:            # recorded as used, so the hash and summary say it
        pue = float(dc_config.DC_REFERENCE_PUE)
    site = sites.get(site)
    cfg = {
        "scenario": asdict(scenario),
        "site": {"key": site.key, "name": site.name, "lat": site.lat, "lon": site.lon,
                 "carbon_api_region": site.carbon_api_region,
                 "tnuos_zone": site.tnuos_zone, "tdr_band": site.tdr_band,
                 "connection_limit_mw": site.connection_limit_mw},
        "start": start, "end": end,
        "size_mw_it": size_mw_it, "pue": pue, "resample_hours": resample_hours,
        "points": points, "cost_case": cost_case, "horizon_years": horizon_years,
        "unserved_fraction": unserved_fraction,
        # Hashed as asked; the value actually used is recorded on the site
        # below, after the series is built.
        "connection_headroom": connection_headroom,
        # How the price list is chosen (COST_PLAN §1.11): None is the default
        # mode, which is hashed by name below once the series says what it was.
        "connection_mode": connection_mode,
        "gwp_target_kg_per_year": gwp_target_kg_per_year,
        # In the hash, not just in build_tech's arguments: the share moves both
        # the price and the burden of bought green hydrogen, so a cached run at
        # a different share is a different answer.
        "green_h2_grid_share": green_h2_grid_share,
        # Same reason: each moves one store's losses, so a run cached at the
        # default (None) is not an answer at any other point of the band.
        "batt_standing_loss_per_hour": batt_standing_loss_per_hour,
        "tank_leakage_per_hour": tank_leakage_per_hour,
        "coefficients": _coefficient_identity(),
    }
    h = config_hash(cfg)
    folder = out_root / scenario.key
    summary_path = folder / "summary.json"

    # A cached run that predates the dispatch capture has a valid summary and no
    # dispatch.parquet. Asking for the dispatch has to miss the cache, or the
    # page would offer a chart it can never draw.
    if summary_path.exists() and not refresh:
        try:
            cached = json.loads(summary_path.read_text(encoding="utf-8"))
            if cached.get("config_hash") == h and (
                    not save_dispatch or (folder / "dispatch.parquet").exists()):
                cached["cached"] = True
                return cached
        except Exception:
            pass

    t0 = time.time()
    series, meta = I.build_series(site, start, end, size_mw_it, pue=pue,
                                  connection_headroom=connection_headroom,
                                  connection_mode=connection_mode,
                                  grid=A.architecture(scenario.architecture, flags=scenario.assets).grid,
                                  on_progress=notice)
    # Record what was *used*, not what was asked for. site.tdr_band is None
    # whenever the band is derived from the load, so writing it straight into
    # the config would leave the run with no record of the band it was actually
    # charged on — and a config that cannot reproduce its own run is worse than
    # no config.
    cfg["site"]["tdr_band"] = meta["tdr_band"]
    cfg["site"]["tdr_band_source"] = ("pinned on the site" if site.tdr_band
                                      else "derived from the load")
    cfg["site"]["transmission_connected"] = meta["transmission_connected"]
    cfg["site"]["connection_limit_mw"] = meta["connection_limit_mw"]
    cfg["site"]["connection_headroom"] = meta["connection_headroom"]
    cfg["site"]["connection_limit_source"] = ("pinned on the site"
                                              if site.connection_limit_mw is not None
                                              else "derived from the load")
    cfg["site"]["connection_mode"] = meta.get("connection_mode")
    cfg["site"]["connection_chosen_by"] = meta.get("connection_chosen_by")
    if resample_hours:
        series = I.resample(series, resample_hours)
    tech = I.build_tech(site, meta, ely_tech=scenario.ely_tech or "PEM operation",
                        tank_design=scenario.tank_design, h2_colour=scenario.h2_colour,
                        h2_colour_2=scenario.h2_colour_2,
                        soec_heat=scenario.soec_heat,
                        green_h2_grid_share=green_h2_grid_share,
                        batt_standing_loss_per_hour=batt_standing_loss_per_hour,
                        tank_leakage_per_hour=tank_leakage_per_hour,
                        cost_case=cost_case, horizon_years=horizon_years,
                        size_mw_it=size_mw_it, pue=pue)
    # The ceiling the band was read from is the ceiling the LP is held to.
    # Deriving one and optimising against the other is exactly the incoherence
    # this chain exists to remove.
    assets = A.architecture(scenario.architecture,
                            offshore=site.offshore_wind,
                            grid_limit_mw=meta["connection_limit_mw"],
                            grid_floor_mw=meta.get("connection_floor_mw", 0.0),
                            flags=scenario.assets)
    # An architecture that *may* buy hydrogen still needs a priced colour on
    # each stream it unlocks. Without one the LP buys it free and carbon-free;
    # see the guard in dc_model.build_model. Locking the unpriced stream off is
    # the right default: the scenario builds its own hydrogen instead.
    from dataclasses import replace as _replace
    if scenario.h2_colour is None and assets.buy_h2:
        assets = _replace(assets, buy_h2=False)
    if scenario.h2_colour_2 is None and assets.buy_h2_2:
        assets = _replace(assets, buy_h2_2=False)
    result = P.front(series, assets, tech, points=points,
                     ely_strategy=scenario.strategy,
                     unserved_fraction=unserved_fraction,
                     gwp_target=gwp_target_kg_per_year,
                     progress=progress, keep_dispatch=save_dispatch)

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "config.json").write_text(json.dumps(cfg, indent=2, default=str), encoding="utf-8")
    result["front"].to_parquet(folder / "pareto.parquet", index=False)
    if result.get("dispatch"):
        # One long frame rather than one file per point: three or four points of
        # a year at hourly steps is a few MB, and a single file cannot go stale
        # against its own siblings.
        disp = pd.concat([d.assign(point=name) for name, d in result["dispatch"].items()])
        disp.index.name = "t"
        disp.reset_index().to_parquet(folder / "dispatch.parquet", index=False)

    mwh = float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale
    summary = {
        "key": scenario.key, "n": scenario.n, "label": scenario.label,
        "architecture": scenario.architecture, "ely_tech": scenario.ely_tech,
        "soec_heat": tech.labels.get("soec_heat"),
        "h2_colour": scenario.h2_colour, "h2_colour_2": scenario.h2_colour_2,
        "green_h2_grid_share": tech.labels.get("green_h2_grid_share"),
        # The values used, defaults included (both zero and ASSUMED).
        "batt_standing_loss_per_hour": tech.labels.get("batt_standing_loss_per_hour"),
        "tank_leakage_per_hour": tech.labels.get("tank_leakage_per_hour"),
        "strategy": scenario.strategy,
        "site": site.key, "site_name": site.name,
        "lat": site.lat, "lon": site.lon,
        "carbon_api_region": site.carbon_api_region, "tnuos_zone": site.tnuos_zone,
        "start": start, "end": end,
        "size_mw_it": size_mw_it, "pue": pue,
        "resample_hours": resample_hours, "cost_case": cost_case,
        "slices": series.n, "demand_MWh_per_year": mwh,
        "degenerate": result["degenerate"],
        "min_cost": result["min_cost"], "min_gwp": result["min_gwp"],
        "knee": result["knee"], "carbon_price": result["carbon_price"],
        "max_curvature": result["max_curvature"],
        "carbon_price_GBP_per_tCO2": result.get("carbon_price_GBP_per_tCO2"),
        "target": result.get("target"),
        "target_gwp_kgco2e_per_year": result.get("target_gwp_kgco2e_per_year"),
        "target_note": result.get("target_note"),
        "assets": scenario.assets,
        "network_charges": meta.get("network_charges"),
        "connection_limit_mw": meta.get("connection_limit_mw"),
        "connection_floor_mw": meta.get("connection_floor_mw", 0.0),
        "tdr_band": meta.get("tdr_band"),
        "transmission_connected": meta.get("transmission_connected"),
        # The price list: chosen by the optimiser among these options, or fixed
        # by the rule (COST_PLAN §1.11). The option each point chose is in the
        # point itself (connection_option, connection_tier, ... from dc_pareto).
        "connection_mode": meta.get("connection_mode"),
        "connection_chosen_by": meta.get("connection_chosen_by"),
        "connection_options": meta.get("connection_options"),
        "connection_options_dropped": meta.get("connection_options_dropped"),
        "connection_options_note": meta.get("connection_options_note"),
        "connection_reference": meta.get("connection_reference"),
        "connection_groups": meta.get("connection_groups"),
        "register_freshness": meta.get("register_freshness"),
        # Points whose connection sits on its band's floor: a lower band would
        # probably be cheaper, so re-run with the ceiling just below the floor.
        # With the price list chosen in the LP the floor is the chosen band's,
        # so sitting on it means the band below was dearer or too small.
        "grid_floor_binding": _floor_binding(result, assets),
        "perfect_foresight": True,
        "solve_seconds": time.time() - t0,
        "config_hash": h, "cached": False,
        "note": scenario.note,
    }
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def _floor_binding(result: dict, assets) -> list[str]:
    out = []
    for name in ("min_cost", "knee", "min_gwp"):
        p = result.get(name)
        if not isinstance(p, dict):
            continue
        floor = p.get("connection_floor_mw")                  # the chosen option's, when chosen
        if floor is None:
            floor = assets.grid_floor_mw if assets.grid else 0.0
        if floor > 0 and p.get("cap_grid", 0.0) <= floor * (1 + 1e-6):
            out.append(name)
    return out


def _worker(args):
    scenario, kw = args
    try:
        return run_one(scenario, **kw)
    except Exception as exc:
        return {"key": scenario.key, "n": scenario.n, "label": scenario.label,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}


def run_matrix(scenarios=None, *, site=sites.DEFAULT_PRESET, start="2025-01-01",
               end="2025-12-29", size_mw_it=100.0, pue=None,
               resample_hours=1.0, points=12, cost_case="central",
               horizon_years=25.0, unserved_fraction=0.0,
               gwp_target_kg_per_year=None, connection_headroom=None,
               connection_mode=None,
               green_h2_grid_share=None,
               batt_standing_loss_per_hour=None, tank_leakage_per_hour=None,
               out_root: Path | None = None, workers=None,
               save_dispatch=False, refresh=False, progress=print) -> pd.DataFrame:
    """Solve every configuration, in parallel, and return the comparison table."""
    scenarios = scenarios if scenarios is not None else A.core_matrix()
    site = sites.get(site)
    out_root = Path(out_root or OUT_ROOT / f"{site.key}_{size_mw_it:g}MW_{start[:4]}")
    out_root.mkdir(parents=True, exist_ok=True)

    kw = dict(site=site, start=start, end=end, size_mw_it=size_mw_it, pue=pue,
              resample_hours=resample_hours, points=points, cost_case=cost_case,
              horizon_years=horizon_years, unserved_fraction=unserved_fraction,
              gwp_target_kg_per_year=gwp_target_kg_per_year,
              green_h2_grid_share=green_h2_grid_share,
              batt_standing_loss_per_hour=batt_standing_loss_per_hour,
              tank_leakage_per_hour=tank_leakage_per_hour,
              connection_headroom=connection_headroom, connection_mode=connection_mode,
              out_root=out_root, save_dispatch=save_dispatch, refresh=refresh)

    results, t0 = [], time.time()
    if workers == 1:
        for s in scenarios:
            results.append(_worker((s, kw)))
            _report(results[-1], len(results), len(scenarios), progress)
    else:
        # Windows caps a process pool at 61 workers (63 handles minus the
        # result queue and the wakeup reader) and raises ValueError above that,
        # before a single LP is solved. The same --workers that runs on the
        # study's other machine should degrade here, not abort.
        if workers and sys.platform == "win32" and workers > 61:
            print(f"Windows caps a process pool at 61 workers; using 61 "
                  f"rather than the {workers} asked for.")
            workers = 61
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_worker, (s, kw)): s for s in scenarios}
            for i, fut in enumerate(as_completed(futures), 1):
                results.append(fut.result())
                _report(results[-1], i, len(scenarios), progress)

    ok = [r for r in results if "error" not in r]
    bad = [r for r in results if "error" in r]
    progress(f"\n{len(ok)}/{len(scenarios)} solved in {time.time() - t0:.0f} s")
    for r in bad:
        progress(f"  FAILED {r['key']}: {r['error']}")

    df = comparison_table(ok)
    if len(df):
        df.to_csv(out_root / "comparison.csv", index=False)
        progress(f"Wrote {out_root / 'comparison.csv'}")
    return df


def _report(r, i, n, progress):
    if "error" in r:
        progress(f"[{i}/{n}] {r['key']:<40} FAILED  {r['error'][:60]}")
    else:
        tag = "cached" if r.get("cached") else f"{r['solve_seconds']:.0f}s"
        progress(f"[{i}/{n}] {r['key']:<40} {tag:>8}  "
                 f"knee £{r['knee']['cost_GBP_per_year'] / 1e6:.2f}m / "
                 f"{r['knee']['gwp_kgco2e_per_year'] / 1000:,.0f}t")


def comparison_table(summaries) -> pd.DataFrame:
    """One row per configuration, at each of the three answers."""
    rows = []
    for s in summaries:
        points = ["min_cost", "min_gwp", "knee"]
        if s.get("target"):
            points.append("target")
        for point in points:
            p = s[point]
            rows.append({
                "n": s["n"], "key": s["key"], "label": s["label"],
                "architecture": s["architecture"], "strategy": s["strategy"],
                "ely": (s["ely_tech"] or "-").split()[0]
                       + (" (e-boiler)" if s.get("soec_heat") == "electric_boiler" else ""),
                "h2_colour": " + ".join(
                    c for c in (s["h2_colour"], s.get("h2_colour_2")) if c) or "-",
                "point": point, "degenerate": s["degenerate"],
                "cost_m_GBP_per_year": p["cost_GBP_per_year"] / 1e6,
                "gwp_t_per_year": p["gwp_kgco2e_per_year"] / 1000.0,
                "gwp_g_per_kWh": p["gwp_g_per_kWh"],
                "cost_GBP_per_MWh": p["cost_GBP_per_MWh"],
                **{k: p[k] for k in P.CAPACITY_VARS},
            })
    df = pd.DataFrame(rows)
    return df.sort_values(["n", "point"]).reset_index(drop=True) if len(df) else df


def load_results(out_root: Path) -> list[dict]:
    """Read back every summary.json under a results folder."""
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(out_root).glob("*/summary.json"))]
