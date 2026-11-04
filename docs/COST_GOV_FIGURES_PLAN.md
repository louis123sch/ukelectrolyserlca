# Plan: putting the UK government cost figures into the model — 4 Nov 2026

**Rule (user, 4 Nov):** UK government sources are the most preferable. Evidence for every figure:
`docs/COST_SOURCE_SEARCH_2026-11-04.md`. **Built 4 Nov 2026, uncommitted; see *Built* at the foot, which supersedes
figures above it where they differ.** Effort: XS < 1 h, S ≈ half a day,
M ≈ 1–2 days. Before-and-after numbers are hand arithmetic, not solves; step 1 of the build
replaces them with the code's own.

**Not before the ±50 % connection sweep ends.** It is still writing to
`optimisation_outputs/sensitivity_connection_*`, and any re-started process would read edited cost code.
Its supporting work (`dc_inputs.py`, `dc_pareto.py`, `sensitivity.py`, the cost map) is also uncommitted, so
commit that first.

## What moves

| Coefficient | Now | After (central) | Change | Source |
|---|---|---|---|---|
| `cost_wind`, £/MW/yr | 147,073 | 180,544 | +23 % | DESNZ/Arup, ONS |
| `cost_solar`, £/MWp/yr | 48,368 | 58,667 | +21 % | DESNZ/Arup, ONS; one assumed acreage |
| `cost_batt_p`, £/MW/yr | 34,903 | 31,025 | −11 % | BEIS 2022, at Modo's 5 % rate |
| `cost_batt_e`, £/MWh/yr | 11,634 | 16,508 | +42 % | BEIS 2022, at Modo's 5 % rate |
| `cost_fc`, £/MW/yr | 99,842 | 121,384 | +22 % | Baringa for DESNZ, Element Energy |
| `cost_fc_bop_per_mw`, £ | 1,486,089 | 1,834,020 | +23 % | same |
| `cost_fc_stack_per_mw`, £ | 308,698 | 380,980 | +23 % | same; the 17.2 % split stays a hole |
| `cost_tank`, £/kg/yr | 64.64 | 58.85 | −9 % | Element Energy, ONS |
| `cost_ely` solid-oxide, £/MW/yr | 318,766 | 588,093 | +84 % | BEIS 2021 annex (D3) |
| `cost_ely_variable_per_kg` solid-oxide, £ | 0.123 | 0.50, plus heat 0.20 on gas | ×5.7 | BEIS annex; FES gas price |
| PEM, alkaline, connection, network, levies | | unchanged | | NESO etc. already UK sources |

Reference run (London, 100 MW, £110.6 m/yr, build held fixed): wind and solar +£14.1 m, battery +£3.7 m,
so **about +£17.8 m, +16 %**, before the optimiser re-chooses. The grid line does not move, so generation
and storage get dearer against imports, and the best design will very likely shift.

## Build order

### 1. Baseline and the shared inflation figure (S)
- Snapshot every `Tech` cost field for the reference cases, as the cost-map work did, to print a before-and-after table.
- **New `optimisation/price_base.py`:** `GDP_DEFLATOR` (ONS YBGB, 2015–2025, in Python per the no-data-files rule) and
  `to_2025(value, year)`, recorded with `T.cost`. Register `ons_gdp_deflator` in `source_register.py`. A script checks the
  constants against the live series; tests stay offline.

### 2. Wind and solar: `optimisation/tech_costs.py` (M)
| Change | Where | Figures |
|---|---|---|
| Land | new rows in `ONSHORE_WIND`, `SOLAR_PV` | Wind £9.0 / 19.5 / 36.0k per MW/yr (§5.8.1). Solar £0.8 / 1.0 / 1.0k per acre/yr (§6.8.1) × acres (hole H1) |
| Business rates | same | Wind £10.0 / 12.0 / 24.0k (§5.8.2). Solar £1.0 / 1.8 / 2.5k (§6.8.2) |
| Take out generators' own network charges | `annual_cost`, opex | Subtract `connection_and_uos`: plant is behind our meter and export is refused |
| Finance during building | `annual_cost`, capital | Hurdle rate over the report's construction period |
| Inflate to 2025 | `annual_cost` | ×1.076, from 2023 |

