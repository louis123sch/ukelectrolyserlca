#!/bin/bash
# The weekend run, 20-23 Nov 2026: everything for the final model in one go. On a login node,
# after `git pull` in ~/ukdclca:
#   bash scripts/cluster/weekend_setup.sh
# Makes ~/wk, a copy of ~/ukdclca at origin/source-update with its data caches but none of its old
# results (so nothing resumes from an older model), and submits, most important first:
#   1. pieces/weekend_sites.txt       231 pieces, 8 cores, 32 GB, 12 h: the 26-site study, three
#                                     buying settings (central = none bought, pipeline, truck)
#   2. pieces/weekend_signoff.txt       4 pieces, 8 cores, 32 GB, 12 h: sign-off steps 4 and 5
#   3. the whole test suite on ~/wk (tests.pbs): sign-off step 2
#   4. pieces/weekend_robustness.txt  556 pieces, 4 cores, 16 GB, 8 h: robustness at sites 2, 15, 18, 23
#   5. pieces/weekend_breakeven.txt   154 pieces, 4 cores, 16 GB, 12 h: break-even with buying off
# Far more than Imperial's 500 cores per user at once: the scheduler holds the rest and starts
# them as cores free up. Arrays stay under 10,000 pieces and every folder under 10,000 files.
# Light work only on the login node: a copy and a checkout; the solving is in the jobs.
set -e
cd "$HOME/ukdclca"
if [ -e "$HOME/wk" ]; then echo "$HOME/wk already exists: remove it first"; exit 1; fi
rsync -a --exclude cluster_jobs --exclude 'optimisation_outputs/uk_sites_2025*' \
      --exclude 'optimisation_outputs/dc_runs' --exclude 'optimisation_outputs/sensitivity_*' \
      --exclude 'optimisation_outputs/signoff' --exclude '*.o[0-9]*' "$HOME/ukdclca/" "$HOME/wk/"
git -C "$HOME/wk" checkout -q -f origin/source-update
echo "wk: $(git -C "$HOME/wk" log --oneline -1)"
grep -q '"central"' "$HOME/wk/scripts/uk_sites.py" && grep -q "reserve_battery_power" "$HOME/wk/optimisation/dc_model.py" \
    || { echo "~/wk does not hold the weekend code: stop"; exit 1; }
sub() {  # name, pieces file, cores, memory, hours
    local n
    n=$(grep -v '^\s*#' "scripts/cluster/pieces/$2" | grep -c .)
    echo "$1 ($n pieces, $3 cores): batch $(bash scripts/cluster/submit.sh \
        -l select=1:ncpus="$3":mem="$4" -l walltime="$5":00:00 -J 1-"$n" \
        -v PIECES="$2",REPO="$HOME"/wk scripts/cluster/batch.pbs)"
}
sub "26 sites"   weekend_sites.txt      8 32gb 12
sub "sign-off"   weekend_signoff.txt    8 32gb 12
echo "tests: job $(bash scripts/cluster/submit.sh -v REPO="$HOME"/wk scripts/cluster/tests.pbs)"
sub "robustness" weekend_robustness.txt 4 16gb 8
sub "break-even" weekend_breakeven.txt  4 16gb 12
echo "check with: bash scripts/cluster/progress.sh <batch number>"
