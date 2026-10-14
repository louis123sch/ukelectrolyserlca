"""
Transformer conversion losses — the energy each voltage step costs.
=============================================================================

The LP's node balance used to treat a kWh at a generator's terminals as a kWh
at the data centre, while every kWh imported already paid its delivery losses
down to high voltage (``optimiser_lca.grid.DELIVERY``, ×1.0338). That flattered
on-site generation against import, one way only. ``transformers.py`` and
``grid_connection.py`` charge the transformers' *capital*; this module charges
their *losses*, which two manufacturer EPDs put at ~99 % of a transformer's
life-cycle GWP. The lost kWh is not given a carbon coefficient: it has to be
generated or imported, by plant and connections the LP already sizes and
charges, so it enters as energy and its carbon follows.

Three steps, each a transformer the study already inventories:

* **wind** — one turbine step-up per turbine, Leng et al. (2026)'s 2.2 MVA unit,
  50 per 100 MW (1.1 MVA per MW);
* **solar** — IEA PVPS T12-33:2026's 2.5 MVA inverter-station unit, 4 per 10 MWp
  (1.0 MVA per MWp);
* **grid intake** — Leng's 100 MVA main transformer, two per MW of connection
  for N-1 (``grid_connection.TRANSFORMER_REDUNDANCY``), each carrying half.

Loss figures are the GB legal maxima, retained Commission Regulation (EU)
No 548/2014 Annex I, Tier 2 (from 1 July 2021), read on legislation.gov.uk on
14 Oct 2026. A real unit is at or below them, so these err high — but only
by the margin a design beats the floor of the regulation.

How the losses enter a linear model
-----------------------------------
A transformer of rating S carrying power p loses ``Po + Pk (p/S)²``.

* **No-load loss** ``Po`` is drawn whenever the unit is energised, which is
  always: a demand on the node of ``Po/S`` MW per MVA installed, so it scales
  with capacity, not output.
* **Load loss** is quadratic. It is linearised as ``Pk/S · x_eff · p``, where
  ``x_eff = Σx² / Σx`` is the energy-weighted loading. That is exact in energy
  terms when the unit carries its availability profile; ``dc_model`` computes
  it from the window's own capacity factors, so it follows the site and the
  resampling. Curtailment lowers the true loading, so this errs slightly high.
  The grid intake's loading is a solve outcome, so it takes an ASSUMED
  ``x_eff`` instead.

Out of scope: inverter and PCS losses (inside the battery's round-trip
efficiency and the fuel cell's net efficiency), and the data centre's own
distribution, which the PUE carries.
"""
from __future__ import annotations

# --- transcribed: Regulation (EU) No 548/2014 Annex I, Tier 2 ----------------
# Table I.1, three-phase liquid-immersed medium power transformers ≤ 3,150 kVA.
# rated kVA: (maximum load losses Pk W, maximum no-load losses Po W)
TABLE_I1_TIER2 = {
    1_000: (7_600, 693),
    2_000: (15_000, 1_305),
    2_500: (18_500, 1_575),
    3_150: (23_000, 1_980),
}
# Table I.7, minimum Peak Efficiency Index, liquid-immersed large power
# transformers, rated power ≥ 100 MVA.
PEI_TIER2_GE_100MVA = 0.99770
SOURCE = ("Commission Regulation (EU) No 548/2014 (retained), Annex I, Tier 2, "
          "Tables I.1 and I.7; legislation.gov.uk, read 14 Oct 2026")

# --- assumed -----------------------------------------------------------------
# Loading at which a large power transformer reaches its peak efficiency. The
# PEI gives total loss at that loading (2 Po), not the split between Po and Pk,
# which k_PEI sets: Pk = Po / k_PEI². 0.4 is a typical design point. ASSUMED.
LARGE_TX_K_PEI = 0.4
# Energy-weighted loading of the grid intake, Σx²/Σx on the connection
# rating. Its imports are a solve outcome, so this cannot be read off a
# profile. ASSUMED; at 0.5 the intake's load loss is 0.07 % of imports.
GRID_INTAKE_X_EFF = 0.5

# --- the study's units -----------------------------------------------------
WIND_UNIT_KVA = 2_200          # Leng et al. 2026 Table S1, one per turbine
WIND_MVA_PER_MW = 50 * 2.2 / 100.0
SOLAR_UNIT_KVA = 2_500         # IEA PVPS T12-33:2026 Table 49
SOLAR_MVA_PER_MWP = 0.4 * 2.5  # Table 50: 4 units per 10 MWp


