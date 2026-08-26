"""Every number, bound and option list the Streamlit widgets start from.

Change a value here and the UI changes. Nothing in this file is computed —
it is a flat list of constants so it can be read top to bottom.

Naming: ``<PAGE>_<THING>``, with ``_MIN`` / ``_MAX`` / ``_STEP`` suffixes where the
widget takes bounds. Page prefixes:

    SETUP_  page 1, Setup LCA
    ELY_    page 2, Electrolyser Optimiser
    DC_     page 3, Data Centre Optimiser

Two things deliberately do NOT live here:

* Values already centralised in ``dashboard_config.py`` (site coordinates,
  turbine, capacities, time period). Those are the notebooks' settings too, so
  duplicating them here would create a second source of truth.
* Cost and carbon coefficients. Those belong to ``optimisation/`` so that the
  headless ``scripts/run_dc_scenarios.py`` uses exactly the same numbers.

Values marked MODELLING ASSUMPTION are study inputs, not UI convenience —
changing them changes results, not just the starting position of a widget.
"""

from __future__ import annotations

import datetime as dt

# =============================================================================
# Shared across pages
# =============================================================================
COST_CASES = ["low", "central", "high"]
COST_CASE_INDEX = 1                      # "central"

ANSWER_POINTS = ["knee", "min_cost", "min_gwp"]

LCA_METHODS = ["cheap", "exact"]
LCA_METHOD_INDEX = 0                     # "cheap" — decompose once, reuse per timeslice

# =============================================================================
# Page 1 — Setup LCA
# =============================================================================
SETUP_STRATEGY_GRID_ONLY = "Grid only"
SETUP_STRATEGIES = [
    SETUP_STRATEGY_GRID_ONLY,
    "Wind + grid (blended)",
    "Wind + grid (switching)",
    "Wind + grid (both)",
]
SETUP_WIND_MODE_BY_STRATEGY = {
    "Wind + grid (blended)": "blended",
    "Wind + grid (switching)": "switching",
    "Wind + grid (both)": "both",
}

SETUP_TURBINE_OTHER = "Other…"
SETUP_TURBINE_OPTIONS = [
    "Vestas V90 2000",
    "Vestas V80 2000",
    "Siemens SWT 2300",
    "Enercon E70 2300",
    SETUP_TURBINE_OTHER,
]

SETUP_WIND_CAPACITY_KW_MIN = 0.0
SETUP_WIND_CAPACITY_KW_STEP = 100.0

SETUP_HUB_HEIGHT_M_MIN = 0.0

SETUP_ELECTROLYSER_KW_MIN = 0.0
SETUP_ELECTROLYSER_KW_STEP = 100.0

SETUP_MIN_LOAD_MIN = 0.0
SETUP_MIN_LOAD_MAX = 1.0

SETUP_TIME_MODES = ["single", "range", "year_average"]
SETUP_YEAR_MIN = 2015

# Monte Carlo uncertainty analysis
SETUP_MC_ITER_MIN = 20
SETUP_MC_ITER_MAX = 1000
SETUP_MC_ITER = 50
SETUP_MC_ITER_STEP = 10
SETUP_MC_TEMPLATE_ROWS = 5
SETUP_MC_SECONDS_PER_ITER_LOW = 3.5      # only used to estimate runtime in a caption
SETUP_MC_SECONDS_PER_ITER_HIGH = 4.5

# =============================================================================
# Page 2 — Electrolyser Optimiser
# =============================================================================
ELY_TECH = "PEM operation"

ELY_RATING_MW_MIN = 0.1
ELY_RATING_MW_MAX = 1000.0
ELY_RATING_MW = 10.0
ELY_RATING_MW_STEP = 1.0

ELY_MIN_LOAD_MIN = 0.0
ELY_MIN_LOAD_MAX = 0.5
ELY_MIN_LOAD = 0.10                      # MODELLING ASSUMPTION: stack turndown floor
ELY_MIN_LOAD_STEP = 0.05

ELY_CLEAN_THRESHOLD_MIN = 0.0
ELY_CLEAN_THRESHOLD_MAX = 0.5
ELY_CLEAN_THRESHOLD = 0.05               # kg CO2e/kWh, grid_when_clean strategy only
ELY_CLEAN_THRESHOLD_STEP = 0.01

ELY_LAT_MIN, ELY_LAT_MAX = -90.0, 90.0
ELY_LON_MIN, ELY_LON_MAX = -180.0, 180.0

# The dispatch window. Grid and price CSVs must already cover it continuously.
ELY_START_DATE = dt.date(2025, 1, 1)
ELY_END_DATE = dt.date(2025, 3, 31)

ELY_PV_TILT_MIN = 0.0
ELY_PV_TILT_MAX = 90.0
ELY_PV_TILT = 35.0                       # MODELLING ASSUMPTION: degrees
ELY_PV_TILT_STEP = 5.0

ELY_USE_LCHS = True
ELY_THRESHOLD_MIN = 0.1                  # g CO2e/MJ LHV
ELY_THRESHOLD_MAX = 200.0
ELY_THRESHOLD_STEP = 1.0

