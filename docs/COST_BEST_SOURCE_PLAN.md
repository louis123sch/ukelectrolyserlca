# Plan: the best source for each cost input — 4 Nov 2026

**Rule (user, 4 Nov):** UK government where possible; if there is none, or it looks wrong, an authoritative alternative.
**"Looks wrong"** here means one of two things, and nothing softer: its method does not fit the use, or several independent authoritative sources contradict it.
"Government" includes NESO and reports departments commissioned. Follows `COST_GOV_FIGURES_PLAN.md` (built, uncommitted). Evidence: that file, `COST_SOURCE_SEARCH_2026-11-04.md`, `COST_SOURCES_NON_UK_2026-11-04.md`.

**Built 4 Nov 2026, evening (steps 1, A, C, D's losses and tank; B dropped), uncommitted at the time of writing; see *Built* at the foot.** After-figures below are hand arithmetic, 2025 pounds, with the discount rates of step C unless a column says otherwise; step 1 of the build replaces them with the code's own.

Foreign figures: inflate in their own currency (US: World Bank deflator; euro area: Eurostat `nama_10_gdp`), then convert at the study's FES 2025 rate (£1 = €1.17 = $1.2815).

## Corrections to what was said earlier
- **The stack's duty life is 30,000 h, not 80,000 h** (`fuel_cell.decompose`). 80,000 h is the rest of the system. So the stack needs no change: 30,000 h is inside the 20,000–40,000 h evidence.
- **The stack's "4 years against 10" mismatch mostly falls away.** Element Energy's 4 years is continuous running, about 32,000 h, which the model's duty limit already charges. The 10 years only applies to lightly used units.
- **ENSPRESO's solar sheet uses old region codes:** the 0.84 GW labelled UKI3 is old code UKI2, Outer London by the old scheme, and Inner London (old UKI1) is zero. To be confirmed against its conversion sheet in step B.

## Which source supplies what

### Replace: the current source looks wrong, or there is a better one
| Input | Now | Source to use | Figure | Why |
|---|---|---|---|---|
| **Solid-oxide capital, central** | £4,945/kW, BEIS ratio | **Danish Energy Agency**, Renewable Fuels (Aug 2026), sheet 80 SOEC 10 MW | €2,959/kW, 2025 € = **£2,529** | The UK method assumes a mature plant and lands above every range read. BEIS stays as the bracket: low £1,660, high £4,945. NESO cites this agency |
| **Fuel cell stack share** | 45.4 %, Element Energy | **Clean Hydrogen Partnership** SRIA Table 21 | €400 of €1,900 = **21 %** | 45 % is 77 % of Baringa's equipment figure and above all six others (11–41 %). Battelle stays as a range |
| **Fuel cell capital, low** | £2,015 | **US national lab** TP-91146 | $1,352 (2022 $) less US sales tax and grid spur, inflated = **about £946** | £2,015 is the same document as central, so it was no real range. Central and high stay UK |
| **Tank, low** | Rozzi, £392 | **Clean Hydrogen Partnership** Table 11 | €600/kg at 20 t = **£513** | An EU body, not a journal dataset; also ends the Rozzi licence question |
| **Tank, high** | Uncited €1,040 | **Danish Energy Agency**, Storage (151a) | €957/kg installed, 2020 €, inflated = **about £982** | Replaces a figure with no document. It is 200 bar, so it fairly bounds the top |
| **Battery, low** | Modo + unsourced £100 | Modo's published £400 at 1 h + **Ember** Oct 2025 | $125/kWh = £98/kWh, so **£302/kW + £98/kWh** | The extra-hour figure finally has a source, and nearly the same number |
| **Battery, high** | Central × Modo spread | **US Annual Technology Baseline 2025**, API | 2026, all-in, inflated: **£387/kW + £180/kWh** | Recent, every duration, stated scope. Includes US tax, so a fair top |
| **Bought blue hydrogen, central** | European observatory | **NESO** blue table | To read from `h2_prices` | UK government exists and was only the low case |
| **Discount rates** | 5.8 %, 5 %, 5 %, 6 % unsourced | **CEPA for DESNZ** (2025), Table E.1 | Wind, solar 7.6 %; battery 8.9 %; electrolyser 10.1 % | UK government, newer, one consistent method. Replaces an unsourced 6 % and a Modo rate. Fuel cell and tank have no row: 10.1 %, as "Hydrogen, emerging" and "Novel long duration" |

### Add: nothing is charged, or nothing limits
| Input | Source | Figure | Note |
|---|---|---|---|
| **Major-hazard compliance** | **HSE** assessment for COMAH 2015 | Upper tier £118k + £27k/yr, lower £20k + £10k, 2013 prices | UK. A step on tonnes held |
| **Finance during building, other assets** | **BEIS 2022**, 1 y battery; **BEIS annex**, 3 y electrolyser; **Mott for BEIS**, 1 y hydrogen store; **US national lab**, 3 y fuel cell | Hurdle rate over the build | As wind and solar |

### Keep: UK government, and it holds up
| Input | Source | Figure | Checked against |
|---|---|---|---|
| Wind, solar capital, running, life, load factor | DESNZ/Arup 2024 | As built | Reproduces its own LCOE within 1 % |
| Wind, solar land and rates | DESNZ/Arup §5.8, §6.8; DESNZ solar land | As built | Solar rent is near the report's 5–6 % of revenue. Rates survive SI 2022/405 |
| Battery capital and running, central | BEIS 2022 Exhibit 3.11 | £256/kW + £159/kWh | Mid-range: £683–1,560/kW at 7 h |
| Fuel cell capital, central and high | Baringa for DESNZ | £2,215, £2,700 | Others lower but modelled and unbuilt, and the US lab says a data-centre build costs more. The only built plant |
| Fuel cell maintenance, insurance | Element Energy; DESNZ ratio | £64/kW; 0.23 % | Danish 5 %, US lab $37.60/kW-yr: same order |
| Tank, central and running | Element Energy | £599/kg; 2.97 % | Danish £818–982, EU £513–641: inside |
| Solid-oxide running, fixed | BEIS annex | £0.50/kg; £67/kW | Danish stack 25,000 h and €388/kW gives about £0.58/kg |
| Membrane and alkaline | NESO | As built | Matches live feed |
| Gas, electricity prices, levies, network, connection | DESNZ, Ofgem, HMRC, NESO, network companies | As built | ±50 % test says connection needs no more |
| Supplier margin | CMA 2015 | £4.19/MWh | EDF's filings £4.35–6.12 |
| Inflation | ONS | As built | Add 2013 for HSE, and a forecast for 2026/27 |

### Keep the alternative: no UK figure exists
| Input | Source | Why |
|---|---|---|
| Fuel cell stack life 30,000 h | Nedstack, as reported; NREL, STAYERS, PNNL say 20,000–40,000 h | No UK figure in hours |
| Rest of system 80,000 h, 20 y | US DOE target, natural gas | Weakest here: sweep 40,000–80,000, carbon moves too |
| Tank minimum fill | Marocco 2021 | Physics, same vessel class |
| Grey hydrogen | European Hydrogen Observatory | UK row; NESO models no grey |
| Turquoise hydrogen | Constructed | A scenario, never a conclusion |

## Build order
Group the reruns at the end, so they run once.

**1. Baseline (XS).** Snapshot coefficients; save the current reference result. Commit what is built first, if you want it separate.

**A. Swap sources (S).**
- `h2_capex.py`: `_soec_capex_gbp_per_kwe`, `SOE_*` fixed share on the new capital, low and high as above; `FC_STACK_COST_FRACTION` from Clean Hydrogen; `FC_GBP_PER_KW["low"]`; `tank_capex_gbp_per_kg` low and high.
- `battery.py`: `cost_components` low and high.
- `h2_prices.py`: blue central; regenerate `h2_prices_recommended.csv`.
- `source_register.py`: add Danish Energy Agency (both), Clean Hydrogen SRIA, US lab TP-91146, ATB 2025, Ember; retire `rozzi_2024` and `h2_vessel_literature`.
- Pin every new central in `tests/test_coefficients.py`. Update the battery-case test: low power is now above central, by design.

**B. Land: dropped (user, 4 Nov).** A central London data centre with wind is not a real case; a London run is illustrative. No regional limit, no urban land rent. The model keeps rural rents and no area limit, stated in `ASSUMPTIONS.md` §4. ENSPRESO and MHCLG stay in the evidence if this ever comes back.

**C. Discount rates and finance (S, large effect).**
- `tech_costs`: CEPA's rate for the annuity, keeping the report's rate for the LCOE check. `battery.WACC_REAL`, `h2_capex.FC_DISCOUNT_RATE`, `dc_inputs.DISCOUNT_RATE`. Connection keeps NESO's own annuity.
- Finance factor for battery, electrolyser, fuel cell, tank.

**D. Smaller items (S each).**
- Major hazard: a reported adder first; an on/off switch in `dc_model` only if it moves a design. Rule 3 decides.
- Transmission loss: `levies.TLMO_OFFTAKING_ASSUMED` becomes Elexon's four seasonal estimates.
- Tank design: `optimiser_lca/h2_tank.TANK_DESIGNS` gains the bulk carbon-steel vessel as default, Gandiglio's kept as the sensitivity (cut-off rule's substitution clause). Carbon moves, so its own commit.
- `sensitivity`: one sweep over the assumptions below.
- One price base: network charges, levies, connection prices from 2026/27 to 2025 money, with an OBR deflator.
- `cost_exclusions.py`: move what is now built out of `open`.

