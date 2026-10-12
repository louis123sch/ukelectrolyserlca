# Response plan — reviewer feedback of 30 Sep 2026

Covers the four points raised on `DC_Optimiser_Overview.docx` and
`Optimiser_Commercial_Brief.docx`, what a survey of the model found alongside
them, and what the three attached workbooks (BatPaC 5.2, EverBatt 2023, the
Capital Equipment Cost Database) can and cannot do for the cost side.

Line references are to the working tree as of 30 Sep 2026, which has
uncommitted changes.

---

## At a glance

| # | Reviewer point | Verdict | Fix | Effort | Moves a published number? |
|---|---|---|---|---|---|
| 1 | Cost charges stack replacement but not BoP replacement; carbon charges both | **Confirmed** | Charge BoP replacements in cost with one linear rule shared by stack and BoP (§1) | S | Yes, for any fuel cell run above 2,400 h/yr (islanded hydrogen builds). Not the London worked example, which builds no fuel cell |
| 2 | Stack calendar wear is tied to the study horizon, not the stack's own life | **Confirmed** | New `STACK_CALENDAR_LIFETIME_YEARS`, graded ASSUMED, swept (§2) | S | Not at the default horizon of 25 y. Yes whenever the UI horizon is changed, and once a sourced life replaces 25 |
| 3 | 250 vs 118 gCO₂/kWh reads as a contradiction | **Both right, but the 250 is mislabelled** — it is not a grid intensity (§4) | One reconciliation line, plus fixing the phrase "a 250 g grid" | XS | No model change. It does change how the forward-trajectory work must be built |
| 4 | Check the brief's regulatory and market numbers against primary sources | Needed — 47 claims, 14 high-risk, plus 5 internal inconsistencies (§5) | Claim register → primary source per row → correct or cut | M | The worked example is also stale and must be regenerated after §1–§3 |
| — | Attached workbooks | Useful, but narrowly — none closes a blocking gap (§6) | Options ranked in §6 | — | — |

The survey also found **one more defect of exactly the reviewer's kind**: the
hydrogen tank's cost and carbon describe two different vessels (§3, item 1).
Wherever a tank is built, the error is ~3–10× on its cost line, larger per
unit than point 1.

---

## 1. BoP replacement is free in cost (reviewer point 1)

**Evidence.**
- The cost objective charges the fuel cell as `cost_fc * cap_fc + cost_fc_stack_per_mw * fc_stack_units` (`dc_model.py:363-367`).
  - `cost_fc` is the BoP share of capex annuitised on the 25-year calendar life (`h2_capex.py:150-151`). It does not move with duty.
- The carbon objective charges `gwp_fc_bop_per_mw * fc_bop_units` (`dc_model.py:380`), where `fc_bop_units ≥ max(cap_fc/25 y, MWh/60,000 h)` (`:330-334`).
- `fc_bop_units` never appears in the cost objective, in `contributions()` (`:571-572`), or in `myopic.evaluate` (`myopic.py:169-180`).

**Size of the error.**
- BoP duty binds above **60,000 / 25 = 2,400 full-load hours a year** (27 % capacity factor).
- Central case: system capex is £1.795 m/MW, and the stack's share, taken from the LCA split, is 17.2 %.
- At 8,760 h/yr the fuel cell line is £245k/MW-yr where it should be about £403k/MW-yr. That is **39 % understated**.
- The bias runs one way: cost-optimal islanded builds over-run the fuel cell, and hydrogen tipping-point prices are flattered.
- Backup fuel cells are unaffected.

**Why the audit did not catch it.** `audit.DUTY_VIA` (`audit.py:68-70`) pools the two replacement variables, so charging the stack alone passes the parity check.

### The fix — one rule for both replaceable parts

For each component *x* ∈ {stack, BoP}, with capex *Aₓ*, calendar life *Lₓ* and duty life *Hₓ*:

```
nₓ ≥ K_f / Lₓ        nₓ ≥ E_f / Hₓ                                  (unchanged in form)
costₓ = Aₓ·(CRF(r, Lₓ) − 1/Lₓ)·K_f  +  Aₓ·nₓ                         (new)
```

- It is linear. The capacity coefficient is non-negative, and the constraint on *nₓ* keeps the increment non-negative.
- When calendar life binds it gives *Aₓ·CRF·K_f* exactly, so every calendar-bound result is unchanged.
- When duty binds it stays within ±2 % of the exact equivalent annual cost *Aₓ·CRF(r, Hₓ/h)* across effective lives of 2 to 25 years (checked numerically).
- At r = 0 it collapses to the carbon rule, so the two objectives become one formula at two discount rates.

