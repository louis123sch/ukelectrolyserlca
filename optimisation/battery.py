"""
Lithium-ion battery storage — cost and embodied carbon.
=============================================================================

Costs come from **Modo Energy**, which is the source NESO itself uses: the FES
2025 Economics Methodology report states its Li-ion CAPEX is "a combination of
Modo survey data with CAPEX data from the National Renewable Energy
Laboratory". Modo's model assumptions are published openly at
docs.modoenergy.com, already in **real 2025 GBP** — the same basis as every
other cost in this study, so no deflation or FX is needed.

Embodied carbon comes from ecoinvent 3.9.1. Cost and carbon are deliberately
kept on the same two-part structure — a **power** term (£/kW, kg CO2e/kW) and
an **energy** term (£/kWh, kg CO2e/kWh) — so the optimiser can size power and
duration independently instead of being locked to a 4-hour product.

Sources
-------
cost, technical   Modo Energy, "BESS Cost and Technical Assumptions",
                  docs.modoenergy.com/pages/jan-2026/uk-europe/model-assumptions/
                  (July 2026). ~£400/kW for a 1-hour system today falling to
                  ~£200/kW by 2040; each additional hour of duration adds
                  £100/kW in 2025. 15-year asset life, ~67 % capacity
                  remaining after 10,000 cycles (~12-15 years), 1-2 cycles per
                  day, WACC 5.0 % real. Real 2025 GBP.

cost spread       Modo Energy BESS CapEx Survey 2024 (30 market participants,
                  2.8 GW at 1.9 h average): average £580k/MW, two-hour median
                  £650k/MW, 68 % of projects between £400k/MW and £700k/MW.

round-trip eff.   88 %, Modo's standard assumption. Not stated on the model
                  assumptions page itself, so it is the least firmly sourced
                  number here.

embodied carbon   ecoinvent 3.9.1 apos, IPCC 2021 GWP100.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run:  python optimisation/battery.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "optimisation_outputs"

CASES = ("low", "central", "high")

# =============================================================================
# Cost — Modo Energy, real 2025 GBP
# =============================================================================
# Modo quote a 1-hour system at ~400 GBP/kW and each further hour at
# +100 GBP/kW. A 1-hour system is 1 kWh per kW, so that decomposes cleanly:
#   energy component = 100 GBP/kWh   (the marginal hour)
#   power component  = 400 - 100 = 300 GBP/kW
# Everything duration-dependent then falls out of those two numbers.
MODO_1H_GBP_PER_KW = 400.0
MODO_MARGINAL_HOUR_GBP_PER_KW = 100.0

CAPEX_ENERGY_CENTRAL = MODO_MARGINAL_HOUR_GBP_PER_KW              # GBP/kWh
CAPEX_POWER_CENTRAL = MODO_1H_GBP_PER_KW - CAPEX_ENERGY_CENTRAL   # GBP/kW

# Modo's 2024 survey spans 400-700 k/MW (68 %) around a 580 k/MW average at
# 1.9 h. Those bounds are 0.69x and 1.21x the average, applied here to both
# cost components. Note the survey average (580) sits ~18 % ABOVE what the
# forward-looking model assumption gives at the same duration (300 + 1.9x100 =
# 490 k/MW) - Modo's assumption is the more optimistic of their own two
# numbers. The high case is what covers that gap; see cost_table().
SURVEY_LOW_MULTIPLIER = 400.0 / 580.0
SURVEY_HIGH_MULTIPLIER = 700.0 / 580.0

# Fixed OPEX is the one battery input with no published source. Modo do not
# publish it, and FES routes battery OPEX to BEIS's 2022 Long Duration
# Electricity Storage report rather than to Modo. 2 % of CAPEX per year is a
# common convention and is used here as an explicit proxy - replace it once a
# sourced figure is available.
FIXED_OPEX_PCT_CAPEX = {"low": 0.015, "central": 0.020, "high": 0.030}
OPEX_IS_PROXY = True

WACC_REAL = 0.050            # Modo: 5.0 % real (~7.1 % nominal)
ASSET_LIFE_YEARS = 15        # Modo: BESS asset lifetime

# =============================================================================
# Technical — Modo
# =============================================================================
WARRANTED_CYCLES = 10_000          # to the repowering threshold
CAPACITY_AT_END_OF_LIFE = 0.67     # ~67 % remaining after those cycles
ROUND_TRIP_EFFICIENCY = 0.88       # Modo standard; least firmly sourced here
CYCLES_PER_DAY = (1.0, 2.0)        # configurable, warranty-aligned

# =============================================================================
# Embodied carbon — ecoinvent 3.9.1 apos, IPCC 2021 GWP100
# =============================================================================
# ecoinvent's LFP dataset documents a 203 kg pack holding 23.5 kWh gross, and
# its own price comment independently cites 0.115 kWh/kg. The cell figure
# (0.159 kWh/kg x 0.727 kg cell per kg pack = 0.1156) agrees to 0.2 %.
PACK_KWH_PER_KG = 23.5 / 203.0
BATTERY_ACTIVITY = ("market for battery, Li-ion, LFP, rechargeable, prismatic", "GLO")
PCS_ACTIVITY = ("market for inverter, 500kW", "GLO")
PCS_RATED_KW = 500.0

# Scored once and pinned here so this module runs without Brightway;
# check_against_ecoinvent() re-scores them and fails if they have moved.
PACK_KGCO2E_PER_KG = 11.368
PCS_KGCO2E_PER_UNIT = 15_930.86

# ecoinvent 3.9.1 has no stationary BESS enclosure - no container, racking,
# HVAC or fire suppression. Those are real mass that the EV-pack dataset does
# not carry. Set to 0.0 to report packs + PCS only, which is what the numbers
# below do; anything non-zero is an uplift you are choosing, not a dataset.
CONTAINER_UPLIFT_FRACTION = 0.0

# ecoinvent's LFP pack is an electric-vehicle traction pack (Dai et al. /
# GREET), not a grid battery. Reusing it for stationary storage is standard
# practice in the literature but it is an approximation in both directions:
# stationary cells are cheaper and less mass-optimised, while a real BESS
# carries enclosure mass this dataset omits.
LCA_CAVEAT = ("ecoinvent LFP pack is an EV traction pack (Dai et al./GREET), "
              "reused for stationary storage; no container/HVAC/racking")


def capital_recovery_factor(rate, lifetime_years):
    rate, lifetime_years = float(rate), float(lifetime_years)
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    if rate == 0:
        return 1.0 / lifetime_years
    return rate * (1.0 + rate) ** lifetime_years / ((1.0 + rate) ** lifetime_years - 1.0)


def cost_components():
    """Power (GBP/kW) and energy (GBP/kWh) capex, by case."""
    mult = {"low": SURVEY_LOW_MULTIPLIER, "central": 1.0, "high": SURVEY_HIGH_MULTIPLIER}
    return {c: {"power_GBP_per_kW": CAPEX_POWER_CENTRAL * mult[c],
                "energy_GBP_per_kWh": CAPEX_ENERGY_CENTRAL * mult[c]}
            for c in CASES}


def system_capex_gbp_per_kw(duration_h, case="central"):
    """Total capex of a system of a given duration, GBP per kW of power."""
    c = cost_components()[case]
    return c["power_GBP_per_kW"] + c["energy_GBP_per_kWh"] * float(duration_h)


def lifetime_throughput_mwh_per_mwh():
    """MWh discharged over life, per MWh of installed capacity.

    Capacity fades linearly from 100 % to CAPACITY_AT_END_OF_LIFE across the
    warranted cycles, so the mean capacity over life is the average of the two.
    Modo quote capacity as AC useable at the point of connection, so depth of
    discharge is already inside the rating and is not applied again.
    """
    mean_capacity = (1.0 + CAPACITY_AT_END_OF_LIFE) / 2.0
    return WARRANTED_CYCLES * mean_capacity


def embodied_components():
    """Embodied carbon split the same way as cost: per kW and per kWh."""
    kg_per_kwh = 1.0 / PACK_KWH_PER_KG
    energy = kg_per_kwh * PACK_KGCO2E_PER_KG * (1.0 + CONTAINER_UPLIFT_FRACTION)
    power = PCS_KGCO2E_PER_UNIT / PCS_RATED_KW
    return {"energy_kgco2e_per_kWh": energy, "power_kgco2e_per_kW": power}


def builds_over_horizon(horizon_years):
    """How many battery builds a longer-lived host asset needs.

    The data centre runs 25 years; the battery lasts 15. Ignoring this would
    silently give the battery a 25-year life it does not have.
    """
    return float(horizon_years) / float(ASSET_LIFE_YEARS)


def cost_table(durations=(1, 2, 4, 8)):
    rows = []
    crf = capital_recovery_factor(WACC_REAL, ASSET_LIFE_YEARS)
    for case in CASES:
        comp = cost_components()[case]
        for d in durations:
            capex_kw = system_capex_gbp_per_kw(d, case)
            opex_kw = capex_kw * FIXED_OPEX_PCT_CAPEX[case]
            rows.append({
                "case": case, "duration_h": d,
                "capex_GBP_per_kW": round(capex_kw, 1),
                "capex_GBP_per_kWh": round(capex_kw / d, 1),
                "capex_GBP_per_MW": round(capex_kw * 1000, 0),
                "power_component_GBP_per_kW": round(comp["power_GBP_per_kW"], 1),
                "energy_component_GBP_per_kWh": round(comp["energy_GBP_per_kWh"], 1),
                "fixed_opex_GBP_per_kW_year": round(opex_kw, 2),
                "crf": round(crf, 5),
                "annualised_capex_GBP_per_kW_year": round(capex_kw * crf, 2),
                "total_annual_GBP_per_kW_year": round(capex_kw * crf + opex_kw, 2),
                "opex_is_proxy": OPEX_IS_PROXY,
            })
    return pd.DataFrame(rows)


def carbon_table(durations=(1, 2, 4, 8)):
    emb = embodied_components()
    thr = lifetime_throughput_mwh_per_mwh()
    rows = []
    for d in durations:
        per_kw = emb["power_kgco2e_per_kW"] + emb["energy_kgco2e_per_kWh"] * d
        per_kwh = per_kw / d
        rows.append({
            "duration_h": d,
            "embodied_kgco2e_per_kW": round(per_kw, 1),
            "embodied_kgco2e_per_kWh": round(per_kwh, 1),
            "embodied_tco2e_per_MW": round(per_kw, 1),
            "lifetime_throughput_MWh_per_MWh": round(thr, 0),
            "embodied_kgco2e_per_MWh_throughput": round(per_kwh * 1000 / thr, 2),
        })
    return pd.DataFrame(rows)


def check_against_ecoinvent():
    """Re-score the pinned ecoinvent factors and fail if they have drifted."""
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        import bw2data as bd
        import lca_helpers as H
        ei, _bio, _fg, _m = H.setup_brightway()
        method = next(m for m in bd.methods if m[1] == "IPCC 2021"
                      and m[2] == "climate change" and "GWP100" in str(m)
                      and "no LT" not in str(m))
    except Exception as e:
        return f"skipped — Brightway unavailable ({type(e).__name__})"

    problems = []
    for (name, loc), pinned, label in (
            (BATTERY_ACTIVITY, PACK_KGCO2E_PER_KG, "LFP pack"),
            (PCS_ACTIVITY, PCS_KGCO2E_PER_UNIT, "inverter 500kW")):
        hits = [a for a in ei if a["name"] == name and a["location"] == loc]
        if not hits:
            problems.append(f"{label}: activity not found")
            continue
        got = H.run_lca_score(hits[0], method)
        if abs(got - pinned) / pinned > 0.001:
            problems.append(f"{label}: ecoinvent={got:.3f} pinned={pinned:.3f}")
    if problems:
        raise AssertionError("battery factors are stale:\n  " + "\n  ".join(problems))
    return "OK — 2 ecoinvent factors match their pinned values"


def run():
    print("=" * 92)
    print("BATTERY STORAGE — Li-ion LFP, real 2025 GBP and IPCC 2021 GWP100")
    print("=" * 92)
    print(check_against_ecoinvent())

    comp = cost_components()
    emb = embodied_components()
    print()
    print("Two-part structure (power and energy sized independently)")
    print("-" * 92)
    print(f"{'':<22}{'low':>14}{'central':>14}{'high':>14}")
    print(f"{'capex, power':<22}" + "".join(
        f"{comp[c]['power_GBP_per_kW']:>13.0f} " for c in CASES) + " GBP/kW")
    print(f"{'capex, energy':<22}" + "".join(
        f"{comp[c]['energy_GBP_per_kWh']:>13.0f} " for c in CASES) + " GBP/kWh")
    print(f"{'embodied, power':<22}{emb['power_kgco2e_per_kW']:>13.1f} "
          f"{'(no case spread)':>28}  kg CO2e/kW")
    print(f"{'embodied, energy':<22}{emb['energy_kgco2e_per_kWh']:>13.1f} "
          f"{'':>28}  kg CO2e/kWh")

    print()
    print(f"WACC {WACC_REAL:.1%} real | life {ASSET_LIFE_YEARS} y | "
          f"CRF {capital_recovery_factor(WACC_REAL, ASSET_LIFE_YEARS):.4f} | "
          f"RTE {ROUND_TRIP_EFFICIENCY:.0%}")
    print(f"{WARRANTED_CYCLES:,} cycles to {CAPACITY_AT_END_OF_LIFE:.0%} capacity "
          f"-> {lifetime_throughput_mwh_per_mwh():,.0f} MWh out per MWh installed")

    ct, kt = cost_table(), carbon_table()
    print()
    print("By duration")
    print("-" * 92)
    print(f"{'dur':>5}{'capex k/MW':>13}{'£/kWh':>9}{'ann. £/kW/y':>14}"
          f"{'embodied t/MW':>16}{'kg/MWh cycled':>16}")
    for d in (1, 2, 4, 8):
        c = ct[(ct.case == "central") & (ct.duration_h == d)].iloc[0]
        k = kt[kt.duration_h == d].iloc[0]
        print(f"{d:>4}h{c.capex_GBP_per_MW/1000:>13,.0f}{c.capex_GBP_per_kWh:>9.0f}"
              f"{c.total_annual_GBP_per_kW_year:>14,.0f}"
              f"{k.embodied_tco2e_per_MW:>16,.0f}"
              f"{k.embodied_kgco2e_per_MWh_throughput:>16.1f}")

    print()
    print("Cross-checks and caveats")
    print("-" * 92)
    survey_19h = system_capex_gbp_per_kw(1.9, "central")
    print(f"  Modo model assumption at 1.9 h: {survey_19h:,.0f} GBP/kW vs their own")
    print(f"  2024 survey average of 580 GBP/kW at the same duration — the forward")
    print(f"  assumption is {100*(580/survey_19h-1):.0f} % below observed 2024 outturn. The high case covers it.")
    print(f"  Two-hour: model {system_capex_gbp_per_kw(2,'central'):,.0f} vs survey median 650 GBP/kW.")
    print(f"  Battery life {ASSET_LIFE_YEARS} y vs data centre 25 y -> "
          f"{builds_over_horizon(25):.2f} builds over the DC's life,")
    print(f"  which both cost and carbon must carry.")
    print(f"  OPEX is a PROXY ({FIXED_OPEX_PCT_CAPEX['central']:.0%} of capex/y) — Modo do not publish it.")
    print(f"  LCA: {LCA_CAVEAT}.")

    OUT_DIR.mkdir(exist_ok=True)
    ct.to_csv(OUT_DIR / "battery_costs.csv", index=False)
    kt.to_csv(OUT_DIR / "battery_carbon.csv", index=False)
    print()
    print("Wrote: optimisation_outputs/battery_costs.csv, battery_carbon.csv")
    return ct, kt


if __name__ == "__main__":
    run()