**E. Records and runs (run time, hours).** Full test suite; `SOURCES.md`, `DATA_GAPS.md`, `ASSUMPTIONS.md`, `TODO.md`; both maps rebuilt; reference cases; one ±50 % case; `sensitivity cost_cutoff`.

## What it does
Hand arithmetic at the build's scale, rates of step C.

| Per unit | Built today | After A–C |
|---|---|---|
| Wind, £/MW/yr | 180,544 | about 210,000 |
| Solar, £/MWp/yr | 57,591 | about 74,000 |
| Battery power, £/MW/yr | 31,025 | about 39,000 |
| Battery energy, £/MWh/yr | 16,508 | about 21,700 |
| Tank, £/kg/yr (rural) | 66.76 | about 86 |
| Fuel cell at calendar life, £/MW/yr | 275,000 | about 322,000 |
| Solid-oxide, £/MW/yr | 454,272 | about 347,000 |
| Membrane, £/MW/yr | 212,511 | about 277,000 |

Everything built on site gets dearer against imports, so designs move towards the grid. The reference result, £128.0 m, will move with them. That reference run, the cost map and the ±50 % test are all at a London coordinate, which is illustrative only. **North Norfolk is the reference site for conclusions (user, 4 Nov)**: step E runs its reference cases and the ±50 % test there, and London stays as a demo.

