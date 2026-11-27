# Plan: Terlouw's 75 % sell-off for assets that outlive the data centre

Written 25 Nov 2026. **Implemented 25 Nov 2026** (sections 1, 2 "while working" and "before
committing", 3 and 4's `ASSUMPTIONS.md` text); the equations page has a new "Assets that outlive the
data centre" section under building costs. **On the cluster (25 Nov, 04face6):** A = 26510, B = 26511,
C = 26512. A's three `old_lives` pieces were cancelled: the old central runs at site 23
(`uk_sites_2025_checks_none/central`, 9893e62 off grid, e469668 on the grid) are the "before", since
nothing but the sell-off changed since. The robustness set on the new rule was added at the user's request
(`sell_off_robustness_eg.txt`, 136 pieces, `sell_off_setup.sh robustness`). The rest of step D (26 sites,
near-optimal, +25 % grid price) waits. The methodology doc paragraphs wait for the results.

## Results (collected 26 Nov 2026; East Grinstead, site 23, hourly, nothing bought)

All 145 runs and 4 sign-off pieces finished without errors, on 04face6/8baed7a, sell-off at 75 %
(`optimisation_outputs/sell_off_checks_2025`, summary.csv; sign-off CSVs in `optimisation_outputs/`;
the previous sign-off CSVs kept in `Desktop/cluster_transfer/sell_off_26nov/old_signoff_csvs`).

- **Before/after** (old central `uk_sites_2025_checks_none/central` against the new central, all 7
  points x 3 levels): no kit added or dropped anywhere; the whole yearly bill +2.1 to +2.7 %.
  Lowest-carbon designs identical (same sizes and carbon at every level), cost +2.5 to +2.6 %.
  Lowest-cost designs: wind 214 -> 207 MW, solar 171 -> 163 MWp (177 -> 169 off grid), gas engines
  unchanged, carbon +3.5 % (242.7 -> 251.3 g/kWh). Middle points: sizes within a few per cent (off-grid
  battery 862 -> 817 MWh). Grid connection sizes unchanged. The in-between points sit at carbon caps
  set from each curve's own ends, so they are not exactly like for like.
- **The 75 % at x0.5 / x1.5:** no kit added or dropped at any of 42 points; bill +0.6 to +0.8 % /
  -0.6 to -0.8 %; sizes within 5.4 %, except one small 25 MW-level grid connection (20 %).
- **Robustness:** 885 of 952 verdicts hold (no kit over 1 MW / 1 t added or dropped against the
  variant's own central), against 879 of 952 on the old rule. 6 verdicts changed, all from "moves" to
  "holds"; none the other way.
- **Sign-off steps 4-5:** cost cut-off passes (nothing added or dropped, no size over 5 %); carbon
  cut-off gives the same moves as 25 Nov (lowest-carbon battery and solar, which do not depend on
  cost), which passed rule 3 with the 1 % size floor. Judged with a scratch script, as on 25 Nov.
- **Maps, workbooks and explainer rebuilt 27 Nov** from batch 32858 (6402a36): East Grinstead, full
  grid, central, on the sell-off, hourly operation saved (1 h 31 min on one core, 4.4 GB), in
  `optimisation_outputs/uk_sites_2025_sell_off/full/23/` and copied to
  `dc_runs/eastgrinstead_full_2025/` (the old-rule copy kept in
  `Desktop/cluster_transfer/sell_off_26nov/old_dc_run_eastgrinstead_full_2025`). The two map tests
  pass again. The Excel check found that the workbooks had left the gas engines out of every total
  since 13 Nov (the layout listed technologies by hand); fixed in `scripts/workbook_layout.py`, with
  a test, and every cell now recalculates to the model's value. Explainer copied to OneDrive.
- **26-site central set on the sell-off (27 Nov, user: "optimise for queue time"):** submitted at
  31222d3 as batches **42354** (off grid, 26 pieces, 3 h), **42355** (25 MW, 26, 5 h) and **42356**
  (full grid, 25, 5 h), one site and level per piece, one core, 6 GB, into `uk_sites_2025_sell_off`
  (site 23 full already there). Collect: `Desktop/cluster_transfer/sell_off_sites_collect.bat`, then
  `uk_sites.py --set central --summary --out uk_sites_2025_sell_off`, compare with
  `uk_sites_2025_central`, and update the methodology doc's author note. Not re-run (user agreed 27 Nov):
  near-optimal (lowest-carbon designs did not move), the other two buying settings, the four-site
  robustness checks and the +25 % grid price case; the doc states them as on the old rule.
- **Methodology doc updated 27 Nov:** Section 4 "Assets that outlive the facility" with the equation,
  Section 5.7 (cost credit only), Table 3 (75 % at x0.5/x1.5), and an author note with these results.
- **Cluster queue tidied 26 Nov:** leftover arrays 16880, 16881, 16883, 16884 (every piece already
  gone, resubmitted 24 Nov or superseded) cancelled; 3054377 was already out of the queue.

## Scope

**Only three assets change: wind, solar and the grid connection.** They are the only ones that
outlive the 25-year data centre. The step-up transformers at the wind and solar farms are inside
the farms' prices, so they go with them.

Everything else is untouched. That covers every other asset, all replacements, all carbon and the
optimiser's equations.

| Asset | Life | Years left at year 25 |
|---|---|---|
| Wind | 35 y | 10 |
| Solar | 38 y | 13 |
| Grid connection | 40 y | 15 |

## The rule

Following Terlouw et al. (2025, Applied Energy 377), OPTIMES `rep_annual_int`, the branch for a
component that outlives the project:

1. Repay the asset's build cost over the data centre's 25 years, instead of over its own life.
2. At year 25, sell it for **years left ÷ life × 75 % × its build cost**.
3. Discount that sale to today at the asset's own interest rate and take it off.

As one formula, per £ of build cost, for an asset of life L at interest rate r:

> yearly factor = repayment over 25 y × (1 − 0.75 × (L − 25) ÷ L ÷ (1 + r)^25)

It replaces today's "repayment over L years". The build-finance factor, running costs, land and
rates stay as they are.

The 75 % is Terlouw's assumption, with no source behind it in his paper. It gets the usual
×0.5 / ×1.5 test (37.5 % and 112.5 %). His Crete results never used this branch, because nothing
there outlives his 30-year project, so the wording says "following the treatment in Terlouw et
al.'s model".

## What it does to the numbers

| Asset | Yearly build cost | Whole yearly cost (roughly) | At 37.5 % / 112.5 % (build cost) |
|---|---|---|---|
| Wind | +6.1 % | about +4 % | +8.0 % / +4.2 % |
| Solar | +7.1 % | about +5–6 % | +9.4 % / +4.8 % |
| Grid connection | +11.6 % | about +11 % | +16.6 % / +6.6 % |

Carbon doesn't change. Expected effect (a judgement, not a result): builds a few per cent dearer,
with a slight lean away from on-site wind and solar.

---

## 1. Code

| File | Change |
|---|---|
| `dc_config.py` | `DATA_CENTRE_LIFE_YEARS = 25.0` (the facility's life, `optimiser_lca/data_centre.py`); `RESALE_SHARE = 0.75` (Terlouw); `SELL_OFF = True` (the new rule is the default) |
| `optimisation/tech_costs.py` | `annual_cost` (wind, solar): the repayment factor `crf` becomes the formula above when the asset's life is over 25 y and `SELL_OFF` is on. Each new number recorded with `T.cost`: project years, years left, resale share (cited to Terlouw), discount to year 25, the factor. The returned `lifetime_years` stays the asset's own life; add `project_years`. The cross-check against the source's own levelised cost keeps the own-life basis, since it checks the source |
| `optimisation/connection_cost.py` | `annual_factor`: `crf(r, 40)` becomes the same formula at the network's rate, with the same `T.cost` records |
| `optimisation/dc_inputs.py` | `build_tech(sell_off=None, resale_share=None)`, passed through to the two functions above, so one copy of the code can run old and new side by side; both recorded in the run's settings |
| `optimisation/dc_runner.py` | both settings go into the run's fingerprint and `summary.json`, so cached old-rule runs never mix with new ones |
| `scripts/fixed_choice_checks.py` | three variants: `old_lives` (`sell_off=False`), and `resale_share_x0.5` / `_x1.5` as pushes on the recorded resale share, the same way the other screened inputs are pushed |
| `optimisation/sensitivity.py` | the resale share added to `SHAKY_KNOBS` (unsourced, so it is screened like the rest) |
| `optimisation/audit.py` | `check_lifetime_agreement`: compare own lives as now, and print the 25-year repayment and resale share for the three assets. Also fix its stale comment that the grid connection has no money-side life (`annual_factor` repays over 40 y) |
| `scripts/build_workbooks.py` | a formula for the sell-off factor next to `capital_recovery_factor`, so the cost workbook rebuilds the new numbers from cells |
| `optimisation/source_register.py`, `optimisation/SOURCES.md` | Terlouw et al. 2025 registered (confirm the exact reference with the supervisor, as in the validation write-up) |
| `optimisation/ASSUMPTIONS.md` §5a | the paragraph below |

**Not touched:** every other asset, all replacements, every carbon number, `dc_model.py`, the
optimiser_lca inventories, the LCA map and the carbon workbook.

---

## 2. Testing, the usual way (`docs/TESTING.md`)

### While working: unit tests only, no solves

New `tests/test_sell_off.py`:
1. **Matches Terlouw's code.** A short copy of his `rep_annual_int` (with his BSD-3 licence notice)
   is run alongside ours. Our factor equals his 25-year repayment plus his outlives-the-project
   credit, at 75 %, to 1e-12, for wind, solar and the grid connection at their own lives and rates.
2. **Old rule unchanged.** With `sell_off=False`, every cost number equals today's.
3. **Only the three assets move.** With the default, wind, solar and grid-connection build cost
   rise by 6.1 %, 7.1 % and 11.6 %. Every other cost field of `build_tech`, and every carbon field,
   is identical to the old rule.
4. **The limits behave.** A resale share of 0 gives a plain 25-year repayment; a share of 1 gives
   straight-line resale.
5. **The audit's life check passes.**

Update the pinned wind, solar and grid-connection cost values in `tests/test_coefficients.py`,
`tests/test_connection_prices_by_area.py` and `tests/test_levies_and_connection_cost.py` (both read
`annual_factor`), and the cost workbook's `.expected.json`. Run the tests for those areas while working.

### Before committing

- The full test suite, which takes about 11 minutes.
- Rebuild the model explainer (`scripts/build_model_explainer.py`), the cost workbook and the cost
  map, which need no solve. Commit with the change, and copy the explainer to OneDrive.

### Runs: only when you say

All at East Grinstead (site 23), never London; all hourly; all on the cluster (section 3). Before
and after come from **one copy of the code at one commit**, with the old rule switched on by the
`old_lives` variant. No second code copy is needed.

| Step | What | Pieces | Passes when |
|---|---|---|---|
| A | **Before/after:** central and `old_lives`, East Grinstead × off-grid / 25 MW / full | 6 | reported, no pass mark. Off-grid has no grid connection, so it moves only through wind and solar. Carbon of any unchanged design is identical |
| B | **Percentage test** on the resale share: `resale_share_x0.5`, `_x1.5` × 3 levels | 6 | as for every screened input: recorded, and any design move over 5 %, or kit added or dropped, stated with the result |
| C | **Sign-off** (`docs/TESTING.md`) on the committed code: step 2 tests, steps 4–5 cut-off rule 3, step 6 screened inputs (now including the resale share) at East Grinstead | as in `weekend_signoff.txt` plus the screen | as in `docs/TESTING.md` |
| D | **Re-run what goes stale**, since wind, solar and the grid connection feed every build: the 26-site central study at three levels, East Grinstead robustness, near-optimal, +25 % grid price | as in `rerun_grid_sites.txt`, `finish_offgrid_sites.txt`, `rerun_grid_robustness_eg.txt`, `near_optimal_eg.txt`, `grid_price_eg.txt` | as before; **you choose which of these to redo** |

A and B answer "what does this rule do and does the 75 % matter". C makes it quotable. D brings
the headline results onto the new rule.

---

## 3. Cluster, set up for queue speed

As on 24 Nov (`scripts/cluster/requeue_small.sh`, `extra_checks_setup.sh`): every logged piece
ran on one core whatever was asked for, and small requests fit gaps in the queue. So:

- **Every piece gets one core and 6 GB** (the most seen was 4.4 GB), with short time limits from
  the logs: off-grid 3 h (85 min seen), East Grinstead checks at 25 MW and full grid 4 h (138 min
  seen), 26-site grid pieces 8 h.
- **One small piece per site, level and variant**, so pieces start as soon as gaps appear.
- **One code copy.** `~/ukdclca` is pulled to the commit that adds the rule; there is no `~/fix-*`
  copy, since the `old_lives` variant gives the "before".
- **New files:**
  - `scripts/cluster/pieces/sell_off_eg.txt`: step A, 6 lines of `scripts/fixed_choice_checks.py
    --no-summary --supply none --variants central old_lives --sites 23 --levels <level>`, one per
    level and variant;
  - `scripts/cluster/pieces/sell_off_resale_eg.txt`: step B, 6 lines, the two resale variants;
  - `scripts/cluster/sell_off_setup.sh`: checks that `~/ukdclca` holds the rule (refuses to submit
    otherwise), prints the commit, and submits each list as an array through `submit.sh` and
    `batch.pbs` at `ncpus=1:mem=6gb` with that list's time limit. Then the sign-off pieces, and
    step D's lists only if you've said which.
- **Logins:** one password tab for `git pull` plus `bash scripts/cluster/sell_off_setup.sh`
  (no double quotes inside the ssh command, as the 19 Nov lesson says), and one for collecting
  through a `.bat` that streams one packed file back. Progress with
  `bash scripts/cluster/progress.sh <batch>`.
- **Collect** into `optimisation_outputs/` on the laptop, then `fixed_choice_checks.py --summary`,
  the before/after table (sizes, cost, carbon, kit added or dropped), and the sign-off log row.

---

## 4. Wording

`ASSUMPTIONS.md` §5a:

> **Assets that outlive the data centre.** Wind (35 y), solar (38 y, with their step-up
> transformers) and the grid connection (40 y) outlast the 25-year facility. Following the
> treatment in Terlouw et al.'s model (2025), each is repaid over the facility's 25 years and sold
> at year 25 for 75 % of its remaining straight-line value, discounted to today at its own rate.
> The 75 % is their assumption and is tested at ×0.5 and ×1.5. Carbon is spread over each asset's
> own life, as in Terlouw et al.

Methodology doc, cost section:

> Assets whose life exceeds the facility's 25 years (onshore wind, solar PV and the grid
> connection) are annualised over 25 years with a residual value at year 25 of 75 % of their
> remaining straight-line value, discounted at the asset's hurdle rate, following Terlouw et al.
> (2025); the 75 % is tested at ±50 %.

Methodology doc, future work (the parked 2045 question):

> Grid carbon and prices are held at the sample year's values over the asset lives. Re-scoring the
> chosen designs against projected future grids (for example the NESO Future Energy Scenarios
> pathways) is left for future work, as in Terlouw et al. (2025).

---

## 5. Order of work

1. Settings, `tech_costs.py`, `connection_cost.py`, `build_tech` plumbing, run fingerprint.
2. `tests/test_sell_off.py` and the pinned-value updates; area tests.
3. Audit, workbook formula, `fixed_choice_checks.py` variants, `SHAKY_KNOBS`, source register,
   `SOURCES.md`, `ASSUMPTIONS.md`.
4. Full test suite; rebuild explainer, cost workbook and cost map; commit; OneDrive copy.
5. Cluster files (section 3), committed and pushed.
6. **Stop: you review.** Runs A and B on your word, then C, then whichever of D you choose.
7. Methodology doc paragraphs once results are in.
