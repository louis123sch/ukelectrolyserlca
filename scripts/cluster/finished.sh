#!/bin/bash
# The finished pieces of cluster batches: what each ran, how long, how much memory, any error,
# and for 26-site pieces the frontier itself (scripts/cluster/show_piece.py). On a login node:
#   bash ~/ukdclca/scripts/cluster/finished.sh 8757 8930 8931
cd "$HOME/ukdclca" || exit 1
eval "$("$HOME/miniforge3/bin/conda" shell.bash hook)"
conda activate ukdclca
for JOB in "$@"; do
    for f in $(grep -l '^finished' *.o"$JOB".* 2>/dev/null | sort -t. -k3 -n); do
        echo "== $f"
        grep -m1 '^run:' "$f" | sed 's/^run: *python /   ran:     /'
        T=$(grep -m1 'Elapsed (wall clock)' "$f" | awk '{print $NF}')
        M=$(grep -m1 'Maximum resident' "$f" | awk '{printf "%.1f GB", $NF/1048576}')
        echo "   time:    $T   memory: $M"
        grep -m3 -e FAILED -e Error -e 'not_found' -e 'already_viable' -e 'found ' "$f" | sed 's/^/   note:    /'
        # 26-site pieces: print the answer.
        ARGS=$(grep -m1 '^run:' "$f")
        if echo "$ARGS" | grep -q uk_sites.py; then
            LEVEL=$(echo "$ARGS" | sed -n 's/.*--levels \([a-z]*\).*/\1/p')
            SITE=$(echo "$ARGS" | sed -n 's/.*--sites \([0-9]*\).*/\1/p')
            python scripts/cluster/show_piece.py "optimisation_outputs/uk_sites_2025_present/$LEVEL/$(printf %02d "$SITE")" 2>/dev/null | tail -n +2
        fi
    done
done
