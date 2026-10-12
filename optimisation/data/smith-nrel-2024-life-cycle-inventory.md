# Life cycle inventory — NREL utility-scale PV LCA (2024)

Transcribed from Appendix A (Tables A1–A23) of Smith, Sekar, Mirletz, Heath & Margolis (2024), *An Updated Life Cycle Assessment of Utility-Scale Solar Photovoltaic Systems Installed in the United States*, NREL. 23 unit processes, 375 flows.

## How to read this

- Each section is one unit process, scaled to the **reference flow** given under its heading.
- `Provider` is the ecoinvent 3.9 process string as printed in the report (`market for X | X | Cutoff, U - GLO`), a compartment path for elementary flows (`elementary flows/emission to air/...`), or a cross-reference to another process here (e.g. `Table A2` means the silicon metal process below).
- `Varies by case defined in Tables 5–6` marks electricity inputs that change with the supply-chain scenario. Imported cases use Southwest China / national China / Northeast China grids for low / average / high emission; domestic cases use ecoinvent NPCC / U.S. national average / Puerto Rico grids.
- Amounts are reproduced verbatim, including qualifiers such as `Import: 1.30E+01` and avoided-burden notes shown in italics.
- Waste-treatment processes (A17–A23) list their reference flow among the inputs, as the source does.

**Known defect in the source.** In **A18** the input-flow block is misaligned: flow names do not correspond to their units and providers — `copper, cathode` is given in MJ with a diesel-combustion provider, and `Carbon dioxide, fossil` appears as an input with a copper-scrap-treatment provider. The name column looks to have been sorted independently of the rest of the row. Verified against the rendered page and transcribed as printed; check against Stolz et al. (2017) before using that inventory.

Every scientific-notation value on the source pages was cross-checked against this transcription: 290 in the report, 290 captured.


---

## A1 — Silica sand production

*Stage:* manufacturing · *Source:* Table A1, PDF pages 52, 53  
*Reference flow:* **Silica sand** — 9.25E+04 t

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| building, hall | input | 4.84E+01 | m2 | building construction, hall - RoW |
| conveyor belt | input | 9.15E+00 | m | conveyor belt production RoW |
| diesel | input | 3.16E+04 | kg | diesel production, petroleum refinery operation - RoW |
| electricity, medium voltage | input | 2.62E+05 | kWh | Varies by case defined in Tables 5–6 |
| gravel/sand quarry infrastructure | input | 4.57E-03 | Item(s) | gravel/sand quarry construction \| RoW |
| heat, district or industrial, other than natural gas | input | 1.85E+07 | MJ | heat production, heavy fuel oil, at industrial furnace 1MW \| RoW |
| heavy fuel oil | input | 5.25E+03 | kg | heavy fuel oil production, petroleum refinery operation \| RoW |
| industrial machine, heavy, unspecified | input | 1.08E+03 | kg | industrial machine production, heavy, unspecified \| - RoW |
| lime, packed | input | 2.72E+03 | kg | lime production, milled, packed - RoW |
| lubricating oil | input | 1.18E+02 | kg | lubricating oil production - RoW |
| sand, quartz | input | 1.00E+05 | t |  |
| steel, unalloyed | input | 1.25E+03 | kg | steel production, converter, unalloyed - RoW |
| synthetic rubber | input | 1.92E+02 | kg | synthetic rubber production - RoW |
| transport, freight, light commercial vehicle | input | 1.49E+03 | t*km | transport, freight, light commercial vehicle - RoW |
| transport, freight, lorry, unspecified | input | 1.01E+04 | t*km | market group for transport, freight, lorry, unspecified \| GLO |
| Water, process and cooling, unspecified natural origin | output | 1.33E+05 gravel/sand quarry construction \| RoW | m3 |  |
| Water, process, unspecified natural origin | output | heat production, heavy fuel oil, at industrial 9.71E+05 furnace 1 MW - RoW | m3 |  |

---

## A2 — Silicon metal production

*Stage:* manufacturing · *Source:* Table A2, PDF pages 53, 54  
*Reference flow:* **silicon, metallurgical grade** — 1 kg

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| charcoal | input | 1.70E-01 | kg | market for charcoal \| charcoal \| Cutoff, U - GLO |
| coke | input | 2.31E+01 | MJ | market for coke \| coke \| Cutoff, U - GLO |
| electric arc furnace converter | input | 1.00E-11 | Item(s) | market for electric arc furnace converter \| electric arc furnace converter \| Cutoff, U - GLO |
| electricity, medium voltage | input | Import: 1.30E+01 Domestic: 1.10E+01 | kWh | Varies by case defined in Tables 5–6 |
| graphite | input | 1.00E-01 | kg | market for graphite \| graphite \| Cutoff, U - GLO |
| oxygen, liquid | input | 2.00E-02 | kg | market for oxygen, liquid \| oxygen, liquid \| Cutoff, U - RoW |
| petroleum coke | input | 5.00E-01 | kg | market for petroleum coke \| petroleum coke \| Cutoff, U - GLO |
| silica sand | input | 2.70E+00 | kg | Table A1. |
| transport, freight train | input | 6.90E-02 | t*km | market for transport, freight train \| transport, freight train \| Cutoff, U - US |
| transport, freight, lorry, unspecified | input | 1.56E-01 | t*km | market group for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - GLO |
| wood chips, wet, measured as dry mass | input | 3.25E-03 | kg | market for wood chips, wet, measured as dry mass \| wood chips, wet, measured as dry mass \| Cutoff, U - RoW |
| antimony | waste/emission | 7.85E-09 | kg | elementary flows/emission to air/low population density |
| arsenic | waste/emission | 9.42E-09 | kg | elementary flows/emission to air/low population density |
| boron | waste/emission | 2.79E-07 | kg | elementary flows/emission to air/low population density |
| cadmium | waste/emission | 3.14E-10 | kg | elementary flows/emission to air/low population density |
| calcium | waste/emission | 7.75E-07 | kg | elementary flows/emission to air/low population density |
| carbon dioxide, biogenic | waste/emission | 1.61E+00 | kg | elementary flows/emission to air/low population density |
| carbon dioxide, fossil | waste/emission | 3.58E+00 | kg | elementary flows/emission to air/low population density |
| carbon monoxide, fossil | waste/emission | 1.38E-03 | kg | elementary flows/emission to air/low population density |
| carbon monoxide, land transformation | waste/emission | 6.20E-04 | kg | elementary flows/emission to air/low population density |
| chlorine | output | 7.85E-08 elementary flows/emission to air/low population density | kg |  |
| chromium III | output | 7.85E-09 elementary flows/emission to air/low population density | kg |  |
| cyanide | output | 6.87E-06 elementary flows/emission to air/low population density | kg |  |
| fluorine | output | 3.88E-08 elementary flows/emission to air/low population density | kg |  |
| heat, waste | output | 7.13E+01 elementary flows/emission to air/unspecified | MJ |  |
| hydrogen fluoride | output | 5.00E-04 elementary flows/emission to air/low population density | kg |  |
| hydrogen sulfide | output | 5.00E-04 elementary flows/emission to air/low population density | kg |  |
| iron | output | 3.88E-06 elementary flows/emission to air/low population density | kg |  |
| lead | output | 3.44E-07 elementary flows/emission to air/low population density | kg |  |
| mercury | output | 7.85E-09 elementary flows/emission to air/low population density | kg |  |
| nitrogen oxides | output | 9.74E-03 elementary flows/emission to air/low population density | kg |  |
| NMVOC, non-methane volatile organic compounds, unspecified origin | output | 9.60E-05 elementary flows/emission to air/low population density | kg |  |
| particulates, >10 μm | output | 7.75E-03 elementary flows/emission to air/low population density | kg |  |
| potassium | output | 6.20E-05 elementary flows/emission to air/low population density | kg |  |
| silicon | output | 7.51E-03 elementary flows/emission to air/low population density | kg |  |
| slag from metallurgical grade silicon production | output | market for slag from metallurgical grade silicon production \| slag from metallurgical grade silicon production \| Cutoff, U - 2.50E-02 GLO | kg |  |
| sodium | output | 7.75E-07 elementary flows/emission to air/low population density | kg |  |
| sulfur dioxide | output | 1.22E-02 elementary flows/emission to air/low population density | kg |  |
| tin | output | 7.85E-09 elementary flows/emission to air/low population density | kg |  |

