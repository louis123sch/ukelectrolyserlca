"""
GB grid carbon — the whole LCA, in one place.
=============================================================================

The optimiser's grid carbon is a half-hourly series built by
``optimisation/grid_build.py`` from the NESO Carbon Intensity API's regional
generation mix. This module is everything *LCA* about that series:

1. **Sources** — the one activity that scores each API fuel, named by exact
   identity (name, location, reference product, and the database when it is a
   foreground one). ``SOURCES`` is the only place the grid's processes are
   chosen; each resolves by exact match and refuses zero or several hits. It
   used to be a search query plus a hit index, and ``"GAS": 3`` silently
   landed on the conventional plant (558 g/kWh) though the query asked for
   combined cycle (387) — about 12–21 % on every grid series. That is why
   nothing here is a search rank.
2. **Composites** — the API reports wind and imports as single figures.
   Wind is split by fixed weights from ecoinvent's own GB market. Imports are
   split by **where they came from in that half-hour**: Elexon's half-hourly
   interconnector flows, attributed to the region by a fit to NESO's own
   regional import share (``IMPORT_ATTRIBUTION``, section 2b).
3. **Pass-through storage** — pumped storage returns electricity the grid
   generated earlier, so it carries its own plant plus that electricity, not
   ecoinvent's GB market (section 3).
4. **The closed-form score** — ``score_row`` = Σ share × source score, per
   kWh *generated*. No losses, no network: those belong to delivery.
5. **Delivery** — every kWh taken over the network carries the losses and the
   network's embodied carbon down to the voltage it is taken at
   (``DELIVERY``). One basis for everything that takes grid electricity: the
   data centre's imports and a bought-hydrogen seller's electrolyser alike.

What a grid CSV holds
---------------------
``generation_kgco2e_per_kwh``   section 4, per kWh generated.
``custom_electricity_score``    delivered at ``REFERENCE_VOLTAGE`` (high), the
                                one-number grid intensity everything quotes.
``imp_<CC>``                    each country's share of the region's imports.

The LP does not read ``custom_electricity_score``: ``dc_inputs`` delivers the
generation column at the site's own connection voltage.

Every grid CSV records ``sources_id()`` — a hash of *everything* above that
moves a score (identities, method, weights, attribution, delivery) — and the
scored sources in a ``.sources.json`` beside it, so a series can always say
what scored it. ``profiles`` ignores a series scored on a different basis.
Editing anything here therefore makes every series stale;
``python -m optimisation.grid_build --rescore`` brings them back from the mix
each file already holds.

Method
------
**IPCC 2021 GWP100, with long-term emissions**, the variant every asset
coefficient in ``optimisation/`` is scored on. Until 13 Oct 2026 the grid used
the "no LT" variant; for these sources the two differ by under 0.02 %.
"""
from __future__ import annotations

import hashlib
import json

from optimiser_lca import registry as R
from optimiser_lca.common import Process

METHOD_LABEL = "IPCC 2021, climate change, GWP100 (with long-term emissions)"

