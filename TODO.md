# TODO

Running list of jobs on this study.

It is deliberately not a second copy of `optimisation/DATA_GAPS.md`. That file
is the **register**: every input the study needs, what is known about it, and
why it is or is not closed. This file is the **worklist**: what to actually do
next, and roughly in what order. Items here point at the register rather than
restating it.

**Adding to it:** one line, in whichever section fits, newest at the bottom.
A pointer to the file, module or document that carries the detail is worth more
than a paragraph here.

**Closing an item:** delete the line, and record the outcome in `SOURCES.md`
(provenance), `DATA_GAPS.md` (the register) or `ASSUMPTIONS.md` (scope). Those
three are the durable record and should stay tidy. This file is allowed to be
scruffy.

---

## Blocking a result

Work where a number the study reports is not currently defensible.

- [ ] **Fuel cell capex, and a per-replacement stack cost.** One job, not two —
      a £/replacement figure fixes the duty-versus-calendar asymmetry at the
      same time. Until then the cost axis of *every* hydrogen architecture is a
      ~4× range with a known-direction bias, and cost-optimal builds over-run
      the fuel cell for free. `h2_capex.py`, `fuel_cell.py`, `DATA_GAPS.md`.
- [ ] **SOEC capex/opex.** Currently PEM × 1.2/1.5/2.0 with no source at all.
      Try NESO Green Hydrogen Portal, then IEA. Carbon-only SOEC runs are a
      defensible partial result meanwhile — cost-optimal SOEC is not.
- [ ] **Electrolyser consumables cost.** SOEC's 5.24 kWh/kg external heat and
      0.65 m³/kg water are charged in carbon and free in cost, so the cost
      objective prefers SOEC partly for a reason that does not exist. Also
      check the heat is *available*: at ~800 °C a data centre's own waste heat
      cannot supply it, and nothing tests that today.
- [ ] **Fuel cell BoP replacement is free in cost** (reviewer, 30 Sep).
      Carbon charges `fc_bop_units` = max(calendar, duty); cost charges a
      calendar annuity only, so above 2,400 h/yr the FC line is up to 39 %
      low. Fix is the calendar-anchored increment in
      `docs/REVIEW_RESPONSE_PLAN.md` §1 — independent of the capex sourcing
      above, so do it first. `audit.DUTY_VIA` pools the two replacement
      variables, which is why the audit passed it.
- [ ] **Stack calendar life is `horizon_years`** (reviewer, 30 Sep).
      `dc_model.py:336`. Add `STACK_CALENDAR_LIFETIME_YEARS` (ASSUMED 25,
      sweep 10/15/25); horizon then drives nothing in the LP, so fix or drop
      the UI box. Plan §2.
- [ ] **Tank cost and tank carbon describe different vessels.** Default
      `gandiglio_28bar` is 313 kg stainless/kg H₂ in carbon, but costed at the
      €500–1,040/kg high-pressure range — ~3–10× low on its own shell mass.
      Price it from `steel_kg_per_kg_h2` (Capital Equipment Cost Database).
      Needs a decision on the default design. Plan §3 item 1, §6.3.
