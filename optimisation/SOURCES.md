# Source register

Every number the optimisation study uses, where it came from, and how far it
can be trusted. Three provenance grades are used throughout the code and in
the tables below:

| grade | meaning |
|---|---|
| **transcribed** | copied from a named table in a named published document, or pulled from a public API |
| **derived** | computed from transcribed values plus this project's own inventories, with the arithmetic in the code |
| **assumed** | a scenario choice with no source. Every one is flagged in the module that uses it and printed in its output |

Price basis throughout is **real 2025 GBP**. Where a source publishes in EUR
or USD, conversion uses the FES 2025 Data Workbook's own cross-rate table
(2025: GBP→EUR 1.17, USD→EUR 0.913, so USD→GBP 0.7803) and its GDP deflator,
so every currency conversion in the study traces back to one published table.
Emissions are IPCC 2021 GWP100 on ecoinvent 3.9.1 apos throughout.

---

## Baseline 1 — data centre on the GB grid
`baseline_grid.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Data centre inventory | 1.60e9 kWh over 25 y; 21,036 t CO₂e fixed | transcribed | Zhang, M., Carbajales-Dale, M., Ma, X., Guo, L., Fan, C. (2025), hyperscale Virginia data centre. Built into `data centre foreground` by `optimiser_lca/data_centre.py` |
| Continuous load | 7,306 kW | derived | 1.60e9 kWh ÷ 25 y ÷ 8760 h — the inventory's own figure, not an added assumption |
| Grid carbon intensity | half-hourly, mean 0.1585 kg CO₂e/kWh delivered at high voltage. History: 0.2369 on the conventional gas plant; 0.1882 after the gas fix; 0.1585 after the import split, delivery terms and grid solar (all 13 Oct 2026) | derived | NESO Carbon Intensity API, regional (region 13, London), with Elexon FUELHH interconnector flows, via `optimisation/grid_build.py` |
| Per-fuel life-cycle scores | gas CCGT 387, coal 1,061, nuclear 7.4, solar 30.9; imports FR/BE/NL/NO/DK/IE 74/178/479/22/207/352 g CO₂e/kWh | transcribed | Activities named by exact identity in `optimiser_lca.grid.SOURCES`, resolved by `lca_helpers.resolve_exact`, which refuses zero or several matches; IPCC 2021 GWP100 with long-term emissions, as every asset is. Gas was the conventional plant (558) until 13 Oct 2026. Nuclear is BWR, as ecoinvent's own GB market proxies the AGR fleet. Solar is the Smith 2024 plant (`optimiser_lca/upv.py`) at ecoinvent's GB yield, replacing the 2008 El Tesoro plant (79.8). NO and DK are those countries' own HV markets — ecoinvent has no GB import activity for them, and its FR/BE/NL/IE ones are the exporter's HV market under another name |
| Import split | per half-hour: Elexon FUELHH flow on each link × a per-region attribution. London FR 74 / BE 16 / NL 8 / NO 2 % over 2025 | derived | `optimiser_lca.grid.IMPORT_ATTRIBUTION`, fitted by `grid_build.fit_import_attribution` (non-negative least squares of the region's API import share on the ten links' flows, 2025; London R² 0.70). Replaced ecoinvent's GB-market split, FR 63 / NL 30 / IE 7 % on every region: −29 g/kWh on London 2025 |
| Delivery to the facility | ×1.0338 on generation + 1.93 g CO₂e/kWh network (high voltage) | derived | ecoinvent 3.9.1 GB voltage chain, `optimiser_lca.grid.derive_delivery`: the HV market's 3.27 % self-loss, and the market without its electricity input — lines, cables, maintenance and the N₂O its lines emit. At 7.3 MW the facility is banded EHV2, which `network_charges.delivery_voltage` puts at high voltage. Replaced a flat 3.16 % with no network carbon: +2.3 g/kWh |
| Wholesale electricity price | half-hourly, mean £79.83/MWh | transcribed | Elexon BMRS Market Index Data, provider APXMIDP, via `optimisation/grid_build.py` (originally notebook 5) |
| Linear decomposition | `fixed + Σ kWh×EF` | derived | Validated against a full Brightway LCA to 1e-6 by the script itself |

---

## Generation costs — wind and solar
`tech_costs.py`

All three technologies are **transcribed**, real 2023 prices as published.

| Technology | Source |
|---|---|
| Onshore wind | DESNZ / Ove Arup & Partners, *Renewable Energy Generation Cost and Technical Assumptions — Onshore Wind and Solar PV, Cost of Electricity Report Update 2024*, ref 299867-00, Final, 14 July 2025. **Table 3, p.6** |
| Solar PV (>5 MW) | Same report, **Table 4, p.7**. Costs are per **kWp DC**, not kW AC |
| Offshore wind | DESNZ / Ove Arup & Partners, *…— Offshore Wind, Cost of Electricity Report Update 2024*, Final, 24 July 2025. **Table 3, p.6**. Infrastructure **excludes** OFTO transmission, recovered via TNUoS inside opex |
| LCOE cross-check | Onshore/solar **Table 5, p.8**; offshore **Table 4, p.7** |

Hurdle rates are each report's own pre-tax real figure — onshore 5.8 %,
offshore 6.2 %, solar 5.0 % — not a single project WACC.

**Verification built in.** `check_against_price_outputs()` asserts the onshore
wind rows still match the independent transcription the retired `5.prices.ipynb`
wrote to `price_outputs/static_cost_assumptions.csv` (now a frozen file). The
LCOE cross-check reproduces each report's own published LCOE to within 8 %;
the residual is methodological (this module uses a plain CRF annuity, the
reports use the DESNZ LCOE calculator, which also discounts construction-period
spend). That check is what caught the reports' inverse case-pairing, where a
low-cost scenario is paired with a **high** load factor and lifetime.

---

## Hydrogen prices by colour
`h2_prices.py`

| Colour | Central | Grade | Source |
|---|---|---|---|
| grey (SMR) | £2.93/kg | transcribed | European Hydrogen Observatory, *Hydrogen production costs 2024*, UK rows, technology "SMR" |
| blue (SMR+CCS) | £3.78/kg | transcribed | Same, technology "Reforming with carbon capture" — matches `smr_ccs_hermesmann`. NESO's ATR+CCS (£2.90) is the cheaper-route low case |
| green, behind meter | £4.93/kg | transcribed | Same, "Renewable hydrogen directly connected to a renewable electricity generation source" |
| green, grid-connected | £8.33/kg | transcribed | Same, "Grid electrolysis". Includes €2.77/kg of UK grid fees and taxes — 29 % of its total |
| turquoise (pyrolysis) | £3.21/kg | **derived** | Constructed: 86 % grey + 14 % green, weighted by the MP-E inventory's own gas:electricity energy split (62.8 kWh gas + 10.3 kWh electricity per kg, HHV) |

Supporting inputs:

| Input | Value | Grade | Source |
|---|---|---|---|
| Green LCOH cube | 424,080 rows | transcribed | NESO Green Hydrogen Data Portal, resource `cc2dad0c-393c-4ae0-ae67-a98703169ad4`, "Levelised cost of green hydrogen modelling, 2025 to 2050" |
| Blue LCOH | ATR+CCS 2025–2050 | transcribed | NESO, resource `3f3b1bf0-4664-494f-a501-a39adabecd0d` |
| NBP gas price | £33.74/MWh HHV (2025) | transcribed | FES 2025 Data Workbook V006, sheet **CP1**, base case, 2010–2050 |
| GB carbon price | £78.96/tCO₂ (2025) | transcribed | FES 2025 Data Workbook V006, sheet **CP2**, GB total carbon price |
| Gas m³ / electricity kWh per kg H₂ | per colour | transcribed | This project's own `hydrogen foreground` activities |
| Plausibility band | grey $1–4, blue +$0.4–1, green $3–>10 per kg | transcribed | IEA, *Global Hydrogen Review 2026*, **Figure 3.20 and pp.110–111** |
| Turquoise validation | LCOH $2–4/kg; Brazilian EPE $1.5–4.4/kg | transcribed | Rego, E.E., Oller Nascimento, C.A., Ribeiro, C.O. (2026), *Economic analysis under uncertainty of turquoise hydrogen via methane pyrolysis*, Int. J. Hydrogen Energy **225**, 154378. Open access, CC BY |
| Carbon black price | $1.52/kg; 3 kg C per kg H₂ | transcribed / stoichiometric | Rego et al. 2026, **Table 1**. Credit defaulted **off** — see the module for why the market cannot absorb it |

**Verification built in.** `check_against_inventory()` re-reads the gas and
electricity coefficients from the Brightway activities and fails if the
module's constants have gone stale. A monotonicity guard fails the run if any
colour's low/central/high are out of order — it caught grey's high case
landing *below* central, because SMR exports electricity, so a dearer power
market makes grey hydrogen cheaper. A third guard fails if the two output
tables disagree by more than half a penny.

**Known discrepancy, recorded not hidden.** Rego et al. assume 16 kWh/kg for
pyrolysis; this study's MP-E inventory uses 10.29 kWh/kg. This study's
turquoise is therefore cheaper and cleaner than theirs by construction.

### Bought green hydrogen is assembled, not scored — `h2_prices.GREEN_H2_ELECTRICITY_BASES`

Green hydrogen is defined by its input: a third party makes it from renewable
electricity and sells it on. Scoring `pem_op_hermesmann_1kg_h2` whole charged it
**17.001 kg CO₂e/kg** — dirtier than grey SMR — because that activity links its
54 kWh/kg to ecoinvent's GB *grid* market at **311.22 g CO₂e/kWh** (scored
directly; the value obtained by subtracting the non-electricity burden agrees to
9.5 × 10⁻⁹). At that figure green was strictly Pareto-dominated on both cost and
carbon by all three other colours, so no objective weight and no ε-limit could
select it: every bought-green run was dead code the solver discarded.

Two things make this a propagation rather than a new judgement. **76 % of that
311 g/kWh comes from one dataset** — `electricity production, natural gas,
conventional power plant`, parameterised on 2012 IEA data and given a 39.5 % GB
share while ecoinvent's own GB CCGT gets zero — and `optimiser_lca/grid.py`
scores this study's own grid on the combined-cycle plant instead. And grid-connected electrolysis
is already modelled properly as the `grid_h2` architecture, where the LP charges
electricity carbon from its own half-hourly dispatch; the bought row was a
worse-modelled duplicate of it carrying a renewable price tag.

The coefficient is therefore assembled as
`foreground_fixed_kgco2e_per_kg + kwh_per_kg × I`, both terms from
`electrolysers_embodied.csv`. `foreground_fixed` (0.19507) already contains the
seller's electrolyser capital good, so `capital_kgco2e_per_kg_h2` must **not** be
added on top — doing so inflates the answer by 17.6 %. This is not a violation of
`assert_no_double_count`: it charges the *seller's* electrolyser per kg bought,
while `capital_kgco2e_per_MW` charges the one the LP builds.

| Basis | I (g CO₂e/kWh) | kg CO₂e/kg H₂ | Grade | Source |
|---|---|---|---|---|
| **`ecoinvent_onshore`** — default | **14.466** | **0.976** | transcribed | This study's own `electricity production, wind, 1-3MW turbine, onshore` GB activity, unrestated — `renewables_embodied.csv`, column `ecoinvent_per_kWh` |
| `iea_2025_onshore_harmonised` | 11.76 | 0.830 | transcribed | IEA, *Life Cycle Upstream Emission Factors 2025*, onshore wind median: ~50 estimates harmonised on **AR6 GWP100**, the same characterisation vintage as this study's IPCC 2021 method |
| `study_onshore_restated` | 5.635 | 0.499 | derived | `renewables.py` restated at 38.1 % LF / 35 y. **Parity sensitivity only, never a purchase basis** |

**Every basis is renewable, and the grid is not among them.** There is no
grid-carbon green hydrogen: offered as a peer of the wind options, ecoinvent's GB
grid figure would let a caller pair behind-the-meter renewable pricing with grid
carbon, which is the incoherence this section exists to remove.
`green_h2_gwp_per_kg()` refuses it by name. The value survives as
`ECOINVENT_GB_LV_GCO2E_PER_KWH` (311.220) and
`LEGACY_GREEN_H2_GWP_KGCO2E_PER_KG` (17.001) for provenance and for reproducing
pre-fix runs — deliberate friction, since reproducing a known-wrong number should
not be a keyword argument away.

**Why ecoinvent's own turbine and not the harmonised median.** It keeps the
"ecoinvent 3.9.1 apos throughout" claim intact — solar is already the one
departure — and it is the conservative end, which is the right direction for a
commodity being bought rather than built. It is corroborated four ways: IPCC AR5's
"infrastructure and supply chain typical" 15, ClimateXChange's mean 15, ZHAW
2025's European average 14.9, and both harmonised interquartile ranges. Rejecting
ecoinvent's 2008 PV plant while keeping its turbine is the position
`renewables.py` already states — a turbine is steel and concrete and ages far
more slowly than a PV module.

**Why not this study's own restated 5.635.** Re-amortising at a 38.1 % load
factor and 35-year life is right for a wind farm *the LP builds* and wrong for a
seller's, whose load factor and asset life the buyer does not control. It also
fails on its own terms: it lands **below IPCC AR5's reported onshore minimum of
7.0**, `restate()` returns capital only so it omits the 0.131 g/kWh O&M residual
(full scope 5.766) and is not comparable with published ranges that include it,
and the 38.1 % figure is a DESNZ/Arup *new-build project* assumption against a UK
fleet average of 24.1 %, where ecoinvent's implied 26.2 % is within 9 %. The tell
is that restated offshore (5.750) comes out *above* restated onshore (5.635)
despite ecoinvent's offshore being 18 % dirtier per kWh — the 50.5 % load factor
absorbs the whole difference, inverting the physical ordering.

**The two green rows differ in delivery, not in source.** Both are renewable —
that is what makes them green — but taking the power over the network rather than
off the generator's terminals costs two things, and ecoinvent separates both from
generation. They are the grid's own delivery terms (`optimiser_lca.grid.DELIVERY`)
at the seller's voltage, `h2_prices.GREEN_H2_SELLER_VOLTAGE` = **high** (> 24 kV),
so a seller's electrolyser and this study's data centre take grid electricity on
one basis. The voltage is **assumed**: a grid-connected electrolyser at the
5–100 MW scale of the GB pipeline connects at 33 kV or above, but no register of
connection voltages is published.

| Term | Value | Source |
|---|---|---|
| Loss gross-up | **1.033799** kWh generated per kWh delivered (+3.38 %) | GB `market for electricity, high voltage`, whose self-input loses 3.27 % per kWh out |
| Network carbon | **1.932** g CO₂e/kWh delivered | The HV market without its electricity input, × its throughput: N₂O emitted by the lines (corona discharge) 1.41, HVDC lines, cables and their maintenance 0.52 |

So on the default basis a grid-delivered seller's electricity is
14.466 × 1.033799 + 1.932 = **16.887 g CO₂e/kWh**, and its hydrogen
**1.107 kg CO₂e/kg** against 0.976 behind the meter — a **+13.4 %** delivery
premium. Behind the meter pays neither term, which is the physical meaning of
"directly connected". `check_grid_delivery()` re-derives every voltage's terms
from the live database and fails the run if they drift, on the same contract as
`check_against_inventory()`.

Until 13 Oct 2026 the seller paid **low-voltage** delivery — ×1.063495 and
8.2125 g/kWh, giving 1.469 kg/kg (+50.5 %). That is a household's connection, and
both terms were short even for one: the gross-up left CHP and import kWh out of
"generation" (corrected low voltage: ×1.1132) and the network omitted the N₂O and
the direct SF₆ (corrected: 11.30 g/kWh).

**The default is a 50:50 mix of the two, not one or the other.** A buyer
contracting on the open market gets a portfolio, not one plant.
`build_tech(green_h2_grid_share=...)` sets the fraction taken over the network
and defaults to `h2_prices.GREEN_H2_GRID_SHARE` = 0.5, blending price and delivery
burden together so the two can never be mismatched; `h2_variant=` pins a single
row instead. Previously an undocumented `.iloc[0]` made the second row
unreachable.

| grid share | electricity g/kWh | kg CO₂e/kg | £/kg | kg CO₂e/MWh |
|---|---|---|---|---|
| 0.00 — all behind the meter | 14.466 | 0.9762 | 4.93 | 61.66 |
| **0.50 — default** | **15.676** | **1.0416** | **6.63** | **65.79** |
| 1.00 — all grid-connected | 16.887 | 1.1069 | 8.33 | 69.91 |

The share is **ASSUMED**, and is the weakest input in this section: no GB
breakdown of green hydrogen production by connection type is published, and at
the current size of the GB electrolyser fleet any such split would be dominated by
a handful of projects. 50:50 is a neutral prior, exposed as a parameter precisely
so it can be swept rather than trusted.

Both effects run the same way, which is the reassuring part: £8.33/kg is £4.93
plus €2.77/kg of UK network fees and taxes, and the grid-connected route pays more
carbon for the same structural reason it pays more money — it is a network user.
The cost gap decomposes as taxes £1.36, grid fees £1.06, electricity £0.99
(£43.4/MWh direct-connected against £61.7/MWh from the grid), CAPEX −£0.01. That
last figure is the caveat: EHO's CAPEX is €2.771 against €2.761, i.e. **the same
utilisation is assumed for both configurations**, when a behind-the-meter
electrolyser is limited to its generator's 24–38 % load factor. CAPEX is 49 % of
the behind-the-meter total, so rescaling it alone gives £5.69/kg at CF 0.38,
£6.54 at 0.30 and £7.55 at 0.24 — £4.93/kg and strictly matched dedicated wind
are probably not available at the same time.

**LCHS is a ceiling, never a value.** The UK Low Carbon Hydrogen Standard's
20 g CO₂e/MJ LHV × 120 MJ/kg = **2.400 kg CO₂e/kg** (`LCHS_CEILING_KGCO2E_PER_KG`).
It cannot supply a coefficient: the standard excludes capital goods and therefore
sets renewable electricity to 0.0 g CO₂e/kWh, zero-rating precisely the term
being estimated here. As a bound it is worth quoting — every basis above clears
it, and the status quo failed it by 7.1×.

### Bought hydrogen is compressed onto a trailer — `h2_prices.bought_h2_compression_*`

Hydrogen this study *makes* pays a compression parasitic to enter the tank —
`h2_storage.compression_kwh_per_kg`, from the electrolyser's delivery pressure to
the vessel's. Hydrogen it *buys* paid none: `dc_model`'s tank balance takes
`h2_buy` at coefficient 1.0. The omission was one-directional and it favoured
buying, so it is now charged for every colour.

It is charged at the **seller's** gate, not the buyer's. A tube trailer arrives
at 200 bar and decants into a 28 bar vessel on pressure difference alone, so this
is a term in the purchased coefficient and the purchased price, not a compressor
added to the LP.

| Input | Value | Grade | Source |
|---|---|---|---|
| Trailer pressure | **200 bar** | transcribed | Conventional Type I steel tube trailer, and the same pressure as this study's own second `TANK_DESIGNS` entry, so the two hydrogen pressures in the study are one number. Composite trailers run 350–500 bar: +29 % and +48 % on the energy |
| Green outlet pressure | 30 bar | transcribed | Read from `electrolysers.DELIVERY_PRESSURE_BAR["PEM operation"]` rather than restated, so the seller's plant and the buyer's own PEM cannot drift apart |
| Grey / blue / turquoise outlet | 20 bar | **assumed** | Steam reformers run at 15–30 bar and the PSA purifying the product works just below its feed pressure. The Hermesmann inventories are SimaPro exports of mass and energy flows and state no pressure. 20 bar is the low end, which charges *more* compression — the honest direction for a term closing an omission |
| Specific work | `h2_storage.compression_kwh_per_kg` | derived | Isothermal minimum scaled to a real multistage machine; the same function the buyer's own compression uses, so the two sides are one thermodynamics |
| Compressor electricity price | £40 / 80 / 120 per MWh | assumed | `PRODUCER_ELEC_GBP_PER_MWH`, already used for grey and turquoise |

Resulting terms, at the default bases:

| Colour | kWh/kg | I (g CO₂e/kWh) | kg CO₂e/kg | % of production | £/kg |
|---|---|---|---|---|---|
| green | 1.194 | 15.68 | **0.019** | +1.8 % | 0.096 |
| blue | 1.450 | 311.22 | **0.451** | +14.5 % | 0.116 |
| grey | 1.450 | 311.22 | 0.451 | +4.3 % | 0.116 |
| turquoise | 1.450 | 311.22 | 0.451 | +8.3 % | 0.116 |

**The intensity is colour-specific, and that is the whole point.** Green's
compressor runs on whatever its electrolyser runs on — the same renewable basis
and the same `grid_share` treatment — because a plant defined by sitting behind a
renewable meter cannot compress on grid power. Pricing it off the GB grid would
reintroduce exactly the incoherence `GREEN_H2_ELECTRICITY_BASES` exists to
remove. Every other colour is a fossil plant already scored whole against the GB
grid its own activity links to, so its compressor takes that grid.

The consequence is the opposite of what was expected. `DATA_GAPS.md` carried
**~0.761 kg CO₂e/kg** as this term's likely size for green — which would have
been 78 % of production and might have re-dominated the row. That figure assumed
a *grid*-powered compressor. Charged coherently, green's compression is **0.019**,
and it is **blue** that the term actually moves, at 14.5 %.

**Not included: the compressor's own capital**, in either objective, and no
public per-kg figure for a hydrogen loading compressor was found. The carbon term
is complete and the cost term is a floor, so a residual bias toward buying
remains — smaller, and now in one place rather than two.

---

---

## Battery storage
`battery.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| CAPEX, 1-hour system | ~£400/kW today → ~£200/kW by 2040 | transcribed | Modo Energy, *BESS Cost and Technical Assumptions*, `docs.modoenergy.com/pages/jan-2026/uk-europe/model-assumptions/` (July 2026). Real 2025 GBP |
| CAPEX, marginal hour | £100/kW per additional hour (2025) | transcribed | Same |
| Power / energy split | £300/kW + £100/kWh | derived | The two above decompose cleanly: a 1-hour system is 1 kWh per kW, so the marginal hour *is* the energy component |
| Cost spread | avg £580k/MW at 1.9 h; 2 h median £650k/MW; 68 % within £400–700k/MW | transcribed | Modo Energy BESS CapEx Survey 2024, 30 participants, 2.8 GW |
| WACC | 5.0 % real (~7.1 % nominal) | transcribed | Modo model assumptions page |
| Asset life | 15 years | transcribed | Same |
| Degradation | ~67 % capacity remaining after 10,000 cycles (~12–15 y) | transcribed | Same |
| Cycling limit | 1–2 per day, warranty-aligned | transcribed | Same |
| Round-trip efficiency | 88 % | transcribed (weakly) | Modo's standard assumption, but **not** on the model-assumptions page itself — the least firmly sourced number in this module |
| Fixed OPEX | 2 % of capex/year | **assumed** | Modo do not publish it. FES routes battery opex to BEIS 2022 *Benefits of Long Duration Electricity Storage* instead. Flagged `OPEX_IS_PROXY = True` |
| Energy-term embodied carbon | **97.75 kg CO₂e per kWh nameplate** → **108.6 per usable kWh** | derived | `battery foreground`, built by `optimiser_lca/bess.py` (below): Jasper et al. 2026's liquid-cooled LFP container around Voß et al. 2025's LFP cell, made in China, on ecoinvent 3.9.1 apos, IPCC 2021 GWP100. Pinned as `BESS_KGCO2E_PER_KWH_NAMEPLATE` |
| Usable fraction | 0.90 of nameplate | **assumed** | `cap_batt_e` is the energy the LP can swing (`soc` runs 0..`cap_batt_e`) and Modo's costs are per usable kWh, while both sources report per kWh of cells. 0.90 is commercial operating practice; Jasper's 80 % depth of discharge would make it 122.2 |
| PCS embodied carbon | 15,930.86 kg CO₂e/unit = 31.9 /kW | transcribed | ecoinvent 3.9.1 apos, `market for inverter, 500kW` [GLO]. Unchanged; Jasper's own 800 kg PCS is excluded from the energy term so it is not charged twice |
| Legacy: EV pack | 11.368 kg CO₂e/kg at 0.1158 kWh/kg = 98.2 /kWh | transcribed | ecoinvent 3.9.1 apos, `market for battery, Li-ion, LFP, rechargeable, prismatic` [GLO]. The basis before 14 Oct 2026, kept as `EMBODIED_BASIS = "ecoinvent_ev_pack"` to reproduce old runs only |

