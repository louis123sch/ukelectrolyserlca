#!/bin/bash
# Before/after check for the code-check fixes (docs/CODE_CHECK_FIX_PLAN.md step 5, 19 Nov 2026).
# On a login node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/fixcheck_setup.sh
# Makes two copies of ~/ukdclca with its data caches (results and job folders left out), puts one
# at the commit before the fixes and one at the fixes, and submits pieces/fixcheck_before.txt and
# fixcheck_after.txt: the laptop run of 19 Nov (reference cases + scenario list) on the cluster,
# at East Grinstead (scripts/cluster/fixcheck_site.py).
# Light work only on the login node: a copy and two checkouts; the solving is in the jobs.
set -e
BEFORE=c9cc1dc      # source-update just before the fixes
AFTER=origin/source-update   # the fixes (4a6184f) plus this check's job lists
cd "$HOME/ukdclca"
for t in before after; do
    if [ -e "$HOME/fix-$t" ]; then echo "$HOME/fix-$t already exists: remove it first"; exit 1; fi
done
for t in before after; do
    rsync -a --exclude cluster_jobs --exclude 'optimisation_outputs/uk_sites_2025*' \
          --exclude '*.o[0-9]*' "$HOME/ukdclca/" "$HOME/fix-$t/"
done
git -C "$HOME/fix-before" checkout -q -f "$BEFORE"
# the East Grinstead runner is newer than the before commit: the same file in both copies
cp scripts/cluster/fixcheck_site.py "$HOME/fix-before/scripts/cluster/"
git -C "$HOME/fix-after" checkout -q -f "$AFTER"
echo "before: $(git -C "$HOME/fix-before" log --oneline -1)"
echo "after:  $(git -C "$HOME/fix-after" log --oneline -1)"
for t in before after; do
    N=$(grep -v '^\s*#' scripts/cluster/pieces/fixcheck_$t.txt | grep -c .)
    echo "$t: $N pieces, batch $(bash scripts/cluster/submit.sh -J 1-"$N" -v PIECES=fixcheck_$t.txt,REPO="$HOME"/fix-$t scripts/cluster/batch.pbs)"
done
echo "check with: bash scripts/cluster/progress.sh <batch number>"
