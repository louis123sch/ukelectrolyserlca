# Carbon-side plan — 14 Oct 2026

A plan for closing every open item on the **carbon objective**: the `gwp`
expression in `dc_model.build_model`, the inventories in `optimiser_lca/` that
feed it, and the tools that check it. It is drawn from `TODO.md`,
`optimisation/DATA_GAPS.md` and `docs/OBJECTIVE_AUDIT.md` as they stood on
14 Oct, after the grid work of 13 Oct and the battery, fuel-cell BoP and
grid-intake rebuilds of 14 Oct.

Cost-only items (fuel cell, SOEC and tank capex, levies, discount rates, network
charge shapes) are out of scope here. They are included only where a carbon fix
moves cost through the same constant, as the fuel-cell calendar lives do.

**Closing an item** works as `TODO.md` says: delete the TODO line, and record the
outcome in `SOURCES.md`, `DATA_GAPS.md` or `ASSUMPTIONS.md`. Every phase below
also ends with a test that **pins the new value**. Half the audit's findings were
terms that were exercised but never asserted.

Effort: XS < 1 h, S ≈ half a day, M ≈ 1–2 days, L > 2 days.

---

## At a glance

| Phase | What | Needs sourcing? | Effort | Moves a reported number? |
|---|---|---|---|---|
| 0 | Commit the last two days; fix stale register rows | no | XS | no |
| 1 | Tooling: a sensitivity runner, `myopic` parity, `audit.py` blind spots, unskipped tests | no | M | no, but every later phase depends on it |
| 2 | LP defects: unserved load, leaked H₂, conversion losses | one decision each | S–M | yes, min-GWP runs |
| 3 | Inventory fixes, ranked by size | yes | L in total | yes |
| 4 | Sweeps reported as bands | no | S once phase 1 exists | adds ranges |
| 5 | Regenerate validation, figures and docs | no | M | the published numbers |

Do the phases in order. Phase 1 has to come first because phases 2–4 cannot be
checked without it. Phase 5 is last because every earlier phase moves the
numbers it would publish.

---

## Phase 0 — housekeeping (XS)

1. **Commit.** Nothing has been committed since `15db683` (13 Oct, 14:39). Make
   two commits: the grid work (13 Oct), then the battery, fuel-cell BoP,
   grid-intake transformer and storage-loss sweep (14 Oct, including the untracked
   `optimiser_lca/bess.py` and `optimisation_outputs/storage_loss_sweep.csv`).
2. **Stale register rows.**
   - `DATA_GAPS.md`, *Bought green H₂ supply mix*: the range is 0.976–**1.107**
     kg CO₂e/kg since the 13 Oct delivery fix, not 0.976–1.469.
   - `DATA_GAPS.md`, *dispatch profile vs amortisation load factor*: the 13.96–15.15 %
     solar capacity factors are from the 35° series. Mark them as such until
     phase 5 re-fetches at 20°.
   - `TODO.md`, *Regenerate every doc figure*: `validate.py` already sizes Zhang's
     7.31 MW as facility draw at `DC_REFERENCE_PUE` (`validate.py:311-334`), and so
     does `myopic.py:235`. Check this against audit §7 A4 and drop the "fix it
     first" clause if it holds.
   - `TODO.md`, *Add a wind-operational row*: add the row now, as an open row for
     phase 3.1, rather than waiting.

---

## Phase 1 — tooling first (M)

### 1.1 One sensitivity runner — `optimisation/sensitivity.py` (S)

`thresholds.sweep` finds tipping points by bisection. It does not report a band.
The 14 Oct storage-loss sweep was run ad hoc and has no script in the repo.
Write one:

- `run(case, grid: dict[str, list], objectives=("cost", "gwp")) -> DataFrame`.
  It takes the Cartesian product over `build_tech` keyword overrides, builds the
  series once per case, and writes the totals, capacities and
  `contributions()` to `optimisation_outputs/sensitivity_<name>.csv`.
- Two named reference cases:
  - **`islanded_h2`**: North Norfolk, 100 MW IT, PUE 1.5, 2025, hourly, `res_h2`
    with the battery unlocked. This is the storage-loss reference, the one case
    where every hydrogen asset is built.
  - **`london_grid`**: London, the default grid-connected architecture. This is
    the case the published figures come from.
- **Acceptance:** re-running the storage-loss grid reproduces
  `storage_loss_sweep.csv` to solver tolerance. That becomes the test.

