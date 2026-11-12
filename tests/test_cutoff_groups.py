"""Rule 3 one group or one item at a time (11 Nov 2026): cutoff="upper:<field or flow>"
adds only the still-excluded entries named, on top of what the central mode carries."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from optimisation import dc_inputs as I              # noqa: E402
from optimiser_lca import exclusions as X            # noqa: E402
from test_dc_model import tech                       # noqa: E402,F401 - the two-week fixture


def _added(t, mode):
    return I.with_cutoff(t, mode).labels["cutoff_added"]


def _excluded():
    return [e for e in X.REGISTER if e.kind == "cutoff" and e.status == "excluded"
            and e.estimate("upper") is not None]


def test_groups_add_up_to_the_whole(tech):
    central, upper = _added(tech, "central"), _added(tech, "upper")
    fields = {I.CUTOFF_FIELD[(e.technology, e.side)] for e in _excluded()}
    assert fields
    for f in fields:
        one = _added(tech, f"upper:{f}")
        for k in set(upper) | set(central):
            want = upper.get(k, 0.0) if k == f else central.get(k, 0.0)
            assert one.get(k, 0.0) == pytest.approx(want, abs=1e-6), (f, k)


def test_a_single_flow_adds_only_its_own_estimate(tech):
    e = _excluded()[0]
    f = I.CUTOFF_FIELD[(e.technology, e.side)]
    central = _added(tech, "central")
    one = _added(tech, f"upper:{e.flow}")
    assert one.get(f, 0.0) - central.get(f, 0.0) == pytest.approx(e.estimate("upper"), rel=1e-6)


def test_an_unknown_name_is_refused(tech):
    with pytest.raises(ValueError):
        I.with_cutoff(tech, "upper:no such flow")
    with pytest.raises(ValueError):
        I.with_cutoff(tech, "upper:")
    with pytest.raises(ValueError):
        I.with_cutoff(tech, "lower")