# =============================================================================
# 1. Sources — one activity per Carbon Intensity API fuel
# =============================================================================
SOURCES = {
    # Conventional generation
    "GAS": Process(
        identity=("electricity production, natural gas, combined cycle power plant",
                  "GB", "electricity, high voltage"),
        query="electricity production natural gas combined cycle GB",
        why="GB's gas fleet is CCGT; the conventional plant dataset is 558 g/kWh "
            "against 387 here, and a search rank once picked it by mistake"),
    "COAL": Process(
        identity=("electricity production, hard coal", "GB", "electricity, high voltage"),
        query="electricity production hard coal GB"),
    "NUCLEAR": Process(
        identity=("electricity production, nuclear, boiling water reactor",
                  "GB", "electricity, high voltage"),
        query="electricity production nuclear GB",
        why="BWR, not PWR, as ecoinvent's own GB market does (17.0 % BWR, 2.5 % PWR "
            "of GB HV supply): GB's AGR fleet has no dataset and ecoinvent proxies it "
            "with BWR. 7.4 against 6.8 g/kWh, so the choice barely moves anything"),
    # Wind sub-technologies (composite, split by WIND_GROUP_WEIGHTS)
    "WIND_GT3_ONSHORE": Process(
        identity=("electricity production, wind, >3MW turbine, onshore",
                  "GB", "electricity, high voltage"),
        query="electricity production wind >3MW onshore GB"),
    "WIND_13_OFFSHORE": Process(
        identity=("electricity production, wind, 1-3MW turbine, offshore",
                  "GB", "electricity, high voltage"),
        query="electricity production wind 1-3MW offshore GB"),
    "WIND_13_ONSHORE": Process(
        identity=("electricity production, wind, 1-3MW turbine, onshore",
                  "GB", "electricity, high voltage"),
        query="electricity production wind 1-3MW onshore GB"),
    "WIND_EMB": Process(
        identity=("electricity production, wind, <1MW turbine, onshore",
                  "GB", "electricity, high voltage"),
        query="electricity production wind <1MW onshore GB",
        why="embedded (small, behind-the-meter) wind the API reports separately"),
    # Hydro
    "HYDRO": Process(
        identity=("electricity production, hydro, run-of-river", "GB", "electricity, high voltage"),
        query="electricity production hydro run-of-river GB"),
    # Imports (composite, split by country — section 2b). An exporter is scored
    # on its own high-voltage market: ecoinvent's "import from XX" [GB]
    # activities are exactly that market and nothing else (checked for FR, IE,
    # NL and BE), and there are none for NO or DK.
    "IMPORTS_FR": Process(
        identity=("electricity, high voltage, import from FR", "GB", "electricity, high voltage"),
        query="electricity high voltage import from FR GB"),
    "IMPORTS_BE": Process(
        identity=("electricity, high voltage, import from BE", "GB", "electricity, high voltage"),
        query="electricity high voltage import from BE GB"),
    "IMPORTS_NL": Process(
        identity=("electricity, high voltage, import from NL", "GB", "electricity, high voltage"),
        query="electricity high voltage import from NL GB"),
    "IMPORTS_NO": Process(
        identity=("market for electricity, high voltage", "NO", "electricity, high voltage"),
        query="market for electricity high voltage NO",
        why="North Sea Link; ecoinvent has no GB import-from-NO activity, and "
            "the others are this market under another name"),
    "IMPORTS_DK": Process(
        identity=("market for electricity, high voltage", "DK", "electricity, high voltage"),
        query="market for electricity high voltage DK",
        why="Viking Link; no GB import-from-DK activity, as for NO"),
    "IMPORTS_IE": Process(
        identity=("electricity, high voltage, import from IE", "GB", "electricity, high voltage"),
        query="electricity high voltage import from IE GB",
        why="all three Irish links, Moyle included: Northern Ireland trades in "
            "the all-island market and has no dataset of its own"),
    # Other generation
    "BIOMASS": Process(
        identity=("heat and power co-generation, wood chips, 6667 kW, state-of-the-art 2014",
                  "GB", "electricity, high voltage"),
        query="heat and power co-generation wood chips 6667 kW GB",
        why="the only GB biomass electricity dataset; Drax-scale pellet plant has none"),
    "OTHER": Process(
        identity=("electricity production, oil", "GB", "electricity, high voltage"),
        query="electricity production oil GB"),
    "SOLAR": Process(
        identity=("UPV, GB grid solar fleet, electricity per kWh", "GB",
                  "electricity, low voltage"),
        database=R.SOLAR_DB,
        why="the Smith 2024 plant this study builds its own solar on, at ecoinvent's "
            "GB yield (optimiser_lca/upv.py). It replaces ecoinvent's 2008 El Tesoro "
            "plant (79.8 g/kWh), which the study rejects for cap_solar"),
    "STORAGE": Process(
        identity=("electricity production, hydro, pumped storage", "GB", "electricity, high voltage"),
        query="electricity production hydro pumped storage GB",
        why="scored WITHOUT its electricity input, which is added back from the "
            "grid's own mix — see section 3"),
}

# What the sidecars record and the id hashes: the identity, plus the database
# for a foreground source.
GRID_SOURCES = {k: tuple(p.identity) + ((p.database,) if p.database else ())
                for k, p in SOURCES.items()}

# =============================================================================
# 2. Composites — the API's single wind and imports figures, split
# =============================================================================
# 2a. Wind. Shares inside ecoinvent 3.9.1's GB high-voltage market, normalised
# within the group. Transcribed from the market's own exchange amounts.
WIND_GROUP_WEIGHTS = {
    "WIND_GT3_ONSHORE": 0.006725107846 / 0.157504068947,
    "WIND_13_OFFSHORE": 0.05505783324  / 0.157504068947,
    "WIND_13_ONSHORE":  0.095721127861 / 0.157504068947,
}

