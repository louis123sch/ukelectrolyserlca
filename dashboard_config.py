"""
=============================================================================
MASTER DASHBOARD — single source of truth for the split notebooks.
=============================================================================

Every notebook (tech_lca_foreground, custom_grid, wind_power, dashboard_lca)
imports its settings from this file. Edit values here once and they apply
everywhere — no per-notebook duplication.

Quick start:
    >>> from dashboard_config import *

Or in a notebook cell:
    >>> import dashboard_config as cfg
    >>> cfg.PROJECT_NAME
"""

# =============================================================================
# Brightway project / database settings
# =============================================================================
PROJECT_NAME      = "hydrogen-smr"
ECOINVENT_VERSION = "3.9.1"
SYSTEM_MODEL      = "apos"                       # "apos", "cutoff", "consequential", ...
FOREGROUND_DB     = "hydrogen foreground"

# Set True only if you need to import ecoinvent into the active Brightway
# project. Credentials are requested interactively at run time.
RUN_IMPORT_ECOINVENT = False

# Rebuilds the foreground database from the SimaPro-derived inventories.
# Leave False once the foreground database already exists.
RUN_BUILD_FOREGROUND_DATABASE = True

# Run a reference LCA on the foreground processes using their original electricity inputs.
RUN_REFERENCE_LCA = False

# =============================================================================
# CSV input (National Grid ESO half-hourly fuel mix)
# =============================================================================
CSV_PATH = "df_fuel_ckan.csv"

# =============================================================================
# Grid scenario run options (custom_grid notebook)
# =============================================================================
RUN_GRID_SCENARIO_LCA = True

GRID_TIME_MODE        = "year_average"                  # "single", "range" or "year_average"
GRID_SINGLE_DATETIME  = "2023-07-15 12:00:00"
GRID_RANGE_START      = "2025-01-01 00:00:00"
GRID_RANGE_END        = "2025-12-29 00:00:00"    # inclusive

# "year_average" mode: pick one whole year and run the LCA on 12 wind-based
# representative days (per season: the average-wind day, the top-10% wind day
# and the bottom-10% wind day). Each representative day is collapsed into a
# single energy-weighted daily-average grid mix, so a year => 12 results.
GRID_YEAR             = 2025                     # year used by "year_average" mode
GRID_REP_DECILE       = 0.10                     # top/bottom fraction for rep days
GRID_WIND_COLS        = ["WIND", "WIND_EMB"]     # columns summed as "wind"

METHOD_MODE           = "cheap"                  # "exact" or "cheap"
APPLY_LOSSES          = True
MARKET_LOSS_SHARE     = 0.031642692177

# Selected foreground technologies for the grid LCA.
# Leave TECH_SELECTED empty to use the first TECH_COUNT items from TECH_ORDER_DEFAULT.
TECH_ORDER_DEFAULT = [
    "SMR",
    "SMR-CCS",
    "AE operation",
    "PEM operation",
    "SOEC operation",
    "MP-E",
]
TECH_SELECTED = ["PEM operation"]  # e.g. ["SMR", "AE operation"]
TECH_COUNT    = 1

# Optional validation: compare cheap result with exact temp-activity result.
VALIDATE_CHEAP_METHOD = False
VALIDATION_N          = 0

# =============================================================================
# Wind + grid electrolyser run options (wind_power notebook)
# =============================================================================
RUN_WIND_GRID_LCA = True

# The wind notebook reuses the grid time window above
# (GRID_TIME_MODE / GRID_SINGLE_DATETIME / GRID_RANGE_START / GRID_RANGE_END)
# so both LCAs always cover the same period.

WIND_LCA_MODE     = "both"                    # "blended", "switching", or "both"

# LCA method for the wind/grid run — same idea as METHOD_MODE for the grid:
#   "exact" builds a temporary activity per slice and runs a full Brightway LCA.
#   "cheap" decomposes each electrolyser tech once (fixed non-electricity score
#           + direct electricity kWh) and combines it linearly with one-off wind
#           and closed-form grid electricity scores. Much faster, ~identical.
WIND_METHOD_MODE  = "cheap"                   # "exact" or "cheap"

