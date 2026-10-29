"""Calibrate each area's site-specific (EDCM) demand charges from its listed
EHV sites, for ``optimisation.ehv_charges``.

    python -I scripts/calibrate_ehv_charges.py ["<OneDrive>/DC optimiser/connection sources"]

Schedule 18 (LRIC) §6.3 and §19.4-19.6, Schedule 17 (FCP) likewise:
    capacity (p/kVA/day)  = local charge 1 (£/kVA/yr) x 100/365 + A
    super-red (p/kWh)     = remote charge 1 (£/kVA/yr) / super-red hours x 100 + B
    fixed (p/day)         = residual fixed charge for the band + sole-use asset charge
A collects the area-wide parts (transmission exit, network rates and direct
costs on the site's assets, indirect costs x (0.5 + coincidence factor));
B is zero in the method and is measured here as a check. Neither is
published, so both are calibrated from each area's Annex 2 import sites:

    pairs   NGED only: a listed site matched by name to a located substation,
            its nearest price node read, A = capacity - local/365 per site;
            the area's A is the median, the quartiles its range.
    medians every area: median listed capacity (band 3-4 network sites) minus
            the median local/365 over the area's located network nodes at
            33 and 132 kV. Measured against `pairs` on NGED.

Writes optimisation_outputs/substation_register/ehv_calibration.csv. SSEN's
two areas charged outside the EDCM for 2026/27 (Ofgem direction): their
rows are marked and ehv_charges keeps the listed-site medians there.
"""
from __future__ import annotations

import re
import statistics as st
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimisation import duos_areas as D          # noqa: E402
from optimisation import substations as SUB       # noqa: E402

DEFAULT_SOURCES = Path.home() / "OneDrive - Imperial College London" / "DC optimiser" / "connection sources"
OUT = ROOT / "optimisation_outputs" / "substation_register" / "ehv_calibration.csv"
CUSTOMER = re.compile(r"\b(PV|SOLAR|WIND|WF|BESS|BATTERY|STORAGE|ESS|STOR|CHP|GEN|GENERATION|BIOMASS|LANDFILL|HYDRO|"
                      r"EFW|GAS|ENERGY|POWER)\b", re.I)
OUTSIDE_EDCM_2026_27 = (1, 12)      # SSEN: Ofgem direction, 24 Jan 2025 request

# "Residual Charging Bands" sheet, Designated EHV Properties, £ per MPAN per year,
# bands 1-4 (29 Oct 2026). NGED's sheets leave the value blank; SSEN North Scotland
# publishes it as p/kVA/day on capacity instead (and is outside the EDCM anyway).
RESIDUAL_FIXED_GBP_PER_YEAR = {
    2: (5147.44, 38268.67, 80308.77, 101405.45),
    3: (630.87, 5419.47, 11063.57, 13548.05),
    4: (9822.53, 19452.80, 70840.02, 262737.84),
    5: (8010.03, 48071.77, 132534.86, 376746.25),
    6: (49888.97, 155102.98, 300762.94, 779525.50),
    10: (18297.45, 88775.99, 212600.29, 278592.24),
    12: (3674.03, 23938.43, 64035.05, 264098.13),
    13: (942.58, 8702.12, 25455.92, 53850.23),
    14: (9237.98, 44473.17, 120036.35, 227029.22),
}


def listed_sites(src: Path, region: int) -> pd.DataFrame:
    """Annex 2 import rows: band, capacity p/kVA/day, super-red p/kWh, fixed p/day, name."""
    d = src / "3 DUoS"
    f = d / "2026-27 schedules" / D.FILES[region]
    f = f if f.exists() else d / D.FILES[region]
    rows = list(openpyxl.load_workbook(f, read_only=True, data_only=True)["Annex 2 Designated EHV charges"].iter_rows(values_only=True))
    h = next(i for i, r in enumerate(rows) if any(isinstance(c, str) and "Residual Charging Band" in c for c in r))
    hdr = [str(c or "").replace("\n", " ") for c in rows[h]]
    col = lambda *k: next((j for j, c in enumerate(hdr) if all(x.lower() in c.lower() for x in k)), None)
    jb, js, jf, jc, jn = col("Residual Charging Band"), col("Import", "Super Red"), col("Import", "fixed"), col("Import", "capacity charge"), col("Name")
    num = lambda x: float(x) if isinstance(x, (int, float)) else None
    out = []
    for r in rows[h + 1:]:
        if len(r) <= jc or (num(r[js]) is None and num(r[jc]) is None):
            continue
        b = str(r[jb]).split(".")[0].strip() if r[jb] is not None else ""
        if b not in ("1", "2", "3", "4"):
            continue
        name = str(r[jn]) if jn is not None and r[jn] is not None else ""
        out.append({"band": int(b), "cap_p": num(r[jc]), "sr_p": num(r[js]) or 0.0, "fx_p": num(r[jf]), "name": name,
                    "customer": bool(CUSTOMER.search(name))})
    return pd.DataFrame(out)


