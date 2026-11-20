# Code check: fix plan

**Status: final, 19 Nov 2026. Not yet carried out.**

Drafted 19 Nov 2026 from the equation write-up (`docs/model_equations_explorer.html`). It covers the nine items found when `optimisation/dc_model.py` and `optimisation/dc_pareto.py` were read against their equations at commit ee4a623.

**In short:** offshore wind is removed as a buildable asset, since the study doesn't use it. One code fix changes results (electrolyser stacks), one stops a possible crash (NumPy), and one removes duplicate scenarios (`flexible` with a grid). The other five items are sentences for the paper; one of them needs a quick data check first. Do the steps in the order below. Each ends with a test or check, so nothing is left half-done.

**Decided 19 Nov 2026:** offshore wind is removed (step 2), and electrolyser stacks get a one-stack floor (D2 = option B, step 3). With a grid, the electrolyser runs freely (step 4). No decisions are open.

---

## Order of work

| Step | Item | Type | Changes results? | Size |
|---|---|---|---|---|
| 1 | NumPy `ptp` | Code | No | 2 lines |
| 2 | Remove offshore wind | Code (about 30 files) | No: it's already switched off | Medium |
| 3 | Electrolyser stack charging | Code | Yes, small, hydrogen rows | Small–medium |
| 4 | `flexible` with a grid → `free` | Code (relabel) | Removes duplicate rows only | Small |
| 5 | Re-run, compare, check prices | Runs | — | One sweep |
| 6 | Paper wording for items 5–9 | Text | No | Short |
| 7 | Update the equation write-ups | Docs | No | Small |

---

## Step 1 · NumPy `ptp` (stops a possible crash)

**Problem.** `dc_pareto.special_points` calls `c.ptp()` and `g.ptp()` (lines 371–372). NumPy 2.0 removed `ndarray.ptp`, so on NumPy 2.x the knee selection raises `AttributeError`.

**Fix.**
1. Replace `c.ptp()` with `np.ptp(c)` and `g.ptp()` with `np.ptp(g)`.
2. Search the rest of the repo for `.ptp(` and fix any others the same way.
3. Pin NumPy in the requirements file so the version is recorded (the `.venv` in the repo folder holds only pip, so the version in use isn't visible).

**Check.** Run `pytest tests/` on whichever NumPy you use. Add one test that calls `special_points` on a three-row front and checks the knee index.

---

## Step 2 · Remove offshore wind as a buildable asset (no change to results)

**Why.** Offshore wind isn't in the study: every site is on land. It's already switched off (`dc_architectures.OFFSHORE_IN_SCOPE = False`, decided 3 Sep 2026), so the onshore-profile bug never reached a result. It still adds a capacity, a flow, two coefficients and a stack of code paths that can go wrong. Removing it makes the model, the equations and the paper simpler.

**What stays.** Offshore wind as part of the **GB grid mix** is real data and is not touched:
- `optimiser_lca/grid.py` (`WIND_13_OFFSHORE` in the grid electricity inventory)
- the substation-name filter in `scripts/build_substation_register.py`
- the "this far offshore" message for map clicks in `pages/2_Data_Centre_Optimiser.py`
- citation text that quotes a source's own tables (for example CEPA's offshore hurdle rate in `source_register.py`)

**What goes, by file.**