### 1.2 Make the remaining assumed constants overridable (S)

`build_tech` already takes `batt_standing_loss_per_hour`,
`tank_leakage_per_hour` and `green_h2_grid_share`. Add:

- `fc_stack_calendar_years`, `fc_bop_calendar_years`. These feed both the
  replacement constraints and `h2_capex.fuel_cell_costs()`, so the cost and carbon
  sides move together.
- `fc_kw_per_container`. The container is a single exchange inside the BoP
  foreground (`optimiser_lca/fuel_cell.py:456`), so this needs no LCA rebuild.
  Decompose `gwp_fc_bop_per_mw` into a container term and the rest when the
  coefficient is read, then scale the container term by
  `FC_KW_PER_CONTAINER / fc_kw_per_container`. Test that the default reproduces
  today's 44.3 t/MW.
- `batt_usable_fraction` (the ASSUMED 0.90 in `bess.py`). This is a division at
  read time, with no rebuild.

### 1.3 `myopic.evaluate` reads the LP's objective (S)

`myopic.evaluate` (`myopic.py:130`) re-implements the objective by hand. It has
no grid-connection carbon, no bought-H₂ path, and neither leakage term, so the
no-foresight bracket is wrong for any architecture that buys hydrogen.

- Factor the `gwp` and `cost` expressions in `dc_model.py:374-416` into one
  function of `(quantities, series, tech)`. It must be evaluable on solved
  variables **and** on a dispatch DataFrame, so that `contributions()` and
  `myopic.evaluate` both call it.
- **Parity test:** feed the LP's own dispatch to `myopic.evaluate` and require
  both totals to match the LP's within 1e-6 relative error, on every
  architecture in `dc_architectures`.

This has to land before phase 2, which adds objective terms. Otherwise every new
term would need writing twice.

### 1.4 `audit.py` blind spots (S)

From audit §5:

- **`NOT_ASSETS`** hides `unserved` and bought H₂ (`audit.py:85`). Give both a
  coverage check: unserved needs a carbon term after phase 2.1, and bought H₂ needs
  matching cost and carbon streams.
- **`DUTY_VIA`** pools FC maintenance with the replacement variables
  (`audit.py:68`). Check maintenance on its own, because it is charged in carbon
  only.
- **`cap_batt_e`** is never slack-checked. Add it.
- **The lifetime-agreement check** can only fail for the electrolyser, because
  every other pair reads the same constant on both sides. Add pairs for the grid
  connection (40 y) and the transformers (35 y), and make renewables compare the
  carbon amortisation life against the cost annuity life rather than one constant
  against itself.
- The ACCEPTED PV entry and the `foreign` list still name IEA PVPS 2023. Point them
  at Smith 2024.

### 1.5 Unskip the two tests that never run (S)

The tests at `test_dc_model.py:244` (fuel cell replacement rule) and `:193`
(baseload floor) skip on every run, because the synthetic fixture never builds
either asset. Force the build with a lower bound on `cap_fc` and `cap_ely`, and
refresh the fixture to today's coefficients. The fixture still carries
`dc_fixed` 841,457 (v1), `dc_other` 0 and `gwp_solar` 60,600.

---

## Phase 2 — defects in the LP's carbon objective (S–M)

Each item adds or changes a term in the shared objective function from 1.3, so
`contributions()`, `myopic` and `audit` inherit the change automatically.

### 2.1 Unserved load is carbon-free (S, **decision needed**)

A min-GWP solve with allowance *f* sheds exactly *f*, choosing the dirtiest hours
(455.7 against a 236.9 kg/MWh mean on the old grid). Every g/kWh then divides by
gross demand.

- **Recommended:** charge unserved MWh at the life-cycle intensity of what would
  actually carry the load: a **diesel genset**, from ecoinvent's
  `electricity production, diesel, at generator`. That makes shedding a carbon
  *cost*, not a saving, and it matches the genset `ASSUMPTIONS.md` §7 excludes
  from the built assets. The alternative, the half-hour's grid intensity, is
  meaningless for an islanded build.
- Report g/kWh and £/MWh on **served** demand, and rename the page's "Demand
  served" label, which shows gross demand.
- Fix the VoLL comment and `solve()`'s error message. Both say VoLL turns an
  infeasible target into an expensive one, which is true only for f > 0.
- **Test:** a min-GWP solve with f = 1 % sheds nothing it would not shed under
  min cost.

### 2.2 Leaked hydrogen as a greenhouse gas (XS)

