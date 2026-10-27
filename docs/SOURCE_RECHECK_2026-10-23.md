# Third source read — 23 Oct 2026

Nine independent readers each re-read one source group against its module in
`optimiser_lca/` and the coefficient it feeds, with every closed item (DATA_GAPS
*Closed*, SOURCE_DIFF, the cut-off register, ASSUMPTIONS §5–8) handed over so it
was not re-raised. The findings that change a number were then re-checked by
hand against the source. Nothing in the code was changed by this read.

**Verdict.** Every source's inventory rows are transcribed at the printed amount
and unit; no closed decision is implemented differently from how it was recorded.
The findings below are mapping, normalisation and scope points, each under a few
per cent of its technology, plus stale documentation.

## Findings that change a number

| # | Where | Finding | Size and direction | Checked by hand |
|---|---|---|---|---|
| 1 | Facility, `dc_inputs.py:78-79` | The IT-driven burden is divided by 5.219 MW of IT, read back from Zhang's printed 1.60e9 kWh. Zhang's S1 (cell D26) sizes servers, UPS and building on **5.38 MW IT** (7.53 MW × 8,760 × 25 = 1.649e9; the printed 1.60e9 is a slip). ASSUMPTIONS §2 notes the 3 % gap but not that the per-MW coefficient inherits it. | Per-MW-IT facility term **3.1 % high**; +475 t/yr at 100 MW IT. Energy-driven term unaffected. | yes |
| 2 | Facility, scope | Zhang §2.2b names chillers, cooling towers, pumps and piping as in scope; S1 sizes an 850 RT plant but inventories none of it, and the cut-off register has no entry. | Unsourced; rough estimate 0.5–2.4 % of the IT-driven term, so it may fail rule 1. Needs a register entry and the 1 % test. Model low. | yes (S1 text) |
| 3 | Facility, `data_centre.py:224` | S1 carries only the 450 kg R134a top-up; the 2,000 kg initial charge it states is charged nowhere. | 34 t over 25 y, 0.17 % of the IT-driven term. Model low. | yes |
| 4 | Battery cell, `bess.py:270`, `:677` | The Chinese cell factory's 68.4 MJ/kWh of gas is on RoW "heat, district or industrial, natural gas", ~85 % gas-CHP heat at 0.038 kg/MJ. Voß's own Chinese gas factor is 0.0785; an industrial furnace is 0.074. Reader confidence ~60 %. | Cell **2.5–2.8 kg CO2e/kWh low** (3.0–3.4 %). | partly |
| 5 | Battery cell, `bess.py:516` | FePO4 (Voß Table S32) is read per 0.91 kg of output; the inputs fit 1.00 kg, and only the per-kg reading reproduces Voß's own LFP-C (7.6) and cathode (17.0), while every other material reproduces as built. Reader confidence ~80 %. | Cell **0.56 kg/kWh high** (0.7 %); block 101.237 → 100.675. | yes |
| 6 | Battery, `dc_inputs.py:512-513`, `:534` | Jasper §2.4.6 gives 20 y for container, transformer, cables and controller (15 y for cells, cooling, inverter); everything is amortised over 15 y. Unrecorded. | `gwp_batt_e` 0.9–4.4 % high; container transformer 25 % high. Errs high. | no |
| 7 | Battery, `bess.py:967` | The HFC-227ea activity keeps Jasper's −0.1 kg tetrafluoroethylene avoided-product credit, against ASSUMPTIONS §5 "no credits anywhere"; the comment cites the SMR credit, dropped 22 Oct. | +209 kg per container, +0.07 % of the block. | yes |
| 8 | Electrolyser, `dc_model.py:674-681` | The `baseload` strategy forces an 85 % annual capacity factor. Three 50,000 h stacks cover 25 y only below ~68 %, so baseload runs under-charge stacks; the DATA_GAPS premise "the optimiser runs below 73 %" holds for `free`/`flexible` only. | Baseload runs: unit capital 10–21 % low. Default `free` runs unaffected unless they run above ~68 %. | yes |
| 9 | Electrolyser AE, `hydrogen.py:348`, `:660` | AE keeps the export's German electricity and RoW datasets for manufacture; PEM and SOEC were rebased. | AE unit +5.9 % (+48.7 t), +~0.8 % from materials. AE is not the default. | yes |
| 10 | Electrolyser SOEC, `hydrogen.py:463` | Praseodymium oxide is on the Pr–Nd oxide market; the reader reports "market for praseodymium oxide" exists in 3.9.1, against the `why` text. | +0.26 % of the SOEC unit. | no |
| 11 | Tank, `h2_storage.py` | The LP treats the full gross content at 28 bar as usable; no minimum (cushion) pressure is stated. | At a 2–5 bar minimum the tank coefficient rises 8–22 %. **Already on TODO.md as *Tank heel*** (Audit §3.3), not new. | no |
| 12 | Tank, 200 bar sensitivity | The 28 bar compressibility (Z = 1.017) is applied to the 200 bar design's pad. | +0.5 % on that sensitivity only. | no |
| 13 | Grid connection, `stepup_transformers.py:470-513` | The switchyard's nine Leng rows are transcribed correctly but score 394 t per 100 MW against Leng's own 2,157 t (18 %); the gap most likely sits in "site formation" (0.58 kg/m³ on hydraulic digging). The register (`exclusions.py:291`) and ASSUMPTIONS §8 print 539 kg/MW/yr while the coefficient charges 98.6. | If Leng's figure is right, `gwp_grid_per_mw` 286.9 → ~727; still under 0.1 % of the system. | yes |
| 14 | Grid connection, register | The flow "switchgear, protection and the bay" carries Teffera's switchgear mass only, not Table 5's HV civil-structure steel or grid-connection hardware. | +~17 kg/MW/yr (+6 % of the connection). | no |
| 15 | Wind step-ups, connection | Leng's intra-site transport (S2, 300 km) and the station's 3 km on-site leg are neither modelled nor recorded as boundary. | ~1.5 % of wind step-ups, ~0.7 % of the connection. | no |
| 16 | Wind step-ups | Leng's electrical installation scores 441 t per 100 MW against ~2.6 t for the four printed rows; probably unprinted cable. Unrecorded. | Mostly collection cabling, outside this inventory. | no |
| 17 | Solar, `upv.py` | Smith's A11 transformer pad (1.1 m³ concrete, 2,000 kg rebar) left out with the A11 transformer; whether the IEA station building covers it is unrecorded. | +0.26 % of solar. | no |
| 18 | Battery cell, `voss_de` | The German sensitivity cell omits Voß's sea and Europe legs (upstream, in scope). | 73.68 → 75.49 kg/kWh; default unaffected. | no |

