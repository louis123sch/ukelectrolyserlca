# Source register

Every number the optimisation study uses, where it came from, and how far it
can be trusted. Three provenance grades are used throughout the code and in
the tables below:

| grade | meaning |
|---|---|
| **transcribed** | copied from a named table in a named published document, or pulled from a public API |
| **derived** | computed from transcribed values plus this project's own inventories, with the arithmetic in the code |
| **assumed** | a scenario choice with no source. Every one is flagged in the module that uses it and printed in its output |

Price basis throughout is **real 2025 GBP**. Where a source publishes in EUR
or USD, conversion uses the FES 2025 Data Workbook's own cross-rate table
(2025: GBP→EUR 1.17, USD→EUR 0.913, so USD→GBP 0.7803) and its GDP deflator,
so every currency conversion in the study traces back to one published table.
Emissions are IPCC 2021 GWP100 on ecoinvent 3.9.1 apos throughout.

---

## Baseline 1 — data centre on the GB grid
`baseline_grid.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Data centre inventory | 1.60e9 kWh over 25 y; 21,036 t CO₂e fixed | transcribed | Zhang, M., Carbajales-Dale, M., Ma, X., Guo, L., Fan, C. (2025), hyperscale Virginia data centre. Built into `data centre foreground` by `2.tech_lca_foreground.ipynb` |
| Continuous load | 7,306 kW | derived | 1.60e9 kWh ÷ 25 y ÷ 8760 h — the inventory's own figure, not an added assumption |
| Grid carbon intensity | half-hourly, mean 0.2369 kg CO₂e/kWh | transcribed | NESO Carbon Intensity API, regional (region 13, London), via `3.1.custom_grid_carbon_intensity_api.ipynb` |
| Wholesale electricity price | half-hourly, mean £79.83/MWh | transcribed | Elexon BMRS Market Index Data, provider APXMIDP, via `5.prices.ipynb` |
| Linear decomposition | `fixed + Σ kWh×EF` | derived | Validated against a full Brightway LCA to 1e-6 by the script itself |

---

## Generation costs — wind and solar
`tech_costs.py`

All three technologies are **transcribed**, real 2023 prices as published.

| Technology | Source |
|---|---|
| Onshore wind | DESNZ / Ove Arup & Partners, *Renewable Energy Generation Cost and Technical Assumptions — Onshore Wind and Solar PV, Cost of Electricity Report Update 2024*, ref 299867-00, Final, 14 July 2025. **Table 3, p.6** |
| Solar PV (>5 MW) | Same report, **Table 4, p.7**. Costs are per **kWp DC**, not kW AC |
| Offshore wind | DESNZ / Ove Arup & Partners, *…— Offshore Wind, Cost of Electricity Report Update 2024*, Final, 24 July 2025. **Table 3, p.6**. Infrastructure **excludes** OFTO transmission, recovered via TNUoS inside opex |
| LCOE cross-check | Onshore/solar **Table 5, p.8**; offshore **Table 4, p.7** |

Hurdle rates are each report's own pre-tax real figure — onshore 5.8 %,
offshore 6.2 %, solar 5.0 % — not a single project WACC.

**Verification built in.** `check_against_price_outputs()` asserts the onshore
wind rows still match what `5.prices.ipynb` independently writes to
`price_outputs/static_cost_assumptions.csv`, so the two cannot drift. The
LCOE cross-check reproduces each report's own published LCOE to within 8 %;
the residual is methodological (this module uses a plain CRF annuity, the
reports use the DESNZ LCOE calculator, which also discounts construction-period
spend). That check is what caught the reports' inverse case-pairing, where a
low-cost scenario is paired with a **high** load factor and lifetime.

---

## Hydrogen prices by colour
`h2_prices.py`

| Colour | Central | Grade | Source |
|---|---|---|---|
| grey (SMR) | £2.93/kg | transcribed | European Hydrogen Observatory, *Hydrogen production costs 2024*, UK rows, technology "SMR" |
| blue (SMR+CCS) | £3.78/kg | transcribed | Same, technology "Reforming with carbon capture" — matches `smr_ccs_hermesmann`. NESO's ATR+CCS (£2.90) is the cheaper-route low case |
| green, behind meter | £4.93/kg | transcribed | Same, "Renewable hydrogen directly connected to a renewable electricity generation source" |
| green, grid-connected | £8.33/kg | transcribed | Same, "Grid electrolysis". Includes €2.77/kg of UK grid fees and taxes — 29 % of its total |
| turquoise (pyrolysis) | £3.21/kg | **derived** | Constructed: 86 % grey + 14 % green, weighted by the MP-E inventory's own gas:electricity energy split (62.8 kWh gas + 10.3 kWh electricity per kg, HHV) |

Supporting inputs:

| Input | Value | Grade | Source |
|---|---|---|---|
| Green LCOH cube | 424,080 rows | transcribed | NESO Green Hydrogen Data Portal, resource `cc2dad0c-393c-4ae0-ae67-a98703169ad4`, "Levelised cost of green hydrogen modelling, 2025 to 2050" |
| Blue LCOH | ATR+CCS 2025–2050 | transcribed | NESO, resource `3f3b1bf0-4664-494f-a501-a39adabecd0d` |
| NBP gas price | £33.74/MWh HHV (2025) | transcribed | FES 2025 Data Workbook V006, sheet **CP1**, base case, 2010–2050 |
| GB carbon price | £78.96/tCO₂ (2025) | transcribed | FES 2025 Data Workbook V006, sheet **CP2**, GB total carbon price |
| Gas m³ / electricity kWh per kg H₂ | per colour | transcribed | This project's own `hydrogen foreground` activities |
| Plausibility band | grey $1–4, blue +$0.4–1, green $3–>10 per kg | transcribed | IEA, *Global Hydrogen Review 2026*, **Figure 3.20 and pp.110–111** |
| Turquoise validation | LCOH $2–4/kg; Brazilian EPE $1.5–4.4/kg | transcribed | Rego, E.E., Oller Nascimento, C.A., Ribeiro, C.O. (2026), *Economic analysis under uncertainty of turquoise hydrogen via methane pyrolysis*, Int. J. Hydrogen Energy **225**, 154378. Open access, CC BY |
| Carbon black price | $1.52/kg; 3 kg C per kg H₂ | transcribed / stoichiometric | Rego et al. 2026, **Table 1**. Credit defaulted **off** — see the module for why the market cannot absorb it |

**Verification built in.** `check_against_inventory()` re-reads the gas and
electricity coefficients from the Brightway activities and fails if the
module's constants have gone stale. A monotonicity guard fails the run if any
colour's low/central/high are out of order — it caught grey's high case
landing *below* central, because SMR exports electricity, so a dearer power
market makes grey hydrogen cheaper. A third guard fails if the two output
tables disagree by more than half a penny.

**Known discrepancy, recorded not hidden.** Rego et al. assume 16 kWh/kg for
pyrolysis; this study's MP-E inventory uses 10.29 kWh/kg. This study's
turquoise is therefore cheaper and cleaner than theirs by construction.

---

## Battery storage
`battery.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| CAPEX, 1-hour system | ~£400/kW today → ~£200/kW by 2040 | transcribed | Modo Energy, *BESS Cost and Technical Assumptions*, `docs.modoenergy.com/pages/jan-2026/uk-europe/model-assumptions/` (July 2026). Real 2025 GBP |
| CAPEX, marginal hour | £100/kW per additional hour (2025) | transcribed | Same |
| Power / energy split | £300/kW + £100/kWh | derived | The two above decompose cleanly: a 1-hour system is 1 kWh per kW, so the marginal hour *is* the energy component |
| Cost spread | avg £580k/MW at 1.9 h; 2 h median £650k/MW; 68 % within £400–700k/MW | transcribed | Modo Energy BESS CapEx Survey 2024, 30 participants, 2.8 GW |
| WACC | 5.0 % real (~7.1 % nominal) | transcribed | Modo model assumptions page |
| Asset life | 15 years | transcribed | Same |
| Degradation | ~67 % capacity remaining after 10,000 cycles (~12–15 y) | transcribed | Same |
| Cycling limit | 1–2 per day, warranty-aligned | transcribed | Same |
| Round-trip efficiency | 88 % | transcribed (weakly) | Modo's standard assumption, but **not** on the model-assumptions page itself — the least firmly sourced number in this module |
| Fixed OPEX | 2 % of capex/year | **assumed** | Modo do not publish it. FES routes battery opex to BEIS 2022 *Benefits of Long Duration Electricity Storage* instead. Flagged `OPEX_IS_PROXY = True` |
| Pack embodied carbon | 11.368 kg CO₂e/kg | transcribed | ecoinvent 3.9.1 apos, `market for battery, Li-ion, LFP, rechargeable, prismatic` [GLO], IPCC 2021 GWP100 |
| PCS embodied carbon | 15,930.86 kg CO₂e/unit = 31.9 /kW | transcribed | ecoinvent 3.9.1 apos, `market for inverter, 500kW` [GLO] |
| Pack energy density | 0.1158 kWh/kg | transcribed | ecoinvent's own dataset comment: a 203 kg pack holding 23.5 kWh gross. Its price comment independently cites 0.115 kWh/kg, and the cell figure (0.159 kWh/kg × 0.727 kg cell/kg pack) agrees to 0.2 % |

