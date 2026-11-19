#!/bin/bash
# Progress of the fix-plan before/after batches, and their results packed into one file to copy
# home. On a login node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/fixcheck_pack.sh 3033334 3033335
# Then from the laptop: scp -O ls1524@login.cx3.hpc.imperial.ac.uk:fixcheck_results.tgz <dest>
BEFORE=${1:?before batch number}
AFTER=${2:?after batch number}
for b in "$BEFORE" "$AFTER"; do bash "$HOME/ukdclca/scripts/cluster/progress.sh" "$b"; done
cd "$HOME" || exit 1
FILES=()
for t in before after; do
    for f in "fix-$t/optimisation_outputs/dc_runs/fixcheck_east_grinstead" fix-"$t"/optimisation_outputs/sensitivity_fixcheck_*.csv; do
        [ -e "$f" ] && FILES+=("$f")
    done
done
LOGS=(ukdclca/batch.o"$BEFORE".* ukdclca/batch.o"$AFTER".*)
tar czf fixcheck_results.tgz "${FILES[@]}" "${LOGS[@]}" 2>/dev/null
echo "packed $(tar tzf fixcheck_results.tgz | grep -c summary.json) configuration results, $(tar tzf fixcheck_results.tgz | grep -c 'sensitivity_fixcheck') reference-case files into ~/fixcheck_results.tgz ($(du -h fixcheck_results.tgz | cut -f1))"