---

## A3 — Polysilicon production

*Stage:* manufacturing · *Source:* Table A3, PDF pages 54, 55  
*Reference flow:* **silicon, solar grade** — 1 kg

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| chlorine, gaseous | input | 2.15E-01 | kg | market for chlorine, gaseous \| chlorine, gaseous \| Cutoff, U - RoW |
| electricity, high voltage | input | 7.20E+01 | kWh | Varies by case defined in Tables 5–6 |
| graphite | input | 5.40E-03 | kg | market for graphite \| graphite \| Cutoff, U - GLO |
| heat, district or industrial, natural gas | input | 7.00E+01 | MJ | heat production, natural gas, at industrial furnace >100kW \| heat, district or industrial, natural gas \| Cutoff, U - RoW |
| hydrogen, liquid | input | 5.36E-02 | kg | market for hydrogen, liquid \| hydrogen, liquid \| Cutoff, U - RoW |
| nitrogen, liquid | input | 1.29E+01 | kg | market for nitrogen, liquid \| nitrogen, liquid \| Cutoff, U - RoW |
| quicklime, milled, packed | output | 5.80E-01 | kg | market for quicklime, milled, packed \| quicklime, milled, packed \| Cutoff, U - RoW |
| silicon, metallurgical grade | output | 1.26E+00 | kg | Table A2 |
| silicone factory | output | 1.00E-11 | Item(s) | market for silicone factory \| silicone factory \| Cutoff, U - GLO |
| sodium hydroxide, without water, in 50% solution state | output | 3.50E-01 | kg | market for sodium hydroxide, without water, in 50% solution state \| sodium hydroxide, without water, in 50% solution state \| Cutoff, U - GLO |
| transport, freight train | output | 3.65E+00 | t*km | market for transport, freight train \| transport, freight train \| Cutoff, U - US |
| transport, freight, lorry, unspecified | output | 2.87E+00 | t*km | market group for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - GLO |
| AOX, adsorbable organic halogen as Cl | waste/emission | 1.26E-05 | kg | elementary flows/emission to water/surface water |
| BOD5, biological oxygen demand | waste/emission | 2.05E-04 | kg | elementary flows/emission to water/surface water |
| chloride | waste/emission | 3.60E-02 | kg | elementary flows/emission to water/surface water |
| COD, chemical oxygen demand | waste/emission | 2.02E-03 | kg | elementary flows/emission to water/surface water |
| copper, ion | waste/emission | 1.02E-07 | kg | elementary flows/emission to water/surface water |
| DOC, dissolved organic carbon | waste/emission | 9.10E-04 | kg | elementary flows/emission to water/surface water |
| heat, waste | waste/emission | 3.96E+02 | MJ | elementary flows/emission to air/unspecified |
| iron, ion | waste/emission | 5.61E-06 | kg | elementary flows/emission to water/surface water |
| nitrogen | waste/emission | 2.08E-04 | kg | elementary flows/emission to water/surface water |
| phosphate | waste/emission | 2.80E-06 | kg | elementary flows/emission to water/surface water |
| sodium, ion | waste/emission | 3.38E-02 | kg | elementary flows/emission to water/surface water |
| TOC, total organic carbon | waste/emission | 9.10E-04 | kg | elementary flows/emission to water/surface water |
| zinc, ion | waste/emission | 1.96E-06 | kg | elementary flows/emission to water/surface water |

---

## A4 — Czochralski ingot production

*Stage:* manufacturing · *Source:* Table A4, PDF pages 55, 56, 57  
*Reference flow:* **silicon, single crystal, Czochralski** — 1 kg

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| process, photovoltaics | output |  |  |  |
| acetone, liquid | input | 4.90E-02 | kg | market for acetone, liquid \| acetone, liquid \| Cutoff, U - RoW |
| argon, liquid | input | 4.60E-02 | kg | market for argon, liquid \| argon, liquid \| Cutoff, U - RoW |
| ceramic tile | input | 6.20E-02 | kg | market for ceramic tile \| ceramic tile \| Cutoff, U - GLO |
| electricity, medium voltage | input | 3.84E+01 | kWh | Varies by case defined in Tables 5–6 |
| hydrochloric acid, without water, in 30% solution state | output | 4.38E-04 | kg | hydrochloric acid production, from the reaction of hydrogen with chlorine \| hydrochloric acid, without water, in 30% solution state \| Cutoff, U - RoW |
| hydrogen fluoride | output | 3.51E-03 | kg | market for hydrogen fluoride \| hydrogen fluoride \| Cutoff, U - RoW |
| lime, hydrated, packed | output | 2.20E-02 | kg | market for lime, hydrated, packed \| lime, hydrated, packed \| Cutoff, U - RoW |
| nitric acid, without water, in 50% solution state | output | 7.78E-03 | kg | market for nitric acid, without water, in 50% solution state \| nitric acid, without water, in 50% solution state \| Cutoff, U - RoW |
| silicon, solar grade | output | 1.03E+00 | kg | Table A3 |
| silicone factory | output | 5.00E-12 | Item(s) | market for silicone factory \| silicone factory \| Cutoff, U - GLO |
| sodium hydroxide, without water, in 50% solution state | output | 4.78E-03 | kg | market for sodium hydroxide, without water, in 50% solution state \| sodium hydroxide, without water, in 50% solution state \| Cutoff, U - GLO |
| transport, freight train | output | 1.41E+00 | t*km | market for transport, freight train \| transport, freight train \| Cutoff, U - US |
| transport, freight, lorry, unspecified | output | 1.13E+00 | t*km | market group for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - GLO |
| water, completely softened | output | 6.84E-02 | kg | market for water, completely softened \| water, completely softened \| Cutoff, U - US |
| Water, cooling, unspecified natural origin | output | 2.33E+00 | m3 |  |
| BOD5, biological oxygen demand | waste/emission | 1.30E-01 | kg | elementary flows/emission to water/unspecified |
| COD, chemical oxygen demand | waste/emission | 1.30E-01 | kg | elementary flows/emission to water/unspecified |
| DOC, dissolved organic carbon | waste/emission | 4.05E-02 | kg | elementary flows/emission to water/unspecified |
| fluoride | waste/emission | 2.37E-03 | kg | elementary flows/emission to water/surface water |
| heat, waste | waste/emission | 1.15E+02 | MJ | elementary flows/emission to air/low population density |
| hydrocarbons, unspecified | waste/emission | 2.28E-02 | kg | elementary flows/emission to water/surface water |
| hydroxide | waste/emission | 7.42E-03 | kg | elementary flows/emission to water/surface water |
| nitrogen | waste/emission | 9.10E-03 | kg | elementary flows/emission to water/surface water |
| TOC, total organic carbon | waste/emission | 4.05E-02 | kg | elementary flows/emission to water/unspecified |
| waste, from silicon wafer production, inorganic | waste/emission | 1.00E-01 | kg | market for waste, from silicon wafer production, inorganic \| waste, from silicon wafer production, inorganic \| Cutoff, U - GLO |
| water | waste/emission | 3.00E-01 | m3 | elementary flows/emission to air/unspecified |
| water | output | 2.20E+00 elementary flows/emission to water/unspecified | m3 |  |

