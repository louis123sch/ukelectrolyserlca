#!/bin/bash
# How far a batch (scripts/cluster/batch.pbs) has got, in plain counts. On a login node:
#   bash ~/ukdclca/scripts/cluster/progress.sh 8757
# From the laptop's terminal, in one go (asks for the college password):
#   ssh -t ls1524@login.cx3.hpc.imperial.ac.uk "bash -lc 'cd ukdclca && git pull -q && bash scripts/cluster/progress.sh 8757'"
JOB=${1:?give the batch number, e.g. 8757}
cd "$HOME/ukdclca" || exit 1
# Status of every piece: Q waiting, R running, X or F finished.
STATES=$(qstat -x -t "${JOB}[]" 2>/dev/null | awk -v j="$JOB" '$1 ~ "^"j"\\[[0-9]+\\]" {print $(NF-1)}')
TOTAL=$(echo "$STATES" | grep -c .)
echo "batch $JOB: $TOTAL pieces"
echo "  waiting:  $(echo "$STATES" | grep -cx Q)"
echo "  running:  $(echo "$STATES" | grep -cx R)"
echo "  finished: $(echo "$STATES" | grep -cxE 'X|F')"
# Each piece's log is <name>.o<batch>.<piece> (name: batch, checks, breakeven), written live in ~/ukdclca.
FAILED=$(grep -l -e 'FAILED' -e 'Traceback' *.o"${JOB}".* 2>/dev/null)
if [ -n "$FAILED" ]; then
    echo "  PIECES WITH ERRORS:"
    for f in $FAILED; do echo "    $f: $(grep -m1 -e FAILED -e Error "$f")"; done
else
    echo "  no errors so far"
fi
echo "  pieces whose log reached the end: $(grep -l "^finished" *.o"${JOB}".* 2>/dev/null | wc -l)"
