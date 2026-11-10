"""The solver switch (10 Nov 2026): HiGHS by default, Gurobi by DC_SOLVER=gurobi or
solver="gurobi", with HiGHS's option names translated. The Gurobi checks skip
where gurobipy or a licence is missing."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from optimisation import dc_model as M      # noqa: E402
import test_connection_choice as TC         # noqa: E402
import test_dc_model as TD                  # noqa: E402
from test_dc_model import series, tech      # noqa: E402,F401 - the two-week fixtures

pytest.importorskip("linopy")


def _gurobi_ok() -> bool:
    try:
        import gurobipy as gp
        gp.Env(params={"OutputFlag": 0}).dispose()
        return True
    except Exception:                            # noqa: BLE001 - not installed, or no licence
        return False


needs_gurobi = pytest.mark.skipif(not _gurobi_ok(), reason="gurobipy or its licence is not available")


def test_the_default_is_highs_and_the_environment_can_choose(monkeypatch):
    monkeypatch.delenv("DC_SOLVER", raising=False)
    assert M.current_solver() == "highs"
    monkeypatch.setenv("DC_SOLVER", "Gurobi")
    assert M.current_solver() == "gurobi"
    assert M.current_solver("highs") == "highs"          # an explicit argument wins
    monkeypatch.setenv("DC_SOLVER", "cplex")
    with pytest.raises(ValueError):
        M.current_solver()


def _cost_and_build(solver, series, tech, assets, **kw):
    m, V, obj = M.build_model(series, assets, tech, **kw)
    M.solve(m, solver=solver)
    caps = {k: float(V[k].solution) for k in ("cap_wind", "cap_solar", "cap_batt_e", "cap_tank", "cap_fc")
            if k in V}
    return float(m.objective.value), caps


@needs_gurobi
def test_gurobi_matches_highs_on_the_whole_system(series, tech):
    for objective in ("cost", "gwp"):
        c_h, _ = _cost_and_build("highs", series, tech, TD.ALL, objective=objective)
        c_g, _ = _cost_and_build("gurobi", series, tech, TD.ALL, objective=objective)
        assert c_g == pytest.approx(c_h, rel=1e-6)


@needs_gurobi
def test_gurobi_matches_highs_with_a_choice_of_price_lists():
    s = TC._series(7.31, TC.GROUPS)
    t = TC._tech(connection_options=(TC.SMALL, TC.LARGE))
    m_h, V_h, _ = M.build_model(s, M.Assets(grid=True), t, objective="cost")
    M.solve(m_h, solver="highs")
    m_g, V_g, _ = M.build_model(s, M.Assets(grid=True), t, objective="cost")
    M.solve(m_g, solver="gurobi")
    assert len(m_g.binaries) == 2
    assert float(m_g.objective.value) == pytest.approx(float(m_h.objective.value), rel=1e-6)
    assert [round(float(V_g[f"on_{i}"].solution)) for i in range(2)] == \
           [round(float(V_h[f"on_{i}"].solution)) for i in range(2)]
