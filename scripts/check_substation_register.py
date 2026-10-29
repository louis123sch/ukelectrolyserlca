"""Check the substation register built by scripts/build_substation_register.py,
and report how far it gets and what its gaps cost.

    python scripts/check_substation_register.py

Checks: all 14 areas present; every location inside Great Britain; every
`how` and `kind` a known value; located network nodes at 33/132 kV at or above
the floors below (set from the 29 Oct 2026 build, so a source or matcher that
gets worse fails). Reports, per area, the fallback error: for each located
network node, the difference between its location price and its nearest other
located node's — what using the nearest located node costs when a site's own
node is not located. Exits 1 on any failed check.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimisation import duos_areas as D   # noqa: E402

REG = ROOT / "optimisation_outputs" / "substation_register"
# Share of network price nodes at 33 kV located, per area, as built on 29 Oct 2026
# (South Scotland, NGED Midlands' unnamed and UKPN's anonymised nodes are customers
# or carry no location price; see the summary's unlocated_with_price).
FLOOR_33KV = {1: 0.85, 2: 0.55, 3: 0.75, 6: 0.90, 7: 0.40, 8: 0.90, 9: 0.95, 10: 0.95, 11: 0.55, 12: 0.65}
FLOOR_GROUP = {4: 0.85, 5: 0.95}


def fallback_error(nodes: pd.DataFrame) -> pd.DataFrame:
    n = nodes[(nodes.kind == "network") & nodes.lat.notna()
              & (nodes.voltage_kv.isin([33.0, 132.0]) | nodes.voltage_kv.isna())].copy()
    n["price"] = n.local_GBP_per_kVA + n.remote_GBP_per_kVA
    rows = []
    for r, d in n.groupby("region"):
        d = d.drop_duplicates(subset=["lat", "lon", "price"])
        if len(d) < 5:
            continue
        xy = np.c_[d.lat, d.lon * 0.6]
        dist, idx = cKDTree(xy).query(xy, k=2)
        err = np.abs(d.price.to_numpy() - d.price.to_numpy()[idx[:, 1]])
        charge = D.EHV_BANDS[int(r)][4].capacity_p_per_kva_day[1] * 3.65
        rows.append({"region": int(r), "area": D.AREA_NAMES[int(r)], "nodes": len(d),
                     "median_error_GBP_per_kVA": round(float(np.median(err)), 2),
                     "p90_error_GBP_per_kVA": round(float(np.percentile(err, 90)), 2),
                     "median_error_vs_band4_capacity_charge": round(float(np.median(err) / charge), 3),
                     "median_neighbour_km": round(float(np.median(dist[:, 1]) * 111), 1)})
    return pd.DataFrame(rows)


def main() -> int:
    problems = []
    S = pd.read_csv(REG / "substations.csv", low_memory=False)
    N = pd.read_csv(REG / "price_nodes.csv", low_memory=False)
    if set(N.region.dropna().astype(int)) != set(D.FILES):
        problems.append(f"price nodes cover regions {sorted(set(N.region.dropna().astype(int)))}, not all 14")
    for name, t in (("substations", S), ("price nodes", N)):
        ok = t.dropna(subset=["lat", "lon"])
        bad = ok[~(ok.lat.between(49.8, 61.0) & ok.lon.between(-8.7, 2.0))]
        if len(bad):
            problems.append(f"{len(bad)} {name} outside Great Britain, e.g. {bad.head(3)[['name' if 'name' in t else 'node_id', 'lat', 'lon']].values.tolist()}")
    if not set(N.how.dropna()) <= {"name", "place", "group", "code", "none"}:
        problems.append(f"unknown how values {set(N.how.dropna())}")
    if not set(N.kind.dropna()) <= {"network", "customer"}:
        problems.append(f"unknown kind values {set(N.kind.dropna())}")
    net = N[N.kind == "network"]
    for r, floor in FLOOR_33KV.items():
        d = net[(net.region == r) & (net.voltage_kv == 33.0)]
        share = d.lat.notna().mean() if len(d) else 0.0
        if share < floor:
            problems.append(f"region {r} {D.AREA_NAMES[r]}: 33 kV located {share:.0%} < floor {floor:.0%}")
    for r, floor in FLOOR_GROUP.items():
        d = net[(net.region == r)]
        share = d.lat.notna().mean() if len(d) else 0.0
        if share < floor:
            problems.append(f"region {r} {D.AREA_NAMES[r]}: located {share:.0%} < floor {floor:.0%}")
    fe = fallback_error(N)
    fe.to_csv(REG / "fallback_error.csv", index=False)
    print(fe.to_string(index=False))
    print()
    for p in problems:
        print("  PROBLEM", p)
    print(f"{len(S):,} substations, {len(N):,} price nodes; {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
