# Source hunt for the weakest inputs, 11 Nov 2026

Research only. No model code or data was changed and nothing was run. Each section gives the value the
code uses now, what was found, a proposed central value and range, and what changing it would mean for
the tests. The user agrees values first; the model is then changed once and the lowest-carbon tests rerun.

Source order, as the project requires: UK government first, then peer-reviewed papers, then US national
laboratories and EU bodies, then industry. Where no UK government source exists, the section says so.
Every source cited was opened (page or PDF), not taken from a search summary. Figures are quoted with the
page, table or section they sit on.

---

## 1. Battery carbon per usable kWh (`battery.energy_per_usable_kWh`)

**Now.** 115.0 kg CO2e per usable kWh = 103.5 kg CO2e per kWh of cells (`BESS_KGCO2E_PER_KWH_NAMEPLATE`,
Jasper et al. 2026's liquid-cooled LFP container around Voß et al. 2025's cell made in China, rebuilt on
ecoinvent 3.9.1, IPCC 2021) divided by a usable share of 0.90 (assumed). Of the 103.5, the cell is 82.9 and
everything else (racks, cooling, fire system, container, foundation) 20.6. Graded "assumed" because of the
0.90. Charged over the 15-year life and replaced. A ±50 % push moves the lowest-carbon battery from near
zero to 17 times its size; +0.6 % moved it 8 %.

**UK government source: none.** No DESNZ, BEIS or NESO document gives the carbon of making a grid
battery. A search of gov.uk found only conversion factors for fuels and grid electricity.

**What was found.**

Whole battery containers, from the makers' own environmental product declarations (third-party
verified, ISO 14025; "manufacturing" = materials plus the maker's own factory, cradle to gate):

| Product | What it covers | kg CO2e per kWh of cells | Against the model's 103.5 |
|---|---|---|---|
| Trina Storage TSMG4073-H-E, liquid-cooled, 4,073 kWh, 35 t, made in Anhui. EPDItaly MR-EPDITALY0103, issued 3 Jan 2025; 2023 factory data; ecoinvent 3.10; EN 15804+A2 (EF 3.1). Table 9: upstream 107, core 33.7 | battery container, no inverter | **140.7** | +36 % |
| Gotion 2.7 MWh air-cooled cabin, 2,703 kWh, 32.4 t, made in Hefei. EPDItaly, 27 May 2024; ecoinvent 3.9.1; EN 15804+A2. Results table: upstream 78.7, core 0.87 | battery cabin, air-cooled | **79.6** | −23 % |
| NHOA PowerIsland #3, 7,455 kWh with a 3.6 MVA inverter and its medium-voltage skid, Italian integrator. EPDItaly (v3.7); GaBi 2023.2. Table 5: upstream 96.6, core 2.33 | battery **plus inverter and transformer** | **98.9** | the model's like-for-like figure at this 2-hour size is about 126 (energy term plus inverter and transformer per kWh), so −22 % |