**Why Modo rather than NREL.** The FES 2025 Economics Methodology report
states NESO's Li-ion CAPEX is *"a combination of Modo survey data with CAPEX
data from the National Renewable Energy Laboratory"*. Modo's assumptions are
published openly and already in real 2025 GBP, so they need neither FX nor
deflation — unlike NREL, which is USD and US-market.

**Verification built in.** `check_against_ecoinvent()` re-scores both
ecoinvent factors and fails if they have moved by more than 0.1 %.

**Caveats printed by the module.** ecoinvent's LFP dataset is an electric-
vehicle traction pack (Dai et al. / GREET), reused for stationary storage —
standard practice, but an approximation in both directions. It carries no
container, racking, HVAC or fire suppression, because ecoinvent 3.9.1 has no
stationary BESS enclosure. And the battery's 15-year life against the data
centre's 25 means **1.67 builds** over the study horizon, which both cost and
carbon must carry.

---

## Renewable generation — embodied carbon per MW
`renewables.py`

ecoinvent supplies renewables as **per-kWh** activities with capital already
amortised over a lifetime output ecoinvent chose. This module strips that back
out to **kg CO₂e per MW installed**, so the burden of building capacity does
not depend on how much it happens to generate.

| Technology | Capital | ecoinvent implied LF | Restated at DESNZ LF | Grade |
|---|---|---|---|---|
| Onshore wind | 658 t CO₂e/MW | 26.2 % over 20 y | 5.6 g CO₂e/kWh (was 14.5) | transcribed / derived |
| Offshore wind | 890 t CO₂e/MW | 30.0 % over 20 y | 5.7 g CO₂e/kWh (was 17.1) | transcribed / derived |
| Solar PV | 2,303 t CO₂e/MWp | 11.0 % over 30 y | 56.7 g CO₂e/kWh (was 79.8) | transcribed / derived |

