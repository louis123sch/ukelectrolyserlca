"""The inventory package: every module well-formed without Brightway, and —
where the project is present — every identity resolving to exactly one
activity and the written databases matching the modules.

Without Brightway: the static checks in ``optimiser_lca.common.check`` (units
from the fixed set, every exchange naming a declared process or flow, no
duplicate codes), the registry complete for every database, the grid sources
id unchanged (every series on disk carries it), each module's own ``check()``.

With Brightway (skipped if the project is absent): every pinned identity
resolves, and is still among the search hits for its query; and the seven
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
    assert grid.sources_id() == "055e53f4b11b"   # = test_grid_build.GRID_BASIS_ID
    assert set(grid.GRID_SOURCES) == set(grid.TECH_SPECS)
    assert abs(sum(grid.WIND_GROUP_WEIGHTS.values()) - 1) < 1e-9
    for fit in grid.IMPORT_ATTRIBUTION.values():
        assert abs(sum(fit["beta"].values()) - 1) < 1e-3
        assert abs(sum(fit["annual"].values()) - 1) < 1e-3
        assert fit["r2"] >= grid.IMPORT_FIT_MIN_R2


def test_grid_score_row_is_share_times_score():
    scores = {k: 0.0 for k in grid.TECH_SPECS}
    scores.update(GAS=0.4, NUCLEAR=0.01)
    g = grid.score_row({"GAS_perc": 50.0, "NUCLEAR_perc": 50.0}, scores)
    assert g == pytest.approx(0.5 * 0.4 + 0.5 * 0.01)


def test_grid_imports_use_the_recorded_country_split():
    scores = {k: 0.0 for k in grid.TECH_SPECS}
    scores.update(IMPORTS_FR=0.07, IMPORTS_NO=0.02)
    row = {"IMPORTS_perc": 100.0, **{f"imp_{c}": 0.0 for c in grid.COUNTRIES}}
    row.update(imp_FR=0.5, imp_NO=0.5)
    assert grid.score_row(row, scores) == pytest.approx(0.045)


def test_pumped_storage_returns_the_grids_own_electricity():
    """Its plant, plus 1.43 kWh of the half-hour's other generation per kWh."""
    scores = {k: 0.0 for k in grid.TECH_SPECS}
    scores.update(GAS=0.4, STORAGE=0.05)
    g = grid.score_row({"GAS_perc": 90.0, "STORAGE_perc": 10.0}, scores)
    assert g == pytest.approx(0.9 * 0.4 + 0.1 * (0.05 + grid.STORAGE_KWH_IN * 0.4))


def test_delivery_grows_down_the_voltages():
    hv, mv, lv = (grid.DELIVERY[v] for v in grid.VOLTAGES)
    assert 1.0 < hv["gross_up"] < mv["gross_up"] < lv["gross_up"] < 1.2
    assert 0.0 < hv["network_gco2e_per_kwh"] < mv["network_gco2e_per_kwh"] < lv["network_gco2e_per_kwh"]
    assert grid.delivered(0.1, "medium") == pytest.approx(
        0.1 * mv["gross_up"] + mv["network_gco2e_per_kwh"] / 1000.0)
    with pytest.raises(ValueError):
        grid.delivered(0.1, "extra high")


def test_one_delivery_basis_for_data_centre_and_hydrogen_seller():
    """The TODO this closes: grid imports and bought green H2 were delivered on
    different bases. Both now read grid.DELIVERY at a stated voltage."""
    from optimisation import h2_prices, network_charges as nc
    seller = grid.DELIVERY[h2_prices.GREEN_H2_SELLER_VOLTAGE]
    assert h2_prices.GRID_DELIVERY_LOSS_GROSS_UP == seller["gross_up"]
    assert h2_prices.GRID_DELIVERY_NETWORK_GCO2E_PER_KWH == seller["network_gco2e_per_kwh"]
    assert nc.delivery_voltage(True, "T-Demand4") == "high"
    assert nc.delivery_voltage(False, "EHV2") == "high"
    assert nc.delivery_voltage(False, "HV1") == "medium"


def test_module_checks_pass():
    from optimiser_lca import fuel_cell, stepup_transformers, upv
    assert fuel_cell.check_parameters().startswith("OK")
    assert stepup_transformers.check().startswith("OK")
    assert upv.check().startswith("OK")


