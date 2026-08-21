"""
=============================================================================
MASTER DASHBOARD — single source of truth for the split notebooks.
=============================================================================

The intended entry point is now:

    1.dashboard_lca_adaptive.ipynb

Edit this file once, save it, restart the notebook kernel, then run the adaptive
notebook. It will call the selected grid notebook, wind notebook and price
notebook using the settings below.
"""

# =============================================================================
# Brightway project / database settings
# =============================================================================
PROJECT_NAME      = "hydrogen-smr"
ECOINVENT_VERSION = "3.9.1"
SYSTEM_MODEL      = "apos"                       # "apos", "cutoff", "consequential", ...
FOREGROUND_DB     = "hydrogen foreground"
DC_FOREGROUND_DB  = "data centre foreground"  # separate DB for non-hydrogen foregrounds (e.g. notebook 2's Zhang et al. data centre process)
FC_FOREGROUND_DB  = "fuel cell foreground"    # separate DB for notebook 2's Babatunde et al. 1 kW PEM fuel cell stack

# Set True only if you need to import ecoinvent into the active Brightway project.
RUN_IMPORT_ECOINVENT = False

# Rebuilds the foreground database from the SimaPro-derived inventories.
# Leave False once the foreground database already exists.
RUN_BUILD_FOREGROUND_DATABASE = True

# Run a reference LCA on the foreground processes using their original electricity inputs.
RUN_REFERENCE_LCA = False

# =============================================================================
# Adaptive-dashboard orchestration
# =============================================================================
# These control what 1.dashboard_lca_adaptive.ipynb runs when you Run All.
# Set RUN_FOREGROUND_NOTEBOOK_FROM_DASHBOARD=True only on first setup or after
# changing foreground inventories, because it can be slower than the other steps.
RUN_FOREGROUND_NOTEBOOK_FROM_DASHBOARD = False
RUN_GRID_NOTEBOOK_FROM_DASHBOARD = True
RUN_WIND_NOTEBOOK_FROM_DASHBOARD = True
RUN_PRICE_NOTEBOOK_FROM_DASHBOARD = False

# =============================================================================
# Grid data source selector
# =============================================================================
# "csv"        / "3"   = old 3.custom_grid.ipynb using df_fuel_ckan.csv
# "carbon_api" / "3.1" = new 3.1.custom_grid_carbon_intensity_api.ipynb
# ("4"/"4.1" also still accepted — the pre-renumbering shorthand.)
GRID_DATA_SOURCE = "carbon_api"

# CSV input for the old National Grid ESO half-hourly fuel mix workflow.
CSV_PATH = "df_fuel_ckan.csv"

# Carbon Intensity API input settings for 3.1.
CARBON_API_BASE = "https://api.carbonintensity.org.uk"
CARBON_API_SCOPE = "regional_auto"          # "regional_auto" or "national"
CARBON_API_REGION_ID_OVERRIDE = None
CARBON_API_LOCAL_TZ = "Europe/London"
CARBON_API_MAX_DAYS_PER_REQUEST = 13
CARBON_API_REQUEST_SLEEP_S = 0.05
CARBON_API_USE_CACHE = True
CARBON_API_CACHE_DIR = "carbon_intensity_api_cache"
CARBON_API_DEFAULT_IMPORT_SPLIT = {
    "IMPORTS_FR": 1/3,
    "IMPORTS_IE": 1/3,
    "IMPORTS_NL": 1/3,
}
CARBON_API_WIND_EMB_SHARE = 0.0

# =============================================================================
# Grid scenario run options (custom_grid / custom_grid_carbon_intensity_api)
# =============================================================================
RUN_GRID_SCENARIO_LCA = True

GRID_TIME_MODE = 'range'
GRID_SINGLE_DATETIME = '2023-07-15 12:00:00'
GRID_RANGE_START = '2025-01-01 00:00:00'
GRID_RANGE_END = '2025-02-28 00:00:00'

# "year_average" mode: pick one whole year and run the LCA on 12 wind-based
# representative days (per season: average-wind day, top-10% wind day and
# bottom-10% wind day). Each representative day is collapsed into one daily row.
GRID_YEAR = 2025
GRID_REP_DECILE       = 0.10
GRID_WIND_COLS        = ["WIND", "WIND_EMB"]