The 14 Oct sweep surfaced ~290 t CO₂e/yr (0.46 %) at 0.1 %/day that is in
neither objective. Leakage defaults to zero today, so this is about making a
non-zero default safe.

- New `tech.gwp_h2_per_kg_leaked` = H₂ GWP100 × 1 kg. Use 11.6 (Sand et al.
  2023) or 11 ± 5 (Warwick et al. 2022 for DESNZ). Record whichever is chosen in
  `SOURCES.md`.
- New term: `scale · Σ tank_leakage_per_hour · dt · tank(t-1) · gwp_h2_per_kg_leaked`.
- **Test:** at leakage 0 the objective is unchanged. At 0.1 %/day on
  `islanded_h2` the term matches the CSV's `h2_leak_gwp100_t_per_year_NOT_IN_LP`
  column.

### 2.3 Conversion losses (M)

The LP treats 1 kWh at a generator's terminals as 1 kWh at the data centre.
Imports carry delivery losses (×1.0338 at high voltage), so on-site generation is
flattered.

- Multiply the availability constraints by a step-up transformer efficiency:
  `p_wind ≤ η_tx · cf · cap`, and the same for solar. Take η from Commission
  Regulation (EU) No 548/2014 Annex I: 99.17 % at full load for a 1,000 kVA
  liquid-immersed unit, and a peak efficiency index of 99.724 % at 40 MVA. Use the
  rating that matches each transformer basis.
- Apply the **site's own intake transformer** efficiency to `imp` as well, since
  ecoinvent's delivery chain stops at the high-voltage market. This keeps the
  comparison symmetric rather than just penalising on-site generation.
- About 0.3–0.8 % on generation. It moves both objectives, because more capacity
  is needed for the same load.
- **Test:** with η = 1 the model reproduces today's solve exactly.

### 2.4 Export — leave it refused

`dc_model.build_model` raises if export is switched on (since 12 Oct), and
nothing in the study needs it. No work is planned. The TODO line stays as the
specification for building it, should export ever be wanted.

---

## Phase 3 — inventory fixes, largest first

### 3.1 Wind: life extension and net yield (L) — the largest open carbon item

**3.1a Replacement parts.** The ecoinvent turbine is designed for 20 y with no
replacements and is amortised over 35–40 y. The restated ~5.6 g/kWh sits below
the lowest published wind LCA (~7 g, IPCC AR5). The upper bound, if nothing
lasts past 20 y, is `gwp_wind` +73 % (19,244 → 33,349 kg/MW/yr).

- **Source:** Vestas publishes product LCAs (V136, V150, V162) that itemise
  replacement components over a stated life: gearbox and generator exchanges,
  blade fractions. Transcribe the replacement share as
  `renewables.WIND_LIFE_EXTENSION` (a fraction of nacelle and rotor mass per year
  beyond 20 y) and add it to the capital term.
- **Keep the 35–40 y life.** That was decided on 3 and 7 Sep. Charge what it takes
  to reach that life, rather than shortening it.
- **Acceptance:** the restated g/kWh lands at or above ~7. Report 0 / sourced /
  20-y bound as a band.

**3.1b Net capacity factor.** Renewables.ninja gives a gross single-turbine V90
series: 52–60 % at coastal sites, against DESNZ's *net* high case of 41.3 %.

- Apply one `profiles.WIND_NET_FACTOR` for availability, wake and electrical
  losses, taken from the DESNZ/Arup report's own gross-to-net assumptions, to
  `cf_wind` at load time. Do not cap the series, because that would distort its
  shape.
- This moves cost and carbon together, at exactly the sites the locational
  headline rests on.

**3.1c Offshore is dispatched on the onshore profile** (`dc_model.py:303-304`).
It gets built in the high cost case. Either fetch a ninja offshore series for the
flagged regions, or switch offshore off until one exists. **Recommended:** switch
it off now (XS), and fetch the series later.

### 3.2 Fuel cell stack: test Babatunde against Gramc (M)

Babatunde's 2 kW graphite-plate stack (97 kg CO₂e/kW) is now the largest
fuel-cell term, at ~3–4× an automotive stack, and it carries ~80 % of a backup
unit's fuel-cell carbon.

- Build Gramc et al. 2025 (IJHE 104:623) Table 3, a 48 kW stack, as a second
  foreground `pemfc_stack_1kw_gramc`. Put it on our boundary by stripping their
  end-of-life credits.
