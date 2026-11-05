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
    Source("baringa_h2p_2025", "Hydrogen to Power Costs and Barriers", "Baringa Partners for DESNZ",
           "9 December 2025", "document",
           link="https://assets.publishing.service.gov.uk/media/69663541e8b93f59c3aecd76/hydrogen-to-power-cost-barriers.pdf",
           basis="2025 £",
           note="§4.4 and §5, PEM fuel cells: equipment over £1,300/kW; installed over £2,500/kW for a pipeline-fed "
                "grid-scale system; purification about £485/kW; 80 MW Korean plant about £2,700/kW. Limited evidence "
                "by its own account; no running cost, stack share or life"),
    Source("element_energy_2018", "Hydrogen supply chain evidence base", "Element Energy for BEIS", "November 2018",
           "document",
           link="https://www.gov.uk/government/publications/hydrogen-supply-chain-evidence-base",
           basis="no general price base stated; 'the majority of the assumptions were collated in 2017' (p. 3), so taken as 2017 £",
           note="pp. 93–95 fuel cell CHP, stack replacement, fully installed, maintenance, with the reformer removed; "
                "boiler efficiency; p. 109 above-ground vessels, 95 m³ holding ~405 kg at 50–80 bar, a supplier's quote; "
                "p. 110 footprint; p. 112 fixed cost"),
    Source("pnnl_esgc_2022", "2022 Grid Energy Storage Technology Cost and Performance Assessment (PNNL-33283)",
           "Pacific Northwest National Laboratory for the US Department of Energy", "August 2022", "document",
           link="https://www.pnnl.gov/sites/default/files/media/file/ESGC%20Cost%20Performance%20Report%202022%20PNNL-33283.pdf",
           note="Figure 4.3, PDF p. 46: LFP total installed cost at 1 and 10 MW, 2, 4, 10 and 24 hours, 2021 and 2030. "
                "The one source read that prices lithium past 12 hours. Used for the line's shape, not its level"),
    Source("lcp_delta_long_bess_2025", "Value of long-duration BESS to the GB power system", "LCP Delta for Gresham House",
           "April 2025", "document", link="https://greshamhouse.com/wp-content/uploads/2025/04/Value-of-long-duration-BESS.pdf",
           basis="real 2024 £",
           note="p. 30: lithium to 10-12 hours, its own Q4 2024 assumptions, about £1,470/kW in 2030 read off a chart; "
                "each added two hours costs the same. Commissioned by a battery investor, so read with that in mind"),
    Source("hse_comah_2015_ia", "The transposition of the Seveso III Directive into UK law through the COMAH "
                                "Regulations 2015: impact assessment HSE 0082", "HSE", "2014, read as Annex A of S.R. 2015 "
                                "No. 325's explanatory memorandum", "document",
           link="https://legislation.gov.uk/nisr/2015/325/pdfs/nisrem_20150325_en.pdf",
           basis="2013 £",
           note="Paras 56-60 and Table 3, PDF pp. 24-25: average compliance cost per establishment, from a survey of time "
                "taken and wage rates, no plant. Upper tier one-off £100-135k (best £118k), about £24-29k a year (best "
                "£27k); lower tier £15-23k (best £20k), £9-11k (best £10k). HSE calls the one-off a likely slight underestimate"),
    Source("beis_h2_costs_2021", "Hydrogen Production Costs 2021, annex: key assumptions and outputs", "BEIS",
           "August 2021", "workbook",
           link="https://assets.publishing.service.gov.uk/media/611a706ed3bf7f63a7b29216/Hydrogen_Production_Cost_2021_Annex.xlsx",
           basis="real 2020 £",
           note="'Technical and cost assumptions', 10 MW, commissioning 2025, construction period 3 years. Assumes a "
                "mature solid-oxide plant and heat at no cost. Its PEM is a third of NESO's 2025 figure, so its level is "
                "the low case and its ratio to PEM the high; the central is the Danish Energy Agency's"),
    Source("beis_ldes_2022", "Benefits of Long Duration Electricity Storage (Research Paper 2022/019)",
           "AFRY for BEIS", "July 2022", "document",
           link="https://www.gov.uk/government/publications/benefits-of-long-duration-electricity-storage",
           basis="real 2019 £, 2030 capital",
           note="Exhibit 3.11, p. 30: Li-ion at 1, 2, 4, 6 and 9 hours, build time 1 year. A 2022 forecast of 2030 "
                "prices; the document FES 2025 uses for storage running costs"),
    Source("desnz_solar_land_2024", "Land utilised by solar PV", "DESNZ", "19 December 2024", "document",
           link="https://assets.publishing.service.gov.uk/media/6762f0efcdb5e64b69e307d5/Land_utilised_by_solar_PV__September_2024.pdf",
           note="New sites about 4 acres (1.6 ha) per MW, existing 5.6; per MW, read here as per MWp"),
    Source("desnz_nondomestic_prices", "Prices of fuels purchased by non-domestic consumers, tables 3.4.1 and 3.4.2",
           "DESNZ", "29 September 2026", "workbook",
           link="https://www.gov.uk/government/statistical-data-sets/gas-and-electricity-prices-in-the-non-domestic-sector",
           basis="cash, 2025 annual",
           note="Gas, large consumers, including CCL 4.149 p/kWh; electricity, extra large, excluding CCL 20.927 p/kWh"),
    Source("cma_retail_profitability_2015", "Profitability of retail energy supply (working paper)", "CMA", "March 2015",
           "document", link="https://assets.publishing.service.gov.uk/media/55070c2040f0b613e6000015/Profitability_of_retail_energy_supply.pdf",
           note="Table 1: EBIT margin on industrial and commercial supply 2.0 %, FY09–13, six largest firms. Ofgem's "
                "2023 non-domestic review gives −3.6 % to +4.2 %, 2019–22"),
    Source("ons_gdp_deflator", "Gross domestic product at market prices: Implied deflator: SA (series YBGB)", "ONS",
           "release of 30 September 2026", "data feed",
           link="https://www.ons.gov.uk/economy/grossdomesticproductgdp/timeseries/ybgb/qna",
           note="2024 = 100; optimisation/price_base.py holds it, scripts/check_price_base.py compares it"),
    Source("worldbank_us_gdp_deflator", "GDP deflator, United States (NY.GDP.DEFL.ZS)", "World Bank",
           "fetched 4 November 2026", "data feed",
           link="https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.DEFL.ZS?format=json",
           note="2020 = 100. Inflates US figures in their own currency before the FES cross-rate"),
    Source("eurostat_ea_gdp_deflator", "GDP and main components, price index (nama_10_gdp, EA20, PD15_EUR)", "Eurostat",
           "fetched 4 November 2026", "data feed",
           link="https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_gdp?geo=EA20&unit=PD15_EUR&na_item=B1GQ",
           note="2015 = 100. Inflates euro figures in their own currency before the FES cross-rate"),
    # --- authoritative alternatives, where no UK government figure exists or it looks wrong (4 Nov 2026)
    Source("cepa_hurdle_rates_2025", "Hurdle rate estimates for electricity sector technologies (final report)",
           "CEPA for DESNZ", "30 June 2025, published October 2025", "document",
           link="https://assets.publishing.service.gov.uk/media/68cd1d818c44a661b4995d9f/cepa-desnz-hurdle-rates-electricity.pdf",
           basis="pre-tax real (CPI), 50 % gearing, whole-life, 31 December 2024",
           note="Table E.1: solar PV and onshore wind 7.60 %, offshore wind 8.90 %, lithium batteries 8.90 %, hydrogen "
                "electrolyser 10.10 %, hydrogen to power (emerging) and novel long-duration storage 10.10 %. No fuel cell "
                "or hydrogen storage row: they take 10.10 %"),
    Source("dea_renewable_fuels_2026", "Technology Data for Renewable Fuels, data sheet 80 SOEC 10 MW (v0019, DNV)",
           "Danish Energy Agency and Energinet", "August 2026", "workbook",
           link="https://ens.dk/media/6444/download", basis="2025 € for the electrolysis chapters (Intro sheet)",
           note="Solid-oxide 10 MW, 2025 column: specific investment €2,959/kW of input electricity (range 2,851–3,067), "
                "fixed O&M 7 % (4–10) excluding stacks, stack replacement every 25,000 h, 20 y. A government agency NESO "
                "itself cites"),
    Source("dea_energy_storage_2025", "Technology Data for Energy Storage, chapter 151 hydrogen storage tanks",
           "Danish Energy Agency and Energinet", "chapter 2019–2020; catalogue updated to July 2026", "document",
           link="https://ens.dk/media/6588/download", basis="2020 €",
           note="Table 6: 15 Type I steel tanks in a rack at 200 bar holding 500 kg, €600/kg; piping, power electronics and "
                "manhours about €150,000 per 500 kg system; compressor €500,000; 25 years"),
    Source("clean_hydrogen_sria_kpis", "Clean Hydrogen Joint Undertaking Strategic Research and Innovation Agenda 2021–2027, "
           "key performance indicators", "Clean Hydrogen Partnership (EU)", "2022", "document",
           link="https://www.clean-hydrogen.europa.eu/knowledge-management/strategy-map-and-key-performance-indicators/clean-hydrogen-ju-sria-key-performance-indicators-kpis_en",
           basis="€, price year not stated",
           note="Table 21, PEM stationary fuel cells 51–500 kWe, 2020 state of the art: system €1,900/kW (excluding power "
                "conversion and site), stack production cost €400/kWe. Table 11, above-ground storage: €750/kg at 1.1 t "
                "(2020), €600/kg at 20 t (2030 target), including compression to 120 bar and purification"),
    Source("nlr_tp_91146", "Cost Analysis of Heavy-Duty Vehicle Proton Exchange Membrane Fuel Cell Stationary Power Plants "
           "(NLR/TP-5400-91146)", "National Laboratory of the Rockies (US)", "February 2026", "document",
           link="https://www.osti.gov/biblio/3018256", basis="2022 US $",
           note="Table 18, 100 MW plant: total overnight cost $1,352/kW, of which sales tax $143.17/kW and transmission "
                "and interconnection $100/kW; Table 12: construction period 3 years, stack durability 25,000 h"),
    Source("nrel_atb_2025", "Annual Technology Baseline 2025, utility-scale battery storage", "National Laboratory of the "
           "Rockies (US)", "v1.0.0, September 2026", "data feed",
           link="https://oedi-data-lake.s3.amazonaws.com/ATB/electricity/parquet/2025/v1.0.0/ATBe.parquet",
           basis="2023 US $",
           note="Moderate scenario, 2026, total capital by duration: 2 h $908/kW, 4 h $1,344, 6 h $1,781, 8 h $2,218, "
                "10 h $2,655. All-in: transformer, substation, spur line, developer costs, US sales tax"),
    Source("ember_bess_2025", "How cheap is battery storage?", "Ember", "11 December 2025", "document",
           link="https://ember-energy.org/latest-insights/how-cheap-is-battery-storage/", basis="US $, October 2025",
           note="All-in capital about $125/kWh for projects of 4 hours and more outside China and the United States: about "
                "$75/kWh equipment and $50/kWh to install and connect; assumes cheap land"),
    Source("elexon_tlf_public_report", "Transmission Loss Factor analysis, interactive report (BSC Year 2026/27)", "Elexon",
           "read 4 November 2026", "data feed",
           link="https://www.elexon.co.uk/bsc/operational/transmission-losses/transmission-loss-factors-analysis/",
           held="OneDrive, DC optimiser/cost sources/5 prices and inflation",
           note="Adjusted seasonal zonal TLFs to five decimals, all 14 zones and 4 seasons, read from the report's "
                "TLF Value card; no login. Their mean reproduces the report's all-zone 0.00524"),
    Source("elexon_etlmo_2026_27", "Estimated Transmission Loss Adjustment values for 2026/27", "Elexon",
           "13 January 2026", "document",
           link="https://www.elexon.co.uk/bsc/article/new-2026-2027-estimated-transmission-losses-adjustment-values-published/",
           note="Offtaking ETLMOj-: spring 0.00948, summer 0.01068, autumn 0.00991, winter 0.00671. Approved by the "
                "Imbalance Settlement Group for use from 1 April 2026; indicative, for reporting"),
    Source("mott_macdonald_storage_2018", "Storage cost and technical assumptions for BEIS", "Mott MacDonald for BEIS",
           "August 2018", "document",
           link="https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/910261/storage-costs-technical-assumptions-2018.pdf",
           note="Table 53: hydrogen storage system build time 1 year"),
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