METHOD_MODE = 'cheap'
APPLY_LOSSES          = True
MARKET_LOSS_SHARE     = 0.031642692177

# Selected foreground technologies for the grid LCA.
TECH_ORDER_DEFAULT = [
    "SMR",
    "SMR-CCS",
    "AE operation",
    "PEM operation",
    "SOEC operation",
    "MP-E",
]
TECH_SELECTED = ['Data centre facility, hyperscale, Virginia (Zhang et al. 2025)']
TECH_COUNT    = 1

# Optional per-label source override: {label: (database_name, activity_code)}.
# Lets a technology label point at an activity outside FOREGROUND_DB — e.g. a
# process the AI-LCA foreground extractor wrote into its own database. Leave
# empty to use the built-in H2_CODES/ELECTROLYSER_CODES lookup as before.
# Populated by the Streamlit Setup-LCA page; safe to leave {} in notebook use.
TECH_SOURCE_OVERRIDES = {'Data centre facility, hyperscale, Virginia (Zhang et al. 2025)': ('data centre foreground', 'dc_zhang_virginia_baseline_25y')}

VALIDATE_CHEAP_METHOD = False

# =============================================================================
# PEM fuel cell operation (notebook 2 — "fuel cell foreground")
# =============================================================================
# Turns the Babatunde et al. (2024) stack into a generator: 1 kWh of AC
# electricity from hydrogen. Every value here is a literature parameter, not a
# fitted one — see notebook 2's "PEM fuel cell operation" markdown for the
# citations and for why the activity has no direct biosphere flows.

FC_RATED_POWER_KW     = 1.0        # matches the paper's 1 kW stack
FC_H2_LHV_KWH_PER_KG  = 33.33      # hydrogen lower heating value, 120 MJ/kg

# Net AC electrical efficiency at beginning of life, LHV basis. DOE's stationary
# 1-25 kWe target is >=45% on natural gas (i.e. including reformer losses, so a
# pure-H2 system should beat it); reported stack efficiency for a 1 kW H2-fed
# PEMFC is ~51.6%, and ~50% is the usual figure quoted for mid-size stationary
# PEMFC. 0.50 sits in the middle; 0.45-0.55 is the defensible range.
FC_ETA_NET_BOL        = 0.50

# Mean-over-life efficiency as a fraction of beginning-of-life. PEMFC end of life
# is conventionally defined as a 10% drop in cell voltage (Stropnik et al. 2022);
# degrading linearly to that point gives a lifetime mean of 95% of BOL. Set to
# 1.0 to model a non-degrading stack.
FC_DEGRADATION_DERATE = 0.95

FC_STACK_LIFETIME_H   = 32_000     # Babatunde et al. 2024, section 3.4 (their own figure)
FC_SYSTEM_LIFETIME_H  = 60_000     # DOE 2020 stationary target; BoP outlives the stack

# Balance of plant and maintenance are taken from ecoinvent's own PEMFC datasets,
# each written as (ecoinvent dataset - its stack content), so the paper's stack
# can never be double-counted.
FC_BOP_LOCATION = "CH"   # the only location where ecoinvent links the stack directly

# ecoinvent's PEMFC is a domestic micro-CHP unit. Two of its items are artefacts
# of that setting rather than of fuel cells: the hot-water/hydronic kit (34% of
# the system's GWP) and 200 km of passenger-car travel per service visit (a
# technician driving to a house). Neither applies to a rack of stacks in a data
# centre, so both are subtracted by default. Set True if you are modelling a
# domestic micro-CHP instead.
FC_DOMESTIC_CHP_ITEMS = False

# Stack fraction inside one ecoinvent maintenance event — i.e. a full stack is
# replaced every 1/0.167 ~ 6 services. Used to scale maintenance to this
# notebook's own stack-replacement rate, and to subtract the stack ecoinvent
# bundles into it.
FC_MAINT_STACK_FRACTION = 0.167

