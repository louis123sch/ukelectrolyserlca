#!/bin/sh
# Model explainer, rebuilt with every commit that touches the model (user, 19 Nov 2026).
#
# When a commit stages model Python (optimisation/*.py, optimiser_lca/*.py) or the
# equations page, this rebuilds optimisation_outputs/model_explainer.html, adds it to
# the same commit, and refreshes the copy in the OneDrive report exports folder.
# It is built from the working tree, so stage whole files when committing model changes.
#
# Installed by one line in the shared hook (.git/hooks/pre-commit, used by every
# worktree), placed before its final "exit 0":
#
#     [ -f scripts/hooks/pre-commit-model-explainer.sh ] && { sh scripts/hooks/pre-commit-model-explainer.sh || exit 1; }
#
# Checkouts without this file (main, the overnight branch) skip it.
# tests/test_model_explainer.py fails whenever the page is out of date, hook or not.

top=$(git rev-parse --show-toplevel)
git diff --cached --name-only \
  | grep -qE '^(optimisation/[^/]*\.py|optimiser_lca/[^/]*\.py|docs/model_equations_explorer\.html)$' \
  || exit 0

PY="${EXPLAINER_PYTHON:-C:/Users/ls1524/AppData/Local/miniconda3/envs/brightway/python.exe}"
MKL_THREADING_LAYER=TBB "$PY" "$top/scripts/build_model_explainer.py" || {
  echo "pre-commit: the model explainer did not build; fix that before committing model changes." >&2
  exit 1
}
git add "$top/optimisation_outputs/model_explainer.html"

export_dir="${EXPLAINER_EXPORT_DIR:-/c/Users/ls1524/OneDrive - Imperial College London/DC optimiser/report exorts}"
if [ -d "$export_dir" ]; then
  cp "$top/optimisation_outputs/model_explainer.html" "$export_dir/model explainer.html" \
    && echo "pre-commit: model explainer rebuilt and copied to $export_dir"
fi
exit 0
