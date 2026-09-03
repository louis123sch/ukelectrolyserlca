"""
Hydrogen purchase price by colour.
=============================================================================

Hydrogen is **bought**, not self-produced: every colour is a delivered £/kg
that the data centre pays. Transport is out of scope (production is assumed
co-located — see ``ASSUMPTIONS.md``), so these are plant-gate prices with no
delivery leg added.

Each colour is tied to the Brightway activity that supplies its *emissions*,
so a price and its LCA can never drift apart.

Sources, and how solid each one is
----------------------------------
green (PEM / Alkaline)  TRANSCRIBED. NESO Green Hydrogen Data Portal,
                        "Levelised cost of green hydrogen modelling, 2025 to
                        2050" (resource cc2dad0c). A full sensitivity cube:
                        tech x scenario x build year x capacity factor x
                        electricity price x discount rate.

blue (ATR + CCS)        TRANSCRIBED. Same NESO dataset family, "Levelised
                        cost of blue hydrogen modelling, 2025 to 2050"
                        (resource 3f3b1bf0). Includes its own fuel, CO2 T&S
                        and emissions cost components.

grey (SMR unabated)     DERIVED. NESO and FES model green, blue and pink
                        only — neither publishes a grey price. So grey is
                        built from this study's own SMR inventory (4.85 m3
                        natural gas per kg H2) priced at the FES 2025 NBP gas
                        projection, plus a non-fuel cost scaled off NESO's
                        own blue cost stack, plus UK ETS carbon on the 9 kg
                        CO2/kg H2 the inventory emits directly.

turquoise (pyrolysis)   ASSUMED. Methane pyrolysis is pre-commercial and
                        appears in no UK official dataset. Built the same way
                        as grey from the MP-E inventory (5.72 m3 gas +
                        10.29 kWh per kg), with a non-fuel cost premium for
                        first-of-a-kind plant and an optional carbon-black
                        co-product credit. Treat as a scenario, not a price.

Deriving grey and turquoise from the project's *own* inventories is
deliberate: it means the gas consumption behind the price is the same number
the LCA charges emissions on.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run:  python optimisation/h2_prices.py
"""
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "optimisation_outputs"
CACHE_DIR = ROOT / "optimisation_outputs" / "neso_cache"

NESO_DATASTORE = "https://api.neso.energy/api/3/action/datastore_search"
NESO_GREEN_RESOURCE = "cc2dad0c-393c-4ae0-ae67-a98703169ad4"
NESO_BLUE_RESOURCE = "3f3b1bf0-4664-494f-a501-a39adabecd0d"

# --- reference point -------------------------------------------------------
BUILD_YEAR = 2025
# NESO's grid starts at 0.06. The study's own hurdle rates are 5.0-6.2 %, so
# 0.06 is the closest consistent choice; 0.08/0.10 read as merchant-risk.
DISCOUNT = {"low": 0.06, "central": 0.06, "high": 0.08}
GREEN_TECH = "PEM"          # matches pem_op_hermesmann_1kg_h2
GREEN_SCENARIO = "Central"

# Green LCOH is dominated by utilisation and power price, so the three cases
# pair them the way they actually co-occur: a cheap plant runs hard on cheap
# power. The central electricity price is baseline 1's own mean GB wholesale
# (79.83 GBP/MWh), rounded to NESO's 5 GBP grid.
GREEN_CASES = {
    "low":     {"capacity_factor": 0.70, "electricity_price": 40.0},
    "central": {"capacity_factor": 0.50, "electricity_price": 80.0},
    "high":    {"capacity_factor": 0.30, "electricity_price": 120.0},
}

# --- FES 2025 Data Workbook V006, sheets CP1 / CP2 -------------------------
# Real 2025 prices. The workbook publishes in EUR; its own conversion table
# gives GBP->EUR 1.17 for 2025.
EUR_PER_GBP_2025 = 1.17
# USD cross-rate via the same table (2025 USD->EUR 0.913), so every currency
# conversion in this module traces back to one published source.
USD_PER_GBP_2025 = 1.17 / 0.913
NBP_GAS_EUR_PER_MWH = {2025: 39.48, 2030: 29.89, 2035: 29.07, 2040: 28.58,
                       2045: 28.63, 2050: 28.72}
GB_CARBON_EUR_PER_T = {2025: 92.3808, 2030: 108.178, 2035: 115.309,
                       2040: 120.500, 2045: 128.782, 2050: 134.609}

# Natural gas higher heating value. UK pipeline gas is ~39.5 MJ/m3 gross.
GAS_KWH_HHV_PER_M3 = 39.5 / 3.6

# --- inventory coefficients, read from this project's own foreground -------
# (kept as constants so this module runs without Brightway; verified against
#  the activities by ``check_against_inventory()``)
INVENTORY = {
    "grey":      {"code": "smr_hermesmann_1kg_h2",
                  "gas_m3_per_kg": 4.85, "elec_kwh_per_kg": -1.1,
                  "direct_co2_kg_per_kg": 9.0},
    "blue":      {"code": "smr_ccs_hermesmann_1kg_h2",
                  "gas_m3_per_kg": 5.33, "elec_kwh_per_kg": -0.05,
                  "direct_co2_kg_per_kg": 0.99},
    "turquoise": {"code": "mp_e_1kg_h2",
                  "gas_m3_per_kg": 5.72, "elec_kwh_per_kg": 10.29,
                  "direct_co2_kg_per_kg": 0.0},
    "green":     {"code": "pem_op_hermesmann_1kg_h2",
                  "gas_m3_per_kg": 0.0, "elec_kwh_per_kg": 54.0,
                  "direct_co2_kg_per_kg": 0.0},
}

