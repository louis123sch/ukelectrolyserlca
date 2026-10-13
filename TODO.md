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
      BoP duty reached cost on 12 Oct (plan §1 step 1); step 2 — discount the
      stack the same way and put fixed opex on full system capex — is part of
      this job, since it moves every backup fuel cell (+12 % central).
- [ ] **SOEC capex/opex.** Currently PEM × 1.2/1.5/2.0 with no source at all.
      Try NESO Green Hydrogen Portal, then IEA. Carbon-only SOEC runs are a
      defensible partial result meanwhile — cost-optimal SOEC is not.
- [ ] **Electrolyser consumables cost.** SOEC's 5.24 kWh/kg external heat and
      0.65 m³/kg water are charged in carbon and free in cost, so the cost
      objective prefers SOEC partly for a reason that does not exist. Also
      check the heat is *available*: at ~800 °C a data centre's own waste heat
      cannot supply it, and nothing tests that today.
- [ ] **Tank cost and tank carbon describe different vessels.** Default
      `gandiglio_28bar` is 313 kg stainless/kg H₂ in carbon, but costed at the
      €500–1,040/kg high-pressure range — ~3–10× low on its own shell mass.
      Price it from `steel_kg_per_kg_h2` (Capital Equipment Cost Database).
      Needs a decision on the default design. Plan §3 item 1, §6.3.
- [ ] **Grid imports carry no network embodied carbon.** The grid series is
      generation only (× `MARKET_LOSS_FACTOR` 1.0316); bought green H₂ is
      charged 8.2125 g/kWh network + a 1.0635 loss gross-up
      (`h2_prices.GRID_DELIVERY_*`). Small at London's ~250 g/kWh, but about
      half again on a ~16 g/kWh Scottish grid, and it flatters import against
      on-site assets. Decide one delivery basis for both. `grid_build.score_mix`.
- [ ] **The import price carries no levies.** RO/FiT/CfD/CM/AAHEDC ≈ £54/MWh
      plus CCL — about +50 % on the grid-only bill, and it flatters import
      against every on-site asset. `ELECTRICITY_DELIVERED_UPLIFT` cannot reach
      the LP (`profiles.py` never reads `price_timeslices`). Audit §3.5.
- [ ] **Fuel-cell carbon is a natural-gas micro-CHP.** BoP carries
      fuel-processor kit and 400 km of installer travel; `gwp_fc_maint` is
      reformer-catalyst replacement (~0 for H₂-fed). ecoinvent states 15 y /
      80,000 h (system) and 6 y / 32,000 h (stack); DOE's MW class is 80,000 h,
      not 60,000. Do alongside the FC capex item. Audit §3.4.
- [ ] **Wind carbon and yield both flatter wind.** The 35–40 y life is
      deliberate (DESNZ lifespans, chosen 3 and 7 Sep) — keep it. What is
      missing is the carbon of the replacement parts an ecoinvent turbine,
      designed for 20 y with none, needs to last that long: the restated
      figure (~5.6 g/kWh) sits below the lowest published wind LCA (~7 g,
      IPCC AR5), as the 3 Sep bought-green work already noted. Separately,
      coastal ninja CFs (52–60 %) exceed DESNZ's *net* 41.3 % high case.
      Audit §3.1.

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
- [ ] **CO₂ transport & storage: replace, don't add.** Blue's price already
      carries T&S — NESO's ATR+CCS LCOH has a £0.62/kg T&S line, EHO implies
      ~£0.74/kg — so adding FES's £450/tCO₂ on top would double count
      (+£3.60/kg). If FES is wanted, swap it for the embedded rate (and check
      whether the £450 is capital, ~£55/t levelised). `h2_prices.py:81`
      already reads CP1/CP2 of that workbook. Also: grey's central price
      carries 2024 ETS (~£32/t), not FES CP2 (£78.96/t). Audit §3.6.
- [ ] **Sweep the fuel cell stack calendar life 10 / 15 / 25 y.** It is now
      `fuel_cell.STACK_CALENDAR_LIFETIME_YEARS` (ASSUMED 25, a placeholder) and
      no longer the horizon. Then look for a source: DOE backup-power targets,
      Clean Hydrogen Partnership SRIA, manufacturer design lives. Plan §2.
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
      `optimiser_lca/stepup_transformers.py` from Leng et al. (2026) Table S1, and no longer touches
      `market for transformer, high voltage use` — which ecoinvent's own comment
      describes as a **280 g** part used "in the information and communication
      technology". `grid_connection.py` is now the last user of it, and the
      argument for keeping it (one shared asset definition) died with the
      rewrite. Leng's own 100 MVA grid-end unit, `XZ11-100000/110` at
      715 kg/MVA, is the obvious basis and is already transcribed in the paper.
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
- [ ] **Network charge shape.** DUoS uses the "No Residual" class (a data
      centre is Band 1–4) and an unverified Nov–Feb red band (historic LPN is
      all-year 11–14 and 16–19: £6.96 vs £2.05/MWh); TDR is banded on the
      connection ceiling while DUoS bills `cap_grid`; TNUoS HH is a Triad
      charge, not a capacity one. Audit §3.5.
