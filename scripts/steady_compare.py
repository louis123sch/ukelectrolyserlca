#!/usr/bin/env python
"""The steady hydrogen contract against just in time, site by site (18 Nov 2026).

Reads the 26-site ``present`` set (bought hydrogen just in time) and the ``steady`` set (one rate,
the same every hour, into the tank) from ``scripts/uk_sites.py`` and puts them side by side, so the
user can decide which belongs in the central case. The numbers the decision rests on, at each site
and grid level:

    hydrogen used        at any frontier point (the fuel cell serving 1 % of supply)
    reach                the highest-carbon point at which hydrogen is still used, g/kWh
    share at min_gwp     the fuel cell's share of supply at the lowest-carbon point
    bought, made         tonnes a year at the lowest-carbon point
    tank                 tonnes, 405 kg vessels (h2_capex.TANK_VESSEL_KG) and footprint
                         (h2_capex.TANK_FOOTPRINT_M2_PER_KWH_HHV), since land has no limit
    cost at min_gwp      GBP/MWh

    python scripts/steady_compare.py

Writes optimisation_outputs/uk_sites_2025_present_steady/compare.csv and compare.md.
Run ``python scripts/uk_sites.py --set steady --summary`` first.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimisation import h2_capex  # noqa: E402

OUTS = ROOT / "optimisation_outputs"
JIT, STEADY = OUTS / "uk_sites_2025_present", OUTS / "uk_sites_2025_present_steady"
KWH_PER_KG = 39.41


def _side(folder: Path, tag: str) -> pd.DataFrame:
    s = pd.read_csv(folder / "summary.csv")
    lim = pd.read_csv(folder / "hydrogen_limits.csv").set_index(["site", "level"])
    lo = s.loc[s.groupby(["site", "level"]).gwp_g_per_kWh.idxmin()].set_index(["site", "level"])
    out = pd.DataFrame({
        "place": lo.place,
        "h2_points": lim.h2_points,
        "reach_g_per_kWh": lim.h2_up_to_g_per_kWh,
        "share_at_min_gwp": lim.h2_share_at_min_gwp,
        "min_gwp_g_per_kWh": lo.gwp_g_per_kWh,
        "min_gwp_cost_GBP_per_MWh": lo.cost_GBP_per_MWh,
        "bought_t": lo.h2_bought_t_per_year,
        "made_t": lo.h2_made_t_per_year,
        "ely_MW": lo.cap_ely,
        "tank_t": lo.cap_tank / 1000.0,
    })
    out["steady_t_per_day"] = out.bought_t / 365.0
    out["tank_vessels"] = (lo.cap_tank / h2_capex.TANK_VESSEL_KG).round()
    out["tank_km2"] = lo.cap_tank * h2_capex.TANK_FOOTPRINT_M2_PER_KWH_HHV * KWH_PER_KG / 1e6
    return out.add_prefix(f"{tag}:").rename(columns={f"{tag}:place": "place"})


def compare() -> pd.DataFrame:
    a, b = _side(JIT, "jit"), _side(STEADY, "steady")
    df = a.join(b.drop(columns="place"), how="inner").reset_index()
    return df


def headline(df: pd.DataFrame) -> list[str]:
    n = len(df)
    used_jit = (df["jit:h2_points"] > 0).sum()
    used_st = (df["steady:h2_points"] > 0).sum()
    lost = ((df["jit:h2_points"] > 0) & (df["steady:h2_points"] == 0)).sum()
    halved_share = (df["steady:share_at_min_gwp"] < 0.5 * df["jit:share_at_min_gwp"]).sum()
    lines = [
        f"# Steady hydrogen contract against just in time, {n} site-levels", "",
        f"- Hydrogen used at some point: {used_jit} just in time, {used_st} steady; lost at {lost} of {used_jit}.",
        f"- Share at the lowest-carbon point halved or worse at {halved_share} of {n}.",
    ]
    for lev, g in df.groupby("level"):
        med = g.median(numeric_only=True)
        lines.append(
            f"- {lev}: reach {med['jit:reach_g_per_kWh']:.0f} -> {med['steady:reach_g_per_kWh']:.0f} g/kWh; "
            f"share at min_gwp {med['jit:share_at_min_gwp']:.2f} -> {med['steady:share_at_min_gwp']:.2f}; "
            f"bought {med['jit:bought_t']:.0f} -> {med['steady:bought_t']:.0f} t/yr; "
            f"made {med['jit:made_t']:.0f} -> {med['steady:made_t']:.0f} t/yr; "
            f"tank {med['jit:tank_t']:.0f} -> {med['steady:tank_t']:.0f} t "
            f"({med['steady:tank_vessels']:.0f} vessels, {med['steady:tank_km2']:.2f} km2); "
            f"lowest-carbon cost {med['jit:min_gwp_cost_GBP_per_MWh']:.0f} -> "
            f"{med['steady:min_gwp_cost_GBP_per_MWh']:.0f} GBP/MWh (medians)")
    return lines


def main():
    df = compare()
    df.to_csv(STEADY / "compare.csv", index=False)
    lines = headline(df)
    (STEADY / "compare.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
