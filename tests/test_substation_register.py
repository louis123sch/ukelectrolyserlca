"""The substation register (scripts/build_substation_register.py): its helpers,
and the built tables in optimisation_outputs/substation_register checked by
scripts/check_substation_register.py."""
import importlib.util
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
REG = ROOT / "optimisation_outputs" / "substation_register"


def _builder():
    spec = importlib.util.spec_from_file_location("build_substation_register", ROOT / "scripts" / "build_substation_register.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = _builder()


def test_grid_reference_conversion_matches_greenwich():
    """OS National Grid TQ 38890 77320 is the Royal Observatory, 51.4778 N, 0.0015 W."""
    lat, lon = B.bng_to_wgs84(538890, 177320)
    assert lat == pytest.approx(51.4778, abs=2e-4) and lon == pytest.approx(-0.0015, abs=3e-4)


def test_a_blank_grid_reference_gives_no_location_rather_than_hanging():
    lat, lon = B.bng_to_wgs84(float("nan"), 177320)
    assert lat != lat and lon != lon


@pytest.mark.parametrize("a, b", [("DUNBAR A", "DUNBAR B"), ("Abberton Grid 33kV", "ABBERTON"),
                                  ("E KILBRIDE SOUTH", "EAST KILBRIDE SOUTH"), ("ROCHDALE MAIN 1/2", "ROCHDALE")])
def test_names_normalise_to_the_same_key(a, b):
    assert B.norm(a) == B.norm(b)


def test_group_labels_compare_as_sets_of_members():
    assert B.group_key("Bromborough - Rock Ferry") == B.group_key("BROMBOROUGH GT3 / ROCK FERRY GT2")
    assert B.group_key("SALTCOATS A&B") == B.group_key("SALTCOATS")


@pytest.mark.parametrize("label, customer", [("Hopkins Farm 33kV", True), ("Parc Cynog WF", True),
                                             ("Shell Stanlow", False), ("Cumbernauld", False)])
def test_customer_and_generator_nodes_are_flagged(label, customer):
    assert bool(B.CUSTOMER.search(label)) == customer


@pytest.mark.skipif(not (REG / "price_nodes.csv").exists(), reason="register not built")
def test_the_built_register_passes_its_checks():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_substation_register.py")],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout[-3000:]
