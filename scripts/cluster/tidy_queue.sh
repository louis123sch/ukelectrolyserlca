#!/bin/bash
# Cancel old job arrays that are only leftovers (26 Nov 2026). For each array number given: show how
# many of its pieces are waiting / running / finished, then cancel the array if NONE is running.
# One with a running piece is left alone and reported, so nothing live is killed by mistake.
#   bash scripts/cluster/tidy_queue.sh 3054377 16880 16881 16883 16884
for b in "$@"; do
    st=$(qstat -t "${b}[]" 2>/dev/null | awk 'NR>2 && $1 ~ /\[[0-9]+\]/ {print $5}' | sort | uniq -c | tr '\n' ' ')
    if [ -z "$(qstat "${b}[]" 2>/dev/null | tail -n +3)" ]; then
        echo "batch $b: no longer in the queue"
    elif qstat -t "${b}[]" 2>/dev/null | awk 'NR>2 && $1 ~ /\[[0-9]+\]/ && $5 == "R"' | grep -q .; then
        echo "batch $b: pieces by state: $st- something is RUNNING, left alone"
    else
        qdel "${b}[]" && echo "batch $b: pieces by state: ${st:-none listed} - cancelled"
    fi
done