### The grid battery's energy term — Jasper et al. 2026, Voß et al. 2025

> F.B. Jasper, Y. Zhou, H. Ersoy, M. Baumann et al. (2026), "Life Cycle
> Assessment of Grid-Scale Battery Storage", *Energy Advances* **5**, 550–570,
> doi:10.1039/D5YA00341E. SI workbook on Zenodo, doi:10.5281/zenodo.17651912,
> **CC-BY-NC**.
>
> P. Voß, B. Gruber, M. Mitterfellner, J.-D. Plöpst, F. Degen, R. Schmuch,
> S. Lux (2025), "Benchmarking state-of-the-art sodium-ion battery cells",
> *Energy Environ. Sci.* **18**, 8104–8129, doi:10.1039/D5EE00415B. Table 3
> and ESI Tables S5, S31, S32, S35, S36.

**Why it replaced the EV pack.** ecoinvent's pack is an electric-vehicle
traction pack (Dai et al. / GREET, 2016-era) with no container, racking, HVAC
or fire suppression. The "25–35 % high" finding in the review plan (§6.1–6.2)
compared it with *newer EV packs* (BatPaC, EverBatt), which is right pack for
pack and wrong for a grid battery: every stationary system source — Jasper's
inventory, and the Trina (140.7, DC block), Sungrow (152–160 with PCS) and
Huawei (106–114, on 3.9.1) EPDs — lands **above** 98.2, because the enclosure
is 18–23 % of a DC block's carbon and a whole container is no lighter per kWh
than an EV pack.

