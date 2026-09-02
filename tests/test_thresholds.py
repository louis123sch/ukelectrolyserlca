"""The threshold search: bracketing, bisection, and the knob transforms.

Pure arithmetic — no LP, no Brightway. The search is driven against synthetic
step functions whose tipping point is known exactly, which is the only way to
tell a converged answer from a plausible one. Whether the LP itself is right is
test_dc_model's job.
"""
import json
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "/Users/louis/lca-ai-project/ukelectrolyserlca")
from optimisation import dc_model as M
from optimisation import thresholds as T


# --------------------------------------------------------------------------
#                               the knob table
# --------------------------------------------------------------------------
def test_every_knob_is_internally_consistent():
    for name, k in T.KNOBS.items():
        assert k.name == name
        assert k.mode in ("multiplier", "absolute")
        assert k.sense in ("down", "up")
        assert k.fields, f"{name} moves nothing"
        assert k.floor < k.ceiling
        # The base case must sit inside the range the search may explore, or
        # bracketing starts outside its own bounds.
        base = 1.0 if k.mode == "multiplier" else None
        if base is not None:
            assert k.floor <= base <= k.ceiling


def test_default_knobs_all_exist():
    assert set(T.DEFAULT_KNOBS) <= set(T.KNOBS)


def test_grid_price_level_is_not_a_knob():
    """Deliberate: a price *level* is not monotone in hydrogen's favour."""
    assert "grid_price" not in T.KNOBS
    assert "price_spread" in T.KNOBS


# --------------------------------------------------------------------------
#                              applying a knob
# --------------------------------------------------------------------------
def _tech(**kw):
    fields = {f: 1.0 for f in M.Tech.__dataclass_fields__ if f != "labels"}
    fields.update(kw)
    return M.Tech(**fields)


def _series(price, n=8):
    return M.Series(index=pd.date_range("2025-01-01", periods=n, freq="h"),
                    dt_hours=1.0, demand_mw=np.ones(n), cf_wind=np.zeros(n),
                    cf_solar=np.zeros(n), grid_gwp_per_mwh=np.zeros(n),
                    grid_price_per_mwh=np.asarray(price, dtype=float))


def test_multiplier_scales_every_field_it_names():
    tech = _tech(cost_ely=100.0, cost_tank=10.0, cost_fc=200.0,
                 cost_fc_stack_per_mw=50.0)
    out, _ = T.apply(T.KNOBS["h2_chain"], 0.25, tech, _series([1, 2]))
    assert out.cost_ely == 25.0 and out.cost_tank == 2.5
    assert out.cost_fc == 50.0 and out.cost_fc_stack_per_mw == 12.5


def test_multiplier_leaves_untouched_fields_alone():
    tech = _tech(cost_ely=100.0, cost_batt_p=7.0)
    out, _ = T.apply(T.KNOBS["ely_capex"], 0.5, tech, _series([1, 2]))
    assert out.cost_ely == 50.0 and out.cost_batt_p == 7.0


def test_absolute_sets_the_coefficient_itself():
    tech = _tech(bought_h2_gbp_per_kg=4.93)
    out, _ = T.apply(T.KNOBS["h2_price"], 1.5, tech, _series([1, 2]))
    assert out.bought_h2_gbp_per_kg == 1.5


def test_h2_price_does_not_touch_the_carbon_side():
    """Sweeping a price must not silently make the hydrogen cleaner too."""
    tech = _tech(bought_h2_gbp_per_kg=4.93, bought_h2_gwp_per_kg=2.5)
    out, _ = T.apply(T.KNOBS["h2_price"], 0.5, tech, _series([1, 2]))
    assert out.bought_h2_gwp_per_kg == 2.5


def test_price_spread_holds_the_mean_and_scales_deviations():
    s = _series([10.0, 30.0, 50.0, 70.0])          # mean 40
    _, out = T.apply(T.KNOBS["price_spread"], 2.0, _tech(), s)
    assert out.grid_price_per_mwh.mean() == pytest.approx(40.0)
    assert out.grid_price_per_mwh.tolist() == [-20.0, 20.0, 60.0, 100.0]