# Which hydrogen the fuel cell burns: (database, activity code). Any per-kg-H2
# activity works — swap in ae_op_/soec_op_/smr_ for a different supply chain.
FC_H2_SOURCE = ("hydrogen foreground", "pem_op_hermesmann_1kg_h2")

# =============================================================================
# Hydrogen storage tank (notebook 2)
# =============================================================================
# ecoinvent 3.9.1 has no hydrogen storage vessel, so the tank is modelled the
# way Gandiglio et al. (2022) model theirs: as a mass of steel and nothing else.
#   M. Gandiglio, P. Marocco, I. Bianco, D. Lovera, G.A. Blengini, M. Santarelli,
#   "Life cycle assessment of a renewable energy system with hydrogen-battery
#   storage for a remote off-grid community", Int. J. Hydrogen Energy 47 (2022).
# Their inventory is one line - 15,652 kg of chromium steel 18/8 for the 21.6 m3
# / 28 bar vessel at Ginostra - amortised over the plant's 25-year output.
H2_STORAGE_FOREGROUND_DB = "hydrogen storage foreground"

TANK_DESIGNS = {
    # The real vessel in the paper. Low-pressure buffer, so heavy per kg stored.
    "gandiglio_28bar": {
        "steel_process": ("market for steel, chromium steel 18/8", "GLO"),
        "steel_kg": 15_652.0, "volume_m3": 21.6, "pressure_bar": 28.0,
        "note": "Gandiglio et al. 2022, Table 3 - as-built 21.6 m3 stainless vessel at Ginostra",
    },
    # Type I all-steel cylinder at 200 bar, sized from ~1 wt% gravimetric
    # capacity. Roughly 3x lighter per kg H2 than the 28 bar design above.
    "type1_200bar": {
        "steel_process": ("market for steel, low-alloyed, hot rolled", "GLO"),
        "steel_kg_per_kg_h2": 100.0, "pressure_bar": 200.0,
        "note": "Type I seamless cylinder, ~1 wt% H2 - typical industrial stationary bottle",
    },
}
TANK_DESIGN = "gandiglio_28bar"
if TANK_DESIGN not in TANK_DESIGNS:
    raise ValueError(f"TANK_DESIGN must be one of {list(TANK_DESIGNS)}")

# Conditions used to convert the paper's tank volume + pressure into kg of H2.
TANK_H2_TEMPERATURE_K   = 288.15   # 15 C
TANK_H2_COMPRESSIBILITY = 1.017    # Z for H2 at ~28 bar; 1.0 would be ideal gas

TANK_LIFETIME_YEARS = 25   # the paper's plant lifetime; the tank is never replaced
# Electrolyser delivers at ~30 bar. Charged as electricity in the dispatch, not
# as tank capital. Zero for the 28 bar design, which needs no extra compression.
TANK_COMPRESSION_KWH_PER_KG = 0.0 if TANK_DESIGNS[TANK_DESIGN]["pressure_bar"] <= 30 else 2.5

# =============================================================================
# 4.3 wind -> data centre -> electrolyser -> tank -> fuel cell system model
# =============================================================================
SYS_DC_DEMAND_MW      = 7.31    # data centre continuous draw
SYS_WIND_CAPACITY_MW  = 50.0    # wind farm at WIND_LAT / WIND_LON
SYS_ELECTROLYSER_MW   = 25.0    # max rate surplus wind can be absorbed
SYS_TANK_CAPACITY_T   = 10.0    # tonnes of H2. There is a real optimum here: with the
                                # Gandiglio steel-mass tank, carbon falls to ~4.37 kt/yr at
                                # 5-10 t and rises either side — 20 t costs 4.71 because the
                                # vessel's own steel outweighs the grid import it displaces,
                                # and 0 t costs 5.07 because nothing rides through a lull.
                                # 5 t is within 1% of 10 t on half the steel, so if the tank
                                # model worries you, go smaller. The optimum moves up if you
                                # switch TANK_DESIGN to the lighter type1_200bar vessel.
SYS_FUELCELL_MW       = None    # None = size to the data centre's demand
SYS_START             = "2025-01-01"
SYS_END               = "2025-12-31"
SYS_INITIAL_SOC_FRAC  = 0.5     # tank fill at the start of the run
SYS_ALLOW_GRID_BACKUP = True    # False = report unserved load instead of importing