**What is built.** Jasper's liquid-cooled LFP design, 1,600 kW / 3,008 kWh, 8
racks × 8 modules × 47 kWh, 306 Ah cells — liquid cooling being what current
containers ship with. The cell is Voß's, which Jasper link and do not
reproduce; Voß is on ecoinvent 3.9.1, so it rebuilds here without a version
mismatch.

| Part | kg CO₂e/kWh nameplate | Jasper Fig. 4, LC LFP (3.11, EF 3.1) |
|---|---|---|
| Cells (made in China) | **79.48** | 95.44 |
| Modules without cells | 6.55 | 6.57 |
| Racks | 6.85 | 6.59 |
| Container | 1.22 | 3.50 |
| Liquid cooling | 2.58 | 2.64 |
| Fire suppression | 0.76 | 0.76 |
| Others (BESS controller) | 0.32 | 0.25 |
| **DC block** | **97.75** | 115.75 (140.11 less PCS, transformer, foundation) |

Every non-cell part reproduces Jasper's to within 4 % except the container,
where ecoinvent 3.9.1's 20 ft intermodal container (2.9 t CO₂e) is about a
third of whatever 3.11 carries; this is built as the inventory says, on the
study's database, and the gap is stated rather than patched. The cell gap is
the graphite route (3.11's Acheson dataset against Voß's own Table S5) and the
blend (65:35 against 75:25).

**The cell, validated.** Voß Table 3's LFP/graphite cell — 383.4 Wh,
2,170.8 g, 176.6 Wh/kg — with each material from its ESI table:

| Check | Rebuilt | Voß |
|---|---|---|
| Synthetic graphite, Acheson powder route (Table S5) | 24.51 kg/kg, +0.51 of Voß's transport = 25.02 | 25.1 |
| Natural graphite (Engels 2022) | 4.675 kg/kg, +0.515 transport = 5.19 | 5.19 |
| Cell, German factory, 75:25 | 72.45 kg/kWh | 71.2 |

The German cell lands 1.8 % high *despite* leaving out the transport and
processing materials Voß include, so like for like it is ~6 % high. The
likeliest cause is the factory energy, which Voß do not tabulate: 18 kWh
electricity + 19 kWh gas per kWh is Degen et al. (2023) as restated by Jasper
§2.4.1. It errs high, the conservative direction.

**Choices this study makes, not the sources.**
- *Cells made in China* — where most stationary LFP cells are made, and what
  Jasper assume. +7.0 kg/kWh over Voß's German factory. The German cell is
  built too (`bess_lfp_cell_1kwh_de`) so Voß's figure stays reproducible.
- *Graphite 75:25 synthetic:natural* — Voß's benchmark, given as current market
  share. All-synthetic would be +5.0 kg/kWh, all-natural −15.0 (Voß's own
  figures move by +4.9 and −14.7).
- *The 330 g housing is charged wholly on Voß Table S36* — Voß put fixing and
  isolation materials (S37, all PET) inside it without a split; S36 already
  carries PET, and the Al-heavy table errs high.
- *Ellingsen's busbars*, which Jasper do not reproduce, are mapped to their
  metals, the bimetallic set 50:50 copper:aluminium (~1.8 kg/kWh in all).
- *The BESS controller* (30 kg), which has no inventory in the SI, is
  ecoinvent's electronics for control units, as Jasper's HV control box is.

**Pinned footprints, not inventories.** Five source figures are carbon
footprints: natural graphite 5.19, PVDF 60.6 (Hu et al.), separator 5.06
(ecoinvent 3.8, which Voß chose over 3.9.1's 39.6 as "unrealistically high";
3.9.1 scores 34.4–39.5 here), and Carrère's crucible (7.346) and packaging
(0.432) per kg of synthetic graphite. Each enters as fossil CO₂ of its own
size: right for GWP100 and *only* for GWP100.

