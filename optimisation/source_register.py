"""
Every document and data feed the cost objective reads, once, by key.
=============================================================================

A cost number recorded with ``trace.cost`` names where it was read as
``cites=[(key, "Table 3, p.6")]``: a key of ``SOURCES`` plus the exact table,
page, sheet or dataset. The cost map (``scripts/build_cost_map.py``) draws one
box per source with every number that cites it, and its checker fails on a
citation to a key that is not here, a source nothing cites, or a transcribed
number that cites nothing.

``SOURCES.md`` stays the prose record of what each number is and how far it
can be trusted; this is the index the map links through. ``link`` is filled
only where the code or the documents record a public address — a blank link
is shown on the map as "no link recorded", not guessed. ``held`` is where the
copy the numbers were read from is kept: a cache in the repository, or the
OneDrive folder of source documents (``DC optimiser/connection sources``).

The DNO price lists and DUoS schedules are read off the modules that hold
their numbers (``connection_cost.PRICE_LISTS``, ``duos_areas.FILES``), so a
list added there is a source here without a second entry.
"""
from __future__ import annotations

from dataclasses import dataclass

KINDS = ("document", "data feed", "charging statement", "workbook", "register")
NESO_DATASTORE = "https://api.neso.energy/api/3/action/datastore_search?resource_id="
ONEDRIVE = "OneDrive, DC optimiser/connection sources"


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    publisher: str
    date: str                  # as the source dates itself
    kind: str                  # one of KINDS
    link: str = ""             # public address, only where one is recorded
    held: str = ""             # where the copy the numbers came from is kept
    basis: str = ""            # price basis, where it matters
    note: str = ""


