# Cost-side plan — 28 Oct 2026

A to-do list for the **cost objective**: the `cost` expression in
`dc_model.build_model` (`cost_capital` + `cost_operational` in
`objective_terms`, plus `objective_constants`) and the modules that feed it. It
is the counterpart of `docs/CARBON_PLAN.md`. Drawn from `TODO.md`,
`optimisation/DATA_GAPS.md` and `docs/OBJECTIVE_AUDIT.md` §2–§4, re-checked
against the code as it stood on 28 Oct, with the grid connection first because
that is where the work starts.

Every item here is also a line on `TODO.md`; this file sequences them and
carries the longer detail. **New** marks an item first raised in this plan
(added to `TODO.md` the same day).

Effort: XS < 1 h, S ≈ half a day, M ≈ 1–2 days, L > 2 days.

## Status — 28 Oct 2026, end of day

| Item | State | Where |
|---|---|---|
| 1.1 Tier and band | done — GB voltage rule (240 MVA E&W, 120 MVA Scotland), band floor on `cap_grid`, floor-binding flag | `network_charges.py`, `dc_inputs.py`, `dc_model.py`, `tests/test_connection_tier.py` |
| 1.3 Connection capital | done — NGED substation per MW, 2 × 2 km cable fixed, NESO §14 annuity | `connection_cost.py` |
| 1.4 Levies and losses | done — £62.99/MWh flat + CM on its window; ×1.0338 losses | `levies.py` |
| 2.1 Electrolyser stacks | done — NESO variable opex per kg | `h2_capex.py`, `dc_model.py` |
| Tariff year | done — every network tariff 2026/27 (TNUoS, TDR, BSUoS; LPN DUoS already was); cache refetches a missing year; NESO's renamed columns read | `network_charges.py` |
| Connection voltage | done — 11 kV up to 15 MVA (HV bands, medium-voltage grid carbon), else 33/132 kV (EHV) | `network_charges.connection_voltage` |
| 1.2 London DUoS | done — rows re-checked against LPN's 2026/27 schedule (they matched); tariff row by residual band, not No Residual; all-year red 11–14 and 16–19. Unit charge ~£2.04 → £0.04/MWh for a band-4 site | `network_charges.duos_tariff_for`, `duos_band` |
| 1.3 Connection capital, re-sourced | done — NGED June 2026 prices at the site's own voltage (132 kV cable +30 %; 33 and 11 kV sites priced on their own rows) | `connection_cost.py` |
| 1.4 Levies, 2026/27 | done — every figure from the filed documents, £/MWh computed in code; CM £308/MWh in window (was £177); losses from LPN line loss factors × assumed TLM 1.011 | `levies.py` |
| 1.5 Triad | done — HH locational tariff on `triad_mw` >= import in every weekday Nov-Feb 16:30-18:30 step (all 21 Triads 2019/20-2025/26) | `network_charges.triad_window`, `dc_model` |
| 1.6 DUoS for every DNO area | done 29 Oct — 14 schedules: 11 kV on each area's HV row and time bands, 33/132 kV on the median of the area's Annex 2 EHV sites in the band and its super-red window, each area's own LLFs (NGED's assumed: Annex 5 blank). Checked figure by figure | `duos_areas.py`, `scripts/check_duos_areas.py` |
| 1.8 Band boundaries | done — NESO Table TB (RIIO-ET3, fixed to 2031), T-Demand on MWh/yr | `network_charges.py` |
| 1.9 A–D Site connection | done 29 Oct — substation register (10,829 substations, 8,432 price nodes), cable route from the site, spare-capacity flag, site-specific 33/132 kV charges | `substations.py`, `ehv_charges.py`, `scripts/build_substation_register.py` |
| 1.9 E Build prices by area | done 29 Oct — eleven areas on their own 2026 statements, POA rows on the publishers' median (stand-in), NGED's substations kept and flagged low | `connection_cost.py`, `tests/test_connection_prices_by_area.py` |
| 1.9 H Voltage rule and ceiling | done 29 Oct — published rule as floor, area's substation capacities above it; ceiling 1 / 0.70 (FES load factor) instead of 1.5 assumed | `substations.voltage_with_room`, `network_charges.connection_voltage(site=)`, `sites.py` |
| 1.9 G Chain check | run 29 Oct — 14 areas x 3 sizes, 42/42 solved, 21 checks pass; found and fixed the band floor sitting on the boundary (one kVA above now) | `scripts/check_connection_chain.py`, `optimisation_outputs/connection_chain.csv` |

