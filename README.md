# UK Electrolyser LCA

Hydrogen electrolyser life-cycle assessment against the live UK grid (Carbon
Intensity API) and wind data (renewables.ninja), on top of a Brightway/
ecoinvent foreground model.

## Streamlit app

A multipage app wraps the notebooks in a UI:

- **Home** — Brightway project status and latest run results.
- **1 Setup LCA** — pick any foreground process (the six built-in
  electrolysis/H2 techs, or anything written by page 1), configure the
  background scenario (grid region, wind farm, running strategy, time
  period), and run it.
- **2 Electrolyser Optimiser** — fix the demand (electrolyser technology,
  rating, running strategy), the site and the date range, and find the
  cheapest wind / solar / battery build that still meets an emissions
  threshold — by default the UK Low Carbon Hydrogen Standard's 20 gCO2e/MJ
  LHV. Its cost and carbon inputs (generation costs, embodied carbon,
  battery storage) are shown on the page itself; pressing Run builds
  whatever data the run needs first, under one progress bar.
- **3 Data Centre Optimiser** — pick a size, a site, a window and which power
  options to compare; get the installed mix at minimum cost, minimum
  emissions, and the knee point between them. Its inputs (the GB grid
  baseline, hydrogen prices by colour, generation and battery coefficients)
  are shown on the page itself. Every table on both optimiser pages is
  produced by a module in `optimisation/`, so no page ever holds a second
  copy of the science.

### Setup

Requires the `brightway` conda environment (bw2data/bw2io/bw2calc, streamlit,
pandas, jupyter, scipy). The data-centre optimiser additionally needs an LP
solver — see `DC_OPTIMISER_PLAN.md`.

Create a `.env` file (gitignored) with a Renewables.ninja API token, used by
`optimisation/profiles.py` to fetch wind and solar capacity factors:

```
RENEWABLES_NINJA_TOKEN=...
```

```bash
conda activate brightway
streamlit run Home.py
```

### How "Run LCA" works

`dashboard_config.py` is the project's single source of truth — every
notebook reads it, and its own docstring says to "edit this file once, save
it, restart the kernel, then run." The Setup LCA page follows that same
contract: it patches the relevant variables in the on-disk
`dashboard_config.py` (backing up the previous version to
`_streamlit_runs/dashboard_config.before_last_run.py`, gitignored) and then
executes `1.dashboard_lca_adaptive.ipynb` via `jupyter nbconvert`, the same
notebook the manual workflow uses. This keeps all of the actual LCA science —
the Carbon Intensity API client, wind dispatch logic, Brightway calls — in
the tested notebooks and `lca_helpers.py`; the Streamlit layer only edits
config text, runs the subprocess, and displays the resulting CSVs and plots.

Because notebook 2's plotting cells run as part of that same execution, the
figures they produce are extracted from the executed notebook and saved to
`_streamlit_runs/plots/` (gitignored) — shown on the Setup LCA page right
after a run, and as a "latest run" section on Home so they're still visible
on a later visit without re-running anything.

Because it's a shared local config file, only run one LCA at a time.

### Foreground selection across databases

`lca_helpers.py` adds three additive helpers so the Setup LCA page isn't
limited to the six hardcoded techs in `H2_CODES`:

- `list_foreground_databases()` / `list_process_activities(db)` — enumerate
  every non-ecoinvent/biosphere database and its process activities.
- `resolve_tech_activity(label, tech_source_overrides)` — resolves a tech
  label to an activity, preferring an explicit `(database, code)` override
  over the built-in `H2_CODES`/`ELECTROLYSER_CODES` lookup.

`dashboard_config.TECH_SOURCE_OVERRIDES` (default `{}`, so existing notebook
runs are unaffected) carries these per-run overrides; notebooks `4.1` and `5`
resolve technologies through `H.resolve_tech_activity()` instead of a direct
`H2_CODES`/`FOREGROUND_DB` lookup. The electricity-exchange swap itself
(`is_any_electricity_exchange`, `run_lca_with_custom_elec`) was already
generic across any foreground activity — the overrides just let a label point
at one outside the default database.

### Uncertainty and Monte Carlo

A flow's amount can carry a triangular-distribution range (lower/mode/upper):