- [ ] **Decide SOEC's heat dataset.** 87 % of SOEC's consumables carbon is
      "heat, other than natural gas" [RER], kept because Hermesmann's inventory
      uses it — not a study choice, and it can change. It alone decides SOEC vs
      PEM on renewable power (2.27 vs 0.89 kg/kg; 0.22 on zero-burden heat).
      Pick a basis for the ~800 °C heat a site would actually buy. `SOURCES.md`.
- [ ] **Tank heel.** `cap_tank` drains to zero; a 1–5 bar minimum for the FC
      feed makes both objectives 4–22 % low per usable kg. Audit §3.3.

## Verification and hygiene

- [ ] **EHV band boundaries against DCUSA Schedule 32.**
      `network_charges.EHV_BAND_KVA` came from secondary summaries and has
      never been checked against the primary.
- [ ] **Add a wind-operational row to `DATA_GAPS.md`** when that work lands —
      it is not in the register at all yet.
- [ ] **`myopic.evaluate` has drifted from the LP.** Stack and BoP costs
      were added on 12 Oct, but there is still no grid connection carbon and no
      bought-H₂ path at all — so the no-foresight bracket is wrong for any
      architecture that buys hydrogen. Import the objective from `dc_model`;
      add a parity test. Plan §3 item 4.
- [ ] **Docs: reconcile 118 vs ~250 gCO₂/kWh** (reviewer, 30 Sep). 250 is the
      grid-only *total per MWh of load*, not a grid intensity: 118 (FES,
      national, direct, 2024) → 139 (API London 2025, direct) → 237
      (life-cycle) → 252 (+ facility embodied). Line drafted in plan §4.
      Since the gas fix (13 Oct) the life-cycle figure is 188, not 237, and
      the grid-only total 203 g/kWh, not 252: update the drafted line.
- [ ] **Commercial brief: verify every regulatory/market number at source**
      before any investor sees it. Register at `docs/brief_claim_register.md`
      (47 rows, 14 high-risk). Also fix the in-house issues in plan §5:
      "full life-cycle" vs cradle-to-gate, stale worked example, 18.7 MW of
      wind at Westminster, CRU and RICS overreaches.
- [ ] **Regenerate every doc figure** — `validate.py` was re-run on 12 Oct
      after the FC fixes, but the Overview and brief still quote 2026-08-24
      numbers. Best done after the gas-dataset fix, which moves the baseline.
- [ ] **Unserved load is carbon-free.** A min-GWP solve with any allowance
      sheds the dirtiest hours, and every g/kWh and £/MWh divides by gross
      demand. Audit §3.7.
- [ ] **Stale-docs sweep** — list in audit §6. Also the solar capacity
      factors quoted in `DATA_GAPS.md` (13.96–15.15 %), which are from the old
      35° series; new runs already fetch 20° (tilt is in the cache key).
- [ ] **"Flexible" with a grid is identical to "free"** (`dc_model.py:448-449`),
      so three matrix scenarios are duplicates. Drop it or define it.
      Audit §3.3.
- [ ] **`audit.py` blind spots.** Lifetime agreement can only fail for the
      electrolyser; `NOT_ASSETS` hides unserved and bought H₂; `DUTY_VIA` also
      hides FC maintenance; `cap_batt_e` is never slack-checked. Audit §5.
- [ ] **Export is refused until it is modelled** (`dc_model.build_model`
      raises since 12 Oct). To build it: credit at an export price, not demand
      rates; give it a carbon credit; add it to `contributions()`. Audit §3.5.
- [ ] **Unverified — check against the papers:** blue's carbon balance
      (~0.9 kg CO₂/kg H₂ unaccounted from SMR-CCS's extra gas; CCS-step diesel
      with no combustion) against Hermesmann, and R134a leakage (~27.5 t/yr if
      Zhang's 450 kg is an emission) against Zhang. Audit §3.6, §3.7.

## Balance of plant not counted

Kit that a build genuinely needs and no coefficient in the study charges for.
All one-directional — every one of these makes an architecture look cleaner
than it is. Checked exchange by exchange against the inventories, so this list
is what is *actually* absent rather than what sounds absent.

- [ ] **Hydrogen compressor capital — cost side only.** Its carbon was judged
      negligible on 4 Sep (~12.8 t CO₂e per 300 kW unit, 0.01 % of the tank);
      its £ is still open. Check before adding anything: compressor *power*
      already sits inside `cap_ely` (4.7 % of SOEC's, priced at electrolyser
      rates) and Hermesmann's bills list compressors, so plan §6.3 option 2
      would double count as written. Distinct from the parked seller-side
      loading compressor below. `h2_storage.py`, audit §3.3.
- [ ] **Hydrogen tank frame and foundations.** Gandiglio's inventory is
      15,652 kg of chromium steel and nothing else. Valves and piping are
      small, but on 4 Sep the skid, frame and foundations were judged worth
      chasing — a 10–20 % uplift was 380–770 t CO₂e/yr in the surplus-only
      run. No paper itemises it; the two routes are a manufacturer's total
      module mass, or a concrete pad sized from first principles.

**Closed 4 Sep as negligible** — not to be reopened without new evidence:
battery enclosure, battery and fuel-cell step-up transformers, connection and
step-up switchgear, and the data centre's own electrical distribution.
Sized against the North Norfolk 100 MW run, all of them together are at most
~1.6 % of total carbon at the knee point and under 0.2 % at minimum cost, so
none can move a ranking. Recorded in `DATA_GAPS.md` on 12 Oct.

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

