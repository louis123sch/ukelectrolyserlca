"""The knee is picked on a normalised front (CODE_CHECK_FIX_PLAN step 1).

special_points used ndarray.ptp(), which NumPy 2.0 removed; it now uses np.ptp.
"""
import pandas as pd

from optimisation import dc_pareto


def test_knee_is_the_point_nearest_the_utopia_corner():
    df = pd.DataFrame({
        "cost_GBP_per_year": [100.0, 110.0, 200.0],
        "gwp_kgco2e_per_year": [1000.0, 300.0, 100.0],
        "point": ["min_cost", "eps_1", "min_gwp"],
    })
    sp = dc_pareto.special_points(df, degenerate=False)
    assert sp["knee"]["point"] == "eps_1"
