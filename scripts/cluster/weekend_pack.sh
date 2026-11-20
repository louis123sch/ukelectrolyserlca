#!/bin/bash
# Progress of the weekend run's batches, and its results packed into one file to copy home.
# On a login node, after `git pull` in ~/ukdclca, with the batch numbers weekend_setup.sh printed:
#   bash scripts/cluster/weekend_pack.sh <sites> <signoff> <tests job> <robustness> <break-even>
# Packs ~/wk's results (the three 26-site sets, the robustness checks, break-even, the sign-off
# sweeps) and the tests job's log into ~/weekend_results.tgz. From the laptop, one password:
#   ssh <host> "bash -lc 'bash ~/ukdclca/scripts/cluster/weekend_pack.sh ... >&2 ; cat ~/weekend_results.tgz'" > <dest>.tgz
[ $# -ge 1 ] || { echo "give the batch numbers"; exit 1; }
for b in "$@"; do bash "$HOME/ukdclca/scripts/cluster/progress.sh" "$b" 2>/dev/null; done
cd "$HOME" || exit 1
FILES=()
for f in wk/optimisation_outputs/uk_sites_2025_central wk/optimisation_outputs/uk_sites_2025_present \
         wk/optimisation_outputs/uk_sites_2025_present_steady wk/optimisation_outputs/uk_sites_2025_checks_none \
         wk/optimisation_outputs/uk_sites_2025_breakeven_h2_chain wk/optimisation_outputs/sensitivity_*eastgrinstead*; do
    [ -e "$f" ] && FILES+=("$f")
done
for b in "$@"; do
    for f in ukdclca/tests.o"$b" ukdclca/batch.o"$b"*; do [ -e "$f" ] && FILES+=("$f"); done
done
tar czf weekend_results.tgz "${FILES[@]}" 2>/dev/null
echo "packed $(tar tzf weekend_results.tgz | grep -c pareto.parquet) frontiers, $(tar tzf weekend_results.tgz | grep -c result.json) break-even results, $(tar tzf weekend_results.tgz | grep -c 'sensitivity_') sign-off files into ~/weekend_results.tgz ($(du -h weekend_results.tgz | cut -f1))"
