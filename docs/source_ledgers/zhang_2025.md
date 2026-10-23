# Zhang 2025 — row ledger (22 Oct 2026)

Source re-read against `optimiser_lca/data_centre.py` (activity `dc_zhang_virginia_baseline_25y`, registry code `R.DATA_CENTRE`): 16 technosphere rows + 1 biosphere row. Repository untouched.

## Files read

Source (all under `C:\Users\ls1524\OneDrive - Imperial College London\DC optimiser\data centre reading\zhang virginia dat\`):

- `Zhang LCA data centre virginia 5.pdf` — the paper, 11 pages, text extracted with PyMuPDF (the Read tool cannot render PDFs on this machine: no poppler). Table 1 (p. 3), Table 2 and Table 3 (p. 4), §2.1–2.2 (p. 3), §3 (pp. 4–8).
- `1-s2.0-S2772783125000548-mmc1.xlsx`, sheet `S1 LCA Inventory List` (51 × 6): the 33 flows in six phase blocks with columns Flow Name / Amount / Estimation logic and formula / Key sentence or figure cited / Number taken. Every row dumped.
- `1-s2.0-S2772783125000548-mmc2.xlsx`, sheet `Sheet1` (A1:H45): "Upstream contributions to: Global warming - TRACI 2.1". Column C is `process | reference product | Cutoff, U - location`; column G is the upstream GWP contribution (kg CO2-eq); column H, present on seven rows, appears to be the process's own direct contribution (e.g. the MV electricity market's SF6, waste incineration's stack CO2). Rows 2–45 fall into six contiguous phase blocks (identified below by summing them against mmc3).
- `1-s2.0-S2772783125000548-mmc3.xlsx`, four sheets: `GWP Under Three Strategies ` (phase totals for SERC and WECC at PUE 1.4 / 1.2 / 1.1, absolute and normalised), `Other Categories Change Grid `, `Other Categories Change PUE `, `Other Categories Combined` (the nine TRACI non-GWP categories).

Repository (read only): `optimiser_lca/data_centre.py` (197 lines), `docs/SOURCE_DIFF.md` (#7–9, "Implemented" row, genset note), `optimisation/SOURCES.md` lines 21–36 and 1189–1237, `optimiser_lca/validate.py` (`ZHANG_PAPER_KGCO2E` line 140, `data_centre_vs_paper` lines 298–309), `dc_config.py` lines 39–44, `optimisation/ASSUMPTIONS.md` §1, §2, §6, §7.

## Table S1 — every flow by phase → dc_zhang_virginia_baseline_25y

Amounts are as printed in Table S1 column "Amount" (Table 1 in the paper prints the same figures with one less significant digit in places; differences noted). Module amounts and units are from `data_centre.py` lines 168–185.

| # | Phase | Source row (as printed) | Amount | Unit | Module (key, amount) | Disposition | Note |
|---|---|---|---|---|---|---|---|
| 1 | Material Production | 1 Concrete | 4 000 | m³ | `concrete`, 4000 cubic meter | IN | S1: 10 000 m² × CUI 0.40 m³/m². mmc2 row 9 `market for concrete, 30-32MPa` **RoW**; module picks **RNA** with a stated `why` (North American market for a Virginia build). Location differs from the paper's pick, documented. |
| 2 | Material Production | 2 Reinforcing steel | 4.8 × 10⁵ | kg | `reinforcing_steel`, 4.80e5 kilogram | IN | 4 000 m³ × 120 kg/m³. mmc2 row 10 `market for reinforcing steel` GLO = module. |
| 3 | Material Production | 3 Structural steel | 1.2 × 10⁵ | kg | `structural_steel`, 1.20e5 kilogram | IN | 10 000 m² × 12 kg/m². mmc2 row 12 `market for steel, low-alloyed, hot rolled` GLO = module. |
| 4 | Material Production | 4 Copper | 2.0 × 10⁴ | kg | `copper`, 2.00e4 kilogram | IN | Amount matches. **Process does not**: mmc2 row 14 shows the paper scored copper on `market for metal part of electronics scrap, in copper, anode` GLO (27 857 kg CO2e, 1.39 kg/kg); the module uses `market for copper, cathode` GLO. Not one of the three stated substitutions. See mmc2 section. |
| 5 | Material Production | 5 Aluminium alloy | 1.5 × 10⁴ | kg | `aluminium_alloy`, 1.50e4 kilogram | IN | 10 000 m² × 1.5 kg/m² (expanded-metal facade). mmc2 row 11 `market for aluminium alloy, metal matrix composite` GLO = module (the paper's own odd pick, 18.0 kg CO2e/kg in its model, carried faithfully). |
| 6 | Material Production | 6 Insulation, rigid PUR foam | 2.5 × 10⁴ | kg | `insulation_pur`, 2.50e4 kilogram | IN | 830 m³ at 30 kg/m³, 83 mm over 10 000 m². mmc2 row 13 `market for polyurethane, rigid foam` RoW = module. |
| 7 | Transportation | 1 transport, freight, sea, container ship | 1.88 × 10⁶ kg; 16 160 km; 3.036 × 10⁷ t·km | t·km | — | BOUNDARY (delivery to site) | Shanghai → Norfolk for the servers. mmc2 row 15, 282 491 kg CO2e. Table 1 prints only the kg. |
| 8 | Transportation | 2 transport, freight, lorry 16-32 t, EURO 6 | 1.02 × 10⁷ kg; 60 km; 6.10 × 10⁵ t·km | t·km | — | BOUNDARY (delivery to site) | mmc2 row 16, RoW, 102 470 kg CO2e. |
| 9 | Transportation | 3 transport, freight, lorry, unspecified | 1.5 × 10⁶ kg; 60 km; 9.00 × 10⁴ t·km | t·km | — | BOUNDARY (delivery to site) | mmc2 row 18, RoW, 12 149 kg CO2e. |
| 10 | Transportation | 4 transport, freight train | 6.0 × 10⁵ kg; 400 km; 2.40 × 10⁵ t·km | t·km | — | BOUNDARY (delivery to site) | mmc2 row 17, US, 13 344 kg CO2e. Phase total 410 454 = mmc3 Transportation exactly. |
| 11 | Construction | 1 Diesel, burned in building machine | 2.10 × 10⁶ | MJ | `diesel_construction`, 2.10e6 megajoule | IN | Restored 21 Oct (SOURCE_DIFF #7). S1 formula: 4.5 L/m² × 10 000 m² × 1.30 contingency = 58 500 L × 36 MJ/L = 2.106 × 10⁶, "rounded 2.10 × 10⁶". mmc2 row 31 `market for diesel, burned in building machine` GLO = module; 189 854 kg CO2e (0.0904 kg/MJ). |
| 12 | Construction | 2 Electricity, medium voltage, US-SERC | 2.80 × 10⁵ | MJ | `electricity_mv_gb`, 7.8e4 kilowatt hour | IN-DIFFERS | Restored 21 Oct (#8). Unit: 2.80 × 10⁵ MJ / 3.6 = 77 778 kWh; the module's 78 000 kWh is S1's own intermediate ("7.8 kWh m⁻² × 10 000 m² = 78 000 kWh × 3.6 = 2.81 × 10⁵ MJ", printed 2.80 × 10⁵). Difference 0.3 %, inside the source's own rounding. Process: paper US-SERC (mmc2 row 32, 45 740 kg CO2e); module deliberately GB, and `baseline_grid.py` strips it onto the half-hourly GB series like the operating electricity (`why`, lines 115–117). |
| 13 | Construction | 3 Tap water, municipal (construction use) | 1.20 × 10⁶ | kg | `tap_water`, 1.20e6 kilogram | IN | Restored 21 Oct (#9). 800 m³ mixing water + 400 m³ site use. Process: paper `market for tap water` **RoW** (mmc2 row 33, 1 257 kg CO2e); module reuses the operation key `market group for tap water` GLO. A 1-tonne-CO2e row either way; the one dataset-name difference in the construction block. |
| 14 | Operation | 1 Electricity, medium voltage, US-SERC | 5.76 × 10⁹ | MJ | `electricity_mv_serc`, 1.60e9 kilowatt hour | IN-DIFFERS | 5.76 × 10⁹ MJ / 3.6 = 1.600 × 10⁹ kWh exactly. mmc2 row 2 `market for electricity, medium voltage` US-SERC = module; 940 933 543 kg CO2e (0.5881 kg/kWh; the same factor recurs in the construction and disposal electricity rows). Note the source's own formula does not reproduce its printed figure: "7.53 MW × 8 760 h × 25 y" = 1.649 × 10⁹ kWh, not 1.60 × 10⁹. The module takes the printed/modelled 1.60 × 10⁹, which is what the paper's score rests on; ASSUMPTIONS §1's 7 306 kW continuous therefore sits 3 % under Zhang's stated 7.53 MW facility load. |
| 15 | Operation | 2 Tap water | 2.90 × 10⁹ | kg | `tap_water`, 2.9e9 kilogram | IN | WUE 1.8 L/kWh × 1.60 × 10⁹ kWh = 2.88 × 10⁹ L, printed 2.9 × 10⁹ kg. mmc2 row 4 `market group for tap water` GLO = module; 2 231 927 kg CO2e. |
| 16 | Operation | 3 Diesel, burned in diesel engine | 8.60 × 10⁶ | MJ | `diesel_generator`, 8.60e6 megajoule | IN | **Genset: in the inventory activity, scored and reported, excluded from every objective (ASSUMPTIONS §7, SOURCE_DIFF "The genset is not a decision").** S1's name is "diesel engine"; the dataset actually used is mmc2 row 5 `market for diesel, burned in diesel-electric generating set, 10MW` GLO = module; 741 699 kg CO2e (0.0862 kg/MJ), 0.077 % of the paper's total. S1's own arithmetic gives 8.1 × 10⁶ MJ (4 h/yr × 25 y × 7.53 MW × 0.30 L/kWh × 36 MJ/L = 8.13 × 10⁶) and says "rounded to 8.6 × 10⁶ MJ in the model"; the module takes the modelled 8.6 × 10⁶. |
| 17 | Operation | 4 Computer, laptop | 1.00 × 10⁵ | items | `servers`, 1.0e5 unit | IN | The paper's own process is `market for computer, laptop` GLO (mmc2 row 3, 16 995 243 kg CO2e, 170 kg/unit) — identical to the module's identity, so this is the source's proxy for servers rather than a module substitution; the docstring's "the same proxy the paper used" is right. S1 derivation: 5.38 MW / 0.35 kW = 15 000 servers; refresh every 3.98 y → "6 cycles: 15 000 × (1 + 5 refresh) = 1 × 10⁵" (the product is 90 000; the source rounds up). |
| 18 | Operation | 5 Battery | 2.00 × 10⁴ | kg | `battery`, 2.0e4 kilogram | SUBSTITUTED | Paper: mmc2 row 7 `market for battery, Li-ion, rechargeable, prismatic` GLO (160 993 kg CO2e, 8.05 kg/kg). Module: `market for battery, Li-ion, NMC111, rechargeable, prismatic` GLO — stated substitution, 3.9.1 having split the generic market by chemistry (docstring lines 44–47; LFP flagged as the likelier real UPS chemistry). S1: 10-min bridge at 7.53 MW = 1.255 MWh × 8 kg/kWh = 10 040 kg, one mid-life replacement → 20 000 kg. |
| 19 | Operation | 6 Sodium hypochlorite | 1.30 × 10⁵ | kg | `sodium_hypochlorite`, 1.30e5 kilogram | IN | 2.9 × 10⁹ L × 45 mg NaOCl/L. mmc2 row 6 `market for sodium hypochlorite, without water, in 15% solution state` RoW = module; 328 546 kg CO2e. |
| 20 | Operation | 7 Tetrafluoroethane | 450 | kg | `refrigerant_r134a`, 450 kilogram | SUBSTITUTED | Paper: mmc2 row 8 `market for tetrafluoroethane` GLO (2 958 kg CO2e, 6.57 kg/kg — the "~6.6 kg CO2e/kg" the docstring quotes). Module: `market for refrigerant R134a` GLO, stated substitution (same substance, 3.9.1 name). The 450 kg is also the basis of the added biosphere row, below. |
| 21 | Disposal | 1 Diesel, burned in building machine | 1.0 × 10⁶ | MJ | — | BOUNDARY (end-of-life) | Demolition: 0.46 L/m³ × 60 000 m³ = 27 600 L × 36 MJ/L. mmc2 row 19, 90 407 kg CO2e. |
| 22 | Disposal | 2 Electricity, medium voltage, US-SERC | 5.0 × 10⁴ | MJ | — | BOUNDARY (end-of-life) | 1.4 kWh/m² × 10 000 m² = 14 000 kWh × 3.6. mmc2 row 25, 8 168 kg CO2e. |
| 23 | Disposal | 3 Tap water | 5.0 × 10⁵ | kg | — | BOUNDARY (end-of-life) | Dust suppression 4 L/m²/day × 12.5 days. mmc2 row 29, 385 kg CO2e. |
| 24 | Disposal | 4 Transport, freight, lorry | 3.0 × 108 (sic) | t·km | — | BOUNDARY (end-of-life) | The cell reads "3.0 × 108 t·km" in S1 and "3 × 108 kg⋅km" in Table 1 — a lost superscript; the formula says 3 000 t × 100 km = 3.0 × 10⁵ t·km. mmc2 row 21 (lorry 16-32 t EURO6 RoW), 50 395 kg CO2e. The Disposal block in mmc2 also carries the waste-treatment processes (rows 20, 22–24, 26–28, 30) that the Recycling block then credits. Block sum 298 986 vs mmc3 299 061 (−74 kg, rounding). |
| 25 | Recycling | 1 Scrap aluminium | 1.20 × 10⁴ | kg | — | BOUNDARY (end-of-life, credit) | 15 t × 80 %. mmc2 rows 35 (incineration, −167) and 42 (`aluminium hydroxide production` RoW, −97 204). |
| 26 | Recycling | 2 Scrap copper | 1.60 × 10⁴ | kg | — | BOUNDARY (end-of-life, credit) | 20 t × 80 %. mmc2 rows 36 (−222), 38 (`sheet rolling, copper` −8 749), 44 (`metal working, average for copper product manufacturing` RoW, −1 466 344). |
| 27 | Recycling | 3 Scrap steel | 5.40 × 10⁵ | kg | — | BOUNDARY (end-of-life, credit) | 600 t × 90 %. mmc2 rows 37 (−5 766) and 45 (`steel production, converter, low-alloyed` RoW, −3 063 680 — the single largest credit). |
| 28 | Recycling | 4 Waste electric or electronic equipment (WEEE) | 8.00 × 10⁵ | kg | — | BOUNDARY (end-of-life) | 100 000 servers × 10 kg × 80 %. mmc2 rows 22 (+39 434 in Disposal) and 40 (−39 434 in Recycling): nets to zero. |
| 29 | Recycling | (unnumbered) Waste polyurethane | 2.50 × 10⁴ | kg | — | BOUNDARY (end-of-life) | All 25 t of PUR. mmc2 rows 20 (+68 089) and 41 (−68 089): nets to zero. |
| 30 | Recycling | 5 Waste reinforced concrete | 4.80 × 10⁶ | kg | — | BOUNDARY (end-of-life) | 6 000 t × 80 %. mmc2 rows 34 (`treatment of waste concrete gravel, recycling` +18 205) and 39 (`treatment of waste reinforced concrete, recycling` −26 558). |
| 31 | Recycling | 6 Aluminium hydroxide | −1.70 × 10⁵ | kg | — | BOUNDARY (end-of-life, avoided burden) | −14.2 kg per kg scrap Al × 12 t. This is the credit flow behind row 25. |
| 32 | Recycling | 7 Metal working | −4.68 × 10⁵ | kg | — | BOUNDARY (end-of-life, avoided burden) | −0.867 kg per kg scrap steel × 540 t (Table 1 prints −4.7 × 10⁵). Scored in mmc2 as `metal working, average for copper product manufacturing` (row 44), i.e. the paper credited a copper-working dataset against a steel EAF co-product; out of boundary here, noted only. |
| 33 | Recycling | 8 Steel | −8.80 × 10⁵ | kg | — | BOUNDARY (end-of-life, avoided burden) | −1.63 kg secondary steel per kg scrap × 540 t. mmc2 row 45. Recycling block sum −4 974 039 = mmc3 Recycling exactly. |

Row count check: 6 + 4 + 3 + 7 + 4 + 9 = 33 flows in S1, matching the "33 flows" the module's docstring refers to. The 16 in-boundary rows (#1–6, 11–20) are the module's 16 technosphere rows, one-to-one, in the same order.

## Module rows with no source row — the HFC-134a leak (ADDED)

`data_centre.py` lines 187–190: biosphere `("hfc134a_air", 450, "kilogram", "R134a leaked: the 450 kg top-up replaces leakage at 0.9 %/yr (Zhang Table S1)")`, flow `Ethane, 1,1,1,2-tetrafluoro-, HFC-134a` to air.

Table S1 does derive the 450 kg as leakage. Sheet `S1 LCA Inventory List`, Operation row 7 (spreadsheet row 32), column "Estimation logic and formula", verbatim:

> • Cooling plant = 850 RT (3 MW) with charge 2–4 lb RT⁻¹ : mid-point 3 lb RT⁻¹: 2 000 kg initial.
> • EU F-Gas best sites leak 1–3 % y⁻¹; adopt 0.9 % y⁻¹.
> • 2 000 kg × 0.009 y⁻¹ × 25 y = 450 kg top-up.

Column "Key sentence or figure cited": "full recharge requires 2–4 lb per ton of capacity" (ameritechfl.com); "leakage rates … 1 – 3 % for stationary A/C" (www2.mst.dk).

So the docstring's quotation (lines 54–62) is accurate: 2 000 kg × 0.009 y⁻¹ × 25 y = 450 kg, bought to replace what leaked, and the paper charges only its production (mmc2 row 8: 2 958 kg CO2e). The module emits the same 450 kg to air (450 × 1 530 = 688 500 kg CO2e, the docstring's 688 t). The paper has no emission row for it anywhere in S1 or mmc2, so this is a genuine module addition on the source's own reasoning, and the 0.9 %/yr is indeed below the 1–3 %/yr the source cites. The 2 000 kg initial charge appears nowhere in the paper's inventory (neither as production nor as end-of-life), as the docstring says.

## Parameters

| Parameter | Where the paper states it | Module / repo | Check |
|---|---|---|---|
| 25-year life | §2.1: "the functional unit of the data center facility operating over a 25-year lifetime (TC, 2016)"; §2.2a: "Assumed 25 years of continuous 24/7 operation at full utilization"; Fig. 1 caption "a 25-year operational phase" | `dc_config.DC_OPERATION_YEARS = 25` (line 41, "the Zhang foreground's operating life"); docstring, activity name, comment | ✓ |
| PUE 1.4 baseline | §2.1: "we choose PUE = 1.4 as the baseline research and set the parameter to 1.1–1.2 for future design"; §2.2a: "Baseline Power Usage Effectiveness (PUE) = 1.4, representing about 40 % overhead for cooling and auxiliary systems"; S1 Operation row 1 ("target a PUE of 1.4", packetpower.com) | `dc_config.DC_REFERENCE_PUE = 1.4` (line 44) | ✓ |
| 10 000 m² white space | §2.2a: "Hyperscale data center with 10,000 m² of server white space"; §4: "large-scale data centers with 10,000 m²"; every S1 material and construction row scales off it | docstring line 8, comment line 160 | ✓ |
| IT density and IT load | S1 Operation row 1 only: "IT density 50 W ft⁻² : 540 W m⁻²; 10 000 m² white space: 5.38 MW IT"; §2.2a says only "IT power capacity on the order of tens of megawatts" | ASSUMPTIONS §1 back-solves 5 219 kW IT from 7 306 kW / 1.4 | Differs 3 % from Zhang's 5.38 MW, because of the 1.60 vs 1.65 × 10⁹ kWh slip in row 14. Not a module error; worth a sentence in ASSUMPTIONS §1. |
| Facility load | S1: "Facility load PUE 1.4 : 7.53 MW" | ASSUMPTIONS §1: 7 306 kW continuous | Same 3 % slip. |
| WUE 1.8 L/kWh | S1 Operation row 2 only ("The average data center has a WUE of 1.8 L / kWh", sunbirddcim.com). Not in the paper's main text. | comment on row 15, "WUE 1.8 L/kWh over 25y" | ✓ |
| Server count and refresh | S1 Operation row 4 only: 350 W/server (200–400 W range), 15 000 servers on-line, refresh every 3.98 y (Forrester via ftei.com), 6 cycles, 1 × 10⁵ units; Dell R320 194 W cited | docstring line 52 "a server count with a refresh-cycle adjustment"; comment on row 17 "incl. refresh cycles" | ✓ (source rounds 90 000 up to 1 × 10⁵) |
| UPS sizing | S1 Operation row 5: 10-min bridge, 1.255 MWh, 8 kg/kWh, 10 040 kg initial, one replacement, 20 000 kg (Sandia ESHB ch. 3) | comment "Battery, Li-ion, rechargeable, prismatic — UPS" | ✓ |
| Genset duty | S1 Operation row 3: 0.30 L/kWh, 4 h/yr "conservative" against operators' < 24 h/yr, 753 MWh over life | ASSUMPTIONS §7: 8.6e6 MJ, 32.5 t CO2e/yr, excluded from objectives | ✓ amount; the paper's own score is 742 t over 25 y (29.7 t/yr), the module's 32.5 t/yr is 3.9.1 apos vs 3.7 cutoff |
| Refrigerant | S1 Operation row 7: 850 RT (3 MW) plant, 3 lb/RT, 2 000 kg charge, 0.9 %/yr | docstring lines 54–62 | ✓ (quoted above) |
| Grid | §2.2d: SERC baseline, WECC alternative, "from the Ecoinvent U.S. global markets database" | `electricity_mv_serc` US-SERC, swapped to GB by `baseline_grid.py` | ✓ |
| LCIA / database | §2.2: TRACI 2.1 in OpenLCA; S1 Recycling rows cite "Ecoinvent 3.7 Cut-off"; mmc2 process names carry "Cutoff, U" | docstring lines 35–37, validate.py line 139 | ✓ |

## 21 Oct restores re-checked

| SOURCE_DIFF # | Flow | Table S1 (sheet `S1 LCA Inventory List`) | Table 1 (paper p. 3) | Module | Verdict |
|---|---|---|---|---|---|
| #7 | Construction diesel | Construction row 1, "Diesel, burned in building machine", **2.10 × 10⁶ MJ** (formula 58 500 L × 36 MJ/L = 2.11 × 10⁶, "rounded 2.10 × 10⁶") | "Diesel, burned in building machine 2.1 × 10⁶ MJ" under Construction | `diesel_construction`, 2.10e6 megajoule, `market for diesel, burned in building machine` GLO | Confirmed: amount, unit, phase and process (mmc2 row 31) all match. Paper's score 189 854 kg CO2e, i.e. SOURCE_DIFF's "~190 t". |
| #8 | Construction electricity | Construction row 2, "Electricity, medium voltage, US-SERC", **2.80 × 10⁵ MJ** (formula 7.8 kWh/m² × 10 000 m² = 78 000 kWh × 3.6 = 2.81 × 10⁵) | "Electricity, medium voltage, US-SERC 2.8 × 10⁵ MJ" under Construction | `electricity_mv_gb`, 7.8e4 kilowatt hour | Confirmed: 2.80e5 MJ / 3.6 = 77 778 kWh; module carries S1's 78 000 kWh. Phase correct. Process deliberately GB (stripped onto the GB series). Paper's score 45 740 kg CO2e; SOURCE_DIFF's "~12 t on the GB grid" follows from the lower GB factor. |
| #9 | Construction tap water | Construction row 3, "Tap water, municipal (construction use)", **1.20 × 10⁶ kg** (800 m³ mixing + 400 m³ site) | "Tap water, municipal 1.2 × 10⁶ kg" under Construction | `tap_water`, 1.20e6 kilogram | Confirmed: amount and phase. Process: paper `market for tap water` RoW (mmc2 row 33, 1 257 kg CO2e); module `market group for tap water` GLO. SOURCE_DIFF's "~1 t" holds. |

The three rows sit under a `# --- Construction (Zhang S1; in since 21 Oct 2026) ---` header (line 174) and the docstring (lines 24–30) states the restored boundary. **However, three places still carry the pre-21-Oct wording**: the activity `comment` string in `data_centre.py` lines 162–165 ("Boundary narrowed to Material Production + Operation only (Transportation, Construction energy/water, Disposal and Recycling excluded by scope choice)"), ASSUMPTIONS §2 lines 53–56 ("the activity is Material Production + Operation only. Transportation, construction energy and water, disposal and recycling are excluded by scope choice, as the foreground's own comment records") and the ASSUMPTIONS §6 table row "Data centre | Material production + operation only". The built Brightway activity inherits the stale comment.

## Published result

Paper Table 2 (p. 4), "Contribution of each stage in the life cycle to the global warming potential", with the exact values from mmc3 sheet `GWP Under Three Strategies `, block "Baseline: SERC PUE 1.4", row PUE 1.4:

| Stage | Table 2 | Share | mmc3 exact (kg CO2-eq) |
|---|---|---|---|
| Total | 9.63 × 10⁸ | 100 % | 963 468 887.65 |
| Material Production | 2.79 × 10⁶ | 0.29 % | 2 791 653.09 |
| Transportation | 4.10 × 10⁵ | 0.04 % | 410 453.69 |
| Construction | 2.37 × 10⁵ | 0.02 % | 236 851.35 |
| Operation | 9.65 × 10⁸ | 99.61 % | 964 704 908.08 |
| Disposal | 2.99 × 10⁵ | 0.03 % | 299 060.58 |
| Recycling | −4.97 × 10⁶ | −0.52 % | −4 974 039.14 |

Points for `validate.py`:

- `ZHANG_PAPER_KGCO2E = 9.63e8` (line 140) is Table 2's and Fig. 6's cradle-to-grave total and is the right published figure. The paper's running text is internally inconsistent: §3.2 says "the full life-cycle GWP drops from approximately 2.56 × 10⁹ kg CO₂-eq under the baseline to 1.83 × 10⁹ under the WECC grid" and §3.4 "1.46 × 10⁹ … compared to 2.56 × 10⁹ in the baseline", whereas Table 2, Fig. 6's caption ("the first bar (9.63 × 10⁸)") and mmc3 (SERC 9.63 × 10⁸, WECC 6.91 × 10⁸, WECC + PUE 1.1 5.48 × 10⁸) all agree on 9.63 × 10⁸. The 2.56 × 10⁹ figures are a uniform factor 2.66 above mmc3 and look like a leftover from an earlier model version. validate.py's choice stands.
- The like-for-like comparator for the module's boundary (Material Production + Construction + Operation, no transport, no end-of-life) from the paper's own model is 2 791 653 + 236 851 + 964 704 908 = **967 733 413 kg = 9.68 × 10⁸**, 0.44 % above 9.63 × 10⁸ (the net end-of-life credit of −4.67 × 10⁶ and transport 4.1 × 10⁵ are what drop out). The docstring's 0.87 ratio (8.38 × 10⁸, full-boundary rebuild) is unaffected at two decimals; `data_centre_vs_paper`'s printed note could cite 9.68e8 as the same-boundary figure.
- Genset share: the paper gives none in text or tables. mmc2 row 5: 741 698.69 kg CO2e = 0.0770 % of the total, 0.0769 % of Operation. On the module's own scoring (ASSUMPTIONS §7, 32.5 t/yr × 25 = 812 t) it is 0.084 % of 9.63 × 10⁸.
- mmc2's phase blocks reproduce mmc3 exactly for Material Production, Transportation, Construction and Recycling, within 74 kg for Disposal, but the seven Operation rows sum to 961 394 908, i.e. 3 310 000 kg (0.34 %) short of mmc3's 964 704 908. The gap is not explained by any S1 row (450 kg HFC-134a at TRACI's 1 430 would be 6.4 × 10⁵; 2 000 kg would be 2.86 × 10⁶). Likely a direct emission on the operation unit process or a tree snapshot from a slightly different model state; it does not affect the module.
- Table 3 (the nine other categories) matches mmc3 `Other Categories Change Grid ` row 1 (e.g. Acidification 2 593 935 kg SO2 eq, Ecotoxicity 9.18 × 10⁹ CTUe, Fossil fuel depletion 8.97 × 10⁸ MJ surplus). Not used by the repo.

## mmc2 process names — paper's dataset vs the module's identity

Only the in-boundary rows. "Paper" is mmc2 column C (`process | reference product | Cutoff, U - location`); "Module" is the `identity` tuple in `data_centre.py`.

| S1 row | Paper's process (mmc2 row) | Paper's GWP, kg CO2e | Module identity | Match |
|---|---|---|---|---|
| Concrete | `market for concrete, 30-32MPa` RoW (9) | 1 256 454 | `market for concrete, 30-32MPa` RNA | Same dataset family, **location differs** (RoW → RNA), documented in `why` |
| Reinforcing steel | `market for reinforcing steel` GLO (10) | 895 359 | `market for reinforcing steel` GLO | Exact |
| Structural steel | `market for steel, low-alloyed, hot rolled` GLO (12) | 183 879 | `market for steel, low-alloyed, hot rolled` GLO | Exact |
| Copper | **`market for metal part of electronics scrap, in copper, anode` GLO** (14) | 27 857 (1.39 kg/kg) | `market for copper, cathode` GLO | **Mismatch, not among the three stated substitutions.** The paper's pick is a scrap-derived copper-anode flow, almost certainly a mis-selection for "copper, cabling and architectural elements"; the module's cathode is the defensible dataset but scores several times higher per kg (copper cathode in ecoinvent is of order 4–6 kg CO2e/kg against the paper's 1.39). On 2.0 × 10⁴ kg the difference is of order 10⁵ kg CO2e over 25 y: well under 0.1 % of the facility, but the module's `why` for `copper` is empty and the docstring's list of deviations from the paper is therefore incomplete. |
| Aluminium alloy | `market for aluminium alloy, metal matrix composite` GLO (11) | 270 655 | `market for aluminium alloy, metal matrix composite` GLO | Exact (the paper's own unusual pick, 18.0 kg/kg, carried as-is) |
| Insulation PUR | `market for polyurethane, rigid foam` RoW (13) | 157 449 | `market for polyurethane, rigid foam` RoW | Exact |
| Construction diesel | `market for diesel, burned in building machine` GLO (31) | 189 854 | `market for diesel, burned in building machine` GLO | Exact |
| Construction electricity | `market for electricity, medium voltage` US-SERC (32) | 45 740 | `market for electricity, medium voltage` GB | Deliberate: GB, then stripped onto the GB series (`why`) |
| Construction tap water | `market for tap water` RoW (33) | 1 257 | `market group for tap water` GLO | Minor dataset difference (market vs market group, RoW vs GLO), undocumented; ~1 t either way |
| Operation electricity | `market for electricity, medium voltage` US-SERC (2) | 940 933 543 | `market for electricity, medium voltage` US-SERC | Exact (then stripped onto the GB series by `baseline_grid.py`) |
| Operation tap water | `market group for tap water` GLO (4) | 2 231 927 | `market group for tap water` GLO | Exact |
| Genset diesel | `market for diesel, burned in diesel-electric generating set, 10MW` GLO (5) | 741 699 | `market for diesel, burned in diesel-electric generating set, 10MW` GLO | Exact (S1's flow name "diesel engine" is looser than the dataset; the module follows the dataset) |
| Servers | `market for computer, laptop` GLO (3) | 16 995 243 | `market for computer, laptop` GLO | Exact — so "laptop for servers" is the paper's substitution, not the module's; the module adds no deviation here |
| UPS battery | `market for battery, Li-ion, rechargeable, prismatic` GLO (7) | 160 993 | `market for battery, Li-ion, NMC111, rechargeable, prismatic` GLO | Stated substitution (chemistry split in 3.9.1) |
| NaOCl | `market for sodium hypochlorite, without water, in 15% solution state` RoW (6) | 328 546 | same, RoW | Exact |
| Refrigerant | `market for tetrafluoroethane` GLO (8) | 2 958 | `market for refrigerant R134a` GLO | Stated substitution (same substance, 3.9.1 name) |

Beyond the three the docstring declares, the deviations from the paper's own datasets are: copper (dataset, unstated), concrete (location, stated), construction electricity (location, stated and intended), construction tap water (market vs market group, unstated, negligible).

## Summary

Counts over the 33 Table S1 flows: **IN 12** (#1–6, 11, 13, 15–17, 19), **IN-DIFFERS 2** (#12 construction electricity MJ→kWh and SERC→GB; #14 operation electricity MJ→kWh), **SUBSTITUTED 2** (#18 battery, #20 refrigerant), **BOUNDARY 17** (4 Transportation = delivery to site; 4 Disposal + 9 Recycling = end-of-life incl. the avoided-burden credits), **MISSING 0**, **NOT-APPLICABLE 0**. 12 + 2 + 2 = the module's 16 technosphere rows, one-to-one. Plus **1 ADDED** biosphere row (450 kg HFC-134a to air), grounded in S1's own "2 000 kg × 0.009 y⁻¹ × 25 y = 450 kg top-up".

1. **The transcription is complete and exact.** Every in-boundary S1 flow is in the module at the printed amount; the two MJ→kWh conversions are right (5.76e9 / 3.6 = 1.60e9; 2.80e5 / 3.6 = 77 778 ≈ the source's own 78 000); the three 21 Oct restores (#7–9) are at S1's printed amounts, in the Construction phase, on the paper's datasets (electricity deliberately GB). Nothing is missing. The genset row is in the activity as the brief describes and excluded only at the objective.
2. **One unstated dataset deviation: copper.** The paper scored its 2.0 × 10⁴ kg of copper on `market for metal part of electronics scrap, in copper, anode` (mmc2 row 14), the module on `market for copper, cathode`. The module's pick is the sensible one and the effect is far below 0.1 % of the facility, but the docstring's "three deliberate substitutions" should become four, or the `copper` process should get a `why`.
3. **Stale boundary text in three places**: `data_centre.py` activity comment (lines 162–165), ASSUMPTIONS §2 (lines 53–56) and the ASSUMPTIONS §6 table row still say "Material Production + Operation only … construction energy/water excluded by scope choice". The docstring and the code disagree with them since 21 Oct; the Brightway activity carries the stale comment.
4. **The source's own arithmetic slips, inherited correctly.** S1's printed 1.60 × 10⁹ kWh is 3 % below its formula (7.53 MW × 8 760 × 25 = 1.65 × 10⁹); the genset's 8.6 × 10⁶ MJ is "rounded" from a computed 8.1 × 10⁶; the servers' 1 × 10⁵ from 90 000; construction electricity 2.80 vs 2.81 × 10⁵. The module takes the printed/modelled numbers, which is right because they are what the paper's 9.63 × 10⁸ rests on (electricity scores at 0.5881 kg/kWh × 1.60 × 10⁹ exactly). Consequence: ASSUMPTIONS §1's 7 306 kW and 5 219 kW IT are 3 % under Zhang's stated 7.53 MW / 5.38 MW, which §1 could say.
5. **validate.py's 9.63e8 is the right published total** (Table 2, Fig. 6, mmc3), despite the paper's text quoting 2.56 × 10⁹ in §3.2 and §3.4. The same-boundary figure from mmc3 is 9.68 × 10⁸ (MP + Construction + Operation); the paper gives no genset share, mmc2 puts it at 0.077 %.
6. **The HFC-134a addition is faithful to the source's reasoning**: S1 derives the 450 kg as leakage replacement and the paper charges only its production (2 958 kg CO2e); the module's 688.5 t emission has no counterpart in S1, mmc2 or mmc3, as the docstring states.
7. Minor: construction tap water is on the GLO market group rather than the paper's RoW market (~1 t); concrete is RNA rather than the paper's RoW (documented); the mmc2 Operation block is 0.34 % short of mmc3's Operation total for reasons internal to the paper's model.
