# Smith 2024 — row ledger (22 Oct 2026)

Source: Smith, Sekar, Mirletz, Heath & Margolis (2024), *An Updated Life Cycle Assessment of Utility-Scale Solar Photovoltaic Systems Installed in the United States*, NREL/TP-7A40-87372, Appendix A (Tables A1–A23) and Table 3.
Module: `optimiser_lca/upv.py` (1,001 lines), activities `upv_silica_sand` … `upv_fence` (registry `UPV_TABLES`), `upv_fixed_tilt_mounting`, `upv_fixed_tilt_plant_per_mwp`, `upv_fixed_tilt_om30_per_mwp`, `upv_gb_grid_fleet_1kwh`.
Read-only check; nothing in the repository was changed.

Files read
- `C:\Users\ls1524\Desktop\ukdclca\optimiser_lca\upv.py` — whole file.
- `C:\Users\ls1524\Desktop\ukdclca\optimisation\data\smith-nrel-2024-life-cycle-inventory.md` — whole file (all 23 tables).
- `C:\Users\ls1524\OneDrive - Imperial College London\DC optimiser\sources\smith solar utility lca.pdf` — text layer of PDF pages 52–72 (printed pages 41–61, Appendix A) and of the whole report (Table 3 is PDF page 20, printed page 9; §3.3–3.4 on PDF pages 29–30, printed 18–19); rendered pages 53, 60 and 66 (printed 42, 49, 55) viewed as images.
- `C:\Users\ls1524\Desktop\ukdclca\optimisation\data\UPV-DEFERRED-ISSUES.md` — whole file.
- `C:\Users\ls1524\Desktop\ukdclca\docs\SOURCE_DIFF.md` — whole file (items #4, S6, the "deferred rows" claim, and the Implemented table).
- `C:\Users\ls1524\Desktop\ukdclca\optimisation\SOURCES.md` — the Smith section (lines ~432–623).
- `C:\Users\ls1524\Desktop\ukdclca\optimiser_lca\registry.py` — `UPV_TABLES`, `TX_SOLAR_REPL30`.
- `C:\Users\ls1524\Desktop\ukdclca\optimiser_lca\stepup_transformers.py` — lines 248–262 and 572–592 (S6).

Conventions in the tables below. "Amount" is the amount as printed in the transcription (which the PDF text layer and rendered pages reproduce exactly — see the spot-check). "Module" is the process/flow key in `upv.py` and the amount the module carries. The module writes waste-treatment services with ecoinvent's negative sign; that is a sign convention, not a difference. Smith's biosphere rows name a substance but the module pins each to a compartment; where the compartment differs from Smith's printed one it is noted, and for the four GWP-carrying flows the characterisation factor is compartment-independent so the score is unaffected. Chain links are the `FG(_T[...])` rows.

Dispositions: IN / IN-DIFFERS / BOUNDARY / SUBSTITUTED / NOT-APPLICABLE / MISSING.

---

## Table A1 → upv_silica_sand

Reference flow: silica sand, **9.25E+04 t**. Module: `production_amount=92_500.0`, unit "tonne"; amounts kept as printed per batch and divided at write time. A2 consumes it as 0.0027 t (= 2.70E+00 kg as printed).

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | building, hall | 4.84E+01 | m2 | building_hall, 48.4 | IN | |
| 2 | conveyor belt | 9.15E+00 | m | conveyor_belt, 9.15 | IN | provider: Smith "conveyor belt production RoW" → GLO market (why-note in module) |
| 3 | diesel | 3.16E+04 | kg | diesel, 31_600 | IN | |
| 4 | electricity, medium voltage | 2.62E+05 | kWh | electricity_mv_cn, 262_000 | IN | "Varies by case": module takes the average-import case = weighted national average for China (Smith Table 5) |
| 5 | gravel/sand quarry infrastructure | 4.57E-03 | Item(s) | quarry_infrastructure, 0.00457 unit | IN | |
| 6 | heat, district or industrial, other than natural gas | 1.85E+07 | MJ | heat_hfo, 18_500_000 | IN | |
| 7 | heavy fuel oil | 5.25E+03 | kg | heavy_fuel_oil, 5250 | IN | |
| 8 | industrial machine, heavy, unspecified | 1.08E+03 | kg | industrial_machine, 1080 | IN | |
| 9 | lime, packed | 2.72E+03 | kg | lime_packed, 2720 | IN | |
| 10 | lubricating oil | 1.18E+02 | kg | lubricating_oil_production, 118 | IN | |
| 11 | sand, quartz | 1.00E+05 | t | — (foot comment) | NOT-APPLICABLE | Natural-resource input, no provider, zero GWP100. Prints cleanly on PDF p. 41 (text layer: "t 1.00E+05", empty provider). Deferred; restorable as a zero-GWP row (3.9.1 `Sand, unspecified`, natural resource/in ground, per UPV-DEFERRED-ISSUES) |
| 12 | steel, unalloyed | 1.25E+03 | kg | steel_unalloyed_converter, 1250 | IN | |
| 13 | synthetic rubber | 1.92E+02 | kg | synthetic_rubber, 192 | IN | |
| 14 | transport, freight, light commercial vehicle | 1.49E+03 | t*km | light_commercial_vehicle, 1490 | IN | upstream transport inside the chain: in scope |
| 15 | transport, freight, lorry, unspecified | 1.01E+04 | t*km | lorry, 10_100 | IN | |
| 16 | Water, process and cooling, unspecified natural origin | 1.33E+05 | m3 | — (foot comment) | NOT-APPLICABLE | Natural-resource water input (the md's "output" type is the repeated page header, not a flow direction). Rendered PDF p. 42 viewed: flow name, unit m3 and 1.33E+05 print cleanly; the provider cell in **Smith's own PDF** reads "gravel/sand quarry construction \| RoW" — a layout spill in the source, not in the transcription. Zero GWP. v2 name; nearest 3.9.1 names `Water, cooling, unspecified natural origin` / `Water, unspecified natural origin` |
| 17 | Water, process, unspecified natural origin | 9.71E+05 | m3 | — (foot comment) | NOT-APPLICABLE | As row 16 (PDF provider cell reads "heat production, heavy fuel oil, at industrial furnace 1 MW - RoW", Smith's spill). Zero GWP; 3.9.1 `Water, unspecified natural origin` |

A1: 14 IN, 3 NOT-APPLICABLE (all three at the foot comment, lines 549–552 of `upv.py`). The foot comment's reason ("mangled rows in the source PDF") is the superseded one — see "Deferred rows" below.

---

## Table A2 → upv_silicon_metal

Reference flow: silicon, metallurgical grade, 1 kg. Chain link A2→A1: **2.70E+00 kg** printed; module `FG(A1) 0.0027 tonne` ("2.7 kg as printed").

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | charcoal | 1.70E-01 | kg | charcoal, 0.17 | IN | |
| 2 | coke | 2.31E+01 | MJ | coke, 23.1 | IN | |
| 3 | electric arc furnace converter | 1.00E-11 | Item(s) | eaf_converter, 1e-11 | IN | |
| 4 | electricity, medium voltage | Import: 1.30E+01 / Domestic: 1.10E+01 | kWh | electricity_mv_cn, 13 | IN | import value, as the SE-Asia import case requires |
| 5 | graphite | 1.00E-01 | kg | graphite, 0.1 | IN | |
| 6 | oxygen, liquid | 2.00E-02 | kg | oxygen_liquid, 0.02 | IN | |
| 7 | petroleum coke | 5.00E-01 | kg | petroleum_coke, 0.5 | IN | |
| 8 | silica sand (Table A1) | 2.70E+00 | kg | FG(A1), 0.0027 tonne | IN | chain link; unit converted kg→t because A1 is per tonne |
| 9 | transport, freight train (US) | 6.90E-02 | t*km | freight_train_us, 0.069 | IN | |
| 10 | transport, freight, lorry, unspecified | 1.56E-01 | t*km | lorry, 0.156 | IN | |
| 11 | wood chips, wet, measured as dry mass | 3.25E-03 | kg | wood_chips, 0.00325 | IN | |
| 12 | antimony | 7.85E-09 | kg | antimony, 7.85e-9 | IN | compartment: Smith air/low pop.; module natural resource/in ground (zero GWP) |
| 13 | arsenic | 9.42E-09 | kg | arsenic, 9.42e-9 | IN | compartment as row 12 |
| 14 | boron | 2.79E-07 | kg | boron, 2.79e-7 | IN | module air/urban |
| 15 | cadmium | 3.14E-10 | kg | cadmium, 3.14e-10 | IN | compartment as row 12 |
| 16 | calcium | 7.75E-07 | kg | calcium, 7.75e-7 | IN | compartment as row 12 |
| 17 | carbon dioxide, biogenic | 1.61E+00 | kg | co2_biogenic, 1.61 | IN | 3.9.1 name "Carbon dioxide, non-fossil" |
| 18 | carbon dioxide, fossil | 3.58E+00 | kg | co2_fossil, 3.58 | IN | **GWP100 = 1.** Smith: air/low population density; module ("air",) — factor identical |
| 19 | carbon monoxide, fossil | 1.38E-03 | kg | co_fossil, 0.00138 | IN | |
| 20 | carbon monoxide, land transformation | 6.20E-04 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 42, rendered page viewed). Zero GWP; 3.9.1 `Carbon monoxide, from soil or biomass stock` |
| 21 | chlorine | 7.85E-08 | kg | chlorine, 7.85e-8 | IN | module water/surface water vs Smith air |
| 22 | chromium III | 7.85E-09 | kg | chromium_iii, 7.85e-9 | IN | module soil/industrial vs Smith air |
| 23 | cyanide | 6.87E-06 | kg | cyanide, 6.87e-6 | IN | module air/low pop., long-term |
| 24 | fluorine | 3.88E-08 | kg | fluorine, 3.88e-8 | IN | |
| 25 | heat, waste | 7.13E+01 | MJ | heat_waste, 71.3 | IN | module soil/forestry vs Smith air/unspecified (docstring admits) |
| 26 | hydrogen fluoride | 5.00E-04 | kg | hf, 0.0005 | IN | |
| 27 | hydrogen sulfide | 5.00E-04 | kg | h2s, 0.0005 | IN | |
| 28 | iron | 3.88E-06 | kg | iron, 3.88e-6 | IN | module natural resource |
| 29 | lead | 3.44E-07 | kg | lead_resource, 3.44e-7 | IN | module natural resource |
| 30 | mercury | 7.85E-09 | kg | mercury, 7.85e-9 | IN | module natural resource |
| 31 | nitrogen oxides | 9.74E-03 | kg | nox, 0.00974 | IN | |
| 32 | NMVOC, non-methane volatile organic compounds, unspecified origin | 9.60E-05 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 43). Zero GWP; 3.9.1 `NMVOC, non-methane volatile organic compounds` |
| 33 | particulates, >10 μm | 7.75E-03 | kg | pm10, 0.00775 | IN | 3.9.1 name "Particulate Matter, > 10 um" |
| 34 | potassium | 6.20E-05 | kg | potassium, 6.2e-5 | IN | module natural resource |
| 35 | silicon | 7.51E-03 | kg | silicon, 0.00751 | IN | module water/surface water vs Smith air |
| 36 | slag from metallurgical grade silicon production | 2.50E-02 | kg | slag_mg_silicon, −0.025 | IN | treatment service, negative sign |
| 37 | sodium | 7.75E-07 | kg | sodium_soil, 7.75e-7 | IN | module soil vs Smith air |
| 38 | sulfur dioxide | 1.22E-02 | kg | so2, 0.0122 | IN | |
| 39 | tin | 7.85E-09 | kg | tin_resource, 7.85e-9 | IN | module natural resource |

A2: 37 IN, 2 NOT-APPLICABLE (foot comment, lines 599–601).

---

## Table A3 → upv_polysilicon

Reference flow: silicon, solar grade, 1 kg. Chain link A3→A2: **1.26E+00 kg**; module `FG(A2) 1.26`.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | chlorine, gaseous | 2.15E-01 | kg | chlorine_gas, 0.215 | IN | |
| 2 | electricity, high voltage | 7.20E+01 | kWh | electricity_hv_cn, 72 | IN | China national grid, HV |
| 3 | graphite | 5.40E-03 | kg | graphite, 0.0054 | IN | |
| 4 | heat, district or industrial, natural gas | 7.00E+01 | MJ | heat_gas, 70 | IN | |
| 5 | hydrogen, liquid | 5.36E-02 | kg | hydrogen_liquid, 0.0536 | IN | |
| 6 | nitrogen, liquid | 1.29E+01 | kg | nitrogen_liquid, 12.9 | IN | |
| 7 | quicklime, milled, packed | 5.80E-01 | kg | quicklime_packed, 0.58 | IN | md types it "output" (page-header artefact); it is an input |
| 8 | silicon, metallurgical grade (Table A2) | 1.26E+00 | kg | FG(A2), 1.26 | IN | chain link |
| 9 | silicone factory | 1.00E-11 | Item(s) | silicone_factory, 1e-11 | IN | |
| 10 | sodium hydroxide, without water, in 50% solution state | 3.50E-01 | kg | naoh_50pct, 0.35 | IN | |
| 11 | transport, freight train (US) | 3.65E+00 | t*km | freight_train_us, 3.65 | IN | |
| 12 | transport, freight, lorry, unspecified | 2.87E+00 | t*km | lorry, 2.87 | IN | |
| 13 | AOX, adsorbable organic halogen as Cl | 1.26E-05 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 44). Zero GWP; 3.9.1 `AOX, Adsorbable Organic Halogen` |
| 14 | BOD5, biological oxygen demand | 2.05E-04 | kg | bod5, 0.000205 | IN | |
| 15 | chloride | 3.60E-02 | kg | chloride, 0.036 | IN | |
| 16 | COD, chemical oxygen demand | 2.02E-03 | kg | cod, 0.00202 | IN | module water/ocean vs Smith surface water |
| 17 | copper, ion | 1.02E-07 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly. Zero GWP; 3.9.1 `Copper ion` (per UPV-DEFERRED-ISSUES) |
| 18 | DOC, dissolved organic carbon | 9.10E-04 | kg | doc, 0.00091 | IN | |
| 19 | heat, waste | 3.96E+02 | MJ | heat_waste, 396 | IN | |
| 20 | iron, ion | 5.61E-06 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly. Zero GWP; 3.9.1 `Iron ion` |
| 21 | nitrogen | 2.08E-04 | kg | nitrogen, 0.000208 | IN | module air vs Smith water/surface |
| 22 | phosphate | 2.80E-06 | kg | phosphate, 2.8e-6 | IN | module water/ground- |
| 23 | sodium, ion | 3.38E-02 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly. Zero GWP; 3.9.1 `Sodium` (water) |
| 24 | TOC, total organic carbon | 9.10E-04 | kg | toc, 0.00091 | IN | |
| 25 | zinc, ion | 1.96E-06 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly. Zero GWP; 3.9.1 `Zinc II` |

