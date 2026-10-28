"""The LCA map is held to the live model.

The map is generated from the code (``scripts/build_lca_map.py``: the LP's own
term functions, the coefficient modules' trace steps, and Brightway), and
``scripts/check_lca_map.py`` re-reads the written map against the live
repository: the fingerprint of what it was built from, the build's own
problem list, the graph's integrity, every LP term against ``dc_model``,
every inventory activity and exchange, the energy tab and the page. This runs
its no-Brightway sections under pytest, so an inventory, coefficient-code or
term edit without a map rebuild goes red here rather than waiting to be
noticed.

Skipped when no map has been built. Rebuild with
``python scripts/build_lca_map.py`` (Brightway, under a minute) and republish.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

MAP = ROOT / "optimisation_outputs" / "lca_map.json"


def test_map_fingerprint_is_current():
    """The cheap check first: what the map was built from is what is live."""
    if not MAP.exists():
        pytest.skip("no lca_map.json — run scripts/build_lca_map.py")
    import json
    import map_fingerprint as F
    meta = json.loads(MAP.read_text(encoding="utf-8")).get("meta") or {}
    diffs = F.compare(meta.get("fingerprint"))
    assert not diffs, "the map is stale — rebuild it: " + "; ".join(diffs)


def test_map_matches_the_live_model():
    """Every section of check_lca_map.py that needs no Brightway."""
    if not MAP.exists():
        pytest.skip("no lca_map.json — run scripts/build_lca_map.py")
    import check_lca_map as C
    rc = C.main(use_bw=False)
    assert rc == 0, f"{len(C.problems)} problems, e.g. " + " | ".join(C.problems[:6])
