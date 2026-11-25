#!/bin/bash
# Progress of the sell-off batches (sell_off_setup.sh) and their results packed into one file.
# On a login node, with every batch number to report:
#   bash scripts/cluster/sell_off_pack.sh 123456 123457 [123458]
# Then from the laptop, one password, through a .bat so the file arrives intact:
#   ssh ls1524@login.cx3.hpc.imperial.ac.uk "cat sell_off_results.tgz" > C:\...\sell_off_results_%RANDOM%.tgz
# Unpack into ukdclca, then: python scripts/fixed_choice_checks.py --summary --out sell_off_checks_2025
[ $# -ge 1 ] || { echo "give the batch numbers"; exit 1; }
for b in "$@"; do bash "$HOME/ukdclca/scripts/cluster/progress.sh" "$b"; done
cd "$HOME/ukdclca" || exit 1
FILES=()
for f in optimisation_outputs/sell_off_checks_2025 optimisation_outputs/sensitivity_cost_cutoff_eastgrinstead_*.csv \
         optimisation_outputs/sensitivity_cutoff_eastgrinstead_*.csv; do
    [ -e "$f" ] && FILES+=("$f")
done
LOGS=()
for b in "$@"; do
    for f in batch.o"$b".* batch.o"$b"; do [ -e "$f" ] && LOGS+=("$f"); done
done
tar czf "$HOME/sell_off_results.tgz" "${FILES[@]}" "${LOGS[@]}" 2>/dev/null
echo "packed $(tar tzf "$HOME/sell_off_results.tgz" | grep -c pareto.parquet) runs, ${#LOGS[@]} logs into ~/sell_off_results.tgz ($(du -h "$HOME/sell_off_results.tgz" | cut -f1))"
