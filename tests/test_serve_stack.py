"""The dispatch attribution: bands that add up, in an order that reads.

serve_stack answers a question the LP does not: which source served the load in
a period when several were flowing. The convention is documented on the
function; these tests hold it to the two things it must never get wrong — the
bands sum to demand, and nothing is negative.
"""
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import dc_model as M

COLS = ("demand", "p_wind", "p_offshore", "p_solar", "dis", "p_fc", "unserved")


def frame(**cols) -> pd.DataFrame:
    n = len(next(iter(cols.values())))
    base = {c: np.zeros(n) for c in COLS}
    base.update(cols)
    return pd.DataFrame(base, index=pd.date_range("2025-01-01", periods=n, freq="h"))


def total(stack) -> pd.Series:
    return stack.groupby("t").mw.sum()


def test_bands_sum_to_demand():
    df = frame(demand=[10.0, 10.0, 10.0],
               p_wind=[4.0, 12.0, 0.0], p_solar=[2.0, 0.0, 0.0],
               dis=[1.0, 0.0, 3.0], p_fc=[0.5, 0.0, 0.0])
    st = M.serve_stack(df)
    assert np.allclose(total(st).to_numpy(), df.demand.to_numpy())


def test_surplus_renewables_do_not_overfill_the_stack():
    """12 MW of wind against 10 MW of demand serves 10, not 12."""
    df = frame(demand=[10.0], p_wind=[12.0])
    st = M.serve_stack(df).set_index("source").mw
    assert st["Wind"] == pytest.approx(10.0)
    assert st["Grid import"] == pytest.approx(0.0)


def test_renewables_are_split_pro_rata_not_by_merit_order():
    df = frame(demand=[6.0], p_wind=[6.0], p_solar=[2.0])
    st = M.serve_stack(df).set_index("source").mw
    assert st["Wind"] == pytest.approx(4.5)      # 6/8 of 6 MW served
    assert st["Solar PV"] == pytest.approx(1.5)  # 2/8


def test_the_grid_is_the_residual():
    df = frame(demand=[10.0], p_wind=[3.0], dis=[2.0], p_fc=[1.0])
    st = M.serve_stack(df).set_index("source").mw
    assert st["Grid import"] == pytest.approx(4.0)


def test_unserved_is_a_band_and_is_not_attributed():
    df = frame(demand=[10.0], p_wind=[4.0], unserved=[6.0])
    st = M.serve_stack(df).set_index("source").mw
    assert st["Unserved"] == pytest.approx(6.0)
    assert st["Wind"] == pytest.approx(4.0)
    assert st["Grid import"] == pytest.approx(0.0)


def test_solver_noise_never_draws_below_the_axis():
    df = frame(demand=[5.0], p_solar=[-0.0], p_wind=[-1e-12], dis=[5.0])
    st = M.serve_stack(df)
    assert (st.mw >= 0).all()


def test_rank_orders_renewables_below_and_unserved_on_top():
    df = frame(demand=[1.0], p_wind=[1.0])
    st = M.serve_stack(df).drop_duplicates("source").set_index("source")["rank"]
    assert st["Solar PV"] < st["Battery"] < st["Grid import"] < st["Unserved"]