_FIXED = [
    # --- generation --------------------------------------------------------
    Source("desnz_arup_2024_onshore_solar",
           "Renewable Energy Generation Cost and Technical Assumptions — Onshore Wind and Solar PV, "
           "Cost of Electricity Report Update 2024 (ref 299867-00)",
           "DESNZ / Ove Arup & Partners", "Final, 14 July 2025", "document",
           basis="real 2023 £", note="Onshore wind Table 3 (p.6); solar PV >5 MW Table 4 (p.7); LCOE Table 5 (p.8)"),
    Source("desnz_arup_2024_offshore",
           "Renewable Energy Generation Cost and Technical Assumptions — Offshore Wind, "
           "Cost of Electricity Report Update 2024",
           "DESNZ / Ove Arup & Partners", "Final, 24 July 2025", "document",
           basis="real 2023 £", note="Table 3 (p.6); infrastructure excludes offshore transmission assets"),
    # --- battery -----------------------------------------------------------
    Source("modo_bess_assumptions",
           "BESS Cost and Technical Assumptions (GB model assumptions)", "Modo Energy", "July 2026",
           "document", link="https://docs.modoenergy.com/pages/jan-2026/uk-europe/model-assumptions/",
           basis="real 2025 £",
           note="~£400/kW for a 1-hour system, +£100/kW per further hour; 15-year life; 5.0 % real WACC. "
                "The source NESO's FES 2025 uses for battery capital"),
    Source("modo_capex_survey_2024",
           "BESS CapEx Survey 2024 (30 market participants, 2.8 GW at 1.9 h)", "Modo Energy", "2024",
           "document", basis="nominal 2024 £",
           note="Average £580k/MW; 68 % of projects between £400k and £700k/MW — the low and high cases"),
    # --- hydrogen assets ---------------------------------------------------
    Source("neso_green_h2_portal_costs",
           "Green Hydrogen Data Portal — electrolyser capital, fixed and variable operating cost, plant life",
           "NESO", "2025", "data feed", held="price_outputs/electrolyser_costs_clean.csv",
           basis="real 2025 £", note="AE and PEM, build year 2025, Low / Central / High scenarios"),
    Source("doe_fc_chp_targets",
           "Technical Targets for 100 kW–3 MW Combined Heat and Power and Distributed Generation Fuel Cell "
           "Systems Operating on Natural Gas", "U.S. Department of Energy", "2015 status, 2020 targets",
           "document", basis="US $, not deflated",
           note="2015 status $1,200–4,500/kW; 2020 target $1,000/kW. Natural-gas systems include a reformer "
                "this study's unit does not have: biased high"),
    Source("h2_vessel_literature",
           "Above-ground compressed hydrogen storage costs across the literature (€500 and €1,040 per kg "
           "of capacity; DOE 2005 status $1,100/kg at 430 bar)", "various", "2005–2022", "document",
           basis="€ and US $", note="No UK or recent source; spread over 2x. A range, not one document"),
    Source("fes_2025_workbook",
           "Future Energy Scenarios 2025 Data Workbook V006 (cross-rates, gas price CP1, carbon price CP2)",
           "NESO", "2025", "workbook", basis="real 2025 £",
           note="Every currency conversion in the study uses its 2025 cross-rates: £1 = €1.17, $1 = €0.913"),
    # --- bought hydrogen ---------------------------------------------------
    Source("eho_uk_2024",
           "European Hydrogen Observatory — levelised cost of hydrogen production, United Kingdom, 2024",
           "European Hydrogen Observatory", "2024", "data feed", basis="€ 2024, converted to real 2025 £",
           note="SMR, reforming with carbon capture, renewable directly connected, grid electrolysis"),
    Source("neso_lcoh_green", "Levelised cost of green hydrogen modelling, 2025 to 2050 (resource cc2dad0c)",
           "NESO", "2025", "data feed", basis="real 2025 £",
           note="The green price range; full sensitivity cube"),
    Source("neso_lcoh_blue", "Levelised cost of blue hydrogen modelling, 2025 to 2050 (resource 3f3b1bf0)",
           "NESO", "2025", "data feed", basis="real 2025 £", note="ATR + CCS; the blue low case"),
    # --- import price ------------------------------------------------------
    Source("elexon_market_index",
           "Market Index Data, provider APXMIDP — half-hourly wholesale price", "Elexon BMRS",
           "the solved window", "data feed", link="https://data.elexon.co.uk/bmrs/api/v1",
           held="price_outputs/ (cached by grid_build.py)", basis="nominal £ in the window"),
    Source("neso_tnuos_hh", "TNUoS half-hourly demand tariffs by zone, 2026/27 Final",
           "NESO Data Portal", "2026/27", "data feed",
           link=NESO_DATASTORE + "6abe8416-149c-4c78-b65b-059eea19957a", held="optimisation_outputs/neso_cache/"),
    Source("neso_tnuos_tdr", "TNUoS Transmission Demand Residual tariffs by band, 2026/27 Final",
           "NESO Data Portal", "2026/27", "data feed",
           link=NESO_DATASTORE + "dcca94fd-343e-4d4e-8c5d-66009dec4ad3", held="optimisation_outputs/neso_cache/"),
    Source("neso_bsuos_fixed", "Fixed BSUoS tariffs, by half-year, Final", "NESO Data Portal", "2026/27",
           "data feed", link=NESO_DATASTORE + "4dfa533f-bec6-491b-a3f1-7ce92449bc9a",
           held="optimisation_outputs/neso_cache/"),
    Source("ofgem_ro_2026_27", "RO buy-out price and mutualisation threshold and ceilings 2026 to 2027",
           "Ofgem", "2026", "document", held=f"{ONEDRIVE}/5 levies and losses",
           note="Buy-out £69.34 per ROC; obligation 0.472 ROCs per MWh supplied (England, Wales and Scotland)"),
    Source("ofgem_fit_quarterly", "FIT Quarterly Report, Issues 62–65 (Jul 2025 – Jun 2026)", "Ofgem",
           "2025–2026", "document", held=f"{ONEDRIVE}/5 levies and losses",
           note="Levelisation fund and supply less exempt supply per quarter; £/MWh = fund / (supply − exempt)"),
    Source("emr_key_figures_2026_27", "Key Figures for Payments in 2026/27", "EMR Settlement", "2026/27",
           "document", held=f"{ONEDRIVE}/5 levies and losses",
           note="§1, §3 CfD interim levy rates and operational levy; §5, §7 Nuclear RAB; §9, §12 Capacity Market"),
    Source("neso_aahedc_2026_27", "AAHEDC Final Tariff and Charging Statement 2026-27, Schedule 1", "NESO",
           "2026/27", "document", held=f"{ONEDRIVE}/5 levies and losses",
           note="Total Scheme Energy Consumption Tariff 0.044269 p/kWh"),
    Source("govuk_ccl_rates", "Climate Change Levy rates", "GOV.UK (HMRC)", "from 1 April 2026", "document",
           held=f"{ONEDRIVE}/5 levies and losses",
           note="Electricity £0.00801/kWh; 92 % discount under a Climate Change Agreement"),
    Source("elexon_tlf_guidance", "Guidance document for Transmission Loss Factors v1.0", "Elexon",
           "January 2026", "document", held=f"{ONEDRIVE}/5 levies and losses",
           note="Offtaking TLM = 1 + TLF(zone, season) + TLMO−; the worked example's 0.011"),
    Source("elexon_tlf_report_2026_27", "Analysis Reporting for TLFs — BSC Year 2026/27 V1.0", "Elexon",
           "April 2026", "document", held=f"{ONEDRIVE}/5 levies and losses",
           note="Adjusted seasonal zonal TLFs, read from the charts on pp. 7–8 (about ±0.0005)"),
    # --- connection --------------------------------------------------------
    Source("neso_use_of_system_statement",
           "The Statement of Use of System Charges, Issue 8.0 (Section 14 connection charges)", "NESO",
           "effective 1 April 2026", "charging statement", held=f"{ONEDRIVE}/4 connection capital",
           note="§15–16 and Appendix A: 40-year depreciation, maintenance 0.43 % of asset value, running cost "
                "0.90 %; Table 3.1 rate of return NGET 5.02 %, SPT 5.14 %, SHET 4.32 %"),
    Source("enwl_es216", "ES216 Issue 4 — substation transformer ratings", "Electricity North West",
           "July 2024", "document", held=f"{ONEDRIVE}/4 connection capital",
           note="132/33 kV transformer ≤ 60 MVA (§5.2); 33/11 kV ≤ 29 MVA (§6.2)"),
    Source("substation_register",
           "Substation register: 10,829 substations from 39 network-company portal datasets, with spare "
           "capacity, built by scripts/build_substation_register.py", "this study, from DNO and NESO portals",
           "see optimisation_outputs/substation_register/freshness.json", "register",
           held="optimisation_outputs/substation_register/",
           note="The connection voltage, the nearest substation with room and the cable route to it"),
]