if SYS_FUELCELL_MW is None:
    SYS_FUELCELL_MW = SYS_DC_DEMAND_MW
for _n, _v in (("SYS_DC_DEMAND_MW", SYS_DC_DEMAND_MW), ("SYS_WIND_CAPACITY_MW", SYS_WIND_CAPACITY_MW),
               ("SYS_ELECTROLYSER_MW", SYS_ELECTROLYSER_MW), ("SYS_TANK_CAPACITY_T", SYS_TANK_CAPACITY_T),
               ("SYS_FUELCELL_MW", SYS_FUELCELL_MW)):
    if _v is None or _v < 0:
        raise ValueError(f"{_n} must be a non-negative number, got {_v!r}")
if not 0.0 <= SYS_INITIAL_SOC_FRAC <= 1.0:
    raise ValueError("SYS_INITIAL_SOC_FRAC must be between 0 and 1.")

# --- 4.2.datacentre_hydrogen.ipynb ---
# Backgrounds for the hydrogen chain's electricity. Carbon-only notebook.
DC_H2_WIND_QUERY  = "electricity production, wind, 1-3MW turbine, onshore"
DC_H2_WIND_LOC    = "GB"
DC_H2_GRID_QUERY  = "market for electricity, low voltage"
DC_H2_GRID_LOC    = "GB"
DC_OPERATION_YEARS = 25   # the data centre foreground's operating life
DC_H2_WIND_CAPACITIES_MW = [0, 10, 25, 50, 75, 100, 150, 200]   # wind farm sizes to sweep
DC_H2_WIND_YEAR = "2025"  # year of Renewables.ninja wind data to pull for the sweep

# --- derived ---
FC_ETA_NET_MEAN = FC_ETA_NET_BOL * FC_DEGRADATION_DERATE
FC_H2_PER_KWH   = 1.0 / (FC_ETA_NET_MEAN * FC_H2_LHV_KWH_PER_KG)      # kg H2 / kWh AC
FC_STACK_PER_KWH = 1.0 / (FC_RATED_POWER_KW * FC_STACK_LIFETIME_H)    # unit / kWh AC
FC_BOP_PER_KWH   = 1.0 / (FC_RATED_POWER_KW * FC_SYSTEM_LIFETIME_H)   # unit / kWh AC
# Maintenance events per kWh, tied to the stack-replacement rate above so the two
# can never disagree: ~6 services per stack, then x0.5 for ecoinvent's 2 kW unit.
FC_MAINT_PER_KWH = (FC_STACK_PER_KWH / FC_MAINT_STACK_FRACTION) * 0.5

if not 0.0 < FC_ETA_NET_BOL <= 1.0:
    raise ValueError("FC_ETA_NET_BOL must be a fraction in (0, 1].")
if not 0.0 < FC_DEGRADATION_DERATE <= 1.0:
    raise ValueError("FC_DEGRADATION_DERATE must be a fraction in (0, 1].")
if FC_STACK_LIFETIME_H <= 0 or FC_SYSTEM_LIFETIME_H <= 0:
    raise ValueError("Fuel cell lifetimes must be positive.")
if not 0.0 < FC_MAINT_STACK_FRACTION <= 1.0:
    raise ValueError("FC_MAINT_STACK_FRACTION must be a fraction in (0, 1].")

VALIDATION_N          = 0

# =============================================================================
# Wind + grid electrolyser run options (wind_power notebook)
# =============================================================================
RUN_WIND_GRID_LCA = True
WIND_LCA_MODE = 'blended'
WIND_METHOD_MODE = 'cheap'

# Renewables.ninja site/turbine settings
WIND_LAT = 51.732
WIND_LON = -0.3711
NINJA_DATASET               = "merra2"
NINJA_TURBINE = 'Vestas V90 2000'
NINJA_HUB_HEIGHT_M = 80.0
WIND_INSTALLED_CAPACITY_KW = 1000.0

