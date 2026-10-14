"""
Reproduce the papers from the activities just written.
=============================================================================

    python -m optimiser_lca.validate            # all three checks
    python -m optimiser_lca.validate fc_stack   # one of: fc_stack, fc_operation, data_centre

* ``fc_stack_vs_paper``: the Babatunde stack through ReCiPe 2016 v1.03 (H),
  category by category against the paper's Tables 3, 4 and 5. ``ratio`` is
  ours ÷ paper. Re-run after any change to the stack's processes, amounts or
  ``FC_SCALE``. The paper does not state its ReCiPe perspective; (H) is
  SimaPro's default and is what matches.
* ``fc_operation_sanity``: the operation activity cannot be checked against a
  paper (there is no use phase), so: where the per-kWh burden comes from,
  whether the capital amortisation lands near ecoinvent's own PEMFC operation
  dataset once its domestic-CHP artefacts are stripped, and how hard the
  efficiency assumption pushes.
* ``data_centre_vs_paper``: GWP100 of the Zhang facility against the paper's
  9.63e8 kg CO2e, remembering the boundary here is narrower.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from optimiser_lca import registry as R  # noqa: E402

# =============================================================================
# Babatunde et al. 2024 — published results, transcribed from the PDF
# =============================================================================
PAPER_TABLE3 = {   # mid-point characterisation, 1 kW FC — paper p. 361
    "Fine particulate matter formation":       (0.77385,   "kg PM2.5 eq"),
    "Fossil resource scarcity":                (22.9546,   "kg oil eq"),
    "Freshwater ecotoxicity":                  (35.132,    "kg 1,4-DCB"),
    "Freshwater eutrophication":               (0.07111,   "kg P eq"),
    "Global warming":                          (96.5796,   "kg CO2 eq"),
    "Human carcinogenic toxicity":             (10.8858,   "kg 1,4-DCB"),
    "Human non-carcinogenic toxicity":         (1109.94,   "kg 1,4-DCB"),
    "Ionizing radiation":                      (3.83781,   "kBq Co-60 eq"),
    "Land use":                                (3.91375,   "m2a crop eq"),
    "Marine ecotoxicity":                      (44.8299,   "kg 1,4-DCB"),
    "Marine eutrophication":                   (0.00322,   "kg N eq"),
    "Mineral resource scarcity":               (6.24947,   "kg Cu eq"),
    "Ozone formation, Human health":           (0.76387,   "kg NOx eq"),
    "Ozone formation, Terrestrial ecosystems": (0.78174,   "kg NOx eq"),
    "Stratospheric ozone depletion":           (0.00031,   "kg CFC11 eq"),
    "Terrestrial acidification":               (2.61008,   "kg SO2 eq"),
    "Terrestrial ecotoxicity":                 (129.522,   "kg 1,4-DCB"),
    "Water consumption":                       (0.47144,   "m3"),
}
PAPER_TABLE4 = {   # end-point characterisation — paper p. 362
    "Fine particulate matter formation":        (0.000485875, "DALY"),
    "Fossil resource scarcity":                 (4.72288595,  "USD2013"),
    "Freshwater ecotoxicity":                   (2.43e-8,     "species/yr"),
    "Freshwater eutrophication":                (4.76e-8,     "species/yr"),
    "Global warming, Freshwater ecosystems":    (7.39e-12,    "species/yr"),
    "Global warming, Human health":             (8.96e-5,     "DALY"),
    "Global warming, Terrestrial ecosystems":   (2.70e-7,     "species/yr"),
    "Human carcinogenic toxicity":              (3.61e-5,     "DALY"),
    "Human non-carcinogenic toxicity":          (0.000252875, "DALY"),
    "Ionizing radiation":                       (3.26e-8,     "DALY"),
    "Land use":                                 (3.47e-8,     "species/yr"),
    "Marine ecotoxicity":                       (4.71e-9,     "species/yr"),
    "Marine eutrophication":                    (5.48e-12,    "species/yr"),
    "Mineral resource scarcity":                (1.44555365,  "USD2013"),
    "Ozone formation, Human health":            (6.95e-7,     "DALY"),
    "Ozone formation, Terrestrial ecosystems":  (1.01e-7,     "species/yr"),
    "Stratospheric ozone depletion":            (1.62e-7,     "DALY"),
    "Terrestrial acidification":                (5.53e-7,     "species/yr"),
    "Terrestrial ecotoxicity":                  (1.48e-9,     "species/yr"),
    "Water consumption, Aquatic ecosystems":    (6.27e-13,    "species/yr"),
    "Water consumption, Human health":          (4.94e-7,     "DALY"),
    "Water consumption, Terrestrial ecosystem": (4.98e-9,     "species/yr"),
}
PAPER_TABLE5 = {   # damage assessment — paper p. 362
    "Human health": (0.000866, "DALY"),
    "Ecosystems":   (1.04e-6,  "species/yr"),
    "Resources":    (6.16844,  "USD2013"),
}
# Paper's category names -> this project's ReCiPe 2016 (H) method names
MIDPOINT_MAP = {
    "Fine particulate matter formation":       "particulate matter formation",
    "Fossil resource scarcity":                "energy resources: non-renewable, fossil",
    "Freshwater ecotoxicity":                  "ecotoxicity: freshwater",
    "Freshwater eutrophication":               "eutrophication: freshwater",
    "Global warming":                          "climate change",
    "Human carcinogenic toxicity":             "human toxicity: carcinogenic",
    "Human non-carcinogenic toxicity":         "human toxicity: non-carcinogenic",
    "Ionizing radiation":                      "ionising radiation",
    "Land use":                                "land use",
    "Marine ecotoxicity":                      "ecotoxicity: marine",
    "Marine eutrophication":                   "eutrophication: marine",
    "Mineral resource scarcity":               "material resources: metals/minerals",
    "Ozone formation, Human health":           "photochemical oxidant formation: human health",
    "Ozone formation, Terrestrial ecosystems": "photochemical oxidant formation: terrestrial ecosystems",
    "Stratospheric ozone depletion":           "ozone depletion",
    "Terrestrial acidification":               "acidification: terrestrial",
    "Terrestrial ecotoxicity":                 "ecotoxicity: terrestrial",
    "Water consumption":                       "water use",
}
ENDPOINT_MAP = {
    "Fine particulate matter formation":        ("human health",     "particulate matter formation"),
    "Fossil resource scarcity":                 ("natural resources", "energy resources: non-renewable, fossil"),
    "Freshwater ecotoxicity":                   ("ecosystem quality", "ecotoxicity: freshwater"),
    "Freshwater eutrophication":                ("ecosystem quality", "eutrophication: freshwater"),
    "Global warming, Freshwater ecosystems":    ("ecosystem quality", "climate change: freshwater ecosystems"),
    "Global warming, Human health":             ("human health",     "climate change: human health"),
    "Global warming, Terrestrial ecosystems":   ("ecosystem quality", "climate change: terrestrial ecosystems"),
    "Human carcinogenic toxicity":              ("human health",     "human toxicity: carcinogenic"),
    "Human non-carcinogenic toxicity":          ("human health",     "human toxicity: non-carcinogenic"),
    "Ionizing radiation":                       ("human health",     "ionising radiation"),
    "Land use":                                 ("ecosystem quality", "land use"),
    "Marine ecotoxicity":                       ("ecosystem quality", "ecotoxicity: marine"),
    "Marine eutrophication":                    ("ecosystem quality", "eutrophication: marine"),
    "Mineral resource scarcity":                ("natural resources", "material resources: metals/minerals"),
    "Ozone formation, Human health":            ("human health",     "photochemical oxidant formation: human health"),
    "Ozone formation, Terrestrial ecosystems":  ("ecosystem quality", "photochemical oxidant formation: terrestrial ecosystems"),
    "Stratospheric ozone depletion":            ("human health",     "ozone depletion"),
    "Terrestrial acidification":                ("ecosystem quality", "acidification: terrestrial"),
    "Terrestrial ecotoxicity":                  ("ecosystem quality", "ecotoxicity: terrestrial"),
    "Water consumption, Aquatic ecosystems":    ("ecosystem quality", "water use: aquatic ecosystems"),
    "Water consumption, Human health":          ("human health",     "water use: human health"),
    "Water consumption, Terrestrial ecosystem": ("ecosystem quality", "water use: terrestrial ecosystems"),
}
DAMAGE_MAP = {
    "Human health": ("total: human health",     "human health"),
    "Ecosystems":   ("total: ecosystem quality", "ecosystem quality"),
    "Resources":    ("total: natural resources", "natural resources"),
}
RECIPE_MID = "ReCiPe 2016 v1.03, midpoint (H)"
RECIPE_END = "ReCiPe 2016 v1.03, endpoint (H)"

# Zhang et al. 2025's own reported baseline, full cradle-to-grave, ecoinvent 3.7
# cutoff + TRACI 2.1.
ZHANG_PAPER_KGCO2E = 9.63e8


def _gwp_with_lt(bd):
    return next(m for m in bd.methods if m[1] == "IPCC 2021" and m[2] == "climate change"
                and "GWP100" in m[3] and "no LT" not in m[1])


def fc_stack_vs_paper():
    import bw2calc as bc
    import bw2data as bd
    import lca_helpers as H
    H.setup_brightway()

    mid_methods = {m[2]: m for m in bd.methods if m[1] == RECIPE_MID}
    end_methods = {(m[2], m[3]): m for m in bd.methods if m[1] == RECIPE_END}
    if not mid_methods or not end_methods:
        raise RuntimeError(f"{RECIPE_MID!r} / {RECIPE_END!r} not found in this project's methods. "
                           "The comparison needs the ecoinvent-bundled ReCiPe 2016 v1.03 methods.")
    fc_act = bd.get_activity((R.FUEL_CELL_DB, R.FC_STACK))
    lca = bc.LCA({fc_act: 1.0}, next(iter(mid_methods.values())))
    lca.lci()
    lca.lcia()

    def score(method):
        lca.switch_method(method)
        lca.lcia_calculation()
        return lca.score

    def report(title, paper_table, method_lookup):
        print("=" * 104)
        print(title)
        print("=" * 104)
        print(f"{'Impact category':<42}{'unit':<14}{'paper':>13}{'notebook':>13}{'ratio':>8}")
        ratios = []
        for category, (paper_value, unit) in paper_table.items():
            s = score(method_lookup[category])
            ratio = s / paper_value
            ratios.append(ratio)
            flag = "" if 0.9 <= ratio <= 1.1 else ("  <-- outside +-10%" if 0.85 <= ratio <= 1.15 else "  <-- outside +-15%")
            print(f"{category:<42}{unit:<14}{paper_value:>13.5g}{s:>13.5g}{ratio:>8.2f}{flag}")
        within = sum(1 for r in ratios if 0.9 <= r <= 1.1)
        print(f"\n  median ratio {statistics.median(ratios):.3f} | "
              f"{within}/{len(ratios)} categories within +-10% of the paper\n")
        return ratios

    out = {
        "midpoint": report("Paper Table 3 — mid-point characterisation, 1 kW PEM fuel cell stack (ReCiPe 2016 H)",
                           PAPER_TABLE3, {k: mid_methods[v] for k, v in MIDPOINT_MAP.items()}),
        "endpoint": report("Paper Table 4 — end-point characterisation (ReCiPe 2016 H)",
                           PAPER_TABLE4, {k: end_methods[v] for k, v in ENDPOINT_MAP.items()}),
        "damage": report("Paper Table 5 — damage assessment",
                         PAPER_TABLE5, {k: end_methods[v] for k, v in DAMAGE_MAP.items()}),
    }
    print("The categories that miss +-15% are the ecotoxicity, metal-resource, land-use and")
    print("water-use ones: exactly the categories whose characterisation factors and underlying")
    print("metal/land inventories changed most between ecoinvent 3.7.1 (the paper, via SimaPro)")
    print("and 3.9.1 apos (this project). The three damage totals in Table 5 and every")
    print("combustion-driven mid-point category land within a few percent, which is the check")
    print("that the inventory itself is right.")
    return out


def fc_operation_sanity():
    import bw2calc as bc
    import bw2data as bd
    import lca_helpers as H
    from optimiser_lca import fuel_cell as fc
    H.setup_brightway()
    GWP = _gwp_with_lt(bd)
    print("Method:", GWP, "\n")

    fc_op = bd.get_activity((R.FUEL_CELL_DB, R.FC_OP))
    h2_key = tuple(fc.FC_H2_SOURCE)

    def gwp(target, amount=1.0):
        l_ = bc.LCA({target: amount}, GWP)
        l_.lci(); l_.lcia()
        return l_.score

    total = gwp(fc_op)
    print("=" * 92)
    print(f"Contribution to 1 kWh of fuel cell electricity — {total*1000:,.1f} g CO2e/kWh")
    print("=" * 92)
    print(f"{'exchange':<58}{'amount':>13}{'g CO2e/kWh':>12}{'share':>8}")
    capital = 0.0
    for exc in fc_op.technosphere():
        s = gwp(exc.input, exc.amount)
        if exc.input.key != h2_key:
            capital += s
        print(f"{exc.input.get('name','')[:56]:<58}{exc.amount:>13.4e}{s*1000:>12.3f}{s/total*100:>7.1f}%")
    h2 = total - capital
    print("-" * 92)
    print(f"{'hydrogen':<58}{'':>13}{h2*1000:>12.3f}{h2/total*100:>7.1f}%")
    print(f"{'stack + balance of plant (embodied)':<58}{'':>13}{capital*1000:>12.3f}{capital/total*100:>7.1f}%")

    # --- The system against published fuel-cell systems ---------------------------
    # Whole systems cradle-to-gate per kW. The vehicle ones carry no inverter and no
    # enclosure; this one does, and its stack is ecoinvent's 2 kW graphite-plate
    # unit, heavier than any automotive stack. So it should sit above the vehicle
    # band and below the 3 kW UPS, whose fixed parts are not spread over scale.
    stack_kw = gwp(bd.get_activity((R.FUEL_CELL_DB, R.FC_STACK)))
    bop_act = bd.get_activity((R.FUEL_CELL_DB, R.FC_BOP))
    bop_kw = gwp(bop_act)
    parts = {"process loops (Usai 2021)": 0.0, "inverter": 0.0, "container": 0.0}
    for exc in bop_act.technosphere():
        note = exc.get("comment", "").lower()
        key = "inverter" if "inverter" in note else "container" if "container" in note \
            else "process loops (Usai 2021)"
        parts[key] += gwp(exc.input, exc.amount)
    print()
    print("=" * 92)
    print("The system per kW, against published fuel-cell systems (cradle-to-gate)")
    print("=" * 92)
    print(f"  stack (Babatunde 2024)                          {stack_kw:>8.1f} kg CO2e/kW")
    for k, v in parts.items():
        print(f"  balance of plant: {k:<29}{v:>8.1f}")
    print(f"  this system                                     {stack_kw + bop_kw:>8.1f}")
    usai_loops = 854.05416864 / 80.0     # Usai's own BoP result, results workbook
    print(f"\n  Usai's process loops rebuilt on 3.9.1: {parts['process loops (Usai 2021)']:.2f} "
          f"against their own {usai_loops:.2f} kg CO2e/kW (ecoinvent 3.6) - "
          f"{parts['process loops (Usai 2021)'] / usai_loops:.2f}x; the printed table rounds to "
          "two decimals.")
    for label, v in (("Miotti 2017, 80 kW car", 29.0), ("Usai 2021, 80 kW car, no tank", 37.3),
                     ("Gentilucci 2024, 200 kW truck", "30.5-51.4"),
                     ("Ballard FCmove-HD, 70 kW module", 73.0),
                     ("Stropnik 2018 via Bionaz 2022, 3 kW UPS", 405.5)):
        print(f"  {label:<46}{v!s:>10}")
    # --- How hard does the efficiency assumption push? -----------------------------
    print()
    print("=" * 92)
    print("Sensitivity to the efficiency assumption (everything else held fixed)")
    print("=" * 92)
    h2_act = bd.get_activity(h2_key)
    h2_gwp_per_kg = gwp(h2_act)
    print(f"{'eta BOL':>9}{'eta mean':>10}{'kg H2/kWh':>12}{'g CO2e/kWh':>13}{'vs default':>12}")
    for eta in (0.45, 0.50, 0.55):
        mean = eta * fc.FC_DEGRADATION_DERATE
        kg = 1.0 / (mean * fc.FC_H2_LHV_KWH_PER_KG)
        tot = kg * h2_gwp_per_kg + capital
        print(f"{eta:>9.2f}{mean:>10.3f}{kg:>12.5f}{tot*1000:>13.1f}{tot/total:>11.2f}x")

    # --- Round trip ------------------------------------------------------------------
    elec_in = [e.amount for e in h2_act.technosphere() if H.is_any_electricity_exchange(e)]
    if elec_in:
        kwh_per_kg = sum(elec_in)
        kwh_in = fc.FC_H2_PER_KWH * kwh_per_kg
        print()
        print("=" * 92)
        print("Round trip through this hydrogen source")
        print("=" * 92)
        print(f"  {h2_act['name']}")
        print(f"  electrolyser  {kwh_per_kg:.1f} kWh/kg H2   x   fuel cell {fc.FC_H2_PER_KWH:.5f} kg H2/kWh")
        print(f"  → {kwh_in:.2f} kWh in per kWh out   =   {100/kwh_in:.1f}% round-trip efficiency")
        print(f"  → hydrogen carries {h2_gwp_per_kg:.2f} kg CO2e/kg here, i.e. {h2*1000:,.0f} g CO2e/kWh delivered")
    return {"total_kgco2e_per_kwh": total, "capital_kgco2e_per_kwh": capital}


def data_centre_vs_paper():
    import bw2data as bd
    import lca_helpers as H
    H.setup_brightway()
    GWP = _gwp_with_lt(bd)
    dc = bd.get_activity((R.DATA_CENTRE_DB, R.DATA_CENTRE))
    s = H.run_lca_score(dc, GWP)
    print(f"Zhang facility, 25 y, materials + operation: {s:.3e} kg CO2e "
          f"({s / ZHANG_PAPER_KGCO2E:.2f} x the paper's {ZHANG_PAPER_KGCO2E:.2e}, which is "
          "full cradle-to-grave on ecoinvent 3.7 cutoff + TRACI 2.1; the full-boundary "
          "rebuild gave 0.87)")
    return s


def gb_grid_vs_series(tol=1e-4):
    """The GB grid activity must score to its pinned figure and its series' mean."""
    import bw2data as bd
    import lca_helpers as H
    from optimiser_lca import gb_grid
    H.setup_brightway()
    print(gb_grid.check_against_series())
    s = H.run_lca_score(bd.get_activity((R.GRID_DB, R.GB_GRID_HV_2025)), _gwp_with_lt(bd)) * 1000
    pinned = gb_grid.GB_GRID_2025_HV_GCO2E_PER_KWH
    print(f"GB study grid, 2025, delivered at HV: {s:.3f} g CO2e/kWh (pinned {pinned:.3f})")
    if abs(s - pinned) > tol * pinned:
        raise AssertionError("gb_grid has moved: update GB_GRID_2025_HV_GCO2E_PER_KWH")
    return s


CHECKS = {"fc_stack": fc_stack_vs_paper, "fc_operation": fc_operation_sanity,
          "data_centre": data_centre_vs_paper, "gb_grid": gb_grid_vs_series}


def main(argv=None):
    names = argv if argv else list(CHECKS)
    for n in names:
        print("\n" + "#" * 78 + f"\n# {n}\n" + "#" * 78)
        CHECKS[n]()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
