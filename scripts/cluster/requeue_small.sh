#!/bin/bash
# Resubmit a batch's waiting pieces as small jobs, for queue speed (24 Nov 2026). On a login node:
#   bash scripts/cluster/requeue_small.sh BATCH PIECES REPO MEM HOURS
# e.g. bash scripts/cluster/requeue_small.sh 16878 rerun_grid_sites.txt $HOME/wk2 6gb 8
# Pieces already running keep going. Each piece still waiting (Q) or held (H) is cancelled and its line
# is written, in order, to pieces/requeue_<BATCH>.txt (on the cluster only), which is submitted as a new
# array at one core: every piece in the weekend logs ran on one core whatever was asked for, and small
# requests fit gaps in the queue. MEM and HOURS from the weekend logs: at most 4.4 GB, 138 minutes for a
# robustness piece at full grid.
set -e
JOB=${1:?batch number}; LIST=${2:?pieces file}; REPO=${3:?repo}; MEM=${4:?memory, e.g. 6gb}; HOURS=${5:?hours}
cd "$HOME/ukdclca"
SRC="scripts/cluster/pieces/$LIST"
[ -f "$SRC" ] || { echo "no $SRC"; exit 1; }
# Waiting or held sub-jobs, by index ("16878[5].pbs-8 ... Q ...").
IDX=$(qstat -t "${JOB}[]" 2>/dev/null | awk -v j="$JOB" '$1 ~ "^"j"\\[[0-9]+\\]" && ($(NF-1)=="Q" || $(NF-1)=="H") {
          s=$1; sub(/^[0-9]+\[/, "", s); sub(/\].*/, "", s); print s}' | sort -n)
N=$(echo "$IDX" | grep -c . || true)
if [ "$N" -eq 0 ]; then echo "batch $JOB: nothing waiting"; exit 0; fi
OUT="scripts/cluster/pieces/requeue_${JOB}.txt"
{ echo "# Waiting pieces of batch $JOB ($LIST), resubmitted small on $(date)"
  for i in $IDX; do grep -v '^\s*#' "$SRC" | grep -v '^\s*$' | sed -n "${i}p"; done; } > "$OUT"
[ "$(grep -v '^\s*#' "$OUT" | grep -c .)" -eq "$N" ] || { echo "batch $JOB: list mismatch, nothing cancelled"; exit 1; }
# An array needs at least two pieces: a lone piece gets a harmless second line (its script's --help).
if [ "$N" -eq 1 ]; then echo "$(grep -v '^\s*#' "$OUT" | head -1 | awk '{print $1}') --help" >> "$OUT"; ARR=2; else ARR=$N; fi
qdel $(for i in $IDX; do echo "${JOB}[$i]"; done) 2>/dev/null || true
sleep 3
echo "batch $JOB: $N waiting pieces -> batch $(bash scripts/cluster/submit.sh \
    -l select=1:ncpus=1:mem="$MEM" -l walltime="$HOURS":00:00 -J 1-"$ARR" \
    -v PIECES="requeue_${JOB}.txt",REPO="$REPO" scripts/cluster/batch.pbs) (1 core, $MEM, ${HOURS} h)"
