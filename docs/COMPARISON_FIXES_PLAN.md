# Fixes from the Rozzi, Viole and Terlouw comparisons: plan

Drafted 20 Nov 2026. Branch `source-update`, folder `C:\Users\ls1524\Desktop\ukdclca-sources`.

**In short:** electrolyser stacks get charged in cost, the electrolysers move to a 2026 build, solar output
is reduced for panel ageing, two inputs join the ×0.5/×1.5 tests, and some presentation and wording
fixes. Nothing runs until the user gives the word. No solving on the laptop. Commit only when asked.
Nothing on `main`.

Findings behind this plan:
- `Claude outputs/rozzi_cost_comparison.md` (cost inputs against Rozzi 2024; Danish Energy Agency check)
- `Claude outputs/viole_inventory_comparison.md` (inventories against Viole 2024)
- the Terlouw (OPTIMES) review of 19 Nov 2026, whose fuel-cell stack fix is already done (`5a1e262`)

## Status, 20 Nov 2026

Implemented on `source-update`, not committed. Stage 1 done: 22 new tests in `tests/test_comparison_fixes.py` pass; the quick tests pass except the cost map, which is stale until a run with the new model (it was already stale: it still shows offshore wind). Membrane at 6,185 h: +£29.3k per MW a year (+9.1 %), slightly under the £31k estimate because the 2026 build is about 4 % cheaper. Coefficient table rebuilt, explainer rebuilt and copied to OneDrive, methods doc updated (sections 2.5, 4, 5.2, Tables 1 and 3, an author note). Lowest grid price: below zero in 3 half-hours at every site; result and the open choice in `docs/CODE_CHECK_FIX_PLAN.md` step 5. Stage 2 (cluster before/after at East Grinstead) waits for the user.

## Decisions (user, 20 Nov 2026)