# Electrolyser operating rule — list any subset of available techs.
ELECTROLYSER_TECHS = ['Data centre facility, hyperscale, Virginia (Zhang et al. 2025)']
ELECTROLYSER_CAPACITY_KW = 1000.0
MIN_LOAD_FRACTION = 0.1
WIND_TO_HALFHOUR_METHOD   = "ffill"              # "ffill" or "linear"
USE_GETPASS = False

# Renewables.ninja API token. Leave empty to be prompted interactively.
NINJA_API_TOKEN           = ""

WIND_BACKGROUND_QUERY = "electricity production, wind, 1-3MW turbine, onshore GB"
WIND_BACKGROUND_INDEX = 0

# =============================================================================
# Wind + grid data centre run options (4.1.datacentre_wind_power notebook)
# =============================================================================
# Reuses the same wind installation (WIND_LAT/WIND_LON/turbine settings above)
# and the same GRID_TIME_MODE/GRID_RANGE_START/GRID_RANGE_END "timescale of
# choice" as the electrolyser notebook — only the demand side (data centre's
# average operational power draw, computed from its own foreground activity)
# and the LCA mode/method are kept separate, so re-running one notebook never
# has to touch the other's settings.
RUN_DC_WIND_GRID_LCA = True
DC_WIND_LCA_MODE     = 'blended'   # 'blended', 'switching', or 'both'
DC_WIND_METHOD_MODE  = "cheap"     # cheap-method only is supported (see notebook 4.1) — thousands of slices
DC_MIN_LOAD_FRACTION = MIN_LOAD_FRACTION  # reuse the electrolyser's 10% default; override here if wanted

# =============================================================================
# Price data run options (5.prices notebook)
# =============================================================================
RUN_PRICE_DATA = True
PRICE_OUTPUT_DIR = "price_outputs"

# Mirror grid/wind notebook time selection unless you intentionally override.
PRICE_TIME_MODE        = GRID_TIME_MODE
PRICE_SINGLE_DATETIME  = GRID_SINGLE_DATETIME
PRICE_RANGE_START      = GRID_RANGE_START
PRICE_RANGE_END        = GRID_RANGE_END
PRICE_GRID_CSV_PATH    = CSV_PATH

# Elexon BMRS Market Index Data for half-hourly wholesale electricity price.
# APXMIDP is the main provider; N2EXMIDP is retained as a fallback/sensitivity.
ELEXON_API_BASE = "https://data.elexon.co.uk/bmrs/api/v1"
ELEXON_MARKET_INDEX_PROVIDER = "APXMIDP"
ELEXON_MARKET_INDEX_FALLBACK_PROVIDER = "N2EXMIDP"
ELEXON_CHUNK_DAYS = 7
ELEXON_REQUEST_SLEEP_S = 0.15
ELEXON_TIMEOUT_S = 60
ELECTRICITY_DELIVERED_UPLIFT_GBP_PER_MWH = 0.0

# NESO Green Hydrogen Data Portal: PEM and Alkaline electrolyser cost assumptions.
NESO_API_BASE = "https://api.neso.energy/api/3/action"
NESO_ELECTROLYSER_RESOURCE_ID = "88cfa584-db79-4573-a0c0-c14086257f8f"
NESO_LIMIT = 5000

# Proxy electrolyser assumptions used if NESO returns no usable rows.
USE_ELECTROLYSER_PROXY_IF_NESO_EMPTY = True
PROXY_ELECTROLYSER_BUILD_YEAR = 2025
PROXY_ELECTROLYSER_CAPEX_GBP_PER_KWE = {
    "Alkaline": {"low": 700,  "central": 1200, "high": 1700},
    "PEM":      {"low": 850,  "central": 1450, "high": 2100},
    "SOEC":     {"low": 1500, "central": 2500, "high": 3500},
}
PROXY_ELECTROLYSER_EFFICIENCY_PCT = {
    "Alkaline": 70.0,
    "PEM": 67.0,
    "SOEC": 80.0,
}
PROXY_ELECTROLYSER_FIXED_OPEX_PCT_CAPEX = {
    "Alkaline": 0.03,
    "PEM": 0.04,
    "SOEC": 0.04,
}
PROXY_ELECTROLYSER_LIFETIME_YEARS = {
    "Alkaline": 20,
    "PEM": 20,
    "SOEC": 20,
}

