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
| **CO2 transport & storage** | FES: **£450/tCO2 in 2025**, falling to **£200/tCO2** long term; opex 5 % of capex | Needed for SMR-CCS, which captures 8.01 kg CO2 per kg H2. |
| **Battery opex** | BEIS 2022 *Benefits of Long Duration Electricity Storage* | Public PDF. FES uses it for battery opex and storage discount rates. |
| **Demand-side network charges** | Ofgem / DNO DUoS + TNUoS demand tariffs | The DESNZ connection figures are *generator*-side and are not a substitute. |

## Open — no public source

| Input | Problem |
|---|---|
| ~~**Battery capex**~~ **CLOSED** | Source now identified and used. The FES *Economics Methodology report* states NESO's Li-ion capex is *"a combination of Modo survey data with CAPEX data from the National Renewable Energy Laboratory"*, citing **NREL, Cost Projections for Utility-Scale Battery Storage: 2023 Update (June 2023)**. Modo is proprietary; NREL is public. Using NREL is therefore not a US-flavoured fallback — it is half of what NESO itself uses. Modo's own model assumptions are published openly at docs.modoenergy.com and are already in real 2025 GBP, so NREL was not needed: **£300/kW + £100/kWh**, WACC 5.0 % real, 15 y life, 10,000 cycles to 67 % capacity. See `battery.py`. |
| ~~**Battery LCA as a sized asset**~~ **MOSTLY CLOSED** | Built in `battery.py`: **98.2 kg CO₂e/kWh** (LFP pack) + **31.9 kg CO₂e/kW** (PCS), using ecoinvent's own documented pack density of 0.1158 kWh/kg. Still missing the **container/racking/HVAC**, which ecoinvent 3.9.1 has no dataset for. |
| **Battery fixed OPEX** | The one battery input with no source. Modo do not publish it; FES routes it to BEIS 2022 *Benefits of Long Duration Electricity Storage*. Currently a flagged 2 %-of-capex proxy. |
| ~~**PV as a sized asset**~~ **CLOSED** | Built in `renewables.py`: **2,303 t CO₂e/MWp**, decomposed out of ecoinvent's per-kWh activity and verified to re-amortise back exactly. Wind and offshore wind done the same way. Caveat: ecoinvent's GB PV dataset is 2012-vintage multi-Si, so its embodied figure is a conservative upper bound. |

## Not applicable

| Input | Why |
|---|---|
| H2 storage capex (FES) | FES models **salt caverns** only (DNV-GL 2019). This study uses a ~10 t steel vessel, already inventoried from Gandiglio et al. 2022. |
| H2 transmission/distribution | Out of scope under co-location. |
| Hydrogen refuelling stations | Not relevant to a data centre. |
