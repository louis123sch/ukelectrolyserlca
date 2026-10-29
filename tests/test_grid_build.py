"""grid_build — the Python replacement for notebooks 3.1 and 5.

The contract that matters is continuity: every grid and price series already on
disk was written by the notebooks, and ``profiles.py`` finds them by file name
and reads them by column. So these tests pin the names, the parsing of both API
response shapes, and — where Brightway is available — that re-scoring an
existing file's own fuel mix reproduces its ``custom_electricity_score``.
"""
import pathlib
import sys

import pandas as pd
import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from optimisation import grid_build as G

# The basis id every grid series on disk carries. Changes whenever anything in
# optimiser_lca.grid that moves a score does — then rescore and update this.
GRID_BASIS_ID = "055e53f4b11b"


# -----------------------------------------------------------------------------
# File names: what profiles.py globs for, and what is already on disk
# -----------------------------------------------------------------------------
def test_grid_file_name_matches_the_notebooks():
    assert G.grid_csv_name(13, "2025-01-01 00:00:00", "2025-12-29 00:00:00") == (
        "custom_grid_lca_carbon_api_regional_auto_r13_cheap_"
        "2025-01-01T00-00-00T_to_T2025-12-29T00-00-00.csv")


def test_price_file_names_match_the_notebooks():
    raw, clean = G.price_csv_names("2025-01-01 00:00:00", "2025-12-29 00:00:00")
    assert clean == "elexon_market_index_clean_2025-01-01_00-00-00_to_2025-12-29_00-00-00.csv"
    assert raw == "elexon_market_index_raw_2025-01-01_00-00-00_to_2025-12-29_00-00-00.csv"
    assert not set('<>:"/\\|?*') & set(clean)


def test_existing_files_follow_the_same_names():
    on_disk = {p.name for p in (REPO / "custom_grid_lca_outputs").glob("*_r13_cheap_2025-01-01T*")}
    assert G.grid_csv_name(13, "2025-01-01 00:00:00", "2025-12-29 00:00:00") in on_disk


# -----------------------------------------------------------------------------
# Carbon Intensity API parsing
# -----------------------------------------------------------------------------
_REC = {"from": "2025-06-02T00:00Z", "to": "2025-06-02T00:30Z",
        "intensity": {"forecast": 120, "index": "moderate"},
        "generationmix": [{"fuel": "gas", "perc": 40.0}, {"fuel": "wind", "perc": 60.0}]}


def test_records_from_the_region_shape():
    payload = {"data": [{"regionid": 13, "shortname": "London", "data": [_REC]}]}
    recs, name = G._records(payload, 13)
    assert recs == [_REC] and name == "London"


def test_records_from_the_bare_dict_shape():
    payload = {"data": {"regionid": 13, "shortname": "London", "data": [_REC]}}
    recs, _ = G._records(payload, 13)
    assert recs == [_REC]


def test_records_from_the_timeslice_shape():
    payload = {"data": [{"from": _REC["from"], "to": _REC["to"], "regions": [
        {"regionid": 1, "shortname": "North Scotland", "intensity": {}, "generationmix": []},
        {"regionid": 13, "shortname": "London", "intensity": _REC["intensity"],
         "generationmix": _REC["generationmix"]}]}]}
    recs, name = G._records(payload, 13)
    assert name == "London" and recs[0]["generationmix"] == _REC["generationmix"]


def test_api_times_stay_utc():
    # Grid, price and weather share one clock: naive UTC. 00:00Z on 2 June is
    # 00:00 in the series, not 01:00 BST as the notebook wrote it.
    assert G._api_z(G._utc("2025-06-02 00:00:00")) == "2025-06-02T00:00Z"
    payload = {"data": [{"regionid": 13, "shortname": "London", "data": [_REC]}]}
    recs, _ = G._records(payload, 13)
    assert pd.to_datetime(recs[0]["from"], utc=True).tz_localize(None) == pd.Timestamp("2025-06-02 00:00")