| Question | Decision |
|---|---|
| Electrolyser stack share | Danish Energy Agency *Renewable Fuels* sheets (Aug 2026); Rozzi 2024 as cross-check; BEIS 2021's 60 % not used |
| Stack life on the cost side | 50,000 h for every type, the same as the carbon side; Danish lives stated as a limitation |
| Solar ageing | Reduce solar output by the life-average factor, 0.87 |
| Wind ageing | **No** |
| Build year | Move the membrane and alkaline electrolysers to the **2026** build |
| Fuel cell's low case (cheap plant, maintenance costed for a dearer one) | No fix: the new ×0.5/×1.5 test on fuel-cell maintenance covers it; state the mismatch |
| Test the electrolyser stack's factory electricity | **No** (sourced; stays in under the cut-off rule) |
| Build interest on each replacement (Rozzi finding 6) | Keep the 19 Nov fuel-cell formula; one sentence in the methods |
| Electrolyser insurance overlap | State it (at most 0.23 % of capital a year); no change |
| Battery round-trip efficiency (88 % against Rozzi's 85.5 %) | Noted only |

---

## The changes

### 1 · Electrolyser stacks charged in cost

**Why.** The cost side pays nothing for stack replacements; the carbon side replaces a stack every
50,000 running hours. NESO's per-kg figure is 0.9 % of capital a year spread over 7,884 h, the same
0.9 % NESO uses for gas reforming, which has no stacks. The Danish Energy Agency, one of NESO's named
sources, says its fixed running cost excludes stack replacement (note P on every electrolyser sheet)
and prices no water (note Q).

**Figures.** Danish sheets, 2025 central column, "hereof electrolyser stack" over "specific investment"
(installed, the same scope as NESO's capital):

| Type | Stack share | Sheet |
|---|---|---|
| Membrane | 311.96 / 1,765.27 = 17.7 % | 80 PEMEC 100 MW |
| Alkaline | 177.31 / 1,254.04 = 14.1 % | 80 AEC 100 MW |
| Solid oxide | 387.73 / 2,959.14 = 13.1 % | 80 SOEC 10 MW |

Cross-check: Rozzi's 35 % is a share of equipment; at the Danish 61 % equipment share that is about
21 % of an installed price.

**Files.**
1. `optimisation/h2_capex.py`
   - the Danish stack shares as constants, and `ely_stack_cost_fraction(tech)`;
   - NESO's rule as constants (0.009 of capital a year over 7,884 h) and a per-kg helper;
   - membrane and alkaline per-kg figure relabelled "water and consumables" (number unchanged);
   - solid oxide: the government annex's per-kg stack figure replaced by NESO's 0.9 % rule on solid
     oxide's own price, so its stacks are not charged twice;
   - docstrings that call NESO's figure "stack replacement and water" corrected.
2. `optimisation/dc_inputs.py`
   - `T.cost("cost.electrolyser.stack_cost_fraction", …)`, using the returned value so pushes move it;
   - `cost_ely` split as the fuel cell is: (1−s)·f·CRF(25) + s·(f·CRF(Ls) − 1/Ls) + fixed + insurance
     and rates, then × the existing `electrolyser.stack_share` and × `to26`, as today;
   - `cost_ely_stack_per_mw` = price × 1000 × s, × the same two factors;
   - variable name `stack_cost_frac` (`stack_share` already means the stack's share of the
     electricity);
   - when stacks last the plant's life, the total equals today's cost exactly.
3. `optimisation/dc_model.py`
   - field `cost_ely_stack_per_mw: float = 0.0`;
   - "electrolyser" cost term = `cost_ely·cap_ely + cost_ely_stack_per_mw·ely_stack_units`;
   - running-cost term renamed "electrolyser water and consumables"; old name kept in `CHAINS` so saved
     runs still read; matching labels in `scripts/build_cost_map.py` and `scripts/workbook_layout.py`.
4. `optimisation/sensitivity.py`: `cost.electrolyser.stack_cost_fraction` ×0.5/×1.5 in `SHAKY_KNOBS`
   (8.9–26.6 % for membrane, covering Rozzi's ~21 %).
5. `optimisation/audit.py`: close "ely_stack_units moves carbon but not cost", text kept for history.
6. Documents: `docs/ELECTROLYSER_STACKS.md` (contradicts itself today), `optimisation/SOURCES.md`
   (dated section), `optimisation/DATA_GAPS.md` ("stacks and water from NESO"); the source register
   carries `dea_renewable_fuels_2026` (add it if missing).

**Stated limitation.** Danish stack lives are 60,000 h (membrane), 70,000 h (alkaline) and 25,000 h
(solid oxide); the model uses 50,000 h for all three, so solid oxide's stacks are replaced about half
as often as they should be.

**Expected effect.** Membrane at about 6,200 h a year (islanded lowest-cost design): about +£31k per MW
a year, roughly +9 % on the electrolyser line. Nothing changes below about 2,000 h a year.

### 2 · 2026 build for the membrane and alkaline electrolysers

- Read NESO *FES 2025 Economics Inputs* v2, sheet H.01: if it has a 2026 build column, use it (as sheet
  H.02 does for solid oxide).
- If not, a straight line between NESO's 2025 and 2030 figures, stated as such in `SOURCES.md`.
- `optimisation/h2_capex.py` (around `:538`, `:629`) and `optimisation/dc_inputs.py:940`.
- Expected effect: electrolyser capital about 3–4 % lower (about £1,924/kW membrane, £1,682/kW alkaline
  on the straight line). Fixed and variable costs follow, since they are shares of capital.

### 3 · Solar ageing

- Solar output never falls over its 38-year life today, while its cost and carbon are spread over 38
  years. Wind is unchanged (decision above).
- New traced input `solar.life_average_output_factor` = 1 − 0.007 × (38 − 1) / 2 = **0.870**: Smith 2024's
  0.7 % a year (`docs/source_ledgers/smith_2024.md:498`), linear, over the 38-year life
  (`tech_costs.py:100`). Applied where the solar profile enters the model.
- Recorded in `SOURCES.md`, and the new line in `DATA_GAPS.md` closed with it; wind ageing stated as a
  limitation there.
- Cited figure: no ×0.5/×1.5 test.
- Expected effect: solar about 15 % dearer and higher-carbon per unit delivered.

### 4 · Two new ×0.5 / ×1.5 tests (`SHAKY_KNOBS`)

- `cost.h2_tank.capex_per_kg`: the low case is only 14 % below central; ×0.5 (about £308/kg) sits by
  Rozzi's large low-pressure tanks.
- `cost.fuel_cell.maintenance_per_kW_year` (or the traced name it carries): about three times Rozzi's
  and untested. This also covers the low case's mismatch, which is stated rather than fixed.
- With the stack share from change 1, the screened-input test gains six runs per case.

### 5 · Presentation, checks and wording (no change to results)

1. **Coefficient table.** `optimisation/coefficients.py:134` still says "three stacks per unit life";
   split the electrolyser into "plant" and "stack per replacement" and rebuild
   `optimisation_outputs/tech_lca_coefficients.csv`.
2. **Battery cycling warning** in `optimisation/audit.py`: warn when a run's cycles a year are well above
   the assumed 180 (`battery.py:384-387`) or reach the 10,000-cycle limit.
3. **Lowest grid price.** One pass over `grid_price_per_mwh` for every site and window in the sweep
   (`docs/CODE_CHECK_FIX_PLAN.md` step 5). Never below zero: same-hour battery charging and discharging
   is harmless and gets the sentence in that plan's step 6. Below zero: report before choosing a fix.
4. **Methods doc**, author notes and three sentences:
   - platinum drives both hydrogen stacks, and the ecoinvent version used (allocation at the point of
     substitution, `ASSUMPTIONS.md` §6) scores it higher than the cut-off version Terlouw and Viole use;
   - each replacement carries the first build's financing, which errs high by about 2 %;
   - electrolyser insurance may overlap NESO's fixed cost by at most 0.23 % of capital a year.
   Plus which results must re-run.
5. **Water.** `DATA_GAPS.md`: Gerloff's 88 kg of softened water per kg of hydrogen (`optimiser_lca/hydrogen.py:675,771,865`)
   is probably cooling water and must be checked before any water-use result is reported.

---

## Testing

### Stage 1 · Laptop, no solving

Existing quick tests, all passing with no warnings: `test_dc_model`, `test_coefficients`, `test_audit`,
`test_sweep_push`, `test_cost_map`, `test_workbooks`, `test_model_explainer`, `test_equations_page`,
`test_cost_exclusions`.

New tests:

| Change | Test |
|---|---|
| Electrolyser stacks | Stacks lasting the plant's life: cost unchanged to the penny. At 6,185 h a year, membrane +~£31k per MW a year. Solid oxide's stack charged once only. |
| Build year | Membrane and alkaline price = NESO 2026 (or the straight-line value); nothing else moves. |
| Solar ageing | Solar output in the model = profile × 0.870; solar's cost and carbon per MW unchanged; per unit delivered up by 1 / 0.870. Wind unchanged. |
| New tests | Each new push key exists in the trace and moves its figure by exactly ×0.5 and ×1.5. |
| Coefficient table | Plant + stack rows add up to what the optimiser charges at a given number of running hours. |
| Battery warning | Fires on a made-up run at 400 cycles a year; silent at 180. |

Hand checks: the electrolyser's yearly cost line before and after at 2,000 and 6,185 h a year, against the
figures above. Then rebuild the model explainer, run its link check, copy it to
`OneDrive - Imperial College London/DC optimiser/report exorts/model explainer.html`. Run the lowest-grid-price
pass and record the result.

### Stage 2 · Cluster, East Grinstead (site 23), on the user's word

Before/after over the same configuration list as the fuel-cell fix check; "before" = `5a1e262`.

- Configurations with no electrolyser and no solar: identical to the last digit. Anything else: stop and look.
- Electrolyser designs: the bill moves by about electrolyser MW × the expected figure (up at high running
  hours, down 3–4 % on capital where hours are low). Report any design that changes size or technology at
  the lowest-cost, middle and lowest-carbon points.
- Solar designs: expect less solar or a shift to wind, battery or grid; report how much at each point.
- Carbon unchanged wherever the design is unchanged.
- Full test suite (`pytest -q`) as one small job.

Write-up in `docs/SOURCE_DIFF.md`; close the `DATA_GAPS.md` rows with the figures; rebuild the maps and
workbooks from the new run; rebuild the explainer.

### Stage 3 · Later, the user's decision

These changes void the last sign-off. The screened-input test (now with six more runs per case), the
hourly sign-off, and the 26-site and four-site studies are best re-run once, after this.
