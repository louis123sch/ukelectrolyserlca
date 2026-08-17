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

This repo is standalone: the paper extractor (`ai_lca/`, vendored from the
[ai-lca-starter](https://github.com/louis123sch/ai-lca-starter) project)
ships in this repo, not a sibling clone — nothing outside this directory is
required to run it.

### Setup

Requires the `brightway` conda environment (already has bw2data/bw2io/bw2calc,
streamlit, pandas, jupyter, openai, and the rest of `ai_lca`'s dependencies).

Copy `.env.example` to `.env` and fill in a real `OPENAI_API_KEY` — needed by
the Add Foreground page and by `1.paper_ingest_and_extract.ipynb` (the only
places that call the LLM).

```bash
cp .env.example .env   # then edit .env with your OpenAI key
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
executes `2.dashboard_lca_adaptive.ipynb` via `jupyter nbconvert`, the same
notebook the manual workflow uses. This keeps all of the actual LCA science —
the Carbon Intensity API client, wind dispatch logic, Brightway calls — in
the tested notebooks and `lca_helpers.py`; the Streamlit layer only edits
config text, runs the subprocess, and displays the resulting CSVs.

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

## Paper reader notebooks (`1.*`)

A notebook-native alternative to the Add Foreground Streamlit page, for
running the extraction yourself cell by cell instead of through a UI:

- **[1.paper_ingest_and_extract.ipynb](1.paper_ingest_and_extract.ipynb)** —
  loads the source document/text and runs the two-pass LLM extraction (the
  only notebook here that calls OpenAI). Prints the classified/locked process
  structure and extracted flows, with their `process_id`/`flow_id` values.
- **[1.1.paper_process_review.ipynb](1.1.paper_process_review.ipynb)** —
  applies `PROCESS_REVIEW` (include/rename/merge/re-parent).
- **[1.2.paper_inventory_review.ipynb](1.2.paper_inventory_review.ipynb)** —
  applies `INVENTORY_REVIEW` (include/amount/unit/direction/notes per flow).
- **[1.3.paper_brightway_matching.ipynb](1.3.paper_brightway_matching.ipynb)** —
  searches Brightway for each flow and picks a candidate via
  `SEARCH_CANDIDATE_INDEX`, mirroring `GRID_CANDIDATE_INDEX`'s pattern; prints
  every candidate list so a bad auto-match (e.g. full-text search returning an
  unrelated activity) is visible before it reaches the writer.
- **[1.4.paper_write_foreground.ipynb](1.4.paper_write_foreground.ipynb)** —
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
