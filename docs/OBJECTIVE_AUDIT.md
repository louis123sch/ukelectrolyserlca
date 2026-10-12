# Objective-term audit — 30 Sep 2026

Every term in the two objectives of `dc_model.build_model()`, and every parameter
that decides how much of each term gets bought. For each: its value, where it
comes from, what has actually been checked, what is already on the books, and
what is missing that nothing records yet.

Working tree as of 30 Sep 2026, uncommitted changes included. Central case,
PEM, London, unless stated. Read-only: nothing in the repo was changed to
produce this, and every cache was read as it stands.

**How it was checked.**
- Every coefficient was recomputed by hand from its module constants, CSVs and
  caches, and compared with what `build_tech()` returns for PEM/SOEC/AE ×
  low/central/high.
- Primary sources were re-opened where reachable: the DESNZ/Arup PDFs, Modo's
  assumptions page, NESO's field definitions, the DOE targets and Battelle 2016,
  and the ecoinvent dataset comments.
- Stored runs and cached series were analysed; scratch LPs were solved in memory.
- The test suite was run: **153 passed, 3 skipped**.
- `audit.py`'s structural checks were run on a synthetic series.

**Markers.** **[K]** means the gap is already in `TODO.md`, `DATA_GAPS.md`,
`ASSUMPTIONS.md` or `docs/REVIEW_RESPONSE_PLAN.md`. **[N]** means it is new —
recorded nowhere. *Unverified* marks a finding inferred rather than checked;
everything else was checked against code or data.

---

## 0. The short version

- **The arithmetic is sound; the wiring mostly is.**
  - Every coefficient in `Tech` reproduces exactly from its constants, across all
    three cost cases and all three electrolysers.
  - The LP is dimensionally consistent throughout.
  - The structural audit finds nothing it has not already accepted.
  - What is weak is mainly what the numbers *describe*. There are three genuine
    wiring bugs as well: the grid-carbon clock, the fixed charge on islanded
    builds, and offshore running on the onshore profile.
- **What has been checked against a primary source:**
  - the DESNZ/Arup generation tables (confirmed against the PDFs in this audit);
  - the Smith 2024 solar foreground;
  - both transformer bills of materials;
  - the Gandiglio tank;
  - the Babatunde stack transcription;
  - the NESO/TNUoS/TDR/BSUoS values;
  - the battery's pinned ecoinvent scores.
  - Most other terms are proxies, secondary figures or assumptions whose
    arithmetic is right but whose source was never re-opened.
- **Tests pin almost nothing that decides a result.**
  - Only the two transformer terms are checked by value, and then only against
    bounds.
  - The grid fixed charge and the facility constant are checked only for passing
    through, on fixture values.
  - Everything else is exercised but never asserted.
  - The only test of the fuel-cell `max(calendar, duty)` rule skips on every
    run, as does the baseload-strategy test.
- **Eight new findings move results.** Each is detailed below.

| # | Finding | Direction | Size |
|---|---|---|---|
| 1 | Grid gas is scored on ecoinvent's *conventional power plant* (558 g/kWh), not CCGT (387). The docs say that dataset is refused | `ci` too high, which flatters every on-site asset | ~30–50 g/kWh (12–21 %) of a 236.9 mean |
| 2 | The import price carries no policy levies (RO, FiT, CfD, CM, AAHEDC, CCL) | Import too cheap, which flatters the grid | ~£54/MWh; +50 % on the grid-only bill |
| 3 | Grid carbon is in London local time while price and weather are UTC | Intraday carbon wrong by 1 h, seven months a year | +0.6 % annual; matters for timing |
| 4 | Islanded builds pay the grid fixed charge | Biased against islanded | £271k/yr London; up to £4.67 m |
| 5 | The fuel-cell *carbon* inventory is a natural-gas micro-CHP (reformer kit, reformer upkeep, installer travel) | FC carbon too high | maintenance term → ~0; BoP −15 % or more |
| 6 | Bought grid-connected green is market-based; the LP's own grid electrolyser is location-based | Favours buying | 1.50 vs ~13.3 kg CO₂e/kg |
| 7 | Offshore wind is dispatched on the *onshore* profile | Offshore mis-valued; built in the high case on the wrong yield | whole term |
| 8 | `validate.py`'s grid-only benchmark would now fail | Validation stale and broken | 1.85 % vs a 0.5 % threshold |

---

## 1. The two objectives

`s` is `annual_scale` (8,760 h ÷ window hours) and `Δt` is the step. `K` is a
capacity. Flows are per step. Line numbers refer to `dc_model.py`.

**Cost, £/yr** (`:358-374`, plus one constant)

| ID | Term | Central coefficient |
|---|---|---|
| C1 | `cost_wind · K_wind` | £147,073/MW/yr |
| C2 | `cost_offshore · K_offshore` | £419,201/MW/yr |
| C3 | `cost_solar · K_solar` | £48,368/MWp/yr |
| C4 | `cost_batt_p · K_batt_p` | £34,903/MW/yr |
| C5 | `cost_batt_e · K_batt_e` | £11,634/MWh/yr |
| C6 | `cost_ely · K_ely` | £212,511/MW/yr (AE 183,965; SOEC 318,766) |
| C7 | `cost_tank · K_tank` | £64.64/kg/yr |
| C8 | `cost_fc · K_fc` | £160,835/MW/yr (BoP share only) |
| C9 | `cost_fc_stack_per_mw · n_stack` | £308,698 per MW of stack replaced |
| C10 | `cost_grid_per_mw_year · K_grid` | £40,949/MW/yr London; £0 in floored TNUoS zones |
| C11 | `s · Σ price_t · imp_t · Δt` | £94.19/MWh mean London 2025 (wholesale 79.83 + BSUoS 12.31 + DUoS 2.05) |
| C12 | `s · Σ π₁ · buy₁_t` | green £6.73/kg delivered |
| C13 | `s · Σ π₂ · buy₂_t` | grey £3.05/kg delivered |
| C14 | `s · Σ VoLL · unserved_t · Δt` | £100,000/MWh |
| C15 | `− s · Σ price_t · exp_t · Δt` | dormant: `allow_export` is never set |
| C16 | constant `cost_grid_fixed_per_year` | £271k (EHV2) to £4.67 m/yr |

**GWP, kg CO₂e/yr** (`:375-399`, plus two constants)

| ID | Term | Central coefficient |
|---|---|---|
| G1 | `gwp_wind · K_wind` | 19,244 kg/MW/yr (16,930–26,710 by cost case) |
| G2 | `gwp_offshore · K_offshore` | 26,408 kg/MW/yr |
| G3 | `gwp_solar · K_solar` | 23,561 kg/MWp/yr |
| G4 | `gwp_batt_p · K_batt_p` | 2,124 kg/MW/yr |
| G5 | `gwp_batt_e · K_batt_e` | 6,547 kg/MWh/yr |
| G6 | `gwp_ely · K_ely` | 10,434 kg/MW/yr (SOEC 14,511; AE 17,295) |
| G7 | `gwp_tank · K_tank` | 63.79 kg/kg/yr |
| G8 | `gwp_fc_bop_per_mw · n_bop` | 469,040 kg per MW of BoP replaced |
| G9 | `gwp_fc_stack_per_mw · n_stack` | 97,431 kg per MW of stack replaced |
| G10 | `gwp_grid_per_mw · K_grid` | 333.5 kg/MW/yr |
| G11 | `gwp_tx_wind_per_mw · (K_wind + K_offshore)` | 278.7 kg/MW/yr |
| G12 | `gwp_tx_solar_per_mwp · K_solar` | 296.0 kg/MWp/yr |
| G13 | `s · Σ gwp_fc_maint · p_fc · Δt` | 3.114 kg/MWh |
| G14 | `s · Σ ci_t · imp_t · Δt` | 236.9 kg/MWh mean London 2025 (range 27.6–489.8) |
| G15 | `s · Σ γ₁ · buy₁_t` | green 1.245 kg/kg |
| G16 | `s · Σ γ₂ · buy₂_t` | grey 10.92 kg/kg |
| G17 | `s · Σ g_cons · 1000/(e_ely + e_comp) · p_ely · Δt` | 0.107 / 1.628 / 0.042 kg/kg (PEM/SOEC/AE) |
| G18 | constant `dc_fixed_gwp_per_year` | 157.1 t per MW of IT per year |
| G19 | constant `dc_other_gwp_per_mwh · demand` | 1.809 kg/MWh |