### Outcome, 26 Oct 2026 (the user's decisions)

| # | Outcome |
|---|---|
| 1 | **Fixed.** IT-driven burden normalised by 5.38 MW (`data_centre.ZHANG_IT_MW`); 158,743 → 153,986 kg per MW IT per year. |
| 2 | **Not added (user).** Zhang does not disaggregate the cooling plant; taken as inside his rows. Recorded in ASSUMPTIONS §2. |
| 3 | **Not added (user)**, with 2: the 2,000 kg is S1's sizing note for the top-up, not an inventory row. |
| 4 | **Fixed 26 Oct (user).** The CN cell's factory gas is on Voß's Chinese dataset, "market for heat, central or small-scale, natural gas" RoW (main text p. 8114; ESI Tables S5, S31, S32). +2.77 kg/kWh on the cell. |
| 5 | **Fixed 26 Oct (user).** FePO4 read per 1.00 kg: S32's printed 0.91 output is S31's consumption copied; the inputs are stoichiometric for 1 kg (ESI p. 23, Eq. S25). LFP-C now 7.31 + Voß's legs = 7.63 vs his 7.6. −0.56 kg/kWh. |
| 6 | **Kept at 15 y (user)**, written down in DATA_GAPS (*Battery component lives*) until the cost side can take a 20-year system with mid-life replacements. |
| 7 | **Fixed.** Credit row deleted; block 101.237 → 101.306 kg per kWh nameplate. |
| 8 | **Fixed 26 Oct (user, option B).** Stacks charged as max(3 per 25 y, running hours ÷ 50,000), the fuel cell's rule; see docs/ELECTROLYSER_STACKS.md. |
| 9 | **Fixed 26 Oct (user: follow the article).** Gerloff §2: Europe first, Germany where possible, RoW/GLO only as fallback. Manufacturing electricity on DE LV for all three; AE's ten RoW materials to RER, SOEC's ABS to RER, tube insulation to DE in all three; zirconium oxide stays RoW (no European dataset). AE unit −0.8 %. |
| 10 | **Fixed.** `market for praseodymium oxide` GLO, as exported. |
| 11 | On TODO.md (*Tank heel*); no action. |
| 12 | **Closed (user).** Recorded in DATA_GAPS. |
| 13 | **Label fixed (user).** The register prints the charged 98.6 kg/MW/yr and states Leng's own 539 as not charged. |
| 14 | **Fixed.** New register entry, 289 kg/MW at 2.5–4.57 kg CO2e/kg over 40 y: +18.1 kg/MW/yr, carried. The switchgear entry renamed "switchgear and protection (MV + HV devices)". |
| 15 | **Recorded as boundary** (user: transport to site): register entry and TX_SCOPE. |
| 16 | **Recorded as an unsourced cut-off entry (user).** Central 0, upper 125 kg/MW/yr (0.5 % of wind): passes rules 1 and 2. Not added. |
| 17 | **Investigated, nothing to add.** IEA PVPS §3.7.2: the transformers are "housed in the central electrical building" (Z-PV-238 L13), whose ecoinvent hall carries 0.30 m³ concrete and 33 kg rebar per m², 1.2 m³ per MWp: the foundation is there. Smith's 2,000 kg of rebar per pad belongs to the rejected A11 bill. |
| 18 | **Fixed.** `voss_de` 73.677 → 75.495 kg per kWh. |