def test_old_local_clock_files_are_ignored(tmp_path):
    from optimisation import profiles
    old = tmp_path / "old.csv"
    pd.DataFrame({"datetime": ["2025-06-02 00:00:00"], "custom_electricity_score": [0.1]}).to_csv(old, index=False)
    new = tmp_path / "new.csv"
    pd.DataFrame({"datetime": ["2025-06-02 00:00:00"], "custom_electricity_score": [0.1],
                  "clock": ["UTC"]}).to_csv(new, index=False)
    assert not profiles.grid_file_is_utc(old)
    assert profiles.grid_file_is_utc(new)


def test_duos_bands_follow_the_uk_clock():
    """Amber starts at 07:00 on the UK clock: 06:00 UTC in summer, 07:00 in winter."""
    from optimisation import network_charges as nc
    summer = pd.DatetimeIndex(["2025-07-02 05:30", "2025-07-02 06:00"])   # Wednesday, BST
    winter = pd.DatetimeIndex(["2025-01-08 06:30", "2025-01-08 07:00"])   # Wednesday, GMT
    assert list(nc.duos_band(summer)) == ["green", "amber"]
    assert list(nc.duos_band(winter)) == ["green", "amber"]
    # Red runs all year: 16:00 UK clock is 16:00 UTC in January, 15:00 UTC in July.
    assert nc.duos_band(pd.DatetimeIndex(["2025-01-08 16:00"])).iloc[0] == "red"
    assert nc.duos_band(pd.DatetimeIndex(["2025-07-02 15:00"])).iloc[0] == "red"


def test_settlement_periods_count_from_uk_midnight():
    raw = pd.DataFrame({"settlementDate": ["2025-07-02"], "settlementPeriod": [1],
                        "price": [50.0], "dataProvider": ["APXMIDP"]})
    # SP1 on a BST day starts at 00:00 BST = 23:00 UTC the previous day.
    assert G.normalise_elexon(raw)["DATETIME"].iloc[0] == pd.Timestamp("2025-07-01 23:00")


def test_chunks_cover_the_window_without_gaps():
    chunks = list(G._chunks("2025-01-01 00:00:00", "2025-02-15 00:00:00"))
    assert all(b == c for (_, b), (c, _) in zip(chunks, chunks[1:]))
    assert all(b - a <= pd.Timedelta(days=G.CARBON_API_MAX_DAYS_PER_REQUEST) for a, b in chunks)


# -----------------------------------------------------------------------------
# Scoring
# -----------------------------------------------------------------------------
def test_score_is_share_times_source_score_then_delivered():
    from optimiser_lca import grid
    mix = pd.DataFrame([{f"api_{f}": 0.0 for f in G.CI_FUELS}])
    mix.loc[0, "api_gas"], mix.loc[0, "api_nuclear"] = 50.0, 50.0
    mix["DATETIME"] = pd.Timestamp("2025-06-02 00:00")
    scores = {k: 0.0 for k in grid.TECH_SPECS}
    scores.update(GAS=0.4, NUCLEAR=0.01)
    out = G.score_mix(mix, scores)
    gen = 0.5 * 0.4 + 0.5 * 0.01
    hv = grid.DELIVERY["high"]
    assert out["generation_kgco2e_per_kwh"].iloc[0] == pytest.approx(gen)
    assert out["custom_electricity_score"].iloc[0] == pytest.approx(
        gen * hv["gross_up"] + hv["network_gco2e_per_kwh"] / 1000.0)


def _flows(**mw):
    from optimiser_lca import grid
    t = pd.DatetimeIndex(["2025-06-02 00:00", "2025-06-02 00:30"])
    return pd.DataFrame({k: [mw.get(k, 0.0)] * 2 for k in grid.LINKS}, index=t)


