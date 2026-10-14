"""
Write every foreground database, in dependency order.
=============================================================================

    python -m optimiser_lca.build                 # all eight
    python -m optimiser_lca.build fuel_cell upv   # just these
    python -m optimiser_lca.build --check         # static checks only, no Brightway

Each database is deleted and rewritten whole. Later databases link into
earlier ones (the fuel cell burns hydrogen from ``hydrogen foreground``), so
the order is the one in ``registry.DATABASES``. Rebuilding a single database
that others link *into* (hydrogen) keeps those links, which are by (database,
code), but the dependents are reprocessed afterwards: the rewrite renumbers
the nodes their matrices point at.

Afterwards the coefficient caches are stale: run ``python
optimisation/coefficients.py`` to refresh them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimiser_lca import registry  # noqa: E402
from optimiser_lca.common import check, resolve, write  # noqa: E402

# Module name -> database, in build order.
MODULES = [
    ("upv",                 registry.SOLAR_DB),
    ("gb_grid",             registry.GRID_DB),
    ("hydrogen",            registry.HYDROGEN_DB),
    ("data_centre",         registry.DATA_CENTRE_DB),
    ("bess",                registry.BESS_DB),
    ("fuel_cell",           registry.FUEL_CELL_DB),
    ("h2_tank",             registry.H2_STORAGE_DB),
    ("stepup_transformers", registry.TRANSFORMER_DB),
]


def load(name: str):
    import importlib
    return importlib.import_module(f"optimiser_lca.{name}")


def inventories(names=None):
    names = names or [n for n, _ in MODULES]
    out = []
    for n, db in MODULES:
        if n in names:
            inv = load(n).inventory()
            if inv.database != db:
                raise AssertionError(f"{n} writes {inv.database!r}, registry expects {db!r}")
            out.append((n, inv))
    return out


def check_all(names=None) -> list[str]:
    """Static checks, no Brightway."""
    lines = []
    for n, inv in inventories(names):
        lines.append(check(inv))
        expected = set(registry.CODES_BY_DATABASE[inv.database])
        got = {a.code for a in inv.activities}
        if expected != got:
            raise AssertionError(f"{n}: registry lists {sorted(expected ^ got)} differently")
    return lines


def reprocess_dependents(rebuilt: set[str]) -> None:
    """Reprocess every database that links into one just rewritten.

    A rewrite gives each activity a new node id. The (database, code) links
    survive, but a dependent's processed matrices still hold the old ids, and
    its next LCA fails as a non-square technosphere (the fuel cell, after
    rebuilding hydrogen alone).
    """
    import bw2data as bd
    for db in bd.databases:
        if db not in rebuilt and rebuilt & set(bd.databases[db].get("depends", [])):
            print(f"Reprocessing {db!r}: it links into a rebuilt database.")
            bd.Database(db).process()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("modules", nargs="*", help="subset to build, e.g. fuel_cell upv")
    ap.add_argument("--check", action="store_true", help="static checks only")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    names = args.modules or None
    unknown = set(names or []) - {n for n, _ in MODULES}
    if unknown:
        ap.error(f"unknown module(s) {sorted(unknown)}; choose from {[n for n, _ in MODULES]}")

    for line in check_all(names):
        print(line)
    if args.check:
        return 0

    import lca_helpers as H
    H.setup_brightway()
    for n, inv in inventories(names):
        print("\n" + "#" * 78)
        print(f"# {n}: {inv.name} -> {inv.database!r}")
        print("#" * 78)
        resolved = resolve(inv)
        write(inv, resolved, verbose=not args.quiet)
    reprocess_dependents({inv.database for _, inv in inventories(names)})
    H.refresh_foreground()
    print("\nDone. Coefficient caches are now stale: run `python optimisation/coefficients.py`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
