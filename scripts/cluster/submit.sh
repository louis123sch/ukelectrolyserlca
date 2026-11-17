#!/bin/bash
# qsub with an email when the job ends or fails, to the address in ~/.cluster_email
# (a private file on the cluster, kept out of this public repository). Without that file
# it is plain qsub. An array job sends one email for the whole array, not one per piece.
#   bash scripts/cluster/submit.sh -v SITE=13,LEVEL=limited scripts/cluster/uk_sites_piece.pbs
MAIL=()
if [ -s "$HOME/.cluster_email" ]; then
    MAIL=(-m ae -M "$(head -n 1 "$HOME/.cluster_email")")
fi
qsub "${MAIL[@]}" "$@"