# --- the electricity behind bought green hydrogen --------------------------
# Green hydrogen is defined by what goes into it: a third party makes it from
# renewable electricity and sells it on. Its burden is therefore that seller's
# plant, cradle to gate, and the only free term is the carbon intensity of the
# electricity the seller runs on.
#
# Scoring ``pem_op_hermesmann_1kg_h2`` whole gets this wrong, because the
# activity's 54 kWh/kg is linked to ecoinvent's GB *grid* market. That charged
# bought green 17.001 kg CO2e/kg — dirtier than grey SMR, and dirtier than the
# LP plugging its own electrolyser into the grid, the 1 % gap being nothing but
# the seller's amortised capital. Grid electrolysis is a real configuration,
# but the study already models it properly as ``grid_h2``, where the LP supplies
# the electricity carbon from its own half-hourly dispatch instead of from one
# stale annual average. The bought row was a worse-modelled duplicate of it.
#
# 76 % of that 311 g/kWh comes from a single dataset, "electricity production,
# natural gas, conventional power plant", which ``lca_helpers.py`` already
# refuses to use for this study's own grid. The refusal was never propagated
# here; this is that propagation, not a new judgement.
#
# The default is ecoinvent's own GB onshore wind activity, unmodified — same
# database, version and method as every other coefficient in the study, and
# conservative against the harmonised literature (IPCC AR5's "infrastructure and
# supply chain typical" 15, ClimateXChange's mean 15, ZHAW 2025's European
# average 14.9 all sit beside it). ``renewables.py`` restates that same activity
# down to 5.635 g/kWh at this study's 38.1 % load factor and 35-year life. That
# restatement is right for a wind farm the LP builds and wrong for a seller's,
# whose load factor and asset life the buyer does not control; it also lands
# below IPCC AR5's reported onshore minimum of 7.0 and is capital-only in scope.
# It stays selectable as a parity sensitivity, never as a purchase basis.
GREEN_H2_ELECTRICITY_BASES = {
    "ecoinvent_onshore": {
        "gco2e_per_kwh": 14.465892541442467,
        "label": "ecoinvent 3.9.1 apos, GB onshore wind 1-3MW turbine, as scored",
        "grade": "transcribed",
        "note": "the study's own generation activity, unrestated — see "
                "renewables_embodied.csv, column ecoinvent_per_kWh",
    },
    "iea_2025_onshore_harmonised": {
        "gco2e_per_kwh": 11.76,
        "label": "IEA, Life Cycle Upstream Emission Factors 2025, onshore wind median",
        "grade": "transcribed",
        "note": "~50 estimates harmonised on AR6 GWP100, the same "
                "characterisation vintage as this study's IPCC 2021 method",
    },
    "study_onshore_restated": {
        "gco2e_per_kwh": 5.634870431035291,
        "label": "renewables.py restated GB onshore wind, 38.1 % LF / 35 y",
        "grade": "derived",
        "note": "own-build parity sensitivity only. Below IPCC AR5's reported "
                "onshore minimum, and capital-only in scope (the full-scope "
                "figure is 5.766) — not comparable with published ranges",
    },
}
GREEN_H2_ELECTRICITY_BASIS = "ecoinvent_onshore"
if GREEN_H2_ELECTRICITY_BASIS not in GREEN_H2_ELECTRICITY_BASES:
    raise ValueError("GREEN_H2_ELECTRICITY_BASIS must be one of "
                     f"{list(GREEN_H2_ELECTRICITY_BASES)}")

# Every basis above is renewable, and deliberately so: there is no grid-carbon
# green hydrogen. The grid figure below is kept for provenance and for
# reproducing pre-fix runs, but it is *not* a basis and must not be selectable
# as one — offered as a peer of the wind options it would let a caller pair
# behind-the-meter renewable pricing with grid carbon, which is the exact
# incoherence this whole section exists to remove.
ECOINVENT_GB_LV_GCO2E_PER_KWH = 311.21970194853005
LEGACY_GREEN_H2_GWP_KGCO2E_PER_KG = 17.00093068911594

# --- delivering it: what separates the two green rows ----------------------
# Green hydrogen is renewable however the electricity reaches the electrolyser,
# but reaching it *over the grid* is not free, and the two terms that make it
# costly are ones ecoinvent separates from generation itself:
#
#   losses   1.063495 kWh must be generated per kWh delivered at low voltage,
#            a 6.35 % gross-up, accumulated over the HV -> MV -> LV chain.
#   network  8.2125 g CO2e per kWh delivered, being the transmission and
#            distribution infrastructure: LV distribution 5.932, MV
#            transmission 1.583, HV transmission 0.655, network maintenance
#            0.019, SF6 switchgear leakage 0.025.
#
# Behind the meter the electrolyser sits on the generator's own terminals and
# pays neither. That is the entire carbon difference between the two green
# rows — a *delivery* difference, not a generation one, since the source is
# renewable in both. Both are derived from ecoinvent 3.9.1 apos's GB
# `market for electricity, low voltage` by contribution analysis, and
# ``check_grid_delivery()`` re-derives them from the live database.
GRID_DELIVERY_LOSS_GROSS_UP = 1.063495
GRID_DELIVERY_NETWORK_GCO2E_PER_KWH = 8.2125
# The variant in h2_prices_recommended.csv that takes delivery over the grid.
GREEN_GRID_DELIVERED_VARIANT = "grid-connected electrolyser"

# Default supply mix. A buyer contracting for green hydrogen on the open market
# gets a portfolio, not one plant: some of it made behind a generator's meter,
# some by electrolysers taking renewable power over the network. Both are green —
# the source is renewable either way — so the mix moves price and delivery burden
# together and nothing else.
#
# ASSUMED. 50:50 is a neutral prior, not a market observation: no GB breakdown of
# green hydrogen production by connection type is published, and at the current
# scale of the GB electrolyser fleet any such split would be dominated by a
# handful of projects. It is exposed as ``green_h2_grid_share`` on
# ``build_tech()`` precisely so it can be swept rather than trusted.
# 0.0 is all behind the meter, 1.0 all grid-connected.
GREEN_H2_GRID_SHARE = 0.5