Alternatives considered and rejected:

| Option | Error when calendar binds | Error at 8,760 h | Why rejected |
|---|---|---|---|
| Aₓ·CRF·Lₓ per unit of nₓ | exact | +57 % | A longer assumed calendar life would *raise* the price of running |
| Undiscounted Aₓ per unit (today's stack convention) | −49 % | −20 % | Implies a 0 % discount rate for this one asset |
| **Calendar-anchored increment (above)** | **exact** | **±2 %** | — |

### Rolling it out

**Step 1 — the reviewer's point only.** Bit-identical for every run that does not push the fuel cell past 2,400 h/yr.
- `h2_capex.fuel_cell_costs()`:
  - annuity becomes `A_bop·(CRF + o − 1/L_p)`
  - add a new `bop_GBP_per_MW = A_bop` column
  - read lives from module constants, not from the JSON cache
- `dc_model.Tech`: add a non-defaulted `cost_fc_bop_per_mw`, so a missing value fails loudly rather than defaulting to zero.
- Add `+ tech.cost_fc_bop_per_mw * V["fc_bop_units"]` to the cost objective and to `contributions()`.
- `dc_inputs.build_tech`: wire the new field.

**Step 2 — make stack and BoP consistent.**
- Apply the same rule to the stack, which today is undiscounted A_s/T.
- Put fixed opex on full system capex. Today it sits on the BoP share only (`h2_capex.py:150-151`).
- Effect: **every backup fuel cell rises by £21.1k/MW-yr (+12 %) in the central case** (£5.4k low, £61k high).
- This moves `grid_h2` results and the fuel-cell capex tipping points, so it deserves its own commit and its own note in `ASSUMPTIONS.md`.

**Mirrors that must change with it:**
- `myopic.evaluate` — see §3, item 4
- `fuel_cell.burden_kgco2e_per_year` and its docstring table
- `coefficients.py:136-140`
- the fuel-cell knobs in `thresholds.py:160,167`
- `audit.py:68-70`: check each replacement variable separately
- `dc_runner._coefficient_identity`: it fingerprints the stale `h2_capex.csv` rather than `h2_capex.py` and `fuel_cell.py`
- regenerate `h2_capex.csv` and `tech_lca_coefficients.csv`

**Tests:**
- Fix the fixture. `tests/test_dc_model.py:59` sets `cost_fc=194_244`, the pre-split *full* annuity, which double-counts the stack alongside `cost_fc_stack_per_mw`.
- Add:
  - `test_bop_duty_replacements_reach_the_cost_objective` — islanded fuel cell at 8,760 h
  - `test_calendar_bound_fuel_cell_cost_equals_the_annuity`
  - `test_both_objectives_charge_every_replacement_variable`
  - a coefficient test that the increment stays within 2 % of the exact CRF over 2,400–8,760 h

---

## 2. Stack calendar life is the study horizon (reviewer point 2)

**Evidence.**
- `fc_stack_units ≥ cap_fc / tech.horizon_years` (`dc_model.py:336`, mirrored at `myopic.py:144`).
- The BoP uses its own `fuel_cell.BOP_CALENDAR_LIFETIME_YEARS`. No stack calendar-life parameter exists anywhere: `dashboard_config.py:139-140` has duty lives only, and `coefficients.py:136-140` leaves the stack's calendar field blank.

**The UI makes this worse.**
- The *Horizon (years)* box (`pages/2_Data_Centre_Optimiser.py:222`) says "Amortisation only".
- In the LP, horizon drives **nothing except the stack's calendar rate**. Change it and only the stack moves. At backup duty:

| Horizon | Stack cost | Stack carbon |
|---|---|---|
| 10 y | £30.9k/MW-yr | 9.7 t/MW-yr |
| 25 y | £12.3k/MW-yr | 3.9 t/MW-yr |
| 50 y | £6.2k/MW-yr | 1.9 t/MW-yr |

- `fuel_cell.burden_kgco2e_per_year` defaults the stack calendar to 25 y instead, so it diverges from the LP whenever horizon ≠ 25.

**Fix.**
- Add `STACK_CALENDAR_LIFETIME_YEARS = 25.0` with `STACK_CALENDAR_LIFE_IS_ASSUMED = True` beside `fuel_cell.py:86`, and a non-defaulted `Tech.fc_stack_calendar_years`.
- `dc_model.py:336` then divides by the stack's life, not the horizon.
- 25 reproduces every current default run. It is a placeholder, not a claim.
- **Sourcing:**
  - PEM membranes age at open circuit, so a stack sitting idle as backup does not last 25 years.
  - Look at the DOE stationary and backup-power fuel cell targets, the Clean Hydrogen Partnership SRIA stationary KPIs, and backup-PEMFC manufacturer design lives.
  - Until one is found, sweep 10 / 15 / 25 y and report the band.
- **After the fix horizon drives nothing in the LP.** Either remove the input, or rewrite its help text and reserve it for the multi-period work. Leaving a control that silently does nothing is the same defect in a different place.
- **Cache trap:** `fuel_cell.decompose()` serves its lives from a JSON cache, so editing the module constant is silently ignored until the cache is refreshed. Read lives from constants.

**Docs.** In the Overview:
- eq. (11): n_s ≥ K_f/T becomes n_s ≥ K_f/L_s
- the cost objective gains + c_p n_p
- the notation table replaces T with L_s

Also rewrite `DATA_GAPS.md:63` ("Fuel cell duty cost", which describes the half-fix as if it were the whole fix) and the TODO item.

---

## 3. Survey — other places where cost and carbon price different physics

The reviewer's two points are one class of defect: *the two objectives charge different physics for the same kit.* Every such case biases the Pareto front, because it moves one axis and not the other. A per-asset audit of `dc_model` and `dc_inputs` found these, ranked by likely effect on results:

1. **The tank's cost and carbon describe different vessels.** New, found via the Capital Equipment Cost Database.
   - The default `TANK_DESIGN = "gandiglio_28bar"` is the as-built Ginostra vessel: **312.8 kg of 18/8 stainless per kg H₂**, 1,595 kg CO₂e per kg of capacity.
   - Its cost is `h2_capex.TANK_EUR_PER_KG_CAPACITY` (€500–1,040/kg). That is a literature range for high-pressure compressed tanks, which is roughly what the 100 kg/kg `type1_200bar` design would cost.
   - Priced on its own shell mass, the 28 bar vessel is £1,840–2,850/kg on carbon-steel correlations and **£5,940–6,490/kg as 304 stainless**, before installation. So its cost is **~3–10× low**.
   - Effect: long-duration hydrogen storage looks cheap on the cost axis while being charged as the heavy vessel on the carbon axis.
   - Fix: see §6.3, option 1. Price the vessel from `steel_kg_per_kg_h2`, so one parameter drives both objectives.
   - **Needs a decision:** keep the 28 bar as-built vessel as default (honest to the inventory, and probably fatal to tank storage on cost), or switch the default to 200 bar and add compressor capital (§6.3, option 2).
2. **Fuel cell stack/BoP parity at backup duty** — the +12 % in §1 Step 2.
3. **Electrolyser consumables are carbon-only.** SOEC's 5.24 kWh/kg of heat and its water. Already on `TODO.md`. The cost database does not help; a heat price from the FES gas series does.
4. **`myopic.evaluate` has drifted from the LP.**
   - Its docstring promises "exactly the same coefficients", but:
     - its cost has **no stack term**
     - its carbon omits the grid connection (`gwp_grid_per_mw · cap_grid`)
     - it has **no bought-hydrogen or export path at all**
   - So for any architecture that buys hydrogen, the no-foresight bracket the Overview advertises (§4, "Dispatch") is wrong, not merely loose.
   - Fix: import the objective from `dc_model` rather than restating it, and add a parity test.
5. **Electrolyser is duty-blind in both objectives.** This is symmetric between the objectives, so it does not distort the front, but it flatters baseload in both.
   - The capital inventory is amortised over 160,000 full-load hours (a 73 % capacity factor).
   - So the ≥85 % baseload strategy under-charges carbon by ≥16 %, and no stack replacement is ever charged.
   - The §1 machinery applies directly once a stack/BoP split exists (`DATA_GAPS.md:60`).
6. **Battery has no cycle or throughput limit in either objective.** Symmetric. Modo's 10,000-cycle warranty (≈667 cycles/yr) is not enforced, and fade to 67 % is not modelled. Neither BatPaC nor EverBatt closes this (§6).
7. **Step-up transformer carbon is charged on wind and solar only.** The battery PCS and the fuel-cell inverter inject on the same bus (already on `TODO.md`). The capex-side argument that transformers sit inside DESNZ/Arup capex holds for generation only. It does not hold for the fuel cell (DOE's figure covers power conditioning), is unverified for Modo's battery figure, and leaves `cap_grid` with £0 of capital.
8. **`sizing.py` charges electrolyser capital per kg** (`:306`) but costs it on calendar life (`:275`). This is the 3.5× trap that `electrolysers.py:11-19` warns about, and it affects the Size Optimiser page's verdicts at low capacity factor.

---

## 4. 250 vs 118 gCO₂/kWh (reviewer point 3)

Both numbers are right. They measure four different things, and the docs call the 250 a grid intensity when it is not one.

| Figure | What it is | Scope | Year | Basis |
|---|---|---|---|---|
| **118** | NESO FES 2025, GB grid carbon intensity | national | 2024 | direct (combustion) — confirm the definition in the FES workbook |
| **139** | NESO Carbon Intensity API, the study's own half-hourly series, time-mean | London (region 13) | 2025 | direct, on NESO's per-fuel factors |
| **237** | The model's grid factor: the same half-hourly mix, each fuel scored on its ecoinvent 3.9.1 inventory. Imports are split ⅓ FR/IE/NL, and 3.16 % losses are added | London | 2025 | life-cycle, IPCC 2021 GWP100 |
| **252** (≈250 in the docs) | Grid-only *total* per MWh of load: 237 plus the facility's own embodied burden (~15 g) and the connection | London | 2025 | a whole-system footprint, **not a grid intensity** |

The 237 and 139 are computed from
`custom_grid_lca_outputs/…_r13_…2025….csv`, and the 252 is from
`optimisation_outputs/option_summary.csv`. The docs quote 250.1 from
`VALIDATION.md`, which was built on 2026-08-24 on earlier coefficients.

**Line to add** in the Overview near §7, and as a footnote to the brief's §4 and §11:

> The 118 gCO₂/kWh is NESO's national, direct-emissions figure for 2024. This
> study's London grid in 2025 averaged 139 g/kWh on the same direct basis, and
> 237 g/kWh once every generator is scored on its life-cycle inventory (fuel
> supply chains, plant construction, imports, network losses). The ~250 g/kWh in
> the worked example is the whole grid-only footprint per MWh consumed — that
> life-cycle grid plus the facility's own embodied burden — not a grid intensity.

**And fix the phrase** "a system sized against a 250 gCO₂/kWh grid" (Overview §8, brief §11). It should say "today's grid, 237 g/kWh on a life-cycle basis".

**The consequence for the roadmap matters more than the wording.**
- FES pathways are *direct* intensities. The life-cycle uplift, 98 g/kWh or +70 % here, does not fall to zero with them: wind, solar and nuclear keep their embodied burden.
- So "the grid heads to ~zero by 2050" (brief §11) is overstated for a life-cycle model.
- The forward-trajectory work must take FES **generation mixes** and score them through the same per-fuel inventories, ideally `premise`-projected. It must not drop FES intensities in directly, or the model will mix bases.

**Worth a follow-up check.** Imports are 30 % of London's 2025 mix, scored as ⅓ Ireland and ⅓ Netherlands (both gas-heavy). That assumption probably drives a large share of the 98 g uplift, and a reviewer will ask about it next.

---

## 5. Commercial brief — verification before it goes near an investor (reviewer point 4)

The full register is in `docs/brief_claim_register.md`: 47 rows, each with location, cited source and risk grade.

**Method, per row.**
1. Fetch the primary source.
2. Record the URL, the exact table or quote, the publication date and the date accessed.
3. Grade it Verified / Corrected / Secondary-only / Unverifiable.
4. Fix the text. Anything left Secondary-only or Unverifiable comes out of the executive summary.

**House rules for the rewrite:**
- No secondary citation (law firm, estate agent, trade press, aggregator) for any figure in the executive summary.
- Every regulatory row quotes its operative clause.
- Proposals are labelled as proposals.
- Volatile numbers carry an as-of date: queue sizes, vendor prices, funding rounds.

**The 14 high-risk rows.**
- **Secondary-sourced but load-bearing:** the ~117 "beachhead" projects (Greenberg Traurig), the 86 GW (Knight Frank), the "2037 and beyond" (BCLP), and the £226.5m vs £56.8m power-cost comparison (SMF via a Commons briefing).
- **No source row at all:** the 257 projects of ≥100 MW, the BTM gas price of >US$120/MWh, the US$11–14 m 5 MW run-rate, feasibility studies at 0.75–1.5 % of project cost, and the fab at 400–600 MW.
- **£9.5 m/MW as "Ofgem's own working assumption":** needs the page.
- **£380–430 m of power system:** applies 40–45 % of *hard construction* cost to *total project* capital, so it mixes bases.
- **The regulatory table's wording, rather than its figures:**
  - *RICS WLCA* is mandatory for how a member carries out a whole-life carbon assessment, not a requirement to do one on every project. "RICS already requires embodied carbon" overreaches.
  - *EU Taxonomy 8.1*: check that "life-cycle evaluation of materials" is actually in the annex text.
  - *GHG Protocol Scope 2* is still a draft. "Binding in practice" is our inference and should say so.

**Five things that need no external source, only fixing:**
1. **"Full life-cycle carbon"** (executive summary, §1, §8) contradicts the Overview's cradle-to-gate, no-end-of-life boundary. The brief's own §8 says to phrase it "embodied plus operational from a cradle-to-gate inventory"; the summary does not.
2. **"No way to comply [with the CRU decision] without performing this optimisation."** Untrue: a gas plant sized to import capacity complies with no optimisation at all.
3. **The worked example is stale.** It comes from `VALIDATION.md` of 2026-08-24. The coefficients have changed since: facility decomposition v2 without the genset, transformers, the renewables residual, and bought-H₂ compression. The baseline now reads 16,132 t / 252 g, not 16,014 t / 250 g. Regenerate it after §1–§2.
4. **The worked example builds 18.7 MW of onshore wind and 20.9 MWp of solar at Westminster** (stored run `r13_51.5074_-0.1278_7.31MW_2025_custom`). Say where those renewables are assumed to be (private wire, sleeved PPA, a different site), or use a site where they fit. An investor will ask in the first minute.
5. **The worked-example table mixes units.** Two rows are £/MWh and one is £m/yr.

Many cited items post-date mid-2026, so they need live retrieval rather than recall.

---

## 6. The attached workbooks

**None of the three workbooks closes a blocking gap.** The blocking gaps are:
- fuel-cell capex
- the per-replacement stack cost
- SOEC capex
- electrolyser consumables

What the three workbooks do offer:
- **BatPaC**: a cross-check on the battery's energy cost, and a bill of materials for rebuilding its embodied carbon.
- **EverBatt**: the battery end-of-life that the study excludes.
- **The cost database**: the tank/cost parity defect in §3, and compressor capital.

### 6.1 BatPaC 5.2 (Argonne, released Nov 2024)

**What it is.**
- A bottom-up model of what it costs a manufacturer to build an EV battery pack, from materials to finished pack.
- 28 chemistry pairings, including LFP-graphite in Energy and Power variants. Pouch cells only.
- It rolls up to $/kWh through materials, purchased parts, BMS, labour, energy, overheads, depreciation, profit and warranty mark-ups.
- Open licence (BSD-3 style, UChicago Argonne), so figures can be redistributed with the notice kept.

**What it lacks.**
- **No stationary or grid mode.** The presets are HEV / PHEV / EV only.
- **No dollar year or plant location** is stated.
- It needs Excel's iterative calculation, so it can only feed the model as a pre-computed table.

**LFP results** (recalculated on a scratch copy; the default NMC811 case reproduces the cached $100.92/kWh exactly):

| Case | $/kWh (pack) | Note |
|---|---|---|
| LFP-G Energy, 100 kWh, 50 GWh/yr plant | **98.7** | Cells 78.9; 151 Wh/kg pack, 233 Wh/kg cell |
| Plant 0.5 → 50 GWh/yr | 123 → 99 | Volume sensitivity about ±25 % |
| Pack 25 → 250 kWh | 160 → 85 | Marginal cost ≈ **$75.5/kWh** plus ~$2,300 fixed per pack |
| Power:energy 0.25 → 4 | 98.3 → 100.4 | **Power costs ≈ $0.55/kW inside a pack** |

**Weaknesses of the model that it addresses.**

| # | Option | What it fixes | Effort | Caveats |
|---|---|---|---|---|
| 1 | **Cross-check the £100/kWh energy term** (`battery.py:60-63`). BatPaC's LFP pack at the margin is ≈ £59/kWh, or £77/kWh on average, which leaves £23–41/kWh for container, racking, HVAC, fire suppression, DC cabling and install | Gives the Modo split an independent anchor in `SOURCES.md` | S | US plant, EV pack, no dollar year; volume and size sensitivities of ±25–60 % |
| 2 | **Justify the two-part cost structure.** Power inside the pack costs ~£0.4/kW, so the £300/kW term is almost wholly PCS, transformer, connection and installation | Documents why power and energy are sized separately | S | An argument, not a coefficient |
| 3 | **Rebuild the battery's embodied-energy carbon as a Brightway foreground from BatPaC's LFP bill of materials:** 6.62 kg/kWh (LFP 1.94, graphite ~1.0, Cu 0.51, Al 0.79, steel 0.93 + 0.40 stainless, electrolyte 0.55), plus 42.6 kWh/kWh of factory energy | Replaces the 2016-era ecoinvent EV pack (8.64 kg/kWh, 159 Wh/kg cells) behind today's **98.2 kg CO₂e/kWh**. A naive mass scaling points to ~67, which is indicative only until re-scored. Same pattern as the Smith 2024 solar foreground | M | Still an EV pack with no enclosure. ecoinvent's LFP dataset (Dai et al.) is itself BatPaC lineage, so this is an update, not an independent check. Factory energy is counted wholly as electricity |
| 4 | **Compare its bill of materials with ecoinvent's** | ecoinvent carries 2.5× the electrolyte, 1.9× the copper foil and 2× the separator per kWh. That points to where 98.2 is high | S | — |
| 5 | **Build the battery cost band bottom-up** from plant volume, lithium price and cathode price, instead of the 0.69× / 1.21× survey multipliers | A traceable low/high band | S–M | Moves the energy term only |
| 6 | **Price a cells-only replacement** (cells are 80 % of pack cost), *if* cycle-based replacement is added | See §3, item 6. The §1 `max(calendar, duty)` machinery applies directly (below) | M | Cycle life still comes from Modo |

**It does not address:**
- the enclosure or balance of plant (a carbon gap, since Modo's cost already covers the whole system)
- the PCS or installation
- the 2 % opex proxy
- standing loss or the 88 % round-trip efficiency (BatPaC gives only DC ohmic efficiency)
- degradation (it has no cycle or calendar life at all; its "warranty" is a price mark-up)
- anything grid-scale (warnings fire above 150 kWh per pack and 1,000 V)

**A cheap consequence of §1.** Once the calendar-anchored replacement rule exists, the battery can become the third replaceable part:
- n_b ≥ K_b^E / 15 y, and n_b ≥ discharge MWh / (10,000 cycles × mean capacity).
- Priced at BatPaC's cell share for the replacement.
- It binds only above about 1.8 cycles a day. The London min-cost run does ~313 cycles a year, so the rule mostly guards high-cycling arbitrage builds. This closes §3, item 6 with no new data.

### 6.2 EverBatt 2023 (Argonne, Dai et al.)

**What it is.**
- A cost, energy and emissions model of an EV battery's whole chain: material production, cell and pack manufacturing, collection and transport, disassembly, then pyrometallurgical, hydrometallurgical or direct recycling, and finally cathode re-manufacture.
- Background data is GREET 2022 on AR6 GWP100, which matches the model's IPCC 2021 basis. Grid options are US, CA, CN, KR or user-defined. Costs default to 2020 $.
- BSD-3-style licence.

**Limitations.**
- The workbook **ships blank** (every output is #N/A). Results below come from running a scratch copy in Excel.
- **EV packs only.**
- **LFP is excluded from its closed-loop cathode production and recycled-content modules** ("Results not available for LFP and LMO chemistries").

**LFP numbers (US plant at 50 GWh/yr; recycler at 10 kt/yr).**

| | Value | vs model |
|---|---|---|
| Pack manufacturing GHG | **62.4 kg CO₂e/kWh** (cell 54.3); 154 Wh/kg | Model uses **98.2** at 116 Wh/kg. Per kg the two are only 15 % apart (9.62 vs 11.37). The gap is **specific energy**, and at EverBatt's density the model's own factor gives 73.7 |
| Pack manufacturing cost | $108/kWh (cell $86) | Agrees with BatPaC's $98.7 |
| Collection and transport | $0.93/kg (hazmat packaging $0.59); 0.26 kg CO₂e/kg | — |
| Recycling, hydrometallurgical route | Needs a **$2/kg gate fee paid *to* the recycler** (hard-coded for LFP). Break-even fee $1.88/kg. 0.88 kg CO₂e/kg including transport | LFP end-of-life is a **net cost** to the owner |
| Scale sensitivity | Net hydro cost: $11.3/kg at 2 kt/yr, –$1.1/kg at 50 kt/yr | Dominates everything else |
| Avoided-burden credit (system expansion) | –2.54 kg CO₂e/kg for hydro and direct routes. About 45 % of that is graphite credited at *virgin synthetic* burden | Not compatible with the study's attributional framing |

**The convergent finding from 6.1 and 6.2.**
- BatPaC (6.62 kg/kWh) and EverBatt (6.49 kg/kWh, 154 Wh/kg) both describe a current LFP pack about 25 % lighter per kWh than the 2016-era ecoinvent pack (8.64 kg/kWh).
- So **the battery's embodied carbon is probably overstated by roughly 25–35 %**.
- That biases the carbon objective *against* the battery.
- The two workbooks are not independent of ecoinvent's dataset (all three are Argonne/Dai lineage). But they are *newer* versions of the same lineage, which is the relevant point.

**Weaknesses of the model it addresses.**

| # | Option | What it fixes | Effort | Caveats |
|---|---|---|---|---|
| 1 | **Specific-energy sensitivity on `PACK_KWH_PER_KG`** (116 → 154 Wh/kg): battery carbon 98.2 → ~74 kg CO₂e/kWh | The battery's carbon bias above. Cheapest action on this list | S | Proper fix is 6.1 option 3 (BatPaC-based foreground) |
| 2 | **Battery end-of-life cost adder:** collection plus gate fee ≈ $2.9/kg ≈ **$19–25/kWh at year 15**, i.e. ~$0.9–1.2/kWh-yr annuitised, or 5–10 % of today's energy annuity | Cost side of decommissioning, which the study omits | S | US 2020 $; the gate fee is an assumption; ±5× with recycler scale |
| 3 | **Battery end-of-life carbon, burden only (no credit):** +4.4–7.6 kg CO₂e/kWh (+5–8 %) | Checked in ecoinvent: the retired pack's own end-of-life is *absent* from the pack dataset, not embedded in it | S–M | GREET US grid; can be re-run on a user-defined grid |
| 4 | **Rescore EverBatt's LFP recycling inventory (energy, reagents, recovered masses) in ecoinvent 3.9.1 with GB electricity** | The defensible way to get option 3, without mixing GREET into an ecoinvent study | M | Same route as the Smith PV foreground |
| 5 | Avoided-burden credit (–11 to –14 kg CO₂e/kWh net) | Sensitivity only | S | Conflicts with APOS/attributional; double counts secondary Al/Cu already in APOS; graphite credit inflated; no Li/LFP credit computed |

**The catch: "same footing".**
- `ASSUMPTIONS.md` §6 excludes end-of-life for *every* asset so that all options compare on one boundary.
- Adding it for the battery alone breaks that. Wind decommissioning, and the PGM and titanium value in fuel cells and electrolysers, would stay at zero.
- For example, +6–8 % on 98.2 lifts the battery above the 28 bar tank's 100.7 (`SOURCES.md:781`), flipping a quoted comparison by boundary choice alone.
- **Recommendation:**
  - Report battery end-of-life as a side sensitivity now.
  - Take study-wide cradle-to-grave only as a deliberate L-effort project.
  - Meanwhile, stop the brief calling the carbon "full life-cycle" (§5).

**It does not address:**
- standing loss, auxiliary load or round-trip efficiency
- degradation, cycle life or second life
- the BESS enclosure (its pack assembly energy is zero)
- the inverter or power term
- fixed opex
- current lithium prices (2018–22 averages; lower prices worsen LFP recycling economics)
- end-of-life for any non-battery asset

### 6.3 Capital Equipment Cost Database

**What it is.**
- One sheet with 793 rows of purchased-equipment cost correlations. It was built in 2021 by Townsend & Faber for AssessCCUS (Global CO₂ Initiative).
- The rows are harmonised from four US process-engineering textbooks: Sinnott & Towler 2020, Woods 2007, Turton/Capcost 2017, and Seider 2016.
- Every row has the form cost = C_min·(S/S_min)^SF, escalated by CEPCI. The currency is USD by implication.
- It has no installation factors, no embodied carbon, no lifetimes and no opex.

**Weaknesses of the database itself.**
- **Each textbook correlation has been replaced by a two-point power law through its range ends.** Mid-range this overstates Sinnott & Towler compressors by 1.24–1.46× and vessels by up to 1.76×. That is outside the file's own ±20 % claim, so use the original *a + b·Sⁿ* forms, which back out cleanly: reciprocating compressor 220,000 + 2,300·S^0.75, and vertical carbon-steel vessel 10,000 + 29·S^0.85.
- Several bad rows: row 85 (an axial compressor at $5.9k for 4 MW), row 521, rows 748–750 (exponent 1.23), and rows 651–652 (units).

**What it covers that matters here:**
- pressure vessels priced by shell mass (rows 55–58, 552, 717–718)
- compressors (rows 29, 87, 91–92, 579)
- boilers (row 622)
- ion exchange (row 71)
- pipe (row 143)

**What it does not cover:** electrolysers, fuel cells, batteries, transformers, switchgear, cables, MW-scale power electronics, hydrogen diaphragm compressors, and storage above 7 MPa.

**Options, best first.**

| # | Use | Closes | Effort | Caveats |
|---|---|---|---|---|
| 1 | **Price the tank from its shell mass.** £/kg capacity = C(m_v·`steel_kg_per_kg_h2`)/m_v, with the tank treated as identical vessel modules so it is exactly linear | §3, item 1: tank cost/carbon parity | S | Installation not in the file; stainless vs carbon steel; US Gulf Coast basis; thick-wall 200 bar fabrication understated by a mass basis |
| 2 | **Fold compressor capital into `cost_ely`.** kW of compressor per MW of electrolyser is fixed (PEM→200 bar 21.6; SOEC→28 bar 47.3; SOEC→200 bar 73.1; PEM/AE→28 bar 0). Linearise at a design size and iterate once | TODO "Hydrogen compressor capital". The cost side only | S–M | Process-gas machines, not H₂ diaphragm units; Woods is capped at 7 MPa. Adds £19–109k per MW of electrolyser (1–4 % of SOEC capex). Needs an embodied-carbon counterpart, or it creates a new one-sided term |
| 3 | **Bound the seller's loading compressor** as a £/kg adder in `h2_prices` | Parked TODO item | S | Comes out at £0.007–0.10/kg (0.1–2 % of the green price), so it can be closed as immaterial with a number attached |
| 4 | SOEC steam-raising capex adder (row 622) | Part of SOEC consumables | S | Small (£4–40k/MW). The real fix is a heat *price* and a heat-availability check, which this file does not give |

**Escalation, whichever option is taken.**
- CEPCI → about 800 (2023–24; confirm) → GBP.
- CEPCI is a different route from the FES GDP deflator used elsewhere in the repo, so record that in `SOURCES.md`.
- US→UK location factors and installation (Lang/Hand) factors have to come from the textbooks themselves.

---

## 7. Sequencing

| Phase | Work | Effort | Gate |
|---|---|---|---|
| 0 | Doc wording only: the §4 reconciliation line, "full life-cycle" → "embodied plus operational, cradle-to-gate", the CRU and RICS overreaches, and a "pre-correction" flag on the worked example | ½ day | none |
| 1 | §1 Step 1 + §2 stack calendar + `myopic` parity + audit fix + fixture fix + new tests | 1 day | `pytest` green; `audit.py` reports stack and BoP separately |
| 2 | §1 Step 2 (stack/BoP parity); §3 item 1 tank-from-shell-mass | 1 day | **Decisions:** Step 2 now or with FC capex sourcing? Which tank design is the default? |
| 3 | Re-run `validate.py` and the matrix; regenerate `VALIDATION.md`; update the docx numbers and eq. (11) / cost objective / notation; re-pick the worked-example site | 1 day | 9/9 benchmarks; every doc figure traced to a run ID |
| 4 | Brief verification pass (§5) | 1–2 days | No H-risk row left unresolved in the executive summary |
| 5 | Workbook-driven work (§6), in the order below | per option | — |

**Workbook options, in priority order.**

Tank from shell mass (§6.3, option 1) is already in Phase 2. After that:

1. **Battery specific-energy sensitivity** (§6.2, option 1) and the **BatPaC cost cross-check** (§6.1, options 1–2). S. Surfaces the ~25–35 % carbon bias against the battery, and anchors the Modo split.
2. **Battery as a third replaceable part** under the §1 rule, with BatPaC's cell share as the replacement cost (§6.1, option 6). M. Closes §3, item 6.
3. **BatPaC-based Brightway foreground for battery carbon** (§6.1, options 3–4). M. The proper fix behind item 1.
4. **Compressor capital into `cost_ely`, with an embodied-carbon counterpart** (§6.3, option 2). S–M. Closes a TODO item, and must not become a new one-sided term.
5. **Battery end-of-life as a side sensitivity** (§6.2, options 2–3). S. Then rescore in ecoinvent (§6.2, option 4). M.
6. **Close the loading-compressor parked item with a bound** (§6.3, option 3). S.

**Decisions only you can make:**
- whether §1 Step 2 (+12 % on backup fuel cells) lands now or with the fuel-cell capex sourcing;
- which tank design is the default once its cost is honest;
- whether end-of-life stays excluded study-wide, becomes a battery-only sensitivity, or becomes a cradle-to-grave project;
- who runs the brief verification, which needs live source retrieval.
