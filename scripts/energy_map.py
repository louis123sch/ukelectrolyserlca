"""The energy-flow map: how power reaches the data centre, component by component.

Read by ``build_lca_map.py`` and drawn as the second tab of the LCA map. Every
rating, voltage and loss is read from the module that sets it, so the diagram
shows what the LP actually does, not a generic data centre. No Brightway: it
reads module constants and the decomposition caches only, so it is rebuilt on
every ``--html-only`` run too.

Scope is energy only — the components electricity or hydrogen passes through,
down to the lowest level that changes the energy (a module, an inverter, a
transformer, a stack). Manufacturing, transport and non-energy kit (fences,
mounting, civils) are the LCA tab's business.

Layout: lanes left to right (one per route in), rows top to bottom (from the
resource down to the data centre). The 20 kV site bus is the LP's single node.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lp_terms import (T_BATT_E, T_BATT_P, T_BOUGHT, T_DC_ENERGY, T_DC_IT, T_ELY_STACK, T_FC_BOP, T_FC_STACK,  # noqa: E402
                      T_TX_BATT, T_TX_FC, T_TX_SOLAR, T_TX_WIND)


def _x_eff(cf):
    import numpy as np
    cf = np.asarray(cf, dtype=float)
    return float((cf * cf).sum() / cf.sum()) if cf.sum() > 0 else None


def energy_section(gap_ids=lambda *k: []):
    import dc_config as cfg
    from optimisation import (battery, conversion_losses as cl, electrolysers as ely,
                              fuel_cell as fc, grid_connection as gc, h2_prices as hp,
                              h2_storage as h2s, profiles, sites)
    from optimiser_lca import bess, gb_grid, grid as G, h2_tank, stepup_transformers as tx, upv
    from optimiser_lca import fuel_cell as fcl

    # ------------------------------------------------------------ the numbers
    rows = {r["technology"]: r for r in ely.decompose_all()}
    pem, ae, soec = rows["PEM operation"], rows["AE operation"], rows["SOEC operation"]
    d_fc = fc.decompose()
    fc_kg_mwh = d_fc["h2_kg_per_MWh"]
    lw, ls, lg = cl.stepup("onshore_wind"), cl.stepup("solar_pv"), cl.grid_intake()
    hv = G.DELIVERY["high"]
    try:                                     # the London 2025 profiles, for loading
        sol, _ = profiles.fetch_solar_cf(51.5074, -0.1278, "2025-01-01", "2025-12-31")
        xs = _x_eff(sol.iloc[:, 0])
        cf_s = float(sol.iloc[:, 0].mean())
    except Exception:                                    # noqa: BLE001
        xs, cf_s = None, None
    try:
        win, _ = profiles.fetch_wind_cf(51.5074, -0.1278, "2025-01-01", "2025-12-29")
        cf_w_gross = float(win.iloc[:, 0].mean())
        xw = _x_eff(win.iloc[:, 0] * profiles.WIND_NET_FACTOR)
    except Exception:                                    # noqa: BLE001
        xw, cf_w_gross = None, None
    load_s = ls["load_loss_per_mw_at_full_loading"] * (xs or 0.5)
    load_w = lw["load_loss_per_mw_at_full_loading"] * (xw or 0.5)
    comp_soec = h2s.compression_kwh_per_kg(ely.DELIVERY_PRESSURE_BAR["SOEC operation"],
                                           h2_tank.DESIGN["pressure_bar"])
    comp_pem = h2s.compression_kwh_per_kg(ely.DELIVERY_PRESSURE_BAR["PEM operation"],
                                          h2_tank.DESIGN["pressure_bar"])
    p2p = 1000.0 / (pem["kwh_per_kg"] + comp_pem) / fc_kg_mwh
    p2p_soec = 1000.0 / (soec["kwh_per_kg"] + comp_soec) / fc_kg_mwh
    eta_b = battery.ROUND_TRIP_EFFICIENCY ** 0.5
    mix = gb_grid.MIX_2025
    imports = gb_grid.IMPORTS_2025
    vessel_kg = h2_tank.capacity_kg(h2_tank.DESIGN)
    pue = float(cfg.DC_REFERENCE_PUE)

    def pc(x, d=1):
        return f"{x * 100:.{d}f} %"

    N, E = [], []

    def n(id_, name, lane, row, kind, *, rating=None, model=None, loss=None, lp=None,
          term=None, source=None, note=None, gaps=(), status="modelled", route=()):
        N.append({"id": id_, "name": name, "lane": lane, "row": row, "kind": kind,
                  "rating": rating, "model": model, "loss": loss, "lp": lp, "term": term,
                  "source": source, "note": note, "gaps": gap_ids(*gaps),
                  "status": status, "routes": list(route)})

    def e(a, b, carrier, label=None, *, status="modelled", loss=None, route=(), note=None):
        E.append({"from": a, "to": b, "carrier": carrier, "label": label, "status": status,
                  "loss": loss, "routes": list(route), "note": note})

    # ================================================================ solar
    R = ("solar",)
    n("sun", "Sunlight on the array", 0, 0, "source", route=R,
      rating=f"shown for the London 2025 reference: CF {pc(cf_s) if cf_s else '—'} at {cfg.PV_TILT_DEG:g}° tilt",
      model="Renewables.ninja hourly PV profile (MERRA-2) at the site's coordinate, south-facing, "
            f"{cfg.PV_TILT_DEG:g}° fixed tilt. The LP sees it as cf_solar[t] × cap_solar.",
      source="profiles.fetch_solar_cf; dc_config.PV_TILT_DEG", gaps=("dispatch profile",))
    n("pv_modules", "PV modules — mono-Si PERC", 0, 1, "component", route=R,
      rating=f"{upv.UPV_PV_MODULE_W:g} Wp per module, {pc(upv.UPV_PV_MODULE_EFF)} efficient",
      model="cap_solar is the array's DC rating in MWp. Output in each hour is cf_solar × cap_solar, "
            "already net of the system losses below.",
      lp="cap_solar (MWp DC)", term="Solar PV (utility, fixed tilt 20°)",
      source=upv.UPV_PV_SOURCE, gaps=("solar",))
    n("pv_dc", "DC strings, combiner boxes, DC cabling", 0, 2, "component", route=R,
      rating="the array's electrical balance of system (Smith Table A12)",
      model="Not a variable. Its losses are inside Renewables.ninja's flat system loss.",
      loss=f"inside the {pc(cfg.PV_SYSTEM_LOSS, 0)} system loss", status="inside",
      source="Smith et al. 2024 Table A12; dc_config.PV_SYSTEM_LOSS (ASSUMED)")
    n("pv_inverter", "Inverter, DC → 0.4 kV AC (central, 2.7 MVA)", 0, 3, "component", route=R,
      rating=f"{upv.UPV_PV_INVERTER_MVA:g} MVA each, DC/AC ratio {upv.UPV_PV_ILR:g} "
             f"(one per {upv.UPV_PV_INVERTER_MVA * upv.UPV_PV_ILR:.1f} MWp)",
      model=f"Sized with the array, not separately. Renewables.ninja applies one flat "
            f"{pc(cfg.PV_SYSTEM_LOSS, 0)} system loss (ASSUMED) for the inverter, wiring and soiling; "
            "clipping at the DC/AC ratio is not modelled on its own.",
      loss=f"inside the {pc(cfg.PV_SYSTEM_LOSS, 0)} system loss", status="inside",
      source="Smith et al. 2024 Table A10 (2,700 kVA central inverter)")
    n("pv_tx", "Step-up transformer, 0.4 → 20 kV, at the inverter station", 0, 4, "component", route=R,
      rating=f"{tx.UPV_TX_UNIT_MVA:g} MVA oil-immersed, "
             f"{tx.UPV_TX_UNITS_PER_PLANT} per {tx.UPV_TX_REFERENCE_MWP:g} MWp",
      model="Losses applied in the LP: availability × (1 − load loss), plus no-load drawn at the bus.",
      loss=f"no-load {pc(ls['noload_mw_per_mw'], 3)} of capacity, always; load "
           f"{pc(ls['load_loss_per_mw_at_full_loading'], 2)} at full loading ≈ {pc(load_s, 2)} of output",
      term=T_TX_SOLAR, source=f"{tx.UPV_TX_SOURCE}; {cl.SOURCE}",
      gaps=("transformer",))

    # ================================================================ wind
    R = ("wind",)
    n("wind", "Wind at hub height", 1, 0, "source", route=R,
      rating=f"shown for the London 2025 reference: gross CF {pc(cf_w_gross) if cf_w_gross else '—'} (one V90, 80 m)",
      model="Renewables.ninja hourly profile for one Vestas V90 2 MW at 80 m; the LP takes it "
            f"× {profiles.WIND_NET_FACTOR:.3f} to make it a farm's net output.",
      source="profiles.fetch_wind_cf; Staffell & Pfenninger 2016", gaps=("wind life extension",))
    n("rotor", "Rotor, blades, gearbox, generator", 1, 1, "component", route=R,
      rating=f"generates at {tx.TX_TURBINE_TERMINAL_V:g} V",
      model="cap_wind in MW. Three turbines stand behind it: a V90 2 MW in dispatch, ecoinvent's "
            "2 MW turbine in carbon, DESNZ's 4.3–6.8 MW machines in cost.",
      loss=f"availability {profiles.WIND_NET_COMPONENTS['availability']}, performance "
           f"{profiles.WIND_NET_COMPONENTS['performance']}",
      lp="cap_wind (MW)", term="Onshore wind", source="Arup 2024 §5.8.2; renewables.py",
      gaps=("wind",))
    n("wake", "Array: wake and turbine electrical losses", 1, 2, "component", route=R,
      rating="the farm, not one turbine",
      model="Not a component in the LP; the losses are in the net factor on the profile.",
      loss=f"wake {profiles.WIND_NET_COMPONENTS['wake']}, electrical "
           f"{profiles.WIND_NET_COMPONENTS['electrical']} → net factor {profiles.WIND_NET_FACTOR:.3f}",
      status="inside", source="Arup 2024 §5.8.4 (wake 9 %); Vestas LCAs §3.4.2 (electrical 2.5 %)")
    n("turbine_tx", "Step-up transformer, 0.69 → 20 kV, one per turbine", 1, 3, "component", route=R,
      rating=f"{tx.TX_LENG_UNIT_MVA:g} MVA box transformer, one per turbine "
             f"({lw['MVA_per_MW']:.1f} MVA per MW)",
      model="Losses applied in the LP: availability × (1 − load loss), plus no-load at the bus. "
            "The site collects at 20 kV (ASSUMED, inside the 1–24 kV band the data centre draws "
            "at), so this is a 0.69/20 kV unit. Its carbon is Leng's S11-2200/35, wound for 35 kV, "
            "used as the proxy: heavier per MVA, so it errs high. No further 35 → 20 kV step exists "
            "in the chain.",
      loss=f"no-load {pc(lw['noload_mw_per_mw'], 3)} of capacity; load "
           f"{pc(lw['load_loss_per_mw_at_full_loading'], 2)} at full loading ≈ {pc(load_w, 2)} of output",
      term=T_TX_WIND, source=f"Leng et al. 2026 Table S1 (S11-2200/35); {cl.SOURCE}",
      gaps=("wind transformer", "transformer"))
    n("collect", "Array collection cables, 20 kV", 1, 4, "component", route=R, status="inside",
      rating=f"underground MV cables, turbine to site bus, at {tx.TX_SITE_COLLECTION_KV:g} kV (ASSUMED)",
      model="Losses: inside the net factor's electrical term (0.98). Vestas's LCAs put electrical "
            "losses at 2.5 % to the connection point, cables and transformers together; the step-up's "
            "share is charged separately above, leaving 2 % for the cables. Carbon: inside ecoinvent's "
            "'wind turbine network connection, 2MW' dataset, a capital good in the wind coefficient.",
      loss=f"inside net factor {profiles.WIND_NET_FACTOR:.3f} (electrical {profiles.WIND_NET_COMPONENTS['electrical']})",
      source="Vestas V136/V150/V162 LCAs §3.4.2; ecoinvent 3.9.1 wind turbine network connection",
      gaps=("wind transformer",))

    # ================================================================ grid
    R = ("grid",)
    mix_txt = ", ".join(f"{k.lower()} {v:.0%}" for k, v in sorted(mix.items(), key=lambda kv: -kv[1]) if v > 0.005)
    imp_txt = ", ".join(f"{k} {v:.1%}" for k, v in sorted(imports.items(), key=lambda kv: -kv[1]) if v > 0.0005)
    n("gb_gen", "GB generators and interconnectors", 2, 0, "source", route=R,
      rating=f"GB-wide 2025 mix: {mix_txt}; imports {sum(imports.values()):.1%} ({imp_txt})",
      model="Shown GB-wide; the LP uses the site's own region (London, region 13) half-hour by "
            "half-hour from the Carbon Intensity API, which sets ci[t]. The LP chooses imp[t] each "
            "half-hour up to cap_grid.",
      term="Grid imports (half-hourly, regional)", source="NESO Carbon Intensity API; Elexon FUELHH",
      gaps=("grid", "import"))
    n("tx_net", "Transmission network, 400 / 275 / 132 kV", 2, 1, "component", route=R,
      rating="national grid plus HVDC links",
      model="A gross-up on every imported kWh's carbon, and its losses: the kWh generated per kWh "
            "delivered at high voltage.",
      loss=f"×{hv['gross_up']:.4f} generated per kWh delivered ({pc(hv['gross_up'] - 1, 2)} losses); "
           f"network carbon {hv['network_gco2e_per_kwh']:.2f} g/kWh",
      source="optimiser_lca.grid.DELIVERY, from ecoinvent's GB voltage chain")
    n("line", "Connection line", 2, 2, "component", route=R, status="not",
      rating=f"{gc.LINE_KM:g} km (ASSUMED, site-specific)",
      model="Reported but not charged per MW; its losses are not applied.",
      source="grid_connection.LINE_KM", gaps=("transmission connection",))
    n("meter", "Connection point and import meter", 2, 3, "component", route=R,
      rating=f"cap_grid ≤ load × {sites.CONNECTION_HEADROOM_ASSUMED:.3g} (connection ceiling: 1 / the FES 70 % data-centre load factor); "
             "a connection above 100 MW counts as transmission-connected (ASSUMED)",
      model="imp[t] ≤ cap_grid. Imports are priced and scored here, on the grid side of the "
            "intake. Export is switched off (refused until modelled).",
      lp="cap_grid (MW), imp[t]", term="Grid connection (intake transformers, N-1)",
      gaps=("grid connection capacity", "transmission-vs-distribution", "tdr band"))
    n("intake", "Grid intake transformers, 110/132 → 20 kV", 2, 4, "component", route=R,
      rating=f"{gc.TRANSFORMER_REDUNDANCY / gc.POWER_FACTOR:g} MVA per MW of connection (N-1, "
             f"power factor {gc.POWER_FACTOR:g}), charged per MVA on Leng's {tx.TX_LENG_MAIN_MVA:g} MVA unit",
      model="Losses applied in the LP: delivered = (1 − load loss) × imp, no-load drawn at the bus.",
      loss=f"no-load {pc(lg['noload_mw_per_mw'], 3)} of the connection; load {pc(lg['load_loss_fraction'], 3)} "
           f"of imports (k_PEI {cl.LARGE_TX_K_PEI}, loading {cl.GRID_INTAKE_X_EFF} ASSUMED)",
      term="Grid connection (intake transformers, N-1)",
      source=f"Leng et al. 2026 XZ11-100000/110; {cl.SOURCE}", gaps=("grid-intake",))

    # ================================================================ battery
    R = ("battery",)
    n("bess_cooling", "Liquid cooling, HVAC, BMS", 3, 1, "component", route=R, status="inside",
      rating="auxiliary load of the container",
      model="Its electricity is a standing loss on the stored energy: 0 by default, swept 0–0.5 %/day.",
      loss=f"standing loss {battery.STANDING_LOSS_PER_HOUR:g} /h (ASSUMED)",
      source="Jasper et al. 2026 container; battery.STANDING_LOSS_PER_HOUR", gaps=("standing loss",))
    n("bess_dc", "LFP DC block — cells, modules, racks", 3, 2, "storage", route=R,
      rating=f"{bess.CSS_KWH:,.0f} kWh per container = {bess.CSS_RACKS} racks × "
             f"{bess.CSS_MODULES_PER_RACK} modules × {bess.CSS_MODULE_KWH:g} kWh; {bess.CELL_WH:g} Wh cells",
      model=f"cap_batt_e is usable energy ({pc(battery.USABLE_FRACTION, 0)} of nameplate). "
            "soc[t] ≤ cap_batt_e, cyclic over the window.",
      loss=f"usable {pc(battery.USABLE_FRACTION, 0)} of nameplate",
      lp="cap_batt_e (MWh), soc[t]", term=T_BATT_E,
      source="Jasper et al. 2026; Voß et al. 2025 cell", gaps=("battery",))
    n("pcs", "Power conversion system, AC ↔ DC", 3, 3, "component", route=R,
      rating=f"{battery.PCS_RATED_KW:g} kW inverters (ecoinvent dataset)",
      model="cap_batt_p in MW bounds charge and discharge. Round-trip efficiency is split evenly: "
            f"√{battery.ROUND_TRIP_EFFICIENCY} = {eta_b:.3f} each way.",
      loss=f"round trip {pc(battery.ROUND_TRIP_EFFICIENCY, 0)} (Modo)", lp="cap_batt_p (MW), ch[t], dis[t]",
      term=T_BATT_P, source="Modo Energy; battery.PCS_ACTIVITY", gaps=("battery",))
    lb = cl.container_stepup("battery")
    n("bess_tx", "Step-up transformer, 0.4 → 20 kV, one per container", 3, 4, "component", route=R,
      rating=f"{cl.BATTERY_UNIT_KVA / 1000:g} MVA per {bess.CSS_KW / 1000:g} MW container (Jasper 2026)",
      model="Losses applied in the LP: discharge arrives at the bus net of the load loss, charge is drawn "
            "grossed up by it, and no-load is drawn on cap_batt_p every hour.",
      loss=f"no-load {pc(lb['noload_mw_per_mw'], 3)} of PCS rating; load {pc(lb['load_loss_fraction'], 2)} "
           f"of throughput at x_eff {lb['x_eff']:g} (ASSUMED)",
      lp="cap_batt_p (MW)", term=T_TX_BATT,
      source="Jasper et al. 2026 (mass) on IEA PVPS T12-33:2026 (composition); Reg. 548/2014 Tier 2 (losses)")

    # ================================================================ hydrogen made on site
    R = ("hydrogen",)
    n("ely_psu", "Electrolyser power supply: transformer and rectifier", 5, 4, "component", route=R,
      status="inside", rating="AC → DC for the stack",
      model="Taken as inside the inventory's kWh per kg (54 for PEM), i.e. that figure is read as a "
            "system-level consumption with the rectifier included. Not verified against Gerloff's "
            "own definition; if their 54 kWh/kg is stack-only, the system draw is ~2–4 % higher.",
      source="Gerloff 2021 SI Table 6; electrolysers.decompose_all")
    n("ely", "Electrolyser stack — PEM (AE, SOEC selectable)", 5, 3, "component", route=R,
      rating=f"PEM {pem['kwh_per_kg']:g} kWh/kg at {ely.DELIVERY_PRESSURE_BAR['PEM operation']:g} bar · "
             f"AE {ae['kwh_per_kg']:g} · SOEC {soec['kwh_per_kg']:g} kWh/kg + 5.24 kWh/kg heat",
      model="p_ely[t] ≤ cap_ely. Hydrogen made = p_ely ÷ (kWh/kg + compression). Can run at any "
            "part load (no unit commitment).",
      loss=f"{1000 / pem['kwh_per_kg']:.2f} kg H₂ per MWh (PEM) = {pc(33.33 / pem['kwh_per_kg'], 0)} LHV",
      lp="cap_ely (MW), p_ely[t]; ely_stack_units = max(calendar, running hours / 50,000)", term=T_ELY_STACK,
      source="Gerloff 2021; electrolysers.DELIVERY_PRESSURE_BAR",
      gaps=("electrolyser", "alkaline", "soec"))
    n("gas", "Natural gas supply", 4, 0, "source", route=("hydrogen",), status="option",
      rating="GB gas network, high pressure (SOEC only)",
      model="Fuel for the SOEC's boiler. Bought fuel: its carbon is in the electrolyser's "
            "consumables term; it does not pass through the site bus.",
      source="Mehmeti et al. 2018; ecoinvent heat production, natural gas, at boiler", gaps=("consumables",))
    n("soec_heat", "SOEC external heat: gas boiler", 4, 3, "component", route=("hydrogen",),
      status="option", rating="5.24 kWh heat per kg H₂ (SOEC only)",
      model="Gas boiler by default (bought fuel, carbon only). The electric-boiler scenario takes "
            "5.29 kWh/kg from the site bus instead.",
      source="Mehmeti et al. 2018; electrolysers.SOEC_HEAT_SOURCES", gaps=("consumables",))
    n("compress", "Compression to tank pressure", 5, 1.0, "component", route=R,
      rating=f"PEM {ely.DELIVERY_PRESSURE_BAR['PEM operation']:g} → {h2_tank.DESIGN['pressure_bar']:g} bar: "
             f"{comp_pem:.2f} kWh/kg · SOEC 1 → {h2_tank.DESIGN['pressure_bar']:g} bar: {comp_soec:.2f} kWh/kg",
      model="Its electricity is added to the electrolyser's kWh per kg, drawn from the bus.",
      source="h2_storage.compression_kwh_per_kg", gaps=("alkaline delivery pressure",))
    n("tank", "Hydrogen tank — steel vessel", 5.5, 0, "storage", route=("hydrogen", "bought"),
      rating=f"{h2_tank.DESIGN['pressure_bar']:g} bar, {vessel_kg:.0f} kg H₂ per "
             f"{h2_tank.DESIGN['volume_m3']:g} m³ vessel",
      model="tank[t] ≤ cap_tank (kg), cyclic. Fed by the electrolyser and by bought hydrogen; "
            "drained by the fuel cell. Drains to zero (no heel).",
      loss=f"leakage {h2s.LEAKAGE_FRAC_PER_HOUR:g} /h by default (swept); leaked H₂ is charged at GWP 11.6",
      lp="cap_tank (kg), tank[t]", term=f"Hydrogen tank ({h2_tank.TANK_DESIGN})",
      source=h2_tank.DESIGN["note"], gaps=("tank", "leakage"))

    # ================================================================ hydrogen used
    n("fc_stack", "Fuel cell stack — PEM", 6, 1.0, "component", route=R + ("bought",),
      rating=f"{fc_kg_mwh:.1f} kg H₂ per MWh AC = {pc(fcl.FC_ETA_NET_MEAN, 1)} net (LHV), lifetime mean",
      model="p_fc[t] ≤ cap_fc; hydrogen burned = 63.2 kg × MWh. Stacks are replaced on max(calendar "
            f"{d_fc['stack_calendar_lifetime_years']:g} y, {d_fc['stack_lifetime_hours']:,.0f} h).",
      loss=f"BOL {pc(fcl.FC_ETA_NET_BOL, 0)} × degradation {fcl.FC_DEGRADATION_DERATE}",
      lp="cap_fc (MW), p_fc[t]", term=T_FC_STACK,
      source="fuel_cell.FC_ETA_NET_BOL, FC_DEGRADATION_DERATE", gaps=("fuel cell",))
    n("fc_bop", "Fuel cell balance of plant: air blower, humidifier, coolant pumps", 6, 2, "component",
      route=R + ("bought",), status="inside", rating="parasitic loads",
      model="Inside the net efficiency (the 47.5 % is net AC, after these loads).",
      source="Usai et al. 2021 process loops", gaps=("fuel cell bop",))
    n("fc_inv", "Fuel cell inverter, DC → AC", 6, 3, "component", route=R + ("bought",),
      rating=f"{fcl.FC_INVERTER_KW:g} kW units (ecoinvent dataset), in a container per "
             f"{fcl.FC_KW_PER_CONTAINER:,.0f} kW",
      model="Inside the net efficiency and the BoP carbon; not a separate variable.",
      status="inside", term=T_FC_BOP)
    lfc = cl.container_stepup("fuel_cell")
    n("fc_tx", "Step-up transformer, 0.4 → 20 kV, one per container", 6, 4, "component", route=R + ("bought",),
      rating=f"{cl.FC_UNIT_KVA / 1000:g} MVA per {fcl.FC_KW_PER_CONTAINER / 1000:g} MW container",
      model="Losses applied in the LP: p_fc arrives at the bus net of the load loss; no-load is drawn on "
            "cap_fc every hour because the unit is kept energised on standby (decision, 15 Oct).",
      loss=f"no-load {pc(lfc['noload_mw_per_mw'], 3)} of cap_fc, always; load {pc(lfc['load_loss_fraction'], 2)} "
           f"of output at x_eff {lfc['x_eff']:g} (ASSUMED)",
      lp="cap_fc (MW)", term=T_TX_FC,
      source="Jasper et al. 2026 (mass) on IEA PVPS T12-33:2026 (composition); Reg. 548/2014 Tier 2 (losses)")

    # ================================================================ bought hydrogen
    R = ("bought",)
    n("h2_seller", "Off-site hydrogen producer", 7, 0, "source", route=R,
      rating="grey SMR · blue SMR + CCS · turquoise pyrolysis · green PEM (one or two colours)",
      model="h2_buy[t] in kg, unbounded (no delivery limit), priced and scored per kg at the gate.",
      lp="h2_buy[t], h2_buy_2[t]", term=T_BOUGHT,
      source="Hermesmann & Müller 2022 (fossil, 30 bar at the plant), Gerloff 2021 (green); h2_prices.py", gaps=("bought", "green h"))
    n("trailer_comp", "Compression onto a tube trailer", 7, 1, "component", route=R,
      rating=f"to {hp.BOUGHT_H2_TRAILER_PRESSURE_BAR:g} bar: {hp.bought_h2_compression_kwh_per_kg('grey'):.2f} "
             f"kWh/kg (fossil), {hp.bought_h2_compression_kwh_per_kg('green'):.2f} (green)",
      model="Charged in both objectives at the seller's electricity; not drawn from the site bus.",
      source="h2_prices.bought_h2_compression_*", gaps=("outlet pressure", "loading compressor"))
    n("haulage", "Road haulage to site", 7, 2, "component", route=R, status="not",
      rating="distance unknown (seller location)",
      model="Not modelled: no fuel, no losses. Arriving hydrogen enters the tank at coefficient 1.",
      gaps=("haulage",))

    # ================================================================ bus and data centre
    ALL = ("solar", "wind", "grid", "battery", "hydrogen", "bought")
    n("bus", f"{tx.TX_SITE_COLLECTION_KV:g} kV site bus — the LP's single node", 3.5, 5, "bus", route=ALL,
      rating="every source in, every load out, each half-hour",
      model="Σ supply − charging − electrolysis − no-load losses = demand, each half-hour. A copper "
            "plate: no internal network, no cable lengths. Curtailment happens here (supply below "
            "availability).",
      lp="balance[t]", source="dc_model.build_model, constraint (1)")
    n("dc_dist", "Data-centre MV/LV distribution, switchgear, UPS", 3.5, 6, "component", route=ALL,
      status="inside", rating="inside the facility",
      model="Not modelled separately (closed as negligible 4 Sep). The facility's own losses are in "
            "its PUE; the UPS battery is in Zhang's facility inventory.",
      term=T_DC_IT, gaps=("balance of plant",))
    n("it", "IT load — servers, storage, network", 3, 7, "load", route=ALL,
      rating="100 MW IT (reference run), flat",
      model="demand[t] = IT × PUE, flat at 100 % all year.",
      term=T_DC_IT, source="Zhang et al. 2025; ASSUMPTIONS.md §1")
    n("cooling", "Cooling and auxiliaries", 4, 7, "load", route=ALL,
      rating=f"(PUE − 1) × IT = {(pue - 1) * 100:g} MW at PUE {pue:g}",
      model=f"The PUE share of demand. Default PUE {pue:g} (Zhang's own); the page lets the user choose.",
      term=T_DC_ENERGY, source="dc_config.DC_REFERENCE_PUE")
    n("genset", "Standby diesel genset", 5.5, 6, "component", route=(), status="not",
      rating="backup only",
      model="Excluded from the LP (backup is a decision variable); scored and reported in the facility.",
      source="baseline_grid.DC_DRIVERS (backup)")
    n("unserved", "Unserved load", 6, 7, "load", route=(), status="option",
      rating="0 by default (hard reliability constraint)",
      model="unserved[t] ≤ allowance; penalised at VoLL in both objectives (£100,000/MWh; "
            "1,266 t CO₂e/MWh). Not an energy source.",
      term="Unserved load (penalty, not an emission)")

    # ================================================================ edges
    e("sun", "pv_modules", "sun", "irradiance", route=("solar",))
    e("pv_modules", "pv_dc", "dc", "DC, string voltage", route=("solar",))
    e("pv_dc", "pv_inverter", "dc", "DC", route=("solar",), loss=f"system loss {pc(cfg.PV_SYSTEM_LOSS, 0)} (with inverter)")
    e("pv_inverter", "pv_tx", "lv", "0.4 kV AC", route=("solar",))
    e("pv_tx", "bus", "mv", "20 kV AC", route=("solar",), loss=f"≈{pc(load_s + ls['noload_mw_per_mw'] / (cf_s or 0.14), 2)} of output")

    e("wind", "rotor", "wind", "wind", route=("wind",))
    e("rotor", "wake", "lv", "690 V AC", route=("wind",))
    e("wake", "turbine_tx", "lv", "690 V AC", route=("wind",), loss=f"net factor {profiles.WIND_NET_FACTOR:.3f}")
    e("turbine_tx", "collect", "mv", "20 kV AC", route=("wind",))
    e("collect", "bus", "mv", "20 kV AC", route=("wind",), status="inside", loss="cable losses inside the net factor")

    e("gb_gen", "tx_net", "hv", "generation", route=("grid",))
    e("tx_net", "line", "hv", "132 kV class AC", route=("grid",), loss=f"{pc(hv['gross_up'] - 1, 2)} delivery losses")
    e("line", "meter", "hv", "132 kV class AC", route=("grid",), status="not")
    e("meter", "intake", "hv", "imp[t]", route=("grid",))
    e("intake", "bus", "mv", "20 kV AC", route=("grid",), loss=f"{pc(lg['load_loss_fraction'], 3)} + no-load")
    e("intake", "meter", "hv", "export — disabled", route=(), status="off")

    e("bus", "bess_tx", "mv", "charge ch[t]", route=("battery",))
    e("bess_tx", "pcs", "lv", "LV AC", route=("battery",), loss=f"×{1 - lb['load_loss_fraction']:.4f}")
    e("pcs", "bess_dc", "dc", "DC", route=("battery",), loss=f"×{eta_b:.3f}")
    e("bess_dc", "pcs", "dc", "DC", route=("battery",), loss=f"×{eta_b:.3f}")
    e("pcs", "bess_tx", "lv", "LV AC", route=("battery",))
    e("bess_tx", "bus", "mv", "discharge dis[t]", route=("battery",), loss=f"×{1 - lb['load_loss_fraction']:.4f}")
    e("bess_cooling", "bess_dc", "lv", "auxiliary power", route=("battery",), status="inside")

    e("bus", "ely_psu", "mv", "p_ely[t]", route=("hydrogen",))
    e("ely_psu", "ely", "dc", "DC", route=("hydrogen",))
    e("gas", "soec_heat", "gas", "natural gas", route=("hydrogen",), status="option")
    e("soec_heat", "ely", "gas", "heat, SOEC only", route=("hydrogen",), status="option")
    e("bus", "soec_heat", "mv", "electric-boiler option", route=(), status="option")
    e("ely", "compress", "h2", f"H₂ at {ely.DELIVERY_PRESSURE_BAR['PEM operation']:g} bar", route=("hydrogen",))
    e("compress", "tank", "h2", f"H₂ at {h2_tank.DESIGN['pressure_bar']:g} bar", route=("hydrogen",))
    e("tank", "fc_stack", "h2", "h2_fc[t]", route=("hydrogen", "bought"))
    e("fc_stack", "fc_bop", "dc", "DC", route=("hydrogen", "bought"))
    e("fc_bop", "fc_inv", "dc", "DC, net of parasitics", route=("hydrogen", "bought"))
    e("fc_inv", "fc_tx", "lv", "LV AC", route=("hydrogen", "bought"))
    e("fc_tx", "bus", "mv", "p_fc[t]", route=("hydrogen", "bought"), loss=f"×{1 - lfc['load_loss_fraction']:.4f}")

    e("h2_seller", "trailer_comp", "h2", "H₂ at 20–30 bar", route=("bought",))
    e("trailer_comp", "haulage", "h2", "H₂ at 200 bar", route=("bought",))
    e("haulage", "tank", "h2", "h2_buy[t]", route=("bought",), status="not")

    e("bus", "dc_dist", "mv", "demand[t]", route=ALL)
    e("dc_dist", "it", "lv", "LV AC", route=ALL, status="inside")
    e("dc_dist", "cooling", "lv", "LV AC", route=ALL, status="inside")
    e("genset", "dc_dist", "lv", "backup only", route=(), status="off")
    e("unserved", "dc_dist", "lv", "shortfall", route=(), status="option")

    routes = {
        "solar": {"label": "Solar", "chain": f"1 kWh DC at the modules → {1 - cfg.PV_SYSTEM_LOSS:.2f} after system "
                  f"losses → about {(1 - cfg.PV_SYSTEM_LOSS) * (1 - load_s):.3f} at the bus, less no-load"},
        "wind": {"label": "Wind", "chain": f"1 kWh at one turbine's terminals → {profiles.WIND_NET_FACTOR:.3f} "
                 f"net of the farm → about {profiles.WIND_NET_FACTOR * (1 - load_w):.3f} at the bus, less no-load"},
        "grid": {"label": "GB grid", "chain": f"{hv['gross_up']:.4f} kWh generated per kWh at the meter → "
                 f"{1 - lg['load_loss_fraction']:.4f} through the intake, less no-load"},
        "battery": {"label": "Battery", "chain": f"1 kWh charged → {battery.ROUND_TRIP_EFFICIENCY:.2f} discharged "
                    f"({eta_b:.3f} each way); usable {battery.USABLE_FRACTION:.0%} of nameplate"},
        "hydrogen": {"label": "Hydrogen, made on site", "chain": f"1 MWh into a PEM electrolyser → "
                     f"{1000 / pem['kwh_per_kg']:.1f} kg H₂ → {p2p:.3f} MWh back from the fuel cell "
                     f"({p2p:.1%} round trip; SOEC {p2p_soec:.1%} plus heat)"},
        "bought": {"label": "Hydrogen, bought", "chain": f"1 kg delivered → {1000 / fc_kg_mwh:.1f} kWh at the bus "
                   f"(fuel cell {fcl.FC_ETA_NET_MEAN:.1%} net)"},
    }
    lanes = ["Solar", "Wind", "GB grid", "Battery", "Gas (SOEC heat)", "H₂ made on site", "H₂ used", "H₂ bought"]
    rows_ = ["Resource", "", "", "", "Into the site", "Site bus", "Facility", "Data centre"]
    return {"nodes": N, "edges": E, "routes": routes, "lanes": lanes, "rows": rows_}


if __name__ == "__main__":
    import json
    out = energy_section()
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}, indent=1, default=str)[:2000])