def test_fuel_cell_bop_is_hydrogen_fed_and_per_kw():
    """The BoP is Usai's per-kW table plus inverter and container - no micro-CHP left."""
    from optimiser_lca import fuel_cell as fc
    assert fc.FC_H2_PER_KWH == pytest.approx(1 / (0.5 * 0.95 * 33.33))
    keys = {k for k, *_ in fc.BOP.technosphere if isinstance(k, str)}
    assert {"inverter_500kw", "bop_pump_40w", "bop_cable"} <= keys
    assert not {k for k in fc.processes if "ecoinvent" in k or "hydronics" in k or "transport" in k}
    # The two per-system lines of Usai's Table 1, divided once by the 80 kW system.
    amt = {k: a for k, a, *_ in fc.BOP.technosphere if isinstance(k, str)}
    assert amt["bop_pump_40w"] == pytest.approx(3 / 80)
    assert amt["bop_cable"] == pytest.approx(16 / 80)
    assert fc.FC_SYSTEM_LIFETIME_H > fc.FC_STACK_LIFETIME_H > fc.FC_SERVICE_INTERVAL_H


def test_tank_as_built_is_313_kg_steel_per_kg_h2():
    from optimiser_lca import h2_tank
    d = h2_tank.TANK_DESIGNS["gandiglio_28bar"]
    assert h2_tank.capacity_kg(d) == pytest.approx(50.0, abs=0.3)
    assert h2_tank.steel_kg_per_kg_h2(d) == pytest.approx(313.0, abs=2.0)


def test_transformer_bills_reconcile_to_their_sources():
    from optimiser_lca import stepup_transformers as tx
    assert sum(tx.TX_LENG_BOX_KG.values()) == pytest.approx(282_343.0)
    # The workbook's "36.96 m3" pressboard cell is 36.96 kg (its own comment says
    # so), and the bill then sums to 5,670.0 against the report's "approximately
    # 5,680" (21 Oct 2026). Pinned exactly, and held within 0.5 % of the report.
    bill = sum(tx.UPV_TX_MATERIALS_KG.values()) + tx.UPV_TX_FIBREBOARD_KG
    assert bill == pytest.approx(5_670.0, abs=0.01)
    assert abs(bill - tx.UPV_TX_STATED_TOTAL_KG) <= tx.UPV_TX_TOTAL_TOLERANCE * tx.UPV_TX_STATED_TOTAL_KG
    assert tx.UPV_TX_UNITS_PER_MWP == pytest.approx(0.4)


def test_grid_intake_transformer_is_lengs_main_unit():
    """Table S1's XZ11-100000/110: 71,458.6 kg on 100 MVA, the 715 kg/MVA SOURCES.md quotes."""
    from optimiser_lca import stepup_transformers as tx
    from optimisation import grid_connection as gc
    assert sum(tx.TX_LENG_MAIN_KG.values()) == pytest.approx(71_458.6)
    assert tx.TX_LENG_MAIN_MVA == 100.0
    assert sum(tx.TX_GRID_KG_PER_MVA.values()) == pytest.approx(714.586)
    assert gc.transformer_kg_per_mva() == pytest.approx(714.586)
    assert set(tx.TX_LENG_MAIN_KG) == set(tx.TX_LENG_BOX_KG)   # same materials, same mapping
    assert gc.TRANSFORMER_CODE == registry.TX_GRID
    assert registry.TX_GRID in registry.CODES_BY_DATABASE[registry.TRANSFORMER_DB]


def test_container_step_up_is_jaspers_unit_on_the_iea_composition():
    """The battery's and fuel cell's LV → 20 kV unit reads its mass and rating from
    the battery inventory's own Jasper bill, and every row is an IEA Table 49 row
    scaled by the mass ratio — one activity, per MW of inverter rating."""
    from optimiser_lca import stepup_transformers as tx, bess
    assert tx.CSS_TX_KG == bess.CSS_EXCLUDED["transformer, for grid connection"][0] == 5_500.0
    assert tx.CSS_TX_KW == bess.CSS_KW == 1_600.0
    assert tx.CSS_TX_KG_PER_MW == pytest.approx(3_437.5)
    act = next(a for a in tx.activities if a.code == registry.TX_LV_CONTAINER)
    assert act.unit == "megawatt"
    solar = next(a for a in tx.activities if a.code == registry.TX_SOLAR)
    # The solar activity also carries its station building (Z-PV-238, since
    # 21 Oct 2026), which is civils of the plant, not of the unit: compare the
    # transformer rows only, which are the "upv_" keys.
    solar_unit_rows = [r for r in solar.technosphere if str(r[0]).startswith("upv_")]
    assert len(act.technosphere) == len(solar_unit_rows)
    ratio = tx.CSS_TX_UNITS_PER_MW / tx.UPV_TX_UNITS_PER_MWP
    for (k, amt, *_), (ks, amt_s, *_) in zip(act.technosphere, solar_unit_rows):
        assert k == ks
        assert amt == pytest.approx(amt_s * ratio)
    assert registry.TX_LV_CONTAINER in registry.CODES_BY_DATABASE[registry.TRANSFORMER_DB]


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
