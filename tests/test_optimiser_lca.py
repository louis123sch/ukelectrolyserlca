"""The inventory package: every module well-formed without Brightway, and —
where the project is present — every identity resolving to exactly one
activity and the written databases matching the modules.

Without Brightway: the static checks in ``optimiser_lca.common.check`` (units
from the fixed set, every exchange naming a declared process or flow, no
duplicate codes), the registry complete for every database, the grid sources
id unchanged (every series on disk carries it), each module's own ``check()``.

With Brightway (skipped if the project is absent): every pinned identity
resolves, and is still among the search hits for its query; and the six
databases in the project hold exactly the activities and exchanges the modules
declare, so a module edit without a rebuild is caught here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimiser_lca import build, common, grid, registry  # noqa: E402

MODULES = [n for n, _ in build.MODULES]


# -----------------------------------------------------------------------------
# No Brightway needed
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("name", MODULES)
def test_inventory_is_well_formed(name):
    inv = build.load(name).inventory()
    assert common.check(inv).startswith("OK")


def test_registry_lists_exactly_what_each_module_writes():
    for name, inv in build.inventories():
        assert {a.code for a in inv.activities} == set(registry.CODES_BY_DATABASE[inv.database]), name
    assert list(registry.CODES_BY_DATABASE) == registry.DATABASES


def test_codes_are_unique_across_databases():
    seen = {}
    for db, codes in registry.CODES_BY_DATABASE.items():
        for c in codes:
            assert c not in seen, f"{c} in both {seen[c]} and {db}"
            seen[c] = db


def test_grid_sources_id_is_the_one_every_series_carries():
    assert grid.sources_id() == "158704fcb705"
    assert set(grid.GRID_SOURCES) == set(grid.TECH_SPECS)
    assert abs(sum(grid.WIND_GROUP_WEIGHTS.values()) - 1) < 1e-9
    assert abs(sum(grid.IMPORT_GROUP_WEIGHTS.values()) - 1) < 1e-9


def test_grid_score_row_is_share_times_loss_times_score():
    scores = {k: 0.0 for k in grid.TECH_SPECS}
    scores.update(GAS=0.4, NUCLEAR=0.01)
    s, a = grid.score_row({"GAS_perc": 50.0, "NUCLEAR_perc": 50.0}, scores)
    assert s == pytest.approx(grid.MARKET_LOSS_FACTOR * (0.5 * 0.4 + 0.5 * 0.01))
    assert a == pytest.approx(grid.MARKET_LOSS_FACTOR)


def test_module_checks_pass():
    from optimiser_lca import fuel_cell, stepup_transformers, upv
    assert fuel_cell.check_parameters().startswith("OK")
    assert stepup_transformers.check().startswith("OK")
    assert upv.check().startswith("OK")


def test_fuel_cell_maintenance_cancels_its_stack_content():
    from optimiser_lca import fuel_cell as fc
    assert fc._MAINT * fc.FC_MAINT_STACK_FRACTION == pytest.approx(fc.FC_STACK_PER_KWH * 0.5, rel=1e-12)
    assert fc.FC_H2_PER_KWH == pytest.approx(1 / (0.5 * 0.95 * 33.33))


def test_tank_as_built_is_313_kg_steel_per_kg_h2():
    from optimiser_lca import h2_tank
    d = h2_tank.TANK_DESIGNS["gandiglio_28bar"]
    assert h2_tank.capacity_kg(d) == pytest.approx(50.0, abs=0.3)
    assert h2_tank.steel_kg_per_kg_h2(d) == pytest.approx(313.0, abs=2.0)


def test_transformer_bills_reconcile_to_their_sources():
    from optimiser_lca import stepup_transformers as tx
    assert sum(tx.TX_LENG_BOX_KG.values()) == pytest.approx(282_343.0)
    assert sum(tx.UPV_TX_MATERIALS_KG.values()) + tx.UPV_TX_FIBREBOARD_KG == pytest.approx(5_680.0, abs=1.0)
    assert tx.UPV_TX_UNITS_PER_MWP == pytest.approx(0.4)


def test_fuel_cell_stack_amounts_are_as_printed_and_scaled_once():
    from optimiser_lca import fuel_cell as fc
    platinum = next(amt for k, amt, *_ in fc.STACK.technosphere if k == "platinum")
    assert platinum == 0.00075                      # Table S1, verbatim
    assert fc.STACK.scale == pytest.approx(0.5 * 1.878606235)


# -----------------------------------------------------------------------------
# With Brightway
# -----------------------------------------------------------------------------
def _project_or_skip():
    bd = pytest.importorskip("bw2data")
    import dc_config as cfg
    if cfg.PROJECT_NAME not in bd.projects:
        pytest.skip("Brightway project not present on this machine")
    return bd


@pytest.mark.parametrize("name", MODULES)
def test_every_identity_resolves_and_is_findable(name):
    _project_or_skip()
    inv = build.load(name).inventory()
    resolved = common.resolve(inv, strict_search=True)
    assert set(resolved) == set(inv.processes) | set(inv.flows)


@pytest.mark.parametrize("name", MODULES)
def test_written_database_matches_the_module(name):
    """What is in Brightway is what the module says — an edit without a rebuild fails here."""
    bd = _project_or_skip()
    inv = build.load(name).inventory()
    if inv.database not in bd.databases:
        pytest.skip(f"{inv.database!r} not built — run `python -m optimiser_lca.build {name}`")
    expected = common.to_bw_dict(inv)
    db = bd.Database(inv.database)
    assert {a["code"] for a in db} == {c for _, c in expected}
    for (dbn, code), want in expected.items():
        act = bd.get_activity((dbn, code))
        got = sorted((e["type"], tuple(e.input.key), round(float(e["amount"]), 12)) for e in act.exchanges())
        exp = sorted((e["type"], tuple(e["input"]), round(float(e["amount"]), 12)) for e in want["exchanges"])
        assert got == exp, f"{dbn}/{code} differs from the module"