# 2b. Imports. Until 13 Oct 2026 every half-hour's imports were split by the
# shares inside ecoinvent's GB market — FR 63 %, NL 30 %, IE 7 % — whatever the
# region and whatever was actually flowing. That basis is pre-2021: it has no
# North Sea Link or Viking Link, and in 2025 GB imported 21 % of its
# interconnector electricity from Norway and 11 % from Denmark. It also put
# the same mix on every region, though NESO's regional import share is plainly
# geographic (South East 43 %, North East 28 % where Norway lands, North
# Scotland under 1 %).
#
# Now: Elexon reports every interconnector's flow each half-hour (FUELHH).
# Positive flow is import. A region's imports in a half-hour are split across
# the links in proportion to  beta[link] x import flow[link], where beta says
# how much of each link reaches that region. beta is fitted per region by
# non-negative least squares of the region's API import share on the ten
# links' import flows over 2025 (grid_build.fit_import_attribution); the
# fit's R2 is recorded. The fit is used for *composition* — which links feed
# the region — not to predict how much it imports (the API supplies that), so
# a modest R2 still carries the answer: Yorkshire's 0.20 is 95 % North Sea
# Link, the South West's 0.19 is 81 % French. A region whose fit is noise
# (R2 < 0.15) or whose imports are negligible (< 2 % on average) takes every
# link equally, i.e. the national flows: North Scotland, South Scotland and
# South Wales, which import 0.6, 2.9 and 1.1 %.
#
# What 2025 gives (annual split of each region's imports):
#   London            FR 74 %, BE 16 %, NL 8 %, NO 2 %       R2 0.70
#   South East        FR 78 %, BE 13 %, NO 8 %               R2 0.71
#   East England      NL 60 %, FR 29 %, BE 10 %, DK 2 %      R2 0.68
#   North East        NO 88 %, FR 11 %                       R2 0.69
# against ecoinvent's FR 63 / NL 30 / IE 7 on every region before. Checked
# by the regression in grid_build.fit_import_attribution, re-runnable with
# ``python -m optimisation.grid_build --fit-imports``.
#
# Elexon fuel type -> (link, exporting country, GB landing point).
INTERCONNECTORS = {
    "INTFR":   ("IFA",            "FR", "Sellindge, Kent"),
    "INTIFA2": ("IFA2",           "FR", "Chilling, Hampshire"),
    "INTELEC": ("ElecLink",       "FR", "Folkestone, Kent"),
    "INTNEM":  ("Nemo Link",      "BE", "Richborough, Kent"),
    "INTNED":  ("BritNed",        "NL", "Isle of Grain, Kent"),
    "INTNSL":  ("North Sea Link", "NO", "Blyth, Northumberland"),
    "INTVKL":  ("Viking Link",    "DK", "Bicker Fen, Lincolnshire"),
    "INTIRL":  ("Moyle",          "IE", "Auchencrosh, Ayrshire"),
    "INTEW":   ("East West",      "IE", "Connah's Quay, Flintshire"),
    "INTGRNL": ("Greenlink",      "IE", "Pembroke"),
}
LINKS = list(INTERCONNECTORS)
COUNTRY_SOURCE = {"FR": "IMPORTS_FR", "BE": "IMPORTS_BE", "NL": "IMPORTS_NL",
                  "NO": "IMPORTS_NO", "DK": "IMPORTS_DK", "IE": "IMPORTS_IE"}
COUNTRIES = list(COUNTRY_SOURCE)

# Each link's share of GB's 2025 interconnector imports (positive half-hourly
# flows, Elexon FUELHH, 1 Jan - 31 Dec 2025). The fallback when a window has
# no flow data, and the national weights a region without a fit uses.
LINK_IMPORT_SHARE_2025 = {
    "INTFR": 0.2424, "INTIFA2": 0.1362, "INTELEC": 0.1361, "INTNEM": 0.0852,
    "INTNED": 0.0662, "INTNSL": 0.2146, "INTVKL": 0.1082, "INTIRL": 0.0032,
    "INTEW": 0.0014, "INTGRNL": 0.0064,
}

