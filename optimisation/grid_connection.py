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
The **materials** of the transformers that step the network down onto the
site — cradle-to-gate, the same boundary as the wind step-ups — charged per MW
of ``cap_grid``. The line that reaches the site is scored and reported but
not charged per MW (see ``decompose``). Switchgear, protection, the bay, civils,
the transformer's manufacturing energy, its losses and its end-of-life are
**not** counted, so this is a floor rather than an estimate.

The inventory is not here
-------------------------
The transformer is a foreground activity, ``TRANSFORMER_DB`` /
``registry.TX_GRID``, built by ``optimiser_lca/stepup_transformers.py`` from
Leng et al. (2026) Supplementary Table S1 alongside the wind step-ups: the
Gaoyou farm's grid-end main transformer, **XZ11-100000/110**, one 100 MVA
unit at 71,458.6 kg = **714.6 kg/MVA**, per 1 MVA of rating. This module only
scores it, sizes it per MW and amortises it.

It replaces ecoinvent 3.9.1's ``market for transformer, high voltage use``,
which by its own comment is a ~280 g electronic component "used in the
information and communication technology" — scored per kg and scaled by a
300 t / 240 MVA mass DERIVED from a GB 400 kV supergrid transformer that had no
citation. That gave 333.5 kg CO2e/MW/year; the dataset ran ~2x high per kg of
real transformer when the wind side was rebuilt the same way.

The voltage judgement
---------------------
Leng's unit is wound for **110 kV**. That fits a GB **132 kV** EHV/DNO
connection, which is the common case for a ~100 MW data centre. For a site
connected to the transmission system at **275 or 400 kV** it errs **LOW**:
supergrid transformers carry more insulation and are heavier per MVA. It is
used for every site as the default, whatever ``transmission_connected`` says,
and the direction of the error is registered in DATA_GAPS.md.

Sources
-------
transformer         Leng, H. et al. (2026), *Processes* 14(7), 1045,
                    Supplementary Table S1, main transformer XZ11-100000/110:
                    100 MVA, 71,458.6 kg. TRANSCRIBED into
                    ``stepup_transformers.TX_LENG_MAIN_KG``; materials on
                    ecoinvent 3.9.1 apos via ``TX_MATERIAL_PROCESSES``.
line                ecoinvent 3.9.1 apos, ``market for transmission network,
                    electricity, high voltage`` [GLO], per km. TRANSCRIBED.
redundancy          2 transformers for N-1. ASSUMED.
power factor        1.0, MW -> MVA. ASSUMED: a data centre's load is corrected
                    close to unity; a lower one would scale this up as 1/pf.
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

# The foreground activity optimiser_lca/stepup_transformers.py builds, per MVA.
# What the transformer is made of lives there; this module only scores it.
from optimiser_lca.registry import TRANSFORMER_DB, TX_GRID as TRANSFORMER_CODE  # noqa: E402

LINE_ACTIVITY = "market for transmission network, electricity, high voltage"

TRANSFORMER_REDUNDANCY = 2.0              # ASSUMED: N-1
LINE_KM = 2.0                             # ASSUMED, site-specific
ASSET_LIFE_YEARS = 40.0                   # ASSUMED
POWER_FACTOR = 1.0                        # ASSUMED: MW -> MVA

ASSUMED = ("TRANSFORMER_REDUNDANCY", "POWER_FACTOR", "LINE_KM", "ASSET_LIFE_YEARS",
           "Leng's 110 kV unit for every connection voltage")

_CACHE: dict | None = None


def transformer_kg_per_mva() -> float:
    """Leng's main transformer mass per MVA of rating. No Brightway needed."""
    from optimiser_lca import stepup_transformers as tx
    return sum(tx.TX_LENG_MAIN_KG.values()) / tx.TX_LENG_MAIN_MVA


