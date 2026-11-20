#!/bin/bash
# Before/after for the comparison fixes (docs/COMPARISON_FIXES_PLAN.md stage 2, 20 Nov 2026):
# electrolyser stacks charged in cost, the 2026 electrolyser build, solar ageing. On a login
# node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/fixcheck_cmp_setup.sh
# Makes one more copy of ~/ukdclca, ~/fix-cmp, at the fixes, and submits at East Grinstead:
#   - pieces/fixcheck_cmp.txt (22 pieces, 4 cores and 16 GB each),
#   - the slow configurations 2, 3, 21 with 16 cores and 64 GB (pieces/fixcheck_slow_after.txt),
# 22 x 4 + 3 x 16 + 4 (tests) = 140 cores at once, within Imperial's 500 per user. More than the
# last run (2 and 8 cores; the slow three took over 1.5 h on 2): Gurobi takes Threads from NCPUS.
#   - the whole test suite as one job (tests.pbs).
# The "before" for this check is the fuel-cell fix run already in ~/fix-fc (5a1e262's model).
# Light work only on the login node: a copy and a checkout; the solving is in the jobs.
set -e
CMP=origin/source-update
cd "$HOME/ukdclca"
if [ -e "$HOME/fix-cmp" ]; then echo "$HOME/fix-cmp already exists: remove it first"; exit 1; fi
rsync -a --exclude cluster_jobs --exclude 'optimisation_outputs/uk_sites_2025*' \
      --exclude '*.o[0-9]*' "$HOME/ukdclca/" "$HOME/fix-cmp/"
git -C "$HOME/fix-cmp" checkout -q -f "$CMP"
echo "fix-cmp: $(git -C "$HOME/fix-cmp" log --oneline -1)"
grep -q "cost_ely_stack_per_mw" "$HOME/fix-cmp/optimisation/dc_model.py" \
    && grep -q "SOLAR_LIFE_AVERAGE_FACTOR" "$HOME/fix-cmp/optimisation/profiles.py" \
    || { echo "fix-cmp does not hold the comparison fixes: stop"; exit 1; }
N=$(grep -v '^\s*#' scripts/cluster/pieces/fixcheck_cmp.txt | grep -c .)
echo "fast pieces ($N, 4 cores): batch $(bash scripts/cluster/submit.sh -l select=1:ncpus=4:mem=16gb -J 1-"$N" \
    -v PIECES=fixcheck_cmp.txt,REPO="$HOME"/fix-cmp scripts/cluster/batch.pbs)"
echo "slow pieces (3, 16 cores): batch $(bash scripts/cluster/submit.sh -l select=1:ncpus=16:mem=64gb -J 1-3 \
    -v PIECES=fixcheck_slow_after.txt,REPO="$HOME"/fix-cmp scripts/cluster/batch.pbs)"
echo "tests: job $(bash scripts/cluster/submit.sh -v REPO="$HOME"/fix-cmp scripts/cluster/tests.pbs)"
echo "check with: bash scripts/cluster/progress.sh <batch number>"
