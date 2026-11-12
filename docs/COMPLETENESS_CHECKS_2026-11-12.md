# Completeness checks, 12 Nov 2026

Four checks for the question "how complete is the hybrid data-centre model?", aimed at what the testing so
far cannot see: the testing covers the uncertainties we know about, so these look for the ones we do not.
**Nothing was solved, rebuilt or changed.** Every figure here comes from the code and saved outputs on
branch `source-update` (commit 5cd2758), from one saved run, and from published sources. The scratch
arithmetic is outside the repository.

| # | Check | What it can catch |
|---|---|---|
| 1 | Top-down carbon: capital cost × UK government carbon per pound, against our inventories | Whole groups of materials or parts an inventory leaves out |
| 2 | Life-cycle stage and cost category checklist per asset | A stage or cost line that is neither inside the model nor declared outside it |
| 3 | Headline results against published studies | A result far from what similar systems give |
| 4 | Fresh-eyes review of the notes and model structure | Modelling choices a referee would question that our notes do not mention |

**Headline.**
- The fuel cell's inventory captures about a tenth of what its price implies, which makes it the one large
  gap these checks found.
- The electrolyser and the grid intake are also low, but they matter little at North Norfolk.
- Wind, the battery's cells, solar and the tank pass.
- Costs and carbon sit inside the published range once the data centre building is taken out of our carbon
  figure.
- The fresh-eyes review adds two model gaps a referee would raise first: the battery never wears out, and
  bought hydrogen can arrive at any rate.

---

## 1. Top-down carbon check

### Method

For each asset: top-down carbon = capital cost × the UK government's carbon per pound for the industry
that makes it. The UK government's figure is the "spend-based emissions multiplier" for that industry. We
then compare our inventory (bottom-up) with it:

> the inventory captures X % of the top-down estimate = bottom-up ÷ top-down.

The comparison is for **one build of each asset**: its manufacture and installation, without later
replacements. On the cost side that is the initial capital. On the carbon side it is one build's
inventory, for example one fuel cell stack, not the stacks over the asset's life.

