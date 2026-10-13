# Plan: one place per LCA

Regularise how the LCA inventories are held so that each one — grid, hydrogen,
data centre, fuel cell, tank, step-up transformers, utility PV — can be read
start to finish in one place, in the same shape, with nothing hidden in a
second file.

Written 13 Oct 2026 against `2.tech_lca_foreground.ipynb` (73 cells, ~2,800
lines), `dc_config.py` (576 lines) and `lca_helpers.py` (477 lines).

**Implemented 13 Oct 2026.** All nine steps below are done; §6 records what
the rebuild-and-compare found. The notebook is 20 cells, `dc_config.py` 60
lines, `lca_helpers.py` 270 lines, and `optimiser_lca/` holds the seven
inventories.

---

## 1. What is where today

### The notebook has three generations of code in it

| cells | what | shape |
|---|---|---|
| 3–42 | Hermesmann hydrogen: SMR, SMR-CCS, CCS, MP-E, AE/PEM/SOEC build + operation | uniform: `queries` → `candidate_index` → `pick_candidate` by **search rank** → `technosphere_exchanges` list of `(key, amount, unit, comment)` |
| 43–52 | Zhang data centre, Babatunde FC stack, FC operation | same pattern plus long markdown; FC operation resolves by exact name with guards, and its parameters live in `dc_config` (`FC_*`) while the exchange assembly lives here |
| 53–60 | H2 tank, wind step-up, solar step-up, UPV plant | each cell has its own ad-hoc resolver (`_matches = [a for a in ei if …]`, `_resolve_one`, `_one`), its own print layout, physics mixed in (real-gas law, amps at 690 V), bills read from `dc_config` or `optimisation/data/upv_smith_bill.json`, and placeholder `("__FG__", code)` keys |
| 62 | one 565-line write cell for six databases | activity names, reference products, locations and paragraph-long comments live **here**, far from the inventories; capital-good links (3.24e-7 unit/kg, 8.01 kg CO2 → CCS) are hard-coded here, not with the inventory; `SMR_CODE` is defined here, every other code upstream; `H2_CODES` re-declared, duplicating `lca_helpers.H2_CODES` |
| 63–66 | FC stack validation vs the paper; FC operation sanity check | legitimate, but not attached to the FC section |
| 67–72 | "Solar PV LCA — IEA PVPS 2024 basis" | **stale**: walks the old `iea_pvps_2023_mono_si` basis that `renewables.py` no longer defaults to (cell 59's own markdown says so). `python optimisation/renewables.py` already prints this comparison |

The pattern the start of the notebook has — queries, pick, inventory, database — is
the right *order*. What breaks it later is that the pattern is not a function,
so every new asset re-implemented it by hand, and the later ones put half of
their data in `dc_config.py`.

### `dc_config.py` is 70 % inventory data

| lines | content | is it config? |
|---|---|---|
| 26–38 | Brightway project, ecoinvent version, DB names, run flags | yes |
| 43–46 | DC operating life, reference PUE | yes |
| 63–97 | `GRID_SOURCES` (16 ecoinvent identities), loss factor | **grid LCA inventory** |
| 107–165 | fuel cell efficiency, lifetimes, BoP location, maintenance fraction, H2 source, derived per-kWh amounts | **FC operation inventory** — these numbers *are* exchange amounts |
| 177–205 | tank designs, steel process, real-gas constants | **tank inventory** |
| 235–277 | Leng transformer bill + process map, voltage chain | **wind step-up inventory** |
| 296–395 | IEA PVPS transformer bill, forming, energy, process map, `upv_tx_check()` | **solar step-up inventory** |
| 422–513 | Smith PV spec, scope, O&M, IEA mounting bill, `upv_pv_check()` | **UPV inventory** |
| 523–526 | PV tilt/azimuth/loss | profiles setting, not LCA |

### `lca_helpers.py` is four things

Brightway session (setup, handles, method); search/pick helpers; LCA scoring
(`run_lca_score`, `run_non_electricity_lca`); **grid composite weights and
the closed-form score** (`WIND_GROUP_WEIGHTS`, `IMPORT_GROUP_WEIGHTS`,
`TECH_SPECS`, `FUEL_COLS`, `custom_electricity_score_for_row`); the foreground
code registry (`H2_CODES`); and a Renewables.ninja HTTP client whose only
caller is `profiles.py`.

### So the grid LCA is in four files

`dc_config.GRID_SOURCES` + `MARKET_LOSS_*` → `lca_helpers` weights and
`custom_electricity_score_for_row` → `grid_build.source_table / score_mix` →
`h2_prices.GRID_DELIVERY_*` (a second, hard-coded view of the GB network with
its own Brightway check). That is the case the plan is built around.

### Smaller inconsistencies worth fixing on the way

- Foreground codes are string literals in seven modules (`fuel_cell.py`
  `"pemfc_op_1kwh_h2"`, `h2_storage.py` `"h2_tank_steel_1kg_capacity"`,
  `baseline_grid.DC_CODE`, `renewables` `capital_code`, `transformers.WIND_CODE`,
  `dc_inputs` and `electrolysers` `"hydrogen foreground"`).
- The ecoinvent database is named three ways: `find_database_name`,
  `cfg.ECOINVENT_DB if hasattr(...)`, and the literal `"ecoinvent-3.9.1-apos"`.
- Five hand-rolled exact-match resolvers (notebook ×3, `grid_connection`,
  `transformers`, `h2_prices`), beside `lca_helpers.get_exact_activities`
  which already does it properly.
- Search-rank picks (`candidate_index`) are fragile. `dc_config` records the
  precedent: `"GAS": 3` silently landed on the conventional plant, 12–21 % on
  every grid series. The Hermesmann cells still use that mechanism.
- `grid_connection.py`, `renewables.TECHNOLOGIES`, `battery.py` and
  `transformers.LEGACY_ACTIVITY` each score an ecoinvent activity directly —
  small inventories hidden inside coefficient modules.

---

## 2. What Brightway practice says

The official data model (docs.brightway.dev, "Inventory"): a process node is a
dict with `name`, `unit`, `location`, `code`, `database`, `reference product`
and `exchanges`; each exchange has `input` (a `(database, code)` key),
`amount` and `type` ∈ {`production`, `technosphere`, `biosphere`}; codes are
assigned by hand for user-built data. A foreground is written either by
`Database.write({(db, code): {...}})` — what the notebook does — or through
`bw2io`'s importer pipeline (`ExcelImporter`/`CSVImporter` →
`apply_strategies()` → `match_database(ecoinvent, fields=("name","location",
"unit","reference product"))` → `statistics()` → `write_database()`), which
links to the background by **exact field match**, never by search ranking.

