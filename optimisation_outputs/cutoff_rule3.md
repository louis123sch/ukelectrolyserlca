### Rule 3 — the design-change test

The two reference cases re-solved at both anchors with every still-excluded flow added at its
upper estimate (`dc_inputs.build_tech(cutoff="upper")`, sensitivity knob `cutoff`), against the
central model. Q4's test: the same technologies are built and no built capacity moves by more than
5 %. Solved 2026-11-11; `optimisation_outputs/sensitivity_cutoff_*.csv`.

| Case | Anchor | Technologies built | Same with upper? | Largest capacity move | GWP t/yr, central → upper | Verdict |
|---|---|---|---|---|---|---|
| norfolk_grid_green | min_cost | batt_e, batt_p, fc, grid, solar, wind | yes | grid +0.0% | 55,761 → 55,997 | pass |
| norfolk_grid_green | min_gwp | batt_e, batt_p, ely, fc, grid, solar, tank, wind | yes | batt_e -3.5% | 44,305 → 44,592 | pass |
| islanded_h2 | min_cost | batt_e, batt_p, ely, fc, solar, tank, wind | yes | fc -0.0% | 61,672 → 62,022 | pass |
| islanded_h2 | min_gwp | batt_e, batt_p, ely, fc, solar, tank, wind | yes | ely +0.3% | 52,698 → 53,085 | pass |

**Rule 3 passes**: at both anchors of both cases the upper-estimate run builds the same technologies and moves no capacity by more than 5 %.

The islanded case has no grid connection.