# Per Carbon Intensity region: beta per link (normalised to sum 1), the fit's
# R2, and the region's 2025 annual import split by country (the fallback when
# a half-hour has no usable flow). Written by
# grid_build.fit_import_attribution() over 2025; a region absent here uses
# the national flows.
IMPORT_FIT_MIN_R2 = 0.15
IMPORT_FIT_MIN_SHARE_PERC = 2.0
IMPORT_ATTRIBUTION: dict = {3: {'beta': {'INTIFA2': 0.0548,
              'INTELEC': 0.0533,
              'INTNEM': 0.0478,
              'INTNED': 0.0362,
              'INTNSL': 0.8078},
     'r2': 0.56,
     'annual': {'FR': 0.0757, 'BE': 0.021, 'NL': 0.0123, 'NO': 0.891, 'DK': 0.0, 'IE': 0.0}},
 4: {'beta': {'INTFR': 0.041,
              'INTIFA2': 0.0052,
              'INTELEC': 0.0834,
              'INTNEM': 0.0208,
              'INTNED': 0.0067,
              'INTNSL': 0.8429},
     'r2': 0.695,
     'annual': {'FR': 0.1073, 'BE': 0.0086, 'NL': 0.0022, 'NO': 0.8819, 'DK': 0.0, 'IE': 0.0}},
 5: {'beta': {'INTNSL': 0.3104,
              'INTVKL': 0.0046,
              'INTIRL': 0.3172,
              'INTEW': 0.0604,
              'INTGRNL': 0.3075},
     'r2': 0.199,
     'annual': {'FR': 0.0, 'BE': 0.0, 'NL': 0.0, 'NO': 0.9492, 'DK': 0.0071, 'IE': 0.0437}},
 6: {'beta': {'INTFR': 0.027,
              'INTELEC': 0.0716,
              'INTNED': 0.0125,
              'INTNSL': 0.3435,
              'INTEW': 0.5454},
     'r2': 0.296,
     'annual': {'FR': 0.1778, 'BE': 0.0, 'NL': 0.0091, 'NO': 0.805, 'DK': 0.0, 'IE': 0.0081}},
 8: {'beta': {'INTFR': 0.0868,
              'INTIFA2': 0.2248,
              'INTELEC': 0.0941,
              'INTNEM': 0.1511,
              'INTNED': 0.2675,
              'INTNSL': 0.1253,
              'INTIRL': 0.0504},
     'r2': 0.393,
     'annual': {'FR': 0.5279, 'BE': 0.1054, 'NL': 0.1452, 'NO': 0.2202, 'DK': 0.0, 'IE': 0.0013}},
 9: {'beta': {'INTFR': 0.0526,
              'INTIFA2': 0.0347,
              'INTELEC': 0.001,
              'INTNED': 0.172,
              'INTNSL': 0.0965,
              'INTVKL': 0.068,
              'INTIRL': 0.2782,
              'INTEW': 0.1544,
              'INTGRNL': 0.1425},
     'r2': 0.178,
     'annual': {'FR': 0.2981, 'BE': 0.0, 'NL': 0.1928, 'NO': 0.3504, 'DK': 0.1246, 'IE': 0.034}},
 10: {'beta': {'INTFR': 0.0612,
               'INTELEC': 0.0581,
               'INTNEM': 0.0871,
               'INTNED': 0.7009,
               'INTVKL': 0.0114,
               'INTEW': 0.0813},
      'r2': 0.685,
      'annual': {'FR': 0.2918, 'BE': 0.0952, 'NL': 0.5958, 'NO': 0.0, 'DK': 0.0158, 'IE': 0.0014}},
 11: {'beta': {'INTFR': 0.0623,
               'INTIFA2': 0.495,
               'INTELEC': 0.0864,
               'INTNEM': 0.0984,
               'INTNSL': 0.0582,
               'INTVKL': 0.0048,
               'INTIRL': 0.0637,
               'INTGRNL': 0.1312},
      'r2': 0.195,
      'annual': {'FR': 0.8077, 'BE': 0.0718, 'NL': 0.0, 'NO': 0.107, 'DK': 0.0044, 'IE': 0.009}},
 12: {'beta': {'INTFR': 0.155,
               'INTIFA2': 0.5407,
               'INTELEC': 0.0584,
               'INTNEM': 0.1706,
               'INTNED': 0.0215,
               'INTIRL': 0.02,
               'INTGRNL': 0.0337},
      'r2': 0.647,
      'annual': {'FR': 0.88, 'BE': 0.1073, 'NL': 0.0105, 'NO': 0.0, 'DK': 0.0, 'IE': 0.0021}},
 13: {'beta': {'INTFR': 0.3505,
               'INTIFA2': 0.0721,
               'INTELEC': 0.0681,
               'INTNEM': 0.2651,
               'INTNED': 0.1678,
               'INTNSL': 0.0133,
               'INTIRL': 0.063},
      'r2': 0.699,
      'annual': {'FR': 0.739, 'BE': 0.1604, 'NL': 0.079, 'NO': 0.0203, 'DK': 0.0, 'IE': 0.0014}},
 14: {'beta': {'INTFR': 0.4265,
               'INTIFA2': 0.059,
               'INTELEC': 0.1071,
               'INTNEM': 0.2509,
               'INTNSL': 0.0641,
               'INTVKL': 0.0047,
               'INTIRL': 0.0742,
               'INTGRNL': 0.0134},
      'r2': 0.713,
      'annual': {'FR': 0.778, 'BE': 0.132, 'NL': 0.0, 'NO': 0.0849, 'DK': 0.0031, 'IE': 0.002}}}