def test_imports_split_by_the_half_hours_flows():
    """A half-hour's imports follow what is flowing in on the region's links."""
    from optimiser_lca import grid
    mix = pd.DataFrame({"DATETIME": pd.DatetimeIndex(["2025-06-02 00:00", "2025-06-02 00:30"]),
                        "api_region_id": [99, 99], "api_imports": [10.0, 10.0]})
    # Region 99 has no fit, so every link counts equally: national flows.
    # Exports (negative) count as zero.
    out = G.attach_import_shares(mix, _flows(INTFR=1000.0, INTNSL=3000.0, INTNED=-800.0))
    assert out["imp_FR"].iloc[0] == pytest.approx(0.25)
    assert out["imp_NO"].iloc[0] == pytest.approx(0.75)
    assert out["imp_NL"].iloc[0] == 0.0
    assert set(out["import_basis"]) == {"flows"}
    assert out[grid.IMPORT_SHARE_COLS].sum(axis=1).tolist() == pytest.approx([1.0, 1.0])


def test_no_flow_falls_back_to_the_regions_annual_split():
    from optimiser_lca import grid
    mix = pd.DataFrame({"DATETIME": pd.DatetimeIndex(["2025-06-02 00:00"]),
                        "api_region_id": [13], "api_imports": [30.0]})
    out = G.attach_import_shares(mix, _flows(INTNED=-500.0))       # all exporting
    assert out["import_basis"].iloc[0] == "annual"
    for c, v in grid.annual_import_shares(13).items():
        assert out[f"imp_{c}"].iloc[0] == pytest.approx(v)


def test_a_fitted_region_weights_its_own_links():
    """London's imports come through the Channel links, not North Sea Link."""
    from optimiser_lca import grid
    if 13 not in grid.IMPORT_ATTRIBUTION:
        pytest.skip("London has no fitted attribution")
    beta = grid.link_weights(13)
    assert beta["INTFR"] > 10 * beta.get("INTNSL", 0.0)
    shares, basis = grid.import_shares(13, {"INTFR": 1000.0, "INTNSL": 1000.0})
    assert basis == "flows" and shares["FR"] > 0.9


def test_import_attribution_fit_recovers_known_weights():
    import numpy as np
    from optimiser_lca import grid
    rng = np.random.default_rng(0)
    t = pd.date_range("2025-01-01", periods=400, freq="30min")
    flows = pd.DataFrame(rng.uniform(-500, 1500, (400, len(grid.LINKS))), index=t, columns=grid.LINKS)
    true = {k: 0.0 for k in grid.LINKS}
    true.update(INTFR=0.02, INTNEM=0.01)
    imports = sum(true[k] * flows[k].clip(lower=0) for k in grid.LINKS) / 1000.0 * 1000.0
    mix = pd.DataFrame({"DATETIME": t, "api_imports": imports.to_numpy()})
    fit = G.fit_import_attribution(mix, flows)
    assert fit["r2"] == pytest.approx(1.0, abs=1e-9)
    assert fit["beta"]["INTFR"] == pytest.approx(2 / 3, abs=1e-6)
    assert fit["beta"]["INTNEM"] == pytest.approx(1 / 3, abs=1e-6)


def test_elexon_settlement_periods_become_times():
    raw = pd.DataFrame({"settlementDate": ["2025-01-08", "2025-01-08"],   # GMT day
                        "settlementPeriod": [1, 2], "price": [50.0, 51.0],
                        "dataProvider": ["APXMIDP", "APXMIDP"]})
    out = G.normalise_elexon(raw)
    assert list(out["DATETIME"].dt.strftime("%H:%M")) == ["00:00", "00:30"]
    assert list(out.columns) == ["DATETIME", "provider", "price_GBP_per_MWh", "volume_MWh"]


def test_rescoring_an_existing_file_reproduces_it():
    """The real check: the notebook's own output, re-scored by this module from
    the fuel mix it recorded, gives the same kg CO2e/kWh."""
    bd = pytest.importorskip("bw2data")
    import dc_config as cfg
    if cfg.PROJECT_NAME not in bd.projects:
        pytest.skip("Brightway project not present on this machine")
    path = (REPO / "custom_grid_lca_outputs" /
            "custom_grid_lca_carbon_api_regional_auto_r14_cheap_"
            "2025-06-02T00-00-00T_to_T2025-06-09T00-00-00.csv")
    if not path.exists():
        pytest.skip(f"{path.name} not on disk")
    old = pd.read_csv(path)
    mix = old.rename(columns={"datetime": "DATETIME"})
    new = G.score_mix(mix)
    # Relative, not exact: each Brightway session's sparse solve differs in the
    # last few digits (measured ~1e-6 relative, i.e. ~0.0001 g/kWh).
    rel = ((new["custom_electricity_score"] - old["custom_electricity_score"]).abs()
           / old["custom_electricity_score"].abs())
    assert rel.max() < 1e-5, f"max relative difference {rel.max():.3e}"


