# Hermesmann & Müller 2022 — row ledger (22 Oct 2026)

Source: Hermesmann, M. & Müller, T.E. (2022), "Green, Turquoise, Blue, or Grey? Environmentally friendly Hydrogen Production in Transforming Energy Systems", Prog. Energy Combust. Sci. 90, 100996. 28 pages. Read against `optimiser_lca/hydrogen.py` (activities `smr_hermesmann_1kg_h2`, `smr_ccs_hermesmann_1kg_h2`, `ccs_hermesmann_1kg_co2`, `mp_e_1kg_h2`) at git HEAD 1c99ab0 (working tree unchanged for that file). Repository not modified.

## Files read

**The paper was found**, twice, identical first pages:
- `C:\Users\ls1524\OneDrive - Imperial College London\article LCA\article reading\hermesman SMRCCS 834.pdf` (used; text extracted with PyMuPDF, pages 11–13 also rendered to PNG and checked by eye for column alignment)
- `C:\Users\ls1524\OneDrive - Imperial College London\old\production\hermesmann colours 602.pdf` (duplicate)

**The paper's SI was also found**: `...\article LCA\article reading\hermesman muller suplementary materials.docx` — Table S1 (the ecoinvent 3.6 cut-off datasets behind every Table 2–4 row), Table S3 (reference-case contribution shares). It settles several dataset questions below.

SimaPro exports (all SimaPro 10.3.0.1, project "HyPT", process identifiers `IMPERIAL0001117095001xx`), dumped row by row with pandas/openpyxl:
- `...\article LCA\processes\SMR.XLSX` (DE electricity/gas; created 27/03/2026, exported 01/06/2026)
- `...\article LCA\processes\UK SMR Operation.XLSX` (same rows, GB electricity/gas)
- `...\article LCA\processes\UK SMR-CCS Operation.XLSX` (GB; carries 8.01 kg to the CCS waste treatment)
- `...\article LCA\processes\UK CCS operation.XLSX` (GB electricity; not in the brief but it is the UK twin of ccs.XLSX)
- `...\article LCA\processes\UK MP Operation.XLSX` — **not Hermesmann's MP-E** (see §3.2.4 below)
- `C:\Users\ls1524\Documents\brightway\smr ccs.XLSX` (DE twin of the UK SMR-CCS file; identical amounts)
- `C:\Users\ls1524\Documents\brightway\ccs.XLSX` (DE twin of UK CCS operation; identical amounts)

