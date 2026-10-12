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
by location, so ``connection_limit_mw`` cannot be sourced for a given site. What
*can* be said is that a connection is contracted against the load it serves:
a site does not agree 868 MW to run a 360 MW data centre without a reason, and
the agreed capacity is what the TDR band is then read from.

``max_connection_mw`` therefore derives a ceiling from the load and a stated
headroom multiple, and the band follows from that ceiling rather than from the
load directly. The multiple is **ASSUMED** and named so it can be argued with;
what is not assumed is the chain. Before this, the three could disagree freely —
a 300 MW load could carry an unbounded connection billed at a 7 MW site's band.

Pin ``connection_limit_mw`` explicitly whenever a real figure exists; the
derivation is a default, not a claim about a particular substation.

Sources
-------
reverse geocoding    postcodes.io (Open Government Licence)
CI region            NESO Carbon Intensity API, /regional/postcode/{outcode}
TNUoS zone           fixed GSP-group correspondence, checked against the presets
connection limits    **not supplied** — see above

Run:  python optimisation/sites.py
"""
from __future__ import annotations

import contextlib
import json
import sys
import time
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

# TDR band is set by agreed capacity, not by location. EHV2 suits a data centre
# of a few tens of MW; see network_charges.tnuos_tdr() for the full band list.
# None means "derive it from what the site actually draws", via
# network_charges.tdr_band_for. "EHV2" was the study's reference 7.31 MW data
# centre — correct for that site, and 17x too cheap for a 300 MW one, because
# nothing rescaled it. Pin a string here only to override the derivation.
DEFAULT_TDR_BAND = None

# How much more connection than load a site is assumed to contract for.
#
# ASSUMED, and the most consequential assumption here, so it is one named number
# rather than a scatter of judgements. A connection must cover the load at
# minimum; above that it buys the ability to import hard in a lull — to serve
# demand and refill storage at the same time — which is precisely what the
# optimiser reaches for when it is left unbounded. Measured on the 300 MW
# Highland run, the unbounded minimum-carbon build wanted 2.41x the load, and
# spent six hours a year using it.
#
# 1.5 is deliberately below that: it grants real headroom without conceding the
# whole peak the optimiser would take if nothing stopped it. Raise it to see
# what the extra connection buys; set it to 1.0 to ask what a site sized purely
# for its load can achieve.
CONNECTION_HEADROOM_ASSUMED = 1.5


def max_connection_mw(load_mw: float,
                      headroom: float | None = None) -> tuple[float, str]:
    """The largest connection a site of this load is assumed to contract for.

    Returns ``(mw, note)``. The note is never empty: this number is assumed,
    and every caller should be able to say so.
    """
    if load_mw <= 0:
        raise ValueError(f"load_mw must be positive, got {load_mw}")
    h = CONNECTION_HEADROOM_ASSUMED if headroom is None else headroom
    if h < 1.0:
        raise ValueError(
            f"headroom must be at least 1.0 — a connection below the load "
            f"cannot serve it — got {h}")
    return load_mw * h, (
        f"connection ceiling ASSUMED at {h:g}x the {load_mw:,.1f} MW load; "
        f"see sites.CONNECTION_HEADROOM_ASSUMED")

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
    tdr_band: str | None = DEFAULT_TDR_BAND
    connection_limit_mw: float | None = None
    # None means "infer from the connection size". An explicit True/False states
    # it, which is always better: whether a site takes its supply from the
    # transmission or the distribution system is a network-design fact, and
    # inferring it from an assumed MW threshold decides the TDR band — £270,752
    # a year against £4,670,801 — on a guess.
    transmission_connected: bool | None = None
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
    # nothing at the default. Widen, then fall back to the outcode endpoint.
    #
    # The outcode fallback needs its radius widened too, and by a lot: its own
    # default is 5 km, and empty country is exactly where no postcode was found
    # in the first place. A point in the Cairngorms (57.15, -3.52) is 17 km
    # from the nearest outcode centroid — it used to fail as "not in GB", which
    # for a map click is both wrong and unhelpful. 25 km is the endpoint's
    # maximum. A hit that far away only ever decides the *region*, and regions
    # are hundreds of km across, so the extra reach costs nothing in accuracy.
    hit, outcode = None, None
    try:
        q = urllib.parse.urlencode({"lon": lon, "lat": lat, "limit": 1, "radius": 2000})
        hit = (_get(f"{POSTCODES_IO}?{q}").get("result") or [None])[0]
        if hit is None:
            q = urllib.parse.urlencode({"lon": lon, "lat": lat, "limit": 1,
                                        "radius": 25000})
            hit = (_get(f"{POSTCODES_IO.replace('/postcodes', '/outcodes')}?{q}")
                   .get("result") or [None])[0]
    except Exception as exc:
        raise RuntimeError(
            f"Could not reach postcodes.io to resolve {lat}, {lon}: {exc}. "
            "Pass carbon_api_region= explicitly to skip the lookup.") from exc
    if hit is None:
        raise ValueError(
            f"No GB postcode within 2 km of {lat}, {lon}, and no postcode "
            f"district within 25 km. This study's grid, "
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
            transmission_connected: bool | None = None,
            tdr_band: str | None = DEFAULT_TDR_BAND,
            carbon_api_region: int | None = None) -> Site:
    """Build a Site from a coordinate, deriving its region and TNUoS zone.

    ``carbon_api_region`` overrides the lookup, for a boundary case you have
    checked yourself or when the APIs are unreachable.
    """
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
        transmission_connected=transmission_connected,
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


def _as_datetime(value, *, end_of_day=False) -> str:
    """Accept '2025-01-01' or a full timestamp; return what the config wants.

    A bare date as the *end* means "include that day", so it is pushed to the
    following midnight — otherwise asking for 01-01..02-20 builds a series that
    stops the instant 20 February begins, and the window check then reports the
    build as short by a day. A value that already carries a time is left alone.
    """
    import re
    import pandas as pd
    ts = pd.Timestamp(value)
    if end_of_day and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value).strip()):
        ts = ts + pd.Timedelta(days=1)
    return ts.strftime("%Y-%m-%d %H:%M:%S")


BUILD_LOCK = ROOT / "optimisation_outputs" / ".grid_build.lock"

# Notebook 2 builds the foreground inventories from ecoinvent and the published
# parameters — there is no API behind it, so unlike the grid series it cannot be
# fetched, only made. dashboard_config keeps it off ("only on first setup ...
# because it can be slower than the other steps"), which is right once it exists
# and wrong the first time: notebook 3.1 scores the data centre against the
# half-hourly mix and looks that activity up by name, so a grid build cannot
# succeed before it has been made once.
_FOREGROUND_TIMEOUT_S = 5400


def _dc_foreground_missing() -> bool:
    """Is the data centre foreground genuinely absent?

    The project has to be opened first. ``bd.databases`` on a process that has
    not opened one returns an empty list rather than raising, so "cannot tell"
    is indistinguishable from "missing" — and guessing "missing" bolts the whole
    of notebook 2 onto a build that did not need it. ``setup_brightway`` is
    idempotent and every real caller has already run it.

    False whenever the question still cannot be answered: the build then fails
    with a clear message, which is better than a silent four-minute detour.
    """
    try:
        import bw2data as bd
        import dashboard_config as cfg
        import lca_helpers as H
        H.setup_brightway()
        return cfg.DC_FOREGROUND_DB not in bd.databases
    except Exception:
        return False

# One exclusive lock, taken two ways. Both ``flock`` and ``msvcrt.locking`` are
# held by the *handle*, so the OS hands the lock back when a holder dies — which
# an O_EXCL lock file does not. That matters here more than the portability: a
# build killed halfway must not leave every later run waiting six hours on a
# file nobody owns any more.
if sys.platform == "win32":
    import msvcrt

    def _try_lock(handle) -> bool:
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _unlock(handle):
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(handle) -> bool:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def _unlock(handle):
        fcntl.flock(handle, fcntl.LOCK_UN)


@contextlib.contextmanager
def _build_lock(wait_s: float = 6 * 3600, on_progress=None):
    """One grid build at a time, machine-wide.

    ``backend.runner.run_lca`` patches the single tracked ``dashboard_config.py``
    and executes the notebook against it. That was safe while a build was a
    deliberate act on the (since removed) Setup LCA page; it is not safe when
    any run can start one, because ``dc_runner.run_matrix``'s workers are separate
    processes and two of them building at once would each be running the
    other's config. Waiting is the right behaviour rather than failing: the
    second builder usually wants what the first is already producing.
    """
    BUILD_LOCK.parent.mkdir(parents=True, exist_ok=True)
    # "a+" rather than "w": the file's contents are irrelevant, and truncating
    # it out from under the process that currently holds the byte lock is not.
    handle = open(BUILD_LOCK, "a+")
    waited = 0.0
    while not _try_lock(handle):
        if waited == 0.0 and on_progress:
            on_progress("waiting for another grid build to finish")
        if waited > wait_s:
            handle.close()
            raise TimeoutError(
                f"Another grid build has held {BUILD_LOCK.name} for "
                f"{waited / 60:.0f} minutes. If nothing is running, delete "
                "that file.")
        time.sleep(5.0)
        waited += 5.0
    try:
        yield
    finally:
        try:
            _unlock(handle)
        finally:
            handle.close()


def build_grid_series(carbon_api_region: int, start="2025-01-01 00:00:00",
                      end="2025-12-29 00:00:00", timeout_s: int = 3600,
                      with_prices: bool = False, restore_config: bool = True):
    """Generate the half-hourly grid series for a region, via notebook 3.1.

    Wraps ``backend.runner.run_lca``, which patches ``dashboard_config.py`` and
    executes ``1.build_grid.ipynb`` (foreground if missing, 3.1, optionally 5). Slow (it
    scores the fuel mix against ecoinvent for every half-hour) but it is what
    makes an arbitrary coordinate usable rather than an error.

    ``with_prices`` also runs the Elexon notebook over the same window. Prices
    are GB-wide, so one build serves every region — but they are per-window
    like everything else, and a window outside what ``price_outputs/`` holds
    fails on price after paying for the grid build. Left off by default because
    the common case (a 2025 window) already has its prices on disk.

    Notebook 2 is run first, but only when its database is genuinely absent —
    see ``_dc_foreground_missing``.
    """
    if carbon_api_region not in CARBON_API_REGIONS:
        raise ValueError(f"Region must be 1-14, got {carbon_api_region}")
    from backend.runner import CONFIG_PATH, run_lca
    start, end = _as_datetime(start), _as_datetime(end, end_of_day=True)
    print(f"Building grid series for region {carbon_api_region} "
          f"({CARBON_API_REGIONS[carbon_api_region]}), {start[:10]} to {end[:10]}"
          + (" (with prices)" if with_prices else "") + ".")
    print("This scores the GB fuel mix against ecoinvent for every half-hour "
          "and takes a while.")
    build_foreground = _dc_foreground_missing()
    if build_foreground:
        # Same principle as the window itself: if it is not there, build it.
        print("The data centre foreground database does not exist yet, so "
              "notebook 2 runs first. That is a one-off — every later build "
              "skips it — and it makes this one considerably slower.")
        timeout_s = max(int(timeout_s), _FOREGROUND_TIMEOUT_S)
    # run_lca patches dashboard_config.py in place and leaves it patched — the
    # old Setup LCA page's contract, where the user chose those values and
    # expected to see them. A build started on the optimiser's behalf did not
    # choose them, so it puts the file back: a run that silently rewrote the project's
    # config would be a worse surprise than a slow one.
    overrides = {
        "GRID_DATA_SOURCE": "carbon_api",
        "CARBON_API_SCOPE": "regional_auto",
        "CARBON_API_REGION_ID_OVERRIDE": int(carbon_api_region),
        "GRID_TIME_MODE": "range",
        "GRID_RANGE_START": start,
        "GRID_RANGE_END": end,
        "RUN_GRID_SCENARIO_LCA": True,
        "RUN_PRICE_NOTEBOOK_FROM_DASHBOARD": bool(with_prices),
        "RUN_FOREGROUND_NOTEBOOK_FROM_DASHBOARD": build_foreground,
    }
    config = CONFIG_PATH.read_text(encoding="utf-8")
    try:
        result = run_lca(overrides, timeout_s=timeout_s)
        # One retry, and only for a run that died without saying why — the
        # notebook process disappearing mid-fetch rather than a cell raising.
        # A cell that raised will raise again and retrying only wastes the
        # window twice; a killed process usually will not, and the API cache
        # means the second attempt resumes rather than restarting. This is
        # worth doing because the cost of not doing it is asymmetric: the
        # whole optimiser run above is thrown away for a fault that had
        # nothing to do with it.
        if not result.success and result.crashed:
            print("The notebook process died without reporting an error "
                  f"(exit {result.returncode}). Retrying once — the API cache "
                  "means it resumes from where it stopped.")
            result = run_lca(overrides, timeout_s=timeout_s)
    finally:
        if restore_config:
            CONFIG_PATH.write_text(config, encoding="utf-8")
    if not result.success:
        raise RuntimeError(
            f"The pipeline run for region {carbon_api_region} failed.\n"
            + (result.error_text or "")[-4000:])
    have = available_grid_regions()
    if carbon_api_region not in have:
        raise RuntimeError(
            "The run finished but no series for region "
            f"{carbon_api_region} appeared in custom_grid_lca_outputs/. "
            "Check the notebook log.")
    # Newest by mtime, not last alphabetically: the region's file list is
    # sorted by name, so "Done: ..." used to name whichever file sorted last —
    # often the representative-days one, which is not what was just built.
    folder = ROOT / "custom_grid_lca_outputs"
    newest = max((folder / n for n in have[carbon_api_region]),
                 key=lambda f: f.stat().st_mtime)
    print(f"Done: {newest.name}")
    return result


# The Carbon Intensity API's regional series begins here; before it there is
# nothing to build, and a run that asks for 2015 should be told so in a second
# rather than after an hour of a notebook fetching empty pages.
CARBON_API_FIRST_DAY = "2018-05-11"


def _check_buildable(start, end):
    """Refuse a window the upstream APIs cannot serve, before paying for it."""
    import pandas as pd
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    now = pd.Timestamp.now().normalize()
    first = pd.Timestamp(CARBON_API_FIRST_DAY)
    if hi <= lo:
        raise ValueError(f"Window ends before it starts: {lo:%Y-%m-%d} to {hi:%Y-%m-%d}.")
    if lo < first:
        raise ValueError(
            f"{lo:%Y-%m-%d} is before the Carbon Intensity API's regional data "
            f"starts ({CARBON_API_FIRST_DAY}). Nothing can be built for it — "
            "pick a later window.")
    if lo > now:
        raise ValueError(
            f"{lo:%Y-%m-%d} is in the future. The grid series is measured data, "
            "not a forecast, so there is nothing to build yet.")


def _build_timeout(start, end) -> int:
    """A cap generous enough for the window asked for, not a fixed hour.

    Measured: a one-week regional build runs in about two minutes end to end
    with a warm API cache. The cap scales off that with a wide margin, because
    it exists to catch a hung notebook, not to time a healthy one — a fixed
    3600 s silently killed long builds partway through.
    """
    import pandas as pd
    days = max((pd.Timestamp(end) - pd.Timestamp(start)).total_seconds() / 86400.0, 1.0)
    return int(min(max(1800.0, 600.0 + days * 120.0), 6 * 3600.0))


def ensure_grid_series(carbon_api_region: int, start, end, *,
                       timeout_s: int | None = None, dry_run: bool = False,
                       on_progress=None):
    """Make the window exist for this region, building only what is missing.

    The optimiser's other inputs already work this way: ask for dates and they
    are fetched and cached. The grid series did not, so a window nobody had
    built yet was an error rather than a wait — and the error named the wrong
    cause, because "no file reaches this window" and "the only file is sampled"
    were reported identically. This is the missing half: check coverage of the
    window actually asked for, build exactly that window if it is missing, and
    do nothing at all when it is already there.

    Returns a dict saying what it found and what it built. ``dry_run`` answers
    "would this run have to build?" without building. ``on_progress`` is called
    with one line of text before the slow part, so a detached run can say what
    it is waiting on rather than going silent for an hour.
    """
    from optimisation import profiles
    if carbon_api_region not in CARBON_API_REGIONS:
        raise ValueError(f"Region must be 1-14, got {carbon_api_region}")
    status = profiles.window_status(start, end,
                                    carbon_api_region=carbon_api_region)
    out = {"region": carbon_api_region, "start": str(start), "end": str(end),
           "grid_ok": status["grid_ok"], "price_ok": status["price_ok"],
           "built": False, "detail": status["detail"]}
    if status["ok"] or dry_run:
        return out
    _check_buildable(start, end)
    with _build_lock(on_progress=on_progress):
        # Re-checked inside the lock: two runs that wanted the same window
        # queue here, and the second one wants what the first just built, not
        # another hour of the same notebook.
        status = profiles.window_status(start, end,
                                        carbon_api_region=carbon_api_region)
        if status["ok"]:
            out.update(grid_ok=True, price_ok=True, detail="")
            return out
        if on_progress:
            on_progress(
                f"building grid data for region {carbon_api_region} "
                f"({CARBON_API_REGIONS[carbon_api_region]}), "
                f"{str(start)[:10]} to {str(end)[:10]}")
        build_grid_series(carbon_api_region, start, end,
                          timeout_s=timeout_s or _build_timeout(start, end),
                          with_prices=not status["price_ok"])
    after = profiles.window_status(start, end,
                                   carbon_api_region=carbon_api_region)
    out.update(built=True, grid_ok=after["grid_ok"], price_ok=after["price_ok"],
               detail=after["detail"])
    if not after["ok"]:
        # The notebook can finish successfully and still not cover the window:
        # the Carbon Intensity API only holds so much history, and it returns
        # what it has rather than failing. Say so here, where the dates are,
        # instead of letting the loader report it as a missing file.
        raise RuntimeError(
            f"Built region {carbon_api_region} for {start}..{end}, but "
            f"{after['detail']}. The upstream APIs return what they hold, so a "
            "window they do not cover comes back short. Check the notebook log "
            "in _streamlit_runs/, and try a window inside what the Carbon "
            "Intensity and Elexon APIs actually serve.")
    return out


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
