# Fuel-cell stack interest and the equations-page wording: plan

Drafted 19 Nov 2026. Branch `source-update`, folder `C:\Users\ls1524\Desktop\ukdclca-sources`.

**In short:** one code fix that changes results (the fuel-cell stack gets charged interest like everything else), then the wording fixes on the equations page from the 19 Nov review. Some of that wording depends on the fix, so the code goes first. All solving runs on the cluster at East Grinstead (site 23). The laptop runs only the quick checks that don't solve anything.

Nothing in this plan runs until the user gives the word.

---

## Order of work

| Step | What | Changes results? | Where it runs |
|---|---|---|---|
| 1 | Fuel-cell stack interest | Yes: fuel-cell builds cost more | Laptop (code), no solving |
| 2 | Equations page wording (the 19 Nov review), with the stack wording updated | No | Laptop |
| 3 | Docs write-up and methods doc | No | Docs |
| 4 | Rebuild the explainer, quick checks, commit, push | No | Laptop, seconds |
| 5 | Collect the batches already running | — | Cluster |
| 6 | Before/after of the stack fix at East Grinstead | — | Cluster |
| 7 | Maps and workbooks from the new run | No | Laptop, from the copied-back run |

---

## Step 1 · Fuel-cell stack interest (changes results)

**The problem.** Every asset is charged a yearly repayment with interest at its rate, including during the build. The fuel-cell stack is the one exception. It's charged its price divided by its life, £466k per MW ÷ 10 years = **£46.6k per MW a year**. Charged like everything else (10.1 %, three-year build), the figure is **£88.3k per MW a year**. So the stack line is about half what it should be, and the fuel-cell line is about 11 % low. Terlouw's code charges interest on it. Our own `DATA_GAPS.md` row "Fuel cell duty cost" already lists it as open. The code comment at `h2_capex.py:336-341` says leaving out the discount "overstates" the cost, but the net effect is too low.

**The fix: treat the stack the same way as the rest of the fuel-cell plant.** The rest of the plant is already charged as:

    rest of plant:  A·(build finance × repayment factor(L) + upkeep − 1/L) on capacity  +  A per replacement

Do the same for the stack, with its own life:

    stack:          S·(build finance × repayment factor(Ls) − 1/Ls) on capacity  +  S per replacement

When the stack is replaced on its 10-year calendar life, this is **exactly** the repayment with interest. When running hours wear it out sooner, it stays within about 8 % of the exact figure either way, depending on whether each replacement also carries build-time interest; the true answer sits between the two. Worked figures:

| Running hours a year | 1,000 | 3,000 | 4,000 | 6,000 | 8,760 |
|---|---|---|---|---|---|
| New charge vs exact (each replacement with build interest) | 0 % | 0 % | −2.2 % | −5.6 % | −8.5 % |
| New charge vs exact (replacements without build interest) | — | — | +13 % | +9 % | +6 % |

(Up to 3,000 hours the stack lasts its full 10 years, so the calendar figure applies exactly. The rest of the plant run flat out is −1.8 % on the same test.)

**Files.**
1. `optimisation/h2_capex.py`, `fuel_cell_cost()`:
   - take `stack_calendar_years` (default `fuel_cell.STACK_CALENDAR_LIFETIME_YEARS`) and record it with `T.cost` as `cost.fuel_cell.stack_life_years`;
   - add `cost.fuel_cell.stack_crf` (the repayment factor over the stack life at the same rate);
   - add the stack term to `cost.fuel_cell.annual_per_MW`: `stack_capital × (finance × stack_crf − 1/stack_life)`;
   - `cost.fuel_cell.stack_per_MW` stays the price per replacement; rewrite its note and the comment at lines 336-341 to say what's now true;
   - `fuel_cell_costs()` passes the stack life through.
2. `optimisation/dc_inputs.py` near line 1002: pass `fc_stack_years` to `hc.fuel_cell_cost`, so the stack-life sensitivity cases (5/10/15 years) move the cost as well as the carbon.
3. `tests/test_coefficients.py`: a stack twin of `test_fuel_cell_bop_cost_increment_tracks_the_exact_annuity`. It must be exact at or below the calendar rate and within 9 % of the exact figure above it. Check that the existing rest-of-plant test still passes.
4. `optimisation/DATA_GAPS.md`, row "Fuel cell duty cost": close the stack part with today's date and the before/after figures from step 6.
5. `docs/CODE_CHECK_FIX_PLAN.md` item 5 ("Replacements undiscounted"): replace the paper sentence with the wording in step 2, item 11.
6. Read `optimisation/audit.py`'s replacement checks. If any of them solves a model, it goes to the cluster with step 6, not the laptop.

