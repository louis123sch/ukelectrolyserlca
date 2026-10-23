### Rule 3 — the design-change test

The two reference cases re-solved at both anchors with every still-excluded flow added at its
upper estimate (`dc_inputs.build_tech(cutoff="upper")`, sensitivity knob `cutoff`), against the
central model. Q4's test: the same technologies are built and no built capacity moves by more than
5 %. Solved 23 Oct 2026; `optimisation_outputs/sensitivity_cutoff_*.csv`.

| Case | Anchor | Technologies built | Same with upper? | Largest capacity move | GWP t/yr, central → upper | Verdict |
|---|---|---|---|---|---|---|
| london_grid | min_cost | batt_e, batt_p, grid, solar, wind | yes | grid -0.0% | 108,904 → 109,096 | pass |
| london_grid | min_gwp | batt_e, batt_p, fc, grid, solar, wind | yes | grid +3.0% | 52,926 → 53,193 | pass |
| islanded_h2 | min_cost | batt_e, batt_p, ely, fc, solar, tank, wind | yes | batt_e +0.0% | 71,895 → 72,285 | pass |
| islanded_h2 | min_gwp | batt_e, batt_p, ely, fc, solar, tank, wind | yes | batt_e -1.1% | 63,828 → 64,148 | pass |

**Rule 3 passes**: at both anchors of both cases the upper-estimate run builds the same technologies and moves no capacity by more than 5 %.

The London case was solved with the grid connection at 282.0 kg CO2e per MW per year; the switchyard's
share of Leng's construction machinery (+4.85, carried since 22 Oct 2026) was added while it ran. At the
145 MW connection the minimum-cost design builds that is 0.7 t CO2e a year, under a millionth of the
system, so it cannot move a design. The islanded case has no grid connection.
