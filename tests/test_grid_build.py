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


def test_api_times_become_london_local():
    # 00:00Z on 2 June is 01:00 BST: the series is in local time, as before.
    assert G._local("2025-06-02 01:00:00").tz_convert("UTC").hour == 0
    assert G._api_z(G._local("2025-06-02 01:00:00")) == "2025-06-02T00:00Z"


def test_chunks_cover_the_window_without_gaps():
    chunks = list(G._chunks("2025-01-01 00:00:00", "2025-02-15 00:00:00"))
    assert all(b == c for (_, b), (c, _) in zip(chunks, chunks[1:]))
    assert all(b - a <= pd.Timedelta(days=G.CARBON_API_MAX_DAYS_PER_REQUEST) for a, b in chunks)


# -----------------------------------------------------------------------------
# Scoring
# -----------------------------------------------------------------------------
def test_score_is_share_times_loss_times_source_score():
    import dc_config as cfg
    import lca_helpers as H
    mix = pd.DataFrame([{f"api_{f}": 0.0 for f in G.CI_FUELS}])
    mix.loc[0, "api_gas"], mix.loc[0, "api_nuclear"] = 50.0, 50.0
    scores = {k: 0.0 for k in H.TECH_SPECS}
    scores.update(GAS=0.4, NUCLEAR=0.01)
    out = G.score_mix(mix, scores)
    expect = cfg.MARKET_LOSS_FACTOR * (0.5 * 0.4 + 0.5 * 0.01)
    assert out["custom_electricity_score"].iloc[0] == pytest.approx(expect)


def test_elexon_settlement_periods_become_times():
    raw = pd.DataFrame({"settlementDate": ["2025-06-02", "2025-06-02"],
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