No carbon effect: solar A8 water entered in kg on an m³ flow (1,000× high,
`upv.py:834`); solar land counted twice (Smith and IEA); silica sand on China's
grid not Smith's four-country mix (<0.003 %); AE KOH on a NiMH-electrolyte dataset.

## Clean

Fuel cell (Usai Table 1, Babatunde S1: every row, every coefficient reproduces);
bought hydrogen (Hermesmann: grey 11.463, blue 3.711, MP-E 3.924 re-score; D1,
credits, 30 bar and the capture split as decided); solar transcription (251 Smith
rows, IEA rows); Gerloff transcription (64 AE, 60 PEM, 173 SOEC rows; stacks ×3;
Tables 3/4/6); Gandiglio tank line; Jasper container parts (re-score Fig. 4); Zhang
S1 rows (the driver split rebuilds exactly); Leng S1/S3 amounts and every
`exclusions.py` central/upper for transformers and switchgear.

## Stale documentation (numbers right in code)

- SOURCES.md: Gerloff capital 433.7/260.9/362.8 t (now 824.4/441.8/484.9); solar
  mounting 161.4 / total 908.1 (now 151.4 / 898.1); battery table at 21 Oct values;
  Zhang 24,896 t (now 25,106); fossil compression 0.451 kg/kg (now 0.1695); old
  battery boundary text (transport, graphite legs, transformer, foundation).
- Bought green 0.976/1.107 kg/kg in SOURCES, ASSUMPTIONS, DATA_GAPS and h2_prices
  (now 1.037/1.168).
- DATA_GAPS: SMR capture row still 8.01 kg and blue 5.15; T&S double count £3.60
  (now £4.31); battery 101.11/112.3 (now 101.237/112.49); the "three stacks errs
  high" premise (finding 8).
- ASSUMPTIONS §2 (facility exchange count, 963 t/yr, now 971.8); §6 step-up scope.
- `hydrogen.py:38-41` says non-AE electricity is the study grid (it is ecoinvent GB
  LV); platinum note 21.7 % (now 41.9 %); "Hermesmann" left in `coefficients.py:125`
  and `electrolysers.py`; `coefficients.py:146` attributes the stack life to Babatunde.
- `h2_tank.py` TANK_SCOPE says valves EXCLUDED (they are carried as an estimate);
  `h2_storage.py` says "Table 3", "steel only", and has an out-of-date battery
  comparison.
- `exclusions.py`: switchgear basis unlabelled (estimated-generation basis); SF6
  reason cites Vestas's end-of-life figure; Voß processing-materials entry cites
  §3.1.3 and omits process water.
