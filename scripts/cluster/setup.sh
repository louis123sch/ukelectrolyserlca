#!/bin/bash
# One-off setup of the model on Imperial's CX3 cluster (first run 17 Nov 2026).
# On a login node:  cd ~/ukdclca && git pull && bash scripts/cluster/setup.sh
# Light setup only, as Imperial's guide allows on login nodes; it solves nothing.
# Safe to run again: each step skips or repeats harmlessly what is already done.
# Expects in the home folder (uploaded from the laptop): the Brightway backup
# brightway2-project-hydrogen-smr-sources-backup.tar.gz, caches.tar.gz and, the first time, .env.
set -e
cd "$HOME"
say() { echo; echo "=== $*"; }

say "1/6 conda (Imperial's miniforge, into ~/miniforge3)"
if [ ! -x "$HOME/miniforge3/bin/conda" ]; then
    module load miniforge/3
    miniforge-setup
fi
eval "$("$HOME/miniforge3/bin/conda" shell.bash hook)"
# Imperial's conda guide: Anaconda's licence rules out its "defaults" channel.
conda config --remove channels defaults 2>/dev/null || true
conda config --add channels conda-forge 2>/dev/null
conda config --set auto_activate false 2>/dev/null

say "2/6 the model's Python setup (environment 'ukdclca')"
if conda env list | grep -qE '^ukdclca\s'; then
    conda env update -n ukdclca -f ukdclca/environment-cluster.yml
else
    conda env create -f ukdclca/environment-cluster.yml
fi
# The cluster's own /lib64/libstdc++ is older than conda's. Packages from pip (highspy,
# gurobipy) otherwise load the old one first and pandas then fails (GLIBCXX_3.4.29, 17 Nov).
# Putting the environment's lib folder first on the library path fixes it whenever it is active.
conda env config vars set -n ukdclca LD_LIBRARY_PATH="$HOME/miniforge3/envs/ukdclca/lib" >/dev/null
conda activate ukdclca

say "3/6 the life-cycle database (Brightway project hydrogen-smr-sources)"
python - <<'PY'
import bw2data as bd, bw2io
if "hydrogen-smr-sources" in bd.projects:
    print("already there")
else:
    bw2io.restore_project_directory("brightway2-project-hydrogen-smr-sources-backup.tar.gz",
                                    project_name="hydrogen-smr-sources")
bd.projects.set_current("hydrogen-smr-sources")
print("databases:", len(bd.databases))
assert "gas engine foreground" in bd.databases, "gas engine database missing"
PY

say "4/6 saved online data (so jobs need no internet)"
if [ -f caches.tar.gz ]; then tar -xzf caches.tar.gz -C ukdclca; fi
for d in carbon_intensity_api_cache optimisation_outputs/profile_cache optimisation_outputs/neso_cache; do
    echo "$(find "ukdclca/$d" -type f | wc -l) files, $(du -sh --apparent-size "ukdclca/$d" | cut -f1)  $d"
done

say "5/6 keys file (readable by you only)"
if [ -f .env ]; then mv .env ukdclca/.env; fi
chmod 600 ukdclca/.env
ls -l ukdclca/.env

say "6/6 checks (no solves)"
export GRB_LICENSE_FILE=/sw-eb/software/Gurobi/13.0.1-GCCcore-14.3.0/gurobi.lic
cd ukdclca
DC_BW_PROJECT=hydrogen-smr-sources python - <<'PY'
import sys
import highspy, gurobipy as gp           # pip-installed first: the order that broke on 17 Nov
import numpy, pandas, scipy, linopy, bw2data, bw2calc
print("python", sys.version.split()[0], "| numpy", numpy.__version__, "| pandas", pandas.__version__,
      "| linopy", linopy.__version__, "| gurobipy", gp.__version__)
assert numpy.__version__ == "1.26.4", "numpy is not the laptop's 1.26.4"
m = gp.Model()                          # takes a licence place from gurobi.cc.ic.ac.uk for a moment
print("Gurobi licence OK, version", gp.gurobi.version())
m.dispose()
import dc_config
print("model project:", dc_config.PROJECT_NAME)
from optimisation import dc_model       # the model code itself imports
print("model code imports OK")
PY

echo
echo "SETUP FINISHED."