---

## A5 — Monocrystalline silicon wafer production

*Stage:* manufacturing · *Source:* Table A5, PDF pages 57, 58  
*Reference flow:* **single-Si wafer, photovoltaic** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| acrylic binder, with water, in 54% solution state | input | 2.00E-03 | kg | market for acrylic binder, with water, in 54% solution state \| acrylic binder, with water, in 54% solution state \| Cutoff, U - RoW |
| alkylbenzene sulfonate, linear, petrochemical | input | 3.40E-02 | kg | market for alkylbenzene sulfonate, linear, petrochemical \| alkylbenzene sulfonate, linear, petrochemical \| Cutoff, U - GLO |
| brass | input | 7.45E-03 | kg | market for brass \| brass \| Cutoff, U - RoW |
| citric acid | input | 1.87E-01 | kg | market for citric acid \| citric acid \| Cutoff, U - GLO |
| electricity, medium voltage | input | 2.35E+00 | kWh | Varies by case defined in Tables 5–6 |
| glass wool mat | input | 1.06E-02 | kg | market for glass wool mat \| glass wool mat \| Cutoff, U - GLO |
| heat, district or industrial, natural gas | input | 1.80E+00 | MJ | heat production, natural gas, at industrial furnace >100kW \| heat, district or industrial, natural gas \| Cutoff, U - RoW |
| hydrogen peroxide, without water, in 50% solution state | input | 2.53E-02 | kg | hydrogen peroxide production, product in 50% solution state \| hydrogen peroxide, without water, in 50% solution state \| Cutoff, U - RoW |
| potassium hydroxide | input | 3.81E-03 | kg | market for potassium hydroxide \| potassium hydroxide \| Cutoff, U - GLO |
| silicon, single crystal, Czochralski process, photovoltaics | input | 5.95E-01 | kg | Table A4 |
| sodium hydroxide, without water, in 50% solution state | input | 1.50E-02 | kg | market for sodium hydroxide, without water, in 50% solution state \| sodium hydroxide, without water, in 50% solution state \| Cutoff, U - GLO |
| steel, low-alloyed, hot rolled | input | 8.96E-04 | kg | market for steel, low-alloyed, hot rolled \| steel, low-alloyed, hot rolled \| Cutoff, U - GLO |
| wafer factory | input | 2.00E-06 | Item(s) | market for wafer factory \| wafer factory \| Cutoff, U - GLO |
| water, completely softened | input | 2.17E+01 | kg | market for water, completely softened \| water, completely softened \| Cutoff, U - US |
| wire drawing, steel | input | 8.96E-04 | kg | market for wire drawing, steel \| wire drawing, steel \| Cutoff, U - GLO |
| AOX, adsorbable organic halogen as Cl | waste/emission | 5.01E-04 | kg | elementary flows/emission to water/surface water |
| BOD5, biological oxygen demand | waste/emission | 2.96E-02 | kg | elementary flows/emission to water/surface water |
| COD, chemical oxygen demand | waste/emission | 2.96E-02 | kg | elementary flows/emission to water/surface water |
| copper, ion | output | 6.05E-05 elementary flows/emission to water/surface water | kg |  |
| DOC, dissolved organic carbon | output | 1.11E-02 elementary flows/emission to water/surface water | kg |  |
| heat, waste | output | 8.00E+00 elementary flows/emission to air/low population density | MJ |  |
| nitrogen | output | 9.94E-03 elementary flows/emission to water/surface water | kg |  |
| TOC, total organic carbon | output | 1.11E-02 elementary flows/emission to water/surface water | kg |  |
| waste, from silicon wafer production | output | market for waste, from silicon wafer production \| waste, 2.00E-02 from silicon wafer production \| Cutoff, U - GLO | kg |  |
| water | output | 9.75E-03 elementary flows/emission to air/unspecified | m3 |  |
| water | output | 5.53E-02 elementary flows/emission to water/unspecified | m3 |  |

---

## A6 — Trimethylaluminum production

*Stage:* manufacturing · *Source:* Table A6, PDF page 58  
*Reference flow:* **Trimethylaluminum, purified** — 18 kg

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| aluminium chloride | input | 1.34E+00 | kg | aluminium chloride production \| aluminium chloride \| Cutoff, U - GLO |
| aluminium, wrought alloy | input | 2.16E+01 | kg | market for aluminium, wrought alloy \| aluminium, wrought alloy \| Cutoff, U - GLO |
| electricity, medium voltage | input | 5.57E+00 | kWh | Varies by case defined in Tables 5 – 6 |
| helium | input | 1.20E-01 | kg | market for helium \| helium \| Cutoff, U - GLO |
| methylchloride | input | 6.09E+01 | kg | market for methylchloride \| methylchloride \| Cutoff, U - RoW |
| nitrogen, liquid | input | 8.25E-01 | kg | market for nitrogen, liquid \| nitrogen, liquid \| Cutoff, U - RoW |
| paraffin | input | 1.53E-01 | kg | market for paraffin \| paraffin \| Cutoff, U - GLO |
| sodium | input | 3.30E+01 | kg | market for sodium \| sodium \| Cutoff, U - GLO |
| fly ash and scrubber sludge | waste/emission | 3.80E+00 | kg | treatment of fly ash and scrubber sludge, hazardous waste incineration \| fly ash and scrubber sludge \| Cutoff, U - RoW |
| hazardous waste, for incineration | waste/emission | 1.07E+02 | kg | treatment of hazardous waste, hazardous waste incineration \| hazardous waste, for incineration \| Cutoff, U - RoW |

---

## A7 — PERC cell production