Community convention (lca_algebraic handbook, brightway_recipes, optimex):
one Brightway project per study; background and foreground as separate
databases; model logic in an importable module or package; notebooks as thin
drivers that import it, show tables and run checks. Parameterised foregrounds
(fuel-cell efficiency, tank pressure) are the normal case and are handled by
computing the exchange amount from named parameters in code, which this repo
already does.

Nothing here says "inventory must be a spreadsheet". It says: declare the
inventory as data, link by exact identity, keep the notebook thin. Sources:
[Brightway inventory data model](https://docs.brightway.dev/en/latest/content/overview/inventory.html),
[bw2io on PyPI](https://pypi.org/project/bw2io/),
[lca_algebraic handbook](https://lca-algebraic.readthedocs.io/en/dev/notebooks/handbook.html),
[optimex Brightway setup](https://optimex.readthedocs.io/en/latest/content/brightway_setup/),
[brightway_recipes](https://github.com/benportner/brightway_recipes).

---

## 3. The target layout

### Answer to "queries in the ipynb, foreground in a .py?"

Partly. Keep *exploration* (search, look at candidates, decide) in a notebook,
but once an activity is chosen, pin its exact identity **next to the amounts
that use it**, in one Python module per technology. Do not leave a
`candidate_index` in the notebook that a `.py` depends on: that recreates the
split you dislike, and it means the notebook must run for the build to exist.
The thing you like about the start of the notebook — the order queries →
pick → inventory → database — survives as the fixed section order of every
module and of every notebook section.

### One package, `optimiser_lca/`, one module per LCA

```
optimiser_lca/
  __init__.py
  registry.py            every database name and activity code, in one table
  common.py              Inventory/Activity dataclasses, resolve(), show(), to_bw_dict()
  grid.py                GRID_SOURCES, loss factor, wind/import split weights,
                         TECH_SPECS/FUEL_COLS, score_mix (closed form)
  hydrogen.py            Hermesmann: SMR, SMR-CCS, CCS, MP-E, AE/PEM/SOEC build+op
  data_centre.py         Zhang 2025 facility
  fuel_cell.py           Babatunde stack + the per-kWh operation activity
  h2_tank.py             Gandiglio vessel, both designs
  stepup_transformers.py Leng wind + IEA PVPS solar
  upv.py                 Smith plant, IEA mounting, O&M (reads upv_smith_bill.json)
  build.py               python -m optimiser_lca.build  → writes every DB in order
  validate.py            FC stack vs paper tables, FC op sanity, DC vs paper
```

Every inventory module has the same four sections, in this order, so any of
them can be read top to bottom without opening another file:

1. **Source and scope** — module docstring: citation, functional unit,
   what is deliberately excluded and in which direction it biases. This is
   where the long markdown from cells 43/47/51/53/55/57/59 goes (the
   duplicate copies in `optimisation/transformers.py` etc. become one-line
   pointers).
2. **Parameters** — the named numbers that enter an exchange amount
   (`FC_ETA_NET_BOL`, `TANK_DESIGN`, `UPV_PV_ILR`, …) with their derived
   values and `check()` guards. Graded TRANSCRIBED / DERIVED / ASSUMED
   inline, as `dc_config` already does.
3. **Processes** — `{key: Process(query, pick, identity, why)}`: the search
   that found it, the exact identity that builds it, the reason. Biosphere
   flows likewise, with `(name, categories)` as the identity.
4. **Activities** — one `Activity(code, name, reference_product, unit,
   location, comment, technosphere=[(key, amount, unit, note), …],
   biosphere=[…])` per foreground activity, including links to other
   foreground activities by registry code.

`common.py` supplies four verbs: `show(inv)` (per process, the search
candidates with the chosen row marked and its `why`; per activity, a
DataFrame of key, amount, unit, ecoinvent name, location, note), `pin(inv)`
(fill any missing identity from its search pick and say what was pinned),
`resolve(inv)` (exact identity → Brightway activity, refusing 0 or >1 hits,
and refusing if the identity is no longer among that query's search hits), and
`to_bw_dict(inv)` (the `Database.write` payload). That replaces the five
hand-rolled resolvers and the `_append_techno`/`_append_bio`/write blocks.

### Search-based picking is kept, and made safe

A process entry carries both the search and the answer:

```python
"steel": Process(
    query="market for steel unalloyed GLO", pick=0,
    identity=("market for steel, unalloyed", "GLO", "steel, unalloyed"),
    why="generic unalloyed steel market; Hermesmann lists no grade",
),
```

The query and pick are how a choice is *made and changed*: edit either, run
`show()`, accept the pin. The identity is how it is *built*: the build never
depends on search order, so a ranking shift between ecoinvent or bw2data
versions becomes a refusal with a message, not a silent swap (the gas-plant
precedent). The `why` is what makes the choice legible a year later. The
notebook section therefore still prints the candidate neighbourhood for every
process, as today.

### What moves where

| from | to |
|---|---|
| `dc_config.GRID_SOURCES`, `APPLY_LOSSES`, `MARKET_LOSS_*` | `optimiser_lca/grid.py` |
| `lca_helpers` `WIND_GROUP_WEIGHTS`, `IMPORT_GROUP_WEIGHTS`, `TECH_SPECS`, `*_KEYS`, `FUEL_COLS`, `custom_electricity_score_for_row` | `optimiser_lca/grid.py` |
| `h2_prices.GRID_DELIVERY_*`, `ECOINVENT_GB_LV_*` and their check | `optimiser_lca/grid.py` (one description of the GB network) |
| `dc_config.FC_*` block | `optimiser_lca/fuel_cell.py` |
| `dc_config` tank block (`TANK_DESIGNS`, `TANK_DESIGN`, `TANK_H2_*`, compression) | `optimiser_lca/h2_tank.py` |
| `dc_config` `TX_*`, `UPV_TX_*`, `upv_tx_check`, `UPV_TX_SITE_KV_CHECK` | `optimiser_lca/stepup_transformers.py` |
| `dc_config` `UPV_PV_*`, `UPV_MOUNT_*`, `upv_pv_check` | `optimiser_lca/upv.py` |
| `lca_helpers.H2_CODES`, `ELECTROLYSER_CODES`, every code literal in `optimisation/` | `optimiser_lca/registry.py` |
| `lca_helpers` Renewables.ninja client | `optimisation/profiles.py` (its only caller) |
| notebook cells 63–66 validation | `optimiser_lca/validate.py` |
| notebook cells 67–72 | deleted (`renewables.py __main__` already prints it) |

What **stays** in `dc_config.py` (≈80 lines): Brightway project, ecoinvent
version and system model, the one `ECOINVENT_DB` name, `RUN_IMPORT_ECOINVENT`,
`DC_OPERATION_YEARS`, `DC_REFERENCE_PUE`, the amortisation lifetimes the
optimiser applies after the LCA (`TX_ASSET_LIFE_YEARS`, `TANK_LIFETIME_YEARS`),
`PV_TILT_DEG` etc. Rule: a number that changes an **exchange amount** lives
with its inventory; a number that only **amortises** a scored activity in
`optimisation/` stays in `dc_config`. `RUN_BUILD_FOREGROUND_DATABASE` goes —
`python -m optimiser_lca.build` is run on purpose.

What **stays** in `lca_helpers.py` (≈150 lines): `setup_brightway`, the
handles, `_select_gwp_method`, `resolve_exact` (promoted from
`get_exact_activities`), `show_candidates`/`pick_candidate` for exploration
only, `run_lca_score`, `run_non_electricity_lca`, `is_any_electricity_exchange`.

### The notebook afterwards

`2.tech_lca_foreground.ipynb` becomes the reader, ~400 lines, one `##` per
LCA, every section identical in shape:

```
## Grid                    grid.show()  → sources table with g CO2e/kWh each,
                           split weights, one worked half-hour
## Hydrogen (Hermesmann)   hydrogen.show() → one table per activity
## Data centre (Zhang)     …
## Fuel cell (Babatunde)   … then validate.fc_stack_vs_paper()
## H2 tank (Gandiglio)     …
## Step-up transformers    …
## Utility PV (Smith)      …
## Build                   optimiser_lca.build.main()  — or run from the shell
```

A separate `scratch/find_activities.ipynb` is for open-ended searching when
a new source needs mapping, before a `Process` entry exists. It writes
nothing. Once an entry exists, its neighbourhood is shown in the main
notebook by `show()`.

---

## 4. Steps, in order

Each step leaves the repo working; the acceptance test for every step is the
snapshot comparison in step 0.

0. **Freeze a reference.** Script dumps every activity in the six foreground
   DBs — `(db, code)`, name, unit, location, and each exchange's input key,
   amount, unit, type — to `optimisation_outputs/foreground_snapshot.json`.
   Re-run after each step; any diff is either a bug or a finding to record
   in `SOURCES.md`. Also re-run `python optimisation/coefficients.py` and
   diff `tech_lca_coefficients.csv`.
1. **Registry and resolver, no behaviour change.** Add
   `optimiser_lca/registry.py`; replace the code/DB literals in
   `fuel_cell.py`, `h2_storage.py`, `baseline_grid.py`, `renewables.py`,
   `transformers.py`, `dc_inputs.py`, `electrolysers.py`, `h2_prices.py`.
   Add `lca_helpers.resolve_exact(name, location, unit=None, product=None)`
   and use it in `grid_connection.py`, `transformers.py`, `h2_prices.py`.
   One `ECOINVENT_DB` in `dc_config`.
2. **Cells 53–60 first** (the messy ones, and already half in `dc_config`):
   `h2_tank.py`, `stepup_transformers.py`, `upv.py`. The `("__FG__", code)`
   placeholders become real keys because the registry knows the DB name.
   Physics becomes a named function with a printed check. Snapshot must
   match exactly.
3. **Fuel cell and data centre**: `fuel_cell.py` (stack + operation, with the
   `FC_*` parameters), `data_centre.py`. `validate.py` gets cells 64 and 66.
4. **Hermesmann hydrogen**: keep each query and index as the `Process`'s
   `query`/`pick`, run `pin()` once to record the identity beside it, and
   add a `why` for each.
   This is the step most likely to surface a wrong pick (see the gas
   precedent); the snapshot diff is the guard and any change is a finding.
   The capital-good links and the SMR-CCS → CCS link move from cell 62 into
   the operation activities where they belong.
5. **Grid**: `optimiser_lca/grid.py`; `grid_build.py` imports it. `grid_sources_id()`
   hashes the dict *content* (sorted JSON), so moving the dict unchanged keeps
   every series on disk valid — verify the id before and after. Fold the
   `h2_prices` network constants in so one module describes GB delivery.
6. **`build.py`** writes the DBs in dependency order (hydrogen → data centre →
   fuel cell → tank → transformers → upv), deleting and rewriting each, and
   prints each activity as cell 62 does now. `backend/runner.py` and
   `sites.ensure_foreground` call it as a subprocess instead of nbconvert,
   which also retires the Windows console-subsystem workaround.
7. **Rewrite the notebook** as the thin reader above; delete cells 67–72;
   move the markdown essays into module docstrings and leave a two-line
   pointer in each notebook section.
8. **Slim `dc_config.py` and `lca_helpers.py`** to the residue in §3; move the
   ninja client to `profiles.py`. Update `README.md`, `STREAMLINING_PLAN.md`,
   `SOURCES.md` pointers ("built in `optimiser_lca/x.py`" instead of "cells of
   notebook 2"), and `optimisation/*` docstrings that say "the inventory lives
   in the notebook".
9. **Tests.** `tests/test_optimiser_lca.py`: without Brightway — every module's
   tables are well-formed (units from a fixed set, every technosphere key has
   a process, no duplicate codes, registry complete, each `check()` passes);
   with Brightway (skipped if the project is absent) — every identity resolves
   to exactly one activity, and the rebuilt DBs match the snapshot.

Steps 1, 2 and 5 are independent and can be done in any order; 3–4 depend on
1; 6–8 come last.

---

## 5. Decisions taken (13 Oct 2026)

- **Package name**: `optimiser_lca/` — the LCA side of the optimiser.
  `optimisation/transformers.py` already exists, hence
  `optimiser_lca/stepup_transformers.py`.
- **Data format**: Python literals throughout, as the notebook and
  `dc_config` are today; the one JSON bill (`upv_smith_bill.json`) stays as
  it is. No spreadsheets or CSV loaders.
- **Search-based picking**: kept, as `Process(query, pick, identity, why)`
  above. The search stays on screen; only the identity builds.
  `pick_candidate` in `lca_helpers` remains the exploration helper.

---

## 6. What the implementation found

The acceptance test was a snapshot of every foreground activity before and
after (`scripts/snapshot_foreground.py`). The rebuilt databases match the
originals exactly — every activity, every exchange input and amount — for all
30 activities the notebook wrote. Every coefficient cache and
`tech_lca_coefficients.csv` regenerate to the same numbers. Along the way:

- **Seven stray activities** lived in `hydrogen foreground`: six
  `custom_gb_elec_mix_*` and one `direct_wind_electricity_1kwh`, written by
  the archived electrolyser notebooks and never deleted because notebook 2 had
  not been re-run since. Nothing on `main` referenced them; the rebuild
  dropped them, as the old notebook would have.
- **The grid is scored on IPCC 2021 GWP100 "no LT"**; the asset coefficients on
  the with-LT variant. `lca_helpers._select_gwp_method` picks the first match
  in `bd.methods`, which is the no-LT one. Left unchanged (fixing it would
  stale every grid series on disk) and registered in `DATA_GAPS.md`.
- **Search-rank biosphere picks were wrong in zero-GWP ways.** Hermesmann's
  "oxygen to air" is pinned to oxygen to *water*; "water to air" to a
  natural-resource flow. Smith's 40 UPV substances were matched to whichever
  compartment came first in biosphere iteration order — and that order has
  since changed, so re-running the old match today gives different
  compartments. The compartments the original build used are now pinned
  explicitly (`upv.BIOSPHERE_CATEGORIES`) with the reason stated.
- **Five technosphere picks are worth a second look** when the SOEC or MP-E
  stacks are ever scored on non-carbon categories: palladium routed to the
  catalytic-converter market, alumina to the refractory market, cerium oxide
  to mischmetal, and the two 35 MPa concretes (CEM III/A for alkaline, CEM II/B
  for PEM and SOEC) from the same query at different ranks. Each carries a
  `why` in `optimiser_lca/hydrogen.py`.
- **The UPV exchanges carried the bill's raw unit strings** (`kg`, `m2`,
  `Item(s)`); they are now Brightway's names. Cosmetic — the input activity's
  own unit is what Brightway uses — but it was the one place the inventory
  would have failed a unit check.