Capital scores are **transcribed** from ecoinvent 3.9.1 apos (`market for wind
turbine, 2MW, onshore` + its network connection; `market for photovoltaic
plant, 570kWp, multi-Si, on open ground`). The restatement is **derived**,
using DESNZ/Arup load factors and lifetimes from `tech_costs.py`.

**Verification built in.** `check_reconstruction()` re-amortises the per-MW
figure back over ecoinvent's own implied lifetime output and fails unless it
reproduces ecoinvent's published per-kWh score exactly. All three pass.

**Why it matters.** ecoinvent's GB onshore wind assumes 45,918 kWh/kW over
its life; DESNZ/Arup give 116,815 kWh/kW — **2.5× more**. Charging embodied
carbon per kWh at ecoinvent's rate overstates it by that factor. Notebooks 4.1
and 4.3 charge wind per kWh generated and so carry ecoinvent's assumption:
fine for a fixed plant, wrong once capacity is a decision variable.

**Known limitation.** ecoinvent's GB PV dataset is a **2012** multi-Si plant,
so 56.7 g CO₂e/kWh sits well above current literature (~20–40 g/kWh). It is a
conservative upper bound, not a current figure. Wind, being mostly steel and
concrete, is far less affected.

---

## Hydrogen chain — embodied carbon per unit of capacity
`electrolysers.py`, `fuel_cell.py`, `h2_storage.py`, assembled by `coefficients.py`

The same problem `renewables.py` solves, applied to the hydrogen chain: these
inventories amortise their capital over an output level their authors chose, and
the optimiser sizes capacity. Each module strips the capital back out and
asserts that re-amortising it at the original basis rebuilds the original
number.

### Electrolysers — `electrolysers.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| AE / PEM / SOEC capital | 432.4 / 260.8 / 362.8 t CO₂e per MW | derived | Hermesmann et al. capital good, scored on ecoinvent 3.9.1 apos and divided out of the per-kg activity |
| Rated capacity | **1 MW** each | derived | Only PEM states it. AE and SOEC are inferred from lifetime H₂ × specific energy, which lands on 160 GWh/MW for all three to within 0.2 % despite specific energies of 42.3–54.0 kWh/kg. `check_rating()` enforces it |
| Implied utilisation in the foreground | 160,000 full-load hours, **73 % CF** over 25 y | derived | The trap this module exists to escape: an electrolyser built to run at 20 % CF is under-charged **3.7×** by the per-kg figure |
| Variable burden | 0.042 / 0.107 / 1.628 kg CO₂e per kg H₂ | derived | Water, heat, electrolyte — genuinely per-kg, so left per-kg |
| Plant lifetime | 25 y | transcribed | NESO Green Hydrogen Data Portal, same figure as `electrolyser_costs_clean.csv` |

