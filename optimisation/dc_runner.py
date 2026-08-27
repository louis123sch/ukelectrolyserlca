"""
Running the matrix — caching, parallelism, and results on disk.
=============================================================================

21 configurations x a 13-point Pareto sweep is 273 LP solves. At half-hourly
resolution that is hours; hourly resampling and eight cores brings it to
minutes. This module owns that arithmetic so neither the CLI nor the Streamlit
page has to.

What it writes, per scenario
----------------------------
``<out>/<scenario key>/``

``config.json``      everything needed to reproduce the run, including a hash
``pareto.parquet``   the full front, one row per point, with the capacity mix
``summary.json``     the atom the UI and the comparison plots read
``dispatch.parquet`` optional, large, flag-gated

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
    out = {}
    for name in ("tech_lca_coefficients.csv", "h2_capex.csv"):
        f = ROOT / "optimisation_outputs" / name
        out[name] = hashlib.sha256(f.read_bytes()).hexdigest()[:12] if f.exists() else None
    for name in ("dc_model.py", "dc_pareto.py", "dc_inputs.py", "dc_architectures.py"):
        f = ROOT / "optimisation" / name
        out[name] = hashlib.sha256(f.read_bytes()).hexdigest()[:12] if f.exists() else None
    return out


def run_one(scenario: A.Scenario, *, site, start: str, end: str,
            size_mw_it: float, pue: float, resample_hours: float | None,
            points: int, cost_case: str, horizon_years: float,
            unserved_fraction: float, out_root: Path,
            gwp_target_kg_per_year: float | None = None,
            save_dispatch: bool = False, refresh: bool = False,
            progress=None) -> dict:
    """Solve one configuration's Pareto front and write it to disk.

    ``progress`` is called with a short tag per LP ("min_cost", "eps 3/12").
    Only the single-configuration path uses it — across the matrix, progress is
    reported per scenario by ``run_matrix`` instead, since the workers are in
    other processes.
    """
    from optimisation import dc_inputs as I

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
        "gwp_target_kg_per_year": gwp_target_kg_per_year,
        "coefficients": _coefficient_identity(),
    }
    h = config_hash(cfg)
    folder = out_root / scenario.key
    summary_path = folder / "summary.json"

    if summary_path.exists() and not refresh:
        try:
            cached = json.loads(summary_path.read_text())
            if cached.get("config_hash") == h:
                cached["cached"] = True
                return cached
        except Exception:
            pass

    t0 = time.time()
    series, meta = I.build_series(site, start, end, size_mw_it, pue=pue)
    if resample_hours:
        series = I.resample(series, resample_hours)
    tech = I.build_tech(site, meta, ely_tech=scenario.ely_tech or "PEM operation",
                        tank_design=scenario.tank_design, h2_colour=scenario.h2_colour,
                        cost_case=cost_case, horizon_years=horizon_years,
                        size_mw_it=size_mw_it, pue=pue)
    assets = A.architecture(scenario.architecture,
                            offshore=site.offshore_wind,
                            grid_limit_mw=site.connection_limit_mw,
                            flags=scenario.assets)
    if scenario.h2_colour is None and assets.buy_h2:
        # An architecture that *may* buy hydrogen still needs a priced colour.
        # Without one the LP buys it free and carbon-free; see the guard in
        # dc_model.build_model. Locking it off is the right default: the
        # scenario builds its own hydrogen instead.
        from dataclasses import replace as _replace
        assets = _replace(assets, buy_h2=False)
    result = P.front(series, assets, tech, points=points,
                     ely_strategy=scenario.strategy,
                     unserved_fraction=unserved_fraction,
                     gwp_target=gwp_target_kg_per_year,
                     progress=progress)

    folder.mkdir(parents=True, exist_ok=True)
    (folder / "config.json").write_text(json.dumps(cfg, indent=2, default=str))
    result["front"].to_parquet(folder / "pareto.parquet", index=False)

    mwh = float(series.demand_mw.sum() * series.dt_hours) * series.annual_scale
    summary = {
        "key": scenario.key, "n": scenario.n, "label": scenario.label,
        "architecture": scenario.architecture, "ely_tech": scenario.ely_tech,
        "h2_colour": scenario.h2_colour, "strategy": scenario.strategy,
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
        "perfect_foresight": True,
        "solve_seconds": time.time() - t0,
        "config_hash": h, "cached": False,
        "note": scenario.note,
    }
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    return summary


def _worker(args):
    scenario, kw = args
    try:
        return run_one(scenario, **kw)
    except Exception as exc:
        return {"key": scenario.key, "n": scenario.n, "label": scenario.label,
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc()}


def run_matrix(scenarios=None, *, site=sites.DEFAULT_PRESET, start="2025-01-01",
               end="2025-12-29", size_mw_it=7.31, pue=1.0,
               resample_hours=1.0, points=12, cost_case="central",
               horizon_years=25.0, unserved_fraction=0.0,
               gwp_target_kg_per_year=None,
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
              out_root=out_root, save_dispatch=save_dispatch, refresh=refresh)

    results, t0 = [], time.time()
    if workers == 1:
        for s in scenarios:
            results.append(_worker((s, kw)))
            _report(results[-1], len(results), len(scenarios), progress)
    else:
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
                "ely": (s["ely_tech"] or "-").split()[0],
                "h2_colour": s["h2_colour"] or "-",
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
    return [json.loads(p.read_text()) for p in sorted(Path(out_root).glob("*/summary.json"))]
