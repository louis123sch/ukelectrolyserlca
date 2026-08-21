# UK Electrolyser LCA

Hydrogen electrolyser life-cycle assessment against the live UK grid (Carbon
Intensity API) and wind data (renewables.ninja), on top of a Brightway/
ecoinvent foreground model.

## Streamlit app

A multipage app wraps the notebooks in a UI:

- **Home** — Brightway project status and latest run results.
- **1 Add Foreground** — a paper-to-Brightway extractor, so a paper/datasheet
  can be turned into a reviewed foreground process without leaving the app.
  It defaults its Brightway project to this project's (`hydrogen-smr`), so
  anything it writes is immediately visible on page 2.
- **2 Setup LCA** — pick any foreground process (the six built-in
  electrolysis/H2 techs, or anything written by page 1), configure the
  background scenario (grid region, wind farm, running strategy, time
  period), and run it.
- **3 Optimisation Inputs** — the cost and carbon coefficients for the
  data-centre powering study: the GB grid baseline, wind/solar/offshore
  costs and embodied carbon, hydrogen prices by colour, and battery storage.
  Every table is produced by a module in `optimisation/`, so the page never
  holds a second copy of the science.
- **4 Size Optimiser** — fix the demand (electrolyser technology, rating,
  running strategy), the site and the date range, and find the cheapest wind /
  solar / battery build that still meets an emissions threshold — by default
  the UK Low Carbon Hydrogen Standard's 20 gCO2e/MJ LHV.

