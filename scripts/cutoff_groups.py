"""Rule 3 group by group at the lowest-carbon points, to find which still-excluded
cut-off items move a design (first run 12 Nov 2026 on d77d560).

Adds each technology's still-excluded cut-off items at their upper estimate, one
group at a time, and solves the lowest-carbon point only, on the rig.
Writes sensitivity_cutoff_groups_1112_<case>_4h.csv.

    python scripts/cutoff_groups.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimisation import sensitivity as S, dc_inputs as I  # noqa: E402
from optimiser_lca import exclusions as X  # noqa: E402

fields = []
for e in X.REGISTER:
    if e.kind == "cutoff" and e.status == "excluded":
        f = I.CUTOFF_FIELD.get((e.technology, e.side))
        if f and f not in fields:
            fields.append(f)
print("groups:", fields, flush=True)
variants = [{"cutoff": "upper"}] + [{"cutoff": f"upper:{f}"} for f in fields]
for case in ("norfolk_grid_green", "islanded_h2"):
    S.run(case, variants, name=f"cutoff_groups_1112_{case}", objectives=("gwp",))
print("ALL DONE", flush=True)
