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

**Cost side:** every open cost item is sequenced in `docs/COST_PLAN.md`
(28 Oct), grid connection first — work it from there. The items themselves are
lines here like any other.

---

## Blocking a result

Work where a number the study reports is not currently defensible.


- [ ] **Government cost figures: built 4 Nov, to finish** (`docs/COST_GOV_FIGURES_PLAN.md`, *Built*). After the
      connection sweeps end: regenerate `h2_prices_recommended.csv` (the deflator moved), rebuild and
      republish both maps, re-run the reference cases and one ±50 % connection case on the new costs,
      and rule 3 of the cost cut-off (`python -m optimisation.sensitivity cost_cutoff`).
- [ ] **Major-hazard compliance as a step charge** (4 Nov). HSE's per-site figures are in hand
      (`cost_exclusions.py`); charging them on tonnes held needs an on/off switch in `dc_model`.
- [ ] **Best-source build: finish the runs** (4 Nov, evening; `docs/COST_BEST_SOURCE_PLAN.md`, *Built*). Code and
      records done; `cost_cutoff` and `assumptions` run overnight 4/5 Nov on the new costs (results in the
      plan's *Built*); left: the ±50 % connection test at North Norfolk (`norfolk_150_room`, started 5 Nov
      on the pruned lists) and its judge, and both maps republished.
- [ ] **Finish the one price base** (4 Nov). Network charges, levies and connection prices are 2026/27 money,
      wholesale 2025, the rest real 2025.
- [ ] **Wind and solar's own grid connection inside capital** (4 Nov). DESNZ's "infrastructure" (£303/kW, £112/kWp) runs
      to the nearest grid point; behind our meter some is still needed. May overstate; no figure splits it.

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
- [ ] **Report the two big assumed scalars as bands, not points.**
      `green_h2_grid_share` and `transmission_connected` both already have
      override hooks on `build_tech()`. No sourcing — just run the sweep and
      publish the range. The T/D threshold alone swings TDR £270k–£4.67m/year.

- [ ] **One price base and one discount-rate policy.** DESNZ is 2023 real and
      never rebased (~6 % low against Modo/EHO 2025); DOE $ and tank € are
      converted at the exchange rate only; the 6 % on H₂ assets has no source,
      and the Green Book 3.5 % marked closed in `DATA_GAPS.md` is used
      nowhere. Audit §4.
- [ ] **Network tariffs over the asset's life** (28 Oct). Every charge is
      FY2025/26, applied to a connection annualised over 40 y. Run NESO's
      five-year TNUoS forecast as a sensitivity. `COST_PLAN.md` §1.7.
- [ ] **Decommissioning and insurance, like for like** (28 Oct). Check which
      cost sources carry them (DESNZ generators believed to; H₂ assets are bare
      capex + an opex %). `COST_PLAN.md` §4.3.

- [ ] **Third source read, 23 Oct 2026** (`docs/SOURCE_RECHECK_2026-10-23.md`, *Outcome*):
      every finding decided and done by 26 Oct; the stale-docs list at its foot is left.

## Verification and hygiene

- [ ] **Power factor and reactive charges** (28 Oct). PF 1.0 everywhere; the
      DUoS reactive rate is transcribed and never used. State it as an
      assumption unless a source puts a data centre well below 1.
- [ ] **Decide: is connection lead time in scope?** (28 Oct). The binding GB
      constraint on new data centres, and not a £/MW. Either model it (a cost
      of waiting, bridging on on-site generation) or state it out of scope.
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
- [ ] **Cost map: fill the source links** (30 Oct). Most of the 53 entries in
      `optimisation/source_register.py` have no public URL — the code only
      ever recorded NESO's, Elexon's and Modo's. Add each document's address
      as it is re-read; the map's Sources tab lists the gaps. Also hold each
      register entry to a `SOURCES.md` row (`docs/COST_MAP_PLAN.md`).

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
- [ ] **Battery and fuel-cell step-up transformers — cost side** (28 Oct).
      Carbon since 15 Oct; no cost line. Check whether Modo's £/kW already
      includes the transformer (probably) and the fuel-cell proxy (equipment,
      not installed — probably not). `COST_PLAN.md` §2.3.

**Closed 4 Sep as negligible** — not to be reopened without new evidence:
connection and step-up switchgear, and the data centre's own electrical
distribution (inside the PUE). Sized against the North Norfolk 100 MW run,
together under ~1.6 % of total carbon at the knee point and under 0.2 % at
minimum cost. The battery and fuel-cell step-up transformers were closed with
them and are **modelled since 15 Oct** — carbon per MW of `cap_batt_p` and
`cap_fc`, losses in the LP (`transformers.py`, `conversion_losses.py`) — so
the bound now covers only what is left. Recorded in `DATA_GAPS.md`. Since 22 Oct
2026 switchgear is on the cut-off register: carried as an estimate where it fails
1 % (battery, fuel cell, grid connection), left out where it passes (wind, solar);
the estimates were accepted as final on 23 Oct.

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
- [ ] **Turquoise outlet pressure.** 30 bar since 22 Oct 2026: Hermesmann's own
      functional unit for MP-E, as for every route (§3.1). A real molten-media
      plant may run near-atmospheric, which would make its compression term
      ~2.5× larger; check before turquoise carries any conclusion.