The rest of §1–§5 is open. The table below describes the state before these.

## Where the cost objective stands

| Term | Code | State |
|---|---|---|
| Wind, solar capex + opex | `tech_costs.py` (DESNZ/Arup) | sourced; 2023 £, generator-side charges inside, no land or rates |
| Battery | `battery.py` (Modo) | £/kW sourced; £/kWh and opex not |
| Electrolyser | `h2_capex.py` (NESO) | AE/PEM sourced; SOEC unsourced; stacks and consumables free |
| Tank | `h2_capex.py` | unsourced, and prices a different vessel from the carbon side |
| Fuel cell | `h2_capex.py` | proxy; stack share frozen from a carbon split |
| Grid: import energy | Elexon wholesale + BSUoS + DUoS unit | **no levies, CCL, losses or margin** |
| Grid: per MW of connection | TNUoS HH zonal + DUoS capacity | sourced values; tier assumed; DUoS London-only, wrong class |
| Grid: fixed per year | TDR + DUoS fixed | sourced values; band read from the cap, not the build |
| Grid: connection capital | — | **£0 at every site** |
| Bought hydrogen | `h2_prices.py` | secondary; T&S and ETS questions open |

## 1. Grid connection

What the LP charges today (`dc_inputs.build_series` → `network_charges.import_charges`):

- **volumetric**, on `imp[t]`: wholesale + BSUoS + DUoS unit rate (DUoS only if
  distribution-connected);
- **per MW of `cap_grid`**: TNUoS HH zonal tariff + DUoS capacity charge;
- **fixed per year**, only if the build has a grid: TDR band + DUoS standing charge.

What it does not charge is the connection itself. The carbon side does: two
transformers per MW for N-1, the switchyard civils, switchgear and bay hardware
as cut-off estimates (`grid_connection.py`, 305 kg CO₂e/MW/yr). The cost side
has no counterpart, so the two objectives describe different connections.

In order. 1.1 comes first because it decides which tier a site is on, which
decides whether DUoS applies and which connection voltage 1.3 has to cost.

- [ ] **1.1 Tier and band follow the connection built** (M). Already on TODO
      (*Blocking*) and fully sequenced in `docs/CONNECTION_TIER_PLAN.md`; none of
      it has been started. The 100 MW threshold is still
      `network_charges.TRANSMISSION_MW_ASSUMED`. Moves the London headline from
      transmission to distribution (EHV4), which turns DUoS on.
- [ ] **1.2 DUoS tariff — fix the class, then re-transcribe the table** (S).
      Three parts, all in `network_charges.DUOS_LPN_HV`:
      - *Class.* `DUOS_DEFAULT_TARIFF` is still "HV Site Specific No Residual",
        which is for sites with no final demand. A data centre is on Band 1–4,
        and the band should come from the same banding logic as the TDR
        (on TODO under *Network charge shape*).
      - *The table looks inverted* (**new**). The No Residual row carries a
        120.55 p/day standing charge and both Band rows carry 0.0. Since
        DCP358 the residual is recovered through the banded fixed charges, so
        it should be the other way round. The No Residual red rate (3.44 p/kWh)
        is also 15× Band 1's (0.230). Re-read LC14 Annex 1 before trusting any
        of the rows.
      - *Red band.* Nov–Feb only is unverified; LPN's historic red band was
        all year, 11–14 and 16–19 (£6.96 vs £2.05/MWh). On TODO.
      - *HV for EHV.* An EHV site is priced on HV tariffs. EHV charges are
        site-specific (Annex 2), so the honest version is a range across LPN's
        published EHV sites, not one row. Already in `DATA_GAPS.md`.