def _resolve_grid_share(grid_share: float | None) -> float:
    share = GREEN_H2_GRID_SHARE if grid_share is None else float(grid_share)
    if not 0.0 <= share <= 1.0:
        raise ValueError(f"green_h2_grid_share must be in [0, 1], got {share!r}")
    return share

# UK Low Carbon Hydrogen Standard, 20 gCO2e/MJ LHV x 120 MJ/kg. A compliance
# ceiling, never a coefficient: the standard excludes capital goods and so sets
# renewable electricity to 0.0 gCO2e/kWh, zero-rating precisely the term being
# estimated above. Used by ``validate.py`` as an upper bound, and worth quoting
# for what it says about the grid-connected case rather than the green one.
LCHS_CEILING_KGCO2E_PER_KG = 2.400


def _reject_grid_basis(basis: str) -> None:
    """The grid is not a way of making green hydrogen, and never a basis here."""
    if basis in ("ecoinvent_gb_grid", "gb_grid", "grid"):
        raise ValueError(
            "The GB grid mix is not a basis for green hydrogen — green is "
            "defined by renewable input, and this pairing charged grid "
            "generation carbon against a renewable price. Grid electrolysis is "
            "already modelled as the 'grid_h2' architecture, where the LP "
            "supplies the electricity carbon from its own half-hourly dispatch. "
            "For a seller who takes RENEWABLE power over the network, pass "
            "grid_delivered=True, which adds the network's losses and embodied "
            "carbon without changing the source. To reproduce a pre-fix run, "
            "use LEGACY_GREEN_H2_GWP_KGCO2E_PER_KG directly.")


def check_grid_delivery(tol_frac: float = 0.02) -> dict:
    """Re-derive the delivery constants from the live database.

    Same contract as ``check_against_inventory()``: the constants above are kept
    hard-coded so this module runs without Brightway, and this fails the run if
    they have drifted from the activities they were taken from.
    """
    import bw2calc as bc
    import bw2data as bd

    import lca_helpers as H
    from optimisation import electrolysers as ely

    H.setup_brightway()
    method = ely._gwp_method(bd)
    ei = bd.Database("ecoinvent-3.9.1-apos")
    lv = next(a for a in ei if a["name"] == "market for electricity, low voltage"
              and a.get("location") == "GB")
    lca = bc.LCA({lv: 1}, method)
    lca.lci()
    lca.lcia()
    rev = {v: k for k, v in lca.activity_dict.items()}

    gen_kwh = network = 0.0
    for idx, amount in enumerate(lca.supply_array):
        if abs(amount) < 1e-14:
            continue
        act = bd.get_activity(rev[idx])
        name = act["name"]
        # Generation is every leaf that produces a kWh; the loss gross-up is
        # simply how much of it the chain draws to deliver one.
        if act.get("unit") == "kilowatt hour" and name.startswith("electricity production"):
            gen_kwh += amount
        # Take the market rows only: each sits at the top of its own sub-tree,
        # so construction and maintenance are counted once between them.
        elif name.startswith("market for") and (
                "network, electricity" in name
                or name.startswith("market for sulfur hexafluoride")):
            network += H.run_lca_score(act, method) * amount

    out = {"loss_gross_up": gen_kwh,
           "network_gco2e_per_kwh": network * 1000.0,
           "lv_market_gco2e_per_kwh": lca.score * 1000.0}
    problems = []
    for key, const in (("loss_gross_up", GRID_DELIVERY_LOSS_GROSS_UP),
                       ("network_gco2e_per_kwh", GRID_DELIVERY_NETWORK_GCO2E_PER_KWH),
                       ("lv_market_gco2e_per_kwh", ECOINVENT_GB_LV_GCO2E_PER_KWH)):
        if abs(out[key] - const) > tol_frac * abs(const):
            problems.append(f"{key}: constant {const:.6g}, live {out[key]:.6g}")
    if problems:
        raise AssertionError("Grid delivery constants have gone stale:\n  "
                             + "\n  ".join(problems))
    out["ok"] = True
    return out


def green_h2_electricity_gco2e_per_kwh(basis: str | None = None, *,
                                       grid_share: float | None = None) -> float:
    """Carbon intensity of the electricity the seller's electrolyser consumes.

    ``grid_share`` is the fraction of supply taken over the network rather than
    off a generator's terminals, and defaults to ``GREEN_H2_GRID_SHARE``. That
    fraction carries the two costs of delivery — the loss gross-up and the
    network's own embodied carbon — and neither changes where the electricity
    came from: green is renewable at any share.
    """
    basis = basis or GREEN_H2_ELECTRICITY_BASIS
    _reject_grid_basis(basis)
    if basis not in GREEN_H2_ELECTRICITY_BASES:
        raise ValueError(f"Unknown green H2 electricity basis {basis!r}. "
                         f"Available: {list(GREEN_H2_ELECTRICITY_BASES)}")
    share = _resolve_grid_share(grid_share)
    behind = GREEN_H2_ELECTRICITY_BASES[basis]["gco2e_per_kwh"]
    delivered = behind * GRID_DELIVERY_LOSS_GROSS_UP + GRID_DELIVERY_NETWORK_GCO2E_PER_KWH
    return (1.0 - share) * behind + share * delivered


def green_h2_gwp_per_kg(basis: str | None = None, *,
                        grid_share: float | None = None) -> float:
    """kg CO2e per kg of bought green hydrogen, at the seller's gate.

    ``foreground_fixed_kgco2e_per_kg`` is everything in the PEM activity that is
    not electricity — the seller's electrolyser capital good *plus* its water and
    heat — so the electricity term is added once and only once. Do not add
    ``capital_kgco2e_per_kg_h2`` on top of it; that is already inside, and doing
    so inflates the answer by 17.6 %.

    ``grid_share`` mixes the two green supply routes: a seller taking delivery
    over the network pays for its losses and its embodied carbon, one behind the
    meter pays for neither. Defaults to ``GREEN_H2_GRID_SHARE``.
    """
    from optimisation import electrolysers as ely

    intensity = green_h2_electricity_gco2e_per_kwh(basis, grid_share=grid_share)
    row = next(r for r in ely.decompose_all()
               if r["technology"] == "PEM operation")
    return (row["foreground_fixed_kgco2e_per_kg"]
            + row["kwh_per_kg"] * intensity / 1000.0)