**Size of the change.** About +£42k per MW of fuel cell a year in 2025 pounds (about +£43k in the model's 2026 pounds). With the calendar life binding, the fuel-cell line goes from about £366k to £409k per MW a year. Builds with no fuel cell are unchanged to the last digit.

---

## Step 2 · Equations page wording (the 19 Nov review)

Page: `docs/model_equations_explorer.html`, embedded in `optimisation_outputs/model_explainer.html`. The review found **no maths errors**. Fix the wording only, and change no equation except item 2 (mark the battery duration limit optional).

1. **Time step.** "Δt is the step length in hours: 1 in the study's runs (the half-hourly data resampled to hourly), 0.5 if run unresampled. About 8,760 steps a year." Replace "every half-hour" with "every step" in section 4 and the explain boxes. (Code: `dc_runner.py:474`, also `uk_sites.py`, `signoff.py`, `thresholds.py`; raw data `dc_inputs.py:378`.)
2. **Battery duration limit** (`batcap` / `Hmax`): optional and off by default (`dc_model.py:542-543`, default infinity at `:280`, `dc_inputs.py:1307`). Dashed outline and "(optional)" in its name, like the other optional terms. No big brackets.
3. **Strategy box, "free" bullet:** "With a grid, 'flexible' runs as 'free' (strategy_for); baseload still applies." (`dc_architectures.py:221-226`, `dc_model.py:1017-1020`.)
4. **Bought hydrogen carbon** (`gammab`): the figure is delivered to the tank, not at the factory gate. It includes the seller's trailer compression, and hydrogen leaked in production, on the road trailer and at the fuel cell, each × 11.6 (`dc_inputs.py:~1704-1730`, `:1411`; `h2_leakage.py:66-72`). Add "delivered, with compression" to the price panel `pib` (`dc_inputs.py:1121-1139`).
5. **Electrolyser running materials** (`gelv`) and the "Hydrogen leaks" bullet: the coefficient also carries hydrogen leaked at the electrolyser and the fuel cell × 11.6 (`dc_inputs.py:1387-1390`, `h2_leakage.py:55-58`). List all three leak points.
6. **Grid price** (`pi`, `piv`, running-cost box): write it out in plain words as built: (wholesale + balancing charge) × loss factor + local network unit rates + policy levies (`dc_inputs.py:286-288`; per voltage group `:328-329`).
7. **Tank and electrolyser prices.** `ctk`: insurance and business rates are always in, not "where set" (`dc_inputs.py:930-934`, `:1334-1335`). `cel`: add insurance and business rates, and say the price is scaled by the stack share of the input (`dc_inputs.py:927-929`, `:1320-1322`).
8. **Data centre's own carbon** (`Gdc`): the part that scales with IT is the building shell, the servers and the power backup (`dc_inputs.py:59-61`, `:1185-1186`).
9. **Section 5, connection solving:** add "pruned": each price list is priced alone at both ends, those within 2 % are kept, then solved at the tight gap (`dc_runner.py:101`, `:156-160`, `:227-231`).
10. **Replacements box (4.8):** electrolyser stack replacements are on the carbon side only (`dc_model.py:802`); the cost side charges per kg made. In the cheapest-design solve that rate has no weight. The carbon tie-break (`dc_pareto.py:284-285`) and the carbon caps settle it.
11. **Building-costs box, "replacements at face value … overstates"** — **reworded for step 1:**
    "The fuel-cell stack, the rest of the fuel-cell plant and the gas engines are each charged a yearly repayment, less the price ÷ life, on capacity, plus their price at each replacement. When they're replaced on their calendar life, that's exactly the yearly repayment. When running hours wear them out sooner, the extra replacements are charged at their price: within about 2 % of the exact figure for the rest of the plant and about 8 % for the stack run flat out." Electrolyser stacks aren't in this box: their cost is per kg made (item 10). Check the 2 % and 8 % against step 1's test before writing them in. Update the `cfc`, `cfcs` and `cgerep` panels to the same wording.
12. **Number of points** (`N`): "12 by default in `front()` and the scenario list; the 26-site study and the sign-off use 5, and some runs place the points with eps_fracs."
13. **Small wording fixes.** `phiw`: one turbine's capacity factor × the farm factor 0.851 (`dc_inputs.py:373-380`). `cgegas`: 44.6 % is the net efficiency; gas is costed at 2.49 MWh of gas per MWh made, about 40 % gross (`dc_inputs.py:1011-1013`, `optimiser_lca/gas_engine.py:99`). `base` equation: add the grid condition, as the panel has it (`dc_model.py:1017`).

**"Show in code" links that land near the right line** (re-point; search string + anchor):
- `Hduty` → `fc_stack_duty_hours=` at `dc_inputs.py:1306`, not the trace dict at `:1249`. Add the rest-of-plant duty at `:1304`.
- `lconv` → add the grid's (`dc_model.py:306`) and the fuel cell's (`:321`) beside the battery's (`:319`).
- `flex`, `baseload` → the constraints (`dc_model.py:1020`, `:1022`, `:1057`), not `def apply_strategy`.
- `tilde` → the scaling lines (`dc_pareto.py:380-381`), not `def special_points`.
- `pi` → where the price is composed (`dc_inputs.py:286`), not `:383`.
- Step 1 moves line numbers in `h2_capex.py` and `dc_inputs.py`: re-point any links into those files.

**Leave as they are:** `export_cap` (dead, export is refused), `cost_epsilon`, the "connection" objective and `relax_switches` stay described in prose only.

---

## Step 3 · Docs write-up and methods doc

1. **"DC optimiser: model equations"** (https://claude.ai/artifact/TwkZu1qfhf4kKoBMEB4Qhh): apply items 1, 3, 4, 5, 6, 10 and 11 where it has the same wording. Check the Overview time line, the price tables and the replacements paragraph.
2. **Methods doc:** if it carries the "replacements undiscounted" sentence or a fuel-cell cost description, bring it in line with item 11. Add an author note that the fuel-cell cost changed on this date and which results must re-run (step 6 onwards).

---

## Step 4 · Explainer, quick checks, commit

1. `python scripts/build_model_explainer.py` (seconds, no solve). Its header will say the map numbers were "made with an earlier model" until step 7. That's expected.
2. Quick checks on the laptop. None of these solve anything:
   `pytest tests/test_equations_page.py tests/test_model_explainer.py tests/test_coefficients.py tests/test_cost_exclusions.py`, and the link check `build_model_explainer._check_code_links(_code_files())`. All must pass with no warnings.
3. The pre-commit hook that rebuilds the explainer **isn't installed** (`.git/hooks/pre-commit` holds only the overnight rule). So rebuild by hand, and copy `model_explainer.html` to `OneDrive - Imperial College London/DC optimiser/report exorts/model explainer.html`.
4. Commit on `source-update` in two commits: (a) the stack fix with its test and register notes; (b) the page, the explainer and the plan files. Push, so the cluster can pull it.

---

## Step 5 · Collect the batches already running (cluster)

The code-check before/after is still out: batches **3033334** (before) and **3033335** (after), plus the 8-core reruns of the slow configurations, **3034467** and **3034468**.
1. `bash scripts/cluster/progress.sh <batch>` for each; wait for all four.
2. `bash scripts/cluster/fixcheck_pack.sh`, then one `scp` home, and finish the code-check table (`docs/CODE_CHECK_FIX_PLAN.md` step 5).

Their "after" run (commit 3154401) is the baseline for step 6.

---

## Step 6 · Before/after of the stack fix (cluster, East Grinstead)

1. New script `scripts/cluster/fixcheck_fc_setup.sh`, modelled on `fixcheck_setup.sh`: one new copy `~/fix-fc` at the step-1 commit, then submit the same piece list as "after" (`pieces/fixcheck_after.txt`) with `REPO=$HOME/fix-fc`. Submit configurations 2, 3 and 21 at 8 cores from the start (`fixcheck_slow_after.txt`, as in `fixcheck_more_cores.sh`). Light work only on the login node.
2. Also run the **full test suite** there as one small job (`pytest -q`), since some tests solve small models.
3. The user types the password in the Terminal panel, so steps 1-2 are bundled into one login. Show the Terminal pane before asking.
4. **Checks against the "after" run:**
   - every configuration that can't build a fuel cell: identical to the last digit. Anything else means something else changed; stop and look;
   - fuel-cell configurations: the bill rises by about fuel-cell MW × £43k a year where the design doesn't change; report any that change design (smaller fuel cell, swap to battery, tank or gas engines), at the lowest-cost, knee and lowest-carbon points;
   - carbon is unchanged wherever the design is unchanged.
5. Write the table to `docs/SOURCE_DIFF.md`, and close the `DATA_GAPS.md` row with the figures.

**What this voids.** Any model change voids the last sign-off (`docs/TESTING.md`). The fuel-cell capital is one of the screened inputs (`sensitivity.SHAKY_KNOBS`), and the 26-site and four-site robustness results carry the old fuel-cell cost. Re-running those is **not** in this plan. It's a separate decision for the user, best made once, alongside the other pending changes.

---

## Step 7 · Maps and workbooks from the new run

1. Copy the step-6 East Grinstead reference run home.
2. `scripts/build_cost_map.py` and `scripts/build_lca_map.py` from it. Both call the explainer's `write()`, so its "earlier model" flag clears.
3. `scripts/build_workbooks.py` and `scripts/check_workbooks.py`; refresh the expected files.
4. Rebuild the explainer, copy it to OneDrive, commit, push.
5. Republishing "Data Centre Maps" or the equations artifact: ask first.

---

## Not in this plan

- Re-running the 26-site study, the four-site robustness checks or the hourly sign-off with the new fuel-cell cost (see step 6, "What this voids").
- Solar output not being reduced as panels age. This came up in the Terlouw comparison and isn't yet in `DATA_GAPS.md`. It needs a decision first: state it as a limitation, or apply an average derate.
- Changing code defaults away from North Norfolk (a separate job; every run here passes site 23).
