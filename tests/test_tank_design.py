"""The as-built hydrogen tank since 4 Nov 2026 (evening): a bulk carbon-steel vessel at 28 bar, the
class the cost side prices, with Gandiglio's stainless buffer kept as the sensitivity."""
import pytest

from optimisation import h2_storage as h2s
from optimiser_lca import exclusions as X, h2_tank


def test_as_built_tank_is_the_bulk_carbon_steel_vessel():
    assert h2_tank.TANK_DESIGN == "bulk_carbon_steel_28bar"
    assert h2_tank.TANK_STEEL_KG_PER_KG_H2 == pytest.approx(161.2)
    assert h2_tank.DESIGN["steel_process"] == "steel_low_alloyed_hr"
    assert h2_tank.DESIGN["forming_process"] == "sheet_rolling_steel"
    # the paper's vessel is still there, unchanged, as the sensitivity
    assert h2_tank.steel_kg_per_kg_h2(h2_tank.TANK_DESIGNS["gandiglio_28bar"]) == pytest.approx(313.0, abs=2.0)
    assert "OK" in h2_tank.check()


def test_the_inventory_declares_only_what_the_as_built_design_uses():
    used = {k for row in h2_tank.activities[0].technosphere for k in [row[0]]}
    assert used == set(h2_tank.processes)
    assert "steel_chromium_188" not in h2_tank.processes
    assert "steel_chromium_188" in h2_tank.ALL_PROCESSES


def test_usable_fraction_is_the_same_at_the_same_pressure():
    assert h2s.usable_fraction("bulk_carbon_steel_28bar") == pytest.approx(25.0 / 28.0)
    assert h2s.usable_fraction("gandiglio_28bar") == pytest.approx(25.0 / 28.0)


def test_cutoff_register_follows_the_as_built_vessel():
    rows = {e.flow: e for e in X.REGISTER if e.technology == "hydrogen tank"}
    forming = rows["forming of the vessel steel (rolling, welding)"]
    assert forming.amount_central == pytest.approx(161.2 / 25.0)
    assert forming.factor_identity[0] == "market for sheet rolling, steel"
    fittings = rows["valves, pipework and fittings"]
    assert fittings.factor_identity[0] == "market for steel, low-alloyed, hot rolled"
    assert fittings.amount_upper == pytest.approx(0.02 * 161.2 / 25.0)


def test_decomposition_carries_every_design_with_its_own_forming():
    rows = {r["design"]: r for r in h2s.decompose()}
    assert {"bulk_carbon_steel_28bar", "gandiglio_28bar", "type1_200bar"} <= set(rows)
    bulk, gand = rows["bulk_carbon_steel_28bar"], rows["gandiglio_28bar"]
    assert bulk["is_as_built"] and not gand["is_as_built"]
    assert bulk["forming_process"] == "sheet_rolling_steel"
    assert gand["forming_process"] == "sheet_rolling_cr_steel"
    # lighter steel, lower factor and cheaper forming: well under the stainless buffer per kg stored
    assert bulk["kgco2e_per_kg_capacity"] < 0.4 * gand["kgco2e_per_kg_capacity"]
    assert bulk["brightway_kgco2e_per_kg_capacity"] == pytest.approx(bulk["kgco2e_per_kg_capacity"], rel=1e-3)
