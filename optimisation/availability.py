"""
Where can a data centre of this size connect? (COST_PLAN §1.10 R5, 30 Oct 2026)
=============================================================================

For a given IT load the register is read the other way round: not "what does
the connection cost at this site" but "every substation in Great Britain with
room for the connection, each priced through the same chain the optimiser
uses — tier, voltage, band, the area's own network charges and build prices,
losses and levies — without solving". The result is a ranked list of
connectable places with the grid's annual cost and carbon behind each one.

Room is read three ways (``candidates``):
  today               ``demand_headroom_mw`` as the company publishes it (R2)
  net of contracted   room after demand already agreed but not yet connected,
                      where the company publishes it (NGED, Northern Powergrid,
                      SSEN) or it can be derived (headroom minus contracted)
  in year N           the company's scenario headroom for that year (R3), its
                      central scenario; substations without a forward view drop out

What is priced (``price``), for a flat load at the connection's ceiling:
  energy    the 2025 wholesale mean plus BSUoS, grossed up for the area's
            losses at the connection voltage, plus the area's DUoS unit rate
            and the policy levies, times the load's annual MWh
  capacity  TNUoS locational (the zone's tariff) and DUoS capacity (site-
            specific where the connection substation has a named price node),
            times the connection
  fixed     the residual band charge and the DUoS fixed charge
  build     the area's connection price list, annualised, at the default 2 km
            route (the site is taken to be at the substation)
Carbon is the region's mean grid generation intensity (its cached series,
longest window on disk) delivered at the connection voltage, times the energy.
Both are "the grid alone": the optimiser's renewables, storage and hydrogen
are what ``scripts/availability_map.py --solve`` adds for the top few.

Caveats. The headroom is the company's figure on the company's basis
(``headroom_basis`` says which; ``headroom_as_of`` how old). The tier and
voltage are the area's published rules read for the size, so a candidate at a
higher voltage than the rule's is listed too (a 33 kV site may take a 132 kV
offer). A candidate's "room" says the substation can take the demand on its
own transformers; the upstream grid supply point may not (R4 covers five of
six companies at that level, and only the transmission layer reads it).
"""
from __future__ import annotations

import glob
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from optimisation import connection_cost as cc, duos_areas as D, levies, network_charges as nc, sites, substations as S

ROOT = Path(__file__).resolve().parent.parent
PRICE_YEAR = 2025
YEAR_INDEX = pd.date_range(f"{PRICE_YEAR}-01-01", f"{PRICE_YEAR}-12-31 23:00", freq="h")
PUE_DEFAULT = 1.2
TRANSMISSION_REGION_KM = 60.0     # a 275/400 kV substation takes the area of the nearest distribution substation


@lru_cache(maxsize=1)
def wholesale_mean() -> tuple[float, str]:
    """Mean 2025 wholesale price (£/MWh) from the longest clean Elexon file on disk."""
    files = sorted(glob.glob(str(ROOT / "price_outputs" / f"elexon_market_index_clean_{PRICE_YEAR}-01-01_*.csv")),
                   key=lambda f: Path(f).stat().st_size, reverse=True)
    if not files:
        raise FileNotFoundError("no 2025 Elexon price file in price_outputs/")
    p = pd.read_csv(files[0], usecols=["price_GBP_per_MWh"])
    return float(p.price_GBP_per_MWh.mean()), Path(files[0]).name


@lru_cache(maxsize=32)
def region_generation_intensity(region: int) -> tuple[float, str]:
    """Mean grid generation intensity (kg CO2e per kWh generated) for a region,
    from its longest cached series; the label says which window."""
    files = glob.glob(str(ROOT / "custom_grid_lca_outputs" / f"custom_grid_lca_carbon_api_*_r{int(region)}_*.csv"))
    if not files:
        return float("nan"), "no cached grid series for this region"
    best, n = None, -1
    for f in files:
        try:
            d = pd.read_csv(f, usecols=["generation_kgco2e_per_kwh"])
        except ValueError:
            continue
        if len(d) > n:
            best, n, mean = f, len(d), float(d.generation_kgco2e_per_kwh.mean())
    if best is None:
        return float("nan"), "no usable grid series"
    m = re.search(r"_(\d{4}-\d{2}-\d{2})T.*_to_T(\d{4}-\d{2}-\d{2})", Path(best).name)
    return mean, (f"{m.group(1)} to {m.group(2)}" if m else Path(best).name) + f" ({n:,} half-hours)"


@lru_cache(maxsize=1)
def _transmission_regions() -> pd.Series:
    """Region (CI area) of every transmission-layer row: that of the nearest distribution substation."""
    from scipy.spatial import cKDTree
    s = S.substations()
    dist = s[(s.level_std != "transmission") & s.region.notna()]
    tx = s[s.level_std == "transmission"]
    tree = cKDTree(np.c_[dist.lat, dist.lon * 0.6])
    d, i = tree.query(np.c_[tx.lat, tx.lon * 0.6])
    reg = dist.region.to_numpy()[i].astype(float)
    reg[d * 111.0 > TRANSMISSION_REGION_KM] = np.nan
    return pd.Series(reg, index=tx.index)


