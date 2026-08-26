"""
Demand-side network charges — what the data centre actually pays to import.
=============================================================================

Until now this study priced grid imports at the **Elexon wholesale price alone**,
which is roughly half of what a real industrial site pays. That is not a
rounding error, and it is not neutral between the options being compared: it
makes ``grid_only`` and every grid-connected architecture look cheaper than they
are, against exactly the on-site generation that would avoid the charges. The
DESNZ/Arup connection figures already in ``tech_costs.py`` are **generator**-side
and are not a substitute — a generator is paid or charged for exporting; a data
centre is charged for importing, under a different methodology.

Four charges, each with a different shape, and the shape is what matters to an
optimiser:

| charge | basis | falls on |
|---|---|---|
| **TNUoS HH locational** | £/kW of Triad demand | peak import — capacity-like |
| **TNUoS demand residual (TDR)** | £/site/day, banded by agreed capacity | a fixed annual cost of having a connection |
| **BSUoS** | £/MWh imported | every unit — pure volumetric |
| **DUoS** | p/kWh in red/amber/green time bands, plus p/kVA/day | part volumetric and time-varying, part capacity |

So network charges are **not** a flat adder. Two of the four scale with the
connection rather than the energy, which is precisely the trade the hydrogen and
battery architectures exist to make: a smaller grid connection running flatter
avoids TNUoS and DUoS capacity charges even if it imports the same annual energy.
Modelling them as a single £/MWh would erase the effect being studied.

Location, and why it is the headline
------------------------------------
The TNUoS half-hourly demand tariff is **zonal**, and the spread across GB is
enormous. For 2025/26 it runs from **£0.00/kW in Northern and Southern Scotland**
— both floored, their unfloored tariffs are *negative* at -£33.84 and -£23.62 —
to **£7.41 in London**, **£7.57 in Southern** and **£10.12 in South Western**.

A 100 MW data centre therefore pays about **£1.0 m/year** in locational TNUoS at a
South Western site and **nothing** in Scotland, before a single kWh is priced.
That is the same locational signal the renewable resource gives, pointing the
same way, and it was entirely absent from the study.

Sources
-------
TNUoS HH demand,  NESO Data Portal, *Transmission Network Use of System (TNUoS)
TNUoS TDR         Tariffs*, via the CKAN datastore API — the same API
                  ``h2_prices.py`` uses for the LCOH cubes. TRANSCRIBED, and
                  refetchable rather than pasted.
                  HH demand resource 6abe8416-149c-4c78-b65b-059eea19957a
                  TDR resource       dcca94fd-343e-4d4e-8c5d-66009dec4ad3
BSUoS             NESO Data Portal, *BSUoS Fixed Tariffs*, same API.
                  resource 4dfa533f-bec6-491b-a3f1-7ce92449bc9a
DUoS              London Power Networks plc, *Use of System Charging Statement*,
                  LC14, v1.3, effective 1 April 2026, Annex 1 — Schedule of
                  Charges for LV and HV Designated Properties. TRANSCRIBED from
                  the published statement; no open API was found for DNO
                  charging statements, unlike TNUoS and BSUoS.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run:  python optimisation/network_charges.py
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"
CACHE_DIR = OUT_DIR / "neso_cache"

NESO_DATASTORE = "https://api.neso.energy/api/3/action/datastore_search"
TNUOS_HH_RESOURCE = "6abe8416-149c-4c78-b65b-059eea19957a"
TNUOS_TDR_RESOURCE = "dcca94fd-343e-4d4e-8c5d-66009dec4ad3"
BSUOS_RESOURCE = "4dfa533f-bec6-491b-a3f1-7ce92449bc9a"

# Financial year label NESO uses: FY2026 == 2025/26.
TARIFF_FY = 2026
PUBLICATION = "Final"

DAYS_PER_YEAR = 365.0

# -----------------------------------------------------------------------------
# DUoS — London Power Networks, LC14 v1.3, Annex 1, "HV Site Specific"
# -----------------------------------------------------------------------------
# TRANSCRIBED. Only the HV Site Specific family is carried: a data centre of this
# scale is HV or EHV connected, and EHV charges in Annex 2 are *site specific*
# (one row per named site), so they cannot be generalised into a study input.
# Using HV for an EHV-connected site overstates DUoS somewhat — noted in
# DATA_GAPS.md.
DUOS_LPN_HV = {
    "HV Site Specific No Residual": {
        "llfc": 90, "red_p_per_kwh": 3.440, "amber_p_per_kwh": 0.262,
        "green_p_per_kwh": 0.008, "fixed_p_per_mpan_day": 120.55,
        "capacity_p_per_kva_day": 9.19, "exceeded_p_per_kva_day": 9.19,
        "reactive_p_per_kvarh": 0.244,
    },
    "HV Site Specific Band 1": {
        "llfc": 91, "red_p_per_kwh": 0.230, "amber_p_per_kwh": 0.0,
        "green_p_per_kwh": 0.0, "fixed_p_per_mpan_day": 0.0,
        "capacity_p_per_kva_day": 9.19, "exceeded_p_per_kva_day": 9.19,
        "reactive_p_per_kvarh": 0.244,
    },
    "HV Site Specific Band 4": {
        "llfc": 94, "red_p_per_kwh": 0.021, "amber_p_per_kwh": 0.0,
        "green_p_per_kwh": 0.0, "fixed_p_per_mpan_day": 0.0,
        "capacity_p_per_kva_day": 9.19, "exceeded_p_per_kva_day": 9.19,
        "reactive_p_per_kvarh": 0.244,
    },
}
DUOS_DEFAULT_TARIFF = "HV Site Specific No Residual"

# SIMPLIFIED. The statement defines the amber band differently in each of three
# seasons; this keeps the red band exactly as published and merges the seasonal
# amber definitions into one all-year window. Red is what matters — it is an
# order of magnitude above amber and two above green — and it is exact here.
DUOS_RED_MONTHS = (11, 12, 1, 2)
DUOS_RED_HOURS = (16, 19)          # 16:00-19:00, Mon-Fri inclusive of bank hols
DUOS_AMBER_HOURS = ((7, 16), (19, 23))
DUOS_BANDS_SIMPLIFIED = True

# Triad: the three half-hours of highest GB demand between November and
# February, at least ten days apart. A flat 24/7 data centre cannot avoid them,
# so its Triad demand equals its peak import. ASSUMED that no avoidance is
# attempted — true for this study's flat load by construction.
TRIAD_AVOIDANCE = False


def _cache(name: str, fetch):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8")), True
        except Exception:
            pass
    records = fetch()
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records, False


def _fetch_resource(resource_id: str, name: str, limit: int = 5000):
    def go():
        url = NESO_DATASTORE + "?" + urllib.parse.urlencode(
            {"resource_id": resource_id, "limit": limit})
        with urllib.request.urlopen(url, timeout=60) as fh:
            payload = json.load(fh)
        if not payload.get("success"):
            raise RuntimeError(f"NESO datastore refused the request for {name}")
        return payload["result"]["records"]
    return _cache(name, go)


# =============================================================================
# TNUoS
# =============================================================================
def tnuos_hh_demand(year_fy: int = TARIFF_FY, publication: str = PUBLICATION):
    """Zonal half-hourly demand tariff, £/kW of Triad demand."""
    records, cached = _fetch_resource(TNUOS_HH_RESOURCE, "neso_tnuos_hh_demand")
    df = pd.DataFrame(records)
    df = df[(df.Year_FY == year_fy) & (df.Publication == publication)]
    if df.empty:
        raise ValueError(
            f"No TNUoS HH demand tariffs for FY{year_fy} {publication}. "
            f"Available: {sorted({(r['Year_FY'], r['Publication']) for r in records})}")
    out = df[["Zone_No", "Zone_Name", "Peak_£/kW", "YearRound_£/kW",
              "HHTariff(Floored)_£/kW"]].copy()
    out.columns = ["zone_no", "zone_name", "peak_GBP_per_kW",
                   "yearround_GBP_per_kW", "tariff_GBP_per_kW"]
    return out.sort_values("zone_no").reset_index(drop=True), cached


def tnuos_tdr(year_fy: int = TARIFF_FY, publication: str = PUBLICATION):
    """Transmission Demand Residual, £ per site per day, banded."""
    records, cached = _fetch_resource(TNUOS_TDR_RESOURCE, "neso_tnuos_tdr")
    df = pd.DataFrame(records)
    df = df[(df.Year_FY == year_fy) & (df.Publication == publication)]
    col = [c for c in df.columns if c.startswith("TDR Tariff")][0]
    out = df[["TDR Band", col]].copy()
    out.columns = ["band", "GBP_per_site_day"]
    out["GBP_per_site_year"] = out["GBP_per_site_day"] * DAYS_PER_YEAR
    return out.reset_index(drop=True), cached


# -----------------------------------------------------------------------------
# Which band a site falls in
# -----------------------------------------------------------------------------
# The TDR band follows from the site's agreed capacity and connection voltage —
# never from its location, and never from a free choice by the modeller. Left as
# a dropdown it swings the answer by £22/MWh across HV1..EHV4, which is larger
# than most of the differences this study reports.
#
# WARNING — THE BOUNDARIES BELOW ARE ASSUMED, THE TARIFFS ARE NOT.
# The £/site/day figures come from the NESO feed fetched above. The capacity
# boundaries do not: under the Targeted Charging Review each DNO sets its own
# band boundaries in its DCUSA charging statement, so there is no single national
# table, and the NESO resource carries only band -> £/day. The ladder below is a
# stand-in based on typical GB connection practice (HV up to roughly 8 MVA, EHV
# above it, four capacity bands within each tier). Replace it with the DNO's
# published table before quoting any absolute cost.
TDR_BANDS_ARE_ASSUMED = True

TDR_BAND_MAX_MVA = [
    (1.0, "HV1"),
    (2.0, "HV2"),
    (4.0, "HV3"),
    (8.0, "HV4"),
    (15.0, "EHV1"),
    (30.0, "EHV2"),
    (60.0, "EHV3"),
    (float("inf"), "EHV4"),
]


def tdr_band_for_capacity(agreed_capacity_mw: float,
                          power_factor: float = 1.0) -> str:
    """The TDR band a site of this agreed capacity would be assigned.

    `agreed_capacity_mw` is the *connection* size, not the annual energy: the
    grid connection cap where one is imposed, otherwise the site's peak demand.
    See TDR_BANDS_ARE_ASSUMED — the boundaries are a stand-in, not sourced.
    """
    if agreed_capacity_mw <= 0:
        raise ValueError("agreed capacity must be positive to imply a TDR band")
    mva = agreed_capacity_mw / power_factor
    for ceiling, band in TDR_BAND_MAX_MVA:
        if mva <= ceiling:
            return band
    return TDR_BAND_MAX_MVA[-1][1]


# =============================================================================
# BSUoS
# =============================================================================
def bsuos_tariffs():
    """Fixed BSUoS tariff, £/MWh, by the half-year window it applies to."""
    records, cached = _fetch_resource(BSUOS_RESOURCE, "neso_bsuos_fixed")
    df = pd.DataFrame(records)
    df = df[df.Publication == "Final"].copy()
    df["start"] = pd.to_datetime(df["Fixed Tariff Start Date"]).dt.tz_localize(None)
    df["end"] = pd.to_datetime(df["Fixed Tariff End Date"]).dt.tz_localize(None)
    out = df[["start", "end", "Fixed Tariff £/MWh"]].copy()
    out.columns = ["start", "end", "GBP_per_MWh"]
    return out.sort_values("start").reset_index(drop=True), cached


def bsuos_series(index: pd.DatetimeIndex) -> pd.Series:
    """£/MWh for every timestamp, from the half-yearly fixed tariffs."""
    tariffs, _ = bsuos_tariffs()
    out = pd.Series(np.nan, index=index, name="bsuos_GBP_per_MWh")
    for _, r in tariffs.iterrows():
        mask = (index >= r["start"]) & (index <= r["end"] + pd.Timedelta(days=1))
        out[mask] = r["GBP_per_MWh"]
    if out.isna().any():
        lo, hi = tariffs["start"].min(), tariffs["end"].max()
        raise ValueError(
            f"BSUoS is not published for {out.index[out.isna()].min():%Y-%m-%d} "
            f"onwards. Published cover: {lo:%Y-%m-%d} to {hi:%Y-%m-%d}.")
    return out


# =============================================================================
# DUoS
# =============================================================================
def duos_band(index: pd.DatetimeIndex) -> pd.Series:
    """Red / amber / green for every timestamp. See DUOS_BANDS_SIMPLIFIED."""
    weekday = index.dayofweek < 5
    hour = index.hour
    red = weekday & index.month.isin(DUOS_RED_MONTHS) \
        & (hour >= DUOS_RED_HOURS[0]) & (hour < DUOS_RED_HOURS[1])
    amber = weekday & ~red & (
        ((hour >= DUOS_AMBER_HOURS[0][0]) & (hour < DUOS_AMBER_HOURS[0][1]))
        | ((hour >= DUOS_AMBER_HOURS[1][0]) & (hour < DUOS_AMBER_HOURS[1][1])))
    return pd.Series(np.where(red, "red", np.where(amber, "amber", "green")),
                     index=index, name="duos_band")


def duos_series(index: pd.DatetimeIndex, tariff: str = DUOS_DEFAULT_TARIFF) -> pd.Series:
    """£/MWh of DUoS unit charge for every timestamp."""
    t = DUOS_LPN_HV[tariff]
    band = duos_band(index)
    rate = band.map({"red": t["red_p_per_kwh"], "amber": t["amber_p_per_kwh"],
                     "green": t["green_p_per_kwh"]})
    return (rate * 10.0).rename("duos_GBP_per_MWh")     # p/kWh -> GBP/MWh


# =============================================================================
# Assembly — what the LP actually needs
# =============================================================================
def import_charges(index: pd.DatetimeIndex, zone_no: int, tdr_band: str,
                   duos_tariff: str = DUOS_DEFAULT_TARIFF,
                   power_factor: float = 1.0):
    """Split every demand-side charge into the two shapes an LP can carry.

    Returns ``volumetric`` — a £/MWh series to add to the wholesale price on
    ``imp[t]`` — and ``capacity``, a £/MW/year charge on the grid connection,
    plus ``fixed``, a £/year cost of simply having a connection.

    Keeping capacity separate from volumetric is the whole point. A battery or a
    hydrogen store that flattens the import profile shrinks the connection and
    so the capacity term, while importing the same annual energy. Collapsing
    everything into £/MWh would hide exactly that saving.
    """
    hh, _ = tnuos_hh_demand()
    tdr, _ = tnuos_tdr()

    zone = hh[hh.zone_no == zone_no]
    if zone.empty:
        raise ValueError(f"TNUoS zone {zone_no} not found. "
                         f"Zones: {hh.zone_no.tolist()}")
    tnuos_per_kw = float(zone.iloc[0].tariff_GBP_per_kW)

    band = tdr[tdr.band == tdr_band]
    if band.empty:
        raise ValueError(f"TDR band {tdr_band!r} not found. "
                         f"Bands: {tdr.band.tolist()}")
    tdr_per_year = float(band.iloc[0].GBP_per_site_year)

    duos = DUOS_LPN_HV[duos_tariff]
    duos_capacity_per_mw_year = (duos["capacity_p_per_kva_day"] / 100.0
                                 * DAYS_PER_YEAR * 1000.0 / power_factor)
    duos_fixed_per_year = duos["fixed_p_per_mpan_day"] / 100.0 * DAYS_PER_YEAR

    volumetric = bsuos_series(index) + duos_series(index, duos_tariff)
    return {
        "volumetric_GBP_per_MWh": volumetric.rename("network_GBP_per_MWh"),
        "capacity_GBP_per_MW_year": tnuos_per_kw * 1000.0 + duos_capacity_per_mw_year,
        "fixed_GBP_per_year": tdr_per_year + duos_fixed_per_year,
        "components": {
            "tnuos_locational_GBP_per_MW_year": tnuos_per_kw * 1000.0,
            "duos_capacity_GBP_per_MW_year": duos_capacity_per_mw_year,
            "tnuos_tdr_GBP_per_year": tdr_per_year,
            "duos_fixed_GBP_per_year": duos_fixed_per_year,
            "bsuos_mean_GBP_per_MWh": float(bsuos_series(index).mean()),
            "duos_mean_GBP_per_MWh": float(duos_series(index, duos_tariff).mean()),
            "zone_name": zone.iloc[0].zone_name,
            "tdr_band": tdr_band,
            "duos_tariff": duos_tariff,
        },
    }


def run():
    hh, hh_cached = tnuos_hh_demand()
    tdr, _ = tnuos_tdr()
    bsuos, _ = bsuos_tariffs()

    print("=" * 100)
    print(f"DEMAND-SIDE NETWORK CHARGES — FY{TARIFF_FY} ({TARIFF_FY-1}/{str(TARIFF_FY)[2:]}) "
          f"{PUBLICATION}{'  [cached]' if hh_cached else '  [fetched]'}")
    print("=" * 100)

    print("\nTNUoS half-hourly demand tariff, by zone (£/kW of Triad demand)")
    print("-" * 100)
    print(f"  {'':<4}{'zone':<24}{'peak':>10}{'year-round':>13}{'charged':>11}")
    for _, r in hh.iterrows():
        floored = " floored" if abs(r.tariff_GBP_per_kW) < 1e-9 else ""
        print(f"  {int(r.zone_no):<4}{r.zone_name[:24]:<24}{r.peak_GBP_per_kW:>10.2f}"
              f"{r.yearround_GBP_per_kW:>13.2f}{r.tariff_GBP_per_kW:>11.2f}{floored}")
    lo = hh.tariff_GBP_per_kW.min(); hi = hh.tariff_GBP_per_kW.max()
    print(f"\n  Spread £{lo:.2f} to £{hi:.2f}/kW. For a 100 MW data centre that is "
          f"£0 to £{hi * 100_000 / 1e6:.2f} m/year")
    print("  in locational TNUoS alone, before a single kWh is priced. Scotland's")
    print("  tariffs are floored — unfloored they are negative.")

    print("\nTNUoS demand residual, by band (£/site/year)")
    print("-" * 100)
    for _, r in tdr[tdr.band.str.startswith(("HV", "EHV", "T-Demand"))].iterrows():
        print(f"  {r.band:<14}{r.GBP_per_site_year:>14,.0f}")

    print("\nBSUoS, £/MWh imported")
    print("-" * 100)
    for _, r in bsuos.tail(5).iterrows():
        print(f"  {r.start:%Y-%m-%d} to {r.end:%Y-%m-%d}   {r.GBP_per_MWh:>6.2f}")

    print("\nWhat this does to the baseline — 7.31 MW flat, London, 2025")
    print("-" * 100)
    print(f"  {'':<44}{'GBP/MWh':>8}{'m GBP/yr':>10}   shape")
    idx = pd.date_range("2025-01-01", "2025-12-29", freq="30min")
    ch = import_charges(idx, zone_no=12, tdr_band="EHV2")
    c = ch["components"]
    mwh = 7.31 * 8760
    vol = float(ch["volumetric_GBP_per_MWh"].mean())
    cap_cost = ch["capacity_GBP_per_MW_year"] * 7.31
    total = vol * mwh + cap_cost + ch["fixed_GBP_per_year"]
    WHOLESALE = 79.83      # baseline_grid.py, Elexon APXMIDP mean for the window
    rows = [
        ("BSUoS", c["bsuos_mean_GBP_per_MWh"], "volumetric"),
        ("DUoS unit (red/amber/green)", c["duos_mean_GBP_per_MWh"], "volumetric"),
        ("TNUoS locational (%s)" % c["zone_name"],
         c["tnuos_locational_GBP_per_MW_year"] * 7.31 / mwh, "capacity"),
        ("DUoS capacity", c["duos_capacity_GBP_per_MW_year"] * 7.31 / mwh, "capacity"),
        ("TNUoS TDR (%s)" % c["tdr_band"], c["tnuos_tdr_GBP_per_year"] / mwh, "connection"),
    ]
    network = sum(v for _, v, _ in rows)
    print(f"  {'wholesale (the study has used this alone)':<44}{WHOLESALE:>8.2f}"
          f"{WHOLESALE * mwh / 1e6:>10.2f}   —")
    for label, value, shape in rows:
        print(f"  {'+ ' + label:<44}{value:>8.2f}{value * mwh / 1e6:>10.2f}   {shape}")
    print(f"  {'':<44}{'-' * 8}{'-' * 10}")
    print(f"  {'delivered':<44}{WHOLESALE + network:>8.2f}"
          f"{(WHOLESALE + network) * mwh / 1e6:>10.2f}")
    avoidable = sum(v for _, v, shape in rows if shape != "volumetric")
    print(f"\n  Network charges add £{network:.2f}/MWh, "
          f"{network / (WHOLESALE + network):.0%} of the delivered price and "
          f"{1 + network / WHOLESALE:.2f}x")
    print(f"  the wholesale-only figure. £{avoidable:.2f}/MWh of that — "
          f"{avoidable / network:.0%} — is capacity or")
    print("  connection based, so it is avoided by shrinking the grid connection rather")
    print("  than by importing less energy, which is exactly the trade the battery and")
    print("  hydrogen architectures exist to make.")
    if False:
        print("  exactly the trade the battery and hydrogen architectures are there to make.")

    if DUOS_BANDS_SIMPLIFIED:
        print("\n  SIMPLIFIED: the DUoS amber band is defined per-season in the LPN")
        print("  statement and is merged to one all-year window here. Red — the band")
        print("  that matters, an order of magnitude above amber — is exact.")

    OUT_DIR.mkdir(exist_ok=True)
    hh.to_csv(OUT_DIR / "tnuos_hh_demand_tariffs.csv", index=False)
    tdr.to_csv(OUT_DIR / "tnuos_tdr_tariffs.csv", index=False)
    bsuos.to_csv(OUT_DIR / "bsuos_fixed_tariffs.csv", index=False)
    print("\nWrote:\n  optimisation_outputs/tnuos_hh_demand_tariffs.csv"
          "\n  optimisation_outputs/tnuos_tdr_tariffs.csv"
          "\n  optimisation_outputs/bsuos_fixed_tariffs.csv")
    return hh, tdr, bsuos


if __name__ == "__main__":
    run()
