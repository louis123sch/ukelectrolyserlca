"""The near-optimal range (optimisation/near_optimal.py): every design it reports stays inside the
carbon limit, each range holds the lowest-carbon design, and a wider limit never narrows a range.
On the two-week synthetic fixtures of test_dc_model, so no data or full-year solve is needed."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from optimisation import dc_model as M, near_optimal as NO  # noqa: E402
from test_dc_model import series, tech  # noqa: E402,F401  (fixtures)

ASSETS = M.Assets(grid=True, wind=True, solar=True, battery=True, electrolyser=True, tank=True,
                  fuel_cell=True)


@pytest.fixture(scope="module")
def one(series, tech):  # noqa: F811
    return NO.ranges(series, ASSETS, tech, slack=0.01)


@pytest.fixture(scope="module")
def five(series, tech):  # noqa: F811
    return NO.ranges(series, ASSETS, tech, slack=0.05)


def test_every_design_is_inside_the_limit(one):
    assert one["limit_kgco2e_per_year"] == pytest.approx(1.01 * one["g_star_kgco2e_per_year"])
    for r in one["rows"]:
        assert r["gwp_kgco2e_per_year"] <= one["limit_kgco2e_per_year"] * (1 + 1e-6)


def test_each_range_holds_the_lowest_carbon_design(one):
    assert set(one["ranges"]) == set(NO.DEFAULT_VARS)
    for var, d in one["ranges"].items():
        tol = 1e-6 * max(1.0, abs(d["lowest_carbon"]))
        assert d["min"] - tol <= d["lowest_carbon"] <= d["max"] + tol, var


def test_a_wider_limit_never_narrows_a_range(one, five):
    for var in one["ranges"]:
        a, b = one["ranges"][var], five["ranges"][var]
        tol = 1e-6 * max(1.0, a["max"])
        assert b["min"] <= a["min"] + tol and b["max"] >= a["max"] - tol, var


def test_an_asset_that_is_not_allowed_has_no_range(series, tech):  # noqa: F811
    no_h2 = M.Assets(grid=True, wind=True, solar=True, battery=True)
    res = NO.ranges(series, no_h2, tech, slack=0.01)
    assert set(res["ranges"]) == {"cap_batt_e", "cap_batt_p"}


def test_a_bad_slack_fails_at_once(series, tech):  # noqa: F811
    with pytest.raises(ValueError, match="slack"):
        NO.ranges(series, ASSETS, tech, slack=-0.01)
