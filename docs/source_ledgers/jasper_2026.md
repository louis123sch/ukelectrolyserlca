# Jasper 2026 — row ledger (22 Oct 2026)

Source: F.B. Jasper, Y. Zhou, H. Ersoy, M.J. Baumann, J. Peters, D.H. Neuhaus, M. Weil (2026), "Life cycle assessment of grid-scale battery storage: evaluating the environmental competitiveness of sodium-ion systems", *Energy Adv.* 5, 550–570, doi:10.1039/d5ya00341e (published 16 March 2026, "Licensed under CC-BY-NC 4.0", p. 550). SI workbook, Zenodo 10.5281/zenodo.17651912.

Module: `optimiser_lca/bess.py` (Jasper side) and `optimiser_lca/stepup_transformers.py` (CSS_TX_*, `containerised_lv_stepup_per_mw`). Read-only check; nothing in the repo was changed.

## Files read

| File | How | What it gave |
|---|---|---|
| `C:\Users\ls1524\OneDrive - Imperial College London\DC optimiser\sources\jasper grid storage lca.xlsx` | openpyxl, formulas and cached values, every sheet | 8 sheets: `Cover Sheet` (B2:T17), `Air-cooled CSS - Production` (A1:G237), `Air-cooled CSS - EOL` (A1:G326), `Liquid-cooled CSS - Production` (A1:F125), `Liquid-cooled CSS - EOL` (A1:F93), `Numerical results of Figures` (A1:J158), `Results in all EF categories` (A1:S31), `EOL approach` (A1:J20). Liquid production sheet dumped row by row (r1–r125); air-cooled production sheet dumped row by row (r1–r237); results, EF, EOL-approach and liquid EOL sheets dumped. |
| `C:\Users\ls1524\OneDrive - Imperial College London\DC optimiser\sources\Jasper grid storage lca.pdf` | pymupdf text extraction of all 21 pages (the Read tool could not render pages: `pdftoppm` is not installed, so Fig. 4 was checked against the SI's numerical sheet and the text, not the figure image) | §2.1 goal and scope (p. 553), §2.3 Table 2 and Table 3 (p. 556), §2.4.1–2.4.4 LCI (pp. 557–558), §3.1 and Fig. 4 caption (pp. 559–560), data availability (p. 567), refs 12, 25, 46, 47, 56, 61, 66–77 (pp. 567–569) |
| `C:\Users\ls1524\Desktop\ukdclca\optimiser_lca\bess.py` | whole file (1,047 lines) | parameters, `CSS_EXCLUDED`, `BESS_SCOPE`, `JASPER_FIG4_LC_LFP`, every Jasper activity |
| `C:\Users\ls1524\Desktop\ukdclca\optimiser_lca\stepup_transformers.py` | lines 95–135, 255–320, 475–495, 630–690 | CSS_TX_SOURCE/KG/KW/KG_PER_MW/UNITS_PER_MW, `check()`, `_container_row`, the `containerised_lv_stepup_per_mw` comment |
| `C:\Users\ls1524\Desktop\ukdclca\optimiser_lca\registry.py` | BESS codes | activity codes used below |
| `C:\Users\ls1524\Desktop\ukdclca\docs\SOURCE_DIFF.md` | whole file | items #1, #2, S1, S9, the "wrong claims" list, the 21 Oct implementation table |
| `C:\Users\ls1524\Desktop\ukdclca\optimisation\SOURCES.md` | lines 295–420, 900–935 | "The grid battery's energy term", the step-up substitution note |
| `C:\Users\ls1524\Desktop\ukdclca\optimisation\battery.py`, `coefficients.py`, `ASSUMPTIONS.md`, `DATA_GAPS.md`, `docs\CARBON_PLAN.md` | grep only | stale-claim check (last section) |

Workbook conventions used below. Column A is blank on exchange rows; a process block opens with a row carrying the process name, amount 1 and its unit (e.g. r12 `CSS (liquid cooled) | 1 | Item(s)`), followed by a `Flow | Amount | Unit | Provider | Avoided waste` header, then exchange rows. The liquid sheet's r1 says "Only additional processes to air-cooled CSS listed", so the liquid CSS's Container, Fire suppression system, Air conditioner, Rack 48x43, PCS and transformer processes live on the air-cooled sheet; they are ledgered in the second table. The `Provider` cell for ecoinvent datasets is printed as `<dataset> | <product> | Cutoff, U - <geo>`; `3.11` names are mapped to their 3.9.1 equivalents by the module (noted where the name or geography differs).

Dispositions: **IN** = amount and provider as printed (3.9.1 name/geography equivalents noted). **IN-PROXY** = amount as printed, but the source's provider is a dataset the workbook does not carry (Ellingsen 2014; Jasper 2022), so the module uses a stated proxy, graded ASSUMED. **IN-DIFFERS** = both numbers given. **BOUNDARY** = end-of-life or delivery to site. **SUBSTITUTED** = replaced by something else, where stated. **NOT-APPLICABLE** = a row that is zero or belongs to another design. **MISSING** = in the source, inside the boundary, not in the module.

## Liquid-cooled CSS production sheet → module activities

Module activity codes (registry): `bess_dc_block_liquid_1unit` (CSS), `bess_rack_liquid_1unit`, `bess_module_47kwh_liquid`, `bess_rack_housing_1kg`, `bess_liquid_cooling_system_1unit`, `bess_cooling_plate_1unit`, `bess_liquid_cooling_unit_1unit`, `bess_compressor_1kg`, `bess_filter_drier_1kg`, `bess_pump_1kg`, `bess_secondary_coolant_1kg`, `bess_container_20ft_1unit`, `bess_fire_suppression_1unit`, `bess_air_conditioner_1kg`, `bess_dc_block_per_kwh`; cell `bess_lfp_cell_1kwh_cn` (Voß).

| Sheet row | Source row (provider / process, as printed) | Amount | Unit | Module (activity code, key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| r1 | "Only additional processes to air-cooled CSS listed. All processes are production processes…" | — | — | — | structure | Governs the second table below |
| r2 | Reference `Full life cycle CSS (liquid cooled)` | 1 | Item(s) | not built | BOUNDARY (EOL wrapper) | Production + EOL wrapper; the module takes production only |
| r3–r4 | `Inputs` header; `Flow / Amount / Unit / Provider / Avoided waste` | — | — | — | structure | |
| r5 | `CSS(liquid cooling)` → provider `CSS (liquid cooling)` | 1 | Item(s) | `bess_dc_block_liquid_1unit`, and `bess_dc_block_per_kwh` = 1/3,008 of it | IN | The module's functional unit sits one level down (per kWh nameplate) |
| r7–r8 | `Outputs` header | — | — | — | structure | |
| r9 | `Life cycle CSS` | 1 | Item(s) | — | structure | Reference output of the wrapper |
| r10 | `used CSS (liquid cooled)` → `treatment of used CSS (liquid cooled)` | 1 | Item(s) | not built | BOUNDARY (end-of-life) | The whole `Liquid-cooled CSS - EOL` sheet (r1–r93) and `EOL approach` sheet hang off this row; none taken (ASSUMPTIONS §6) |
| r12 | `CSS (liquid cooled)` | 1 | Item(s) | `bess_dc_block_liquid_1unit` | IN | |
| r14 | header | — | — | — | structure | |
| r15 | `Battery rack (liquid cooling)` → `Battery rack (liquid cooling)` | 8 | Item(s) | `(FG(bess_rack_liquid_1unit), CSS_RACKS=8, unit)` | IN | Table 2 p. 556: "8 racks (376.01 kWh)" |
| r16 | `BESS controller` → `BESS controller` | 30 | kg | `("electronics_control", 30.0, kg)` = market for electronics, for control units GLO | IN-PROXY | **No `BESS controller` process exists in either production sheet** (checked r1–r237 air, r1–r125 liquid). Paper §2.4.4 p. 558: "the controller weighs approximately 30 kg. Its composition is based on the LCI of a HSS controller, as reported in a previous study [12]" = Jasper et al. 2022, *J. Cleaner Prod.* 366, 132899 (not held). So the composition exists in a citable source, just not in this workbook; the module's "has no inventory in the SI" is true of the workbook. Implied Jasper score: Fig. 4 "Others" 0.248 kg/kWh × 3,008 / 30 kg = 24.9 kg CO₂e/kg; the module's proxy scores 0.32 × 3,008 / 30 = 32 kg/kg (+28 %, errs high) |
| r17 | `concrete block` → `concrete block production \| concrete block \| Cutoff, U - DE` | 43.9 | t | `bess_container_20ft_1unit`: `("concrete_block_de", 43_900.0, kg)` — process `concrete block production` [DE] | IN | **Confirmed**: amount 43.9 t, provider `concrete block production`, geography DE, on the CSS (liquid cooled) process at one per container (air sheet r18 identical). §2.4.4 p. 558: 20 ft base 6.06 × 2.43 m + 0.20 m each side, 1 m deep, 2,400 kg/m³ → 43.9 t (6.46 × 2.83 × 2,400 = 43,878 kg, checks). Module relocates it from the CSS level to the container activity so the fuel cell shares it (comment at bess.py l. 940–942); same quantity per container |
| r18 | `Container` → `Container` | 1 | Item(s) | `(FG(bess_container_20ft_1unit), 1, unit)` | IN | Recipe on air sheet r134–r148 (second table) |
| r19 | `Fire supression system for 20 ft CSS` → `Fire suppression system for 20ft CSS` | 1 | Item(s) | `(FG(bess_fire_suppression_1unit), 1, unit)` | IN | Recipe on air sheet r164–r202 |
| r20 | `Liquid cooling system` → `Liquid cooling system` | 1 | Item(s) | `(FG(bess_liquid_cooling_system_1unit), 1, unit)` | IN | |
| r21 | `Power conversion system for CSS` → `Production of power conversion system for CSS` | 800 | kg | not in bess.py; `CSS_EXCLUDED["Power conversion system for CSS"] = (800.0, "kg", …)`; charged by `optimisation/battery.py` `PCS_ACTIVITY = ("market for inverter, 500kW", "GLO")`, 15,930.86 kg CO₂e per 500 kW unit | SUBSTITUTED | This is a substitution, not a boundary exclusion: Jasper's per-kg PCS recipe is in the SI (air sheet r204–r221, below) and is set aside for ecoinvent's 500 kW inverter market, stated in `CSS_EXCLUDED`, `BESS_SCOPE["pcs"]` and SOURCES.md l. 303 ("so it is not charged twice"). Scale: Jasper's PCS 8.29 kg/kWh × 3,008 kWh / 1,600 kW = 15.6 kg CO₂e/kW; the module's inverter is 31.9 kg CO₂e/kW, about 2× |
| r22 | `transformer, for grid connection` → `transformer production, for grid connection` | 5500 | kg | not in bess.py; `CSS_EXCLUDED["transformer, for grid connection"] = (5_500.0, "kg", …)`; mass carried by `stepup_transformers.CSS_TX_KG = 5_500.0` per `CSS_TX_KW = 1_600.0`, composition from IEA PVPS Table 49 (`containerised_lv_stepup_per_mw`) | SUBSTITUTED (stated) | Recipe transcribed in the S1 section below. `stepup_transformers.check()` holds CSS_TX_KG to this row |
| r24 | `Battery rack (liquid cooled)` | 1 | Item(s) | `bess_rack_liquid_1unit` | IN | |
| r26 | header | — | — | — | structure | |
| r27 | `Battery pack` → `production of battery pack for CSS (for liquid cooling)` | 8 | Item(s) | `(FG(bess_module_47kwh_liquid), CSS_MODULES_PER_RACK=8, unit)` | IN | Jasper's "battery pack" = module. Table 2: "8 modules (47 kWh)" |
| r28 | `cable, unspecified` → `market for cable, unspecified \| … GLO` | 17.907 | kg | `("cable", 17.907, kg)` GLO | IN | = 0.705 % × 2,540 kg rack (§2.4.1, Table 2 rack weight): 17.907 exactly |
| r29 | `High voltage control box` → `High voltage control box (electronics for control units)` | 15.5 | kg | `("electronics_control", 15.5, kg)` = market for electronics, for control units GLO | IN | §2.4.1 p. 557: "The HV control box is represented using the ecoinvent process 'electronics, for control units'"; Jasper's provider is a wrapper of that dataset |
| r30 | `Rack, 48x43, for stationary battery storage system, Li-Ion battery modules` → same | 431.8 | kg | `(FG(bess_rack_housing_1kg), 431.8, kg)` | IN | = 17 % × 2,540 kg (§2.4.1): 431.8 exactly. Recipe air sheet r124–r132 |
| r31 | `transport, freight, lorry, 16-32 metric ton, diesel, EURO 6` → `market for … EURO 6 \| … RoW` | 0.0962 | t*km | `("lorry_euro6_row", 0.0962, tkm)` | IN (upstream) | 0.0962/100 km = 0.96 kg; 0.58/600 km = 0.97 kg: the 100 + 600 km upstream pattern, but for ~1 kg of material — negligible, and identical on the air-cooled rack (air r101–r102). Kept, as the module says |
| r32 | `transport, freight, train, fleet average` → `market group for transport, freight, train, fleet average \| … GLO` | 0.58 | t*km | `("train_glo", 0.58, tkm)` = market group for transport, freight train GLO | IN (upstream) | 3.11 name → 3.9.1 market group |
| r35 | `production of battery module for CSS` | 1 | Item(s) | `bess_module_47kwh_liquid` | IN | §2.4.1: module after Baumann et al. 2020 [68], "adjusted according to the module weights specified in the manufacturers' data sheets"; 48 cells in series (p. 556) |
| r37 | header | — | — | — | structure | |
| r38 | `03-NFM111 based SIB (Voß et al.)` → `production of 03-NFM111 based SIB` | `NFM111 *37953/160.5` | kg | — | NOT-APPLICABLE | Sodium-ion variant; air r104 description: "cell parameters are 0 or 1". LFP design built |
| r39 | `Aluminium endbars, for module packaging, Li-Ion battery (Ellingsen)` → same | 3.1302 | kg | `("al_wrought", 3.1302, kg)` + `("sheet_rolling_al", 3.1302, kg)` | IN-PROXY | Ellingsen et al. 2014 [25] dataset, not in the workbook; module maps to wrought Al + rolling, marked ASSUMED |
| r40 | `Bimetallic busbars and washers, for module packaging, Li-Ion battery (Ellingsen)` → same | 6.6517 | kg | `cu_cathode` 3.32585 + `sheet_rolling_cu` 3.32585 + `al_wrought` 3.32585 + `sheet_rolling_al` 3.32585 (`BIMETALLIC_COPPER_SHARE = 0.5`) | IN-PROXY | Split ASSUMED 50:50; module says <1 % on the total |
| r41 | `Copper end-busbars, for module packaging, Li->Ion battery (Ellingsen)` → same | 0.9586 | kg | `("cu_cathode", 0.9586)` + `("sheet_rolling_cu", 0.9586)` | IN-PROXY | ASSUMED copper cathode, rolled |
| r42 | `injection moulding` → `market for injection moulding \| … GLO` | 2.7838 | kg | `("injection_moulding", 2.7838, kg)` | IN | |
| r43 | `LFP based LIB (Voß et al.)` → `production of LFP based LIB` | `LFP *47000/176.6` | kg | `(FG(bess_lfp_cell_1kwh_cn), CSS_MODULE_KWH=47.0, kWh)` | IN | With LFP = 1: 266.14 kg of Voß cell at 176.6 Wh/kg = 47.0 kWh. Module charges 47 kWh × (1000/383.4) = 122.59 Voß cells × 2.1708 kg = 266.14 kg: identical mass. Jasper link Voß's cell and do not reproduce it (docstring l. 30–31 confirmed). Note Table 2's physical cell is 306 Ah / 3.2 V, 48s1p = 47.0 kWh; Jasper scale by mass, not cell count, and so does the module |
| r44 | `metal working factory` → `market for metal working factory \| … GLO` | 4.58e-10 | Item(s) | `("metal_working_factory", 4.58e-10, unit)` | IN | |
| r45 | `metal working, average for steel product manufacturing` → market GLO | 28.4727 | kg | `("mw_steel", 28.4727, kg)` | IN | |
| r46 | `Mn-PBA based SIB (Voß et al.)` | `MnPBA *28156/142.2` | kg | — | NOT-APPLICABLE | SIB variant |
| r47 | `NVPF based SIB (Voß et al.)` | `NVPF *34147/151.2` | kg | — | NOT-APPLICABLE | SIB variant |
| r48 | `polypropylene, granulate` → market GLO | 2.7838 | kg | `("polypropylene", 2.7838, kg)` | IN | |
| r49 | `printed wiring board, through-hole mounted, unspecified, Pb free` → market GLO | 0.6442 | kg | `("pwb_through_hole", 0.6442, kg)` | IN | The air-cooled module (air r118–r119) uses surface-mounted 0.1965 and through-hole 0; the liquid module as printed is through-hole 0.6442. Module follows the liquid sheet |
| r50 | `steel, low-alloyed` → market GLO | 28.4727 | kg | `("steel_low_alloyed", 28.4727, kg)` | IN | |
| r51 | `transport, freight, lorry, 16-32 metric ton, diesel, EURO 5` → market RoW | 3.9857 | t*km | `("lorry_euro5_row", 3.9857, tkm)` | IN (upstream) | 3.9857/100 km = 39.9 kg; 23.9144/600 km = 39.9 kg: 100 km lorry + 600 km rail on ≈ the module's non-cell mass (42.6 kg by the bill). RoW/GLO providers, not the RER/sea/Europe set — upstream, kept |
| r52 | `transport, freight, train, fleet average` → market group GLO | 23.9144 | t*km | `("train_glo", 23.9144, tkm)` | IN (upstream) | |
| r54 | `liquid cooling system` | 1 | Item(s) | `bess_liquid_cooling_system_1unit` | IN | |
| r56 | header | — | — | — | structure | |
| r57 | `Air conditioner` → `Air conditioner` | 37 | kg | `(FG(bess_air_conditioner_1kg), 37.0, kg)` | IN | §2.4.2: one 3.6 kW, 37 kg unit for the BoS cabinet; recipe air r34–r79 |
| r58 | `cable, connector for computer, without plugs` → market GLO | 8 | m | `("cable_connector", 8.0, "meter")` | IN | |
| r59 | `cooling plate in battery pack (liquid cooling)` → `production of cooling plate in battery pack (liquid cooling)` | `num_powersection*num_batterypack` | Item(s) | `(FG(bess_cooling_plate_1unit), CSS_COOLING_PLATES = 8 × 8 = 64, unit)` | IN (formula) | The sheet prints the formula, not a value; the parameter values are not in the workbook. 8 racks × 8 modules = 64, one plate per module (§2.4.2 "an aluminum cooling plate integrated into the modules"). **Caveat**: the liquid EOL sheet r67 treats `used cooling plate in battery pack` **144** Item(s) and r70 `waste plastic, industrial electronics` **109.37** kg = 0.75 × 144 + 1.37 — the air-cooled module count (6 × 24). Jasper's EOL model ran the liquid system with 144; whether production did too cannot be read from the sheet. Fig. 4's cooling 2.64 kg/kWh against the module's 2.58 with 64 plates (SOURCES.md l. 339) supports 64 in production; 144 would add ≈ 1.4 kg/kWh |
| r60 | `drawing of pipe, steel` → market GLO | 138.92 | kg | `("drawing_pipe_steel", 138.92, kg)` | IN | Paper §2.4.2 says "copper pipes"; the SI builds chromium-steel pipe. Module follows the SI |
| r61 | `Liquid cooling unit` → `Liquid cooling unit` | 1 | Item(s) | `(FG(bess_liquid_cooling_unit_1unit), 1, unit)` | IN | |
| r62 | `nitrile-compound` → market GLO | `0.75*num_batterypack*num_powersection` | kg | `("nitrile", CSS_NITRILE_KG = 0.75 × 64 = 48, kg)` | IN (formula) | Same parameter caveat as r59 (EOL used 144 → 108 kg) |
| r63 | `polyethylene, high density, granulate` → market GLO | 1.37 | kg | `("hdpe", 1.37, kg)` | IN | |
| r64 | `secondary coolant for liquid cooling system` → `Production of secondary coolant for liquid cooling system` | 126.43 | kg | `(FG(bess_secondary_coolant_1kg), 126.43, kg)` | IN | §2.4.2 "total mass of 126 kg" |
| r65 | `steel, chromium steel 18/8` → market GLO | 138.92 | kg | `("steel_cr", 138.92, kg)` | IN | |
| r66 | `transport, freight, lorry, 16-32 metric ton, diesel, EURO 5` → market **RER** | `1000*160` | kg*km | not built | BOUNDARY (delivery to site) | 160 kg (the ≈160 kg chiller, §2.4.2) × 1,000 km lorry in Europe = 160 t·km; the RER-lorry / sea / Europe-rail triplet is the China-to-German-site leg |
| r67 | `transport, freight, sea, container ship, heavy fuel oil` → market GLO | `8000*160` | kg*km | not built | BOUNDARY (delivery to site) | 1,280 t·km |
| r68 | `transport, freight, train, fleet average` → market **Europe without Switzerland** | `1000*160` | kg*km | not built | BOUNDARY (delivery to site) | 160 t·km |
| r70 | `cooling plate in battery back (liquid cooling)` [sic] | 1 | Item(s) | `bess_cooling_plate_1unit` | IN | |
| r72 | header | — | — | — | structure | |
| r73 | `aluminium alloy, AlMg3` → market GLO | 5.2 | kg | `("al_almg3", 5.2, kg)` | IN | |
| r74 | `metal working, average for aluminium product manufacturing` → market GLO | 5.2 | kg | `("mw_al", 5.2, kg)` | IN | |
| r75 | `synthetic rubber` → market GLO | 0.32 | kg | `("synthetic_rubber", 0.32, kg)` | IN | |
| r77 | `liquid cooling unit` | 1 | Item(s) | `bess_liquid_cooling_unit_1unit` | IN | §2.4.2: Catrini et al. 2018 chiller scaled to 40 kW (≈160 kg), + 3 × 5 kW heaters + pump from ecoinvent |
| r79 | header | — | — | — | structure | |
| r80 | `auxiliary heating unit, electric, 5kW` → market GLO | 3 | Item(s) | `("aux_heater_5kw", 3, unit)` | IN | |
| r81 | `brass` → market **RoW** | 0.4 | kg | `("brass", 0.4, kg)` = market for brass RoW | IN | |
| r82 | `Compressor` → `Compressor` | 44.36 | kg | `(FG(bess_compressor_1kg), 44.36, kg)` | IN | |
| r83 | `copper, anode` → market GLO | 7.44 | kg | `("cu_anode", 7.44, kg)` | IN | |
| r84 | `Filter drier` → `Filter drier` | 0.73 | kg | `(FG(bess_filter_drier_1kg), 0.73, kg)` | IN | |
| r85 | `metal working, average for chromium steel product manufacturing` → market GLO | 153.18 | kg | `("mw_cr", 153.18, kg)` | IN | = 37.83 + 34.46 + 80.89 |
| r86 | `metal working, average for copper product manufacturing` → market GLO | 7.44 | kg | `("mw_cu", 7.44, kg)` | IN | |
| r87 | `metal working, average for metal product manufacturing` → market GLO | 0.4 | kg | `("mw_metal", 0.4, kg)` | IN | |
| r88 | `pump for liquid cooling unit` → `Production of pump for liquid cooling unit` | 29.96 | kg | `(FG(bess_pump_1kg), 29.96, kg)` | IN | |
| r89 | `steel, chromium steel 18/8` → market GLO | 37.83 | kg | `("steel_cr", 37.83, kg)` | IN | |
| r90 | `steel, chromium steel 18/8` → market GLO | 34.46 | kg | `("steel_cr", 34.46, kg)` | IN | Two separate rows in the source, two in the module |
| r91 | `steel, chromium steel 18/8, hot rolled` → market GLO | 80.89 | kg | `("steel_cr_hr", 80.89, kg)` | IN | |
| r92 | `synthetic rubber` → market GLO | 0.068 | kg | `("synthetic_rubber", 0.068, kg)` | IN | |
| r93 | `tetrafluoroethane, R134a` → `market for tetrafluoroethane, R134a \| … GLO` | 9 | kg | `("r134a", 9.0, kg)` = market for refrigerant R134a GLO | IN | 3.11 name → 3.9.1 name; the charge, not a leak (module comment) |
| r95 | `compressor` | 1 | kg | `bess_compressor_1kg` | IN | |
| r97 | header | — | — | — | structure | |
| r98 | `base oil` → market GLO | 0.0404 | kg | `("base_oil", 0.0404, kg)` | IN | |
| r99 | `copper, anode` → market GLO | 0.1442 | kg | `("cu_anode", 0.1442, kg)` | IN | |
| r100 | `metal working, average for chromium steel product manufacturing` → market GLO | 0.8154 | kg | `("mw_cr", 0.8154, kg)` | IN | |
| r101 | `metal working, average for copper product manufacturing` → market GLO | 0.1442 | kg | `("mw_cu", 0.1442, kg)` | IN | |
| r102 | `reinforcing steel` → market GLO | 0.8154 | kg | `("reinforcing_steel", 0.8154, kg)` | IN | |
| r104 | `Filter drier` | 1 | kg | `bess_filter_drier_1kg` | IN | |
| r106 | header | — | — | — | structure | |
| r107 | `metal working, average for chromium steel product manufacturing` → market GLO | 0.5325 | kg | `("mw_cr", 0.5325, kg)` | IN | |
| r108 | `steel, chromium steel 18/8` → market GLO | 0.5325 | kg | `("steel_cr", 0.5325, kg)` | IN | |
| r109 | `zeolite, powder` → market GLO | 0.4675 | kg | `("zeolite", 0.4675, kg)` | IN | |
| r111 | `pump for liquid cooling unit` | 1 | kg | `bess_pump_1kg` | IN | |
| r113 | header | — | — | — | structure | |
| r114 | `aluminium, cast alloy` → market GLO | 0.4402 | kg | `("al_cast", 0.4402, kg)` | IN | Market here (the air conditioner uses the primary-ingot provider, below) |
| r115 | `cast iron` → market GLO | 0.4821 | kg | `("cast_iron", 0.4821, kg)` | IN | |
| r116 | `copper, anode` → market GLO | 0.0777 | kg | `("cu_anode", 0.0777, kg)` | IN | |
| r117 | `metal working, average for aluminium product manufacturing` → market GLO | 0.4402 | kg | `("mw_al", 0.4402, kg)` | IN | |
| r118 | `metal working, average for copper product manufacturing` → market GLO | 0.0777 | kg | `("mw_cu", 0.0777, kg)` | IN | |
| r119 | `metal working, average for metal product manufacturing` → market GLO | 0.4821 | kg | `("mw_metal", 0.4821, kg)` | IN | |
| r121 | `secondaty coolant for liquid cooling system` [sic] | 1 | kg | `bess_secondary_coolant_1kg` | IN | |
| r123 | header | — | — | — | structure | |
| r124 | `ethylene glycol` → `market for ethylene glycol \| … RoW` | 0.5 | kg | `("ethylene_glycol", 0.5, kg)` = market for ethylene glycol **GLO** | IN | Geography differs: module says the RoW market does not exist in 3.9.1 (processes comment l. 407–408) |
| r125 | `water, deionised` → market RoW | 0.5 | kg | `("water_deionised", 0.5, kg)` RoW | IN | |

### Air-cooled production sheet: processes the liquid CSS shares (per the liquid sheet's r1)

| Sheet row | Source row (provider / process, as printed) | Amount | Unit | Module (activity code, key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| r34 | `Air conditioner` | 1 | kg | `bess_air_conditioner_1kg` | IN | §2.4.2: EPD of a 3.6 kW, 37 kg split unit (Midea S-P-06897, ref 70) |
| r37 | `Indoor unit` → `indoor unit` | 0.27 | kg | `(FG(bess_ac_indoor_unit_1kg), 0.27, kg)` | IN | |
| r38 | `Outdoor unit` → `outdoor unit` | 0.73 | kg | `(FG(bess_ac_outdoor_unit_1kg), 0.73, kg)` | IN | |
| r40 | `Indoor unit` | 1 | kg | `bess_ac_indoor_unit_1kg` | IN | |
| r43 | `acrylonitrile-butadiene-styrene copolymer` → `… copolymer production \| … RoW` | 0.1158 | kg | `("abs_row", 0.1158)` | IN | |
| r44 | `aluminium, cast alloy` → `aluminium ingot, primary, to aluminium, cast alloy market \| … GLO` | 0.0979 | kg | `("al_cast_primary", 0.0979)` | IN | Primary ingot provider, as printed |
| r45 | `capacitor, electrolyte type, > 2cm height` → market GLO | 0.0125 | kg | `("capacitor_electrolyte", 0.0125)` | IN | |
| r46 | `copper, anode` → market GLO | 0.1392 | kg | `("cu_anode", 0.1392)` | IN | |
| r47 | `electronics, for control units` → `electronics production, for control units \| … RoW` | 0.0552 | kg | `("electronics_control_row", 0.0552)` | IN | |
| r48 | `injection moulding` → market GLO | 0.5654 | kg | `("injection_moulding", 0.5654)` | IN | |
| r49 | `metal working, average for aluminium product manufacturing` → production RoW | 0.0979 | kg | `("mw_al_row", 0.0979)` | IN | |
| r50 | `metal working, average for copper product manufacturing` → production RoW | 0.1392 | kg | `("mw_cu_row", 0.1392)` | IN | |
| r51 | `metal working, average for steel product manufacturing` → production RoW | 0.1298 | kg | `("mw_steel_row", 0.1298)` | IN | |
| r52 | `plastic granulate, unspecified, recycled` → market IN | 0.0097 | kg | `("plastic_recycled_in", 0.0097)` | IN | |
| r53 | `polyester resin, unsaturated` → production RoW | 0.0656 | kg | `("polyester_resin_row", 0.0656)` | IN | |
| r54 | `polyethylene, high density, granulate` → production RoW | 0.0662 | kg | `("hdpe_row", 0.0662)` | IN | |
| r55 | `polypropylene, granulate` → production RoW | 0.0406 | kg | `("polypropylene_row", 0.0406)` | IN | |
| r56 | `polystyrene, high impact` → production RoW | 0.1668 | kg | `("hips_row", 0.1668)` | IN | |
| r57 | `polyurethane, flexible foam` → market RoW | 0.0501 | kg | `("pu_flexible_row", 0.0501)` | IN | |
| r58 | `steel, low-alloyed` → market GLO | 0.1298 | kg | `("steel_low_alloyed", 0.1298)` | IN | |
| r59 | `styrene-acrylonitrile copolymer` → production RoW | 0.0505 | kg | `("san_row", 0.0505)` | IN | 17 of 17 indoor rows in |
| r61 | `Outdoor unit` | 1 | kg | `bess_ac_outdoor_unit_1kg` | IN | |
| r64 | `aluminium, cast alloy` → primary ingot GLO | 0.0648 | kg | `("al_cast_primary", 0.0648)` | IN | |
| r65 | `capacitor, electrolyte type, > 2cm height` → market GLO | 0.0259 | kg | `("capacitor_electrolyte", 0.0259)` | IN | |
| r66 | `cast iron` → `cast iron production \| … RoW` | 0.0523 | kg | `("cast_iron_row", 0.0523)` | IN | |
| r67 | `copper, anode` → market GLO | 0.206 | kg | `("cu_anode", 0.206)` | IN | |
| r68 | `electronics, for control units` → production RoW | 0.0301 | kg | `("electronics_control_row", 0.0301)` | IN | |
| r69 | `inductor, ring core choke type` → market GLO | 0.0829 | kg | `("inductor_choke", 0.0829)` | IN | |
| r70 | `injection moulding` → `injection moulding \| … RoW` | 0.0645 | kg | `("injection_moulding_row", 0.0645)` | IN | |
| r71 | `metal working, average for aluminium product manufacturing` → production RoW | 0.0648 | kg | `("mw_al_row", 0.0648)` | IN | |
| r72 | `metal working, average for copper product manufacturing` → production RoW | 0.206 | kg | `("mw_cu_row", 0.206)` | IN | |
| r73 | `metal working, average for metal product manufacturing` → production RoW | 0.0523 | kg | `("mw_metal_row", 0.0523)` | IN | |
| r74 | `metal working, average for steel product manufacturing` → production RoW | 0.4736 | kg | `("mw_steel_row", 0.4736)` | IN | |
| r75 | `plastic granulate, unspecified, recycled` → market IN | 0.0101 | kg | `("plastic_recycled_in", 0.0101)` | IN | |
| r76 | `polypropylene, granulate` → production RoW | 0.0188 | kg | `("polypropylene_row", 0.0188)` | IN | |
| r77 | `steel, low-alloyed` → market GLO | 0.4736 | kg | `("steel_low_alloyed", 0.4736)` | IN | |
| r78 | `styrene-acrylonitrile copolymer` → production RoW | 0.0147 | kg | `("san_row", 0.0147)` | IN | |
| r79 | `tetrafluoroethane, R134a` → `refrigerant R134a production \| … RoW` | 0.021 | kg | `("r134a_row", 0.021)` | IN | 16 of 16 outdoor rows in. r82–r83 is the unit's own output block (structure) |
| r124 | `Rack, 48x43, for stationary battery storage system, Li-Ion battery modules` | 1 | kg | `bess_rack_housing_1kg` | IN | |
| r127 | `metal working factory` → market GLO | 4.58e-10 | Item(s) | `("metal_working_factory", 4.58e-10, unit)` | IN | |
| r128 | `metal working, average for steel product manufacturing` → market GLO | 1 | kg | `("mw_steel", 1.0)` | IN | |
| r129 | `powder coat, steel` → market GLO | 0.055 | m2 | `("powder_coat_steel", 0.055, "square meter")` | IN | |
| r130 | `steel, low-alloyed` → market GLO | 1 | kg | `("steel_low_alloyed", 1.0)` | IN | |
| r131 | `transport, freight, lorry, 16-32 metric ton, diesel, EURO 5` → market RoW | 0.10053075 | t*km | `("lorry_euro5_row", 0.10053075, tkm)` | IN (upstream) | 1.0053 kg × 100 km; 0.6031845/600 = 1.0053 kg: the ecoinvent default material legs per kg |
| r132 | `transport, freight, train, fleet average` → market group GLO | 0.6031845 | t*km | `("train_glo", 0.6031845, tkm)` | IN (upstream) | |
| r134 | `Container` | 1 | Item(s) | `bess_container_20ft_1unit` | IN | §2.4.2: ecoinvent 20 ft container, lining after McKinnon et al. 2022 [69] |
| r137 | `Fire damper` → `Fire damper`; Description **"Exclude?"** | 2 | Item(s) | `(FG(bess_fire_damper_1unit), 2, unit)` | IN | Jasper's own open query in the sheet; the module keeps both dampers, as the workbook does |
| r138 | `gypsum plasterboard` → market GLO | 664.66 | kg | `("gypsum_board", 664.66)` | IN | Paper says "cement board"; SI builds gypsum plasterboard plus cement-bonded wood wool (r147) |
| r139 | `intermodal shipping container, 20-foot` → market GLO | 1 | Item(s) | `("iso_container_20ft", 1, unit)` | IN | Module notes 3.9.1's container scores ≈2.9 t CO₂e, a third of what Jasper's 3.11 line implies |
| r140 | `oriented strand board` → market RoW | 0.76 | m3 | `("osb", 0.76, "cubic meter")` | IN | |
| r141 | `plywood` → market RoW | 0.14 | m3 | `("plywood", 0.14, "cubic meter")` | IN | |
| r142 | `polyurethane, flexible foam, flame retardant` → market GLO | 2.5 | kg | `("pu_flexible_fr", 2.5)` | IN | |
| r143 | `steel, low-alloyed, hot rolled` → market GLO | 5 | kg | `("steel_low_alloyed_hr", 5.0)` | IN | |
| r144 | `transport, freight, lorry, … EURO 5` → market **RER** | `=1*2.3` = 2.3 | t*km | not built | BOUNDARY (delivery to site) | 2.3 t container tare × 1,000 km Europe |
| r145 | `transport, freight, sea, container ship, heavy fuel oil` → market GLO | `=8*2.3` = 18.4 | t*km | not built | BOUNDARY (delivery to site) | |
| r146 | `transport, freight, train, fleet average` → market **Europe without Switzerland** | `=1*2.3` = 2.3 | t*km | not built | BOUNDARY (delivery to site) | |
| r147 | `wood wool boards, cement bonded` → market RoW | 0.19 | m3 | `("wood_wool_board", 0.19, "cubic meter")` | IN | |
| r148 | `zinc coat, coils` → market GLO | 3.18 | m2 | `("zinc_coat", 3.18, "square meter")` | IN | |
| — | (module addition on this activity) | 43,900 | kg | `("concrete_block_de", 43_900.0, kg)` | IN (relocated) | Liquid r17 / air r18, moved down one level; see §21 Oct below |
| r150 | `Fire damper` | 1 | Item(s) | `bess_fire_damper_1unit` | IN | |
| r153 | `chemical, inorganic` → market GLO | 0.9 | kg | `("chemical_inorganic", 0.9)` | IN | |
| r154 | `electric motor, for electric scooter` → market GLO | 1.2 | kg | `("e_motor_scooter", 1.2)` | IN | |
| r155 | `glass fibre reinforced plastic, polyamide, injection moulded` → market GLO | 0.09 | kg | `("gfrp_pa", 0.09)` | IN | |
| r156 | `injection moulding` → market GLO | 0.09 | kg | `("injection_moulding", 0.09)` | IN | |
| r157 | `plastic granulate, unspecified, recycled` → market IN | 0.09 | kg | `("plastic_recycled_in", 0.09)` | IN | |
| r158 | `steel, chromium steel 18/8` → market GLO | 0.06 | kg | `("steel_cr", 0.06)` | IN | |
| r159 | `steel, low-alloyed` → market GLO | 0.12 | kg | `("steel_low_alloyed", 0.12)` | IN | |
| r160 | `steel, low-alloyed, hot rolled` → market GLO | 4.14 | kg | `("steel_low_alloyed_hr", 4.14)` | IN | |
| r161 | `synthetic rubber` → market GLO | 0.02 | kg | `("synthetic_rubber", 0.02)` | IN | |
| r162 | `zinc coat, coils` → market GLO | 0.5 | m2 | `("zinc_coat", 0.5, "square meter")` | IN | 10 of 10 damper rows in |
| r164 | `Fire supression system for 20 ft CSS` | 1 | Item(s) | `bess_fire_suppression_1unit` | IN | §2.4.4 p. 558 says "two 12 kg fire extinguishers using HFC-134a"; the SI builds one 21 kg tank of 70 % heptafluoropropane (HFC-227ea). Module follows the SI |
| r167 | `Fire extinguisher tank` → `Production of fire extinguisher tanks` | 21 | kg | `(FG(bess_extinguisher_tank_1kg), 21.0, kg)` | IN | |
| r168 | `Fire Suppression Panel` → `Production of fire suppression panel` | 2.5 | kg | `(FG(bess_suppression_panel_1kg), 2.5, kg)` | IN | |
| r169 | `metal working, average for steel product manufacturing` → market GLO | 30 | kg | `("mw_steel", 30.0)` | IN | |
| r170 | `steel, low-alloyed` → market GLO | 30 | kg | `("steel_low_alloyed", 30.0)` | IN | |
| r171 | `transport, … lorry … EURO 5` → market RER | `=1000*53.5` = 53,500 | kg*km | not built | BOUNDARY (delivery to site) | 53.5 kg = 21 + 2.5 + 30 |
| r172 | `transport, freight, sea, container ship, heavy fuel oil` → market GLO | `=8000*53.5` = 428,000 | kg*km | not built | BOUNDARY (delivery to site) | |
| r173 | `transport, freight, train, fleet average` → Europe without Switzerland | `=1000*53.5` = 53,500 | kg*km | not built | BOUNDARY (delivery to site) | |
| r175 | `Fire extinguisher tank` | 1 | kg | `bess_extinguisher_tank_1kg` | IN | |
| r178 | `heptafluoropropane (HFC)` → `Production of heptafluoropropane` | 0.7 | kg | `(FG(bess_hfc227ea_1kg), 0.7, kg)` | IN | |
| r179 | `steel, unalloyed` → market GLO | 0.3 | kg | `("steel_unalloyed", 0.3)` | IN | |
| r181 | `heptafluoropropane (HFC)` | 1 | kg | `bess_hfc227ea_1kg` | IN | |
| r184 | `electricity, medium voltage` → `market group for electricity, medium voltage \| … GLO` | 5 | kWh | `("electricity_mv_glo", 5.0, kWh)` | IN | |
| r185 | `heat, from steam, in chemical industry` → `steam production, as energy carrier, in chemical industry \| … RoW` | 20 | MJ | `("steam_heat_row", 20.0, MJ)` | IN | |
| r186 | `hydrogen fluoride` → market RoW | 0.131 | kg | `("hydrogen_fluoride", 0.131)` | IN | |
| r187 | `tetrafluoroethylene` → market GLO | 0.981 | kg | `("tetrafluoroethylene", 0.981)` | IN | |
| r190–r191 | `Outputs` header; `heptafluoropropane (HFC)` 1 kg | — | — | — | structure | |
| r192 | output `tetrafluoroethylene` → market GLO, **Avoided product = TRUE** | 0.1 | kg | `("tetrafluoroethylene", -0.1, kg)` "avoided product" | IN | Kept as printed, the module says, the way SMR keeps its avoided electricity |
| r193 | output `hazardous waste, for incineration` → market RoW | 0.02 | kg | `("hazardous_waste_incineration", -0.02, kg)` "production waste sent to treatment" | IN | Sign is the module's waste convention ("negative = waste sent", processes comment l. 451); not re-verified against Brightway's ecoinvent import here |
| r196 | `Fire Suppression Panel` | 1 | kg | `bess_suppression_panel_1kg` | IN | |
| r199 | `acrylonitrile-butadiene-styrene copolymer` → market GLO | 0.5472 | kg | `("abs", 0.5472)` | IN | |
| r200 | `cable, unspecified` → market GLO | 0.088 | kg | `("cable", 0.088)` | IN | |
| r201 | `polycarbonate` → market **RoW** | 0.1159 | kg | `("polycarbonate", 0.1159)` = market GLO | IN | Geography differs, stated (RoW market absent in 3.9.1) |
| r202 | `printed wiring board, surface mounted, unspecified, Pb free` → market GLO | 0.2488 | kg | `("pwb_surface", 0.2488)` | IN | |
| r204–r205 | `Power conversion system for CSS` 1 kg; note: "Mass balance based on the composition of the inverter in Jasper et al (2022). … casing … 27 kg" | 1 | kg | not built (see liquid r21) | SUBSTITUTED | Jasper's PCS recipe per kg, set aside for ecoinvent's 500 kW inverter market |
| r207 | `aluminium alloy, AlMg3` → market GLO | 0.085882353 | kg | — | SUBSTITUTED | |
| r208 | `cable, unspecified` → market GLO | 0.014313725 | kg | — | SUBSTITUTED | |
| r209 | `capacitor, electrolyte type, > 2cm height` → market GLO | 0.042941176 | kg | — | SUBSTITUTED | |
| r210 | `capacitor, film type, for through-hole mounting` → market GLO | 0.057254902 | kg | — | SUBSTITUTED | |
| r211 | `fan, for power supply unit, desktop computer` → market GLO | 0.014313725 | kg | — | SUBSTITUTED | |
| r212 | `Inductor, other` → `production of inductor, other` | 0.386470588 | kg | — | SUBSTITUTED | Jasper's own process; its recipe is not in this workbook |
| r213 | `inductor, ring core choke type` → market GLO | 0.100196078 | kg | — | SUBSTITUTED | |
| r214 | `metal working, average for aluminium product manufacturing` → market GLO | 0.085882353 | kg | — | SUBSTITUTED | |
| r215 | `metal working, average for steel product manufacturing` → market GLO | 0.27 | kg | — | SUBSTITUTED | |
| r216 | `printed wiring board, through-hole mounted, unspecified, Pb containing` → market GLO | 0 | kg | — | NOT-APPLICABLE | zero |
| r217 | `printed wiring board, through-hole mounted, unspecified, Pb free` → market GLO | 0.028627451 | kg | — | SUBSTITUTED | |
| r218 | `steel, low-alloyed` → market GLO | 0.27 | kg | — | SUBSTITUTED | Casing, 27 wt% (§2.4.3) |
| r219–r221 | lorry EURO 5 RER 1 t*km; sea GLO 8 t*km; train Europe w/o CH 1 t*km (per kg) | 1 / 8 / 1 | t*km | — | BOUNDARY (delivery) | and inside a substituted parent |
| r223 | `transformer, for grid connection` | 1 | kg | `stepup_transformers.containerised_lv_stepup_per_mw` (mass only) | SUBSTITUTED (stated) | Transcribed in full in the S1 section |
| r226–r233, r237 | nine material/forming rows | see S1 | kg | — | SUBSTITUTED (stated) | |
| r234–r236 | lorry EURO 5 RER 1 t*km; sea GLO 8 t*km; train Europe w/o CH 1 t*km (per kg) | 1 / 8 / 1 | t*km | — | BOUNDARY (delivery) | |

Air-cooled-only rows, not applicable to the liquid design: r12–r22 `CSS (air cooling)` (6 racks, 600 kg PCS, 4,100 kg transformer, same 30 kg controller and 43.9 t block), r25–r32 `Air cooling system` (514 kg AC, 144 cooling-in-pack units, delivery transport), r86–r91 `cooling in battery pack (air cooled)`, r94–r102 `Battery rack (air cooling)` (24 packs, 20.5155 kg cable = 0.705 % × 2,910, 494.7 kg rack = 17 % × 2,910), r104–r122 air-cooled `Battery pack` (14.33 kWh, Ellingsen rows 0.9548 / 2.0289 / 0.2924, PWB surface 0.1965, lorry 1.2157, train 7.2944). All NOT-APPLICABLE.

## Module rows with no source row — with the module's grade

| Module activity | Row | Amount | Grade in module | Comment |
|---|---|---|---|---|
| `bess_module_47kwh_liquid` | `al_wrought` + `sheet_rolling_al` for "Aluminium endbars (Ellingsen)" | 3.1302 kg each | ASSUMED | Source names Ellingsen 2014's dataset (liquid r39); the metal and forming are the module's reading |
| `bess_module_47kwh_liquid` | `cu_cathode`, `sheet_rolling_cu`, `al_wrought`, `sheet_rolling_al` for "Bimetallic busbars and washers (Ellingsen)" | 3.32585 kg each (`BIMETALLIC_COPPER_SHARE = 0.5`) | ASSUMED | Even split stated at bess.py l. 176–181 ("moves the total by under 1 %") |
| `bess_module_47kwh_liquid` | `cu_cathode` + `sheet_rolling_cu` for "Copper end-busbars (Ellingsen)" | 0.9586 kg each | ASSUMED | |
| `bess_dc_block_liquid_1unit` | `electronics_control` for the BESS controller | 30.0 kg | ASSUMED | Source composition is Jasper 2022's HSS controller (§2.4.4 ref 12), not in the workbook; the proxy scores ≈ +28 % against Jasper's implied 24.9 kg CO₂e/kg |
| `bess_container_20ft_1unit` | `concrete_block_de` | 43,900 kg | TRANSCRIBED (relocated) | Source row is liquid r17 on the CSS; moved to the container so `fuel_cell.py` (l. 535, one container per `FC_KW_PER_CONTAINER` = 1,000 kW) shares it |
| `bess_lfp_cell_1kwh_cn` / `_de` | factory electricity 18 kWh, heat 68.4 MJ per kWh | — | TRANSCRIBED (from the paper, not the workbook) | §2.4.1 p. 557 — see Parameters |
| all cell activities (`bess_*_1kg`, `bess_lfp_cell_materials_1unit`) | Voß 2025 | — | — | Outside this ledger (Voß is its own source); the only Jasper row is liquid r43 |
| process-name/geography swaps | `r134a` (GLO market, 3.11 name "tetrafluoroethane"), `train_glo` (market group for transport, freight train), `ethylene_glycol` GLO for RoW, `polycarbonate` GLO for RoW | — | stated in `processes` comments | None changes an amount |

No module row on the Jasper side is invented beyond these; every exchange in the twenty Jasper activities traces to a sheet row above.

## Parameters — each vs the document

| Parameter | Module | Document | Verdict |
|---|---|---|---|
| `CSS_KWH` | 3,008.0 | Table 2 p. 556 "1600 kW/3008 kWh"; text p. 556 "3008 kWh with a power rating of 1600 kW"; Table 3 System 2064\|**3008**; Fig. 4 denominator (SI "Numerical results" r2 "per kWh storage capacity") | ✓ |
| `CSS_KW` | 1,600.0 | Table 2 "1600 kW"; Symtech Solar "Megatron 1.6 MW x 3 MWh" (ref 46) | ✓. Note §2.4.3 sizes the **transformer** at 1,800 kVA for this system (power factor ≈0.9 + margins); `CSS_TX_KW = 1_600.0` is the PCS rating, as the module says |
| `CSS_RACKS` | 8 | Table 2 "8 racks (376.01 kWh)"; p. 556 "eight racks with eight modules each" | ✓ |
| `CSS_MODULES_PER_RACK` | 8 | Table 2 "8 modules (47 kWh)"; liquid r27 `Battery pack 8` | ✓ |
| `CSS_MODULE_KWH` | 47.0 ("LFP *47000/176.6") | Table 2 "47 kWh"; Table 3 "47.00"; liquid r43 formula; 48s1p × 306 Ah × 3.2 V = 47.0 kWh | ✓ |
| `CSS_COOLING_PLATES` | 8 × 8 = 64 | liquid r59 `num_powersection*num_batterypack` (formula only); §2.4.2 one plate per module | ✓ by design; parameter values not printed; EOL sheet used 144 (see r59 note) |
| `CSS_NITRILE_KG` | 0.75 × 64 = 48 kg | liquid r62 `0.75*num_batterypack*num_powersection` | ✓ (same caveat) |
| `CELL_FACTORY_KWH_ELECTRICITY` / `_GAS` | 18.0 / 19.0 kWh per kWh; gas as 68.4 MJ heat | §2.4.1 p. 557: "following Degen et al. (2023) [67] … The production of LFP cells requires 18 kWh electricity and 19 kWh natural gas per kWh of battery capacity, while SIB production requires 11 kWh electricity and 12 kWh natural gas" | ✓ exact. Not in the workbook (the cell is linked, not reproduced) |
| Graphite 65:35 (`GRAPHITE_SYNTHETIC_SHARE = 0.75` chosen instead) | module says Jasper's 65:35 "is ecoinvent 3.11's default mix, not a market statement" | §2.4.1: "The assumed ratio of natural to synthetic graphite corresponds to the default process composition in the database (35% natural and 65% synthetic)"; Acheson powder route "as implemented in the latest version of ecoinvent 3.11" | ✓ the module's characterisation is accurate; the 75:25 choice is Voß's (SOURCE_DIFF S9) |
| Rack capacity 376 kWh (activity name) | 376 | Table 2 "376.01 kWh"; Table 3 "376" | ✓ |
| Cell 306 Ah (docstring) | 306 Ah | Table 2 "LFP (3.2 V/306 Ah)", "48s1p" | ✓ |
| Container weight (not a parameter) | — | Table 2 28.5 t (liquid), rack 2,540 kg | The rack bill (8 × (266.14 kg cells + 42.64 kg packaging) + 431.8 + 17.9 + 15.5) sums to ≈2,935 kg, 16 % over Table 2's 2,540 kg: a source-internal inconsistency, not a transcription issue |
| `JASPER_FIG4_LC_LFP` | see Claims | SI "Numerical results of Figures" r6–r16 col D | ✓ all 11 |
| Depth of discharge 80 % (SOURCES.md l. 302) | 80 % | §2.4.5 "The depth of discharge was kept constant at 80%" | ✓ |

## 21 Oct restores re-checked

**#1 the concrete block.** Liquid sheet **r17**: Flow `concrete block`, Amount **43.9**, Unit **t**, Provider **`concrete block production | concrete block | Cutoff, U - DE`** — on the `CSS (liquid cooled)` process (r12), one per container, beside the 8 racks, controller, container, fire suppression, cooling, PCS and transformer. Identical on the air-cooled CSS (air r18). Paper §2.4.4 p. 558 derives it (6.06 × 2.43 m footprint + 0.2 m per side, 1 m deep, 2,400 kg/m³ = 43.9 t, "consistent with observations from a field visit"), and Fig. 4 carries it as "Concrete foundation" 2.056 kg CO₂e/kWh (SI results r12 col D). The module: `bess_container_20ft_1unit` → `("concrete_block_de", 43_900.0, kg)` with process `concrete block production` [DE] (bess.py l. 327, l. 942); `BESS_SCOPE["foundation"]` says INCLUDED since 21 Oct. **Confirmed: printed amount, unit and provider match; the only difference is the level (container activity rather than CSS), which does not change the per-container or per-kWh quantity.** The EOL counterpart (liquid EOL r44 `waste concrete block 43.9 t → Treatment of concrete block`) is outside the boundary.

**#2** (fuel cell shares the pad) is an inheritance of #1 via `fuel_cell.py` l. 535; nothing in Jasper to check.

**S9** 65:35 — see Parameters; a documented choice, not a transcription issue.

## S1 — Jasper's container-transformer per-kg recipe, transcribed exactly

Air-cooled production sheet, process `transformer, for grid connection`, reference 1 kg (r223), header r225. Columns: Flow | Amount | Unit | Provider | Description | Avoided waste. The Description column (F) is **empty on every row** — the workbook carries no origin note for this process.

| Row | Flow | Amount | Unit | Provider (as printed) |
|---|---|---|---|---|
| r226 | base oil | 0.14 | kg | market for base oil \| base oil \| Cutoff, U - GLO |
| r227 | copper, cathode | 0.25 | kg | market for copper, cathode \| copper, cathode \| Cutoff, U - GLO |
| r228 | electronics, for control units | 0.09 | kg | market for electronics, for control units \| electronics, for control units \| Cutoff, U - GLO |
| r229 | metal working, average for metal product manufacturing | 0.31 | kg | market for metal working, average for metal product manufacturing \| … \| Cutoff, U - GLO |
| r230 | metal working, average for steel product manufacturing | 0.14 | kg | market for metal working, average for steel product manufacturing \| … \| Cutoff, U - GLO |
| r231 | steel, 3.2% silicon alloy, for grain oriented electrical steel | 0.31 | kg | market for steel, 3.2% silicon alloy, for grain oriented electrical steel \| … \| Cutoff, U - **RER** |
| r232 | steel, low-alloyed | 0.14 | kg | market for steel, low-alloyed \| steel, low-alloyed \| Cutoff, U - GLO |
| r233 | transformer, high voltage use | 0.07 | kg | market for transformer, high voltage use \| transformer, high voltage use \| Cutoff, U - GLO |
| r234 | transport, freight, lorry, 16-32 metric ton, diesel, EURO 5 | 1 | t*km | market for … EURO 5 \| … \| Cutoff, U - RER |
| r235 | transport, freight, sea, container ship, heavy fuel oil | 8 | t*km | market for … \| … \| Cutoff, U - GLO |
| r236 | transport, freight, train, fleet average | 1 | t*km | market for … \| … \| Cutoff, U - Europe without Switzerland |
| r237 | wire drawing, copper | 0.25 | kg | market for wire drawing, copper \| wire drawing, copper \| Cutoff, U - GLO |

Mass rows sum to 1.00 kg: 0.14 + 0.25 + 0.09 + 0.31 + 0.14 + 0.07 = 1.00. Forming rows: metal working 0.31 (metal) + 0.14 (steel), wire drawing 0.25 (= the copper). Transport rows are the delivery triplet (1,000 km lorry RER + 8,000 km sea + 1,000 km rail Europe, per kg), outside this study's boundary regardless. SOURCE_DIFF S1's summary of the recipe matches this transcription exactly.

**What the SI and paper say about its origin.** The workbook says nothing. Paper §2.4.3 pp. 557–558 (verbatim in substance): the transformer LCI "is derived from Hunziker et al. (2020) [75], which provides a detailed inventory for a conventional line-frequency transformer (LFT) with an on-load tap changer (OLTC), commonly used in PV power plants. The reference transformer in the cited study is rated at **630 kVA with a total mass of 2666 kg**. For the CSS in this study, higher-rated transformers are required: 1200 kVA for the air-cooled system and **1800 kVA for the liquid-cooled system**. These ratings include a power factor of approximately 0.9, as well as thermal and overload margins… Scaling was performed based on commercially available transformers of the required ratings and their reported weights. For instance, commercially available 1200 kVA and 1800 kVA transformers weigh approximately 4.1 t and **5.5 t**, respectively, including tanks, accessories, and oil [76,77]. The weight distribution of transformer components closely matches the shares reported by Hunziker et al.; for example, the tank and accessories constitute 36 wt% according to the manufacturer and 31 wt% in the study. Therefore, the composition per kg of transformer mass was modeled according to the study by Hunziker et al. (2020)." Ref 75: C. Hunziker, J. Lehmann, T. Keller, T. Heim, N. Schulz, *Sustain. Energy Grids Netw.* 2020, 21, 100314. Ref 76 (4.1 t): Daelim "1200 kVA Substation Transformer-13.8kV". **Ref 77 (the 5.5 t that `CSS_TX_KG` carries): Larson Electronics "1800 kVA Distribution Transformer – 480V Delta Primary – 220Y/127 Wye-N Secondary – NEMA 3R – 60Hz"** — an LV/LV, 60 Hz unit, not a 20/0.4 kV step-up.

So the repo's statements are confirmed by the paper: Hunziker 2020, 630 kVA, OLTC, mass-scaled to 1,800 kVA using commercial weights (`stepup_transformers.py` l. 116–127 and the activity comment l. 643–648; SOURCES.md l. 911–922). Two things the decision should also carry: (i) the 0.09 kg/kg electronics row being "the tap changer's" is the repo's inference, as it already says (Hunziker not held; the workbook's description cell is blank); (ii) the **mass** the module keeps (5,500 kg) rests on ref 77, an LV/LV distribution unit, so the stated substitution swaps the composition but keeps a mass whose reference machine is also not a 20/0.4 kV unit. 5,500 kg / 1.8 MVA = 3,056 kg/MVA against the IEA unit's 2,272 kg/MVA at 2.5 MVA (module comment l. 640–641); the module's 3,437.5 kg/MW follows from dividing by the 1,600 kW PCS rating rather than the 1,800 kVA transformer rating.

## Claims to check

**"Jasper publish no split for the container transformer."** False, as SOURCE_DIFF says: air-cooled sheet r226–r237 above. Already corrected in `stepup_transformers.py` (l. 116–117 "Jasper do give a per-kg recipe (air-cooled sheet rows 225–236; until 21 Oct this module wrongly said they did not)"), `bess.py` docstring l. 83–84, SOURCES.md l. 911–918 and SOURCE_DIFF. **Still stale in two places:** `docs/CARBON_PLAN.md` l. 394 "(Jasper publish no split)" and `optimisation/DATA_GAPS.md` l. 59 "because Jasper publish no split".

**"Foundation excluded"** — stale since 21 Oct in four places: `optimisation/battery.py` l. 197 (`LCA_CAVEATS["jasper_voss_2026"]` … "foundation, delivery to site and end-of-life"), `optimisation/coefficients.py` l. 120 ("excludes PCS, transformer, foundation"), `optimisation/ASSUMPTIONS.md` l. 252 ("no foundation"), `optimisation/SOURCES.md` l. 408 ("concrete foundation (civils are outside every capital inventory) are excluded" — contradicts l. 301 and the table at l. 334–343 of the same file, which carry the block). SOURCES.md l. 408 also still says "transformer (battery step-up closed as negligible, 4 Sep)", superseded by the 15 Oct activity.

**`bess.JASPER_FIG4_LC_LFP`** against SI "Numerical results of Figures", Figure 4 block ("in kg CO2 eq. / kWh storage capacity"), column D = LFP LC:

| Key | Module | SI r / value | Match |
|---|---|---|---|
| cells | 95.44 | r6 95.43857073860738 | ✓ |
| modules_wo_cells | 6.57 | r7 6.570376808196812 | ✓ |
| racks | 6.59 | r8 6.592916784422201 | ✓ |
| pcs | 8.29 | r9 8.292270688870113 | ✓ |
| container | 3.50 | r10 3.503705046095678 | ✓ |
| transformer | 14.01 | r11 14.008599034913962 | ✓ |
| foundation | 2.06 | r12 2.0561277589454754 | ✓ |
| cooling | 2.64 | r13 2.643638556302982 | ✓ |
| fire_suppression | 0.76 | r14 0.7579664143612765 | ✓ |
| others | 0.25 | r15 0.2479544364187518 | ✓ |
| sum | 140.11 | r16 140.11212626713464 | ✓ |

The "Results in all EF categories" sheet r8 gives Climate change, LC LFP, 140.112 per kWh (total 421,457 kg CO₂e per 3,008 kWh container) — consistent. Fig. 4 is cradle-to-gate (§3.1 p. 559) and, as the inventories show, includes the delivery-transport rows; the module's "with transport" is right. The figure image itself could not be rendered (no `pdftoppm`); the caption (p. 560) and the SI numbers were used.

**Licence.** Cover sheet r17: "All data is published under CC-BY-NC license and free for re-use, as long as the source is properly cited." Paper p. 550: "Licensed under CC-BY-NC 4.0". The workbook may therefore be copied into the repository for this non-commercial research use with attribution (title, authors, DOI, Zenodo DOI) and the licence notice carried with the copy; the NC term would bind any commercial reuse of the repo's copy. The ecoinvent dataset *names* in the workbook are not ecoinvent data and raise no separate licence issue.

**Other source-internal inconsistencies worth knowing (module follows the SI in each):** paper §2.4.4 "two 12 kg fire extinguishers using HFC-134a" vs SI one 21 kg tank at 70 % heptafluoropropane (HFC-227ea), 14.7 kg agent; paper §2.4.2 "copper pipes" vs SI 138.92 kg chromium steel 18/8 + drawing of pipe, steel; paper "cement board" vs SI 664.66 kg gypsum plasterboard + 0.19 m³ cement-bonded wood wool; the cooling-plate/nitrile parameter (64 by design, 144 in the EOL sheet); the rack bill ≈2,935 kg vs Table 2's 2,540 kg.

## Summary

Counts, liquid-cooled production sheet (125 rows): 72 IN (10 process-header rows + 62 exchange rows, including the two formula rows r59/r62 and the three upstream-transport rows r31/r32/r51/r52 counted among them), 4 IN-PROXY (r16 controller, r39–r41 Ellingsen), 4 BOUNDARY (r10 end-of-life; r66–r68 delivery to site), 2 SUBSTITUTED (r21 PCS, r22 transformer), 3 NOT-APPLICABLE (r38, r46, r47 sodium-ion), **0 MISSING**, 0 IN-DIFFERS; the remaining rows are blank or headers (r1–r4, r7–r9, r14, r26, r37, r56, r72, r79, r97, r106, r113, r123). Air-cooled sheet processes the liquid CSS shares: 76 exchange rows IN (AC 2, indoor 17, outdoor 16, rack housing 6, container 9, damper 10, fire system 4, tank 2, HFC 6, panel 4), 12 BOUNDARY (delivery triplets on container, fire system, PCS, transformer), 21 SUBSTITUTED (PCS 12 incl. the `Inductor, other` sub-process, transformer 9), 1 NOT-APPLICABLE (r216 zero). Air-cooled-only process blocks: NOT-APPLICABLE.

Most important findings, in order:

1. **Nothing inside the boundary is missing.** Every material, energy and upstream-transport row of the liquid-cooled design is in `bess.py` at the printed amount and provider (3.9.1 equivalents noted), and the 43.9 t concrete block (liquid r17, `concrete block production`, DE) is confirmed and now carried on the container activity. SOURCE_DIFF's "every material row in" holds.
2. **S1 is confirmed in substance and transcribed in full** (air r226–r237). The origin is in the paper only (§2.4.3): Hunziker 2020, 630 kVA LFT with OLTC, 2,666 kg, mass-scaled to 1,800 kVA. The 5.5 t that `CSS_TX_KG` keeps comes from ref 77, a Larson Electronics 480 V Δ / 220Y/127 V NEMA 3R 60 Hz unit — so the representativeness argument that sets aside Jasper's composition also touches the mass the module retains. The workbook's description cell is blank; the OLTC-electronics link stays an inference.
3. **The cooling-plate count is a formula, not a value.** 64 is right by design and by the Fig. 4 reproduction, but Jasper's own EOL sheet treats 144 plates and 109.37 kg plastic (= 0.75 × 144 + 1.37) for the liquid system, i.e. the air-cooled parameters. Worth a one-line note in the module's r59 comment.
4. **The PCS is a substitution, not an exclusion**: Jasper's per-kg PCS recipe exists (air r204–r221) and is replaced by ecoinvent's 500 kW inverter market on the power term, which scores about 2× Jasper's PCS per kW (31.9 vs 15.6 kg CO₂e/kW). Stated in `CSS_EXCLUDED`/SOURCES.md; the ledger records it as SUBSTITUTED.
5. **The BESS controller has a citable composition** (Jasper 2022 HSS controller, ref 12) even though the workbook carries none; the module's electronics proxy errs ≈28 % high against Jasper's implied 24.9 kg CO₂e/kg. ASSUMED is the right grade; the source pointer could be added.
6. **Six stale sentences** remain: "Jasper publish no split" in `docs/CARBON_PLAN.md` l. 394 and `optimisation/DATA_GAPS.md` l. 59; "foundation excluded" in `optimisation/battery.py` l. 197, `optimisation/coefficients.py` l. 120, `optimisation/ASSUMPTIONS.md` l. 252 and `optimisation/SOURCES.md` l. 408 (which also still has the 4 Sep "closed as negligible" transformer line).
7. `JASPER_FIG4_LC_LFP` matches the SI's numerical sheet on all 11 values; the parameters (3,008 kWh, 1,600 kW, 8 × 8 × 47 kWh, 18 + 19 kWh/kWh from Degen via §2.4.1, 65:35 as ecoinvent 3.11's default) are all as the document states. The SI is CC-BY-NC (cover sheet r17; paper p. 550, 4.0), so the workbook may be copied into the repo with attribution for non-commercial use.
