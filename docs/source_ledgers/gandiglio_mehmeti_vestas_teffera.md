# Four smaller LCA sources re-read against the modules — ledgers (22 Oct 2026)

Repository read-only; nothing under `ukdclca/` was changed. PDFs were read as text
extracted with pymupdf (the Read tool cannot render PDFs on this machine); pages
that hold tables or figures were rendered to PNG and read visually. Page numbers
below are the journal/report page numbers printed on the page; "PDF p." is the
file's page index where it differs.

Dispositions: IN / IN-DIFFERS (both numbers) / BOUNDARY (end-of-life, delivery to
site, genset) / SUBSTITUTED / NOT-APPLICABLE (reason) / MISSING (in source, in
boundary, not in module) / CUT-OFF-INPUT (a number the register will use).

---

# Gandiglio et al. 2022 — ledger (22 Oct 2026)

M. Gandiglio, P. Marocco, I. Bianco, D. Lovera, G.A. Blengini, M. Santarelli,
"Life cycle assessment of a renewable energy system with hydrogen-battery storage
for a remote off-grid community", *Int. J. Hydrogen Energy* 47 (2022) 32822–32834,
doi 10.1016/j.ijhydene.2022.07.199. Ginostra (Stromboli), REMOTE project.

Files read (pages): `gangliano fuel cell hydrogen tank.pdf`, 13 pp = journal
pp. 32822–32834 (PDF p. N = journal p. 32821+N), all read; Table 5 (p. 32828) and
Fig. 7 (p. 32831) also read from rendered images. `gangliano fuel cell hydrogen
tank supplementary.pdf`, 5 pp, all read — it holds only Table S.1 (control-strategy
parameters: electrolyser 70 % HHV, fuel cell 45 % LHV, battery 0.92/0.92, SOC
20–100 %), the two control block diagrams and a nomenclature. No inventory, no cost.

Module: `optimiser_lca/h2_tank.py` (whole file read), activity `R.H2_TANK`,
design `gandiglio_28bar`, functional unit 1 kg of H₂ storage capacity.

## Table 5 (p. 32828), "Inventory of the renewable scenario for 1 kWh of electricity produced" → `h2_tank.py` H2_TANK

All twelve rows of the table, as printed (ecoinvent 3.7, EF 3.0). The paper's
functional unit is 1 kWh delivered over 25 y; the module's is 1 kg of capacity.