- [ ] **1.3 Connection capital** (L). The big gap, and **new as framed here**.
      `DATA_GAPS.md` (*Transmission connection capital cost*) and the TODO
      *Parked* line describe it as a problem for floored Scottish zones only.
      It is not: **every** site pays £0 for its connection assets, whichever
      tier it is on. What it needs:
      - *Same structure as the carbon side*: a per-MW part (intake transformers
        ×2, switchgear bays, civils) that scales with `cap_grid`, and a fixed
        part (the line or cable to the network substation and the remote-end
        bay) that goes on `cost_grid_fixed_per_year`. The per-MW part is the
        one that changes the LP's sizing; the fixed part changes the
        grid-connected versus islanded comparison, which is the comparison the
        architectures exist for.
      - *Who pays what depends on the tier.* Distribution: the Common
        Connection Charging Methodology (sole-use assets, plus a reinforcement
        contribution — check how the 2023 Access SCR changed the demand side).
        Transmission: CUSC Section 14, where connection assets are charged as
        an annual charge on their asset value, so the methodology carries its
        own annualisation (rate of return, depreciation, maintenance).
      - *Candidate sources*, none read yet: the indicative cost tables in DNO
        connection charging statements (UKPN, SSEN, NPg, ENWL); Ofgem's
        RIIO-ED2/T2 unit-cost data; NESO's connection charging statement for the
        Section 14 parameters. DESNZ/Arup's generator connection costs are not a
        substitute, but can serve as a sanity check.
      - Closing it removes `dc_pareto`'s lexicographic second stage. The old
        Scotland-only *Parked* TODO line was replaced by a *Blocking* one.
- [ ] **1.4 Levies and supplier costs on imported energy** (M). On TODO
      (*Blocking*, *The import price carries no levies*). Two points to add
      when doing it:
      - *Shape* (**new**). RO, FiT, CfD and AAHEDC are flat £/MWh, but the
        Capacity Market levy is recovered on winter-weekday 16:00–19:00
        demand. It is time-shaped like DUoS red, and storage can dodge it.
        Model it as a time series, not as part of a flat adder.
      - *Losses.* Cost does not gross imports up for distribution and
        transmission losses (LLF/TLM); carbon does (×1.0338 at high voltage).
- [x] **1.5 TNUoS on Triad, not peak import** — closed 28 Oct. Was (S). On TODO (*Network charge
      shape*). Identical for a flat grid-only load; over-charges every storage
      build and hides Triad avoidance.
- [x] **1.6 DUoS for every DNO area** (L). **Done 29 Oct 2026** (`duos_areas.py`). Already on TODO (*Parked*). After 1.1
      it stops being parked: most England and Wales sites become
      distribution-connected and would be priced on London's tariffs.
- [ ] **1.7 Tariffs over the asset's life** (S, **new**). Every network charge is
      FY2025/26 and is applied to a connection annualised over 40 years. NESO
      publishes a five-year TNUoS forecast; at least run it as a sensitivity.
- [x] **1.8 Band boundaries** — closed 28 Oct from NESO Table TB. Was: EHV band boundaries against DCUSA Schedule 32 (S). On TODO
      (*Verification*). It matters more after 1.1, because the band floors in
      the tier plan come from these boundaries.
- [ ] **1.9 Export** (M). On TODO (*Verification*); refused until modelled.
- [ ] **1.10 Power factor and reactive charges** (XS, **new**). PF 1.0 everywhere;
      the DUoS reactive charge (0.244 p/kVArh) is transcribed and never used. Note
      it as an assumption, unless a source puts a data centre's PF well below 1.

**Not cost, but a question for the study**: connection lead time. In GB that is
the binding constraint on new data centres, and it is not a £/MW. Whether the
study treats it (a cost of waiting, bridging on on-site generation) or states
it as out of scope is a scope decision. `sites.connection_limit_mw` is the only
place it is felt today.

### 1.9 Finishing the connection cost from the data in hand (plan, 29 Oct 2026)

Sources are in OneDrive `connection sources/3 DUoS/site-specific EHV charges`
(index in its README). Parts in build order; each says what is in hand and
what is still missing.

