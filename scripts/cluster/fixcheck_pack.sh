#!/bin/bash
# Progress of the East Grinstead before/after batches, and their results packed into one file to
# copy home. On a login node, after `git pull` in ~/ukdclca, with every batch number to report:
#   bash scripts/cluster/fixcheck_pack.sh 3033334 3033335                       # the code check
#   bash scripts/cluster/fixcheck_pack.sh 3033335 3034468 3034818 3034819 3034820   # + the stack fix
# It packs the results of every code copy that exists (~/fix-before, ~/fix-after, ~/fix-fc) and
# the job logs of the batches named. Then from the laptop:
#   scp -O ls1524@login.cx3.hpc.imperial.ac.uk:fixcheck_results.tgz <dest>
# and, after unpacking, python scripts/fixcheck_compare.py <dest> [--before after --after fc --fc-check].
[ $# -ge 1 ] || { echo "give the batch numbers"; exit 1; }
for b in "$@"; do bash "$HOME/ukdclca/scripts/cluster/progress.sh" "$b"; done
cd "$HOME" || exit 1
FILES=()
for t in before after fc; do
    for f in "fix-$t/optimisation_outputs/dc_runs/fixcheck_east_grinstead" fix-"$t"/optimisation_outputs/sensitivity_fixcheck_*.csv; do
        [ -e "$f" ] && FILES+=("$f")
    done
done
LOGS=()
for b in "$@"; do
    for f in ukdclca/batch.o"$b".* ukdclca/batch.o"$b" ukdclca/tests.o"$b"; do
        [ -e "$f" ] && LOGS+=("$f")
    done
done
tar czf fixcheck_results.tgz "${FILES[@]}" "${LOGS[@]}" 2>/dev/null
echo "packed $(tar tzf fixcheck_results.tgz | grep -c summary.json) configuration results, $(tar tzf fixcheck_results.tgz | grep -c 'sensitivity_fixcheck') reference-case files, ${#LOGS[@]} logs into ~/fixcheck_results.tgz ($(du -h fixcheck_results.tgz | cut -f1))"
