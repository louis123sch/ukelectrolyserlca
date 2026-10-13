"""
GB grid carbon — the whole LCA, in one place.
=============================================================================

The optimiser's grid carbon is a half-hourly series built by
``optimisation/grid_build.py`` from the NESO Carbon Intensity API's regional
generation mix. This module is everything *LCA* about that series:

1. **Sources** — the one ecoinvent activity that scores each API fuel, named
   by exact identity (name, location, reference product). ``SOURCES`` is the
   only place the grid's processes are chosen; grid_build resolves each by
   exact match and refuses zero or several hits. It used to be a search query
   plus a hit index, and ``"GAS": 3`` silently landed on the conventional
   plant (558 g/kWh) though the query asked for combined cycle (387) — about
   12–21 % on every grid series. That is why nothing here is a search rank.
2. **Composites** — the API reports wind and imports as single figures;
   each is split across ecoinvent sub-technologies by the fixed weights below,
   taken from the shares inside ecoinvent's own GB high-voltage market.
3. **Losses** — every kWh delivered needs ``MARKET_LOSS_FACTOR`` kWh
   generated, applied to the whole mix, so the score is per kWh *delivered*.
4. **The closed-form score** — ``score_row`` = Σ share × loss × source score.
5. **Delivery over the network** — the loss gross-up and network embodied
   carbon that separate electricity taken over the grid from electricity
   taken off a generator's terminals. ``h2_prices`` charges bought green
   hydrogen with these; the grid series itself is generation only (see the
   TODO entry on network embodied carbon).

Every grid CSV records ``sources_id()`` — a hash of the identities — and the
sources with their scores in a ``.sources.json`` beside it, so a series can
always say what scored it. ``profiles`` ignores a series scored on a different
table. Editing a source here therefore makes every series stale;
``python -m optimisation.grid_build --rescore`` brings them back from the fuel
mix each file already holds, with no API calls.

Method
------
The sources are scored with ``lca_helpers.method``, which on ecoinvent 3.9.1's
bundled methods is **IPCC 2021 GWP100, "no LT"** (no long-term emissions).
The coefficient modules in ``optimisation/`` score assets on the with-LT
variant. The difference is small for electricity generation but it is a
known inconsistency; it is left as is because changing it stales every
series on disk, and it is registered in DATA_GAPS.md.
"""
from __future__ import annotations

import hashlib
import json

from optimiser_lca.common import Process

# =============================================================================
# 1. Sources — one ecoinvent activity per Carbon Intensity API fuel
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
    # Imports (composite, split by IMPORT_GROUP_WEIGHTS). Located GB: the
    # import into GB, not another country's import from the same place.
    "IMPORTS_FR": Process(
        identity=("electricity, high voltage, import from FR", "GB", "electricity, high voltage"),
        query="electricity high voltage import from FR GB"),
    "IMPORTS_IE": Process(
        identity=("electricity, high voltage, import from IE", "GB", "electricity, high voltage"),
        query="electricity high voltage import from IE GB"),
    "IMPORTS_NL": Process(
        identity=("electricity, high voltage, import from NL", "GB", "electricity, high voltage"),
        query="electricity high voltage import from NL GB"),
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
        identity=("electricity production, photovoltaic, 570kWp open ground installation, multi-Si",
                  "GB", "electricity, low voltage"),
        query="electricity production photovoltaic 570kWp open ground GB",
        why="the 2008 El Tesoro plant this study rejects for its OWN solar (see "
            "renewables.py). Kept for the grid's small solar share for now; a known "
            "inconsistency, registered in DATA_GAPS.md"),
    "STORAGE": Process(
        identity=("electricity production, hydro, pumped storage", "GB", "electricity, high voltage"),
        query="electricity production hydro pumped storage GB"),
}

# The identities alone, in the shape grid_build hashes and the sidecars record.
GRID_SOURCES = {k: p.identity for k, p in SOURCES.items()}

# =============================================================================
# 2. Composites — the API's single wind and imports figures, split
# =============================================================================
# Shares inside ecoinvent 3.9.1's GB high-voltage market, normalised within
# each group. Transcribed from the market's own exchange amounts.
WIND_GROUP_WEIGHTS = {
    "WIND_GT3_ONSHORE": 0.006725107846 / 0.157504068947,
    "WIND_13_OFFSHORE": 0.05505783324  / 0.157504068947,
    "WIND_13_ONSHORE":  0.095721127861 / 0.157504068947,
}
IMPORT_GROUP_WEIGHTS = {
    "IMPORTS_FR": 0.050547023864 / 0.080275563773,
    "IMPORTS_IE": 0.005823079527 / 0.080275563773,
    "IMPORTS_NL": 0.023905460382 / 0.080275563773,
}