**A. One substation register for all 14 areas** — **built 29 Oct 2026**: `scripts/build_substation_register.py`, checked by `scripts/check_substation_register.py` and `tests/test_substation_register.py`; 10,829 substations, 8,432 price nodes; coverage and fallback error in `optimisation_outputs/substation_register/` (SOURCES.md). (foundation for B-D). Name,
level (grid / bulk supply / primary), voltage, coordinates, area, spare
demand capacity where published, and the link to the area's "Nodal prices"
row. *In hand:* locations for all six companies; names for 13 areas; price
links 89-98 % (UKPN, Northern Powergrid), 61-86 % (NGED), 72-90 % of supply
points (SSEN). *Missing:* North West names (fallback: Ordnance Survey Open
Names, free download, to place the price sheet's place names); SP Energy
Networks' price labels decoded from its LTDS tables (in hand, work only).

*Locating price points without names (29 Oct 2026).* Only price and location
matter; a name is just the join. Where the company's own data has no name, a
price point's place name is located (OpenStreetMap named places, substations,
industrial sites) and snapped to the nearest substation of the right level.
Tested on the North West against price points already known: 132 kV picks
the right substation 23 of 23; 33 kV 173 of 214 (81 %), 90 % within 1.8 km.
With busbar labels stripped, direction prefixes dropped, group labels split and
six-letter codes decoded (`decode_code`, about 90 % right where it answers, measured
on NGED's known codes), the North West reaches 88 % of 33 kV and 92 % of 132 kV
price points (from 47 % and 28 %); 187 customer nodes are flagged.
13 customer or generator nodes are set aside (not where a new site connects).
The rest take their 132 kV group's located prices (ENWL's substation
hierarchy gives each substation's group), with the error measured by
hiding known points.

**B. Cable route length from the site's coordinates** — **built 29 Oct 2026** (`substations.connection_point`, `connection_cost.capital(route_km)`). (replaces the 2 km
`connection_cost.ROUTE_KM`). Distance to the nearest substation at the
connection voltage: 11 kV a primary, 33 kV a bulk supply point or primary's
33 kV side, 132 kV a grid site, transmission a 275/400 kV substation. *In
hand:* every distribution substation's coordinates. *Missing:* 275/400 kV
locations (OpenStreetMap, free, 490 in GB — checked 29 Oct); a sourced ratio
of cable route to straight-line distance (until found, ASSUMED and flagged).

**C. Spare capacity at that substation.** — **built 29 Oct 2026** (`substations.connection_point`: flag, both routes, `shortfall_route`). If the site's connection exceeds
the substation's published demand headroom, the next substation in reach
(or the next voltage) is used, or the run is flagged. *In hand:* SSEN and
Northern Powergrid capacity maps (available demand capacity), SP Energy
Networks (firm capacity and maximum load), UK Power Networks (ratings and
maximum demand). *Missing:* the North West's primary and bulk-supply
heatmaps and NGED's capacity map (both on portals the keys in `.env`
open). *Decided 29 Oct 2026:* a shortfall is flagged, and the run then compares
the two ways round it — the cable to the next substation in reach with room,
against the reinforcement the site would pay for at its first choice (under
the Access SCR a demand customer pays reinforcement only above the £1,720/kVA
High Cost Cap, so below the cap the only cost is the wait) — and reports both.
*Fallback where a node is unlocated or unpriced (tested leave-one-out, 29 Oct):*
the nearest located node of the same voltage is as good as or better than
inverse-distance weighting over 3-5 neighbours in 8 of 10 areas (median
error 0-1.2 £/kVA against 0.6-1.5); the area median is worst where prices
vary (North West 3.7). Use the nearest node; where a node's 132 kV group is
known and the nearest node is outside it, use the group's nearest member.

**D. Site-specific charges at 33 and 132 kV** — **built 29 Oct 2026** (`ehv_charges.py`, `scripts/calibrate_ehv_charges.py`; checked against Maxwell House and Vantage, within 16 %). (replaces the area median in
`duos_areas.EHV_BANDS`). Location part from the nearest substation's
"Nodal prices" row (local and remote £/kVA), turned into a capacity and
super-red charge by the Schedule 17 or 18 formula; plus the area's residual
fixed charge for the band (in the model) and its other add-ons. *In hand:*
both schedules, both 2026/27 models (published blank), every area's nodal
prices and listed sites. *Finding (29 Oct):* the listed sites cannot be
tied to price nodes by name (1 of ~300), and no company publishes its
model inputs, so each area's add-on is calibrated statistically — the
area's modelled charges over its own nodes matched to its listed sites'
charges in the same band — and checked against a few listed sites placed by
name (e.g. Tata Steel, Shell Stanlow). DERIVED. *Missing:* nothing to
download.