**Boundary — the same as every other inventory here.** No end-of-life
(Jasper's EOL sheet and `treatment of used CSS` are not taken). No delivery
transport: every rail, lorry and sea row in both sources is left out, as
`upv.py` leaves out Smith's, and where Voß folded their China-to-Berlin legs
into one factor (natural graphite) they are subtracted back out with negative
exchanges. Factory energy is *in*, as it is for solar. Jasper's PCS (charged on
the power term), transformer (battery step-up closed as negligible, 4 Sep) and
concrete foundation (civils are outside every capital inventory) are excluded.
Voß's processing materials — NMP, argon, nitrogen, compressed air — are not
tabulated by them and are left out; this errs low.

**What is still not in it.** Current 20 ft products pack ~5 MWh against
Jasper's 3 MWh; spreading the per-container items over 5 MWh would take ~3
kg/kWh off. End-of-life, as everywhere. And the cell is the soft spot: Jasper's
3.11 cell is 20 % above this one on the same bill.

**Why Modo rather than NREL.** The FES 2025 Economics Methodology report
states NESO's Li-ion CAPEX is *"a combination of Modo survey data with CAPEX
data from the National Renewable Energy Laboratory"*. Modo's assumptions are
published openly and already in real 2025 GBP, so they need neither FX nor
deflation — unlike NREL, which is USD and US-market.

**Verification built in.** `check_against_ecoinvent()` re-scores the battery
foreground and both ecoinvent factors, and fails if any has moved by more than
0.1 %.

**Life.** The battery's 15-year life against the data centre's 25 means **1.67
builds** over the study horizon, which both cost and carbon must carry.

---

## Renewable generation — embodied carbon per MW
`renewables.py`

ecoinvent supplies renewables as **per-kWh** activities with capital already
amortised over a lifetime output ecoinvent chose. This module strips that back
out to **kg CO₂e per MW installed**, so the burden of building capacity does
not depend on how much it happens to generate.

| Technology | Capital | ecoinvent implied LF | Restated at DESNZ LF | Grade |
|---|---|---|---|---|
| Onshore wind | 658 t CO₂e/MW | 26.2 % over 20 y | 5.6 g CO₂e/kWh (was 14.5) | transcribed / derived |
| Offshore wind | 890 t CO₂e/MW | 30.0 % over 20 y | 5.7 g CO₂e/kWh (was 17.1) | transcribed / derived |
| Solar PV | **1,048 t CO₂e/MWp** (IEA PVPS) | — | **25.8 g CO₂e/kWh** | transcribed / derived |
| Solar PV, ecoinvent basis | 2,303 t CO₂e/MWp | 11.0 % over 30 y | 56.7 g CO₂e/kWh (was 79.8) | transcribed / derived |

Wind capital scores are **transcribed** from ecoinvent 3.9.1 apos (`market for
wind turbine, 2MW, onshore` + its network connection). The restatement is
**derived**, using DESNZ/Arup load factors and lifetimes from `tech_costs.py`.

**Verification built in.** `check_reconstruction()` re-amortises the per-MW
figure back over ecoinvent's own implied lifetime output and fails unless it
reproduces ecoinvent's published per-kWh score exactly. All three pass — it is
anchored on `ecoinvent_capital_kgco2e_per_MW`, which every row keeps whatever
basis is in force, so substituting solar's basis does not retire the check.

### Solar is not scored on ecoinvent — `renewables.SOLAR_EMBODIED_BASES`

ecoinvent 3.9.1's GB open-ground PV activity is the 570 kWp **Solarpark El
Tesoro**, Alcolea del Río, Andalusia, **installed 2008** — the dataset's own
comment says so; the "2012" this register carried previously was the citation's
URL access date. It holds 4,401.7 m² of panel for 570 kWp, i.e. 129.5 W/m² or a
**12.95 % module**, against 21–23 % for a module built today. 95.5 % of its
burden is in the two exchanges that scale with panel area (panel 72.0 %,
mounting 23.5 %), so the vintage is essentially the whole number.

Neither obvious fix works. The plant inventory is **byte-identical in ecoinvent
3.10.1** — verified exchange by exchange against the copy in the `hypt`
Brightway project — so upgrading moves only the background. And GB has just
three PV activities in either version, of which the other two are 3 kWp
slanted-roof systems of the same vintage.

So solar's default basis is **IEA PVPS Task 12**, the standard reference for PV
LCA, on the same IPCC 2021 GWP100 method used throughout this study.

| Basis | Source | g CO₂e/kWh at this study's yield | t CO₂e/MWp | Grade |
|---|---|---|---|---|
| `smith_2024_upv_fixed_tilt` *(default)* | Smith et al. 2024 (NREL/TP-7A40-87372) utility-scale inventory, fixed tilt, **rescored on ecoinvent 3.9.1 apos** | **22.0** | **895** | derived |
| `iea_pvps_2023_mono_si` | IEA PVPS T12 2023 update, mono-Si, 20.9 % module — a **3 kWp ROOFTOP** system | 25.8 | 1,048 | transcribed |
| `ecoinvent` | ecoinvent 3.9.1 apos, as above | 56.7 | 2,303 | transcribed |

Three bases. `ecoinvent` exists only to reproduce runs from before the rooftop
default arrived; `iea_pvps_2023_mono_si` only to reproduce runs from before the
utility-scale rebuild.

### Why the default is now a rebuild rather than a citation

`cap_solar` is a utility-scale MWp. The basis it replaces is quoted, in IEA
PVPS's own words, against *"1 kWh AC … produced with a 3 kWp PV system, rooftop
mounted"* — so a solar farm was priced with roof rails, a domestic string
inverter, and **no** perimeter fence, **no** plant-scale site cabling and **no**
land. It was also the one coefficient in the study not on ecoinvent 3.9.1 apos:
IEA PVPS use UVEK in SimaPro under **recycled-content** allocation, a different
system model, which `SOURCES.md` had not previously recorded.

Smith publishes on ecoinvent **cut-off**, so his results cannot simply be
relabelled — APOS and cut-off differ precisely where recycled content matters,
which for a PV plant is the aluminium, steel and copper. His **inventory** is
therefore taken and rescored in this project, which makes the answer apos by
construction, exactly as the wind transformer and the data centre are. His
process names are ecoinvent-native, so 93 % resolve with no decision at all.

**Verification.** 290 of 290 scientific-notation values in Appendix A appear in
the transcription; 251 rows were association-checked against the PDF text and
249 are clean, the two flagged being zero-GWP flows. Of 79 biosphere rows,
exactly **four** carry a non-zero GWP100 factor — the silicon-smelting CO₂ and
the two fluorinated cell gases, CF₄ at 7,380 and C₂F₆ at 12,400 — and all four
are included. The module lands at **684 kg CO₂e/kWdc**, and Smith states his
average-import module sits *above* the 630 kg CO₂e/kW EPEAT low-carbon
threshold: his own published result, reproduced from his inventory, on a
different system model.

| per MWp | t CO₂e |
|---|---|
| module (A1–A8) | 683.8 |
| fixed-tilt mounting (IEA PVPS T12-33:2026) | 148.6 |
| electrical balance of system | 30.8 |
| inverters | 11.7 |
| fence | 1.3 |
| installation energy | 1.3 |
| O&M, 30 y prorated to 38 y | 17.8 |
| **total** | **895.3** |

**Four substitutions, each stated.** Smith's system is single-axis **tracked**;
GB utility-scale is fixed tilt, so Table A9 is replaced by IEA PVPS T12-33:2026
`Z-PV-239`, a pile-driven steel table at 20°. That makes the mounting *heavier*,
not lighter — 9.730 against 9.618 kg/m² of structure — because a fixed table
needs more clamps and fasteners per m² than a torque tube; the module frame is
untouched, being 1.51 kg/m² of AlMg3 inside the module. The **transformer** is
excluded because `transformers.py` already charges the step-up, and Smith's A11
is unusable regardless at 19,796 kg/MVA, ~9× the measured specific mass at that
rating. The **inverter count** comes from Smith's stated DC/AC of 1.34, not from
his Table A14 count, which implies 1.75 — the two are inconsistent in the
source. **O&M** keeps his replacement *fraction* (30 % of the installed count
over 30 years, Mason's 10 %/decade) rather than his absolute count, since our
inverter count differs.

**Excluded, with direction.** End-of-life, as everywhere in this study.
Construction transport — the sea leg alone is 201 t·km/m² for this import
chain, so the figure **understates by roughly 1.5 %**. Supply chain is the SE
Asia import case: China's national grid for the silicon chain, Thailand for cell
fabrication and module assembly.

**The O&M prorating cancels in the objective.** Since `restate()` gives
`annual = capital_total / life` and `capital_total = capital + om30 × life/30`,
the annual charge is `capital/life + om30/30`. The O&M term is life-independent
once annualised, so the 30 → 38 year scaling moves only the reported per-kWh
columns, never the LP.

Issues knowingly parked are listed in `data/UPV-DEFERRED-ISSUES.md`; the frozen
bill is `data/upv_smith_bill.json`, and the parsing heuristics that produced it
ran once and are not shipped. IEA PVPS's multi-Si figure is **not** offered as a basis — see
below for why it is evidence rather than a scenario.

Source: Stucki M., Götz M., de Wild-Scholten M. & Frischknecht R. (2024),
*Environmental Life Cycle Assessment of Electricity from PV systems — 2023 data
update*, IEA PVPS Task 12, May 2024. Reference system: 1 kWh AC from a 3 kWp
rooftop array, in-plane irradiation 1,331 kWh/m², **annual yield 976 kWh/kWp**
including 0.7 %/a degradation, 30 y panel / 15 y inverter.

**Why the transfer is clean.** A published per-kWh figure carries its author's
yield and lifetime, so it is turned back into t CO₂e/MWp before `restate()` puts
it on this study's own yield — the **derived** half. That works here because IEA
PVPS's 976 kWh/kWp sits within 10 % of the DESNZ GB solar load factor (12.2 % =
1,069 kWh/kWp), so no irradiance correction is needed. Most PV harmonisations
normalise to 1,700 kWh/m²/yr and would need a large one.

**Why mono-Si, and why multi-Si is evidence rather than an option.** `cap_solar`
is a decision variable for a plant that does not exist yet, so the question is
what would actually be built. IEA PVPS record multi-Si market share below 3 % in
2022 and ~1 % in 2023 — they could not even update its parameters for want of
current data. Offering it as a basis would let the study be run on a technology
nobody deploys, failing the test on exactly the ground ecoinvent fails it, so it
is deliberately absent from `SOLAR_EMBODIED_BASES`.

