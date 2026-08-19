"""
=============================================================================
MASTER DASHBOARD — single source of truth for the split notebooks.
=============================================================================

The intended entry point is now:

    2.dashboard_lca_adaptive.ipynb

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
DC_FOREGROUND_DB  = "data centre foreground"  # separate DB for non-hydrogen foregrounds (e.g. notebook 3's Zhang et al. data centre process)

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
# These control what 2.dashboard_lca_adaptive.ipynb runs when you Run All.
# Set RUN_FOREGROUND_NOTEBOOK_FROM_DASHBOARD=True only on first setup or after
# changing foreground inventories, because it can be slower than the other steps.
RUN_FOREGROUND_NOTEBOOK_FROM_DASHBOARD = False
RUN_GRID_NOTEBOOK_FROM_DASHBOARD = True
RUN_WIND_NOTEBOOK_FROM_DASHBOARD = True
RUN_PRICE_NOTEBOOK_FROM_DASHBOARD = False

# =============================================================================
# Grid data source selector
# =============================================================================
# "csv"        / "4"   = old 4.custom_grid.ipynb using df_fuel_ckan.csv
# "carbon_api" / "4.1" = new 4.1.custom_grid_carbon_intensity_api.ipynb
GRID_DATA_SOURCE = "carbon_api"

# CSV input for the old National Grid ESO half-hourly fuel mix workflow.
CSV_PATH = "df_fuel_ckan.csv"

# Carbon Intensity API input settings for 4.1.
CARBON_API_BASE = "https://api.carbonintensity.org.uk"
CARBON_API_SCOPE = "regional_auto"          # "regional_auto" or "national"
CARBON_API_REGION_ID_OVERRIDE = None        # e.g. 13 for London; leave None for auto from WIND_LAT/WIND_LON
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
GRID_YEAR             = 2025
GRID_REP_DECILE       = 0.10
GRID_WIND_COLS        = ["WIND", "WIND_EMB"]

METHOD_MODE           = "cheap"                  # "exact" or "cheap"
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
TECH_SELECTED = ['Alkaline electrolyser, Hermesmann']
TECH_COUNT    = 1

# Optional per-label source override: {label: (database_name, activity_code)}.
# Lets a technology label point at an activity outside FOREGROUND_DB — e.g. a
# process the AI-LCA foreground extractor wrote into its own database. Leave
# empty to use the built-in H2_CODES/ELECTROLYSER_CODES lookup as before.
# Populated by the Streamlit Setup-LCA page; safe to leave {} in notebook use.
TECH_SOURCE_OVERRIDES = {'Alkaline electrolyser, Hermesmann': ('hydrogen foreground', 'ae_hermesmann_1unit')}

VALIDATE_CHEAP_METHOD = False
VALIDATION_N          = 0

# =============================================================================
# Wind + grid electrolyser run options (wind_power notebook)
# =============================================================================
RUN_WIND_GRID_LCA = True
WIND_LCA_MODE = 'blended'
WIND_METHOD_MODE  = "cheap"                      # "exact" or "cheap"

# Renewables.ninja site/turbine settings
WIND_LAT                    = 51.7320
WIND_LON                    = -0.3711
NINJA_DATASET               = "merra2"
NINJA_TURBINE               = "Vestas V90 2000"
NINJA_HUB_HEIGHT_M          = 80
WIND_INSTALLED_CAPACITY_KW  = 1000.0

# Electrolyser operating rule — list any subset of available techs.
ELECTROLYSER_TECHS = ['Alkaline electrolyser, Hermesmann']
ELECTROLYSER_CAPACITY_KW  = 1000.0
MIN_LOAD_FRACTION         = 0.10
WIND_TO_HALFHOUR_METHOD   = "ffill"              # "ffill" or "linear"
USE_GETPASS = False

# Renewables.ninja API token. Leave empty to be prompted interactively.
NINJA_API_TOKEN           = ""

WIND_BACKGROUND_QUERY = "electricity production, wind, 1-3MW turbine, onshore GB"
WIND_BACKGROUND_INDEX = 0

# =============================================================================
# Price data run options (6.prices notebook)
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
        "4": "csv", "old": "csv", "ckan": "csv", "eso_csv": "csv", "csv": "csv",
        "4.1": "carbon_api", "api": "carbon_api", "carbon": "carbon_api",
        "carbon_api": "carbon_api", "carbon_intensity_api": "carbon_api",
    }
    if raw not in aliases:
        raise ValueError(
            f"Invalid GRID_DATA_SOURCE {value!r}. Use 'csv'/'4' or 'carbon_api'/'4.1'."
        )
    return aliases[raw]

GRID_SOURCE_NORMALIZED = normalise_grid_data_source(GRID_DATA_SOURCE)
GRID_NOTEBOOK_BY_SOURCE = {
    "csv": "4.custom_grid.ipynb",
    "carbon_api": "4.1.custom_grid_carbon_intensity_api.ipynb",
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