A3: 20 IN, 5 NOT-APPLICABLE (foot comment, lines 630–635).

---

## Table A4 → upv_cz_ingot

Reference flow: silicon, single crystal, Czochralski process, photovoltaics, 1 kg (the md's spurious row "process, photovoltaics \| output" is the wrapped reference-flow name, not a flow). Chain link A4→A3: **1.03E+00 kg**; module `FG(A3) 1.03`.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | acetone, liquid | 4.90E-02 | kg | acetone, 0.049 | IN | |
| 2 | argon, liquid | 4.60E-02 | kg | argon_liquid, 0.046 | IN | |
| 3 | ceramic tile | 6.20E-02 | kg | ceramic_tile, 0.062 | IN | |
| 4 | electricity, medium voltage | 3.84E+01 | kWh | electricity_mv_cn, 38.4 | IN | |
| 5 | hydrochloric acid, without water, in 30% solution state | 4.38E-04 | kg | hcl_30pct_production, 0.000438 | IN | provider is the production process, as printed |
| 6 | hydrogen fluoride | 3.51E-03 | kg | hydrogen_fluoride, 0.00351 | IN | |
| 7 | lime, hydrated, packed | 2.20E-02 | kg | lime_hydrated, 0.022 | IN | |
| 8 | nitric acid, without water, in 50% solution state | 7.78E-03 | kg | nitric_acid_50pct, 0.00778 | IN | |
| 9 | silicon, solar grade (Table A3) | 1.03E+00 | kg | FG(A3), 1.03 | IN | chain link |
| 10 | silicone factory | 5.00E-12 | Item(s) | silicone_factory, 5e-12 | IN | |
| 11 | sodium hydroxide, without water, in 50% solution state | 4.78E-03 | kg | naoh_50pct, 0.00478 | IN | |
| 12 | transport, freight train (US) | 1.41E+00 | t*km | freight_train_us, 1.41 | IN | |
| 13 | transport, freight, lorry, unspecified | 1.13E+00 | t*km | lorry, 1.13 | IN | |
| 14 | water, completely softened (US) | 6.84E-02 | kg | water_softened_us, 0.0684 | IN | |
| 15 | Water, cooling, unspecified natural origin | 2.33E+00 | m3 | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 45: "m3 2.33E+00", empty provider). Natural-resource input; zero GWP; 3.9.1 `Water, cooling, unspecified natural origin` exists under that very name |
| 16 | BOD5, biological oxygen demand | 1.30E-01 | kg | bod5, 0.13 | IN | |
| 17 | COD, chemical oxygen demand | 1.30E-01 | kg | cod, 0.13 | IN | |
| 18 | DOC, dissolved organic carbon | 4.05E-02 | kg | doc, 0.0405 | IN | |
| 19 | fluoride | 2.37E-03 | kg | fluoride, 0.00237 | IN | module soil/agricultural vs Smith water/surface (docstring admits) |
| 20 | heat, waste | 1.15E+02 | MJ | heat_waste, 115 | IN | |
| 21 | hydrocarbons, unspecified | 2.28E-02 | kg | hydrocarbons, 0.0228 | IN | module soil/agricultural vs Smith water/surface |
| 22 | hydroxide | 7.42E-03 | kg | hydroxide, 0.00742 | IN | |
| 23 | nitrogen | 9.10E-03 | kg | nitrogen, 0.0091 | IN | |
| 24 | TOC, total organic carbon | 4.05E-02 | kg | toc, 0.0405 | IN | |
| 25 | waste, from silicon wafer production, inorganic | 1.00E-01 | kg | waste_wafer_inorganic, −0.1 | IN | treatment service |
| 26 | water (emission to air/unspecified) | 3.00E-01 | m3 | water, 0.3 m3 | IN | module pins "Water" to water/ocean for every water row |
| 27 | water (emission to water/unspecified) | 2.20E+00 | m3 | water, 2.2 m3 | IN | as row 26 |