def _medium(kva: float) -> tuple[float, float]:
    """(Pk, Po) as fractions of rating, interpolated linearly in Table I.1.

    Leng's 2.2 MVA unit is wound for 35 kV, above the table's 24 kV class;
    it is read off the table anyway as the nearest legal limit, and noted.
    """
    pts = sorted(TABLE_I1_TIER2)
    if not pts[0] <= kva <= pts[-1]:
        raise ValueError(f"{kva} kVA is outside Table I.1's transcribed rows")
    lo = max(p for p in pts if p <= kva)
    hi = min(p for p in pts if p >= kva)
    w = 0.0 if hi == lo else (kva - lo) / (hi - lo)
    pk = TABLE_I1_TIER2[lo][0] + w * (TABLE_I1_TIER2[hi][0] - TABLE_I1_TIER2[lo][0])
    po = TABLE_I1_TIER2[lo][1] + w * (TABLE_I1_TIER2[hi][1] - TABLE_I1_TIER2[lo][1])
    return pk / (kva * 1000.0), po / (kva * 1000.0)


def _large() -> tuple[float, float]:
    """(Pk, Po) as fractions of rating for a ≥ 100 MVA unit, from its PEI.

    PEI = 1 - 2 Po / (k S) at the loading k where load loss equals no-load
    loss, so Po/S = (1 - PEI) k / 2 and Pk/S = (Po/S) / k².
    """
    po = (1.0 - PEI_TIER2_GE_100MVA) * LARGE_TX_K_PEI / 2.0
    return po / LARGE_TX_K_PEI ** 2, po


def stepup(technology: str) -> dict:
    """Per MW (MWp for solar) of generation capacity.

    ``noload_mw_per_mw``: MW drawn at the node per MW installed, every hour.
    ``load_loss_per_mw_at_full_loading``: the load-loss share of delivered
    power when the unit runs at its full MW rating. ``dc_model`` multiplies it
    by the profile's x_eff.
    """
    if technology in ("onshore_wind", "offshore_wind"):
        kva, mva_per_mw = WIND_UNIT_KVA, WIND_MVA_PER_MW
    elif technology == "solar_pv":
        kva, mva_per_mw = SOLAR_UNIT_KVA, SOLAR_MVA_PER_MWP
    else:
        raise ValueError(f"no step-up for {technology!r}")
    pk, po = _medium(kva)
    # A unit rated r MVA per MW carries x MW per MW at loading x/r of its
    # rating, so its load loss per MW delivered is Pk/S · x / r.
    return {"noload_mw_per_mw": po * mva_per_mw,
            "load_loss_per_mw_at_full_loading": pk / mva_per_mw,
            "unit_kVA": kva, "MVA_per_MW": mva_per_mw}


def grid_intake() -> dict:
    """Per MW of ``cap_grid``: two units of 1/PF MVA each, sharing the load."""
    from optimisation import grid_connection as gc
    pk, po = _large()
    units, mva_each = gc.TRANSFORMER_REDUNDANCY, 1.0 / gc.POWER_FACTOR
    # Each of n units carries p/n at loading p/(n · mva_each · cap).
    load_frac = pk * GRID_INTAKE_X_EFF / (units * mva_each)
    return {"noload_mw_per_mw": po * units * mva_each,
            "load_loss_fraction": load_frac}


def describe() -> str:
    w, s, g = stepup("onshore_wind"), stepup("solar_pv"), grid_intake()
    return "\n".join([
        f"  wind step-up   no-load {w['noload_mw_per_mw'] * 100:.4f} % of capacity, "
        f"load {w['load_loss_per_mw_at_full_loading'] * 100:.3f} % of output at full loading",
        f"  solar step-up  no-load {s['noload_mw_per_mw'] * 100:.4f} % of capacity, "
        f"load {s['load_loss_per_mw_at_full_loading'] * 100:.3f} % of output at full loading",
        f"  grid intake    no-load {g['noload_mw_per_mw'] * 100:.4f} % of connection, "
        f"load {g['load_loss_fraction'] * 100:.3f} % of imports",
        f"  source: {SOURCE}",
    ])


if __name__ == "__main__":
    print(describe())