# Search space, as multiples of the electrolyser's rating.
ELY_WIND_MAX_MIN, ELY_WIND_MAX_MAX, ELY_WIND_MAX, ELY_WIND_MAX_STEP = 0.5, 50.0, 5.0, 1.0
ELY_SOLAR_MAX_MIN, ELY_SOLAR_MAX_MAX, ELY_SOLAR_MAX, ELY_SOLAR_MAX_STEP = 0.0, 50.0, 5.0, 1.0
ELY_BATT_MW_MIN, ELY_BATT_MW_MAX, ELY_BATT_MW, ELY_BATT_MW_STEP = 0.0, 20.0, 2.0, 0.5
ELY_BATT_H_MIN, ELY_BATT_H_MAX, ELY_BATT_H, ELY_BATT_H_STEP = 0.0, 48.0, 8.0, 1.0

# Differential-evolution solver settings.
ELY_MAXITER_MIN, ELY_MAXITER_MAX, ELY_MAXITER, ELY_MAXITER_STEP = 10, 120, 40, 10
ELY_POPSIZE_MIN, ELY_POPSIZE_MAX, ELY_POPSIZE, ELY_POPSIZE_STEP = 5, 30, 12, 1

ELY_DURATION_OPTIONS = [1, 2, 4, 8, 12]  # battery durations to tabulate, hours
ELY_DURATIONS = [1, 2, 4, 8]

# =============================================================================
# Page 3 — Data Centre Optimiser
# =============================================================================
# GB bounding box — the coordinate drives weather, grid region and TNUoS zone.
DC_LAT_MIN, DC_LAT_MAX = 49.0, 61.0
DC_LON_MIN, DC_LON_MAX = -9.0, 2.0
DC_COORD_STEP = 0.01

DC_CONNECTION_MW_MIN = 0.0
DC_CONNECTION_MW_MAX = 10_000.0
DC_CONNECTION_MW = 0.0                   # 0 means unconstrained
DC_CONNECTION_MW_STEP = 1.0

DC_TDR_BANDS = ["HV1", "HV2", "HV3", "HV4", "EHV1", "EHV2", "EHV3", "EHV4"]
DC_TDR_BAND_INDEX = 5                    # "EHV2", only used when overriding
DC_TDR_OVERRIDE = False                  # derive from agreed capacity by default

DC_IT_LOAD_MW_MIN = 0.1
DC_IT_LOAD_MW_MAX = 1000.0
DC_IT_LOAD_MW = 7.31                     # MODELLING ASSUMPTION: Zhang et al. baseline draw
DC_IT_LOAD_MW_STEP = 1.0

DC_PUE_MIN = 1.0
DC_PUE_MAX = 2.0
DC_PUE = 1.00                            # MODELLING ASSUMPTION: foreground is already facility-level
DC_PUE_STEP = 0.05

# The dispatch window. Real grid and price data exists for 2025 only.
DC_WINDOW_START = "2025-01-01"
DC_WINDOW_END = "2025-12-29"

DC_HORIZON_YEARS_MIN = 1.0
DC_HORIZON_YEARS_MAX = 50.0
DC_HORIZON_YEARS = 25.0                  # MODELLING ASSUMPTION: amortisation period
DC_HORIZON_YEARS_STEP = 1.0

DC_RESAMPLE_OPTIONS = [1.0, 0.5, 2.0]    # hours per timestep
DC_RESAMPLE_INDEX = 0                    # 1 h
DC_RESAMPLE_LABELS = {
    0.5: "30 min (native)",
    1.0: "1 h (recommended)",
    2.0: "2 h (exploration)",
}

DC_UNSERVED_MIN = 0.0
DC_UNSERVED_MAX = 0.10
DC_UNSERVED = 0.0                        # MODELLING ASSUMPTION: 0 is the data centre standard
DC_UNSERVED_STEP = 0.001

DC_SELECTION_CORE = "Core matrix (all 21)"
DC_SELECTION_MODES = [DC_SELECTION_CORE, "Pick configurations"]
DC_CONFIGS = [1, 2, 3]                   # pre-picked when not running the core matrix

DC_PARETO_POINTS_MIN = 2
DC_PARETO_POINTS_MAX = 20
DC_PARETO_POINTS = 12

DC_IGNORE_CACHE = False

# Only used to warn about runtime before a long run.
DC_SOLVE_WARN_THRESHOLD = 60             # LPs
DC_SECONDS_PER_SOLVE_LOW = 20
DC_SECONDS_PER_SOLVE_HIGH = 30
DC_CORES = 8

# Result-table columns: solver variable -> column heading.
DC_CAP_COLUMNS = [
    ("cap_wind", "Wind MW"),
    ("cap_offshore", "Offshore MW"),
    ("cap_solar", "Solar MWp"),
    ("cap_batt_p", "Battery MW"),
    ("cap_batt_e", "Battery MWh"),
    ("cap_ely", "Electrolyser MW"),
    ("cap_tank", "H₂ tank kg"),
    ("cap_fc", "Fuel cell MW"),
    ("cap_grid", "Grid MW"),
]
