# UK Electrolyser LCA

Hydrogen electrolyser life-cycle assessment against the live UK grid (Carbon
Intensity API) and wind data (renewables.ninja), on top of a Brightway/
ecoinvent foreground model.

## Streamlit app

A multipage app wraps the notebooks in a UI:

- **Home** — Brightway project status and latest run results.
- **1 Add Foreground** — embeds the sibling [ai-lca-starter](../ai-lca-starter)
  paper-to-Brightway extractor, so a paper/datasheet can be turned into a
  reviewed foreground process without leaving the app. It defaults the
  extractor's Brightway project to this project's (`hydrogen-smr`), so
  anything it writes is immediately visible on page 2.
- **2 Setup LCA** — pick any foreground process (the six built-in
  electrolysis/H2 techs, or anything written by page 1), configure the
  background scenario (grid region, wind farm, running strategy, time
  period), and run it.

### Setup

Requires the `brightway` conda environment (already has bw2data/bw2io/bw2calc,
streamlit, pandas, jupyter, and the ai-lca-starter dependencies).

`ai-lca-starter` must be cloned as a sibling directory (`../ai-lca-starter`
relative to this repo), with its own `.env` containing `OPENAI_API_KEY` —
see that repo's README. Set `AI_LCA_STARTER_DIR` to override the location.

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