- **Setup LCA page, section 3** — an optional, per-run Monte Carlo table for
  the *selected* foreground process's own non-electricity exchanges (default
  5 empty rows, add more freely). Pre-filled automatically when the process
  already carries a stored range.

This calls `write_foreground_database()`, which sets a real
Brightway/stats_arrays triangular distribution (`uncertainty type = 5`) on
the matching exchange — the *canonical* place Brightway expects uncertainty,
so it works from any Brightway tooling, not just this app. Setup LCA's "Run
LCA" then runs `bc.LCA(..., use_distributions=True)` for N iterations
(`H.run_monte_carlo_non_electricity` in `lca_helpers.py`) and shows a
histogram + mean/P5/P50/P95/std next to the deterministic result.

Electricity exchanges are always excluded from Monte Carlo — the grid/wind
pipelines already model electricity's own real-world variability from live
data, so adding a second independent uncertainty source there would
double-count it. Each iteration re-solves the full ecoinvent LCI, so it's
slow (~3-4s/iteration on typical hardware) — the iteration slider defaults
low (50) with a live time estimate.

## Optimisation inputs (`optimisation/`)

Cost and carbon coefficients for a study comparing ways to power a data
centre. Each module is standalone, runs from the project root, prints its own
cross-checks and writes CSVs to `optimisation_outputs/`:

| Module | Produces |
| --- | --- |
| `baseline_grid.py` | Baseline 1 — the data centre on the GB grid, with its US-SERC electricity swapped for the half-hourly Carbon Intensity API mix |
| `tech_costs.py` | Onshore wind, offshore wind and solar PV costs — DESNZ/Arup 2024 |
| `renewables.py` | The same three technologies' embodied carbon **per MW installed**, decomposed out of ecoinvent's per-kWh activities |
| `h2_prices.py` | Hydrogen purchase price by colour — grey, blue, turquoise, green |
| `battery.py` | Li-ion LFP storage — capex/opex and embodied carbon, split into power and energy terms |
| `profiles.py` | Wind, solar, grid intensity and price on one half-hourly index for a site and period. Renewables.ninja fetches are disk-cached; sampled "representative day" files are refused, because a dispatch carrying battery state cannot use them |
| `sizing.py` | The optimiser — a chronological dispatch plus a search over wind, solar and battery sizes, minimising levelised cost subject to an emissions threshold |

Three companion documents carry the reasoning rather than the numbers:
[SOURCES.md](optimisation/SOURCES.md) gives every input's provenance and a
grade (transcribed / derived / assumed);
[ASSUMPTIONS.md](optimisation/ASSUMPTIONS.md) records the scope decisions and
what each one costs you; [DATA_GAPS.md](optimisation/DATA_GAPS.md) tracks what
is still open.

Each module carries self-checks that fail loudly rather than returning a
plausible wrong number — coefficients are re-read from Brightway and compared
against the values pinned in the module, scenario cases are checked for
monotonicity, the renewables decomposition is re-amortised back to ecoinvent's
own published per-kWh score, and `tech_costs` asserts its onshore wind rows
still match what `5.prices.ipynb` independently writes. Between them these have
caught several real errors, including a case-pairing bug inherited from the
DESNZ reports' own scenario convention.

The Streamlit pages **2 Electrolyser Optimiser** and **3 Data Centre Optimiser** are thin
views over these modules. They reload them on each rerun, so edits to
`optimisation/*.py` show up without restarting the app.

### Sizing runs

`sizing.py` fixes the demand and sizes the supply. The electrolyser's rating and
running strategy are yours to choose; wind MW, solar MWp and battery MW/MWh are
what the optimiser solves for. The battery starts full and carries state across
the whole period, which is why `profiles.py` insists on a continuous series.

Three running strategies are supported: `baseload` (flat at rated power, grid
fills the gaps), `renewables_only` (never import; shut down below minimum load)
and `grid_when_clean` (import only when grid intensity is below a threshold).

The emissions target is a **constraint, not a weighting** — the answer is the
cheapest build that complies, and when nothing in the search space complies the
result says so and names any bound the solver pressed against, rather than
quietly returning a non-compliant build.

## The data centre powering study

Two entry points, one engine. `pages/3_Data_Centre_Optimiser.py` for exploring
and `scripts/run_dc_scenarios.py` for the full matrix headless:

```bash
python scripts/run_dc_scenarios.py --lat 51.5074 --lon -0.1278 --workers 8
```

**A GB coordinate is the input.** The Carbon Intensity region and the TNUoS
demand zone are derived from it (postcodes.io → Carbon Intensity API, then a
fixed GSP-group correspondence), so the weather, the grid mix and the network
bill always move together — picking a location cannot change one without the
others. `optimisation/sites.PRESETS` holds shortcuts for common sites.

Only region 13 (London) has a cached half-hourly grid series. For anywhere else,
`sites.build_grid_series(<region>)` generates one via notebook 3.1 — slow, since
it scores the GB fuel mix against ecoinvent for every half-hour — and until then
`require_grid_region()` refuses to substitute another region's intensities
rather than producing a confident wrong answer.

> **A correction this exposed.** `dashboard_config.WIND_LAT / WIND_LON` is a
> field near St Albans — Carbon Intensity region 10, TNUoS zone 9 — while every
> cached grid series is region 13, zone 12. The study previously paired London's
> grid intensity and London's £7.41/kW demand tariff with a Hertfordshire wind
> site. Carbon-wise the regions are similar; the network charge is not
> (£7.41/kW against £1.11/kW). Nothing warned about it because nothing connected
> the wind coordinate to the grid region.

21 configurations, 18 of them involving hydrogen, each solved as a linear
program that sizes nine assets *jointly* with ~8,700 hourly dispatch decisions.
Results land in `optimisation_outputs/dc_runs/`, which is **gitignored** —
they are regenerable, and a 21-scenario matrix is ~90 files. The results that
matter are tracked: `optimisation/VALIDATION.md` and the executed outputs in
`6.datacentre_optimiser.ipynb`, both generated from a real run.

So a fresh clone has no `dc_runs/`. Run the command above once (~15 min on 8
cores) and the notebook and the Streamlit page will find it.

`optimisation/VALIDATION.md` carries the benchmarks (generated, not
transcribed), `SOURCES.md` the provenance of every number, and `DATA_GAPS.md`
what is still open — including the fuel cell and hydrogen vessel costs, which
have no UK source and are graded `assumed`.

### How this relates to notebook 4.3

`4.3.wind_h2_storage_system.ipynb` dispatches a **fixed** build by a merit
order that sees only the current step. The optimiser supersedes it for *sizing*
— a tank's value comes from filling in spring and draining in autumn, which a
myopic rule cannot anticipate, so it systematically mis-sizes the store. But
4.3 is not obsolete: its merit order is preserved in `optimisation/myopic.py`
as the **lower** bound on what a build achieves, against the LP's upper bound.
Section 7 of notebook 6 runs both on the same build.

The `SYS_*` settings in `dashboard_config.py` (50 MW wind, 25 MW electrolyser,
10 t tank) are 4.3's hand-chosen inputs. The optimiser derives those numbers
rather than reading them, so the two will disagree — that is the point, not a
bug.

## Notebooks (numbered `1`–`6` at the project root)

The root-level sequence runs `1` through `6` with no gap:

| Notebook | Role |
| --- | --- |
| `1.dashboard_lca_adaptive.ipynb` | entry point — orchestrates and plots |
| `1.dashboard_lca.ipynb` | earlier, non-adaptive orchestration notebook |
| `2.tech_lca_foreground.ipynb` | builds the foreground database |
| `3.custom_grid.ipynb` / `3.1.custom_grid_carbon_intensity_api.ipynb` | grid LCA (CSV vs. live Carbon Intensity API) |
| `4.wind_power.ipynb` / `4.1.datacentre_wind_power.ipynb` | wind/grid electrolyser and data-centre LCA |
| `5.prices.ipynb` | electricity prices and techno-economic cost inputs |
| `6.datacentre_optimiser.ipynb` | **results of the data-centre powering study** — Pareto fronts, installed mixes, carbon by source, a dispatch week, and the foresight bracket |

`dashboard_config.GRID_DATA_SOURCE` accepts the new `'3'`/`'3.1'` shorthand
(the old `'4'`/`'4.1'` values from before the renumbering still work too).
`a.dashboard_lca.ipynb` is a pre-existing snapshot of an earlier
`dashboard_lca` revision, kept as a manual backup.