**Built-in check:** adding the finance step reproduces DESNZ's own published cost per MWh: wind £45.94 against
£45.80, solar £46.16 against £46.50 (now £44.07 and £45.26). Pin it in a test. Decommissioning stays out (under 1 %, and
carbon leaves end-of-life out by the same rule). Offshore is out of scope and takes the same arithmetic, untested.

### 3. Battery: `optimisation/battery.py` (S)
- Replace `MODO_1H_GBP_PER_KW`, `MODO_MARGINAL_HOUR_GBP_PER_KW` (`:68-72`) with BEIS Exhibit 3.11, fitted as a straight line across
  1–9 h (within 2 % of every row): **£200/kW + £124/kWh in 2019 £, so £256/kW + £159/kWh in 2025 £.**
- Replace `FIXED_OPEX_PCT_CAPEX` (`:88`) with the same exhibit's running cost: **£6.35/kW + £1.23/kWh a year**. That means a
  per-kW and per-kWh running cost rather than a share of capital, in `annual_costs` (`:230-262`) and `cost_table` (`:358`).
- Low case: today's Modo figures, as a real market floor. High case: BEIS × Modo's survey spread (`:81`). See D2.
- Fix the wrong grade: the £100 at `:235` is marked `transcribed` but is not on the page. Rewrite `SOURCES.md:291-300`.

