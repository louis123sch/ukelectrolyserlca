#!/bin/bash
# Before/after for the REopt comparison fixes (docs/REOPT_FIXES.md, 20 Nov 2026): solar's cost
# seeing discounted ageing, the off-grid spare-power rule, and three reporting fixes. On a login
# node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/fixcheck_reopt_setup.sh
# Makes two copies of ~/ukdclca: ~/fix-rbefore at 2a17552 (the commit just before the fixes,
# bought hydrogen already off by default) and ~/fix-reopt at the fixes. Submits, for each, at
# East Grinstead, the same pieces as the comparison-fixes run:
#   - pieces/fixcheck_cmp.txt (22 pieces, 4 cores and 16 GB each),
#   - the slow configurations 2, 3, 21 with 16 cores and 64 GB (pieces/fixcheck_slow_after.txt),
# and the whole test suite once on the fixes (tests.pbs). 2 x (22 x 4 + 3 x 16) + 4 = 276 cores
# at once, within Imperial's 500 per user.
# What to expect: grid configurations without solar match exactly; those with solar move a little
# (solar about 6 % cheaper per MWh); the islanded ones (10-15, 24, 25 and the islanded reference
# case) move most (spare power held off grid).
# Light work only on the login node: copies and checkouts; the solving is in the jobs.
set -e
BEFORE=2a17552
AFTER=origin/source-update
cd "$HOME/ukdclca"
for t in rbefore reopt; do
    if [ -e "$HOME/fix-$t" ]; then echo "$HOME/fix-$t already exists: remove it first"; exit 1; fi
done
for t in rbefore reopt; do
    rsync -a --exclude cluster_jobs --exclude 'optimisation_outputs/uk_sites_2025*' \
          --exclude 'optimisation_outputs/dc_runs' --exclude 'optimisation_outputs/sensitivity_*' \
          --exclude '*.o[0-9]*' "$HOME/ukdclca/" "$HOME/fix-$t/"
done
git -C "$HOME/fix-rbefore" checkout -q -f "$BEFORE"
git -C "$HOME/fix-reopt" checkout -q -f "$AFTER"
echo "before: $(git -C "$HOME/fix-rbefore" log --oneline -1)"
echo "after:  $(git -C "$HOME/fix-reopt" log --oneline -1)"
grep -q "reserve_battery_power" "$HOME/fix-reopt/optimisation/dc_model.py" \
    && ! grep -q "reserve_battery_power" "$HOME/fix-rbefore/optimisation/dc_model.py" \
    || { echo "the two copies are not before and after the REopt fixes: stop"; exit 1; }
N=$(grep -v '^\s*#' scripts/cluster/pieces/fixcheck_cmp.txt | grep -c .)
for t in rbefore reopt; do
    echo "$t fast pieces ($N, 4 cores): batch $(bash scripts/cluster/submit.sh -l select=1:ncpus=4:mem=16gb \
        -J 1-"$N" -v PIECES=fixcheck_cmp.txt,REPO="$HOME"/fix-$t scripts/cluster/batch.pbs)"
    echo "$t slow pieces (3, 16 cores): batch $(bash scripts/cluster/submit.sh -l select=1:ncpus=16:mem=64gb \
        -J 1-3 -v PIECES=fixcheck_slow_after.txt,REPO="$HOME"/fix-$t scripts/cluster/batch.pbs)"
done
echo "tests: job $(bash scripts/cluster/submit.sh -v REPO="$HOME"/fix-reopt scripts/cluster/tests.pbs)"
echo "check with: bash scripts/cluster/progress.sh <batch number>"