*Stage:* manufacturing · *Source:* Table A7, PDF pages 59, 60, 61  
*Reference flow:* **photovoltaic cell, single-Si wafer** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| ammonia, anhydrous, liquid | input | 1.65E-02 | kg | market for ammonia, anhydrous, liquid \| ammonia, anhydrous, liquid \| Cutoff, U - RoW |
| calcium chloride | input | 2.07E-02 | kg | market for calcium chloride \| calcium chloride \| Cutoff, U - RoW |
| electricity, medium voltage | input | 6.03E+00 | kWh | Varies by case defined in Tables 5–6 |
| heat, district or industrial, natural gas | input | 3.55E+00 | MJ | heat production, natural gas, at industrial furnace >100kW \| heat, district or industrial, natural gas \| Cutoff, U - RoW |
| hydrochloric acid, without water, in 30% solution state | input | 6.81E-02 | kg | market for hydrochloric acid, without water, in 30% solution state \| hydrochloric acid, without water, in 30% solution state \| Cutoff, U - RoW |
| hydrogen fluoride | input | 7.47E-02 | kg | market for hydrogen fluoride \| hydrogen fluoride \| Cutoff, U - RoW |
| metallization paste, back side | input | 1.02E-03 | kg | Müller et al. 2021 |
| metallization paste, back side, aluminium | input | 9.01E-03 | kg | market for metallization paste, back side, aluminium \| metallization paste, back side, aluminium \| Cutoff, U - RoW |
| metallization paste, front side | input | 3.48E-03 | kg | market for metallization paste, front side \| metallization paste, front side \| Cutoff, U - RoW |
| nitric acid, without water, in 50% solution state | input | 8.22E-02 | kg | market for nitric acid, without water, in 50% solution state \| nitric acid, without water, in 50% solution state \| Cutoff, U - RoW |
| nitrogen, liquid | input | 2.62E+00 | kg | market for nitrogen, liquid \| nitrogen, liquid \| Cutoff, U - RoW |
| nitrous oxide | input | 7.66E-03 | kg | market for nitrous oxide \| nitrous oxide \| Cutoff, U - GLO |
| oxygen, liquid | input | 3.34E-01 | kg | market for oxygen, liquid \| oxygen, liquid \| Cutoff, U - RoW |
| phosphorus oxychloride | input | 1.82E-04 | kg | market for phosphorus oxychloride \| phosphorus oxychloride \| Cutoff, U - RoW |
| photovoltaic cell factory | input | 4.00E-07 | Item(s) | market for photovoltaic cell factory \| photovoltaic cell factory \| Cutoff, U - GLO |
| potassium hydroxide | input | 1.51E-01 | kg | market for potassium hydroxide \| potassium hydroxide \| Cutoff, U - GLO |
| propane | input | 4.14E-02 | kg | market for propane \| propane \| Cutoff, U - GLO |
| silicon tetrahydride | input | 2.83E-03 | kg | market for silicon tetrahydride \| silicon tetrahydride \| Cutoff, U - GLO |
| single-Si wafer, photovoltaic | input | 1.02E+00 | m2 | Table A5 |
| solvent, organic | input | 1.23E-02 | kg | market for solvent, organic \| solvent, organic \| Cutoff, U - GLO |
| sulfuric acid | output | 2.06E-02 | kg | sulfuric acid production \| sulfuric acid \| Cutoff, U - RoW |
| transport, freight train | output | 1.52E+00 | t*km | market for transport, freight train \| transport, freight train \| Cutoff, U - RoW |
| transport, freight, lorry, unspecified | output | 2.74E-01 | t*km | market group for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - GLO |
| transport, freight, sea, container ship | output | Import cases only: 1.57E+00 | t*km | transport, freight, sea, container ship \| transport, freight, sea, container ship \| Cutoff, U - GLO |
| trimethylaluminum | output | 2.88E-04 | kg | Table A6 |
| water, completely softened | output | 2.32E+01 | kg | market for water, completely softened \| water, completely softened \| Cutoff, U - RoW |
| Water, cooling, unspecified natural origin | output | 2.31E-01 | m3 |  |
| water, deionised | output | 3.94E+01 | kg | water production, deionised \| water, deionised \| Cutoff, U - RoW |
| aluminium | waste/emission | 7.73E-04 | kg | elementary flows/emission to air/high population density |
| ethane, hexafluoro-, HFC-116 | waste/emission | 1.19E-04 | kg | elementary flows/emission to air/high population density |
| heat, waste | waste/emission | 5.18E+01 | MJ | elementary flows/emission to air/low population density |
| hydrogen chloride | waste/emission | 2.66E-04 | kg | elementary flows/emission to air/high population density |
| hydrogen fluoride | waste/emission | 4.85E-06 | kg | elementary flows/emission to air/high population density |
| lead | waste/emission | 3.48E-07 | kg | elementary flows/emission to air/high population density |
| methane, tetrafluoro-, R-14 | waste/emission | 2.48E-04 | kg | elementary flows/emission to air/high population density |
| nitrogen oxides | waste/emission | 5.00E-05 | kg | elementary flows/emission to air/high population density |
| NMVOC, non-methane volatile organic compounds, unspecified origin | waste/emission | 1.94E-01 | kg | elementary flows/emission to air/high population density |
| particulates, <2.5 μm | waste/emission | 2.66E-03 | kg | elementary flows/emission to air/high population density |
| silicon | waste/emission | 7.27E-05 | kg | elementary flows/emission to air/high population density |
| silver | waste/emission | 6.60E-06 | kg | elementary flows/emission to air/low population density |
| waste, from silicon wafer production, inorganic | waste/emission | 6.41E-03 | kg | market for waste, from silicon wafer production, inorganic \| waste, from silicon wafer production, inorganic \| Cutoff, U - GLO |
| wastewater from PV cell production | waste/emission | 1.32E-02 | m3 | market for wastewater from PV cell production \| wastewater from PV cell production \| Cutoff, U - RoW |
| water | waste/emission | 1.68E-02 | m3 | elementary flows/emission to air/unspecified |
| water | output | 2.77E-01 elementary flows/emission to water/unspecified | m3 |  |

---

## A8 — PERC module production