**Parameters that set the quantities** (`:283-342`)

| ID | Parameter | Value |
|---|---|---|
| P1 | `cf_wind[t]` (onshore **and offshore**), `cf_solar[t]` | Renewables.ninja at the site |
| P2 | `batt_rte`, `batt_leakage_per_hour` | 0.88, 0 |
| P3 | `ely_kwh_per_kg` + `tank_compression_kwh_per_kg` | PEM 54.0 + 0; SOEC 42.3 + 2.098; AE 51.8 + 0 |
| P4 | `tank_leakage_per_hour` | 0 |
| P5 | `fc_kg_h2_per_mwh` | 63.16 (50 % × 0.95 derate) |
| P6 | fuel-cell lives | BoP 25 y / 60,000 h; stack **`horizon_years`** / 32,000 h |
| P7 | strategy floors | 0.8 per step, 0.85 annual |
| P8 | demand = IT × PUE, flat | PUE default 1.15, which no production caller uses |

---

## 2. Scorecard

**Source** column:
- ✔ — checked against the primary source (by the study or this audit)
- ~ — partly: the proxy is confirmed as the stated dataset, or a transcription is asserted but not re-checked
- ✘ — no source, or not checked

**Test** column:
- ✔ — a test pins the value
- ~ — a test exercises or bounds it
- ✘ — nothing

| ID | Grade | Source | Test | Open items |
|---|---|---|---|---|
| C1 `cost_wind` | SOURCED | ✔ | ✘ | [N] generator network charges on behind-the-meter plant (+11.6 %); [N] land and rates missing (−21 %); [N] 2023 £ not rebased |
| C2 `cost_offshore` | SOURCED | ✔ | ✘ | [N] onshore profile; [N] built in the high case on the wrong yield |
| C3 `cost_solar` | SOURCED | ✔ | ✘ | [N] 2023 £; [N] generator charges (+3.3 %) |
| C4 `cost_batt_p` | 1-h total SOURCED; opex ASSUMED | ~ | ✘ | [K] opex proxy; [N] power/energy split unsourced |
| C5 `cost_batt_e` | **UNSOURCED** | ✘ | ✘ | [N] £100/kWh not on the cited page; [N] no duration bound (42 h islanded) |
| C6 `cost_ely` | SECONDARY (NESO); SOEC UNSOURCED | ~ | ✘ | [K] SOEC; [K] consumables; [N] NESO variable opex (stack + water) dropped; [N] 6 % unsourced |
| C7 `cost_tank` | **UNSOURCED** | ✘ | ✘ | [K] describes a different vessel (3–10× low); [N] heel |
| C8 `cost_fc` | PROXY | ~ | ✘ (stale fixture) | [K] capex; [K] BoP duty free; [N] equipment not installed cost, undeflated 2015 $ |
| C9 `cost_fc_stack_per_mw` | PROXY × carbon-share split | ✘ | ✘ | [K] undiscounted; [K] horizon; [N] cost-based share is 22–41 %, not 17 % |
| C10 `cost_grid_per_mw_year` | SOURCED (FY2026 / LPN) | ✔ | ~ (slow test) | [K] London-only DUoS; [K] £0 floored; [N] Triad shape; [N] two different agreed capacities |
| C11 import price | SOURCED | ~ | ~ | [N] **levies absent**; [N] **clock**; [N] DUoS tariff class and red band |
| C12–13 bought H₂ £ | SECONDARY + ASSUMED | ✔ reproduced | ~ (compression) | [K] share, haulage; [N] grey ETS level; [N] T&S already in blue; [N] levy asymmetry |
| C14 VoLL | ASSUMED | — | ✘ | [N] unserved is carbon-free; gross-demand denominators |
| C15 export | — | — | ✘ | [N] credited at demand rates, so unbounded if switched on |
| C16 fixed charge | SOURCED values | ~ | ~ (pass-through only) | [N] **charged to islanded builds**; [K] Sch. 32 bands; [K] 100 MW threshold |
| G1 `gwp_wind` | SECONDARY (ecoinvent V80) | ~ | ✘ | [N] 20-year turbine amortised over 35–40 years; [N] coastal CF above DESNZ net |
| G2 `gwp_offshore` | SECONDARY / PROXY | ~ | ✘ | [N] no offshore substation or export system |
| G3 `gwp_solar` | SECONDARY (Smith, rescored) | ✔ | ~ | [K] 21 parked UPV items; [N] cached series at 35° |
| G4 `gwp_batt_p` | PROXY (PV inverter) | ~ | ✘ | [K] no step-up |
| G5 `gwp_batt_e` | PROXY (EV pack) | ~ | ✘ | [K] enclosure; [K] 25–35 % high; [N] per gross DC kWh |
| G6 `gwp_ely` | SECONDARY (Hermesmann) | ~ | ~ (identity) | [K] duty-blind; [N] factory electricity GB vs DE |
| G7 `gwp_tank` | **SOURCED primary** | ✔ | ✘ | [K] leakage, fittings; [N] heel |
| G8 `gwp_fc_bop_per_mw` | SECONDARY: **natural-gas** 2 kW micro-CHP | ✘ | ~ (identity) | [N] reformer kit, installer travel, 2 kW scaled linearly |
| G9 `gwp_fc_stack_per_mw` | SECONDARY | ✔ transcription | ✘ | [K] horizon; [N] dataset states 6 y |
| G10 `gwp_grid_per_mw` | PROXY; mass uncited | ✘ | ✘ | [K] electronics part; [N] no source row |
| G11 `gwp_tx_wind_per_mw` | SECONDARY (Leng) | ✔ | ~ | [K] materials only |
| G12 `gwp_tx_solar_per_mwp` | SECONDARY (IEA PVPS 2026) | ✔ | ~ | [N] six comments and one TODO item still call it the old unit |
| G13 `gwp_fc_maint` | SECONDARY: **reformer upkeep** | ✘ | ✘ | [N] should be ~0 for a hydrogen-fed PEMFC; no cost counterpart |
| G14 `ci[t]` | mix SOURCED, factors DERIVED | ~ (arithmetic) | ✘ | [N] **gas dataset**; [N] **clock**; [N] import weights; [K] marginal |
| G15–16 bought H₂ carbon | mixed | ✔ reproduced | ✘ | [N] market vs location basis; [N] turquoise constructs differ |
| G17 consumables | SECONDARY + PROXY heat | ~ | ✘ | [K] free in cost; [N] the heat proxy decides SOEC vs PEM |
| G18 `dc_fixed` | SECONDARY (Zhang) | ✔ (rebuild to 1e-4) | ~ (pass-through, v1 fixture) | [N] validate runs it at 1.40×; registers carry v1 figures |
| G19 `dc_other` | SECONDARY | ✔ | ✘ (fixture 0) | [N] R134a leakage *unverified* |
| P1 capacity factors | SECONDARY | ~ | ✘ | [N] offshore = onshore; [N] solar cache at 35° |
| P2 battery RTE, leak | UNSOURCED / ASSUMED | ✘ | ✘ | [K] standing loss; [N] wrong loss form for the planned sweep |
| P3 kWh/kg, compression | SECONDARY / derived | ~ | ✘ | [N] compressor draw sits inside `cap_ely` |
| P4 tank leak | ASSUMED | — | ✘ | [K] |
| P5 FC efficiency | ASSUMED | ~ | ~ (band) | [N] anchors are a stack figure and uncited numbers |
| P6 FC lives | ASSUMED / wrong class | ✘ | ✘ (skips) | [K] horizon; [N] 80,000 h class; dataset 15 y / 6 y |
| P7 strategies | ASSUMED | — | ✘ (skips) | [N] "flexible" with a grid is identical to "free" |
| P8 demand, PUE | — | — | ~ | [N] entry points use PUE 1.0 / 1.2 / 1.5 |

---

## 3. Term by term

### 3.1 Renewable generation — C1–C3, G1–G3, G11, G12, P1

