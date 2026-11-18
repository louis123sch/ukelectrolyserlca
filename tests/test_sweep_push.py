"""The sweep's "push" knob and the screened-input sweep (10 Nov 2026): one recorded
number times a factor, through the real code (trace.pushed), and the list the
input screen picked (sensitivity.SHAKY_KNOBS)."""
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import sensitivity as S, trace as T      # noqa: E402


def _made_from(x):
    a = T.step("toy.a", x, "unit", "an input", grade="assumed")
    b = T.step("toy.b", 2.0, "unit", "another input", grade="transcribed")
    return T.step("toy.c", a * b, "unit", "made from both", uses=["toy.a", "toy.b"])


def test_a_push_moves_the_step_and_everything_made_from_it():
    assert _made_from(3.0) == 6.0
    with T.pushed("toy.a", 1.5) as hits:
        assert _made_from(3.0) == pytest.approx(9.0)
    assert hits == [True]
    assert _made_from(3.0) == 6.0                       # gone once the block ends


def test_a_push_works_with_a_recording_open_and_records_the_pushed_value():
    with T.recording() as rec, T.pushed("toy.b", 0.5):
        assert _made_from(3.0) == pytest.approx(3.0)
    assert rec.steps["toy.b"].value == pytest.approx(1.0)


def test_a_push_on_a_key_nobody_records_hits_nothing_and_a_flag_is_not_scaled():
    with T.pushed("toy.nothing", 2.0) as hits:
        _made_from(3.0)
    assert hits == []
    with T.pushed("toy.flag", 2.0) as hits:
        assert T.step("toy.flag", True, "yes/no", "a flag") is True
    assert hits == [False]


def test_pushes_nest_and_each_moves_its_own_step():
    """Bundles (fixed_choice_checks.BUNDLES, 18 Nov 2026) push several inputs at once."""
    with T.pushed("toy.a", 1.5) as ha, T.pushed("toy.b", 0.5) as hb:
        assert _made_from(3.0) == pytest.approx(4.5)     # 4.5 * 1.0
    assert ha == [True] and hb == [True]
    with T.pushed("toy.a", 2.0), T.pushed("toy.a", 2.0):
        assert _made_from(3.0) == pytest.approx(24.0)    # the same key twice takes both
    assert _made_from(3.0) == 6.0


def test_a_push_scales_arrays():
    with T.pushed("toy.series", 2.0):
        v = T.step("toy.series", np.array([1.0, 2.0]), "unit", "a series")
    assert v.tolist() == [2.0, 4.0]


def test_parse_push():
    assert S.parse_push("cost.fuel_cell.capex_per_kW*1.5") == ("cost.fuel_cell.capex_per_kW", 1.5)
    assert S.parse_push("a.b*c*0.5") == ("a.b*c", 0.5)
    for bad in ("no-factor", "*1.5", "key*0", "key*-1", "key*inf"):
        with pytest.raises(ValueError):
            S.parse_push(bad)


def test_the_screened_sweep_drops_the_bought_hydrogen_knobs_where_none_is_bought():
    islanded, green = S.CASES["islanded_h2"], S.CASES["norfolk_grid_green"]
    assert islanded.h2_colour is None and green.h2_colour == "green"
    iv, gv = S.shaky_variants(islanded), S.shaky_variants(green)
    assert iv[0] == {} and gv[0] == {}                   # central first
    pushes = lambda vs: {v["push"] for v in vs if "push" in v}
    assert not any(p.startswith("cost.bought_h2") for p in pushes(iv))
    assert not any("green_h2_grid_share" in v for v in iv)
    assert {p for p in pushes(gv) if p.startswith("cost.bought_h2")} == {
        "cost.bought_h2.green.delivered*0.5", "cost.bought_h2.green.delivered*1.5"}
    assert any("green_h2_grid_share" in v for v in gv)
    for p in pushes(gv):
        S.parse_push(p)                                    # every push is well formed