## The gaps: filled, or assumed
Second search and calculation, 4 Nov. Each assumption is graded `assumed` in the trace, sits on the cost map as one, and goes in one sweep at step E, so a result that depends on it shows. Scratch working: pressure-vessel wall by the standard cylinder formula (SA-516 Gr 70, 138 MPa allowable, 110 % design pressure, 3 mm corrosion allowance), Sinnott & Towler cost by shell mass from the held Capital Equipment Cost Database.

### Filled
| Gap | How | Result |
|---|---|---|
| **Tank at 28 bar** | Steel per kg of hydrogen barely moves with pressure: about 160 kg at 28, 50 and 80 bar. Same correlation, as a ratio to Element Energy's vessel (405 kg in 95 m³, about 50 bar) | 95 m³ at 28 bar £674/kg; 200 m³ £587; 500 m³ £505. **Central £599 holds** for bulk. EU's £513 agrees with the 500 m³ figure. Small 21.6 m³: £1,004 |
| **Transmission loss factors, exact** | Elexon's public Transmission Loss Factor report (Power BI, no login): `elexon.co.uk/bsc/operational/transmission-losses/transmission-loss-factors-analysis/`. All 14 zones × 4 seasons read 4 Nov, saved in `cost sources/5 prices and inflation` | Replaces `levies.TLF_ZONE_2026_27`. All 56 within 0.0005 of the chart readings; their mean gives the report's own all-zone 0.00524. Moves little, but ends the "read from charts" flag |
| **Transmission loss top-up** | Elexon's published 2026/27 offtaking estimates, by season | 0.00948, 0.01068, 0.00991, 0.00671, replacing an assumed flat 0.011. Elexon calls them indicative. London's mean multiplier: 1.0334 to 1.0314 |
| **Compressor** | Compression power already sits in `cap_ely`: 47 kW per MW of solid-oxide at electrolyser rates, about **£120k/MW**. Calculated range for a 10 MW site: textbook about £72k (installed), Element Energy extrapolated £157k, Danish £215k | **Already charged, inside the range.** No new line; adding one would double count. Zero on the default |