| Term | Central | Grade | Reproduced | Source checked | Test pins value |
|---|---|---|---|---|---|
| C1 `cost_wind` | £147,073/MW/yr | SOURCED: DESNZ/Arup 2024 T3, matches the PDF | ✔ | ✔ (this audit) | ✘ |
| C2 `cost_offshore` | £419,201/MW/yr | SOURCED: offshore T3 | ✔ | ✔ | ✘ |
| C3 `cost_solar` | £48,368/MWp/yr | SOURCED: T4, per kWp DC | ✔ | ✔ | ✘ |
| G1 `gwp_wind` | 19,244 kg/MW/yr | SECONDARY: ecoinvent V80 2 MW, decomposed | ✔ | reconstruction passes when run by hand | ✘ |
| G2 `gwp_offshore` | 26,408 kg/MW/yr | SECONDARY / PROXY | ✔ | partly | ✘ |
| G3 `gwp_solar` | 23,561 kg/MWp/yr | SECONDARY: Smith 2024 UPV rescored on apos | ✔ | ✔ (290/290 values; EPEAT reproduced) | basis and life only |
| G11 `gwp_tx_wind_per_mw` | 278.7 kg/MW/yr | SECONDARY: Leng 2026 BoM, materials only | ✔ | ✔ | ratio and share bounds |
| G12 `gwp_tx_solar_per_mwp` | 296.0 kg/MWp/yr | SECONDARY: IEA PVPS T12-33:2026 | ✔ | ✔ | ratio and share bounds |
| P1 `cf_wind` | 36.0 % London 2025 (V90, 80 m, MERRA-2) | SECONDARY; not in `SOURCES.md` | — | partly | ✘ |
| P1 `cf_solar` | 13.96 %, **at 35°** | SECONDARY; losses assumed | — | partly | ✘ |

Every value reproduces across all three cost cases. The price base is 2023 real
(see §4). DESNZ has no variable O&M, so curtailed output costs nothing on either
side.

**Solar's step-up transformer is already on the IEA PVPS basis.**
`transformers.SOLAR_BASIS = "iea_pvps_2026"`; the legacy basis would give 184.2.
`DATA_GAPS.md` is right. Stale:
- the `TODO.md` item "Solar's step-up is still the old invented unit";
- six code comments: `dc_model.py:162-163` (which also calls solar "the smaller
  of the two" — it is the larger), `dc_model.py:388-391`, `dc_inputs.py:398-401`,
  `transformers.py:354-356` and `tests/test_coefficients.py:429-431`;
- TODO's "230.2 kg CO₂e/MW/year", which appears nowhere else except as a
  synthetic test input.

**Already recorded [K]**
- The CRF omits construction-period financing.
- Solar's 21 parked UPV items.
- Construction transport (−1.5 %).
- The DESNZ-vs-ninja solar load-factor gap.
- The wind transformer is materials-only and Chinese.
- Switchgear and conversion losses.

**New [N]**
- **Generator network charges are charged to behind-the-meter plant.**
  - DESNZ's "Connection and UoS" line is the generator's own TNUoS/DUoS.
  - The study's generation sits behind the data centre's meter with export off —
    `transformers.py:87-92` drops the export transformer on exactly that ground.
  - Cost still carries:
    - +£17.0k/MW/yr onshore (11.6 % of `cost_wind`);
    - +£1.6k/MWp solar (3.3 %);
    - +£83.4k offshore (19.9 %).
  - `DATA_GAPS.md` lists this as closed.
- **Land and business rates are missing.**
  - DESNZ keeps them out of opex (§5.8: onshore land ~£19.5k and rates ~£12.0k/MW/yr).
  - That is about 21 % of `cost_wind`, pulling the other way from the item above.
  - No register mentions it.
- **The ecoinvent turbine is a 20-year asset amortised over 35–40 years, with no
  replacement burden.**
  - Its own comment: "all parts will hold for the lifetime of 20 years".
  - DESNZ's O&M pays for the life extension on the cost side; carbon gets it free.
  - Upper bound: `gwp_wind` 33,349 (+73 %) at 20 years.
- **Coastal wind yields exceed what DESNZ allows.**
  - Cached 2025 capacity factors: London 36.0 %, North Norfolk 52.3 %, Cornwall 59.5 %.
  - Stored min-cost runs dispatch 42.6 % and 50.4 % even after curtailment.
  - Both are above DESNZ's high-case *net* 41.3 %, which already allows for
    availability, wakes and electrical losses.
  - A gross single-turbine V90 series therefore flatters wind-heavy and islanded
    builds at exactly the sites the locational headline rests on.
  - Only the solar version of this gap is registered.
- **Offshore is dispatched on the onshore profile** (`dc_model.py:291`, also
  `:474` and `:663-664`).
  - No offshore profile exists anywhere, and nothing documents this.
  - In the low and central cases offshore is strictly dominated and never built.
  - In the **high** case `gwp_offshore` (26,322) falls below `gwp_wind` (26,708),
    because onshore life drops to 25 y. A scratch LP built 59 MW of offshore and no
    onshore, on onshore yield, at £520.6k/MW/yr.
  - Offshore is live for sites flagged in regions {1, 2, 4, 5, 6, 7, 10, 11, 12, 14}.
  - Offshore *carbon* has no substation or export system, while cost carries OFTO
    through TNUoS.
- **Cached solar series use the old 35° geometry.** Config now says 20°. All ten
  cached series, and the 13.96–15.15 % quoted in `DATA_GAPS.md`, are at 35°.
- **Three different turbines.** Cost is for 4.3–6.8 MW machines, carbon for a
  V80 2 MW, dispatch for a V90 2 MW at 80 m.
- **The cost case moves carbon.**
  - Intended (`renewables.py:397-402`, for lifetime parity), but in no register.
  - The UI says the cost case "drives every cost table".
  - Onshore moves −12 % / +39 %.
- **Stale files and checks.**
  - `tech_lca_coefficients.csv` (3 Sep) still carries the IEA rooftop row and no
    transformers.
  - `UPV-DEFERRED-ISSUES.md` gives the plant total as 908.2; it is 895.3.
  - SOURCES.md, the `renewables.py` docstrings and `audit.py` still name IEA PVPS
    2023 as the default.
  - The mounting mass is 9.618 kg/m² in one place and 9.764 in another.
  - `audit.check_lifetime_agreement` cannot fail for renewables, because both
    sides read the same constant.
  - Nothing pins the three cost values, `gwp_wind` or `gwp_offshore`.

### 3.2 Battery — C4, C5, G4, G5, P2

| Term | Central | Grade | Reproduced | Source checked | Test pins value |
|---|---|---|---|---|---|
| C4 `cost_batt_p` | £34,903/MW/yr = £300/kW × (CRF 5 %/15 y + 2 %) | 1-hour total SOURCED (Modo); the split is not | ✔ | partly | ✘ |
| C5 `cost_batt_e` | £11,634/MWh/yr = £100/kWh × the same | **UNSOURCED** (below) | ✔ | ✘ | ✘ |
| G4 `gwp_batt_p` | 2,124 kg/MW/yr = 31.9 kg/kW ÷ 15 y | PROXY: ecoinvent-v2 one-way PV inverter | ✔ | ✔ (pinned score) | ✘ |
| G5 `gwp_batt_e` | 6,547 kg/MWh/yr = 98.2 kg/kWh ÷ 15 y | PROXY: 2016-era EV traction pack | ✔ | ✔ (density) | ✘ |
| P2 `batt_rte` | 0.88 | UNSOURCED value — Modo defines RTE at the point of connection but gives no number | — | ✘ | ✘ |
| P2 `batt_leakage_per_hour` | 0 | ASSUMED | — | — | ✘ |

`battery.check_against_ecoinvent()` re-scores both pinned factors to within
0.1 %, but only `battery.run()` and the page call it; no test does.

**Already recorded [K]**
- No enclosure, HVAC or racking.
- Pack carbon probably 25–35 % high (BatPaC, EverBatt).
- Opex is a 2 % proxy.
- No step-up transformer.
- No cycle limit or fade.
- Standing loss is zero.
- End-of-life excluded.

**New [N]**
- **The £100/kWh energy price is not on the cited page.**
  - `SOURCES.md` grades "£100/kW per additional hour" as *transcribed* from Modo's
    model-assumptions page.
  - Re-fetched 30 Sep, the page gives "~£400/kW (1h)" and nothing else on cost: no
    duration increment, no RTE, no opex.
  - That £100 sets 66–75 % of battery capex at the durations actually built.
- **Duration is unconstrained, and the LP uses that.**
  - Stored Pareto points hold 5.8–8.8 h, three to five times Modo's 1.9 h
    evidence base.
  - An islanded scratch solve on live coefficients built a **42 h** Li-ion battery
    cycling about 10 times a year.
  - There is no E/P or C-rate bound, and no test.
- **Simultaneous charge and discharge.**
  - Nothing forbids it, and five of six stored anchors do it (15–27 % of reported
    discharge).
  - It is harmless degeneracy where curtailment exists.
  - At negative prices it burns imports through losses.
  - It inflates cycle counts: plan §6.1's "~313 cycles/yr" includes about 20
    phantom cycles.
- **The standing-loss rationale is contradicted by its own source.**
  - Modo's RTE definition includes auxiliary load, so auxiliaries are inside the
    0.88.
  - But that load is spread per cycle, so it is under-counted at the 22–119
    cycles/yr the carbon-minimal builds actually run.
  - The planned sweep also uses the wrong form: `leak × soc` decays stored energy,
    whereas HVAC scales with installed MWh.
  - At the 8–11 % mean state of charge the min-GWP builds hold, the two forms
    differ by 12×.
- **"1 MWh" has three different bases.**
  - Cost is per AC-usable kWh at the point of connection.
  - Carbon is per gross DC pack kWh, with no depth-of-discharge factor.
  - `cap_batt_e` is per internal stored kWh (0.938 deliverable).
  - The mismatch is roughly 5–10 %, in a different direction on each side.
- **Price year.** Modo is real 2025; generation is DESNZ real 2023, not rebased
  (see §4).
- **Checks and records.**
  - `audit.check_lifetime_agreement` compares `ASSET_LIFE_YEARS` with itself.
  - `cap_batt_e` is in neither `DIRECT_BOUND` nor `ENERGY_VARS`, so it is never
    slack-checked.
  - `dc_runner` does not fingerprint `battery.py`.
  - The "300 MW Highland" run quoted in `DATA_GAPS.md` is not stored.

### 3.3 Electrolyser, tank and compression — C6, C7, G6, G7, G17, P3, P4, P7

| Term | Central | Grade | Reproduced | Source checked | Test pins value |
|---|---|---|---|---|---|
| C6 `cost_ely` PEM / AE | £212,511 / £183,965 per MW/yr = capex × (CRF 6 %/25 y + 2.75 %) | SECONDARY (NESO portal); **no `SOURCES.md` row** | ✔ | partly | ✘ (ordering only) |
| C6 `cost_ely` SOEC | £318,766 = PEM × 1.5 | UNSOURCED | ✔ | — | ✘ |
| G6 `gwp_ely` | 10,434 / 14,511 / 17,295 kg/MW/yr (PEM/SOEC/AE) | SECONDARY (Hermesmann, never cited by title or table) | ✔ | cache only | identity checks |
| G17 `ely_variable_gwp_per_kg` | 0.107 / 1.628 / 0.042 kg/kg | SECONDARY + PROXY heat | ✔ | ✘ | ✘ |
| P3 `ely_kwh_per_kg` | 54.0 / 42.3 / 51.8 | SECONDARY; within 1–2 % of NESO's efficiency (a cross-check nobody runs) | ✔ | partly | ✘ |
| P3 `tank_compression_kwh_per_kg` | 0 / 2.098 / 0 | derived physics (Makridis 2017, cited only in a comment); AE 30 bar ASSUMED | ✔ ±10 % | ✘ | ✘ (fixture sets 0) |
| C7 `cost_tank` | £64.64/kg/yr = €770/kg ÷ 1.17 × (CRF + 2 %) | **UNSOURCED**: €500 and €1,040 uncited, €770 a midpoint | ✔ | ✘ | ✘ |
| G7 `gwp_tank` | 63.79 kg/kg/yr = 312.8 kg steel/kg × 5.10 ÷ 25 | **SOURCED primary**, transcribed and Brightway-checked | ✔ | ✔ | ✘ |
| P4 `tank_leakage_per_hour` | 0 | ASSUMED | — | — | ✘ |
| P7 baseload 0.8 / 0.85 | — | ASSUMED, in no register | — | — | skips every run |

**Already recorded [K]**
- SOEC capex is unsourced.
- Consumables are free in cost.
- The tank cost describes a different vessel, ~3–10× low. Reproduced
  independently here at 4.0× the central value, using the plan's carbon-steel
  correlation.
- Compressor capital is missing.
- The electrolyser is duty-blind (160,000 full-load hours = 73 % CF).
- Leakage is zero.
- The AE delivery pressure is assumed.

**New [N]**
- **NESO's variable opex is in the CSV and never read.**
  - `electrolyser_costs_clean.csv` carries `variable_opex_GBP_per_kWh_H2_HHV`.
    NESO defines it as "other opex including water costs and electrolyser stack
    replacement".
  - `h2_capex.electrolyser_costs()` drops it: PEM £0.123/kg, AE £0.104/kg.
  - So **stack replacement and water are in neither objective** for any
    electrolyser — wider than the consumables-cost gap already recorded.
  - Adding it puts +3–9 % on PEM `cost_ely` across 30–85 % CF.
- **The 6 % discount rate has no source.**
  - It comes from `sizing.Electrolyser.discount_rate`.
  - `dc_inputs.py:43` says "see ASSUMPTIONS.md", which says nothing about it.
  - The Green Book 3.5 % that `DATA_GAPS.md` lists as *closed* is used by no code.
  - At 3.5 %: `cost_ely` −16.6 %, `cost_tank` −17.9 %.
- **NESO's low/central/high *do* vary capex** — from 2030 onwards (PEM 1,480 /
  1,580 / 1,740). They coincide only in 2025. `DATA_GAPS.md` and
  `h2_capex.py:281-286` say the opposite.