**D, the blocker: each area's add-ons need sites whose substation is known.**
Checked 29 Oct 2026, how each company labels the sites in its Annex 2:
NGED (4 areas) by real name — 40-50 % match a named, located site in NGED's
own LTDS network files (e.g. University of Warwick, Cauldon Cement, BOC
Margam); SP Energy Networks (2) by company name (Shotton Paper, Shell
Stanlow, Tata Steel); UK Power Networks (3) by six-letter site codes
(e.g. BRMLEY), possibly its own site codes; ENWL, Northern Powergrid (2)
and SSEN (2) anonymised ("Tariff 1", "EHV Site Specific (LLFC 603)").

1. *The formula.* From Schedules 17 and 18 and the two model guides, write
   down how a site's capacity and super-red charges are built from the
   node's local and remote charges, the site's peak-time demand share and
   the area-wide parts — which parts are location-specific, which are not.
2. *Known pairs.* NGED from its network files (weak name matches checked by
   hand); SP Energy Networks by placing company names (OpenStreetMap search,
   free); UK Power Networks by testing its site codes against its site list.
   Each pair: site -> location -> nearest price node at its voltage.
3. *Pilot on NGED.* Fit the area-wide part from the pairs; measure the error.
   A poor fit means the formula was misread or the sites' unknown
   peak-time shares dominate — fix before going on.
4. *Anonymised areas.* Choose each area's add-on so the formula over its
   33/132 kV nodes reproduces the spread of its listed sites' charges by
   band. Test this on the NGED areas first, where the answer is known, and
   quote that error.
5. *Wire it in:* site -> nearest node -> formula + add-on + band residual;
   low/high from the fit error and the nodes in reach.

Nothing more to download for 1-4 (OpenStreetMap place search is free). The
exact answer would need each company's populated charging model, which none
publishes.

*Found by searching, 29 Oct 2026:*
- **Three real data centres in the 2026/27 Annex 2 lists, all band 4** — the
  check points for D: Maxwell House Data Centre (NGED East Midlands: 1.33
  p/kVA/day, 25,690.69 p/day fixed, 1.554 p/kWh super-red), Cardiff Data
  Centre (NGED South Wales: 2.17, 95,701.75, 0) and Vantage (NGED South Wales:
  3.29, 118,417.56, 0.09). All sit inside their area's band-4 quartiles in
  `duos_areas.EHV_BANDS`, so the current stand-in is in the right range.
- **Formula pieces (Schedule 18):** the local LRIC element is charged on
  maximum import capacity, the remote element on super-red units; the
  indirect-cost part is a rate x (0.5 + coincidence factor) per kVA, the
  coincidence factor being peak-time kW over capacity kVA (about 1 for a
  flat data-centre load). NESO's *CDCM and EDCM model training* (March 2020)
  has worked scenario inputs.
- **Not every area's 2026/27 EHV charges follow the standard method.** SSEN
  (both areas) charged outside the EDCM for 2026/27 under an Ofgem direction:
  locational components and network use factors carried over from earlier
  years, negative fixed charges moved into capacity charges (SSEN request,
  24 Jan 2025). NGED East and West Midlands have a direction for 2027/28
  ("the FCP did not produce prices" / negative residuals). So for SSEN the
  2026/27 nodal prices will not reproduce its listed charges; there the area
  median, or a fit to its listed sites, is the right basis.
- **No populated charging model is public.** NGED's and ENWL's published
  2026/27 models are byte-for-byte the generic blank ones; a 2014 request
  for the network tables was refused. UKPN's statement (5.1-5.2) calls the
  nodal costs "illustrative": a new connection changes utilisations and so
  its own charge.
- **Cable route vs straight line:** no UK factor found. Candidates to read:
  DESNZ/Ramboll *Undergrounding transmission cables* (2025); NGED
  *Underground cable costs report*.