- Add `FC_STACK_BASES = {"babatunde_2024", "gramc_2025"}` with a `build_tech`
  override, following the `solar_basis` pattern.
- **Decision after the build:** keep Babatunde as the conservative default, or
  move to the MW-relevant stack. Record the reasoning in `SOURCES.md` either way.

### 3.3 Tank frame and foundations (M)

Gandiglio's inventory is 15,652 kg of chromium steel and nothing else. A 10–20 %
uplift would be 380–770 t CO₂e/yr in the surplus-only run.

- **Route:** build it from first principles. Size a reinforced-concrete pad from
  the vessel footprint (Gandiglio's dimensions plus clearance, 0.5 m thick), and
  add a steel skid at a stated fraction of shell mass. Both are ecoinvent
  exchanges added to `optimiser_lca/h2_tank.py`, flagged DERIVED.
- If a manufacturer's total module mass turns up (McPhy, Hexagon, NPROXX data
  sheets), use it as the cross-check.

### 3.4 R134a leakage at the facility (S)

`optimiser_lca/data_centre.py:156` buys 450 kg of R134a as a product and emits
none of it. If Zhang's 450 kg is a lifetime top-up, then it is the leakage.

- Read Zhang et al. If it is a top-up, add a biosphere exchange of 450 kg
  `Ethane, 1,1,1,2-tetrafluoro-, HFC-134a` to air (GWP100 1,530 in AR6). That is
  ~27.5 t/yr at Zhang scale, ~24 % of the energy group.
- Either way, write the reading into `SOURCES.md`, since the audit flagged it as
  unverified.

### 3.5 Blue hydrogen carbon balance (S)

About 0.9 kg CO₂/kg H₂ from SMR-CCS's extra gas looks unaccounted, and the
CCS-step diesel is linked as a product with no combustion. This is inferred from
stoichiometry and not yet checked against the source.

- Do a carbon mass balance on the Hermesmann SI inventory: gas in = captured +
  vented + in-product. If it does not close, add the missing fossil CO₂ to air,
  and add diesel combustion (ecoinvent `diesel, burned in building machine`
  instead of the bare product). This could raise blue by 11–48 %.
- Add a test that closes the carbon balance within 2 %.

### 3.6 Fossil bought hydrogen on the old grid (S, **decision needed**)

`h2_prices.bought_h2_compression_gco2e_per_kwh` charges grey, blue and turquoise
compression at ecoinvent's 311 g/kWh low-voltage market
(`ECOINVENT_GB_LV_GCO2E_PER_KWH`). That market runs on the conventional gas plant
the grid no longer uses. The inventories' own process electricity links to the
same market.

- **Recommended:** build one `optimiser_lca.grid` foreground, *GB annual-mean
  2025 mix delivered at high voltage*, and relink **both** the compression and
  the inventories' internal GB electricity to it. That way every fossil coefficient
  is on the study's grid, and none is left half-converted.
- Expected: blue's compression term about halves (0.45 → ~0.23 kg/kg). The
  inventory electricity moves by an amount to be measured.

### 3.7 Battery soft spots (S)

- **Cell basis:** add Jasper's 3.11 cell (+20 % on the same bill) as a second
  `bess.py` cell option, swept in phase 4.
- **Usable fraction:** sweep 0.85 / 0.90 / 0.95 via 1.2.
- Voß's own factory energy against Degen's, and the 5 MWh container
  (~−3 kg/kWh): record both as known and directional in `SOURCES.md`. They are
  not worth building.

### 3.8 Bought hydrogen: haulage and turquoise pressure (S each, conditional)

Both favour buying, in one direction only. Do them only if a bought colour is
load-bearing in a result.

- **Haulage:** a distance band of 0 / 100 / 300 km, using ecoinvent lorry
  tonne-km and a tube trailer's ~1 t H₂ per ~40 t gross. This bounds the term
  without an unanswerable seller location.
- **Turquoise outlet pressure:** a 1 bar sensitivity, which makes compression
  2.3× larger.

### 3.9 Small, low priority (S each)

- **Grid-intake transformer at 275/400 kV.** Look for a supergrid transformer
  EPD (Hitachi Energy and Siemens Energy publish them for large power
  transformers). Switch the basis on `transmission_connected`. The whole term is
  ~0.7 % of wind's per-MW burden.
- **Wind transformer factory energy.** Reconcile Leng's published totals (342 t on
  the intake unit) against the materials-only rebuild (~275 t), and add the factory
  electricity on the same footing as solar's (~6 %).
