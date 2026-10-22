# Source diff — every inventory against its source, 21 Oct 2026

The systematic check the boundary decision of 20 Oct called for: for each
inventory in `optimiser_lca/`, every row of its source is either in the module,
a listed boundary item (end-of-life, delivery to site, the genset), or a listed
substitution. Five checks were run in parallel, one per source family, each
reading the source documents directly (Jasper's SI workbook, Voß's ESI,
Smith's appendix and transcription, Usai's SI and Babatunde's SI, Gerloff's SI
and Hermesmann's paper via the SimaPro exports, Zhang's mmc1–3, Leng's SI,
the IEA PVPS workbook, Gandiglio). Working files are in the session scratchpad
under `agent_bess`, `agent_upv`, `agent_fc`, `agent_h2dc`, `agent_tx`.

Nothing in the repo was changed by the check. This note records what it
found; `CUTOFF_RULE_PLAN.md` carries the work.

## Clean

| Inventory | Source | Result |
|---|---|---|
| Fuel cell BoP | Usai 2021 SI Table 1 | 25/25 rows in, at printed amounts; pumps and cable per system (3/80, 16/80), supported by the SI's 59 kg total |
| Fuel cell stack | Babatunde 2024 Table S1 (found at `OneDrive…\data centre reading\fuel cell\`) | 16 technosphere + 6 biosphere rows in; identical to ecoinvent's live 2 kW dataset |
| Hydrogen tank | Gandiglio 2022 | the one steel row in (it is **Table 5**, not Table 3 as the docstring says); frame and pad are additions |
| Jasper container, racks, cooling, fire suppression | Jasper 2026 SI | every material row in, incl. the upstream transport restored on 20 Oct |
| Smith A1–A8, A10, A12, A13 | Smith 2024 | 231 rows in at the same amounts; inter-stage transport in |
| Gerloff AE/PEM/SOEC bills | Gerloff 2021 SI Figs 1–5, Tables 3–6 | every row ties to the SimaPro exports; three small deviations below |
| Hermesmann SMR, SMR-CCS, CCS | Hermesmann & Müller 2022 Tables 2–3, §3.2.3 | all rows in; two items below |
| Leng transformer bills | Leng 2026 Table S1 | all ten material rows in; forming added |
| IEA PVPS Z-PV-276 transformer | T12-33:2026 Table 49 | 19/20 rows exact; one unit slip below |

## Missing: in a source, inside the boundary, not in the module

These are restored without a threshold test (plan step 2A).

| # | Technology | Flow | Amount | Source | Scale |
|---|---|---|---|---|---|
| 1 | Battery | Container concrete block | 43.9 t per 3,008 kWh container (provider "concrete block production, DE") | Jasper SI liquid sheet row 17 | ~2.3 % of the battery |
| 2 | Fuel cell | The same pad, via the shared container at 1 MW each | as #1 | inherited | ~2.3 % of a calendar-life fuel cell |
| 3 | Battery | Voß's 1,000 km in-China lorry leg on **every** cell material (SGr, LFP-C, SBR, housing, and by §3.1.3 CMC, carbon black, both foils, separator, electrolyte, PVDF); currently kept on natural graphite only | 1.0 t·km per kg of material ≈ 5.4 t·km per kWh of cells | Voß ESI Tables S5, S31, S35, S36, §3.1.3 | ~0.5 kg CO₂e/kWh, under 1 % |
| 4 | Solar | Land occupation, natural (non-use) | 3 m²·a per m² of module | Smith A14 | zero GWP100, verified |
| 5 | Solar mounting | Ten Z-PV-239 rows: upstream transport (lorry 1.946, rail 5.838, LCV 0.973 t·km/m²: standard material-to-factory distances, IEA calls the dataset cradle-to-gate), two packaging-waste rows (cardboard 0.0926 kg, PE/PP 0.00534 kg), five land rows (zero GWP) | per m² | IEA PVPS Z-PV-239 | small |
| 6 | Solar step-ups | Transformer station building, "building, hall, steel construction" | 10 m² per 2.5 MVA unit = 4 m²/MWp | IEA PVPS Z-PV-238 Table 50 | to score |
| 7 | Facility | Construction-phase diesel | 2.10e6 MJ, `diesel, burned in building machine` | Zhang S1 | ~190 t over 25 y |
| 8 | Facility | Construction-phase electricity | 7.8e4 kWh | Zhang S1 | ~12 t on the GB grid |
| 9 | Facility | Construction-phase tap water | 1.20e6 kg | Zhang S1 | ~1 t |
| 10 | Grid intake / wind step-ups | Leng Table S3 civils: box-transformer foundations (backfill 728 m³, C15 56 m³, C30 280 m³, rebar 19.6 t, welding and truck energy); booster-station buildings and outdoor venue (four building projects, Leng's own score 6,269 t CO₂e per 100 MVA); electrical installation (section steel 261 kg, terminal blocks 375 kg, …) | as printed | Leng 2026 S3 | box-transformer pads ~3.4 m³ concrete + 196 kg rebar per MW; the booster station is ~23× the intake transformer's materials. See decision D2 |
| 11 | Electrolyser (SOEC) | Lanthanum oxide and strontium carbonate in the electrolyte layer | unknown: Gerloff's SI points to an Excel sheet not held; the SimaPro model carries both at 0 kg | Gerloff SI Fig. 5 row 53 | small |
| 12 | Hydrogen (SMR, SMR-CCS) | Nitrogen to air | 16.41 / 20.84 kg per kg H₂ | Hermesmann Table 2 | zero GWP |

Facility construction (#7–9) totals ~237 t CO₂e over 25 y in Zhang's own
model, about +1 % on the facility's non-electricity fixed burden.

## Substituted: in a source, replaced by something else, worth a decision

| # | Technology | What the source has | What the module does | Note |
|---|---|---|---|---|
| S1 | Battery and fuel cell step-up | Jasper gives the container transformer's composition per kg: Cu cathode 0.25 + wire drawing, GO electrical steel 0.31, low-alloyed steel 0.14, base oil 0.14, electronics 0.09, ecoinvent HV transformer 0.07, metal working 0.31 + 0.14 (sums to 1.00) | 5,500 kg on the IEA PVPS *aluminium-wound* unit's composition, with the docstring saying Jasper publish no split | The claim is wrong. Jasper's own split is copper-wound with an electronics row and would score higher per kg. Switch to Jasper's split, or state why not (the GOES market may not exist in 3.9.1) |
| S2 | Hydrogen (MP-E) | 3.00 kg solid carbon per kg H₂ as an avoided-burden credit against carbon black (§3.2.4) | no co-product, no credit; hydrogen carries the whole burden | The credit is of order 6–9 kg CO₂e/kg H₂, larger than the route's ~4 kg/kg score. See decision D1 |
| S3 | Electrolyser (PEM) | 0.8 kg iridium (Gerloff, from UBA data) | 0.8 kg platinum, "used as a replacement for iridium" | Material for GWP and resource use; needs an iridium dataset or a stated proxy factor |
| S4 | Hydrogen (CCS) | "15.4 kg diesel per kg CO₂" for well drilling (Verma) | read as per tonne (÷1000), burned | Deliberate and defensible (per kg would be 660 MJ/kg CO₂); keep, but say so |
| S5 | Electrolyser (AE) | gas separator steel 80 + 80 kg; diaphragm sheet rolling 400 kg | 160 + 160; 405 | +165 kg steel on a 1 MW unit; the "(2 ×)" line doubled twice |
| S6 | Solar | Smith A15: 30 % transformer replacement over 30 y | step-up module has no replacement term (35-y life) | A gap only if the transformer's life is shorter than 35 y; consistent with the wind step-ups |
| S7 | IEA PVPS Z-PV-276 | fibreboard 36.96 **kg** (the cell says m³, its comment says kg) | 0.03696 m³ = 46.9 kg, back-solved to hit "5,680 kg"; the bill actually sums to 5,670 | +27 % on a 0.65 % row; `check()` reconciles on the wrong lever |
| S8 | Battery cell | Voß Table S37 fixing and isolation materials (PET bag, retainer, envelope, tapes, 1 kg/kg) | all 330 g of housing on Table S36 | Voß give no split; already marked ASSUMED |
| S9 | Battery | Jasper's cells 65:35 SGr:NGr | Voß's 75:25 market share | by choice, documented |

## Claims in the repo that the sources do not support

These are wrong in the code or docs and mislead the next reader:

- **"Leng add factory electricity on the Chinese grid"** (`stepup_transformers.py` lines ~94–96 and 120–121; `transformers.py` ~109–111; `SOURCES.md` ~758 and ~869; `DATA_GAPS.md` rows ~97–99; and `CUTOFF_RULE_PLAN.md` as first written). Leng publish **no** factory energy for either transformer: Table S1 is materials, S2 transport, S3 civils, and the main transformer was "modeled based on" Li et al. 2020, which is not held. The 342 t vs 275 t gap is ecoinvent 3.11 + RoW proxies against 3.9.1 apos GLO markets. There is nothing to restore; if factory energy is wanted it has no Leng source. IEA PVPS gives 0.42 kWh + 1.74 MJ per kg for its own unit.
- **"Jasper publish no split for the container transformer"** (`stepup_transformers.py`). They do (S1 above).
- **The electrolysers are Gerloff 2021's, not Hermesmann's** (`hydrogen.py`, `SOURCES.md`). Bills, manufacturing energy, lifetime H₂ and operating data all tie to Gerloff's SI; Hermesmann has no AE or SOEC and his PEMEL is a different, Bareiß-based bill. The "SimaPro exports of Hermesmann" are the user's own SimaPro project (`Documents\brightway\*.XLSX`).
- **Gandiglio "Table 3"** in `h2_tank.py` is Table 5.
- **`UPV-DEFERRED-ISSUES.md` reasons**: the 20 deferred Smith rows are not mangled (A1, A4, A7, A8 print cleanly) and most of their flow names exist in the 3.9.1 biosphere under current names. All 20 have **no** GWP100 factor, now verified, so they can be restored as zero-GWP rows or kept deferred with the right reason.
- **`bop_extrusion_film` "absent from 3.9.1"** (`fuel_cell.py`): `extrusion, plastic film` exists as RER/RoW/CA-QC plus a GLO market.
- **Leng box-transformer rating**: main text says 3,500 kVA, the module takes 2.2 MVA from the model number. Per-MW scaling is unaffected.

## Still unsourced (cut-off candidates, plan step 2B)

Confirmed by the diff to be absent from every held source, so they stay on the
1 % / 5 % / design-change test: Voß's processing materials (NMP, argon, N₂,
compressed air: datasets named, no amounts); battery and fuel-cell container
switchgear; tank forming, valves and compressor hardware; grid-connection
switchgear, protection and bay; Usai gives no BoP assembly energy (a coverage
gap of the source, not a transcription miss).

## Implemented, 21 Oct 2026

All foregrounds rebuilt, caches refreshed, 184 tests passing.

| Item | Done | Effect |
|---|---|---|
| #1, #2 Jasper's concrete block | on the container activity (`bess.py`), so the fuel cell shares it | battery DC block 97.91 → 101.11 kg CO₂e/kWh nameplate; fuel-cell BoP container 3.7 → 10.1 t/MW |
| #3 Voß's in-China lorry leg | on every cell material and the graphite, LFP-C, SBR and housing activities | cell 79.53 → 80.58 kg/kWh |
| #4 Smith land occupation | biosphere row on the plant, 3 m²·a per m² | zero GWP |
| #5 Z-PV-239 rows | transport, packaging waste and land rows on the mounting | solar plant 877.5 → 890.3 t/MWp (+1.5 %) |
| #6 Z-PV-238 station building | 4 m²/MWp on the solar step-ups, scored apart as civils | solar step-ups 296 → 343 kg/MWp/yr |
| #7–9 Zhang construction | three rows in `data_centre.py`; construction electricity joins the GB-series swap | facility IT-side +1.0 % |
| #10 Leng box-transformer pads | per MW of wind on the wind step-ups, scored apart as civils; booster station awaits D2 | wind step-ups 279 → 329 kg/MW/yr |
| #12 Nitrogen to air | SMR and SMR-CCS biosphere rows | zero GWP |
| S4 CCS diesel | per-tonne reading stated in the module | none |
| S5 AE steel | 5,214.4 → 5,134.4 and 10,215 → 10,130 kg | AE capital −0.05 % |
| S7 fibreboard | 36.96 kg, bill 5,670 held within 0.5 % of "~5,680" | solar unit −0.18 % mass |
| Wrong claims | Leng factory energy (code, SOURCES, DATA_GAPS); Jasper's split; Gerloff attribution and activity names; Gandiglio Table 5; deferred-rows reasons; extrusion film | docs only |
| MP-E | no credit, full allocation: stated in `hydrogen.py` and ASSUMPTIONS §5 (user, 21 Oct) | none (already so) |
| S6 transformer replacement | Smith A15's 30.2 % over 30 y as its own activity (`TX_SOLAR_REPL30`), charged per year by `transformers.py` whatever life the unit is amortised over | solar step-ups 343 → 448 kg/MWp/yr (+104 replacements) |
| S1 container transformer | **kept on the IEA recipe as a stated substitution** on technological representativeness: Jasper's recipe is Hunziker 2020's 630 kVA unit with an on-load tap changer, scaled by mass; the IEA unit is a current 2.5 MVA 20/0.4 kV distribution transformer. Jasper's recipe is the sensitivity case (user, 22 Oct) | none; sensitivity +72 % on the unit, battery about +2 %, fuel cell about +4 % |

Not done: #11 (La₂O₃/SrCO₃, no amount held), S3 (iridium, parked by the
user), D2 (Leng's booster station, below).
The wind step-ups have no replacement rate because Leng publish none: an
unsourced flow for the cut-off register. `option_summary.csv`, the sensitivity CSVs
and the LCA map are stale until the reference cases are re-run.

## Decisions for the user

- **D1. The methane-pyrolysis carbon co-product.** Hermesmann apply a
  substitution credit (avoided carbon black), which is system expansion inside
  an otherwise attributional study (ASSUMPTIONS §5), and §6 already refuses
  end-of-life credits. Options: (a) the credit, as the source; (b) allocation
  between H₂ and carbon, which keeps the study attributional (an unused
  mass-allocation model exists at `OneDrive…\article LCA\processes\UK MP
  Operation.XLSX`, 4.26 kg carbon black per kg H₂); (c) leave it, all burden
  on hydrogen, and say so. Turquoise is bought hydrogen only, so no on-site
  asset depends on it.
- **D2. Leng's booster-station civils.** In the source and inside the boundary,
  but it is a wind farm's substation, so what to take needs a decision.

  *Leng's farm against ours.* Gaoyou is 100 MW of turbines behind one 100 MVA
  main transformer, with no N-1 unit. The London reference case is a 150 MW
  load; the optimiser builds a 145 MW connection at minimum cost and 5.9 MW at
  minimum carbon, and the intake is charged at 2 MVA per MW for N-1. So Leng's
  substation is about the size of our minimum-cost connection, and one yard
  serves both of our transformers, so the civils scale by MW of connection,
  not by MVA installed.

  *What the station is.* Four building projects, Leng's own shares of its
  6,269 t CO₂e (Fig. 9c):

  | Part | Share | t CO₂e per 100 MW | kg CO₂e per MW of connection per year, 40 y | What it is |
  |---|---|---|---|---|
  | Comprehensive building | 43.8 % | 2,746 | 687 | control room, offices, staff quarters |
  | Outdoor venue | 34.4 % | 2,157 | 539 | the switchyard: 23,650 m³ site formation, 896 m³ concrete, 12 t rebar, foundation beams |
  | Attached building | 13.7 % | 859 | 215 | auxiliary building |
  | Production building | 8.1 % | 508 | 127 | equipment hall |
  | Whole station | 100 % | 6,269 | 1,567 | |
  | *For scale: the intake transformer, materials only* | | | 138 | |

  At 145 MW the whole station is ~227 t/yr and the venue alone ~78 t/yr,
  against a ~108,500 t/yr system at minimum cost: 0.2 % and 0.07 %. Per
  technology it is 11× and 4× the transformer.

  *Recommendation.* Take the **outdoor venue** per MW of connection: it is the
  electrical yard every intake substation has, and its rows are plain civils.
  Treat the three **buildings** as covered by the facility's own building,
  which Zhang's inventory already carries (4,000 m³ of concrete and 480 t of
  rebar, housing the data centre's electrical rooms) — a stated substitution,
  not an omission. Taking the whole station would double-count a control
  building against Zhang's.
- **D3. Iridium.** Gerloff's 0.8 kg of iridium has no 3.9.1 dataset in the
  module's map; platinum stands in. Find an iridium factor or state the proxy.
- **The genset** is not a decision: Zhang's 8.6e6 MJ is scored and reported by
  `data_centre.py` and excluded from every objective (ASSUMPTIONS §7), which is
  what boundary (c) means.