- **SOEC's heat is scored on a proxy, and the proxy decides the technology
  choice.**
  - 87 % of SOEC's 1.628 kg/kg is 18.9 MJ of "heat, district or industrial, other
    than natural gas" [RER].
  - On renewable power that makes SOEC 2.27 kg/kg against PEM's 0.89. With
    zero-burden heat SOEC would be 0.22.
  - `SOURCES.md` does not record the choice.
- **Manufacturing electricity differs by technology.**
  - 43 % of PEM's and 38 % of SOEC's capital carbon is factory electricity on
    ecoinvent's GB grid at 311 g/kWh — the dataset the study refuses for its own
    grid.
  - AE's factory electricity is on the **DE** grid.
- **Compressor power is already inside `cap_ely`.**
  - `p_ely` includes compression draw, so 4.7 % of SOEC's `cap_ely` is compressor,
    priced at electrolyser rates (≈£142k/MW).
  - Hermesmann's bills of materials already list compressors.
  - So plan §6.3 option 2 would double count as written.
  - SOEC's 42.3 kWh/kg may already include compression. *Unverified.*
- **Tank heel.**
  - `cap_tank` is gross content, but the LP drains the tank to zero.
  - With a 1 / 3 / 5 bar minimum for the fuel-cell feed, usable capacity is 96 /
    89 / 82 %.
  - Both objectives are therefore 4–22 % low per usable kg.
- **"Flexible" with a grid is the same as "free".**
  - `apply_strategy` adds no constraint when a grid exists (`dc_model.py:448-449`).
  - So the three grid + H₂ × flexible matrix scenarios duplicate "free", while the
    UI calls the mode "surplus only".
- **Smaller items.**
  - `sizing.py:80` hard-codes £2,010/kWe for every technology, so AE is 15.5 % high
    and SOEC 33 % low against the LP.
  - `ASSUMPTIONS.md` §3 still says compression comes from
    `dashboard_config.TANK_COMPRESSION_KWH_PER_KG`, which the LP no longer reads.
  - `coefficients.py` shows 0.0 kWh/kg for the 28 bar tank even when SOEC feeds it.
  - `DATA_GAPS.md` and `audit.py` quote SOEC's advantage as 21.7 % / 12.4 %; with
    compression it is 17.8 % / 8.6 %.
- *Unverified:* Hermesmann's 160,000 h equals 20 y × 8,000 h. If that is the
  paper's basis, amortising over 25 y understates `gwp_ely` by 20 %.

