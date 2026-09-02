"""
GB map — the coastline, and the coordinates you are allowed to click on.
=============================================================================

``sites.resolve(lat, lon)`` takes a coordinate and derives the Carbon Intensity
region, the TNUoS zone and the renewable resource from it. Typing a coordinate
is exact but blind: nobody knows where 54.31, -2.77 is without a map. This
module supplies the map, so the same input can be given by pointing at it.

Two things are needed for that, and both live here rather than in the page:

1. **An outline to point at.** ``outline()`` returns a GeoJSON
   FeatureCollection of the UK and Ireland coastlines, held as a file in
   ``data/`` so the app never depends on a tile server or a live download.
2. **A set of clickable coordinates.** Vega can only report a click as *the
   data point nearest the cursor*, so an arbitrary click is not available;
   what is available is a grid of candidate points, one of which the click
   picks. ``land_grid()`` is that grid.

The grid is deliberately **land-only and GB-only**:

* land, because ``sites.lookup`` reverse-geocodes through postcodes.io, and a
  point in the North Sea has no postcode — a sea click would fail rather than
  place a data centre;
* GB, excluding Northern Ireland, because the Carbon Intensity API's regional
  series — the grid mix this whole study runs on — covers GB only. NI has no
  region to resolve to, so it is not offered.

Resolution is a compromise, and it is stated on the page: at the default step
a click lands within about 5 km of where it was aimed. That is finer than a
Carbon Intensity region and much finer than a TNUoS zone, so the derived region
and tariff are right except within a few km of a boundary — where the number
inputs, which stay authoritative, can place the site exactly.

Sources
-------
coastline   Natural Earth 1:50m admin-0 countries (public domain), UK and
            Ireland only, outer rings, islets below ~30 km2 dropped and
            coordinates rounded to 3 dp (~100 m) — see ``data/gb_outline.geojson``

Run:  python optimisation/gb_map.py
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent / "data" / "gb_outline.geojson"

# The map window. Wide enough to hold Shetland, the Outer Hebrides, Cornwall
# and Ireland, which is drawn for orientation but never clickable.
BBOX = {"lon_min": -8.8, "lon_max": 2.2, "lat_min": 49.7, "lat_max": 61.2}

# A point known to be in Northern Ireland, used to identify — and drop — the
# one polygon of the UK feature that GB's grid data does not cover.
BELFAST = (54.60, -5.93)

DEFAULT_STEP_LAT = 0.05          # ~5.6 km
DEFAULT_STEP_LON = 0.08          # ~5.2 km at 55 degrees N


@lru_cache(maxsize=1)
def outline() -> dict:
    """The UK + Ireland coastline as a GeoJSON FeatureCollection."""
    return json.loads(DATA.read_text(encoding="utf-8"))


def _rings(iso: str) -> list[np.ndarray]:
    out = []
    for f in outline()["features"]:
        if f["properties"]["iso"] != iso:
            continue
        for poly in f["geometry"]["coordinates"]:
            out.append(np.asarray(poly[0], dtype=float))   # lon, lat
    return out


def _inside(ring: np.ndarray, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Ray-casting point-in-polygon, vectorised over the candidate points."""
    x1, y1 = ring[:-1, 0], ring[:-1, 1]
    x2, y2 = ring[1:, 0], ring[1:, 1]
    lon = lon[:, None]
    lat = lat[:, None]
    straddles = (y1 > lat) != (y2 > lat)
    # x of the edge at this latitude; guard the horizontal edges straddles
    # has already excluded.
    dy = np.where(y2 == y1, 1.0, y2 - y1)
    xint = x1 + (lat - y1) * (x2 - x1) / dy
    return (straddles & (lon < xint)).sum(axis=1) % 2 == 1


@lru_cache(maxsize=4)
def land_grid(step_lat: float = DEFAULT_STEP_LAT,
              step_lon: float = DEFAULT_STEP_LON) -> pd.DataFrame:
    """Every clickable coordinate: a regular grid, kept where GB land is.

    Northern Ireland is excluded — see the module docstring.
    """
    lats = np.arange(BBOX["lat_min"], BBOX["lat_max"] + 1e-9, step_lat)
    lons = np.arange(BBOX["lon_min"], BBOX["lon_max"] + 1e-9, step_lon)
    glon, glat = np.meshgrid(lons, lats)
    glon, glat = glon.ravel(), glat.ravel()

    keep = np.zeros(glon.shape, dtype=bool)
    for ring in _rings("GBR"):
        hit = _inside(ring, glon, glat)
        if _inside(ring, np.array([BELFAST[1]]), np.array([BELFAST[0]]))[0]:
            keep &= ~hit                      # Northern Ireland: not GB grid
        else:
            keep |= hit
    return pd.DataFrame({"lat": np.round(glat[keep], 4),
                         "lon": np.round(glon[keep], 4)})


def nearest_land(lat: float, lon: float,
                 step_lat: float = DEFAULT_STEP_LAT,
                 step_lon: float = DEFAULT_STEP_LON) -> tuple[float, float]:
    """The clickable point closest to a typed coordinate."""
    g = land_grid(step_lat, step_lon)
    d = (g.lat - lat) ** 2 + ((g.lon - lon) * np.cos(np.radians(lat))) ** 2
    row = g.loc[d.idxmin()]
    return float(row.lat), float(row.lon)


def run():
    fc = outline()
    print(f"Outline: {len(fc['features'])} features, "
          f"{sum(len(p[0]) for f in fc['features'] for p in f['geometry']['coordinates'])}"
          " coastline points")
    g = land_grid()
    print(f"Clickable GB land points: {len(g):,} "
          f"({DEFAULT_STEP_LAT} deg lat x {DEFAULT_STEP_LON} deg lon)")
    print(f"  lat {g.lat.min():.2f}..{g.lat.max():.2f}   "
          f"lon {g.lon.min():.2f}..{g.lon.max():.2f}")
    for name, (la, lo) in {"Central London": (51.5074, -0.1278),
                           "Inverness": (57.48, -4.22),
                           "Belfast (should NOT be offered)": BELFAST,
                           "North Sea (should snap to land)": (54.5, 1.5)}.items():
        nl = nearest_land(la, lo)
        km = np.hypot((nl[0] - la) * 111, (nl[1] - lo) * 111 * np.cos(np.radians(la)))
        print(f"  {name}: nearest clickable {nl[0]:.4f}, {nl[1]:.4f} ({km:.1f} km away)")


if __name__ == "__main__":
    run()