| File | Remove |
|---|---|
| `optimisation/dc_model.py` | `Assets.offshore_wind`; `Tech.gwp_offshore`, `Tech.cost_offshore`; variables `cap_offshore`, `p_offshore`; `offshore_cf` constraint; offshore in the balance, the no-load loss, the `flexible` rule, both objectives, `CHAINS`, `SERVE_SOURCES`, the serve-stack split and the dispatch frame |
| `optimisation/dc_architectures.py` | `OFFSHORE_IN_SCOPE`, the `offshore=` argument on `custom()` and `architecture()`, `offshore_wind` in `ASSET_FLAGS` and `_SHORT` |
| `optimisation/dc_inputs.py` | `gwp_offshore` and `cost_offshore` in `build_tech`; tidy the two comments |
| `optimisation/dc_pareto.py` | `cap_offshore` in `CAPACITY_VARS` and `ENERGY_VARS` |
| `optimisation/myopic.py` | `cap_offshore` in availability and both capacity lists |
| `optimisation/audit.py` | `p_offshore`; `offshore_wind` in the asset loop |
| `optimisation/sites.py` | `OFFSHORE_REGIONS`, `Site.offshore_wind`, and the column in the site table |
| `optimisation/thresholds.py`, `sensitivity.py`, `dc_runner.py` | the `offshore=` argument they pass |
| `optimisation/tech_costs.py` | `OFFSHORE_WIND`, `OFFSHORE_SOURCE`, the offshore cost entry and hurdle rate |
| `optimisation/renewables.py` | the offshore inventory entry and its life; tidy comments |
| `optimisation/transformers.py`, `conversion_losses.py` | `offshore_wind` in the technology lists |
| `optimisation/coefficients.py` | the docstring row |
| `optimisation/source_register.py` | the `desnz_arup_2024_offshore` source, if nothing else cites it |
| `pages/2_Data_Centre_Optimiser.py` | the offshore colour and the `offshore_wind` flag |
| `scripts/` (`build_workbooks`, `workbook_layout`, `build_cost_map`, `build_lca_map`, `cutoff_rule3`, `screen_inputs`, `shaky_judge`, `signoff`, `solver_compare`) | `cap_offshore` and offshore labels |
| `tests/` (`test_dc_model`, `test_connection_choice`, `test_serve_stack`, `test_thresholds`, `test_coefficients`) | offshore fields in the test `Tech`s and `Series`; replace `test_offshore_wind_is_out_of_scope` with a test that `Assets` has no offshore field |
| Docs | `DATA_GAPS.md`, `SOURCES.md`, `ASSUMPTIONS.md`; the cost source PDF stays in `cost sources/` as reading |

**How.**
1. Run the full test suite first and save the result (on this machine the solver needs `DC_SOLVER=highs`; Gurobi is the default).
2. Make the removals file by file, starting with `dc_model.py`, then everything that imports it.
3. `grep -ri offshore` afterwards. Only the "what stays" lines should remain.
4. Old saved results in `optimisation_outputs/` may still carry `cap_offshore` columns (all zero). Scripts reading them should ignore unknown columns rather than fail, so check `build_workbooks` against one old output.

**Check.**
- The same tests pass as before (minus the replaced offshore test).
- Re-run one reference case before and after: cost, GWP and every capacity must match to the last digit, because offshore was always zero.

---

## Step 3 · Electrolyser stacks charged two ways (changes results, slightly)

**How it got this way.** On 26 Oct 2026 (`docs/ELECTROLYSER_STACKS.md`, option B) the electrolyser's embodied carbon was split into plant + stacks. Stacks became `ely_stack_units` ≥ max(capacity ÷ 8.33 years, yearly MWh ÷ 50,000 h): the same rule as the fuel cell. The 8.33-year floor isn't a sourced calendar life. It's 25 years ÷ 3 stacks, chosen so that low-use electrolysers kept the charge they had before (three stacks per plant life). The change was made **carbon only**, because NESO publishes no separate stack cost to mirror.

**What each side does now.**
- **Carbon:** at least 3 stacks per 25 years, whatever the use; more above about 68 % utilisation (6,000 h a year).
- **Cost:** NESO's capex (which includes the first stack) + NESO's variable opex per kg made ("stack replacement and water"). Replacements therefore scale with output only, with no floor.

The sides agree around 68 % utilisation and part company below it. For the islanded PEM reference case, the min-carbon design's 81 MW electrolyser runs at 17 % and is charged about 3 stacks against 0.7 by running hours: roughly 1,000 t CO2e a year, 2.3 % of the system (`ELECTROLYSER_STACKS.md`). Cost has no such penalty.

**Decision D2: option B chosen (19 Nov 2026).**