def test_price_spread_of_one_is_the_identity():
    s = _series([10.0, 30.0, 50.0, 70.0])
    _, out = T.apply(T.KNOBS["price_spread"], 1.0, _tech(), s)
    np.testing.assert_allclose(out.grid_price_per_mwh, s.grid_price_per_mwh)


def test_apply_is_pure():
    """Probes run in a loop over one prepared tech — mutation would compound."""
    tech, s = _tech(cost_ely=100.0), _series([10.0, 30.0])
    T.apply(T.KNOBS["ely_capex"], 0.1, tech, s)
    T.apply(T.KNOBS["price_spread"], 5.0, tech, s)
    assert tech.cost_ely == 100.0
    assert s.grid_price_per_mwh.tolist() == [10.0, 30.0]


def test_baseline_value_is_one_for_multipliers_and_the_coefficient_otherwise():
    tech = _tech(bought_h2_gbp_per_kg=4.93, cost_ely=212510.0)
    assert T.baseline_value(T.KNOBS["ely_capex"], tech) == 1.0
    assert T.baseline_value(T.KNOBS["h2_price"], tech) == 4.93


# --------------------------------------------------------------------------
#                          bracketing and bisection
# --------------------------------------------------------------------------
def _step(cut, sense="down", share=0.05):
    """A knob whose hydrogen share switches on at ``cut``. Counts its calls."""
    calls = []

    def f(x):
        calls.append(x)
        on = x <= cut if sense == "down" else x >= cut
        return {"value": x, "h2_share_of_load": share if on else 0.0}
    f.calls = calls
    return f


def _find(f, knob_name, base, **kw):
    kw.setdefault("target", T.ENTRY_SHARE)
    kw.setdefault("rel_tol", 0.02)
    kw.setdefault("max_expand", 12)
    kw.setdefault("progress", None)
    return T._bracket_and_bisect(f, T.KNOBS[knob_name], base, **kw)


def test_downward_knob_converges_on_the_true_cut():
    r = _find(_step(0.3), "h2_chain", 1.0)
    assert r["status"] == "found"
    assert r["threshold"] == pytest.approx(0.3, rel=0.03)


def test_upward_knob_converges_on_the_true_cut():
    r = _find(_step(6.0, sense="up"), "price_spread", 1.0)
    assert r["status"] == "found"
    assert r["threshold"] == pytest.approx(6.0, rel=0.03)


def test_the_returned_threshold_is_a_value_that_actually_worked():
    """A threshold on the failing side of the step would be quoted as viable."""
    f = _step(0.3)
    r = _find(f, "h2_chain", 1.0)
    assert f(r["threshold"])["h2_share_of_load"] >= T.ENTRY_SHARE


def test_bracket_straddles_the_cut():
    r = _find(_step(0.3), "h2_chain", 1.0)
    lo, hi = r["bracket"]
    assert lo <= 0.3 <= hi


def test_tighter_tolerance_costs_more_solves_and_gets_closer():
    loose = _find(_step(0.3), "h2_chain", 1.0, rel_tol=0.2)
    tight = _find(_step(0.3), "h2_chain", 1.0, rel_tol=0.001)
    assert len(tight["curve"]) > len(loose["curve"])
    assert abs(tight["threshold"] - 0.3) < abs(loose["threshold"] - 0.3)


def test_already_viable_short_circuits_after_one_solve():
    r = _find(_step(2.0), "h2_chain", 1.0)          # cut is above the base case
    assert r["status"] == "already_viable"
    assert r["threshold"] == 1.0 and len(r["curve"]) == 1


def test_unreachable_knob_says_so_rather_than_guessing():
    r = _find(_step(1e-9), "h2_chain", 1.0)
    assert r["status"] == "not_reached" and r["threshold"] is None
    assert r["limit_is_floor"] and r["limit_tried"] == T.KNOBS["h2_chain"].floor