# =============================================================================
# 3. Pass-through storage
# =============================================================================
# ecoinvent's GB pumped storage takes 1.43 kWh from GB's high-voltage market
# per kWh returned (70 % round trip) and is 466 g/kWh because that market is
# its 2018 mix on the conventional gas plant. The electricity it returns was
# generated by this same grid, so it is scored as its own plant and reservoir
# (the dataset without its electricity input) plus 1.43 kWh of the half-hour's
# other generation. The API has reported storage as 0 % in every regional
# series built so far, so this is correctness, not a number that moves.
STORAGE_KWH_IN = 1.43       # transcribed; source_table() checks the dataset

TECH_SPECS = {
    "GAS":              {"row_key": "GAS"},
    "COAL":             {"row_key": "COAL"},
    "NUCLEAR":          {"row_key": "NUCLEAR"},
    "WIND_GT3_ONSHORE": {"row_key": "WIND"},
    "WIND_13_OFFSHORE": {"row_key": "WIND"},
    "WIND_13_ONSHORE":  {"row_key": "WIND"},
    "WIND_EMB":         {"row_key": "WIND_EMB"},
    "HYDRO":            {"row_key": "HYDRO"},
    **{COUNTRY_SOURCE[c]: {"row_key": "IMPORTS"} for c in COUNTRIES},
    "BIOMASS":          {"row_key": "BIOMASS"},
    "OTHER":            {"row_key": "OTHER"},
    "SOLAR":            {"row_key": "SOLAR"},
    "STORAGE":          {"row_key": "STORAGE"},
}
SIMPLE_TECH_KEYS = ["GAS", "COAL", "NUCLEAR", "WIND_EMB", "HYDRO",
                    "BIOMASS", "OTHER", "SOLAR"]
WIND_COMPONENT_KEYS   = ["WIND_GT3_ONSHORE", "WIND_13_OFFSHORE", "WIND_13_ONSHORE"]
IMPORT_COMPONENT_KEYS = [COUNTRY_SOURCE[c] for c in COUNTRIES]
# The share columns a grid CSV carries.
FUEL_COLS = ["GAS", "COAL", "NUCLEAR", "WIND", "WIND_EMB",
             "HYDRO", "IMPORTS", "BIOMASS", "OTHER", "SOLAR", "STORAGE"]
IMPORT_SHARE_COLS = [f"imp_{c}" for c in COUNTRIES]

if set(TECH_SPECS) != set(SOURCES):
    raise AssertionError("SOURCES and TECH_SPECS disagree on which sources exist")
if abs(sum(WIND_GROUP_WEIGHTS.values()) - 1.0) > 1e-9:
    raise AssertionError("wind weights must sum to one")
if abs(sum(LINK_IMPORT_SHARE_2025.values()) - 1.0) > 1e-3 or set(LINK_IMPORT_SHARE_2025) != set(LINKS):
    raise AssertionError("LINK_IMPORT_SHARE_2025 must cover every link and sum to one")


def link_weights(region: int | None) -> dict:
    """beta per link for a region: its fit, or every link equally (national)."""
    fit = IMPORT_ATTRIBUTION.get(int(region)) if region is not None else None
    return dict(fit["beta"]) if fit else {link: 1.0 for link in LINKS}


def _by_country(per_link: dict) -> dict:
    out = {c: 0.0 for c in COUNTRIES}
    for link, v in per_link.items():
        out[INTERCONNECTORS[link][1]] += v
    total = sum(out.values())
    return {c: v / total for c, v in out.items()} if total > 0 else {}


def annual_import_shares(region: int | None) -> dict:
    """``{country: share}`` of a region's imports over 2025. The fallback for a
    half-hour with no flow data or no import flowing on its links."""
    fit = IMPORT_ATTRIBUTION.get(int(region)) if region is not None else None
    if fit:
        return dict(fit["annual"])
    return _by_country(LINK_IMPORT_SHARE_2025)


