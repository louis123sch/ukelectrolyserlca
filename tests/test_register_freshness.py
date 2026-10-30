"""The register update check (30 Oct 2026): the manifest's dates against the
portals', with a replaceable lookup so no portal is touched; and the cached
answer a run reads (``substations.freshness``)."""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from optimisation import substations as S                       # noqa: E402
from scripts import fetch_register_sources as F                  # noqa: E402


def _manifest(tmp_path, **mods):
    folder = tmp_path / "api"
    folder.mkdir()
    F.write_manifest(folder, {k: {"modified": v, "fetched": "2026-10-30"} for k, v in mods.items()})
    return folder


def test_a_newer_portal_date_is_stale_and_errors_are_not(tmp_path):
    folder = _manifest(tmp_path, ukpn_heatmap="2026-09-01", npg_heatmap="2026-03-01", ssen_queue="2026-05-05")

    def lookup(s, keys):
        if s.key == "ukpn_heatmap":
            return {"modified": "2026-10-15"}               # newer on the portal
        if s.key == "npg_heatmap":
            return {"modified": "2026-03-01"}               # unchanged
        if s.key == "ssen_queue":
            raise ConnectionError("offline")
        return {"skipped": "no key"}

    rows = {r["key"]: r for r in F.check_updates(folder, {}, {"ukpn_heatmap", "npg_heatmap", "ssen_queue", "enwl_substations"}, lookup)}
    assert rows["ukpn_heatmap"]["stale"] and rows["ukpn_heatmap"]["portal_modified"] == "2026-10-15"
    assert not rows["npg_heatmap"]["stale"]
    assert not rows["ssen_queue"]["stale"] and "offline" in rows["ssen_queue"]["error"]
    assert rows["enwl_substations"]["skipped"] == "no key" and not rows["enwl_substations"]["stale"]


def test_a_source_never_fetched_counts_as_stale_once_the_portal_has_it(tmp_path):
    folder = _manifest(tmp_path)
    rows = F.check_updates(folder, {}, {"ukpn_heatmap"}, lambda s, k: {"modified": "2026-10-01"})
    assert rows[0]["stale"] and rows[0]["fetched_modified"] is None


def test_freshness_is_cached_and_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "FRESHNESS", tmp_path / "freshness.json")
    monkeypatch.setenv(S.NO_PORTAL_CHECK_ENV, "1")
    first = S.freshness(force=True)
    assert first["skipped"] and first["ok"] and "checked" in first
    (tmp_path / "freshness.json").write_text(json.dumps({**first, "note": "cached copy"}), encoding="utf-8")
    assert S.freshness()["note"] == "cached copy"                 # within a day: the cached answer
    assert S.freshness(max_age_hours=0.0)["note"] != "cached copy"  # expired: checked again


def test_the_note_names_the_two_commands_when_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "FRESHNESS", tmp_path / "freshness.json")
    monkeypatch.delenv(S.NO_PORTAL_CHECK_ENV, raising=False)
    monkeypatch.setattr(F, "check_updates", lambda folder: [
        {"key": "ukpn_heatmap", "stale": True, "error": None, "skipped": None},
        {"key": "npg_heatmap", "stale": False, "error": None, "skipped": None}])
    out = S.freshness(force=True)
    assert out["stale"] == ["ukpn_heatmap"] and not out["ok"]
    assert "fetch_register_sources.py" in out["note"] and "--capacity-only" in out["note"]
