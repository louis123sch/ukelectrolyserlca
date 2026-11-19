#!/bin/bash
# Before/after for the fuel-cell stack interest fix (docs/FUEL_CELL_STACK_AND_EQUATIONS_PLAN.md
# step 6, 19 Nov 2026). On a login node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/fixcheck_fc_setup.sh
# Makes one more copy of ~/ukdclca, ~/fix-fc, at the fix, and submits at East Grinstead:
#   - pieces/fixcheck_fc.txt (22 pieces, 2 cores each, batch.pbs's default),
#   - the slow configurations 2, 3, 21 with 8 cores and 32 GB (pieces/fixcheck_slow_after.txt),
#   - the whole test suite as one job (tests.pbs).
# The "before" for this check is the code-check "after" run already in ~/fix-after.
# Light work only on the login node: a copy and a checkout; the solving is in the jobs.
set -e
FC=origin/source-update      # the stack fix (e30c83d) and the page and these scripts after it
cd "$HOME/ukdclca"
if [ -e "$HOME/fix-fc" ]; then echo "$HOME/fix-fc already exists: remove it first"; exit 1; fi
rsync -a --exclude cluster_jobs --exclude 'optimisation_outputs/uk_sites_2025*' \
      --exclude '*.o[0-9]*' "$HOME/ukdclca/" "$HOME/fix-fc/"
git -C "$HOME/fix-fc" checkout -q -f "$FC"
echo "fix-fc: $(git -C "$HOME/fix-fc" log --oneline -1)"
git -C "$HOME/fix-fc" log --oneline -8 | grep -q "Fuel-cell stack carries its interest" \
    || { echo "fix-fc is not at the stack fix: stop"; exit 1; }
N=$(grep -v '^\s*#' scripts/cluster/pieces/fixcheck_fc.txt | grep -c .)
echo "fast pieces ($N, 2 cores): batch $(bash scripts/cluster/submit.sh -J 1-"$N" \
    -v PIECES=fixcheck_fc.txt,REPO="$HOME"/fix-fc scripts/cluster/batch.pbs)"
echo "slow pieces (3, 8 cores): batch $(bash scripts/cluster/submit.sh -l select=1:ncpus=8:mem=32gb -J 1-3 \
    -v PIECES=fixcheck_slow_after.txt,REPO="$HOME"/fix-fc scripts/cluster/batch.pbs)"
echo "tests: job $(bash scripts/cluster/submit.sh -v REPO="$HOME"/fix-fc scripts/cluster/tests.pbs)"
echo "check with: bash scripts/cluster/progress.sh <batch number>"