- [ ] **Grid carbon is probably 12–21 % high: gas is scored on the wrong
      dataset.** `dc_config.GRID_CANDIDATE_INDEX["GAS"] = 3` picks the GB
      *conventional* gas plant (558 g/kWh) though the query asks for combined
      cycle (candidate #1, 387 g/kWh) — the dataset `SOURCES.md` says we
      refuse. Imports are FR/IE/NL 63/7/30, not ⅓ each. Rebuild the series and
      the 16,132 t baseline. `docs/OBJECTIVE_AUDIT.md` §3.5.
- [ ] **Grid carbon is one hour out of step in BST.** `grid_build.py` (as 3.1 did) writes London local
      time; Elexon and Renewables.ninja are UTC; `profiles.py:343` joins the
      naive stamps, so intraday carbon is an hour late seven months a year.
      Audit §3.5.
- [ ] **The import price carries no levies.** RO/FiT/CfD/CM/AAHEDC ≈ £54/MWh
      plus CCL — about +50 % on the grid-only bill, and it flatters import
      against every on-site asset. `ELECTRICITY_DELIVERED_UPLIFT` cannot reach
      the LP (`profiles.py` never reads `price_timeslices`). Audit §3.5.
- [ ] **Islanded builds pay the grid fixed charge.** `dc_model.py:353` adds
      `cost_grid_fixed_per_year` whatever `assets.grid` is — £271k/yr at
      London, up to £4.67 m. Audit §3.7.
- [ ] **Fuel-cell carbon is a natural-gas micro-CHP.** BoP carries
      fuel-processor kit and 400 km of installer travel; `gwp_fc_maint` is
      reformer-catalyst replacement (~0 for H₂-fed). ecoinvent states 15 y /
      80,000 h (system) and 6 y / 32,000 h (stack); DOE's MW class is 80,000 h,
      not 60,000. Do alongside the FC capex item. Audit §3.4.
- [ ] **Bought grid-connected green is market-based, our own grid electrolyser
      location-based** — 1.50 vs ~13.3 kg CO₂e/kg for the same physical setup,
      which favours buying. State the basis or align them. Audit §3.6.
- [ ] **Wind carbon and yield both flatter wind.** The ecoinvent turbine is a
      20-year inventory amortised over 35–40 y with no replacements (up to
      +73 % on `gwp_wind`); coastal ninja CFs (52–60 %) exceed DESNZ's *net*
      41.3 % high case. Audit §3.1.
- [ ] **Offshore wind runs on the onshore profile** (`dc_model.py:291`),
      undocumented; in the high cost case the LP builds offshore on onshore
      yield. Fetch an offshore series or switch offshore off. Audit §3.1.
- [ ] **`validate.py`'s grid-only benchmark would now fail** (1.85 % vs 0.5 %).
      `validate.py:316-319` and `myopic.py:232-234` pass 7.31 MW as *IT* at
      PUE 1.0 (1.40× Zhang's IT load), and `baseline_grid.run()` still counts
      the genset. Fix before the re-run item below. Audit §3.7.

## Cheap wins

Either the source is named and public, or no new sourcing is needed at all.

- [ ] **Battery embodied carbon is probably 25–35 % high.** BatPaC 5.2 (6.62
      kg/kWh) and EverBatt 2023 (154 Wh/kg, 62.4 kg CO₂e/kWh) both describe a
      current LFP pack ~25 % lighter than the 2016-era ecoinvent pack behind
      `battery.PACK_KWH_PER_KG` (116 Wh/kg → 98.2 kg CO₂e/kWh). Sweep it now;
      proper fix is a BatPaC-BOM foreground. Plan §6.1–6.2.

- [ ] **Sweep the two storage loss terms.** `battery.STANDING_LOSS_PER_HOUR`
      and the tank's leakage are both pinned at zero and push in *opposite*
      directions, so the H₂-versus-battery seasonal result is unbounded rather
      than conservative. The wiring already exists — `battery.py:112` →
      `dc_inputs.py:403` — and `build_tech()` already carries the optional-kwarg
      pattern. `DATA_GAPS.md` states the order (0.1–0.5 %/day) so no source is
      needed to bound it.
- [ ] **CO₂ transport & storage from FES.** £450/tCO₂ in 2025 → £200 long term,
      opex 5 % of capex, stated outright. `h2_prices.py:81` already parses
      sheets CP1/CP2 of the same workbook and holds its GDP rebasing table, so
      this is a third series through a working reader. Needed for SMR-CCS.
- [ ] **Battery fixed opex from BEIS 2022** *Benefits of Long Duration
      Electricity Storage*. Public PDF, and what FES itself routes to. Replaces
      the 2 %-of-capex proxy — the one battery input with no source.
- [ ] **Check Gandiglio et al. 2022 for a tank cost.** It already supplies the
      vessel inventory, so it is the only source that would match the asset
      actually modelled. Twenty minutes; might close H2 tank capex outright.
- [ ] **Report the two big assumed scalars as bands, not points.**
      `green_h2_grid_share` and `transmission_connected` both already have
      override hooks on `build_tech()`. No sourcing — just run the sweep and
      publish the range. The T/D threshold alone swings TDR £270k–£4.67m/year.

- [ ] **Rebuild the *grid connection* transformer from a bill of materials.**
      Done for wind: `transformers.py` now reads a foreground activity built in
      notebook 2 from Leng et al. (2026) Table S1, and no longer touches
      `market for transformer, high voltage use` — which ecoinvent's own comment
      describes as a **280 g** part used "in the information and communication
      technology". `grid_connection.py` is now the last user of it, and the
      argument for keeping it (one shared asset definition) died with the
      rewrite. Leng's own 100 MVA grid-end unit, `XZ11-100000/110` at
      715 kg/MVA, is the obvious basis and is already transcribed in the paper.
      `DATA_GAPS.md`.

- [ ] **Solar's step-up is still the old invented unit.** Wind moved to real
      per-turbine transformers; `solar_pv` did not, because Leng is wind-only.
      It keeps one plant-rated unit on the electronics dataset, ~2× high, with
      no per-inverter-station units — and it is now on a *different basis* from
      wind, which `test_wind_and_solar_are_on_different_transformer_bases`
      pins so it cannot close by accident. IEA PVPS Task 12's 2020 LCI report
      Table 40 is a ground-mount "Inverters + Transformers" bill (20,049 kg per
      MW DC) that explicitly includes step-up transformers; the inverter share
      needs subtracting, since the IEA PVPS solar basis already carries it.
      `DATA_GAPS.md`.

- [ ] **Read NESO's variable opex.** `electrolyser_costs_clean.csv` carries
      `variable_opex_GBP_per_kWh_H2_HHV` — stack replacement and water, PEM
      £0.12/kg — and `h2_capex.electrolyser_costs()` drops it. Audit §3.3.
- [ ] **One price base and one discount-rate policy.** DESNZ is 2023 real and
      never rebased (~6 % low against Modo/EHO 2025); DOE $ and tank € are
      converted at the exchange rate only; the 6 % on H₂ assets has no source,
      and the Green Book 3.5 % marked closed in `DATA_GAPS.md` is used
      nowhere. Audit §4.
- [ ] **Battery: the £100/kWh is not on the cited Modo page** (re-checked
      30 Sep — it gives only "~£400/kW (1h)"), yet it sets 66–75 % of battery
      capex. Also bound duration: an islanded solve builds 42 h of Li-ion.
      Audit §3.2.
- [ ] **Generation cost scope.** DESNZ opex includes the *generator's*
      TNUoS/DUoS (+11.6 % on onshore) for plant behind our meter, and
      excludes land and business rates (~21 % of `cost_wind`). Audit §3.1.
- [ ] **The CO₂ T&S item above would double count.** NESO's ATR+CCS LCOH
      already has a £0.62/kg T&S line and EHO implies ~£0.74/kg — reframe as
      replacing the embedded rate. Grey's central price also carries 2024 ETS
      (~£32/t), not FES CP2 (£78.96/t). Audit §3.6.
- [ ] **Network charge shape.** DUoS uses the "No Residual" class (a data
      centre is Band 1–4) and an unverified Nov–Feb red band (historic LPN is
      all-year 11–14 and 16–19: £6.96 vs £2.05/MWh); TDR is banded on the
      connection ceiling while DUoS bills `cap_grid`; TNUoS HH is a Triad
      charge, not a capacity one. Audit §3.5.
- [ ] **Record SOEC's heat dataset.** 87 % of SOEC's consumables carbon is
      "heat, other than natural gas" [RER]; that choice alone decides SOEC vs
      PEM on renewable power. Audit §3.3.
- [ ] **Tank heel.** `cap_tank` drains to zero; a 1–5 bar minimum for the FC
      feed makes both objectives 4–22 % low per usable kg. Audit §3.3.
- [ ] **Re-fetch the solar series at 20°.** All ten cached series are still
      35°. Audit §3.1.

## Verification and hygiene

- [ ] **EHV band boundaries against DCUSA Schedule 32.**
      `network_charges.EHV_BAND_KVA` came from secondary summaries and has
      never been checked against the primary.
- [ ] **Tidy the duplicate rows in `DATA_GAPS.md`.** Demand-side network
      charges appears as both CLOSED and open; battery opex and electrolyser
      consumables cost each appear twice. The open list should be countable.
- [ ] **Add a wind-operational row to `DATA_GAPS.md`** when that work lands —
      it is not in the register at all yet.
- [ ] **`myopic.evaluate` has drifted from the LP.** No stack cost, no grid
      connection carbon, and no bought-H₂ or export path at all — so the
      no-foresight bracket is wrong for any architecture that buys hydrogen.
      Import the objective from `dc_model`; add a parity test. Plan §3 item 4.
- [ ] **Test fixture double-counts the stack.** `tests/test_dc_model.py:59`
      `cost_fc=194_244` is the pre-split full annuity, used alongside
      `cost_fc_stack_per_mw`.
- [ ] **`dc_runner._coefficient_identity` fingerprints the stale
      `h2_capex.csv`**, not `h2_capex.py`/`fuel_cell.py`, so a coefficient
      change can reuse an old run. Same class: `fuel_cell.decompose()` serves
      lives from its JSON cache, so editing the constants is silently ignored.
- [ ] **Docs: reconcile 118 vs ~250 gCO₂/kWh** (reviewer, 30 Sep). 250 is the
      grid-only *total per MWh of load*, not a grid intensity: 118 (FES,
      national, direct, 2024) → 139 (API London 2025, direct) → 237
      (life-cycle) → 252 (+ facility embodied). Line drafted in plan §4.
- [ ] **Commercial brief: verify every regulatory/market number at source**
      before any investor sees it. Register at `docs/brief_claim_register.md`
      (47 rows, 14 high-risk). Also fix the in-house issues in plan §5:
      "full life-cycle" vs cradle-to-gate, stale worked example, 18.7 MW of
      wind at Westminster, CRU and RICS overreaches.
- [ ] **Re-run `validate.py` and regenerate every doc figure** after the FC
      fixes — `VALIDATION.md` is from 2026-08-24 and the baseline has moved
      (16,014 → 16,132 t).
- [ ] **Two hydrogen tests skip on every run.** `test_dc_model.py:244` (the
      only test of the FC replacement rule) and `:193` (baseload) — the
      fixture never builds a fuel cell or electrolyser. Force the build.
      Audit §5.
- [ ] **The run cache hashes almost nothing.** Beyond the `h2_capex` item
      above: no coefficient module except the four `dc_*.py`, no decomposition
      cache, no `h2_prices_recommended.csv`, no series, and no
      `connection_headroom`. Audit §5.
- [ ] **Unserved load is carbon-free.** A min-GWP solve with any allowance
      sheds the dirtiest hours, and every g/kWh and £/MWh divides by gross
      demand. Audit §3.7.
- [ ] **Stale-docs sweep** — list in audit §6. Includes the "Solar's step-up
      is still the old invented unit" item above, which `DATA_GAPS.md` already
      records as closed.
- [ ] **"Flexible" with a grid is identical to "free"** (`dc_model.py:448-449`),
      so three matrix scenarios are duplicates. Drop it or define it.
      Audit §3.3.
- [ ] **`audit.py` blind spots.** Lifetime agreement can only fail for the
      electrolyser; `NOT_ASSETS` hides unserved and bought H₂; `DUTY_VIA` also
      hides FC maintenance; `cap_batt_e` is never slack-checked. Audit §5.
- [ ] **Compressor capital is partly counted already.** Compressor draw sits
      inside `cap_ely` (4.7 % of SOEC's) and Hermesmann's BoMs list
      compressors, so plan §6.3 option 2 would double count as written.
      Audit §3.3.
- [ ] **Export is broken if anyone switches it on** — credited at demand
      rates, no carbon credit, unbounded with no grid limit, missing from
      `contributions()`. Audit §3.5.
- [ ] **Unverified — check against the papers:** blue's carbon balance
      (~0.9 kg CO₂/kg H₂ unaccounted from SMR-CCS's extra gas; CCS-step diesel
      with no combustion) against Hermesmann, and R134a leakage (~27.5 t/yr if
      Zhang's 450 kg is an emission) against Zhang. Audit §3.6, §3.7.

## Balance of plant not counted

Kit that a build genuinely needs and no coefficient in the study charges for.
All one-directional — every one of these makes an architecture look cleaner
than it is. Checked exchange by exchange against the inventories, so this list
is what is *actually* absent rather than what sounds absent.

- [ ] **Battery enclosure.** `battery.py` is an LFP traction pack plus a
      500 kW inverter and nothing else — no container, racking, HVAC or fire
      suppression, because ecoinvent 3.9.1 has no stationary BESS enclosure.
      Already stated in `SOURCES.md`; needs a source outside ecoinvent, and a
      BESS-container LCA paper is the likely route.
- [ ] **Battery and fuel cell step-up.** `transformers.py` charges the step-up
      on `cap_wind`, `cap_offshore` and `cap_solar` only, but `dis` and `p_fc`
      inject onto the same bus. The battery's PCS is an inverter, not a
      transformer, and ecoinvent's 2 kW PEMFC does carry `inverter, 2.5kW` —
      so both have power conditioning and neither has a step-up. Two more
      coefficients on the same 230.2 kg CO₂e/MW/year basis, no new sourcing.
- [ ] **Hydrogen compressor capital.** `tank_compression_kwh_per_kg` charges
      the electricity to fill the tank in both objectives, and **nothing
      charges the compressor itself** — not its embodied carbon, not its
      capex. Distinct from the parked "hydrogen loading compressor capex"
      below, which is the *seller's* machine for bought hydrogen; this one is
      the study's own, on a tank the LP sizes. `h2_storage.py`.
- [ ] **Hydrogen tank fittings.** Gandiglio's inventory is 15,652 kg of
      chromium steel and nothing else — no valves, piping, instrumentation or
      foundations. Steel dominates a pressure vessel, so this is a bounded
      floor rather than an open question, but it is not zero.
- [ ] **Connection and step-up switchgear.** `grid_connection.py` and
      `transformers.py` both count transformer capital only; switchgear,
      protection, civils and the bay are counted in neither. Same omission
      twice, so one foreground would close both.
- [ ] **Check the data centre's own electrical distribution.** Zhang's
      inventory has twelve non-electricity exchanges and none is discrete
      switchgear, a PDU or a transformer — the facility's power chain is
      whatever the bulk copper, steel and aluminium masses represent. Worth
      confirming against the paper before calling it a gap, since it may be
      deliberate at material-production scope. `baseline_grid.DC_DRIVERS`.

## Parked

No public source found. Revisit if the item becomes load-bearing in a result.

- [ ] **Hydrogen loading compressor capex.** Bought hydrogen now pays trailer
      compression in both objectives, but the **carbon** term is complete while
      the **cost** term is electricity only — no public per-kg figure for a
      hydrogen loading compressor was found, so the seller's compressor capital
      is in neither objective. The cost side is therefore a floor, and a
      residual bias toward buying remains. `h2_prices.bought_h2_compression_gbp_per_kg`.
- [ ] **Road haulage for bought hydrogen.** Compression onto the trailer is
      charged; the journey is not. Distance depends entirely on where the seller
      is, which is the same unanswerable question as `sites.connection_limit_mw`.
      One-directional, and still favours buying.
- [ ] **Turquoise outlet pressure.** Assumed 20 bar, at parity with the other
      thermochemical routes. Molten-media pyrolysis is generally
      near-atmospheric, which would make its compression term 2.3× larger.
      Price this properly before turquoise carries any conclusion.
- [ ] **Transmission connection capital cost.** A grid connection in a floored
      TNUoS zone currently costs £0/MW/year — right as a tariff, wrong as a
      cost, and it flatters exactly the Scottish sites the locational headline
      turns on. Needs a module reading the Connection Charging Methodology, and
      would remove `dc_pareto`'s lexicographic second stage.
- [ ] **DUoS regional coverage.** Only LPN HV Site Specific is transcribed, so
      any distribution-connected site outside London is priced on London
      tariffs. Thirteen DNO charging statements, hand-transcribed, no API.
