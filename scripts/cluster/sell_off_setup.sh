#!/bin/bash
# Terlouw's sell-off for assets that outlive the data centre (docs/SELL_OFF_PLAN.md), 25 Nov 2026.
# Run only when the user has said so. For queue speed rather than solving speed (24 Nov lesson:
# every piece ran on one core whatever was asked, at most 4.4 GB): every piece gets one core, 6 GB
# and a short limit, one small piece per variant and level. One code copy, ~/ukdclca: the "before"
# is the old_lives variant of the same code, so no ~/fix-* copy is made.
#
# On a login node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/sell_off_setup.sh            # step A (before/after) and B (resale x0.5/x1.5): 12 pieces
#   bash scripts/cluster/sell_off_setup.sh signoff    # the same, plus step C: sign-off steps 4-5 at East Grinstead
#   bash scripts/cluster/sell_off_setup.sh robustness # the robustness set on the new rule (136 pieces), on its own
#   bash scripts/cluster/sell_off_setup.sh maprun     # one East Grinstead full-grid run with the hourly operation
#                                                     # saved, for the maps, workbooks and explainer (26 Nov)
# The "before" is the old central runs at site 23 (uk_sites_2025_checks_none/central, made on 9893e62
# off grid and e469668 on the grid; nothing but the sell-off changed since), so the old_lives pieces
# of sell_off_eg.txt (lines 4-6, sub-jobs [4]-[6] of batch 26510) were cancelled as duplicates.
# Step D (re-running the 26 sites, robustness, near-optimal, +25 % grid price on the new rule) is the
# user's choice and needs fresh output folders; it is not submitted here.
# Progress: bash scripts/cluster/progress.sh <batch>. Collect: bash scripts/cluster/sell_off_pack.sh <batches>.
set -e
cd "$HOME/ukdclca"
echo "ukdclca: $(git log --oneline -1)"
if ! { [ -f optimisation/lives.py ] && grep -q '"old_lives"' scripts/fixed_choice_checks.py \
        && grep -q -- '"--out"' scripts/fixed_choice_checks.py; }; then
    echo "~/ukdclca does not hold the sell-off: git pull first. Nothing submitted."; exit 1
fi
if ! git diff --quiet HEAD -- optimisation optimiser_lca dc_config.py scripts; then
    echo "~/ukdclca has uncommitted changes to the model or scripts. Nothing submitted."; exit 1
fi
sub() {  # name, pieces file, cores, memory, hours
    local n
    n=$(grep -v '^\s*#' "scripts/cluster/pieces/$2" | grep -c .)
    echo "$1 ($n pieces, $3 core, $4, $5 h): batch $(bash scripts/cluster/submit.sh \
        -l select=1:ncpus="$3":mem="$4" -l walltime="$5":00:00 -J 1-"$n" \
        -v PIECES="$2",REPO="$HOME"/ukdclca scripts/cluster/batch.pbs)"
}
# Limits from the 24 Nov logs: East Grinstead checks at most 138 min (full grid), 72 min off grid.
if [ "${1:-}" = robustness ]; then
    # Added 25 Nov 2026, after A-C were submitted: the robustness set on the new rule, into the
    # same folder, without A's central or B's resale pieces (those run already).
    sub "robustness on the sell-off, East Grinstead" sell_off_robustness_eg.txt 1 6gb 4
    exit 0
fi
if [ "${1:-}" = maprun ]; then
    # Added 26 Nov 2026: the check runs above save no hourly operation, which the maps need.
    # Full-grid site runs took up to ~3 h on one core on 24 Nov; 8 h leaves room.
    if [ -d optimisation_outputs/uk_sites_2025_sell_off ]; then
        echo "optimisation_outputs/uk_sites_2025_sell_off already exists: move it aside first. Nothing submitted."; exit 1
    fi
    sub "East Grinstead full grid, hourly operation saved" sell_off_maprun_eg.txt 1 6gb 8
    exit 0
fi
if [ -d optimisation_outputs/sell_off_checks_2025 ]; then
    echo "optimisation_outputs/sell_off_checks_2025 already exists: move it aside first. Nothing submitted."; exit 1
fi
sub "A: sell-off before/after, East Grinstead"      sell_off_eg.txt         1 6gb 4
sub "B: resale share x0.5 / x1.5, East Grinstead"   sell_off_resale_eg.txt  1 6gb 4
if [ "${1:-}" = signoff ]; then
    sub "C: sign-off steps 4-5, East Grinstead"    weekend_signoff.txt     1 6gb 12
fi
sleep 5
qstat -u "$USER" | tail -n +4 | awk '{print $1, $(NF-1)}' | sort -k2 | uniq -c -f1 | head