### 3.4 Fuel cell — C8, C9, G8, G9, G13, P5, P6

| Term | Central | Grade | Reproduced | Source checked | Test pins value |
|---|---|---|---|---|---|
| C8 `cost_fc` | £160,835/MW/yr = $2,300/kW ÷ 1.28 × (1 − 0.172) × (CRF 6 %/25 y + 3 %) | PROXY (DOE natural-gas CHP, *equipment* cost) | ✔ | DOE row ✔ | ✘ (ordering) |
| C9 `cost_fc_stack_per_mw` | £308,698 per MW replaced = capex × 0.172, undiscounted | PROXY × a carbon-share split | ✔ | ✘ | ✘ |
| G8 `gwp_fc_bop_per_mw` | 469,040 kg per MW replaced (18.8 t/MW/yr when calendar-bound) | SECONDARY: ecoinvent 2 kW **natural-gas micro-CHP** net of stack | ✔ | ✘ | identity only |
| G9 `gwp_fc_stack_per_mw` | 97,431 kg per MW replaced | SECONDARY: Babatunde transcription checked — the only external check | ✔ | ✔ | ✘ |
| G13 `gwp_fc_maint_per_mwh` | 3.114 kg/MWh | SECONDARY: reformer upkeep | ✔ | ✘ | ✘ |
| P5 `fc_kg_h2_per_mwh` | 63.16 kg/MWh | ASSUMED | ✔ | ✘ | round-trip band only |
| P6 lives | BoP 25 y / 60,000 h; stack `horizon_years` / 32,000 h | ASSUMED / wrong size class / UNSOURCED | — | ✘ | skips every run |

**Already recorded [K]** — all confirmed:
- BoP replacement is free in cost. A synthetic 8,760 h solve reproduces £245k vs
  £403k/MW/yr.
- The stack's calendar life is the horizon.
- DOE natural-gas capex proxy.
- The fixture double counts.
- `myopic` has drifted.
- The `decompose()` cache trap — which also freezes the cost-side CRF life and
  stack split, in `h2_capex.py:124,141`.
- `dc_runner` fingerprints the stale `h2_capex.csv`.
- `DUTY_VIA` pooling.
- No step-up transformer.

**New [N]**
- **The carbon side is a natural-gas machine too.**
  - The ecoinvent system is "Operation with connection to low pressure gas network.
    Electrical efficiency 32 %" (dataset comment, re-read 30 Sep).
  - Outside the stack it carries fuel-processor items: Pt, TiO₂ and activated carbon.
  - The registers attribute the reformer bias to *cost* only.
- **`gwp_fc_maint_per_mwh` is reformer upkeep.**
  - ecoinvent's maintenance dataset: "every fourth year (21,000 h) reformer
    catalyst stack replacement".
  - For a hydrogen-fed PEMFC this term should be near zero. At 8,760 h it is
    27.3 t/MW/yr, 22 % of the fuel cell's non-fuel carbon.
  - It has no cost counterpart — a carbon-only duty term that `DUTY_VIA` pooling
    hides.
- **400 km of installer car travel stays in the BoP** (71.8 t/MW, 15.3 % of it),
  even though the same artefact is netted out of maintenance.
- **A 2 kW unit is scaled linearly to MW** — the rooftop-vs-utility error fixed for
  solar, not registered here.
- **The lives the registers call unsourced are in the dataset.**
  - System: "15 years or 80'000 h". Stack: "6 years or 32'000 h". Both are linked
    to ~5,300 h/yr of duty, so neither is a clean calendar life.
  - `DATA_GAPS.md`'s "no public figure" is wrong.
  - Plan §2's 10/15/25 y stack sweep sits entirely above 6 y.
  - At backup duty those lives give BoP 31.3 t/MW/yr (vs 18.8) and stack 16.2 (vs 3.9).
- **60,000 h is the wrong DOE size class.**
  - It is the 1–25 kW residential target. The 100 kW–3 MW class whose capex is
    used targets 80,000 h, and so does ecoinvent.
  - With 60,000 h, duty binds above 2,400 h/yr instead of 3,200.
  - Plan §1's fix would copy the error into cost.
- **The "biased high" label on the capex is unsupported.**
  - The figure used is DOE's *equipment* cost; installed cost is 1.2–2.0× that.
  - The 2015 dollars are not deflated (~+35 %).
  - Removing the fuel processor would take off 32–44 %.
  - Net factor 0.9–1.8×: ambiguous, if anything low.
- **Splitting cost by carbon share is a category error.**
  - Battelle's cost-based stack share is 13–27 % for natural-gas CHP, and 22–41 %
    for a hydrogen-fed unit. `h2_capex.py:132-135` misquotes it.
  - Any carbon fix silently moves both cost coefficients: dropping the car travel
    alone moves the share to 19.7 %.
- **The self-checks are identities.**
  - `check_reconstruction`, `check_full_duty` and the rebuild asserts in
    `test_coefficients.py` just sum the parts.
  - `audit` compares the cached 25 y with itself.
  - No test pins a live fuel-cell value, and the only test of the replacement rule
    skips.
- **Smaller items.**
  - The BoP is on Swiss electricity and the stack on GLO.
  - Babatunde's 32,000 h *is* ecoinvent's figure, so the "independent
    corroboration" is circular.
  - The ~51.6 % efficiency anchor is a stack figure, not a net AC system figure.

### 3.5 Grid — C10, C11, C15, C16, G10, G14

| Term | Central (London 2025) | Grade | Reproduced | Source checked | Test pins value |
|---|---|---|---|---|---|
| C11 wholesale | £79.83/MWh mean (−£92 to £1,399) | SOURCED (Elexon APXMIDP) | ✔ | API | ✘ |
| C11 BSUoS | £12.31/MWh | SOURCED (NESO) | ✔ | ✔ | coverage |
| C11 DUoS unit rate | £2.05/MWh | SOURCED LPN, simplified bands | ✔ | ✘ | red-band months |
| C11 levies, CCL, losses, margin | **absent** (~£54–64/MWh) | — | — | — | — |
| C10 TNUoS + DUoS capacity | £7,405 + £33,544 = £40,949/MW/yr | SOURCED (FY2026 / LPN) | ✔ | ✔ | slow test only |
| C16 TDR + DUoS fixed | £575,765/yr (EHV3) | values SOURCED; bands SECONDARY; tier ASSUMED | ✔ | partly | ✘ |
| C15 export credit | dormant — `allow_export` is never set | — | — | — | ✘ |
| G14 `ci[t]` | 236.9 kg/MWh (27.6–489.8); the API's direct figure is 139.1 | mix SOURCED; factors DERIVED (graded "transcribed") | ✔ to 0.004 g | arithmetic only | ✘ |
| G10 `gwp_grid_per_mw` | 333.5 kg/MW/yr | PROXY + uncited mass + ASSUMED | ✔ | ✘ | fixture only |
| (connection capital) | £0 | — | — | — | — |

**Already recorded [K]**
- Levies and supplier margin omitted — one clause in `ASSUMPTIONS.md` §4, never
  quantified.
- DUoS is London-only.
- HV used as a proxy for EHV.
- EHV bands unverified against DCUSA Sch. 32.
- The 100 MW transmission threshold is assumed.
- £0/MW connection in floored TNUoS zones, and no connection capital.
- The grid-connection transformer is still the 280 g electronics part.
- No switchgear.
- Imports flagged for follow-up (plan §4).
- Average rather than marginal intensity (`ASSUMPTIONS.md` §5).