A4: 26 IN, 1 NOT-APPLICABLE (foot comment, lines 671–672).

---

## Table A5 → upv_wafer

Reference flow: single-Si wafer, photovoltaic, 1 m2. Chain link A5→A4: **5.95E-01 kg**; module `FG(A4) 0.595`.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | acrylic binder, with water, in 54% solution state | 2.00E-03 | kg | acrylic_binder_54pct, 0.002 | IN | |
| 2 | alkylbenzene sulfonate, linear, petrochemical | 3.40E-02 | kg | alkylbenzene_sulfonate, 0.034 | IN | |
| 3 | brass | 7.45E-03 | kg | brass, 0.00745 | IN | |
| 4 | citric acid | 1.87E-01 | kg | citric_acid, 0.187 | IN | |
| 5 | electricity, medium voltage | 2.35E+00 | kWh | electricity_mv_cn, 2.35 | IN | |
| 6 | glass wool mat | 1.06E-02 | kg | glass_wool_mat, 0.0106 | IN | |
| 7 | heat, district or industrial, natural gas | 1.80E+00 | MJ | heat_gas, 1.8 | IN | |
| 8 | hydrogen peroxide, without water, in 50% solution state | 2.53E-02 | kg | h2o2_50pct, 0.0253 | IN | |
| 9 | potassium hydroxide | 3.81E-03 | kg | koh, 0.00381 | IN | |
| 10 | silicon, single crystal, Czochralski process, photovoltaics (Table A4) | 5.95E-01 | kg | FG(A4), 0.595 | IN | chain link |
| 11 | sodium hydroxide, without water, in 50% solution state | 1.50E-02 | kg | naoh_50pct, 0.015 | IN | |
| 12 | steel, low-alloyed, hot rolled | 8.96E-04 | kg | steel_low_alloyed_hr, 0.000896 | IN | |
| 13 | wafer factory | 2.00E-06 | Item(s) | wafer_factory, 2e-6 | IN | |
| 14 | water, completely softened (US) | 2.17E+01 | kg | water_softened_us, 21.7 | IN | |
| 15 | wire drawing, steel | 8.96E-04 | kg | wire_drawing_steel, 0.000896 | IN | |
| 16 | AOX, adsorbable organic halogen as Cl | 5.01E-04 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 46). Zero GWP |
| 17 | BOD5, biological oxygen demand | 2.96E-02 | kg | bod5, 0.0296 | IN | |
| 18 | COD, chemical oxygen demand | 2.96E-02 | kg | cod, 0.0296 | IN | |
| 19 | copper, ion | 6.05E-05 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 47). Zero GWP |
| 20 | DOC, dissolved organic carbon | 1.11E-02 | kg | doc, 0.0111 | IN | |
| 21 | heat, waste | 8.00E+00 | MJ | heat_waste, 8 | IN | |
| 22 | nitrogen | 9.94E-03 | kg | nitrogen, 0.00994 | IN | |
| 23 | TOC, total organic carbon | 1.11E-02 | kg | toc, 0.0111 | IN | |
| 24 | waste, from silicon wafer production | 2.00E-02 | kg | waste_wafer, −0.02 | IN | treatment service |
| 25 | water (to air/unspecified) | 9.75E-03 | m3 | water, 0.00975 | IN | |
| 26 | water (to water/unspecified) | 5.53E-02 | m3 | water, 0.0553 | IN | |

A5: 24 IN, 2 NOT-APPLICABLE (foot comment, lines 706–708).

---

## Table A6 → upv_trimethylaluminum

Reference flow: Trimethylaluminum, purified, **18 kg**. Module `production_amount=18.0`, amounts as printed per batch. A7 consumes 2.88E-04 kg.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | aluminium chloride | 1.34E+00 | kg | aluminium_chloride, 1.34 | IN | |
| 2 | aluminium, wrought alloy | 2.16E+01 | kg | aluminium_wrought, 21.6 | IN | |
| 3 | electricity, medium voltage | 5.57E+00 | kWh | electricity_mv_cn, 5.57 | IN | |
| 4 | helium | 1.20E-01 | kg | helium, 0.12 | IN | |
| 5 | methylchloride | 6.09E+01 | kg | methylchloride, 60.9 | IN | |
| 6 | nitrogen, liquid | 8.25E-01 | kg | nitrogen_liquid, 0.825 | IN | |
| 7 | paraffin | 1.53E-01 | kg | paraffin, 0.153 | IN | |
| 8 | sodium | 3.30E+01 | kg | sodium, 33 | IN | |
| 9 | fly ash and scrubber sludge | 3.80E+00 | kg | fly_ash_incineration, −3.8 | IN | treatment service |
| 10 | hazardous waste, for incineration | 1.07E+02 | kg | hazardous_waste_incineration, −107 | IN | treatment service |

A6: 10 IN.

---

## Table A7 → upv_perc_cell