| Option | Carbon rule | Cost rule | For | Against |
|---|---|---|---|---|
| A. Keep and state it | ≥ 3 stacks per 25 y, or by hours | per kg (NESO) | No work; conservative on carbon | Sides disagree below 68 %; the floor isn't sourced and can shrink the min-carbon electrolyser |
| **B. One-stack floor (chosen)** | ≥ 1 stack per 25 y (the first one is always built), or by hours | per kg (NESO), capex holds the first stack | Both sides then mean the same thing; every number is sourced (Gerloff 50,000 h, NESO) | Ignores calendar ageing of membranes; no held source quantifies it |
| C. Floor on both sides | ≥ 3 stacks per 25 y, or by hours | the same, with a stack price per MW | Consistent and conservative | Needs a stack price and a calendar life that no held source gives |

**Fix (option B, chosen).**
1. `electrolysers.py`: set `STACK_CALENDAR_YEARS = PLANT_LIFETIME_YEARS` (25 y, one stack) and update its comment and grade.
2. Keep option A as a named sensitivity (`STACK_CALENDAR_YEARS = 25 / 3`) so the paper can report both.
3. `ELECTROLYSER_STACKS.md`: add a dated section recording the change and why.

**Check.**
- Unit test: an electrolyser at 10 % utilisation carries one stack per 25 years; one at 85 % carries 85 % × 8,760 × 25 ÷ 50,000 ≈ 3.7.
- The existing test `test_electrolyser_calendar_floor_is_the_old_whole_unit_charge` will fail by design: replace it.

---

## Step 4 · `flexible` does nothing with a grid

**Problem.** `apply_strategy("flexible")` adds the surplus-only rule only when `assets.grid` is False. Grid-connected hydrogen rows labelled `flexible` therefore solve exactly as `free`.

**Decision (19 Nov 2026): with a grid, the electrolyser runs freely.** No grid-connected flexible rule is added. The carbon objective already prices every MWh the electrolyser draws from the grid at that half-hour's carbon intensity, so the trade-off curve shows how much grid-heavy running each point accepts.

**Fix.**
1. `dc_architectures.py` / the scenario matrix: don't offer `flexible` for grid-connected architectures. Map any request for it to `free`, with a note in the run summary.
2. Drop the duplicate grid + `flexible` rows from the scenario list and update the configuration count wherever it's quoted (18 → the new number).
3. `apply_strategy` docstring: say that `flexible` is an off-grid rule (surplus-only) and that grid-connected runs are `free`.
4. Paper: one sentence in the methods. "With a grid connection the electrolyser is dispatched freely; its imports are charged at the half-hourly grid carbon intensity in the GWP objective."

**Check.** A test that asking for grid + `flexible` returns a `free` run, and that the scenario list has no grid + `flexible` rows.

---

## Step 5 · Re-run and compare

1. Run `pytest tests/` and make sure everything passes.
2. Re-run the two reference cases used in `scripts/solver_compare.py` and the full scenario sweep (`scripts/run_dc_scenarios.py`).
3. Produce a before/after table per configuration: min-cost cost and GWP, min-GWP cost and GWP, knee cost and GWP, capacities.
4. **Expected changes:**
   - Step 2 (offshore removal) changes nothing: every row must match before step 3.
   - Hydrogen rows: small cost changes from step 3.
   - Everything else: identical to the last digit. If not, something else changed. Investigate before going on.
5. **Negative-price check (item 8).** Print the minimum of `grid_price_per_mwh` for every site and window in the sweep. If none is below zero, item 8 is a sentence (step 6). If any is, look in those solved dispatches for half-hours with both battery charging and discharging above zero, and report what you find before choosing a fix.

   **Result (20 Nov 2026, no solving):** the delivered price goes below zero in 3 half-hours of 2025 (6 Sep, 12:30-13:30) at every site and price list read: 47 price lists over 22 of the 26 sites plus East Grinstead, lowest -£35.79/MWh (Stroud, 11 kV). Four sites had no room in full-grid mode; two hit the Renewables.ninja hourly limit. In the saved 26-site runs (231 point-runs) the battery charges and discharges in the same step only when nothing is imported: surplus renewable output burned through the battery's losses instead of curtailed, which is equally optimal. 2 such steps fall at a below-zero price, none with an import, so no price-driven cycling was seen. The overlap is 2.3-2.5 % of discharge at the lowest-cost and knee points and 9.7 % at the lowest-carbon point: cost and carbon are unaffected, but reported battery throughput and cycles are inflated by that share. Fix not chosen: user's decision (state it; or a tiny penalty on charging so surplus is curtailed instead).
