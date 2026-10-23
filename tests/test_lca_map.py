"""The LCA map is held to the live model.

``scripts/check_lca_map.py`` re-derives the map from the code: every LP term
at ``build_tech``'s coefficient, every foreground exchange against its
inventory module, every activity of every inventory shown, the energy tab
against a fresh ``energy_section()``, and — since 22 Oct 2026 — the
fingerprint of what the map was built from against what is live now, and the
page against the JSON. This runs the checker's no-Brightway sections under
pytest, so an inventory or coefficient edit without a map rebuild goes red
here rather than waiting to be noticed.

Skipped when no map has been built. Rebuild with
``python scripts/build_lca_map.py`` (Brightway, ~7 min) and republish.
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