# Non-fuel cost (capex + fixed + variable opex) per kg H2. NESO's blue stack
# at 2025/6 % is 0.511 + 0.185 + 0.029 = 0.725 GBP/kg for ATR+CCS.
BLUE_NONFUEL_GBP_PER_KG = 0.725
# Unabated SMR needs no capture train, shift upgrade or CO2 compression.
GREY_NONFUEL_FRACTION_OF_BLUE = 0.60
# --- methane pyrolysis -----------------------------------------------------
# No UK or IEA cost data exists for pyrolysis, so its price is *constructed*
# rather than sourced. It is built as a mix of the grey and green routes,
# weighted by pyrolysis's own energy inputs: MP-E consumes natural gas like a
# reformer (5.72 m3/kg) and electricity like an electrolyser (10.29 kWh/kg),
# so its cost should sit between the two in the same proportion.
#
# Weights come from the inventory itself, on an HHV energy basis, so they
# cannot drift from the LCA. This replaces an earlier first-of-a-kind
# multiplier on ATR+CCS non-fuel cost, which was pure guesswork.
#
# The blend carries no first-of-a-kind premium by default. Pyrolysis is
# pre-commercial (IEA GHR 2026: Hycamite 2 ktpa, Hazer 30-50 ktpa design
# package), so a real plant would cost more than mature-technology inputs
# imply. The high case carries a premium; 0 keeps the blend pure.
TURQUOISE_FOAK_PREMIUM_GBP_PER_KG = {"low": 0.0, "central": 0.0, "high": 0.50}
# --- solid carbon co-product ----------------------------------------------
# CH4 -> C + 2 H2 yields exactly 3 kg of solid carbon per kg of H2 (12/4).
# Rego et al. 2026 adopt a commercial-grade carbon black price of USD 1.52/kg
# and find it the single strongest driver of pyrolysis economics - their
# sensitivity analysis ranks it above both gas and electricity price, and
# they cite work showing carbon revenues can cut LCOH by up to 80 %.
#
# The credit is nonetheless defaulted OFF. At full realisation it is worth
# ~3 x 1.52 = USD 4.56/kg H2, which would make the hydrogen free or
# negative - arithmetic that only holds if the carbon black market can
# absorb pyrolysis output at commercial-grade prices. It cannot: global
# carbon black demand is ~15 Mt/y against the tens of Mt of carbon that
# large-scale pyrolysis would produce, and the paper itself flags quality
# requirements, purification cost and price volatility. Set the realisation
# fraction to explore it as a scenario.
CARBON_BLACK_USD_PER_KG = 1.52          # Rego et al. 2026, Table 1
CARBON_KG_PER_KG_H2 = 3.0               # stoichiometric
CARBON_CREDIT_REALISATION = {"low": 0.0, "central": 0.0, "high": 0.0}


def carbon_black_credit_gbp_per_kg(case):
    """Sourced value of the solid-carbon co-product, GBP per kg H2."""
    gross_usd = CARBON_BLACK_USD_PER_KG * CARBON_KG_PER_KG_H2
    return (gross_usd / USD_PER_GBP_2025) * CARBON_CREDIT_REALISATION[case]


# Backwards-compatible view used by the cost-stack cross-check.
# --- literature validation bands for turquoise -----------------------------
# Rego, E.E., Oller Nascimento, C.A., Ribeiro, C.O. (2026), "Economic analysis
# under uncertainty of turquoise hydrogen via methane pyrolysis", Int. J.
# Hydrogen Energy 225, 154378. Open access, CC BY.
TURQUOISE_LITERATURE_USD_PER_KG = {
    "Rego et al. 2026 (LCOH range)": (2.0, 4.0),
    "Brazilian EPE, cited therein": (1.5, 4.4),
}
# The same paper assumes 16 kWh/kg H2 of fuel/electricity. This study's MP-E
# inventory uses 10.29 kWh/kg - a materially lower-energy variant. Recorded
# so the gap is visible rather than silently averaged away; it makes this
# study's turquoise cheaper and cleaner than Rego et al.'s.
TURQUOISE_LITERATURE_KWH_PER_KG = 16.0


TURQUOISE_CARBON_CREDIT_GBP_PER_KG = {
    c: (CARBON_BLACK_USD_PER_KG * CARBON_KG_PER_KG_H2 / USD_PER_GBP_2025)
       * CARBON_CREDIT_REALISATION[c]
    for c in ("low", "central", "high")}


def turquoise_energy_weights():
    """Share of pyrolysis energy input from gas vs electricity, HHV basis."""
    inv = INVENTORY["turquoise"]
    gas_kwh = inv["gas_m3_per_kg"] * GAS_KWH_HHV_PER_M3
    elec_kwh = inv["elec_kwh_per_kg"]
    total = gas_kwh + elec_kwh
    return {"gas_kwh": gas_kwh, "elec_kwh": elec_kwh, "total_kwh": total,
            "gas_share": gas_kwh / total, "elec_share": elec_kwh / total}


def turquoise_blend(grey_price, green_price, case):
    """Mix the grey and green prices by pyrolysis's own gas:electricity split."""
    w = turquoise_energy_weights()
    blended = w["gas_share"] * grey_price + w["elec_share"] * green_price
    return (blended
            + TURQUOISE_FOAK_PREMIUM_GBP_PER_KG[case]
            - TURQUOISE_CARBON_CREDIT_GBP_PER_KG[case])
# Does the hydrogen producer pay UK ETS on its own direct CO2?
APPLY_CARBON_PRICE = {"low": False, "central": True, "high": True}
# Electricity price the producer pays, GBP/MWh (used by grey/turquoise).
PRODUCER_ELEC_GBP_PER_MWH = {"low": 40.0, "central": 80.0, "high": 120.0}

