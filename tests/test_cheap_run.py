"""The cheap run (4 Nov 2026): the price-list switches relaxed to fractions,
pruning on the relaxed shares, and the loose gap through the frontier — on
the toy model of test_connection_choice.py (no register, no Brightway)."""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from optimisation import dc_model as M, dc_pareto as P      # noqa: E402
import test_connection_choice as TC                         # noqa: E402

pytest.importorskip("linopy")


def test_relaxed_switches_are_fractions_and_the_problem_has_no_binaries():
    s = TC._series(7.31, TC.GROUPS)
    t = TC._tech(connection_options=(TC.SMALL, TC.LARGE))
    m, V, _ = M.build_model(s, M.Assets(grid=True), t, objective="cost", relax_switches=True)
    assert len(m.binaries) == 0
    M.solve(m)
    on = [float(V[f"on_{i}"].solution) for i in range(2)]
    assert sum(on) == pytest.approx(1.0) and all(-1e-9 <= x <= 1 + 1e-9 for x in on)
    m2, _, _ = M.build_model(s, M.Assets(grid=True), t, objective="cost")
    assert len(m2.binaries) == 2


def test_pruning_prices_each_list_whole_and_keeps_the_best_at_either_anchor():
    s = TC._series(7.31, TC.GROUPS)
    t = TC._tech(connection_options=(TC.SMALL, TC.LARGE))
    t2, rep = P.prune_options(s, M.Assets(grid=True), t)
    assert set(rep["per_list"]) == {"small", "large"}
    assert all({"cost", "gwp"} <= set(v) for v in rep["per_list"].values())
    # 7.31 MW does not fit the small list: it cannot serve the load, so the large one is the only survivor
    assert rep["per_list"]["small"]["cost"] == float("inf") or rep["per_list"]["small"]["cost"] > rep["per_list"]["large"]["cost"]
    assert "large" in rep["kept"]
    # the cost minimum over the lists is the full solve's cost minimum
    full = P.front(s, M.Assets(grid=True), t, points=1)
    best = min(v["cost"] for v in rep["per_list"].values())
    assert abs(best - full["min_cost"]["cost_GBP_per_year"]) / full["min_cost"]["cost_GBP_per_year"] < 1e-4
    # asking for a dropped key keeps it
    t3, rep3 = P.prune_options(s, M.Assets(grid=True), t, keep_keys=["small", "large"])
    assert rep3["kept"] == ["small", "large"] and not rep3["pruned"]
    assert M.connection_options_of(t3) == M.connection_options_of(t)
    # one option is nothing to prune
    t4, rep4 = P.prune_options(s, M.Assets(grid=True), TC._tech(connection_options=(TC.LARGE,)))
    assert not rep4["pruned"] and t4 is not None


def test_the_pruned_frontier_matches_the_full_one_when_nothing_real_is_dropped():
    s = TC._series(7.31, TC.GROUPS)
    t = TC._tech(connection_options=(TC.SMALL, TC.LARGE))
    full = P.front(s, M.Assets(grid=True), t, points=1)
    t2, rep = P.prune_options(s, M.Assets(grid=True), t)
    cheap = P.front(s, M.Assets(grid=True), t2, points=1, mip_rel_gap=M.LOOSE_MIP_REL_GAP)
    assert cheap["min_cost"]["cost_GBP_per_year"] <= full["min_cost"]["cost_GBP_per_year"] * (1 + M.LOOSE_MIP_REL_GAP + 1e-9)
    assert cheap["min_cost"]["connection_option"] == full["min_cost"]["connection_option"]


def test_the_loose_gap_is_within_its_bound_of_the_tight_answer():
    s = TC._series(7.31, TC.GROUPS)
    t = TC._tech(connection_options=(TC.SMALL, TC.LARGE))
    tight = P.front(s, M.Assets(grid=True), t, points=1)
    loose = P.front(s, M.Assets(grid=True), t, points=1, mip_rel_gap=M.LOOSE_MIP_REL_GAP)
    a, b = tight["min_cost"]["cost_GBP_per_year"], loose["min_cost"]["cost_GBP_per_year"]
    assert b >= a * (1 - 1e-9) and b <= a * (1 + M.LOOSE_MIP_REL_GAP + 1e-9)