def decompose(refresh: bool = False) -> dict:
    """kg CO2e per MW of connection per year, and the parts it came from."""
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE

    import bw2data as bd
    import lca_helpers as H
    from optimisation import baseline_grid as bg
    from optimiser_lca import stepup_transformers as tx

    H.setup_brightway()
    method = bg.gwp_method()
    tx.check()

    try:
        act = bd.get_activity((TRANSFORMER_DB, TRANSFORMER_CODE))
    except Exception:
        raise RuntimeError(
            f"{TRANSFORMER_DB!r}/{TRANSFORMER_CODE!r} is not in this Brightway project. "
            "Run `python -m optimiser_lca.build stepup_transformers` first — the "
            "inventory lives in optimiser_lca/stepup_transformers.py, not here.") from None
    per_mva = H.run_lca_score(act, method)
    per_km = H.run_lca_score(H.resolve_exact(LINE_ACTIVITY, "GLO", unit="kilometer"), method)

    mva_per_mw = TRANSFORMER_REDUNDANCY / POWER_FACTOR
    kg_per_mva = transformer_kg_per_mva()
    tx_per_mw = per_mva * mva_per_mw
    line_total = per_km * LINE_KM

    _CACHE = {
        "transformer_database": TRANSFORMER_DB,
        "transformer_code": TRANSFORMER_CODE,
        "transformer_source": "Leng et al. 2026, Processes 14(7) 1045, Table S1, "
                              "main transformer XZ11-100000/110",
        "transformer_rating_MVA": float(tx.TX_LENG_MAIN_MVA),
        "transformer_kV": float(tx.TX_LENG_MAIN_KV),
        "kgco2e_per_MVA_transformer": per_mva,
        "transformer_kg_per_MVA": kg_per_mva,
        # Implied, for comparison with the old ecoinvent basis (5.34 kg/kg).
        "kgco2e_per_kg_transformer": per_mva / kg_per_mva,
        "transformer_MVA_per_MW": mva_per_mw,
        "transformer_kg_per_MW": kg_per_mva * mva_per_mw,
        "transformer_kgco2e_per_MW": tx_per_mw,
        "kgco2e_per_km_line": per_km,
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
    print(f"  transformer          {TRANSFORMER_DB}/{TRANSFORMER_CODE}")
    print(f"  {d['transformer_source']}")
    print(f"  {d['transformer_rating_MVA']:g} MVA at {d['transformer_kV']:g} kV, "
          f"{d['transformer_kg_per_MVA']:,.1f} kg/MVA, materials only")
    print(f"                       {d['kgco2e_per_MVA_transformer']:>12,.1f} kgCO2e/MVA"
          f"  ({d['kgco2e_per_kg_transformer']:.2f} kgCO2e/kg)")
    print(f"  x {d['transformer_MVA_per_MW']:g} MVA/MW  "
          f"({TRANSFORMER_REDUNDANCY:g} for N-1 / power factor {POWER_FACTOR:g})")
    print(f"  = {d['transformer_kgco2e_per_MW']:>12,.0f} kgCO2e/MW installed")
    print(f"  over {d['asset_life_years']:g} years"
          f"  -> {d['kgco2e_per_MW_year']:>10,.1f} kgCO2e/MW/year")
    print()
    print(f"  line, {d['line_km']:g} km      {d['line_kgco2e_total']:>12,.0f} kgCO2e"
          f"  -> {d['line_kgco2e_per_year']:,.0f} kgCO2e/year, not charged per MW")
    print()
    print(f"  For scale, wind is 18,807 kgCO2e/MW/year, so a connection is about "
          f"{d['kgco2e_per_MW_year'] / 18807 * 100:.1f}% of a wind farm's per-MW burden.")
    print("  Was 333.5 kgCO2e/MW/year on ecoinvent's 280 g electronics transformer.")
    print(f"  A {d['transformer_kV']:g} kV unit fits a 132 kV EHV/DNO connection; for a "
          "275/400 kV site it errs LOW.")
    print(f"  ASSUMED: {', '.join(ASSUMED)}.")
    print("  Switchgear, protection, civils, the bay, manufacturing energy, losses")
    print("  and end-of-life are not counted, so this is a floor.")