# =============================================================================
# European Hydrogen Observatory — UK 2024 production costs (EUR/kg, 2024)
# =============================================================================
# "Hydrogen production costs 2024" workbook: country x technology x cost
# component. UK rows only. This is the most direct source available - UK
# specific, per technology, with the full cost stack - so it takes precedence
# over the derivation for grey and blue, which is retained as a cross-check.
#
# Note "Grid electrolysis" carries 1.214 grid fees + 1.556 taxes = 2.77 EUR/kg
# of network cost, 29 % of its total. A behind-the-meter electrolyser on
# on-site wind avoids that, which is why the directly-connected row is the
# right analogue for this study's own electrolyser and the grid-connected row
# is the right one for an electrolyser importing from the grid.
EHO_UK_2024_EUR_PER_KG = {
    "SMR": {"CAPEX": 0.263, "Natural gas costs": 2.666, "CO2 costs": 0.332,
            "Other OPEX": 0.092},
    "Reforming with carbon capture": {"CAPEX": 0.430, "Natural gas costs": 2.876,
                                      "CO2 costs": 0.883, "Other OPEX": 0.131},
    "Grid electrolysis": {"CAPEX": 2.761, "Wholesale electricity costs": 3.805,
                          "Grid Fees": 1.214, "Taxes": 1.556, "Other OPEX": 0.187},
    "Renewable hydrogen directly connected": {"CAPEX": 2.771,
                                              "Electricity costs": 2.676,
                                              "Grid fees and taxes": 0.0,
                                              "Other OPEX": 0.182},
}
# GDP deflator 2024 -> 2025, from the FES workbook's own rebasing table.
DEFLATOR_2024_TO_2025 = 124.1 / 121.2


def eho_gbp_per_kg(technology):
    """EHO UK total for a technology, converted to real 2025 GBP."""
    total_eur = sum(EHO_UK_2024_EUR_PER_KG[technology].values())
    return total_eur / EUR_PER_GBP_2025 * DEFLATOR_2024_TO_2025


# =============================================================================
# IEA Global Hydrogen Review 2026 — published 2025 ranges, for a sanity check
# =============================================================================
# Figure 3.20 and surrounding text, page 110-111. Global ranges, so they are a
# plausibility band, not a target: GB is a high-gas-price, high-power-price
# market and should sit in the upper part of each.
IEA_2026_USD_PER_KG = {
    "grey":  (1.0, 4.0),    # "less than USD 1/kg to more than USD 4/kg" (2025)
    "blue":  (1.4, 5.0),    # grey + "USD 0.4/kg to more than USD 1/kg" for CCUS
    "green": (3.0, 10.0),   # "over USD 3/kg to well above USD 10/kg"
}

CASES = ("low", "central", "high")
INVERSE_CASE = {"low": "high", "central": "central", "high": "low"}


def _fetch(resource_id, name):
    """Pull a NESO datastore resource, caching it locally."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{name}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    records, offset = [], 0
    while True:
        r = requests.get(NESO_DATASTORE,
                         params={"resource_id": resource_id,
                                 "limit": 10000, "offset": offset},
                         timeout=60)
        r.raise_for_status()
        batch = r.json()["result"]["records"]
        records += batch
        if len(batch) < 10000:
            break
        offset += 10000
    df = pd.DataFrame(records)
    df = df[[c for c in df.columns if c != "_id"]]
    df.to_csv(cache, index=False)
    return df


def gas_gbp_per_mwh(year=BUILD_YEAR):
    return NBP_GAS_EUR_PER_MWH[year] / EUR_PER_GBP_2025


def carbon_gbp_per_t(year=BUILD_YEAR):
    return GB_CARBON_EUR_PER_T[year] / EUR_PER_GBP_2025


def green_prices():
    """NESO green LCOH at this study's reference point, GBP/kg."""
    df = _fetch(NESO_GREEN_RESOURCE, "neso_green_lcoh")
    df = df[(df["Units"] == "£/kg H2") &
            (df["Build Year"].astype(int) == BUILD_YEAR) &
            (df["Tech"] == GREEN_TECH) &
            (df["Scenario"] == GREEN_SCENARIO)]
    out = {}
    for case in CASES:
        spec = GREEN_CASES[case]
        sel = df[(df["Capacity Factor"].astype(float) == spec["capacity_factor"]) &
                 (df["Electricity Price"].astype(float) == spec["electricity_price"]) &
                 (df["Discount Factor"].astype(float) == DISCOUNT[case])]
        if sel.empty:
            raise LookupError(f"no NESO green row for {case}: {spec}")
        out[case] = float(sel["LCOH"].iloc[0])
    return out


def blue_prices():
    """NESO blue (ATR + CCS) LCOH, GBP/kg."""
    df = _fetch(NESO_BLUE_RESOURCE, "neso_blue_lcoh")
    df = df[(df["Units"] == "£/kg H2") &
            (df["Build Year"].astype(int) == BUILD_YEAR)]
    out = {}
    for case in CASES:
        sel = df[df["Discount Factor"].astype(float) == DISCOUNT[case]]
        if sel.empty:
            raise LookupError(f"no NESO blue row for discount {DISCOUNT[case]}")
        out[case] = float(sel["LCOH"].iloc[0])
    # low/high widen on capex the way FES's own sensitivities do (+/-25 %),
    # applied only to the capex component of the stack.
    capex = 0.511
    out["low"] = out["low"] - 0.25 * capex
    out["high"] = out["high"] + 0.25 * capex
    return out


