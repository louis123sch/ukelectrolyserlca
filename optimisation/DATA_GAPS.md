# Data gap register

Status of every input the optimisation study needs but the repo did not
already have. Sources confirmed against NESO **FES 2025 Economics Assumptions
v1** (published 2025-12-11), which is a signposting document — it names the
authoritative UK source for each assumption rather than tabulating values.

## Closed

| Input | Value / source | Where |
|---|---|---|
| Onshore wind capex/opex/LF/life | DESNZ/Arup 2024, Table 3 | `tech_costs.py` |
| Offshore wind capex/opex/LF/life | DESNZ/Arup 2024 offshore, Table 3 | `tech_costs.py` |
| Solar PV capex/opex/LF/life | DESNZ/Arup 2024, Table 4 (>5MW, per kWp DC) | `tech_costs.py` |
| Hurdle rates (power) | 5.8 % onshore, 6.2 % offshore, 5.0 % solar, pre-tax real | `tech_costs.py` |
| Social discount rate (non-power) | **3.5 %**, HM Treasury Green Book 2022 | FES confirms |
| Generator connection & UoS | in all three DESNZ/Arup tables | `tech_costs.py` |
| Electrolyser capex/opex | NESO Green Hydrogen Data Portal | `5.prices.ipynb` |
| Wholesale electricity price | Elexon APXMIDP half-hourly | `5.prices.ipynb` |
| Grid carbon intensity | Carbon Intensity API, regional, half-hourly | `3.1` notebook |
| Data centre load shape | flat 7,306 kW — the foreground's own figure | `ASSUMPTIONS.md` |
| H2 transport | **out of scope** — production co-located with use | `ASSUMPTIONS.md` |
| **H2 price, green** | NESO LCOH green 2025-2050 (resource cc2dad0c) — full CF x power price x discount cube | `h2_prices.py` |
| **H2 price, blue** | NESO LCOH blue, ATR+CCS (resource 3f3b1bf0) | `h2_prices.py` |
| **H2 price, grey** | European Hydrogen Observatory *Hydrogen production costs 2024*, UK SMR. Corroborated to 3 % by an independent derivation from this study's own inventory | `h2_prices.py` |
| **H2 price, blue** | EHO UK, reforming with carbon capture (matches `smr_ccs_hermesmann`); NESO ATR+CCS is the cheaper-route low case | `h2_prices.py` |
| **H2 price, turquoise** | Constructed as an 86 % grey / 14 % green blend weighted by the MP-E inventory's own gas:electricity energy split. Validated against Rego et al. 2026 (IJHE 225, 154378), a dedicated pyrolysis TEA | `h2_prices.py` |
| **All H2 prices, plausibility** | Cross-checked against IEA *Global Hydrogen Review 2026* Fig 3.20 published 2025 ranges | `h2_prices.py` |
| **Natural gas price** | FES 2025 Data Workbook CP1, NBP base case 2010-2050. 2025 = **£33.74/MWh HHV** | `h2_prices.py` |
| **Carbon price** | FES 2025 Data Workbook CP2, GB total carbon. 2025 = **£78.96/tCO2** | `h2_prices.py` |

## Open — public source identified, not yet pulled