- [ ] **Finish the connection cost from the data in hand** (29 Oct): plan in
      `docs/COST_PLAN.md` §1.9 — A substation register, B cable length, C spare
      capacity, D site-specific charges, E build prices by area and H the
      voltage rule and 1 / 0.70 ceiling all BUILT 29 Oct; G the 14-area chain
      check RUN 29 Oct (42/42, 21 checks; found the band-floor boundary bug,
      fixed). Left: F the exact loss multiplier (Elexon Portal). From G: a
      150 MW IT site sits on the transmission boundary in every England and
      Wales area, and run both ways (29 Oct, `scripts/run_both_tiers.py`) the
      local network is £6.5–11.5 m/yr (7–13 %) cheaper with the same carbon
      in all six areas tried — the default tier from the 1.43x ceiling is the
      expensive one at that size. Decide: both-ways by default in the
      uncertain band, or a tier choice inside the LP. Northern Powergrid has
      no placed 33 kV price node, so its 33 kV sites take the area median.
- [x] **Connection wizard on page 2** (agreed and built 4 Nov 2026; `COST_PLAN.md` §1.11, `tests/test_connection_wizard.py`):
      clicking the site shows the substations within reach (name, voltage,
      distance, published room, register freshness) as a clickable list, and two
      paths. (1) *Pick a substation*: rows with room are live, rows with none
      are greyed but still clickable; a live pick runs with that one connection
      capped at its room (the one-option case, old speed, 38 min a year), with
      an optional typed size beside it (room shown; typing above the room is the
      reinforcement assumption, labelled); a greyed pick asks for a size ("no
      room published here, set your own size") and runs ignoring room, labelled
      as assuming the company provides it; "run islanded" sits beside the list
      when nothing has room. (2) *Let it choose*: the room mode as built, over
      the window the user picks — never default a year to the week; show the
      time estimate (about 3x a week, about 10x a year) as a warning and let it
      run. No "closest substation" mode. Model side: a site setting that pins
      the substation (one new override), the typed size is `connection_limit_mw`;
      the rest is page work (the preview table becomes the list; the mode radio
      and the islanded tick move behind it). **Band choice added the same
      afternoon:** at a picked substation the band is set from the load (one
      list) or left to the optimiser (every band at that voltage, a few
      switches; `Site.connection_band_optimised`; timed free on a London
      year). **Cheap run** (same afternoon): on the open path over two months
      the page offers full / loose gap (0.1 %) / prune first (each list priced
      alone at both ends, survivors within 2 %, then the tight frontier), full
      the default; `dc_runner.run_one(connection_solve=)`. The relaxed-share
      pruning was tried and dropped (lost the optimum on a week).
- [ ] **Cost map** (agreed 30 Oct 2026, for a fresh chat after the §1.11 commit):
      the LCA map's twin for the cost objective, as **one map with a side
      switch** (carbon / cost) so each technology's two coefficients sit on one
      box and mismatched lives or scopes show. Read the cost terms from
      `dc_model.objective_terms` the way `scripts/build_lca_map.py` already
      reads the carbon ones (same chains, same page, same checker and
      fingerprint); wrap every cost coefficient in `T.step` where it is made
      (`dc_inputs.build_tech`: capital x annuity + fixed opex share, with the
      rate, life and document as inputs; `connection_cost`, `network_charges`,
      `levies`, `duos_areas`, `h2_capex`, `tech_costs`, `battery`) and trace
      into or cite the three tables that arrive ready-made
      (`tech_lca_coefficients` / `annualised_table`, `electrolyser_costs_clean.csv`,
      `h2_prices_recommended.csv`); add a **document leaf** (statement, table,
      page, date, grade) in place of the Brightway inventory layer; show the
      half-hourly series (wholesale price, import charges by voltage group) by
      their mean as grid carbon is. Not a results view: the page's cost
      breakdown already does that. Start from the `lca-map` memory and
      docs/LCA_STYLE.md; republish at the same link.
- [x] **Let the optimiser choose the grid, voltage and charging band** (plan 30
      Oct, built 30 Oct, `docs/COST_PLAN.md` §1.11): on/off switch per price
      list (binaries in HiGHS, gap 1e-7), one import series per voltage group;
      modes room (default) / cap / single (`connection_options.py`,
      `dc_inputs.build_series(connection_mode=)`, `dc_model.ConnectionOption`,
      page radio). Decided 30 Oct: room is a hard limit; a substation with no
      figure is skipped for the nearest that publishes one; the next with room
      is a second option; the voltage is chosen too, the rule as floor. Checked:
      `run_both_tiers.py` passes in six areas (switched = cheaper forced run on
      the two lists; cheaper again with every list), chain re-run in every
      mode on the final code (single and cap 42/42; room 37/42, the other five
      stop on "no room found nearby"), solve time ~3.5x on the June week for
      London and 1.7-1.9x across the chain, but ~10x on the full year (cap
      mode, 11 lists: 6.4 h for a three-point frontier against 38 min fixed), so
      a full-year run with a choice of lists is a batch job until the lists are
      pruned (pick the list on the week or the relaxed problem, then fix it for
      the year; done for the sweeps 5 Nov, `sensitivity.run(list_choice=)`:
      central at the loose gap, variants on its list; the connection test
      prunes per variant). The year's own answer favours the switch in cap mode: £141.24 m
      on 132 kV against £146.39 m on the fixed national-grid list; in room mode
      London lands at Ealing (£147.55 m) because its twelve nearer national-grid
      substations publish no figure. **Still open:** the national
      grid option starts at the company's top (a lower floor is one line);
      11 kV vs above still by the published rule; a one-week window makes the
      grid look optional (headlines from full-year runs only); future-year and
      net-of-contracted room are reported, not caps. **No room nearby** (30
      Oct, afternoon): zero room drops the option, reach per voltage
      (`substations.REACH_KM`, assumed), `ConnectionUnavailable` and the page's
      "run islanded?" instead of a fabricated 1.43x list; next: reinforcement
      dates on the options, a "reinforced" option priced at the high-cost cap,
      then a two-period run (COST_PLAN §1.11 *Open* vi).
- [x] **Live, complete capacity register and the availability map** (plan 30 Oct,
      built 30 Oct, `docs/COST_PLAN.md` §1.10): R1 `scripts/fetch_register_sources.py`
      (39 portal datasets, each stamped with the portal's date) and
      `build_substation_register.py --capacity-only`; R2 every company's
      standard capacity datasets with `headroom_basis` / `headroom_as_of`
      (primaries 76–100 % everywhere, London from 1 % to 80 %; SSEN 100 % from
      its Headroom Dashboard); R3 headroom by year to 2050 and the connection
      queue; R4 364 grid-supply-point records; R5 `optimisation/availability.py`
      and the page panel; R6 re-run (both-ways unchanged). Decided and applied:
      location + headroom is the backbone; a price node is used only where
      matched by name to the connection substation, else the area figure.
      **Kept as a known limitation (30 Oct):** room is checked at the connecting
      substation only, not upstream; matters for 11 kV sites only.
      **Still open:** NGED's 33 kV switching stations and location-list rows
      publish nothing (their bulk coverage 16–50 %); UKPN and NGED publish no
      grid-supply-point capacity and NESO none; the companies' bases differ
      and the "central" scenario is a choice; the page panel is untested in
      the browser; the fork's survey also found Northern Powergrid's
      `gsp-appendix-g-information` (GSP contracted positions, mostly
      generation) and NGED's LTDS Table 3, both unused.
- [x] **Register quality, from the both-ways run** (29 Oct, fixed the same day):
      generators' and interconnectors' own 275/400 kV sites excluded from the
      transmission layer by name (36 of 412; Brighton now runs to Bolney); UK
      Power Networks' "Grid Substation" rows split by the lower voltage in the
      name — 132/11 kV grid sites are grid supply points plus an 11 kV primary,
      bare "132KV" names are switching sites, only 132/33 (66) stay bulk supply
      points. Still open there: the OpenStreetMap layer carries no capacity,
      and only 17 of UKPN's 454 grid rows publish a headroom.
      Still assumed:
      the 1.3 cable route factor (B), the half-published threshold for
      overruling the voltage rule (H), the publishers' median for POA price
      rows (E). Check still to do: NGED Table 6 / SPEN appendix 6
      connection-request sizes against the voltage rule.
- [ ] **NGED's connection prices read as transformer-only** (29 Oct). Its 132 kV
      substation £1.70–2.79 m against £6.96–13.04 m from the other four
      publishers; kept and flagged (`connection_cost.NGED_SUBSTATION_FLAG`).
      Ask NGED what the row covers, or price its four areas on the publishers'
      median (~4x on that line, ~1 % of a 150 MW site's annual cost).
- [ ] **EHV local charges for a named node** (29 Oct). 33/132 kV sites take
      the median of their area's listed sites in the same band
      (`duos_areas.EHV_BANDS`). Plan: (1) the EDCM method, DCUSA Schedules 17
      (FCP: HYDE, SOUT, SPOW, MANW, EMEB, MIDE) and 18 (LRIC: EELC, NORW, LOND,
      NEEB, YELG, SEEB, SWAE, SWEB) — both v17.5, held since 29 Oct, with
      ENWL's blank 2026/27 LRIC model (OneDrive `3 DUoS/site-specific EHV charges`);
      (2) each area's EDCM model workbook, if published with its charging
      statement; (3) node locations — LTDS or the DNO open-data portals —
      joined to the "Nodal prices" sheet we already hold (node, name, local and
      remote £/kVA); (4) site -> nearest node at its voltage -> nodal price ->
      tariff by the schedule's formula + the area's residual band (held) and
      cost adders (EDCM model); (5) check by reproducing Annex 2 charges for
      listed sites; low/high from the area's cheapest and dearest nodes.

