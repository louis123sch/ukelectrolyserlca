"""
Sites — a coordinate, and everything that follows from it.
=============================================================================

You give the optimiser a latitude and a longitude. Four things follow from that,
and until this module existed only the first of them was actually wired up:

1. **Renewable resource.** ``profiles.py`` fetches wind and solar capacity
   factors from Renewables.ninja by lat/lon, so this was always general.
2. **Grid carbon intensity.** The Carbon Intensity API is *regional*, and the
   half-hourly series this study uses is cached per region. Using London's
   intensities for a Scottish site would invert the whole renewables-versus-grid
   conclusion, so ``require_grid_region`` refuses rather than substituting.
3. **Network charges.** TNUoS demand tariffs are *zonal*, and span £0.00/kW in
   Scotland to £10.12/kW in the South West — see ``network_charges.py``. On a
   100 MW load that is a £1 m/year swing before a single kWh is priced.
4. **Grid connection availability.** The constraint that actually decides where
   data centres get built, and the one with no public dataset.

``resolve(lat, lon)`` derives 2 and 3 from the coordinate so they cannot drift
apart from each other or from 1. Picking a location must move the weather, the
grid mix and the network bill together, or the comparison is meaningless.

How the coordinate becomes a region
-----------------------------------
Both hops are real lookups rather than a hand-drawn map:

    lat/lon --> postcodes.io reverse geocode --> outcode
            --> Carbon Intensity API /regional/postcode --> region id + name
            --> CI_REGION_TO_TNUOS_ZONE --> TNUoS demand zone

The last step is a fixed 14-to-14 table rather than an API, because no open API
publishes it. Both schemes partition GB by **GSP group**, so the correspondence
is structural rather than approximate — and it is checked: the three named
presets were set by hand from published sources before this table existed, and
all three agree with it. ``check_zone_mapping()`` asserts that, so a wrong entry
cannot pass silently.

Near a region boundary the nearest-postcode hop can land on the wrong side. The
resolved region and zone are always reported, never hidden, so a boundary case
is visible rather than silent.

A pre-existing inconsistency this resolver exposes
--------------------------------------------------
``dashboard_config.WIND_LAT / WIND_LON`` is 51.7320, -0.3711 — a field near St
Albans, which resolves to **Carbon Intensity region 10 (East England)** and
**TNUoS zone 9**. Every cached grid series in this repo is **region 13
(London)**, TNUoS zone 12. So the study as it stood paired London's grid carbon
intensity and London's network tariff with a wind site in Hertfordshire.

Carbon-wise the two regions are similar and the effect is small. The network
charge is not: zone 12 is £7.41/kW against zone 9's £1.11/kW. Nothing warned
about this before, because nothing connected the wind coordinate to the grid
region — which is exactly what ``resolve`` now does, and what
``require_grid_region`` now refuses to let slide.

Grid connection limits are ASSUMED
----------------------------------
There is no public, machine-readable register of available connection capacity
by location. ``connection_limit_mw`` defaults to **None** — unconstrained —
because an invented number would be the single most decision-relevant input in
the study and the least defensible. Set it explicitly when you have a real
figure for a real site.

Sources
-------
reverse geocoding    postcodes.io (Open Government Licence)
CI region            NESO Carbon Intensity API, /regional/postcode/{outcode}
TNUoS zone           fixed GSP-group correspondence, checked against the presets
connection limits    **not supplied** — see above

Run:  python optimisation/sites.py
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CACHE_PATH = ROOT / "optimisation_outputs" / "site_lookup_cache.json"

POSTCODES_IO = "https://api.postcodes.io/postcodes"
CARBON_API = "https://api.carbonintensity.org.uk/regional/postcode"

# NESO Carbon Intensity API regional ids.
CARBON_API_REGIONS = {
    1: "North Scotland", 2: "South Scotland", 3: "North West England",
    4: "North East England", 5: "Yorkshire", 6: "North Wales",
    7: "South Wales", 8: "West Midlands", 9: "East Midlands",
    10: "East England", 11: "South West England", 12: "South England",
    13: "London", 14: "South East England",
}

# Both schemes partition GB by GSP group, so this is a structural
# correspondence, not a geographic approximation. Checked by check_zone_mapping().
CI_REGION_TO_TNUOS_ZONE = {
    1: 1,    # North Scotland      -> Northern Scotland
    2: 2,    # South Scotland      -> Southern Scotland
    3: 4,    # North West England  -> North West
    4: 3,    # North East England  -> Northern
    5: 5,    # Yorkshire           -> Yorkshire
    6: 6,    # North Wales & Mersey -> N Wales & Mersey
    7: 10,   # South Wales         -> South Wales
    8: 8,    # West Midlands       -> Midlands
    9: 7,    # East Midlands       -> East Midlands
    10: 9,   # East England        -> Eastern
    11: 14,  # South West England  -> South Western
    12: 13,  # South England       -> Southern
    13: 12,  # London              -> London
    14: 11,  # South East England  -> South East
}

# The TDR band is set by agreed capacity and connection voltage, not by
# location and not by preference. Prefer passing ``agreed_capacity_mw`` to
# ``resolve()`` and letting it derive; see
# ``network_charges.tdr_band_for_capacity()``. This default only applies when
# neither a band nor a capacity is given, and reproduces the figure this study
# published before the band was derived.
DEFAULT_TDR_BAND = "EHV2"

# Offshore wind needs a credible coastal connection. Judged by the resolved
# region rather than by distance to water, which would need a coastline dataset.
OFFSHORE_REGIONS = {1, 2, 4, 5, 6, 7, 10, 11, 12, 14}

CONNECTION_LIMITS_ARE_ASSUMED = True


@dataclass(frozen=True)
class Site:
    lat: float
    lon: float
    carbon_api_region: int
    tnuos_zone: int
    name: str = ""
    outcode: str = ""
    tdr_band: str = DEFAULT_TDR_BAND
    connection_limit_mw: float | None = None
    key: str = ""

    @property
    def region_name(self) -> str:
        return CARBON_API_REGIONS.get(self.carbon_api_region, "?")

    @property
    def offshore_wind(self) -> bool:
        return self.carbon_api_region in OFFSHORE_REGIONS

    # kept so older call sites reading .grid_connection_limit_mw still work
    @property
    def grid_connection_limit_mw(self) -> float | None:
        return self.connection_limit_mw

    def describe(self) -> str:
        return (f"{self.name or f'{self.lat:.4f}, {self.lon:.4f}'} — "
                f"CI region {self.carbon_api_region} ({self.region_name}), "
                f"TNUoS zone {self.tnuos_zone}, "
                f"{'offshore available' if self.offshore_wind else 'no offshore option'}, "
                f"connection "
                f"{'unconstrained' if self.connection_limit_mw is None else f'{self.connection_limit_mw:g} MW'}")


# -----------------------------------------------------------------------------
# Coordinate -> region
# -----------------------------------------------------------------------------
def _cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(c: dict):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(c, indent=2, sort_keys=True), encoding="utf-8")


def _get(url: str, timeout: int = 20):
    with urllib.request.urlopen(url, timeout=timeout) as fh:
        return json.load(fh)


def lookup(lat: float, lon: float) -> dict:
    """lat/lon -> {outcode, place, carbon_api_region, region_name, tnuos_zone}."""
    key = f"{round(float(lat), 3)},{round(float(lon), 3)}"
    cache = _cache()
    if key in cache:
        return cache[key]

    # 100 m is postcodes.io's default radius and misses open country — the
    # repo's own wind coordinate is in a field near St Albans and returns
    # nothing at the default. Widen, then fall back to the outcode endpoint,
    # which resolves anywhere in GB.
    hit, outcode = None, None
    try:
        q = urllib.parse.urlencode({"lon": lon, "lat": lat, "limit": 1, "radius": 2000})
        hit = (_get(f"{POSTCODES_IO}?{q}").get("result") or [None])[0]
        if hit is None:
            q = urllib.parse.urlencode({"lon": lon, "lat": lat, "limit": 1})
            hit = (_get(f"{POSTCODES_IO.replace('/postcodes', '/outcodes')}?{q}")
                   .get("result") or [None])[0]
    except Exception as exc:
        raise RuntimeError(
            f"Could not reach postcodes.io to resolve {lat}, {lon}: {exc}. "
            "Pass carbon_api_region= explicitly to skip the lookup.") from exc
    if hit is None:
        raise ValueError(
            f"No GB postcode within 2 km of {lat}, {lon}. This study's grid, "
            "price and network-charge data are all GB-only, so a site outside "
            "GB cannot be modelled.")
    outcode = hit.get("outcode")
    district = hit.get("admin_district")
    if isinstance(district, list):          # the outcodes endpoint returns a list
        district = district[0] if district else None

    try:
        ci = _get(f"{CARBON_API}/{outcode}")["data"][0]
    except Exception as exc:
        raise RuntimeError(
            f"Could not reach the Carbon Intensity API for {outcode}: {exc}") from exc
    region = int(ci["regionid"])

    out = {
        "outcode": outcode,
        "place": district or hit.get("region") or outcode,
        "carbon_api_region": region,
        "region_name": CARBON_API_REGIONS.get(region, ci.get("shortname", "?")),
        "tnuos_zone": CI_REGION_TO_TNUOS_ZONE[region],
        "postcode": hit.get("postcode"),
    }
    cache[key] = out
    _save_cache(cache)
    return out


def resolve(lat: float, lon: float, *, name: str | None = None,
            connection_limit_mw: float | None = None,
            tdr_band: str | None = None,
            agreed_capacity_mw: float | None = None,
            carbon_api_region: int | None = None) -> Site:
    """Build a Site from a coordinate, deriving its region and TNUoS zone.

    ``carbon_api_region`` overrides the lookup, for a boundary case you have
    checked yourself or when the APIs are unreachable.

    The TDR band is derived from the connection, in this order: an explicit
    ``tdr_band`` wins; otherwise it is banded from ``connection_limit_mw`` if
    one is imposed, else from ``agreed_capacity_mw`` (the site's peak demand);
    otherwise it falls back to DEFAULT_TDR_BAND.
    """
    if tdr_band is None:
        capacity = connection_limit_mw or agreed_capacity_mw
        if capacity:
            from . import network_charges as nc
            tdr_band = nc.tdr_band_for_capacity(float(capacity))
        else:
            tdr_band = DEFAULT_TDR_BAND

    if carbon_api_region is not None:
        region = int(carbon_api_region)
        info = {"outcode": "", "place": name or "",
                "carbon_api_region": region,
                "region_name": CARBON_API_REGIONS.get(region, "?"),
                "tnuos_zone": CI_REGION_TO_TNUOS_ZONE[region]}
    else:
        info = lookup(lat, lon)
    return Site(
        lat=float(lat), lon=float(lon),
        carbon_api_region=info["carbon_api_region"],
        tnuos_zone=info["tnuos_zone"],
        name=name or info.get("place") or f"{lat:.4f}, {lon:.4f}",
        outcode=info.get("outcode", ""),
        tdr_band=tdr_band, connection_limit_mw=connection_limit_mw,
        key=f"r{info['carbon_api_region']}_{float(lat):.4f}_{float(lon):.4f}",
    )


# -----------------------------------------------------------------------------
# Presets — convenience only. Coordinates are the interface.
# -----------------------------------------------------------------------------
PRESETS = {
    # The repo's own WIND_LAT / WIND_LON, and the coordinate every cached
    # Renewables.ninja series was fetched for. It resolves to **region 10, East
    # England** — not London — which matters, because the cached grid series is
    # region 13. See the note in the module docstring.
    "repo_default": (51.7320, -0.3711, "St Albans (the repo's WIND_LAT/WIND_LON)"),
    "london": (51.5074, -0.1278, "Central London"),
    "slough": (51.5098, -0.6002, "Slough"),
    "scotland": (57.4800, -4.2200, "Inverness, Northern Scotland"),
    "east_england": (52.6200, 1.2900, "Norwich, East England"),
    "south_west": (50.7200, -3.5300, "Exeter, South West"),
}
DEFAULT_PRESET = "london"


def preset(key: str, **kw) -> Site:
    if key not in PRESETS:
        raise ValueError(f"Unknown preset {key!r}. Available: {sorted(PRESETS)}")
    lat, lon, name = PRESETS[key]
    return resolve(lat, lon, name=name, **kw)


def get(spec, **kw) -> Site:
    """Accept a preset name, a (lat, lon) pair, or a Site. Coordinates win."""
    if isinstance(spec, Site):
        return spec
    if isinstance(spec, (tuple, list)) and len(spec) == 2:
        return resolve(spec[0], spec[1], **kw)
    if isinstance(spec, str):
        if "," in spec:
            lat, lon = (float(x) for x in spec.split(",", 1))
            return resolve(lat, lon, **kw)
        return preset(spec, **kw)
    raise TypeError(f"Cannot interpret site spec {spec!r}")


# -----------------------------------------------------------------------------
# Grid data availability
# -----------------------------------------------------------------------------
def available_grid_regions() -> dict[int, list[str]]:
    """Which Carbon Intensity regions have a cached half-hourly series."""
    import re
    out: dict[int, list[str]] = {}
    folder = ROOT / "custom_grid_lca_outputs"
    for p in sorted(folder.glob("custom_grid_lca_carbon_api_*.csv")):
        m = re.search(r"_r(\d+)_", p.name)
        if m:
            out.setdefault(int(m.group(1)), []).append(p.name)
    return out


def require_grid_region(site: Site, grid_filename: str):
    """Refuse a grid series that was not generated for this site's region.

    Silently using London's half-hourly intensities for a Scottish site would
    not fail anywhere downstream — it would produce a confident, wrong answer
    about whether renewables beat the grid there. So it fails here instead.
    """
    if f"_r{site.carbon_api_region}_" in grid_filename:
        return True
    import re
    found = re.search(r"_r(\d+)_", grid_filename)
    got = int(found.group(1)) if found else None
    have = available_grid_regions()
    raise ValueError(
        f"{site.name} is in Carbon Intensity region {site.carbon_api_region} "
        f"({site.region_name}), but the best available series is "
        f"{grid_filename!r}"
        + (f" — region {got} ({CARBON_API_REGIONS.get(got, '?')})." if got else ".")
        + "\n\nCached regions: "
        + (", ".join(f"{r} ({CARBON_API_REGIONS[r]})" for r in sorted(have)) or "none")
        + f"\n\nGenerate this one with:\n"
          f"    python -c \"from optimisation import sites; "
          f"sites.build_grid_series({site.carbon_api_region})\"\n"
          f"or run 3.1.custom_grid_carbon_intensity_api.ipynb with "
          f"CARBON_API_REGION_ID_OVERRIDE = {site.carbon_api_region}.")


def build_grid_series(carbon_api_region: int, start="2025-01-01 00:00:00",
                      end="2025-12-29 00:00:00", timeout_s: int = 3600):
    """Generate the half-hourly grid series for a region, via notebook 3.1.

    Wraps ``backend.runner.run_lca``, which patches ``dashboard_config.py`` and
    executes the pipeline — the same path the Setup LCA page uses. Slow (it
    scores the fuel mix against ecoinvent for every half-hour) but it is what
    makes an arbitrary coordinate usable rather than an error.
    """
    if carbon_api_region not in CARBON_API_REGIONS:
        raise ValueError(f"Region must be 1-14, got {carbon_api_region}")
    from backend.runner import run_lca
    print(f"Building grid series for region {carbon_api_region} "
          f"({CARBON_API_REGIONS[carbon_api_region]}), {start[:10]} to {end[:10]}.")
    print("This scores the GB fuel mix against ecoinvent for every half-hour "
          "and takes a while.")
    result = run_lca({
        "GRID_DATA_SOURCE": "carbon_api",
        "CARBON_API_SCOPE": "regional_auto",
        "CARBON_API_REGION_ID_OVERRIDE": int(carbon_api_region),
        "GRID_TIME_MODE": "range",
        "GRID_RANGE_START": start,
        "GRID_RANGE_END": end,
        "RUN_GRID_SCENARIO_LCA": True,
        # Notebook 3.1 writes the grid series only *after* scoring a foreground
        # technology, so the run dies before writing anything if TECH_SELECTED
        # names something this project cannot resolve. Which technology gets
        # scored makes no difference to the grid series itself, so pin it to the
        # built-in default (empty TECH_SELECTED falls back to TECH_ORDER_DEFAULT)
        # rather than inheriting whatever the last Setup-LCA run left behind.
        "TECH_SELECTED": [],
        "TECH_COUNT": 1,
        "TECH_SOURCE_OVERRIDES": {},
        # ELECTROLYSER_TECHS is validated against the built-in electrolyser
        # names unless the label is in TECH_SOURCE_OVERRIDES, which was just
        # cleared — so it has to be pinned to a built-in too.
        "ELECTROLYSER_TECHS": ["PEM operation"],
    }, timeout_s=timeout_s)
    have = available_grid_regions()
    if carbon_api_region not in have:
        detail = (result.error_text or "")[-1500:] if result is not None else ""
        raise RuntimeError(
            "The run finished but no series for region "
            f"{carbon_api_region} appeared in custom_grid_lca_outputs/."
            + (f"\n\nEnd of the notebook log:\n{detail}" if detail.strip()
               else " Check _streamlit_runs/last_run_executed.ipynb."))
    print(f"Done: {have[carbon_api_region][-1]}")
    return result


# -----------------------------------------------------------------------------
def check_zone_mapping():
    """The CI-region -> TNUoS-zone table must match the hand-set presets.

    Those three were set from published sources before the table existed, so
    they are an independent check on it rather than a restatement.
    """
    known = {13: 12, 1: 1, 10: 9}      # london, scotland, east_england
    bad = [f"CI {r}: table says {CI_REGION_TO_TNUOS_ZONE[r]}, presets say {z}"
           for r, z in known.items() if CI_REGION_TO_TNUOS_ZONE[r] != z]
    if bad:
        raise AssertionError("TNUoS zone mapping is wrong:\n  " + "\n  ".join(bad))
    if sorted(CI_REGION_TO_TNUOS_ZONE) != list(range(1, 15)):
        raise AssertionError("mapping must cover CI regions 1-14")
    if sorted(CI_REGION_TO_TNUOS_ZONE.values()) != list(range(1, 15)):
        raise AssertionError("mapping must be a bijection onto TNUoS zones 1-14")
    return "OK — 14 regions map one-to-one onto 14 zones, and the presets agree"


def run():
    from optimisation import network_charges as nc
    print("=" * 100)
    print("SITES — a coordinate, and everything that follows from it")
    print("=" * 100)
    print(check_zone_mapping())

    hh, _ = nc.tnuos_hh_demand()
    tariff = hh.set_index("zone_no").tariff_GBP_per_kW

    print(f"\n  {'preset':<14}{'lat':>9}{'lon':>9}  {'CI region':<22}"
          f"{'zone':>5}{'£/kW':>7}{'offshore':>10}")
    rows = []
    for k in PRESETS:
        try:
            s = preset(k)
        except Exception as exc:
            print(f"  {k:<14} lookup failed: {exc}")
            continue
        t = float(tariff.get(s.tnuos_zone, float("nan")))
        rows.append({"preset": k, "lat": s.lat, "lon": s.lon,
                     "ci_region": s.carbon_api_region, "region": s.region_name,
                     "tnuos_zone": s.tnuos_zone, "tnuos_GBP_per_kW": t,
                     "offshore": s.offshore_wind})
        print(f"  {k:<14}{s.lat:>9.4f}{s.lon:>9.4f}  "
              f"{str(s.carbon_api_region) + ' ' + s.region_name:<22}"
              f"{s.tnuos_zone:>5}{t:>7.2f}{str(s.offshore_wind):>10}")

    print("\n  Presets are shortcuts. Any GB coordinate works:")
    print("    sites.resolve(51.51, -0.60)      # or sites.get('51.51,-0.60')")

    have = available_grid_regions()
    print(f"\n  Cached grid series: "
          + (", ".join(f"region {r} ({CARBON_API_REGIONS[r]})" for r in sorted(have))
             or "none"))
    missing = [r for r in {x["ci_region"] for x in rows} if r not in have]
    if missing:
        print("  Missing for: "
              + ", ".join(f"{r} ({CARBON_API_REGIONS[r]})" for r in sorted(missing)))
        print("  Generate with sites.build_grid_series(<region>) — slow, but it is")
        print("  what makes an arbitrary coordinate usable rather than an error.")

    if CONNECTION_LIMITS_ARE_ASSUMED:
        print("\n  Grid connection limits default to unconstrained. No public register")
        print("  of available capacity by location exists, and an invented number")
        print("  would be the most decision-relevant input in the study and the")
        print("  least defensible. Set connection_limit_mw when you have a real one.")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    run()