def import_shares(region: int | None, import_flow_mw: dict | None) -> tuple[dict, str]:
    """``({country: share}, basis)`` of a region's imports in one half-hour.

    ``import_flow_mw`` is each link's flow, positive into GB; exports count as
    zero. ``basis`` is ``"flows"`` when the half-hour's flows decided it and
    ``"annual"`` when they could not (no data, or nothing flowing in on the
    region's links).
    """
    if import_flow_mw:
        beta = link_weights(region)
        weighted = {k: beta.get(k, 0.0) * max(float(import_flow_mw.get(k, 0.0) or 0.0), 0.0)
                    for k in LINKS}
        shares = _by_country(weighted)
        if shares:
            return shares, "flows"
    return annual_import_shares(region), "annual"


# =============================================================================
# 4. The closed-form score
# =============================================================================
def score_row(csv_row, source_scores: dict) -> float:
    """kg CO2e per kWh *generated* for one half-hour: Σ share × source score.

    ``csv_row`` carries ``<row_key>_perc`` columns in percent and, for imports,
    ``imp_<CC>`` country shares (else the region's 2025 split is used, from
    ``api_region_id``). ``source_scores`` is ``{source key: kg CO2e/kWh}``,
    with STORAGE scored without its electricity input. Losses and network
    are not here — see ``delivered``.
    """
    def perc(key):
        return float(csv_row.get(key + "_perc", 0) or 0) / 100.0

    score = share_sum = 0.0
    for tech_key in SIMPLE_TECH_KEYS:
        share = perc(TECH_SPECS[tech_key]["row_key"])
        if share > 0:
            score += share * source_scores[tech_key]
            share_sum += share

    wind_total = perc("WIND")
    if wind_total > 0:
        for tech_key in WIND_COMPONENT_KEYS:
            score += wind_total * WIND_GROUP_WEIGHTS[tech_key] * source_scores[tech_key]
        share_sum += wind_total

    imports_total = perc("IMPORTS")
    if imports_total > 0:
        recorded = {c: csv_row.get(f"imp_{c}") for c in COUNTRIES}
        if all(v is not None and v == v for v in recorded.values()) and sum(recorded.values()) > 0:
            split = {c: float(v) for c, v in recorded.items()}
        else:
            region = csv_row.get("api_region_id")
            split = annual_import_shares(None if region is None or region != region else region)
        for c, w in split.items():
            score += imports_total * w * source_scores[COUNTRY_SOURCE[c]]
        share_sum += imports_total

    storage = perc("STORAGE")
    if storage > 0:
        rest_per_kwh = score / share_sum if share_sum > 0 else 0.0
        score += storage * (source_scores["STORAGE"] + STORAGE_KWH_IN * rest_per_kwh)

    return score


# =============================================================================
# 5. Delivery over the network
# =============================================================================
# Taking a kWh at a given voltage costs two things ecoinvent separates from
# generation: the losses on the way down (a gross-up on the generation mix)
# and the network's own embodied carbon. Derived from ecoinvent 3.9.1 apos's
# GB markets and voltage transformations by check_delivery(), which walks the
# chain HV market -> HV/MV transformer -> MV market -> MV/LV -> LV market:
#
#   gross_up   kWh generated per kWh delivered. Each market loses its own
#              self-input (HV 3.27 %, MV 0.44 %, LV 3.13 % per kWh out) and
#              each transformer its excess input (HV/MV 0.68 %, MV/LV 3.16 %).
#   network    g CO2e per kWh delivered: every activity in the chain with its
#              electricity inputs removed — the lines, cables, transformers,
#              their maintenance, SF6 leakage, and the N2O the high-voltage
#              market emits from corona discharge (5.0e-6 kg/kWh, 1.37 g of
#              the 1.93) — times its throughput.
#
#              voltage   gross-up   network g/kWh
#              high      1.033799   1.932
#              medium    1.045414   4.893
#              low       1.113247  11.296
#
# The chain treats all supply as entering at high voltage. ecoinvent itself
# injects a little at lower voltages (MV waste incineration, LV rooftop PV);
# the API mix already counts that generation, and routing it through the
# upper levels overstates the medium and low voltage gross-up by well under
# 1 %.
#
# Voltage bands are ecoinvent's: high > 24 kV, medium 1-24 kV, low < 1 kV.
# A data centre's voltage follows its connection (network_charges.
# delivery_voltage); a bought-hydrogen seller's is h2_prices.
# GREEN_H2_SELLER_VOLTAGE. The same constants serve both, which is the point.
#
# Until 13 Oct 2026 the grid series carried a flat 3.16 % (MARKET_LOSS_SHARE)
# and no network carbon, while bought green hydrogen paid low-voltage delivery
# — 6.35 % and 8.2125 g/kWh, the gross-up undercounted because CHP and import
# kWh were left out of "generation", and the network missing the N2O and the
# direct SF6. A data centre is not a low-voltage customer, and neither is a
# grid-connected electrolyser.
VOLTAGES = ("high", "medium", "low")
DELIVERY = {
    "high":   {"gross_up": 1.03379915593905,   "network_gco2e_per_kwh": 1.9318200445737765},
    "medium": {"gross_up": 1.045413872956057,  "network_gco2e_per_kwh": 4.893252997861607},
    "low":    {"gross_up": 1.1132474252952393, "network_gco2e_per_kwh": 11.295551508863387},
}
REFERENCE_VOLTAGE = "high"
# ecoinvent's own GB low-voltage market, kept for provenance: it is the grid
# figure the old bought-green row used, and must not be selectable as a basis.
GB_LV_MARKET_GCO2E_PER_KWH = 311.21970194853005