*Stage:* manufacturing · *Source:* Table A8, PDF pages 61, 62  
*Reference flow:* **photovoltaic panel** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| adipic acid | input | 3.69E-04 | kg | market for adipic acid \| adipic acid \| Cutoff, U - GLO |
| aluminium alloy, AlMg3 | input | 1.51E+00 | kg | market for aluminium alloy, AlMg3 \| aluminium alloy, AlMg3 \| Cutoff, U - GLO |
| copper, cathode | input | 1.48E-01 | kg | market for copper, cathode \| copper, cathode \| Cutoff, U - GLO |
| corrugated board box | input | 7.63E-01 | kg | market for corrugated board box \| corrugated board box \| Cutoff, U - RoW |
| diode, auxilliaries and energy use | input | 2.81E-03 | kg | diode production, auxilliaries and energy use \| diode, auxilliaries and energy use \| Cutoff, U - GLO |
| electricity, medium voltage | input | 3.32E+00 | kWh | Varies by case defined in Tables 5–6 |
| ethylvinylacetate, foil | input | 7.93E-01 | kg | market for ethylvinylacetate, foil \| ethylvinylacetate, foil \| Cutoff, U - GLO |
| EUR-flat pallet | input | 5.00E-02 | Item(s) | EUR-flat pallet production \| EUR-flat pallet \| Cutoff, U - RoW |
| glass fibre reinforced plastic, polyamide, injection moulded | input | 1.88E-01 | kg | market for glass fibre reinforced plastic, polyamide, injection moulded \| glass fibre reinforced plastic, polyamide, injection moulded \| Cutoff, U - GLO |
| lead | input | 1.08E-02 | kg | market for lead \| lead \| Cutoff, U - GLO |
| lubricating oil | input | 1.61E-03 | kg | market for lubricating oil \| lubricating oil \| Cutoff, U - RoW |
| metal working, average for aluminium product manufacturing | input | 1.51E+00 | kg | market for metal working, average for aluminium product manufacturing \| metal working, average for aluminium product manufacturing \| Cutoff, U - GLO |
| packaging film, low density polyethylene | input | 4.01E-02 | kg | market for packaging film, low density polyethylene \| packaging film, low density polyethylene \| Cutoff, U - GLO |
| photovoltaic cell, single-Si wafer | input | 9.00E-01 | m2 | Table A7 |
| photovoltaic panel factory | input | 4.00E-06 | Item(s) | market for photovoltaic panel factory \| photovoltaic panel factory \| Cutoff, U - GLO |
| polyethylene terephthalate, granulate, amorphous | input | 2.81E-01 | kg | market for polyethylene terephthalate, granulate, amorphous \| polyethylene terephthalate, granulate, amorphous \| Cutoff, U - GLO |
| polyethylene, high density, granulate | input | 2.42E-02 | kg | market for polyethylene, high density, granulate \| polyethylene, high density, granulate \| Cutoff, U - GLO |
| polyethylene, low density, granulate | input | 5.48E-02 | kg | market for polyethylene, low density, granulate \| polyethylene, low density, granulate \| Cutoff, U - GLO |
| polyvinylfluoride, film | output | 4.51E-02 | kg | market for polyvinylfluoride, film \| polyvinylfluoride, film \| Cutoff, U - GLO |
| silicone product | output | 1.44E-01 | kg | market for silicone product \| silicone product \| Cutoff, U - RoW |
| solar glass, low-iron | output | 8.00E+00 | kg | market for solar glass, low-iron \| solar glass, low-iron \| Cutoff, U - GLO |
| tempering, flat glass | output | 8.00E+00 | kg | market for tempering, flat glass \| tempering, flat glass \| Cutoff, U - GLO |
| tin | output | 1.04E-02 | kg | market for tin \| tin \| Cutoff, U - GLO |
| transport, freight train | output | 1.66E+01 | t*km | market for transport, freight train \| transport, freight train \| Cutoff, U - RoW |
| transport, freight, lorry, unspecified | output | 2.99E+00 | t*km | market group for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - GLO |
| Water, cooling, unspecified natural origin | output | 7.16E-02 | m3 |  |
| wire drawing, copper | output | 1.48E-01 | kg | market for wire drawing, copper \| wire drawing, copper \| Cutoff, U - GLO |
| carbon dioxide, fossil | waste/emission | 2.18E-02 | kg | elementary flows/emission to air/low population density |
| heat, waste | waste/emission | 1.34E+01 | MJ | elementary flows/emission to air/low population density |
| municipal solid waste | waste/emission | 9.34E-02 | kg | market for municipal solid waste \| municipal solid waste \| Cutoff, U - RoW |
| NMVOC, non-methane volatile organic compounds, unspecified origin | waste/emission | 8.06E-03 | kg | elementary flows/emission to air/high population density |
| waste mineral oil | waste/emission | 1.61E-03 | kg | market for waste mineral oil \| waste mineral oil \| Cutoff, U – RoW |
| waste plastic, mixture | waste/emission | 2.48E-02 | kg | market for waste plastic, mixture \| waste plastic, mixture \| Cutoff, U - RoW |
| waste polyvinylfluoride | waste/emission | 9.02E-04 | kg | market for waste polyvinylfluoride \| waste polyvinylfluoride \| Cutoff, U - RoW |
| waste, from silicon wafer production | waste/emission | 3.52E-03 | kg | market for waste, from silicon wafer production \| waste, from silicon wafer production \| Cutoff, U – GLO |
| water | waste/emission | 2.79E-02 | kg | elementary flows/emission to air/unspecified |

---

## A9 — Single-axis tracker

*Stage:* manufacturing · *Source:* Table A9, PDF pages 62, 63  
*Reference flow:* **1-axis tracker (per module area)** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| aluminium, wrought alloy | output | market for aluminium, wrought alloy \| aluminium, 8.36E-02 wrought alloy \| Cutoff, U - GLO | kg |  |
| battery cell, Li-ion, LFP | output | market for battery cell, Li-ion, LFP \| battery cell, Li- 4.60E-03 ion, LFP \| Cutoff, U - GLO | kg |  |
| corrugated board box | output | market for corrugated board box \| corrugated board 8.58E-02 box \| Cutoff, U - US | kg |  |
| electric motor, vehicle | output | market for electric motor, vehicle \| electric motor, 5.65E-02 vehicle \| Cutoff, U - GLO | kg |  |
| photovoltaic panel, single-Si wafer | output | 5.00E-03 module assembly VN-MY - RoW | m2 |  |
| polystyrene, high impact | output | market for polystyrene, high impact \| polystyrene, 7.97E-04 high impact \| Cutoff, U - GLO | kg |  |
| section bar extrusion, aluminium | output | market for section bar extrusion, aluminium \| section 8.36E-02 bar extrusion, aluminium \| Cutoff, U - GLO | kg |  |
| section bar rolling, steel | output | market for section bar rolling, steel \| section bar 9.45E+00 rolling, steel \| Cutoff, U - GLO | kg |  |
| section bar rolling, steel | output | market for section bar rolling, steel \| section bar 8.36E-02 rolling, steel \| Cutoff, U - GLO | kg |  |
| steel, chromium steel 18/8 | output | market for steel, chromium steel 18/8 \| steel, 8.36E-02 chromium steel 18/8 \| Cutoff, U - GLO | kg |  |
| steel, low-alloyed, hot rolled | output | market for steel, low-alloyed, hot rolled \| steel, low- 9.45E+00 alloyed, hot rolled \| Cutoff, U - GLO | kg |  |

---

## A10 — Inverter (2.7 MWac)