| # | Source row (as printed) | Amount | Unit | Module (name, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | Photovoltaic panel — *Photovoltaic panel, single-Si wafer {GLO}\| market for \| Alloc Rec, S*; "PV systems size: 170 kW; PV total area: 922.23 m²; No replacements … (25 years)" | 2.15·10⁻⁴ | m²/kWh | — | NOT-APPLICABLE (PV is sourced elsewhere: Smith 2024 / IEA PVPS) | |
| 2 | Photovoltaic plant — *Photovoltaic plant, electrical installation for 570 kWp open ground module {GLO}* | 6.95·10⁻⁸ | p/kWh | — | NOT-APPLICABLE | |
| 3 | Photovoltaic mounting system — *… for 570 kWp open ground module {GLO}* | 6.41·10⁻⁵ | m²/kWh | — | NOT-APPLICABLE | |
| 4 | Generators — *Diesel-electric generating set, 18.5 kW {GLO}*; "47 kW; lifetime 16,000 h; 1 generator, no replacements" | 5.92·10⁻⁷ | p/kWh | — | BOUNDARY (standby genset) | |
| 5 | Diesel — *Modified from: Diesel, burned in diesel-electric generating set, 18.5 kW {GLO}*; 3,639 l/year | 2.12·10⁻¹ | kWh/kWh | — | BOUNDARY (genset) | |
| 6 | Battery — *Battery, Li-ion, rechargeable, prismatic {GLO}*; "Lifetime 10 years; 1 battery (600 kWh) + 2 replacements; 150 Wh/kg" | 2.3·10⁻³ | kg/kWh | — | NOT-APPLICABLE (battery is Jasper/Voß) | |
| 7 | Fuel cell — *Fuel cell, stack polymer electrolyte membrane, 2 kW electrical, future {GLO}\| market for \| Cut-off, S*; "Lifetime 5 years; 1 fuel cell (50 kW) + 4 replacements" | 2.91·10⁻⁵ | p/kWh | `fuel_cell.py` cites the 5-y replacement as indicative (SOURCES.md:981) | NOT-APPLICABLE as inventory (stack is Babatunde); the 5-y life is used as a *calendar-life* indication — IN there | A 50 kW unit inventoried as ecoinvent's 2 kW stack alone, no BoP; the only row on the *Cut-off* system model, the rest are *Alloc Rec* (APOS) |
| 8 | Alkaline electrolyser — "Data from literature [39]; Lifetime 9 years; 1 electrolyser (50 kW) + 2 replacements" | 3.50·10⁻⁵ | kWe/kWh | — | NOT-APPLICABLE (electrolysers are Gerloff) | [39] is Staffell & Ingram 2010, an alkaline **fuel-cell CHP** LCA, not an electrolyser inventory |
| 9 | **Steel – H₂ storage** — *Steel, chromium steel 18/8 {GLO}\| market for \| Alloc Rec, S*; "Total volume: 21.6 m³. Mass: 15,652 kg." | **3.65·10⁻³** | kg/kWh | `TANK_DESIGNS["gandiglio_28bar"]`: `steel_kg` 15,652, `volume_m3` 21.6, `pressure_bar` 28, process `steel_chromium_188` = *market for steel, chromium steel 18/8* [GLO]; `TANK_STEEL_KG_PER_KG_H2` = 312.8 kg per kg H₂ | **IN** | Mass, volume and dataset transcribed exactly. The per-kg-capacity conversion (50.04 kg H₂ in the vessel) is the module's own, see Parameters. The paper gives no source for the 15,652 kg (no citation on the row) |
| 10 | Steel – O₂ storage — same dataset; "Total volume: 10.3 m³. Mass: 7826 kg." | 1.82·10⁻³ | kg/kWh | — | NOT-APPLICABLE (the study's fuel cell breathes air; Ginostra feeds pure O₂ "to avoid sending air rich in marine salt" to the cathode, p. 32825) | 7,826 = 15,652 / 2 exactly, for 0.477 of the volume: the two masses look like one scaled estimate (725 vs 760 kg/m³), not two weighed vessels. The text (p. 32825) says the O₂ tank is 10.8 m³; Table 5 says 10.3 m³ |
| 11 | Transport with helicopter — *Transport, helicopter {GLO}\| processing*; "PV panels, batteries, electrolyser, hydrogen storage, oxygen storage, fuel cell, diesel generator and diesel fuel to Ginostra, including … replacements" | 9.50·10⁻⁶ | h/kWh | — | BOUNDARY (delivery to site) | The paper's own result: transport "less than 0.5 % in all impact categories" (p. 32830), "less than 1 % of the total emissions" (p. 32832) |
| 12 | (not a row — stated boundary) End-of-life "excluded … as a precautionary measure" (p. 32827) | — | — | module excludes EoL | BOUNDARY | Same choice as the study |

Nothing else in Table 5 touches the tank: **no forming, no valves, no pipework, no
compressor, no foundation, no leakage, no purification** — one line of steel,
exactly as the module's docstring says.

## Parameters

| Parameter | Source value (page) | Module value | Disposition |
|---|---|---|---|
| Table number for the tank line | Table 5 (p. 32828). Table 3 (p. 32827) is the diesel-genset specification, Table 4 (p. 32827) the reference-scenario inventory | `note: "… Table 5"`; docstring says Table 5 | IN (the earlier "Table 3" was wrong) |
| Plant lifetime | 25 years — abstract (p. 32822: "6570 t of CO₂ equivalent can be saved in 25 years (lifetime of the plant)"), every Table 5 note, Conclusions (p. 32832) | docstring "25 years"; amortised in `h2_storage.py` over `TANK_LIFETIME_YEARS` | IN |
| Tank replacement | Not stated for the tank (Table 5 notes give replacement counts for battery, fuel cell, electrolyser, generator, and "No replacements" for PV; the two tank rows carry only volume and mass). Derived: 15,652 kg ÷ (25 y × 171,540 kWh/y) = 3.650·10⁻³ kg/kWh — the printed value — so the tank is charged **once** in 25 y | "never replaced" | IN (derived from the arithmetic, not from a sentence) |
| Vessel volume | 21.6 m³ (p. 32825, Table 5) | 21.6 | IN |
| Vessel pressure | "maximum pressure of 28 bar" (p. 32825) | 28 bar, taken as the stored-gas pressure | IN-DIFFERS in wording only: the paper says *maximum*; it never states a minimum pressure or a kg capacity, so the module's 50.04 kg H₂ (28 bar, 15 °C, Z = 1.017, 2.317 kg/m³ × 21.6 m³) is the gross content, an upper bound on usable capacity |
| Annual load / per-kWh figure | Total electrical load 171.54 MWh/year (Table 2, p. 32826); 3.65·10⁻³ kg steel/kWh (Table 5) | docstring "171.5 MWh/y … 3.65e-3 kg/kWh, their Table 5" | IN (171.54 rounds to 171.5) |
| Steel per kg H₂ | not in the paper | 15,652 / 50.04 = 312.8 kg/kg (`steel_kg_per_kg_h2()`) | derived in the module; arithmetic checked |
| Paper's own tank carbon | H₂ storage **0.0155 kg CO₂ eq./kWh** of the 0.197 total (Fig. 7, p. 32831); O₂ storage 0.0078 | not transcribed | Cross-check: 0.0155 / 3.65·10⁻³ = **4.25 kg CO₂e per kg chromium steel** (ecoinvent 3.7 APOS, EF 3.0 climate change). The study scores the same market at 5.10 kg/kg (CUTOFF_RULE_PLAN.md:205; DATA_GAPS tank 63.8 kg/kg-yr × 25 / 312.8 = 5.10) on 3.9.1 apos, IPCC 2021 — +20 %, the version/method difference. The module reproduces the paper's line |
| Frame, pad, rebar | not in the paper | 10 % of shell (31.3 kg/kg), 0.238 m³ concrete/kg, 23.8 kg rebar/kg, graded ASSUMED | NOT in source — the module says so ("No paper itemises a pressure vessel's skid or pad") |
| "as-built" | The paper never says the mass is as-built; the row has no citation and the O₂ mass is exactly half of it | `note: "as-built 21.6 m3 stainless vessel at Ginostra"` | IN-DIFFERS (wording): "as modelled by Gandiglio" is what the source supports |
| System model | "Alloc Rec, S" = ecoinvent 3.7 APOS, SimaPro, EF 3.0 (pp. 32826–32827) | 3.9.1 apos, IPCC 2021 | consistent allocation; different version/method (above) |

## Hydrogen chain beyond the tank — what the paper could source for the cut-off candidates

The paper's whole hydrogen chain is three inventory lines plus the O₂ tank and the
helicopter: electrolyser (row 8, a literature kWe figure from an alkaline *fuel
cell* paper), fuel cell (row 7, ecoinvent's 2 kW stack), H₂ tank (row 9). **There
is no compressor row, no valve, no pipework, no gas-handling, no power
electronics, no foundation, no end-of-life.** The system description (p. 32825)
says only: 50 kW alkaline electrolyser, 50 kW PEM fuel cell "available as 25 kW
modules", 21.6 m³ / 28 bar H₂ tank, 10.8 m³ O₂ tank, 47 kW diesel back-up. No
compressor is mentioned anywhere (an alkaline unit at ≤30 bar feeds the 28 bar
vessel directly, which is the module's own reading: `TANK_COMPRESSION_KWH_PER_KG`
= 0 for this design).

So for the register's tank rows — *forming of the vessel steel*, *valves and
pipework*, *compressor hardware* — Gandiglio 2022 supplies **nothing**: they are
MISSING in the source as well as in the module, and the cut-off test (not a
source) has to carry them. The one number the paper does give that the register
can use is the helicopter row (delivery), which is BOUNDARY here.

## Tank cost (TODO.md item "Check Gandiglio et al. 2022 for a tank cost")

**No.** The paper is LCA-only; no cost, price or capex appears for any component
(searched the text for cost/€/EUR/capex: the only economic statements point to
the companion techno-economic study, "[33] Marocco P, Ferrero D, Gandiglio M, …
A study of the techno-economic feasibility of H2-based energy storage systems in
remote areas. *Energy Convers Manag* 2020;211:112768", pp. 32825–32826, 32832).
The supplementary file has no cost either. That companion paper is **not** in
`sources/` (checked: the folder has `Bionaz 2022 remote h2 storage system lca.pdf`
from the same group, and the two Gandiglio files). The TODO item can be closed as
"no cost in Gandiglio 2022; the vessel's capex, if the REMOTE partners published
one, is in Marocco et al. 2020 (ECM 211:112768), not held".

## Claims to check

1. `h2_tank.py:72` and the activity comment call the vessel "as-built". The
   paper gives mass and volume with no provenance, and the O₂ tank is exactly
   half the H₂ tank's mass. Reword to "as inventoried by Gandiglio".
2. The paper's "maximum pressure of 28 bar" is read as the stored pressure; no
   minimum pressure is given, so 50 kg is gross content, not usable capacity.
   The module's `capacity_kg()` docstring could say "gross".
3. SOURCES.md:1003 says Gandiglio's fuel cell is "inventoried as ecoinvent's
   2 kW stack alone" — confirmed (row 7), and on the *Cut-off* model while the
   rest of their Table 5 is APOS.
4. The paper states the H₂ storage line at 0.0155 kg CO₂e/kWh (Fig. 7). The
   study's factor is 20 % above the paper's implied 4.25 kg/kg; worth one line
   in SOURCES.md as the reproduction check.

## Summary

- The module transcribes the paper's single tank line exactly (15,652 kg
  chromium steel 18/8 GLO market, 21.6 m³, 28 bar, 25 y, charged once), from
  Table 5 (p. 32828) — the table number is now right. The paper's own carbon for
  that line, 0.0155 kg CO₂e/kWh (Fig. 7), implies 4.25 kg CO₂e/kg steel against
  the study's 5.10 on a newer database and method.
- Gandiglio give no tank cost; their economics are in Marocco et al. 2020, which
  the study does not hold. Close the TODO item that way.
- The paper inventories nothing for forming, valves, pipework, compressor,
  foundations or end-of-life, for the tank or for any other hydrogen component,
  so it cannot source any of the tank's cut-off candidates.
- Two small wording issues: "as-built" is the module's word, not the paper's;
  "28 bar" is the paper's *maximum* pressure, so 50 kg is gross content.
- The O₂ tank (row 10) and the helicopter (row 11) are the only other
  tank-related rows: not applicable and boundary respectively.

---

# Mehmeti et al. 2018 — ledger (22 Oct 2026)

A. Mehmeti, A. Angelis-Dimakis, C. Boigues Muñoz, M. Graziadio, S.J. McPhail,
"Eco-thermodynamics of hydrogen production by high-temperature electrolysis using
solid oxide cells", *J. Clean. Prod.* 199 (2018) 723–736,
doi 10.1016/j.jclepro.2018.07.166.

Files read (pages): `mehmeti soec heat.pdf`, 14 pp = journal pp. 723–736, all read
(Table 1 on p. 726, §2.2 on pp. 725–727, Table 2 on p. 730, §3.4 on p. 732).
`mehmeti soec heat.xlsx` (Appendix A), sheets 'Title page', 'List of Tables',
'LCA-ReCiPe 2016' (Tables A1–A8 by electricity pathway), 'Endpoint analysis',
'LCA-SED', 'LCA-CEENE', 'Manufacturing' (A34–A36) — A1 and A2 read in full, the
manufacturing sheet scanned.

Modules: `optimisation/electrolysers.py` lines 135–152 (`SOEC_HEAT_SOURCES`,
`SOEC_HEAT_DEFAULT`, `ELECTRIC_BOILER_EFFICIENCY`, the comment block) and
`with_heat_source()` lines 266–294; `optimisation/SOURCES.md` line 966 ("SOEC
external heat") and 967.

## Table 1 (p. 726), "Input-output flows for production of 1 kg of hydrogen with high-temperature solid oxide electrolysis (SOEC)" → SOEC heat row

| # | Source row (as printed) | Amount | Unit | Module (name, amount) | Disposition | Note |
|---|---|---|---|---|---|---|
| 1 | Operation — Deionized water | 10.84 | kg | — | NOT-APPLICABLE (the study's SOEC consumables come from Gerloff 2021; only the heat row is taken from Mehmeti) | |
| 2 | Operation — Electricity supply ᵃ | 40.3 | kWh | — | NOT-APPLICABLE (electricity is the LP's own) | ᵃ Grid = *Electricity, medium voltage, at grid/IT*; the other seven pathways listed |
| 3 | **Operation — Heat, Natural gas, at boiler modulating** | **5.24** | **kWh** | `electrolysers.py:135` "SOEC's 5.24 kWh/kg of external heat"; SOURCES.md:966 "18.864 MJ (5.24 kWh)/kg H₂" | **IN** | 5.24 × 3.6 = 18.864 MJ exactly. The dataset name is an ecoinvent-2 name with **no boiler size** (<100 kW / >100 kW not stated) |
| 4 | Products/Services — Hydrogen, at SOEC plant | 1 | kg | functional unit 1 kg H₂ | IN | "at the plant gate … compression, storage, and delivery pathways are not taken into account" (p. 725) |
| 5 | By-Product — Oxygen, at SOEC plant | 7.8 | kg | — | NOT-APPLICABLE | "released into the environment; hence, no multi-functionality" (p. 725) |
| 6–17 | Stack — YSZ 4.41·10⁻⁴ kg, LSM 2.64·10⁻⁴, NiO 2.22·10⁻⁴, ethanol 6.49·10⁻⁴, PEG 1.30·10⁻⁴, 1-butanol 7.35·10⁻⁵, phthalic anhydride 7.35·10⁻⁵, chromium 8.10·10⁻³, chromium steel 18/8 4.68·10⁻³, sheet rolling chromium steel 4.68·10⁻³, electricity UCTE 1.90·10⁻⁴ MWh, alumina-silica insulation 1.30·10⁻³, transport 3.19·10⁻³ tkm | per kg H₂ | | — | NOT-APPLICABLE (capital good is Gerloff's) | Stack life 5 y, scaled linearly from a generic SOFC inventory (Staffell 2012; Mehmeti 2018b) |
| 18–30 | BoP — reinforcing steel 1.32·10⁻⁴, sheet rolling steel 1.32·10⁻⁴, chromium 5.39·10⁻⁴, aluminium 5.82·10⁻⁵, copper 2.81·10⁻⁴, electricity 1.15·10⁻⁶ MWh, transport 2.02·10⁻⁴ tkm, heating/sanitary cogen unit 1.17·10⁻⁶ MJ, construction work cogen 5.46·10⁻⁶ unit, light fuel oil boiler 1.30·10⁻² MJ, building multi-storey 4.90·10⁻⁶ m³, building hall 8.07·10⁻⁷ m² | per kg H₂ | | — | NOT-APPLICABLE | BoP life 20 y, scaled with exponent 0.7 |

## Parameters — each against the module and SOURCES.md:966

| Parameter | Source (page, words) | Module / SOURCES.md | Disposition |
|---|---|---|---|
| Heat before degradation | p. 727: "this equals to 36 kWh/kgH2 for the electrical side and **4.75 kWh/kgH2 (assuming an efficiency of the heat exchange of 95%)** for the heating side" | SOURCES.md:966 "gives 4.75 kWh/kg" | IN |
| Degradation uplift | p. 727: "The average stack degradation rate was assumed to be **0.5% per 1,000 h**. Thus, energy requirements in terms of electricity and heat are 40.3 kWh/kgH2 and **5.24 kWh/kgH2**, respectively." | SOURCES.md:966 "raised to 5.24 for 0.5 %/1,000 h degradation"; module 5.24 | IN. Note the uplift is +10.3 % on heat (5.24/4.75) and +11.9 % on electricity (40.3/36); the paper does not show the derivation |
| What the heat is for | p. 727: "the only external thermal power needed in the system is the one necessary to heat the inlet flows from room temperature to the nominal operating temperature of the stack (i.e. **750 °C**)"; operating point "the thermo-neutral voltage at 750 °C with an inlet gas composition of 80 mol% H2O and 20 mol% H2 and a conversion rate of 83%" (pp. 726–727), 1.286 V, 0.7 A/cm², 121 cm² cells, 1320 cells, 143.8 kW stack / 150 kW with BoP, 100 kg H₂/day, steam inlet 1,086 kg/day | `electrolysers.py:146` "resistance heating reaches the ~750 °C stack inlet"; SOURCES.md:966 "heating the stack inlet flows to 750 °C at 95 % heat-exchange efficiency" | IN. Thermoneutral operation means the stack's Joule heat covers the reaction endotherm; the 5.24 kWh is feed preheat net of 95 % recuperation |
| Heat-exchange efficiency | 95 % (p. 727, quoted above) | SOURCES.md:966 "95 % heat-exchange efficiency" (not in the module, which needs only the 5.24) | IN |
| Dataset the heat is supplied from | Table 1: "Heat, Natural gas, at boiler modulating" — no size, ecoinvent-2 naming (the whole table uses v2 names although §2.2 says "Ecoinvent database (v.3)") | SOURCES.md:966: *heat production, natural gas, at boiler modulating >100kW* [Europe without Switzerland], "that dataset's v3 successor … >100kW because a 1 MW SOEC draws ~124 kW of heat" | SUBSTITUTED, documented. Check of the size argument: Mehmeti's own plant (100 kg/day) draws 100/24 × 5.24 = **21.8 kW** of heat, so for *their* plant the <100 kW unit is the match; the study's 1 MW SOEC draws 1000/40.3 × 5.24 = 130 kW (124 kW at the study's 42.3 kWh/kg), so >100 kW is right for the study. Worth one clause in SOURCES.md |
| Mehmeti's own heat-line carbon | xlsx sheet 'LCA-ReCiPe 2016', block **A1 GRID**, row "Global warming, GWP, kg CO₂-eq": Mfg. Stack 0.368618 \| Mfg. BoP 0.042724 \| Electricity supply 23.449888 \| Maintenance 0.077819 \| **Heat supply 1.293596** \| Water supply 0.008801 \| TOTAL 25.241447. The heat column is 1.293596 in every pathway block (A2 COAL checked) | SOURCES.md:966 "Mehmeti's own heat line is 1.294 kg CO₂e/kg H₂ (0.0686/MJ, supplementary Table A1), against 1.417 here" | IN. 1.293596 / 18.864 = **0.06857 kg/MJ** → 0.0686 ✓. The study's 0.0751 kg/MJ (1.417 kg/kg) is +9.5 %, the v2→3.9.1 and boiler-size difference. The paper's Table 2 (p. 730) prints the grid total as 25.64, the SI as 25.24 — a 1.6 % mismatch inside the source, not in the heat column |
| Heat share of the study's SOEC variable burden | — | SOURCES.md:966 "Heat is still 87 % of SOEC's 1.632 kg/kg" (1.417/1.632 = 86.8 %) | arithmetic IN |
| Electric-boiler scenario, 0.99 | not Mehmeti's (Danish Energy Agency) | `ELECTRIC_BOILER_EFFICIENCY = 0.99`, SOURCES.md:967 | NOT-APPLICABLE to this source |
| Stack / BoP life | 5 y / 20 y (p. 727) | not used (Gerloff's capital) | NOT-APPLICABLE |
| §3.4 on the heat (p. 732) | "a fraction of energy is supplied as heat, affecting global warming, photochemical oxidant formation … since natural gas is used to provide process heat in the reference case … Shifting from combined natural gas and electric to an all-electric hydrogen production plant will be associated with the increased electricity usage" | the module's `electric_boiler` scenario is exactly this shift | consistent |

## Claims to check

1. SOURCES.md:966 attributes the ">100kW" choice to the study's 1 MW draw; add
   that Mehmeti's own 21.8 kW plant would take the <100 kW unit, so the size is
   the study's judgement, not the source's.
2. SOURCES.md:966 says Gerloff 2021 "carried the 5.24 kWh but modelled it on
   heat, district or industrial, other than natural gas" — not checkable here
   (Gerloff not in this brief); the Mehmeti side of the sentence is confirmed.
3. The paper's electricity figure (40.3 kWh/kg, 36 before degradation) is
   tied to the same operating point as the heat (83 % conversion, 80/20 inlet,
   thermoneutral at 750 °C). The study pairs Mehmeti's heat with Gerloff's
   electricity; if Gerloff's stack runs at a different conversion or inlet
   ratio the preheat duty would differ. State the pairing in SOURCES.md.
4. Minor: the paper's abstract/Table 2 GWP for the Italian grid (25.64) and the
   SI's Table A1 total (25.24) disagree; irrelevant to the heat column, which is
   identical across all eight pathway blocks.

## Summary

- Every figure the module and SOURCES.md take from Mehmeti is in the source and
  transcribed correctly: 4.75 kWh/kg at 95 % heat-exchange efficiency to heat
  the inlet flows to 750 °C, 5.24 kWh/kg (= 18.864 MJ) after 0.5 %/1,000 h
  degradation (Table 1 p. 726; §2.2 p. 727), supplied from "Heat, Natural gas,
  at boiler modulating", and the SI's own heat-supply line 1.293596 kg CO₂e/kg
  H₂ = 0.0686 kg/MJ (Table A1).
- The only judgement that is the study's rather than the source's is the boiler
  size (>100 kW): right for a 1 MW SOEC, but Mehmeti's own 100 kg/day plant
  draws 21.8 kW. Say so.
- Mehmeti's boundary is the plant gate; compression, storage and delivery are
  excluded — matching how the study uses the row.

---

# Vestas V162-6.2 MW LCA — ledger (22 Oct 2026)

Vestas Wind Systems A/S, *Life Cycle Assessment of Electricity Production from an
onshore EnVentus V162-6.2 MW Wind Plant*, authors S. Mali, P. Garrett, version
1.0 dated 31.01.2023 (reviewed final version 1.1, 31 January 2023), reference
year 2021, CML 2016, GaBi/Sphera 2021 background. Baseline plant (p. 12): 16 ×
6.2 MW = 99.2 MW, hub 149 m, low (IECS) wind 7.4 m/s, Germany, 20 km to a 110 kV
grid, 21,568 MWh per turbine per year (CF 39.7 %), 6,902 GWh per plant over 20 y.
GWP 6.2 g CO₂e/kWh (manufacture 9.1, plant set-up 0.0, operation 0.3,
end-of-life −3.2; Table 9 p. 48); 430 t CO₂/MW plant, 313 t/MW turbine-only
(pp. 14, 47).

Files read (pages): `vestas lca 6.2MW wind.pdf`, 113 pp. Read in full as text:
executive summary pp. 12–16, §3.2 pp. 27–28, §3.3 p. 30, §3.4 pp. 31–35, §5.1
Fig. 7 p. 47 (rendered image, segments measured), Table 9 p. 48, §5.2.6 p. 54,
§5.2.9–5.3.2 pp. 57–60, §6 p. 66, §7.2.2 p. 71, §7.2.3 p. 72, §7.2.5 pp. 73–74,
§7.2.8 p. 76, Annex B.10–B.12 p. 91, Annex F.3, Annex G p. 107. Other pages
grepped only.

Modules: `optimisation/renewables.py` lines 118–165 (`WIND_SERVICING_FRACTION_PER_20Y`
= 0.04, `WIND_OVERHAUL_FRACTION` = 0.205, `WIND_DESIGN_LIFE_YEARS` = 25,
`wind_parts_fraction()`); `docs/CUTOFF_RULE_PLAN.md` "The rule" (lines 21–110,
Vestas cited at 60 and 107–108).

## §3.3 Cut-off criteria (p. 30) → CUTOFF_RULE_PLAN.md "The rule"

Quoted exactly, in full:

> **3.3 Cut-off criteria**
> The following cut-off criteria were used to ensure that all relevant potential
> environmental impacts were appropriately represented:
> • Mass – if a flow is less than 0.1% of the mass at a product-level, then it
> may be excluded, provided its environmental relevance is not of concern.
> • Energy – if a flow is less than 1% of the energy at a product-level, then it
> may be excluded, provided its environmental relevance is not a concern.
> • Environmental relevance – if a flow meets the above criteria for exclusion
> but is considered to potentially have a significant environmental impact, it
> has been included. All material flows which leave the system (emissions) and
> whose environmental impact is higher than 1% of the whole impact of an impact
> category that has been considered in the assessment, shall be included.
> • The sum of the neglected material flows shall not exceed 5% of total mass,
> energy, or environmental relevance, at a product-level.
> Over 99.4% of the total mass of materials in the EnVentus V162-6.2 MW turbine
> (i.e. covering all parts of the turbine-only, excluding foundation, site cables
> and site parts) have been accounted for, covering around 25,000 components that
> make-up the entire turbine. Scaling of the turbine up to 100% of total mass has
> not been conducted. Additionally, all site parts, foundations and cables are
> also included in their entirety for the complete wind power plant. As such, the
> LCA includes all materials and all components of environmental significance,
> with over 99.7% of the entire power plant accounted for by mass. The
> cut-off-criteria applied in the secondary data is addressed in the respective
> documentation (Sphera 2021).

| # | Source statement | Plan's rule | Disposition | Note |
|---|---|---|---|---|
| 1 | Mass: < 0.1 % of product mass may be excluded | not used ("not their mass and energy screens") | NOT-APPLICABLE by choice | Vestas's mass screen is **0.1 %**, not 1 % |
| 2 | Energy: < 1 % of product energy may be excluded | not used | NOT-APPLICABLE by choice | |
| 3 | Environmental relevance: emissions > 1 % of the whole impact of a category shall be included | Rule 1: unsourced flow may stay out only if < 1 % of its technology's carbon | IN-DIFFERS: Vestas's 1 % is for *material flows which leave the system (emissions)*, per impact category, per product; the plan applies it to unsourced *inputs* (capital flows) per technology, GWP only. The number matches, the object differs — say "adapted from" rather than "uses" | The plan's "per technology" is a fair reading of "at a product-level" |
| 4 | Sum of neglected flows ≤ 5 % of mass, energy or environmental relevance at product level | Rule 2: all unsourced flows together < 5 % of the technology's carbon | IN (same number, same per-product sum; GWP standing in for "environmental relevance") | |
| 5 | 99.4 % of turbine mass, 99.7 % of plant mass accounted for; no scaling to 100 % | — | context | Shows what "under 1 % / 5 %" meant in practice: Vestas left ~0.3–0.6 % out |
| 6 | Annex G p. 107: "A mass cut-off has been applied to Table G1 in order to limit the number of flows presented" | — | NOT-APPLICABLE (presentation, not inventory) | Do not cite Annex G as a cut-off rule |

The plan (line 79) says "Rules 1 and 2 are the per-technology tests PAS 2050 and
Vestas set" — on Vestas's wording, rule 2 is theirs; rule 1 is their
emissions-relevance clause transplanted to inputs. The plan's own line 108
("read in full, 20 Oct") is borne out; the wording above is what to quote.

## Fig. 7 (p. 47; same chart in the executive summary p. 14), "Production and use-phase environmental impacts of V162-6.2 MW" → `renewables.py` servicing and overhaul shares

The chart is a stacked 100 % bar per impact category with **no printed numbers**;
the shares below are measured from the rendered page at 400 dpi (segment width ÷
bar width; ±0.5 % each; the ten segments sum to 99.3 %, the rest is boundary
pixels). Basis: "all life cycle stages excluding end-of-life" (p. 47), i.e.
manufacture 9.1 + set-up 0.0 + operation 0.3 = 9.4 g CO₂e/kWh.

GWP bar, left to right (legend order):

| Segment | Measured share of production + use GWP | Module | Disposition |
|---|---|---|---|
| Site parts | 2.8 % | — | — |
| Installation/decommissioning | 0.9 % | — | — |
| Foundation | 15.9 % | — | — |
| Tower | 36.9 % | — | — |
| Nacelle | 8.9 % | — | — |
| **Gear & mainshaft** | **8.0 %** | `renewables.py:133` "8 % … for the V162 (Fig 7)" | **IN** |
| Hub | 5.0 % | — | — |
| **Blades** | **15.0 %** | `renewables.py:133` "15 % for the V162 (Fig 7)" | **IN** |
| Vestas factories | 1.9 % | — | — |
| **Replacements/servicing** | **4.0 %** | `renewables.py:127–128` "V162-6.2 MW 2023 Fig 7, 4.0 %"; `WIND_SERVICING_FRACTION_PER_20Y = 0.04` | **IN** |

Corroboration from the text: Table 9 (p. 48) operation 0.3 g of 9.4 g = 3.2 %
(2.7–3.8 % within the table's one-decimal rounding), where "operation: includes
power plant maintenance, servicing, and transport" (p. 47) and "Site servicing
and operations (including transport): serviced parts, such as oil and filters,
and replaced components (due to wear and tear of moving parts within the
lifetime of a wind turbine) are included" (p. 24); crew transport 1,500 km per
plant per year (p. 35). §7.2.3 (p. 72): doubling replacement parts raises GWP
by ~1–6 % (all categories 1–11 %), halving lowers by 1–6 % — consistent with a
~4 % share. The module's "operation at 1.8–5.3 % of manufacturing across
V90-2.0 to V162" is 3.3 % for the V162 (0.3/9.1); the V90/V136 reports are not
in `sources/`, so the V136 half of the 20.5 % midpoint (9 % + 9 %) **could not
be checked**.

| # | Source statement | Module | Disposition | Note |
|---|---|---|---|---|
| 1 | Fig. 7 replacements/servicing 4.0 % of production+use GWP over 20 y | servicing 4 % per 20 operating years, pro rata | IN | |
| 2 | Fig. 7 gear & mainshaft 8.0 %, blades 15.0 % | overhaul = V162 (8 + 15 = 23 %) and V136 (9 + 9 = 18 %) midpoint 20.5 %, ASSUMED | IN for the V162 numbers; the overhaul itself is the study's construction — Vestas model no life extension | §5.2.6 text (p. 54) gives a *different* breakdown of GWP: "tower (34%), foundations (16%), blades (13%), gear and mainshaft (11%), nacelle (9%), and cables (2%)" — a different denominator/grouping (gear & mainshaft 11 % vs 8 %, blades 13 % vs 15 %). On that basis the V162 pair is 24 % instead of 23 %; the 20.5 % midpoint would move to 21 %. Record both |
| 3 | §7.2.2 (p. 71): lifetime sensitivity ±4 y with "No account … for changes to replacement parts and servicing" | the module scales servicing pro rata and adds an overhaul past 25 y | IN-DIFFERS by design: Vestas hold parts fixed when they vary life; the study does not | |

## Design life

| Source statement (page) | Module | Disposition |
|---|---|---|
| Baseline table (p. 12): "Lifetime, years, 20"; functional unit "based on the design lifetime of the power plant (of 20 years)" (p. 12) | `renewables.py:139` "(Vestas state 20)" | IN |
| §3.4.1 (p. 31): "The lifetime of the wind plant is assumed to be 20 years. This corresponds to the design lifetime of the EnVentus V162-6.2 MW turbine and applies to all components of the wind plant, except for certain replacement parts. … Vestas has direct knowledge of a number of its turbines exceeding the design lifetime of 20 years. Additionally, other site components such as the site cabling and foundations may have a significantly longer useful lifetime (around 50 years)." | `WIND_DESIGN_LIFE_YEARS = 25` (Siemens Gamesa's), with the Vestas figure noted | IN-DIFFERS by documented choice (25 vs 20); the 50-y cabling/foundation remark supports not overhauling those parts |
| §3.2.3 (p. 28): "The time period for service/maintenance represents the typical 20-year design life." | servicing 4 % *per 20 years* | IN — the 4 % is a 20-y quantity, pro-rating it is the study's step |
| §6 (p. 66): Roaring 40s V90-3.0 MW plant "calculated lifetime of the turbine to be 24 years"; exec summary (p. 15): "some turbines reaching operational lives of 30 years and over" | — | context for the 35-y amortisation |
| §7.2.2 (p. 71): "The lifetime of a wind power plant is designed for 20 years; however, this may vary … and could be up to 30 years lifetime or over"; ±4 y → +25 % / −17 % per kWh | — | context |

## Transport to site

| Source statement (page) | Study | Disposition |
|---|---|---|
| §3.2.1.2 (p. 27): "Wind plant set up: This phase includes transport of wind plant components to site and installation and erection"; Table 9 basis (p. 47): "manufacture: includes raw material extraction through to factory gate **and transport to site**" | delivery to site excluded (site unknown) | BOUNDARY — Vestas include it, the study does not |
| §3.4.8 Table 4 (p. 34), Vestas factories → site, European plant, 2021 average sales: Nacelle 600 km truck + 9,000 km ship; Hub 600 + 8,600; Blades 1,450 + 5,100; Tower 425 + 0; Foundation 50 + 0; Other site parts 600 + 0. Upstream: raw materials to suppliers 600 km truck (concrete 50 km); large components to Vestas factories 600 km truck (90 % of turbine mass); end-of-life 200 km (concrete 50 km); crew 1,500 km/plant/yr; business flights (p. 35) | upstream transport is in scope (inside ecoinvent's turbine where it carries it) | the upstream legs are IN-scope items; only the factory-to-site leg is BOUNDARY |
| Magnitude: "Transport of the turbine components contributes between around 1% and 40% across all impact categories, and 10% to the total global warming potential impacts" where "Transport refers to the aggregated impacts covering all transport stages" (p. 13, fn 2); §7.2.5 (pp. 73–74): Australian sourcing −1 to −4 % (GWP +1–2 %), USA +0.03 to 6 %; "the baseline scenario represents a conservative assumption" (p. 74) | — | CUT-OFF-INPUT for the boundary note: all transport stages ≤ 10 % of a wind plant's GWP, delivery-to-site a fraction of that (bounded by the ±6 % swing between continents) |

## Other items the register can use

| Source statement (page) | Use | Disposition |
|---|---|---|
| §3.4.5 SF₆ (p. 33): "Each turbine contains switchgears, and they are also used onsite for connecting the turbines and transformer substation … the turbine switchgear may potentially release up to 0.1% w/w of the sulphur hexafluoride per year, accounting for a potential 2% w/w total release over 20 years"; EoL: ≤1 % released in reclamation, 95 % of switchgears returned, 5 % vented. §5.2.6 (p. 54): SF₆ "0.0003%" of GWP. §7.2.8 (p. 76): blow-out 1 in 2,000 switchgears → ~100 g SF₆ per 16-turbine plant, "below 0.01% of the total global warming potential" | switchgear rows in the cut-off register (Teffera's switchgear carries no SF₆ flow, see below) | CUT-OFF-INPUT: SF₆ from turbine/site switchgear is < 0.001 % of wind GWP in normal operation |
| B.11 (p. 91): "A 110 MVA transformer has been included in the wind plant. The transformer is modelled from an EPD from ABB on a Power transformer 250 MVA and scaled down to 110 MVA"; but B.10 (p. 91) says the cables connect "the turbine plant and the 60 MVA transformer", and F.3 says "scaled down from 250MVA to 100MVA to represent the requirements of the 100MW wind plant" | SOURCES.md:730 "Vestas' 60 MVA for a 100.8 MW plant (0.595) is the outlier" | IN-DIFFERS: the report gives three ratings (60, 110, 100 MVA) for a 99.2 MW plant (16 × 6.2; "100.8" is not in the report). On B.11's 110 MVA the ratio is 1.11, in line with Leng and Teffera — the "outlier" rests on the B.10 figure alone |
| B.10 (p. 91): 24 km of 33 kV aluminium PEX site cables; 20 km of 110 kV 630 mm² cable to grid; §3.4.2 (p. 31): electrical losses 2.5 % to grid incl. transformer station and site cables, wake 6 %, availability 98 % | `profiles.WIND_NET_FACTOR` cites "Vestas 2.5 %" | IN (p. 31 and p. 12 note) |

## Claims to check

1. `renewables.py:127` cites "V162-6.2 MW 2023 Fig 7, 4.0 %" — confirmed by
   measurement, but the figure prints no numbers; say "read off Fig 7 (unlabelled
   stacked bar)" so a reader knows the precision (±0.5 %).
2. The §5.2.6 text breakdown (gear & mainshaft 11 %, blades 13 %) disagrees with
   the Fig 7 segments (8 %, 15 %). Either basis gives 23–24 % for the V162; note
   both so the 20.5 % midpoint is traceable.
3. The V136-4.2 MW report (9 % + 9 %) is not in `sources/`; the other half of
   `WIND_OVERHAUL_FRACTION` is unchecked here.
4. CUTOFF_RULE_PLAN.md:60 "uses the impact criteria of PAS 2050 and Vestas V162
   §3.3": Vestas's 1 % clause is about emissions per impact category; the plan
   transplants it to unsourced inputs. "Adapted from" is the honest verb.
5. SOURCES.md:730's "60 MVA for a 100.8 MW plant" — the report's own §B.11 says
   110 MVA and the plant is 99.2 MW.

## Summary

- §3.3 (p. 30) is quoted in full above. Its criteria are mass 0.1 %, energy 1 %,
  emissions > 1 % of a category must be in, neglected sum ≤ 5 % — all "at a
  product-level". The plan's 5 % sum is Vestas's; its 1 %-per-flow is an
  adaptation of the emissions clause to inputs.
- The three Fig 7 shares the module transcribes for the V162 — replacements/
  servicing 4.0 %, gear & mainshaft 8 %, blades 15 % of production + use GWP —
  are confirmed by measuring the unlabelled chart (p. 47). The §5.2.6 text gives
  11 % and 13 % for the same two parts on another basis.
- Design life 20 y is stated repeatedly (pp. 12, 28, 31, 71), with cabling and
  foundations ~50 y and lives "up to 30 years … or over" acknowledged; the
  module's 25 y is a documented departure.
- Vestas include transport to site (Table 4 distances) inside "manufacture";
  all transport stages are 10 % of GWP, so the study's delivery-to-site
  exclusion is bounded well under that.
- The report contradicts itself on the plant transformer (60 / 110 / 100 MVA);
  SOURCES.md's "outlier" remark uses the least-supported figure.

---

# Teffera et al. 2021 — ledger (22 Oct 2026)

B. Teffera, B. Assefa, A. Björklund, G. Assefa, "Life cycle assessment of wind
farms in Ethiopia", *Int J Life Cycle Assess* 26 (2021) 76–96, doi
10.1007/s11367-020-01834-5. Three farms, 324 MW (ASWF 120 MW, AWF I 51 MW,
AWF II 153 MW), ecoinvent 3.01 "allocation, default, recycled content" (cut-off),
SimaPro 8.0.3.14, ReCiPe 2008 H midpoint, 20-y life, 33.6 g CO₂e/kWh.

Files read (pages): `teffera ethiopia wind farm LCA.pdf`, 21 pp = journal
pp. 76–96, all read; Tables 1–2 (p. 78) also from a rendered image; Table 5
(pp. 84–86) transcribed from the text layer and checked row-count against the
printed table.

Modules: `optimiser_lca/stepup_transformers.py:164` (`TX_TURBINE_TERMINAL_V =
690.0`, "TRANSCRIBED - Teffera Table 2, all four models"), :47–49 and :520–521
(cross-check against Table 5), :201–204 ("Teffera's equivalent inventory is
steel and copper only"); `optimisation/transformers.py:77–83, 104–107, 155–158`;
`optimisation/SOURCES.md:719–731, 752–757`; `optimisation/DATA_GAPS.md:53, 97`;
`docs/CUTOFF_RULE_PLAN.md:203–209, 240–241, 322` ("Teffera 0.61 t/MW switchgear
vs 1.08 t/MW transformer").

## Table 2 (p. 78), "Summary of relevant technical data of wind turbines in Ethiopian wind energy systems" → `TX_TURBINE_TERMINAL_V`

| # | Parameter (as printed) | GV HP (ASWFᵃ) | ECO 74 (ASWFᵃ) | GW77/1500 (AWF Iᵇ) | SE7715 (AWF IIᶜ) | Module | Disposition |
|---|---|---|---|---|---|---|---|
| 1 | Axis of rotation | Horizontal | Horizontal | Horizontal | Horizontal | — | — |
| 2 | Number of wind turbines | 30 | 54 | 34 | 102 | — | — |
| 3 | Number of blades | 2 | 3 | 3 | 3 | — | — |
| 4 | Rotor diameter, m | 62 | 74 | 77 | 77 | — | — |
| 5 | Hub height, m | 70 | 80 | 65 | 70 | — | — |
| 6 | Rated power, kW | **100** (sic) | 1670 | 1500 | 1500 | — | source typo: the text (p. 78) says "the 30 1 MW GEV HP turbines", and 30 × 1 + 54 × 1.67 = 120.2 MW = Table 1's 120 MW; read 1,000 kW |
| 7 | **Rated voltage, volts** | **690** | **690** | **690** | **690** | `TX_TURBINE_TERMINAL_V = 690.0` | **IN** — all four models |
| 8 | Cut-in and cut-out wind speeds, m/s | 3, 25 | 3, 25 | 3, 25 | 3, 25 | — | — |
| 9 | Rated wind speed, m/s | 15.5 | 15.5 | 11 | 11 | — | — |
| 10 | Power density, W/m² | 571 | 571 | 654ᵈ | 440 | — | — |
| 11 | Annual average wind speed, m/s | 8.5 | 8.5 | 8.11 | 8.22 | — | — |
| 12 | Wind class as per IEC 61400-1 | Class IIA | Class IIA | Class IIA | Class IIA | — | — |
| 13 | Type of wind turbine generators | DFIG | DFIG | PMDD | DFIG | — | — |

ᵃ Wudu (2015) ᵇ EEP (2017) ᶜ Tadesse (2014) ᵈ Hydrochina (2009). Corroboration in
§3 (p. 79): AWF I "Each wind turbine generator is connected to 33 step-up
transformers through 0.6/1 kV cables"; AWF II "passes through 0.6/1 kV cables to
33 kV box-type transformer" — the LV side is a 0.6/1 kV cable class, consistent
with 690 V.

Transformer sizing stated in §3 (pp. 78–79), used in SOURCES.md:729: ASWF "two
63 MVA transformers" for 120.2 MW (1.048), 230/33 kV; AWF I "a power transformer
of 55 MVA" for 51 MW (1.078), 132 kV, 8 km line; AWF II "two 230 kV step-up
transformers" (rating not given), 78 km of 33 kV line on 403 angle-iron towers,
13 km of 230 kV line on 43 towers. MV collection at ASWF: "two CGM.3
gas-insulated switchgears" and "four CGM.3 gas-insulated MV collection
cubicles" (Ormazabal); HV switchgear air-insulated (GE Grid Solutions) at ASWF.
IN as quoted.

## Table 5 (pp. 84–86), "LCI data of wind power system in Ethiopia per 1 kWh wind electricity" → cross-check band for the step-ups; switchgear and civils estimates in the cut-off register

Whole table transcribed. Per-MW columns are this ledger's conversion: value per
kWh × lifetime kWh per MW, on the two generation bases the paper publishes
(Table 1, p. 78):

- **realized** — 3-year mean 2015–2017 actual generation, (239+198+105)/3 +
  (187+143+100)/3 + (245+418+306)/3 = **647 GWh/y**, CF 0.228, × 20 y ÷ 324 MW =
  **3.994·10⁷ kWh per MW**. The paper states this is the normalisation basis:
  "A 3-year average realized electricity generation and consumption data was
  used to calculate total lifetime electricity generation" (§7 Temporal
  boundaries, p. 82); Fig. 6 caption (p. 91): "relative to the base case (i.e.,
  using 3-year average production)".
- **estimated** — power-curve generation 362 + 157 + 488 = **1,007 GWh/y**, CF
  0.355 (ECF 0.34–0.36), × 20 ÷ 324 = **6.216·10⁷ kWh per MW**.

| Subsystem | Subassembly | Material (as printed) | Unit | Value per kWh | per MW, realized basis | per MW, estimated basis |
|---|---|---|---|---|---|---|
| Wind turbines | Rotor assembly | Cast iron | kg | 1.12E-04 | 4,473 | 6,962 |
|  |  | Glass fiber | kg | 1.06E-04 | 4,233 | 6,589 |
|  |  | Low-alloyed steel | kg | 8.61E-05 | 3,439 | 5,352 |
|  |  | Epoxy resin | kg | 4.93E-05 | 1,969 | 3,064 |
|  |  | Adhesives | kg | 1.03E-05 | 411 | 640 |
|  |  | Chromium steel | kg | 7.85E-06 | 314 | 488 |
|  |  | Electricity, medium voltage | kWh | 3.36E-04 | 13,419 | 20,886 |
|  | Nacelle assembly | Low-alloyed steel | kg | 2.95E-04 | 11,782 | 18,337 |
|  |  | Cast iron | kg | 1.95E-04 | 7,788 | 12,121 |
|  |  | Chromium steel | kg | 6.21E-05 | 2,480 | 3,860 |
|  |  | Copper | kg | 1.70E-05 | 679 | 1,057 |
|  |  | GRP plastic | kg | 1.09E-05 | 435 | 678 |
|  | Tower assembly | Low-alloyed steel | kg | 1.36E-03 | 54,316 | 84,538 |
|  |  | Electricity, medium voltage | kWh | 4.14E-04 | 16,534 | 25,734 |
|  | Transportation | Truck transport | tkm | 2.85E-03 | 113,823 | 177,156 |
|  |  | Ship transport | tkm | 2.56E-02 | 1,022,413 | 1,591,296 |
|  | Construction | Land requirement | m² | 2.27E-04 | 9,066 | 14,110 |
|  |  | Concrete | m³ | 3.58E-06 | 143 | 223 |
|  |  | Reinforcing steel | kg | **2.32E-02** | 926,562 | 1,442,112 |
|  |  | low alloyed steel | kg | 1.02E-04 | 4,074 | 6,340 |
|  |  | Electricity, medium voltage | kWh | 3.26E-05 | 1,302 | 2,026 |
| Internal connection network | **Unit transformer** | Low-alloyed steel | kg | 5.02E-05 | 2,005 | 3,120 |
|  |  | Copper | kg | 3.82E-06 | 153 | 238 |
|  |  | Aluminum | kg | 1.95E-06 | 78 | 121 |
|  |  | Electricity | kWh | 2.28E-03 | 91,059 | 141,725 |
|  |  | Heat, natural gas | MJ | 9.70E-05 | 3,874 | 6,030 |
|  | Cable | Copper | kg | 8.11E-07 | 32 | 50 |
|  | Grounding system | Aluminum | kg | 2.98E-05 | 1,190 | 1,852 |
|  |  | Copper | kg | 5.84E-06 | 233 | 363 |
|  | Transportation | Truck transport | tkm | 7.92E-04 | 31,631 | 49,231 |
|  |  | Ship transport | tkm | 3.95E-03 | 157,755 | 245,532 |
|  | Construction | Land requirement | m² | 3.16E-07 | 12.6 | 19.6 |
|  |  | Concrete | m³ | 5.58E-08 | 2.23 | 3.47 |
|  |  | Reinforcing steel | kg | 6.10E-06 | 244 | 379 |
| MV subsystem | **Collection switchgears** | Low-alloyed steel | kg | 8.93E-07 | 35.7 | 55.5 |
|  |  | Copper | kg | 2.05E-07 | 8.2 | 12.7 |
|  | Earthling system | Low-alloyed steel | kg | 2.90E-05 | 1,158 | 1,803 |
|  | OH conductors | Aluminum, cast alloy | kg | 2.12E-05 | 847 | 1,318 |
|  |  | Low-alloyed steel | kg | 9.58E-06 | 383 | 596 |
|  | Power cables | Copper | kg | 6.86E-06 | 274 | 426 |
|  | Steel poles and gantry | Low-alloyed steel | kg | 1.27E-04 | 5,072 | 7,894 |
|  | Transportation | Truck transport | tkm | 3.81E-04 | 15,216 | 23,683 |
|  |  | Ship transport | tkm | 1.34E-03 | 53,517 | 83,294 |
|  | Construction | Land requirement | m² | 1.43E-05 | 571 | 889 |
|  |  | Concrete | m³ | 9.52E-07 | 38.0 | 59.2 |
|  |  | Reinforcing steel | kg | 1.30E-04 | 5,192 | 8,081 |
| HV subsystem | **Power transformer** | Low-alloyed steel | kg | 1.42E-05 | 567 | 883 |
|  |  | Copper | kg | 3.12E-06 | 125 | 194 |
|  |  | Porcelain | kg | 2.59E-07 | 10.3 | 16.1 |
|  |  | MV Electricity | kWh | 5.83E-04 | 23,284 | 36,239 |
|  | Civil structures | Low-alloyed steel | kg | 3.52E-06 | 141 | 219 |
|  | **Switchgear devices** | Porcelain | kg | 5.05E-06 | 202 | 314 |
|  |  | Steel, low-alloyed | kg | 2.72E-06 | 109 | 169 |
|  |  | Aluminum | kg | 8.37E-07 | 33.4 | 52.0 |
|  |  | Copper | kg | 2.43E-07 | 9.7 | 15.1 |
|  | OH conductors | Aluminum | kg | 1.71E-06 | 68.3 | 106 |
|  |  | Low-alloyed steel | kg | 6.40E-07 | 25.6 | 39.8 |
|  | Earthling system | Low-alloyed steel | kg | 1.54E-06 | 61.5 | 95.7 |
|  | Transmission towers | Low-alloyed steel | kg | 1.74E-05 | 695 | 1,082 |
|  | Grid connection | Porcelain | kg | 6.67E-07 | 26.6 | 41.5 |
|  |  | Low-alloyed steel | kg | 3.68E-07 | 14.7 | 22.9 |
|  |  | Aluminum | kg | 1.20E-07 | 4.8 | 7.5 |
|  |  | Kraft paper | kg | 3.97E-08 | 1.6 | 2.5 |
|  | Transportation | Truck transport | tkm | 8.11E-05 | 3,239 | 5,041 |
|  |  | Ship transport | tkm | 6.09E-04 | 24,322 | 37,855 |
|  | Construction | Land requirement | m² | 2.98E-06 | 119 | 185 |
|  |  | Concrete | m³ | 1.35E-07 | 5.39 | 8.39 |
|  |  | Reinforcing steel | kg | 7.19E-05 | 2,872 | 4,469 |
|  |  | Sand | kg | 3.35E-06 | 134 | 208 |
| Operation and maintenance | Materials for replacement | Glass fiber | kg | 5.26E-05 | 2,101 | 3,270 |
|  |  | Low alloyed steel | kg | 4.24E-05 | 1,693 | 2,636 |
|  |  | Cast iron | kg | 3.15E-05 | 1,258 | 1,958 |
|  |  | Polyester resin | kg | 2.45E-05 | 979 | 1,523 |
|  |  | Chromium steel | kg | 1.20E-05 | 479 | 746 |
|  |  | Adhesives | kg | 5.10E-06 | 204 | 317 |
|  | Transportation | Truck transport | tkm | 1.89E-04 | 7,548 | 11,748 |
|  |  | Ship transport | tkm | 9.51E-04 | 37,981 | 59,114 |
|  | Operation | Mineral oils | kg | 1.76E-04 | 7,029 | 10,940 |
| Waste management (p. 86, negative = to treatment) | Aluminum scrap, post-consumer recycling | Aluminum scrap | kg | −2.80E-06 | | |
|  | Electronics scrap treatment | Electronics scrap | kg | −6.57E-06 | | |
|  | Iron scrap sorting, pressing | Steel scrap | kg | −8.84E-04 | | |
|  | Scrap aluminum municipal incineration | Aluminum scrap | kg | −3.35E-06 | | |
|  | Scrap copper municipal incineration | Copper scrap | kg | −5.76E-06 | | |
|  | Copper scrap recycling | Copper scrap | kg | −1.57E-05 | | |
|  | Scrap steel landfill | Steel scrap | kg | −2.84E-04 | | |
|  | Used cable recycling | Used cables | kg | −3.27E-06 | | |
|  | Waste concrete landfill | Waste concrete | kg | −9.07E-03 | | |
|  | Magnetic steel recycling | Waste permanent magnet | kg | −5.22E-06 | | |
|  | Waste glass landfill | FGR plastic | kg | −2.99E-04 | | |
|  | Waste mineral oil incineration | Waste mineral oil | kg | −3.73E-05 | | |
|  | Waste paperboard incineration | Kraft paper | kg | −1.84E-06 | | |
|  | Waste polyethylene, municipal incineration | Polyethylene | kg | −1.95E-05 | | |
|  | Waste wood incineration | waste wood | kg | −2.73E-06 | | |

Note on Table 5's basis: p. 82 says it is per kWh of the 3-year *realized*
generation. SOURCES.md:723 says the paper "do[es] not say which" — it does
(p. 82 and the Fig. 6 caption, p. 91), although §20 (p. 91) muddles it with a
"36 % to 37 % increase" that reproduces on neither basis (1,007/647 = +56 %).

### The rows the study uses, and how they come out

| # | Source rows | Amount (per kWh → per MW) | Module / plan | Disposition | Note |
|---|---|---|---|---|---|
| 1 | Unit transformer: low-alloyed steel 5.02E-05, copper 3.82E-06, aluminium 1.95E-06 kg | 5.60E-05 kg/kWh → **2,235 kg/MW (realized)**, 3,479 kg/MW (estimated) | `stepup_transformers.py` scores Leng's 2,823 kg/MW; Teffera is the independent check (SOURCES.md:719–726 "228–333 kg CO₂e/MW/year … Leng sits inside that band") | IN as cross-check: Leng's mass sits between the two readings | The band in SOURCES.md is the study's own re-scoring of these three rows over 35 y on the two CF bases — not a number Teffera publish |
| 2 | Unit transformer: *Electricity* 2.28E-03 kWh, *Heat, natural gas* 9.70E-05 MJ | 91,059 kWh and 3,874 MJ per MW (realized) | not transcribed | MISSING in the module, but see note | The electricity row is **0.228 % of every kWh generated** — 26–41 kWh per kg of transformer, 60–100× any manufacturing energy (IEA PVPS: 2,368 kWh / 5,680 kg = 0.42 kWh/kg). It is the size of transformer **losses** (no-load + part of load loss), and Table 4 (p. 83) sources the transformer rows from "Supplier technical drawings and (ABB 2003)", an EPD whose declared impact is dominated by use-phase losses. The heat row, 1.0–1.7 MJ/kg, does match IEA PVPS's 9,904 MJ / 5,680 kg = 1.74 MJ/kg of manufacturing heat. The paper explains neither. The study charges losses in `conversion_losses.py`, so the electricity row is not a missing flow — but it must not be read as factory energy (DATA_GAPS.md:97–98 "wind's transformer carries no factory energy": Teffera is not a source for one, except possibly the gas-heat row) |
| 3 | HV power transformer: low-alloyed steel 1.42E-05, copper 3.12E-06, porcelain 2.59E-07 kg | 1.76E-05 kg/kWh → **702 kg/MW (realized)**, **1,093 kg/MW (estimated)** | CUTOFF_RULE_PLAN.md:209 "1.08 t/MW transformer"; SOURCES.md:754, DATA_GAPS.md:53 "a plant transformer's 1.08 t/MW" | CUT-OFF-INPUT. The plan's 1.08 reproduces on the **estimated** basis; on the paper's stated realized basis it is 0.70 t/MW | 2 × 63 MVA + 55 MVA (+ AWF II's unstated pair) for 324 MW; materials only, no oil, no core "iron" row |
| 4 | HV power transformer: *MV Electricity* 5.83E-04 kWh | 23,284 kWh/MW (realized), 0.058 % of output | not transcribed | same reading as row 2: loss-sized | |
| 5 | MV collection switchgears: low-alloyed steel 8.93E-07, copper 2.05E-07 kg | 1.10E-06 kg/kWh → 44 kg/MW (realized), 68 (estimated) | part of the plan's "0.61 t/MW switchgear" | CUT-OFF-INPUT | CGM.3 **gas-insulated** cubicles, yet **no SF₆ row** anywhere in Table 5; p. 80: "Energy consumption for the manufacturing of components such as cables and switchgear devices like circuit breakers, current and voltage measurement instruments, disconnector, and switches were not included as it is deemed of negligible contribution" — materials only |
| 6 | HV switchgear devices: porcelain 5.05E-06, steel 2.72E-06, aluminium 8.37E-07, copper 2.43E-07 kg | 8.85E-06 kg/kWh → 353 kg/MW (realized), 550 (estimated) | part of "0.61 t/MW" | CUT-OFF-INPUT | 57 % of the mass is porcelain (insulators); materials only; air-insulated at ASWF |
| 7 | **MV + HV switchgear, rows 5 + 6** | 9.95E-06 kg/kWh → **397 kg/MW (realized)**, **618 kg/MW (estimated)** | CUTOFF_RULE_PLAN.md:203, 207, 209; SOURCES.md:754; DATA_GAPS.md:53 "MV plus HV switchgear at 0.61 t/MW"; `transformers.py:106` | CUT-OFF-INPUT. **The plan's 0.61 t/MW reproduces only on the estimated-generation basis (6.216·10⁷ kWh/MW); on the paper's own stated basis it is 0.40 t/MW.** Either way it is a materials-only, SF₆-free floor | For the register's *upper* estimate the 0.61 is the conservative reading and can stay, labelled "Teffera Table 5 at ECF 0.355"; the ratio to the transformer (0.61/1.08 = 0.40/0.70 = 0.57) is basis-independent, so the plan's "~55 %" verdict on the grid connection does not move |
| 8 | HV "Grid connection": porcelain 6.67E-07, steel 3.68E-07, aluminium 1.20E-07, kraft paper 3.97E-08 kg | 1.19E-06 kg/kWh → 48 kg/MW (realized), 74 (estimated) | not in the plan | CUT-OFF-INPUT (bay hardware: bushings/insulators by the look of it; the paper does not define the row) | |
| 9 | HV Civil structures: low-alloyed steel 3.52E-06; HV Construction: concrete 1.35E-07 m³, reinforcing steel 7.19E-05 kg, sand 3.35E-06 kg, land 2.98E-06 m² | steel 141 / 219 kg/MW; concrete 5.4 / 8.4 m³/MW; rebar 2,872 / 4,469 kg/MW; sand 134 / 208 kg/MW (realized / estimated) | CUTOFF_RULE_PLAN.md:210 "Grid connection — Civils — bay foundations, mass × factor" (no source named) | CUT-OFF-INPUT with a **warning**: 7.19E-05 kg rebar against 1.35E-07 m³ concrete is 533 kg of rebar per m³ — five times a heavy reinforcement ratio. The substation buildings are inside the HV system (p. 80), which may explain some of it, but see the next row |
| 10 | Wind-turbine Construction: concrete 3.58E-06 m³ (text p. 82: 6.56E-06 m³ all classes), reinforcing steel 2.32E-02 kg (text: 3.62E-02 kg total) | rebar **927–1,446 t/MW**; concrete 143–262 m³/MW | — | NOT-APPLICABLE to the study, but it tests the table: 3.62E-02 kg rebar per kWh would be 6,480 kg per m³ of concrete and 17× the tower steel, and at ~1.5 kg CO₂e/kg would alone be 54 g/kWh against the paper's total of 33.6 g/kWh. **The reinforcing-steel rows of Table 5 are wrong by an order of magnitude** (kg printed for what was scored as ~10× less, or a slipped exponent). Treat every "Reinforcing steel" row in Table 5, including row 9's, as unreliable |
| 11 | Transmission towers 1.74E-05 kg steel; MV steel poles and gantry 1.27E-04; OH conductors; cables | per-MW in the table | not used (the study's connection is a bay, not a line; "the 2 km line term is reported but not charged") | NOT-APPLICABLE | AWF II's 78 km 33 kV line on 403 towers dominates these rows |
| 12 | Operation and maintenance: replacement materials (blades 50 %, gearboxes 50 %, generators 30 % for DFIG; 50 %/15 % for PMDD over 20 y, p. 83) and mineral oils (every 3 y) | 9 % of GHG (p. 87) | wind servicing 4 % per 20 y (Vestas) | context: Teffera's replacement assumption is far heavier than Vestas's (doubling it → +18–25 % on all categories, p. 90) | |
| 13 | Transportation rows (truck + ship) | 0.14–22 % of impacts by category; CC: "transportation … 1.6 and 22%" range (p. 87); >90 % of it overseas shipping (p. 93) | delivery to site excluded | BOUNDARY | |
| 14 | Waste management rows | 3 % of GHG (p. 87); recycled-content (cut-off) model, no EoL credits in the baseline | end-of-life excluded | BOUNDARY | |

### Teffera's own transformer bill (what DATA_GAPS.md:97 and SOURCES.md:726 refer to)

| Component | Rows (kg per kWh) | Not in the bill |
|---|---|---|
| Unit (turbine) transformer, 33/0.69 kV box type | low-alloyed steel 5.02E-05; copper 3.82E-06; **aluminium 1.95E-06** (+ electricity 2.28E-03 kWh, heat 9.70E-05 MJ) | no oil, no separate core "iron", no paper/pressboard, no porcelain |
| HV power transformer, 230/33 kV and 132/33 kV | low-alloyed steel 1.42E-05; copper 3.12E-06; **porcelain 2.59E-07** (+ MV electricity 5.83E-04 kWh) | no oil, no aluminium |

So: SOURCES.md:726 and DATA_GAPS.md:97 ("adds aluminium and porcelain bushings
that Leng omits") — IN. `stepup_transformers.py:203` and SOURCES.md:702
("Teffera's equivalent inventory is steel and copper only") — IN-DIFFERS: steel,
copper **and aluminium** for the unit transformer; steel, copper and porcelain
for the HV unit. The "Iron" judgement still holds (Teffera have no iron row, so
their steel is core and tank together). Neither Teffera transformer has an oil
row, which Leng's do (17.6 t / 50 units) — so Teffera's masses err low on that
count, in the opposite direction to the voltage argument.

## Parameters

| Parameter | Source (page) | Module / docs | Disposition |
|---|---|---|---|
| Lifetime | 20 y (abstract; p. 82 "A lifespan of 20 years extending from erection to demolition"; sensitivity 15 / 25 y, p. 90) | 35 y amortisation is the study's | context |
| Generation basis | 3-year realized average (p. 82, Fig. 6 caption p. 91); CF realized 0.17 / 0.32 / 0.24 (avg 0.243), estimated 0.34 / 0.35 / 0.36 (Table 1, p. 78) | SOURCES.md:723 "do not say which" | IN-DIFFERS: the paper does say — realized |
| Transformer share of GHG | p. 87: "Transformers represent 12.4% (i.e., unit transformers with 8.7% and power transformers with 3.8%)"; internal connection network 12 %, HV subsystem 5.3 %, MV subsystem 3.2 % of pre-operation | SOURCES.md:721 band 228–333 kg CO₂e/MW/yr | **Claim to check**: 8.7 % × 33.6 g = 2.92 g/kWh = ~5,800 kg CO₂e/MW/yr on the realized basis — ~20× the study's band. ~2.3 g of the 2.92 is the 2.28E-03 kWh electricity row on a ~1 kg/kWh Chinese grid; the three material rows score ~0.13 g/kWh. Teffera's *published* transformer carbon therefore does not corroborate the study's figure; only their *masses* do. Do not cite the 12.4 % |
| Switchgear manufacturing energy | excluded as negligible (p. 80) | — | the register's switchgear estimate is materials only |
| SF₆ | none in Table 5, although the MV cubicles are gas-insulated (p. 78) | DATA_GAPS.md:53 notes the SF₆ asymmetry | the Teffera-based estimate carries no SF₆; Vestas (above) bound it at < 0.001 % of wind GWP in normal operation |
| Recycling | recycled-content (cut-off) model; "environmental burdens from recycling were not taken into consideration"; 80 % recycling sensitivity −27 % GHG (p. 92) | EoL excluded | BOUNDARY |
| Transformer MVA per MW | 1.048 (ASWF), 1.078 (AWF I) (pp. 78–79) | SOURCES.md:729 | IN |

## Claims to check

1. **CUTOFF_RULE_PLAN.md:203, 207, 209, SOURCES.md:754, DATA_GAPS.md:53,
   `transformers.py:106` — "0.61 t/MW switchgear vs 1.08 t/MW transformer".**
   Both reproduce exactly on the estimated-generation basis (1,007 GWh/y, CF
   0.355: 618 and 1,093 kg/MW). The paper states its Table 5 is per kWh of the
   realized 3-year average (647 GWh/y), on which they are 0.40 and 0.70 t/MW.
   The ratio (0.57) and so the "~55 %" verdict do not change; the absolute
   upper estimate is 1.56× conservative. Label the basis.
2. SOURCES.md:723 "do not say which" — p. 82 and Fig. 6's caption say realized.
3. `stepup_transformers.py:203` / SOURCES.md:702 "steel and copper only" —
   add aluminium (unit) and porcelain (HV).
4. SOURCES.md:721 "228–333 kg CO₂e/MW/year" is the study's re-scoring of
   Teffera's mass rows; Teffera's own transformer GHG (12.4 % of 33.6 g/kWh) is
   ~20× that because of an unexplained electricity row sized like losses. Say
   the cross-check is on mass, and never on Teffera's published share.
5. Table 5's reinforcing-steel rows are internally impossible (6,480 kg rebar
   per m³ of concrete for the turbines; 533 kg/m³ for the HV bay). Any civils
   estimate for the grid bay taken from Teffera must use the concrete rows
   (5.4–8.4 m³/MW) with a normal reinforcement ratio, not the printed rebar.
6. Table 2 prints the GEV HP rating as 100 kW; it is 1 MW (text p. 78).
7. The study's grid-intake switchgear estimate uses HV rows that are 57 %
   porcelain; scoring porcelain at a ceramic factor rather than "mass × steel
   factor" changes the estimate materially — check which factor the register
   applies.

## Summary

- Table 2 gives 690 V for all four turbine models (p. 78) — the module's
  `TX_TURBINE_TERMINAL_V` is a clean transcription (and the 0.6/1 kV LV cables
  in §3 agree). One source typo: GEV HP printed at 100 kW, actually 1 MW.
- Table 5 is transcribed in full above with per-MW conversions. The cut-off
  plan's "0.61 t/MW switchgear vs 1.08 t/MW transformer" are the MV + HV
  switchgear and HV power-transformer material rows on the *estimated* CF
  (0.355); the paper says Table 5 is normalised on *realized* generation (CF
  0.228), which makes them 0.40 and 0.70 t/MW. The ratio, and the plan's
  verdict, are unchanged; the upper estimate is conservative by 1.56×.
- Teffera's switchgear is materials only (manufacturing energy excluded, p. 80)
  and carries no SF₆ despite gas-insulated MV cubicles; 57 % of the HV
  switchgear mass is porcelain.
- Teffera's transformer bills are steel + copper + aluminium (unit) and steel +
  copper + porcelain (HV), with no oil — the module's "steel and copper only"
  needs the aluminium. Their large electricity rows (0.23 % and 0.06 % of
  output) look like losses, not factory energy, and make Teffera's published
  transformer share (12.4 % of GHG) ~20× the study's materials-based band;
  cite the masses, not the share.
- Table 5's reinforcing-steel rows are wrong by about an order of magnitude
  (they would exceed the paper's whole carbon total); do not build the grid
  bay's civils from them.
