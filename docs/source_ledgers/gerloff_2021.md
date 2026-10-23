# Gerloff 2021 — row ledger (22 Oct 2026)

Source: Gerloff, N. (2021), "Comparative Life-Cycle-Assessment analysis of three major water electrolysis technologies while applying various energy scenarios for a greener hydrogen production", *J. Energy Storage* 43, 102759.
Module: `optimiser_lca/hydrogen.py` — `ae_hermesmann_1unit`, `pem_con_hermesmann_1unit`, `soec_con_hermesmann_1unit` (1 MW capital goods) and `ae_op_/pem_op_/soec_op_hermesmann_1kg_h2` (per kg H2).
Repository untouched; this file is the only output. Working files (EMF renders, text dumps, XLSX dumps) are in `…\scratchpad\gerloff_work\`.

## Files read

| File | What it is | How read |
|---|---|---|
| `OneDrive…\DC optimiser\sources\gerlof electrolysis lca bop 200.docx` | **The Supplementary Information** (first line "Supplementary Information"; Sections: Additional manufacturing energy, Operating data, Values/ecoinvent processes, General assumptions, Comparative values, Comparison). Tables 1–12 are Word tables; **Figures 1–5 (the bills) are five EMF images** (`word/media/image1-5.emf`), no embedded workbook. | python-docx for text/tables; the EMF `EMR_EXTTEXTOUTW` text records parsed directly (every value is a text string, so the transcription below is exact, not OCR) and the EMFs rendered to PNG with Pillow to confirm the row layout. |
| `OneDrive…\DC optimiser\sources\gerlof electrolysis bop 210.pdf` | **The paper** (17 pages, Elsevier typeset). Its Tables 6–8 give component *names* only; §2.2 says "Values … can be found in the SI Figs. 1-4". | PyMuPDF text extraction (the Read tool's PDF renderer is not installed on this machine). |
| `Documents\brightway\{alkaline electrolyser, alkaline operation, uk pem construction, ukpemoperation, uksoecconstruction, uksoecoperation}.XLSX` | The user's SimaPro 10.3 exports (project "HyPT", dated 08/08–09/09/2025) the module was recreated from. | openpyxl, every row. |

Table numbering, to stop the "Table 3?" confusion: **SI** Table 1 = energy factors per kg; **SI Table 2** = stack/BoP manufacturing energy in kWh/kW; **SI Table 3** = additional manufacturing energy in kWh of the 1 MW systems; **SI Table 4** = produced H2 in 20 years; **SI Table 5** = the same per kg H2; **SI Table 6** = operating data (= **paper Table 3**). Paper Table 4 = disposal processes; paper Tables 6/7/8 = AEC/PEMEC/SOEC component lists (names only).

Dispositions: IN / IN-DIFFERS (both numbers) / BOUNDARY (which) / SUBSTITUTED / NOT-APPLICABLE / MISSING. The module aggregates one row per ecoinvent process, so "Module (key, amount)" names the aggregate the SI row sits in; the per-process sums are proved in the three-way section.

---

## SI Fig. 1 — "Values for AEC 1 MW BoP and stack components" → `ae_hermesmann_1unit`

64 printed input rows, 21 components (18 BoP, 3 stack). Component numbers as printed.

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | water purifier and feed tank — extrusion, plastic pipes | 464.6 | kg | extrusion_pipes 464.6 | IN | |
| 1 | — polyethylene production, **low density**, granulate | 464.6 | kg | polyethylene_hd_row 464.6 | IN-DIFFERS | SI: LD; export and module: **HD** {RoW}. Amount equal. PEM/SOEC exports use LD as the SI. |
| 1 | — reinforcing, steel production | 232.3 | kg | reinforcing_steel_row 5,134.4 | IN | |
| 1 | — sheet rolling, steel | 232.3 | kg | sheet_rolling_steel 10,130.0 | IN | |
| 2 | control panel/electronics — electronics production, for control unit | 100.0 | kg | electronics_row 100.0 | IN | |
| 3 | transformer and rectifier — market for aluminium, wrought alloy | 100.0 | kg | aluminium_wrought 160.0 | IN | |
| 3 | — market for copper | 200.0 | kg | copper_cathode 616.7 | IN | |
| 3 | — reinforcing steel production | 600.0 | kg | reinforcing_steel_row | IN | |
| 3 | — sheet rolling, aluminium | 100.0 | kg | sheet_rolling_aluminium 100.0 | IN | |
| 3 | — sheet rolling, steel | 600.0 | kg | sheet_rolling_steel | IN | |
| 3 | — tube insulation production, elastomere | 100.0 | kg | tube_insulation 207.9 | IN | |
| 3 | — wire drawing, copper | 200.0 | kg | wire_drawing_copper 616.7 | IN | |
| 4 | hydrogen dryer and deoxidizer — glass fibre production | 464.6 | kg | glass_fibre_row 464.6 | IN | |
| 4 | — reinforcing, steel production | 696.8 | kg | reinforcing_steel_row | IN | |
| 4 | — sheet rolling steel | 696.8 | kg | sheet_rolling_steel | IN | |
| 4 | — sheet rolling, chromium steel | 232.3 | kg | sheet_rolling_cr_steel 26,892.2 | IN | |
| 4 | — steel production, chromium steel 18/8 hot rolled | 232.3 | kg | cr_steel_hot_rolled_row 26,892.2 | IN | |
| 5 | frequency converter diaphragm compressor — market for aluminium, wrought alloy | 60.0 | kg | aluminium_wrought | IN | |
| 5 | — market for copper | 45.0 | kg | copper_cathode | IN | |
| 5 | — reinforcing steel production | 180.0 | kg | reinforcing_steel_row | IN | |
| 5 | — tube insulation production, elastomere | 15.0 | kg | tube_insulation | IN | |
| 5 | — wire drawing, copper | 45.0 | kg | wire_drawing_copper | IN | |
| 6 | diaphragm, for diaphragm compressor — cast iron production | 600.0 | kg | cast_iron_row 716.1 | IN | |
| 6 | — ethylene glycol production | 7.0 | kg | ethylene_glycol_row 7.0 | IN | |
| 6 | — reinforcing steel production | 1300.0 | kg | reinforcing_steel_row | IN | |
| 6 | — sheet rolling, chromium steel | 405.0 | kg | sheet_rolling_cr_steel | IN | |
| 6 | — sheet rolling, steel | **400.0** | kg | sheet_rolling_steel | IN | export had 405 (copied the Cr value); corrected 21 Oct. |
| 6 | — steel production, chromium steel 18/8, hot rolled | 405.0 | kg | cr_steel_hot_rolled_row | IN | |
| 7 | container with pipes and fittings for diaphragm compressor — reinforcing steel production | 1000.0 | kg | reinforcing_steel_row | IN | |
| 7 | — sheet rolling, chromium steel | 1500.0 | kg | sheet_rolling_cr_steel | IN | |
| 7 | — sheet rolling, steel | 1000.0 | kg | sheet_rolling_steel | IN | |
| 7 | — steel production, chromium steel 18/8, hot rolled | 1500.0 | kg | cr_steel_hot_rolled_row | IN | |
| 8 | buffertank — sheet rolling, chromium steel | 511.0 | kg | sheet_rolling_cr_steel | IN | |
| 8 | — steel production chromium steel 18/8 hot rolled | 511.0 | kg | cr_steel_hot_rolled_row | IN | |
| 8 | — welding, arc steel | 29.0 | m | welding_arc_steel 29.0 m | IN | |
| 9 | tubing and cables — market for copper | 371.7 | kg | copper_cathode | IN | |
| 9 | — wire drawing, copper | 371.7 | kg | wire_drawing_copper | IN | |
| 9 | — sheet rolling chromium steel | 929.1 | kg | sheet_rolling_cr_steel | IN | |
| 9 | — steel production, chromium steel | 929.1 | kg | cr_steel_hot_rolled_row | IN | |
| 9 | — tube insulation production, elastomere | 92.9 | kg | tube_insulation | IN | |
| 10 | water cooling plant for electrolyzer — reinforcing steel production | 836.2 | kg | reinforcing_steel_row | IN | |
| 10 | — sheet rolling, steel | 836.2 | kg | sheet_rolling_steel | IN | |
| 11 | pumps and coolers — cast iron production | 116.1 | kg | cast_iron_row | IN | |
| 11 | — reinforcing steel production | 209.1 | kg | reinforcing_steel_row | IN | |
| 11 | — sheet rolling, steel | 209.1 | kg | sheet_rolling_steel | IN | |
| 12 | heat exchanger — sheet rolling, chromium steel | 1161.4 | kg | sheet_rolling_cr_steel | IN | |
| 12 | — steel production, chromium steel 18/8, hot rolled | 1161.4 | kg | cr_steel_hot_rolled_row | IN | |
| 13 | **gas separator (2 x)** — reinforcing steel production | **80.0** | kg | reinforcing_steel_row | IN | one printed value against a "(2 x)" label; export entered 160. See S5. |
| 13 | — sheet rolling, steel | **80.0** | kg | sheet_rolling_steel | IN | as above |
| 14 | steel tank for KOH — sheet rolling chromium steel | 851.0 | kg | sheet_rolling_cr_steel | IN | |
| 14 | — steel production, chromium steel | 851.0 | kg | cr_steel_hot_rolled_row | IN | |
| 15 | alkali-resistant rotary pump — polypropylene production granulate | 3.0 | kg | polypropylene_row 3.0 | IN | |
| 15 | — injection moulding | 3.0 | kg | injection_moulding 3.0 | IN | |
| 16 | storage tank — sheet rolling chromium steel | 1108.0 | kg | sheet_rolling_cr_steel | IN | |
| 16 | — steel production, chromium steel | 1108.0 | kg | cr_steel_hot_rolled_row | IN | |
| 17 | container — sheet rolling, steel | 6075.6 | kg | sheet_rolling_steel | IN | |
| 17 | — steel production, low alloyed, hot rolled | 6075.6 | kg | low_alloyed_steel_hr_row 6,075.6 | IN | |
| 18 | fundament — concrete production 35MPa, RNA only [RoW] | 7.7 | m3 | concrete_35mpa_cem3 7.7 | IN | SI dataset is the North-American recipe with RoW geography; module uses GLO CEM III/A (flagged in the module as built). |
| 19 | **Stack** — anode and cathode with frame — sheet rolling, chromium steel | 20194.4 | kg | sheet_rolling_cr_steel | IN | 75 % of the unit's Cr steel is stack |
| 19 | — steel production, chromium steel 18/8, hot rolled | 20194.4 | kg | cr_steel_hot_rolled_row | IN | |
| 19 | — market for nickel, 99.5% | 2884.9 | kg | nickel_class1 2,884.9 | IN | export linked "nickel mine operation, sulfidic ore"; module's class-1 market is the 3.9.1 successor of the SI's dataset |
| 20 | gasket — tetrafluoroethylene production | 144.2 | kg | tetrafluoroethylene_row 144.2 | IN | |
| 21 | diaphragm, zirfon — polysulfon production | 48.8 | kg | polysulfone 48.8 | IN | paper §2.2.1: 40 % polysulfone / 60 % ZrO2 of 121.8 kg ✓ |
| 21 | — zirconium oxide production | 73.0 | kg | zirconium_oxide_row 73.0 | IN | |
| T3 | SI Table 3 "AEC Stack" additional manufacturing energy | 286,659.9 | kWh | electricity_lv_de 323,773.4 | IN | = 218.9 kWh/kW × 1000^0.88 × **3** (three stacks, SI p.1 and paper §2.1.3) |
| T3 | SI Table 3 "AEC BoP" | 37,113.5 | kWh | electricity_lv_de 323,773.4 | IN | = 37.1 kWh/kW × 1000 (linear, not the 0.7 the SI text says) |

Items in Gerloff's AEC model that are not a row of Fig. 1:

| Item | Source | Amount | Module | Disposition |
|---|---|---|---|---|
| Stack materials × 3 over the 20-y life (rows 19–21) | paper §2.1.2, §2.1.3; SI p.1 ("stack values are multiplied by 3") | +2 × (20,194.4 kg Cr steel + sheet rolling, 2,884.9 kg Ni, 144.2 kg TFE, 48.8 kg polysulfone, 73.0 kg ZrO2) per 160,000 h | one stack's materials; **three stacks' electricity** | **MISSING** (see Summary) |
| Transport leg 1: materials to assembly, 250 km, lorry >32 t EURO6 RER, on every component's weight | paper §2.1 p.3–4 | 43,993 kg of materials (excl. foundation) × 250 km = **≈11,000 t·km per unit** (≈22,700 with three stacks) | none | **MISSING** (upstream transport is in scope) |
| Transport leg 2: components to the plant site, 250 km | paper §2.1 p.4 | as above | none | BOUNDARY (delivery to site) |
| Disposal of every material, paper Table 4 processes | paper §2.1.9 | — | none | BOUNDARY (end-of-life) |

---

## SI Fig. 2 — "Values for PEMEC 1 MW BoP and stack components" → `pem_con_hermesmann_1unit`

60 inputs on 61 printed value lines (the foundation is printed twice, kg and m3) plus one stray value; 26 numbered rows (1–17 BoP, 18 = "Stack" header, 19–26 stack).

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | power eletronics (rectifier, voltage adaption) — market for aluminium, wrought alloy | 100.0 | kg | aluminium_wrought 287.0 | IN | |
| 1 | — market for copper | 200.0 | kg | copper_cathode 349.5 | IN | |
| 1 | — reinforcing steel production | 600.0 | kg | reinforcing_steel_eur 3,312.3 | IN | |
| 1 | — sheet rolling, aluminium | 100.0 | kg | sheet_rolling_aluminium 227.0 | IN | |
| 1 | — sheet rolling, steel | 600.0 | kg | sheet_rolling_steel 5,382.3 | IN | |
| 1 | — tube insulation production, elastomere | 100.0 | kg | tube_insulation 115.0 | IN | |
| 1 | — wire drawing, copper | 200.0 | kg | wire_drawing_copper 245.0 | IN | |
| 2 | control panel/electronics — electronics production, for control unit | 100.0 | kg | electronics_rer 100.0 | IN | |
| 3 | tubing and pump — steel production, low-alloyed | 900.0 | kg | low_alloyed_steel_hr_rer 3,150.0 | IN | |
| 3 | — sheet rolling , steel | 900.0 | kg | sheet_rolling_steel | IN | |
| 4 | steel construction element — sheet rolling, chromium steel | 750.0 | kg | sheet_rolling_cr_steel 4,427.0 | IN | |
| 4 | — steel production, chromium steel 18/8, hot rolled | 750.0 | kg | cr_steel_hr_rer 4,427.0 | IN | |
| 5 | gas purification (De-Oxo) & water treatment — market for aluminium, wrought alloy | 100.0 | kg | aluminium_wrought | IN | label clipped in the figure |
| 5 | — sheet rolling, aluminium | 100.0 | kg | sheet_rolling_aluminium | IN | |
| 6 | water-gas seperator — copper production, primary | 100.0 | kg | copper_cathode | IN | SI's "copper production, primary" and "market for copper" both land on the module's copper-cathode market |
| 6 | — sheet rolling copper | 100.0 | kg | sheet_rolling_copper 104.5 | IN | |
| 7 | valve — polypropylene production | 300.0 | kg | polypropylene_rer 300.0 | IN | |
| 7 | — injection moulding | 300.0 | kg | injection_moulding 300.0 | IN | |
| 8 | back pressure regulator — lubricating oil | 100.0 | kg | lubricating_oil 100.0 | IN | |
| 9 | ion exchanger — zeolite production, powder | 100.0 | kg | zeolite 100.0 | IN | |
| 10 | heat exchanger — sheet rolling, chromium steel | 1161.0 | kg | sheet_rolling_cr_steel | IN | (AEC's is 1161.4) |
| 10 | — steel production, chromium steel 18/8, hot rolled | 1161.0 | kg | cr_steel_hr_rer | IN | |
| 11 | water purifier and feed tank — extrusion, plastic pipes | 464.6 | kg | extrusion_pipes 464.6 | IN | |
| 11 | — polyethylene production, low density, granulate | 464.6 | kg | polyethylene_ld_rer 464.6 | IN | |
| 11 | — reinforcing, steel production | 232.3 | kg | reinforcing_steel_eur | IN | |
| 11 | — sheet rolling, steel | 232.3 | kg | sheet_rolling_steel | IN | |
| 12 | frequency converter diaphragm compressor — market for aluminium, wrought alloy | 60.0 | kg | aluminium_wrought | IN | |
| 12 | — market for copper | 45.0 | kg | copper_cathode | IN | |
| 12 | — reinforcing steel production | 180.0 | kg | reinforcing_steel_eur | IN | |
| 12 | — tube insulation production, elastomere | 15.0 | kg | tube_insulation | IN | |
| 12 | — wire drawing, copper | 45.0 | kg | wire_drawing_copper | IN | |
| 13 | diaphragm for diaphragm compressor — cast iron production | 600.0 | kg | cast_iron_rer 600.0 | IN | |
| 13 | — ethylene glycol production | 7.0 | kg | ethylene_glycol_rer 7.0 | IN | |
| 13 | — reinforcing steel production | 1300.0 | kg | reinforcing_steel_eur | IN | |
| 13 | — sheet rolling, chromium steel | 405.0 | kg | sheet_rolling_cr_steel | IN | |
| 13 | — sheet rolling, steel | 400.0 | kg | sheet_rolling_steel | IN | export has 400 (right, unlike the AE export) |
| 13 | — steel production, chromium steel 18/8, hot rolled | 405.0 | kg | cr_steel_hr_rer | IN | |
| 14 | container with pipes and fittings for diaphragm compressor — reinforcing steel production | 1000.0 | kg | reinforcing_steel_eur | IN | |
| 14 | — sheet rolling, chromium steel | 1500.0 | kg | sheet_rolling_cr_steel | IN | |
| 14 | — sheet rolling, steel | 1000.0 | kg | sheet_rolling_steel | IN | |
| 14 | — steel production, chromium steel 18/8, hot rolled | 1500.0 | kg | cr_steel_hr_rer | IN | |
| 15 | buffertank — sheet rolling, chromium steel | 511.0 | kg | sheet_rolling_cr_steel | IN | |
| 15 | — steel production chromium steel 18/8 hot rolled | 511.0 | kg | cr_steel_hr_rer | IN | |
| 15 | — welding, arc steel | 29.0 | **kg** (sic) | welding_arc_steel 29.0 **m** | IN | SI typo: Figs 1 and 5 print "m" for the same 29.0/33.3; ecoinvent welding is per metre. Export and module take m. |
| 16 | container — sheet rolling, steel | 2250.0 | kg | sheet_rolling_steel | IN | |
| 16 | — steel production, low alloyed, hot rolled | 2250.0 | kg | low_alloyed_steel_hr_rer | IN | |
| 17 | foundation concrete — concrete production 35MPa, RNA only [RoW] | 5600.0 | kg | — | NOT-APPLICABLE | the same foundation printed by mass; 5600/2.3 = 2,435 kg/m3 |
| 17 | — concrete production 35MPa, RNA only [RoW] | 2.3 | m3 | concrete_35mpa_cem2 2.3 | IN | module: GLO CEM II/B (as built) |
| 18 | **Stack** (header line) | 511.0 | kg | — | NOT-APPLICABLE | a stray value on the section header (a copy of row 15's 511.0 that was not cleared); no process named. Export rightly ignores it. |
| 19 | end plate — market for aluminium, wrought alloy | 27.0 | kg | aluminium_wrought | IN | |
| 19 | — sheet rolling, aluminium | 27.0 | kg | sheet_rolling_aluminium | IN | |
| 20 | bipolarplate — titanium production, primary | 528.0 | kg | titanium 528.0 | IN | |
| 21 | membrane polymere — tetraflouroethylen production | 16.0 | kg | tetrafluoroethylene_rer 16.0 | IN | Nafion proxy, paper §2.2.2 |
| 22 | electrocatalyst anode — carbon black production | 4.5 | kg | carbon_black 9.0 | IN | |
| 22 | — **market for iridium** | **0.8** | kg | platinum 0.875 (= 0.075 + 0.8) | **SUBSTITUTED** | platinum "used a replacement for iridium" — stated in the export's comment (uk pem construction.XLSX R61) and in SOURCE_DIFF S3/D3. Gerloff self-built iridium from UBA ProBas data [49]; "market for iridium" is not an ecoinvent dataset. At the map's 70,598 kg CO2e/kg of platinum the 0.8 kg is 56.5 t = 21.7 % of the PEM unit. |
| 23 | electrocatalyst cathode — market for platinum | 0.075 | kg | platinum 0.875 | IN | |
| 23 | — carbon black production | 4.5 | kg | carbon_black | IN | |
| 24 | current collector — copper production, primary | 4.5 | kg | copper_cathode | IN | |
| 24 | — sheet rolling, copper | 4.5 | kg | sheet_rolling_copper | IN | |
| 25 | bolts and screws — sheet rolling, chromium steel | 100.0 | kg | sheet_rolling_cr_steel | IN | |
| 25 | — steel production, chromium steel 18/8, hot rolled | 100.0 | kg | cr_steel_hr_rer | IN | |
| 26 | gasket — synthetic rubber production | 4.8 | kg | synthetic_rubber 4.8 | IN | |
| T3 | SI Table 3 "PEMEC Stack" | 311,672.3 | kWh | electricity_lv_gb 361,672.3 | IN | = 238 kWh/kW × 1000^0.88 × **3** |
| T3 | SI Table 3 "PEMEC BoP" | 50,000.0 | kWh | electricity_lv_gb 361,672.3 | IN | = 50 kWh/kW × 1000 (the SI's own 27 kWh/kW estimate was replaced by the 50 from PEMFC cost data) |

Model-level items (same logic as for AE): stack materials × 3 (rows 19–26; 690.2 kg per stack) **MISSING**; transport leg 1 on 13,871 kg of materials × 250 km = **≈3,470 t·km per unit** **MISSING**; leg 2 BOUNDARY (delivery); paper Table 4 disposal BOUNDARY (end-of-life).

---

## SI Figs. 3, 4, 5 — "Values for SOEC 1 MW BoP and stack components" (parts 1–3) → `soec_con_hermesmann_1unit`

173 valued inputs on 176 printed lines (one duplicate concrete line, two rows with no value), 55 numbered rows: Fig. 3 rows 1–17, Fig. 4 rows 18–32, Fig. 5 rows 33–55. Fig. 3 header reads "BoP"; the "Stack" header is in Fig. 5 before row 49.

**Fig. 3 (part 1) — rows 1–17**

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | heat exchanger 1 — sheet rolling, chromium steel / steel production, chromium steel 18/8, hot rolled | 1079.0 / 1079.0 | kg | sheet_rolling_cr_steel 25,597.5 / cr_steel_hr_rer 25,597.5 | IN | Patyk's 7.13 MW heat exchangers scaled down (paper §2.2.3) |
| 2 | heat exchanger 2 — same pair | 75.8 / 75.8 | kg | as above | IN | |
| 3 | heat exchanger 3 — same pair | 29.8 / 29.8 | kg | as above | IN | |
| 4 | heat exchanger 4 — same pair | 4187.3 / 4187.3 | kg | as above | IN | |
| 5 | heat exchanger 5 — same pair | 205.8 / 205.8 | kg | as above | IN | |
| 6 | heat exchanger 6 — same pair | 66.5 / 66.5 | kg | as above | IN | |
| 7 | heat exchanger 7 — same pair | 35.2 / 35.2 | kg | as above | IN | |
| 8 | heat exchanger 8 — same pair | 83.6 / 83.6 | kg | as above | IN | |
| 9 | heat exchanger 9 — same pair | 57.8 / 57.8 | kg | as above | IN | |
| 10 | heat exchanger 10 — same pair | 23.1 / 23.1 | kg | as above | IN | |
| 11 | heat exchanger 11 — same pair | 14.3 / 14.3 | kg | as above | IN | HX 1–11 sum = 5,858.2 = export "Heat exchanger 1-11" |
| 12 | frequency converter diaphragm compressor 1 — market for aluminium, wrought alloy | 60.0 | kg | aluminium_wrought 401.0 | IN | |
| 12 | — market for copper | 45.0 | kg | copper_cathode 428.5 | IN | |
| 12 | — reinforcing steel production | 180.0 | kg | reinforcing_steel_eur 13,730.6 | IN | |
| 12 | — tube insulation production, elastomere | 15.0 | kg | tube_insulation 176.6 | IN | |
| 12 | — wire drawing, copper | 45.0 | kg | wire_drawing_copper 428.5 | IN | |
| 13 | diaphragm for diaphragm compressor 1 — cast iron production | 600.0 | kg | cast_iron_rer 3,000.0 | IN | |
| 13 | — ethylene glycol production | 7.0 | kg | ethylene_glycol_rer 35.0 | IN | |
| 13 | — reinforcing steel production | 1300.0 | kg | reinforcing_steel_eur | IN | |
| 13 | — sheet rolling, chromium steel | 405.0 | kg | sheet_rolling_cr_steel | IN | |
| 13 | — sheet rolling, steel | 400.0 | kg | sheet_rolling_steel 12,081.2 | IN | |
| 13 | — steel production, chromium steel 18/8, hot rolled | 405.0 | kg | cr_steel_hr_rer | IN | |
| 14 | container with pipes and fittings for diaphragm compressor 1 — reinforcing steel production | 1000.0 | kg | reinforcing_steel_eur | IN | |
| 14 | — sheet rolling, chromium steel | 1500.0 | kg | sheet_rolling_cr_steel | IN | |
| 14 | — sheet rolling, steel | 1000.0 | kg | sheet_rolling_steel | IN | |
| 14 | — steel production, chromium steel 18/8, hot rolled | 1500.0 | kg | cr_steel_hr_rer | IN | |
| 15–17 | compressor 2: the same 15 lines with identical values | as 12–14 | kg | as 12–14 | IN | |

**Fig. 4 (part 2) — rows 18–32**

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 18–20 | compressor 3: the same 15 lines, identical values | as 12–14 | kg | as 12–14 | IN | |
| 21–23 | compressor 4: the same 15 lines, identical values | as 12–14 | kg | as 12–14 | IN | |
| 24–26 | compressor 5: the same 15 lines, identical values | as 12–14 | kg | as 12–14 | IN | five compressors: Al 300, Cu 225, rebar 900+6,500+5,000, TI 75, WD 225, cast iron 3,000, EG 35, SR Cr 2,025+7,500, SR steel 2,000+5,000, Cr HR 2,025+7,500 = export rows |
| 27 | power eletronics (rectifier, voltage adaption) — market for aluminium, wrought alloy | 100.0 | kg | aluminium_wrought | IN | |
| 27 | — market for copper | 200.0 | kg | copper_cathode | IN | |
| 27 | — reinforcing steel production | 600.0 | kg | reinforcing_steel_eur | IN | |
| 27 | — sheet rolling, aluminium | 100.0 | kg | sheet_rolling_aluminium 100.0 | IN | |
| 27 | — sheet rolling, steel | 600.0 | kg | sheet_rolling_steel | IN | |
| 27 | — tube insulation production, elastomere | 100.0 | kg | tube_insulation | IN | |
| 27 | — wire drawing, copper | 200.0 | kg | wire_drawing_copper | IN | |
| 28 | control electronics — electronics production, for control unit | 100.0 | kg | electronics_rer 100.0 | IN | |
| 29 | mixer 1 — sheet rolling, chromium steel / steel production, chromium steel 18/8, hot rolled | 2.1 / 2.1 | kg | sheet_rolling_cr_steel / cr_steel_hr_rer | IN | |
| 30 | mixer 2 — same pair | 25.3 / 25.3 | kg | as above | IN | |
| 31 | splitter 2 (valve) — same pair | 0.4 / 0.4 | kg | as above | IN | |
| 32 | splitter 1 — same pair | 2.0 / 2.0 | kg | as above | IN | rows 29–32 sum 29.8 = export "Mixer 1/2 and splitter 1/2" |

**Fig. 5 (part 3) — rows 33–55**

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| — | *heater 1 (water)* sub-header | | | | | |
| 33 | flange — sheet rolling, chromium steel / steel production, chromium steel 18/8, hot rolled | 11.0 / 11.0 | kg | sheet_rolling_cr_steel / cr_steel_hr_rer | IN | |
| 34 | vessel — same pair | 29.3 / 29.3 | kg | as above | IN | |
| 35 | control panel — acrylonitrile-butadiene production | 0.4 | kg | abs_row 1.4 | IN | SI says "acrylonitrile-butadiene"; export/module ABS copolymer |
| 35 | — injection moulding | 0.4 | kg | injection_moulding 1.4 | IN | |
| 35 | — tube insulation production, elastomere | 0.4 | kg | tube_insulation | IN | |
| 35 | — market for copper | 0.9 | kg | copper_cathode | IN | |
| 35 | — wire drawing, copper | 0.9 | kg | wire_drawing_copper | IN | |
| 35 | — reinforcing, steel production | 2.7 | kg | reinforcing_steel_eur | IN | |
| 35 | — sheet rolling, steel | 2.7 | kg | sheet_rolling_steel | IN | |
| 36 | skid component — reinforcing, steel production / sheet rolling, steel | 92.3 / 92.3 | kg | reinforcing_steel_eur / sheet_rolling_steel | IN | |
| — | *heater 1 (pre-heating)* sub-header | | | | | |
| 37 | flange — same Cr pair | 53.1 / 53.1 | kg | as row 33 | IN | |
| 38 | vessel — same Cr pair | 121.0 / 121.0 | kg | as row 33 | IN | flange+vessel ×2 = 214.4 = export |
| 39 | control panel — ABS / injection moulding / tube insulation / copper / wire drawing / reinforcing steel / sheet rolling steel | 1.0 / 1.0 / 1.0 / 1.9 / 1.9 / 5.8 / 5.8 | kg | as row 35 | IN | rows 35+39 = export's 1.4 / 1.4 / 1.4 / 2.8 / 2.8 / 8.5 / 8.5 |
| 40 | skid component — reinforcing, steel production / sheet rolling, steel | 359.8 / 359.8 | kg | as row 36 | IN | 92.3+359.8 = 452.1 = export |
| 41 | seperator — same Cr pair | 399.0 / 399.0 | kg | as row 33 | IN | |
| 42 | water pump — same Cr pair | 7.0 / 7.0 | kg | as row 33 | IN | |
| 43 | frequency converter water pump — market for aluminium, wrought alloy | 1.0 | kg | aluminium_wrought | IN | |
| 43 | — market for copper | 0.7 | kg | copper_cathode | IN | |
| 43 | — reinforcing steel production | 3.0 | kg | reinforcing_steel_eur | IN | |
| 43 | — tube insulation production, elastomere | 0.2 | kg | tube_insulation | IN | |
| 43 | — wire drawing, copper | 0.7 | kg | wire_drawing_copper | IN | |
| 44 | tubing — steel production, low-alloyed / sheet rolling , steel | 1503.6 / 1503.6 | kg | low_alloyed_steel_hr_rer 3,753.6 / sheet_rolling_steel | IN | 100 kW SOFC tubing × (10)^0.7, paper §2.2.3 |
| 45 | water purifier & feed tank — extrusion, plastic pipes / polyethylene production, low density, granulate | 534.0 / 534.0 | kg | extrusion_pipes 534.0 / polyethylene_ld_rer 534.0 | IN | |
| 45 | — reinforcing, steel production / sheet rolling, steel | 267.0 / 267.0 | kg | reinforcing_steel_eur / sheet_rolling_steel | IN | |
| 46 | buffertank — sheet rolling, chromium steel / steel production chromium steel 18/8 hot rolled | 588.0 / 588.0 | kg | as row 33 | IN | |
| 46 | — welding, arc steel | 33.3 | m | welding_arc_steel 33.3 m | IN | |
| 47 | container — sheet rolling, steel / steel production, low alloyed, hot rolled | 2250.0 / 2250.0 | kg | sheet_rolling_steel / low_alloyed_steel_hr_rer | IN | |
| 48 | foundation concrete — concrete production 35MPa, RNA only [RoW] | 5600.0 | kg | — | NOT-APPLICABLE | duplicate of the m3 line |
| 48 | — concrete production 35MPa, RNA only [RoW] | 2.3 | m3 | concrete_35mpa_cem2 2.3 | IN | |
| — | *Stack* header | | | | | |
| 49 | air electrode — sheet rolling, chromium steel / steel production, chromium steel 18/8, hot rolled | 8976.1 / 8976.1 | kg | as row 33 | IN | 35 % of the unit's Cr steel |
| 50 | air electrode screen printing — market for praseodymium oxide | 9.0 | kg | praseodymium_oxide 9.0 | IN | module: Pr-Nd oxide market (no Pr oxide alone in 3.9.1) |
| 50 | — market for nickel 99,5% | 7.5 | kg | nickel_class1 144.1 | IN | |
| 51 | blocking layer — zirconium oxide production [RoW] | 170.7 | kg | zirconium_oxide_row_soec 170.7 | IN | |
| 51 | — market for samarium europium gadolinium concentrate, 94% rare earth oxide | 14.8 | kg | samarium_seg_oxide 37.7 | IN | Gerloff's stand-in for yttria (paper §2.2.3) |
| 52 | blocking layer screen printing — market for cerium concentrate | 91.5 | kg | cerium_oxide 91.5 | IN | module: cerium oxide → mischmetal market (as built, flagged) |
| 52 | — market for samarium europium gadolinium concentrate, 94% rare earth oxide | 22.9 | kg | samarium_seg_oxide | IN | |
| 53 | **electrolyte — market for lanthanum oxide** | *"see excel sheet_Data generation_material"* | — | — | **MISSING** | no amount, no unit in the SI; export carries 0 kg. See #11. |
| 53 | **— market for strontium carbonate** | *(same cell text)* | — | — | **MISSING** | as above |
| 54 | electrolyte + H2 electrode — aluminium oxide production [IAI Area, EU27 & EFTA | 6.4 | kg | aluminium_oxide 6.4 | IN | glass-sealant oxide, 25 % each (paper §2.2.3); module routes to the refractory market (as built, flagged) |
| 54 | — boric oxide production [GLO] | 6.4 | kg | boric_oxide 6.4 | IN | |
| 54 | — barium oxide production [GLO] | 6.4 | kg | barium_oxide 6.4 | IN | |
| 54 | — silicone product production [RER] | 6.4 | kg | silicone_product 6.4 | IN | the paper (§2.2.3) says "the process for pure silicon has been selected" for SiO2; the SI figure, export and module all carry *silicone* product. Follows the figure. |
| 55 | firing of cell after air electrode application — market for nickel 99,5% | 136.6 | kg | nickel_class1 144.1 | IN | 7.5 + 136.6 = 144.1 |
| T3 | SI Table 3 "SOEC Stack" | 366,673.3 | kWh | electricity_lv_gb 443,093.5 | IN | = 280 kWh/kW (Häfele) × 1000^0.88 × **3** |
| T3 | SI Table 3 "SOEC BoP" | 76,420.2 | kWh | electricity_lv_gb 443,093.5 | IN | = 76.4 kWh/kW × 1000 |

Not a row, but part of Gerloff's SOEC stack per paper Table 8 and §2.2.3: the LSM layer also needs **manganese** (La(1-x)Sr(x)MnO3); no Mn row appears in Figs 3–5 either — it will be in the same Excel sheet as #11. Paper Table 8 lists "Interconnect (including LSM layer)" and "Electrolyte" as separate items; the SI puts the LSM ingredients under "electrolyte" (row 53).

Model-level items: stack materials × 3 (rows 49–55; 9,454.7 kg per stack) **MISSING**; transport leg 1 on 48,237 kg × 250 km = **≈12,060 t·km per unit** **MISSING**; leg 2 BOUNDARY; disposal BOUNDARY.

---

## SI Tables 3–6 → the operation activities and lifetime outputs

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| T4 | Produced amount of hydrogen in 20 years — AEC | 3,085,961.12 | kg | AE_UNITS_PER_KG_H2 = 3.24e-7 (1/3,085,961 = 3.2405e-7) | IN | 51.8 kWh/kg × 3,085,961 kg = 159.85 GWh = 1 MW × 8,000 h × 20 y (paper §2.1.2, §2.1.7). Export comment "3085961kg in 20 year lifetime from gerloff" |
| T4 | — PEMEC | 2,964,315.35 | kg | PEM_UNITS_PER_KG_H2 = 3.37e-7 (exact 3.3735e-7, −0.10 %) | IN | 54 × 2,964,315 = 160.07 GWh |
| T4 | — SOEC | 3,779,894.18 | kg | SOEC_UNITS_PER_KG_H2 = 2.645e-7 (exact 2.6456e-7) | IN | 42.3 × 3,779,894 = 159.89 GWh. Export has 2.64e-7 (−0.21 %); the module's 2.645e-7 is the closer transcription |
| T6 | Water demand H2 production (l), all three | 8.9 | l/kg H2 | water_deionised **8.99** kg (all three) | IN-DIFFERS | SI/paper Table 3: 8.9; export and module: 8.99 (+1.0 %). Stoichiometry is 8.94. The export's figure is not the SI's. |
| T6 | Water demand cooling & compressor (l) — AEC | 88.1 | l | water_softened 88.1 kg | IN | SI note 1: per-hour demand ÷ kg H2/h, "see excel sheet H2_generation" |
| T6 | — PEMEC | 88.1 | l | water_softened 88.1 kg | IN | |
| T6 | — SOEC | 644.7 | l | water_softened 644.7 kg | IN | 7.3 × the AEC/PEMEC figure; Gerloff's own |
| T6 | Electricity demand (kWh) — AEC | 51.8 | kWh | electricity_lv_de 51.8 | IN | IndWEDe average (48.7+51.8+54.9)/3; Gerloff runs it on the German 2019/2030/2050/RE mixes — the module's DE LV market is a grid substitution (study choice); the AE_OP comment "Electricity LV GB" is wrong, the row is DE |
| T6 | — PEMEC | 54 | kWh | electricity_lv_gb 54.0 | IN | grid rebased to GB (study choice) |
| T6 | — SOEC | 42.3 | kWh | electricity_lv_gb 42.3 | IN | as above |
| T6 | KOH (kg) — AEC | 0.0037 | kg | electrolyte_koh 0.0037 | IN | 3,800 kg × 3 fills / 3,086,000 kg (SI note 4). Dataset is the user's: "electrolyte, KOH, LiOH additive" is a battery electrolyte, not KOH; immaterial at 3.7 g/kg |
| T6 | Heat (kWh) — PEMEC | 0.28 | kWh | heat_rer 1.008 MJ | IN | SI note 5: 1.64 MJ/h for a 100 kW PEMEC at 1.6 kg/h (Zhang) → 0.28 kWh/kg; dataset "market for heat, district or industrial [RER]" (paper §2.2.3) = export = module |
| T6 | Heat (kWh) — SOEC | 5.24 | kWh | heat_ng_boiler 18.864 MJ | IN (amount) | SI note 5 cites "Mehmeti p. 10"; dataset deliberately swapped to Mehmeti's boiler — not checked here, per brief |
| T3/T5 | Additional manufacturing energy per kg (Table 5) | 0.0929+0.0120 / 0.1051+0.0169 / 0.0970+0.0202 | kWh/kg | via the capital good ÷ lifetime kg | IN | Table 5 = Table 3 ÷ Table 4 exactly; the module reproduces it by linking the unit at 1/Table 4 |
| §2.1 | Oxygen co-product: "released into the atmosphere", no allocation | — | — | none (exports carry O2 8 kg at 0 % allocation) | NOT-APPLICABLE | no burden, zero GWP |
| §2.1 | System model: ecoinvent 3.5, allocation cut-off | — | — | ecoinvent 3.9.1 apos | SUBSTITUTED (background) | study choice, documented elsewhere |

---

## Three-way check — Gerloff SI vs the SimaPro export vs the module

Per ecoinvent process (the module's granularity). "Export" is the user's `Documents\brightway\*.XLSX`; the exports' row order and comment column do not follow the SI, so the sums are what ties them.

### AE — `alkaline electrolyser.XLSX` (64 material rows + 2 electricity) → `ae_hermesmann_1unit`

| Process | SI Fig. 1 (sum of rows) | Export | Module | Flag |
|---|---|---|---|---|
| extrusion, plastic pipes | 464.6 | 464.6 | 464.6 | |
| polyethylene LD granulate | 464.6 (**LD**) | 464.6 **HD** {RoW} | 464.6 HD | **export ≠ SI (dataset)**; module follows the export |
| reinforcing steel | 232.3+600+696.8+180+1300+1000+836.2+209.1+**80** = **5,134.4** | …+**160** = **5,214.4** | **5,134.4** | export ≠ SI: gas separator 160 for 80; module corrected 21 Oct |
| sheet rolling, steel | 232.3+600+696.8+**400**+1000+836.2+209.1+**80**+6075.6 = **10,130.0** | 405 and 160 → **10,215.0** | **10,130.0** | export ≠ SI in two rows (405/400, 160/80); module corrected 21 Oct |
| electronics, control units | 100 | 100 {RoW} | 100 | |
| aluminium, wrought alloy | 100+60 = 160 | 100 (APOS) + 60 (Cut-off) = 160 | 160 | export mixes APOS and Cut-off datasets; harmless once rebuilt |
| copper (market) | 200+45+371.7 = 616.7 | 616.7 | 616.7 | |
| sheet rolling, aluminium | 100 | 100 | 100 | |
| tube insulation | 100+15+92.9 = 207.9 | 207.9 | 207.9 | |
| wire drawing, copper | 616.7 | 616.7 | 616.7 | |
| glass fibre | 464.6 | 464.6 | 464.6 | |
| sheet rolling, chromium steel | 232.3+405+1500+511+929.1+1161.4+851+1108+20194.4 = 26,892.2 | 26,892.2 | 26,892.2 | |
| steel, chromium 18/8 hot rolled | 26,892.2 | 26,892.2 | 26,892.2 | |
| cast iron | 600+116.1 = 716.1 | 716.1 | 716.1 | |
| ethylene glycol | 7 | 7 | 7 | |
| welding, arc, steel | 29 m | 29 m | 29 m | |
| polypropylene / injection moulding | 3 / 3 | 3 / 3 | 3 / 3 | |
| steel, low-alloyed hot rolled | 6,075.6 | 6,075.6 | 6,075.6 | |
| concrete 35MPa | 7.7 m3 | 7.7 m3 | 7.7 m3 | dataset proxy only |
| nickel 99.5 % | 2,884.9 | 2,884.9 (mine operation dataset) | 2,884.9 (class 1 market) | identity only |
| tetrafluoroethylene | 144.2 | 144.2 | 144.2 | |
| polysulfone / zirconium oxide | 48.8 / 73 | 48.8 / 73 | 48.8 / 73 | |
| electricity (manufacturing) | 286,659.9 + 37,113.5 = 323,773.4 | 323,773.4 DE LV | 323,773.4 DE LV | |
| lanthanum/strontium | — | — | — | n/a (SOEC only) |

The export's comment column is shifted against its rows (e.g. "Nickel 2884.9 — Hydrogen drier and deoxidiser", "Concrete 7.7 — Control panel/electronics"); the module's own row comments are correct against the SI, so nothing to fix there.

### PEM — `uk pem construction.XLSX` (60 rows + 2 electricity) → `pem_con_hermesmann_1unit`

All 60 amounts equal the SI's, row for row (sums: Al 287, SR Al 227, Cu 349.5, SR Cu 104.5, WD 245, rebar 3,312.3, SR steel 5,382.3, SR Cr 4,427, Cr HR 4,427, low-alloyed 3,150, TI 115, cast iron 600, EG 7, extrusion 464.6, PE LD 464.6, PP 300, IM 300, lube oil 100, zeolite 100, welding 29 m, concrete 2.3 m3, electronics 100, carbon black 9, Pt 0.075, Ti 528, TFE 16, rubber 4.8; electricity 311,672.3 + 50,000 = 361,672.3). The one difference is the **dataset** on row 22: SI "market for iridium" 0.8 kg → export "Platinum {GLO}| market for" 0.8 kg with the comment "used a replacement for iridium" → module platinum 0.875. Export TFE is {RoW}, module RER — trivial.

### SOEC — `uksoecconstruction.XLSX` (74 rows × parameter r=1 + 2×2 electricity rows on pnorm/pwind) → `soec_con_hermesmann_1unit`

All 72 valued export rows equal the SI's aggregates (sums shown in the figure tables above; e.g. SR Cr 5,858.2+2,025+7,500+29.8+214.4+399+7+588+8,976.1 = 25,597.5; SR steel 2,000+5,000+600+8.5+452.1+1,503.6+267+2,250 = 12,081.2; rebar 900+6,500+5,000+600+8.5+452.1+267+3 = 13,730.6). The export's two extra rows "Lanthanum oxide {GLO}| market for — 0 kg — Electrolyte (Stack)" and "Strontium carbonate {GLO}| market for — 0 kg" carry the SI's un-valued row 53 at zero; the module drops them. The export's wind-only electricity rows (pwind = 0) are a scenario switch the module does not carry. Electricity 76,420.2 + 366,673.3 = 443,093.5 on GB LV (export, module); Gerloff: German scenario mixes.

### Operation exports vs SI Table 6

| Row | SI | Export | Module | Flag |
|---|---|---|---|---|
| water, H2 production | 8.9 l | 8.99 kg (all three) | 8.99 | **export ≠ SI** (+1 %) |
| water, cooling & compressor | 88.1 / 88.1 / 644.7 | same | same | |
| electricity | 51.8 / 54 / 42.3 | same (DE / GB / GB) | same | |
| KOH | 0.0037 | 0.0037 | 0.0037 | |
| heat | 0.28 / 5.24 kWh | 0.28 / 5.24 kWh | 1.008 / 18.864 MJ | |
| unit per kg | 1/Table 4 | 3.24e-7 / 3.37e-7 / 2.64e-7 | 3.24e-7 / 3.37e-7 / 2.645e-7 | SOEC export rounds low; module closer |

Rows where the **export differs from the SI**: AE gas separator (×2 rows, 160 vs 80), AE diaphragm sheet rolling (405 vs 400), AE polyethylene HD vs LD, PEM iridium → platinum (stated), SOEC La2O3/SrCO3 at 0 (unavoidable), water 8.99 vs 8.9 (all three operations). Everything else ties to the decimal.

---

## #11 — the SOEC electrolyte layer (SI Fig. 5 row 53)

Exactly what the SI prints (EMF text records; confirmed on the render):

> **53 | electrolyte | market for lanthanum oxide | see excel sheet_Data**
> **   |             | market for strontium carbonate | generation_material**

The value column of the two-line row holds the text "see excel sheet_Data generation_material" split across the two lines; **no amount, no unit** for either material. SI p.9 (Section "Values, ecoinvent processes and general assumptions") names the same sheet: "The values and further comments … can be found in the excel sheet **data_generation_material** as well as the values entered in the software related to the FU." Two other SI notes point to a second sheet, **H2_generation** (water demand per kg, H2 cooling calculation, the 19.3 kg H2/h production rate). Neither sheet is in the docx (the zip holds only the five EMF images; no `word/embeddings`).

Can an amount be derived from the SI? **No.** The SI gives no layer mass, no stack mass and no LSM composition. The paper (§2.2.3) says only that "the production of LSM and its ingredients is based on Staffell et al. [63] and the periodic table", that the stack data are Häfele et al. 2016 [28] for a **1 kW** stack scaled by 1000^0.88 = 436.5, and (§5) that LSM and iridium were "self-created" processes whose "shares … on the mass balance are little". The route, if the user wants it: take Häfele's LSM mass per kW, × 436.5, then split by stoichiometry — for La0.8Sr0.2MnO3 (231.6 g/mol) that is 0.563 kg La2O3, 0.128 kg SrCO3 and 0.375 kg MnO2 per kg LSM. Paper Table 8 puts the LSM on the **interconnect** ("Interconnect (including LSM layer)"), not the electrolyte; the SI's "electrolyte" label on row 53 is loose. Manganese appears nowhere in Figs 3–5 either. Scale: the whole SOEC stack's listed materials score 59.5 t CO2e on the map's factors; an LSM layer of a few tens of kg at ecoinvent rare-earth/Sr factors (La2O3 market ≈ tens of kg CO2e/kg) is of order 1 t, i.e. well under 1 % of the 362.8 t unit. SOURCE_DIFF #11's "small" stands.

---

## S5 re-checked — AE gas separator steel and diaphragm sheet rolling against SI Fig. 1

**Diaphragm (row 6): 405 → 400 is unambiguously right.** Fig. 1 prints sheet rolling, chromium steel 405.0 / sheet rolling, steel **400.0** / chromium steel 18/8 405.0. Figs 2, 3 and 4 print the same 405/400/405 for every other diaphragm compressor, and the PEM and SOEC exports carry 400. The AE export's 405 was a copy of the Cr value. −5 kg.

**Gas separator (row 13): 160 → 80 is right against the printed figure, with one caveat.** Fig. 1 prints a single two-line row "gas separator (2 x)" with reinforcing steel production **80.0** kg and sheet rolling, steel **80.0** kg. The export entered 160 on both, i.e. read 80 as per separator and doubled it. The module now carries 80 + 80, i.e. the printed values: reinforcing steel 5,214.4 − 80 = **5,134.4** and sheet rolling steel 10,215 − 85 = **10,130.0** — both equal the sums of the printed rows exactly.

Caveat: the figure does not say whether 80.0 is for both separators or each. Two readings of the SI's own conventions pull opposite ways: Gerloff lists every multiple item in the SOEC figures as its own row with its own value (compressor 1…5, heat exchanger 1…11, mixer 1/2, splitter 1/2), which argues that a value printed once is the total entered; but "(2 x)" with a single value could equally be "two of them, 80 kg each". I tried to settle it from Gerloff's own number — the AEC BoP manufacturing energy of 37,113.5 kWh (SI Table 3) is built from these masses × the Table 1 factors — but the literal rule set reproduces neither reading (34,290 kWh with 80, 34,714 with 160; both ≈2,500 short), so it does not discriminate. The printed 80.0 is the only evidence and the 21 Oct correction follows it. The alternative costs +80 kg rebar and +80 kg sheet rolling, ≈ +0.05 % on the unit — immaterial either way; the ambiguity is worth one sentence in the module comment, nothing more.

---

## Parameters — Table 3 energy, Table 4 lifetime H2, Table 6 operating data vs the module

| Parameter | Gerloff | Module | Check |
|---|---|---|---|
| Manufacturing energy, AE unit | SI Table 3: stack 286,659.9 + BoP 37,113.5 kWh | electricity_lv_de 323,773.4 kWh | = sum; stack term = 218.9 kWh/kW × 1000^0.88 × 3 = 286,660 |
| — PEM unit | 311,672.3 + 50,000.0 | electricity_lv_gb 361,672.3 | = 238 × 436.5 × 3 + 50 × 1000 |
| — SOEC unit | 366,673.3 + 76,420.2 | electricity_lv_gb 443,093.5 | = 280 × 436.5 × 3 + 76.42 × 1000 |
| Lifetime H2 (SI Table 4) | 3,085,961.12 / 2,964,315.35 / 3,779,894.18 kg | 1/3.24e-7 / 1/3.37e-7 / 1/2.645e-7 = 3,086,420 / 2,967,359 / 3,780,718 | within 0.1 % (PEM) and 0.02 % (AE, SOEC) |
| 160 GWh at 1 MW | 1 MW × 8,000 h/y × 20 y (paper §2.1.2) | `EXPECTED_LIFETIME_GWH_PER_MW = 160` | 159.85 / 160.07 / 159.89 GWh from Table 4 × Table 6 |
| Electricity, kWh/kg | 51.8 / 54 / 42.3 (SI Table 6 = paper Table 3) | 51.8 / 54.0 / 42.3 | = |
| Water, l (≈kg)/kg | 8.9 + 88.1 / 8.9 + 88.1 / 8.9 + 644.7 | 8.99 + 88.1 / 8.99 + 88.1 / 8.99 + 644.7 | 8.9 ≠ 8.99 |
| KOH | 0.0037 | 0.0037 | = |
| Heat | 0.28 / 5.24 kWh | 1.008 / 18.864 MJ | = ×3.6 |
| Stack life / replacements | 50,000 h; stacks × 3 over 20 y (paper §2.1.2–2.1.3) | one stack's materials over the unit's whole life (25 y calendar in `electrolysers.py`); three stacks' electricity | **inconsistent** — see Summary |
| Transport | 2 × 250 km, lorry >32 t EURO6 RER, per component weight (paper §2.1) | none | leg 1 in scope, leg 2 out |

The module's parameter comment (hydrogen.py lines 62–63) still reads "Hermesmann's own lifetime outputs, transcribed"; they are Gerloff SI Table 4. `electrolysers.py`'s docstring (lines 6, 27, 44) still says "Hermesmann's capital good".

---

## Claims to check

**"Gerloff's SI points to an Excel sheet not held."** Correct as far as the held files go. The SI names two sheets — `data_generation_material` (SI p.9 and Fig. 5 row 53: "see excel sheet_Data generation_material") and `H2_generation` (SI notes 1, 2 and 4 under Table 6) — and the Word SI contains no embedded workbook. Whether Elsevier hosts an `.xlsx` alongside the Word file could not be verified from here: the paper only says "Supplementary material associated with this article can be found, in the online version, at doi:10.1016/j.est.2021.102759", and the ScienceDirect page (PII S2352152X21004874) refuses automated fetches (HTTP 403). Worth one look at that page's "Appendix A. Supplementary materials" list in a browser: if there is an mmc2.xlsx, #11, the 8.9/8.99 water question and the gas-separator reading are all settled by it.

**"Hermesmann has no AE or SOEC and his PEM bill is Bareiß-based."** Not checkable from these files (Hermesmann's paper is not among them), so no verdict on Hermesmann. What the Gerloff files do show is that the *descriptor* does not discriminate: Gerloff's own PEMEC bill is also Bareiß-based (paper §2.2.2: "The PEMEC BoP and stack components data (see Table 7) stem from Bareiß et al. [5] and correspond to a 1 MW system", with the water purifier, buffer tank and heat exchanger added from Zhang's 300 kW AEC). The attribution of the module to Gerloff rests on the row-level tie instead, and that is complete: all 60 PEM rows including the Gerloff-specific 0.8 kg Ir / 0.075 kg Pt split and the Zhang-derived 464.6/232.3/511/1161 kg additions, all 64 AE rows, all 173 SOEC rows, the three Table 4 lifetime outputs to eight significant figures, and the six Table 3 energies to the decimal. The SI's transformer/rectifier, control-panel and container assumptions (SI Section 3) are stated to come from Bareiß for all three technologies, which is why the AE, PEM and SOEC bills share identical 100 kg electronics, 1 t transformer (600 steel / 200 Cu / 100 Al / 100 elastomer) and 2,250 kg container rows.

Other wrong or stale statements found on the way: `hydrogen.py` AE_OP row comment "Electricity LV GB — electrolysis" on a DE process; SOURCES.md line 970 "No stack/BoP split is possible — Gerloff's capital good is one monolithic activity" and `electrolysers.py` lines 42–48 — the SI figures label every row Stack or BoP (AE rows 19–21, PEM 19–26, SOEC 49–55) and SI Table 3 splits the energy, so a split is possible from the source; it is the export, not Gerloff, that is monolithic.

---

## Summary

Counts (capital-good rows are SI printed input rows; parameters are SI Table rows):

| Disposition | AE (Fig. 1) | PEM (Fig. 2) | SOEC (Figs 3–5) | Tables 3–6 | Model-level items |
|---|---|---|---|---|---|
| IN | 63 | 59 | 173 | 20 | — |
| IN-DIFFERS | 1 (PE LD→HD, dataset only) | 0 | 0 | 1 (water 8.9 → 8.99, ×3 activities) | — |
| SUBSTITUTED | 0 | 1 (0.8 kg Ir → Pt, stated) | 0 | grid datasets (DE/GB for German mixes); 3.9.1 apos for 3.5 cut-off | — |
| MISSING | 0 | 0 | 2 (La2O3, SrCO3: no amount in the SI) | 0 | stack × 3 (AE, PEM, SOEC); transport leg 1 (AE, PEM, SOEC) |
| BOUNDARY | — | — | — | — | transport leg 2 (delivery); paper Table 4 disposal (end-of-life) |
| NOT-APPLICABLE | 0 | 2 lines (foundation printed in kg as well as m3; stray "511.0 kg" on the Stack header) | 1 line (foundation in kg) | O2 co-product at 0 % | — |

Most important first:

1. **Gerloff's stacks are replaced: the source carries three stacks' materials per 20-year life (paper §2.1.2 "replaced 3 times", §2.1.3 "stack components … multiplied with a factor of 3", SI p.1), and the module already carries three stacks' *manufacturing electricity* (SI Table 3 stack energies are × 3, proved by 218.9 × 1000^0.88 × 3 = 286,660) but only one stack's materials.** On the map's own factors one stack's materials are 194.1 t CO2e of the AE unit's 433.7 t (44.8 %), 90.3 t of PEM's 260.9 t (34.6 %, platinum and titanium) and 59.5 t of SOEC's 362.8 t (16.4 %). Two further stacks would add +89.5 % / +69.2 % / +32.8 % to the units as Gerloff amortises them (160,000 h). This is the largest divergence from the source by two orders of magnitude, and the module is internally inconsistent on it. It is also a boundary decision for the user rather than a transcription slip: `electrolysers.py` amortises the unit over 25 calendar years and says stack replacement "cannot be charged separately" — but the SI's Stack/BoP row labels and Table 3's stack/BoP split mean it can.
2. **Upstream transport is in Gerloff and not in the module**: 250 km by lorry >32 t EURO6 on every component's weight for the manufacturing/assembly leg (in scope), plus a second 250 km to site (out). ≈11,000 / 3,470 / 12,060 t·km per AE / PEM / SOEC unit on the single-stack bills; ≈1 / 0.3 / 1.2 t CO2e at ~0.1 kg/t·km, ≤0.3 % of each unit. Small, but sourced and inside the boundary, so by the study's own rule it goes in without a threshold test.
3. **Bills: every valued SI row is in the module at the printed amount** — 64 + 60 + 173 rows — after the 21 Oct AE corrections, which are right against the printed Fig. 1 (400 unambiguously; 80 is the printed value, with the "(2 x)" reading noted as unresolvable from the SI and worth ±0.05 %). The only material substitution is the stated 0.8 kg iridium → platinum (56.5 t CO2e, 21.7 % of the PEM unit on the map's platinum factor, so the proxy matters). The only missing rows are La2O3 and SrCO3 (and, by implication, Mn), whose amounts exist only in Gerloff's `data_generation_material` sheet; nothing in the SI lets them be derived.
4. **Export-vs-SI slips not yet in SOURCE_DIFF**: water for H2 production 8.99 kg in all three operation exports and the module against 8.9 l in SI Table 6 / paper Table 3; AE polyethylene high-density for the SI's low-density; SOEC capital coefficient 2.64e-7 in the export (module's 2.645e-7 is right). Three figure typos for the record: PEM welding printed in kg, a stray 511.0 kg on the PEM "Stack" header, PEM row 5 label clipped.
5. **Attribution**: the capital goods, energies, lifetimes and operating data are Gerloff's to the decimal; "Hermesmann" survives in the activity codes, hydrogen.py lines 62–63, electrolysers.py lines 6/27/44, and the AE_OP comment says GB for a DE row.
