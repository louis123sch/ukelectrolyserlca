# Cost source search and threshold test — 4 Nov 2026

Three questions: does a hydrogen cost feed already cover the missing figures; are
the other equipment figures good enough; is everything above a threshold costed.
**Nothing here has been applied.** No model value changed, and `h2_capex.py`,
`battery.py` and `tech_costs.py` are as they were. Every pound conversion below uses
the study's own FES 2025 cross-rates (£1 = €1.17 = $1.2815). In §2 no inflation is added,
so each figure there is still in its source's price year; §0 corrects for that.

**Applied 4 Nov 2026, with later government finds:** see *Built* in `docs/COST_GOV_FIGURES_PLAN.md`,
which supersedes the figures and "no figure found" lines here where they differ.

## 0. UK government sources first (rule set by the user, same day)

**This section supersedes the "Reading" lines of the first draft of §2**, which compared
figures across price years without inflating them. Rebased to 2025 £ with the ONS GDP deflator
(series YBGB, §1): 2017 ×1.333, 2018 ×1.308, 2019 ×1.277, 2020 ×1.220, 2023 ×1.076.

| Figure | Now | UK government figure, 2025 £ | Against ours | Source and catch |
|---|---|---|---|---|
| **Fuel cell** | £1,795/kW | **about £2,000–2,200/kW** installed; equipment alone over £1,300/kW | **UK figure 12–23 % above ours** | Baringa for DESNZ, *Hydrogen to Power Costs and Barriers* (9 Dec 2025) §4.4 and §5: over £2,500/kW installed for a pipeline-fed grid-scale system, less about £485/kW of purification our hydrogen may not need; the 80 MW Korean plant at about £2,700/kW. In 2025 £ and PEM, but "limited" evidence by its own account, and no running cost, stack share or life |
| Fuel cell, older | | £2,642/kWe fully installed, first unit, 1.4 MW (hydrogen-fed: reformer removed); £48/kWe/yr maintenance; stack 4 y now, 10 y mature | Inflated (taking its prices as 2017–18), about £3,500 | Element Energy for BEIS (2018) p. 94, from Roland Berger 2015. Supports the direction. £1,417 at 500 units |
| **Tank** | £658/kg | **about £590–600/kg** installed | **ours about 10 % high** | Element Energy p. 109: £449/kg, inflated taking its prices as 2017–18 (price year not confirmed). 50–80 bar, not 28; a supplier's quote |
| **Solid-oxide capital** | £3,015/kWe | **about £4,900–5,100/kWe** as a ratio to today's NESO PEM; £1,660/kWe as an absolute | ours 40 % low on the ratio, 80 % high on the absolute | BEIS 2021 annex. The ratio (2.46× PEM per kWe) is the consistent one, because the annex's own PEM (£675/kWe in 2025 £) is a third of NESO's £2,010. Assumes a mature plant |
| **Solid-oxide running** | £0.12/kg | **£0.50/kg** (0.34–0.86); fixed £64.70/kW H₂/yr | **ours 4× low** | BEIS 2021 annex; stack 60 % of capital, replaced every 7 y; heat at zero |
| **Battery, at the 7.1 h built** | £1,008/kW; running £20/kW/yr | **£1,371/kW; running £15/kW/yr** | **the yearly line would rise 25 %** at Modo's 5 % rate, **44 %** at BEIS's own 7.3 % (+£3.6–6.2 m/yr in the reference run) | BEIS 2022 Exhibit 3.11: £423 at 1 h (agrees with Modo's £400), +£159/kW per extra hour (ours £100). **But** it is a 2022 forecast of 2030 capital, and cell prices have fallen since, so this may overstate |

**Reversals from the first draft:** the fuel cell is not "1.7× high" and the tank is not "1.5–3× high"
on the UK-first rule. The foreign and journal figures stay as cross-checks, and they were uninflated
too. The tank's "3–10× low" on `TODO` is still not supported: the UK figure is within about 10 %.

**No UK government figure found for:** fuel-cell stack share; tank and fuel-cell fixed running cost as
a share of capital (Element Energy's £42–48/kWe/yr is the nearest); tank at 28 bar specifically.

**Generation running costs and land stay on DESNZ, which is already UK government.** `Electricity
Generation Costs 2025` (DESNZ, Jan 2026) has no fuel cell or battery cost, and defers hydrogen figures.

## 1. The hydrogen feed, and every other API (double-checked)

| API | Checked | Relevant cost data? |
|---|---|---|
| **NESO portal** `api.neso.energy` | All 131 datasets and 1,395 tables, by name and description | Only the three hydrogen tables below. Green cube: PEM 212,040 rows, alkaline 212,040, solid-oxide none. No fuel cell, tank or battery cost |
| **data.gov.uk** catalogue API | Six searches on these costs | Nothing relevant (carbon-storage licences, school energy bills, research projects) |
| **ONS time series** `ons.gov.uk/.../timeseries/ybgb/qna/data` | Live, free, no key | **Yes, for inflation only:** GDP deflator 2015–2025, release 29 Sep 2026. Not yet used by the study. `h2_prices.py:604` uses FES's 2024→2025 (+2.4 %) where this gives +3.6 %, a difference for the *one price base* job |
| The six network companies' portals | Keys held; surveyed 29–30 Oct (`COST_PLAN.md` §1.9 E) | Capacity and flexibility, plus the two scheme-cost sets already noted. No equipment prices |
| Elexon, Carbon Intensity, Renewables.ninja, postcodes | Already used by the repo | No equipment cost, by what they are |
| **European Hydrogen Observatory** | Site responds; no API found by search | We hold its production price workbook; not confirmed whether it has fuel cell or storage costs |
| US technology baseline (OpenEI) | Refused from here (403) | Not UK; not reached |
| Zenodo (Rozzi dataset) | Downloaded | A data file, not an API; not government |

**So no API, UK or otherwise found here, carries fuel cell, tank, solid-oxide or battery prices.** Those
stay on documents. The `.env` holds keys for Renewables.ninja and five network companies only.

### The NESO hydrogen dataset

The NESO portal (`api.neso.energy`) has one hydrogen dataset,
`levelised-cost-of-green-hydrogen`, with three tables: green price (`cc2dad0c`), blue
price (`3f3b1bf0`), and electrolyser capital and running costs (`88cfa584`, PEM and
alkaline only). All three are already used. Searches for "fuel cell" and "storage
cost" return nothing else. So the feed has no fuel cell, no tank and no solid-oxide.

Checked live on 4 Nov: `price_outputs/electrolyser_costs_clean.csv` equals `88cfa584`
on capital, fixed and variable cost in all 36 rows, though the portal re-stamped the
table on 24 Sep 2026.

FES 2025 Economics Assumptions (held) does not fill the gap either: its only hydrogen
store is salt caverns (DNV 2019), and it builds no fuel cell line. What it does give is
a policy precedent for `TODO` *one price base and one discount-rate policy*: Green Book
outside power, technology-specific rates in power, BEIS 2022 for storage, GDP deflator
to 2025 prices.

## 2. Figures found

### Fuel cell — now $2,300/kW = £1,795/kW (natural-gas CHP, 100 kW–3 MW, 2015, no deflator)

| Source | Held? | Figure | £/kW | Scope and catch |
|---|---|---|---|---|
| **NLR/TP-5400-91146** (Reznicek et al., Feb 2026) Tables 5, 12, 18, pp. 23, 30 | new | **$1,352/kW** ($2022), 100 MW hydrogen plant | **1,055**; 865 without US sales tax and grid spur | All-in overnight: modules, inverter and transformer, cooling, civils, substation, install, contingency, land. **Catch:** vehicle modules, 25,000 h, built for 2–10 % running; it says a data-centre build would cost more. Its web abstract says $954; the report's own tables say $1,352, used here |
| Same, running costs | | Fixed $7.03/kW/yr, tax and insurance 1.5 % of capital, stack refit 63 % of the $236/kW module | | Fixed cost assumed equal to a gas turbine's |
| Rozzi et al. 2024 dataset (Zenodo 12784516), ≥1 MW, estimates from 2018 | paper held, data new | median **€1,430/kW**, quartiles 1,200–2,379, n=16 (€2024) | **1,222** (1,026–2,033) | Uninstalled. All rows from two references, so not 16 independent views |
| Marocco et al. 2021 (ECM 238:114147) Table 5 | held | €3,947/kW at 10 kW, exponent 0.7 → €991/kW at 1 MW | 847 | Scaled by me from 10 kW. Stack 26.7 % of capital, fixed + variable running 4 %, 30,000 h |

**Stack share (now 17.2 %, frozen from a carbon split):** Marocco 26.7 %; Rozzi replacement
median 25 % (n=23, quartiles 18–42); audit §3.4 reads Battelle as 22–41 % hydrogen-fed;
NLR's whole module is 17.5 % of plant and its refit 11 %.

**Reading, superseded by §0:** against NLR alone central looks high by about 1.7× (uninflated). The
UK government figure points the other way. NLR's cheap plant also lasts 25,000 h, where ours assumes 80,000 h.

### Tank — now €770/kg = £658/kg (a midpoint of two uncited figures)

| Source | Held? | Figure | £/kg | Vessel |
|---|---|---|---|---|
| **Marocco et al. 2021** Table 5, from Tractebel & Hinicio | **held** | **€470/kg**, running 2 %, project life | **402** | **3–28 bar**, the study's own pressure, and a 3 bar minimum for the heel. TODO names Marocco 2020 as "not held"; this later paper by the same group has the number |
| **Element Energy for BEIS, *Hydrogen supply chain evidence base*** (Nov 2018) p. 109 | new | £182k per 95 m³ vessel holding ~405 kg, installed (factor 1.3) | **449** | **UK**, installed, 50–80 bar, farms of tens. A supplier's private quote |
| Rozzi dataset, 30 bar, 50 t (ref [86] in the workbook) | data new | €207–289/kg (€2020) | 177–247 | Closest in size and pressure. Uninstalled: ×1.3 gives 230–321 |
| Rozzi fit (Table 4): €467/kg at 2,028 kg, exponent 0.83 | held | €356 at 10 t, €241 at 100 t | 304, 206 | All pressures; R² low |
| Sens et al. via Viole 2023; Chen; Palys 2026 | held | $286–780/kg (2030); $600; $900 | 223–609; 468; 702 | Compressed gas, pressures vary or high |

**Reading, corrected by §0:** before inflation the published vessel prices cluster at about
£200–450/kg; the UK figure inflated is about £590–600/kg, within about 10 % of central £658/kg.
Either way this contradicts the `TODO` line "~3–10× low". That figure came
from a textbook shell-mass correlation applied to the carbon side's 313 kg of stainless per
kg of hydrogen. A thin-walled steel cylinder needs about the same steel per kg of hydrogen at
any pressure, about 130 kg/kg in carbon steel by my estimate at the Element Energy vessel's
pressure (not sourced). So the mismatch is real, but the outlier may be the carbon side's
heavy small stainless vessel rather than the price. **Needs your decision on the default
vessel before either side moves.**

### Solid-oxide electrolyser — now PEM × 1.5 = £3,015/kWe, variable as PEM's £0.123/kg, life 25 y

| Source | Held? | Figure | Note |
|---|---|---|---|
| **BEIS *Hydrogen Production Costs 2021* annex**, 10 MW, commissioning 2025 (real 2020 £) | new | Capital **£891 / £1,304 / £2,081 per kW H₂ HHV**, about £1,360/kWe medium; fixed £53/kW H₂/yr; **variable £0.0104/kWh H₂ = £0.41/kg** (0.28–0.70); stack 60 % of capital, replaced every 7 y; 30 y life | UK government. Assumes a mature plant, and heat at zero. In the same annex PEM is £553/kWe against NESO's £2,010 today, so its absolute level is dated: its ratio to PEM is 2.5× per kWe |
| **CATF, *Solid Oxide Electrolysis: A Technology Status Assessment*** (Nov 2023) Table 5, p. 26 | new | System **$917–4,000/kW**, stack $250–2,000 ($2020); 20,000–50,000 h; 38 kWh/kg with steam import | £716–3,121. Stack life today 2.5–5 y at full load |
| Rozzi dataset, SOEC estimates from 2018 | data new | median **€3,069/kW**, quartiles 2,150–3,869, n=21; replacement 30 % (€2024) | £2,623 (1,838–3,307). Includes future-year rows |

**Reading, corrected by §0:** £3,015/kWe sits inside the non-government ranges, but below the
BEIS ratio. **The clear error is variable cost: £0.123/kg against BEIS's £0.41/kg in 2020 £, £0.50/kg
in 2025 £, about 4× low.** The heat is still free as well (§3).

### Battery — now £300/kW + £100/kWh, running 2 %

The Modo page (re-read 4 Nov) gives only about £400/kW for one hour. **The £100 per extra
hour is not on it**, yet `battery.py:235` grades it `transcribed`, citing Modo. It sets
£10.05 m of the reference run's £14.31 m battery line, on a **7.1-hour** battery. FES also
lists Modo's capital data as "Not public data".

**BEIS 2022, *Benefits of Long Duration Electricity Storage*, Exhibit 3.11, p. 30** (real 2019 £,
2030 capital; public; what FES itself uses for storage running cost):

| Hours | 1 | 2 | 4 | 6 | 9 |
|---|---|---|---|---|---|
| Capital £/kW | 331 | 449 | 696 | 930 | 1,328 |
| Running £/kW/yr | 5 | 7 | 10 | 11 | 13 |

That is about £125/kW per extra hour and £1,073/kW at 7.1 h before inflation, against our £1,008.
**Corrected by §0: in 2025 £ it is £159/kW per hour and £1,371/kW, so the source covers the duration
built but does not simply confirm our number.** Running cost is about £15/kW/yr at 7 h in 2025 £ against
2 % = £20/kW/yr. Its hurdle rate is 7.3 % (10 % at 9 h) against Modo's 5.0 %. Rozzi's €328/kWh median
for 4 h and up is higher still, but it is an older literature.

### Others

- **Wind, solar (DESNZ/Arup 2024):** sound source, right table. The problem is scope (§3).
- **PEM, alkaline (NESO):** sound, and confirmed against the live feed.
- **Connection and network charges:** wait for the ±50 % test.
- **Fuel-cell and tank fixed running cost:** no longer need to be unsourced: NLR and Marocco give figures.

## 3. Is everything above a threshold costed? No

The cost side has **no threshold test**: `optimiser_lca/exclusions.py` and `optimisation/cutoff.py`
cover carbon only. Below, the carbon rule (each item under 1 % of its technology, under 5 % together,
no change to the best design) is applied by hand to the reference run: London, 100 MW IT, £110.6 m/yr,
285.7 MW wind, 441.2 MWp solar, 122 MW / 864 MWh battery.

| Not costed | Evidence | £ m/yr | % of its technology | Test |
|---|---|---|---|---|
| Wind land | DESNZ §5.8.1: £19.5k/MW/yr (£9–36k, mostly Scottish sites) | +5.57 | 13 % | **fails** |
| Wind business rates | §5.8.2: £12.0k/MW/yr | +3.43 | 8 % | **fails** |
| Solar land | §6.8.1: about £1k/acre/yr; 5 acres/MWp is **my assumption** | ~+2.2 | ~10 % | **fails** |
| Solar business rates | §6.8.2: £1.8k/MW/yr | +0.79 | 4 % | **fails** |
| *Should come out:* generators' own network charges, for plant behind our meter | DESNZ tables; audit §3.1 | −4.86, −0.71 | −12 %, −3 % | **fails** |
| Price year: 2023 £, not 2025 £ | ONS deflator: +7.6 % (audit §4 estimated ~6 %) | +4.80 | 8 % | **fails** |
| Building-period finance | our cost per MWh against DESNZ's own: £44.07 vs £45.80; £45.26 vs £46.50 (the gap's cause is my inference) | ~+2.2 | 3–4 % | **fails** |
| Decommissioning | §5.8 and §6.8: £31k and £15k/MW once, at end of life | ~+0.15 | under 1 % | passes (and carbon leaves end-of-life out) |

**Net about +£13.5 m/yr, +12 % on this bill**, before any battery change (§0). All of it lands on wind and
solar, which become roughly 20 % dearer *relative to grid power*. That is the comparison the study exists to make, so the third
limb (no change to the best design) very likely fails. **Not solved; that needs a run.**

Only when hydrogen is built:

| Not costed | Evidence | Size |
|---|---|---|
| Tank heel | Marocco 3 bar minimum; audit §3.3 | 4–22 % of the tank line, which is **£50.1 m of £225.8 m** in the 48 MW-capped London run |
| Major-hazard compliance | COMAH: hydrogen lower tier 5 t, upper tier 50 t (Scottish Government guidance; FNC for BEIS 2022 gives the 50 t; Schedule 1 itself not read) | No cost figure found. The capped runs hold 775, 193 and 108 t: all upper tier |
| Tank space | 775 t at 28 bar is about 340,000 m³ (my arithmetic), or about 1,900 Element Energy vessels | No land cost and no area limit |
| Fuel-cell installation, transformer | Inside NLR's figure if adopted; not in the DOE figure used now | Installed is 1.2–2× equipment (audit §3.4) |
| Solid-oxide heat | 5.24 kWh/kg × £33.74/MWh ÷ 0.9 ≈ £0.20/kg at wholesale gas (my arithmetic) | About 6 % of its line at 50 % running. Solid-oxide only |
| Compressor capital | `REVIEW_RESPONSE_PLAN.md` §6.3: £19–109k per MW; Element Energy has a compressor table; Rozzi has 70 rows | Zero on the PEM default; solid-oxide or higher pressure only |

Could not size:

- **Supplier margin**: unpublished (`levies.py:89`). About £1.60/MWh would cross 1 % of the grid line (my estimate).
- **Battery land, rates, transformer**: Modo does not say what its figure includes.
- **Land for any asset at an urban site**: DESNZ's figures are rural, and `dc_model` has no area limit, so London builds 578 MW of wind and 765 MWp of solar on no land at all.

Outside the boundary and worth stating: the data centre's own building and IT carry carbon as a constant
but no cost. They would not move a design, but they do mean the £/MWh is not an all-in figure.

## 4. Not reached

- Elicit: this account's plan has no API access, so its paper search could not be used.
- NREL's battery projections and technology baseline: the host did not resolve from here.
- Battelle 2016 (stack share): located, not read; the 15 % found is one slide for a 250 kW CHP unit.
- IEAGHG 2024 *Analysis of Electrolytic Hydrogen Technologies*: named by FES as a source; not read.

## 5. Sources not yet held

No copies were saved to OneDrive. **Licence catch:** the Rozzi dataset is CC BY-NC-ND (non-commercial,
no derivatives), which matters if a figure reaches the commercial brief; the paper's own fit is the safer citation.

- [Baringa for DESNZ, Hydrogen to Power Costs and Barriers](https://assets.publishing.service.gov.uk/media/69663541e8b93f59c3aecd76/hydrogen-to-power-cost-barriers.pdf)
- [DESNZ, Electricity Generation Costs 2025](https://assets.publishing.service.gov.uk/media/69ba657326909a14239612e3/electricity-generation-costs-report-2025.pdf)
- [ONS GDP deflator, series YBGB](https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ybgb/qna)
- [NLR/TP-5400-91146](https://docs.nlr.gov/docs/fy26osti/91146.pdf) ([OSTI record](https://www.osti.gov/biblio/3018256))
- [Element Energy, Hydrogen supply chain evidence base](https://www.gov.uk/government/publications/hydrogen-supply-chain-evidence-base)
- [BEIS Hydrogen Production Costs 2021](https://www.gov.uk/government/publications/hydrogen-production-costs-2021) and [annex](https://assets.publishing.service.gov.uk/media/611a706ed3bf7f63a7b29216/Hydrogen_Production_Cost_2021_Annex.xlsx)
- [CATF, Solid Oxide Electrolysis](https://www.catf.us/resource/solid-oxide-electrolysis-technology-status-assessment/)
- [BEIS 2022, Benefits of Long Duration Electricity Storage](https://www.gov.uk/government/publications/benefits-of-long-duration-electricity-storage)
- [Rozzi et al. dataset on Zenodo](https://zenodo.org/records/12784516)
- [FNC for BEIS, Hydrogen infrastructure requirements up to 2035](https://assets.publishing.service.gov.uk/media/63973bfde90e077c2e1ce834/Hydrogen_infrastructure_requirements_up_to_2035_-_report.pdf)
- [Scottish Government, hydrogen planning and consenting guidance](https://www.gov.scot/publications/hydrogen-planning-consenting-guidance/pages/5/)
