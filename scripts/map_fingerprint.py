"""What the LCA map was built from, as a fingerprint.

``build_lca_map.py`` stamps ``fingerprint()`` into ``lca_map.json["meta"]``;
``check_lca_map.py`` (and ``tests/test_lca_map.py``) recompute it from the
live repository and fail when any compared part differs, so a map built
before an inventory, coefficient or grid change is caught instead of trusted.
Nothing here needs Brightway: the inventories are hashed as the modules
declare them, the coefficients as the CSV the optimiser reads.

    python scripts/map_fingerprint.py      # print the live fingerprint
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

COEFFICIENTS_CSV = ROOT / "optimisation_outputs" / "tech_lca_coefficients.csv"

# The parts the checker compares. git_head is recorded for the reader only: a
# commit that touches nothing the map shows must not make the map stale.
COMPARED = ("inventories", "coefficients", "grid_sources_id", "register")


def _digest(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def inventories_digest() -> str:
    """Every inventory module's static content: tables, activities, rows."""
    from optimiser_lca import build
    from optimiser_lca.common import FG

    def row(r):
        key, amount, unit, note = (list(r) + [None] * 4)[:4]
        key = f"FG:{key.database or ''}/{key.code}" if isinstance(key, FG) else str(key)
        return [key, float(amount), unit, note]

    dump = {}
    for _name, inv in build.inventories():
        dump[inv.database] = {
            "processes": {k: [list(p.identity) if p.identity else None, p.unit, p.database]
                          for k, p in inv.processes.items()},
            "flows": {k: ([f.identity[0], list(f.identity[1])] if f.identity else None)
                      for k, f in inv.flows.items()},
            "activities": [{
                "code": a.code, "name": a.name, "unit": a.unit, "location": a.location,
                "product": a.reference_product, "production_amount": float(a.production_amount),
                "scale": float(a.scale), "technosphere": [row(r) for r in a.technosphere],
                "biosphere": [row(r) for r in a.biosphere],
            } for a in inv.activities],
        }
    return _digest(dump)


def coefficients_digest() -> str | None:
    """The coefficient table the LP reads, less its build timestamp."""
    if not COEFFICIENTS_CSV.exists():
        return None
    lines = [ln for ln in COEFFICIENTS_CSV.read_text(encoding="utf-8").splitlines()
             if not ln.startswith("# built_at")]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def register_digest() -> str | None:
    """The cut-off register (optimiser_lca/exclusions.py), once it exists."""
    try:
        from optimiser_lca import exclusions
    except ImportError:
        return None
    from dataclasses import asdict, is_dataclass
    rows = [asdict(e) if is_dataclass(e) else e for e in exclusions.REGISTER]
    return _digest(rows)


def git_head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:                                      # noqa: BLE001 — no git, no problem
        return None


def fingerprint() -> dict:
    from optimiser_lca import grid
    return {
        "inventories": inventories_digest(),
        "coefficients": coefficients_digest(),
        "grid_sources_id": grid.sources_id(),
        "register": register_digest(),
        "git_head": git_head(),
    }


def compare(stamped: dict | None, live: dict | None = None) -> list[str]:
    """Human-readable differences on the compared parts; empty when current."""
    live = live or fingerprint()
    if not stamped:
        return ["the map carries no fingerprint — rebuild it with the current build_lca_map.py"]
    return [f"{k}: map {stamped.get(k)} vs live {live.get(k)}"
            for k in COMPARED if stamped.get(k) != live.get(k)]


if __name__ == "__main__":
    for k, v in fingerprint().items():
        print(f"{k:16s} {v}")