def _fossil_price(colour, case):
    """Build a grey or turquoise price from gas, power, carbon and non-fuel."""
    inv = INVENTORY[colour]
    gas_mwh = inv["gas_m3_per_kg"] * GAS_KWH_HHV_PER_M3 / 1000.0
    fuel = gas_mwh * gas_gbp_per_mwh()

    # low/central/high label the price of *hydrogen*, so each driver is paired
    # with whichever direction pushes the H2 price that way. Electricity is a
    # cost for pyrolysis (10.29 kWh/kg) but a by-product credit for SMR
    # (-1.1 kWh/kg), so its pairing flips with the sign of the coefficient -
    # a dear power market makes pyrolysis H2 dearer and SMR H2 cheaper.
    elec_case = case if inv["elec_kwh_per_kg"] >= 0 else INVERSE_CASE[case]
    power = inv["elec_kwh_per_kg"] / 1000.0 * PRODUCER_ELEC_GBP_PER_MWH[elec_case]

    if colour == "grey":
        nonfuel = BLUE_NONFUEL_GBP_PER_KG * GREY_NONFUEL_FRACTION_OF_BLUE
        credit = 0.0
    else:
        # Direct energy cost only. Turquoise's headline price comes from
        # turquoise_blend(); this stack is retained as the cross-check on it.
        nonfuel = 0.0
        credit = TURQUOISE_CARBON_CREDIT_GBP_PER_KG[case]

    carbon = 0.0
    if APPLY_CARBON_PRICE[case]:
        carbon = inv["direct_co2_kg_per_kg"] / 1000.0 * carbon_gbp_per_t()

    return {"fuel": fuel, "power": power, "nonfuel": nonfuel,
            "carbon": carbon, "credit": -credit,
            "total": fuel + power + nonfuel + carbon - credit}


def headline_prices(green_neso, blue_neso):
    """The one headline price per colour, shared by every output.

    Defined once so ``price_table()`` and ``recommended_table()`` cannot
    disagree - an earlier version had them differ by up to 0.9 GBP/kg because
    each picked its own preferred source.

    Green is the behind-the-meter variant, which is the one this study's own
    electrolyser sees; the grid-connected variant is added by
    ``recommended_table()`` as a second row.
    """
    grey = {"low": _fossil_price("grey", "central")["total"],
            "central": eho_gbp_per_kg("SMR"),
            "high": eho_gbp_per_kg("SMR") * 1.15}
    blue = {"low": blue_neso["central"],
            "central": eho_gbp_per_kg("Reforming with carbon capture"),
            "high": eho_gbp_per_kg("Reforming with carbon capture") * 1.15}
    green = {"low": green_neso["low"],
             "central": eho_gbp_per_kg("Renewable hydrogen directly connected"),
             "high": green_neso["central"]}
    return grey, blue, green


def price_table():
    """Per-source build-up. ``recommended_table()`` is the deliverable; this
    is the working detail behind it, and must agree with it colour by colour."""
    green, blue = green_prices(), blue_prices()
    grey_px, blue_px, green_px = headline_prices(green, blue)
    rows = []
    for colour in ("grey", "blue", "turquoise", "green"):
        for case in CASES:
            inv = INVENTORY[colour]
            if colour == "green":
                total, stack = green_px[case], {}
            elif colour == "blue":
                total, stack = blue_px[case], {}
            elif colour == "turquoise":
                # headline is the energy-weighted grey/green blend; the direct
                # energy stack rides along as its breakdown and cross-check
                stack = _fossil_price(colour, case)
                total = turquoise_blend(grey_px[case], green_px[case], case)
            else:
                # grey: EHO UK is the headline, same as recommended_table().
                # The derivation stays visible as the component stack, which
                # is what corroborates it rather than competing with it.
                stack = _fossil_price(colour, case)
                total = grey_px[case]
            rows.append({
                "colour": colour,
                "case": case,
                "price_GBP_per_kg": round(total, 2),
                "activity_code": inv["code"],
                "activity_database": "hydrogen foreground",
                "gas_m3_per_kg": inv["gas_m3_per_kg"],
                "elec_kwh_per_kg": inv["elec_kwh_per_kg"],
                "direct_co2_kg_per_kg": inv["direct_co2_kg_per_kg"],
                "build_year": BUILD_YEAR,
                "discount_rate": DISCOUNT[case],
                "basis": {"green": "transcribed", "blue": "transcribed",
                          "grey": "derived", "turquoise": "constructed"}[colour],
                "source": {
                    "green": "NESO Green Hydrogen Data Portal, LCOH green 2025-2050",
                    "blue": "NESO Green Hydrogen Data Portal, LCOH blue (ATR+CCS) 2025-2050",
                    "grey": "Derived: SMR inventory gas x FES 2025 NBP gas price "
                            "+ scaled NESO blue non-fuel + UK ETS on direct CO2",
                    "turquoise": "Constructed: grey/green blend weighted by the "
                                 "MP-E inventory's own gas:electricity energy split",
                }[colour],
                **{f"component_{k}": round(v, 3) for k, v in stack.items()
                   if k != "total"},
            })
    return pd.DataFrame(rows)


# =============================================================================
# Recommended assumption set — triangulated across sources
# =============================================================================
# Central takes the best-matched source for each colour; low/high are the
# spread across the sources that disagree, not an invented band. Where only
# one source exists (turquoise), that is stated rather than disguised.
#
# Blue maps to EHO's "Reforming with carbon capture" rather than NESO's
# "ATR + CCS" because this study's activity is smr_ccs_hermesmann - SMR with
# capture, not autothermal reforming. NESO's ATR figure becomes the low case,
# which is the right shape: ATR is the cheaper, more efficient route.
#
# Green splits in two because the physical setup differs and the cost gap is
# almost entirely UK network charges (2.77 EUR/kg of grid fees and taxes):
# an electrolyser behind the meter on on-site wind pays none of them.

