# Smith UPV rebuild - deferred issues

Parked deliberately, not forgotten. None can move the plant total (895.3 t CO2e/MWp, SOURCES.md) by
more than ~1 %. The same dropped rows are commented at the foot of each activity in
`optimiser_lca/upv.py`, where the inventory itself is written out.

**Re-checked 21 Oct 2026 against the PDF and the 3.9.1 biosphere.** The stated reasons below are
mostly wrong and are kept only as history: the "mangled-row-skipped" rows (A1, A4, A7, A8) print
cleanly in Smith's PDF — they are natural-resource flows (sand, process and cooling water) — and most
of the "unmatched" flow names exist in `ecoinvent-3.9.1-biosphere` under their current names
(`NMVOC, non-methane volatile organic compounds`, `Particulate Matter, < 2.5 um`, `AOX, Adsorbable
Organic Halogen`, `Copper ion`, `Iron ion`, `Zinc II`, `Sodium`, `Hydrochloric acid`, `Carbon
monoxide, from soil or biomass stock`, `Sand, unspecified`, `Water, unspecified natural origin`,
`Water, cooling, unspecified natural origin`). Every one of the 20 has **no** characterisation factor
under IPCC 2021 GWP100, now verified (CF4 = 7,380 and CO2 = 1 confirmed in the same lookup), so
"believed zero-GWP, not verified" is upgraded to verified. They remain deferred because they carry no
GWP, not because they cannot be matched; restore them before any non-carbon category is reported.

| table | issue | flow | detail | note | amount |
|---|---|---|---|---|---|
| A1 | mangled-row-skipped | sand, quartz |  | provider text came from another column | 100000.0 |
| A1 | mangled-row-skipped | Water, process and cooling, unspecified natu | gravel/sand quarry construction \| RoW | provider text came from another column | 133000.0 |
| A1 | mangled-row-skipped | Water, process, unspecified natural origin | heat production, heavy fuel oil, at industri | provider text came from another column | 971000.0 |
| A2 | unmatched-biosphere-flow | carbon monoxide, land transformation |  | believed zero-GWP, not verified | 0.00062 |
| A2 | unmatched-biosphere-flow | NMVOC, non-methane volatile organic compound |  | believed zero-GWP, not verified | 9.6e-05 |
| A3 | unmatched-biosphere-flow | AOX, adsorbable organic halogen as Cl |  | believed zero-GWP, not verified | 1.26e-05 |
| A3 | unmatched-biosphere-flow | copper, ion |  | believed zero-GWP, not verified | 1.02e-07 |
| A3 | unmatched-biosphere-flow | iron, ion |  | believed zero-GWP, not verified | 5.61e-06 |
| A3 | unmatched-biosphere-flow | sodium, ion |  | believed zero-GWP, not verified | 0.0338 |
| A3 | unmatched-biosphere-flow | zinc, ion |  | believed zero-GWP, not verified | 1.96e-06 |
| A4 | mangled-row-skipped | Water, cooling, unspecified natural origin |  | provider text came from another column | 2.33 |
| A5 | unmatched-biosphere-flow | AOX, adsorbable organic halogen as Cl |  | believed zero-GWP, not verified | 0.000501 |
| A5 | unmatched-biosphere-flow | copper, ion |  | believed zero-GWP, not verified | 6.05e-05 |
| A7 | mangled-row-skipped | Water, cooling, unspecified natural origin |  | provider text came from another column | 0.231 |
| A7 | unmatched-biosphere-flow | hydrogen chloride |  | believed zero-GWP, not verified | 0.000266 |
| A7 | unmatched-biosphere-flow | NMVOC, non-methane volatile organic compound |  | believed zero-GWP, not verified | 0.194 |
| A7 | unmatched-biosphere-flow | particulates, <2.5 μm |  | believed zero-GWP, not verified | 0.00266 |
| A8 | mangled-row-skipped | Water, cooling, unspecified natural origin |  | provider text came from another column | 0.0716 |
| A8 | unmatched-biosphere-flow | NMVOC, non-methane volatile organic compound |  | believed zero-GWP, not verified | 0.00806 |
| A9 | mangled-row-skipped | photovoltaic panel, single-Si wafer | module assembly VN-MY - RoW | provider text came from another column | 0.005 |
| A10 | sanity-check-wanted | concrete slab | market for concrete slab [RoW] | 1.1 m3 scores ~1,025 kg CO2e/m3, which looks high; 2.7% of t | 1.1 |

**21 entries.**

- `unmatched-biosphere-flow` - Smith uses ecoinvent v2 flow names (metal ions, AOX, NMVOC, CO). All believed to have a zero GWP100 characterisation factor; **not verified**.
- `mangled-row-skipped` - the transcription bled provider text into the amount cell and the recovered provider does not name the flow, so the row was dropped rather than guessed.
- `location-substituted` - Smith states a location that this activity does not have in ecoinvent 3.9.1 apos.