_CHAIN = (
    ("high",   "market for electricity, high voltage", None),
    ("medium", "market for electricity, medium voltage",
     "electricity voltage transformation from high to medium voltage"),
    ("low",    "market for electricity, low voltage",
     "electricity voltage transformation from medium to low voltage"),
)


def delivery(voltage: str) -> dict:
    """``{"gross_up", "network_gco2e_per_kwh"}`` at one voltage."""
    if voltage not in DELIVERY:
        raise ValueError(f"voltage must be one of {VOLTAGES}, got {voltage!r}")
    return dict(DELIVERY[voltage])


def delivered(generation_kgco2e_per_kwh, voltage: str = REFERENCE_VOLTAGE):
    """kg CO2e per kWh delivered at ``voltage``, from per kWh generated.
    Works on a float or an array."""
    d = delivery(voltage)
    return generation_kgco2e_per_kwh * d["gross_up"] + d["network_gco2e_per_kwh"] / 1000.0


def derive_delivery() -> dict:
    """Walk ecoinvent's GB voltage chain and return ``DELIVERY`` as it should
    be. Needs the Brightway project."""
    import lca_helpers as H
    H.setup_brightway()

    def kwh_inputs(act):
        return [(e.input, float(e["amount"])) for e in act.exchanges()
                if H.is_any_electricity_exchange(e)]

    out, upper = {}, None
    for voltage, market_name, transformer_name in _CHAIN:
        market = H.resolve_exact(market_name, "GB")
        self_loss = sum(a for inp, a in kwh_inputs(market) if inp.key == market.key)
        throughput = 1.0 / (1.0 - self_loss)          # market kWh per kWh out
        network = throughput * H.run_non_electricity_lca(market)[0]
        if transformer_name is None:
            gross_up = throughput
        else:
            tx = H.resolve_exact(transformer_name, "GB")
            t_in = sum(a for _inp, a in kwh_inputs(tx))
            network += throughput * H.run_non_electricity_lca(tx)[0]
            gross_up = throughput * t_in * upper["gross_up"]
            network += throughput * t_in * upper["network_gco2e_per_kwh"] / 1000.0
        upper = {"gross_up": gross_up, "network_gco2e_per_kwh": network * 1000.0}
        out[voltage] = dict(upper)
    return out


def check_delivery(tol_frac: float = 0.01) -> dict:
    """Re-derive ``DELIVERY`` from the live database and fail if it has drifted."""
    live = derive_delivery()
    problems = []
    for v in VOLTAGES:
        for key in ("gross_up", "network_gco2e_per_kwh"):
            const, got = DELIVERY[v][key], live[v][key]
            if const is None or abs(got - const) > tol_frac * abs(const):
                problems.append(f"{v} {key}: constant {const}, live {got:.6g}")
    if problems:
        raise AssertionError("Grid delivery constants have gone stale:\n  " + "\n  ".join(problems))
    return {"ok": True, **live}


# =============================================================================
# The basis id, and the scored table
# =============================================================================
def basis() -> dict:
    """Everything that moves a grid score, in the shape the id hashes."""
    from optimiser_lca import upv
    return {
        "sources": {k: list(v) for k, v in sorted(GRID_SOURCES.items())},
        "method": METHOD_LABEL,
        "wind": WIND_GROUP_WEIGHTS,
        "interconnectors": {k: v[1] for k, v in INTERCONNECTORS.items()},
        "link_share_2025": LINK_IMPORT_SHARE_2025,
        "import_attribution": {str(k): v for k, v in sorted(IMPORT_ATTRIBUTION.items())},
        "storage_kwh_in": STORAGE_KWH_IN,
        "solar_fleet": [upv.UPV_GRID_FLEET_KWH_PER_KWP, upv.UPV_GRID_FLEET_YEARS],
        "delivery": DELIVERY,
        "reference_voltage": REFERENCE_VOLTAGE,
    }