def _price_lists() -> list[Source]:
    from optimisation import connection_cost as cc
    return [Source(f"connection_prices.{k}", p.source, p.name, str(cc.PRICE_YEAR), "charging statement",
                   held=f"{ONEDRIVE}/4 connection capital",
                   note="Statement of Methodology and Charges for Connection, §7 tables F5 (cables) and F7 "
                        "(substations); £ excluding VAT")
            for k, p in cc.PRICE_LISTS.items()]


def _duos_schedules() -> list[Source]:
    from optimisation import duos_areas as da
    out = [Source(f"duos_schedule.{r}", f"Schedule of charges and other tables {da.SCHEDULE_YEAR} — "
                  f"{da.AREA_NAMES[r]} ({f})", da.AREA_NAMES[r], da.SCHEDULE_YEAR, "workbook",
                  held=f"{ONEDRIVE}/3 DUoS/2026-27 schedules",
                  note="Annex 1 HV tariffs, Annex 2 designated EHV sites, Annex 5 line loss factors")
           for r, f in da.FILES.items()]
    out += [Source(f"llf_file.{r}", f"LLFs for year beginning 1 April 2026 — {da.AREA_NAMES[r]} ({f})",
                   da.AREA_NAMES[r], "2026/27", "workbook", held=f"{ONEDRIVE}/3 DUoS/2026-27 schedules",
                   note="NGED publish the line loss factors apart from the schedule")
            for r, f in da.LLF_FILES.items()]
    return out


def _all() -> dict[str, Source]:
    out = {}
    for s in _FIXED + _price_lists() + _duos_schedules():
        if s.key in out:
            raise ValueError(f"source {s.key!r} registered twice")
        if s.kind not in KINDS:
            raise ValueError(f"source {s.key!r}: kind {s.kind!r} is not one of {KINDS}")
        out[s.key] = s
    return out


SOURCES: dict[str, Source] = _all()


def get(key: str) -> Source:
    if key not in SOURCES:
        raise KeyError(f"no source {key!r} in source_register.SOURCES")
    return SOURCES[key]


if __name__ == "__main__":
    for s in SOURCES.values():
        print(f"{s.key:<36} {s.kind:<19} {s.publisher[:28]:<28} {s.link or '(no link recorded)'}")