def recommended_table():
    green_neso = green_prices()
    blue_neso = blue_prices()
    grey_derived = _fossil_price("grey", "central")["total"]

    grey_px, blue_px, green_px = headline_prices(green_neso, blue_neso)
    turq = {c: turquoise_blend(grey_px[c], green_px[c], c) for c in CASES}
    w = turquoise_energy_weights()

    rows = [
        {"colour": "grey", "variant": "SMR unabated",
         "activity_code": "smr_hermesmann_1kg_h2",
         "low": round(grey_px["low"], 2),
         "central": round(grey_px["central"], 2),
         "high": round(grey_px["high"], 2),
         "central_source": "EHO UK 2024, SMR",
         "corroboration": f"derived from own inventory + FES gas: "
                          f"{grey_derived:.2f} ({100*(grey_derived/eho_gbp_per_kg('SMR')-1):+.0f} %)"},
        {"colour": "blue", "variant": "SMR + CCS",
         "activity_code": "smr_ccs_hermesmann_1kg_h2",
         "low": round(blue_px["low"], 2),
         "central": round(blue_px["central"], 2),
         "high": round(blue_px["high"], 2),
         "central_source": "EHO UK 2024, reforming with carbon capture",
         "corroboration": f"NESO ATR+CCS {blue_neso['central']:.2f} "
                          f"(cheaper route, used as low case)"},
        {"colour": "turquoise", "variant": "methane pyrolysis",
         "activity_code": "mp_e_1kg_h2",
         "low": round(turq["low"], 2), "central": round(turq["central"], 2),
         "high": round(turq["high"], 2),
         "central_source": f"CONSTRUCTED — {w['gas_share']:.0%} grey + "
                           f"{w['elec_share']:.0%} green, by its own energy split",
         "corroboration": f"direct energy cost "
                          f"{_fossil_price('turquoise','central')['total']:.2f}; "
                          f"IEA GHR 2026 pre-commercial, publishes no cost"},
        {"colour": "green", "variant": "behind the meter, on-site renewables",
         "activity_code": "pem_op_hermesmann_1kg_h2",
         "low": round(green_px["low"], 2),
         "central": round(green_px["central"], 2),
         "high": round(green_px["high"], 2),
         "central_source": "EHO UK 2024, renewable H2 directly connected",
         "corroboration": f"NESO PEM cube {green_neso['low']:.2f}-{green_neso['central']:.2f} "
                          f"at CF 0.7-0.5"},
        {"colour": "green", "variant": "grid-connected electrolyser",
         "activity_code": "pem_op_hermesmann_1kg_h2",
         "low": round(green_neso["central"], 2),
         "central": round(eho_gbp_per_kg("Grid electrolysis"), 2),
         "high": round(green_neso["high"], 2),
         "central_source": "EHO UK 2024, grid electrolysis",
         "corroboration": "includes 2.77 EUR/kg UK grid fees + taxes, 29 % of total"},
    ]
    return pd.DataFrame(rows)


def check_against_iea():
    """Plausibility check against IEA GHR 2026's published 2025 ranges."""
    rec = recommended_table()
    lines, problems = [], []
    for colour, (lo_usd, hi_usd) in IEA_2026_USD_PER_KG.items():
        lo, hi = lo_usd / USD_PER_GBP_2025, hi_usd / USD_PER_GBP_2025
        sub = rec[rec.colour == colour]
        for _, r in sub.iterrows():
            inside = lo <= r["central"] <= hi
            # IEA's green range is for *renewable-based* electrolysis, i.e.
            # dedicated generation. It excludes the network charges and taxes
            # a grid-connected electrolyser pays, which in the UK are
            # 2.77 EUR/kg. Exceeding the band there is a category difference,
            # not a disagreement, so it is exempted rather than flagged.
            exempt = (colour == "green" and "grid-connected" in r["variant"])
            status = "ok" if inside else ("n/a — different scope" if exempt
                                          else "OUTSIDE")
            lines.append(f"  {colour:<10} {r['variant'][:34]:<34} "
                         f"{r['central']:>6.2f}  vs IEA {lo:>5.2f}-{hi:>5.2f} GBP/kg  "
                         f"{status}")
            if not inside and not exempt:
                problems.append(f"{colour}/{r['variant']}")
    # turquoise has no IEA figure; validate it against the dedicated TEA instead
    turq = rec[rec.colour == "turquoise"]["central"].iloc[0]
    for label, (lo_usd, hi_usd) in TURQUOISE_LITERATURE_USD_PER_KG.items():
        lo, hi = lo_usd / USD_PER_GBP_2025, hi_usd / USD_PER_GBP_2025
        inside = lo <= turq <= hi
        lines.append(f"  {'turquoise':<10} {label[:34]:<34} "
                     f"{turq:>6.2f}  vs lit {lo:>5.2f}-{hi:>5.2f} GBP/kg  "
                     f"{'ok' if inside else 'above band'}")
    return "\n".join(lines), problems


def check_against_inventory():
    """Verify the hardcoded coefficients still match the Brightway activities."""
    try:
        import bw2data as bd
        bd.projects.set_current("hydrogen-smr")
    except Exception as e:
        return f"skipped — Brightway unavailable ({type(e).__name__})"
    problems = []
    for colour, inv in INVENTORY.items():
        act = bd.get_activity(("hydrogen foreground", inv["code"]))
        # unit check matters: PEM has "heat ... other than natural gas" in MJ,
        # which a bare name match would wrongly count as gas.
        gas = sum(float(e["amount"]) for e in act.technosphere()
                  if e.input.get("unit") == "cubic meter"
                  and "natural gas" in (e.input["name"] or "").lower())
        elec = sum(float(e["amount"]) for e in act.technosphere()
                   if (e.input.get("unit") == "kilowatt hour"
                       and "electricity" in (e.input["name"] or "").lower()))
        for label, got, want in (("gas_m3", gas, inv["gas_m3_per_kg"]),
                                 ("elec_kwh", elec, inv["elec_kwh_per_kg"])):
            if abs(got - want) > 1e-6:
                problems.append(f"{colour}.{label}: activity={got:g} module={want:g}")
    if problems:
        raise AssertionError("h2_prices coefficients are stale:\n  "
                             + "\n  ".join(problems))
    return f"OK — {len(INVENTORY)} activities match their module coefficients"


