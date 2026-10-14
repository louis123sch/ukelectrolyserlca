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

**Carbon side:** every open carbon item is sequenced in `docs/CARBON_PLAN.md`
(14 Oct) — work it from there.

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
      objective prefers SOEC partly for a reason that does not exist (except
      in the electric-boiler scenarios, where the heat is bought power). The heat
      is a gas boiler (Mehmeti 2018, `SOURCES.md`), so a gas tariff ÷ boiler
      efficiency prices it. Availability is no longer a question: bought fuel,
      not the data centre's waste heat (closed on the carbon side 14 Oct).
- [ ] **Tank cost and tank carbon describe different vessels.** Default
      `gandiglio_28bar` is 313 kg stainless/kg H₂ in carbon, but costed at the
      €500–1,040/kg high-pressure range — ~3–10× low on its own shell mass.
      Price it from `steel_kg_per_kg_h2` (Capital Equipment Cost Database).
      Needs a decision on the default design. Plan §3 item 1, §6.3.
- [ ] **The import price carries no levies.** RO/FiT/CfD/CM/AAHEDC ≈ £54/MWh
      plus CCL — about +50 % on the grid-only bill, and it flatters import
      against every on-site asset. `ELECTRICITY_DELIVERED_UPLIFT` cannot reach
      the LP (`profiles.py` never reads `price_timeslices`). Audit §3.5.

## Cheap wins

Either the source is named and public, or no new sourcing is needed at all.

- [ ] **CO₂ transport & storage: replace, don't add.** Blue's price already
      carries T&S — NESO's ATR+CCS LCOH has a £0.62/kg T&S line, EHO implies
      ~£0.74/kg — so adding FES's £450/tCO₂ on top would double count
      (+£3.60/kg). If FES is wanted, swap it for the embedded rate (and check
      whether the £450 is capital, ~£55/t levelised). `h2_prices.py:81`
      already reads CP1/CP2 of that workbook. Also: grey's central price
      carries 2024 ETS (~£32/t), not FES CP2 (£78.96/t). Audit §3.6.
- [ ] **Sweep the fuel cell calendar lives.** Stack 5 / 10 / 15 y (central 10
      since 14 Oct), BoP 15 / 20 / 25 y (central 20). Both indicative, not
      MW-class H₂ warranties; the stack's binds at backup duty and carries
      ~80 % of a backup unit's fuel-cell carbon. Both move cost too. Plan §2.
- [ ] **MW of fuel cell per container** — 1 MW assumed in
      `optimiser_lca/fuel_cell.FC_KW_PER_CONTAINER`; sweep 0.5–2. 3.7 of the
      BoP's 44 t/MW.
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
- [ ] **Tank heel.** `cap_tank` drains to zero; a 1–5 bar minimum for the FC
      feed makes both objectives 4–22 % low per usable kg. Audit §3.3.

## Verification and hygiene

- [ ] **EHV band boundaries against DCUSA Schedule 32.**
      `network_charges.EHV_BAND_KVA` came from secondary summaries and has
      never been checked against the primary.
- [ ] **Docs: reconcile 118 vs ~250 gCO₂/kWh** (reviewer, 30 Sep). 250 is the
      grid-only *total per MWh of load*, not a grid intensity: 118 (FES,
      national, direct, 2024) → 139 (API London 2025, direct) → 159
      (life-cycle, delivered) → 174 (+ facility embodied). The drafted line in
      plan §4 carries these numbers (13 Oct, after the gas, import, delivery
      and grid-solar fixes); what is left is putting it in the Overview and
      the brief, which wait on the figure regeneration below.
- [ ] **Commercial brief: verify every regulatory/market number at source**
      before any investor sees it. Register at `docs/brief_claim_register.md`
      (47 rows, 14 high-risk). Also fix the in-house issues in plan §5:
      "full life-cycle" vs cradle-to-gate, stale worked example, 18.7 MW of
      wind at Westminster, CRU and RICS overreaches.
- [ ] **Regenerate every doc figure** — `validate.py` was re-run on 12 Oct
      after the FC fixes, but the Overview and brief still quote 2026-08-24
      numbers (16,014 t baseline, 6,605 t optimised). The grid-only baseline is
      now 11,114 t/yr at 174 g/kWh after the 13 Oct grid fixes (gas, imports,
      delivery, solar). `validate.py` and `myopic.py` already size Zhang's
      7.31 MW as facility draw at `DC_REFERENCE_PUE` (audit §7 A4 is done).
- [ ] **Stale-docs sweep** — mostly done 14 Oct (code comments, ASSUMPTIONS
      §2/§3/§4/§6, SOURCES facility total, DATA_GAPS solar CFs and Rego).
      Left: the cost-side rows audit §6 lists (NESO LCOH range wording, SOEC
      21.7/12.4 %, network charges listed closed and open) and VALIDATION.md,
      which the figure regeneration below rewrites.
- [ ] **"Flexible" with a grid is identical to "free"** (`dc_model.py:448-449`),
      so three matrix scenarios are duplicates. Drop it or define it.
      Audit §3.3.
- [ ] **Export is refused until it is modelled** (`dc_model.build_model`
      raises since 12 Oct). To build it: credit at an export price, not demand
      rates; give it a carbon credit; add it to `contributions()`. Audit §3.5.

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

**Closed 4 Sep as negligible** — not to be reopened without new evidence:
battery and fuel-cell step-up transformers, connection and
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