def sources_id() -> str:
    """Short, stable id of ``basis()``. No Brightway needed. Every grid CSV
    records it, and a series scored on another basis is ignored."""
    canon = json.dumps(basis(), sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12]


_TABLE = None


def source_table(refresh: bool = False) -> dict:
    """``{key: {name, location, product, database, kgco2e_per_kwh}}``, every
    source resolved exactly and scored once. STORAGE is scored without its
    electricity input. Needs the Brightway project."""
    global _TABLE
    if _TABLE is not None and not refresh:
        return _TABLE
    import lca_helpers as H
    _ei, _bio, _fg, method = H.setup_brightway()
    picked = {k: H.resolve_exact(*p.identity, database=p.database) for k, p in SOURCES.items()}
    scores = H.calculate_source_lca_scores(
        {k: a for k, a in picked.items() if k != "STORAGE"}, method)
    storage, kwh_in, _n = H.run_non_electricity_lca(picked["STORAGE"], method)
    if abs(kwh_in - STORAGE_KWH_IN) > 1e-9:
        raise AssertionError(f"pumped storage takes {kwh_in} kWh, not STORAGE_KWH_IN={STORAGE_KWH_IN}")
    scores["STORAGE"] = storage
    failed = set(picked) - set(scores)
    if failed:
        raise RuntimeError(f"Scoring failed for {sorted(failed)}; see above.")
    _TABLE = {k: {"name": a["name"], "location": a["location"],
                  "product": a.get("reference product"),
                  "database": SOURCES[k].database or H.ecoinvent_name(),
                  "kgco2e_per_kwh": scores[k]}
              for k, a in picked.items()}
    return _TABLE


def source_scores() -> dict:
    return {k: v["kgco2e_per_kwh"] for k, v in source_table().items()}


# =============================================================================
# Reading it
# =============================================================================
def show(candidates: bool = False):
    """The grid LCA on one screen: every source with its score, the import
    attribution, the delivery terms, and one worked half-hour."""
    import pandas as pd
    table = source_table()
    rows = []
    for k, p in SOURCES.items():
        t = table[k]
        rows.append({"source": k, "api_row": TECH_SPECS[k]["row_key"],
                     "g_co2e_per_kwh": t["kgco2e_per_kwh"] * 1000.0,
                     "activity": t["name"], "location": t["location"], "why": p.why})
    df = pd.DataFrame(rows)
    print(f"Grid basis {sources_id()}, scored with {METHOD_LABEL}")
    with pd.option_context("display.width", 220, "display.max_colwidth", 70):
        print(df.to_string(index=False))
    print("\nImport attribution by region (beta per link, R2):")
    for region in range(1, 15):
        fit = IMPORT_ATTRIBUTION.get(region)
        split = annual_import_shares(region)
        tag = f"R2 {fit['r2']:.2f}" if fit else "national flows"
        print(f"  {region:>2}  {tag:<15} 2025: " +
              ", ".join(f"{c} {s:.0%}" for c, s in split.items() if s >= 0.005))
    print("\nDelivery (per kWh delivered):")
    for v in VOLTAGES:
        d = DELIVERY[v]
        print(f"  {v:<6} x{d['gross_up']:.6f} generation + {d['network_gco2e_per_kwh']:.4f} g network")
    example = {"GAS_perc": 40.0, "WIND_perc": 30.0, "NUCLEAR_perc": 15.0, "IMPORTS_perc": 10.0,
               "SOLAR_perc": 5.0, "api_region_id": 13}
    g = score_row(example, source_scores())
    print(f"\nWorked London half-hour {example}: {g * 1000:.1f} g/kWh generated, "
          f"{delivered(g) * 1000:.1f} g/kWh delivered at high voltage.")
    if candidates:
        import lca_helpers as H
        for k, p in SOURCES.items():
            if p.query is None:
                continue
            print("\n" + "=" * 96)
            print(f"{k}: {p.query}")
            for i, act in enumerate(list(H.ei.search(p.query))[:8]):
                mark = "->" if (act["name"], act["location"], act.get("reference product")) == p.identity else "  "
                print(f"  {mark}{i:>3} | {act['name']} | {act.get('reference product')} | {act['location']}")
    return df