def test_not_reached_reports_what_was_probed_not_the_configured_floor():
    """With a short search the floor is never tried; saying it was is a lie."""
    r = _find(_step(1e-9), "h2_chain", 1.0, max_expand=3)
    assert r["status"] == "not_reached"
    assert not r["limit_is_floor"]
    assert r["limit_tried"] == pytest.approx(0.125)      # 1 -> .5 -> .25 -> .125
    assert r["limit_tried"] == min(r["curve"][i]["value"] for i in range(len(r["curve"])))


def test_search_stops_at_the_floor_rather_than_probing_past_it():
    r = _find(_step(1e-9), "h2_chain", 1.0)
    assert min(p["value"] for p in r["curve"]) >= T.KNOBS["h2_chain"].floor


def test_every_probe_is_kept_in_the_curve():
    f = _step(0.3)
    r = _find(f, "h2_chain", 1.0)
    assert [p["value"] for p in r["curve"]] == f.calls


def test_progress_is_called_once_per_solve():
    seen = []
    f = _step(0.3)
    r = _find(f, "h2_chain", 1.0, progress=seen.append)
    assert len(seen) == len(r["curve"])


# --------------------------------------------------------------------------
#                             the monotonicity guard
# --------------------------------------------------------------------------
def _curve(pairs):
    return [{"value": v, "h2_share_of_load": s} for v, s in pairs]


def test_a_clean_downward_curve_is_monotone():
    c = _curve([(1.0, 0.0), (0.5, 0.0), (0.25, 0.4), (0.375, 0.2)])
    assert T._check_monotone(c, T.KNOBS["h2_chain"])


def test_a_curve_that_doubles_back_is_flagged():
    c = _curve([(1.0, 0.0), (0.5, 0.3), (0.25, 0.1)])
    assert not T._check_monotone(c, T.KNOBS["h2_chain"])


def test_the_guard_respects_the_knob_sense():
    rising = _curve([(1.0, 0.0), (2.0, 0.2), (4.0, 0.5)])
    assert T._check_monotone(rising, T.KNOBS["price_spread"])
    assert not T._check_monotone(rising, T.KNOBS["h2_chain"])


def test_solver_noise_does_not_trip_the_guard():
    """Capacities come back as -1e-15; that is zero, not a reversal."""
    c = _curve([(1.0, -1.6e-15), (0.5, 0.0), (0.25, 3e-16)])
    assert T._check_monotone(c, T.KNOBS["h2_chain"])


# --------------------------------------------------------------------------
#                                  reporting
# --------------------------------------------------------------------------
def _result(**kw):
    r = {"status": "found", "threshold": 0.3, "baseline_value": 1.0,
         "bracket": [0.29, 0.31], "curve": _curve([(1.0, 0.0), (0.3, 0.4)]),
         "scenario": "21_res_h2_grid_pem_free", "knob": "h2_chain",
         "knob_label": "Whole H2 chain annualised cost", "unit": "x today",
         "sense": "down", "ratio_to_today": 0.3, "target_share": 0.01,
         "monotone": True, "solves": 2, "solve_seconds": 12.0}
    r.update(kw)
    return r


def test_table_reads_a_downward_threshold_as_a_discount():
    row = T.table([_result()]).iloc[0]
    assert row["needs"] == "70 % cheaper"


def test_table_reads_an_upward_threshold_as_a_multiple():
    row = T.table([_result(knob="batt_capex", sense="up", threshold=3.4,
                           ratio_to_today=3.4)]).iloc[0]
    assert row["needs"] == "3.4x dearer"


def test_table_leaves_an_unfound_threshold_blank_rather_than_zero():
    row = T.table([_result(status="not_reached", threshold=None,
                           ratio_to_today=None)]).iloc[0]
    assert row["threshold"] is None and row["needs"] is None