**E. Build prices by area.** — **built 29 Oct 2026** (`connection_cost.PRICE_LISTS`,
`AREA_PRICE_LIST`, `prices(region)`; 27 tests in `tests/test_connection_prices_by_area.py`).
Eleven areas on their own statements; POA rows on the publishers' median, named
as stand-ins; NGED's substation rows kept and flagged (`NGED_SUBSTATION_FLAG`).
Central, 2 km: 132 kV substation £141,667–204,496/MW outside NGED against
£37,431 inside; the whole-area table prints from `python optimisation/connection_cost.py`.
All seven statements are in OneDrive `4 connection capital`.

**H. The voltage rule and the connection ceiling** — **built 29 Oct 2026**.
The published rule is the floor; the area's own substation capacities decide
above it (`substations.voltage_with_room`: step up where every substation in
reach that publishes a headroom is short, if at least half publish one — an
assumed threshold). A 103 MW connection goes 33 -> 132 kV in Manchester and
Reading; London and Norwich keep 33 kV for want of published headrooms.
The ceiling is 1 / 0.70 = 1.43x the load from the FES 70 % data-centre load
factor (NGED Data Centre Impact Study, Nov 2025, pp. 29, 37), replacing the
assumed 1.5x; no voltage or tier changes at the test sizes, the tier flips
between the two only for 133–146 MW IT at PUE 1.2. Not done: NGED Table 6 /
SPEN appendix 6 connection-request sizes as a check on the rule.

*E, read off the statements (29 Oct 2026; new double-transformer substation,
cable per additional metre in footpath or carriageway, published range):*

| | NGED (the stand-in) | SSEN Southern | SSEN N. Scotland | UKPN East / South East | ENWL | SPEN | Northern Powergrid |
|---|---|---|---|---|---|---|---|
| 132 kV substation | £1.70-2.79 m | £11.5-13.0 m (outdoor) | N/A (transmission) | £8.0-9.2 m (indoor; London POA) | £7.0-11.3 m (outdoor) | POA | POA |
| 33 kV primary | £1.36-1.50 m | £2.62-2.83 m | £1.94-2.85 m (indoor) | £5.2-5.8 m (indoor) | £4.04-4.77 m (indoor) | POA | POA |
| 132 kV cable, £/m | 3,171 | 1,405-32,316 | N/A | 600-900 | 2,300-3,500 | POA | POA |
| 33 kV cable, £/m | 221-540 | 437-1,054 | 141-439 | 400-700 | 2,300-3,200 | 557-722 | POA |