*Stage:* manufacturing · *Source:* Table A10, PDF pages 63, 64  
*Reference flow:* **2.7 MWac inverter** — 1 Items

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| aluminium, wrought alloy | input | 80 | kg | market for aluminium, wrought alloy \| aluminium, wrought alloy \| Cutoff, U - GLO |
| cable, network cable, category 5, without plugs | input | 940 | m | market for cable, network cable, category 5, without plugs \| cable, network cable, category 5, without plugs \| Cutoff, U - GLO |
| cable, three-conductor cable | input | 61 | m | market for cable, three-conductor cable \| cable, three- conductor cable \| Cutoff, U - GLO |
| capacitor, electrolyte type, >2 cm height | input | 5 | kg | market for capacitor, electrolyte type, > 2cm height \| capacitor, electrolyte type, > 2cm height \| Cutoff, U - GLO |
| capacitor, film type, for through-hole mounting | input | 50 | kg | market for capacitor, film type, for through-hole mounting \| capacitor, film type, for through-hole mounting \| Cutoff, U - GLO |
| concrete slab | input | 1.1 | m3 | concrete slab - RoW |
| copper, cathode | input | 430 | kg | market for copper, cathode \| copper, cathode \| Cutoff, U - GLO |
| glass fibre reinforced plastic, polyamide, injection moulded | input | 30 | kg | market for glass fibre reinforced plastic, polyamide, injection moulded \| glass fibre reinforced plastic, polyamide, injection moulded \| Cutoff, U - GLO |
| inductor, ring core choke type | output | market for inductor, ring core choke type \| inductor, ring 650 core choke type \| Cutoff, U - GLO | kg |  |
| integrated circuit, logic type | output | market for integrated circuit, logic type \| integrated circuit, 0.2 logic type \| Cutoff, U - GLO | kg |  |
| lubricating oil | output | 1 market for lubricating oil \| lubricating oil \| Cutoff, U - RoW | kg |  |
| printed wiring board, through- hole mounted, unspecified, Pb free | output | market for printed wiring board, through-hole mounted, unspecified, Pb free \| printed wiring board, through-hole 3 mounted, unspecified, Pb free \| Cutoff, U - GLO | kg |  |
| reinforcing steel | output | market for reinforcing steel \| reinforcing steel \| Cutoff, U - 1200 GLO | kg |  |
| transformer, high voltage use | output | market for transformer, high voltage use \| transformer, high 100 voltage use \| Cutoff, U - GLO | kg |  |
| transistor, wired, big size, through-hole mounting | output | market for transistor, wired, big size, through-hole mounting \| transistor, wired, big size, through-hole 0.3 mounting \| Cutoff, U - GLO | kg |  |
| fan, for power supply unit, desktop computer | output | market for fan, for power supply unit, desktop computer \| fan, for power supply unit, desktop computer \| Cutoff, U - 0.2 GLO | kg |  |

---

## A11 — Transformer (2.7 MWac)

*Stage:* manufacturing · *Source:* Table A11, PDF page 64  
*Reference flow:* **2.7 MWac transformer** — 1 items

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| concrete slab | input | 1.10E+00 | m3 | concrete slab \| ROW |
| copper, cathode | input | 5.80E+03 | kg | market for copper, cathode \| copper, cathode \| Cutoff, U - GLO |
| epoxy resin, liquid | input | 1.05E+03 | kg | market for epoxy resin, liquid \| epoxy resin, liquid \| Cutoff, U - RoW |
| ferrite | input | 2.36E+04 | kg | market for ferrite \| ferrite \| Cutoff, U - GLO |
| injection moulding | input | 1.05E+03 | kg | market for injection moulding \| injection moulding \| Cutoff, U - GLO |
| lubricating oil | input | 2.10E+04 | kg | market for lubricating oil \| lubricating oil \| Cutoff, U - RoW |
| reinforcing steel | input | 2.00E+03 | kg | market for reinforcing steel \| reinforcing steel \| Cutoff, U - GLO |
| wire drawing, copper | input | 5.80E+03 | kg | market for wire drawing, copper \| wire drawing, copper \| Cutoff, U - GLO |

---

## A12 — Cables, conduit, other electrical balance of system

*Stage:* manufacturing · *Source:* Table A12, PDF page 65  
*Reference flow:* **electrical balance-of-system** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| (per module area) | output |  |  |  |
| aluminium, wrought alloy | input | 0.4 | kg | wrought alloy \| Cutoff, U - GLO |
| epoxy resin, liquid | input | 4.9E-05 | kg | market for epoxy resin, liquid \| epoxy resin, liquid \| Cutoff, U - RoW |
| nylon 6 | input | 6.4E-03 | kg | market for nylon 6 \| nylon 6 \| Cutoff, U - RoW |
| polycarbonate | input | 6.1E-05 | kg | market for polycarbonate \| polycarbonate \| Cutoff, U - GLO |
| polyvinylchloride, bulk polymerised | input | 0.11 | kg | market for polyvinylchloride, bulk polymerised \| polyvinylchloride, bulk polymerised \| Cutoff, U - GLO |
| wire drawing, copper | input | 0.4 | kg | market for wire drawing, copper \| wire drawing, copper \| Cutoff, U - GLO |

---

## A13 — Fence

*Stage:* manufacturing · *Source:* Table A13, PDF page 65  
*Reference flow:* **fence (per module area)** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| concrete, 25MPa | input | 2.9E-05 | m3 | market for concrete, 25MPa \| concrete, 25MPa \| Cutoff, U - RoW |
| section bar rolling, steel | input | 4.6E-02 | kg | market for section bar rolling, steel \| section bar rolling, steel \| Cutoff, U - GLO |
| steel, low-alloyed | input | 9.9E-02 | kg | market for steel, low-alloyed \| steel, low-alloyed \| Cutoff, U - GLO |
| wire drawing, steel | input | 5.3E-02 | kg | market for wire drawing, steel \| wire drawing, steel \| Cutoff, U - GLO |
| zinc coat, coils | input | 3.3E-03 | m2 | market for zinc coat, coils \| zinc coat, coils \| Cutoff, U - GLO |

---

## A14 — Installation

*Stage:* installation · *Source:* Table A14, PDF pages 65, 66  
*Reference flow:* **Installed UPV system** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| (per module area) | output |  |  |  |
| 1-axis tracker (per module area) | input | 1 | m2 | Table A9 |
| diesel, burned in building machine | input | 2.6 | MJ | market for diesel, burned in building machine \| diesel, burned in building machine \| Cutoff, U - GLO |
| 2.7 MWac inverter | output | 4.30E-05 Table A10 | Item(s) |  |
| Occupation, unspecified, natural (non-use) | output | 3 | m2*a |  |
| photovoltaic panel | output | 1 Table A8 | m2 |  |
| 2.7 MWac transformer | output | 4.30E-05 Table A11 | Item(s) |  |
| transport, freight train | output | market for transport, freight train \| transport, freight 2.2 train \| Cutoff, U - RoW | t*km |  |
| transport, freight train | output | market for transport, freight train \| transport, freight 2 train \| Cutoff, U - RoW | t*km |  |
| transport, freight, lorry, unspecified | output | market group for transport, freight, lorry, unspecified \| 3.3E-03 transport, freight, lorry, unspecified \| Cutoff, U - GLO | t*km |  |
| transport, freight, lorry, unspecified | output | market group for transport, freight, lorry, unspecified \| 0.51 transport, freight, lorry, unspecified \| Cutoff, U - GLO | t*km |  |
| transport, freight, lorry, | output | market group for transport, freight, lorry, unspecified \| |  |  |
| unspecified | output | 0.55 transport, freight, lorry, unspecified \| Cutoff, U - GLO | t*km |  |
| transport, freight, sea, container ship | output | Import cases only: transport, freight, sea, container ship \| transport, 201 freight, sea, container ship \| Cutoff, U - GLO | t*km |  |
| electrical balance of system (per module area) | output | 1 Table A12 | m2 |  |
| fence (per module area) | output | 1 Table A13 | m2 |  |

