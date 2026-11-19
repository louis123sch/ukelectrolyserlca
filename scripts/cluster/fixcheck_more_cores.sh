#!/bin/bash
# The fix-plan before/after check's slowest configurations (2, 3, 21) again with 8 cores and 32 GB
# each, alongside the 1-2 core originals (user, 19 Nov 2026); whichever copy finishes first answers.
# A configuration already finished is read from its saved result and returns at once.
#   bash scripts/cluster/fixcheck_more_cores.sh
set -e
cd "$HOME/ukdclca"
for t in before after; do
    echo "$t: batch $(bash scripts/cluster/submit.sh -l select=1:ncpus=8:mem=32gb -J 1-3 \
        -v PIECES=fixcheck_slow_$t.txt,REPO="$HOME"/fix-$t scripts/cluster/batch.pbs)"
done