### Assumed
| Gap | Assumption | Basis | Range to sweep |
|---|---|---|---|
| **Tank level** | Central stays £599/kg | One quote, but other sources sit either side. The textbook correlation in absolute terms is about £1,090/kg before installation, 1.8× it, so level is uncertain even though pressure is settled | £513–982/kg |
| **Tank and carbon vessels differ** | **Bulk carbon-steel vessel, 161 kg of steel per kg** in place of Gandiglio's 313 kg stainless on the carbon side | The calculation above: a stated plausibility check, as the substitution clause asks. Gandiglio is a 21.6 m³ small stainless buffer (calculated 178 kg in carbon steel). Carbon side only, so its own commit | Gandiglio kept as the sensitivity |
| **Fuel cell life at MW scale** | **Stack 30,000 h as now**, in stacks that do not change with plant size, since a MW plant is many stacks in parallel | Nedstack: over 23,000 h demonstrated at stack and 65,000 h at plant, largest plant over 2 MW (its slides at the DOE workshop, 2019, read); over 33,000 h on a 60 kW system (SINTEF slides, 2013, read); 2.3 mV per 1,000 h, about 30,000 h projected (journal paper, search snippet); STAYERS over 20,000 h | 20,000–40,000 h; rest of system 40,000–80,000 h |
| **Today's UK battery price** | Central stays BEIS; **real UK project funding is now the check** | Thorpe Marsh: £1,039 m, 1,400 MW / 3,100 MWh, Sept 2025 (National Wealth Fund, government-owned) = £335/kWh, £742/kW at 2.2 h, against the fit's £607. Coalburn 2 and Devilla: £800 m, Jan 2025, 1 GW / 2 GWh (sizes from the 1.5 GW / 3 GWh portfolio) = £400/kWh, £800/kW, against £573. Funding, not stated as cost, so it likely includes finance and reserves. Carrying Thorpe Marsh to 7 h at £98–159/kWh gives £1,212–1,505/kW, either side of the central £1,379. No UK project at 7 h | £1,008–1,647/kW at 7 h; the high case is closest to these projects at 2 h |
| **Generators' connection behind the meter** | Keep it all in capital | On-site cable and transformers are still needed, and DESNZ does not split them | Take out 5 % of wind and 12 % of solar capital: wind about −3.5 %, solar about −9 % a year |
| **Battery business rates** | Zero to 2035 | SI 2022/405's memorandum names storage used with renewables | Solar's £1.8k/MW |
| **Tank insurance, rates** | Inside the 2.97 % | BEIS says its fixed cost holds insurance and local taxes; Element Energy does not itemise | Wind's ratio, 0.23 % + 0.76 % of capital |
| **Supplier margin** | £4.19/MWh stays | CMA | EDF's £6.12/MWh |

**No source and no sound assumption yet:** nothing. Every gap in the model now has a source or a labelled assumption with a range. That is not the same as being known: the tank's level and the battery's current price are the two most able to move a result.

## Calls, confirmed by the user 4 Nov
North Norfolk (52.85, 1.04) is the reference site; `sensitivity.CASES` already has it islanded (`islanded_h2`), so step E adds a grid-connected case there. Discount rates: the 2025 study on every asset. Solid-oxide capital: Danish £2,529/kW. Stack share: EU 21 %. Tank carbon: bulk steel, in a separate commit.

- **CEPA's rates everywhere,** wind and solar included, over the 5.8 % and 5 % in DESNZ/Arup. Both are government; CEPA is newer and is the only one covering every asset.
- **Solid-oxide and stack share leave UK government,** by the "looks wrong" test.
- **The tank's carbon moves to a bulk carbon-steel vessel,** an assumption from the calculation above, replacing a sourced inventory for a small stainless one.
- **No new compressor line,** because the model already charges about the right amount by another route.