Links: [Trina](https://www.epditaly.it/en/wp-content/uploads/2016/12/MR-EPDITALY0103.pdf),
[Gotion](https://www.epditaly.it/en/wp-content/uploads/2016/12/EPDitaly_Hefei-Gotion-High-tech-Power-Energy-Co.Ltd_._-20240527.pdf),
[NHOA](https://www.epditaly.it/wp-content/uploads/2016/12/NHOA_EPDv3.7.pdf).

Cells and modules only (the model's cell is 82.9, Voß made in China; 74.9 made in Germany; Jasper's own
Fig. 4 cell 95.4):

- CATL stationary LFP cells, three types, EPDItaly0751, issued 27 Sep 2024; factory data May 2023 to
  Apr 2024; ecoinvent 3.9.1; EN 15804+A2. Tables 6-1 to 6-3, manufacturing (upstream + core):
  **53.0, 50.8 and 50.3** kg CO2e per kWh of guaranteed energy. The Zhaoqing factory's power is 70 % hydro
  (its section on electricity data), so this is a best case, not a typical Chinese cell.
  [CATL](https://www.epditaly.it/wp-content/uploads/2016/12/CATL-EPD-REPORT-EPDITALY0751-V20927.pdf)
- Sungrow ST5015UX battery module (cells in their module, no container), EPDItaly0945, revised 26 Nov
  2025; ecoinvent 3.10; EF 3.1. Table 5-2, manufacturing: **60.5**.
  [Sungrow](https://www.epditaly.it/en/wp-content/uploads/2016/12/EPD-of-Sungrow-20251113-update.pdf)
- Degen, Mitterfellner and Kampker, J. Industrial Ecology 29(1) 113–128 (2025), peer reviewed; ecoinvent
  3.10; results section on GWP: LFP cells **about 59–70** kg CO2e per kWh of cell.
  [doi:10.1111/jiec.13594](https://doi.org/10.1111/jiec.13594)
- Llamas-Orozco et al., PNAS Nexus 2(11) pgad361 (2023), peer reviewed; Fig. 3B: LFP battery, global
  production **56** kg CO2e per kWh (a car pack, cradle to gate).
  [White Rose copy](https://eprints.whiterose.ac.uk/id/eprint/206163/1/pgad361.pdf)

The current basis itself, re-opened: Jasper et al., Energy Advances (2026), doi:10.1039/D5YA00341E, §3.1:
the parts other than cells are 32–58 % of the carbon across their eight systems. Their liquid-cooled design
holds 3,008 kWh per container; the 2025 products above hold 4,073–5,016 kWh in the same 20-foot box (the
HiTHIUM 5,016 kWh datasheet, 40 t), so the container, cooling and fire system per kWh are now smaller than in
Jasper's design. Not quantified here.

The usable share: PNNL for US DOE, *2022 Grid Energy Storage Technology Cost and Performance Assessment*
(PNNL-33283, Aug 2022), §6.1.4 p. 124 and Table 6.4: lithium batteries "typically cycled at ≤ 80% DOD to
account for degradation". Jasper also use 80 %. The model handles fade separately (capacity falls over the
warranted cycles), so 80 % would count part of the fade twice; 0.90 stays a reasonable middle. No source gives
a usable share for a modern grid container directly.

**Proposed.** Keep the central at **115 kg CO2e per usable kWh** (103.5 per kWh of cells, 0.90 usable).
The three container declarations bracket it (79.6 to 140.7, their mean 106 although their scopes differ).
Replace the ±50 % test with the published span: **89 to 156 kg CO2e per usable kWh** (the Gotion and
Trina containers at 0.90 usable), that is −23 % / +36 %. Say in the report that the low end needs a cell
like CATL's hydro-powered one and the high end Trina's factory data.

**Decided 11 Nov 2026 (user): keep the straight ±50 % on this study's own figure.** Other products' totals
differ in scope, database and method, so they are not used as the test range; they stay above only as a
check that the central is realistic. Briefly changed to ×0.7687 / ×1.3592 the same afternoon and reverted.

**What changing it would do.** The central does not change, so nothing reruns for the value itself. The
range replaces ±50 % in the lowest-carbon ±tests (`sensitivity.py`, `push=battery.energy_per_usable_kWh`);
both ends need the hourly lowest-carbon solves at North Norfolk again. Since +0.6 % already moves that
battery by 8 %, the honest report is that published sources cannot settle the lowest-carbon storage mix:
state the battery and tank sizes across 89–156, not one answer.

**Found on the way (not one of the seven).** Both container declarations give the power their cooling and
control draw all the time, the term `DATA_GAPS.md` leaves open ("battery cooling and control load"):
Trina 5.33 kW for 4,073 kWh (§1.8, Table 3), Gotion 4.48 kW for 2,703 kWh (Table 6). That is **3.1 % and
4.0 % of capacity a day**, six to eight times the 0.5 % a day tried on the rig on 5 Nov. These are the
makers' own figures at 25 °C under the declaration rules, and they would weigh on a battery kept mostly
idle, as the lowest-carbon designs do. Worth its own decision.

---

## 2. Fuel cell capital cost (`cost.fuel_cell.capex_per_kW`)

**Now.** Central **£2,215 per kW** (2025 £) = Baringa for DESNZ, *Hydrogen to Power Costs and Barriers*
(9 Dec 2025), §4.4, "the 80 MW PEM facility commissioned in South Korea in 2021", c. £2,700/kW, less §5's
£485/kW purification (the model's hydrogen is already pure). High £2,700. Low: NREL TP-5400-91146
Table 18, a modelled 100 MW plant, $1,352/kW (2022 $) less sales tax and grid spur, about £1,000. A ±50 %
push moves the bill up to about 6–10 %.

**UK government source: only Baringa.** NESO's FES 2025 economics workbook has no fuel cell row (its
hydrogen rows are turbines, "hydrogen peaking plants" and small hydrogen heat-and-power). DESNZ's
*Electricity Generation Costs 2025* covers hydrogen turbines only.

**What was found.**

- **Baringa's reference plant is not a membrane fuel cell plant.** The plant is Shinincheon (Incheon,
  78.96 MW, Oct 2021). Doosan's own release (2 Nov 2021) says Doosan supplied 124 units of 440 kW to it;
  Doosan's 440 kW unit is the PureCell Model 400, and its hydrogen datasheet (HyAxiom, a Doosan company)
  says "proven PAFC fuel cell technology", i.e. phosphoric acid. The rest came from POSCO Energy. So the
  £2,700 is a phosphoric-acid plant on by-product hydrogen, and subtracting a membrane plant's purification
  is not like for like. Baringa states the cost "equivalent to c. £215 million in 2025"; one helper's check of
  the exchange rate suggests it may be a 2021 conversion not inflated (about £3,200/kW if so). Not settled.
  [Baringa](https://assets.publishing.service.gov.uk/media/69663541e8b93f59c3aecd76/hydrogen-to-power-cost-barriers.pdf),
  [Doosan release](https://www.doosanfuelcell.com/en/media-center/medi-0101_view/?id=57),
  [datasheet](https://www.doosan.com/images/media-center/ces2024/(Data%20Sheet)%20HyAxiom%20PureCell%20Model%20400%20Hydrogen.pdf)
- Baringa's two other figures (same report, opened): membrane fuel cell **equipment "over £1,300/kW"**
  (p. 52), and a grid-scale system's installed cost **"estimated to exceed £2,500/kW"** (p. 55).
- US DOE targets for 100 kW–3 MW stationary fuel cells (energy.gov, natural-gas systems): 2015 status
  equipment $1,200–4,500/kW, installed $2,400–5,500/kW; 2020 target $1,000 equipment, $1,500 installed.
  Useful only for the ratio of installed to equipment cost, about 1.5.
- Clean Hydrogen Partnership research agenda, Annex 5 Table 21 (p. 167), membrane stationary fuel cells
  51–500 kWe: 2020 state of the art €1,900/kW, targets €1,200 (2024) and €900 (2030). A factory price at
  100 MW a year, no site work: about £1,950 in 2025 £.
- NREL TP-5400-91146 (Feb 2026) Table 18 confirmed at $1,352/kW; its fuel cell modules are only $272/kW of
  that (vehicle stacks).
- Daesan, Korea, 50 MW, also phosphoric acid: USD 212m, about $4,240/kW (2020 $), Hanwha release.
- No membrane fuel cell plant of tens of MW has a published cost. Baringa (p. 49) notes the UK has no
  grid-connected hydrogen fuel cell power at all.

**Proposed.** Keep the number, change what it stands on, using Baringa alone (no mixing of sources).
Baringa p. 52: membrane fuel cell equipment "over £1,300/kW", and "total installed system costs more than
double that amount for a pipeline-supplied system with hydrogen purification", so over £2,600/kW with
purification; less its own purification figure (£485/kW, same paragraph) gives **over about £2,100/kW** for
a plant fed pure hydrogen. Its p. 55 "exceed £2,500/kW" for a grid-scale system agrees. Central
**£2,200 per kW**. (The DOE installed-to-equipment ratio of about 1.5, giving £1,950, is a cross-check only.) Range **£1,000 to £2,700**
(NREL modelled plant; Baringa's grid-scale figure as published), with £3,200 (Shinincheon if not inflated)
named as an upper check. Drop "less purification" from the description.

**Closed 11 Nov 2026 (user): left as it is.** £946 / £2,215 / £2,700 per kW stay, Baringa's figures as the
government took them, purification already out of the central. No other UK government fuel cell cost
exists (checked: NESO FES 2025 economics workbook, DESNZ Electricity Generation Costs 2025, DESNZ
hydrogen-to-power consultation Dec 2023 and response Dec 2024, Mott MacDonald for BEIS 2018 storage;
Element Energy for BEIS 2018 p. 94 is older, £2,642 first unit). One-sentence caveat added to SOURCES.md:
Baringa's Korean plant is mostly phosphoric-acid units. Baringa's own conclusion (p. 55, "exceed
£2,500/kW") agrees within 13 %.

**What changing it would have done.** The central would not move, so nothing reruns. The range sits inside the
±50 % already tested (£1,100–3,300). Only the source text in `h2_capex.py` and `SOURCES.md` changes. The
Baringa misdescription is worth one sentence in the report to the supervisor.

---

## 3. Bought green hydrogen, delivered price (`cost.bought_h2.green.delivered`)

**Now.** About **£5.1 per kg** plus trailer compression electricity, 2026 £: half European Hydrogen
Observatory UK "renewable hydrogen directly connected" (£4.30) and half "grid electrolysis" (£5.89), both
2025 levelised production costs at the plant gate. Road haulage is excluded. Named by the supervisor; ±50 %
moves the bill up to about 6 %.

**UK government sources: yes, two, and they rank above the Observatory.**

- **DESNZ, HAR2 cost challenge guidance (7 Apr 2025)**, opened: the first hydrogen allocation round
  reached a "weighted average strike price of 241 £/MWh H2 (HHV)", footnote 1 "In 2023 real prices". On the
  higher heating value (39.4 kWh per kg) that is **£9.50 per kg in 2023 £**, about **£10.1 in 2025 £**
  (dividing by the lower heating value, 33.3 kWh per kg, would wrongly give about £7.2). The same page: a
  quarter of the bidders reported wholesale electricity at or below £66/MWh, and total electricity prices
  below £82/MWh including network costs (April 2024 bids). At about 52 kWh per kg, £82/MWh is about
  £4.3 per kg for electricity alone, so the Observatory's £4.30 for the whole cost is low for
  the UK. Government "expects a significant cost reduction" in the second round, with no figure; no second-round
  prices are published yet (the gov.uk collection was last updated 7 Apr 2025).
  [HAR2 guidance](https://www.gov.uk/government/publications/hydrogen-allocation-round-2-har2-due-diligence-and-cost-assurance/har2-cost-challenge-guidance-for-shortlisted-projects-on-being-cost-competitive)
- **DESNZ, Hydrogen Transport and Storage Cost Report (Dec 2023)**, opened, Annex Tables A3–A4 (p. 37),
  2023 £, Type IV tube trailers. For a 1,300 kg trailer making 300 trips a year: trailering alone **£0.90,
  £1.02, £1.14 per kg** at 100, 200, 300 km; including compression £2.10–2.33. At 100 trips a year
  trailering is £2.29–2.53. The £/MWh column implies the higher heating value.
  [Report](https://assets.publishing.service.gov.uk/media/659e600b915e0b00135838a6/hydrogen-transport-and-storage-cost-report.pdf)
- Context, not used: BEIS *Hydrogen Production Costs 2021* (2020 prices, pre-crisis power); the 2022
  heads of terms for the producer contract (BEIS, opened) say the buyer pays a negotiated price, at least the
  gas reference price, and the taxpayer tops the producer up to the strike price.

**Is the strike price what a buyer pays?** No. Under the contract a buyer pays something near gas parity
and the taxpayer pays the gap. But the strike price is the latest UK government figure for what
electrolytic hydrogen actually being built costs, return on capital included, which is the model's rule
(present-day, latest published cost). It slightly understates full cost: grant-funded capital and
electricity levies are left out of it.

**Proposed.** Two separate decisions, so either can be taken alone:

1. **Plant gate: £10.1 per kg (2025 £)**, the first-round strike price, replacing the Observatory. Range
   **£5.1 to £11.5**: the Observatory mix as the low case (standing in for the second-round cost cut, which has
   no figure yet), the NESO grid-electrolysis top end as the high.
2. **Add road haulage: £1.1 per kg (2025 £)**, DESNZ Table A4, 1,300 kg trailer, 200 km, trailering only
   (the model already charges the compression electricity; the compressor's own capital, about £0.5 per kg
   by subtraction from the same table, would come with it if the user wants the full figure). Range £0.9–2.5
   (100 km busy trailer to 300 km trailer used 100 times a year). DESNZ's trailers run at 500 bar, the
   model's compression goes to 200 bar: a small mismatch, worth one line. The distance is a judgement: the nearest
   shortlisted projects are in Humberside, Lincolnshire and Kent, none in East Anglia.

Both together: **about £11.2 per kg** plus compression electricity, **roughly double** the present input.

**What changing it would do.** It makes bought hydrogen much less attractive. Every design with bought
green hydrogen on offer needs re-solving: the North Norfolk runs with bought hydrogen (the saved run the
maps and workbooks are built from), `sensitivity_shaky_norfolk_grid_green_4h`, and the lowest-carbon tests.
The bought-hydrogen rows in `h2_prices_recommended.csv` and the Observatory note in `SOURCES.md` change.

---

## 4. Grid share behind bought green hydrogen (`green_h2_grid_share`)

**Now.** 0.5, assumed ("a neutral prior"), swept at 0 and 1.

**UK government source: the first round's project list.** DESNZ, *HAR1 successful projects* (14 Dec 2023)
and the press release on the ten signed contracts (23 Jul 2025), both opened, plus each project's own
material for its power arrangement (industry sources, opened by the helper):

| Arrangement | Projects | MW |
|---|---|---|
| On or next to a wind or solar farm (most can also import) | Cromarty 10.6, HyMarnham 9.3, Whitelee 7.1, Tees Green 5.2 | 32.2 |
| Over the network with a power contract, confirmed | Barrow 21.0, Green Hydrogen 3 10.6, Trafford 10.5 | 42.1 |
| Not stated, probably over the network | Bradford 24.5 (city site), West Wales 14.2, Langage 7.0 | 45.7 |
| Total signed |  | 119.8 |

By capacity, the network share is **0.35** on confirmed projects alone and **0.73** if the three unstated
ones are networked. By energy it is higher, since the co-located plants also import. No second-round split
is possible yet (the shortlist gives no power arrangements).
[HAR1 list](https://www.gov.uk/government/publications/hydrogen-production-business-model-net-zero-hydrogen-fund-shortlisted-projects/hydrogen-production-business-model-net-zero-hydrogen-fund-har1-successful-projects),
[press release](https://www.gov.uk/government/news/jobs-unlocked-as-first-wave-of-hydrogen-projects-sign-contracts)

**Government statement (found 11 Nov, after the first draft).** DESNZ, *Hydrogen Update to the Market:
July 2025*, p. 19, "Electricity usage and grid integration": of the projects seeking support in the first
and second rounds, "most of these projects aim to use long term power purchase agreements powered by
multiple generation assets". Power from several generators under a contract arrives over the network, so
government confirms "most" are networked; it gives no number. The tally above gives the number.
[Update to the market](https://assets.publishing.service.gov.uk/media/6880b2139fab8e2e86160efe/hydrogen-update-to-the-market-2025.pdf)

**Other rounds (checked 11 Nov 2026).** Second round: 27 projects shortlisted on 7 Apr 2025 from 87
applications (same update, p. 16); government expected to name winners "in early 2026", but the gov.uk
collection still shows only the shortlist (last updated 7 Apr 2025) and no second-round prices are
published. Third round: "aim to launch HAR3 by 2026", fourth "from 2028", with a move to price-based
competition considered from 2030 (p. 16); only a Dec 2023 call for evidence exists. So the first round is
the only one with a published price and project list.

The Low Carbon Hydrogen Standard v4 (Jan 2026, Annex B Table 4, opened) requires network-supplied
electrolysers to match named generators half-hourly, losses included. That is already how the model scores
the networked share (renewable source plus delivery losses and the network's own carbon), so no change of
method follows.

**Proposed.** Central **0.7**, range **0.35–1.0**. Keep 0 only as a bound.

**What changing it would do.** It raises price and carbon of bought green hydrogen a little (about a fifth
of the gap between the two sellers). If section 3's strike price is adopted, the share stops mattering for
price (the strike price is one figure for all sellers) and acts on carbon only. Same reruns as section 3,
so do them together.

---

## 5. Wind turbine life extension to 35 years (`renewables.WIND_LIFE_EXTENSION`)

**Now.** 27.5 % of the turbine's carbon added for parts at 35 years: servicing 4 % per 20 years pro rata
(7 %) plus one gearbox, main shaft and blade overhaul (20.5 %). Assumed; ±50 % moves carbon 2.8–5.6 %.

**UK government source: for the life only, not the parts.** DESNZ/Arup, *Renewable Energy Generation
Cost and Technical Assumptions 2024* (final, 14 Jul 2025), Table 23 p. 41: onshore life 35 years (25–40).
Nothing on what is replaced. It cites an Arup 2022 repowering and life-extension study for BEIS that could
not be found published.

**What was found.**

- Vestas V162-6.2 MW LCA (31 Jan 2023), opened: the study includes "lifetime repairs of main components like
  gearbox and generator" (p. 20, refurbished for a second use), so part of a gearbox is already in the 4 %
  servicing; §7.2.3 p. 72: doubling repair and replacement parts raises most impacts 1–6 %, halving lowers them
  1–6 %.
- NREL, *Report on Wind Turbine Subsystem Reliability* (NREL/PR-5000-59111, 2013), slides 30–31, DNV KEMA
  data on about 1,500 US turbines over their first 10 years: blades, "about 2% of turbines per year";
  gearboxes about 5 % a year; generators about 3.5 % a year. Older US designs with batch faults, so upper
  end. [Slides](https://docs.nlr.gov/docs/fy13osti/59111.pdf)
- WindTrace (J. Industrial Ecology, Dec 2025) leaves component replacement out as too case-specific: no
  published inventory of a 20-to-35-year extension exists.

**Proposed.** Keep **27.5 %**. Range **15–40 %**: low = servicing plus one gearbox set, blades refurbished
not replaced; high = servicing plus gearboxes at NREL's 5 % a year over 35 years (1.75 sets), one blade
set and generators. Vestas's built-in gearbox repairs mean the central slightly double-counts, which leans
low. Say plainly that the figure is still built across sources: the part shares are Vestas's (modern
European turbines), the replacement rates NREL's (older US turbines, first 10 years only, stretched to 35),
the life DESNZ/Arup's, all applied to ecoinvent's 1–3 MW turbine. Hence it stays "assumed". Cite Vestas §7.2.3 and NREL 2013 alongside the existing Vestas and Siemens Gamesa figures.

**What changing it would do.** Nothing reruns: 15–40 % is about the ±50 % already tested (13.75–41.25 %).
The grade can stay "assumed" with the range now sourced.

---

## 6. Fuel cell stack calendar life (`fuel_cell.STACK_CALENDAR_LIFETIME_YEARS`)

**Now.** 10 years, assumed; swept 5 / 10 / 15. The stack is replaced at 10 years or 30,000 running hours,
whichever first.

**UK government source: none.** Baringa's membrane fuel cell table has no lifetime row.

**What was found.**

- US DOE targets for 1–10 kW hydrogen backup-power fuel cells (energy.gov): life **10 years** (2015
  status), **15 years** (2020 target).
- NREL TP-5400-60730 (Kurtz, Saur and Sprik, Mar 2015), telecom backup units in the field: Table 3 p. 25,
  more than 4 years analysed, "estimated ~10 years"; stacks kept healthy by conditioning runs.
- Clean Hydrogen Partnership research agenda: its stationary targets assume a 10-year system life
  (p. 167); for small home units, makers claim 10-year stacks (p. 76).
- Not used: the HyAxiom PureCell 400 datasheet's "10-year cell stack life" is for a phosphoric-acid stack,
  a different technology.
- Pahon et al., J. Power Sources 488 (2021) 229436: a small membrane stack lost 12 % of power after two
  years in storage at room temperature. Data on idle ageing are scarce.
- Makers of MW-class membrane units (Ballard, Vertiv) give hours only: about 25,000 before overhaul.

**Proposed.** Keep **10 years**, range **5–15** (Pahon and Gandiglio low; DOE 2020 target high). Main
citations: DOE's backup-power figure and NREL's field estimate, both membrane units on backup duty. Grade
could move from "assumed" to "proxy": the years come from kW-class backup units, not a MW plant, and the
DOE figure is a system life, not a stack life.

**What changing it would do.** Nothing reruns: the sweep already covers 5 and 15. Citations only.

---

## 7. Hydrogen tank design (`optimiser_lca/h2_tank.py`)

**Now.** Bulk carbon-steel vessel at 28 bar, 161 kg of steel per kg of hydrogen (thin-wall formula,
SA-516 Grade 70), the default since 4 Nov. Comparison case: Gandiglio's small stainless vessel at 313 kg
per kg, about 3.6 times the tank's carbon; that switch changes the lowest-carbon design.

**UK government source: on pressure, not on steel.** Element Energy for BEIS, *Hydrogen supply chain
evidence base* (Nov 2018), PDF p. 109: above-ground vessels typically 5–8 MPa, a 95 m³ vessel about 405 kg;
pp. 12 and 15: electrolysers deliver at 2–3 MPa (3 MPa base). No steel mass. No HSE report on bulk vessel
materials was found.

**What was found.**

- NREL for DOE, *Hydrogen Station Compression, Storage and Dispensing Independent Review* (May 2014),
  appendix: the DOE station models' low-pressure store is "rolled and welded ASTM SA516 Grade 70 carbon steel
  plate", 1.25 m across, 7.6 m long, 64 mm wall, each holding 89 kg at 172 bar. By this note's own arithmetic
  that is about 14–16 t of steel, **about 160–185 kg per kg** depending on the heads: the model's 161 is
  the same class of vessel. [Review](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/58564.pdf)
- Argonne (Papadias and Ahluwalia, Int. J. Hydrogen Energy 2021, OSTI 1840539): bulk storage in buried
  carbon-steel line pipe (X52, built to the US hydrogen piping code), 500 t at 100 bar; by the helper's
  arithmetic about 205 kg of steel per kg.
- Sandia (SAND2006-11526P): carbon and low-alloy steels are the usual materials for hydrogen vessels;
  low-strength carbon steels are proven in hydrogen service to 13 MPa. Stainless is not required at 28 bar.
- The steel per kg of hydrogen barely depends on pressure (wall and gas both scale with it), so 28 bar is
  fine for carbon; its cost is size (100–220 t at 28 bar is tens of thousands of m³).
- ecoinvent's "low-alloyed" steel is slightly conservative for SA-516, a carbon-manganese steel;
  "unalloyed" would be closer and lower.

**Proposed.** Keep the **carbon-steel vessel at 161 kg per kg**. For the lowest-carbon test, replace the
stainless comparison with a range on the carbon-steel vessel: **127–205 kg of steel per kg** (low: a
sphere with the model's own design margins, 122.1 against the cylinder's 155.4 by the same formula, that
ratio on 161.2 = 126.7; high: Argonne's pipe store, ~24,000 twelve-metre segments of 24-inch schedule 60
pipe for 500 t, 102 kt of steel = 204.5). A bare sphere with no margins would be about 105, a theoretical
floor, not a buildable design. Both ends are arithmetic on published designs, not printed figures.
**Decided 11 Nov 2026 (user), replacing the above:** the tank stays the carbon-steel vessel at 161 kg per kg,
and its test is its own carbon at ×0.5 and ×1.5 (`sensitivity.TANK_PUSH`, a push on `coefficient.gwp_tank`),
a percentage change like the other unsourced ranges. The two extra designs above were added and then
removed the same afternoon. Gandiglio's 313 stainless stays in the code but is no longer tested: at
28 bar it is a small off-the-shelf vessel, not a bulk store.

**What changing it would do.** The central does not move. The tank comparison in the lowest-carbon tests
becomes two solves at 127 and 205 kg per kg (`tank_design` would need a steel-mass override, or two
entries in `TANK_DESIGNS`), in place of the Gandiglio switch.

---

## Ranked summary

Ranked by how much the proposal would change the model.

| # | Input | Now | Proposed central | Proposed range | Change? | Reruns |
|---|---|---|---|---|---|---|
| 1 | Bought green hydrogen delivered (§3) | ~£5.1/kg, plant gate, EU observatory | **Done 11 Nov (user agreed), strike price only, no haulage** (haulage to site is outside the boundary): £9.50/kg in 2023 £, £10.22 in 2025 £, £10.62 delivered in 2026 £ with compression, both sellers, every case | ±50 % push, as before | **Yes, about ×2** | All bought-hydrogen runs, the saved run behind maps and workbooks, lowest-carbon tests |
| 2 | Battery carbon per usable kWh (§1) | 115 kg CO2e | 115 (unchanged) | **±50 % kept** (user, 11 Nov); declarations a check only | None | As planned |
| 3 | Grid share behind bought hydrogen (§4) | 0.5 | **0.7, done 11 Nov** (carbon only now: 1.17 kg CO2e/kg against 1.14 at 0.5) | swept 0 and 1, as before | Yes, small | With §3 |
| 4 | Tank design (§7) | carbon steel 161 kg/kg; stainless comparison | unchanged | **tank carbon ×0.5 / ×1.5**, replacing the stainless switch (done 11 Nov) | Test only | Two lowest-carbon solves |
| 5 | Fuel cell capital (§2) | £2,215/kW | **Closed 11 Nov: left as it is** (£946 / £2,215 / £2,700) | as now | A caveat only: Baringa's Korean plant is mostly phosphoric acid | None |
| 6 | Fuel cell stack calendar life (§6) | 10 y | 10 y | 5–15 y | Citations, grade to "proxy" | None (already swept) |
| 7 | Wind life extension (§5) | 27.5 % | 27.5 % | **×0.5 / ×1.5 on the parts share** (done 11 Nov) | Test only | With the final run |

**Swap tests removed, 11 Nov 2026 (user: not standard).** Every unsourced range is now a percentage change on
this study's own figure. In `sensitivity.SHAKY_KNOBS` and `CARBON_KNOBS`: the battery cell swap
(`batt_cell_basis`) is dropped, covered by the battery's ×0.5 / ×1.5; the wind life-extension swap
(`wind_life_extension` none / servicing) becomes `onshore_wind.parts_fraction` ×0.5 / ×1.5; the fuel cell
stack swap (`fc_stack_basis` Gramc) becomes `coefficient.gwp_fc_stack_per_mw` ×0.5 / ×1.5; the tank swap
becomes `coefficient.gwp_tank` ×0.5 / ×1.5 (above). The alternative bases stay in the code, untested.
**For the final run** the branch's run list must carry these push labels in place of the old
`batt_cell_basis=`, `wind_life_extension=`, `fc_stack_basis=` and `tank_design=` lines.

Three things for the user to decide:

1. Whether bought green hydrogen moves to the UK strike price (and whether to add haulage). It is the one
   change that moves results by itself.
2. Whether to replace the ±50 % pushes on the battery and the tank with the published spans above.
3. Separately, whether the battery's standing cooling and control load (3–4 % of capacity a day from two
   makers' declarations, §1) should enter the model. It may matter to the lowest-carbon storage mix as much as
   the battery's carbon does.

No UK government source exists for the battery's carbon, the tank's steel mass, the wind parts or the
stack life; for the fuel cell's cost the only one is Baringa, with the plant mislabelled.

**Checking.** Three helpers searched sections 2–7 in parallel; each opened the pages it cites. Re-opened
for this note: the HAR2 guidance (£241/MWh, higher heating value, 2023 prices), the DESNZ transport cost
tables, Baringa pp. 49–55, Doosan's release and the PureCell datasheet, NREL's 2013 reliability slides,
Vestas V162 §7.2.3, and NREL's 2014 vessel description. Conversions to 2025 £ use consumer price inflation
2023→2025 of about 6 %; the model's own price base would set the exact figure.

---

## Added later on 11 Nov: bought blue hydrogen (user agreed; not one of the original seven)

**Was.** £3.05 per kg (2025 £), the European Hydrogen Observatory's UK "reforming with carbon capture";
low £2.90 (NESO, autothermal reforming, a different process), high +15 % (assumed).

**Now.** BEIS, *Hydrogen Production Costs 2021* (17 Aug 2021), annex sheet "2025_R": SMR with CCUS,
300 MW, commissioning 2025, total levelised cost on the industrial LRVC gas price, which the report
takes as its main basis (p. 24). Low / central / high gas: 42.28 / 51.89 / 63.79 £/MWh H2 (HHV) in 2020
prices = **£2.03 / £2.50 / £3.07 per kg** in 2025 £ (× 39.41 kWh/kg, GDP deflator 2020→2025). UK
government, all three cases from one document, and the same process as the life-cycle inventory
(steam reforming, 90 % capture, p. 12). Caveats: 2020 prices and a 2021 gas outlook (its gas, about
£22/MWh in 2020 money, is near DESNZ's current 2026 projection of about £25); 74 % efficiency against
the inventory's ~67 %. No UK contract price for blue exists: the first blue plant (EET Hydrogen, HPP1,
350 MW) is reported, in trade press not opened here, as targeting a decision in the second half of 2026,
and uses an autothermal-type process.

**Effect.** Blue about 18 % cheaper. Expected to change no result: through a fuel cell it would still cost
about £160 per MWh of electricity for fuel alone, above the grid, and its carbon is unchanged. Reruns only
where blue is on offer.

---

## Added later on 11 Nov: the tank's steel recipe fixed (user: "fix the tank")

The carbon-steel vessel was charged as ecoinvent's "steel, low-alloyed, hot rolled" (2.50 kg CO2e per kg,
already rolled at the mill) plus "sheet rolling, steel" (0.39) on top, the rolling counted twice, and in a
low-alloy grade where SA-516 is plain carbon-manganese steel. Now: "steel, unalloyed" (2.05) plus "hot
rolling, steel" (0.28) once, shell and frame alike; bending and welding stay on the cut-off register (arc
welding about 0.2 kg per metre, negligible), with average metal working for steel (2.06) as its upper. The
tank goes from **555.5 to 463.1 kg CO2e per kg of capacity (−17 %)**, 22.2 to 18.5 per kg per year.
Stale text naming Gandiglio's vessel as the inventory was corrected; the tank life (25 years) is now
labelled as the data centre's own life, no tank-specific source.

**Not yet rebuilt in Brightway.** The tank's foreground activity is built into the Brightway project the
presented version also reads, so `python -m optimiser_lca.build` waits for the final round. Until then
`h2_storage.check_against_brightway` will report 463.1 (rebuilt) against 555.5 (built).

**Checked and kept, 11 Nov 2026 (user).** The EU Joint Research Centre's *Environmental life cycle assessment
(LCA) comparison of hydrogen delivery* (JRC137953, 2024), Table 4 p. 22, builds a 30–70 bar hydrogen pipeline
from un-rolled steel (63 % unalloyed, 37 % low-alloyed, as ecoinvent builds gas pipelines) plus one forming step
on the whole mass (drawing of pipe): plain steel and one forming step, as here, not pre-rolled steel rolled
again. Its grade mix would put the steel about 3 % above the unalloyed used here. Kept at 463.1 kg CO2e per kg
of capacity; the tank's test is its carbon at ×0.5 / ×1.5.

## Added later on 11 Nov: battery cooling and control load (closed, no change)

The source LCA (Jasper et al. 2026, §2.4.5) includes cooling, standby and electronics' electricity in the
use phase only through one system round-trip efficiency (90 % liquid-cooled, one cycle a day), saying the
detailed data are not published. The model does the same with Modo's 88 %. Kept that way (user, 11 Nov
2026); stated limitation: a lightly cycled battery pays little of it, where the makers' declarations
(Trina 5.33 kW per 4,073 kWh, Gotion 4.48 kW per 2,703 kWh) put the constant part at 3.1–4.0 % of capacity
a day. No new term in the optimiser.

## Wind life extension: value kept (user, 11 Nov 2026)

27.5 % of the turbine's build carbon at 35 years (servicing 7 % + one overhaul 20.5 %, from Vestas V136/V162
and Siemens Gamesa SG 6.2-170) stays, graded assumed; tested at ×0.5 / ×1.5. State in the report: no source
itemises a 20-to-35-year extension; Vestas's servicing already includes some gearbox repairs, so it likely
leans high; the shares are from 4–6 MW turbines applied to ecoinvent's 1–3 MW one; no UK government source.

**Every item in this note is now decided.** Left: the run list and the tank's Brightway rebuild before the
test round, then the test round and the commit, on the user's word.