COST_CASE = "central"                            # "low", "central", or "high"
WIND_COST_CASE = COST_CASE
ELECTROLYSER_COST_SCENARIO = "central"
ELECTROLYSER_COST_BUILD_YEAR = 2025

# Battery cost placeholders for optimisation.
BATTERY_CAPEX_GBP_PER_MWH = {"low": None, "central": None, "high": None}
BATTERY_FIXED_OPEX_PCT_CAPEX = {"low": None, "central": None, "high": None}
BATTERY_LIFETIME_YEARS = {"low": None, "central": None, "high": None}

# =============================================================================
# Output folders
# =============================================================================
GRID_OUTPUT_DIR            = "custom_grid_lca_outputs"
WIND_OUTPUT_DIR_BLENDED    = "blended_wind_grid_lca_outputs"
WIND_OUTPUT_DIR_SWITCHING  = "hybrid_wind_grid_lca_outputs"

# =============================================================================
# Ecoinvent candidate templates
# =============================================================================
SHOW_FOREGROUND_ECOINVENT_CANDIDATES = True
SHOW_GRID_ECOINVENT_CANDIDATES = False

# =============================================================================
# Helper functions
# =============================================================================
def normalise_grid_data_source(value=None):
    raw = str(value or GRID_DATA_SOURCE).strip().lower()
    aliases = {
        "3": "csv", "4": "csv", "old": "csv", "ckan": "csv", "eso_csv": "csv", "csv": "csv",
        "3.1": "carbon_api", "4.1": "carbon_api", "api": "carbon_api", "carbon": "carbon_api",
        "carbon_api": "carbon_api", "carbon_intensity_api": "carbon_api",
    }
    if raw not in aliases:
        raise ValueError(
            f"Invalid GRID_DATA_SOURCE {value!r}. Use 'csv'/'3' or 'carbon_api'/'3.1' "
            "('4'/'4.1' also still accepted)."
        )
    return aliases[raw]

GRID_SOURCE_NORMALIZED = normalise_grid_data_source(GRID_DATA_SOURCE)
GRID_NOTEBOOK_BY_SOURCE = {
    "csv": "3.custom_grid.ipynb",
    "carbon_api": "3.1.custom_grid_carbon_intensity_api.ipynb",
}
SELECTED_GRID_NOTEBOOK = GRID_NOTEBOOK_BY_SOURCE[GRID_SOURCE_NORMALIZED]


def capital_recovery_factor(rate, lifetime_years):
    """Return the capital recovery factor for annualising CAPEX."""
    rate = float(rate)
    lifetime_years = float(lifetime_years)
    if lifetime_years <= 0:
        raise ValueError("lifetime_years must be positive")
    if rate == 0:
        return 1.0 / lifetime_years
    return rate * (1.0 + rate) ** lifetime_years / ((1.0 + rate) ** lifetime_years - 1.0)


def selected_cost(mapping, case=None):
    """Return low/central/high value from a cost dictionary."""
    chosen_case = case or COST_CASE
    if chosen_case not in mapping:
        raise ValueError(f"Invalid cost case {chosen_case!r}; expected one of {list(mapping)}")
    return mapping[chosen_case]

# =============================================================================
# Derived settings — do not normally edit below this line
# =============================================================================
if METHOD_MODE not in ("exact", "cheap"):
    raise ValueError("METHOD_MODE must be 'exact' or 'cheap'")
if GRID_TIME_MODE not in ("single", "range", "year_average"):
    raise ValueError("GRID_TIME_MODE must be 'single', 'range' or 'year_average'")
if WIND_LCA_MODE not in ("blended", "switching", "both"):
    raise ValueError("WIND_LCA_MODE must be 'blended', 'switching', or 'both'")
if WIND_METHOD_MODE not in ("exact", "cheap"):
    raise ValueError("WIND_METHOD_MODE must be 'exact' or 'cheap'")
if DC_WIND_LCA_MODE not in ("blended", "switching", "both"):
    raise ValueError("DC_WIND_LCA_MODE must be 'blended', 'switching', or 'both'")