def test_describe_covers_every_status():
    for r in (_result(),
              _result(status="already_viable"),
              _result(status="not_reached", threshold=None, limit_tried=0.01,
                      limit_is_floor=True, ratio_to_today=None),
              {"status": "not_applicable", "knob": "batt_capex",
               "reason": "cannot build battery"}):
        assert isinstance(T.describe(r), str) and T.describe(r)


def test_describe_warns_when_the_curve_is_not_monotone():
    assert "NON-MONOTONE" in T.describe(_result(monotone=False))
    assert "NON-MONOTONE" not in T.describe(_result(monotone=True))


def test_curve_frame_is_sorted_by_knob_value():
    df = T.curve_frame(_result(curve=_curve([(1.0, 0.0), (0.25, 0.4), (0.5, 0.0)])))
    assert df["value"].tolist() == [0.25, 0.5, 1.0]


def test_curve_frame_of_an_unprobed_result_is_empty_not_an_error():
    assert T.curve_frame({"curve": []}).empty


# --------------------------------------------------------------------------
#                     inheriting a solved run's settings
# --------------------------------------------------------------------------
def _config(tmp_path, **over):
    """A config.json shaped like the one dc_runner writes."""
    cfg = {
        "scenario": {"n": 0, "architecture": "custom", "label": "grid + PEM + tank + FC",
                     "ely_tech": "PEM operation", "h2_colour": None, "strategy": "free",
                     "tank_design": None, "note": "",
                     "assets": {"grid": True, "wind": False, "offshore_wind": False,
                                "solar": False, "battery": False, "electrolyser": True,
                                "tank": True, "fuel_cell": True, "buy_h2": False}},
        "site": {"key": "r13_51.5074_-0.1278", "name": "Central London",
                 "lat": 51.5074, "lon": -0.1278, "carbon_api_region": 13,
                 "tnuos_zone": 12, "tdr_band": "EHV2",
                 "connection_limit_mw": 10.965, "connection_headroom": 1.5,
                 "transmission_connected": False},
        "start": "2025-01-01", "end": "2025-12-29",
        "size_mw_it": 7.31, "pue": 1.0, "resample_hours": 1.0,
        "points": 12, "cost_case": "high", "horizon_years": 25.0,
        "unserved_fraction": 0.0,
        "coefficients": __import__("optimisation.dc_runner", fromlist=["x"])
                        ._coefficient_identity(),
    }
    cfg.update(over)
    folder = tmp_path / "00_custom_getf_pem_free"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "config.json").write_text(json.dumps(cfg))
    return folder


def test_from_run_inherits_every_setting_that_moves_a_threshold(tmp_path):
    got = T.from_run(_config(tmp_path))
    kw = got["kwargs"]
    assert kw["start"] == "2025-01-01" and kw["end"] == "2025-12-29"
    assert kw["size_mw_it"] == 7.31 and kw["pue"] == 1.0
    assert kw["cost_case"] == "high"          # not the "central" default
    assert kw["resample_hours"] == 1.0
    assert kw["horizon_years"] == 25.0


def test_from_run_pins_the_derived_band_and_connection(tmp_path):
    """run_one rewrites both to what it was charged; a threshold must match it."""
    site = T.from_run(_config(tmp_path))["kwargs"]["site"]
    assert site.tdr_band == "EHV2"
    assert site.connection_limit_mw == 10.965
    assert (site.lat, site.lon) == (51.5074, -0.1278)
    assert site.carbon_api_region == 13


def test_from_run_flags_a_front_that_predates_a_model_change(tmp_path):
    folder = _config(tmp_path, coefficients={"dc_model.py": "0000deadbeef"})
    got = T.from_run(folder)
    assert got["stale"] and "dc_model.py" in got["stale_keys"]


def test_from_run_is_not_stale_against_the_current_code(tmp_path):
    got = T.from_run(_config(tmp_path))
    assert not got["stale"], got["stale_keys"]