6. Commit with the before/after table in the message or in `docs/SOURCE_DIFF.md`.

---

## Step 6 · Paper wording (no code change needed)

| Item | Sentence for the methods section | Optional code change |
|---|---|---|
| 5. Replacements undiscounted | **Superseded 19 Nov 2026** (`docs/FUEL_CELL_STACK_AND_EQUATIONS_PLAN.md`): the old sentence hid an error, since the fuel-cell stack carried no interest at all, about half its annuity; it is now fixed in code. New sentence: "The fuel-cell stack, the rest of the fuel-cell plant and the gas engines are charged a capital recovery annuity on capacity, less price ÷ life, plus their price at each replacement. At the calendar replacement rate this is exactly the annuity; when running hours wear them out sooner, the extra replacements are charged at their price, within about 2 % (balance of plant) and 9 % (stack, run flat out) of the exact annuity on the shorter life. Electrolyser stack wear is costed per kg made (NESO's variable opex)." | Done in code (`h2_capex.fuel_cell_cost`) |
| 6. Mixed-integer | "The model is a linear program, mixed-integer where the connection tier is chosen (one binary per option); Pareto points are solved to a 10⁻⁷ relative gap (10⁻³ in the quick run)." | Update the "front is exact" docstrings in both files |
| 7. Carbon-price point | "The carbon-price point is the best of the solved Pareto points at £72.27/t." | One extra solve of min (cost + λ × GWP) |
| 8. Simultaneous charge and discharge | If step 5's check finds no negative prices: "The battery may charge and discharge in the same step; this is never optimal because import prices are non-negative." | If prices go negative: a binary, or a penalty on simultaneous flows |
| 9. Bought hydrogen | "Bought hydrogen is delivered without a per-step rate limit." | A delivery cap per step |


---

## Step 7 · Update the equation write-ups

Both write-ups describe the code at ee4a623 and go out of date after steps 1–4.

1. **Docs write-up** ("DC optimiser: model equations"):
   - remove K_o, p_o, c_o, g_o and every offshore term from the objectives, the energy balance, the availability constraints and the `flexible` rule
   - replacements (constraint 5.8): the electrolyser stack's calendar floor becomes 25 years (one stack per plant life)
   - strategy (5.9): `flexible` is off-grid only; grid-connected runs are `free`
   - code check: mark items 1–4 as fixed, with the commit; add the item 8 result from step 5
2. **`docs/model_equations_explorer.html`**: the same changes. Remove Cap_offshore and Offshore(t); update the Repl_ely stack and flexible explanations; remove the code-check notes on fixed items (the wavy underlines).
3. Update the commit reference in both from ee4a623 to the new commit.

**Check.** No equation or term mentions offshore. The explorer's clickable-term test still passes with every symbol explained.

---

## Done when

- [ ] Step 1: `np.ptp` in place; NumPy version pinned; tests pass
- [ ] Step 2: `grep -ri offshore` shows only the "what stays" lines; reference case identical to before
- [ ] Step 3: one-stack floor in place; 3-stack floor kept as a named sensitivity; `ELECTROLYSER_STACKS.md` updated
- [ ] Step 4: no grid + `flexible` rows; configuration count updated where quoted
- [ ] Step 5: full suite passes; before/after table committed; negative-price result recorded
- [ ] Step 6: sentences for items 5–9 in the methods draft
- [ ] Step 7: Docs write-up and explorer match the new code

---

## Not in this plan

- Export stays switched off (`allow_export` raises), which is correct as it stands.
- The optional code changes in step 6 (discounting replacements, a direct carbon-price solve, a hydrogen delivery cap) are left for later. Do them only if a reviewer asks.