def sizing(size_mw_it: float, pue: float = PUE_DEFAULT, headroom: float | None = None) -> dict:
    load = float(size_mw_it) * float(pue)
    conn, note = sites.max_connection_mw(load, headroom)
    return {"size_mw_it": float(size_mw_it), "pue": float(pue), "load_mw": load, "connection_mw": conn,
            "annual_mwh": load * 8760.0, "connection_note": note}


def _band(conn_mw: float, annual_mwh: float, voltage: str, transmission: bool) -> str:
    if transmission:
        return next(b for ceiling, b in nc.T_DEMAND_BAND_MWH if annual_mwh <= ceiling)
    kva = conn_mw * 1000.0
    table = nc.HV_BAND_KVA if voltage == "11 kV" else nc.EHV_BAND_KVA
    return next(b for ceiling, b in table if kva <= ceiling)


def candidates(size_mw_it: float, pue: float = PUE_DEFAULT, headroom: float | None = None, *,
               year: int | None = None, scenario: str | None = None, net_of_contracted: bool = False,
               regions=None, include_unknown: bool = False) -> pd.DataFrame:
    """Every substation with room for the connection a site of this size needs.

    Per area the published rule gives the tier and the lowest voltage; every
    voltage from there to the area's top is searched (a substation with room
    a voltage up is a real offer). ``year`` reads the company's scenario
    headroom for that year instead of today's; ``net_of_contracted`` reads
    room after agreed demand. ``include_unknown`` keeps substations that
    publish no figure, flagged ``room == "unknown"``."""
    z = sizing(size_mw_it, pue, headroom)
    conn = z["connection_mw"]
    s = S.with_year_headroom(year, scenario) if year is not None else S.substations().copy()
    if year is not None:
        s["room_mw"], s["room_basis"] = s.headroom_year_mw, "scenario headroom in " + str(year) + " (" + s.headroom_year_scenario.astype(str) + ")"
    elif net_of_contracted:
        derived = s.demand_headroom_mw - s.demand_contracted_mw
        s["room_mw"] = s.headroom_net_of_contracted_mw.fillna(derived)
        s["room_basis"] = np.where(s.headroom_net_of_contracted_mw.notna(), "published net of contracted",
                                   np.where(derived.notna(), "headroom minus contracted (derived)",
                                            np.where(s.demand_headroom_mw.notna(), "headroom; no contracted figure published", "")))
        s.loc[s.room_mw.isna() & s.demand_headroom_mw.notna(), "room_mw"] = s.demand_headroom_mw
    else:
        s["room_mw"], s["room_basis"] = s.demand_headroom_mw, "published headroom today"
    tx_region = _transmission_regions()
    s.loc[tx_region.index, "region"] = tx_region
    out = []
    for r in sorted(regions or D.AREA_NAMES):
        trans, _ = nc.is_transmission_connected(conn, r)
        if trans:
            rows = s[(s.level_std == "transmission") & (s.region == r)].assign(voltage="transmission", transmission=True)
            out.append(rows)
            continue
        rule = nc.connection_voltage(conn, r, False)
        top = "33 kV" if r in S.SCOTTISH_REGIONS else "132 kV"
        order = S.DISTRIBUTION_VOLTAGES[S.DISTRIBUTION_VOLTAGES.index(rule): S.DISTRIBUTION_VOLTAGES.index(top) + 1]
        for v in order:
            lv = S.levels_for(v, r)
            rows = s[(s.region == r) & s.level_std.isin(lv)].assign(voltage=v, transmission=False)
            out.append(rows)
    c = pd.concat(out, ignore_index=True) if out else s.iloc[0:0]
    c["room"] = np.where(c.room_mw.isna(), "unknown", np.where(c.room_mw >= conn, "room", "short"))
    c = c[(c.room == "room") | (include_unknown & (c.room == "unknown"))]
    # a substation reachable at two voltages is one candidate: keep the lowest voltage
    c = c.sort_values("voltage", key=lambda v: v.map({"11 kV": 0, "33 kV": 1, "132 kV": 2, "transmission": 3}))
    c = c.assign(_la=c.lat.round(3), _lo=c.lon.round(3)).drop_duplicates(subset=["company", "_la", "_lo", "level_std"])
    c = c.drop(columns=["_la", "_lo"]).reset_index(drop=True)
    for k, v in z.items():
        c.attrs[k] = v
    return c