# Which API row (``<row_key>_perc`` column) each scored source belongs to.
TECH_SPECS = {
    "GAS":              {"row_key": "GAS"},
    "COAL":             {"row_key": "COAL"},
    "NUCLEAR":          {"row_key": "NUCLEAR"},
    "WIND_GT3_ONSHORE": {"row_key": "WIND"},
    "WIND_13_OFFSHORE": {"row_key": "WIND"},
    "WIND_13_ONSHORE":  {"row_key": "WIND"},
    "WIND_EMB":         {"row_key": "WIND_EMB"},
    "HYDRO":            {"row_key": "HYDRO"},
    "IMPORTS_FR":       {"row_key": "IMPORTS"},
    "IMPORTS_IE":       {"row_key": "IMPORTS"},
    "IMPORTS_NL":       {"row_key": "IMPORTS"},
    "BIOMASS":          {"row_key": "BIOMASS"},
    "OTHER":            {"row_key": "OTHER"},
    "SOLAR":            {"row_key": "SOLAR"},
    "STORAGE":          {"row_key": "STORAGE"},
}
SIMPLE_TECH_KEYS = ["GAS", "COAL", "NUCLEAR", "WIND_EMB", "HYDRO",
                    "BIOMASS", "OTHER", "SOLAR", "STORAGE"]
WIND_COMPONENT_KEYS   = ["WIND_GT3_ONSHORE", "WIND_13_OFFSHORE", "WIND_13_ONSHORE"]
IMPORT_COMPONENT_KEYS = ["IMPORTS_FR", "IMPORTS_IE", "IMPORTS_NL"]
# The share columns a grid CSV carries.
FUEL_COLS = ["GAS", "COAL", "NUCLEAR", "WIND", "WIND_EMB",
             "HYDRO", "IMPORTS", "BIOMASS", "OTHER", "SOLAR", "STORAGE"]

if set(TECH_SPECS) != set(SOURCES):
    raise AssertionError("SOURCES and TECH_SPECS disagree on which sources exist")
if abs(sum(WIND_GROUP_WEIGHTS.values()) - 1.0) > 1e-9 or abs(sum(IMPORT_GROUP_WEIGHTS.values()) - 1.0) > 1e-9:
    raise AssertionError("composite weights must sum to one")

# =============================================================================
# 3. Losses
# =============================================================================
# Transmission and distribution losses: every kWh delivered needs this much
# more generated. Applied to the whole mix, so grid carbon is per kWh delivered.
APPLY_LOSSES      = True
MARKET_LOSS_SHARE = 0.031642692177          # ecoinvent GB market, transcribed
MARKET_LOSS_FACTOR = (1.0 + MARKET_LOSS_SHARE) if APPLY_LOSSES else 1.0


# =============================================================================
# 4. The closed-form score
# =============================================================================
def score_row(csv_row, source_scores: dict) -> tuple[float, float]:
    """kg CO2e per kWh delivered for one half-hour, and the kWh generated per
    kWh delivered that it took. ``csv_row`` carries ``<row_key>_perc`` columns
    in percent; ``source_scores`` is ``{source key: kg CO2e/kWh}``."""
    score = 0.0
    amount_sum = 0.0
    lf = MARKET_LOSS_FACTOR

    for tech_key in SIMPLE_TECH_KEYS:
        if tech_key not in source_scores:
            continue
        share = float(csv_row.get(TECH_SPECS[tech_key]["row_key"] + "_perc", 0) or 0) / 100.0
        if share <= 0:
            continue
        amount = share * lf
        score += amount * source_scores[tech_key]
        amount_sum += amount

    wind_total = float(csv_row.get("WIND_perc", 0) or 0) / 100.0
    if wind_total > 0:
        for tech_key in WIND_COMPONENT_KEYS:
            if tech_key not in source_scores:
                continue
            amount = wind_total * WIND_GROUP_WEIGHTS[tech_key] * lf
            score += amount * source_scores[tech_key]
            amount_sum += amount

    imports_total = float(csv_row.get("IMPORTS_perc", 0) or 0) / 100.0
    if imports_total > 0:
        for tech_key in IMPORT_COMPONENT_KEYS:
            if tech_key not in source_scores:
                continue
            amount = imports_total * IMPORT_GROUP_WEIGHTS[tech_key] * lf
            score += amount * source_scores[tech_key]
            amount_sum += amount

    return score, amount_sum


def sources_id() -> str:
    """Short, stable id of ``GRID_SOURCES``. No Brightway needed. Every grid
    CSV records it, and a series scored on another table is ignored."""
    canon = json.dumps({k: list(v) for k, v in sorted(GRID_SOURCES.items())}, sort_keys=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:12]


_TABLE = None


def source_table(refresh: bool = False) -> dict:
    """``{key: {name, location, product, kgco2e_per_kwh}}``, every source
    resolved exactly and scored once. Needs the Brightway project."""
    global _TABLE
    if _TABLE is not None and not refresh:
        return _TABLE
    import lca_helpers as H
    _ei, _bio, _fg, method = H.setup_brightway()
    picked = {k: H.resolve_exact(*p.identity) for k, p in SOURCES.items()}
    scores = H.calculate_source_lca_scores(picked, method)
    failed = set(picked) - set(scores)
    if failed:
        raise RuntimeError(f"Scoring failed for {sorted(failed)}; see above.")
    _TABLE = {k: {"name": a["name"], "location": a["location"],
                  "product": a.get("reference product"), "kgco2e_per_kwh": scores[k]}
              for k, a in picked.items()}
    return _TABLE


