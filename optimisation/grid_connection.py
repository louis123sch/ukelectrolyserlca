"""
Grid connection — embodied carbon per MW of connection.
=============================================================================

The one sized asset in ``dc_model`` that carried no carbon at all. Every other
capacity — wind, solar, battery power and energy, electrolyser, tank, fuel cell
— has an embodied coefficient; ``cap_grid`` had none, so a carbon-only solve
could not see the connection and had no reason to keep it small. On the 300 MW
Highland run that produced an 868 MW connection used for six hours a year, and
after the DUoS fix it produced a variable with a zero coefficient in *both*
objectives, whose reported size was whichever vertex the solver stopped at.

Why the cost side stays at zero, and why that is right
-----------------------------------------------------
It is tempting to read "£0/MW/year" as the same kind of hole. It is not. For a
transmission-connected **demand** site the use-of-system charge is the zonal
half-hourly demand tariff plus the TDR, and both are already modelled; NESO's
local substation tariffs are *generation* charges and do not apply. In a floored
TNUoS zone the zonal tariff really is £0.00/kW. What is missing on the cost side
is the **connection charge** for sole-use assets, which is bilateral under the
Connection Charging Methodology rather than a published £/MW tariff, so it
cannot be transcribed. That gap is registered in DATA_GAPS.md and is a different
gap from this one.

What is counted
---------------
The assets a connection actually adds: the transformers that step the site onto
the network, and the line that reaches it. Switchgear, protection, civils and
the bay itself are **not** counted, so this is a floor rather than an estimate.

Sources
-------
transformer         ecoinvent 3.9.1 apos, ``market for transformer, high
                    voltage use`` [GLO], scored per kg. TRANSCRIBED.
line                ecoinvent 3.9.1 apos, ``market for transmission network,
                    electricity, high voltage`` [GLO], per km. TRANSCRIBED.
transformer mass    ~300 t for a 400 kV supergrid transformer, against the
                    240 MVA rating standard for GB SGTs. DERIVED -> 1.25 t/MVA.
redundancy          2 transformers for N-1. ASSUMED.
line length         ASSUMED, and site-specific in reality. Deliberately short:
                    a data centre sited for its connection is near a substation.
asset life          40 years. ASSUMED, and typical for transmission plant —
                    longer than any generation asset in this study.

Run:  python optimisation/grid_connection.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRANSFORMER_ACTIVITY = "market for transformer, high voltage use"
LINE_ACTIVITY = "market for transmission network, electricity, high voltage"

TRANSFORMER_T_PER_MVA = 300.0 / 240.0     # DERIVED: GB 400 kV SGT
TRANSFORMER_REDUNDANCY = 2.0              # ASSUMED: N-1
LINE_KM = 2.0                             # ASSUMED, site-specific
ASSET_LIFE_YEARS = 40.0                   # ASSUMED
POWER_FACTOR = 1.0                        # MW -> MVA

ASSUMED = ("TRANSFORMER_REDUNDANCY", "LINE_KM", "ASSET_LIFE_YEARS")

_CACHE: dict | None = None


def decompose(refresh: bool = False) -> dict:
    """kg CO2e per MW of connection per year, and the parts it came from."""
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE

    import bw2data as bd
    import lca_helpers as H
    import dashboard_config as cfg
    from optimisation import baseline_grid as bg

    H.setup_brightway()
    method = bg.gwp_method()
    ei = bd.Database(cfg.ECOINVENT_DB if hasattr(cfg, "ECOINVENT_DB")
                     else "ecoinvent-3.9.1-apos")

    def score(name, unit):
        hits = [a for a in ei if a["name"] == name and a["unit"] == unit]
        if not hits:
            raise ValueError(f"{name!r} ({unit}) not in {ei.name}")
        return H.run_lca_score(hits[0], method)

    per_kg = score(TRANSFORMER_ACTIVITY, "kilogram")
    per_km = score(LINE_ACTIVITY, "kilometer")

    tx_kg_per_mw = TRANSFORMER_T_PER_MVA * 1000.0 * TRANSFORMER_REDUNDANCY / POWER_FACTOR
    tx_per_mw = per_kg * tx_kg_per_mw
    line_total = per_km * LINE_KM

    _CACHE = {
        "kgco2e_per_kg_transformer": per_kg,
        "kgco2e_per_km_line": per_km,
        "transformer_kg_per_MW": tx_kg_per_mw,
        "transformer_kgco2e_per_MW": tx_per_mw,
        "line_kgco2e_total": line_total,
        "line_km": LINE_KM,
        "asset_life_years": ASSET_LIFE_YEARS,
        # The line is a fixed cost of reaching the site, not a per-MW one, so it
        # is deliberately left out of the per-MW figure the LP uses: charging it
        # per MW would make a bigger connection look worse than it is for a
        # reason that has nothing to do with its size. It is reported here so it
        # can be added to the fixed term if a run wants it.
        "kgco2e_per_MW_year": tx_per_mw / ASSET_LIFE_YEARS,
        "line_kgco2e_per_year": line_total / ASSET_LIFE_YEARS,
    }
    return _CACHE


def kgco2e_per_mw_year(refresh: bool = False) -> float:
    return decompose(refresh)["kgco2e_per_MW_year"]


if __name__ == "__main__":
    d = decompose()
    print("=" * 78)
    print("GRID CONNECTION — embodied carbon per MW")
    print("=" * 78)
    print(f"  transformer          {d['kgco2e_per_kg_transformer']:>12,.2f} kgCO2e/kg")
    print(f"  x {d['transformer_kg_per_MW']:>10,.0f} kg/MW  "
          f"({TRANSFORMER_T_PER_MVA:.2f} t/MVA x {TRANSFORMER_REDUNDANCY:g} for N-1)")
    print(f"  = {d['transformer_kgco2e_per_MW']:>12,.0f} kgCO2e/MW installed")
    print(f"  over {d['asset_life_years']:g} years"
          f"  -> {d['kgco2e_per_MW_year']:>10,.1f} kgCO2e/MW/year")
    print()
    print(f"  line, {d['line_km']:g} km      {d['line_kgco2e_total']:>12,.0f} kgCO2e"
          f"  -> {d['line_kgco2e_per_year']:,.0f} kgCO2e/year, not charged per MW")
    print()
    print(f"  For scale, wind is 18,807 kgCO2e/MW/year, so a connection is about "
          f"{d['kgco2e_per_MW_year'] / 18807 * 100:.1f}% of a wind farm's per-MW burden.")
    print(f"  ASSUMED: {', '.join(ASSUMED)}. Switchgear, protection, civils and the")
    print("  bay are not counted, so this is a floor.")
