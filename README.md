# UK Data Centre Optimiser

Cost and carbon of powering a UK data centre from the grid, wind, solar,
batteries and hydrogen (electrolyser → tank → fuel cell, or bought H2), sized
jointly by a linear program against half-hourly regional grid carbon (Carbon
Intensity API), wholesale prices (Elexon) and weather (Renewables.ninja), with
embodied carbon from a Brightway/ecoinvent foreground model.

This branch is the data-centre study on its own. The electrolyser-LCA work it
grew out of — the Setup LCA and Size Optimiser pages, the wind/grid electrolyser
notebooks (`1.dashboard_lca*`, `3.custom_grid`, `4.*`) and their outputs — is
still on `main`.

## Streamlit app

- **Home** — Brightway project status, and which regional grid series are
  already on disk.
- **Data Centre Optimiser** — the whole study on one page.
  Size the data centre, place it on a GB coordinate — by clicking the map or
  by typing the latitude and longitude, which are the same input — tick the
  infrastructure worth investigating (grid, onshore/offshore wind, solar, battery,
  electrolyser, H2 tank, fuel cell, bought H2), say which answer you want —
  cheapest, lowest-carbon, cheapest that hits a carbon target, or the knee of
  the trade-off curve — and it returns the installed capacity of each ticked
  asset that delivers it. The study's 21 named configurations load into the
  tick-boxes as presets. Pressing **Optimise** launches the solve as a
  detached process (`optimisation/dc_job.py`), so leaving the page,
  refreshing, closing the tab or restarting Streamlit does not lose it —
  come back and the page finds the run again, in progress or finished.
  Section 5 also charts the dispatch behind each answer. Section 6 carries the
  coefficients the answer runs on — the GB grid baseline, wind/solar/offshore
  costs and embodied carbon, hydrogen prices by colour, and battery storage.
  Every table is produced by a module in `optimisation/`, so the page never
  holds a second copy of the science. The page reloads those modules on each
  rerun, so edits show up without restarting the app.

### Setup

Requires the `brightway` conda environment (bw2data/bw2io/bw2calc, streamlit,
pandas, jupyter, scipy, an LP solver).

Create a `.env` file (gitignored) with a Renewables.ninja API token, used by
`optimisation/profiles.py` to fetch wind and solar capacity factors:

```
RENEWABLES_NINJA_TOKEN=...
```

```bash
conda activate brightway
streamlit run Home.py
```

On a new machine, run `2.tech_lca_foreground.ipynb` once to build the
foreground databases (data centre facility, fuel cell, electrolysers, H2
storage, SMR/SMR-CCS/pyrolysis for bought hydrogen, UPV, transformers). The
first grid build will do it for you if it is missing.

## The data centre powering study

Two entry points, one engine. `pages/2_Data_Centre_Optimiser.py` for exploring
one combination at a time and `scripts/run_dc_scenarios.py` for the full
21-configuration matrix headless (`scripts/run_dc_thresholds.py` for the
threshold sweeps):

```bash
python scripts/run_dc_scenarios.py --lat 51.5074 --lon -0.1278 --workers 8
```

**A GB coordinate is the input.** The Carbon Intensity region and the TNUoS
demand zone are derived from it (postcodes.io → Carbon Intensity API, then a
fixed GSP-group correspondence), so the weather, the grid mix and the network
bill always move together — picking a location cannot change one without the
others. `optimisation/sites.PRESETS` holds shortcuts for common sites.

**Any window, anywhere, builds itself.** A run needs a half-hourly grid series
for its region *and its dates*; if one is not on disk, `sites.ensure_grid_series`
builds exactly that window before the first LP, the same way Renewables.ninja is
already fetched on demand for whatever dates are asked for. It is the slow part —
the GB fuel mix is scored against ecoinvent for every half-hour, a couple of
minutes per week of window — so it builds only what is genuinely missing, one
build at a time machine-wide, and puts `dashboard_config.py` back afterwards.
What it will never do is substitute another region's or another month's
intensities: `require_grid_region()` and the window check refuse that rather
than produce a confident wrong answer. Windows run from 2018-05-11, where the
Carbon Intensity API's regional data begins, to yesterday.

### How a grid build runs

`backend/runner.py` patches the region and window into `dashboard_config.py`
(the single config every notebook reads) and executes `1.build_grid.ipynb` via
`nbconvert`. That notebook only orchestrates: it `%run`s
`2.tech_lca_foreground.ipynb` if the foreground is missing,
`3.1.custom_grid_carbon_intensity_api.ipynb` for the grid series, and
`5.prices.ipynb` when prices for the window are asked for. They share one kernel
because `5.prices` reads the timeslices `3.1` leaves behind. Results land in
`custom_grid_lca_outputs/` and `price_outputs/`; raw API responses are cached in
`carbon_intensity_api_cache/` (gitignored, refetched on demand).

