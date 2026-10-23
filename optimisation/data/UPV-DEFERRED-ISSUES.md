# UPV deferred rows — closed 22 Oct 2026

The twenty rows this file once listed as "mangled" or "not verified" were
re-read against Smith's PDF on 22 Oct 2026 (`docs/source_ledgers/smith_2024.md`):
all print cleanly and all carry zero GWP100. Under the study's cut-off principle
(a sourced in-boundary row is in whatever its size) the nineteen real rows are
now in `optimiser_lca/upv.py` under their ecoinvent 3.9.1 names, each flow's
`why` naming Smith's v2 name:

| Smith name | 3.9.1 flow | Tables |
|---|---|---|
| sand, quartz (resource) | Sand, unspecified (natural resource, in ground) — a stated proxy | A1 |
| Water, process (and cooling), unspecified natural origin | Water, unspecified natural origin | A1 |
| Water, cooling, unspecified natural origin | the same name | A4, A7, A8 |
| carbon monoxide, land transformation | Carbon monoxide, from soil or biomass stock | A2 |
| NMVOC, …, unspecified origin | NMVOC, non-methane volatile organic compounds | A2, A7, A8 |
| AOX, adsorbable organic halogen as Cl | AOX, Adsorbable Organic Halogen (water) | A3, A5 |
| copper / iron / sodium / zinc, ion | Copper ion / Iron ion / Sodium I / Zinc II (water) | A3, A5 |
| hydrogen chloride | Hydrochloric acid (air) | A7 |
| particulates, <2.5 μm | Particulate Matter, < 2.5 um (air) | A7 |

The twentieth, A9's photovoltaic panel row, is out by substitution (the tracker
table is replaced whole by the IEA PVPS mounting), not by deferral. The
concrete-slab note (A10, ~1,025 kg CO₂e/m³, 2.7 % of the inverter) stands as a
remark on a row that is in.