**New [N]**
- **The carbon series is one hour out of step for seven months of the year.**
  - Notebook 3.1 converts the API's UTC timestamps to London local time and drops
    the zone (`row["DATETIME"] = from_local.tz_localize(None)`).
  - The Elexon price and Renewables.ninja series are UTC.
  - `profiles.py:343` joins them on the naive timestamp.
  - Verified: the grid file jumps 00:30 → 02:00 on 30 Mar, while the price file
    runs straight through.
  - So in BST (58 % of slices) `ci[t]` is paired with price and weather from an
    hour later.
  - The annual mean barely moves (+0.6 % on solar's displaced intensity), but
    every intraday carbon signal is an hour out.
  - The same pattern is in `lca_helpers.py:1265-1273`.
- **Grid gas is scored on the "conventional power plant" dataset the docs say is
  refused.**
  - `GRID_CANDIDATE_INDEX = {"GAS": 3}` in notebook 3.1 picks "electricity
    production, natural gas, conventional power plant [GB]", at 558 g/kWh.
  - The query asks for combined cycle, and ecoinvent's GB CCGT (387 g/kWh,
    re-scored in this audit) is candidate #1.
  - `SOURCES.md:104-111` and `h2_prices.py:132-135` state that the study refuses
    this dataset for its own grid. It does not.
  - Gas is about 28 % of London's 2025 mix, so `ci` is plausibly **30–50 g/kWh
    (12–21 %) high**. The 16,132 t baseline and every grid-vs-on-site comparison
    inherit it.
- **Imports are not weighted a third each.**
  - The weights actually used are FR/IE/NL 63.0 / 7.3 / 29.8 %
    (`lca_helpers.py:63-67`). NL is scored at 478.9 g, and there is no Norway,
    Belgium or Denmark. Plan §4's "a third each" is wrong.
  - Cheap mode omits network infrastructure and SF₆, and uses the HV loss while the
    site draws at MV (~1–3 % low).
  - Grid solar is the 2008 El Tesoro plant that was rejected for on-site PV.
  - Nuclear is a boiling-water reactor dataset; GB has none.
  - Net: `ci` is plausibly **55–90 g/kWh high**.
- **Levies are never quantified.**
  - For 2025/26: RO (0.493 × £67.06 = £33.06), FiT £8.80, CfD £6.39, CM £5.00,
    AAHEDC £0.45 — about **£54/MWh**.
  - Plus CCL (£7.75, or £0.62 under a CCA) and about £2.5 of losses. Carbon grosses
    imports up for 3.16 % losses; cost does not.
  - On the London grid-only bill that is **+£3.95 m/yr (+50 %)**, and it removes
    116 of the 124 negative-price slices.
  - The `ELECTRICITY_DELIVERED_UPLIFT` hook in `5.prices.ipynb` only writes
    `price_timeslices` files, which `profiles.py` never reads. So the LP cannot see
    it even when it is set.
  - The omission flatters grid import against every behind-the-meter asset.
  - *These rates are this audit's reading of the 2025/26 publications; transcribe
    them into `SOURCES.md` before use.*
- **Wrong DUoS tariff class.**
  - "HV Site Specific No Residual" is for certified non-final-demand sites. A data
    centre belongs on Band 1–4, so DUoS is about £2/MWh too high.
  - The Nov–Feb-only red band is unverified. LPN's historic red band was all year,
    weekdays 11:00–14:00 and 16:00–19:00. If that still holds, DUoS is
    £6.96/MWh, not £2.05.
- **Two different agreed capacities.**
  - TDR is banded on the connection *ceiling* (1.5 × load), while DUoS capacity is
    billed on the LP's `cap_grid`.
  - At London the ceiling lands in EHV3 while grid-only `cap_grid` sits in EHV2:
    +£304.6k/yr (£4.14/MWh).
  - `SOURCES.md`'s "£23.26/MWh" network adder holds only at PUE 1.0; the default
    run pays £26.85.
- **TNUoS HH demand is levied on Triad demand.**
  - The module's own docstring says so, but the LP charges it on peak import.
  - Identical for flat grid-only; for storage builds it over-charges (up to ~£31k/yr
    at London) and cannot represent triad avoidance.
- **Export, if ever switched on, is broken.**
  - It is credited at demand rates (wholesale + BSUoS + DUoS demand): ~£14/MWh too
    much, ~£50 in red periods.
  - It gets no carbon credit.
  - Nothing stops import and export in the same slice.
  - With no grid limit the LP is unbounded.
  - `contributions()` omits export revenue.
- **Smaller items.**
  - `gwp_grid_per_mw`'s 300 t / 240 MVA transformer mass has no citation, and
    `SOURCES.md` has no `grid_connection` rows.
  - It assumes PF 1.0.
  - Its life is 40 y, against 35 y for the step-ups and 25 y for the facility.
  - The same 400 kV basis is used for distribution-connected sites.
  - In total it is small: 0.02 % of import carbon.
  - Eleven zero-volume APXMIDP slices enter as £0/MWh.

### 3.6 Bought hydrogen — C12, C13, G15, G16

| Colour | £/kg (low / central / high) | kg CO₂e/kg | Grade | Reproduced |
|---|---|---|---|---|
| Green 50:50 | 5.60 / 6.73 / 9.38 | 1.245 | SECONDARY (EHO) + SOURCED (NESO, ecoinvent) + ASSUMED share | ✔ |
| Grey | 2.91 / 3.05 / 3.54 | 10.92 | SECONDARY; ×1.15 high and 0.60 non-fuel undocumented | ✔ |
| Blue | 2.96 / 3.90 / 4.52 | 3.57 | SECONDARY; low is ATR (a PROXY for SMR-CCS) | ✔ |
| Turquoise | 3.09 / 3.33 / 4.55 | 5.91 | ASSUMED construct | ✔ |

`recommended_table()`, regenerated from `neso_cache`, matches the CSV exactly, and
the seven compression tests pass. Nothing else is pinned; the IEA band check lives
only in `run()`.

**Already recorded [K]**
- The green grid share is assumed.
- Green has three different utilisation bases.
- Haulage is excluded.
- Loading-compressor capex is missing.
- Turquoise outlet pressure.

**New [N]**
- **Grid-connected green is market-based; the LP's own grid electrolyser is
  location-based.**
  - Bought grid-connected green is scored on wind, plus losses and network
    embodied carbon. That is renewable only under PPA/REGO matching, which no file
    states, and its EHO price carries no PPA or REGO premium.
  - The LP charges its own grid electrolyser the half-hourly grid (London 2025 mean
    ~237 g/kWh): ~13.3 kg/kg, against 1.50 for the same physical setup bought in.
  - On a location basis the 50:50 blend would be ~7.1 kg/kg, not 1.245.
  - This favours buying.
- **CO₂ T&S is already in blue's price.**
  - NESO's ATR+CCS LCOH carries an explicit `LCOH CO2 T&S Cost` line: £15.69/MWh
    HHV ≈ £0.62/kg (verified in `neso_cache`). EHO's capture case implies ~£0.74/kg.
  - So the `TODO.md` cheap win "CO₂ T&S from FES … needed for SMR-CCS" would
    **double count** if added on top (+£3.60/kg at £450/t).
  - The only coherent version is to replace the embedded rate. The £450/t may also
    be a capital figure (~£55/t levelised).
- **Grey's carbon price is the 2024 ETS level, not FES.**
  - The central case carries ~£32/t (EHO 2024). Only the derived *low* case uses
    FES CP2 at £78.96/t, so low carries 2.4× the carbon cost of central.
  - At CP2 the central price would rise ~£0.42/kg (+14 %).
- **Levy asymmetry.** EHO's grid-connected green carries about £1.36/kg of taxes
  and levies, while the LP's own imports carry none (§3.5). At the 0.5 share that
  is a ~£0.68/kg penalty on bought green.
- **Turquoise price and carbon are different constructs.**
  - The price is an 86/14 grey/green energy blend, on renewable electricity and
    with grey's ETS cost.
  - The carbon is the MP-E inventory on the GB grid.
  - `h2_prices.run()` prints "above band" against Rego et al., yet `DATA_GAPS.md`
    says "validated against Rego".
- **No delivery limit.**
  - `h2_buy` is unbounded and `grid_h2_bought` has no tank, so supply behaves as a
    pipeline.
  - The stored North Norfolk 100 MW min-GWP point buys 13.6 t/day — about 20
    trailer loads an hour at peak.
  - None of this is documented.
- *Unverified:* blue's carbon balance may not close.
  - About 0.9 kg CO₂/kg H₂ from the extra gas appears unaccounted.
  - The CCS-step diesel is linked as a product, with no combustion emissions.
  - This is inferred from stoichiometry, not checked against Hermesmann. If
    confirmed, blue rises 11–48 %.
- **Stale cache and fingerprint.**
  - `bought_h2_gwp_cache.json` predates the 17 Sep rewrite of the hydrogen
    foreground, has no fingerprint, and still holds the dead 17.0 legacy value.
  - `dc_runner` hashes none of `h2_prices.py`, its CSV or its cache.