**The factors.** Defra, *UK and England's carbon footprint to 2023* (published 30 June 2026, updated 24
July 2026), workbook "Spend-based emissions multipliers, 1997 to 2023":
- sheet `SIC_multipliers_2023`, column "Greenhouse gases (kgCO2e per £)";
- [statistics page](https://www.gov.uk/government/statistics/uks-carbon-footprint);
- [workbook](https://assets.publishing.service.gov.uk/media/6a3ce5fa33bc5beefd3c4983/spend_based_emissions_multipliers_1997_to_2023.ods);
- [methods paper](https://assets.publishing.service.gov.uk/media/6a3ce626eaee00074150f449/UK_and_England_s_Carbon_Footprint_Summary_of_Methods_2026.pdf)
  (University of Leeds; §1.4 pp. 5–6 for gases, §2.2.2 pp. 9–10 for prices).

The industries follow the UK standard industrial classification (SIC). This is the newest edition; older
editions called these figures "conversion factors by SIC code". A UK government source exists, so no
fallback was needed.

| Industry row (as published) | kg CO2e per £, 2023 |
|---|---|
| 27 Electrical equipment | 0.8428 |
| 28 Machinery and equipment n.e.c. | 0.5116 |
| 25OTHER Fabricated metal products (25.1–3, 25.5–9) | 0.5677 |
| 26 Computer, electronic and optical products | 0.5364 |
| 42.1–2 Civil engineering | 0.2655 |
| 71 Architectural and engineering services | 0.1617 |

No finer split is published. For example, transformers, batteries and cables are all inside row 27.

**What the factors cover, and how prices were handled.**

- *Price year.* The factors are per pound spent in 2023. The model's capital costs are held in 2025 pounds
  (`optimisation/price_base.py`, `BASE_YEAR`) before the single step to 2026. Each capital cost was taken
  back to 2023 pounds with that industry's own producer price index, from the ONS PPI dataset (October
  2026 release). The 2025 ÷ 2023 ratios were:
  - row 27: 135.4/127.2
  - row 28: 140.4/130.6
  - row 25: 152.4/145.3
  - row 26: 120.2/115.4
  - civil engineering: 143.6/137.4, from ONS construction output prices for infrastructure new work
  - services: the GDP deflator, as the model uses.

  The wind and solar figures in DESNZ/Arup 2024 are already in 2023 pounds, so the factors apply to them
  directly. Using the GDP deflator for everything instead moves no ratio by more than one percentage
  point.
- *Basic against purchaser prices.* The factors exclude VAT (workbook, note 5). The methods paper builds
  them at basic prices, without margins or product taxes. That is our reading of §2.2.2; the workbook does
  not say so in words. Our capital costs are what a developer pays: excluding VAT, but including the
  supplier's margin, delivery and installation. Applying a basic-price factor to those pounds overstates
  the top-down figure by roughly the margin share, perhaps 5–15 % for plant bought direct. So the
  "captures" percentages below are, if anything, slightly low. No flag depends on that margin.
- *What the factors count.* Full supply chain, imports included (a ten-region world model). The seven
  Kyoto gases are weighted by the IPCC's 2014 warming values (AR5), while the study uses the 2021 values;
  the difference is a few per cent. The factors do not count the suppliers' own factories and machines,
  which ecoinvent does, so they lean slightly low against us.
- *Read the factors as averages.* A row is an average over a broad product group, so ±30 % is about
  as precise as this check gets. The verdicts only flag ratios well outside that band.

### Results

Bottom-up figures:
- carbon coefficients: `optimisation_outputs/tech_lca_coefficients.csv` (built 11 Nov 16:04, after today's
  tank change);
- step records: `optimisation_outputs/lca_map.json`;
- step-up transformers and cut-off estimates: `optimiser_lca/exclusions.py`.

Capital costs:
- `tech_costs.py`, `battery.py`, `h2_capex.py`, `connection_cost.py`;
- the cost map (`optimisation_outputs/cost_map.json`), unchanged by today's commit apart from a tank-life
  note.

| Asset (one build) | Industry matched, and why | Capital (2025 £) | Top-down | Bottom-up | Inventory captures |
|---|---|---|---|---|---|
| **Onshore wind**, per MW | Split as the DESNZ/Arup cost table splits it: pre-development £81/kW to row 71 (services); construction £1,204/kW to row 28 (turbines are "engines and turbines", inside machinery); infrastructure £303/kW to row 42 (roads, foundations, cabling) | 1,708,378 | 712 t | 670 t (ecoinvent's 20-year turbine + its network connection + Leng step-ups) | **94 %** (82 % if all at row 28) |
| **Solar**, per MWp | Pre-development to row 71; construction (modules, inverters, frames) to row 26, where cells sit; infrastructure to row 42 | 707,880 | 324 t | 910 t (Smith/IEA PVPS plant + step-ups) | **281 %** (190 % with construction at row 27) |
| **Battery power** (inverter side), per MW | Row 27: inverters and step-ups are electrical equipment | 190,744 | 151 t | 49 t (500 kW inverter, container step-up, switchgear estimate) | **33 %** |
| **Battery energy** (cells, racks, container), per usable MWh | Row 27, which holds batteries (27.20) | 180,090 | 143 t | 115 t | **81 %** |
| Battery as built at lowest cost (98 MW / 852 MWh) | Row 27 | 172.1 m | 136 kt | 103 kt | **75 %** |
| **PEM electrolyser**, per MW | Row 28 (process machinery). Shown as a range because the plant is part electrical (row 27) and the price includes site work (row 42) | 2,010,000 | 956 t (row 28); range 511–1,591 t | 220 t (balance of plant + one stack) | **23 %** (range 14–44 %) |
| **Hydrogen tank**, per kg held | Row 25 for the vessel (tanks and reservoirs are fabricated metal). The 23 % installation share (Element Energy's ×1.3) goes to row 42 | 599 | 0.29 t | 0.47 t | **164 %** (144 % all at row 25) |
| **Fuel cell**, per MW | Row 27 for the equipment, £1,300/kW (Baringa for DESNZ, p. 52: "over £1,300/kW"); the rest of the £2,215 installed figure to row 42 | 2,215,000 | 1,262 t | 165 t (balance of plant + one stack + step-up + switchgear estimate) | **13 %** (9 % all at row 27; 16 % all at row 28) |
| — fuel cell stack alone | Row 27 | 466,316 | 369 t | 97 t | 26 % |
| — fuel cell balance of plant + step-up | Row 27 | 1,748,684 | 1,384 t | 68 t | **5 %** |
| **Step-up transformers** | Row 27 (27.11). **They have no cost of their own:** the model reads them as inside each parent asset's capital (ASSUMPTIONS §4), so they cannot be tested apart. They are 1–10 % of each parent's carbon, so they cannot move the parent ratios above | — | — | — | not testable |
| **Grid intake substation**, 33 kV, per MW | Row 27 if read as equipment, row 42 if read as civils. The DNO price list is an installed figure covering transformers, switchgear, civils and land | 182,527 | 45–145 t | 12 t | **8–26 %** |
| **Grid cable**, 33 kV, per km of route (2 circuits) | Row 27 (cable is 27.3) or row 42 (trenching) | 1,068,369 | 271–846 t | 696 t (ecoinvent overhead line per km, a proxy) | **82 %** (row 27) to 256 % (row 42) |
| Grid connection as built (24.5 MW, 14.8 km) | Row 27 | 20.2 m | 16.0 kt | 10.6 kt | **66 %** |

### What it says

**Wind passes; solar and the tank sit above their top-down.** Above means "check the mapping", not
"inventory missing". A spend-based factor for "electronic products" averages chips, instruments and
phones. It cannot see that a solar module's polysilicon is made with coal-heavy electricity, or that
module prices have fallen faster than their carbon. Our solar figure agrees with IEA PVPS (about
1,048 kg CO2e per kWp in `renewables.py`), so the inventory stands and the factor is the weak side here.
The tank is a thick steel vessel, heavier in steel per pound than the average fabricated-metal product,
so being above is the expected direction.

**The battery's cells pass (81 %); its inverter side is low (33 %).** The inverter-side price is the
intercept of a cost line fitted against duration (`battery.py`, `cost.battery.power_per_kW`). It carries
every per-project cost that does not scale with hours, so the gap is partly a price artefact. It is a
small term: 0.6 % of the lowest-cost design's carbon.

**The fuel cell is far below (13 %; balance of plant 5 %): likely missing flows.** This is the one large
finding. The balance of plant is Usai et al.'s 80 kW vehicle system taken per kW, plus one inverter and
one container per MW (`optimiser_lca/fuel_cell.py`). A megawatt-scale plant also has a hydrogen supply
skid, heat rejection, buildings or enclosures beyond one container, foundations, controls and safety
systems, and none of these is counted. The price side has its own problem: Baringa's £2,700/kW is a
Korean phosphoric-acid plant (SOURCE_HUNT §2), so it is not a like-for-like plant either. The project
already records "no MW-class hydrogen PEM inventory exists" as a stated limitation (DATA_GAPS, closed 23
Oct). What this check adds is its likely size:

| Point | Fuel cell carbon now | If raised to the top-down figure | Share of the point's total |
|---|---|---|---|
| Lowest cost (57 MW) | 0.7 kt/yr | +5.0 kt/yr | +9 % |
| Knee (74 MW) | 1.0 kt/yr | +6.5 kt/yr | +15 % |
| Lowest carbon (132 MW) | 1.7 kt/yr | +11.5 kt/yr | +27 %; +48 % of the supply-only carbon (see §3) |

That is an upper bound from a crude method, not a correction. But it is large enough that the lowest-carbon
design, which leans on 132 MW of fuel cell, could change. The present tests push the stack's carbon
×0.5/×1.5 but not the balance of plant's, and even ×1.5 on the whole fuel cell would not reach the
top-down figure.

**The electrolyser is low (23 %, range 14–44 %).** Gerloff's unit does include power electronics, a
compressor, a container and a foundation (`optimiser_lca/hydrogen.py` around lines 609–706). The likely
gaps are plant-scale items: water treatment, cooling, buildings, and the engineering and site share of
NESO's installed price. It is built only at the lowest-carbon point (33 MW). Raised to its top-down figure
it would add about 2.2 kt/yr there, 5 % of that point's total.

**The grid intake is low (8–26 %) but immaterial.** The DNO price buys a whole substation, while the
inventory counts transformers, civils and estimated switchgear. At 24.5 MW it is 0.3 kt/yr of a 53 kt/yr
total, and the cable, which is most of the connection's carbon, is in line.

---

## 2. Life-cycle stage and cost category checklist

Each cell is one of:
- **in** — counted, with where;
- **boundary** — excluded by ASSUMPTIONS §3, §6 or §7 and listed as a boundary row in
  `optimiser_lca/exclusions.py` or `optimisation/cost_exclusions.py`;
- **register** — unsourced, tested under the 1 %/5 % rule and left out;
- **est.** — carried as a cut-off estimate;
- **MISSING** — neither counted, nor boundary, nor on a register: a finding.

### Carbon: the stages of the European standard for construction-product declarations (EN 15804)

| Asset | Materials and making (A1–A3) | Transport to site (A4) | Installation (A5) | Maintenance, repair, replacement (B2–B5) | Operating energy (B6) | End of life (C1–C4) | Credits beyond the system (D) |
|---|---|---|---|---|---|---|---|
| Onshore wind | in: ecoinvent 3.9.1 turbine and its network connection (`optimisation/renewables.py`); step-ups (`optimiser_lca/stepup_transformers.py`, Leng 2026) | boundary for the step-ups (Leng S2). **ecoinvent's turbine is used whole, so any to-site legs inside it stay in.** Not stated anywhere; small | in: foundation inside ecoinvent's turbine; step-up pads (Leng S3) | in: lubricating oil (`restate` residual); life-extension parts from 20 to 35 years (DATA_GAPS "Wind life extension"). Step-up replacement: register, 0.40 % | in as energy: step-up losses (`conversion_losses.py`); turbine own use inside the net load factor | boundary; database end-of-life residual stated (§6) | boundary (no credits, §5) |
| Solar | in: Smith 2024 / IEA PVPS rebuild (`optimiser_lca/upv.py`); step-ups | boundary (Smith A14 rows) | in: installation diesel (Smith A14) | in: Smith A15 operation and maintenance; inverter replacements via the inverter count over 30 years (`upv.py` note 3); step-up replacements | in as energy: step-up losses | boundary | boundary |
| Battery, inverter side | in: ecoinvent 500 kW inverter (`battery.PCS_ACTIVITY`), container step-up, switchgear est. | boundary | register: crane and commissioning diesel, 0.20 % | asset annualised over its own 15 years; **no fade or cycle limit in the model** (check 4, B2) | in: round-trip efficiency, self-discharge 0.0143 %/h, step-up losses. Cooling and control load folded into round-trip efficiency (user, 11 Nov) | boundary | boundary |
| Battery, cells and container | in: Jasper/Voß (`optimiser_lca/bess.py`), foundation block in | boundary (Jasper's China-to-Germany legs) | register, as above | as above | as above | boundary | boundary |
| PEM electrolyser | in: Gerloff plant and stack (`optimiser_lca/hydrogen.py`) | boundary (Gerloff's second 250 km leg) | in: foundation concrete and building-machine diesel | in: stacks (three per 25 years), water per kg | in as energy: kWh per kg in the model. Standby and hot-idle draw not modelled (check 4) | boundary | boundary (oxygen unallocated) |
| Hydrogen tank | in: shell, forming, frame, pad (`optimiser_lca/h2_tank.py`) | boundary | in: pad; erection not itemised | none over 25 years; valves and pipework est. (1.44 %) | in: leakage, charged at warming potential 11.6 (`dc_model.H2_GWP100`); compression zero at 28 bar | boundary | boundary |
| Fuel cell stack | in: Babatunde 2024 (`optimiser_lca/fuel_cell.py`) | boundary | n/a (inside the balance of plant) | in: replaced on max(calendar 10 years, 30,000 h) | in: net efficiency | boundary | boundary |
| Fuel cell balance of plant | in: Usai 2021 loops, inverter, container, step-up, switchgear est. | boundary | **MISSING**: no foundation, building or site work, and not on the register (only "assembly energy" is, at 0.97 %) | in: filters and coolant per 8,000 h; replaced on max(20 years, 80,000 h) | in: step-up no-load loss on standby | boundary | boundary |
| Step-up transformers | in: wind (Leng), solar (IEA PVPS), container units (Jasper mass on IEA composition) | boundary | in for wind and solar (pads, station building); none for the container units | solar replacements in; wind's on the register | in as energy | boundary | boundary |
| Grid connection | in: two 100 MVA units (Leng), switchyard civils, line per km (overhead-line proxy); switchgear, steelwork, factory energy est. | boundary | in: civils; construction machinery est. | **MISSING**: no maintenance (insulating-gas top-up, oil, parts) and none on the register; 40-year life, no replacement | in: delivery losses on imports; intake no-load loss | boundary | boundary |
| Data centre facility (for completeness) | in: Zhang 2025 (`optimiser_lca/data_centre.py`) | boundary | in: construction energy and water | in: refrigerant top-up | in: the facility's energy and water per MWh | boundary | boundary |

### Cost: the categories DESNZ's generation cost reports use

| Asset | Pre-development | Construction | Infrastructure | Fixed running cost | Variable running cost | Insurance | Connection and use of system | Decommissioning |
|---|---|---|---|---|---|---|---|---|
| Onshore wind | in (£81/kW) | in | in | in | n/a in source | in (£3.6k/MW/yr) | generator's own charges removed (no export); land and business rates added | boundary (cost register) |
| Solar | in (£24/kWp) | in | in | in | n/a | in | as wind | boundary |
| Battery | **not stated**: NESO/Modo give one total | in | in (connection read as the site's) | in (NESO, from BEIS 2022) | **MISSING**: no cost for capacity fade or top-up | **not stated** in source; not on register | through the site's connection | boundary |
| PEM electrolyser | **not stated** (NESO portal capital) | in | **not stated** | in (2.75 % of capital) | in: stacks and water per kg made | **not stated**; not on register | through the site | boundary |
| Hydrogen tank | **not stated** | in (installed, ×1.3) | in | in (2.97 %) | n/a | **not stated**; not on register | n/a | boundary |
| Fuel cell | in (installed plant) | in | in | in (Element Energy) | stacks and balance of plant on max(calendar, duty) | est. (wind's ratio) | through the site | boundary |
| Step-up transformers | read as inside each parent's capital (deliberate, ASSUMPTIONS §4) | | | | | | | |
| Grid connection | n/a | in (DNO price list) | in (cable) | in (0.43 % of capital) | n/a | n/a | in: national and local network charges, balancing charge, levies, losses | boundary |

Two lines DESNZ adds outside its own tables:
- *Business rates:* in for wind and solar, and zero for the battery (exempt to 2035, on the register).
  **MISSING for the electrolyser, fuel cell and tank**, which are rateable plant.
- *Land:* in for wind and solar; estimated for the tank; battery and fuel cell tested and left out.
  **MISSING for the electrolyser.**

### Findings: blanks that are neither boundary nor register

| # | Gap | Size | Suggested handling (for discussion) |
|---|---|---|---|
| 2.1 | Fuel cell balance of plant: installation, foundations and buildings | Part of the check-1 gap above; likely the largest single carbon gap | Add to the cut-off register with an estimate. Better, treat as part of the "no MW-class inventory" limitation and test it (summary) |
| 2.2 | Grid connection maintenance (carbon) | Small: transformer service is a minor share of its life cycle once losses are charged as energy | One register row |
| 2.3 | Battery fade: no cost, and no carbon effect through extra capacity | 10–17 % on the battery's per-usable-MWh cost and carbon (check 4, B2) | Model change, or a stated limitation with a ×0.5/×1.5 test on battery cost |
| 2.4 | Business rates on the electrolyser, fuel cell and tank; land under the electrolyser | Fuel cell rates, if like solar's £1.8k/MW, are under 1 % of its £221k/MW/yr; electrolyser land is similar | Register rows; likely pass the 1 % test |
| 2.5 | Insurance and pre-development for the battery, electrolyser and tank: the sources give totals and do not say whether these are inside | Insurance at wind's ratio (0.23 % of capital a year) is about 2 % of each annual coefficient, so it would **fail** the 1 % test, as the fuel cell's did (2.3 %) | Carry as an estimate, as for the fuel cell, unless the source is shown to include it |
| 2.6 | Transport legs inside ecoinvent's turbine datasets, against a boundary that excludes transport to site | Small, and inside the background (the same kind of residual as end-of-life, §6) | One sentence in ASSUMPTIONS §6 |

---

## 3. Results against published studies

**Which run.** Tonight's sign-off had written no North Norfolk run under the branch's
`optimisation_outputs/dc_runs/` when this was written; the folder does not exist yet. Step 2 of the
sign-off ("every test") has already **failed**: three map tests fail because today's source update made the
cost and carbon maps out of date (`optimisation_outputs/signoff/2026-11-11_1608/step_2.log`). So the
numbers below are the presented run:

`C:\Users\ls1524\Desktop\ukdclca\optimisation_outputs\dc_runs\r10_52.8500_1.0400_100MW_2025_custom\00_custom_gwsbetfx_pem_green`
(main checkout, 11 Nov 13:38).

It was made **before today's input changes**:
- Bought green hydrogen was about £5.1–5.9 per kg; it is now £10.62 delivered in 2026 £.
- The grid share behind bought green hydrogen was 0.5; it is now 0.7.
- The tank was 555.5 kg CO2e per kg held; it is now 463.1.

If no design changed, the new hydrogen price would add at most about **£12/MWh at lowest cost, £23 at the
knee and £25 at lowest carbon**. These are upper bounds, from the hydrogen bought at each point × about
£5.5/kg; the optimiser will re-plan around it.

**Our results** (140 MW flat demand, 1,226 GWh a year, every hour served):

| Point | £/MWh | g CO2e/kWh, as reported | g CO2e/kWh, supply only | Wind / solar | Battery | Fuel cell | Electrolyser / tank | Grid | Bought hydrogen | Wind+solar curtailed |
|---|---|---|---|---|---|---|---|---|---|---|
| Lowest cost | 125.9 | 43.6 | **28.8** | 263 / 320 MW | 98 MW / 852 MWh (8.7 h) | 57 MW | — | 24.5 MW | 2,640 t/yr | 23 % |
| Knee | 138.0 | 36.4 | **21.6** | 355 / 229 MW | 68 MW / 543 MWh (8.0 h) | 74 MW | — | 24.5 MW | 5,100 t/yr | 44 % |
| Lowest carbon | 164.4 | 34.6 | **19.8** | 460 / 117 MW | 9 MW / 35 MWh | 132 MW | 33 MW / 34 t | 0.6 MW | 5,550 t/yr | 59 % |

**"Supply only" matters for any comparison.** The reported g/kWh includes the data centre's own building,
servers and water. That is `dc_fixed_gwp_per_year`, 15.4 kt a year, plus 2.24 kg per MWh, about
**14.8 g/kWh** at every point (`dc_model.py` around line 921). Published supply studies leave that out.
Our £/MWh does not include the building (cost register: "the £/MWh is not an all-in figure"), so the two
headline figures have different scopes. That should be said wherever they appear side by side.

**Published studies.** Each was opened by a helper on 11 Nov. Figures from Rollinson and the Royal Society
were re-checked against the papers' text for this note. Conversions to 2026 £ are rough: consumer price
inflation plus annual-average exchange rates. Use them only for "same range or not".

| Study | System | Published figure | ≈ 2026 £ | Comparable? |
|---|---|---|---|---|
| Riepin & Brown 2022, TU Berlin, [Zenodo 7180098](https://zenodo.org/record/7180098) | Flat load, every hour clean, 2025; wind, solar, battery, **plus hydrogen in salt caverns**; Ireland, Germany, west Denmark, Netherlands; surplus sold | €84.7–113.5/MWh (2020 €) with hydrogen; €154–229 without | £98–132; £179–267 without | Closest palette; ours is islanded, uses tanks, sells nothing |
| Riepin & Brown 2024, *Energy Strategy Reviews* 54:101488, [doi](https://doi.org/10.1016/j.esr.2024.101488) | Same model, one weather year, 3-hourly | Ireland 220 MW load needs 4.0 GW wind+solar without hydrogen; hydrogen cuts the premium for every hour to +42 % | — | Same lesson: hydrogen for the last hours |
| Xu, Manocha, Patankar & Jenkins 2021, Princeton, [Zenodo 6229426](https://zenodo.org/record/6229426) | Hourly-matched buyers in California and the US mid-Atlantic grid, 2030 | $79.7–99.5/MWh (2020 $) for 100 % with today's technologies; $64–68 with clean firm plant | £65–101 | Grid-tied, US; agrees that a fuel bought for the last few per cent is cheapest, which is our lowest-cost design |
| Rollinson, Urquhart & Thomson 2025, *Energies* 18:382, [doi](https://doi.org/10.3390/en18020382) | **50 MW flat off-grid data centre**, wind + solar + 10 h battery + gas engines, 3 % interest | £70–102/MWh; **21–74 g/kWh**; south-west England £102 and 48 g, wind capacity factor 31 % | ~£80–120 | Same set-up and country; gas instead of hydrogen; a 3 % interest rate against our 7.6–10.1 % |
| Baranko et al. 2024, [offgridai.us](https://www.offgridai.us/) (white paper, not peer reviewed) | Off-grid solar + battery + gas, 100–1,000 MW data centre, Texas | $93–109/MWh at 44–90 % renewable | £71–90 | Low: sunny, US tax credits, gas fills 10–56 % |
| Royal Society 2023, *Large-scale electricity storage*, [pdf](https://royalsociety.org/-/media/policy/projects/large-scale-electricity-storage/Large-scale-electricity-storage-report.pdf) | All of Great Britain on wind + solar + cavern hydrogen, **37 weather years**, 2050 costs | £52–92/MWh (2021 £); supply ≈ 1.3 × demand | £66–117 | National smoothing, caverns, future costs; warns that one or a few weather years seriously understate storage |
| Ruhnau & Qvist 2022, *Environ. Res. Lett.* 17:044018, [doi](https://doi.org/10.1088/1748-9326/ac4dc8) | Germany, 100 % renewable, 35 weather years | ~€80/MWh; **single-year optimisation gave on average half the hydrogen storage** | — | Method evidence on our one-year limit |
| DESNZ, *Electricity Generation Costs 2025*, [pdf](https://assets.publishing.service.gov.uk/media/69ba657326909a14239612e3/electricity-generation-costs-report-2025.pdf) | UK levelised costs (2024 £, read off charts ±£5) | Onshore wind ~£58, solar ~£60 (2030 start); 100 % hydrogen turbine £230–650 by running hours | wind and solar ~£61–64 | Ours is 2–2.7× bare wind and solar: the price of every hour |
| IPCC AR5 WG3 Annex III, Table A.III.2, [pdf](https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_wg3_ar5_annex-iii.pdf) | Life-cycle g/kWh, min/median/max | Onshore wind 7/11/56; utility solar 18/48/180 | — | Generation only, no storage |
| Oymak & Tur 2025, *Processes* 13:2909, [doi](https://doi.org/10.3390/pr13092909) | Off-grid village: wind, solar, battery, electrolyser, tank, fuel cell | 36–45 g/kWh, hydrogen leakage included | — | Same chain, tiny scale |

**Not opened, so not cited:** UNECE 2021/22 (site refused access), NREL's life-cycle fact sheet (site
unreachable), and the Berkeley Lab, Energy Innovation, RMI and Google/IEA hourly-matching papers.

### Verdict

- **Cost (£126–164/MWh): high end of the range, but explained.**
  - It sits at or just above the hydrogen-storage range of the closest study (£98–132), well below that
    study's no-hydrogen range (£179–267), and above whole-country and gas-backed studies (£66–120).
  - Every difference points the expected way:
    - We are islanded, with 24.5 MW of grid, sell no surplus, and store hydrogen in tanks, not caverns.
    - We use present-day costs at commercial rates of 7.6–10.1 %.
    - No hour may go unserved.
  - Today's hydrogen price will push it higher, by at most £12–25/MWh.
- **Carbon: in line, and below the hybrid studies on the supply-only basis.**
  - Supply-only: 19.8–28.8 g/kWh. That is around the ~20 g a wind-led mix gives at the generator on the
    IPCC medians, and at the low end of Rollinson's 21–74 g and below Oymak & Tur's 36–45 g.
  - Two cautions:
    - Check 1 says our fuel cell and electrolyser are probably under-counted. At the lowest-carbon point
      that could lift supply-only carbon from about 20 g towards 30 g.
    - Our bought green hydrogen is scored on a market-based basis (ASSUMPTIONS §3).
- **What gets built matches the literature's pattern.**
  - The lowest-cost design buys fuel for the hard hours rather than building hydrogen storage (Princeton's
    finding). Hydrogen storage appears only when carbon is pushed down (Riepin & Brown).
  - Nameplate wind+solar is about 4.2× the load (Rollinson about 6×; Riepin & Brown's no-hydrogen case
    about 18×).
  - The energy available from wind and solar is 1.16–1.58× demand (Royal Society 1.3×).
- **The literature points one way on our main structural limit.** Single-year, perfect-foresight models
  understate storage, by about half for hydrogen in Ruhnau & Qvist. Our lowest-carbon design, with its
  34 t tank, is the most exposed. The lowest-cost and knee designs hold no stored hydrogen; they depend
  instead on bought hydrogen arriving when needed (check 4, B1).

---

## 4. Fresh-eyes review

A helper read ASSUMPTIONS.md, DATA_GAPS.md, SOURCES.md, VALIDATION.md, `dc_model.py`, `dc_inputs.py` and
today's source hunt as a referee who has never seen the project. Its full review, with file and line
references, is in the session notes folder (`fresh_eyes_review.md`). Below are the items that matter,
plus three this session found.

Each item was checked against the code here unless marked "(not re-checked)":
- confirmed in `dc_model.py`: the battery constraints, the hydrogen balance, the stack constraints, and the
  facility constant in the carbon total;
- confirmed in `dc_inputs.py`: the electrolyser stack cost per kg.

### Not covered anywhere in the project's notes

| # | Issue | Where | Why it matters |
|---|---|---|---|
| F1 | **The reported g/kWh mixes supply with the data centre's own building and servers** (14.8 g/kWh at every point), while £/MWh leaves the building out | `dc_model.py` ~921 (`gwp_const`); `cost_exclusions.py` | Comparisons with any supply study are off by 14.8 g unless split (§3). *Found this session* |
| F2 | **Electrolyser stacks: cost pays per kg made, carbon pays max(calendar, duty)** | cost: `dc_inputs.py` ~1237 (`cost_ely_variable_per_kg`); carbon: `dc_model.py` 607–613, 766 | At the 17 % use of the lowest-carbon design, cost charges far fewer stacks than carbon does. The fuel cell was aligned in both objectives (DATA_GAPS "Fuel cell duty cost"); the electrolyser was not. Makes a lightly used electrolyser look cheap |
| F3 | **Grid carbon held at its 2025 level for every asset's life** | `dc_inputs.py` ~305; `dc_model.py` ~801 | Wind's build carbon is spread over 35 years while imports pay 2025's mix for ever, so on-site plant looks better against imports than over its life. Small at North Norfolk (imports ≤ 56 GWh); large for grid-heavy sites. A ×0.5 push on import carbon would fit the percentage-test rule (not re-checked in size) |
| F4 | **One weather year with no out-of-sample test** | `dc_model.py`; `dc_inputs.py` warns only about unusual price years | Storage is sized exactly to 2025's worst spell with zero unserved demand. A replay of 2025's build on other years, counting unserved hours, needs no new optimisation. Only hinted at in VALIDATION.md and TODO.md |
| F5 | **No spare capacity or outage case** for on-site plant; the grid side alone pays for N-1 (two intake transformers, two circuits) | `dc_model.py`; ASSUMPTIONS §4, §7 | A data centre designs to N+1. Every design's fuel cell or battery is sized as if nothing fails |
| F6 | **Electrolyser and fuel cell efficiency stay at new-stack values for life** | `dc_inputs.py` ~1274–1293 (not re-checked) | Round trip about 29 % new, perhaps 27–28 % on average; hydrogen kit a few per cent bigger |
| F7 | **Assets outlive the 25-year data centre; the convention (annualise over each asset's own life, i.e. renewed for ever) is not stated** | `tech_costs.py`; coefficients | Over 25 years only, wind's yearly carbon would be about 40 % higher and its cost about 10 % higher |
| F8 | **The carbon-price point counts grid carbon twice**: wholesale prices already carry the carbon cost of gas plants, and the point adds £72.27/t on top | `dc_pareto.py` 376–399 | Moves only that reporting point, towards less grid. Minor |
| F9 | **Only climate change is assessed** (iridium stood in by platinum, lithium, land, water) | throughout | The scope limit should be one sentence in ASSUMPTIONS |
| F10 | **Sensitivity tests move one input at a time** | `sensitivity.py` | Interactions are not seen; state it |
| F11 | **Wind output falling with age is not modelled** (solar's mismatch is noted, DATA_GAPS) | `dc_inputs.py` 372–379 (not re-checked) | A few per cent more wind for the same energy |
| F12 | **Grid biomass is scored on a small wood-chip heat-and-power plant** | `optimiser_lca/grid.py` 137–141 (not re-checked) | GB biomass is mostly imported pellets burned for power only, so grid carbon is probably a little low |
| F13 | `transformers.py` docstring says transformer losses are "not implemented"; `conversion_losses.py` has charged them since 14 Oct | `optimisation/transformers.py` ~140 | Stale text. *Found this session* |

### Covered, but weakly or inconsistently

| # | Issue | Where | Note |
|---|---|---|---|
| W1 | **Bought hydrogen can arrive at any rate, with no on-site buffer.** The lowest-cost and knee designs build no tank (`cap_tank` 0) and buy 2.6–5.1 kt a year | `dc_model.py` 526–529: no limit on `h2_buy` | At 57–74 MW of fuel cell that is up to about 3.5–4.7 t an hour, roughly 4–6 tube trailers an hour at peak, with no bays or buffer storage costed. Flagged in OBJECTIVE_AUDIT; never reached the registers. Haulage is a boundary item with no figure. Of everything here, this is the modelling choice that most flatters the lowest-cost design |
| W2 | **Battery never fades and has no cycle limit** | `battery.py` 146–147, 345–354 compute an 83.5 % mean capacity; `dc_model.py` 507–516 use neither | Battery 10–17 % too cheap and too low in carbon per usable MWh; SOURCES.md reads as if both were applied |
| W3 | Charging and discharging in the same hour is allowed | `dc_model.py` battery block; OBJECTIVE_AUDIT found it in 15–27 % of discharge | Inflates cycling; harmless to energy, but it hides the cycle count W2 needs |
| W4 | Perfect foresight never bracketed; the myopic comparison has not been run | VALIDATION.md 55–58; TODO.md | See summary |
| W5 | The lowest-carbon storage mix sits on a knife edge but is reported as one design | SOURCE_HUNT §1; `dc_model.py` ~1048 | Report near-cheapest alternatives or ranges |
| W6 | Hydrogen leakage charged at the tank only, not at electrolyser venting, fuel cell purge or the seller's chain | `dc_model.py` 813–814 | 1 % leakage elsewhere ≈ 0.12 kg CO2e per kg of hydrogen |
| W7 | VALIDATION.md is dated 30 Oct, on London at 7.31 MW; the headline is North Norfolk at 100 MW IT | `optimisation/VALIDATION.md` 5–7 | Also against the "no London tests" rule; the cut-off rule-3 table (ASSUMPTIONS §8) is London too |
| W8 | Average, not marginal, grid carbon: §5 says "report against both", §2b says marginal is out of scope | ASSUMPTIONS 128–140 and 388–392 | Make the two paragraphs agree |
| W9 | Stale or contradictory statements | listed in the review | SOURCES.md:13 says 2025 pounds (the model charges 2026); £78.96/t in SOURCES/DATA_GAPS against £72.27 in code; DATA_GAPS:15–16 still lists the old hurdle rates and a "closed" 3.5 % rate; `dc_model.py` docstring says half-hourly (runs are hourly); ASSUMPTIONS §1 still quotes 7,306 kW |

The review also lists what it found already covered, so we know it looked: no minimum load or start-up
cost; storage wrapping round the year; transformer losses, self-discharge and tank leakage; network
charges and levies; no credits; the end-of-life residual; the standby generator; no area limit; the
battery beyond 9 hours; the coastal wind capacity factor; the cut-off rule.

---

## Summary

**What each check found.**

1. **Top-down carbon.** Wind (94 %) and the battery's cells (81 %) agree with the UK government's
   carbon-per-pound figures. Solar (281 %) and the tank (164 %) sit above them, which points at the
   broad industry averages rather than at missing flows.
   - The **fuel cell is far below (13 %; its balance of plant 5 %)**: the one large likely gap. Raised to
     its top-down figure it would add up to 9 % to the lowest-cost carbon and 27 % to the lowest-carbon
     design's.
   - The electrolyser (23 %) is low but built only at the lowest-carbon point (up to +5 % there).
   - The battery's inverter side (33 %) and the grid intake (8–26 %) are low but immaterial.
2. **Checklist.** Every stage is in or declared out, except:
   - carbon: fuel cell installation and foundations; grid connection maintenance;
   - cost: battery fade; business rates on the electrolyser, fuel cell and tank; land under the
     electrolyser; insurance and pre-development where the sources give only totals;
   - text: one unstated residual (transport legs inside ecoinvent's turbine).

   The fuel cell gap, the battery fade and the missing insurance (about 2 % of each coefficient) are
   likely to fail the 1 % test; the rest look small.
3. **Published studies.** Cost sits at the high end of the range for the reasons the design predicts
   (islanded, tanks, present-day costs, every hour served), and today's hydrogen price will raise it.
   Carbon is in line once the data centre's own 14.8 g/kWh is taken out. The designs follow the
   literature's pattern: buy fuel for the last hours at lowest cost, store hydrogen only when carbon is
   pushed down. The newest run predates today's inputs, and tonight's sign-off has already failed its
   test step on stale maps.
4. **Fresh eyes.** Not in our notes:
   - the g/kWh mixes facility and supply;
   - electrolyser stacks are charged differently in cost and carbon;
   - grid carbon is held at 2025 levels;
   - there is no out-of-sample weather test and no spare capacity;
   - efficiency never ages; the asset-life convention is unstated; only climate change is assessed.

   Weakly covered: bought hydrogen with no delivery limit and no buffer; a battery that never fades;
   several stale statements.

**What, if anything, should change in the model.** For discussion, not action. Roughly in order of how
much each could move a result:
1. The fuel cell's carbon. It is the largest likely gap.
   - At least add the balance of plant to the ×0.5/×1.5 tests the stack already has, and say plainly that
     the top-down check suggests even ×1.5 understates it.
   - A megawatt-scale stationary inventory would settle it; none was found (DATA_GAPS).
2. Bought hydrogen's delivery rate. A limit on trailers per hour, or a required buffer tank for any design
   that buys, would make the lowest-cost and knee designs honest about supply.
3. The battery's fade and cycle limit. `battery.py` already computes the figures the model ignores.
4. The electrolyser stack cost on max(calendar, duty), as the fuel cell already is.
5. Reporting, with no model change: split g/kWh into supply and facility, and state the asset-life
   convention, climate change only, and one-at-a-time sensitivity.
6. Housekeeping:
   - register rows for gaps 2.2 and 2.4, and an insurance estimate for the battery, electrolyser and
     tank (2.5);
   - fix the stale statements (W9, F13);
   - re-run the headline on today's inputs once the maps are rebuilt.

**What "complete" can honestly mean for this model.** It can mean complete against its stated boundary
and its stated question, and on that basis it largely is:
- every stage of every asset is either counted, declared outside the boundary, or tested and registered;
- wind and the battery's cells agree with an independent government top-down estimate;
- the headline cost and carbon sit inside what published studies of similar systems find.

It cannot mean the answer is certain. Four things limit it:
- **Gaps of known size.** The fuel cell, and to a lesser extent the electrolyser, are probably
  under-counted in carbon. Bought hydrogen is supplied without limit. The battery never wears out. All of
  these favour the designs the model picks.
- **The structure has never been tested:**
  - the whole design rests on **one weather year, 2025**, solved with **perfect foresight** of every hour;
  - the published evidence is that this understates storage, possibly by about half for hydrogen;
  - no design has been replayed on another year or run without foresight, so the reliability of "every
    hour served" holds for 2025 as known in advance, not for a year the plant has to face blind.
- **The answer is for one site** (North Norfolk) and **today's prices**.
- **Carbon is measured one way only:** climate change, an average attributional grid figure held at its
  2025 level, and market-based bought green hydrogen.

A fair one-line statement for the report: *the model is complete within its declared boundary and agrees
with independent estimates where they exist. Its main open risks are a likely under-counted fuel cell,
unlimited hydrogen deliveries, and the untested one-year, perfect-foresight structure, which by the
published evidence makes storage-heavy designs look more reliable and cheaper than they would be.*

---

*Working notes and helper outputs (outside the repository):*
- factors: `spend_factors.md`; studies: `published_studies.md`; review: `fresh_eyes_review.md` — in the
  session notes folder
  `C:\Users\ls1524\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_53113854-6f8d-4d29-83a6-a98a68aa80c7\`;
- arithmetic: `scratchpad\scripts\topdown2.py` and `material.py` in this session's scratchpad.