def price(cands: pd.DataFrame, size_mw_it: float, pue: float = PUE_DEFAULT, headroom: float | None = None,
          case: str = "central") -> pd.DataFrame:
    """The grid's annual cost and carbon at each candidate, for a flat load at the ceiling (no solve)."""
    z = sizing(size_mw_it, pue, headroom)
    conn, energy, load = z["connection_mw"], z["annual_mwh"], z["load_mw"]
    whole, price_file = wholesale_mean()
    lev = float(levies.import_levies(YEAR_INDEX)["levies_GBP_per_MWh"].mean())
    rows = []
    cache: dict = {}
    for r in cands.itertuples(index=False):
        region, v, trans = int(r.region), r.voltage, bool(r.transmission)
        band = _band(conn, energy, v, trans)
        key = ("loss", region, v)
        if key not in cache:
            cache[key] = float(levies.loss_series(YEAR_INDEX, v, region).mean())
        loss = cache[key]
        key = ("build", region, v, trans)
        if key not in cache:
            cache[key] = cc.connection_costs(region, trans, case, connection_voltage=v)
        build = cache[key]
        ch = nc.import_charges(YEAR_INDEX, zone_no=sites.CI_REGION_TO_TNUOS_ZONE[region], tdr_band=band,
                               transmission_connected=trans, site=(r.lat, r.lon), connection_voltage=v)
        comp = ch["components"]
        unit = (whole + comp["bsuos_mean_GBP_per_MWh"]) * loss + comp["duos_mean_GBP_per_MWh"] + lev
        cap = ch["capacity_GBP_per_MW_year"] + build["per_MW_year_GBP"]
        fixed = ch["fixed_GBP_per_year"] + build["fixed_per_year_GBP"]
        total = energy * unit + conn * cap + fixed
        gen, window = region_generation_intensity(region)
        from optimiser_lca import grid as grid_lca
        delivered = grid_lca.delivered(gen, nc.delivery_voltage(trans, band)) if gen == gen else float("nan")
        site_specific = (comp.get("duos_site_specific") or {}).get("how")
        rows.append({
            "band": band, "tier": "national grid" if trans else "local network",
            "cost_m_per_year": total / 1e6, "cost_GBP_per_MWh": total / energy,
            "energy_GBP_per_MWh": unit, "capacity_GBP_per_MW_year": cap, "fixed_GBP_per_year": fixed,
            "tnuos_GBP_per_MW_year": comp["tnuos_locational_GBP_per_MW_year"],
            "duos_capacity_GBP_per_MW_year": comp["duos_capacity_GBP_per_MW_year"],
            "build_GBP_per_MW_year": build["per_MW_year_GBP"], "build_fixed_GBP_per_year": build["fixed_per_year_GBP"],
            "duos_how": site_specific or ("none (national grid)" if trans else "area tariff"),
            "loss_gross_up": loss, "carbon_kg_per_kwh_delivered": delivered,
            "carbon_t_per_year": energy * delivered if delivered == delivered else float("nan"),
            "carbon_window": window,
        })
    out = pd.concat([cands.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    out.attrs.update(z, wholesale_GBP_per_MWh=whole, price_file=price_file, levies_GBP_per_MWh=lev, case=case)
    return out


COLUMNS = ["rank", "region", "area", "company", "name", "level", "voltage", "tier", "band", "lat", "lon",
           "room_mw", "room_basis", "headroom_basis", "headroom_as_of", "demand_contracted_mw",
           "cost_m_per_year", "cost_GBP_per_MWh", "energy_GBP_per_MWh", "capacity_GBP_per_MW_year",
           "fixed_GBP_per_year", "duos_how", "carbon_kg_per_kwh_delivered", "carbon_t_per_year", "carbon_window"]


def availability(size_mw_it: float, pue: float = PUE_DEFAULT, headroom: float | None = None, *,
                 year: int | None = None, net_of_contracted: bool = False, regions=None,
                 case: str = "central", top: int | None = None, by: str = "cost") -> pd.DataFrame:
    """Candidates with room, priced and ranked (``by`` "cost" or "carbon")."""
    c = candidates(size_mw_it, pue, headroom, year=year, net_of_contracted=net_of_contracted, regions=regions)
    if c.empty:
        return c
    p = price(c, size_mw_it, pue, headroom, case)
    key = "cost_m_per_year" if by == "cost" else "carbon_t_per_year"
    p = p.sort_values([key, "cost_m_per_year"]).reset_index(drop=True)
    p.insert(0, "rank", np.arange(1, len(p) + 1))
    p["area"] = p.region.astype(int).map(D.AREA_NAMES)
    cols = [c for c in COLUMNS if c in p] + [c for c in p.columns if c not in COLUMNS]
    out = p[cols]
    out.attrs.update(p.attrs)
    return out.head(top) if top else out


def summary(av: pd.DataFrame) -> pd.DataFrame:
    """Per area: candidates with room, the cheapest, and its cost."""
    if av.empty:
        return pd.DataFrame()
    g = av.groupby(["region", "area"], as_index=False).agg(
        with_room=("name", "size"), voltages=("voltage", lambda s: ", ".join(sorted(set(s)))),
        cheapest=("name", "first"), cost_m_per_year=("cost_m_per_year", "min"),
        carbon_t_per_year=("carbon_t_per_year", "min"))
    return g.sort_values("cost_m_per_year").reset_index(drop=True)
