# Source check — network, equipment and prices, 9 Nov 2026

The rest of the cost side, after the levies pilot (`docs/SOURCE_CHECK_LEVIES_2026-11-09.md`). Same
two passes per group: a **blind re-read** (readers given each document and where to look, with the
model's numbers masked out of the checklist) and a **search** for newer or better sources under the
rules: UK government first; a stated figure beats a derived one; charges keep to the 2026/27 year
(a later year is listed apart); equipment may move to a newer edition (it is converted to 2026
pounds anyway). Seven agents: four readers (power equipment, hydrogen equipment, network, prices)
and three searchers (equipment, network, prices). Every figure that would change the model was then
confirmed by hand from the downloaded file.

**Applied the same evening (user: "keep it to gov or system operator as deciding source"):** B1
battery capital and running cost from NESO E.03 (line through 2–9 h); B2 kept at 15 years (NESO,
BEIS); B3 gas from DESNZ's 2026 assumptions — central 11 % lower for bought hydrogen's gas, the
site's delivered gas moved by DESNZ's 2025→2026 central change (85/94), and the range set to DESNZ's
own 2026 low/high (×0.61 / ×1.68) in place of ±25 %; B4 carbon from NESO's Ten Year Outlook 2026
(£72.27/t, 2026 £), also the unserved-energy weighting. B5 applied too: solid-oxide central is
NESO's H.02 (built 2026, £5,135/kWe in 2025 £ on the BEIS conversion), high NESO's 2025-build
figure (£5,459), low the Danish Energy Agency's (£2,529, central until then); fixed opex NESO's.
Group A applied too: SSEN SEPD v1.50 and SHEPD v1.48 rows (and SHEPD's outdoor 33 kV row), the
Observatory's 2025 UK costs (grey 2.29, blue 3.05, green behind the meter 4.30, grid 5.89 £/kg; each
case now takes the lower or higher of its sources, since a source can fall either side of the
central), and the record fixes (carbon 2040, CEPA date, DEA version, NLR folder note).

New documents are in OneDrive
`DC optimiser/cost sources/10 network`, `11 equipment` and `12 prices` (each "checked 9 Nov 2026").

## 1. Read correctly?

**Yes — every figure the model uses matches its document**, in all four groups: 35 cited sources
(148 citations on the cost map) plus the low/high-case sources off the map (Ember, NREL ATB, Modo's
survey, the Danish storage sheet, World Bank, Eurostat, NESO's hydrogen tables). Including:
Arup's wind and solar tables and §5.8/§6.8; every battery case; CEPA's rates; Baringa, NLR,
Element Energy, the Clean Hydrogen KPIs, BEIS 2021 (solid oxide), the Danish SOEC sheet, NESO's
electrolyser table, HSE's COMAH figures; all seven connection price lists (the publishers' median
reproduces: 132 kV £8.0–9.2m → £8.6m, 33 kV → £3.57m); London's and Eastern's local charges and
loss factors; TNUoS by zone and band; BSUoS; the Section 14 annuity terms; FES cross-rates, gas and
carbon; ONS, World Bank and Eurostat deflators; the Observatory's 2024 UK hydrogen costs; and the
wholesale prices (January 2025 mean £114.09/MWh reproduced exactly from the API).

**One misreading found:** `connection_cost.py` takes SSEN North of Scotland's 33 kV primary from the
*indoor* double row, noting "no outdoor row". The statement (v1.46 and v1.48) does print a **new
outdoor double**, £1,807,300–2,523,675, and the rule is outdoor where published. North of Scotland
33 kV sites are priced about 10 % high (mid £2.40m → £2.17m); the publishers' median moves by
under 1 %.

Small things found (no effect on results unless stated):

| Where | Finding |
|---|---|
| `h2_prices.GB_CARBON_EUR_PER_T[2040]` | 120.500; the workbook says **121.25**. Not used (only 2025 is). |
| FES 2025 workbook | Gives **annual** values (2024, 2026, …), not only five-yearly as the code comments, and an earlier chat answer, said. 2026: gas €32.37/MWh, £1 = €1.17, $1 = €0.906. Its 2023 £→€ rate of 1.00 looks like an error in NESO's table (not used). |
| CEPA hurdle rates | Cover dated **30 July 2025**, register says 30 June. |
| Danish SOEC workbook | Labelled "Version 0015" (August 2026), register says v0019. "Per kW of total input_e" is ambiguous (electric only, by the sheet's own size). |
| NLR fuel cell report | Used for the low case and the build period, but filed in OneDrive's "7 cross-checks, not used". |
| Baringa (fuel cell) | Its own figures disagree: purification "roughly 15 %" of £2,700/kW is £405, but §5 says £485. The report does not say whether the £2,700 Korean plant includes purification, which the central case (2,700 − 485) assumes. A judgement, not a misreading. |
| Clean Hydrogen KPIs | The stack share (400/1,900) divides stack cost by a system cost that excludes electrical balance of plant, for units up to 500 kWe, so it overstates the stack share somewhat. |
| Element Energy tank | The land footprint (0.20 m²/kWh) is for high-pressure tubes; the model applies it to medium-pressure vessels (already labelled as a borrowing). The source's own vessel numbers are inconsistent (405 kg vs 479 kg implied). |
| Danish storage, high tank case | The data sheet gives tanks €636/kg and installation €319/kg (2020 €), 6 % above the model's €600 + €300 (read from the PDF table, rounded). |
| Solar land | DESNZ says "per MW" without saying AC or peak; the model reads it per MWp. |
| London local charges | Annex 5 loss factors are marked "illustrative" in the schedule (BSC-approved factors take precedence); ES216 carries a DRAFT watermark although approved. |
| NESO Section 14 | Its worked example uses 4.00 % return, its own Table 3.1 5.02 % (the model uses the table). |
| NESO hydrogen tables | Declare no price base; the model takes them as 2025 £. |

## 2. Newer or better sources

### A. Same document, newer edition — updates with no judgement in them

| # | Item | Finding (confirmed by hand) | Effect |
|---|---|---|---|
| A1 | **SSEN connection price lists** | Southern England **v1.50** and North of Scotland **v1.48**, both 29 Oct 2026, replace v1.47 / v1.46, with new Section 7 prices. Southern: 33 kV primary (outdoor double) £2.62–2.83m → **£3.62–4.79m**; 132 kV (outdoor double) £11.50–13.04m → £12.72–13.25m; 132 kV cable per extra metre £1,405–**32,316** → **£1,527–2,482** (the old top was implausible). | **Southern England 132 kV cable cost falls about eightfold** (mid £16.9k/m → £2.0k/m). The publishers' median for POA areas (London, Northern Powergrid…): 33 kV substation **£3.57m → £4.31m**; 132 kV unchanged (£8.6m). |
| A2 | **Bought hydrogen** | European Hydrogen Observatory **2025** file (posted Nov 2026), UK rows, €/kg: green direct-connected **5.03** (was 5.63), grid electrolysis **6.89** (9.52), SMR **2.68** (3.35), reforming with capture **3.57** (4.32). | Plant-gate prices fall 14–30 % (only matters when buying hydrogen). |
| A3 | SSEN North of Scotland 33 kV | Take the outdoor double row (the misreading above). | North of Scotland 33 kV primary −10 %. |
| A4 | Records | The documentation fixes in §1 (carbon 2040, CEPA date, DEA version, NLR folder). | None. |

### B. Better by the rules — your call

| # | Item | Candidate (confirmed) | Effect / note |
|---|---|---|---|
| B1 | **Battery capital, central** | NESO *FES 2025 Economics Inputs* sheet E.03 (v2, Aug 2026; 2025 £; build year 2026): 1 h £298, 2 h £547, 4 h £920, 6 h £1,265, 9 h £1,813 per kW. A public body's figure, stated by duration for the build year; NESO's own source is Modo's data. Its opex is the same BEIS 2022 figures, inflated. | Against BEIS 2022 (2030 capex, real 2019, ×1.28): 4 h **+3.5 %**, 6 h +6 %, 1 h −30 %. Small for the durations the model builds. |
| B2 | Battery life | Modo's **October 2026** assumptions say **20 years** for batteries (15 before) and lower prices (2 h £503/kW, 4 h £704/kW, 2026 £). NESO and BEIS still say 15. | 20 years would cut the battery's yearly cost by about a fifth. Industry vs government: keep 15 unless you prefer Modo. |
| B3 | **Gas price and its range** | DESNZ *Fossil fuel price assumptions 2025* (Feb 2026, UK government): NBP gas, real 2024, p/therm, for **2026: low 52, central 85, high 143**. | Central ≈ **£30.9/MWh** in 2026 £ against the model's £34.7 (FES 2025's 2025 value, inflated). The range is **−39 % / +68 %**, a published government range instead of our ±25 %. Applies to the gas behind bought grey/turquoise hydrogen and to the gas price tickbox. |
| B4 | **Carbon price** | NESO *Ten Year Outlook 2026* workbook (Sep 2026; real 2026 €, annual; FES is now three-yearly and this replaces its near years): GB total carbon **€80.94/t in 2026** (FES 2025 had €92.38 for 2025). Also gas €30.12/MWh and £1 = €1.12 for 2026. DESNZ's traded carbon values (UK ETS only, without the £18 support price) are the government alternative. | Moves grey hydrogen's carbon cost and the carbon-price point on the trade-off. The unserved-energy weighting is tied to £78.96/t; leave that unless you want it moved too. |
| B5 | Solid-oxide electrolyser | NESO FES 2025 Economics Inputs sheet H.02: SOE **£4,924/kW H2** (2026 build, 2025 £), a UK public-body figure. | About 50 % above the model's central (Danish Energy Agency). Worth showing as a cross-check, or as the high case in place of BEIS 2021. |
| B6 | Wind and solar | DESNZ *Electricity Generation Costs 2025* (Mar 2026) adopts Arup's figures; only hurdle rates (CEPA) and wind load factors differ. | Keep Arup; add as confirmation. |

### C. Nothing better found
Discount rates (CEPA is latest); fuel cell (Baringa, NLR); tank (no UK capex since Element Energy;
EU target ≤ €450/kg as a low-side note); COMAH (HSE IA; regulator hourly rates £218 HSE, ~£274
Environment Agency for 2026/27); NGED and ENWL price lists (current); TNUoS, BSUoS and NESO's
Statement (unchanged for 2026/27); ES216 (latest); ONS/HMT (next ONS release 12 Nov, HMT after 22 Dec);
Elexon market index (still the official series); NESO electrolyser table (columns renamed, values unchanged).

## 3. Check by hand (sites refused automated access)

UK Power Networks (is 3 Aug 2026 still the latest connection statement and is London v1.3 the latest
schedule?), SP Energy Networks (is the joint statement June 2026?) and Northern Powergrid (anything
after 2 Jun 2026?). Their charging-statement pages: ukpowernetworks.co.uk → Connections → charging
statements; scottishpower.com → SP Energy Networks → regulatory documents → connections, use of
system and metering; northernpowergrid.com/document-library.

## 4. Pending or later (not 2026/27)

- **Ofgem's data-centre connection reform** (consultation closed Sep 2026, decision expected by end
  2026): a returnable commitment fee for data centres over 40 MW of **£237,500–712,500 per MW**
  requested, held until energisation. A security, not a tariff, but large.
- CMP417 (demand users onto the generators' securities rules): awaiting Ofgem.
- 2027/28: BSUoS draft £21.67 / £18.42 per MWh (final in December; NESO's November forecast is
  higher); TNUoS draft due end of November; 2027/28 local schedules already published.

## 5. Saved

`10 network`: SSEN Southern v1.50 and North of Scotland v1.48 connection statements; both SSEN
2026/27 schedules v1.2; Ofgem's data-centre connection consultation.
`11 equipment`: DESNZ Electricity Generation Costs 2025 (report and Annex A); NESO FES 2025
Economics Inputs (v2) and Assumptions workbooks; DESNZ Hydrogen Transport and Storage Cost Report.
`12 prices`: NESO Ten Year Outlook 2026 data and assumptions workbooks and explainer; DESNZ fossil
fuel price assumptions 2025 (tables and report); DESNZ traded carbon values 2025 (page); European
Hydrogen Observatory production costs 2025.
