# Streamlining plan — Data Centre Optimiser only

12 Oct 2026. Branch `dc-optimiser` (worktree `Desktop/ukdclca-dc`), cut from
`main` at `9a04185` plus a snapshot of the uncommitted work that was sitting in
`Desktop/ukdclca`.

The goal: a repo where everything left is something the Data Centre Optimiser
(page, scripts, notebook 6, tests) actually runs on, and where the electrolyser
LCA work it grew out of lives only on `main`.

## How "relevant" was decided

Not by name. "Electrolyser" is part of the DC study: surplus renewables →
electrolyser → tank → fuel cell is one of the configurations it sizes. So the
test was **reachability**:

1. Static import graph from `pages/2_Data_Centre_Optimiser.py`,
   `scripts/run_dc_*.py`, `6.datacentre_optimiser.ipynb` and `tests/`.
2. Every file path those modules read at runtime (CSV globs, caches, the
   notebook the grid build executes).
3. What the grid-build notebook chain `%run`s in turn.

## Audit

### Directly on the DC path — kept

| What | Why it is needed |
| --- | --- |
| `pages/2_Data_Centre_Optimiser.py`, `Home.py` | the app |
| 22 `optimisation/*.py` modules the page imports | the model, its inputs, sites, jobs, thresholds |
| `optimisation/{coefficients,validate,audit,check_region_alignment,myopic}.py` | not imported by the page, but DC-only: build `tech_lca_coefficients.csv`, write `VALIDATION.md`, consistency checks, and the no-foresight bound notebook 6 §7 uses |
| `scripts/run_dc_scenarios.py`, `run_dc_thresholds.py` | headless matrix / threshold runs |
| `tests/` (all 8 files) | all test DC modules |
| `backend/runner.py` | executes the grid-build notebook — `sites.build_grid_series` depends on it |
| `lca_helpers.py`, `dashboard_config.py` | used by DC modules *and* by the notebooks a grid build runs |
| `2.tech_lca_foreground.ipynb` | builds every foreground DB the DC reads: DC facility, PEM fuel cell, AE/PEM/SOEC, H2 tank, SMR/SMR-CCS/MP-E (bought-H2 colours), UPV, transformers |
| `3.1.custom_grid_carbon_intensity_api.ipynb` | produces the half-hourly regional `custom_electricity_score` the LP's grid carbon comes from |
| `5.prices.ipynb` | Elexon prices + `electrolyser_costs_clean.csv` (read by `h2_capex.py`) |
| `6.datacentre_optimiser.ipynb` | the study's results |
| `custom_grid_lca_outputs/custom_grid_lca_carbon_api_*` | grid series per region/window |
| `price_outputs/`, `optimisation_outputs/`, `optimisation/data/` | inputs and caches the modules read |
| `docs/` | overview, brief, objective audit, review plan |

### Not on the DC path — cut on the branch

| What | Size | What it was |
| --- | --- | --- |
| `pages/1_Setup_LCA.py` | 433 lines | electrolyser LCA run UI |
| `pages/3_Size_Optimiser.py` + `optimisation/sizing.py` | 740 lines | wind/solar/battery sizing for a fixed electrolyser |
| `1.dashboard_lca.ipynb`, `a.dashboard_lca.ipynb` | 4.1 MB | old orchestration/plotting, and a backup of it |
| `1.dashboard_lca_adaptive.ipynb` | 2.6 MB | **replaced** by `1.build_grid.ipynb` (see below) |
| `3.custom_grid.ipynb` + `df_fuel_ckan.csv` | 59 MB | CSV-sourced national grid; the DC only uses the Carbon Intensity API route |
| `4.wind_power.ipynb` | 1 MB | wind/grid electrolyser LCA |
| `4.1`, `4.2`, `4.3` DC notebooks | 0.4 MB | DC prototypes the LP superseded; 4.3's merit order already lives on in `myopic.py` |
| `blended_wind_grid_lca_outputs/`, `hybrid_wind_grid_lca_outputs/`, `datacentre_hydrogen_outputs/` | 30 MB | outputs of the above |
| `custom_grid_lca_outputs/custom_grid_lca_{cheap,exact}_*` | 4.5 MB | CSV-route grid outputs |
| `carbon_intensity_api_cache/` | 118 MB | **untracked, not deleted** — raw API responses, refetched on demand; now gitignored and kept on disk |
| `.DS_Store` | | |