# -----------------------------------------------------------------------------
# Which sources score the grid
# -----------------------------------------------------------------------------
def test_every_scored_fuel_has_exactly_one_named_source():
    from optimiser_lca import grid
    assert set(grid.GRID_SOURCES) == set(grid.TECH_SPECS)
    # (name, location, product), plus the database for a foreground source.
    assert all(len(v) in (3, 4) and all(isinstance(x, str) and x for x in v)
               for v in grid.GRID_SOURCES.values())
    assert grid.GRID_SOURCES["SOLAR"][3] == "solar foreground"
    assert set(grid.COUNTRY_SOURCE.values()) <= set(grid.SOURCES)
    assert {v[1] for v in grid.INTERCONNECTORS.values()} == set(grid.COUNTRY_SOURCE)


def test_sources_id_moves_when_anything_that_scores_changes(monkeypatch):
    from optimiser_lca import grid
    before = G.grid_sources_id()
    assert before == G.grid_sources_id()                      # stable
    assert before == GRID_BASIS_ID       # the id every series on disk carries
    changed = dict(grid.GRID_SOURCES)
    changed["GAS"] = ("electricity production, natural gas, conventional power plant",
                      "GB", "electricity, high voltage")
    monkeypatch.setattr(grid, "GRID_SOURCES", changed)
    assert G.grid_sources_id() != before
    monkeypatch.undo()
    delivery = {v: dict(d) for v, d in grid.DELIVERY.items()}
    delivery["high"]["network_gco2e_per_kwh"] += 0.1
    monkeypatch.setattr(grid, "DELIVERY", delivery)
    assert G.grid_sources_id() != before


def test_series_scored_on_other_sources_are_ignored(tmp_path):
    from optimisation import profiles
    row = {"datetime": ["2025-06-02 00:00:00"], "custom_electricity_score": [0.1],
           "clock": ["UTC"]}
    unmarked = tmp_path / "unmarked.csv"
    pd.DataFrame(row).to_csv(unmarked, index=False)
    stale = tmp_path / "stale.csv"
    pd.DataFrame({**row, "grid_sources": ["000000000000"]}).to_csv(stale, index=False)
    current = tmp_path / "current.csv"
    pd.DataFrame({**row, "grid_sources": [G.grid_sources_id()]}).to_csv(current, index=False)
    assert not profiles.grid_file_is_current(unmarked)
    assert not profiles.grid_file_is_current(stale)
    assert profiles.grid_file_is_current(current)


def test_grid_sources_resolve_exactly_and_gas_is_combined_cycle():
    """Pins TODO gap #1 shut: gas is scored on CCGT, by identity, not by rank."""
    bd = pytest.importorskip("bw2data")
    import dc_config as cfg
    if cfg.PROJECT_NAME not in bd.projects:
        pytest.skip("Brightway project not present on this machine")
    from optimiser_lca import grid
    table = G.source_table()
    assert table["GAS"]["name"] == "electricity production, natural gas, combined cycle power plant"
    assert 0.35 < table["GAS"]["kgco2e_per_kwh"] < 0.42
    for key, ident in grid.GRID_SOURCES.items():
        assert (table[key]["name"], table[key]["location"], table[key]["product"]) == tuple(ident[:3])
    # The grid's solar is the Smith plant now, not the 2008 El Tesoro one.
    assert 0.02 < table["SOLAR"]["kgco2e_per_kwh"] < 0.04


def test_delivery_constants_match_ecoinvent():
    bd = pytest.importorskip("bw2data")
    import dc_config as cfg
    if cfg.PROJECT_NAME not in bd.projects:
        pytest.skip("Brightway project not present on this machine")
    from optimiser_lca import grid
    assert grid.check_delivery()["ok"]