This repo is standalone: the paper extractor (`ai_lca/`, vendored from the
[ai-lca-starter](https://github.com/louis123sch/ai-lca-starter) project)
ships in this repo, not a sibling clone — nothing outside this directory is
required to run it.

### Setup

Requires the `brightway` conda environment (already has bw2data/bw2io/bw2calc,
streamlit, pandas, jupyter, openai, and the rest of `ai_lca`'s dependencies).

Create a `.env` file (gitignored) with a real `OPENAI_API_KEY` — needed by
the Add Foreground page and by `paper_reading_notebooks/1.paper_ingest_and_extract.ipynb` (the only
places that call the LLM):

```
OPENAI_API_KEY=sk-...
```

```bash
conda activate brightway
streamlit run Home.py
```

The model and reasoning level aren't configured via `.env` — they're fixed
in `ai_lca/llm.py` (`DEFAULT_MODEL`, `DEFAULT_REASONING_EFFORT`), a single
source of truth every extraction call reads, instead of each call site
falling back to its own environment-variable default.

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

A flow's amount can carry a triangular-distribution range (lower/mode/upper),
sourced two ways:

- **Add Foreground page** — the extraction prompt looks for a source-stated
  range for a flow (an asset-lifespan range, an explicit +/- tolerance, a
  min-max table column) and pre-fills `uncertainty_lower`/`uncertainty_upper`
  columns in the inventory review table, alongside `amount` as the mode. Edit
  or add ranges by hand there too.
- **Setup LCA page, section 3** — an optional, per-run Monte Carlo table for
  the *selected* foreground process's own non-electricity exchanges (default
  5 empty rows, add more freely). Pre-filled automatically when the process
  already has a stored range from Add Foreground.

Either path ends up calling `write_foreground_database()`, which sets a real
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

### Recreating and harmonizing a paper's own result

The Add Foreground page's full pipeline, in order:

1. **Interpret paper and extract foreground** — now also pulls the source's
   stated impact assessment method (`study_context.impact_assessment_method`,
   e.g. "IPCC 2021 GWP100") and any result(s) it reports for itself (most
   often its baseline scenario), shown as **Source's own reported result(s)**.
2. **Search Brightway candidates** — matches every flow to a real ecoinvent
   node, same as before (per-flow search/re-search, candidate selection).
3. **Run LCA (source's method)** — before anything is written, scores the
   reviewed-and-mapped foreground with a Brightway method matched from the
   extracted method text (`H.find_methods()` in `lca_helpers.py`, editable),
   using `run_dry_lca()` in `ai_lca/brightway_writer.py`: builds temporary
   activities in the built-in foreground database purely as scratch space,
   scores them, deletes them again — nothing persists. The recreated score
   sits right next to the source's own reported result for comparison.
   **Harmonization** — once you've sanity-checked the recreation, adjust the
   matched background processes for your own study (most commonly
   re-targeting the source's operational geography to yours): set a target
   location and re-search every mapped flow with it promoted first. Existing
   picks stay as the fallback; review/override individual flows in "Review
   Brightway mappings" above.
4. **Extract into your LCA setup** — the actual permanent write (was
   previously the last, unlabelled step) — immediately selectable on Setup
   LCA once done.

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

The Streamlit pages **3 Optimisation Inputs** and **4 Size Optimiser** are thin
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

## Paper reader notebooks (`paper_reading_notebooks/1.*`)

A notebook-native alternative to the Add Foreground Streamlit page, for
running the extraction yourself cell by cell instead of through a UI. These
live in their own [paper_reading_notebooks/](paper_reading_notebooks/)
subfolder, separate from the numbered LCA pipeline notebooks below — each
still opens and runs standalone (a bootstrap cell at the top locates the
project root and chdirs there, so `ai_lca_config`/`ai_lca` imports and every
relative path work exactly as before the move):

- **[paper_reading_notebooks/1.paper_ingest_and_extract.ipynb](paper_reading_notebooks/1.paper_ingest_and_extract.ipynb)** —
  loads the source document/text and runs the two-pass LLM extraction (the
  only notebook here that calls OpenAI). Prints the classified/locked process
  structure and extracted flows, with their `process_id`/`flow_id` values.
- **[paper_reading_notebooks/1.1.paper_process_review.ipynb](paper_reading_notebooks/1.1.paper_process_review.ipynb)** —
  applies `PROCESS_REVIEW` (include/rename/merge/re-parent).
- **[paper_reading_notebooks/1.2.paper_inventory_review.ipynb](paper_reading_notebooks/1.2.paper_inventory_review.ipynb)** —
  applies `INVENTORY_REVIEW` (include/amount/unit/direction/notes per flow).
- **[paper_reading_notebooks/1.3.paper_brightway_matching.ipynb](paper_reading_notebooks/1.3.paper_brightway_matching.ipynb)** —
  searches Brightway for each flow and picks a candidate via
  `SEARCH_CANDIDATE_INDEX`, mirroring `GRID_CANDIDATE_INDEX`'s pattern; prints
  every candidate list so a bad auto-match (e.g. full-text search returning an
  unrelated activity) is visible before it reaches the writer.
- **[paper_reading_notebooks/1.4.paper_write_foreground.ipynb](paper_reading_notebooks/1.4.paper_write_foreground.ipynb)** —
  validates the write plan and, only once `CONFIRM_WRITE_FOREGROUND = True`,
  writes `NEW_FOREGROUND_DB_NAME` — then that database is immediately
  selectable from `1.3.paper_brightway_matching`-review-tested foreground
  processes, either via `H.list_process_activities(...)` in a notebook or the
  Setup LCA page's foreground picker.

All settings — source material, `RUN_LABEL`, the three review-override dicts
above, and the write confirmation gate — live in
[ai_lca_config.py](ai_lca_config.py), following the exact same "edit once,
save, re-run the notebook" contract as `dashboard_config.py`. Each notebook
persists its output under `ai_lca_outputs/<RUN_LABEL>/` (gitignored) so the
next notebook — or a later re-run — can pick up where the last one left off
without repeating the OpenAI call.

Both interfaces call the same vendored `ai_lca` library (`./ai_lca`, including
a `notebook_helpers` module written for this notebook workflow), so review
edits behave identically regardless of which one you use.

## LCA pipeline notebooks (numbered `1`–`5` at the project root)

Renumbered after the paper-reader notebooks moved out to their own
subfolder, so the root-level sequence runs `1` through `5` with no gap:

| Notebook | Role |
| --- | --- |
| `1.dashboard_lca_adaptive.ipynb` | entry point — orchestrates and plots |
| `1.dashboard_lca.ipynb` | earlier, non-adaptive orchestration notebook |
| `2.tech_lca_foreground.ipynb` | builds the foreground database |
| `3.custom_grid.ipynb` / `3.1.custom_grid_carbon_intensity_api.ipynb` | grid LCA (CSV vs. live Carbon Intensity API) |
| `4.wind_power.ipynb` / `4.1.datacentre_wind_power.ipynb` | wind/grid electrolyser and data-centre LCA |
| `5.prices.ipynb` | electricity prices and techno-economic cost inputs |

`dashboard_config.GRID_DATA_SOURCE` accepts the new `'3'`/`'3.1'` shorthand
(the old `'4'`/`'4.1'` values from before the renumbering still work too).
`a.dashboard_lca.ipynb` is an untracked-by-number, pre-existing snapshot of
an earlier `dashboard_lca` revision kept as a manual backup — it wasn't part
of the renumbering.