NGED's 132 kV substation is 4-5x below every other publisher, so the stand-in
understates that line by that factor elsewhere (and NGED's own figure looks
low against the field). Annualised at 60 MVA firm it is £2,350/MW/yr against
£9,000-13,000 — about 1 % of a 150 MW site's annual cost, so small in the total
but wrong as a line. Decision for E: each area's own figures where published;
for the POA areas (SPEN, Northern Powergrid, London's substation) the median of
the publishers, not NGED's, marked as a stand-in.

*Cross-check against real schemes (29 Oct 2026):* ENWL's published capital projects price a single 132/33 kV grid transformer replacement at £1.9-4.1 m and a pair at £3.4 m (Rochdale GT1 and GT2) — more than NGED's £1.7-2.8 m for a whole new double-transformer 132 kV substation, and in line with ENWL's own list (£7.0-11.3 m with switchgear, civils and land). Primary transformer pairs £1.4-1.8 m against NGED's £1.36-1.50 m "new" primary. So NGED's rows read as transformer-only prices; the other lists as whole substations. The stand-in for the POA areas should be the median of the whole-substation publishers, and NGED's own areas are arguably understated too (noted, not changed). No public per-company asset unit costs were found from Ofgem (ED2 annexes are totex-level); Northern Powergrid and UK Power Networks publish no scheme costs.

*Other routes tried for E, 29 Oct 2026, all empty:* the four open-data portals (only flexibility prices and the two cost sets above); NESO's charging statements (no per-site asset values); ENWL's RIIO-ED2 costing annex (method, no asset unit costs); NGED's RIIO-ED2 document library (52 documents, no data tables); the public contracts register (search returns unrelated notices). What remains needs a person: the Business Plan Data Tables (asset unit costs by company), held by Ofgem and the companies but not published as downloads; or a budget estimate from a company.

**F. Exact transmission loss multiplier.** Waiting on the Elexon Portal
(TLFA-I009 and TLFA-I014).

**G. Check.** — **run 29 Oct 2026** (`scripts/check_connection_chain.py` ->
`optimisation_outputs/connection_chain.csv`): 14 areas x 5, 60 and 150 MW IT
at PUE 1.2, one June week (2–9 Jun 2025) hourly, both anchors of the frontier.
42 of 42 solved; 21 checks pass. What it showed:

- *Found and fixed:* the band floor sat **on** the boundary, not above it.
  Every table boundary is inclusive below (≤ 20,000 kVA is still EHV3; "up to
  15 MVA" is still 11 kV; > 240 MVA is transmission), so a connection built at
  exactly 20.000 MW was an EHV3 site charged as EHV4 — and 28 of 39 runs built
  on the floor. The floor is now one kVA above the boundary
  (`network_charges.BAND_FLOOR_STEP_MW`); every built connection is now in the
  band it is charged in. Tests added.
- *The floor binds in 29 of 42 minimum-cost runs* (28 of 42 minimum-carbon):
  the optimiser would build a smaller connection than the band read from the
  1.43x ceiling requires. Every England-and-Wales 150 MW run sits at the
  240/250 MW tier boundary: at that size (257 MW ceiling) the model would
  rather be a large distribution site than a transmission one. That is the
  size the "run both ways" option exists for; a 150 MW IT site is a case to
  run both ways, not to read off one tier.
- *The register moved the voltage in 4 runs* (Inverness 5 MW 11→33 kV;
  Manchester, Bangor, Southampton 60 MW 33→132 kV) and flagged a spare-capacity
  shortfall in 8 of 42. Transmission substations (OpenStreetMap) carry no
  capacity, so every 150 MW run is "unknown".
- *Site-specific local charges in 11 of 16 EHV runs*; area medians for SSEN's
  two areas (outside the method this year) and Northern Powergrid's two (no
  33 kV node could be placed there) — the register's next gap.
- *Build prices:* every area on its own list; the only stand-in rows reached
  were London's 33 kV substation (POA). SSEN Southern's printed 132 kV cable
  range gives its 150 MW transmission run £8.9 m/yr of cable — the printed
  figures, flagged HIGH in the code.
- *Magnitudes, minimum-cost anchor, this one week scaled to a year:* 5 MW IT
  £2.7–3.9 m/yr; 60 MW £31.6–43.8 m; 150 MW £87–110 m. All-in import price
  £134–149/MWh. Cheapest area at every size: South West (Exeter). One June week
  is not a year: these are the chain working, not results.

*150 MW IT both ways (29 Oct 2026, `scripts/run_both_tiers.py` ->
`optimisation_outputs/both_tiers_150mw.csv`; six England-and-Wales areas, same
June week, tier forced each way).* **The local network wins everywhere on cost
and ties on carbon**: minimum-cost £6.5–11.5 m/yr cheaper (7–13 %) — Brighton
−9.4, Cardiff −6.5, Exeter −11.5, London −7.2, Manchester −8.4, Nottingham −8.7;
minimum-carbon anchors within 0.2 % of each other on carbon and £7–11 m
cheaper locally. Three causes, in order: the transmission residual band
(T-Demand4 £7.60 m/yr) against EHV4 (£2.08 m) plus small local fixed charges
— £5.3 m/yr; the cable — a 275/400 kV substation is 3.6–24.2 km of route away
where the 132 kV point is 0.4–1.7 km, so £3.8–6.1 m/yr of 132 kV cable against
£0.2–1.0 m (Brighton's nearest "transmission" point was first the Rampion wind
farm's onshore substation, which no demand customer could join — fixed the
same day: generators' and interconnectors' sites are excluded from the
transmission layer, and UKPN's 132/11 kV grid sites no longer pose as 33 kV
points; re-run on the corrected register Brighton goes to Bolney, 24.2 km by
route against Rampion's 23.9, and no figure here moves by more than £0.03 m);
and the tier floor — 240/250 MW of connection held
and charged per MW where the local run builds 20–165 MW (£1–2 m). The local
run's smaller connection makes it import less (Manchester 48 against 86 GWh)
and build more solar and battery, which gives back part of the saving.
Caveat: the forced-local run is not capped at the DNO's top, but every local
build came in under it, so a real offer is plausible. Consequence: at 150 MW
IT the model's default tier
(from the 257 MW ceiling) is the expensive one; the page's both-ways option
should be the default for sizes in the uncertain band, or the tier should be
chosen by the LP (CONNECTION_TIER_PLAN.md: a tier variable is the next step).

## 2. Carbon is charged and cost is free

Asymmetries that let the cost objective build or run something for nothing. Each
one biases cost-optimal results in a known direction, so they come next.

- [ ] **2.1 Electrolyser stack replacements** (S, **new as an asymmetry**). Since
      26 Oct the carbon side charges stacks by running hours
      (`ely_stack_units`). Cost charges `cost_ely × cap_ely` and nothing per
      replacement, so a cost solve runs the electrolyser hard for free. NESO's
      variable opex (stack replacement and water, PEM £0.12/kg) is the natural
      source: it is in `electrolyser_costs_clean.csv` and dropped by
      `h2_capex.electrolyser_costs()`. Do this job together with the TODO
      *Read NESO's variable opex* item. Decide whether to charge it per kg (as
      NESO does) or per replacement on `ely_stack_units` (as the fuel cell
      does). Doing both would double count.
- [ ] **2.2 Electrolyser consumables** (S). On TODO (*Blocking*).
- [ ] **2.3 Battery and fuel-cell step-up transformers** (XS to check,
      **new**). Carbon has charged them since 15 Oct; cost has no line. Check
      whether Modo's £/kW is a full-project figure that already includes the
      grid transformer (it probably does) and whether the fuel-cell proxy does
      (it is equipment, not installed cost, so probably not).
- [ ] **2.4 Tank cost describes a different vessel** (M). On TODO (*Blocking*).
- [ ] **2.5 Hydrogen compressor capital** (S). On TODO (*Balance of plant*).

## 3. Headline capex with no source

On TODO, in this order of how much they move a result:

- [ ] **3.1 Fuel cell capex and per-replacement stack cost** (L). *Blocking*.
- [ ] **3.2 SOEC capex/opex** (M). *Blocking*.
- [ ] **3.3 Battery £/kWh and duration bound** (S). *Cheap wins*.
- [ ] **3.4 Battery fixed opex from BEIS 2022** (S). *Cheap wins*.
- [ ] **3.5 Marocco 2020 for a tank cost** (S). *Cheap wins*.

## 4. Cross-cutting

- [ ] **4.1 One price base and one discount-rate policy** (M). On TODO. Today:
      DESNZ at each technology's own rate, Modo 5.0 % real, H₂ assets 6 % with
      no source, and the Green Book 3.5 % used nowhere. Do this before 1.3,
      which needs a rate to annualise connection capital.
- [ ] **4.2 Generation cost scope** (S). On TODO (generator-side TNUoS/DUoS
      inside DESNZ opex; land and business rates missing).
- [ ] **4.3 Decommissioning and insurance, consistently** (S, **new**). Carbon has
      end-of-life out everywhere, by rule. On the cost side, check what each
      source includes. DESNZ is believed to carry decommissioning and insurance
      for generators, while the hydrogen assets are bare capex plus an
      opex percentage. If only some technologies carry them, the comparison
      between them is not like for like.
- [ ] **4.4 VoLL** (XS). Assumed, no source. State it as a penalty that sets
      reliability, not as a cost, and keep it out of the £/MWh reported.

## 5. Bought hydrogen

- [ ] **5.1 CO₂ T&S: replace, don't add; grey's ETS level** (S). On TODO
      (*Cheap wins*).
- [ ] **5.2 Seller compression capex, haulage** — Parked on TODO; haulage now
      closed as a boundary item.

## Order

1.1 → 1.2 → 4.1 → 1.3 → 1.4, then 2.1 alongside, then 1.5–1.10. Re-run the
London and Highland reference cases once after 1.1–1.4 rather than after each
one: all four move the same headline, and the figure regeneration on TODO
should wait for them.
