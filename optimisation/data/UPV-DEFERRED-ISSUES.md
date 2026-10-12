# Smith UPV rebuild - deferred issues

Parked deliberately, not forgotten. None can move the plant total (908.2 t CO2e/MWp) by more than ~1 %.

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
