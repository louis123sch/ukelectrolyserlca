"""
Consistency audit — do the model's own parts agree with each other?
=============================================================================

``validate.py`` asks whether the answers agree with things established outside
the LP. This module asks something narrower and, so far, more productive: where
two parts of the model describe the *same physical fact*, do they agree?

Every defect found this way shares a shape. Nothing is wrong in isolation; two
things that were set independently have drifted apart, and the model quietly
believes both. None of them fails a benchmark, because each produces a
confident, plausible number.

* **The site was two different sites at once.** It paid a T-Demand TNUoS
  residual, which is levied on transmission-connected final demand, *and* a
  Distribution Use of System charge, which is levied on users of the
  distribution network. It cannot be both.
* **The band contradicted the load.** ``tdr_band`` was pinned at ``EHV2`` —
  5 to 12 MVA, correct for the study's 7.31 MW reference data centre — while
  the site drew 868 MW.
* **The two objectives described different assets.** ``cap_grid`` carried a
  connection charge in ``cost`` and nothing at all in ``gwp``, so each objective
  was optimising a system the other could not see.
* **The two objectives described different physics.** A fuel cell run hard
  incurs extra stack replacements. ``gwp`` counts them; ``cost`` amortises the
  capital over calendar life alone and charges nothing for duty.

The checks below are structural, so they hold for kit nobody has added yet. Most
need no solve.

Run:  python optimisation/audit.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimisation import dc_model as M

# A capacity may legitimately carry no embodied carbon only if it is not a
# physical asset. Nothing currently qualifies, which is the point: the entry
# exists so that adding one is a deliberate, reviewed act rather than an
# omission nobody notices.
CARBON_EXEMPT: dict[str, str] = {}

# Some capacities carry their carbon through another variable rather than
# directly. The fuel cell is sized by cap_fc, but its embodied burden is charged
# on fc_bop_units and fc_stack_units — the convex max(calendar, duty)
# replacement counts, which constraints tie back to cap_fc. Reading only direct
# coefficients would report a carbon-free fuel cell, which is false.
CARBON_VIA: dict[str, tuple[str, ...]] = {
    "cap_fc": ("fc_bop_units", "fc_stack_units"),
}

# How hard an asset is run can reach an objective through a linked variable
# rather than the flow itself. The fuel cell's replacement counts are tied to
# p_fc by the convex max(calendar, duty) constraints, so an objective that
# charges fc_stack_units *is* charging duty — which is precisely how the cost
# side was fixed. Reading only the flow's own coefficient would still call that
# asymmetric.
DUTY_VIA: dict[str, tuple[str, ...]] = {
    "p_fc": ("fc_bop_units", "fc_stack_units"),
}

# Capacities whose flow the model bounds *directly* (flow <= capacity), so
# capacity above the peak flow is genuine slack. Deliberately excludes wind,
# solar and offshore: those are bounded by cf[t] x capacity, so a peak far below
# the nameplate is the capacity factor doing its job, not padding.
DIRECT_BOUND: dict[str, tuple[str, ...]] = {
    "cap_grid": ("imp",),
    "cap_batt_p": ("ch", "dis"),
    "cap_ely": ("p_ely",),
    "cap_fc": ("p_fc",),
}

# Variables that are accounting devices rather than kit, so an objective may
# reasonably ignore them.
NOT_ASSETS = {"unserved", "fc_bop_units", "fc_stack_units", "soc", "tank",
              "exp", "imp", "ch", "dis", "h2_fc", "h2_buy", "h2_buy_2",
              "p_wind", "p_offshore", "p_solar", "p_ely", "p_fc"}


# Findings that are real, understood, and not defects of plumbing — a missing
# input that cannot be sourced, or a limitation the study states elsewhere.
# Accepting one here is a deliberate act with a reason attached, and the reason
# is printed, so an accepted finding stays visible without recurring as an
# unexplained warning. Anything NOT in here is unaccounted for and needs work.
#
# Keyed "check:what". Delete an entry and the finding comes back.
ACCEPTED: dict[str, str] = {
    "coverage:p_ely moves carbon but not cost (cap_ely)":
        "Electrolyser consumables — water and heat — are charged in carbon and "
        "not in cost, because no price for either is sourced in this study. It "
        "is material and one-directional for SOEC, which draws 18.864 MJ "
        "(5.24 kWh) of external heat per kg of hydrogen and 0.65 m3 of water, "
        "against PEM's 0.28 kWh and 0.10 m3. SOEC's electricity advantage over "
        "PEM is 21.7 %; on total energy it is 12.4 %. Pricing the heat would "
        "narrow it further. See DATA_GAPS.md.",
    "coverage:cap_grid carries carbon but is free in cost":
        "The same fact as the applicability finding below, seen from the "
        "objective side, and correct rather than a hole: a transmission-"
        "connected demand site in a floored TNUoS zone genuinely pays £0.00/kW "
        "of zonal tariff, and the bilateral connection charge for sole-use "
        "assets is not a published £/MW tariff. The check's usual worry — that "
        "a cost-only solve builds it without limit — is real but handled, and "
        "the connection ceiling alone was NOT enough: measured across 14 "
        "regions, min_cost pinned cap_grid at the 180 MW ceiling against a "
        "120 MW load in exactly the seven floored TNUoS zones. Both anchors now "
        "run the lexicographic tie-break in dc_pareto, so the reported "
        "connection is the smallest that is optimal on both objectives.",
    "applicability:the connection costs £0/MW/year":
        "Correct as a tariff, not a hole. A transmission-connected demand site "
        "pays the zonal HH demand tariff plus the TDR, both modelled, and NESO's "
        "local substation tariffs are generation charges that do not apply. The "
        "zonal tariff is genuinely £0.00/kW in a floored zone. What is missing "
        "is the bilateral connection charge for sole-use assets, which is not a "
        "published £/MW tariff and cannot be transcribed. cap_grid is no longer "
        "degenerate regardless, because grid_connection.py gives it carbon.",
    "geography:fuel cell capex is not GB-sourced":
        "DOE, for natural-gas systems including a reformer this study does not "
        "have, so biased high. Stated in h2_capex.py and DATA_GAPS.md; no UK "
        "source exists for stationary fuel cell capital.",
    "geography:data centre foreground is not GB-sourced":
        "Zhang et al.'s Virginia facility is the study's own subject. Its "
        "electricity is swapped for the GB half-hourly mix — that swap is what "
        "baseline_grid.py exists to do and is validated to 1e-4 %. The "
        "remaining non-electricity burden is US-built and constant across every "
        "architecture, so it shifts all results equally and changes no ranking.",
    "geography:PV embodied carbon is not GB-sourced":
        "ecoinvent's GB open-ground PV activity is a 2008 plant at a 12.95 % "
        "module, and is byte-identical in 3.10.1, so the database cannot fix "
        "it. Solar is therefore scored on IEA PVPS Task 12's 2023 update "
        "instead — European rather than GB, but their 976 kWh/kWp reference "
        "yield is within 10 % of the DESNZ GB load factor, so it transfers "
        "with no irradiance correction. No UK source exists; see DATA_GAPS.md. "
        "Pass solar_basis='ecoinvent' to get the old figure back.",
}


@dataclass
class Finding:
    check: str
    severity: str          # "error" | "warn" | "ok"
    what: str
    detail: str = ""


FINDINGS: list[Finding] = []


def report(check, severity, what, detail=""):
    reason = ACCEPTED.get(f"{check}:{what}")
    if reason and severity != "ok":
        severity, detail = "accepted", reason
    FINDINGS.append(Finding(check, severity, what, detail))
    mark = {"error": "FAIL", "warn": "WARN", "ok": "PASS",
            "accepted": "ACPT"}[severity]
    print(f"  [{mark}] {what}")
    if detail:
        print(f"         {detail}")


# =============================================================================
def _coeff_by_variable(model, expr) -> dict[str, float]:
    """Total |coefficient| each named variable carries in one objective.

    linopy stores an objective as flat arrays of variable *labels* and
    coefficients, so this maps labels back to the names the model was built
    with and sums the magnitudes. Summing |coeff| rather than coeff is
    deliberate: a variable that appears with +x and -x in different terms is
    still represented, and this asks only whether the objective can see it.
    """
    label_to_name = {}
    for name in model.variables:
        for lab in np.asarray(model.variables[name].labels).ravel():
            label_to_name[int(lab)] = name
    out: dict[str, float] = {}
    labs = np.asarray(expr.vars).ravel()
    coeffs = np.asarray(expr.coeffs).ravel()
    for lab, c in zip(labs, coeffs):
        if lab < 0:        # linopy's fill label for absent terms
            continue
        n = label_to_name.get(int(lab))
        if n is not None:
            out[n] = out.get(n, 0.0) + abs(float(c))
    return out


def check_objective_coverage(series, assets, tech):
    """Every asset a build can contain must be visible to both objectives.

    An asset priced in one and invisible to the other is not a modelling
    choice, it is a hole: the objective that cannot see it has no reason to
    size it, and the number reported is whatever the constraints happened to
    force. This is exactly how a 868 MW grid connection appeared under a
    carbon-only objective.
    """
    print("\n1. OBJECTIVE COVERAGE — is every asset visible to both objectives?")
    m, V, obj = M.build_model(series, assets, tech, objective="cost")
    cost = _coeff_by_variable(m, obj["cost"])
    gwp = _coeff_by_variable(m, obj["gwp"])

    caps = [n for n in V if n.startswith("cap_")]
    rows = []
    for n in sorted(caps):
        upper = float(np.asarray(m.variables[n].upper).ravel()[0])
        if upper == 0.0:
            continue                      # asset locked off for this build
        c = cost.get(n, 0.0)
        g = gwp.get(n, 0.0) + sum(gwp.get(v, 0.0) for v in CARBON_VIA.get(n, ()))
        rows.append((n, c, g))
        if c > 0 and g == 0 and n not in CARBON_EXEMPT:
            report("coverage", "error",
                   f"{n} is priced in cost but carries no carbon",
                   "A carbon-only solve cannot see it, so its size is set by the "
                   "constraints alone. Add an embodied-carbon coefficient, or "
                   "list it in CARBON_EXEMPT with a reason.")
        elif g > 0 and c == 0:
            report("coverage", "error",
                   f"{n} carries carbon but is free in cost",
                   "A cost-only solve will build it without limit.")
        elif c == 0 and g == 0:
            report("coverage", "error",
                   f"{n} has no coefficient in either objective",
                   "Nothing anywhere prefers a smaller one. Whatever size is "
                   "reported is an artefact of the solver's stopping vertex.")
    # Same question one level down. A capacity says how much kit exists; the
    # flow through it says how hard the kit is run. If one objective's total
    # moves with duty and the other's does not, the two are costing different
    # physics for the same machine — which is how a fuel cell came to incur
    # extra stack replacements in carbon and nothing at all in cost.
    from optimisation.dc_pareto import ENERGY_VARS
    for cap, flow in sorted(ENERGY_VARS.items()):
        if cap not in V or float(np.asarray(m.variables[cap].upper).ravel()[0]) == 0.0:
            continue
        via = DUTY_VIA.get(flow, ())
        c = cost.get(flow, 0.0) + sum(cost.get(v, 0.0) for v in via)
        g = gwp.get(flow, 0.0) + sum(gwp.get(v, 0.0) for v in via)
        if (c > 0) == (g > 0):
            continue
        dearer, cheaper = ("carbon", "cost") if g > 0 else ("cost", "carbon")
        report("coverage", "warn",
               f"{flow} moves {dearer} but not {cheaper} ({cap})",
               f"Running this asset harder changes its {dearer} and not its "
               f"{cheaper}, so the two objectives are charging different "
               f"physics for the same machine. Either both should carry the "
               f"duty term or neither should.")

    if not [f for f in FINDINGS if f.check == "coverage"]:
        report("coverage", "ok", f"all {len(rows)} live capacities are priced in both")
    return pd.DataFrame(rows, columns=["variable", "cost_coeff", "gwp_coeff"])


def check_degeneracy_and_slack(series, assets, tech, objective="gwp"):
    """After a solve, which capacities were free, and which are padded?

    Two symptoms of the same disease. A capacity with no coefficient in the
    objective being minimised is *unpinned* — any value the constraints allow is
    equally optimal. Slack is that seen from the other side: a capacity sitting
    above the peak flow it carries is larger than anything requires.
    """
    print(f"\n3. DEGENERACY AND SLACK — solving for {objective!r}")
    m, V, obj = M.build_model(series, assets, tech, objective=objective)
    M.solve(m)
    active = _coeff_by_variable(m, obj[objective])
    d = M.dispatch_frame(V, series)

    from optimisation.dc_pareto import ENERGY_VARS
    clean = True
    for cap, flow in sorted(ENERGY_VARS.items()):
        if cap not in V:
            continue
        size = float(V[cap].solution)
        if size <= 1e-6:
            continue
        bounds = DIRECT_BOUND.get(cap)
        peak = max(float(d[f].max()) for f in bounds) if bounds else float(d[flow].max())
        slack = (size - peak) if bounds else 0.0
        active_coeff = active.get(cap, 0.0) + sum(
            active.get(v, 0.0) for v in CARBON_VIA.get(cap, ()))
        if active_coeff == 0.0:
            clean = False
            report("degeneracy", "error",
                   f"{cap} = {size:,.2f} is unpinned under {objective!r}",
                   f"zero coefficient in the active objective; any value above "
                   f"the {peak:,.2f} peak of {flow} is equally optimal")
        elif not bounds:
            continue          # cf-bounded: nameplate above peak output is normal
        elif slack > max(size, 1.0) * 1e-6:
            clean = False
            report("degeneracy", "warn",
                   f"{cap} = {size:,.2f} exceeds its own peak flow by {slack:,.2f}",
                   f"peak {flow} is {peak:,.2f}; the excess is not required by "
                   f"any constraint")
    if clean:
        report("degeneracy", "ok", f"every sized capacity is pinned under {objective!r}")


def check_lifetime_agreement():
    """Cost and carbon must amortise the same asset over the same life.

    Nothing enforces this: the cost side takes its lifetime from the capex
    modules and the carbon side from the LCA modules, and they agree today only
    because both happen to say 25 years. If one moves, every £/tCO2e the study
    reports silently stops being a like-for-like comparison, and no benchmark
    would notice.
    """
    print("\n2. LIFETIME AGREEMENT — same asset, same life on both sides?")
    from optimisation import battery as batt, electrolysers as ely
    from optimisation import fuel_cell as fc, h2_capex as hc
    from optimisation import h2_storage as h2s, renewables as ren, tech_costs as tc

    emb = ren.apply_case(ren.decompose_all(), "central").set_index("technology")
    ann = tc.annualised_table()
    pairs = []
    for asset in ("onshore_wind", "offshore_wind", "solar_pv"):
        cost_life = float(ann[(ann.asset == asset) & (ann.case == "central")]
                          .iloc[0].lifetime_years)
        pairs.append((asset, cost_life, float(emb.loc[asset].study_lifetime_years)))

    ec = hc.electrolyser_costs()
    pairs.append(("electrolyser",
                  float(ec[ec.case == "central"].iloc[0].lifetime_years),
                  float(ely.PLANT_LIFETIME_YEARS)))
    tk = hc.tank_costs()
    tank_life = {r["design"]: r.get("lifetime_years") for r in h2s.decompose()}
    pairs.append(("h2_tank", float(tk[tk.case == "central"].iloc[0].lifetime_years),
                  float(next(iter(tank_life.values())))))
    pairs.append(("fuel_cell_bop",
                  float(hc.fuel_cell_costs().iloc[0].lifetime_years),
                  float(fc.decompose()["bop_calendar_lifetime_years"])))
    pairs.append(("battery", float(batt.ASSET_LIFE_YEARS),
                  float(batt.ASSET_LIFE_YEARS)))

    t = pd.DataFrame(pairs, columns=["asset", "cost_life_yr", "carbon_life_yr"])
    t["agree"] = np.isclose(t.cost_life_yr, t.carbon_life_yr)
    print(t.to_string(index=False))
    bad = t[~t.agree]
    if len(bad):
        for _, r in bad.iterrows():
            report("lifetime", "error",
                   f"{r.asset}: cost amortises over {r.cost_life_yr:g} yr, "
                   f"carbon over {r.carbon_life_yr:g} yr",
                   "Every £/tCO2e involving this asset compares two different "
                   "machines.")
    else:
        report("lifetime", "ok",
               f"all {len(t)} assets amortise over the same life on both sides")
    return t


def check_scale_response(site, start, end, sizes=(7.31, 50.0, 300.0)):
    """Which inputs move when the data centre does?

    An input that is identical at 7 MW and 300 MW is either genuinely
    size-independent or was set once for one site and never revisited. This
    cannot tell the two apart, so it prints the table and flags only the case
    that is unambiguously wrong: a *banded* input that never changes band.
    """
    print("\n4. SCALE RESPONSE — do size-dependent inputs actually move?")
    from optimisation import dc_inputs as I
    rows = []
    for mw in sizes:
        _, meta = I.build_series(site, start, end, mw, pue=1.2)
        c = meta["network_charges"]
        rows.append({
            "size_MW_IT": mw,
            "transmission": meta["transmission_connected"],
            "tdr_band": meta["tdr_band"],
            "capacity_GBP_per_MW_yr": meta["capacity_GBP_per_MW_year"],
            "fixed_GBP_per_yr": meta["fixed_GBP_per_year"],
            "duos_cap_GBP_per_MW_yr": c["duos_capacity_GBP_per_MW_year"],
        })
    t = pd.DataFrame(rows)
    print(t.to_string(index=False))
    if t.tdr_band.nunique() == 1 and len(sizes) > 1:
        report("scale", "error",
               f"tdr_band is {t.tdr_band.iloc[0]!r} at every size tested",
               f"{sizes[0]:g} MW to {sizes[-1]:g} MW is a 40x range across a "
               f"banded charge; a band that never moves is not being derived")
    else:
        report("scale", "ok",
               f"tdr_band moves across the range: "
               f"{' -> '.join(dict.fromkeys(t.tdr_band))}")
    return t


def check_applicability(site, start, end, size_mw_it=300.0, pue=1.2):
    """Is each transcribed input being used inside the conditions it came from?

    Provenance is not only *where a number came from* but *where it is allowed
    to be used*. A tariff transcribed for one licence area and one voltage is
    silently wrong everywhere else, and nothing in the number itself says so.
    """
    print("\n5. CONSISTENCY OF SITE AND TARIFF — is each input used where it is valid?")
    from optimisation import dc_inputs as I
    from optimisation import network_charges as nc
    from optimisation import sites as S

    s = S.get(site)
    _, meta = I.build_series(site, start, end, size_mw_it, pue=pue)
    c = meta["network_charges"]
    transmission = meta["transmission_connected"]

    # DUoS is a London Power Networks transcription. Anywhere else it is a proxy.
    if not transmission and c["duos_capacity_GBP_per_MW_year"] > 0:
        if s.tnuos_zone != nc.DUOS_SOURCE_ZONE:
            report("applicability", "warn",
                   f"DUoS is charged from {nc.DUOS_SOURCE_AREA} tariffs at a "
                   f"zone-{s.tnuos_zone} site ({s.name})",
                   "Only one licence area is transcribed, so a site outside it "
                   "is priced on the wrong DNO's tariff. See DATA_GAPS.md.")
        else:
            report("applicability", "ok",
                   f"DUoS licence area matches the site ({nc.DUOS_SOURCE_AREA})")
    elif transmission:
        if c["duos_capacity_GBP_per_MW_year"] or c["duos_mean_GBP_per_MWh"]:
            report("applicability", "error",
                   "a transmission-connected site is being charged DUoS",
                   "DUoS is levied under DCUSA on users of the distribution "
                   "network; a Bilateral Connection Agreement pays none of it.")
        else:
            report("applicability", "ok",
                   "transmission-connected site pays no DUoS, as it should")

    # The band and the tier must tell the same story.
    band = meta["tdr_band"]
    if transmission != band.startswith("T-Demand"):
        report("applicability", "error",
               f"tier and band disagree: transmission={transmission}, band={band}",
               "T-Demand bands are for transmission-connected final demand "
               "sites; LV/HV/EHV are for distribution-connected ones.")
    else:
        report("applicability", "ok", f"tier and band agree ({band})")

    # A per-MW connection cost of zero is a real tariff outcome and a missing cost.
    if meta["capacity_GBP_per_MW_year"] == 0.0:
        report("applicability", "warn",
               "the connection costs £0/MW/year",
               "True as a tariff — floored TNUoS zone, no DUoS — but the "
               "connection assets themselves are charged under the Connection "
               "Charging Methodology, which no module reads. Logged in "
               "DATA_GAPS.md; it is why dc_pareto needs a connection tie-break.")

    for note_key in ("connection_tier_note", "tdr_band_note"):
        if meta.get(note_key):
            report("applicability", "warn", f"{note_key}: {meta[note_key]}")


def check_geography(site, start, end, size_mw_it=300.0, pue=1.2):
    """Every input the run uses must describe the place the run is about.

    This is the failure the study is most exposed to, because nothing about a
    number says where it is allowed to be used. A tariff transcribed for one
    licence area, an ecoinvent activity for one country, a capex survey in one
    currency — each is correct at its source and silently wrong once the site
    moves. The UI makes it worse rather than better: a coordinate box invites
    the user to move the site while every regional input stays where it was.
    """
    print("\n6. GEOGRAPHY — does every input describe this site?")
    from optimisation import dc_inputs as I
    from optimisation import network_charges as nc
    from optimisation import sites as S

    s_ = S.get(site)
    _, meta = I.build_series(site, start, end, size_mw_it, pue=pue)
    rows = [
        ("wind / solar profile", f"lat {s_.lat:.4f}, lon {s_.lon:.4f}",
         "Renewables.ninja, queried on the coordinate", True),
        ("grid carbon intensity", f"region {s_.carbon_api_region} "
         f"({s_.region_name})", "Carbon Intensity API, regional", True),
        ("TNUoS locational", f"zone {s_.tnuos_zone}", "NESO zonal tariff", True),
        ("TNUoS residual (TDR)", meta["tdr_band"], "national, banded", True),
        ("BSUoS", "GB-wide", "single national rate", True),
        ("wholesale price", "GB-wide", "Elexon, national", True),
    ]
    if meta["transmission_connected"]:
        rows.append(("DUoS", "not charged", "transmission connection", True))
    else:
        ok = s_.tnuos_zone == nc.DUOS_SOURCE_ZONE
        rows.append(("DUoS", nc.DUOS_SOURCE_AREA,
                     f"site is in zone {s_.tnuos_zone}", ok))
    t = pd.DataFrame(rows, columns=["input", "resolved to", "basis", "matches site"])
    print(t.to_string(index=False))

    for _, r in t[~t["matches site"]].iterrows():
        report("geography", "error",
               f"{r['input']} is not resolved to this site",
               f"using {r['resolved to']} while {r['basis']}. Only one licence "
               f"area is transcribed, so every site outside it is priced on the "
               f"wrong DNO's tariff.")
    if t["matches site"].all():
        report("geography", "ok",
               f"all {len(t)} regional inputs resolve to this site")

    # Inputs that are foreign by construction. Not defects — the study says so
    # — but they must stay visible, because a GB result assembled from them is
    # only as GB as its weakest input.
    foreign = {
        "fuel cell capex": "US DOE, USD converted at a fixed 2025 rate",
        "data centre foreground": "Zhang et al., Virginia (US-SERC); the "
                                  "electricity is swapped for GB, the rest is not",
        "PV embodied carbon": "IEA PVPS Task 12 2023, European reference system "
                              "(ecoinvent's GB dataset is a 2008 plant)",
    }
    for k, v in foreign.items():
        report("geography", "warn", f"{k} is not GB-sourced", v)
    return t


# =============================================================================
def run(site=None, start="2025-01-01", end="2025-02-01",
        size_mw_it=300.0, pue=1.2):
    from optimisation import dc_inputs as I
    from optimisation import sites as S

    # State the tier rather than let it be inferred. Whether a site takes its
    # supply from the transmission or the distribution system is a
    # network-design fact, and a 360 MW load is not a borderline case. Leaving
    # it unstated makes the audit warn at itself about its own configuration,
    # which teaches nothing; the warning is there for sites that genuinely have
    # not said, and it should still fire for them.
    if site is None:
        site = S.resolve(57.48, -4.22, transmission_connected=True)

    print("=" * 100)
    print("STRUCTURAL AUDIT — is the model well posed, and every input in range?")
    print("=" * 100)

    series, meta = I.build_series(site, start, end, size_mw_it, pue=pue)
    series = I.resample(series, 1.0)
    tech = I.build_tech(site, meta, ely_tech="SOEC operation", cost_case="central",
                        size_mw_it=size_mw_it, pue=pue)
    assets = M.Assets(grid=True, wind=True, solar=True, battery=True,
                      electrolyser=True, tank=True, fuel_cell=True)

    cov = check_objective_coverage(series, assets, tech)
    print()
    print(cov.to_string(index=False, float_format=lambda v: f"{v:,.4g}"))
    check_lifetime_agreement()
    check_degeneracy_and_slack(series, assets, tech, objective="gwp")
    # Deliberately the bare coordinate, not the site above: this check exists to
    # watch the band move as the load does, and a site that pins its tier pins
    # the band along with it.
    check_scale_response("57.48,-4.22", start, end)
    check_applicability(site, start, end, size_mw_it, pue)
    check_geography(site, start, end, size_mw_it, pue)

    errs = [f for f in FINDINGS if f.severity == "error"]
    warns = [f for f in FINDINGS if f.severity == "warn"]
    acc = [f for f in FINDINGS if f.severity == "accepted"]
    ok = [f for f in FINDINGS if f.severity == "ok"]
    print("\n" + "=" * 100)
    print(f"{len(errs)} unaccounted error(s), {len(warns)} unaccounted warning(s), "
          f"{len(acc)} accepted, {len(ok)} clean")
    for f in errs:
        print(f"  ERROR  [{f.check}] {f.what}")
    for f in warns:
        print(f"  WARN   [{f.check}] {f.what}")
    for f in acc:
        print(f"  ACPT   [{f.check}] {f.what}")
    if not errs and not warns:
        print("\n  Nothing unaccounted for. Every finding is either fixed or")
        print("  accepted above with a stated reason.")
    print("=" * 100)
    return FINDINGS


if __name__ == "__main__":
    run()