Reference flow: photovoltaic cell, single-Si wafer, 1 m2. Chain links A7→A5 **1.02E+00 m2** (module `FG(A5) 1.02`) and A7→A6 **2.88E-04 kg** (module `FG(A6) 0.000288`). Rendered PDF p. 49 (printed) viewed for rows 21–43.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | ammonia, anhydrous, liquid | 1.65E-02 | kg | ammonia, 0.0165 | IN | |
| 2 | calcium chloride | 2.07E-02 | kg | calcium_chloride, 0.0207 | IN | |
| 3 | electricity, medium voltage | 6.03E+00 | kWh | electricity_mv_th, 6.03 | IN | Thailand = Smith Table 5 average-import case for cell fabrication |
| 4 | heat, district or industrial, natural gas | 3.55E+00 | MJ | heat_gas, 3.55 | IN | |
| 5 | hydrochloric acid, without water, in 30% solution state | 6.81E-02 | kg | hcl_30pct, 0.0681 | IN | market, as printed |
| 6 | hydrogen fluoride | 7.47E-02 | kg | hydrogen_fluoride, 0.0747 | IN | |
| 7 | metallization paste, back side | 1.02E-03 | kg | paste_back, 0.00102 | IN | provider: Smith "Müller et al. 2021" → ecoinvent back-side paste market (why-note) |
| 8 | metallization paste, back side, aluminium | 9.01E-03 | kg | paste_back_aluminium, 0.00901 | IN | |
| 9 | metallization paste, front side | 3.48E-03 | kg | paste_front, 0.00348 | IN | |
| 10 | nitric acid, without water, in 50% solution state | 8.22E-02 | kg | nitric_acid_50pct, 0.0822 | IN | |
| 11 | nitrogen, liquid | 2.62E+00 | kg | nitrogen_liquid, 2.62 | IN | |
| 12 | nitrous oxide | 7.66E-03 | kg | nitrous_oxide, 0.00766 | IN | |
| 13 | oxygen, liquid | 3.34E-01 | kg | oxygen_liquid, 0.334 | IN | |
| 14 | phosphorus oxychloride | 1.82E-04 | kg | phosphorus_oxychloride, 0.000182 | IN | |
| 15 | photovoltaic cell factory | 4.00E-07 | Item(s) | cell_factory, 4e-7 | IN | |
| 16 | potassium hydroxide | 1.51E-01 | kg | koh, 0.151 | IN | |
| 17 | propane | 4.14E-02 | kg | propane, 0.0414 | IN | |
| 18 | silicon tetrahydride | 2.83E-03 | kg | silane, 0.00283 | IN | |
| 19 | single-Si wafer, photovoltaic (Table A5) | 1.02E+00 | m2 | FG(A5), 1.02 | IN | chain link |
| 20 | solvent, organic | 1.23E-02 | kg | solvent_organic, 0.0123 | IN | |
| 21 | sulfuric acid | 2.06E-02 | kg | sulfuric_acid, 0.0206 | IN | |
| 22 | transport, freight train (RoW) | 1.52E+00 | t*km | freight_train_row, 1.52 | IN | |
| 23 | transport, freight, lorry, unspecified | 2.74E-01 | t*km | lorry, 0.274 | IN | |
| 24 | transport, freight, sea, container ship — Import cases only | 1.57E+00 | t*km | container_ship, 1.57 | IN | inter-stage leg inside the manufacturing chain (China wafer → Thailand cell); import case applies |
| 25 | trimethylaluminum (Table A6) | 2.88E-04 | kg | FG(A6), 0.000288 | IN | chain link |
| 26 | water, completely softened (RoW) | 2.32E+01 | kg | water_softened_row, 23.2 | IN | |
| 27 | Water, cooling, unspecified natural origin | 2.31E-01 | m3 | — (foot comment) | NOT-APPLICABLE | rendered p. 49 viewed: prints cleanly, empty provider. Zero GWP |
| 28 | water, deionised | 3.94E+01 | kg | water_deionised, 39.4 | IN | |
| 29 | aluminium | 7.73E-04 | kg | aluminium, 0.000773 | IN | module natural resource/in ground vs Smith air/high pop. (zero GWP) |
| 30 | ethane, hexafluoro-, HFC-116 | 1.19E-04 | kg | c2f6, 0.000119 | IN | **GWP100 12,400.** Smith air/high pop.; module air/urban — factor identical |
| 31 | heat, waste | 5.18E+01 | MJ | heat_waste, 51.8 | IN | |
| 32 | hydrogen chloride | 2.66E-04 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (p. 49 viewed). Zero GWP; 3.9.1 `Hydrochloric acid` |
| 33 | hydrogen fluoride | 4.85E-06 | kg | hf, 4.85e-6 | IN | |
| 34 | lead | 3.48E-07 | kg | lead_resource, 3.48e-7 | IN | module natural resource |
| 35 | methane, tetrafluoro-, R-14 | 2.48E-04 | kg | cf4, 0.000248 | IN | **GWP100 7,380.** Smith air/high pop.; module air/non-urban — factor identical |
| 36 | nitrogen oxides | 5.00E-05 | kg | nox, 5e-5 | IN | |
| 37 | NMVOC, non-methane volatile organic compounds, unspecified origin | 1.94E-01 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (p. 49 viewed). Zero GWP |
| 38 | particulates, <2.5 μm | 2.66E-03 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (p. 49 viewed). Zero GWP; 3.9.1 `Particulate Matter, < 2.5 um` |
| 39 | silicon | 7.27E-05 | kg | silicon, 7.27e-5 | IN | |
| 40 | silver | 6.60E-06 | kg | silver, 6.6e-6 | IN | module natural resource vs Smith air/low pop. |
| 41 | waste, from silicon wafer production, inorganic | 6.41E-03 | kg | waste_wafer_inorganic, −0.00641 | IN | treatment service |
| 42 | wastewater from PV cell production | 1.32E-02 | m3 | wastewater_pv_cell, −0.0132 | IN | treatment service |
| 43 | water (to air/unspecified) | 1.68E-02 | m3 | water, 0.0168 | IN | |
| 44 | water (to water/unspecified) | 2.77E-01 | m3 | water, 0.277 | IN | |

A7: 40 IN, 4 NOT-APPLICABLE (foot comment, lines 775–780).

---

## Table A8 → upv_perc_module

Reference flow: photovoltaic panel, 1 m2. Chain link A8→A7: **9.00E-01 m2**; module `FG(A7) 0.9`.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | adipic acid | 3.69E-04 | kg | adipic_acid, 0.000369 | IN | |
| 2 | aluminium alloy, AlMg3 | 1.51E+00 | kg | aluminium_almg3, 1.51 | IN | the module frame |
| 3 | copper, cathode | 1.48E-01 | kg | copper_cathode, 0.148 | IN | |
| 4 | corrugated board box | 7.63E-01 | kg | corrugated_board_box, 0.763 | IN | RoW market, as printed |
| 5 | diode, auxilliaries and energy use | 2.81E-03 | kg | diode, 0.00281 | IN | |
| 6 | electricity, medium voltage | 3.32E+00 | kWh | electricity_mv_th, 3.32 | IN | Thailand, Table 5 average-import module assembly |
| 7 | ethylvinylacetate, foil | 7.93E-01 | kg | eva_foil, 0.793 | IN | |
| 8 | EUR-flat pallet | 5.00E-02 | Item(s) | eur_pallet, 0.05 | IN | |
| 9 | glass fibre reinforced plastic, polyamide, injection moulded | 1.88E-01 | kg | gfrp_polyamide, 0.188 | IN | |
| 10 | lead | 1.08E-02 | kg | lead, 0.0108 | IN | |
| 11 | lubricating oil | 1.61E-03 | kg | lubricating_oil, 0.00161 | IN | |
| 12 | metal working, average for aluminium product manufacturing | 1.51E+00 | kg | metal_working_aluminium, 1.51 | IN | |
| 13 | packaging film, low density polyethylene | 4.01E-02 | kg | ldpe_film, 0.0401 | IN | |
| 14 | photovoltaic cell, single-Si wafer (Table A7) | 9.00E-01 | m2 | FG(A7), 0.9 | IN | chain link |
| 15 | photovoltaic panel factory | 4.00E-06 | Item(s) | panel_factory, 4e-6 | IN | |
| 16 | polyethylene terephthalate, granulate, amorphous | 2.81E-01 | kg | pet_granulate, 0.281 | IN | |
| 17 | polyethylene, high density, granulate | 2.42E-02 | kg | hdpe_granulate, 0.0242 | IN | |
| 18 | polyethylene, low density, granulate | 5.48E-02 | kg | ldpe_granulate, 0.0548 | IN | |
| 19 | polyvinylfluoride, film | 4.51E-02 | kg | pvf_film, 0.0451 | IN | |
| 20 | silicone product | 1.44E-01 | kg | silicone_product, 0.144 | IN | |
| 21 | solar glass, low-iron | 8.00E+00 | kg | solar_glass, 8 | IN | |
| 22 | tempering, flat glass | 8.00E+00 | kg | glass_tempering, 8 | IN | |
| 23 | tin | 1.04E-02 | kg | tin, 0.0104 | IN | |
| 24 | transport, freight train (RoW) | 1.66E+01 | t*km | freight_train_row, 16.6 | IN | |
| 25 | transport, freight, lorry, unspecified | 2.99E+00 | t*km | lorry, 2.99 | IN | |
| 26 | Water, cooling, unspecified natural origin | 7.16E-02 | m3 | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 51). Zero GWP |
| 27 | wire drawing, copper | 1.48E-01 | kg | wire_drawing_copper, 0.148 | IN | |
| 28 | carbon dioxide, fossil | 2.18E-02 | kg | co2_fossil, 0.0218 | IN | **GWP100 = 1** |
| 29 | heat, waste | 1.34E+01 | MJ | heat_waste, 13.4 | IN | |
| 30 | municipal solid waste | 9.34E-02 | kg | municipal_solid_waste, −0.0934 | IN | treatment service |
| 31 | NMVOC, non-methane volatile organic compounds, unspecified origin | 8.06E-03 | kg | — (foot comment) | NOT-APPLICABLE | prints cleanly (PDF p. 51). Zero GWP |
| 32 | waste mineral oil | 1.61E-03 | kg | waste_mineral_oil, −0.00161 | IN | |
| 33 | waste plastic, mixture | 2.48E-02 | kg | waste_plastic, −0.0248 | IN | |
| 34 | waste polyvinylfluoride | 9.02E-04 | kg | waste_pvf, −0.000902 | IN | |
| 35 | waste, from silicon wafer production | 3.52E-03 | kg | waste_wafer, −0.00352 | IN | |
| 36 | water | 2.79E-02 | **kg** | water, 0.0279 kg | IN | Smith prints kg for this one water row; module keeps kg as printed |

A8: 34 IN, 2 NOT-APPLICABLE (foot comment, lines 824–827).

---

## Table A9 — Single-axis tracker → SUBSTITUTED

