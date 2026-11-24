#!/bin/bash
# Two extra checks at East Grinstead, 24 Nov 2026, run in ~/ukdclca itself (pulled to the commit that
# adds them; neither resumes from an old result, since both write folders no earlier run made):
#   pieces/grid_price_eg.txt    2 pieces: the +25 % grid price case, 25 MW and full grid
#   pieces/near_optimal_eg.txt 15 pieces: battery and hydrogen size ranges within 1 % of the lowest
#                              carbon, one size and level a piece
# On a login node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/extra_checks_setup.sh
set -e
cd "$HOME/ukdclca"
echo "ukdclca: $(git log --oneline -1)"
grep -q "grid_price_scale" optimisation/dc_inputs.py && [ -f optimisation/near_optimal.py ] \
    || { echo "~/ukdclca does not hold the extra checks: stop"; exit 1; }
sub() {  # name, pieces file, cores, memory, hours
    local n
    n=$(grep -v '^\s*#' "scripts/cluster/pieces/$2" | grep -c .)
    echo "$1 ($n pieces, $3 cores): batch $(bash scripts/cluster/submit.sh \
        -l select=1:ncpus="$3":mem="$4" -l walltime="$5":00:00 -J 1-"$n" \
        -v PIECES="$2",REPO="$HOME"/ukdclca scripts/cluster/batch.pbs)"
}
# One core, short limits: every piece in the weekend logs ran on one core whatever was asked for.
sub "grid price +25 %, East Grinstead"     grid_price_eg.txt    1 6gb 4
sub "near-optimal range, East Grinstead"   near_optimal_eg.txt  1 6gb 6
