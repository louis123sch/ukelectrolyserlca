"""
=============================================================================
dc_config — the Data Centre Optimiser's fixed study settings.
=============================================================================

What goes in here: the Brightway project the study runs in, and the study
choices the ``optimisation/`` modules apply *after* an activity has been
scored — operating lives, amortisation periods, the PV array geometry.

What does not:

* **Inventories.** A number that changes an exchange amount — a bill of
  materials, a fuel-cell efficiency, a tank design, the grid's sources —
  lives with its inventory in ``optimiser_lca/`` (one module per LCA, each
  readable top to bottom). Database names and activity codes are in
  ``optimiser_lca/registry.py``.
* **Per-run inputs.** IT load, PUE, site, dates, which assets to consider and
  the objective are inputs on the optimiser page (or arguments to
  ``dc_runner`` / ``scripts/run_dc_*.py``); a grid build takes its region and
  window as arguments (``optimisation/grid_build.py``).

Nothing edits this file at run time. Edit, save, then restart whatever
imported it. Changing an inventory in ``optimiser_lca/`` means re-running
``python -m optimiser_lca.build``.
"""

# =============================================================================
# Brightway project
# =============================================================================
PROJECT_NAME      = "hydrogen-smr"
ECOINVENT_VERSION = "3.9.1"
SYSTEM_MODEL      = "apos"                       # "apos", "cutoff", "consequential", ...
ECOINVENT_DB      = f"ecoinvent-{ECOINVENT_VERSION}-{SYSTEM_MODEL}"

# Set True only if you need to import ecoinvent into the active Brightway project.
RUN_IMPORT_ECOINVENT = False

# =============================================================================
# Data centre facility (optimiser_lca/data_centre.py)
# =============================================================================
DC_OPERATION_YEARS = 25   # the Zhang foreground's operating life
# Zhang et al.'s own PUE. Used once, to read an IT load out of the foreground's
# facility draw; every other PUE in this study is the one the caller sets.
DC_REFERENCE_PUE = 1.4

# =============================================================================
# Amortisation — how long a scored asset is charged over (optimisation/)
# =============================================================================
TANK_LIFETIME_YEARS = 25     # Gandiglio's plant lifetime; the tank is never replaced
TX_ASSET_LIFE_YEARS = 35.0   # this study's own generation life; see renewables.py

# =============================================================================
# PV array geometry (optimisation/profiles.py)
# =============================================================================
# 20 deg is the tilt of the mounting structure whose embodied carbon is charged
# (optimiser_lca/upv.py, IEA PVPS T12-33:2026), and is GB utility-scale practice.
PV_TILT_DEG    = 20.0
PV_AZIMUTH_DEG = 180.0    # due south
PV_SYSTEM_LOSS = 0.10     # Renewables.ninja default. ASSUMED.
PV_TRACKING    = 0        # fixed tilt; the tracker variant is not this study


def print_dashboard():
    """Print the settings the study runs against."""
    from optimiser_lca import registry, fuel_cell, h2_tank, grid
    print("dc_config")
    print("---------")
    print("Brightway project:      ", PROJECT_NAME, f"({ECOINVENT_DB})")
    print("Foreground databases:   ", ", ".join(registry.DATABASES))
    print("Fuel cell:              ", f"eta {fuel_cell.FC_ETA_NET_MEAN:.3f} mean, "
          f"stack {fuel_cell.FC_STACK_LIFETIME_H:,} h, system {fuel_cell.FC_SYSTEM_LIFETIME_H:,} h")
    print("Hydrogen tank design:   ", h2_tank.TANK_DESIGN, f"({TANK_LIFETIME_YEARS} y)")
    print("Grid sources id:        ", grid.sources_id(), f"loss factor {grid.MARKET_LOSS_FACTOR}")