Its **number** is kept here, because it is what shows this correction is not
merely an efficiency story. Hold the technology fixed at multi-Si and update
only the manufacturing — thinner wafers, lower kerf loss, less electricity and
heat per m² — and IEA PVPS's 2023 figure is **43.6 g CO₂e/kWh = 1,277 t
CO₂e/MWp**, still 0.55× ecoinvent's 2,303. Most of the gap is manufacturing
vintage, not module efficiency. That is the answer to a reviewer who suspects
the technology was switched in order to flatter the result: switching
technology accounts for 1,277 → 1,048, and the vintage for 2,303 → 1,277.

**Corroboration.** IEA PVPS track the same Swiss mono-Si rooftop system across
editions: 121 (1996) → 76 (2007, 14.0 % module) → 43 (2020) → 36 g CO₂e/kWh
(2023, 20.9 %). ecoinvent's 2008 / 12.95 % plant restating to 57 g/kWh sits
exactly where its vintage predicts once ground-mount and this study's longer
life are allowed for — so the ecoinvent figure is *correct for its vintage*,
which is both its defence and the case against using it. Independently,
NREL/TP-7A40-87372 (Smith et al., March 2024) puts US utility-scale PV at 10–36
g CO₂e/kWh across six supply-chain and end-of-life cases, built on ecoinvent 3.9
with 20.3 % PERC modules.

**Caveats, stated.** IEA PVPS's reference is a **3 kWp rooftop** array, so
ground-mount swaps roof rails for heavier steel; NREL's utility-scale range
brackets the figure, so the error is real but small and points upward. And this
is the one coefficient in the study not scored on ecoinvent 3.9.1 apos — IEA
PVPS use the UVEK LCI database in SimaPro. Both are IPCC 2021 GWP100, but the
backgrounds differ.

**No UK source exists for this.** POSTnote 383 *Carbon Footprint of Electricity
Generation* is from June 2011; the DESNZ GHG Conversion Factors cover
operational emissions only, with no capital goods for generation assets; the
DESNZ/Arup cost reports carry no inventories; and the UK Solar Roadmap (June
2025) is deployment and planning policy. This is the same pattern as the
hydrogen chain — the UK publishes costs and tariffs, not inventories.

**Why it matters.** ecoinvent's GB onshore wind assumes 45,918 kWh/kW over
its life; DESNZ/Arup give 116,815 kWh/kW — **2.5× more**. Charging embodied
carbon per kWh at ecoinvent's rate overstates it by that factor. Notebooks 4.1
and 4.3 charge wind per kWh generated and so carry ecoinvent's assumption:
fine for a fixed plant, wrong once capacity is a decision variable.

**Wind is unaffected by the PV vintage problem** above: ecoinvent's turbine is
mostly steel and concrete and ages far more slowly than a PV module. Its
datasets stay the basis for both onshore and offshore.

---

## Generation step-up transformers — embodied carbon per MW connected
`transformers.py`, inventory built by `optimiser_lca/stepup_transformers.py`

A wind turbine generates at **690 V**, which is *low* voltage — below the 1 kV
boundary ecoinvent itself draws. The data centre draws at *medium* voltage,
1–24 kV, because that is what `market for electricity, medium voltage` describes
and what the Zhang foreground is authored against. Something must bridge them,
and it is **not optional**:

| | at 690 V | at 20 kV |
|---|---|---|
| one 2 MW turbine | 1,673 A | 58 A |
| a 100 MW farm | **83,674 A** | 2,887 A |

So every turbine carries its own transformer at the foot of its tower — **one
per turbine, not one per farm**, and a 100 MW farm has fifty.

**No inventory in this study contains them.** Checked exchange by exchange:
`wind turbine construction, 2MW, onshore` lists its own parts in its comment
("Rotor, Nacelle, Electronics, Tower, Foundation") with no transformer among
them; its only electrical item is **438.7 kg** of `electronics, for control
units`, against the 3–5 t a 2 MW turbine transformer weighs; its stated
component masses (rotor 37 t, nacelle 61 t, tower 165 t) account for the
materials without leaving room for one; and it says outright that it excludes
the grid connection, which is a separate dataset of cable and trench (253.8 kg
copper, 1,375.7 kg HDPE, 1,398.7 m³ excavation).

**And ecoinvent cannot supply the asset.** It has **four** transformer
activities, which are two products with a market and a production each, and both
are electronics — by ecoinvent's own comments, *"a typical high voltage use
transformer **in electronic modules** has an average weight of **280 g** … used
in the information and communication technology"*, and **30 g** for the
low-voltage one. Their compositions match: 0.50 kg ferrite, 0.31 kg epoxy and
0.51 kg injection moulding per kg, against **5 g of steel**. There is no
`substation` activity, no `switchgear` activity, and no power transformer at any
rating. Until this rewrite wind scaled that 280 g component up by a factor of
**205,000**; rebuilding a real transformer's bill of materials gives 177.3 t
CO₂e against 306.2 t on that dataset, with the manufacturer declaring 147.4 t,
so the old basis ran about **2×** high. Nobody who has looked at this used
ecoinvent's transformer — Leng built theirs from materials, Teffera built theirs
from materials, and Vestas scaled a real ABB EPD.

So the transformer is assembled from a published bill of materials, exactly as
the hydrogen tank is, and for the same reason.

### The inventory

> H. Leng, X. Zhou, J. Chen, D. Chen, M. Li, Y. Lin, Z. Yue, N. Zhong, "Life
> Cycle Assessment of an Onshore Wind Farm: Carbon Emission Evaluation and
> Mitigation Pathway Design", *Processes* **14**(7), 1045 (2026), Supplementary
> Table S1. PowerChina Huadong Engineering. ISO 14040/14044.

Their Gaoyou farm in Jiangsu is **fifty 2 MW turbines, 100 MW**, each with its
own `S11-2200/35` box transformer. Table S1 gives the materials for all fifty as
one bill, transcribed into `dc_config.TX_LENG_BOX_KG`:

| material | all fifty | per MW | ecoinvent process | grade |
|---|---|---|---|---|
| Steel | 163,500 kg | 1,635 kg | `steel, low-alloyed` + `sheet rolling, steel` | transcribed |
| Iron *(core)* | 53,300 kg | 533 kg | same as steel | **assumed** |
| Copper | 46,800 kg | 468 kg | `copper, cathode` + `wire drawing, copper` | transcribed |
| Transformer oil | 17,600 kg | 176 kg | `lubricating oil` | transcribed |
| Silicon dioxide | 1,143 kg | 11.4 kg | `silica sand` | **assumed** proxy |
| **total** | **282,343 kg** | **2,823 kg** | | |

Scored on ecoinvent 3.9.1 apos at IPCC 2021 GWP100 and amortised over this
study's own 35-year life:

| capacity variable | kg CO₂e per unit per year | basis |
|---|---|---|
| `cap_wind`, `cap_offshore` (MW) | **278.7** | Leng turbine step-ups |
| `cap_solar` (MWp) | **296.0** | IEA PVPS T12-33:2026 inverter-station step-ups |

278.7 is **1.45 %** of onshore wind's 19,244 kg CO₂e/MW/year.

*"Iron" is the one judgement.* Leng lists Steel and Iron separately and does not
say what the second is. Read here as core steel, since a transformer contains no
cast iron and Teffera's equivalent inventory is steel and copper only. Scoring
it as cast iron instead moves the answer **4 %**.

### Why it is per MW, and why that scales exactly

Sizing needs no power factor. Leng states the transformer content of a 100 MW
farm directly and `cap_wind` is in MW of exactly that kind, so the ratio is read
off rather than derived. One unit per turbine means **30 MW and 1,000 MW carry
the same figure per MW**.

The plant-rated basis this replaces did *not* scale. Specific mass falls with
rating — **2,566 kg/MVA at 2.2 MVA, 1,434 at 40, 715 at 100**, all measured from
the sources above — so one flat number taken from a single farm size was out by
up to **14 %** across a tenfold range of build.

### Independently checked

Teffera et al. (2021), *Int J LCA* 26:76–96, Table 5 — three Ethiopian farms
totalling 324 MW, reported per kWh rather than in tonnes. Converted onto this
study's basis their turbine-level transformers are **228–333 kg CO₂e/MW/year**,
the range being which of their two capacity factors the inventory is built on
(they publish design factors of 0.34–0.36 and realised ones of 0.17–0.32, and do
not say which). Leng's 278.7 sits inside that band. Two teams, two countries, two
reporting formats, one answer. Teffera also resolves the "Iron" question above,
and adds aluminium and porcelain bushings that Leng omits — so Leng errs low.

Their transformer sizing corroborates a third time: Leng's grid-end unit is
`XZ11-**100000**/110`, i.e. 100 MVA for 100 MW; Teffera's farms are 2 × 63 MVA
for 120.2 MW (1.048) and 55 MVA for 51 MW (1.078). Vestas' 60 MVA for a 100.8 MW
plant (0.595) is the outlier.

### What is deliberately not counted

**No grid-export transformer charged to generation.** Leng's farm also has that
100 MVA unit stepping up to 110 kV, and it is not charged to `cap_wind`. This
study's generation is **behind the meter**: there is nothing to export into, and
the one transformation between the site and the outside world is the grid
intake, which `cap_grid` pays for through `grid_connection.py`. Charging it to
generation would bill the site for a voltage change it does not make. The same
unit's bill **is** taken — as the basis of the grid *intake* (below), not of
generation.

**No step between the collection network and the data centre.** Both sit in the
medium-voltage band, so the chain closes. `dc_config.TX_SITE_COLLECTION_KV`
= **20 kV** states this as a number rather than as the phrase "the same bus", and
`transformers.check()` refuses a value outside the band. Leng's units are wound
for 35 kV, above it; a 20 kV unit of the same rating carries less insulation and
is lighter, so taking their mass **errs high** — the safe direction, and it
covers any residual step.