if DC_WIND_METHOD_MODE != "cheap":
    raise ValueError("DC_WIND_METHOD_MODE must be 'cheap' — 'exact' isn't supported by notebook 4.1.")
if PRICE_TIME_MODE not in ("single", "range", "year_average"):
    raise ValueError("PRICE_TIME_MODE must be 'single', 'range' or 'year_average'")
if COST_CASE not in ("low", "central", "high"):
    raise ValueError("COST_CASE must be 'low', 'central', or 'high'")
if WIND_COST_CASE not in ("low", "central", "high"):
    raise ValueError("WIND_COST_CASE must be 'low', 'central', or 'high'")

if not isinstance(ELECTROLYSER_TECHS, (list, tuple)) or len(ELECTROLYSER_TECHS) == 0:
    raise ValueError("ELECTROLYSER_TECHS must be a non-empty list, e.g. ['PEM operation'].")
ELECTROLYSER_TECHS = list(ELECTROLYSER_TECHS)
_valid_electrolysers = ("AE operation", "PEM operation", "SOEC operation")
_bad = [t for t in ELECTROLYSER_TECHS if t not in _valid_electrolysers and t not in TECH_SOURCE_OVERRIDES]
if _bad:
    raise ValueError(
        f"Invalid ELECTROLYSER_TECHS {_bad}. Must be one of {list(_valid_electrolysers)}, "
        "or a label present in TECH_SOURCE_OVERRIDES."
    )

MARKET_LOSS_FACTOR = (1.0 + MARKET_LOSS_SHARE) if APPLY_LOSSES else 1.0
MIN_WIND_POWER_KW  = ELECTROLYSER_CAPACITY_KW * MIN_LOAD_FRACTION

if TECH_SELECTED:
    SELECTED_LCA_TECHS = [
        t for t in TECH_SELECTED if t in TECH_ORDER_DEFAULT or t in TECH_SOURCE_OVERRIDES
    ]
else:
    SELECTED_LCA_TECHS = TECH_ORDER_DEFAULT[: max(1, int(TECH_COUNT))]

if not SELECTED_LCA_TECHS and RUN_GRID_SCENARIO_LCA:
    raise ValueError("No valid technologies selected. Check TECH_SELECTED / TECH_COUNT.")


def print_dashboard():
    """Print the active configuration. Useful at the top of every notebook."""
    print("Master Dashboard")
    print("----------------")
    print("Project:                ", PROJECT_NAME)
    print("Foreground DB:          ", FOREGROUND_DB)
    print("Run adaptive foreground:", RUN_FOREGROUND_NOTEBOOK_FROM_DASHBOARD)
    print("Run adaptive grid:      ", RUN_GRID_NOTEBOOK_FROM_DASHBOARD)
    print("Run adaptive wind/grid: ", RUN_WIND_NOTEBOOK_FROM_DASHBOARD)
    print("Run adaptive prices:    ", RUN_PRICE_NOTEBOOK_FROM_DASHBOARD)
    print("Grid data source:       ", GRID_SOURCE_NORMALIZED, "| notebook:", SELECTED_GRID_NOTEBOOK)
    print("Run grid scenario LCA:  ", RUN_GRID_SCENARIO_LCA)
    print("Run wind/grid LCA:      ", RUN_WIND_GRID_LCA)
    print("Run price data:         ", RUN_PRICE_DATA)
    print("Grid method:            ", METHOD_MODE, "| loss factor:", MARKET_LOSS_FACTOR)
    print("Wind/grid method:       ", WIND_METHOD_MODE)
    print("Selected grid techs:    ", SELECTED_LCA_TECHS)
    print("Wind/grid mode:         ", WIND_LCA_MODE,
          "(blended + switching)" if WIND_LCA_MODE == "both" else "",
          "| electrolyser(s):", ELECTROLYSER_TECHS)
    print("Price output dir:       ", PRICE_OUTPUT_DIR)
    print("Elexon provider:        ", ELEXON_MARKET_INDEX_PROVIDER,
          "| fallback:", ELEXON_MARKET_INDEX_FALLBACK_PROVIDER)
    print("Cost case:              ", COST_CASE, "| wind:", WIND_COST_CASE)
