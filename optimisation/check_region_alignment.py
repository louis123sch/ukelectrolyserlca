"""
Per-region alignment — is every solve input resolved to the right place?
=============================================================================

``audit.py`` asks whether the model's parts agree with each other at one site.
This asks the question a multi-region study cannot answer from one site: when
the coordinate moves, does *everything* move with it, and does everything that
should not move stay put?

Both halves matter, and the second is the one that catches real errors. Grid
carbon intensity and the wind and solar profiles must differ region by region;
the wholesale price, BSUoS and the demand must not, because they are national.
A regional input that silently stays national would understate the spread the
study exists to measure, and a national input that appeared to vary would mean
something was being resolved per site that should not be.

Checks, per region: the grid series really is that region's file; the site
resolves to the region intended; TNUoS locational matches the zone's published
tariff; the TDR band matches the tier and its published charge; a
transmission-connected site pays no DUoS; and the connection ceiling follows
the load.

Run:  python optimisation/check_region_alignment.py
"""
import sys, numpy as np, pandas as pd
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import lca_helpers as H; H.setup_brightway()
from optimisation import dc_inputs as I, network_charges as nc, sites as S
pd.set_option("display.width", 260)

START, END, SIZE, PUE = "2025-06-02", "2025-06-09", 100.0, 1.2
COORDS = {
    1:(57.48,-4.22,"Inverness"), 2:(55.86,-4.25,"Glasgow"), 3:(53.48,-2.24,"Manchester"),
    4:(54.978,-1.617,"Newcastle"), 5:(53.8008,-1.5491,"Leeds"), 6:(53.227,-4.129,"Bangor"),
    7:(51.4816,-3.1791,"Cardiff"), 8:(52.489,-1.898,"Birmingham"),
    9:(52.954,-1.158,"Nottingham"), 10:(52.62,1.29,"Norwich"), 11:(50.72,-3.53,"Exeter"),
    12:(50.91,-1.404,"Southampton"), 13:(51.5074,-0.1278,"London"), 14:(50.82,-0.137,"Brighton"),
}
hh, _ = nc.tnuos_hh_demand(); TARIFF = dict(zip(hh.zone_no, hh.tariff_GBP_per_kW))
tdr, _ = nc.tnuos_tdr(); TDR = dict(zip(tdr.band, tdr.GBP_per_site_year))

rows = []
for r in sorted(COORDS):
    lat, lon, city = COORDS[r]
    s, m = I.build_series(f"{lat},{lon}", START, END, SIZE, pue=PUE)
    c = m["network_charges"]
    bs = nc.bsuos_series(pd.DatetimeIndex(s.index))
    rows.append({
        "r": r, "city": city, "region_name": m["site_name"],
        "lat": m["lat"], "lon": m["lon"],
        "ci_region": m["carbon_api_region"], "zone": m["tnuos_zone"],
        "grid_file": m["grid_file"], "price_file": m["price_file"],
        "band": m["tdr_band"], "trans": m["transmission_connected"],
        "conn_mw": m["connection_limit_mw"],
        "cap_GBP_MW_yr": m["capacity_GBP_per_MW_year"],
        "fixed_GBP_yr": m["fixed_GBP_per_year"],
        "tnuos_loc": c["tnuos_locational_GBP_per_MW_year"],
        "duos_cap": c["duos_capacity_GBP_per_MW_year"],
        "duos_vol": c["duos_mean_GBP_per_MWh"],
        "tdr_yr": c["tnuos_tdr_GBP_per_year"],
        "bsuos": c["bsuos_mean_GBP_per_MWh"],
        "n": s.n, "demand": float(np.unique(s.demand_mw)[0]),
        "ci_mean": float(np.mean(s.grid_gwp_per_mwh)),
        "price_mean": float(np.mean(s.grid_price_per_mwh)),
        "wholesale_mean": float(np.mean(s.grid_price_per_mwh) - bs.mean()),
        "cf_wind": float(np.mean(s.cf_wind)), "cf_solar": float(np.mean(s.cf_solar)),
        "price_hash": hash(np.asarray(s.grid_price_per_mwh).tobytes()),
        "ci_hash": hash(np.asarray(s.grid_gwp_per_mwh).tobytes()),
        "wind_hash": hash(np.asarray(s.cf_wind).tobytes()),
    })
d = pd.DataFrame(rows)
d.to_csv(ROOT / "optimisation_outputs" / "region_alignment.csv", index=False)

fails = []
def chk(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}   {detail}")
    if not ok: fails.append(name)

print("=== per-region resolution ===")
d["grid_r"] = d.grid_file.str.extract(r"_r(\d+)_").astype(int)
print(d[["r","city","ci_region","grid_r","zone","band","trans","conn_mw",
         "n","demand","ci_mean","price_mean","cf_wind","cf_solar"]].round(3).to_string(index=False))

print("\n=== alignment checks ===")
chk("grid file region matches the site's CI region", (d.grid_r == d.ci_region).all(),
    f"mismatches: {d[d.grid_r != d.ci_region].city.tolist() or 'none'}")
chk("every site resolved to its intended region", (d.r == d.ci_region).all())
chk("one price file, national, shared by all", d.price_file.nunique() == 1,
    d.price_file.iloc[0])
chk("wholesale+BSUoS price identical across regions", d.price_hash.nunique() == 1,
    f"{d.price_hash.nunique()} distinct series — all are transmission-connected "
    f"so DUoS is zero and nothing else is regional")
chk("carbon intensity differs by region", d.ci_hash.nunique() == len(d),
    f"{d.ci_hash.nunique()} distinct of {len(d)}")
chk("wind profile differs by coordinate", d.wind_hash.nunique() == len(d),
    f"{d.wind_hash.nunique()} distinct of {len(d)}")
chk("all steps counts equal", d.n.nunique() == 1, f"{d.n.iloc[0]} steps")
chk("all demand equal", d.demand.nunique() == 1, f"{d.demand.iloc[0]:.1f} MW")
chk("BSUoS national (one value)", d.bsuos.round(6).nunique() == 1,
    f"£{d.bsuos.iloc[0]:.2f}/MWh")
d["tnuos_expect"] = d.zone.map(TARIFF) * 1000.0
chk("TNUoS locational matches the zone's published tariff",
    np.allclose(d.tnuos_loc, d.tnuos_expect),
    f"max diff £{np.abs(d.tnuos_loc - d.tnuos_expect).max():.6f}/MW/yr")
chk("capacity charge = TNUoS locational + DUoS capacity",
    np.allclose(d.cap_GBP_MW_yr, d.tnuos_loc + d.duos_cap))
chk("transmission sites pay no DUoS",
    ((~d.trans) | ((d.duos_cap == 0) & (d.duos_vol == 0))).all())
chk("tier and band agree everywhere",
    (d.trans == d.band.str.startswith("T-Demand")).all(),
    f"bands: {sorted(d.band.unique())}")
d["tdr_expect"] = d.band.map(TDR)
chk("TDR charge matches the band's published tariff",
    np.allclose(d.tdr_yr, d.tdr_expect))
chk("connection ceiling = 1.5x the load everywhere",
    np.allclose(d.conn_mw, d.demand * S.CONNECTION_HEADROOM_ASSUMED),
    f"{d.conn_mw.iloc[0]:.1f} MW from {d.demand.iloc[0]:.1f} MW load")
print("\n" + ("ALL ALIGNED" if not fails else f"MISALIGNED: {fails}"))
sys.exit(1 if fails else 0)