**No switchgear, protection or civils.** Absent here and absent from the grid
intake in `grid_connection.py`, so it is a level shift rather than a bias. Teffera puts MV
plus HV switchgear at 0.61 t/MW against a plant transformer's 1.08 t/MW — real
but small, and the insulating-gas term is already carried for imported power,
since ecoinvent's medium-voltage market allocates high-voltage switchgear SF₆ to
medium-voltage demand. Registered in DATA_GAPS.md.

**No manufacturing energy.** Leng's own published figures (342 t CO₂e for the
grid-end unit, 1,793 t for the fifty box transformers) are higher than this
rebuild because they add factory electricity on the Chinese grid. Materials only
is consistent with every other foreground here, and it makes this the lower of
the two available numbers.

**Charged on capacity, never on output**, and **carbon only** — DESNZ/Arup capex
is plant-plus-connection-to-the-point-of-connection, so a £/MW charge would
double count. See ASSUMPTIONS §4.

**Losses are not charged here**, and that is not the omission it looks like. Two
manufacturer EPDs put a transformer's life-cycle GWP at ~99 % use phase, but in
this study the lost kWh is generated by plant the LP has already sized. Its right
home is an efficiency on the availability constraints, which is not implemented
and remains the largest open item in this chain.

### Solar's inverter-station step-ups — IEA PVPS Task 12 (2026)

`solar_pv` used to keep an *invented* plant-rated unit on the electronics
dataset, with **no per-inverter-station transformers at all**. That is now
closed, from a source that did not exist when the wind side was written:

> Götz, M., Deuber, R., Gazbour, N., Brailovsky, P.H., Nold, S.,
> Marchand-Lasserre, M., Frischknecht, R., Khan, A.A., Bovo, G. & Stucki, M.
> (2026), *Life Cycle Inventories of Photovoltaic Systems*, IEA PVPS Task 12,
> Report **T12-33:2026**, July 2026. DOI 10.69766/WJTE1771. **Table 49**
> (the unit) and **Table 50** (four per 10 MWp plant).

The workbook is shipped at
`optimisation/data/IEA-PVPS-T12-33-2026-LCI-PV-SupplyChains.xlsx`.

| material, per 2.5 MVA unit | kg | note |
|---|---|---|
| steel, converter, unalloyed | 2,079.8 | GOES core base metal |
| MG-silicon | 73.2 | the core's alloying input |
| lubricating oil | 1,060.0 | |
| aluminium, wrought | 618.0 | windings — **aluminium**, not copper |
| steel, low-alloyed | 1,734.5 | tank, frame, fittings |
| kraft paper | 34.1 | ASSUMED proxy: ecoinvent has no *unbleached* kraft |
| epoxy, copper, chromium steel, rubber, paint | 33.4 | |
| hardboard pressboard | 46.9 | **unit correction, below** |
| **total** | **5,680** | = the report's own stated figure |

**Two things make this better than the wind side, not merely equal to it.**

*The voltage is exact.* The unit is wound **20 / 0.4 kV** — that is
`TX_SITE_COLLECTION_KV` and the inverter's LV terminals, the same two numbers.
Leng's wind units are wound for 35 kV, so their mass has to be taken as erring
high (above); here no adjustment is applied at all.

*The count is read off, not derived.* Table 50 is titled *"10 MW utility-scale
electrical BoS including 4 units 2.5 MW transformers"* → 0.4 units/MWp. This
retires both ASSUMED constants the old solar path needed, `SOLAR_DC_AC_RATIO`
and `POWER_FACTOR`.

It also resolves the *"Iron"* judgement that is wind's one soft spot. The core
is grain-oriented electrical steel; no LCI database carries a GOES dataset, so
the report disaggregates it into converter-route steel + MG-silicon + hot and
cold rolling + annealing, and states why converter rather than EAF steel (GOES
composition limits cannot be met from scrap).

**A unit error in the source workbook, corrected.** The hardboard cell reads
**36.96 m³**. At ~1,270 kg/m³ that is ~47 **tonnes** — eight times the whole
transformer, and it would have dominated the score. The report's own stated
total proves the intent: 5,633.04 kg of transcribed materials + 0.03696 m³
(46.9 kg) = 5,679.9 kg against a stated ~5,680 kg. The cell is dm³ mislabelled
as m³. `dc_config.upv_tx_check()` and `transformers.check()` both guard
the reconciliation, so restoring the literal value fails loudly rather than
silently inside the LCA.

**Two sources, two technologies, one answer.** Solar's **296.0** against wind's
**278.7** kg CO₂e per unit of capacity per year, for step-ups of comparable
rating (2.5 and 2.2 MVA) transcribed by different teams from different
countries. The one asymmetry is deliberate and stated: **solar carries factory
electricity and heat and wind does not**, because Leng publish theirs and this
study excludes it. Process energy is ~6 % of the solar unit, so materials-only
the two land within ~1 % of each other — which is what makes the agreement a
corroboration rather than a coincidence. It also means **wind now errs low
relative to solar**, and that is the direction to fix next.

The legacy basis gave 184.2, i.e. **1.61× off**. It carried two errors that
partly cancelled: the electronics dataset runs high for a given mass, while a
40 MVA specific mass under-counts a 2.5 MVA unit by ~1.6×. It survives only as
`transformers.SOLAR_BASIS = "legacy"`, to reproduce pre-2026 runs.

### The grid intake — Leng's main transformer

`grid_connection.py`, inventory `transformer foreground/grid_intake_transformer_per_mva`
built by `optimiser_lca/stepup_transformers.py`

`cap_grid` used to be the last thing on the default path still scoring
ecoinvent's 280 g electronics transformer: **333.5 kg CO₂e/MW/year**, from
5.34 kg CO₂e/kg at an uncited 1.25 t/MVA (300 t / 240 MVA, DERIVED from a GB
400 kV supergrid transformer) × 2 for N-1 over 40 years. It now reads the same
Table S1's grid-end unit, transcribed into `stepup_transformers.TX_LENG_MAIN_KG`
and mapped exactly as the box transformers are (same `TX_MATERIAL_PROCESSES`,
same "Iron" reading):

| material, `XZ11-100000/110` | kg | per MVA | grade |
|---|---|---|---|
| Steel | 30,200 | 302.0 | transcribed |
| Iron *(core)* | 20,800 | 208.0 | transcribed; read as core steel, **assumed** |
| Copper | 16,800 | 168.0 | transcribed |
| Transformer oil | 3,430 | 34.3 | transcribed |
| Silicon dioxide | 228.6 | 2.3 | transcribed (printed in kg); silica-sand proxy |
| **total** | **71,458.6** | **714.6** | `check()` holds the sum |

Scored materials-only on ecoinvent 3.9.1 apos: **2,753 kg CO₂e per MVA**
(3.85 kg CO₂e/kg — above the box units' 3.46 because copper is 23.5 % of the
mass rather than 16.6 %, and half the carbon). × 2 MVA/MW (N-1 ÷ power factor
1.0) ÷ 40 years = **137.7 kg CO₂e/MW/year**, −59 % on the old basis. Leng's own
342 t CO₂e for this unit includes factory electricity on the Chinese grid; the
275 t here does not, for consistency with the wind units.

*The voltage judgement.* The unit is wound for **110 kV**, which fits a GB
**132 kV** EHV/DNO connection — the common case for a ~100 MW data centre. For a
site connected at **275/400 kV** it errs **low**, supergrid transformers being
heavier per MVA. It is used for every site as the default and registered in
DATA_GAPS.md. Switchgear, protection, the bay, civils, losses and end-of-life
are excluded, as for the step-ups.

**Sources.** Leng et al. (2026), *Processes* 14(7) 1045 —
<https://doi.org/10.3390/pr14071045>. Teffera et al. (2021), *Int J LCA* 26:76–96
— <https://doi.org/10.1007/s11367-020-01834-5>. Vestas, *LCA of Electricity
Production from an onshore V136-4.2MW Wind Plant* (2018), critically reviewed to
ISO/TS 14071. Götz et al. (2026), *Life Cycle Inventories of Photovoltaic
Systems*, IEA PVPS Task 12 Report T12-33:2026 — DOI 10.69766/WJTE1771, Tables 49
and 50 (solar step-ups). Legacy solar basis:
Hitachi Energy S.p.A., *Environmental Product Declaration*, 40 MVA power
transformers (Monselice), EPDItaly rev. 3, 2022 —
<https://www.epditaly.it/wp-content/uploads/2016/12/EPD_40MVA_Hitachi_rev3-11.03.2022-29.04.2022bis.pdf>.
ABB, *Environmental Product Declaration, Power transformer TrafoStar 500 MVA*,
S-P 00020 —
<https://library.e.abb.com/public/566748ad75116903c1256d630042f1af/ProductdeclarationStarTrafo500.pdf>.
## Hydrogen chain — embodied carbon per unit of capacity
`electrolysers.py`, `fuel_cell.py`, `h2_storage.py`, assembled by `coefficients.py`

The same problem `renewables.py` solves, applied to the hydrogen chain: these
inventories amortise their capital over an output level their authors chose, and
the optimiser sizes capacity. Each module strips the capital back out and
asserts that re-amortising it at the original basis rebuilds the original
number.