def run():
    print("=" * 92)
    print(f"HYDROGEN PURCHASE PRICE BY COLOUR — build year {BUILD_YEAR}, real 2025 GBP")
    print("=" * 92)
    print(check_against_inventory())
    print(f"FES 2025 NBP gas   {gas_gbp_per_mwh():>8.2f} GBP/MWh HHV"
          f"   ({NBP_GAS_EUR_PER_MWH[BUILD_YEAR]} EUR @ {EUR_PER_GBP_2025})")
    print(f"GB total carbon    {carbon_gbp_per_t():>8.2f} GBP/tCO2")

    df = price_table()

    bad = []
    for colour, grp in df.groupby("colour"):
        v = grp.set_index("case")["price_GBP_per_kg"]
        if not (v["low"] <= v["central"] <= v["high"]):
            bad.append(f"{colour}: low={v['low']} central={v['central']} high={v['high']}")
    if bad:
        raise AssertionError(
            "price cases are not monotonic - a driver is paired the wrong way:\n  "
            + "\n  ".join(bad))

    print()
    piv = df.pivot(index="colour", columns="case", values="price_GBP_per_kg")
    piv = piv.reindex(["grey", "blue", "turquoise", "green"])[list(CASES)]
    basis = df.drop_duplicates("colour").set_index("colour")["basis"]
    print(f"{'colour':<12}{'low':>9}{'central':>10}{'high':>9}   basis")
    print("-" * 92)
    for c in piv.index:
        print(f"{c:<12}{piv.loc[c,'low']:>9.2f}{piv.loc[c,'central']:>10.2f}"
              f"{piv.loc[c,'high']:>9.2f}   {basis[c]}")

    print()
    print("Derived cost stacks, central case (GBP/kg)")
    print("-" * 92)
    for colour in ("grey", "turquoise"):
        s = _fossil_price(colour, "central")
        print(f"  {colour:<10} fuel {s['fuel']:>6.2f} | power {s['power']:>6.2f} "
              f"| non-fuel {s['nonfuel']:>5.2f} | carbon {s['carbon']:>5.2f} "
              f"| credit {s['credit']:>5.2f}  =  {s['total']:>5.2f}")

    rec = recommended_table()

    merged = rec.groupby("colour")[["low", "central", "high"]].first()
    detail = df.pivot_table(index="colour", columns="case",
                            values="price_GBP_per_kg")
    for colour in ("grey", "blue", "turquoise", "green"):
        a, b = merged.loc[colour, "central"], detail.loc[colour, "central"]
        if abs(a - b) > 0.005:
            raise AssertionError(
                f"{colour}: recommended table says {a:.2f} but the per-source "
                f"table says {b:.2f} - the two outputs disagree")

    print()
    print("Caveats")
    print("-" * 92)
    w = turquoise_energy_weights()
    print("  turquoise carries no first-of-a-kind premium in the central case. Its")
    print("  blend uses mature grey and green inputs, so it is a floor, not a")
    print("  forecast: %.0f%% gas / %.0f%% electricity by HHV energy (%.1f + %.1f kWh/kg)."
          % (100*w["gas_share"], 100*w["elec_share"], w["gas_kwh"], w["elec_kwh"]))
    print("  Rego et al. 2026 assume %.0f kWh/kg for pyrolysis; this study's MP-E"
          % TURQUOISE_LITERATURE_KWH_PER_KG)
    print("  inventory uses %.2f kWh/kg, a lower-energy variant - so this study's"
          % INVENTORY["turquoise"]["elec_kwh_per_kg"])
    print("  turquoise is cheaper and cleaner than theirs by construction.")
    print("  Carbon-black credit is OFF (realisation 0). At full value it is worth")
    print("  %.2f GBP/kg H2, which would dominate everything else - see the module"
          % (CARBON_BLACK_USD_PER_KG * CARBON_KG_PER_KG_H2 / USD_PER_GBP_2025))
    print("  docstring for why the market cannot actually absorb it.")
    gh = rec.query("colour=='green' and variant.str.contains('grid-connected')",
                   engine="python")["high"].iloc[0]
    print("  green tops out at %.2f for a grid-connected plant at CF %.2f on"
          % (gh, GREEN_CASES["high"]["capacity_factor"]))
    print("  %.0f GBP/MWh power at %.0f%% - an electrolyser that barely runs, on"
          % (GREEN_CASES["high"]["electricity_price"], 100 * DISCOUNT["high"]))
    print("  dear power, paying full UK network charges.")

    print()
    print("=" * 92)
    print("RECOMMENDED ASSUMPTION SET — triangulated, real 2025 GBP/kg")
    print("=" * 92)
    print(f"{'colour':<11}{'variant':<38}{'low':>7}{'central':>9}{'high':>7}")
    print("-" * 92)
    for _, r in rec.iterrows():
        print(f"{r.colour:<11}{r.variant[:37]:<38}{r.low:>7.2f}{r.central:>9.2f}{r.high:>7.2f}")
    print()
    for _, r in rec.iterrows():
        print(f"  {r.colour}/{r.variant[:30]}")
        print(f"      central: {r.central_source}")
        print(f"      check:   {r.corroboration}")

    print()
    print("Plausibility vs IEA Global Hydrogen Review 2026 (global 2025 ranges)")
    print("-" * 92)
    iea_lines, iea_problems = check_against_iea()
    print(iea_lines)
    if iea_problems:
        print(f"  NOTE: {len(iea_problems)} outside IEA's global range — "
              f"expected for GB only if high; check direction.")

    OUT_DIR.mkdir(exist_ok=True)
    rec.to_csv(OUT_DIR / "h2_prices_recommended.csv", index=False)
    path = OUT_DIR / "h2_prices_by_colour.csv"
    df.to_csv(path, index=False)
    print()
    print("Wrote:", path.relative_to(ROOT))
    return df


if __name__ == "__main__":
    run()
