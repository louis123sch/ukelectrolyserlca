# Authoritative non-UK-government sources for the cost gaps — 4 Nov 2026

**Nothing here is applied.** UK government sources stay first (the rule of 4 Nov); these are for where none exists or where the UK figure does not make sense. Pound figures use the study's FES rate (£1 = €1.17 = $1.2815) with **no inflation added**, so they sit in each source's price year. Read by two research agents; marked ✓ where I also opened the file myself.

## APIs and machine-readable data, tested live 4 Nov

| Service | Access | Holds | Use |
|---|---|---|---|
| **NREL Annual Technology Baseline** ✓ `oedi-data-lake.s3.amazonaws.com/ATB/electricity/parquet/2025/v1.0.0/ATBe.parquet` (and `csv/`) | No key; file store, updated Sep 2026 | Battery 2–10 h, wind and solar, capital parts, O&M | Battery; grid connection share |
| **Corine land cover** `image.discomap.eea.europa.eu/arcgis/rest/services/Corine/CLC2018_WM/MapServer/0/query` | No key | Land type at a point | Per-site land |
| **Global Wind Atlas** `globalwindatlas.info/api/gis/country/GBR/wind-speed/100` | No key; GeoTIFF | Wind resource, not land | Cross-check on wind |
| **Overpass** (OpenStreetMap) ✓ | No key; was at capacity for one query | Land use, buildings | Per-site land |
| **European Central Bank** ✓ `data-api.ecb.europa.eu/service/data/EXR/A.GBP.EUR.SP00.A` | No key | £/€ by year | Converting |
| **World Bank** ✓ `api.worldbank.org/v2/country/USA/indicator/NY.GDP.DEFL.ZS` | No key | US deflator | Inflating US figures |
| **Eurostat** ✓ `.../statistics/1.0/data/nrg_pc_205_c?geo=UK` | No key | UK price parts to 2019 only; no margin | Little |
| **IRENASTAT** ✓ `pxweb.irena.org/api/v1/en/IRENASTAT` | No key | Capacity, generation, public finance; no costs | None |
| EIA, Ember APIs ✓ | Free key, not requested | US energy outlook; electricity data, not battery prices | Little |
| EU research data catalogue | Refused this connection | ENSPRESO's own page; its direct download works | |

**Downloads, not APIs:** Danish Energy Agency workbooks ✓; JRC ENSPRESO (CC BY 4.0) ✓; PNNL database (xlsx).

## By gap

| Gap | Now | Best source found | Figure | Catch |
|---|---|---|---|---|
| **Area limit** | None | JRC ENSPRESO 1 ✓ (`jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/ENSPRESO/`) | Inner London wind 0 GW ✓ at every restriction level; outer London at most 0.017 ✓; London ground solar 0.42 / 0.84 ✓ / 1.48 GW, which the solar sheet's old code UKI2 suggests is Outer London, with Inner London zero (corrected: reported first as inner London); UK wind 166–436 GW ✓ | 2030 basis, regional not per site. ENSPRESO 2 has no UK rows. Solar sheet uses old codes |
| **Solid-oxide** | £4,945/kWe by ratio | Danish Energy Agency Renewable Fuels ✓ (DNV, Aug 2026), `ens.dk/media/6444/download`, sheet 80 SOEC 10 MW | €2,959/kW (2,851–3,067) = **£2,529**; stack every 25,000 h; fixed 7 % (4–10) without stack; 20 y | Price year to confirm (agent read 2025 €). Foreign government; NESO cites this agency |
| **Stack life** | 30,000 h, 10 y (corrected: first reported as 80,000 h, which is the rest of the system) | STAYERS; PNNL; NLR; Clean Hydrogen Partnership; DOE record 11014 | Over 20,000 h actual, over 40,000 extrapolated; 40,000 expected; 25,000 (vehicle); about 50,000 derived; 80,000 is DOE's natural-gas target for other cell types | No field hours for hydrogen-fed MW plant. The model's 30,000 h sits inside the 20,000–40,000 h bracket, so it stands. The rest of the system's 80,000 h is the weak one |
| **Stack share** | 45.4 % | Clean Hydrogen Partnership Table 21; NLR; Battelle | €400 of €1,900, 21 %; NLR module 17 %, refit 11 %; Battelle 22–41 % | Smaller units; all well below 45 % |
| **Fuel cell capital** | £2,215/kW (UK) | NLR, PNNL, Danish, Clean Hydrogen | $1,352 = £1,055 (2022 $, 100 MW, all-in); $1,320 = £1,030 + inverter; €1,380 = £1,179 (0.1 MW); €1,900 = £1,624 (no power conversion) | All below the UK figure; NLR says a data-centre build costs more |
| **Fuel cell running** | £69/kW/yr | Danish; PNNL | 5 %/yr; $37.60/kW/yr with tax and insurance | Danish partly expert opinion |
| **Tank** | £599/kg | Danish Energy Storage catalogue; Clean Hydrogen; NREL | €638 + €319 install = €957/kg = £818 (200 bar, 0.5 t); €600–750 (with compression); $623 at 172 bar | Confirms the size. **Nothing for 28 bar at bulk scale** |
| **Tank running** | 2.97 % (UK) | Danish | 0.4 % tank, 0.87 % system | Racks |
| **Compressor** | None | Danish | €5,320/kW for a 100 kW unit, near atmospheric to 200 bar; €43–47/kW of electrolyser, 30 to 80 bar | No 1 to 30 bar figure |
| **Battery, 7 h** | £1,379/kW (UK) | See below | | |
| **Battery scope** | Unknown | NREL TP-93281; IRENA 2025 Fig 9.3 | NREL includes transformer, substation, line, developer costs. **IRENA UK shares:** modules 53 %, power conversion 13.1 %, land and permitting 3.5 % | Chart vectors |
| **Insurance, tax** | Wind's ratio, 0.23 % | DOE H2A rules; NREL ATB | 2 %/yr; ATB carries them inside fixed O&M | US, old rule |
| **Supplier margin** | £4.19/MWh | EDF's Ofgem-required statement | £4.35 (2024), £6.12/MWh (2025), non-domestic | Company filing; small business mixed in. Supports the figure |
| **Generation's grid connection** | Inside capital | NREL ATB; IRENA | Wind 5.2 %, solar 11.9 % of capital (US); UK solar 9.9 % as an upper bound | Export part alone not split |

**Battery at the 7 h built (£/kW):**

| Source | £/kW | Basis |
|---|---|---|
| Ember, Oct 2025 | ~683 | $125/kWh, 4 h and up, outside China and US |
| IRENA / BNEF 2025 | ~765 | $140/kWh at 4 h, world |
| Modo-based (low case) | 1,008 | 2025 £ |
| **BEIS 2022 (central)** | **1,379** | 2025 £ |
| Danish Energy Agency | ~1,486 | 2020 €, my sum of its parts |
| NREL ATB 2025 ✓ | ~1,560 | 2023 $, 2026 all-in: 2 h $908, 4 h $1,344, 10 h $2,655 |

So central sits inside the range, with the cheapest figures from the most recent global sources. There is no recent UK figure.

## Not reached
nrel.gov (Transportation ATB); Argonne's HDSAM; Papadias and Ahluwalia 2021 full text; DEA battery workbook; ACER and CEER non-household mark-ups; UKCEH land cover API.
