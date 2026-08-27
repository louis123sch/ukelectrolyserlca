"""The clickable map's grid: GB land only, and fine enough to be worth clicking.

Fast — pure geometry against the packaged coastline, no network and no
Brightway.
"""
import sys

import numpy as np

sys.path.insert(0, "/Users/louis/lca-ai-project/ukelectrolyserlca")
from optimisation import gb_map, sites


def test_outline_holds_both_countries():
    isos = {f["properties"]["iso"] for f in gb_map.outline()["features"]}
    assert isos == {"GBR", "IRL"}


def test_grid_is_on_gb_land():
    g = gb_map.land_grid()
    assert 5_000 < len(g) < 20_000
    # Land, not sea: the four corners of the map window are all water.
    assert g.lat.min() > 49.8 and g.lat.max() < 61.0
    assert g.lon.min() > -8.0 and g.lon.max() < 2.0


def test_known_places_are_clickable():
    for lat, lon, within_km in (
            (51.5074, -0.1278, 5.0),      # central London
            (57.4800, -4.2200, 5.0),      # Inverness
            (50.7200, -3.5300, 5.0),      # Exeter
            (57.1500, -3.5200, 5.0)):     # open country in the Cairngorms
        la, lo = gb_map.nearest_land(lat, lon)
        km = np.hypot((la - lat) * 111.0,
                      (lo - lon) * 111.0 * np.cos(np.radians(lat)))
        assert km < within_km, f"{lat},{lon} snapped {km:.1f} km away"


def test_northern_ireland_is_not_offered():
    """NI is drawn but never clickable: the CI API's regional series is GB-only."""
    la, lo = gb_map.nearest_land(*gb_map.BELFAST)
    assert not (54.0 < la < 55.4 and lo < -5.4), f"click landed in NI: {la}, {lo}"


def test_every_preset_sits_near_a_clickable_point():
    for key, (lat, lon, _name) in sites.PRESETS.items():
        la, lo = gb_map.nearest_land(lat, lon)
        km = np.hypot((la - lat) * 111.0,
                      (lo - lon) * 111.0 * np.cos(np.radians(lat)))
        assert km < 8.0, f"preset {key} is {km:.1f} km from any clickable point"