### 4. Fuel cell: `optimisation/h2_capex.py` (S)
- `FC_USD_PER_KW` (`:85`) becomes `FC_GBP_PER_KW`: **low £2,015** (Baringa's "over £2,500" less £485 purification), **central £2,215**
  (the Korean plant's £2,700 less purification), **high £2,700** (purification kept, for pipeline hydrogen). Already 2025 £, so
  the US dollar step at `:151-154` goes.
- `FC_FIXED_OPEX_FRAC` (`:90`): **2.5 / 2.9 / 2.9 %**, from Element Energy's £42–48/kWe/yr inflated. The current 3 % turns out nearly right, now sourced.
- Set `FC_INCLUDES_REFORMER` false, and rewrite the module docstring and `run()` text ("none of these is UK").

### 5. Tank: `optimisation/h2_capex.py`, `optimisation/dc_model.py` (S)
- `TANK_EUR_PER_KG_CAPACITY` (`:105`) becomes `TANK_GBP_PER_KG_CAPACITY`: **central £599** (Element Energy £449 × 1.333, if 2017 prices).
  Non-government range: **low about £390** (Rozzi's 30 bar, 50 t row × 1.3 installed), **high £889** (today's top). The € step at `:238-241` goes.
- **Heel:** `tank <= usable × cap_tank` at `dc_model.py:517`, new `Tech.tank_usable_fraction`, central 0.89 (3 of 28 bar, Marocco
  2021). This moves carbon too, so it has its own commit and its own before-and-after.
- Running 2 % stays, now citing Marocco.

### 6. Solid-oxide electrolyser: `optimisation/h2_capex.py`, `optimisation/dc_inputs.py` (S)
- `SOEC_MULTIPLIER_OF_PEM` (`:111`) from the BEIS 2021 annex; see D3. Change it in both `electrolyser_cost` (`:292-307`) and `electrolyser_costs` (`:356-366`).
- Variable: new `SOEC_VARIABLE_GBP_PER_KWH_H2` **£0.0070 / 0.0104 / 0.0178** × 1.22 × 39.4 = **£0.34 / 0.50 / 0.86 per kg**.
- Fixed: **4.07 %** (£53.02 on £1,304). Life stays 25 y to match the carbon side, which `audit.py:397` requires.
- Heat: add 5.24 kWh ÷ 0.9 × gas price to `cost_ely_variable_per_kg` at `dc_inputs.py:998` in the `gas_boiler` scenario only
  (`electrolysers.py:140-153`); in `electric_boiler` it is already bought power. Gas price: hole H6.
- Set `SOEC_HAS_NO_SOURCE` false. Default technology stays PEM, so default runs do not move.

### 7. A cost threshold test (M)
Mirror `optimiser_lca/exclusions.py` and `optimisation/cutoff.py`: **`optimisation/cost_exclusions.py`** with an upper estimate per item, rules 1 and 2
per technology, rule 3 as a `sensitivity` knob. Keep the user's principle from carbon: a sourced, in-boundary cost is always in, and
the test applies only to items no held source itemises. First entries are the holes marked † below.

### 8. Records and maps (S, plus run time)
- Every new number through `T.cost` with `cites`; `source_register.py` gains Baringa, Element Energy, BEIS 2021 annex, BEIS 2022, ONS. Retire
  `doe_fc_chp_targets` and `h2_vessel_literature` (the checker fails on a source nothing cites).
- Add tests pinning each central value: today almost none are pinned (the audit's finding).
- `SOURCES.md`, `DATA_GAPS.md`, `ASSUMPTIONS.md`; delete the closed `TODO.md` lines; update the stale status in `COST_PLAN.md`.
- Rebuild and republish **both** maps (shared code digest), about 13 min for cost plus the LCA build.

### 9. Re-run (run time, hours)
- Full test suite, `audit.py`, `check_cost_map.py`, `check_connection_chain.py`.
- Reference cases on the new costs, with a printed before-and-after of designs. Rule 3 of step 7.
- **One case of the ±50 % connection test again:** today's run is on the old costs, and dearer generation makes the
  grid connection matter more, so its answer may not carry over. About 3.5 h.

## Decisions needed

| # | Decision | Options | My lean |
|---|---|---|---|
| **D1** | Default vessel | Accept a stated mismatch (cost: Element Energy 50–80 bar carbon steel; carbon: Gandiglio 28 bar, 313 kg stainless per kg) or find a bulk-vessel inventory | Accept and state it for now; carbon's vessel is the likelier outlier, which is an LCA job |
| **D2** | Battery central | BEIS as central (a 2022 forecast of 2030 prices; cell prices have fallen since), or Modo as central and BEIS as high | BEIS central by your rule, with the age stated and Modo as the low case |
| **D3** | Solid-oxide capital | Ratio to today's PEM, 2.46× = £4,945/kWe, above every non-government range (top about £3,300); or the annex's absolute £1,660/kWe, dated | Ratio, because it keeps the types consistent; low case the absolute. The most uncertain figure here |
| **D4** | Discount rate on hydrogen assets (6 %, unsourced) | BEIS 2021 annex uses 10 % on the rows read; NESO's grid runs 6–10 %; BEIS 2022 has 7.3 % for batteries; Green Book 3.5 % | Separate job, last, because it moves everything. At 10 % hydrogen capital rises about 40 %. Battery stays on Modo's 5 % until then, or the battery line rises 44 % rather than 25 % |
| **D5** | Which inflation series | ONS YBGB now gives 2024→2025 +3.6 %; `h2_prices.py:604` uses FES's +2.4 % | ONS everywhere, and move `h2_prices` too |

## Holes that remain after all of this

**No UK government figure exists that I could find.** † = goes on the threshold test.

| # | Hole | Stands in | Size | Next step |
|---|---|---|---|---|
| H1 | **Solar acres per MWp** † | 5 acres, assumed | ±£0.4 m per acre on reference | Planning data or DESNZ's solar roadmap |
| H2 | **Fuel cell stack's share of cost** | 17.2 %, frozen from a carbon split | Sets how much running hard costs; non-government 11–27 %, Battelle reading 22–41 % | Read Battelle 2016; sweep meanwhile |
| H3 | **Fuel cell lives** | Stack 10 y, rest 20 y, 80,000 h | Element Energy says 4 y now, 10 y at maturity; Baringa silent. Moves carbon too | Existing `TODO` sweep; read Roland Berger 2015 |
| H4 | **Tank price year and pressure** | Assumed 2017 prices; 50–80 bar for a 28 bar vessel | About 2 % on year | Check Element Energy's price base statement |
| H5 | **Tank price range** | Non-government low and high | No UK range exists | Accept and state |
| H6 | **Gas price for solid-oxide heat** | FES wholesale £33.74/MWh | £0.20/kg at wholesale; retail is higher | DESNZ *Gas and electricity prices in the non-domestic sector* is the right table: located, not read |
| H7 | **Battery cost today** | BEIS's figure is for 2030 | Could overstate; see D2 | None found; Modo's survey is not public |
| H8 | **Battery land, rates, transformer** † | Nothing | Modo and BEIS silent on scope | Ask Modo, or estimate for the test |
| H9 | **Fuel cell and tank land, insurance, rates** † | Inside 2.9 % and 2 % at best | Element Energy's figure is maintenance only | Estimate for the test |
| H10 | **Major-hazard compliance** † | Nothing | Hydrogen over 50 t is upper tier: all three capped runs are (108–775 t) | No cost source; read COMAH Schedule 1 and look at HSE's charges |
| H11 | **Urban land and no area limit** † | DESNZ rural rents; `dc_model` has no limit | London builds 578 MW of wind on no land. A validity issue more than a price | **Needs its own decision:** an area limit per site is a model change, not a figure |
| H12 | **Supplier margin** † | Nothing | Unpublished (`levies.py:89`); about £1.60/MWh crosses 1 % of the grid line | Estimate for the test |
| H13 | **Hydrogen compressor capital** † | Nothing | Solid-oxide or higher pressure only; zero on the PEM default. Element Energy has a table | Check for double counting first (`REVIEW_RESPONSE_PLAN.md` §6.3) |
| H14 | **Finance during building, other assets** | Wind and solar only in step 2 | BEIS: battery 1 y; annex: electrolyser 3 y; none for fuel cell, tank | Apply where a government build time exists, with D4 |
| H15 | **Discount rate** | 6 % unsourced | See D4 | D4 |

## Built, 4 Nov 2026

Steps 1–8 are in the working tree, uncommitted, on D1 accept, D2 BEIS central, D3 ratio, D5 ONS. D4 is not applied.
Where this differs from the plan above, this stands: the research that ran alongside the build found more government figures.

| Changed from the plan | Now | Source |
|---|---|---|
| Solar acres (H1) | 4 per MWp, not an assumed 5 | DESNZ, *Land utilised by solar PV*, Dec 2024 |
| Gas price (H6) | £41.49/MWh, large site including the levy; heat £0.23/kg | DESNZ table 3.4.2, 2025; boiler 95 %, Element Energy p. 95 |
| Stack share (H2) | 45.4 %, not 17.2 % | Element Energy pp. 93–94, a chart read |
| Tank running | 2.97 %, not 2 % | Element Energy p. 112 |
| Tank land | +£2.09/kg/yr, failed the test | Element Energy p. 110, DESNZ rent |
| Fuel cell insurance | +0.23 % of capital, failed the test | DESNZ/Arup ratio |
| Supplier margin (H12) | +£4.19/MWh on imports, failed the test | CMA 2015, DESNZ table 3.4.1 |
| Offshore wind | keeps its network line, no building finance | Its export is paid through that line; finance takes it further from its LCOE. Out of scope |

**Measured, one reference solve** (London, 100 MW IT, 2025, 2-hour steps, room mode, the cost map's run; bought hydrogen's file not yet regenerated, none is bought):

| | Before | After |
|---|---|---|
| Total, £ m/yr | 110.6 | **128.0 (+16 %)** |
| £/MWh served | 90.18 | 104.35 |
| Wind, MW | 285.7 | 273.6 |
| Solar, MWp | 441.2 | 395.5 |
| Battery, MW / MWh | 122 / 864 | 111 / 704 |
| Grid, MW | 120 at 33 kV | 123 at 132 kV |
| Grid energy and network, £ m | 28.3 | 35.7 |

**The design moved**, so rule 3 of the threshold test cannot be assumed: the included estimates were put in because they fail rule 1.

**Remaining holes after the build**

| # | State | What is left |
|---|---|---|
| H1, H2, H4, H6, H9 (tank running), H12 | Closed on government figures | Chart read for H2; price year inferred for H4 |
| H3 Fuel cell lives | Open | Element Energy says stack 4 y now, 10 y mature; no government hours or system life. Moves carbon too, so not changed |
| H5 Tank range | Stated | No UK range exists |
| H7 Battery today | Open | No current government price by duration. LCP Delta for DESNZ (2024) has £400k/MWh for long duration; Modo's 2 h is about £460/kW against the fit's £573 |
| H8 Battery scope | Partly | Land passes the test. Rates: no figure. BEIS never says what its capital includes; Mott MacDonald for BEIS (2018) lists electrical systems and civils in, connection out |
| H9 Fuel cell, tank insurance, rates | Partly | Fuel cell's insurance is an estimate; tank's may sit inside the 2.97 %, not itemised |
| H10 Major-hazard compliance | **Sourced, not built** | A step on tonnes, so it needs a switch in `dc_model` |
| H11 Urban land and area | **Decision** | The biggest validity question: see `ASSUMPTIONS.md` §4 |
| H13 Compressor | Open | Element Energy's table starts at 82 MW; zero on the PEM default |
| H14 Finance, other assets | Open, with D4 | Battery 1 y (BEIS), electrolyser 3 y (annex); none for fuel cell or tank |
| H15, D4 Discount rates | **Government answer found, not applied** | CEPA for DESNZ (Oct 2025), Table E.1: electrolyser 10.1 %, lithium batteries 8.9 %, onshore wind and solar 7.6 %. Moves every asset |

**Checked again, 4 Nov 2026, for sense and UK relevance. No model value changed.**

Re-read at source and confirmed: CMA Table 1 (2.0 %); CEPA Table E.1; DESNZ solar land (future sites 1.6–2 ha, 4–5 acres, per MW: the model takes the low end); planning database (London 12.6 MW onshore wind operating, four sites; South East 112.9 MW); MHCLG industrial land (London £8.5–26 m/ha, Manchester £1.0 m/ha); HSE upper tier one-off, best estimate £118k.

*Business rates, examined and kept.* SI 2022/405 exempts on-site renewable plant and machinery (wind, solar, fuel cells, their storage and transformation) in England and Wales until 31 March 2035. Its memorandum says this brings on-site generation "into line" with off-site generators, who already had the same exemption. The DESNZ/Arup respondents are those generators and still report £12k/MW/yr, so the figure already reflects the exempt position. It concerns Class 1 plant only. Scotland has its own rules, not read.

*Finance during building, confirmed.* DESNZ/Arup §3.6.1.2 says capital excludes interest during construction, so adding it is not a double count.

| Evidence behind the figure | Figures |
|---|---|
| **UK data** | Wind and solar capital, running cost, land, rates (survey of UK developers); gas and electricity prices; levies; national and local network charges; connection prices; solar land; planning database; land values; CMA margin (FY09–13, so old) |
| **UK government document, foreign or modelled evidence** | Fuel cell capital (a Korean plant, from a trade news report); fuel cell maintenance and stack (Roland Berger, European gas units with the reformer removed); installation factor (US DoE); battery (AFRY model forecast of 2030); solid-oxide (BEIS modelled mature plant); membrane and alkaline (NESO, from BloombergNEF, Aurora, IEA, Danish Energy Agency, TNO); tank (one supplier's quote, nationality not stated) |
| **Not UK, not government** | Tank's 3 bar minimum (Italian plant; physics, so travels); tank low case (Rozzi); tank high case (uncited); Modo's 5 % rate is UK but not government; grey and blue bought hydrogen (EU observatory) |

*Do not yet make sense, or need watching:*
- **Fuel cell stack cost.** £1,006/kW per replacement is 77 % of Baringa's £1,300 equipment figure and above every other share read (11–41 %), so `docs/COST_BEST_SOURCE_PLAN.md` replaces it. Corrected the same day: this section first called the stack's cost and life mismatched. Element Energy's 4 years is continuous running, about 32,000 h, which the model's 30,000 h duty limit already charges; its 10-year calendar life only binds on lightly used units. The share moves the total about 2 % at the calendar life.
- **Solid-oxide bracket:** the low case (£1,660/kWe) is below the membrane type's £2,010 and central (£4,945) is above every non-government range. Report it as a scenario only.
- **Battery central** probably runs high against today's market at short durations (2 h: £573 against Modo's about £460/kW); the low case's power part (£300/kW) exceeds central's (£256/kW), though the low system is cheaper above about 1 h.
- **Battery rate and capital are mixed:** BEIS capital with Modo's 5 % (BEIS itself uses 7.3 %).
- **Price years still mixed:** network charges, levies and connection prices are 2026/27 money, wholesale is 2025, the rest real 2025. Small, but the study is not yet on one base.
- **Wind and solar's own grid connection** stays in capital (DESNZ's £303/kW and £112/kWp "infrastructure": to the nearest grid point). Behind our meter some of that is still needed, so it may overstate; no figure splits it.
- **Land:** Scottish-weighted wind rent and rural solar rent applied at every site.

**To finish after the connection sweeps end** (they read `h2_prices_recommended.csv`): regenerate that file, rebuild and republish both maps, re-run the reference
cases and one ±50 % case on the new costs, and run `python -m optimisation.sensitivity cost_cutoff`.

**Carried over, not touched here:** exact transmission loss factors (Elexon portal); National Grid's transformer-only substation prices; network tariffs over
the asset's life; bought hydrogen's carbon-storage and haulage items; and anything the ±50 % test retires.