> **A correction this exposed.** `dashboard_config.WIND_LAT / WIND_LON` is a
> field near St Albans — Carbon Intensity region 10, TNUoS zone 9 — while every
> cached grid series is region 13, zone 12. The study previously paired London's
> grid intensity and London's £7.41/kW demand tariff with a Hertfordshire wind
> site. Carbon-wise the regions are similar; the network charge is not
> (£7.41/kW against £1.11/kW). Nothing warned about it because nothing connected
> the wind coordinate to the grid region.

### Results

21 configurations, 18 of them involving hydrogen, each solved as a linear
program that sizes nine assets *jointly* with ~8,700 hourly dispatch decisions.
Results land in `optimisation_outputs/dc_runs/`, which is **gitignored** —
they are regenerable, and a 21-scenario matrix is ~90 files. The results that
matter are tracked: `optimisation/VALIDATION.md` and the executed outputs in
`6.datacentre_optimiser.ipynb`, both generated from a real run. A fresh clone
has no `dc_runs/`; run the command above once (~15 min on 8 cores) and the
notebook and the Streamlit page will find it.

`optimisation/myopic.py` is the lower bound to the LP's upper one: the same
build dispatched by a fixed merit order that sees only the current step (the
rule from the old notebook 4.3, now on `main` only). Section 7 of notebook 6
runs both on the same build.

## `optimisation/`

Each coefficient module is standalone, runs from the project root, prints its
own cross-checks and writes CSVs to `optimisation_outputs/`.

| Module | Role |
| --- | --- |
| `dc_model.py` | the LP — builds and solves the joint sizing + dispatch problem |
| `dc_architectures.py` | the 21 named configurations |
| `dc_inputs.py` | assembles coefficients and series into model inputs |
| `dc_pareto.py` | cost/carbon frontier and the knee |
| `dc_runner.py` / `dc_job.py` | cached runs and scenario matrices / detached solves for the page |
| `thresholds.py` | how far a configuration is from a carbon threshold, knob by knob |
| `sites.py` / `gb_map.py` | coordinate → region, zone and grid series; building missing windows |
| `profiles.py` | wind, solar, grid intensity and price on one half-hourly index |
| `baseline_grid.py` | Baseline 1 — the data centre on the GB grid |
| `grid_connection.py` / `network_charges.py` / `transformers.py` | connection, TNUoS/BSUoS/DUoS, and transformer embodied carbon |
| `tech_costs.py` / `renewables.py` | wind and solar costs (DESNZ/Arup 2024) and embodied carbon per MW |
| `battery.py` | Li-ion LFP capex/opex and embodied carbon, power and energy terms |
| `electrolysers.py` / `fuel_cell.py` / `h2_storage.py` / `h2_capex.py` | the hydrogen chain's embodied carbon and costs |
| `h2_prices.py` | hydrogen purchase price by colour — grey, blue, turquoise, green |
| `coefficients.py` | writes `tech_lca_coefficients.csv`, the table the LP reads instead of Brightway |
| `validate.py` / `audit.py` / `check_region_alignment.py` | benchmarks (writes `VALIDATION.md`), internal-consistency and per-region checks |
| `myopic.py` | the no-foresight bound |

[SOURCES.md](optimisation/SOURCES.md) gives every input's provenance and a
grade (transcribed / derived / assumed);
[ASSUMPTIONS.md](optimisation/ASSUMPTIONS.md) records the scope decisions and
what each one costs you; [DATA_GAPS.md](optimisation/DATA_GAPS.md) tracks what
is still open. [TODO.md](TODO.md) is the worklist on top of them. `docs/` holds
the overview and commercial brief, the objective audit and the reviewer
response plan.

## Notebooks

| Notebook | Role |
| --- | --- |
| `1.build_grid.ipynb` | grid-build orchestrator — what the optimiser runs for a missing region/window |
| `2.tech_lca_foreground.ipynb` | builds the foreground databases |
| `3.1.custom_grid_carbon_intensity_api.ipynb` | half-hourly regional grid carbon from the Carbon Intensity API |
| `5.prices.ipynb` | Elexon wholesale prices and techno-economic cost inputs |
| `6.datacentre_optimiser.ipynb` | **results of the study** — Pareto fronts, installed mixes, carbon by source, a dispatch week, and the foresight bracket |

The numbering is kept from `main` so references in the docs still line up.