def super_red_hours(region: int) -> float:
    idx = pd.date_range("2026-04-01", "2027-03-31 23:30", freq="30min")
    return float(D.super_red_window(idx, region).sum()) / 2


_STOP = r"\b(LTD|LIMITED|PLC|UK|THE|AND|IMP|IMPORT|EXPORT|SITE|\d+(\.\d+)?\s*KV|\d+/\d+KV|S\s*STN|SUBSTATION|PRIMARY|GRID|CHP|NO|\d+)\b"
_key = lambda s: " ".join(re.sub(_STOP, " ", re.sub(r"[^A-Z0-9 ]", " ", str(s).upper())).split())


def nged_pairs(region: int, sites: pd.DataFrame) -> pd.DataFrame:
    """Listed sites matched by name (Jaccard >= 0.75) to a located NGED substation, with the nearest node."""
    subs = SUB.substations()
    sub = subs[(subs.region == region) & (subs.company == "NGED")]
    pool = {_key(n): r for n, r in zip(sub.name, sub.itertuples())}
    rows = []
    for s in sites.itertuples():
        k = set(_key(s.name).split())
        if not k:
            continue
        sc = sorted(((len(k & set(p.split())) / len(k | set(p.split())), p) for p in pool if p.split()), reverse=True)
        if not sc or sc[0][0] < 0.75:
            continue
        r = pool[sc[0][1]]
        for v in (33.0, 132.0):
            pn = SUB.nearest_price_node(r.lat, r.lon, region, v)
            if pn:
                rows.append({"site": s.name, "band": s.band, "v": v, "cap_p": s.cap_p, "sr_p": s.sr_p, "fx_p": s.fx_p,
                             "local": pn["local_GBP_per_kVA"], "remote": pn["remote_GBP_per_kVA"], "node_km": pn["straight_km"]})
    return pd.DataFrame(rows)


def main(src: Path) -> int:
    nodes = SUB.price_nodes()
    out = []
    for region in sorted(D.FILES):
        sites = listed_sites(src, region)
        net = sites[~sites.customer & sites.band.isin([3, 4])]
        hrs = super_red_hours(region)
        n = nodes[(nodes.region == region) & (nodes.kind == "network")]
        row = {"region": region, "area": D.AREA_NAMES[region], "super_red_hours": hrs,
               "outside_edcm_2026_27": region in OUTSIDE_EDCM_2026_27,
               "listed_sites": len(sites), "listed_network_band34": len(net)}
        for v in (33.0, 132.0):
            nv = n[n.voltage_kv == v]
            loc = nv.local_GBP_per_kVA * 100 / 365
            rem = nv.remote_GBP_per_kVA / hrs * 100
            cap_med = net.cap_p.median() if len(net) else np.nan
            sr_med = net.sr_p.median() if len(net) else np.nan
            row[f"A_median_{v:g}kV"] = round(cap_med - loc.median(), 3) if len(nv) else np.nan
            row[f"A_q25_{v:g}kV"] = round(net.cap_p.quantile(.25) - loc.median(), 3) if len(nv) and len(net) else np.nan
            row[f"A_q75_{v:g}kV"] = round(net.cap_p.quantile(.75) - loc.median(), 3) if len(nv) and len(net) else np.nan
            row[f"B_median_{v:g}kV"] = round(sr_med - rem.median(), 4) if len(nv) else np.nan
            row[f"nodes_{v:g}kV"] = len(nv)
        if region in (7, 8, 9, 11):
            p = nged_pairs(region, sites)
            for v in (33.0, 132.0):
                g = p[p.v == v]
                if len(g) >= 4:
                    a = g.cap_p - g.local * 100 / 365
                    b = g.sr_p - g.remote / hrs * 100
                    row[f"A_pairs_{v:g}kV"] = round(a.median(), 3); row[f"A_pairs_q25_{v:g}kV"] = round(a.quantile(.25), 3)
                    row[f"A_pairs_q75_{v:g}kV"] = round(a.quantile(.75), 3); row[f"B_pairs_{v:g}kV"] = round(b.median(), 4)
                    row[f"pairs_{v:g}kV"] = len(g)
        res = RESIDUAL_FIXED_GBP_PER_YEAR.get(region)
        for b in (3, 4):
            fx = sites[(sites.band == b) & ~sites.customer].fx_p
            row[f"fixed_median_band{b}_GBP_yr"] = round(fx.median() * 3.65, 0) if len(fx) else np.nan
            row[f"residual_band{b}_GBP_yr"] = res[b - 1] if res else np.nan
            row[f"sole_use_median_band{b}_GBP_yr"] = round(fx.median() * 3.65 - res[b - 1], 0) if (res and len(fx)) else np.nan
        out.append(row)
    df = pd.DataFrame(out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    show = ["region", "listed_network_band34", "A_median_33kV", "A_pairs_33kV", "A_median_132kV", "A_pairs_132kV",
            "B_median_33kV", "B_pairs_33kV", "fixed_median_band4_GBP_yr", "residual_band4_GBP_yr", "sole_use_median_band4_GBP_yr"]
    print(df[[c for c in show if c in df]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCES))
