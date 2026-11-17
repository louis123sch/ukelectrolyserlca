#!/bin/bash
# The 26-site study's finished pieces so far, one line per site and grid level: cheapest and
# lowest-carbon results, where hydrogen stops being used, and how big the gas engines get.
# Rebuilds summary.csv and hydrogen_limits.csv from whatever has finished (light: reads files).
#   bash ~/ukdclca/scripts/cluster/sites_so_far.sh
cd "$HOME/ukdclca" || exit 1
eval "$("$HOME/miniforge3/bin/conda" shell.bash hook)"
conda activate ukdclca
export DC_BW_PROJECT=hydrogen-smr-sources
python scripts/uk_sites.py --set present --summary > /dev/null
python - <<'PY'
import pandas as pd
d = "optimisation_outputs/uk_sites_2025_present/"
h = pd.read_csv(d + "hydrogen_limits.csv")
s = pd.read_csv(d + "summary.csv")
ge = s.groupby(["site", "level"]).cap_ge.max().rename("max_gas_engine_MW")
fc = s.groupby(["site", "level"]).cap_fc.max().rename("max_fuel_cell_MW")
h = h.join(ge, on=["site", "level"]).join(fc, on=["site", "level"])
cols = ["site", "place", "level", "min_cost_GBP_per_MWh", "min_cost_g_per_kWh", "min_gwp_GBP_per_MWh" if "min_gwp_GBP_per_MWh" in h else "min_gwp_cost_GBP_per_MWh",
        "min_gwp_g_per_kWh", "h2_up_to_g_per_kWh", "h2_points", "points", "max_fuel_cell_MW", "max_gas_engine_MW"]
pd.set_option("display.width", 250)
print(h[cols].sort_values(["level", "site"]).round(1).to_string(index=False))
PY