---

## A15 — Operations and maintenance

*Stage:* use · *Source:* Table A15, PDF page 66  
*Reference flow:* **30 years operation and maintenance** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| (per module area) | output |  |  |  |
| electric motor, vehicle | input | 1.70E-02 | kg | market for electric motor, vehicle \| electric motor, vehicle \| Cutoff, U - GLO |
| 2.7 MWac inverter | input | 1.30E-05 | Item(s) | Table A10 |
| petrol, low-sulfur | input | 5.50E-02 | kg | petrol production, low-sulfur \| petrol, low-sulfur \| Cutoff, U - RoW |
| photovoltaic panel | input | 1.5E-02 | m2 | Table A8 |
| 2.7 MWac transformer | input | 1.30E-05 | Item(s) | Table A11 |

---

## A16 — Decommissioning

*Stage:* end of life · *Source:* Table A16, PDF page 67  
*Reference flow:* **decommissioned UPV system** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| (per module area) | output |  |  |  |
| diesel, burned in building machine | input | 2.6 | MJ | market for diesel, burned in building machine \| diesel, burned in building machine \| Cutoff, U - GLO |
| installed UPV system (per module area) | input | 1 | m2 | Table A14. |
| PV module EOL | waste/emission | 10.9 | kg | Tables A18-A20 |
| 2.6 MWac transformer EOL | waste/emission | 4.3E-05 | Item(s) | Table A21 |
| electrical balance of system EOL (per module area) | waste/emission | 1 | m2 | Table A22 |
| 1-axis tracker EOL (per module area) | waste/emission | 1 | m2 | Table A23 |
| 2.6 MWac inverter EOL | waste/emission | 4.3E-05 | Item(s) | Table A24 |

---

## A17 — Landfilling PV modules

*Stage:* end of life · *Source:* Table A17, PDF page 67  
*Reference flow:* **PV module EOL** — 1 kg

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| electricity, medium voltage | input | 0.32 | MJ | market group for electricity, medium voltage \| electricity, medium voltage \| Cutoff, U - US |
| PV module EOL | input | 1 | kg | Table A17 |
| transport, freight, lorry | input | 160 | kg*km | transport, freight, lorry, unspecified |
| average incineration residue | output | 0.2 | kg | treatment of average incineration residue, residual material landfill \| average incineration residue \| Cutoff, U - RoW |
| electricity, medium voltage | output | 7.14 _(Avoid in avoided burden cases)_ | MJ | electricity, from municipal waste incineration to generic market for electricity, medium voltage \| electricity, medium voltage \| Cutoff, U - RoW |

---

## A18 — Partial recycling of PV modules

*Stage:* end of life · *Source:* Table A18, PDF pages 68, 69  
*Reference flow:* **PV module EOL** — 1 kg

> ⚠️ Input-flow names are misaligned with their units and providers in the source. See note above.

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| aluminium, primary, ingot | input | Avoided burden (AB) cases only: 5.62E-02 | kg | treatment of aluminium scrap, post-consumer, prepared for recycling, at remelter \| aluminium, wrought alloy \| Cutoff, U - RoW |
| Carbon dioxide, fossil | input | AB cases only: 6.61E-03 | kg | treatment of copper scrap by electrolytic refining \| copper, cathode \| Cutoff, U - RoW |
| copper, cathode | input | 6.48E-02 | MJ | diesel, burned in building machine \| diesel, burned in building machine \| Cutoff, U - GLO |
| heat, district or industrial, natural gas | input | 1.11E-01 | kWh | market group for electricity, medium voltage \| electricity, medium voltage \| Cutoff, U - US |
| heat, district or industrial, other than natural gas | input | 1.00E+00 | kg |  |
| lime, packed | input | 5.00E-01 | t*km | market for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - RoW |
| PV module EOL | input | 1 | kg | Table A17. |
| aluminium, primary, ingot | output | 5.62E-02 _(In avoided burden (AB) cases)_ | kg | aluminium production, primary, ingot \| aluminium, primary, ingot \| Cutoff, U - CA |
| Carbon dioxide, fossil | output | -1.24E-01 | kg | Elementary flows/Emission to air/low population density |
| copper, cathode | output | 6.61E-03 _(In AB cases)_ | kg | copper production, cathode, solvent extraction and electrowinning process \| copper, cathode \| Cutoff, U - GLO |
| heat, district or industrial, natural gas | output | 8.30E-01 _(In AB cases)_ | MJ | heat production, natural gas, at industrial furnace >100kW \| heat, district or industrial, natural gas \| Cutoff, U - RoW |
| heat, district or industrial, other than natural gas | output | 5.38E-01 _(In AB cases)_ | MJ | heat production, heavy fuel oil, at industrial furnace 1MW \| heat, district or industrial, other than natural gas \| Cutoff, U - RoW |
| lime, packed | output | 2.42E-01 _(In AB cases)_ | kg | lime production, milled, packed \| lime, packed \| Cutoff, U - RoW |
| silica sand | output | 3.50E-01 _(In AB cases)_ | kg | market for silica sand \| silica sand \| Cutoff, U - GLO |
| soda ash, light | output | 1.38E-01 _(In AB cases)_ | kg | market for soda ash, light \| soda ash, light \| Cutoff, U - GLO |
| waste plastic, mixture | output | 1.51E-01 | kg | treatment of waste plastic, mixture, sanitary landfill \| waste plastic, mixture \| Cutoff, U - RoW |
| waste plastic, mixture | output | 2.64E-02 | kg | treatment of waste plastic, mixture, municipal incineration \| waste plastic, mixture \| Cutoff, U - RoW |

---

## A19 — Hypothetical high-recovery recycling of PV modules