| Input | Source | Note |
|---|---|---|
| ~~**Demand-side network charges**~~ **CLOSED** | NESO Data Portal CKAN API — the same API `h2_prices.py` already uses. TNUoS HH demand tariffs by zone (resource 6abe8416), TNUoS demand residual by band (dcca94fd), BSUoS fixed tariffs (4dfa533f). DUoS transcribed from London Power Networks LC14 v1.3 Annex 1, since no open API exists for DNO charging statements. See `network_charges.py`. Network charges add **£23.26/MWh** to a £79.83/MWh wholesale price — **29 % more**, of which 38 % is capacity- or connection-based rather than volumetric |
| **Grid connection capacity by location** | No public, machine-readable register exists. `sites.Site.connection_limit_mw` defaults to **None** — unconstrained — rather than carrying an invented figure, because it would be the most decision-relevant input in the study and the least defensible. Set it when you have a real number for a real site |
| **Grid series for regions other than 13** | Only London is cached. `sites.build_grid_series(<region>)` generates one via notebook 3.1, but it scores the GB fuel mix against ecoinvent for every half-hour and is slow. Until then `require_grid_region()` refuses to substitute — given TNUoS alone swings £0/kW to £10.12/kW zonally, the locational comparison is probably the study's headline and is not yet computed |
| **Fuel cell capex** | **PROXY IN USE, graded assumed.** DOE, *Technical Targets for 100 kW-3 MW CHP and Distributed Generation Fuel Cell Systems Operating on Natural Gas*: 2015 status **$1,200-4,500/kW**, 2020 target **$1,000/kW**, 80,000 h to >10 % degradation, 42-47 % LHV electrical | **Blocks the cost objective of every hydrogen architecture.** Three problems before this can be used: it is a *natural-gas* system and therefore includes a reformer this study does not have; the $1,000 figure is an aspirational target at 100 MW/yr volume, not an observed price; and it is USD needing conversion to real 2025 GBP. The 2015 **status range** is the honest basis, and it spans 3.75x |
| **H2 tank capex** | **PROXY IN USE, graded assumed.** No single defensible source. Above-ground compressed vessels are quoted at EUR 500/kg and EUR 1,040/kg of capacity in different studies; DOE's 2005 status for 430 bar stationary was $1,100/kg; one estimate gives $600/kg at 1,000 kg scale | Blocks all hydrogen runs. The spread is over 2x and none of the sources is UK or recent. Gandiglio et al. 2022 has not yet been checked for a cost alongside the inventory it supplies - do that first, since it would at least match the vessel actually inventoried |
| **SOEC capex/opex** | **PROXY IN USE, graded assumed** — PEM x 1.2/1.5/2.0, no source at all. NESO Green Hydrogen Data Portal, or IEA | `electrolyser_costs_clean.csv` has PEM and Alkaline only. SOEC can be run **carbon-only** in the meantime, which is a defensible partial result rather than a fabricated one |
| **Battery standing loss** | Modo Energy assumptions page, or BEIS 2022 | Not modelled at all — `battery.py` has round-trip efficiency only. Dominated by auxiliary load (HVAC, BMS, PCS standby), order 0.1–0.5 %/day |
| **H2 tank leakage** | A compressed-gas storage standard; plus DESNZ/Warwick et al. 2022 for H₂'s own GWP100 (~11) if leakage is charged | Not modelled; flagged as a known omission in notebooks 2 and 4.3. **Decides hydrogen-versus-battery over a season** |
| **Fuel cell BoP calendar life** | No public figure found for a stationary PEMFC balance of plant | Currently 25 y, ASSUMED. 60,000 h is a duty figure and implies a 300-year asset at backup duty |
| **DUoS for EHV-connected sites** | LPN Annex 2 EHV charges are *site specific* — one row per named site — so they cannot be generalised into a study input. `network_charges.py` uses the HV Site Specific family instead, which overstates DUoS somewhat for a large EHV-connected data centre |
| **NESO electrolyser capex has no published range** | NESO publishes one capex per technology per build year; its Low/Central/High labels vary the LCOH scenario, not the capital cost. So AE and PEM capex are fixed across a cost-case sweep while every assumed input around them moves, understating the spread on on-site electrolysis results |
| **CO2 transport & storage** | FES: **£450/tCO2 in 2025**, falling to **£200/tCO2** long term; opex 5 % of capex | Needed for SMR-CCS, which captures 8.01 kg CO2 per kg H2. |
| **Battery opex** | BEIS 2022 *Benefits of Long Duration Electricity Storage* | Public PDF. FES uses it for battery opex and storage discount rates. |
| **Demand-side network charges** | Ofgem / DNO DUoS + TNUoS demand tariffs | The DESNZ connection figures are *generator*-side and are not a substitute. |

## Open — no public source

| Input | Problem |
|---|---|
| ~~**Battery capex**~~ **CLOSED** | Source now identified and used. The FES *Economics Methodology report* states NESO's Li-ion capex is *"a combination of Modo survey data with CAPEX data from the National Renewable Energy Laboratory"*, citing **NREL, Cost Projections for Utility-Scale Battery Storage: 2023 Update (June 2023)**. Modo is proprietary; NREL is public. Using NREL is therefore not a US-flavoured fallback — it is half of what NESO itself uses. Modo's own model assumptions are published openly at docs.modoenergy.com and are already in real 2025 GBP, so NREL was not needed: **£300/kW + £100/kWh**, WACC 5.0 % real, 15 y life, 10,000 cycles to 67 % capacity. See `battery.py`. |
| ~~**Battery LCA as a sized asset**~~ **MOSTLY CLOSED** | Built in `battery.py`: **98.2 kg CO₂e/kWh** (LFP pack) + **31.9 kg CO₂e/kW** (PCS), using ecoinvent's own documented pack density of 0.1158 kWh/kg. Still missing the **container/racking/HVAC**, which ecoinvent 3.9.1 has no dataset for. |
| **Electrolyser stack/BoP split** | Hermesmann's capital good is one monolithic activity, so stack replacement cannot be charged separately and the whole capital is amortised on calendar life. For an electrolyser run hard this understates lifetime burden — real stacks are replaced every 60–90 kh. `fuel_cell.py` *can* make the split and does. |
| **Battery fixed OPEX** | The one battery input with no source. Modo do not publish it; FES routes it to BEIS 2022 *Benefits of Long Duration Electricity Storage*. Currently a flagged 2 %-of-capex proxy. |
| ~~**PV as a sized asset**~~ **CLOSED** | Built in `renewables.py`: **2,303 t CO₂e/MWp**, decomposed out of ecoinvent's per-kWh activity and verified to re-amortise back exactly. Wind and offshore wind done the same way. Caveat: ecoinvent's GB PV dataset is 2012-vintage multi-Si, so its embodied figure is a conservative upper bound. |

## Not applicable

| Input | Why |
|---|---|
| H2 storage capex (FES) | FES models **salt caverns** only (DNV-GL 2019). This study uses a ~10 t steel vessel, already inventoried from Gandiglio et al. 2022. |
| H2 transmission/distribution | Out of scope under co-location. |
| Hydrogen refuelling stations | Not relevant to a data centre. |
