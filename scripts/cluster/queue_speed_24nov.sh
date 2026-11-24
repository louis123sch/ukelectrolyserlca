#!/bin/bash
# 24 Nov 2026, for queue speed rather than solving speed: every waiting piece of the grid re-run and the
# off-grid finish goes back in at one core and a short time limit (requeue_small.sh); running pieces
# carry on. Then the two extra East Grinstead checks go in the same way (extra_checks_setup.sh).
# On a login node, after `git pull` in ~/ukdclca:
#   bash scripts/cluster/queue_speed_24nov.sh
set -e
cd "$HOME/ukdclca"
R=scripts/cluster/requeue_small.sh
bash $R 16878 rerun_grid_sites.txt             "$HOME/wk2" 6gb 8   # 26 sites, grid, new code
bash $R 16880 rerun_grid_robustness_eg.txt     "$HOME/wk2" 6gb 4   # robustness, grid, new code (<= 138 min seen)
bash $R 16883 finish_offgrid_sites.txt         "$HOME/wk"  6gb 3   # 26 sites, off-grid (<= 85 min seen)
bash $R 16884 finish_offgrid_robustness_eg.txt "$HOME/wk"  6gb 3   # robustness, off-grid (<= 72 min seen)
bash scripts/cluster/extra_checks_setup.sh
sleep 15
echo; echo "queue now:"; qstat -u "$USER" | tail -n +4 | awk '{print $1, $(NF-1)}' | sort -k2 | uniq -c -f1 | head
qstat -u "$USER"