- **Grid basis for fossil colours.** Grey, blue and turquoise compression and
  inventory electricity stay on the GB ecoinvent grid that the study refuses for
  its own grid.

### 3.7 Facility, VoLL and reliability — G18, G19, C14, P8

| Term | Central | Grade | Reproduced | Source checked | Test pins value |
|---|---|---|---|---|---|
| G18 `dc_fixed` | 157.1 t per MW IT per year (999 t at 6.36 MW IT) | SECONDARY (Zhang et al., Virginia) | ✔ | ✔ (rebuild to 1e-4) | pass-through only, v1 fixture |
| G19 `dc_other` × demand | 1.809 kg/MWh | SECONDARY | ✔ | ✔ | ✘ (fixture sets 0) |
| C14 VoLL | £100,000/MWh | ASSUMED | — | — | ✘ |
| P8 demand = IT × PUE | flat; PUE 1.15 default, used by no production caller | — | — | — | — |

**Already recorded [K]**
- Genset excluded (`ASSUMPTIONS.md` §7).
- Flat load (§1).
- Facility inputs are not GB (§2).
- Cradle-to-gate boundary (§6).
- No unit commitment.
- Perfect foresight.

**New [N]**
- **`validate.py`'s grid-only benchmark would now fail.**
  - `validate.py:316-319` and `myopic.py:232-234` pass 7.31 MW as *IT* load at
    PUE 1.0. Under the v2 facility split that is 1.40× Zhang's IT load, adding
    +328.7 t.
  - Reproduced from cached series: LP 16,439.1 t against a scaled baseline of
    16,140.4 t — **1.85 % against a 0.5 % threshold**.
  - `baseline_grid.run()` also still scores the 32.5 t genset that the LP excludes.
  - The page's "Grid-only reference" always shows 16,132 t / 252 g, whatever size,
    site or window was solved.
  - `TODO.md` expects only 16,014 → 16,132.
- **The entry points disagree on PUE.**
  - The page uses 1.5; the CLI, matrix, validate and myopic use 1.0; audit uses 1.2.
  - That puts the facility constant anywhere from 13.8 to 19.8 kg/MWh — a level
    shift of up to ~6 g/kWh between entry points.
  - `build_tech`'s `pue` argument is dead.
  - `ASSUMPTIONS.md` §1 and the page's PUE help text describe the v1 behaviour.
- **The registers carry v1 figures.**
  - `ASSUMPTIONS.md` §2 says "841 t/y, 5.3 %". It is now 968.3 t in total, 935.8 t
    charged, 6.0 %.
  - `SOURCES.md:24` gives 21,036 t fixed; it is now 24,207 t (+15.1 %), and the
    cause is not recorded.
  - `dc_architectures.py:12` still says "16,006 t".
  - §2's "the only US-located input" is false: the concrete is RNA.
- **Islanded builds pay the grid fixed charge.**
  - `cost_const = tech.cost_grid_fixed_per_year` is applied unconditionally
    (`dc_model.py:353`; also `contributions()` and `myopic`).
  - So `grid=False` rows pay TDR plus the DUoS fixed charge for a connection they
    do not have: £271,192/yr at London (EHV2), up to £4.67 m in the T-Demand bands.
  - It is a constant, so it never moves an argmin, but it biases every
    islanded-versus-grid comparison.
- **Unserved load carries no carbon.**
  - A min-GWP solve with allowance f sheds exactly f, choosing the dirtiest hours
    (455.7 against a 236.9 kg/MWh mean). That is £219k per tonne avoided, and the
    anchor's cost becomes mostly VoLL, stretching the cost axis.
  - Every g/kWh and £/MWh divides by *gross* demand, and the page labels gross
    demand "Demand served".
  - The VoLL comment and `solve()`'s error message say VoLL turns an infeasible
    target into an expensive one. That is true only for f > 0; at the default
    f = 0 the reliability constraint is hard.
  - `audit.NOT_ASSETS` exempts `unserved`, so the audit cannot see this.
- *Unverified — R134a leakage.* The facility foreground has no biosphere exchanges,
  so refrigerant leakage is never charged. If Zhang's 450 kg is an emission, that
  is ~27.5 t/yr at Zhang scale (~24 % of the energy group). Check the paper.

---

## 4. Cross-cutting

### Price base and discount rates

`SOURCES.md:13-16` says "real 2025 GBP throughout". Only the battery (Modo) and
bought H₂ (EHO) actually are.

| Cost term | Price base | Discount rate | Life |
|---|---|---|---|
| Wind, offshore, solar | **2023 real GBP**, not rebased | 5.8 / 6.2 / 5.0 % pre-tax real | 35 / 35 / 38 y |
| Battery | 2025 real GBP | 5.0 % real | 15 y |
| Electrolyser | GBP, year unstated | 6 %, unsourced; real or nominal unstated | 25 y |
| Tank | EUR, year unstated, exchange rate only | 6 % | 25 y |
| Fuel cell BoP | 2015 / 2020 USD, exchange rate only | 6 % | 25 y (cached) |
| Fuel-cell stack | as above | **0 %** (undiscounted) | max(horizon, 32,000 h) |
| Import energy and network | nominal: window year, FY25/26, FY26/27 | — | — |
| Bought H₂ | 2025 real (EHO); NESO cube year unstated | EHO's own; NESO 6/6/8 % | — |
| Carbon (all terms) | — | 0 % (straight-line) | as above |

- UK CPI 2023→25 is about +6 %, so renewables are understated by roughly that much
  relative to the battery and the grid.
- US CPI 2015→25 is about +36 %, so the fuel cell is understated by that on top of
  the equipment-vs-installed gap (§3.4).
- The Green Book 3.5 % is marked *closed* in `DATA_GAPS.md`, but no code uses it.
- Moving the hydrogen assets from 6 % to 3.5 % would cut `cost_ely` by 16.6 %, the
  fuel-cell BoP by 16.2 % and the tank by 17.9 %.

### LCIA method

- The optimisation modules deliberately use IPCC 2021 GWP100 *including* long-term
  emissions.
- The grid series (via `lca_helpers.setup_brightway()`) and notebook 2's default
  use the *no LT* variant.
- Measured on nine key activities (GB MV market, GB CCGT, onshore wind, nuclear,
  biomass CHP, HV transformer, LFP battery, rebar, PEMFC stack), the difference is
  **≤0.02 %**.
- Immaterial, but one method should be pinned in one place.

### Time handling

- **Clock:** see §3.5.
- **Cyclic storage over sub-year windows.** Storage must balance inside the window,
  which is then scaled up (an 8-day window × 45.6), so seasonal storage is worth
  nothing by construction. The page's warning covers only the annualisation bias.
- **`resample()`.**
  - Its docstring table is stale: min-cost GWP error at 1 h re-measured at −0.86 %,
    against the −0.32 % stated.
  - It silently drops trailing steps (17,350 → 17,348 at 2 h).
- **Undocumented in `ASSUMPTIONS.md`.** Perfect foresight, no unit commitment,
  cyclic storage and annualisation are covered only in the `dc_model` docstring and
  `VALIDATION.md`.

---

## 5. Verification infrastructure

**Test suite** (run 30 Sep): 153 passed, 3 skipped.

The two skips that matter are:
- `test_dc_model.py:244`, "no fuel cell built". This is the only test of the
  replacement rule both reviewer points concern.
- `test_dc_model.py:193`, "optimiser declined to build an electrolyser at all".
  This is the only test of the baseload floor.

The synthetic fixture never builds either asset, so both skip on every run. The
fixture itself is stale:
- `cost_fc` 194,244 (the stack double count);
- `dc_fixed` 841,457 (v1);
- `dc_other` 0;
- `gwp_solar` 60,600.