def source_scores() -> dict:
    return {k: v["kgco2e_per_kwh"] for k, v in source_table().items()}


# =============================================================================
# 5. Delivery over the network
# =============================================================================
# Reaching an electrolyser (or anything) over the grid is not free, and the
# two terms that make it costly are ones ecoinvent separates from generation:
#
#   losses   1.063495 kWh must be generated per kWh delivered at low voltage,
#            a 6.35 % gross-up, accumulated over the HV -> MV -> LV chain.
#   network  8.2125 g CO2e per kWh delivered, being the transmission and
#            distribution infrastructure: LV distribution 5.932, MV
#            transmission 1.583, HV transmission 0.655, network maintenance
#            0.019, SF6 switchgear leakage 0.025.
#
# Both derived from ecoinvent 3.9.1 apos's GB `market for electricity, low
# voltage` by contribution analysis; check_delivery() re-derives them live.
# The LV market's own total is kept for provenance: it is the grid figure the
# old bought-green row used, and it must not be selectable as a green basis.
DELIVERY_LOSS_GROSS_UP        = 1.063495
DELIVERY_NETWORK_GCO2E_PER_KWH = 8.2125
GB_LV_MARKET_GCO2E_PER_KWH    = 311.21970194853005


def check_delivery(tol_frac: float = 0.01) -> dict:
    """Re-derive the delivery constants from the live database and fail if
    they have drifted. Scored on the with-LT GWP100, as the hydrogen
    coefficients are."""
    import bw2calc as bc
    import bw2data as bd
    import lca_helpers as H
    from optimisation import electrolysers as ely

    H.setup_brightway()
    method = ely._gwp_method(bd)
    lv = H.resolve_exact("market for electricity, low voltage", "GB")
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
        if act.get("unit") == "kilowatt hour" and name.startswith("electricity production"):
            gen_kwh += amount
        elif name.startswith("market for") and (
                "network, electricity" in name
                or name.startswith("market for sulfur hexafluoride")):
            network += H.run_lca_score(act, method) * amount

    out = {"loss_gross_up": gen_kwh,
           "network_gco2e_per_kwh": network * 1000.0,
           "lv_market_gco2e_per_kwh": lca.score * 1000.0}
    problems = []
    for key, const in (("loss_gross_up", DELIVERY_LOSS_GROSS_UP),
                       ("network_gco2e_per_kwh", DELIVERY_NETWORK_GCO2E_PER_KWH),
                       ("lv_market_gco2e_per_kwh", GB_LV_MARKET_GCO2E_PER_KWH)):
        if abs(out[key] - const) > tol_frac * abs(const):
            problems.append(f"{key}: constant {const:.6g}, live {out[key]:.6g}")
    if problems:
        raise AssertionError("Grid delivery constants have gone stale:\n  "
                             + "\n  ".join(problems))
    out["ok"] = True
    return out


# =============================================================================
# Reading it
# =============================================================================
def show(candidates: bool = False):
    """The grid LCA on one screen: every source with its score, the composite
    splits, the loss factor, and one worked half-hour."""
    import pandas as pd
    import lca_helpers as H
    table = source_table()
    rows = []
    for k, p in SOURCES.items():
        t = table[k]
        rows.append({"source": k, "api_row": TECH_SPECS[k]["row_key"],
                     "weight_in_row": WIND_GROUP_WEIGHTS.get(k, IMPORT_GROUP_WEIGHTS.get(k, 1.0)),
                     "g_co2e_per_kwh": t["kgco2e_per_kwh"] * 1000.0,
                     "activity": t["name"], "location": t["location"], "why": p.why})
    df = pd.DataFrame(rows)
    print(f"Grid sources (id {sources_id()}), scored with {H.method}")
    with pd.option_context("display.width", 220, "display.max_colwidth", 70):
        print(df.to_string(index=False))
    print(f"\nLoss factor {MARKET_LOSS_FACTOR:.6f} on every kWh delivered"
          f" (losses {'applied' if APPLY_LOSSES else 'NOT applied'}).")
    print(f"Delivery over the network (bought green H2 only): x{DELIVERY_LOSS_GROSS_UP} "
          f"loss gross-up + {DELIVERY_NETWORK_GCO2E_PER_KWH} g/kWh network.")
    example = {"GAS_perc": 40.0, "WIND_perc": 30.0, "NUCLEAR_perc": 15.0, "IMPORTS_perc": 10.0,
               "SOLAR_perc": 5.0}
    s, a = score_row(example, source_scores())
    print(f"\nWorked half-hour {example}: {s * 1000:.1f} g CO2e/kWh delivered, "
          f"{a:.4f} kWh generated per kWh delivered.")
    if candidates:
        for k, p in SOURCES.items():
            print("\n" + "=" * 96)
            print(f"{k}: {p.query}")
            for i, act in enumerate(list(H.ei.search(p.query))[:8]):
                mark = "->" if (act["name"], act["location"], act.get("reference product")) == p.identity else "  "
                print(f"  {mark}{i:>3} | {act['name']} | {act.get('reference product')} | {act['location']}")
    return df
