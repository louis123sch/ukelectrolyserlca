"""
Site-specific local network charges for a 33 or 132 kV site (the EDCM).
=============================================================================

A Designated EHV site pays its DNO a tariff set for its own connection point,
not a published table (``duos_areas`` carries the published 11 kV tables).
Until 29 Oct 2026 the model charged such a site the median of its area's
listed sites in the same residual band (``duos_areas.EHV_BANDS``). This module
charges it for *where it is*, with that median kept as the fallback.

The method (DCUSA Schedule 18 v17.5 §6.3, §19.4-19.6; Schedule 17 the same
with the FCP charge 1)
----------------------------------------------------------------------------
    capacity charge (p/kVA/day) = local charge 1 (£/kVA/yr) x 100 / 365 + A
    super-red rate  (p/kWh)     = remote charge 1 (£/kVA/yr) / super-red hours x 100 + B
    fixed charge    (p/day)     = residual fixed charge for the band + sole-use asset charge

local and remote charge 1 are the "Nodal prices" every DNO publishes with its
schedule of charges, read for the located price node nearest the site at its
voltage (``substations.nearest_price_node``). A collects the parts the method
sets area-wide — transmission exit, network rates and direct costs on the
site's assets, indirect costs x (0.5 + coincidence factor) — which no DNO
publishes; B is zero in the method. Both are CALIBRATED from each area's
listed sites by ``scripts/calibrate_ehv_charges.py``: on NGED's areas, where
listed sites can be tied to nodes, A is the median of capacity - local/365
over those sites (the quartiles give low and high); elsewhere the median
listed capacity less the median local/365 over the area's nodes, a method
that lands within 0.1-0.4 p/kVA/day of the paired one on NGED. The fixed
charge keeps ``duos_areas.EHV_BANDS`` (the listed sites' quartiles by band).

What the nodal price moves
--------------------------
Little, for most sites. The pilot (29 Oct 2026, 37 NGED sites): a listed
site's capacity charge barely tracks its node's local price (correlations
-0.3 to +0.5); the area-wide A of 1-3 p/kVA/day dominates, and Maxwell House
Data Centre (East Midlands) sits on a node priced 0/0 and pays 1.33 p/kVA/day
against the area's A of 1.1. So the site-specific result is "the area's
add-on, plus the local price where there is one", and the quoted range is the
spread of the area's own sites.

Where it does not apply
-----------------------
SSEN's two areas charged outside the EDCM for 2026/27 (Ofgem direction, SSEN
request of 24 Jan 2025): their nodal prices are carried over from earlier
years and their negative fixed charges moved into capacity charges, so the
formula would not reproduce their listed charges. They keep the fallback.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimisation import duos_areas, substations   # noqa: E402
CALIBRATION = ROOT / "optimisation_outputs" / "substation_register" / "ehv_calibration.csv"
OUTSIDE_EDCM_2026_27 = (1, 12)
CASES = ("low", "central", "high")


@lru_cache(maxsize=1)
def calibration() -> pd.DataFrame:
    return pd.read_csv(CALIBRATION).set_index("region")


def addon(region: int, voltage_kv: float, case: str) -> tuple[float | None, float | None, str]:
    """(A p/kVA/day, B p/kWh, basis) for the area at this voltage."""
    c = calibration().loc[region]
    v = f"{voltage_kv:g}kV"
    if pd.notna(c.get(f"A_pairs_{v}", np.nan)):
        a = {"low": c[f"A_pairs_q25_{v}"], "central": c[f"A_pairs_{v}"], "high": c[f"A_pairs_q75_{v}"]}[case]
        return float(a), float(c[f"B_pairs_{v}"]), "listed sites tied to their nodes"
    if pd.notna(c.get(f"A_median_{v}", np.nan)):
        a = {"low": c[f"A_q25_{v}"], "central": c[f"A_median_{v}"], "high": c[f"A_q75_{v}"]}[case]
        return float(a), float(c[f"B_median_{v}"]), "listed-site medians less the area's node median"
    return None, None, "no calibration"


def site_charges(lat: float, lon: float, region: int, voltage: str, band: str,
                 case: str = "central", power_factor: float = 1.0) -> dict:
    """A 33 or 132 kV site's capacity charge, super-red rate and fixed charge.

    Returns ``capacity_GBP_per_MW_year``, ``super_red_p_per_kwh``,
    ``fixed_GBP_per_year``, the node used and ``how`` — or the area median with
    ``how="area median"`` where the method does not apply or no node is found.
    """
    if case not in CASES:
        raise ValueError(f"case must be one of {CASES}, got {case!r}")
    fam, n = duos_areas._family_band(band)
    if fam != "EHV":
        raise ValueError(f"site_charges is for EHV bands, got {band!r}")
    b = duos_areas.EHV_BANDS[region][n]
    fixed = duos_areas._pick(b.fixed_p_per_day, case) / 100.0 * 365.0
    fallback = {
        "capacity_GBP_per_MW_year": duos_areas._pick(b.capacity_p_per_kva_day, case) / 100.0 * 365.0 * 1000.0 / power_factor,
        "super_red_p_per_kwh": duos_areas._pick(b.super_red_p_per_kwh, case),
        "fixed_GBP_per_year": fixed, "how": "area median", "node": None, "basis": None,
    }
    if region in OUTSIDE_EDCM_2026_27:
        fallback["note"] = "SSEN charged outside the EDCM for 2026/27 (Ofgem direction): listed-site median kept"
        return fallback
    vkv = {"33 kV": 33.0, "132 kV": 132.0}.get(voltage)
    if vkv is None:
        fallback["note"] = f"no site-specific method for {voltage}"
        return fallback
    a, bb, basis = addon(region, vkv, case)
    node = substations.price_node_at(lat, lon, region, vkv)
    if a is None or node is None:
        fallback["note"] = ("no calibration for this area" if a is None else
                            "no price node matched by name to the connection substation (area figure, decision of 30 Oct 2026)")
        return fallback
    hours = float(calibration().loc[region, "super_red_hours"])
    cap_p = max(0.0, node["local_GBP_per_kVA"] * 100.0 / 365.0 + a)
    sr_p = max(0.0, node["remote_GBP_per_kVA"] / hours * 100.0 + bb)
    return {
        "capacity_GBP_per_MW_year": cap_p / 100.0 * 365.0 * 1000.0 / power_factor,
        "super_red_p_per_kwh": sr_p, "fixed_GBP_per_year": fixed,
        "how": "site-specific", "basis": basis, "node": node, "addon_p_per_kva_day": a,
        "capacity_p_per_kva_day": cap_p, "super_red_hours": hours,
        "note": f"node {node['node_id']} at {node['substation']} ({node['how']}, {node['straight_km']:.1f} km): "
                f"local {node['local_GBP_per_kVA']:.2f}, remote {node['remote_GBP_per_kVA']:.2f} £/kVA/yr; "
                f"area add-on {a:.2f} p/kVA/day ({basis})",
    }


if __name__ == "__main__":
    for name, lat, lon, region, v in (("Maxwell House DC (East Midlands)", 52.002384, -0.737258, 9, "33 kV"),
                                      ("Vantage, Imperial Park (South Wales)", 51.548, -3.031, 7, "132 kV"),
                                      ("Cardiff centre (approx.)", 51.48, -3.18, 7, "132 kV"),
                                      ("London Docklands", 51.505, -0.02, 13, "132 kV")):
        s = site_charges(lat, lon, region, v, "EHV4")
        print(f"{name:<38} {s['how']:<14} capacity £{s['capacity_GBP_per_MW_year']:>7,.0f}/MW/yr  "
              f"super-red {s['super_red_p_per_kwh']:.3f} p/kWh  fixed £{s['fixed_GBP_per_year']:>9,.0f}/yr\n    {s.get('note', '')}")
