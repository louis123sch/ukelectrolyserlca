### Rule 3 — the design-change test

The two reference cases re-solved at both anchors with every still-excluded flow added at its
upper estimate (`dc_inputs.build_tech(cutoff="upper")`, sensitivity knob `cutoff`), against the
central model. Q4's test: the same technologies are built and no built capacity moves by more than
5 %, counting only assets that are at least 1 % of the design's supply carbon or cost (the size
floor, 12 Nov 2026: a smaller asset's size is not a stable result). Solved 2026-11-13; `optimisation_outputs/sensitivity_cutoff_*.csv`.

| Case | Anchor | Technologies built | Same with upper? | Largest capacity move | GWP t/yr, central → upper | Verdict |
|---|---|---|---|---|---|---|
| norfolk_grid_green | min_cost | batt_e, batt_p, ge, grid, solar, wind | yes | solar +0.0% | 222,412 → 222,594 | pass |
| norfolk_grid_green | min_gwp | batt_e, batt_p, ely, fc, grid, solar, tank, wind | yes | solar +1.2% (below floor: batt_e +5.8%) | 45,221 → 45,517 | pass |
| islanded_h2 | min_cost | batt_e, batt_p, ely, fc, solar, tank, wind | yes | batt_p +0.0% | 62,534 → 62,885 | pass |
| islanded_h2 | min_gwp | batt_e, batt_p, ely, fc, solar, tank, wind | yes | batt_e +14.2% (below floor: batt_p +14.2%) | 51,966 → 52,348 | FAIL |

**Rule 3 fails** on at least one case; the flows that drive the change are to be included (step 5).

The islanded case has no grid connection.
