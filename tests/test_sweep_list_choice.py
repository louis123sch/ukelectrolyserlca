"""How a sweep treats a choice of price lists (5 Nov 2026): ``fixed`` solves the central variant
with every list at the loose gap and the rest on the list it chose, ``pruned`` prices the lists
alone per variant and keeps the survivors, ``full`` is the old tight-gap run. The helpers on the
toy model of test_connection_choice.py; the end-to-end on North Norfolk over two June days."""
import pathlib
import sys
from dataclasses import replace

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from optimisation import dc_model as M, sensitivity as S      # noqa: E402
import test_connection_choice as TC                          # noqa: E402

pytest.importorskip("linopy")


def test_restrict_keeps_the_named_lists_in_order_and_is_a_no_op_otherwise():
    t = TC._tech(connection_options=(TC.SMALL, TC.LARGE))
    assert [o.key for o in S._restrict(t, ["large"]).connection_options] == ["large"]
    assert [o.key for o in S._restrict(t, ["large", "small"]).connection_options] == ["small", "large"]
    assert S._restrict(t, ["nothing"]) is t                    # nothing named survives: unchanged, not empty
    one = TC._tech(connection_options=(TC.LARGE,))
    assert S._restrict(one, ["small"]) is one
    assert S._restrict(TC._tech(), ["large"]).connection_options in (None, ())


def test_the_gap_is_loose_for_a_sweep_s_choice_and_absent_with_one_list():
    two = TC._tech(connection_options=(TC.SMALL, TC.LARGE))
    assert S._gap(two, "fixed") == M.LOOSE_MIP_REL_GAP
    assert S._gap(two, "pruned") == M.LOOSE_MIP_REL_GAP
    assert S._gap(two, "full") is None
    for choice in S.LIST_CHOICES:
        assert S._gap(TC._tech(connection_options=(TC.LARGE,)), choice) is None
        assert S._gap(TC._tech(), choice) is None


def test_lists_chosen_is_first_seen_order_without_blanks():
    rows = [{"connection_option": "b"}, {"connection_option": None}, {"connection_option": "a"},
            {"connection_option": "b"}, {"connection_option": float("nan")}, {}]
    assert S._lists_chosen(rows) == ["b", "a"]


def test_a_bad_list_choice_fails_at_once(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "OUT_DIR", tmp_path)
    with pytest.raises(ValueError, match="list_choice"):
        S.run("islanded_h2", [{}], name="t", list_choice="loose")


@pytest.fixture(scope="module")
def norfolk_days():
    return replace(S.CASES["norfolk_150_room"], start="2025-06-02", end="2025-06-04")


def test_fixed_solves_the_central_variant_on_every_list_and_the_rest_on_its_choice(tmp_path, monkeypatch, norfolk_days):
    monkeypatch.setattr(S, "OUT_DIR", tmp_path)
    df = S.run(norfolk_days, [{"connection_build_scale": 1.5}, {}], name="t", progress=None)
    central, other = df[df.variant == "central"], df[df.variant != "central"]
    assert list(df.variant[:2]) == ["central", "central"]            # the central variant first, wherever it was given
    n = int(central.connection_lists_solved.iloc[0])
    assert n > 1 and (central.mip_rel_gap == M.LOOSE_MIP_REL_GAP).all()
    chosen = S._lists_chosen(central.to_dict("records"))
    assert chosen and (other.connection_lists_solved == len(chosen)).all()
    assert set(other.connection_option) <= set(chosen)
    if len(chosen) == 1:
        assert other.mip_rel_gap.isna().all()                       # one list: no switches, no gap
    assert (df.list_choice == "fixed").all() and df.connection_lists_dropped.isna().all()


def test_fixed_resumes_from_the_central_rows_in_the_file(tmp_path, monkeypatch, norfolk_days):
    monkeypatch.setattr(S, "OUT_DIR", tmp_path)
    S.run(norfolk_days, [{}], name="t", progress=None)
    first = pd.read_csv(tmp_path / "sensitivity_t.csv")
    df = S.run(norfolk_days, [{"connection_build_scale": 0.5}], name="t", progress=None, resume=True)
    assert len(df) == 4
    assert df[df.variant == "central"].solve_s.tolist() == first.solve_s.tolist()    # not solved again
    other = df[df.variant != "central"]
    assert (other.connection_lists_solved == len(S._lists_chosen(first.to_dict("records")))).all()


def test_pruned_prices_each_list_alone_and_records_what_it_dropped(tmp_path, monkeypatch, norfolk_days):
    monkeypatch.setattr(S, "OUT_DIR", tmp_path)
    df = S.run(norfolk_days, [{}], name="t", progress=None, list_choice="pruned")
    assert (df.list_choice == "pruned").all()
    assert "connection_lists_dropped" in df
    # survivors are what the frontier is solved over; the gap is loose only if more than one survived
    n = df.connection_lists_solved
    assert ((n > 1) == (df.mip_rel_gap == M.LOOSE_MIP_REL_GAP)).all()


def test_full_is_every_list_at_the_tight_gap(tmp_path, monkeypatch, norfolk_days):
    monkeypatch.setattr(S, "OUT_DIR", tmp_path)
    df = S.run(norfolk_days, [{}], name="t", progress=None, objectives=("cost",), list_choice="full")
    assert int(df.connection_lists_solved.iloc[0]) > 1 and df.mip_rel_gap.isna().all()
    assert (df.list_choice == "full").all()


def test_the_sweeps_defaults_are_fixed_except_the_connection_test():
    import inspect
    assert inspect.signature(S.run).parameters["list_choice"].default == "fixed"
    assert inspect.signature(S.assumptions).parameters["list_choice"].default == "fixed"
    assert inspect.signature(S.connection).parameters["list_choice"].default == "pruned"
