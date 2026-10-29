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
DUoS              Every DNO's *Schedule of charges and other tables 2026/27*,
                  one per licence area, in ``duos_areas``. TRANSCRIBED (11 kV)
                  and DERIVED (33/132 kV, from the area's listed EHV sites); no
                  open API was found for DNO charging statements.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run:  python optimisation/network_charges.py
"""
from __future__ import annotations

import json
from dataclasses import dataclass
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

# Financial year label NESO uses: FY2027 == 2026/27. Every network tariff —
# TNUoS, TDR, BSUoS, and every DNO's DUoS schedule (effective 1 April 2026) — is
# read for this one year and applied to whatever weather/price window is solved.
# Moved from FY2026 (2025/26) on 28 Oct 2026, once the 2026/27 finals were in
# force; the residual band thresholds (EHV_BAND_KVA, T_DEMAND_BAND_MWH) are
# this year's too.
TARIFF_FY = 2027
PUBLICATION = "Final"

DAYS_PER_YEAR = 365.0

# -----------------------------------------------------------------------------
# DUoS — every licence area, 2026/27 (``duos_areas``)
# -----------------------------------------------------------------------------
# Each region is charged on its own DNO's *Schedule of charges and other tables
# 2026/27*: an 11 kV site on Annex 1 "HV Site Specific Band n" in that area's
# time bands, a 33 or 132 kV site on Annex 2 "Designated EHV" charges in that
# area's super-red window. Until 29 Oct 2026 every site was charged on London
# Power Networks' HV row, including 33 and 132 kV sites, which pay EHV charges.
# The CI region and the TNUoS zone partition GB by the same GSP groups
# (``sites.CI_REGION_TO_TNUOS_ZONE``), so the zone names the area.


def duos_tariff_for(tdr_band: str) -> str:
    """The tariff family a distribution site is charged on, by its residual band.
    Every area's "TNUoS Mapping" sheet: "HV Site Specific Band n" is HVn and
    "Designated EHV Site Specific Band n" is EHVn."""
    band = str(tdr_band)
    for family, row in (("EHV", "Designated EHV Site Specific Band"), ("HV", "HV Site Specific Band")):
        if band.startswith(family) and band[len(family):].isdigit():
            return f"{row} {int(band[len(family):])}"
    raise ValueError(f"no DUoS tariff for residual band {tdr_band!r}")


def region_for_zone(zone_no: int) -> int:
    from optimisation import sites
    inverse = {z: r for r, z in sites.CI_REGION_TO_TNUOS_ZONE.items()}
    if zone_no not in inverse:
        raise ValueError(f"no licence area for TNUoS zone {zone_no!r}")
    return inverse[zone_no]


# Triads: the HH locational TNUoS tariff is "charged to customers on their
# metered output during the Triads ... the three half hour settlement periods of
# highest net system demand between November and February inclusive each year
# ... separated by at least ten full days" (NESO, Final TNUoS Tariffs 2026-27,
# report). The Triads are only known in March, after the winter, so a site
# cannot target them exactly. The LP charges the tariff on a variable at least
# as large as import in every half-hour that could be a Triad, which errs a
# little high (the max over the window, not the mean of three half-hours) and
# needs no foresight.
#
# The window, from NESO's published Triads (connection sources, "Triad data"):
# all 21 Triads of 2019/20 to 2025/26 fell on a weekday, November-February, in
# settlement periods 34-37 — 16:30 to 18:30 UK time (GMT in those months).
# TRANSCRIBED from the seven notices; the 2016/17-2018/19 files are daily
# tables in another layout and were not used.
TRIAD_MONTHS = (11, 12, 1, 2)
TRIAD_SETTLEMENT_PERIODS = (34, 37)        # first and last, inclusive


def triad_window(index: pd.DatetimeIndex) -> np.ndarray:
    """True for every step that could hold a Triad, read on the UK clock.

    Settlement period n is the half-hour starting (n-1) x 30 minutes after
    midnight, so 34-37 is 16:30-18:30."""
    clock = pd.DatetimeIndex(index)
    clock = (clock.tz_localize("UTC") if clock.tz is None else clock).tz_convert("Europe/London")
    sp = clock.hour * 2 + clock.minute // 30 + 1
    first, last = TRIAD_SETTLEMENT_PERIODS
    return np.asarray((clock.dayofweek < 5) & clock.month.isin(TRIAD_MONTHS)
                      & (sp >= first) & (sp <= last))


def _cache(name: str, fetch, has=None):
    """Records from the cache, refetched when it is missing or, if ``has`` is
    given, when ``has(records)`` says it lacks what is needed. Without that the
    cache never refreshed: it held 2026/27 as a *forecast* long after NESO
    published the final tariffs."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{name}.json"
    if path.exists():
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
            if has is None or has(records):
                return records, True
        except Exception:
            pass
    records = fetch()
    path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records, False


def _fetch_resource(resource_id: str, name: str, limit: int = 5000, has=None):
    def go():
        url = NESO_DATASTORE + "?" + urllib.parse.urlencode(
            {"resource_id": resource_id, "limit": limit})
        with urllib.request.urlopen(url, timeout=60) as fh:
            payload = json.load(fh)
        if not payload.get("success"):
            raise RuntimeError(f"NESO datastore refused the request for {name}")
        return payload["result"]["records"]
    return _cache(name, go, has)


def _has_year(year_fy: int, publication: str):
    return lambda records: any(r.get("Year_FY") == year_fy and r.get("Publication") == publication
                               for r in records)


def _column(df: pd.DataFrame, *names: str) -> str:
    """The first of ``names`` the frame has. NESO renamed its columns in 2026
    ("Peak_£/kW" became "Peak GBP per kW"), and the cache may hold either."""
    for n in names:
        if n in df.columns:
            return n
    raise KeyError(f"none of {names} in NESO columns {list(df.columns)}")


# =============================================================================
# TNUoS
# =============================================================================
def tnuos_hh_demand(year_fy: int = TARIFF_FY, publication: str = PUBLICATION):
    """Zonal half-hourly demand tariff, £/kW of Triad demand."""
    records, cached = _fetch_resource(TNUOS_HH_RESOURCE, "neso_tnuos_hh_demand",
                                      has=_has_year(year_fy, publication))
    df = pd.DataFrame(records)
    df = df[(df.Year_FY == year_fy) & (df.Publication == publication)]
    if df.empty:
        raise ValueError(
            f"No TNUoS HH demand tariffs for FY{year_fy} {publication}. "
            f"Available: {sorted({(r['Year_FY'], r['Publication']) for r in records})}")
    out = df[["Zone_No", "Zone_Name",
              _column(df, "Peak GBP per kW", "Peak_£/kW"),
              _column(df, "YearRound GBP per kW", "YearRound_£/kW"),
              _column(df, "HHTariff Floored GBP per kW", "HHTariff(Floored)_£/kW")]].copy()
    out.columns = ["zone_no", "zone_name", "peak_GBP_per_kW",
                   "yearround_GBP_per_kW", "tariff_GBP_per_kW"]
    return out.sort_values("zone_no").reset_index(drop=True), cached


def tnuos_tdr(year_fy: int = TARIFF_FY, publication: str = PUBLICATION):
    """Transmission Demand Residual, £ per site per day, banded."""
    records, cached = _fetch_resource(TNUOS_TDR_RESOURCE, "neso_tnuos_tdr",
                                      has=_has_year(year_fy, publication))
    df = pd.DataFrame(records)
    df = df[(df.Year_FY == year_fy) & (df.Publication == publication)]
    if df.empty:
        raise ValueError(f"No TDR tariffs for FY{year_fy} {publication}")
    col = [c for c in df.columns if c.startswith("TDR Tariff")][0]
    out = df[["TDR Band", col]].copy()
    out.columns = ["band", "GBP_per_site_day"]
    out["GBP_per_site_year"] = out["GBP_per_site_day"] * DAYS_PER_YEAR
    return out.reset_index(drop=True), cached


# =============================================================================
# BSUoS
# =============================================================================
def _fy_start(year_fy: int) -> pd.Timestamp:
    return pd.Timestamp(year_fy - 1, 4, 1)


def bsuos_tariffs(year_fy: int = TARIFF_FY):
    """Fixed BSUoS tariff, £/MWh, by the half-year window it applies to."""
    second_half = _fy_start(year_fy) + pd.DateOffset(months=6)
    records, cached = _fetch_resource(
        BSUOS_RESOURCE, "neso_bsuos_fixed",
        has=lambda rs: any(r.get("Publication") == "Final"
                           and pd.Timestamp(r["Fixed Tariff Start Date"]).tz_localize(None)
                           >= second_half for r in rs))
    df = pd.DataFrame(records)
    df = df[df.Publication == "Final"].copy()
    df["start"] = pd.to_datetime(df["Fixed Tariff Start Date"]).dt.tz_localize(None)
    df["end"] = pd.to_datetime(df["Fixed Tariff End Date"]).dt.tz_localize(None)
    out = df[["start", "end", _column(df, "Fixed Tariff_GBP per MWh", "Fixed Tariff £/MWh")]].copy()
    out.columns = ["start", "end", "GBP_per_MWh"]
    return out.sort_values("start").reset_index(drop=True), cached


def bsuos_series(index: pd.DatetimeIndex, year_fy: int = TARIFF_FY) -> pd.Series:
    """£/MWh for every timestamp, from the tariff year's two half-yearly fixed
    tariffs: April-September takes the first, October-March the second.

    Since April 2023 BSUoS is a fixed tariff set in advance, not a cost tied to
    the day, so it follows the tariff year like TNUoS rather than the window's
    dates. (Until 28 Oct 2026 it was read by date, so a 2025 window paid
    2024/25 and 2025/26 BSUoS while TNUoS was 2025/26.)"""
    tariffs, _ = bsuos_tariffs(year_fy)
    first = _fy_start(year_fy)
    halves = {}
    for half, start in (("Apr-Sep", first), ("Oct-Mar", first + pd.DateOffset(months=6))):
        row = tariffs[tariffs.start == start]
        if row.empty:
            raise ValueError(f"No Final BSUoS fixed tariff starting {start:%Y-%m-%d} "
                             f"(FY{year_fy}, {half}).")
        halves[half] = float(row.iloc[0].GBP_per_MWh)
    summer = pd.DatetimeIndex(index).month.isin([4, 5, 6, 7, 8, 9])
    return pd.Series(np.where(summer, halves["Apr-Sep"], halves["Oct-Mar"]),
                     index=index, name="bsuos_GBP_per_MWh")


# =============================================================================
# DUoS
# =============================================================================
def duos_band(index: pd.DatetimeIndex, region: int = 13) -> pd.Series:
    """Red / amber / green for every timestamp, in the area's own 2026/27 HV time
    bands (``duos_areas.HV_TIME_BANDS``), read on the UK clock — the study's
    series are naive UTC."""
    from optimisation import duos_areas
    return pd.Series(duos_areas.hv_band_series(index, region), index=index, name="duos_band")


# =============================================================================
# Assembly — what the LP actually needs
# =============================================================================
# -----------------------------------------------------------------------------
# TDR band selection — the band a site is in, from what it actually draws
# -----------------------------------------------------------------------------
# The bands are PERCENTILES of the GB site population, not fixed sizes, and the
# two tiers are not even measured on the same quantity:
#
#   distribution (LV/HV/EHV)  40th / 70th / 85th percentile of *agreed capacity*
#                             DCUSA Schedule 32, via DCP358
#   transmission (T-Demand)   40th / 70th / 93rd percentile of *gross
#                             consumption*  — CUSC 14.15.138, as amended by
#                             CMP389 (which moved the 3/4 boundary from the 85th)
#
# NESO re-derives the numeric boundaries at each price control from site data
# the DNOs supply, and publishes them with the tariffs. Those below are the
# RIIO-ET3 boundaries, in force from April 2026 and fixed to March 2031.
#
# Sources
# -------
# percentile structure   CUSC Section 14 v1.48a (1 Apr 2026) 14.15.138-139, as amended
#                        by CMP389 (implemented 1 Apr 2023), "Transmission Demand
#                        Residual (TDR) band boundaries updates", NESO.
#                        TRANSCRIBED.
# band boundaries        NESO, *Final TNUoS Tariffs for 2026-27 - Tables*
#                        (30 Jan 2026), Table TB "Non-locational banded charges",
#                        column "Threshold (kWh/MWh or kVA)". TRANSCRIBED. The
#                        report says "The residual band thresholds will remain
#                        the same for the duration of the RIIO-ET3 price control
#                        period." Replaced 5,000 / 12,000 / 21,500 kVA and an
#                        ASSUMED 500,000 MWh (until 28 Oct 2026), which came
#                        from secondary summaries and matched neither year.
# transmission tier      GB's voltage rule, turned into a size by a DNO design
#                        standard — see below.

# Upper bound of each band, inclusive ("<= 3,500"); the last is open.
EHV_BAND_KVA = ((3_500.0, "EHV1"), (11_000.0, "EHV2"),
                (20_000.0, "EHV3"), (float("inf"), "EHV4"))
# HV bands, for a distribution site connected below 22 kV (see connection_voltage).
HV_BAND_KVA = ((500.0, "HV1"), (1_100.0, "HV2"),
               (2_000.0, "HV3"), (float("inf"), "HV4"))
# Transmission-connected sites are banded on gross annual consumption, MWh.
T_DEMAND_BAND_MWH = ((25_131.0, "T-Demand1"), (64_451.0, "T-Demand2"),
                     (163_880.0, "T-Demand3"), (float("inf"), "T-Demand4"))

# -----------------------------------------------------------------------------
# Transmission or distribution, and the connection voltage — by area
# -----------------------------------------------------------------------------
# GB defines transmission by voltage, not by size. In England and Wales it is
# above 132 kV, so a DNO takes demand up to 132 kV; in Scotland 132 kV is
# already transmission, so a DNO takes demand only up to 33 kV (Electricity Act
# 1989 s.64(1) and s.4(4), TRANSCRIBED). A site has a size, not a voltage, so
# each DNO's own design standard turns one into the other: a site connects at
# the lowest voltage that can carry it, and above the largest the DNO connects
# at its top voltage it is transmission-connected. ``Site.transmission_connected``
# overrides all of this — a real connection offer beats any rule.
#
# The voltage also decides the residual band family. The LC14 charging
# statements' glossary (ENWL 2026/27, from DCUSA): "Extra High Voltage (EHV) —
# Nominal voltages of 22kV and above"; "High Voltage (HV) — Nominal voltages of
# at least 1kV and less than 22kV". So 11 kV takes HV1-4; 33 and 132 kV EHV1-4.
#
# One rule per CI region (each region is one DNO licence area), from that DNO's
# own documents where it publishes a figure and the national default where it
# does not. Every document is in the OneDrive folder "DC optimiser/connection
# sources/1 tier rule/voltage by area", with an index of what each says.
#
# National defaults
# -----------------
# 11 kV   12 MVA. The figure two DNO groups publish: UKPN EDS 08-3100 v9.0
#         (08/12/2025) Table 4-1, maximum at 11 kV "12MVA"; Northern Powergrid
#         IMP/001/010 v10.0 (Sep 2024) §3.11.13: above "12MVA at 11kV ...
#         consideration should be given to providing a Point of Supply at EHV".
# 33 kV   120 MVA. ENWL ES216 Issue 4 (Jul 2024) §2: "33kV at Bulk Supply
#         Points (BSP) 120MVA" — the only DNO that publishes one. PROXY elsewhere.
# 132 kV  240 MVA. ES216 §2 and §5.2: "supplied from a dual connection
#         arrangement shall not exceed 240MVA". PROXY elsewhere.
#
# Which sizes are uncertain
# -------------------------
# NGED, *Data Centre Impact Study* (Nov 2025): "Sites below 250 MW could connect
# to either distribution or transmission", and a transmission site energises "to
# a 132kV connection bay or new substation at a 400kV grid supply point". So
# once a site is too big for 33 kV, the DNO's 132 kV and a transmission 132 kV
# bay are like-for-like alternatives: the band runs from the area's 33 kV limit
# to its top. In Scotland the alternative to the DNO's 33 kV is transmission
# itself; the band runs from what one 33 kV feeder carries (ES216 §6.2: "single
# 33kV feeder shall not exceed 45 MVA") to the 33 kV limit, which is a proxy
# there anyway. Running a site in this band both ways is an option
# (``tier_is_uncertain``; the page's tick box), never the default.

@dataclass(frozen=True)
class AreaRule:
    """How one DNO licence area connects demand, in MVA."""
    area: str
    dno: str
    max_11kv: float          # largest demand at 11 kV; above it, the next voltage
    max_33kv: float          # largest at 33 kV; above it 132 kV (or transmission)
    dno_max: float           # largest the DNO connects at all; above it, transmission
    uncertain_from: float    # from here up to dno_max, either tier is plausible
    sources: str
    # Whether max_11kv itself is still 11 kV. True for "up to" limits (ES216's
    # "11kV 15MVA", Northern Powergrid's "in excess of ... 12MVA"); False for
    # UKPN London's "8MVA and above ... connected to the 33kV network".
    max_11kv_inclusive: bool = True


_DEFAULT = dict(max_11kv=12.0, max_33kv=120.0, dno_max=240.0, uncertain_from=120.0)
_SSEN_PLANNING = ("SSEN's own planning standards (PR-NET-NPL-007 rev 2.00, 33 and 22 kV, and PR-NET-NPL-006 rev 2.00, 132 and 66 kV, both June 2026; TG-NET-NPL-010, 11 kV; TG-NET-ENG-005 rev 3.00, Aug 2025) set no size-to-voltage threshold: NPL-007 §8: \"The point of connection (POC) shall be determined by SSEN\"; §9.1: EHV impact assessed for demand \"Greater than or equal to 500 kVA\"")
_SCOTLAND = dict(max_11kv=12.0, max_33kv=120.0, dno_max=120.0, uncertain_from=45.0)

AREA_RULES = {
    1: AreaRule("North Scotland", "SSEN (SHEPD)", **_SCOTLAND, sources=(
        "SHEPD LTDS Nov 2023 §3.1: \"standardised at 33 kV, 11 kV and 230/400 V\"; "
        "132 kV \"regarded as transmission voltage in Scotland\". " + _SSEN_PLANNING
        + ": national defaults, 33 kV limit a PROXY")),
    2: AreaRule("South Scotland", "SPEN (SP Distribution)", **_SCOTLAND, sources=(
        "SPEN connection charging statement Jan 2023 p6: \"In Scotland our "
        "Distribution System voltages range from 33kV downwards\"; SP Transmission "
        "Getting Connected p5: demand \"connects directly to the SP Transmission "
        "network, typically at 132KV and above\". ESDD-02-021 Issue 4 (Design "
        "Manual §17t) has no voltage-by-size rule — only \"High Voltage spurs can be "
        "used for up to 1MW of group demand\"; the connection arrangements "
        "(ESDD-01-006, Design Manual §6) are unpublished and not pursued (28 Oct "
        "2026): national defaults, 33 kV "
        "limit a PROXY")),
    3: AreaRule("North West", "ENWL", max_11kv=15.0, max_33kv=120.0, dno_max=240.0,
                uncertain_from=120.0, sources=(
        "ES216 Issue 4 §2 Scope: \"11kV 15MVA\", \"33kV at Bulk Supply Points (BSP) "
        "120MVA\", \"132kV 240MVA\"; §5.2 dual 132 kV \"shall not exceed 240MVA\". "
        "(§7.2: 7.5 MVA at 11 kV normally, 15 MVA with double-banked cables.)")),
    4: AreaRule("North East", "Northern Powergrid", **_DEFAULT, sources=(
        "IMP/001/010 v10.0 §3.11.13: above \"12MVA at 11kV\" consider EHV. 33 and "
        "132 kV \"considered on an individual basis\": national defaults")),
    5: AreaRule("Yorkshire", "Northern Powergrid", **_DEFAULT, sources=(
        "IMP/001/010 v10.0 §3.11.13: above \"12MVA at 11kV\" consider EHV. 33 and "
        "132 kV \"considered on an individual basis\": national defaults")),
    6: AreaRule("North Wales and Merseyside", "SPEN (SP Manweb)", **_DEFAULT, sources=(
        "SPEN connection charging statement Jan 2023 p6: in England and Wales "
        "\"they range from 132kV downwards\"; SP Manweb Overview Statement (Apr "
        "2026): \"132 kV, 33 kV, 11 kV and LV\". No SPEN demand limit published "
        "(ESDD-02-021 Issue 4 has none): national defaults")),
    7: AreaRule("South Wales", "NGED", max_11kv=12.0, max_33kv=120.0, dno_max=250.0,
                uncertain_from=120.0, sources=(
        "NGED's own policies set no voltage-by-size rule (POL SD3/11 Dec 2024, ST "
        "SD1F/3, ST SD2A/1 Nov 2024, EHV guidance for ICPs Jul 2026). ST SD4OB/1 (Jan "
        "2025) §2: primary switchgear \"up to 630A per metering circuit breaker\" — "
        "12.0 MVA at 11 kV (DERIVED: 630 A x 11 kV x sqrt 3), which supports the 12 MVA "
        "default. Data Centre Impact Study (Nov 2025): 250 MW and over have not "
        "applied for distribution — top taken as 250 (an observation, not a rule); "
        "33 kV a national default")),
    8: AreaRule("West Midlands", "NGED", max_11kv=12.0, max_33kv=120.0, dno_max=250.0,
                uncertain_from=120.0, sources="As South Wales (NGED)"),
    9: AreaRule("East Midlands", "NGED", max_11kv=12.0, max_33kv=120.0, dno_max=250.0,
                uncertain_from=120.0, sources="As South Wales (NGED)"),
    10: AreaRule("East England", "UKPN (EPN)", **_DEFAULT, sources=(
        "EDS 08-3100 v9.0 Table 4-1: 11 kV maximum \"12MVA\". No 33 or 132 kV "
        "limit (EDS 08-4000 §10.1.1: above 15 MW \"invariably\" 132 kV only where "
        "there is no 33 kV layer): national defaults")),
    11: AreaRule("South West", "NGED", max_11kv=12.0, max_33kv=120.0, dno_max=250.0,
                 uncertain_from=120.0, sources="As South Wales (NGED)"),
    12: AreaRule("Southern England", "SSEN (SEPD)", **_DEFAULT, sources=(
        "SEPD LTDS Nov 2023 §3.1 lists the voltages. " + _SSEN_PLANNING + "; "
        "NPL-006 §11-12: single customers connect at 132 kV by loop-in or tee: "
        "national defaults")),
    13: AreaRule("London", "UKPN (LPN)", max_11kv=8.0, max_33kv=120.0, dno_max=240.0,
                 uncertain_from=120.0, max_11kv_inclusive=False, sources=(
        "EDS 08-3100 v9.0 §4.2.1 and EDS 08-4101 v4.0 §1: \"All supplies of 8MVA "
        "and above ... shall be connected to the 33kV network where it is "
        "available\" — written for central London, applied to the whole region "
        "(SIMPLIFIED). 33 and 132 kV: national defaults")),
    14: AreaRule("South East England", "UKPN (SPN)", **_DEFAULT, sources=(
        "As East England (UKPN)")),
}
SCOTTISH_CI_REGIONS = (1, 2)
# The defaults, kept by name for callers and tests.
E_AND_W_DNO_MAX_MVA = _DEFAULT["dno_max"]
SCOTLAND_DNO_MAX_MVA = _SCOTLAND["dno_max"]


def area_rule(region: int) -> AreaRule:
    if region not in AREA_RULES:
        raise ValueError(f"no connection rule for CI region {region!r}")
    return AREA_RULES[region]


def dno_max_mva(region: int) -> float:
    """The largest demand the DNO connects in this CI region, in MVA."""
    return area_rule(region).dno_max


def is_transmission_connected(peak_mw: float, region: int | None,
                              explicit: bool | None = None, *,
                              power_factor: float = 1.0) -> tuple[bool, str]:
    """Whether a site of this size connects to the transmission system.

    One decision, used by both the TDR band and the DUoS liability, because they
    must agree: a site cannot be on T-Demand bands and paying distribution
    charges at the same time. ``region`` is the Carbon Intensity API region,
    whose DNO's rule is read. Returns ``(is_transmission, note)``; the note is
    empty when ``explicit`` decides.
    """
    if explicit is not None:
        return explicit, ""
    if region is None:
        raise ValueError("the tier rule differs by DNO area: pass the site's CI "
                         "region, or state the tier")
    mva = peak_mw / power_factor
    r = area_rule(region)
    return mva > r.dno_max, (
        f"tier from {r.dno}'s rule for {r.area}: {mva:,.0f} MVA against the "
        f"{r.dno_max:g} MVA it connects; set Site.transmission_connected if a "
        f"connection offer says otherwise")


def tier_is_uncertain(peak_mw: float, region: int, *, power_factor: float = 1.0) -> bool:
    """Whether a site of this size could plausibly go either way in this area —
    the sizes worth running both ways. See *Which sizes are uncertain* above."""
    r = area_rule(region)
    return r.uncertain_from < peak_mw / power_factor <= r.dno_max


def connection_voltage(peak_mw: float, region: int | None, transmission_connected: bool, *,
                       power_factor: float = 1.0) -> str:
    """The voltage a site of this size connects at: "11 kV", "33 kV", "132 kV" or
    "transmission". Distribution sites only take the first three."""
    if transmission_connected:
        return "transmission"
    mva = peak_mw / power_factor
    r = area_rule(region)
    if mva < r.max_11kv or (r.max_11kv_inclusive and mva == r.max_11kv):
        return "11 kV"
    if region in SCOTTISH_CI_REGIONS or mva <= r.max_33kv:
        return "33 kV"
    return "132 kV"


def band_floor_mw(transmission_connected: bool, band: str, region: int | None, *,
                  power_factor: float = 1.0) -> float:
    """The smallest connection that still sits in ``band``, in MW.

    The band is a step function of the connection, which an LP cannot carry, so
    it is fixed from the ceiling and the built connection is held inside it:
    ``floor <= cap_grid <= ceiling``. A transmission site's floor is the tier
    boundary itself: its band is set on annual consumption, which the
    connection size does not move. A distribution site's is the top of the band
    below, and an EHV site's is at least the area's 11 kV limit: a connection
    under it would be an 11 kV, HV-banded one. A pinned band outside these gets
    no floor.
    """
    if region is None:
        return 0.0
    if transmission_connected:
        return dno_max_mva(region) * power_factor
    for table, least in ((HV_BAND_KVA, 0.0), (EHV_BAND_KVA, area_rule(region).max_11kv)):
        bands = [b for _, b in table]
        if band in bands:
            i = bands.index(band)
            below = 0.0 if i == 0 else table[i - 1][0] / 1000.0
            return max(below, least) * power_factor
    return 0.0


def delivery_voltage(transmission_connected: bool, tdr_band: str | None = None) -> str:
    """The ecoinvent voltage level a site takes grid electricity at, for its
    carbon: ``optimiser_lca.grid.delivered`` charges losses and network down
    to it.

    The bands are ecoinvent's (high > 24 kV, medium 1-24 kV). A transmission
    connection is high voltage, and so is an EHV one (33 or 132 kV). An HV band
    means an 11 kV connection (``connection_voltage``), which is medium.
    """
    if transmission_connected:
        return "high"
    if tdr_band is None or str(tdr_band).startswith(("EHV", "T-Demand")):
        return "high"
    return "medium"


def tdr_band_for(peak_mw: float, annual_mwh: float | None = None, *,
                 region: int | None = None,
                 power_factor: float = 1.0,
                 transmission_connected: bool | None = None) -> tuple[str, str]:
    """The TDR band for a site, and a note on how sound the answer is.

    ``peak_mw`` is the agreed capacity the site would contract for — for this
    study, the grid connection the optimiser sizes, or the flat load if the
    connection is not known yet. Returns ``(band, note)``; ``note`` is empty
    only when the answer rests on transcribed boundaries alone.

    ``annual_mwh`` is the site's gross annual consumption, which sets a
    transmission site's band; a distribution site's is set by ``peak_mw``.

    The band matters more than its size suggests: in 2026/27 EHV2 is
    £423,174/year and T-Demand4 £7,602,671/year, so getting the tier wrong is a
    larger error than any plausible mistake inside a tier.
    """
    if peak_mw <= 0:
        raise ValueError(f"peak_mw must be positive, got {peak_mw}")
    transmission_connected, inferred = is_transmission_connected(
        peak_mw, region, transmission_connected, power_factor=power_factor)

    if transmission_connected:
        if annual_mwh is None:
            return "T-Demand4", (
                "T-Demand bands are set on gross annual consumption, and none "
                "was given; top band returned. " + inferred).strip()
        band = next(b for ceiling, b in T_DEMAND_BAND_MWH if annual_mwh <= ceiling)
        return band, inferred

    kva = peak_mw * 1000.0 / power_factor
    voltage = connection_voltage(peak_mw, region, False, power_factor=power_factor)
    table = HV_BAND_KVA if voltage == "11 kV" else EHV_BAND_KVA
    band = next(b for ceiling, b in table if kva <= ceiling)
    return band, (f"connected at {voltage} (ES216), so "
                  f"{'HV' if table is HV_BAND_KVA else 'EHV'} bands. " + inferred).strip()


def import_charges(index: pd.DatetimeIndex, zone_no: int, tdr_band: str,
                   power_factor: float = 1.0,
                   transmission_connected: bool = False,
                   duos_case: str = "central",
                   site: tuple | None = None,
                   connection_voltage: str | None = None):
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

    # DUoS is levied by the DNOs under DCUSA on users of the *distribution*
    # network. A site with a Bilateral Connection Agreement takes its supply
    # from the transmission system and pays none of it — not the capacity
    # charge, not the p/kWh bands, not the standing charge. Charging it anyway
    # was the single largest error in the connection cost: at the 300 MW
    # Highland site it put £33,543.50/MW/year of London Power Networks HV
    # capacity charge on a Scottish transmission connection, £29.1 m/year.
    duos_area = None
    if transmission_connected:
        duos_capacity_per_mw_year = 0.0
        duos_fixed_per_year = 0.0
        duos_vol = pd.Series(0.0, index=index, name="duos_GBP_per_MWh")
        duos_tariff = None
    else:
        from optimisation import duos_areas
        d = duos_areas.charges(index, region_for_zone(zone_no), tdr_band,
                               case=duos_case, power_factor=power_factor,
                               site=site, connection_voltage=connection_voltage)
        duos_capacity_per_mw_year = d["capacity_GBP_per_MW_year"]
        duos_fixed_per_year = d["fixed_GBP_per_year"]
        duos_vol = d["duos_GBP_per_MWh"]
        duos_tariff, duos_area = d["tariff"], d["area"]

    bsuos = bsuos_series(index)
    volumetric = bsuos + duos_vol
    return {
        "volumetric_GBP_per_MWh": volumetric.rename("network_GBP_per_MWh"),
        # Separately too: BSUoS is charged on loss-adjusted volumes, DUoS on
        # metered ones, so the levies module grosses up one and not the other.
        "bsuos_GBP_per_MWh": bsuos,
        "duos_GBP_per_MWh": duos_vol,
        "capacity_GBP_per_MW_year": tnuos_per_kw * 1000.0 + duos_capacity_per_mw_year,
        "fixed_GBP_per_year": tdr_per_year + duos_fixed_per_year,
        "components": {
            "tnuos_locational_GBP_per_MW_year": tnuos_per_kw * 1000.0,
            "duos_capacity_GBP_per_MW_year": duos_capacity_per_mw_year,
            "tnuos_tdr_GBP_per_year": tdr_per_year,
            "duos_fixed_GBP_per_year": duos_fixed_per_year,
            "bsuos_mean_GBP_per_MWh": float(bsuos_series(index).mean()),
            "duos_mean_GBP_per_MWh": float(duos_vol.mean()),
            "transmission_connected": transmission_connected,
            "zone_name": zone.iloc[0].zone_name,
            "tdr_band": tdr_band,
            "duos_tariff": duos_tariff,
            "duos_area": duos_area,
            "duos_site_specific": None if transmission_connected else d.get("site_specific"),
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