*Stage:* end of life · *Source:* Table A19, PDF pages 69, 70  
*Reference flow:* **PV module EOL** — 1.00E+00 kg

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| diesel, burned in building machine | input | 4.00E-02 | MJ | diesel, burned in building machine \| diesel, burned in building machine \| Cutoff, U - GLO |
| electricity, medium voltage | input | 1.14E-01 | kWh | market group for electricity, medium voltage \| electricity, medium voltage \| Cutoff, U - US |
| lime | input | 3.60E-02 | kg | lime production, milled, loose \| lime \| Cutoff, U - RoW |
| nitric acid, without water, in 50% solution state | input | 7.08E-03 | kg | market for nitric acid, without water, in 50% solution state \| nitric acid, without water, in 50% solution state \| Cutoff, U - RoW |
| PV module EOL | input | 1.00E+00 | kg | Table A17 |
| transport, freight, lorry, unspecified | input | 5.00E-01 | t*km | market for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - RoW |
| water, completely softened | input | 3.10E-01 | kg | market for water, completely softened \| water, completely softened \| Cutoff, U - US |
| aluminium scrap, post-consumer | output | 1.83E-01 _(In avoided burden (AB) cases)_ | kg | market for aluminium scrap, post- consumer \| aluminium scrap, post- consumer \| Cutoff, U - GLO |
| blast furnace sludge | output | 5.00E-02 | kg | treatment of blast furnace sludge, residual material landfill \| blast furnace sludge \| Cutoff, U - RoW |
| copper, cathode | output | 4.40E-03 _(In AB cases)_ | kg | copper production, cathode, solvent extraction and electrowinning process \| copper, cathode \| Cutoff, U - GLO |
| electricity, medium voltage | output | 2.49E-01 _(In AB cases)_ | MJ | market group for electricity, medium voltage \| electricity, medium voltage \| Cutoff, U - US |
| fly ash and scrubber sludge | output | 2.00E-03 | kg | treatment of fly ash and scrubber sludge, hazardous waste incineration \| fly ash and scrubber sludge \| Cutoff, U - RoW |
| glass cullet, sorted | output | 6.86E-01 _(In AB cases)_ | kg | market for glass cullet, sorted \| glass cullet, sorted \| Cutoff, U - RoW |
| heat, district or industrial, natural gas | output | 5.03E-01 _(In AB cases)_ | MJ | heat production, natural gas, at industrial furnace >100kW \| heat, district or industrial, natural gas \| Cutoff, U - RoW |
| limestone residue | output | 3.06E-01 | kg | treatment of limestone residue, inert material landfill \| limestone residue \| Cutoff, U - RoW |
| nitrogen oxides | input | 2.00E-04 | kg | Elementary flows/Emission to air/unspecified |
| silicon, metallurgical grade | input | 3.50E-02 _(In AB cases)_ | kg | market for silicon, metallurgical grade \| silicon, metallurgical grade \| Cutoff, U - GLO |
| silver | input | 5.00E-04 _(In AB cases)_ | kg | market for silver \| silver \| Cutoff, U - GLO |
| used cable | input | 1.00E-02 | kg | treatment of used cable \| used cable \| Cutoff, U - GLO |
| waste glass | input | 1.40E-02 | kg | treatment of waste glass, inert material landfill \| waste glass \| Cutoff, U - CH |
| waste plastic, mixture | input | 9.20E-02 | kg | treatment of waste plastic, mixture, municipal incineration \| waste plastic, mixture \| Cutoff, U - RoW |
| waste polyvinylfluoride | input | 1.80E-02 | kg | treatment of waste polyvinylfluoride, municipal incineration \| waste polyvinylfluoride \| Cutoff, U - RoW |
| waste wire plastic | input | 6.70E-03 | kg | treatment of waste wire plastic, municipal incineration \| waste wire plastic \| Cutoff, U - RoW |

---

## A20 — Transformer EOL

*Stage:* end of life · *Source:* Table A20, PDF page 70  
*Reference flow:* **2.7 MWac transformer EOL** — 1 Item(s)

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| copper, cathode | input | 4400 | kg | treatment of copper scrap by electrolytic refining \| copper, cathode \| Cutoff, U - RoW |
| steel, unalloyed | input | 1800 | kg | steel production, converter, unalloyed \| steel, unalloyed \| Cutoff, U - RoW |
| 2.7 MWac transformer EOL | input | 1 | Item(s) | Table A17 |
| transport, freight, lorry, unspecified | input | 1400 | t*km | market for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - RoW |
| copper, cathode | output | 4400 _(In avoided burden (AB) cases)_ | kg |  |
| steel, low-alloyed | output | 1800 _(In AB cases)_ | kg |  |
| waste plastic, mixture | output | 1050 | kg | market group for waste plastic, mixture \| waste plastic, mixture \| Cutoff, U - RER |
| waste reinforced concrete | output | 2400 | kg | treatment of waste reinforced concrete, recycling \| waste reinforced concrete \| Cutoff, U - RoW |

---

## A21 — Electrical balance-of-system EOL

*Stage:* end of life · *Source:* Table A21, PDF page 71  
*Reference flow:* **Electrical balance-of-system EOL (per module area)** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| aluminium, wrought alloy | input | 0.31 | kg | treatment of aluminium scrap, post- consumer, prepared for recycling, at remelter \| aluminium, wrought alloy \| Cutoff, U - RoW |
| Electrical balance-of-system EOL (per module area) | input | 1 | m2 | Table A17 |
| aluminium, primary, ingot | output | 0.31 _(In avoided burden cases)_ | kg |  |
| waste polyvinylchloride | output | 0.11 | kg | market for waste polyvinylchloride \| waste polyvinylchloride \| Cutoff, U - RoW |

---

## A22 — Tracker EOL

*Stage:* end of life · *Source:* Table A22, PDF page 71  
*Reference flow:* **1-axis tracker EOL (per module area)** — 1 m2

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| aluminium, wrought alloy | input | 0.064 | kg | treatment of aluminium scrap, post- consumer, prepared for recycling, at remelter \| aluminium, wrought alloy \| Cutoff, U - RoW |
| steel, unalloyed | input | 9 | kg | steel production, converter, unalloyed \| steel, unalloyed \| Cutoff, U - RoW |
| 1-axis tracker EOL (per module area) | input | 1 | m2 | Table A17 |
| transport, freight, lorry, unspecified | input | 0.5 | t*km | market for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - RoW |
| aluminium, primary, ingot | output | 0.064 _(in avoided burden (AB) cases)_ | kg |  |
| steel, low-alloyed | output | 9 _(in AB cases)_ | kg |  |

---

## A23 — Inverter EOL

*Stage:* end of life · *Source:* Table A23, PDF page 72  
*Reference flow:* **2.7 MWac inverter EOL** — 1 Item(s)

| Flow | Type | Amount | Unit | Provider / compartment |
|---|---|---|---|---|
| 2.7 MWac inverter EOL | input | 1 | Item(s) | Table A17. |
| aluminium, wrought alloy | input | 62 | kg | treatment of aluminium scrap, post- consumer, prepared for recycling, at remelter \| aluminium, wrought alloy \| Cutoff, U - RoW |
| copper, cathode | input | 330 | kg | treatment of copper scrap by electrolytic refining \| copper, cathode \| Cutoff, U - RoW |
| steel, unalloyed | input | 1100 | kg | steel production, converter, unalloyed \| steel, unalloyed \| Cutoff, U - RoW |
| transport, freight, lorry, unspecified | input | 400 | t*km | market for transport, freight, lorry, unspecified \| transport, freight, lorry, unspecified \| Cutoff, U - RoW |
| copper, cathode | output | 330 _(in avoided burden (AB) cases)_ | kg |  |
| steel, low-alloyed | output | 1100 _(in AB cases)_ | kg |  |
| waste plastic, mixture | output | 30 | kg | market group for waste plastic, mixture \| waste plastic, mixture \| Cutoff, U - RER |
| waste reinforced concrete | output | 2400 | kg | treatment of waste reinforced concrete, recycling \| waste reinforced concrete \| Cutoff, U - RoW |
| aluminium, primary, ingot | output | 62 _(in AB cases)_ | kg |  |
