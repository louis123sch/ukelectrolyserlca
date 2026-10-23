# Fuel cell — Usai 2021 and Babatunde 2024 row ledger (22 Oct 2026)

Read-only re-read of the two sources against `optimiser_lca/fuel_cell.py`, plus
`optimiser_lca/validate.py` (PAPER_TABLE3/4/5), `docs/SOURCE_DIFF.md` (Clean
table, Missing #2, the extrusion-film claim, "Still unsourced") and
`optimisation/SOURCES.md` lines 974–1046. Where a claim depends on ecoinvent
rather than on a document, it was checked against the user's Brightway project
`hydrogen-smr`, database `ecoinvent-3.9.1-apos`, method IPCC 2021 GWP100 (read
only; no database or repository file was touched).

## Files read, and what each turned out to be

| File | What it is | Used for |
|---|---|---|
| `…\sources\usai supplementary materials\usai 2021 fc lci per kw.pdf` (18 pp.) | Usai et al. 2021 Supporting Information: Table 1 BoP (pp. 1–3), Tables 2–7 tank/GDL/catalyst/BPP/membrane/other-stack, Tables 8–10 development scenarios, references | Table 1, the BoP preamble ("four different components, with a total weight of 59 kg"; "global average productions"; "final assembly would be in Europe") |
| `…\usai 2021 fc results by component.xlsx` | Two sheets. `Dpro matrices`: ReCiPe Midpoint (H) v1.13 per component for the Reference case and Development scenarios 1–2, per 80 kW system; `Sensitivity Analysis`: +10 % per component | GWP100: BoP 854.054169 kg CO2e; air 71.88, water 252.11, heat 138.56, fuel 59.43, controller 122.12, other 209.95; tanks 1,958.57; d_tot 4,966.97 |
| `…\data centre reading\fuel cell\hydrogen-3005656-supplementary.pdf` (7 pp.) | Babatunde et al. 2024 SI: Table S1 (p. 2), S2–S4 Monte Carlo (pp. 3–7) | Table S1 row by row; S2–S4 for the 2× check |
| `…\data centre reading\fuel cell\hydrogen-05-00020.pdf` (22 pp.) | **Confirmed the paper**: Babatunde, Akintayo, Emezirinwune, Olanrewaju, *Hydrogen* 2024, 5, 352–373, doi 10.3390/hydrogen5020020 | §3.4 scope and 32,000 h; Table 3 (p. 361), Tables 4–5 (p. 366), §4.6 text, Fig. 4/8 |
| `…\data centre reading\fuel cell\1-s2.0-S0360319922032505-main.pdf` (13 pp.) | **Not Gramc, not Bionaz.** Gandiglio, Marocco, Bianco, Lovera, Blengini, Santarelli (2022), "Life cycle assessment of a renewable energy system with hydrogen-battery storage for a remote off-grid community", *IJHE* 47, 32822–32834, doi 10.1016/j.ijhydene.2022.07.199 — the Ginostra study the module and SOURCES.md cite for the 5-year fuel-cell replacement and the 28 bar tank | Table 5 fuel-cell row; lifetime statements. No Gramc 2025 or Bionaz 2022 document is held in this folder, so `GRAMC_STACK` is **not checked** by this ledger |

## Usai SI Table 1 → `pemfc_bop_stationary_1kw`

Reference flow printed: "per kW net". The table has **26 printed rows** (25 with
a non-zero amount plus the "Sulfur trioxide 0.00" row), not the 25 that
SOURCE_DIFF's Clean table counts. Process names are Usai's ecoinvent 3.6
names; the module's `identity` is given where it differs.

| # | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| **Air management** | | | | | | |
| 1 | Chromium steel², Compression Expansion motor — `market for steel, chromium steel 18/8, hot rolled/GLO` | 0.02 | kg | `steel_chromium_188` 0.02 | IN | |
| 2 | Aluminium², Compression Expansion motor — `market for aluminium, cast alloy/GLO` | 0.04 | kg | `bop_al_cast` 0.04 | IN | |
| 3 | Low alloyed steel², Compression Expansion motor — `market for steel, low-alloyed, hot rolled/GLO` | 0.01 | kg | `bop_steel_la_hr` 0.01 | IN | |
| 4 | Permanent magnet², Compression Expansion motor — `permanent magnet production, for electric motor/GLO` | 0.01 | kg | `bop_magnet` 0.01 | IN | production dataset, as Usai |
| 5 | Air filter³ — `market for air filter, in exhaust air valve/GLO/unit` | 0.013 | pc | `bop_air_filter` 0.013 unit | IN | ecoinvent filter = 0.084 kg |
| 6 | Tetrafluoroethylene³, Air ducting — `market for tetrafluoroethylene/GLO` | 0.001 | kg | `tetrafluoroethylene` 0.001 | IN | |
| 7 | Plastic pipes³ — `market for extrusion, plastic pipes/GLO` | 0.03 | kg | `bop_extrusion_pipes` 0.03 | IN | Usai's row is the extrusion service only; no pipe polymer row exists in the source either |
| 8 | Electronics⁴, Mass flow sensor — `market for electronics, for control units/GLO` | 0.004 | kg | `bop_electronics` 0.004 | IN | |
| **Water management** | | | | | | |
| 9 | Polyphenylene sulfide^{1,2}, Humidifier housing — `market for polyphenylene sulfide/GLO` | 0.01 | kg | `bop_pps` 0.01 | IN | |
| 10 | Sulfur trioxide⁵, Nafion tubes — `market for sulfur trioxide/GLO` | 0.00 | kg | `bop_so3` 0.0 | IN (SUBSTITUTED location) | Printed 0.00, carried at 0.0. Module takes the RoW market "where Usai's 3.6 GLO market is regional in 3.9.1" (module comment lines 269–271); location not re-verified here, amount is zero anyway |
| 11 | Tetrafluoroethylene^{5,6}, Nafion tubes — `market for tetrafluoroethylene/GLO` | 0.01 | kg | `tetrafluoroethylene` 0.01 | IN | |
| 12 | Extrusion of plastic, Nafion tubes — `extrusion production, plastic film/RER/kg` | 0.01 | kg | `bop_extrusion_film` 0.01 | SUBSTITUTED (process) | Usai name the **RER production** dataset; module takes `market for extrusion, plastic film` GLO (stated in `why`, lines 301–302). 3.9.1 apos holds `extrusion, plastic film` RER / RoW / CA-QC and the GLO market. Immaterial at 0.01 kg |
| 13 | Aluminium⁷, Air precooler — `market for aluminium, wrought alloy/GLO` | 0.08825 | kg | `aluminium_wrought` 0.08825 | IN | |
| 14 | Polyurethane, Proxy for cordierite — `market for polyurethane, rigid foam/GLO` | 0.019 | kg | `bop_pu_rigid` 0.019 | IN (SUBSTITUTED location) | GLO → RoW, module's stated reason as row 10 |
| 15 | Nylon 6, Demister — `market for nylon 6/GLO` | 0.03 | kg | `bop_nylon6` 0.03 | IN (SUBSTITUTED location) | GLO → RoW, as row 10 |
| **Heat management** | | | | | | |
| 16 | High density polyethylene¹, Fan — `market for polyethylene, high density, granulate/GLO` | 0.01 | kg | `bop_hdpe` 0.01 | IN | |
| 17 | 40W pump, Coolant pump — `market for pump, 40W/GLO/unit` | **3** | pc | `bop_pump_40w` **0.0375** (= 3/80) | IN-DIFFERS | Printed under "per kW net"; module reads it as per 80 kW system. Evidence in *Claims* below |
| 18 | Aluminum¹, Radiators — `market for aluminium, cast alloy/GLO` | 0.01 | kg | `bop_al_cast` 0.01 | IN | |
| 19 | Ethylene glycol, Antifreeze — `market for ethylene glycol/GLO` | 0.01 | kg | `bop_ethylene_glycol` 0.01 | IN | |
| **Fuel management** | | | | | | |
| 20 | Low alloyed steel², Blower — `market for steel, low-alloyed, hot rolled/GLO` | 0.06 | kg | `bop_steel_la_hr` 0.06 | IN | |
| 21 | Chromium steel², Blower — `market for steel, chromium steel 18/8, hot rolled/GLO` | 0.02 | kg | `steel_chromium_188` 0.02 | IN | |
| 22 | Aluminum^{1,2}, Blower, ejectors, pipes — `market for aluminium, wrought alloy/GLO` | 0.03 | kg | `aluminium_wrought` 0.03 | IN | |
| **Other BoP** | | | | | | |
| 23 | Electronics⁴, Controller — `market for electronics, for control units/GLO` | 0.03 | kg | `bop_electronics` 0.03 | IN | |
| 24 | Cables⁴, Wiring — `market for cable, three-conductor cable/GLO/m` | **16** | m | `bop_cable` **0.2** m (= 16/80) | IN-DIFFERS | Printed under "per kW net"; module reads per system. Superscript 4 = Miotti et al. 2015 |
| 25 | Aluminium, Mounting belly pan — `market for aluminium, wrought alloy/GLO` | 0.10 | kg | `aluminium_wrought` 0.10 | IN | module labels it "the module frame here" |
| 26 | Low alloyed steel, Fasteners — `market for steel, low-alloyed, hot rolled/GLO` | 0.013 | kg | `bop_steel_la_hr` 0.013 | IN | |

Nothing in Table 1 is outside the boundary: no end-of-life, no delivery
transport, no genset. Usai's Table 1 carries **no electricity, heat or transport
row at all** (see *Claims*). The SI preamble's "four different components" does
not match the table's five groups (air, water, heat, fuel, other); nothing turns
on it.

## Babatunde Table S1 → `pemfc_stack_1kw_babatunde`

**Reference product confirmed.** Table S1 (SI p. 2) is captioned "Ecoinvent
3.7.1 dataset documentation f fuel cell production, stack polymer electrolyte
membrane, 1kW", but its first line reads *Reference products: Fuel cell, stack
polymer electrolyte membrane, 2kW electrical, future — 1 unit*. The paper's
functional unit is 1 kW (§3.4, p. 360: "The functional unit for the LCA is in
kW"; title). `FC_KW_SCALE = 0.5` is therefore right.

**The 1.8786 factor confirmed.** The live dataset (3.9.1 apos, RoW) was listed
exchange by exchange; the column "3.9.1 ÷ printed" below is that ratio. It is
1.878606 on every row where the printed amount is not rounded; the two
exceptions are rounding of the printed figure (6.6 for 6.608, 22.3 for 22.325).
The module's `FC_S1_SCALE = 1.878606235` is exactly this ratio. Three
independent totals agree that the paper's own results sit on the live amounts,
not the printed ones: the paper's S2 Monte Carlo mean for global warming is
193.47 kg CO2e (ReCiPe 2016, per unit of the 2 kW dataset); the 3.9.1 dataset
scores 194.96 kg CO2e per unit (IPCC 2021 GWP100, CH variant 172.06); and
Gandiglio 2022 (ecoinvent 3.7, EF 3.0) carries 2.91e-5 unit/kWh of the same
dataset contributing 0.006 kg CO2e/kWh, i.e. about 206 kg per unit. The printed
table at face value would give about 104 kg per unit. Module amounts are
"verbatim" (as printed) and scaled once at write time by 0.5 × 1.878606235 =
0.939303118.

| # | Source row (as printed) | Amount | Unit | Module (key, amount, verbatim) | 3.9.1 ÷ printed | Disposition | Note |
|---|---|---|---|---|---|---|---|
| **By-products** | | | | | | | |
| 1 | Waste plastic, industrial electronics | 6.6 | kg | `waste_plastic` −6.6 | 1.8809 (12.41383 / 6.6; printed is 6.608 rounded) | IN | Negative technosphere input of the waste market: ecoinvent's own sign (−12.41383 in 3.9.1). Manufacturing scrap, inside cradle-to-gate |
| 2 | Waste polyvinylfluoride | 0.052 | kg | `waste_pvf` −0.052 | 1.8786 | IN | as above (−0.0976875 in 3.9.1) |
| **Inputs from technosphere** | | | | | | | |
| 3 | Activated carbon, granular | 0.0008 | kg | `activated_carbon` 0.0008 | 1.878606 | IN | |
| 4 | Aluminium, wrought alloy | 0.3 | kg | `aluminium_wrought` 0.3 | 1.878606 | IN | |
| 5 | Building, hall, steel construction | 0.00022 | m² | `building_hall` 0.00022 m² | 1.878606 | IN | factory infrastructure, in scope |
| 6 | Building, multi-storey | 0.0013 | m³ | `building_multi` 0.0013 m³ | 1.878606 | IN | |
| 7 | Electricity, medium voltage | 16.9 | kWh | `electricity_mv` 16.9 | 1.878606 (sum of 8 regional markets 31.7484 kWh) | IN (SUBSTITUTED aggregation) | Dataset splits it RNA 6.011, RLA 1.876, NZ 0.056, AU 0.285, Europe w/o CH 4.095, RAS 17.209, RU 1.276, RAF 0.941; module uses the GLO market group, stated in `why` (lines 230–231). Factory energy, in scope |
| 8 | Glass fibre | 0.1 | kg | `glass_fibre` 0.1 | 1.878606 | IN | |
| 9 | Graphite | 4.5 | kg | `graphite` 4.5 | 1.878606 | IN | |
| 10 | Heat, district or industrial, natural gas | 22.3 | MJ | `heat_natural_gas` 22.3 | 1.8807 (sum of 3 markets 41.9399 MJ; printed is 22.325 rounded) | IN (SUBSTITUTED aggregation) | Europe w/o CH 11.177, RoW 30.265, CA-QC 0.497; GLO market group used, stated in `why` (line 242) |
| 11 | Isopropanol | 0.0095 | kg | `isopropanol` 0.0095 (RoW) | 1.878606 | IN | dataset uses RoW market too |
| 12 | Phenolic resin | 1.1 | kg | `phenolic_resin` 1.1 (RoW) | 1.878606 | IN | |
| 13 | Platinum | 0.00075 | kg | `platinum` 0.00075 | 1.878606 | IN | |
| 14 | Steel, chromium steel 18/8, hot rolled | 0.1 | kg | `steel_chromium_188` 0.1 | 1.878606 | IN | |
| 15 | Tetrafluoroethylene | 0.052 | kg | `tetrafluoroethylene` 0.052 | 1.878606 | IN | |
| 16 | Water, deionised | 0.006 | kg | `water_deionised` 0.006 (RoW) | 1.878606 (0.002654 Europe w/o CH + 0.008617 RoW) | IN | single RoW market for the two regional ones; immaterial |
| **Inputs from environment** | | | | | | | |
| 17 | Occupation, industrial area | 0.0395 | m²/year | `occupation_industrial` 0.0395 m²·a | 1.878606 | IN | |
| 18 | Transformation, from unspecified | 0.0008 | m² | `transformation_from` 0.0008 | 1.878606 | IN | |
| 19 | Transformation, to industrial area | 0.0008 | m² | `transformation_to` 0.0008 | 1.878606 | IN | |
| **Emissions to air** | | | | | | | |
| 20 | Propanol | 0.0095 | kg | `propanol_air` 0.0095 | 1.878606 | IN | dataset's flow is Propanol (air, urban air close to ground) — the module's compartment choice matches |
| 21 | Water | 9 × 10⁻⁷ | m³ | `water_air` 9e-7 | 1.878606 | IN | |
| **Emissions to water** | | | | | | | |
| 22 | Water | 5.1 × 10⁻⁶ | m³ | `water_water` 5.1e-6 | 1.878606 | IN | |

Nothing in Table S1 is a boundary item: no end-of-life row, no delivery row.
The paper's §3.4 scope text names "transportation ... and the distribution of
the product" and "the balance of plant components", but the only inventory it
publishes is this stack dataset; its transport is whatever ecoinvent's markets
carry upstream of the factory gate (Fig. 4/8: about 1 %). The module's
treatment — stack only, manufacturing only — is the right reading of the paper.

## Module rows with no source row

| Activity | Row | Amount | Grade | Note |
|---|---|---|---|---|
| BOP | `inverter_500kw` | 1/500 = 0.002 unit per kW | ASSUMED (dataset choice, 1:1 kW rating) | No source in the held documents; ecoinvent `market for inverter, 500kW` GLO, the same dataset as the battery's power term. Usai's vehicle system has no inverter |
| BOP | container share (`BESS_PARTS["container"]`) | 1/1,000 = 0.001 unit per kW | ASSUMED, stated as such in the code and SOURCES.md | No source states MW per container for fuel cells. Since 21 Oct the container carries Jasper's 43.9 t concrete block (SOURCE_DIFF #2), so the fuel cell inherits a pad |
| SERVICE | `bop_air_filter` | 0.013 unit per kW per service | amount TRANSCRIBED (Usai row 5), event ASSUMED | 0.013/kW is one filter per 80 kW system; a "service" replaces it once |
| SERVICE | `bop_ethylene_glycol` | 0.01 kg per kW per service | amount TRANSCRIBED (Usai row 19), event ASSUMED | 0.8 kg antifreeze per 80 kW system — Usai's whole coolant charge |
| SERVICE | interval | every 8,000 h | ASSUMED (code says so; Battelle 2016 not held) | nothing in Usai, Babatunde or Gandiglio gives a service interval |
| OPERATION | hydrogen | 1/(0.475 × 33.33) = 0.063158 kg/kWh | DERIVED from assumed efficiency | not in any held document |
| OPERATION | stack | 1/30,000 = 3.333e-5 unit/kWh | DERIVED | lifetime discussed below |
| OPERATION | balance of plant | 1/80,000 = 1.25e-5 unit/kWh | DERIVED | |
| OPERATION | service | 1/8,000 = 1.25e-4 unit/kWh | DERIVED | |
| GRAMC_STACK | 15 technosphere + 1 biosphere rows, ×1/48 | — | NOT CHECKED | Gramc et al. 2025 is not among the files in this folder (the third PDF is Gandiglio 2022) |

## Parameters — every TRANSCRIBED constant against the documents

| Constant | Module | What the documents say | Verdict |
|---|---|---|---|
| `FC_KW_SCALE` | 0.5 | Table S1 reference product "2kW electrical, future — 1 unit"; paper FU 1 kW. S2–S4 are per unit of the 2 kW dataset: S2 mean ÷ Table 3 = 2.003 (GW), 1.993 (fossil), 2.006 (freshwater ecotox), 2.005 (marine ecotox), 2.004 (mineral), 1.997 (terr. acid.), 1.955 (human non-carc.), 2.03 (ionising); water consumption 4.16 (its CV is 1,063 %); S4 damage means 1.995 / 2.01 / 1.997 | **Confirmed.** The docstring's "every value in its Tables S2–S4 is *exactly* 2×" overstates: they are Monte Carlo means, 1.95–2.03× (water 4.2×). The paper itself mixes bases: §4.6 (p. 364) says "about 193.16 kg of CO2 eq ... for every 1 kW", the 2 kW-unit figure, while Table 3 says 96.5796 and the same paragraph's "CO2 contributes 82.77 kg, 85.7 %" resolves to 96.58 |
| `FC_S1_SCALE` | 1.878606235 | Not derivable from the paper; verified above against 3.9.1 apos on all 22 rows (1.878606), and corroborated by the three totals (paper S2 193.47; ecoinvent 194.96; Gandiglio ≈206 per unit) | **Confirmed** |
| `FC_RATED_POWER_KW` | 1.0 | Babatunde's FU | Confirmed |
| `FC_H2_LHV_KWH_PER_KG` | 33.33 | physical constant (120 MJ/kg) | n/a |
| `FC_ETA_NET_BOL` | 0.50 | **Not in any held document.** Usai SI: none (cradle-to-gate manufacture). Babatunde: none ("nothing operational is inventoried", true). Gandiglio: fuel-cell specifications are in its Supplementary data, not held; the paper gives only energy flows (fuel cell covers 2.40 MWh/yr from 8.44 MWh/yr to the electrolyser) | Literature value as the docstring says; its cited sources (DOE, the ~51.6 % 1 kW unit) are not in this folder |
| `FC_DEGRADATION_DERATE` | 0.95 | Not in any held document (Stropnik 2022 not held) | Unverified here |
| `FC_STACK_LIFETIME_H` | 30,000 | Babatunde §3.4 p. 360: "The PEMFC is expected to have 32,000 operating hours during its lifetime (6 years if continuously operated)". This is the ecoinvent dataset comment verbatim — 3.9.1's `fuel cell production, stack polymer electrolyte membrane, 2kW electrical, future` reads "Life time operation is 6 years or 32'000 h" — so **SOURCES.md's "Babatunde's 32k was ecoinvent's own figure" is confirmed**. (32,000 h continuous is 3.65 years; ecoinvent's "6 years" implies ~60 % duty, and the paper's "if continuously operated" is its own slip.) Gandiglio Table 5: 5-year calendar replacement of the 50 kW Engie-EPS unit, "1 fuel cell (50 kW) + 4 replacements" over 25 years, inventoried as 25 units of the 2 kW stack dataset per 50 kW. Nedstack and Bionaz are not held | 30,000 h is the module's own choice (Nedstack); the held sources give 32,000 h (ecoinvent via Babatunde) and 5 calendar years (Gandiglio) |
| `FC_SYSTEM_LIFETIME_H` | 80,000 | 3.9.1's `fuel cell production, polymer electrolyte membrane, 2kW electrical, future` comment: "Life time operation is 15 years or 80'000 h" | **Confirmed** as "ecoinvent's own system life"; DOE not held |
| `FC_SERVICE_INTERVAL_H` | 8,000 | nothing in the held documents | ASSUMED, as labelled |
| `USAI_SYSTEM_KW` | 80 | **The SI never prints "80 kW"**: Table 1 is "per kW net" and the preamble gives "a total weight of 59 kg". The rating is from the paper (not held), corroborated by Babatunde p. 354 citing Usai: "5-ton CO2-eq is released ... when an FC with a net power output of 80 kW is manufactured", and by the workbook's d_tot 4,966.97 kg CO2e per system | Confirmed indirectly |
| `USAI_COOLANT_PUMPS_PER_SYSTEM` | 3 | Table 1: "40W pump, pc, 3, Coolant pump", no reference superscript; the SI note says amounts without a reference are "based on Miotti et al." | As printed. "Per system" is the module's inference (see *Claims*) |
| `USAI_WIRING_M_PER_SYSTEM` | 16.0 | Table 1: "Cables⁴, m, 16, Wiring"; superscript 4 = Miotti, Hofer, Bauer 2015 | As printed; "Miotti's per-system figure" cannot be checked here (Miotti not held) |
| `FC_INVERTER_KW` | 500 | ecoinvent dataset rating; no document | n/a |
| `FC_KW_PER_CONTAINER` | 1,000 | none | ASSUMED, as labelled |
| `GRAMC_STACK_KW` | 48 | Gramc not held | Unverified here |
| Benchmark "Usai 37.3 (no tank)" (docstring line 127, SOURCES.md line 1033) | 37.3 kg CO2e/kW | Workbook: (d_tot 4,966.97 − tanks 1,958.57) / 80 = **37.6** kg CO2e/kW; stack + BoP only (other stack 121.09 + membrane 74.65 + BPP 707.36 + catalyst 1,181.58 + auxiliaries 854.05) / 80 = 36.7 | Off by 0.3; cosmetic |
| "Usai's own 854 kg CO2e/80 kW" (docstring line 106) | 854 | Workbook BoP 854.054169 | Confirmed; the 0.82× rebuild (8.81 × 80 = 705 kg) was not re-scored here |

## Published results — Babatunde Tables 3–5 against `validate.PAPER_TABLE3/4/5`

All 18 + 22 + 3 values were compared; the ten per table below are the spot-check
the brief asked for. **Every one of the 43 values matches the PDF exactly.**

Table 3 (mid-point, paper p. 361): Global warming 96.5796 ✓; Fossil resource
scarcity 22.9546 ✓; Human non-carcinogenic toxicity 1109.94 ✓; Human
carcinogenic toxicity 10.8858 ✓; Terrestrial ecotoxicity 129.522 ✓; Marine
ecotoxicity 44.8299 ✓; Mineral resource scarcity 6.24947 ✓; Terrestrial
acidification 2.61008 ✓; Fine particulate matter formation 0.77385 ✓; Water
consumption 0.47144 ✓ (also Freshwater ecotox 35.132, Freshwater eutroph
0.07111, Ionizing 3.83781, Land use 3.91375, Marine eutroph 0.00322, Ozone HH
0.76387, Ozone TE 0.78174, Strat. ozone 0.00031 ✓).

Table 4 (end-point, paper **p. 366** — `validate.py` line 56 says p. 362):
Fine PM 0.000485875 ✓; Fossil 4.72288595 ✓; GW human health 8.96e-5 ✓; GW
terrestrial 2.70e-7 ✓; Human non-carc 0.000252875 ✓; Mineral 1.44555365 ✓;
Terrestrial acidification 5.53e-7 ✓; Land use 3.47e-8 ✓; Water consumption,
human health 4.94e-7 ✓; Water consumption, aquatic 6.27e-13 ✓ (the other 12
also match).

Table 5 (damage, paper **p. 366** — `validate.py` line 80 says p. 362): Human
health 0.000866 ✓; Ecosystems 1.04e-6 ✓; Resources 6.16844 ✓ (also the
abstract's figures).

The page references for Tables 4 and 5 in `validate.py` are the only
discrepancies; Table 3's "p. 361" is right.

## Claims to check

**1. "Pumps and cable per system (3/80, 16/80), supported by the SI's 59 kg total."**
Two tests, both on ecoinvent 3.9.1 datasets (pump 40W: 1.2 kg cast iron +
0.92 kg chromium steel + 0.25 kg copper + 0.02 kg aluminium + 0.03 kg PVC +
0.007 kg rubber = **2.427 kg/unit**, 9.76 kg CO2e/unit; three-conductor cable:
0.492 kg copper + 0.548 kg HDPE = **1.040 kg/m**, 5.57 kg CO2e/m including the
market's transport; air filter 0.084 kg).

*Mass.* Table 1's kg rows sum to 0.56525 kg per kW = 45.2 kg per 80 kW (air
0.115, water 0.16725, heat 0.03, fuel 0.11, other 0.143); the 1.04 filters add
0.09 kg. Read per system: + 3 × 2.427 + 16 × 1.040 = **69.2 kg** against the
printed 59 kg (+17 %). Read per kW: + 240 × 2.427 + 1,280 × 1.040 = **1,960 kg**,
33× the printed total. So the 59 kg discriminates between the two readings by an
order of magnitude; it is not an exact reconciliation (the per-system sum
overshoots by about 10 kg, within what a different cable or pump mass in Miotti
would explain). "Supported" is fair; "reconciled" would not be.

*Usai's own results.* Heat management is 138.56 kg CO2e per 80 kW in the
workbook. Per-kW pumps give 3 × 9.76 + ~0.1 = 29.4 kg/kW = 2,350 kg per system,
**17.0×** Usai's figure; per system they give 0.0375 × 9.76 + 0.1 = 0.46 kg/kW =
37 kg, 0.27× (the module's "radiator lost to rounding" ratio). "Other components"
is 209.95 kg; per-kW cable alone gives 16 × 5.57 × 80 = 7,134 kg, **34×**, and the
controller rebuilt at 0.03 × 32.27 × 80 = 77.5 kg is 0.63× Usai's 122.12. The
docstring's "17x and 35x over" and "0.27 and 0.63 of Usai" are reproduced.

Verdict: the per-system reading is justified on both grounds; it remains a
correction of the printed table, not a transcription, and should stay flagged as
such (it is, lines 101–104 and 177–179).

**2. "`extrusion, plastic film` exists in 3.9.1."** Usai's row (Table 1, Water
management) reads: *Extrusion of plastic | kg | 0.01 | Nafion tubes |
extrusion production, plastic film/RER/kg*. In 3.9.1 apos the datasets are
`extrusion, plastic film` in RER, RoW and CA-QC plus `market for extrusion,
plastic film` GLO — SOURCE_DIFF line 75 is correct, and the module's current
`why` (lines 301–302) no longer claims absence. What the module does is take the
GLO market where Usai name the RER production dataset: a stated substitution,
0.01 kg, immaterial.

**3. "Usai give no BoP assembly energy."** Confirmed. All 26 rows of Table 1
are materials, parts or forming services (two extrusion rows); there is no
electricity, heat or transport row. By contrast Usai's other tables each carry
energy rows (Table 2 tank: heat 118.66 MJ and electricity 41.13 kWh per kg carbon
fibre, 4.50 kWh per system; Table 3 GDL: 11.20 MJ, 3.88 kWh; Table 4 catalyst:
heat and electricity; Table 6 membrane: heat; Table 7 other stack: electricity on
every component). The SI preamble even says "assuming that the final assembly
would be in Europe, thus with its average energy mix" without a matching BoP row.
A coverage gap of the source, for the cut-off register as SOURCE_DIFF line 84
has it. Babatunde's Table S1, by contrast, does carry factory energy and
buildings (rows 5–7, 10), all in the module.

## Summary

- **Most important:** the stack's 1.878606235 correction — a 1.88× lever on the
  largest fuel-cell term (97.4 t CO2e/MW) — is now verified exchange by exchange
  against ecoinvent 3.9.1 (22/22 rows at 1.878606; the two apparent exceptions
  are rounding of the printed 6.6 and 22.3) and corroborated by three
  independent totals per unit of the 2 kW dataset: the paper's own S2 mean 193.47,
  ecoinvent 194.96, Gandiglio's implied ~206. The 2 kW reference product is
  printed in Table S1 itself. The stack transcription is sound.
- **Usai Table 1:** 26 printed rows (SOURCE_DIFF says 25/25; the "0.00" sulfur
  trioxide row makes 26). IN 20 · SUBSTITUTED 4 (three GLO→RoW markets, one RER
  production→GLO market; all stated in the module) · IN-DIFFERS 2 (pumps 3→0.0375,
  cable 16→0.2, per system) · BOUNDARY 0 · NOT-APPLICABLE 0 · MISSING 0.
- **Babatunde Table S1:** 22 rows. IN 20 · SUBSTITUTED 2 (electricity and heat
  aggregated to GLO market groups, stated) · MISSING 0 · BOUNDARY 0.
- **Module-only rows:** inverter and container (ASSUMED, labelled); two service
  rows (Usai amounts, assumed 8,000 h event); four operation rows (derived from
  parameters none of which the held documents supply — efficiency 0.50, derate
  0.95, 30,000 h, 80,000 h, 8,000 h). `GRAMC_STACK` is unchecked: no Gramc
  document is held; the third PDF is Gandiglio 2022.
- **The per-system pumps and cables** are the only two amounts that differ from
  print; both the SI's 59 kg total (69 kg per system vs 1,960 kg per kW) and
  Usai's own component results (17× and 34× over if per kW) support the module's
  reading, which is correctly flagged as a correction.
- **Parameters confirmed from documents:** 2 kW→1 kW halving; 32,000 h is
  ecoinvent's comment verbatim (so not an independent figure, as SOURCES.md
  says); 80,000 h is ecoinvent's system-dataset comment; 80 kW via Babatunde's
  citation and the workbook total. Not confirmable from the held files:
  efficiency, derate, 30,000 h, 8,000 h, inverter and container sizing.
- **Published results:** 43/43 values in `validate.PAPER_TABLE3/4/5` match the
  PDF. Cosmetic errors to fix in docs: `validate.py` page refs for Tables 4–5
  (p. 366, not 362); docstring "exactly 2×" (≈2×, Monte Carlo means, water 4.2×);
  "Usai 37.3 (no tank)" is 37.6 from the workbook; SOURCE_DIFF's "25/25" is 26/26.
- **Coverage gap confirmed:** Usai Table 1 has no assembly energy row (every
  other Usai table does); the SI's "final assembly in Europe" sentence has no
  inventory behind it. Cut-off register, as already recorded.