| Objective term | Fast-suite status |
|---|---|
| Both transformer terms | **pinned** (bounds on ratio and share) |
| Grid fixed-charge constant; `dc_fixed` | pass-through asserted, on fixture values (`dc_fixed` is the v1 figure) |
| Wind, solar, battery, electrolyser and tank capacity terms; import price and carbon; `cap_grid` terms; consumables; FC maintenance; bought H₂ stream 1 | exercised, never asserted |
| FC BoP/stack × units | the replacement-count constraint is pinned by a test that skips; coefficients never |
| `cost_fc` | stale fixture |
| `dc_other` × demand | untested (fixture 0; the equality test would fail if it were non-zero) |
| Offshore wind; bought H₂ stream 2; export | never exercised |
| Annual scaling, `resample`, `contributions` reconciliation, myopic parity, the run hash, `build_tech`, cost annuities | untested |

**`audit.py`** (run 30 Sep on a synthetic series with SOEC). Coverage is clean
apart from its two ACCEPTED entries, and the lifetime and degeneracy checks pass.
But:
- **The lifetime check can only fail for the electrolyser.** Every other pair reads
  the same constant on both sides, and there are no pairs for the grid connection
  (40 y) or the transformers (35 y).
- **`DUTY_VIA` pooling hides two asymmetries:** BoP duty free in cost [K], and FC
  maintenance charged in carbon only [N].
- **`NOT_ASSETS` hides** unserved load and bought H₂.
- **`cap_batt_e` is never slack-checked.**
- **The ACCEPTED PV entry and the `foreign` list** still describe IEA PVPS 2023.

**`validate.py` / `VALIDATION.md`** (built 24 Aug on v1 coefficients):
- The baseline benchmark would now fail (§3.7).
- The superset check would be skipped: it looks for
  `dc_runs/r13_51.5074_-0.1278_7.31MW_2025`, and only `*_custom` folders exist.
- "£103.09/MWh" is a hard-coded string, not a computed value.
- The round-trip benchmark runs PEM only, and never does its promised comparison
  with notebook 4.3.
- Both "What these do not cover" bullets are stale: myopic now exists, and all 14
  regions are cached.

**Mirrors**
- **`myopic.evaluate`:**
  - [K] no grid-connection carbon, no bought H₂, no stack cost, no export;
  - [N] it also ignores both leakage terms and the electrolyser strategy, and never
    runs grid electrolysis.
- **`contributions()`:** reconciles with `totals()` to 1e-6, except export revenue,
  which it omits.
- **`dc_pareto`:**
  - the tie-break is sound;
  - `LEX_TOL` misbehaves on negative totals, which are possible only with export;
  - a failed tie-break is swallowed without a flag.
- **`sizing.py`** diverges further than plan §3.8:
  - wholesale-only grid cost;
  - no transformer or connection carbon;
  - the battery is not cyclic;
  - a 10 % minimum load;
  - £2,010/kWe for every electrolyser;
  - "2012 plant" should be 2008.

**Run cache** (`dc_runner._coefficient_identity`)
- It hashes two stale CSVs that the LP does not read, plus the four `dc_*.py`
  files.
- It misses:
  - `battery`, `tech_costs`, `h2_capex`, `fuel_cell`, `electrolysers`,
    `h2_storage`, `renewables`, `transformers`, `grid_connection`, `h2_prices`,
    `network_charges`, `sites`, `profiles` and `dashboard_config`;
  - every decomposition cache;
  - `h2_prices_recommended.csv`;
  - the NESO cache;
  - the series themselves;
  - and **`connection_headroom`**, which the page exposes and which is added to the
    config only after hashing.
- So changing almost any input silently serves an old run. `TODO.md` records only
  the `h2_capex` / `fuel_cell` part.

---

## 6. Stale documents and comments

**Contradicted by code**
- Solar step-up transformer described as "the old invented unit":
  - `TODO.md` (the item, plus the 230.2 figure);
  - `dc_model.py:162-163` and `:388-391`;
  - `dc_inputs.py:398-401`;
  - `transformers.py:354-356`;
  - `tests/test_coefficients.py:429-431`.
- `SOURCES.md:104-111` and `h2_prices.py:132-135`: "lca_helpers refuses the
  conventional gas dataset for the study's own grid".
- `DATA_GAPS.md`:
  - "NESO's Low/Central/High vary the LCOH scenario, not the capital cost";
  - fuel-cell BoP life "no public figure";
  - "validated against Rego";
  - SOEC advantage 21.7 % / 12.4 %;
  - demand-side network charges listed both closed and open (already on TODO).
- `ASSUMPTIONS.md`:
  - §2 facility figures (v1) and "only US-located input";
  - §3 compression via `TANK_COMPRESSION_KWH_PER_KG`;
  - §4 "no DUoS/TNUoS included yet";
  - §6 "no manufacturing energy" for step-ups.
- `SOURCES.md`:
  - "real 2025 GBP throughout";
  - `:24` 21,036 t;
  - `:812` £23.26/MWh (PUE 1.0 only);
  - `:869-877` network charges not modelled.
- Plan §4: imports "a third each" (actually 63/7/30), and "252 = 237 + facility +
  connection" (it includes the genset and no connection carbon).
- `dc_model.py:410-418` and `dc_pareto.py:206-210`: `cap_grid` "absent from gwp".
- `dc_inputs.py:43`: "see ASSUMPTIONS.md" for the discount rate.
- `dc_architectures.py:12`: "16,006 t".
- `VALIDATION.md`: the whole file.

**Stale caches that nothing reads, but people might**
- `tech_lca_coefficients.csv` — IEA solar row, no transformers.
- `h2_capex.csv` — pre-split fuel cell.

---

## 7. What remains, in order

**A. Fix before any number is quoted again.** Mostly cheap, no sourcing needed.

1. **Grid carbon series.**
   - Take gas from GB CCGT, or document why not.
   - Fix the BST clock in notebook 3.1.
   - Review the import weights.
   - Then rebuild the series and the 16,132 t baseline. [N]
2. **Levies into the import price** through a path the LP actually reads. [N]
3. **Zero the grid fixed charge when `grid=False`.** [N]
4. **Fix `validate.py` and `myopic.py` sizing (IT vs facility) and the genset in
   `baseline_grid.run()`, then regenerate `VALIDATION.md`.** [N + K]
5. **Fuel-cell BoP duty in cost, and a stack calendar constant.** [K, plan §1–§2]
   While doing it, use ecoinvent's stated 15 y / 80,000 h and 6 y / 32,000 h, and
   DOE's 80,000 h class, rather than 25 y / 60,000 h. [N]
6. **Offshore:** give it its own profile, or switch it off. [N]
7. **Make the two skipped tests run** by forcing the build, and fix the fixture. [N + K]

**B. Source or decide.** These block a cost result.

8. **Fuel cell, as one job.**
   - Installed-cost capex for a hydrogen-fed MW system. [K]
   - A cost-based stack share. [N]
   - A carbon inventory that is not a natural-gas micro-CHP: drop the reformer
     upkeep and the installer travel as a first step. [N]
9. **SOEC.**
   - Capex and opex. [K]
   - Consumables cost, including NESO's variable opex. [K + N]
   - The heat basis and its availability. [K + N]
10. **Tank.** Cost from shell mass, the default design, and a heel. [K + N]
11. **One price base and one discount-rate policy** for every cost term. [N]
12. **Battery.**
    - A source for the £100/kWh.
    - A duration bound.
    - A decision on simultaneous charge and discharge. [N]
13. **Bought hydrogen.**
    - State the accounting basis (market vs location) and align it with `grid_h2`.
    - Grey at the FES carbon price.
    - Reframe the CO₂ T&S item as a replacement, not an addition. [N]
14. **Renewables.**
    - Generator charges out, land and rates in.
    - Turbine life beyond the inventory's 20 y.
    - Net coastal wind capacity factors. [N]

**C. Hygiene**

15. The run-cache hash, including `connection_headroom`. [K + N]
16. A sweep of the stale documents (§6).
17. Re-fetch the solar series at 20°. [N]
18. "Flexible" with a grid: drop it or define it. [N]
19. Unserved load: carbon treatment and served-demand denominators. [N]
20. Export, before anyone switches it on. [N]
21. The `resample` docstring. [N]
22. Check against the papers: blue's carbon balance and CCS diesel (Hermesmann), and
    R134a leakage (Zhang). *Unverified.*

The standing cheap wins in `TODO.md` — the battery carbon sweep, storage-loss
sweep, BEIS battery opex, Gandiglio tank cost, T/D threshold and grid share as
bands, grid-connection transformer BoM, and the balance-of-plant items — all
remain open and unchanged by this audit.