*No stack/BoP split is possible* — Hermesmann's capital good is one monolithic
activity, so the whole of it is charged on calendar life. Registered in
`DATA_GAPS.md`.

### PEM fuel cell — `fuel_cell.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Stack | 97.4 t CO₂e per MW, 32,000 h duty life | derived | Babatunde et al. 2024 Table S1; stack life their §3.4 |
| Balance of plant | 469.0 t CO₂e per MW, 60,000 h duty life | derived | ecoinvent 3.9.1 "fuel cell production, PEM 2 kW" net of its own stack and of the domestic-CHP hot-water kit |
| BoP **calendar** life | **25 y** | **assumed** | 60,000 h is a *duty* figure; at 200 h/yr it implies a 300-year asset. No public calendar life found. Charged over the same 25 y as the electrolyser and the data centre |
| Maintenance | 3.11 kg CO₂e per MWh delivered | derived | ecoinvent PEMFC maintenance net of the stack it bundles |
| Hydrogen consumption | 63.16 kg H₂ per MWh | derived | 1/(η 0.475 × LHV 33.33 kWh/kg) |

Both replaceable components are charged at
`max(1/calendar_years, full_load_hours_per_year/duty_hours)` — a maximum of two
linear functions, exact in an LP. This matters at both ends: charged on duty
alone a **backup** fuel cell is under-counted **16.4×**; charged on calendar
alone a **baseload** one is under-counted 3.7×. `check_full_duty()` asserts the
rule collapses onto the foreground's own per-kWh figure at 8,760 h/yr.

Hydrogen is excluded from every coefficient — the LP supplies it explicitly.

### Hydrogen storage — `h2_storage.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Gandiglio 28 bar vessel | 312.8 kg steel per kg H₂ → **1,595 kg CO₂e per kg** capacity | transcribed | Gandiglio et al. 2022, Table 3 — the as-built 21.6 m³ stainless vessel at Ginostra |
| Type I 200 bar cylinder | 100 kg steel per kg H₂ → **250 kg CO₂e per kg** capacity | assumed | ~1 wt% gravimetric capacity, a typical industrial stationary bottle. No Brightway activity exists for it |
| Vessel lifetime | 25 y, never replaced within it | transcribed | The paper's own plant life |
| Standing loss | **0 /h** | **assumed** | No boil-off exists for compressed gas at ambient temperature — that is a liquid-H₂ phenomenon. Real losses are fitting leakage, a maintenance question. **Load-bearing**: near-zero standing loss is exactly why hydrogen beats a battery over a season |

**The design choice is not a detail.** Per kWh *deliverable back through the fuel
cell*, the 28 bar vessel is 100.7 kg CO₂e/kWh against a Li-ion battery's 98.2 —
no advantage at all. The 200 bar cylinder is 15.8, six times better. Which
vessel the study uses decides whether hydrogen storage has an embodied-carbon
case. Both are built; run both.

---

## Demand-side network charges
`network_charges.py`

What the data centre pays to *import*, which until now the study omitted
entirely — imports were priced at the Elexon wholesale price alone, roughly half
of a real industrial bill. The omission was not neutral: it made every
grid-connected architecture look cheaper against exactly the on-site generation
that avoids the charges. The DESNZ/Arup connection figures in `tech_costs.py`
are **generator**-side and are not a substitute.

| Input | Value | Grade | Source |
|---|---|---|---|
| TNUoS HH demand tariff | zonal, **£0.00/kW (Scotland, floored) to £10.12/kW (South Western)**; London £7.41 | transcribed | NESO Data Portal, *TNUoS Tariffs*, CKAN datastore resource `6abe8416-149c-4c78-b65b-059eea19957a`, FY2026 Final. Fetched through the same API `h2_prices.py` uses, so it refreshes rather than going stale |
| TNUoS demand residual (TDR) | banded £/site/day; EHV2 = £270,752/yr | transcribed | Same portal, resource `dcca94fd-343e-4d4e-8c5d-66009dec4ad3` |
| BSUoS | £/MWh imported, half-yearly fixed; 2025 runs £12.17 → £10.74 → £15.69 | transcribed | Same portal, resource `4dfa533f-bec6-491b-a3f1-7ce92449bc9a` |
| DUoS unit and capacity | HV Site Specific: red 3.440, amber 0.262, green 0.008 p/kWh; capacity 9.19 p/kVA/day | transcribed | London Power Networks plc, *Use of System Charging Statement* LC14 v1.3, effective 1 April 2026, **Annex 1**. No open API exists for DNO charging statements |
| DUoS time bands | red = Mon–Fri 16:00–19:00, Nov–Feb | transcribed (red), **simplified** (amber) | The statement defines amber per-season; merged to one all-year window. Red is exact, and is an order of magnitude above amber |

