# Testing: the rig, then the sign-off

Agreed 5 Nov 2026. **Work on the 4-hour rig. Nothing is called passed, final or quotable until the full sign-off below has run on the committed code.**

## While working: the rig

Every sweep defaults to the whole of 2025 in 4-hour steps (`sensitivity.SWEEP_HOURS`), written to `sensitivity_<name>_4h.csv`. It stays a whole year because the tank works across seasons. Use it for anything still changing: trying an input, seeing whether a change matters, comparing options.

Measured against hourly on 5 Nov (`docs/COST_BEST_SOURCE_PLAN.md`, *The assumption sweep on the 4-hour rig*): about ten times faster, bill within 0.35 %, carbon within 0.7 %, the effect of a change within about 1 percentage point. Sizes do not carry over: up to 12.6 % on a main asset, 45 % on a small battery. So:

- Compare a rig row only with a rig central, never with an hourly figure.
- A rig result can say "this looks small" or "this looks worth chasing". It cannot pass the 5 % design test or give a size to quote.
- The fast tests for what you changed are enough while working: `python -m pytest tests/test_<area>.py -q`.

## To finish: the sign-off

Run it before a number goes to the supervisor or into a paper, and before calling a piece of the model done. Any change to the model, the cost inputs or the carbon inputs voids the last sign-off; changes to documents and pages do not.

From a committed tree, one at a time, in the `brightway` environment with `MKL_THREADING_LAYER=TBB`:

| # | Check | Command | Passes when |
|---|---|---|---|
| 1 | Clean tree | `git status` | model, inputs and scripts are all committed; note the commit |
| 2 | Every test | `python -m pytest tests -q` | none fail (about 11 minutes) |
| 3 | Connection's price, ±50 % | delete `optimisation_outputs/sensitivity_connection_norfolk_150_room.csv`, then `python -m optimisation.sensitivity connection norfolk_150_room --hours=1`, then `python scripts/connection_sensitivity.py` | every North Norfolk point passes (about 4.5 hours) |
| 4 | Cost cut-off, rule 3 | `python -m optimisation.sensitivity cost_cutoff --hours=1` | no built size moves by more than 5 %, no technology appears or goes |
| 5 | Carbon cut-off, rule 3 | `python -m optimisation.sensitivity cutoff --hours=1`, then `python scripts/cutoff_rule3.py` | the judge passes |
| 6 | Assumptions at their ranges | `python -m optimisation.sensitivity assumptions --hours=1` | no pass mark: every row is recorded, and any that moves the design is stated with the result |
| 7 | Carbon inputs at their ranges | `python -m optimisation.sensitivity carbon --hours=1` | only if carbon inputs changed since the last sign-off; recorded as in 6 |
| 8 | Both maps | `python scripts/build_lca_map.py`, `python scripts/build_cost_map.py`, then `python -m pytest tests/test_cost_map.py tests/test_lca_map.py -q`, then republish both | no problems listed, tests pass |

Then add a row to the log below, and quote figures only from those hourly files.

Allow a night for it, though only steps 2 and 3 have been timed since sweeps began fixing the price list. Run them one at a time, because memory will not hold two.

**Delete the file in step 3 first.** The connection sweep resumes by default, so it would otherwise keep rows solved on older code. The other sweeps start fresh.

**A failure** stops the sign-off for that result: fix it or state it, commit, and run again from step 2. A later step need not be repeated if the fix cannot reach it, and the log says why.

**Why hourly and not half-hourly.** The data are half-hourly, but every reported result has been hourly: the one measurement (`dc_inputs.resample`, London 2025) puts hourly within 0.14 % on cost and 0.32 % on carbon of half-hourly, at 3.5 times the speed.

**The gap.** With a choice of price lists the hourly central row is solved to a 0.1 % gap, which matched the tight answer to the pound on the London year. A figure that turns on less than 0.1 % needs `--lists=full`.

## Sign-off log

| Date | Commit | Result | Notes |
|---|---|---|---|
| none yet | | | The 5 Nov connection test passed hourly but started before that day's cost changes (major-hazard charge, new knobs), and the 5 Nov assumption sweep is rig only, so neither counts |