### Electrolysers — `electrolysers.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| AE / PEM / SOEC capital | 432.4 / 260.8 / 362.8 t CO₂e per MW | derived | Hermesmann et al. capital good, scored on ecoinvent 3.9.1 apos and divided out of the per-kg activity |
| Rated capacity | **1 MW** each | derived | Only PEM states it. AE and SOEC are inferred from lifetime H₂ × specific energy, which lands on 160 GWh/MW for all three to within 0.2 % despite specific energies of 42.3–54.0 kWh/kg. `check_rating()` enforces it |
| Implied utilisation in the foreground | 160,000 full-load hours, **73 % CF** over 25 y | derived | The trap this module exists to escape: an electrolyser built to run at 20 % CF is under-charged **3.7×** by the per-kg figure |
| Variable burden | 0.042 / 0.107 / 1.632 kg CO₂e per kg H₂ | derived | Water, heat, electrolyte — genuinely per-kg, so left per-kg |
| SOEC external heat | 18.864 MJ (5.24 kWh)/kg H₂ on `heat production, natural gas, at boiler modulating >100kW` [Europe without Switzerland], 0.0751 kg CO₂e/MJ | transcribed | Mehmeti et al. 2018 (*J. Clean. Prod.* 199, Table 1 and §2.2): heating the stack inlet flows to 750 °C at 95 % heat-exchange efficiency gives 4.75 kWh/kg, raised to 5.24 for 0.5 %/1,000 h degradation. They supply it from "Heat, natural gas, at boiler modulating", and this is that dataset's v3 successor. >100kW because a 1 MW SOEC draws ~124 kW of heat. Gerloff 2021 (Table 3) carried the 5.24 kWh but modelled it on "heat, district or industrial, other than natural gas" (52 % coal and peat, his §2.2.3), and Hermesmann copied Gerloff. That swap is why this row used to sit on `market group … other than natural gas` [RER]. The two datasets score 0.0749 and 0.0751 kg/MJ, so the switch fixes the provenance and moves GWP by +0.004 kg/kg. It matters more for the non-GWP categories, where Gerloff blames that coal-heavy proxy for SOEC's particulate, ionising-radiation and carcinogen results. Cross-check: Mehmeti's own heat line is 1.294 kg CO₂e/kg H₂ (0.0686/MJ, supplementary Table A1), against 1.417 here. Heat is still 87 % of SOEC's 1.632 kg/kg. The audit's comparison on renewable power (SOEC 2.27 against PEM 0.89, or 0.22 on zero-burden heat) moves by that same +0.004, so the dataset choice no longer swings the ranking; the heat itself still does. A data centre's waste heat cannot supply it at these temperatures. A boiler cannot literally reach 750 °C either, but it is the source's own basis. Not costed: see `DATA_GAPS.md`, *Electrolyser consumables cost*. Audit §3.3 |
| SOEC heat, electric-boiler scenario | 5.24 kWh ÷ 0.99 = **5.29 kWh/kg H₂** of site electricity, replacing the gas row | assumed | `soec_heat="electric_boiler"` on a `Scenario` (matrix rows 22–25, and a toggle on the optimiser page). `electrolysers.with_heat_source` drops the gas row's 1.417 kg/kg, leaving 0.215 kg/kg of water, and adds the boiler's kWh to `kwh_per_kg`, so the heat costs and emits whatever the LP's electricity does in that hour. Efficiency 99 % from the Danish Energy Agency's *Technology Data*, "Electric boilers", not yet checked against the sheet. `cap_ely` then covers the boiler's draw too, so stack carbon and cost per MW are scaled to the stack's share (≈ 0.90 at a 28 bar tank). **The boiler's own capital is not charged**, in carbon or cost. Resistance heating reaches the ~750 °C inlet, which a gas boiler does not, and it is what commercial SOEC systems use |
| Plant lifetime | 25 y | transcribed | NESO Green Hydrogen Data Portal, same figure as `electrolyser_costs_clean.csv` |

*No stack/BoP split is possible* — Hermesmann's capital good is one monolithic
activity, so the whole of it is charged on calendar life. Registered in
`DATA_GAPS.md`.

### PEM fuel cell — `fuel_cell.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Stack | 97.4 t CO₂e per MW, **30,000 h** duty life | derived | Babatunde et al. 2024 Table S1. Duty life: stationary H₂ stacks are refurbished at 24–30k running hours (Nedstack datasheets, as reported); Bionaz et al. 2022 use 40k. Babatunde's 32k was ecoinvent's own figure, so never an independent check |
| Balance of plant | **44.3 t CO₂e per MW**, **80,000 h** duty life | derived | Rebuilt 14 Oct, below. Duty life: DOE's 100 kW–3 MW stationary class, and ecoinvent's own system life (60,000 h was the 1–25 kW residential target) |
| BoP **calendar** life | **20 y** | **assumed** (indicative) | Nedstack: 20 y for the BoP of their 120 kW CHP unit, 10 y for their mobile unit; DOE backup-power target, 15-y system life. Sweep 15–25. Was 25 y, matched to the electrolyser. Also sets the cost-side annuity: +8.3 % on the fuel-cell cost line |
| Stack **calendar** life | **10 y** | **assumed** (indicative) | Clean Hydrogen Partnership stationary PEMFC KPIs are set on a 10-y system life; Nedstack mobile unit 10 y; Gandiglio et al. 2022 replace their 50 kW Engie-EPS unit every 5 y. Binds for an idle backup stack (membranes age at open circuit). Sweep 5 / 10 / 15. Was a 25-y placeholder |
| Maintenance | **0.003** kg CO₂e per MWh delivered | derived | An air filter and a coolant change per 8,000 h (interval ASSUMED; Battelle 2016 gives one year for backup units), Usai's amounts. Was 3.11, ecoinvent's reformer-catalyst service event |
| Hydrogen consumption | 63.16 kg H₂ per MWh | derived | 1/(η 0.475 × LHV 33.33 kWh/kg) |

Both replaceable components are charged at
`max(1/calendar_years, full_load_hours_per_year/duty_hours)` — a maximum of two
linear functions, exact in an LP. This matters at both ends: charged on duty
alone a **backup** fuel cell at 100 h/yr is under-counted **~31×**; charged on
calendar alone a **baseload** one is under-counted ~2.8×. `check_full_duty()`
asserts the rule collapses onto the foreground's own per-kWh figure at 8,760 h/yr.

#### The balance of plant — a hydrogen-fed stationary unit, not a micro-CHP

Until 14 Oct it was ecoinvent's `fuel cell production, polymer electrolyte
membrane, 2kW electrical, future` net of its stack: a **natural-gas domestic
micro-CHP** ("operation with connection to low pressure gas network"), with
fuel-processor items, a hot-water kit and 400 km of installer driving, scaled
linearly from 2 kW to MW — 469 t CO₂e/MW, and reformer-catalyst replacement as
its maintenance. Audit §3.4.

**No MW-class hydrogen PEM inventory exists.** Checked: Stropnik et al. 2018
(*Energy* 165:824, 3 kW H₂ UPS — the only stationary H₂ unit with a component
bill), Gandiglio et al. 2022 (a 50 kW unit, but inventoried as ecoinvent's 2 kW
stack alone), Gramc, Stropnik et al. 2025 (*IJHE* 104:623, a 48 kW stack only),
Belmonte 2016/2017 (3 kW, on ecoinvent's 2 kW dataset), Gentilucci et al. 2024
(SAE 2024-24-0020, 200 kW truck, BoP from Miotti 2017), Syré et al. 2024 (*WEVJ*
15:114, trucks and buses, Usai's data). A 2026 review (*Energies* 19:3808) finds
fuel-cell BoP inventories still "simplified using obsolete" bills. So the BoP is
assembled, per kW, in `optimiser_lca/fuel_cell.py`:

| Part | kg CO₂e/kW | Source |
|---|---|---|
| Process loops — air, water, heat, fuel, controller, wiring, frame | 8.81 | **Usai et al. 2021**, *J Cleaner Prod* 280:125086, SI Table 1 (`sources/usai supplementary materials/`): an 80 kW H₂ system per kW net, every line on the ecoinvent process Usai name |
| Power conversion to AC | 31.86 | ecoinvent `market for inverter, 500kW` [GLO], the battery's power-term dataset. A vehicle's DC/DC boost sits in its drivetrain, so nothing is counted twice |
| Enclosure | 3.66 | the battery's fire-lined 20 ft container (Jasper 2026, `bess.py`), one per MW — **assumed**, no source gives MW per container for fuel cells; sweep 0.5–2 MW |
| **Balance of plant** | **44.3** | |
| Stack (Babatunde) | 97.4 | unchanged |
| **System** | **141.8** | |

*Two lines of Usai's Table 1 are per system, not per kW.* The 3 coolant pumps
and 16 m of wiring (Miotti's per-system figure) are printed as per kW net;
taken literally they rebuild Usai's own heat and "other" results 17× and 35×
over. Divided by 80 kW they rebuild them. *The rest is as printed*, and rounded
to two decimals, so the loops land at **0.82×** Usai's own 854 kg CO₂e per 80 kW
(their results workbook, ecoinvent 3.6): water 0.99, fuel 0.91, air 1.11, the
radiator and controller lost to rounding. Where Usai's 3.6 GLO market is
regional in 3.9.1 (sulfur trioxide, rigid PU, nylon 6), RoW stands in.

*What is a vehicle part and stays.* The compression-expansion motor stands in
for a stationary air blower (errs high, small); the belly pan for the module
frame.

**Benchmarks**, whole systems cradle-to-gate per kW: Miotti 29, Usai 37.3 (no
tank), Gentilucci 30.5–51.4 (200 kW truck), Ballard 73 (70 kW module, its own
note), Stropnik/Bionaz 405 (3 kW UPS). This system's 142 sits above the vehicle
band because it carries an inverter and an enclosure and because Babatunde's
2 kW graphite-plate stack (97 kg/kW) is ~3–4× an automotive stack. **The stack
is now the soft spot**: Gramc 2025's 48 kW stack inventory is the obvious
sensitivity, rebuilt on this study's boundary.

**Effect**, t CO₂e per MW per year: backup (200 h/yr) 23.3 → **12.0**; baseload
(8,760 h/yr) 122.4 → **33.3**. At backup duty the stack's 10-y calendar life now
carries 81 % of it.

Hydrogen is excluded from every coefficient — the LP supplies it explicitly.

### Hydrogen storage — `h2_storage.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Gandiglio 28 bar vessel | 312.8 kg steel per kg H₂ → **1,595 kg CO₂e per kg** capacity | transcribed | Gandiglio et al. 2022, Table 3 — the as-built 21.6 m³ stainless vessel at Ginostra |
| Type I 200 bar cylinder | 100 kg steel per kg H₂ → **250 kg CO₂e per kg** capacity | assumed | ~1 wt% gravimetric capacity, a typical industrial stationary bottle. No Brightway activity exists for it |
| Vessel lifetime | 25 y, never replaced within it | transcribed | The paper's own plant life |
| Standing loss | **0 /h** | **assumed** | No boil-off exists for compressed gas at ambient temperature — that is a liquid-H₂ phenomenon. Real losses are fitting leakage, a maintenance question. Thought load-bearing; **swept 14 Oct and found not to be** at 0–0.1 %/day: < 0.1 % on cost and carbon, no change in which store dominates (`DATA_GAPS.md`). **The sweep range is ASSUMED**, because no source here gives an order for fitting leakage on a welded steel vessel at 28 bar: 0.1 %/day (≈ 3.6 % a year of the stock held) is set equal to the bottom of the battery's 0.1–0.5 %/day band, so at the top of both bands the two stores leak alike per day — the most hydrogen-adverse comparison still plausible for a gas with no boil-off; 0.01 %/day, an order lower, stands for a well-maintained vessel; zero is the default. Replace it from a fugitive-emissions source (candidate: Frazer-Nash for BEIS, 2022). The leaked H₂'s own GWP (~11) is not charged by the LP |

