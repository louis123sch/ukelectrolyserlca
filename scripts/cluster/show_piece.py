"""Print one run's frontier as CSV (cost, carbon and main sizes per point), to compare a
cluster answer with the laptop's for the same piece. Reads a dc_runner folder's pareto.parquet.

    python scripts/cluster/show_piece.py optimisation_outputs/uk_sites_2025_present/limited/13
"""
import sys
from pathlib import Path

import pandas as pd

COLS = ["point", "cost_GBP_per_year", "gwp_kgco2e_per_year", "cap_wind", "cap_solar", "cap_batt_p",
        "cap_batt_e", "cap_ely", "cap_tank", "cap_fc", "cap_ge", "cap_grid", "h2_bought_kg_per_year"]

for f in sorted(Path(sys.argv[1]).rglob("pareto.parquet")):
    p = pd.read_parquet(f)
    print(f"# {f}")
    print(p[[c for c in COLS if c in p.columns]].round(3).to_csv(index=False), end="")
