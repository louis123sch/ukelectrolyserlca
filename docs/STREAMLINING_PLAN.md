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

## Phase 2 — done (12 Oct 2026)

Items 1–4 of the original list, done together because they are one change:

- **Grid builds are a Python module.** `optimisation/grid_build.py` takes a
  region and window as arguments, fetches the Carbon Intensity API mix and
  Elexon prices, and scores the mix against ecoinvent with the same closed-form
  method notebook 3.1 used. It no longer scores the hydrogen technologies per
  half-hour (the LP never read them). `1.build_grid.ipynb`, `3.1` and `5.prices`
  are deleted; nothing patches a config file at run time any more.
  Same file names and columns, minus the per-technology and `wind_lat/lon`
  columns. Checked: re-building region 14's June week matches the notebook's
  file to 7e-7 relative on every half-hour and exactly on price; a week now
  builds in ~10 s instead of ~2 min.
- **`dashboard_config.py` → `dc_config.py`** (854 → ~560 lines): only what the
  modules and notebook 2 read. Dropped: the electrolyser/wind/4.x/price-notebook
  sections, the run-orchestration flags, `WIND_LAT/LON` and `SYS_*` (only
  docstrings still mentioned them). `GRID_CANDIDATE_INDEX` moved in from 3.1.
- **`backend/runner.py`** only runs a named notebook (notebook 2, once per
  machine); config patching, plot extraction and output snapshots are gone.
- **`lca_helpers.py`** 1,546 → ~480 lines: the electrolyser wind/grid LCAs,
  custom-activity builders, Monte Carlo, CSV-route loaders and template pickers
  had no remaining caller. The Renewables.ninja token now comes only from the
  argument or `.env`/environment (no interactive prompt, no config field).
- `price_outputs/electrolyser_costs_clean.csv` and `static_cost_assumptions.csv`
  were written by notebook 5 and are now frozen inputs. If NESO's electrolyser
  table needs refreshing, the fetch code is on `archive/electrolyser-lca`.

Not changed, deliberately: the grid series is still London local time while
prices and weather are UTC (TODO.md). Fixing it changes every cached file.

### Still open

1. **Prune `TODO.md`, `DATA_GAPS.md`, `ASSUMPTIONS.md`** of items that only
   concerned the cut pages, and tidy docstrings that still compare to
   `sizing.py` / notebook 4.3 (they are history, not wrong).
2. **`price_outputs/`**: the `representative_576days` files and short 2023/2024
   windows came from Setup LCA runs. `profiles.py` refuses representative days
   anyway; worth confirming nothing globs them before deleting.
3. **The BST clock fix**, now a one-line change in `grid_build.fetch_mix` plus
   a rebuild of the cached series.

## Phase 3 — the split

- Done: `dc-optimiser` became `main`; the previous `main` is kept as the
  `archive/electrolyser-lca` branch. A separate repository is still an option.
  The cut files are still in history either way; a separate repo with
  `git filter-repo` is the only route to a small clone (`df_fuel_ckan.csv`
  and the API cache are ~180 MB of history).
- Rename the Brightway project (`hydrogen-smr`) and the remote
  (`ukelectrolyserlca`) if the names now mislead.