**The design choice is not a detail.** Per kWh *deliverable back through the fuel
cell*, the 28 bar vessel is 100.7 kg CO₂e/kWh against a Li-ion battery's 108.6
per usable kWh — barely any advantage. The 200 bar cylinder is 15.8, about
seven times better. Which
vessel the study uses decides whether hydrogen storage has an embodied-carbon
case. Both are built; run both.

---

## Demand-side network charges
`network_charges.py`

What the data centre pays to *import*, which until now the study omitted
entirely — imports were priced at the Elexon wholesale price alone, roughly half
of a real industrial bill. The omission was not neutral: it made every
grid-connected architecture look cheaper against exactly the on-site generation
that avoids the charges. The DESNZ/Arup connection figures in `tech_costs.py`
are **generator**-side and are not a substitute.

| Input | Value | Grade | Source |
|---|---|---|---|
| TNUoS HH demand tariff | zonal, **£0.00/kW (Scotland, floored) to £10.12/kW (South Western)**; London £7.41 | transcribed | NESO Data Portal, *TNUoS Tariffs*, CKAN datastore resource `6abe8416-149c-4c78-b65b-059eea19957a`, FY2026 Final. Fetched through the same API `h2_prices.py` uses, so it refreshes rather than going stale |
| TNUoS demand residual (TDR) | banded £/site/day; EHV2 = £270,752/yr | transcribed | Same portal, resource `dcca94fd-343e-4d4e-8c5d-66009dec4ad3` |
| BSUoS | £/MWh imported, half-yearly fixed; 2025 runs £12.17 → £10.74 → £15.69 | transcribed | Same portal, resource `4dfa533f-bec6-491b-a3f1-7ce92449bc9a` |
| DUoS unit and capacity | HV Site Specific: red 3.440, amber 0.262, green 0.008 p/kWh; capacity 9.19 p/kVA/day | transcribed | London Power Networks plc, *Use of System Charging Statement* LC14 v1.3, effective 1 April 2026, **Annex 1**. No open API exists for DNO charging statements |
| DUoS time bands | red = Mon–Fri 16:00–19:00, Nov–Feb | transcribed (red), **simplified** (amber) | The statement defines amber per-season; merged to one all-year window. Red is exact, and is an order of magnitude above amber |

**The shape matters more than the level.** Two of the four charges scale with the
*connection* rather than the energy, so a battery or hydrogen store that flattens
the import profile shrinks the connection and its charges while importing the
same annual energy. Modelling network charges as a flat £/MWh would erase
precisely the effect the study exists to measure.

For the 7.31 MW baseline in London: **£23.26/MWh on top of £79.83 wholesale**, a
delivered £103.09/MWh and **1.29x** the figure the study had been using. 38 % of
the addition is capacity- or connection-based.

**Location is the headline.** A 100 MW data centre pays about **£1.0 m/year** in
locational TNUoS at a South Western site and **nothing** in Scotland, whose
tariffs are floored — unfloored they are −£33.84 and −£23.62/kW. That signal
points the same way as the renewable resource, and it was entirely absent.

---

## Hydrogen-chain asset costs — the weakest numbers in the study
`h2_capex.py`

Three inputs the cost objective needs that **no UK source provides**. Every
figure is graded `assumed` and given as low/central/high spanning the full
published range rather than a point estimate with a nominal spread.

| Input | Value (real 2025 GBP) | Grade | Source and why it is weak |
|---|---|---|---|
| Fuel cell capex | £780 / £1,795 / £3,512 per kW | assumed | DOE, *Technical Targets for 100 kW–3 MW Stationary CHP/DG Fuel Cell Systems Operating on Natural Gas*. These are **natural-gas** systems including a reformer this study does not have, so biased high; the low case is an aspirational 2020 target at 100 MW/yr volume, not a price |
| H2 vessel capex | £427 / £658 / £889 per kg capacity | assumed | Range across the compressed-storage literature (EUR 500–1,040/kg; DOE 2005 status $1,100/kg at 430 bar). None is UK, none is recent, spread over 2x. **Gandiglio et al. 2022 supplies the inventory and should be checked for a cost too** |
| SOEC capex | PEM × 1.2 / 1.5 / 2.0 | assumed | **No source at all.** A guess about a technology gap, not a measurement |

For a 7.31 MW backup chain the fuel cell dominates below 22 t of storage and the
tank above it — so across the whole plausible range, hydrogen's cost is set by two
numbers with no UK source and spreads of 4.5x and 2x. **The carbon side of these
same architectures is fully sourced. Rank hydrogen options on carbon with
confidence, and on cost only with the caveat attached.**

---

## Site resolution
`sites.py`

| Input | Value | Grade | Source |
|---|---|---|---|
| Coordinate → outcode | reverse geocode, 2 km radius with an outcode fallback | transcribed | postcodes.io (Open Government Licence) |
| Outcode → Carbon Intensity region | region id and name | transcribed | NESO Carbon Intensity API, `/regional/postcode/{outcode}` |
| CI region → TNUoS demand zone | fixed 14→14 table | derived | Both schemes partition GB by **GSP group**, so the correspondence is structural. No open API publishes it. `check_zone_mapping()` asserts it is a bijection and that it agrees with three presets set independently from published sources |
| Offshore availability | by resolved region | assumed | Judged by region rather than distance to coastline, which would need a coastline dataset |
| Connection capacity | **not supplied**, defaults to unconstrained | — | No public register. See `DATA_GAPS.md` |

Near a region boundary the nearest-postcode hop can land on the wrong side. The
resolved region and zone are always reported rather than hidden, so a boundary
case is visible.

---

## Transformer conversion losses — `conversion_losses.py`

Added 14 Oct 2026. The capital of each transformer is charged above; this is
the energy it loses, which enters the LP's node balance rather than a carbon
coefficient — the lost kWh is generated or imported by plant already charged.

| Unit | Rated | Pk (load) | Po (no-load) | Source | Grade |
|---|---|---|---|---|---|
| Wind turbine step-up (Leng) | 2.2 MVA | 16,400 W | 1,413 W | Table I.1 Tier 2, interpolated 2,000–2,500 kVA | transcribed + derived |
| Solar inverter station (IEA PVPS) | 2.5 MVA | 18,500 W | 1,575 W | Table I.1 Tier 2 | transcribed |
| Grid intake (Leng main unit) | 100 MVA | 0.288 % of S | 0.046 % of S | Table I.7 Tier 2, PEI ≥ 100 MVA 99.770 %, split at k_PEI 0.4 | transcribed + **assumed** split |

Retained Commission Regulation (EU) No 548/2014, Annex I, Tier 2 (1 July
2021), read on legislation.gov.uk on 14 Oct 2026 —
<https://www.legislation.gov.uk/eur/2014/548/annex/I/division/1/adopted> and
`/division/2/adopted`. These are legal maxima, so a real unit is at or below
them. Leng's turbine unit is wound for 35 kV, above Table I.1's 24 kV class;
the table is read anyway as the nearest limit.

Per MW: wind 1.1 MVA/MW (50 × 2.2 MVA per 100 MW), solar 1.0 MVA/MWp (4 ×
2.5 MVA per 10 MWp), intake 2 MVA/MW (N-1 ÷ power factor 1.0, each unit
carrying half). No-load loss is drawn at the node on installed capacity every
step; load loss is linearised at the energy-weighted loading Σx²/Σx of the
window's own capacity factors (`dc_model.loss_factors`) and, for the intake,
at an ASSUMED 0.5.

## Hydrogen as a greenhouse gas — `dc_model.H2_GWP100`

Added 14 Oct 2026. Leaked hydrogen is charged at **GWP100 = 11.6 kg CO₂e/kg**
— Sand, M. et al. (2023), "A multi-model assessment of the Global Warming
Potential of hydrogen", *Communications Earth & Environment* 4:203,
<https://doi.org/10.1038/s43247-023-00857-8> (11.6 ± 2.8). Warwick, N. et al.
(2022) for BEIS give 11 ± 5. IPCC 2021 GWP100 as implemented in ecoinvent 3.9.1
carries **no** characterisation factor for hydrogen (checked 14 Oct), so this is
a stated extension of the study's method, applied only to the tank's leakage.

## Unserved load in the carbon objective — `dc_model.VOLL_KGCO2E_PER_MWH`

A penalty, not an emission: VoLL (£100,000/MWh, ASSUMED) at the study's
carbon price, FES 2025 CP2 for 2025 (£78.96/t), = 1,266 t CO₂e/MWh. Charged
the same way cost charges VoLL, so a shed MWh weighs the same in both
objectives. Reported totals carry it; intensities do not.

## Scope decisions

These are choices, not data. They are recorded in `ASSUMPTIONS.md` with their
consequences: the data centre runs flat at 100 %; geography is GB, reached by
swapping the data centre's US-SERC electricity exchanges rather than
re-authoring the inventory; hydrogen is always co-located with its use, so no
transport is modelled for any colour.

## Still open

Tracked in `DATA_GAPS.md`. At the time of writing, on the carbon side: the
fuel cell's BoP calendar life, hydrogen tank standing loss, battery standing
loss (both bounded by sweep but unsourced), and the absence of a stack/BoP split in the electrolyser inventory. On
the cost side: fuel cell capex, hydrogen tank capex, SOEC costs, battery fixed
OPEX, and demand-side network charges (DUoS/TNUoS) for the data centre's own
import — the DESNZ connection figures are *generator*-side and are not a
substitute.