Reference flow: 1-axis tracker (per module area), 1 m2. Whole table replaced by IEA PVPS T12-33:2026 dataset Z-PV-239 (fixed-tilt 20° pile-driven steel table) as activity `upv_fixed_tilt_mounting`, stated in the module docstring, `UPV_PV_SCOPE["mounting"]`, `_COMMENT`, and SOURCES.md. Structure mass 9.730 kg/m² (IEA) vs 9.618 kg/m² (Smith: 9.45 + 0.0836 + 0.0836 kg; the `UPV_PV_SCOPE` string says "9.764", the docstring and `_COMMENT` say "9.618" — an internal inconsistency in the module's own prose, see Summary).

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | aluminium, wrought alloy | 8.36E-02 | kg | aluminium_wrought 0.2849 (IEA clamps) | SUBSTITUTED | |
| 2 | battery cell, Li-ion, LFP | 4.60E-03 | kg | — | SUBSTITUTED | no equivalent in a fixed-tilt table |
| 3 | corrugated board box (US) | 8.58E-02 | kg | corrugated_board_box_rer 0.0926 (IEA packaging) | SUBSTITUTED | |
| 4 | electric motor, vehicle | 5.65E-02 | kg | — | SUBSTITUTED | no motor on fixed tilt |
| 5 | photovoltaic panel, single-Si wafer (module assembly VN-MY - RoW) | 5.00E-03 | m2 | — | SUBSTITUTED | the tracker's own power supply; listed in UPV-DEFERRED-ISSUES as "mangled-row-skipped" — moot, A9 is out whole |
| 6 | polystyrene, high impact | 7.97E-04 | kg | — | SUBSTITUTED | |
| 7 | section bar extrusion, aluminium | 8.36E-02 | kg | sheet_rolling_aluminium 0.2849 (IEA) | SUBSTITUTED | |
| 8 | section bar rolling, steel | 9.45E+00 | kg | section_bar_rolling_steel 9.2354 (IEA) | SUBSTITUTED | |
| 9 | section bar rolling, steel | 8.36E-02 | kg | (in row 8) | SUBSTITUTED | |
| 10 | steel, chromium steel 18/8 | 8.36E-02 | kg | chromium_steel 0.2043 (IEA fasteners) | SUBSTITUTED | |
| 11 | steel, low-alloyed, hot rolled | 9.45E+00 | kg | steel_low_alloyed 9.2354 (IEA table and piles) | SUBSTITUTED | |

11 rows SUBSTITUTED. The A15 actuator-replacement row (electric motor 1.70E-02 kg) goes with it.

---

## Table A10 → upv_inverter_2700kva

Reference flow: 2.7 MWac inverter, 1 Items. Plain decimals in the source.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | aluminium, wrought alloy | 80 | kg | aluminium_wrought, 80 | IN | |
| 2 | cable, network cable, category 5, without plugs | 940 | m | cable_cat5, 940 | IN | |
| 3 | cable, three-conductor cable | 61 | m | cable_three_conductor, 61 | IN | |
| 4 | capacitor, electrolyte type, >2 cm height | 5 | kg | capacitor_electrolyte, 5 | IN | |
| 5 | capacitor, film type, for through-hole mounting | 50 | kg | capacitor_film, 50 | IN | |
| 6 | concrete slab (concrete slab - RoW) | 1.1 | m3 | concrete_slab, 1.1 | IN | provider: production process printed → RoW market used; flagged "sanity-check-wanted" in UPV-DEFERRED-ISSUES (~1,025 kg CO2e/m3, 2.7 % of the inverter) |
| 7 | copper, cathode | 430 | kg | copper_cathode, 430 | IN | |
| 8 | glass fibre reinforced plastic, polyamide, injection moulded | 30 | kg | gfrp_polyamide, 30 | IN | |
| 9 | inductor, ring core choke type | 650 | kg | inductor, 650 | IN | |
| 10 | integrated circuit, logic type | 0.2 | kg | integrated_circuit, 0.2 | IN | |
| 11 | lubricating oil | 1 | kg | lubricating_oil, 1 | IN | |
| 12 | printed wiring board, through-hole mounted, unspecified, Pb free | 3 | kg | pwb_through_hole, 3 | IN | |
| 13 | reinforcing steel | 1200 | kg | reinforcing_steel, 1200 | IN | |
| 14 | transformer, high voltage use | 100 | kg | transformer_hv, 100 | IN | the inverter's internal transformer, not the step-up |
| 15 | transistor, wired, big size, through-hole mounting | 0.3 | kg | transistor, 0.3 | IN | |
| 16 | fan, for power supply unit, desktop computer | 0.2 | kg | fan, 0.2 | IN | |

A10: 16 IN.

---

## Table A11 — Transformer (2.7 MWac) → SUBSTITUTED

Reference flow: 2.7 MWac transformer, 1 items. Replaced by `stepup_transformers` (`TX_SOLAR`, IEA PVPS Z-PV-276 at 20/0.4 kV), stated in `UPV_PV_SCOPE["step_up_transformer"]`, docstring substitution 2 and SOURCES.md. Physical-plausibility ground: the bill below sums to 53,450 kg of materials (Cu 5,800 + epoxy 1,050 + ferrite 23,600 + oil 21,000 + rebar 2,000 — wire drawing and injection moulding are forming services on masses already counted, concrete is in m3) → 19,796 kg/MVA at 2.7 MVA, ~9× a measured unit's specific mass.

| # | Source row (as printed in the transcription) | Amount | Unit | Module | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | concrete slab (ROW) | 1.10E+00 | m3 | — | SUBSTITUTED | same pad as A10 (Smith §3.2) |
| 2 | copper, cathode | 5.80E+03 | kg | — | SUBSTITUTED | |
| 3 | epoxy resin, liquid | 1.05E+03 | kg | — | SUBSTITUTED | |
| 4 | ferrite | 2.36E+04 | kg | — | SUBSTITUTED | 23.6 t of ferrite in a 2.7 MVA unit is the implausible row |
| 5 | injection moulding | 1.05E+03 | kg | — | SUBSTITUTED | |
| 6 | lubricating oil | 2.10E+04 | kg | — | SUBSTITUTED | 21 t of oil |
| 7 | reinforcing steel | 2.00E+03 | kg | — | SUBSTITUTED | |
| 8 | wire drawing, copper | 5.80E+03 | kg | — | SUBSTITUTED | |

8 rows SUBSTITUTED. The A14 count (4.30E-05 per m2) and the A15 replacement (1.30E-05 per m2) follow it: the count is replaced by the step-up module's own sizing, the replacement by `TX_SOLAR_REPL30` (S6, below).

---

## Table A12 → upv_electrical_bos

Reference flow: electrical balance-of-system (per module area), 1 m2.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | aluminium, wrought alloy | 0.4 | kg | aluminium_wrought, 0.4 | IN | provider cell truncated in the PDF ("wrought alloy \| Cutoff, U - GLO"); the market is unambiguous |
| 2 | epoxy resin, liquid | 4.9E-05 | kg | epoxy_resin, 4.9e-5 | IN | |
| 3 | nylon 6 | 6.4E-03 | kg | nylon_6, 0.0064 | IN | |
| 4 | polycarbonate | 6.1E-05 | kg | polycarbonate, 6.1e-5 | IN | |
| 5 | polyvinylchloride, bulk polymerised | 0.11 | kg | pvc, 0.11 | IN | |
| 6 | wire drawing, copper | 0.4 | kg | wire_drawing_copper, 0.4 | IN | Smith applies copper wire drawing to 0.4 kg while the metal row is aluminium — as printed, carried as printed |

A12: 6 IN.

---

## Table A13 → upv_fence

Reference flow: fence (per module area), 1 m2.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | concrete, 25MPa | 2.9E-05 | m3 | concrete_25mpa, 2.9e-5 | IN | |
| 2 | section bar rolling, steel | 4.6E-02 | kg | section_bar_rolling_steel, 0.046 | IN | |
| 3 | steel, low-alloyed | 9.9E-02 | kg | steel_low_alloyed, 0.099 | IN | |
| 4 | wire drawing, steel | 5.3E-02 | kg | wire_drawing_steel, 0.053 | IN | |
| 5 | zinc coat, coils | 3.3E-03 | m2 | zinc_coat_coils, 0.0033 | IN | |

A13: 5 IN.

---

## Table A14 — Installation → parameters on `upv_fixed_tilt_plant_per_mwp`

Reference flow: Installed UPV system (per module area), 1 m2. Not an activity of its own; the kept rows enter the plant activity scaled by `_M2 = UPV_PV_M2_PER_MWP = 4,913.6 m2/MWp`. Rendered PDF p. 55 (printed) viewed for every row. The md's "(per module area) \| output" row is the wrapped reference-flow name; the md splits the 0.55 lorry row across two lines (layout artefact, value intact).

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | 1-axis tracker (per module area) — Table A9 | 1 | m2 | FG(UPV_MOUNT), 4,913.6 m2/MWp | SUBSTITUTED | IEA Z-PV-239 fixed tilt, 1 m2 per m2 of module |
| 2 | diesel, burned in building machine | 2.6 | MJ | diesel_building_machine, _M2 × 2.6 = 12,775 MJ/MWp | IN | installation energy on site: in scope (not transport) |
| 3 | 2.7 MWac inverter — Table A10 | 4.30E-05 | Item(s) | FG(UPV_INVERTER), 1/(2.7 × 1.34) = 0.2764 /MWp | IN-DIFFERS | Smith: 4.30E-05 × 4,913.6 = **0.2113 /MWp** (implies ILR 1.75 at 405 W / 1.99 m2). Module: **0.2764 /MWp** from the stated ILR 1.34 (+31 %). Deliberate, stated (substitution 3) |
| 4 | Occupation, unspecified, natural (non-use) | 3 | m2*a | occupation_natural, _M2 × 3.0 = 14,741 m2·a/MWp | IN | zero GWP100; flow name as printed; see "21 Oct restore" |
| 5 | photovoltaic panel — Table A8 | 1 | m2 | FG(UPV_MODULE), 4,913.6 m2/MWp | IN | |
| 6 | 2.7 MWac transformer — Table A11 | 4.30E-05 | Item(s) | — (stepup_transformers) | SUBSTITUTED | |
| 7 | transport, freight train (RoW) | 2.2 | t*km | — | BOUNDARY (delivery to site) | |
| 8 | transport, freight train (RoW) | 2 | t*km | — | BOUNDARY (delivery to site) | |
| 9 | transport, freight, lorry, unspecified | 3.3E-03 | t*km | — | BOUNDARY (delivery to site) | |
| 10 | transport, freight, lorry, unspecified | 0.51 | t*km | — | BOUNDARY (delivery to site) | |
| 11 | transport, freight, lorry, unspecified | 0.55 | t*km | — | BOUNDARY (delivery to site) | |
| 12 | transport, freight, sea, container ship — Import cases only | 201 | t*km | — | BOUNDARY (delivery to site) | the ~1.5 % understatement the module states |
| 13 | electrical balance of system (per module area) — Table A12 | 1 | m2 | FG(A12), 4,913.6 m2/MWp | IN | |
| 14 | fence (per module area) — Table A13 | 1 | m2 | FG(A13), 4,913.6 m2/MWp | IN | |

A14: 5 IN, 1 IN-DIFFERS, 2 SUBSTITUTED, 6 BOUNDARY. Smith §3.3 confirms the transport rows are "delivery (transportation) of components" to site (Frischknecht 2020b distances), so the boundary call is right.

---

## Table A15 — Operations and maintenance → parameters on `upv_fixed_tilt_om30_per_mwp`

Reference flow: 30 years operation and maintenance (per module area), 1 m2. Rendered PDF p. 55 viewed.

| # | Source row (as printed in the transcription) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | electric motor, vehicle | 1.70E-02 | kg | — | SUBSTITUTED | the tracker actuator (Danelli & Brivio 35 % over 35 y); fixed tilt has none. Stated in `UPV_PV_SCOPE["operation_maintenance"]` |
| 2 | 2.7 MWac inverter — Table A10 | 1.30E-05 | Item(s) | FG(UPV_INVERTER), 0.2764 × 0.3023 = 0.08357 /MWp | IN-DIFFERS | Smith: 1.30E-05 × 4,913.6 = **0.06388 /MWp**; module **0.08357 /MWp** — the fraction 1.30E-05/4.30E-05 = 30.2 % transfers to the module's own count (substitution 4) |
| 3 | petrol, low-sulfur | 5.50E-02 | kg | petrol_low_sulfur, _M2 × 0.055 = 270.2 kg/MWp | IN | vegetation management |
| 4 | photovoltaic panel — Table A8 | 1.5E-02 | m2 | FG(UPV_MODULE), _M2 × 0.015 = 73.7 m2/MWp | IN | 0.05 %/yr × 30 y (Klise 2018) |
| 5 | 2.7 MWac transformer — Table A11 | 1.30E-05 | Item(s) | stepup_transformers `TX_SOLAR_REPL30` | SUBSTITUTED (S6) | same 30.2 % fraction, on the IEA unit and the step-up module's count; implemented 21 Oct |

A15: 2 IN, 1 IN-DIFFERS, 2 SUBSTITUTED.

---

## Tables A16–A23 — end of life → BOUNDARY

All out as end-of-life, as everywhere in this study (`UPV_PV_SCOPE["end_of_life"]`). For the record: A16 decommissioning (diesel 2.6 MJ, installed system 1 m2, module EOL 10.9 kg, transformer EOL 4.3E-05, BOS EOL 1, tracker EOL 1, inverter EOL 4.3E-05 — Smith's own text says "2.6 MWac" and "Table A24", typos as printed); A17 landfill (5 rows); A18 partial recycling (22 rows; the md's documented name-column misalignment is Smith's own, verified on the text layer); A19 high-recovery recycling (23 rows); A20 transformer EOL (8); A21 BOS EOL (4); A22 tracker EOL (6); A23 inverter EOL (10). None is in the module and none should be. A16's diesel (2.6 MJ, "equivalent to the diesel use for installation") is decommissioning energy, so it is EOL, not installation — correctly out.

---

## Transcription spot-check — md vs PDF

**Method.** (1) Automated: every scientific-notation value in the PDF text layer of pages 52–72 was extracted and compared, table by table, with the transcription. (2) By eye: rendered pages 42, 49 and 55 (printed numbering) were viewed as images and read row by row against the md; A10, A12–A15 and Table 3 were read from the text layer.

**Result: no numeric mismatch in any table.** The automated comparison matches 290 scientific-notation values in the PDF against the md for A1–A17 and A19–A23 exactly (A1 18, A2 40, A3 25, A4 27, A5 26, A6 10, A7 44, A8 36, A9 11, A11 8, A12 3, A13 5, A14 3, A15 5, A16 2, A19 23); A18's 16 values were confirmed individually by grep on its page range (5.62E-02 and 6.61E-03 occur twice each in both, as input and output). The md's 303 count exceeds the PDF's 290 only by the A18 duplicates my first table split mis-assigned and A19's reference-flow "1.00E+00" repeated in the md heading. Plain-decimal values (A10, A12–A16) also match.

Values read by eye on rendered pages (≥ 30, 5 tables plus Table 3):

| Table | Values checked (PDF = md) | Count |
|---|---|---|
| A1 (p. 41–42) | 4.84E+01, 9.15E+00, 3.16E+04, 2.62E+05, 4.57E-03, 1.85E+07, 5.25E+03, 1.08E+03, 2.72E+03, 1.18E+02, 1.00E+05, 1.25E+03, 1.92E+02, 1.49E+03, 1.01E+04, 1.33E+05, 9.71E+05 | 17 |
| A2 (p. 42, rendered) | 1.70E-01, 2.31E+01, 1.00E-11, 1.30E+01 / 1.10E+01, 1.00E-01, 2.00E-02, 5.00E-01, 2.70E+00, 6.90E-02, 1.56E-01, 3.25E-03, 7.85E-09, 9.42E-09, 2.79E-07, 3.14E-10, 7.75E-07, 1.61E+00, **3.58E+00**, 1.38E-03, 6.20E-04 | 20 |
| A7 (p. 49, rendered) | 2.06E-02, 1.52E+00, 2.74E-01, 1.57E+00, 2.88E-04, 2.32E+01, 2.31E-01, 3.94E+01, 7.73E-04, **1.19E-04**, 5.18E+01, 2.66E-04, 4.85E-06, 3.48E-07, **2.48E-04**, 5.00E-05, 1.94E-01, 2.66E-03, 7.27E-05, 6.60E-06, 6.41E-03, 1.32E-02, 1.68E-02 | 23 |
| A10 (text layer) | 80, 940, 61, 5, 50, 1.1, 430, 30, 650, 0.2, 1, 3, 1200, 100, 0.3, 0.2 | 16 |
| A14 + A15 (p. 55, rendered) | 1, 2.6, 4.30E-05, 3, 1, 4.30E-05, 2.2, 2, 3.3E-03, 0.51, 0.55, 201, 1, 1; 1.70E-02, 1.30E-05, 5.50E-02, 1.5E-02, 1.30E-05 | 19 |
| Table 3 (p. 9) | 405 Wdc, 1.99 m2, 20.3 %, ILR 1.34, inverter efficiency 96 %, degradation 0.7 %/yr, 30-y life, 100 MWdc | 8 |

Total by eye: 103 values, 0 mismatches.

**Non-numeric transcription artefacts** (no effect on the module, which reads amounts only): the "Type" column is unreliable after every page break (rows under a repeated "Output Flows" running header are typed "output" though they are inputs — A1 rows 16–17, A3 rows 7–12, A4 rows 5–15, A5 rows 19–26, A7 rows 21–28, A8 rows 19–27, all of A9, A10 rows 9–16, A14 rows 3–14); the known pattern of provider text bleeding into the Amount cell (A1, A2, A5, A7, A9, A10, A14) is present but every amount is recoverable and was recovered correctly; spurious rows "process, photovoltaics" (A4) and "(per module area)" (A12–A16) are wrapped reference-flow names; A14's 0.55 row is split across two md rows. Smith's own typos reproduced faithfully: A16 "2.6 MWac", "Table A24"; A17–A23 "Table A17" as the reference-flow cross-reference.

---

## Module rows with no source row

Within the eleven Smith activities: **none** — all 232 exchange rows (counted from `upv.py`: A1 14, A2 37, A3 20, A4 26, A5 24, A6 10, A7 40, A8 34, A10 16, A12 6, A13 5) tie to a printed Smith row at the printed amount. SOURCE_DIFF says "231 rows in"; my count is 232 (A4 has 26, not 25). Provider substitutions on three rows (conveyor belt → GLO market; back-side paste → ecoinvent market; concrete slab → market) are stated in `why=` notes; the amounts are Smith's.

Rows from another source, listed as such:

| Activity | Row | Amount | Source | Grade |
|---|---|---|---|---|
| upv_fixed_tilt_mounting | steel_low_alloyed | 9.23544 kg/m2 | IEA PVPS T12-33:2026 Z-PV-239 | TRANSCRIBED (another source) |
| " | aluminium_wrought | 0.28494 kg/m2 | IEA Z-PV-239 | TRANSCRIBED |
| " | chromium_steel | 0.20434 kg/m2 | IEA Z-PV-239 | TRANSCRIBED |
| " | polypropylene | 0.00534 kg/m2 | IEA Z-PV-239 | TRANSCRIBED |
| " | corrugated_board_box_rer | 0.09259 kg/m2 | IEA Z-PV-239 (packaging) | TRANSCRIBED |
| " | section_bar_rolling_steel | 9.23544 kg/m2 | IEA Z-PV-239 (forming) | TRANSCRIBED |
| " | sheet_rolling_aluminium | 0.28494 kg/m2 | IEA Z-PV-239 | TRANSCRIBED |
| " | wire_drawing_steel | 0.20434 kg/m2 | IEA Z-PV-239 | TRANSCRIBED |
| " | zinc_coat_pieces | 0.51404 m2/m2 | IEA Z-PV-239 | TRANSCRIBED |
| " | lorry / freight_train_rer / light_commercial_vehicle | 1.946 / 5.838 / 0.973 t·km/m2 | IEA Z-PV-239 (material-to-factory legs, restored 21 Oct) | TRANSCRIBED |
| " | waste_paperboard_incineration_row / waste_pe_pp_row | −0.0926 / −0.00534 kg/m2 | IEA Z-PV-239 | TRANSCRIBED |
| " | transformation_from_pasture / transformation_to_industrial / occupation_industrial | 2.25 / 2.25 m2; 67.5 m2·a per m2 | IEA Z-PV-239 land rows | TRANSCRIBED, zero GWP |
| upv_gb_grid_fleet_1kwh | plant and O&M per kWh | 1/(28,842 × 1000) | ecoinvent GB 570 kWp plant yield (renewables_embodied.csv) | DERIVED |

Not checked here against the IEA workbook (out of this ledger's scope); listed so the provenance split is visible.

---

## Parameters

| Parameter | Module | Source | Check |
|---|---|---|---|
| UPV_PV_MODULE_W = 405 | 405 Wdc | Table 3 "405Wdc … = 20.3% × 1.99 m2 × 1,000 Wdc/m2" | TRANSCRIBED, matches |
| UPV_PV_MODULE_M2 = 1.99 | 1.99 m2 | Table 3 | matches |
| UPV_PV_MODULE_EFF = 0.203 | 20.3 % | Table 3 "national average silicon module efficiency" | matches (unused in the inventory beyond the W/m2 identity) |
| UPV_PV_W_PER_M2 | 203.52 W/m2 | derived 405/1.99 | consistent with Table 3's own identity |
| UPV_PV_M2_PER_MWP | 4,913.6 m2/MWp | derived | `check()` holds the inversion |
| UPV_PV_ILR = 1.34 | 1.34 | Table 3 "Inverter loading ratio 1.34" (text-layer rows are shifted; the rendered table pairs 1.34 with the ILR, and §2.1 says "an inverter loading ratio of 1.34") | TRANSCRIBED, matches |
| UPV_PV_INVERTER_MVA = 2.7 | 2.7 MVA | **not Table 3** — from the A10/A11 reference flows "2.7 MWac inverter" and §3.2 "rated for approximately 2.7 MWac" | matches; the docstring's "Table 3 (… 2.7 MWac inverter)" attribution is loose |
| UPV_PV_INVERTERS_PER_MWP | 0.2764 /MWp | derived 1/(2.7 × 1.34) | Smith A14's 4.30E-05 /m2 → 0.2113 /MWp → implied ILR 1/(0.2113 × 2.7) = **1.75**; the module's claim of inconsistency in the source is correct |
| UPV_PV_INSTALL_DIESEL_MJ_PER_M2 = 2.6 | 2.6 MJ/m2 | A14 | matches; 12,775 MJ/MWp |
| Land occupation 3 m2·a per m2 | 14,741 m2·a/MWp | A14 "Occupation, unspecified, natural (non-use) m2*a 3" | matches (see next section) |
| UPV_PV_OM_PETROL_KG_PER_M2 = 5.50E-02 | 270.2 kg/MWp per 30 y | A15 | matches |
| UPV_PV_OM_PANEL_M2_PER_M2 = 1.50E-02 | 73.7 m2/MWp per 30 y | A15 "1.5E-02"; §3.4 0.05 %/yr (Klise) | matches |
| UPV_PV_OM_REPLACEMENT_FRACTION = 1.30E-05/4.30E-05 | 0.3023 | A15 / A14; §3.4 "10% replacement of the inverter and transformer by weight every 10 years based on Mason et al. (2006)" | matches; 30 % over 30 y is Mason's rate as Smith states it |
| S6: UPV_TX_REPLACEMENT_FRACTION_30Y = 1.30E-05/4.30E-05 | 0.3023 | A15 transformer row | implemented in `stepup_transformers.py` lines 251–258 and activity `TX_SOLAR_REPL30` (lines 576–592, registry line 81), charged per year by `optimisation/transformers.py` lines 322–325. SOURCE_DIFF's "Implemented" row for S6 is borne out |
| UPV_PV_OM_REFERENCE_YEARS = 30 | 30 y | A15 reference flow "30 years operation and maintenance"; Table 3 / §2.1 30-year life | matches |
| Supply chain: CN national grid (silicon chain), TH (cell, module) | — | Table 5 "Average emission" column: silicon metal, polysilicon, ingots & wafers → "Weighted national average for China"; PERC cell fabrication and module assembly → "Weighted national average for Thailand"; silica sand → weighted Australia/Cambodia/Malaysia/Pakistan mix | the module puts A1's electricity on CN too (Smith's average import case uses a four-country sand mix) — a stated simplification, immaterial at 262 MWh per 92,500 t |

---

## 21 Oct restore re-checked — #4 land occupation (A14)

Confirmed on the rendered PDF p. 55: row "Occupation, unspecified, natural (non-use)", unit **m2*a**, amount **3**, no provider. Transcription identical. Module: `("occupation_natural", _M2 * 3.0, "square meter-year", …)` on `upv_fixed_tilt_plant_per_mwp`, flow `Occupation, unspecified, natural (non-use)` in ("natural resource", "land") — name as printed, amount as printed, zero GWP100. #4 is correctly restored.

Two observations for whenever a land-use category is scored (no carbon effect now):
1. Smith §3.3 says land occupation "uses a 33% ground coverage ratio", i.e. 1/0.33 ≈ 3 m2 of land per m2 of module. A printed **3 m2·a** is therefore one year's occupation; thirty years at that ratio would be ~90 m2·a per m2. The module carries the printed 3, which is right for a transcription, but the source value itself looks like an occupation *area* mislabelled as area-time.
2. The IEA Z-PV-239 mounting rows restored the same day carry `occupation_industrial` 67.5 m2·a per m2 (2.25 m2 × 30 y) plus two transformation rows on the mounting activity. The plant now has land occupation from two sources for the same ground (3 + 67.5 m2·a per m2). Both are "in the source and inside the boundary", so neither is wrong under the cut-off principle, but they would double-count in any land-use score.

---

## Deferred rows — the 20 in UPV-DEFERRED-ISSUES.md

Each row was located in the PDF text layer; rows 1–3, 11, 14 and 18 also on rendered pages. "Clean" means the flow name, unit and amount are unambiguous in Smith's PDF.

| # | Table | Flow | Amount | Unit | Prints cleanly? | Stated reason (table row / foot comment) | Is the reason right? |
|---|---|---|---|---|---|---|---|
| 1 | A1 | sand, quartz | 1.00E+05 | t | Yes (p. 41; empty provider) | mangled-row-skipped / "mangled rows in the source PDF" | **No** — nothing is mangled; a natural-resource flow with no provider. Zero GWP. The 21 Oct paragraph at the top of the file says so; the table row and the `upv.py` foot comment (line 549) still carry the old reason |
| 2 | A1 | Water, process and cooling, unspecified natural origin | 1.33E+05 | m3 | Yes for name/unit/amount (p. 42 rendered). The provider cell in Smith's PDF really does read "gravel/sand quarry construction \| RoW" — Smith's spill, not the transcription's | mangled-row-skipped, "provider text came from another column" | **Half right**: the provider text is spilled, but in the source, and it is irrelevant to a natural-resource flow. Zero GWP. v2 name; needs a 3.9.1 proxy (`Water, unspecified natural origin` or `Water, cooling, unspecified natural origin`) |
| 3 | A1 | Water, process, unspecified natural origin | 9.71E+05 | m3 | Yes (as #2) | as #2 | as #2; 3.9.1 `Water, unspecified natural origin` |
| 4 | A2 | carbon monoxide, land transformation | 6.20E-04 | kg | Yes (p. 42 rendered) | unmatched-biosphere-flow, "believed zero-GWP, not verified" | Reason right in kind (v2 name), stale in status: the file's own paragraph upgrades it to verified zero GWP; 3.9.1 `Carbon monoxide, from soil or biomass stock` |
| 5 | A2 | NMVOC, …, unspecified origin | 9.60E-05 | kg | Yes (p. 43) | as #4 | as #4; 3.9.1 `NMVOC, non-methane volatile organic compounds` |
| 6 | A3 | AOX, adsorbable organic halogen as Cl | 1.26E-05 | kg | Yes (p. 44) | as #4 | as #4 |
| 7 | A3 | copper, ion | 1.02E-07 | kg | Yes | as #4 | as #4 |
| 8 | A3 | iron, ion | 5.61E-06 | kg | Yes | as #4 | as #4 |
| 9 | A3 | sodium, ion | 3.38E-02 | kg | Yes | as #4 | as #4 |
| 10 | A3 | zinc, ion | 1.96E-06 | kg | Yes | as #4 | as #4 |
| 11 | A4 | Water, cooling, unspecified natural origin | 2.33E+00 | m3 | Yes (p. 45; empty provider) | mangled-row-skipped | **No** — clean; the 3.9.1 flow exists under exactly this name |
| 12 | A5 | AOX, adsorbable organic halogen as Cl | 5.01E-04 | kg | Yes (p. 46) | as #4 | as #4 |
| 13 | A5 | copper, ion | 6.05E-05 | kg | Yes (p. 47) | as #4 | as #4 |
| 14 | A7 | Water, cooling, unspecified natural origin | 2.31E-01 | m3 | Yes (p. 49 rendered; empty provider) | mangled-row-skipped | **No** — clean |
| 15 | A7 | hydrogen chloride | 2.66E-04 | kg | Yes (p. 49 rendered) | as #4 | as #4; 3.9.1 `Hydrochloric acid` |
| 16 | A7 | NMVOC, …, unspecified origin | 1.94E-01 | kg | Yes (p. 49 rendered) | as #4 | as #4 |
| 17 | A7 | particulates, <2.5 μm | 2.66E-03 | kg | Yes (p. 49 rendered) | as #4 | as #4; 3.9.1 `Particulate Matter, < 2.5 um` |
| 18 | A8 | Water, cooling, unspecified natural origin | 7.16E-02 | m3 | Yes (p. 51) | mangled-row-skipped | **No** — clean |
| 19 | A8 | NMVOC, …, unspecified origin | 8.06E-03 | kg | Yes (p. 51) | as #4 | as #4 |
| 20 | A9 | photovoltaic panel, single-Si wafer (module assembly VN-MY - RoW) | 5.00E-03 | m2 | Yes (p. 52; amount in the text layer, provider "module assembly VN-MY - RoW" is Smith's own label) | mangled-row-skipped | Moot: A9 is SUBSTITUTED whole, so this row is out by substitution, not by mangling. It should not be in a "deferred" list at all |

(The 21st entry, A10 concrete slab, is a sanity check on a row that **is** in the module, not a deferred row.)

Verdict on the reasons: the 21 Oct paragraph at the top of UPV-DEFERRED-ISSUES.md is right and the table beneath it is stale — all 20 "issue" and "note" cells still say "mangled-row-skipped" or "believed zero-GWP, not verified". `upv.py` was not updated at all: the docstring (lines 39–41, "cells the PDF mangled, and ecoinvent v2 flow names with no 3.9.1 match") and the seven foot comments (lines 549, 599, 630, 671, 706, 775/777, 824/826) give the superseded reasons. SOURCE_DIFF's "Implemented" table records the deferred-row reasons as fixed "docs only", which is true of the paragraph, not of the table or the code. The 3.9.1 flow names the paragraph cites were not re-verified against the biosphere database in this check (no Brightway session), and `Water, process and cooling, unspecified natural origin` (#2) has no like-named 3.9.1 flow, so one of the 20 needs a stated proxy if restored.

Under the study's own cut-off principle (sourced, in-boundary flows are always in) all 19 real deferred rows qualify for restoration as zero-GWP rows; they are not MISSING only because each sits at a foot comment.

---

## Summary

**Most important finding.** The inventory is complete against Smith inside the study's boundary: every one of the 232 exchange rows in the eleven Smith activities ties to a printed row at the printed amount (no IN-DIFFERS inside A1–A13, no MISSING anywhere), the three inter-stage links and the four GWP-carrying biosphere rows (A2 CO2 fossil 3.58 kg; A7 CF4 2.48E-04 and C2F6 1.19E-04 kg; A8 CO2 fossil 2.18E-02 kg) are all in at the printed amounts, and the transcription itself matches the PDF value for value (290/290 scientific-notation values automated, 103 by eye, 0 mismatches). The only live defect is documentary: the 19 deferred rows are all clean in the PDF and all zero-GWP, but the reasons printed in `upv.py` (docstring and seven foot comments) and in the UPV-DEFERRED-ISSUES.md table are the superseded ones ("mangled", "not verified"); only the file's 21 Oct paragraph is current.

**Counts by disposition (A1–A15, 20 deferred rows counted once).**

| Disposition | Rows | Where |
|---|---|---|
| IN | 232 in A1–A13 + 7 in A14/A15 (diesel, occupation, panel, BOS, fence; petrol, panel replacement) = **239** | |
| IN-DIFFERS | **2** | A14 inverter count 4.30E-05/m2 (0.2113/MWp) → 0.2764/MWp from ILR 1.34; A15 inverter replacement 1.30E-05/m2 (0.0639/MWp) → 0.0836/MWp as a 30.2 % fraction. Both deliberate and stated |
| BOUNDARY (delivery to site) | **6** | A14 transport rows (rail 2.2 + 2; lorry 3.3E-03 + 0.51 + 0.55; sea 201 t·km/m2) |
| BOUNDARY (end of life) | A16–A23, **8 tables, 85 rows** | |
| SUBSTITUTED | **11** (A9) + **8** (A11) + **4** (A14 tracker and transformer; A15 motor and transformer) = **23** | IEA Z-PV-239 mounting; stepup_transformers TX_SOLAR + TX_SOLAR_REPL30 |
| NOT-APPLICABLE (deferred, zero GWP, at a foot comment) | **19** | A1 3, A2 2, A3 5, A4 1, A5 2, A7 4, A8 2 |
| MISSING | **0** | |

**Secondary findings, in order of weight.**
1. `UPV_PV_SCOPE["mounting"]` says Smith's structure is 9.764 kg/m2; the docstring, `_COMMENT` and SOURCES.md say 9.618. A9's steel rows sum to 9.45 + 0.0836 (×2 forming) → the structure is 9.45 kg steel + 0.0836 Al + 0.0836 chromium steel = 9.618 kg/m2 (9.764 would add the motor 0.0565, battery 0.0046, box 0.0858 … no combination gives exactly 9.764). One of the two numbers should go.
2. Smith's A14 "3 m2*a" of land occupation reads as one year's area at his stated 33 % GCR, and the IEA mounting now adds 67.5 m2·a per m2 for the same ground — immaterial for carbon, double-counted for land use.
3. SOURCE_DIFF's "231 rows in" is 232; the docstring attributes the 2.7 MWac inverter size to Table 3, where it is not (it is A10's reference flow and §3.2).
4. Smith's A14 inverter count implies ILR 1.75 against his stated 1.34 — confirmed from the PDF; the module's choice of the stated value is documented and `check()` guards it.
5. Compartments of the zero-GWP biosphere rows are arbitrary (the docstring says so); the four GWP rows are in air compartments whose IPCC 2021 factors do not depend on sub-compartment, so the score is unaffected.
