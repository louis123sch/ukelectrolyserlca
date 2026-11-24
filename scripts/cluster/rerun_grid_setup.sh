#!/bin/bash
# The grid re-run, 24 Nov 2026. Grid gas is now scored at the 2025 fleet's efficiency
# (optimiser_lca/gb_gas_fleet.py), which raises the carbon of every grid MWh. Off-grid pieces use no
# grid power and are unchanged; every grid-connected piece is re-run on the new code. On a login node,
# after `git pull` in ~/ukdclca:
#   bash scripts/cluster/rerun_grid_setup.sh
# 1. cancels the weekend batches still running on the old code (15444 26 sites, 15445 robustness);
# 2. makes ~/wk2, a copy of ~/ukdclca at origin/source-update with its data caches and none of its
#    old results, and submits there: the grid pieces of the 26-site study and of the East Grinstead
#    robustness, the one grid sign-off check with two off-grid pieces as a check, and the test suite;
# 3. resubmits the off-grid pieces in ~/wk (commit 9893e62), where finished ones skip themselves.
# Light work only on the login node: a copy and a checkout; the solving is in the jobs.
set -e
cd "$HOME/ukdclca"
qdel '15444[]' '15445[]' 2>/dev/null && echo "cancelled 15444 and 15445" || echo "15444/15445 not running"
if [ -e "$HOME/wk2" ]; then echo "$HOME/wk2 already exists: remove it first"; exit 1; fi
rsync -a --exclude cluster_jobs --exclude 'optimisation_outputs/uk_sites_2025*' \
      --exclude 'optimisation_outputs/dc_runs' --exclude 'optimisation_outputs/sensitivity_*' \
      --exclude 'optimisation_outputs/signoff' --exclude '*.o[0-9]*' "$HOME/ukdclca/" "$HOME/wk2/"
git -C "$HOME/wk2" checkout -q -f origin/source-update
echo "wk2: $(git -C "$HOME/wk2" log --oneline -1)"
[ -f "$HOME/wk2/optimiser_lca/gb_gas_fleet.py" ] || { echo "~/wk2 does not hold the gas fix: stop"; exit 1; }
echo "wk:  $(git -C "$HOME/wk" log --oneline -1)"
sub() {  # name, pieces file, cores, memory, hours, repo
    local n
    n=$(grep -v '^\s*#' "scripts/cluster/pieces/$2" | grep -c .)
    echo "$1 ($n pieces, $3 cores): batch $(bash scripts/cluster/submit.sh \
        -l select=1:ncpus="$3":mem="$4" -l walltime="$5":00:00 -J 1-"$n" \
        -v PIECES="$2",REPO="$6" scripts/cluster/batch.pbs)"
}
sub "26 sites, grid, new code"       rerun_grid_sites.txt            2 8gb 8 "$HOME/wk2"
sub "robustness, grid, new code"     rerun_grid_robustness_eg.txt    2 8gb 6 "$HOME/wk2"
sub "sign-off and off-grid check, new code" rerun_checks.txt     8 32gb 12 "$HOME/wk2"
echo "tests, new code: job $(bash scripts/cluster/submit.sh -v REPO="$HOME"/wk2 scripts/cluster/tests.pbs)"
sub "26 sites, off-grid, old code"   finish_offgrid_sites.txt        2 8gb 8 "$HOME/wk"
sub "robustness, off-grid, old code" finish_offgrid_robustness_eg.txt 2 8gb 6 "$HOME/wk"
sleep 20
qstat -u "$USER"