- **Electrolyser stack/BoP split.** No public split exists for Hermesmann's
  monolithic capital good. Bound it instead: stack share 30–50 % of capital, life
  60–90 kh, using the replacement rule `fuel_cell.py` already uses.

### 3.10 SOEC heat availability — close on the carbon side

Since the heat became a gas boiler (Mehmeti 2018), it is bought fuel and not the
data centre's waste heat. Availability holds by construction, and the
electric-boiler scenario buys power. No check is needed on the carbon side.
Close it in `DATA_GAPS.md`, and leave the *cost* of that heat with the cost-side
TODO item.

---

## Phase 4 — sweeps reported as bands (S, needs 1.1 and 1.2)

Run every case through `sensitivity.py` on both reference cases and publish one
table, `optimisation_outputs/sensitivity_carbon.csv`, with a summary in
`VALIDATION.md`.

| Knob | Values | Why |
|---|---|---|
| FC stack calendar life | 5 / **10** / 15 y | binds at backup duty; ~80 % of a backup unit's fuel-cell carbon |
| FC BoP calendar life | 15 / **20** / 25 y | indicative only; +8.3 % on cost at 20 vs 25 |
| kW of fuel cell per container | 500 / **1,000** / 2,000 | 3.7 of the BoP's 44 t/MW |
| FC stack basis | **Babatunde** / Gramc | after 3.2 |
| Battery usable fraction | 0.85 / **0.90** / 0.95 | assumed |
| Battery cell | **Voß** / Jasper 3.11 | after 3.7 |
| Wind life-extension parts | 0 / **sourced** / 20-y bound | after 3.1a |
| Wind net factor | 1.0 / **DESNZ** | after 3.1b |
| `green_h2_grid_share` | 0 / **0.5** / 1 | the weakest bought-H₂ input |
| H₂ tank leakage (with 2.2 charged) | **0** / 0.01 / 0.1 %/day | re-run now that the GHG term is in |

Bold marks the central value. **Acceptance:** for each knob, state whether any
architecture ranking flips at the knee point and at both anchors, as the
storage-loss row in `DATA_GAPS.md` already does.

---

## Phase 5 — regenerate and publish (M)

1. Re-fetch every cached solar series at 20° tilt (the tilt is already in the
   cache key), and update the capacity factors quoted in `DATA_GAPS.md`.
2. Make PUE consistent across entry points. Today the page uses 1.5, the CLI,
   matrix, validate and myopic use 1.0, and audit uses 1.2. Choose one reference
   per purpose and delete `build_tech`'s dead `pue` argument, or make it live.
3. Drop the 32.5 t genset from `baseline_grid.run()`, which the LP excludes.
4. Re-run `validate.py`, rebuild `VALIDATION.md`, and replace the hard-coded
   "£103.09/MWh" with a computed value.
5. Regenerate every figure in the Overview and the brief. Add the reconciliation
   line from `REVIEW_RESPONSE_PLAN.md` §4: 118 national direct → 139 London
   direct → 159 life-cycle delivered → 174 with the facility. Re-quote those
   numbers after phases 2–3, since they will move again.
6. Run the stale-docs sweep in audit §6.

---

## Decisions needed before starting

| # | Decision | Recommendation |
|---|---|---|
| 2.1 | What carbon does an unserved MWh carry? | Diesel genset life-cycle intensity |
| 2.3 | Model conversion losses in the LP? | Yes, on generation **and** the intake, to keep the comparison symmetric |
| 3.1 | Wind: charge life-extension parts, or shorten the life? | Charge parts and keep 35–40 y, per the September decision |
| 3.1c | Offshore without its own profile? | Switch it off until a profile is fetched |
| 3.2 | Default fuel-cell stack | Decide after building Gramc; Babatunde stays meanwhile |
| 3.6 | Fossil bought-H₂ electricity | Relink to an `optimiser_lca.grid` annual-mean foreground |

## Order of work

```
0 → 1.1 → 1.2 → 1.3 → 1.4 → 1.5
          ↓
          2.2 (XS) → 2.1 → 2.3
          ↓
          3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7 → (3.8, 3.9 as needed)
          ↓
          4 → 5
```

Phases 3.4 and 3.5 are mostly reading and can be done in any gap. Phase 3.1 is
the item most likely to change a ranking, so if time is short do it straight
after phase 1.