def test_from_run_survives_a_config_written_by_an_older_scenario(tmp_path):
    """Old folders outlive field changes; dropping the unknown beats crashing."""
    folder = _config(tmp_path)
    cfg = json.loads((folder / "config.json").read_text())
    cfg["scenario"]["some_field_we_removed"] = "x"
    (folder / "config.json").write_text(json.dumps(cfg))
    assert T.from_run(folder)["scenario"].architecture == "custom"


def test_run_key_matches_the_dc_runs_convention(tmp_path):
    site = T.from_run(_config(tmp_path))["kwargs"]["site"]
    assert T.run_key(site, 7.31, "2025-01-01") == "r13_51.5074_-0.1278_7.31MW_2025"


# --------------------------------------------------------------------------
#                          which knobs can be asked
# --------------------------------------------------------------------------
def _scen(**flags):
    from optimisation import dc_architectures as A
    base = {k: False for k in A.ASSET_FLAGS}
    base.update(flags)
    return A.Scenario(n=0, architecture="custom", label="t", assets=base,
                      h2_colour=flags.pop("_colour", None))


def test_a_configuration_without_a_battery_is_not_offered_the_battery_knob():
    ks = T.applicable_knobs(_scen(grid=True, electrolyser=True, tank=True,
                                  fuel_cell=True))
    assert "batt_capex" not in ks and "h2_chain" in ks


def test_buying_needs_a_priced_colour_before_the_price_knob_appears():
    from optimisation import dc_architectures as A
    flags = {k: False for k in A.ASSET_FLAGS}
    flags.update(grid=True, fuel_cell=True, buy_h2=True)
    unpriced = A.Scenario(n=0, architecture="custom", label="t", assets=flags)
    priced = A.Scenario(n=0, architecture="custom", label="t", assets=flags,
                        h2_colour="grey")
    assert "h2_price" not in T.applicable_knobs(unpriced)
    assert "h2_price" in T.applicable_knobs(priced)


def test_price_spread_needs_nothing_and_is_always_offered():
    assert "price_spread" in T.applicable_knobs(_scen(grid=True))


def test_estimate_is_a_whole_number_of_solves_per_knob():
    assert T.estimate_solves([]) == 0
    assert T.estimate_solves(["h2_chain"]) == 9
    assert T.estimate_solves(["h2_chain", "ely_capex"]) == 18


# --------------------------------------------------------------------------
#                       reading results back off disk
# --------------------------------------------------------------------------
def test_records_writes_a_missing_threshold_as_null_not_nan():
    """json.dumps emits bare NaN, which most readers reject."""
    rows = T.records([_result(status="not_reached", threshold=None,
                              ratio_to_today=None)])
    assert rows[0]["threshold"] is None and rows[0]["needs"] is None
    assert "NaN" not in json.dumps(rows)


def test_load_run_reads_the_knob_files_and_skips_the_job_files(tmp_path):
    d = tmp_path / "00_custom"
    d.mkdir(parents=True)
    (d / "h2_chain.json").write_text(json.dumps(_result()))
    (d / "status.json").write_text(json.dumps({"state": "done"}))
    (d / "config.json").write_text(json.dumps({"start": "2025-01-01"}))
    (d / "summary.json").write_text(json.dumps({"kind": "thresholds"}))
    got = T.load_run(tmp_path, "00_custom")
    assert [r["knob"] for r in got] == ["h2_chain"]


def test_load_run_ignores_a_file_that_is_not_a_threshold(tmp_path):
    d = tmp_path / "00_custom"
    d.mkdir(parents=True)
    (d / "notes.json").write_text(json.dumps({"hello": "world"}))
    (d / "broken.json").write_text("{not json")
    assert T.load_run(tmp_path, "00_custom") == []


def test_load_run_without_a_scenario_reads_every_scenario(tmp_path):
    for key in ("00_a", "00_b"):
        d = tmp_path / key
        d.mkdir(parents=True)
        (d / "h2_chain.json").write_text(json.dumps(_result(scenario=key)))
    assert len(T.load_run(tmp_path)) == 2