# Renewables.ninja site/turbine settings
WIND_LAT                    = 51.7320
WIND_LON                    = -0.3711
NINJA_DATASET               = "merra2"
NINJA_TURBINE               = "Vestas V90 2000"
NINJA_HUB_HEIGHT_M          = 80
WIND_INSTALLED_CAPACITY_KW  = 1000.0

# Electrolyser operating rule — list any subset of available techs.
ELECTROLYSER_TECHS        = ["AE operation"]    # ["PEM operation", "AE operation", "SOEC operation"]
ELECTROLYSER_CAPACITY_KW  = 1000.0
MIN_LOAD_FRACTION         = 0.10
WIND_TO_HALFHOUR_METHOD   = "ffill"              # "ffill" or "linear"
USE_GETPASS               = True

# Renewables.ninja API token.
# Paste your token here (from https://www.renewables.ninja/profile).
# Leave empty to be prompted interactively when the wind notebook runs.
NINJA_API_TOKEN           = "75dc7f57e0cb6260173f2791f86ef06bc7ee750a"

# Selected background wind process for the foreground wind electricity process.
WIND_BACKGROUND_QUERY = "electricity production, wind, 1-3MW turbine, onshore GB"
WIND_BACKGROUND_INDEX = 0

# =============================================================================
# Output folders (results CSVs are saved here, then loaded by the dashboard)
# =============================================================================
GRID_OUTPUT_DIR            = "custom_grid_lca_outputs"
WIND_OUTPUT_DIR_BLENDED    = "blended_wind_grid_lca_outputs"
WIND_OUTPUT_DIR_SWITCHING  = "hybrid_wind_grid_lca_outputs"

# =============================================================================
# Ecoinvent candidate templates
# =============================================================================
# GRID_CANDIDATE_INDEX, GRID_INFRASTRUCTURE, GRID_EMISSIONS and
# SHOW_GRID_ECOINVENT_CANDIDATES are defined at the top of
# 4.custom_grid.ipynb — edit them there next to the candidate output.
#
# tech_lca_foreground.ipynb defines FOREGROUND_TEMPLATES + FOREGROUND_BIOSPHERE.
#
# Print the ecoinvent candidate lists for every foreground component.
SHOW_FOREGROUND_ECOINVENT_CANDIDATES = True

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

if not isinstance(ELECTROLYSER_TECHS, (list, tuple)) or len(ELECTROLYSER_TECHS) == 0:
    raise ValueError("ELECTROLYSER_TECHS must be a non-empty list, e.g. ['PEM operation'].")
ELECTROLYSER_TECHS = list(ELECTROLYSER_TECHS)
_valid_electrolysers = ("AE operation", "PEM operation", "SOEC operation")
_bad = [t for t in ELECTROLYSER_TECHS if t not in _valid_electrolysers]
if _bad:
    raise ValueError(f"Invalid ELECTROLYSER_TECHS {_bad}. Must be subset of {list(_valid_electrolysers)}.")

MARKET_LOSS_FACTOR = (1.0 + MARKET_LOSS_SHARE) if APPLY_LOSSES else 1.0
MIN_WIND_POWER_KW  = ELECTROLYSER_CAPACITY_KW * MIN_LOAD_FRACTION

if TECH_SELECTED:
    SELECTED_LCA_TECHS = [t for t in TECH_SELECTED if t in TECH_ORDER_DEFAULT]
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
    print("Build foreground DB:    ", RUN_BUILD_FOREGROUND_DATABASE)
    print("Run reference LCA:      ", RUN_REFERENCE_LCA)
    print("Run grid scenario LCA:  ", RUN_GRID_SCENARIO_LCA)
    print("Run wind/grid LCA:      ", RUN_WIND_GRID_LCA)
    print("Grid method:            ", METHOD_MODE, "| loss factor:", MARKET_LOSS_FACTOR)
    print("Wind/grid method:       ", WIND_METHOD_MODE)
    print("Selected grid techs:    ", SELECTED_LCA_TECHS)
    print("Wind/grid mode:         ", WIND_LCA_MODE,
          "(blended + switching)" if WIND_LCA_MODE == "both" else "",
          "| electrolyser(s):", ELECTROLYSER_TECHS)