Also read: `optimiser_lca/hydrogen.py` (whole), `optimiser_lca/registry.py` (codes), `optimiser_lca/common.py` (identity resolution), `optimiser_lca/gb_grid.py` (2025 grid = 141.874 g CO₂e/kWh delivered HV), `docs/SOURCE_DIFF.md` (#12, S2, S4, D1), `optimisation/SOURCES.md` lines 55–290 and 940–1000, `optimisation/ASSUMPTIONS.md` §5–7, the build notebook `Documents\brightway\smr_hermesmann_brightway.ipynb` (cells 16, 32–38, 52, 57), `optimisation_outputs/lca_map.json` (generated 2026-10-22 13:40 at HEAD 1c99ab0; per-exchange contributions quoted below), `optimisation_outputs/h2_prices_by_colour.csv`.

Scores as built (lca_map.json, IPCC 2021 GWP100, kg CO₂e per kg H₂): SMR **11.307**, SMR-CCS **5.154**, CCS treatment **0.0718 per kg CO₂** (×8.01 = 0.575 per kg H₂), MP-E **3.924**.

---

## Table 2 — SMR → `smr_hermesmann_1kg_h2`

Paper Table 2, column "SMR" (p.11). Datasets per SI Table S1 (ecoinvent 3.6 cut-off, the paper's own choices).

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | Input flows: Natural gas | 4.85 | m³ | `gas_hp_gb` 4.85 m³ | IN | Paper/SI: market for natural gas, high pressure **DE**; exports DE (SMR.XLSX) / GB (UK file); module GB. 1.770 kg CO₂e |
| 2 | Process water | 6.64 | kg | `tap_water` 6.64 kg | IN | SI: *market group* for tap water RER; export+module: *market for* tap water, Europe w/o CH. 0.002 kg CO₂e |
| 3 | Cooling water | 0.38 | m³ | `water_resource` 0.38 m³ (biosphere) | IN | SI p.195: "Cooling water … considered as elementary flows". Export: "Water, cooling, unspecified natural origin, GB/DE". Zero GWP |
| 4 | Output flows: Hydrogen | 1.00 | kg | reference product, 1 kg | IN | FU in the paper: "1 kg H₂ at 30 bar … at the production site" (§3.1, p.10) |
| 5 | Electricity | 1.10 | kWh | `FG(GB_GRID_HV_2025)` **−1.1** kWh | IN — credit kept, dataset relinked | The paper's by-product credit ("avoided burden", §3.1.1, §3.2.2; Table 7 "Excess electricity −0.70"). Paper/SI: DE HV market; UK export: GB HV market; module: study grid 141.9 g/kWh → **−0.156 kg CO₂e** (1.4 % of grey). Conflicts with ASSUMPTIONS §5 — see *Claims* |
| 6 | Wastewater | 1.72e-03 | m³ | `wastewater` 0.00172 m³ | IN | SI: market for wastewater, average RER; module Europe w/o CH. −0.0006 (apos) |
| 7 | Emissions (Air): Carbon dioxide | 9.00 | kg | `co2` 9.0 kg (fossil) | IN | Export: "Carbon dioxide" (unspecified); module: fossil. A second, ADDED CO₂ row of 0.6787 kg follows — see *Module rows with no source row* |
| 8 | Nitrogen | 16.41 | kg | `nitrogen_air` 16.41 kg | IN | Absent from every export; restored from the paper (#12). Zero GWP (map contribution 0.0) |
| 9 | Oxygen | 0.31 | kg | `oxygen_air` 0.31 kg | IN | Amount right, compartment wrong: built as Oxygen to **water** (module's own `why`). Zero GWP |
| 10 | Water | 2.93 | kg | `water_air` 2.93 kg | IN | Amount right, flow wrong: "Water, in air" is a natural-resource input, not an emission (module's own `why`). Zero GWP |
| 11 | Construction materials: Concrete | 6.60e-06 | m³ | `concrete_normal` 6.60e-6 m³ | IN | SI: market for concrete, normal RoW — same |
| 12 | Steel | 5.06e-03 | kg | `steel_unalloyed` 5.06e-3 kg | IN | SI: market for steel, unalloyed GLO — same |
| 13 | Aluminum | 4.17e-05 | kg | `aluminium_cast` 4.17e-5 kg | IN | SI: "market for aluminium, cast alloy" GLO; export/module: "aluminium, primary, cast alloy slab from continuous casting" GLO. 0.00014 kg CO₂e, immaterial |
| 14 | Cast iron | 6.18e-05 | kg | `cast_iron_glo` 6.18e-5 kg | IN | SI: market for cast iron GLO — same |
| 15 | Steam turbine | 7.90e-10 | Unit | `gas_turbine` 7.90e-10 unit | IN | **Not an export substitution**: SI Table S1 row "Gas turbine — Market for gas turbine, 10MW electrical GLO" is the paper's own proxy for its "Steam turbine" row. 0.0003 kg CO₂e |

15/15 printed rows in. No row of the paper's SMR column is outside this study's boundary (the paper is cradle-to-gate at the production site, §3.1).

---

## Table 2/3 — SMR-CCS → `smr_ccs_hermesmann_1kg_h2` and `ccs_hermesmann_1kg_co2`

Paper Table 2, column "SMR-CCS (90%)" (post-combustion MEA on the flue gas, p.12, Fig. 9 bottom). The module takes the 90 % column (nitrogen 20.84 confirms it). The 56 % column (MDEA pre-combustion) is not used.

### Table 2 rows → `smr_ccs_hermesmann_1kg_h2` (per kg H₂)

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | Natural gas | 5.33 | m³ | `gas_hp_gb` 5.33 m³ | IN | 1.945 kg CO₂e |
| 2 | Process water | 4.68 | kg | `tap_water` 4.68 kg | IN | |
| 3 | Cooling water | 1.18 | m³ | `water_resource` 1.18 m³ | IN | Zero GWP |
| 4 | Hydrogen | 1.00 | kg | reference product | IN | |
| 5 | Electricity | 0.05 | kWh | `FG(GB_GRID_HV_2025)` **−0.05** kWh | IN — credit kept, dataset relinked | −0.007 kg CO₂e. Paper p.17: for 90 % "no excess electricity remains … used entirely for the subsequent CCS system" — i.e. the 0.05 kWh is netted against the CCS chain's 0.0241 kWh/kg CO₂; the module nets the same way through the CCS activity (−0.05 + 8.01 × 0.0241 = +0.143 kWh net import) |
| 6 | Wastewater | 1.83e-03 | m³ | `wastewater` 0.00183 m³ | IN | |
| 7 | Carbon dioxide | 0.99 | kg | `co2` 0.99 kg | IN | Plus an ADDED closure row of 1.6366 kg — see below |
| 8 | Nitrogen | 20.84 | kg | `nitrogen_air` 20.84 kg | IN | Restored #12; absent from exports; zero GWP |
| 9 | Oxygen | 0.41 | kg | `oxygen_air` 0.41 kg | IN | Compartment wrong (water), self-flagged, zero GWP |
| 10 | Water | 1.33 | kg | `water_air` 1.33 kg | IN | Flow wrong (resource), self-flagged, zero GWP |
| 11 | Concrete | 6.60e-06 | m³ | `concrete_normal` 6.60e-6 | IN | |
| 12 | Steel | 5.06e-03 | kg | `steel_unalloyed` 5.06e-3 | IN | |
| 13 | Aluminum | 4.17e-05 | kg | `aluminium_cast` 4.17e-5 | IN | Dataset as SMR #13 |
| 14 | Cast iron | 6.18e-05 | kg | `cast_iron_glo` 6.18e-5 | IN | |
| 15 | Steam turbine | 7.90e-10 | Unit | `gas_turbine` 7.90e-10 | IN | Paper's own gas-turbine proxy (SI S1) |
| 16 | *(not printed)* CO₂ captured and sent to CCS | — (implied **≈ 8.90**) | kg | `FG(CCS)` **8.01** kg | **IN-DIFFERS (8.01 vs ≈ 8.90)** | The export sets 8.01 = 9.00 − 0.99, i.e. SMR's total CO₂. The paper's own arithmetic says the total scales with the gas: 9.00 × 5.33/4.85 = 9.891, of which 10 % = 0.989 → the printed **0.99**; captured = 8.90. Corroborated twice: the 56 % column (4.12 = 44.3 % of 9.00 × 5.01/4.85 = 9.297, "approximately 56 %"), and Table 7's SMR-CCS (90 %) electricity line of 0.14 kg CO₂e, which at the 0.636 kg/kWh implied by −0.70/1.10 kWh is 0.22 kWh ≈ 9.1 kg × 0.0241 kWh/kg (8.01 kg would give 0.12). Effect on its own is small (0.89 kg × 0.0718 = +0.064 kg CO₂e/kg H₂); its consequence for the closure row is not — see *Module rows with no source row* |

### §3.2.3 text rows → `ccs_hermesmann_1kg_co2` (per kg CO₂ captured)

The paper gives these as narrative, not as a table (p.12–13). The per-kg amounts were derived by the user in ccs.XLSX; the module copies them.

| # | Source statement (p.12–13) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| C1 | CO₂ pipeline "approximated by a natural gas pipeline dataset … A capacity of 14,010 t CO₂ and a transport distance of 300 km" | 300 km / 14,010 t | — | `ccs_pipeline` 2.34666e-9 km | IN (DERIVED) | = 300 / (14,010 t·d⁻¹ × 365 × 25 y × 1000). "Per day" and the 25-year life are **not in the paper** (it states a 20-year plant life; the pipeline's life is not given). Export comment says "14000 t" but the number uses 14,010. At 20 y: 2.933e-9. SI S1: market for pipeline, natural gas, long distance, low capacity, onshore GLO — same dataset. 0.0026 kg CO₂e/kg CO₂ |
| C2 | "For compression during transport, an energy demand of 0.0171 kWh/kg CO₂" | 0.0171 | kWh/kg CO₂ | `FG(GB_GRID_HV_2025)` 0.0171 kWh | IN | Paper/SI DE HV market; UK export GB HV; module study grid. 0.0024 kg CO₂e |
| C3 | "fugitive CO₂ emissions of 2.320 kg CO₂ per kilometer and year" | 2.320 | kg/km/a | `co2` 1.36106e-7 kg | IN (DERIVED) | = 2.320 × 300 / (14,010 × 365 × 1000); reproduces to all six digits |
| C4 | "six wells at a depth of 3,000 m for a storage capacity of 7.3 Mt/a CO₂" | 6 × 3,000 m / 7.3 Mt·a⁻¹ | — | `ccs_well` 9.863e-8 m | IN (DERIVED) | = 18,000 / (7.3e9 kg·a⁻¹ × 25 y); exact. Export comment says "7.4 Mt" but the number uses 7.3. 25-year life again not in the paper (20 y → 1.233e-7). SI S1: market for onshore well, oil/gas GLO — same. 0.0001 kg CO₂e |
| C5 | "For the storage pressure of 150 bar, compressors consume 0.007 kWh/kg CO₂" | 0.007 | kWh/kg CO₂ | `FG(GB_GRID_HV_2025)` 0.0070 kWh | IN | 0.0010 kg CO₂e |
| C6 | "The injection wells are driven by diesel fuel with **15.4 kg diesel/kg CO₂** according to Verma et al [39]." | 15.4 | kg/kg CO₂ | `ccs_diesel_burned` 0.65912 MJ (= 0.0154 kg × 42.8 MJ/kg) | **IN-DIFFERS (15.4 vs 0.0154 kg/kg) + SUBSTITUTED (dataset)** | Read as per tonne (export comment: "15.4kg per T of CO2 (not 15.4kg per kg like in the paper, too high)"). SI Table S1 shows the **paper itself** linked "Diesel — Market group for diesel RER, kg" as a bought product, never burned; the module burns it in a building machine. As built this row is **0.0657 kg CO₂e/kg CO₂ = 91.5 % of the CCS activity, 0.526 kg CO₂e/kg H₂ = 10.2 % of blue**. See *Parameters* for what the paper's own totals allow |

Everything the paper prints for SMR-CCS is in. BOUNDARY: nothing — ASSUMPTIONS §6 keeps the CCS leg inside the gate, and the paper stops at the production site too.

---

## §3.2.4 — MP-E → `mp_e_1kg_h2`

Paper Table 3, column "MP-E" (liquid-tin bubble-column pyrolysis after Postels et al. 2016 [139], electrically heated at 95 %). **There is no SimaPro export of this inventory.** `UK MP Operation.XLSX` is a different model — "UK Hydrogen (Methane Pyrolysis, Diab)": 7.536 m³ gas, 29.56 kWh LV electricity (plasma front end 25.46 + carbon-black back end 0.80 + purification 2.27 + BoP 1.02), graphite 0.019 kg, EAF converter proxy, 0.269 kg direct CO₂, co-products 4.26 kg carbon black + 0.071 kg coke on mass allocation. None of its rows match Table 3. The module's MP-E was typed straight from Table 3 (notebook cell 38: "Inventory for Methane Pyrolysis MP-E (Table 3, MP-E column)"), so the three-way check for this route has two legs, not three.

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | Input flows: Natural gas | 5.72 | m³ | `gas_hp_gb` 5.72 m³ | IN | Paper DE market; module GB. 2.088 kg CO₂e (53 % of MP-E) |
| 2 | Electricity | 10.29 | kWh | `FG(GB_GRID_HV_2025)` 10.29 kWh | IN | Paper/SI DE HV market; notebook DE HV; module study grid → 1.460 kg CO₂e (37 %) |
| 3 | Output flows: Hydrogen | 1.00 | kg | reference product | IN | |
| 4 | Carbon | 3.00 | kg | **no row** | **SUBSTITUTED → NOT-APPLICABLE by decision** | Paper §3.2.4: "the by-product carbon was included as an avoided burden for conventional carbon black production"; Table 7 quantifies it at **−5.62 kg CO₂e/kg H₂** for MP-E (9.91 → 4.28). But p.18: "carbon and oxygen production was no longer given any credit in MP and PEMEL due to the questionable quality, respectively market size of the by-product" — the paper's §4.2 onwards and its country table (p.23: Germany MP-E 9.91, uncredited) drop it. Module: no credit, whole burden on hydrogen (user decision 21 Oct 2026; ASSUMPTIONS §5). The module therefore matches the paper's *own* later convention, not a departure from it. Stoichiometry check: 12.011/4.032 = 2.98 kg C per kg H₂ ≈ 3.00 |
| 5 | Emissions (Air): Carbon dioxide | – | kg | no biosphere row | IN (none) | "No process-related GHG emissions … if the process is heated by electricity" (p.15) |
| 6 | Construction materials: Palladium | 8.45e-06 | kg | `palladium` 8.45e-6 kg | IN | SI: "Market for palladium GLO"; module landed on "palladium to generic market for metal catalyst for catalytic converter" GLO. Scores **0.102 kg CO₂e = 2.6 % of MP-E** — the module's `why` calls it "immaterial"; it is above a 1 % screen. Worth re-pinning to the market and re-scoring |
| 7 | Copper | 5.63e-06 | kg | `copper_cathode` 5.63e-6 kg | IN | SI: market for copper; module copper, cathode. 4e-5 kg CO₂e |
| 8 | Low alloyed steel | 1.99e-03 | kg | `steel_low_alloyed` 1.99e-3 kg | IN | 0.004 kg CO₂e |
| 9 | High alloyed steel | 3.89e-04 | kg | `steel_chromium_188` 3.89e-4 kg | IN | SI: market for steel, chromium steel 18/8 — same |
| 10 | Silica sand | 6.18e-05 | kg | `silica_sand` 6.18e-5 kg | IN | |
| 11 | Tin | 2.58e-02 | kg | `tin` 2.58e-2 kg | IN | 0.268 kg CO₂e (6.8 %); paper Table 7 "Tin 0.27" — agrees |
| 12 | Silicon carbide | 3.23e-06 | kg | `silicon_carbide` 3.23e-6 kg | IN | |

11/12 rows in; the carbon co-product is the one stated substitution. Nothing BOUNDARY, nothing MISSING. Cosmetic: the activity is labelled `location="DE"` while every input it links is GB.

Note on the mass-allocation alternative (SOURCE_DIFF D1 option b): the pointer to `UK MP Operation.XLSX` (4.26 kg carbon black) is to the Diab plasma model, not to Hermesmann's inventory. Mass allocation on Hermesmann's own Table 3 would put 1/(1+3.00) = **25 %** of the MP-E burden on hydrogen (0.98 kg CO₂e/kg instead of 3.92).

---

## Three-way check — paper vs SimaPro export vs module

Export columns: SMR = SMR.XLSX / UK SMR Operation.XLSX; SMR-CCS = smr ccs.XLSX / UK SMR-CCS Operation.XLSX; CCS = ccs.XLSX / UK CCS operation.XLSX. Each DE/GB pair carries identical amounts and differs only in the geography of the electricity (and, for SMR and SMR-CCS, the gas and the cooling-water name). **Flag** marks where an export departs from the paper.

| Row | Paper (Table 2/3, §3.2.3, SI S1) | Export | Module | Flag |
|---|---|---|---|---|
| SMR gas | 4.85 m³, HP market DE | 4.85, DE / GB | 4.85, GB | geography only |
| SMR process water | 6.64 kg, market *group* tap water RER | 6.64, market for tap water Europe w/o CH | same as export | dataset (immaterial) |
| SMR cooling water | 0.38 m³, elementary flow | 0.38 "Water, cooling, unspecified natural origin, GB" (resource) | same | — |
| SMR electricity out | 1.10 kWh, avoided burden, DE HV market | avoided product 1.1 kWh, DE / GB HV market | −1.1 kWh, study GB grid | dataset; credit kept (see Claims) |
| SMR wastewater | 1.72e-3 m³ | 0.00172 | 0.00172 | — |
| SMR CO₂ | 9.00 kg | 9 "Carbon dioxide" (unspecified) | 9.0 fossil **+ 0.6787 closure** | module adds a row the paper does not have |
| SMR **nitrogen** | **16.41 kg** | **absent** | 16.41 | **export omits a printed row** (restored #12) |
| SMR oxygen | 0.31 kg to air | 0.31 "Oxygen" (air) | 0.31, built to *water* | module compartment |
| SMR water to air | 2.93 kg | 2.93 "Water" (air) | 2.93 as "Water, in air" (resource) | module flow |
| SMR concrete / steel / cast iron | 6.60e-6 m³ / 5.06e-3 kg / 6.18e-5 kg | same | same | — |
| SMR aluminium | 4.17e-5 kg, market for aluminium, cast alloy | 4.17e-5, primary cast alloy slab | same as export | dataset (immaterial) |
| SMR steam turbine | 7.90e-10 unit, modelled as gas turbine 10 MW (SI S1) | 7.9e-10 gas turbine 10MW | same | — (paper's own proxy) |
| SMR-CCS gas | 5.33 m³ | 5.33 | 5.33 | — |
| SMR-CCS process water / cooling water | 4.68 kg / 1.18 m³ | same | same | — |
| SMR-CCS electricity out | 0.05 kWh | avoided 0.05 | −0.05 | as SMR |
| SMR-CCS wastewater | 1.83e-3 | 0.00183 | 0.00183 | — |
| SMR-CCS CO₂ | 0.99 kg | 0.99 | 0.99 **+ 1.6366 closure** | module adds a row |
| SMR-CCS **nitrogen** | **20.84 kg** | **absent** | 20.84 | **export omits** (restored #12) |
| SMR-CCS oxygen / water | 0.41 / 1.33 | same | same, wrong compartments | module |
| SMR-CCS materials | as SMR | same | same | — |
| CO₂ to CCS | not printed; implied ≈ 8.90 | **8.01** ("UK Carbon Captured and Stored", waste to treatment) | 8.01 | **export derives 8.01 = 9.00 − 0.99, against the paper's own arithmetic** |
| CCS pipeline | 300 km, 14,010 t CO₂ (no "per day", no life) | 2.34666e-9 km (comment "14000 t/day, 25 y") | same | user-derived assumptions |
| CCS transport compression | 0.0171 kWh/kg CO₂ | 0.0171, DE / GB HV | 0.0171 study grid | geography |
| CCS fugitive | 2.320 kg/km/a | 1.36106e-7 kg | same | exact derivation |
| CCS well | 6 × 3,000 m, 7.3 Mt/a | 9.863e-8 m (comment says 7.4 Mt, 25 y) | same | user-derived life |
| CCS injection compressors | 0.007 kWh/kg CO₂ | 0.007 | 0.0070 | geography |
| CCS **diesel** | **15.4 kg/kg CO₂**, product "market group for diesel RER" (SI S1) | **0.0154 kg**, market group for diesel RER | 0.659 MJ **burned** in building machine | **export ÷1000 (stated in its comment); module burns it** |
| MP-E all rows | Table 3 MP-E column | **no export** (UK MP Operation.XLSX is Diab's plasma model) | typed from Table 3; 11/12 rows, carbon dropped | no export to check |

---

## Module rows with no source row

| Row | Amount | Where | What it is | Grade / verdict |
|---|---|---|---|---|
| `co2` closure on SMR | **0.6787 kg** (= 4.85 × 1.99561 − 9.00) | `smr_hermesmann_1kg_h2` biosphere | ADDED (module comment says so). Charges the gap between ecoinvent GB HP gas's carbon (0.7350 kg/m³ × 0.7410 kg C/kg × 44.0095/12.011 = **1.9956** kg CO₂/m³, the module's `GAS_CO2_KG_PER_M3`; the docstring's "1.997" and "9.686" round it slightly high) and the paper's 9.00. +6.0 % on grey (11.31). | DERIVED. The paper never discusses carbon balance (no "balance", "stoichiometr", "closure" or "carbon content" in 28 pages); it takes 9.00 from IEAGHG's simulation [66] with no gas composition. IEAGHG's gas is 9.00/4.85 = **1.856** kg CO₂ per m³ — 7.5 % leaner in carbon than ecoinvent's GB gas. The same gap can be read as a *different gas basis* rather than as unemitted carbon: carbon-matching the gas to 4.51 m³ would move grey by −0.12, not +0.68. Keep, but say the direction is a choice |
| `co2` closure on SMR-CCS | **1.6366 kg** (= 5.33 × 1.99561 − 0.99 − 8.01) | `smr_ccs_hermesmann_1kg_h2` biosphere | ADDED. +31.8 % on blue (5.15); the single largest term after the gas. | DERIVED, **and its premise contradicts the source**. The module comment: "The SMR-CCS route's extra gas raises steam for solvent regeneration and is burned in a flue the inventory's capture does not reach, so the shortfall is emitted, not captured." The paper's 90 % case is **post-combustion MEA absorption from the flue gas** (p.12; Fig. 9 bottom; §4.1.1 "post-combustion capture of CO₂ from the flue gas"), so the flue *is* the capture point and 90 % of all combustion CO₂ passes the absorber. The paper's own numbers close on exactly that: total ∝ gas (9.89), 10 % emitted (0.99), 90 % captured (8.90) — see Table 2 row 16. Three consistent readings and what blue becomes: (a) module as built: 0.99 + 1.637 emitted, 8.01 captured → **5.15**; (b) module's gas basis with 90 % capture: 1.064 emitted, 9.573 captured → 5.154 − 1.563 + 1.563 × 0.0718 = **3.70** (−28 %); (c) paper's basis, no closure, 8.90 captured: 0.99 emitted → 5.154 − 1.637 + 0.89 × 0.0718 = **3.58** (−31 %). (Hermesmann's own 3.97 on the German grid is of the same order.) Decision for the user; at minimum the comment's physical premise should not stand as written |
| GB study grid in place of the ecoinvent HV market | −1.1, −0.05, 0.0171 + 0.0070 (×8.01), 10.29 kWh | all four activities | SUBSTITUTED dataset: paper/SI DE HV market (ecoinvent 3.6); UK exports GB HV market (3.9.1); module `gb_grid_2025_hv_delivered` (GRID_DB), 141.87 g/kWh | Study decision, stated in `electricity_hv_gb`'s `why` and `gb_grid.py`. Amounts untouched. Biggest effect on MP-E (1.46 kg CO₂e; at the paper's 0.636 kg/kWh DE grid it was 6.52) |
| Diesel burned in building machine | 0.659 MJ per kg CO₂ | `ccs_hermesmann_1kg_co2` | SUBSTITUTED dataset for the paper's/export's "market group for diesel" product row | Study decision (module comment). Adds combustion the source did not score: 0.526 kg CO₂e per kg H₂ |
| Gas on the GB HP market | 4.85 / 5.33 / 5.72 m³ | all three H₂ routes | Geography DE → GB (the UK exports already did this) | Fine; the study is GB |
| "Carbon dioxide, fossil" | 9.0 / 0.99 / 1.36e-7 | — | Export's unspecified "Carbon dioxide" made fossil | Correct specification, same GWP |
| MP-E `location="DE"` | — | `mp_e_1kg_h2` | Label only; all links are GB | Cosmetic |
| Oxygen to water; "Water, in air" resource | 0.31/0.41; 2.93/1.33 | SMR, SMR-CCS | Wrong compartments, carried "as built", self-flagged | Zero GWP; fix before any non-GWP category (module says the same) |

---

## Parameters

| Parameter | Paper | Export | Module | Verdict |
|---|---|---|---|---|
| CO₂ captured per kg H₂ (`CO2_CAPTURED_PER_KG_H2`) | not printed; implied **8.90** (0.99 = 10 % of 9.00 × 5.33/4.85; Table 7 electricity line) | 8.01 (= 9.00 − 0.99) | **8.01** | IN-DIFFERS by 0.89 kg (−10 %). Alone: +0.064 kg CO₂e/kg H₂ if corrected. Matters through the closure (above) |
| Nitrogen to air | Table 2: **16.41 / 17.91 / 20.84** (SMR / 56 % / 90 %) | absent | **16.41 / 20.84** | IN, exact, right columns. Zero GWP |
| Gas, SMR / SMR-CCS (`SMR_GAS_M3`, `SMR_CCS_GAS_M3`) | **4.85 / 5.33** m³ | 4.85 / 5.33 | 4.85 / 5.33 | IN |
| CO₂ emitted, SMR / SMR-CCS (`SMR_CO2_EMITTED`, `SMR_CCS_CO2_EMITTED`) | **9.00 / 0.99** kg | 9 / 0.99 | 9.0 / 0.99 | IN. Paper calls them "process-related GHG emissions" (§4.1.1: SMR 9.00 = 77.75 %; SMR-CCS (90 %) 0.99 = 24.9 % of 3.97) |
| Gas carbon basis (`GAS_KG_PER_M3` 0.7350, `GAS_FOSSIL_C_PER_KG` 0.7410) | none given; IEAGHG implies 1.856 kg CO₂/m³ | — | ecoinvent GB HP gas properties → **1.9956** kg CO₂/m³ | ADDED basis; the docstring's "1.997" / "9.686" / "10.645" are the same quantities rounded high (exact: 1.9956, 9.679, 10.637; the built map carries the exact 0.6787 and 1.6366) |
| Diesel, well drilling (`CCS_DIESEL_KG_PER_KG_CO2`) | p.13, verbatim: *"The injection wells are driven by diesel fuel with 15.4 kg diesel/kg CO₂ according to Verma et al [39]."* ([39] = Verma & Kumar 2015, LCA of hydrogen from underground coal gasification, Appl. Energy 147:556–68). SI S1: product "Market group for diesel RER, kg" | 0.0154 kg, comment "15.4kg per T of CO2 (not 15.4kg per kg like in the paper, too high)" | **0.0154** kg → 0.659 MJ burned | **S4 confirmed as a deliberate ÷1000, and the paper's own totals settle which reading the authors can have modelled.** Per kg: 15.4 × 8.9 = 137 kg diesel per kg H₂ ≈ 75 kg CO₂e unburned, ~530 burned — against the paper's blue total of 3.97: impossible. Per tonne: 0.137 kg diesel ≈ 0.07 kg CO₂e even unburned (3.6 cut-off market group ≈ 0.5 kg/kg) — yet Table 7 puts the **entire** SMR-CCS (90 %) "Plant manufacturing" line, the only line the CCS infrastructure can sit in, at **0.03** (SMR: 0.01). So the paper did not score even the per-tonne reading at the diesel's full upstream burden; whatever it did is below 0.02 kg CO₂e/kg H₂. The module's burned per-tonne row is **0.526 kg CO₂e/kg H₂**, ~25× the paper's whole CCS-infrastructure contribution. Defensible as physics, but it is the module's number, not Hermesmann's |
| Diesel LHV (`DIESEL_MJ_PER_KG`) | — | — | 42.8 MJ/kg (ecoinvent) | Fine |
| Solid carbon, MP-E | Table 3: **3.00** kg per kg H₂; credit −5.62 kg CO₂e (Table 7); withdrawn p.18 | — (no export) | no row | Stated decision; coincides with the paper's §4.2 treatment |
| MP-E electricity | Table 3: **10.29** kWh (95 % electric-heating efficiency, p.13) | — | 10.29 kWh | IN. Paper's Table 7 scores it 6.52 at the 2017 DE grid; the module 1.46 at the 2025 GB study grid |
| MP-E gas | **5.72** m³ (feedstock only, same as MP-C) | — | 5.72 | IN. 5.72 × 36.6 MJ/Nm³ (the paper's LHV, p.13) = 58.2 kWh, consistent with SOURCES.md's "62.8 kWh gas" on HHV |
| Pipeline / well lives | plant 20 y (p.11–12); pipeline and well life not stated | 25 y | 25 y | User assumption; immaterial (0.0027 kg CO₂e/kg CO₂ for both together) |
| Functional unit pressure | **30 bar** at the production site (§3.1, p.10) | — | — | Not a module parameter, but SOURCES.md's compression table assumes **20 bar** for grey/blue/turquoise and says "The Hermesmann inventories … state no pressure". The paper does state it. At 30 bar the fossil colours' trailer-compression term falls from 1.450 to ≈ 1.19 kWh/kg (green's figure) — about −0.08 kg CO₂e/kg on grey/blue/turquoise |

---

## 21 Oct restore re-checked — #12 nitrogen to air on SMR and SMR-CCS

- Paper Table 2, "Emissions (Air): Nitrogen, kg: 16.41 / 17.91 / 20.84" — verified in the extracted text and on the rendered page image (columns SMR / SMR-CCS (56%) / SMR-CCS (90%)).
- Module: `("nitrogen_air", 16.41, _kg, ...)` on SMR (line 426) and `("nitrogen_air", 20.84, _kg, ...)` on SMR-CCS (line 453) — the right two columns. Flow pinned as `("Nitrogen", ("air",))`; `common.resolve_flow` matches name and categories exactly, so the build would fail rather than silently swap.
- Built: `lca_map.json` (2026-10-22 13:40, HEAD 1c99ab0) shows both rows with contribution **0.0** — zero GWP confirmed, as SOURCE_DIFF #12 said.
- Provenance: absent from all four SMR/SMR-CCS exports (DE and UK), so the restore came from the paper, not from SimaPro. `git log -S nitrogen_air` puts it in commit 1c99ab0 (dated 2026-10-22, "Checkpoint before the LCA assurance work"); SOURCE_DIFF lists it under "Implemented, 21 Oct 2026". Consistent (work 21 Oct, committed 22 Oct).
- Not restored, and not needed: the 56 % column's 17.91 (that configuration is not modelled).

Verdict: #12 correctly restored; nothing further.

---

## Claims to check

**1. "SMR and SMR-CCS carry a small *avoided* electricity credit (negative kWh) as the source does" (hydrogen.py docstring).**
TRUE to the source, and the source is explicit that it *is* a by-product credit: Table 2 "Output flows: Electricity 1.10 / 0.05 kWh"; §3.1.1 "environmental credits were assigned to SMR for electricity generated from excess steam"; §3.2.2 "this electricity was included as avoided burden"; Table 7 lists it under **"By-products: Excess electricity −0.70 / −0.11 / −0.03"**; p.18 keeps it ("electricity is an easily usable by-product and energy recovery from excess steam is already common practice") while dropping the carbon and oxygen credits.
In the module: −1.1 kWh × 141.87 g = **−0.156 kg CO₂e/kg** on grey (1.4 % of 11.31); −0.05 kWh = **−0.007** on blue.
**But this contradicts ASSUMPTIONS §5**: "No credits anywhere; co-products carry no burden away … The one case in the inventories is methane pyrolysis." The SMR steam-turbine electricity is a second case, and the paper itself books it as a by-product credit. Two consistent options: (a) delete the two negative rows (grey +0.156, blue +0.007; §5 then true as written), or (b) keep them and amend §5 to state the exception and Hermesmann's p.18 reason. As it stands the module and the docstring are right about the source and §5 is wrong about the module. Note in passing that the module's combination (electricity credit kept, carbon credit dropped) is exactly the paper's own §4.2 convention, i.e. the basis of its country-specific table (Germany SMR 10.87 = 11.57 − 0.70; MP-E 9.91, uncredited).

**2. "The SimaPro exports of Hermesmann are the user's own project" (SOURCE_DIFF).**
TRUE. Every file header reads "SimaPro 10.3.0.1 | process | Project HyPT", process identifiers `IMPERIAL000111709500148/149/152/155/157/158/159`, created 27/03/2026 (SMR, SMR-CCS), 09/04/2026 (CCS), 05/01/2026 (MP Diab), exported 1–3 June 2026; products are named "Hydrogen (SMR Hermesmann)" and "Carbon Captured and Stored (hermesman and muller)"; comments are the user's working notes ("not 15.4kg per kg like in the paper, too high"); the datasets are ecoinvent **3.9.1 APOS** where the paper used **3.6 cut-off** (SI S1). They are the user's transcription of Table 2 and §3.2.3 — faithful on every printed amount except the omitted nitrogen rows, the derived 8.01, and the ÷1000 diesel — and there is no export at all of Table 3 (MP-E). The module's docstring ("Inventories recreated from the study's own SimaPro project") should say so.

**3. The carbon-balance shortfall — does the paper comment on CO₂ closure?**
**No.** Nothing in 28 pages on mass or carbon balance, stoichiometry or gas composition; §4.1.1 and Table 7 take 9.00 / 4.12 / 0.99 as "process-related emission" straight from IEAGHG 2017 [66]. Two things the paper *does* give bear on the module's closure block: (i) the SMR-CCS case the module uses is post-combustion flue-gas capture (p.12, Fig. 9), which contradicts the closure comment's premise that the extra fuel is burned in a flue the capture does not reach; (ii) the paper's own numbers close under "total CO₂ ∝ gas, capture rate applied to the total" (SMR 9.00; SMR-CCS 9.89 → 0.99 emitted / 8.90 captured; 56 %: 9.30 → 4.12 emitted / 5.18 captured; Table 7's CCS electricity lines agree with 8.9 and 5.2 kg captured). The shortfall the module sees (SMR 0.68, SMR-CCS 1.64 kg) is the difference between ecoinvent's GB gas (1.996 kg CO₂/m³) and IEAGHG's gas (1.856 kg CO₂/m³), applied to the SMR-CCS case without its 90 % capture. Numbers in *Module rows with no source row*.

**4. Extra: SOURCES.md says the Hermesmann inventories "state no pressure".** The paper's functional unit is "1 kg H₂ at 30 bar … at the production site" (§3.1). See *Parameters*, last row.

**5. Extra: `palladium` "immaterial".** 8.45e-6 kg scores 0.102 kg CO₂e, 2.6 % of MP-E, on a dataset that is not the paper's "market for palladium". Re-pin and re-score before calling it immaterial.

---

## Summary

Counts (dispositions as defined in the brief; "IN" means the printed amount is carried, whatever dataset it is linked to):

| Block | Rows | IN | IN-DIFFERS | SUBSTITUTED | NOT-APPLICABLE | BOUNDARY | MISSING | ADDED (module only) |
|---|---|---|---|---|---|---|---|---|
| Table 2 SMR | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 1 (CO₂ closure 0.679) |
| Table 2 SMR-CCS | 15 printed + 1 implied | 15 | 1 (captured CO₂ 8.01 vs ≈ 8.90) | 0 | 0 | 0 | 0 | 1 (CO₂ closure 1.637) |
| §3.2.3 CCS | 6 | 5 (4 user-derived) | 1 (diesel 15.4 → 0.0154, also dataset-substituted) | — | 0 | 0 | 0 | 0 |
| Table 3 MP-E | 12 | 11 | 0 | 1 (carbon credit → none, stated) | — | 0 | 0 | 0 |
| **Total** | **49** | **46** | **2** | **1** | 0 | 0 | **0** | **2** |

Dataset relinks that keep the amount (study grid for all electricity, GB gas, diesel burned) are listed under *Module rows with no source row*, not counted as substitutions of source rows.

Most important findings, in order:

1. **The SMR-CCS carbon-closure row (1.637 kg CO₂, 32 % of blue) rests on a premise the paper contradicts.** The 90 % case is post-combustion capture *from the flue gas*; the paper's own numbers imply 8.90 kg captured (not 8.01) and close without any shortfall. Applying the module's own gas-carbon basis *with* the source's 90 % capture gives blue ≈ 3.70 kg CO₂e/kg instead of 5.15; taking the paper's basis unchanged gives ≈ 3.58. The SMR closure (0.679 kg, 6 % of grey) is the same gas-basis difference and the paper is silent on it either way; it is a defensible choice but should be stated as one, and the docstring's 1.997 / 9.686 / 10.645 should be the exact 1.9956 / 9.679 / 10.637.
2. **The avoided-electricity credit (−1.1 / −0.05 kWh) is the paper's by-product credit and contradicts ASSUMPTIONS §5's "no credits anywhere".** Size −0.156 kg on grey, −0.007 on blue. Either drop it or write the exception into §5; the docstring's claim about the source is correct.
3. **S4 diesel:** the per-kg reading is excluded by the paper's own totals; the per-tonne reading is at least what the authors meant, but the paper's Table 7 shows they scored the whole CCS infrastructure at 0.02 kg CO₂e/kg H₂, whereas the module's burned per-tonne diesel is 0.526 kg/kg (10 % of blue, 91 % of the CCS activity). Keep, but grade it as the module's number, not Hermesmann's.
4. **`UK MP Operation.XLSX` is not Hermesmann's MP-E** (it is a Diab plasma-pyrolysis model with 4.26 kg carbon black on mass allocation). The module's MP-E was typed from Table 3 and matches it on all 11 kept rows; SOURCE_DIFF D1(b) points at the wrong inventory, and mass allocation on Hermesmann's own 3.00 kg would leave 25 % of the burden on hydrogen. The no-credit decision coincides with the paper's own p.18 treatment, which SOURCE_DIFF S2 does not mention.
5. **#12 nitrogen is correctly restored** (16.41 / 20.84, the SMR and 90 % columns; zero GWP; absent from every export).
6. Small: captured CO₂ 8.01 should be ≈ 8.90 on the paper's arithmetic (+0.064 kg/kg alone); palladium is 2.6 % of MP-E on a non-market dataset; the paper's FU is 30 bar, not "no pressure"; pipeline/well lives (25 y) and "14,010 t per day" are the user's assumptions, immaterial; aluminium and tap-water datasets differ from SI S1, immaterial.
