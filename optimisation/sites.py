"""
Sites — where the data centre is, and what that changes.
=============================================================================

Location enters this study through four separate channels, and until now only
one of them was wired up:

1. **Renewable resource.** ``profiles.py`` fetches wind and solar capacity
   factors from Renewables.ninja by lat/lon, so this has always been general.
2. **Grid carbon intensity.** The Carbon Intensity API is *regional*, and the
   repo's cached series is region 13, London. Using it for a Scottish site would
   invert the whole renewables-versus-grid conclusion, so ``require_grid_region``
   refuses rather than silently substituting.
3. **Network charges.** TNUoS demand tariffs are zonal and span £0.00/kW in
   Scotland to £10.12/kW in the South West. See ``network_charges.py``.
4. **Grid connection availability.** The constraint that actually decides where
   hyperscale data centres get built, and the one with no public dataset.

A ``Site`` carries all four so they cannot drift apart — picking a location must
move the weather, the grid mix and the network bill together, or the comparison
is meaningless.

Grid connection limits are ASSUMED
----------------------------------
There is no public, machine-readable register of available connection capacity
by location. The figures here are placeholders chosen to express the *ordering*
everyone in the industry agrees on — Slough and London are severely constrained,
Scotland and East England much less so — not to be accurate. They are the single
most decision-relevant number in the study and the least defensible.
Set ``grid_connection_limit_mw=None`` to remove the constraint entirely and see
what the optimiser does unconstrained; that is often the more honest run.

Sources
-------
Carbon Intensity API regions   NESO Carbon Intensity API regional definitions
TNUoS zones                    NESO TNUoS zonal map, via `network_charges.py`
lat/lon                        chosen points, not specific sites
connection limits              **ASSUMED** — see above

Run:  python optimisation/sites.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# NESO Carbon Intensity API regional IDs, for the guard in require_grid_region.
CARBON_API_REGIONS = {
    1: "North Scotland", 2: "South Scotland", 3: "North West England",
    4: "North East England", 5: "Yorkshire", 6: "North Wales",
    7: "South Wales", 8: "West Midlands", 9: "East Midlands",
    10: "East England", 11: "South West England", 12: "South England",
    13: "London", 14: "South East England",
}

CONNECTION_LIMITS_ARE_ASSUMED = True


@dataclass(frozen=True)
class Site:
    key: str
    name: str
    lat: float
    lon: float
    carbon_api_region: int          # which regional CI series is valid here
    tnuos_zone: int                 # which TNUoS demand tariff applies
    tdr_band: str                   # TNUoS demand residual band
    offshore_wind: bool             # is an offshore connection credible
    grid_connection_limit_mw: float | None   # ASSUMED — see module docstring
    note: str = ""

    @property
    def region_name(self) -> str:
        return CARBON_API_REGIONS[self.carbon_api_region]


SITES = {
    "london": Site(
        key="london", name="London (Greater London)",
        lat=51.732, lon=-0.3711,
        carbon_api_region=13, tnuos_zone=12, tdr_band="EHV2",
        offshore_wind=False, grid_connection_limit_mw=20.0,
        note="The only site the repo's cached grid data actually covers. "
             "Highest network charges outside the South West, worst connection "
             "queue, poorest wind resource of the three."),
    "scotland": Site(
        key="scotland", name="Northern Scotland",
        lat=57.48, lon=-4.22,
        carbon_api_region=1, tnuos_zone=1, tdr_band="EHV2",
        offshore_wind=True, grid_connection_limit_mw=100.0,
        note="Best wind resource, cleanest grid, and TNUoS demand tariff floored "
             "to zero — unfloored it is -£33.84/kW. The opposite of London on "
             "every axis that matters."),
    "east_england": Site(
        key="east_england", name="East England",
        lat=52.62, lon=1.29,
        carbon_api_region=10, tnuos_zone=9, tdr_band="EHV2",
        offshore_wind=True, grid_connection_limit_mw=60.0,
        note="Offshore wind landfall, moderate network charges (£1.11/kW), "
             "middling grid intensity. The compromise case."),
}

DEFAULT_SITE = "london"


def get(key: str) -> Site:
    if key not in SITES:
        raise ValueError(f"Unknown site {key!r}. Available: {sorted(SITES)}")
    return SITES[key]


def require_grid_region(site: Site, grid_filename: str):
    """Refuse a grid series that was not generated for this site's region.

    The cached Carbon Intensity output encodes its region in the filename
    (``..._regional_auto_r13_...``). Silently using London's half-hourly
    intensities for a Scottish site would not fail loudly anywhere downstream —
    it would just produce a confident, wrong answer about whether renewables
    beat the grid there. So it fails here instead.
    """
    marker = f"_r{site.carbon_api_region}_"
    if marker in grid_filename:
        return True
    import re
    found = re.search(r"_r(\d+)_", grid_filename)
    found_region = int(found.group(1)) if found else None
    raise ValueError(
        f"{site.name} needs Carbon Intensity region {site.carbon_api_region} "
        f"({site.region_name}), but the best available grid series is "
        f"{grid_filename!r}"
        + (f", which is region {found_region} ({CARBON_API_REGIONS.get(found_region, '?')})."
           if found_region else ", whose region cannot be determined.")
        + f"\n\nRun 3.1.custom_grid_carbon_intensity_api.ipynb with "
          f"CARBON_API_REGION_ID_OVERRIDE = {site.carbon_api_region} for the "
          f"period you want, or pick a site the cached data covers.")


def demand_mw(size_mw_it: float, pue: float = 1.15, index=None,
              profile: str = "flat"):
    """Facility demand from IT load and PUE.

    Flat by default, per ASSUMPTIONS.md §1 — the Zhang foreground's own 1.60e9
    kWh over 25 years is 7,306 kW continuous, and a hyperscale AI training load
    is close to flat. ``profile`` exists so that assumption can be relaxed
    without changing every call site.
    """
    if profile != "flat":
        raise NotImplementedError(
            f"Only the flat profile is implemented. {profile!r} would need a "
            "shape source — see ASSUMPTIONS.md before inventing one.")
    total = size_mw_it * pue
    if index is None:
        return total
    return pd.Series(total, index=index, name="demand_mw")


def table() -> pd.DataFrame:
    from optimisation import network_charges as nc
    hh, _ = nc.tnuos_hh_demand()
    tariff = hh.set_index("zone_no").tariff_GBP_per_kW
    return pd.DataFrame([{
        "site": s.key, "name": s.name, "lat": s.lat, "lon": s.lon,
        "ci_region": s.carbon_api_region, "ci_region_name": s.region_name,
        "tnuos_zone": s.tnuos_zone,
        "tnuos_GBP_per_kW": float(tariff.get(s.tnuos_zone, float("nan"))),
        "tdr_band": s.tdr_band, "offshore_wind": s.offshore_wind,
        "grid_limit_mw": s.grid_connection_limit_mw,
    } for s in SITES.values()])


def run():
    df = table()
    print("=" * 100)
    print("SITES — the four channels location enters through")
    print("=" * 100)
    print(f"  {'site':<14}{'CI region':<22}{'TNUoS zone':>11}{'£/kW':>8}"
          f"{'offshore':>10}{'grid MW':>10}")
    for _, r in df.iterrows():
        print(f"  {r.site:<14}{str(r.ci_region) + ' ' + r.ci_region_name:<22}"
              f"{r.tnuos_zone:>11}{r.tnuos_GBP_per_kW:>8.2f}"
              f"{str(r.offshore_wind):>10}{r.grid_limit_mw:>10.0f}")
    for s in SITES.values():
        print(f"\n  {s.name}\n    {s.note}")
    if CONNECTION_LIMITS_ARE_ASSUMED:
        print("\n  ASSUMED: grid connection limits express an ordering everyone agrees")
        print("  on, not measured availability. No public register exists. They are the")
        print("  most decision-relevant number here and the least defensible — run with")
        print("  grid_connection_limit_mw=None to see the unconstrained answer too.")
    print("\n  Only 'london' has cached grid data. The other two need 3.1 re-run with")
    print("  CARBON_API_REGION_ID_OVERRIDE set; require_grid_region() enforces that.")
    return df


if __name__ == "__main__":
    run()
