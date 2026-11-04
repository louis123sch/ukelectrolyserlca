"""The cost map is held to the live model.

The map is generated from the code (``scripts/build_cost_map.py``: the LP's
cost terms, the cost modules' ``T.cost`` steps, the source register, and one
solve), and ``scripts/check_cost_map.py`` re-reads the written map against the
live repository. This runs its quick sections under pytest, so a cost-code,
term or register edit without a map rebuild goes red here.

Skipped when no map has been built. Rebuild with
``python scripts/build_cost_map.py`` and republish.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

MAP = ROOT / "optimisation_outputs" / "cost_map.json"


def test_cost_map_matches_the_live_model():
    if not MAP.exists():
        pytest.skip("no cost_map.json — run scripts/build_cost_map.py")
    import check_cost_map as C
    rc = C.main(live=False)
    assert rc == 0, f"{len(C.problems)} problems, e.g. " + " | ".join(C.problems[:6])