## A finding that matters on `main` too

Every grid build the optimiser started was running the **electrolyser wind/grid
LCA as well**. `sites.build_grid_series` executes `1.dashboard_lca_adaptive.ipynb`,
whose `RUN_WIND_NOTEBOOK_FROM_DASHBOARD` defaults to `True` and is not in the
optimiser's override list — so each build also ran `4.wind_power.ipynb` (a
Renewables.ninja fetch plus a per-slice electrolyser LCA) and then every
plotting cell, none of which the optimiser reads. On `main`, adding
`"RUN_WIND_NOTEBOOK_FROM_DASHBOARD": False` to the overrides in
`sites.build_grid_series` is a one-line fix.

## Phase 1 — done on the branch

1. Snapshot commit of the uncommitted DC work from the main checkout.
2. `1.build_grid.ipynb`: a three-cell orchestrator that `%run`s 2 (only if the
   foreground is missing), 3.1, and 5 (only if prices are asked for). Same
   shared-kernel contract as before, no wind notebook, no plots.
   `backend/runner.RUNNER_NOTEBOOK` points at it.
3. Deleted everything in the "cut" table; `carbon_intensity_api_cache/`
   untracked and gitignored.
4. `Home.py` rewritten for the DC: Brightway status, which regions have grid
   series on disk, a link to the optimiser.
5. README rewritten for the DC study; docstrings that sent readers to the
   Setup LCA page now point at the grid-build notebook.
6. `tests/test_build_lock.py`: the cp1252 regression test read the runner
   notebook's own bytes, which the slim notebook no longer contains. It now
   builds its own fixture.

Verified: test suite 154 passed / 3 skipped (main: 153 / 3, and the extra one
is that test split in two); Home and the optimiser page render with no errors,
Brightway baseline included; a real one-day grid build ran end to end through
`1.build_grid.ipynb`.

## Phase 2 — proposed, not done

In rough order of payoff:

1. **Stop scoring electrolysers in the grid build.** 3.1 batch-runs an LCA for
   every `SELECTED_LCA_TECHS` entry on every half-hour, and raises if none
   resolve. The DC reads only `custom_electricity_score`. Cutting the per-tech
   batch should make builds markedly faster. Needs care: the output file name
   and columns are what `profiles.py`/`sites.py` glob for.
2. **Replace the notebook-driven build with a module** (`optimisation/grid_build.py`).
   That removes the nbconvert subprocess, the in-place patching of
   `dashboard_config.py`, the kernelspec/PATH workaround, the console-window
   workaround and most of the build-lock rationale. 3.1's API client (≈23 k
   characters in one cell) and 5's Elexon fetch would move into Python. Biggest
   change in this list; do it after 1.
3. **Split `dashboard_config.py`** (854 lines). DC modules read ~50 names from
   it — DC/FC/tank/transformer/PV settings, `SYS_DC_DEMAND_MW`,
   `WIND_LAT/LON`. The wind-electrolyser, DC-wind (4.1), Monte Carlo and
   CSV-grid sections are dead on this branch. Note `WIND_LAT/LON` and
   `SYS_DC_DEMAND_MW` are still read by DC code despite their names.
4. **Trim `lca_helpers.py`.** 13 of its 49 functions (~350 lines) are now
   referenced by nothing on the branch: the wind/split/replacement electricity
   LCAs, Monte Carlo, the template/biosphere pickers. More falls away after
   item 2.
5. **Prune `TODO.md`, `DATA_GAPS.md`, `ASSUMPTIONS.md`** of items that only
   concerned the cut pages, and tidy docstrings that still compare to
   `sizing.py` / notebook 4.3 (they are history, not wrong).
6. **`price_outputs/`**: the `representative_576days` files and short 2023/2024
   windows came from Setup LCA runs. `profiles.py` refuses representative days
   anyway; worth confirming nothing globs them before deleting.

## Phase 3 — the split

- Decide whether `dc-optimiser` becomes `main` (and the current `main` is kept
  as an `archive/electrolyser-lca` branch), or becomes its own repository.
  The cut files are still in history either way; a separate repo with
  `git filter-repo` is the only route to a small clone (`df_fuel_ckan.csv`
  and the API cache are ~180 MB of history).
- Rename the Brightway project (`hydrogen-smr`) and the remote
  (`ukelectrolyserlca`) if the names now mislead.