**The shape matters more than the level.** Two of the four charges scale with the
*connection* rather than the energy, so a battery or hydrogen store that flattens
the import profile shrinks the connection and its charges while importing the
same annual energy. Modelling network charges as a flat £/MWh would erase
precisely the effect the study exists to measure.

For the 7.31 MW baseline in London: **£23.26/MWh on top of £79.83 wholesale**, a
delivered £103.09/MWh and **1.29x** the figure the study had been using. 38 % of
the addition is capacity- or connection-based.

**Location is the headline.** A 100 MW data centre pays about **£1.0 m/year** in
locational TNUoS at a South Western site and **nothing** in Scotland, whose
tariffs are floored — unfloored they are −£33.84 and −£23.62/kW. That signal
points the same way as the renewable resource, and it was entirely absent.

---

## Hydrogen-chain asset costs — the weakest numbers in the study
`h2_capex.py`

Three inputs the cost objective needs that **no UK source provides**. Every
figure is graded `assumed` and given as low/central/high spanning the full
published range rather than a point estimate with a nominal spread.

| Input | Value (real 2025 GBP) | Grade | Source and why it is weak |
|---|---|---|---|
| Fuel cell capex | £780 / £1,795 / £3,512 per kW | assumed | DOE, *Technical Targets for 100 kW–3 MW Stationary CHP/DG Fuel Cell Systems Operating on Natural Gas*. These are **natural-gas** systems including a reformer this study does not have, so biased high; the low case is an aspirational 2020 target at 100 MW/yr volume, not a price |
| H2 vessel capex | £427 / £658 / £889 per kg capacity | assumed | Range across the compressed-storage literature (EUR 500–1,040/kg; DOE 2005 status $1,100/kg at 430 bar). None is UK, none is recent, spread over 2x. **Gandiglio et al. 2022 supplies the inventory and should be checked for a cost too** |
| SOEC capex | PEM × 1.2 / 1.5 / 2.0 | assumed | **No source at all.** A guess about a technology gap, not a measurement |

For a 7.31 MW backup chain the fuel cell dominates below 22 t of storage and the
tank above it — so across the whole plausible range, hydrogen's cost is set by two
numbers with no UK source and spreads of 4.5x and 2x. **The carbon side of these
same architectures is fully sourced. Rank hydrogen options on carbon with
confidence, and on cost only with the caveat attached.**

---

## Site resolution
`sites.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Coordinate → outcode | reverse geocode, 2 km radius with an outcode fallback | transcribed | postcodes.io (Open Government Licence) |
| Outcode → Carbon Intensity region | region id and name | transcribed | NESO Carbon Intensity API, `/regional/postcode/{outcode}` |
| CI region → TNUoS demand zone | fixed 14→14 table | derived | Both schemes partition GB by **GSP group**, so the correspondence is structural. No open API publishes it. `check_zone_mapping()` asserts it is a bijection and that it agrees with three presets set independently from published sources |
| Offshore availability | by resolved region | assumed | Judged by region rather than distance to coastline, which would need a coastline dataset |
| Connection capacity | **not supplied**, defaults to unconstrained | — | No public register. See `DATA_GAPS.md` |

Near a region boundary the nearest-postcode hop can land on the wrong side. The
resolved region and zone are always reported rather than hidden, so a boundary
case is visible.

---

## Scope decisions

These are choices, not data. They are recorded in `ASSUMPTIONS.md` with their
consequences: the data centre runs flat at 100 %; geography is GB, reached by
swapping the data centre's US-SERC electricity exchanges rather than
re-authoring the inventory; hydrogen is always co-located with its use, so no
transport is modelled for any colour.

## Still open

Tracked in `DATA_GAPS.md`. At the time of writing, on the carbon side: the
fuel cell's BoP calendar life, hydrogen tank standing loss, battery standing
loss, and the absence of a stack/BoP split in the electrolyser inventory. On
the cost side: fuel cell capex, hydrogen tank capex, SOEC costs, battery fixed
OPEX, and demand-side network charges (DUoS/TNUoS) for the data centre's own
import — the DESNZ connection figures are *generator*-side and are not a
substitute.
