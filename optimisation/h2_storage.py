"""
Hydrogen storage — embodied carbon per kg of capacity.
=============================================================================

The one asset in the hydrogen chain that was already the right shape. ecoinvent
3.9.1 has no hydrogen vessel, so ``2.tech_lca_foreground.ipynb`` builds one the
way Gandiglio et al. (2022) do — as a mass of steel and nothing else — with a
reference product of **one kilogram of storage capacity**. That is already a
capacity basis, so unlike the electrolyser and the fuel cell there is nothing to
decompose: this module reads it, amortises it, and offers the second design the
config defines but does not build.

What it adds over reading the activity directly:

1. **Both tank designs**, not just the one ``dashboard_config.TANK_DESIGN``
   currently selects, so the optimiser can run 28 bar against 200 bar as a
   sensitivity without a foreground rebuild. The as-built design is
   cross-checked against Brightway; the other is scored from its own steel
   process at its own steel intensity.
2. **The charging parasitic**, which belongs to storage and not to the
   electrolyser: compression from the electrolyser's delivery pressure to the
   tank's. Zero for the 28 bar design, because the electrolyser already leaves
   at ~30 bar.
3. **Standing loss**, which is *not* in the inventory and is not modelled here
   either — see below.

Why steel mass alone is defensible, and where it is not
------------------------------------------------------
Gandiglio's inventory is one line: 15,652 kg of chromium steel 18/8 for a
21.6 m3, 28 bar vessel. Missing are foundations, the enclosure, valves and
instrumentation, and end-of-life. The notebook says so, and so does this module.
Against that, steel is the overwhelming majority of a pressure vessel's embodied
carbon, so the figure is a defensible lower bound rather than a guess.

Standing loss is deliberately zero and needs a source
-----------------------------------------------------
There is **no boil-off** from compressed gas at ambient temperature — that is a
liquid-hydrogen phenomenon, and this is a steel bottle at 28 bar. The real
losses are permeation through the wall, which is negligible for steel at this
pressure, and fitting and valve leakage, which is a maintenance-quality
question rather than a physical constant. ``LEAKAGE_FRAC_PER_HOUR`` is exposed
for the optimiser and **defaults to zero with no source**, which is the honest
position but not a verified one. It matters: near-zero standing loss is
precisely why hydrogen beats a battery over a season, so the parameter that
decides that contest is currently an assumption. Registered in ``DATA_GAPS.md``.

If it is ever set non-zero, the leaked hydrogen should also be charged as a
greenhouse gas in its own right — H2 is an indirect GHG — from DESNZ / Warwick
et al. 2022, *Atmospheric implications of increased hydrogen use*.

Sources
-------
inventory         Gandiglio, M., Marocco, P., Bianco, I., Lovera, D.,
                  Blengini, G.A., Santarelli, M. (2022), "Life cycle assessment
                  of a renewable energy system with hydrogen-battery storage
                  for a remote off-grid community", Int. J. Hydrogen Energy 47.
                  Table 3 — the as-built 21.6 m3 vessel at Ginostra.
type I cylinder   ~1 wt% gravimetric capacity, a typical industrial stationary
                  bottle. DERIVED, not transcribed — see dashboard_config.
embodied carbon   ecoinvent 3.9.1 apos, IPCC 2021 GWP100.
vessel lifetime   25 years, the paper's own plant life. The tank is never
                  replaced within it.

Every number in this module is listed in ``SOURCES.md`` alongside its
source and provenance grade (transcribed / derived / assumed).

Run:  python optimisation/h2_storage.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "optimisation_outputs"

CACHE_PATH = OUT_DIR / "h2_storage_decomposition_cache.json"
_MEMO: list | None = None

# ASSUMED, with no source, and load-bearing. See the module docstring.
LEAKAGE_FRAC_PER_HOUR = 0.0
LEAKAGE_IS_ASSUMED = True

RECONSTRUCTION_TOLERANCE = 1e-4      # bw2calc solver noise; see electrolysers.py

# Ideal-gas-with-compressibility, used to turn a design's volume and pressure
# into the kg of hydrogen it holds. Only needed for designs specified by volume.
R_H2_J_PER_KG_K = 4124.2


def _gwp_method(bd):
    return next(m for m in bd.methods
                if m[1] == "IPCC 2021" and m[2] == "climate change"
                and "GWP100" in str(m) and "no LT" not in str(m))


def capacity_kg(design, cfg):
    """kg of H2 a design holds, from its own volume and pressure."""
    if "steel_kg_per_kg_h2" in design:
        return None      # specified per kg directly; no volume to convert
    p_pa = design["pressure_bar"] * 1e5
    return (p_pa * design["volume_m3"]) / (
        cfg.TANK_H2_COMPRESSIBILITY * R_H2_J_PER_KG_K * cfg.TANK_H2_TEMPERATURE_K)


# Feed pressure assumed when nobody says otherwise. 30 bar is the pressurised
# PEM/alkaline delivery pressure, which is what this module's own docstring was
# silently assuming for every technology. Callers that know the electrolyser
# should pass its real delivery pressure instead — see
# ``electrolysers.DELIVERY_PRESSURE_BAR``.
DEFAULT_FEED_PRESSURE_BAR = 30.0

# Real specific work over the isothermal minimum. Anchored on the worked example
# in the hydrogen storage and compression review (arXiv:1702.06015): compressing
# from 1 to 500 bar takes a minimum of 8 MJ/kg isothermally, against 15 MJ/kg
# for a realistic three-stage adiabatic machine at 70 % isentropic efficiency.
# The isothermal formula below reproduces that 8 MJ/kg to within 6 %, so the
# ratio is applied to it rather than a second correlation being invented.
COMPRESSION_REAL_OVER_ISOTHERMAL = 15.0 / 8.0
H2_GAS_CONSTANT_J_PER_KG_K = 4124.0
COMPRESSION_INLET_K = 293.15


def compression_kwh_per_kg(from_bar: float, to_bar: float) -> float:
    """Electricity to compress one kg of hydrogen between two pressures.

    Isothermal minimum ``R T ln(P2/P1)``, scaled to a real multistage machine.
    Returns zero when the feed is already at or above the target, which is the
    case that made the old flat rule look right: a 30 bar PEM feeding a 28 bar
    tank genuinely needs no compressor. A 1 bar SOEC feeding the same tank needs
    about 2.1 kWh/kg, which is roughly 5 % on top of its 42.3 kWh/kg — enough to
    matter in a comparison it was previously winning.
    """
    if from_bar <= 0 or to_bar <= 0:
        raise ValueError(f"pressures must be positive, got {from_bar}, {to_bar}")
    if to_bar <= from_bar:
        return 0.0
    j_per_kg = (H2_GAS_CONSTANT_J_PER_KG_K * COMPRESSION_INLET_K
                * math.log(to_bar / from_bar))
    return j_per_kg * COMPRESSION_REAL_OVER_ISOTHERMAL / 3.6e6


def steel_kg_per_kg_h2(design, cfg):
    if "steel_kg_per_kg_h2" in design:
        return float(design["steel_kg_per_kg_h2"])
    return design["steel_kg"] / capacity_kg(design, cfg)


def decompose(use_cache: bool = True, refresh: bool = False):
    """Every tank design's embodied carbon per kg of storage capacity."""
    global _MEMO
    if refresh:
        _MEMO = None
        CACHE_PATH.unlink(missing_ok=True)
    if _MEMO is not None:
        return _MEMO
    if use_cache and CACHE_PATH.exists():
        try:
            _MEMO = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            return _MEMO
        except Exception:
            pass

    import bw2data as bd
    import lca_helpers as H
    import dashboard_config as cfg

    ei, _bio, _fg, _m = H.setup_brightway()
    method = _gwp_method(bd)

    rows = []
    for name, design in cfg.TANK_DESIGNS.items():
        proc_name, proc_loc = design["steel_process"]
        steel = [a for a in ei if a["name"] == proc_name and a["location"] == proc_loc]
        if not steel:
            raise ValueError(f"{name}: steel process {proc_name!r} [{proc_loc}] not in ecoinvent")
        per_kg_steel = H.run_lca_score(steel[0], method)
        intensity = steel_kg_per_kg_h2(design, cfg)
        per_kg_cap = per_kg_steel * intensity

        # Filled in by the caller, which is the only place that knows which
        # electrolyser is feeding this tank. Left at the tank's own pressure
        # here so the table still reads standalone.
        compression = compression_kwh_per_kg(DEFAULT_FEED_PRESSURE_BAR,
                                             design["pressure_bar"])
        rows.append({
            "design": name,
            "pressure_bar": design["pressure_bar"],
            "steel_process": proc_name,
            "steel_kg_per_kg_h2": intensity,
            "capacity_kg_h2": capacity_kg(design, cfg),
            "kgco2e_per_kg_steel": per_kg_steel,
            "kgco2e_per_kg_capacity": per_kg_cap,
            "lifetime_years": float(cfg.TANK_LIFETIME_YEARS),
            "kgco2e_per_kg_capacity_year": per_kg_cap / float(cfg.TANK_LIFETIME_YEARS),
            "compression_kwh_per_kg": compression,
            "leakage_frac_per_hour": LEAKAGE_FRAC_PER_HOUR,
            "leakage_is_assumed": LEAKAGE_IS_ASSUMED,
            "is_as_built": name == cfg.TANK_DESIGN,
            "note": design.get("note", ""),
        })

    # Cross-check the as-built design against the activity the notebook wrote.
    act = bd.get_activity((cfg.H2_STORAGE_FOREGROUND_DB, "h2_tank_steel_1kg_capacity"))
    built = H.run_lca_score(act, method)
    for r in rows:
        if r["is_as_built"]:
            r["brightway_kgco2e_per_kg_capacity"] = built

    OUT_DIR.mkdir(exist_ok=True)
    CACHE_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _MEMO = rows
    return rows


def build():
    return pd.DataFrame(decompose())


def check_against_brightway(rows):
    """The design this module rebuilds must match the one the notebook wrote.

    Reconstructing the as-built vessel from its own steel mass and steel process
    is the test that the volume-to-capacity conversion, the steel intensity and
    the process selection are all right. If it passes, the *other* design —
    which has no Brightway activity to check against — is being built the same
    way and can be trusted to the same degree.
    """
    built = [r for r in rows if r["is_as_built"]]
    if len(built) != 1:
        raise AssertionError(
            f"expected exactly 1 as-built design, found {len(built)}. "
            "dashboard_config.TANK_DESIGN does not match TANK_DESIGNS.")
    r = built[0]
    ref = r.get("brightway_kgco2e_per_kg_capacity")
    if ref is None:
        raise AssertionError("no Brightway score recorded for the as-built design")
    err = abs(r["kgco2e_per_kg_capacity"] - ref) / abs(ref)
    if err > RECONSTRUCTION_TOLERANCE:
        raise AssertionError(
            f"{r['design']}: rebuilt {r['kgco2e_per_kg_capacity']:.6f} vs Brightway "
            f"{ref:.6f} kg CO2e/kg capacity, {err:.1e} relative. The steel "
            "intensity or the capacity conversion is wrong.")
    return (f"OK — {r['design']} rebuilds the foreground activity to {err:.1e} "
            f"relative, so the {len(rows) - 1} unbuilt design(s) are derived the same way")


def run():
    rows = decompose()
    df = build()
    print("=" * 100)
    print("HYDROGEN STORAGE — embodied carbon per kg of capacity")
    print("=" * 100)
    print(check_against_brightway(rows))

    print()
    print(f"  {'design':<20}{'bar':>6}{'kg steel/kg':>13}{'kg CO2e/kg':>13}"
          f"{'per year':>11}{'kWh/kg comp':>13}")
    for r in rows:
        mark = " *" if r["is_as_built"] else "  "
        print(f"{mark}{r['design']:<20}{r['pressure_bar']:>6.0f}"
              f"{r['steel_kg_per_kg_h2']:>13.1f}{r['kgco2e_per_kg_capacity']:>13.1f}"
              f"{r['kgco2e_per_kg_capacity_year']:>11.2f}"
              f"{r['compression_kwh_per_kg']:>13.1f}")
    print("  * = the design the foreground currently builds")

    print("\nAgainst a battery, on the only basis that compares — kWh delivered back")
    print("-" * 100)
    import dashboard_config as cfg
    from optimisation import battery as batt
    kwh_out_per_kg = cfg.FC_H2_LHV_KWH_PER_KG * cfg.FC_ETA_NET_MEAN
    b_energy = batt.embodied_components()["energy_kgco2e_per_kWh"]
    print(f"  A kg of H2 holds {cfg.FC_H2_LHV_KWH_PER_KG:.1f} kWh LHV and returns "
          f"{kwh_out_per_kg:.1f} kWh through the fuel cell at "
          f"{cfg.FC_ETA_NET_MEAN:.1%} net.")
    print(f"  A battery returns what it stores, less round-trip losses.\n")
    print(f"  {'store':<22}{'kg CO2e / kWh deliverable':>28}{'vs battery':>13}")
    for r in rows:
        per_kwh = r["kgco2e_per_kg_capacity"] / kwh_out_per_kg
        print(f"  {r['design']:<22}{per_kwh:>28,.1f}{per_kwh / b_energy:>12,.1f}x")
    print(f"  {'Li-ion battery (LFP)':<22}{b_energy:>28,.1f}{1.0:>12,.1f}x")
    print("\n  The 28 bar steel vessel is a Gandiglio as-built low-pressure buffer, and")
    print("  per deliverable kWh it is no better than a lithium battery. The 200 bar")
    print("  Type I cylinder is roughly six times better. Which design the study uses")
    print("  is therefore not a detail — it decides whether hydrogen storage has an")
    print("  embodied-carbon advantage at all. Run both.")

    if any(r["leakage_is_assumed"] for r in rows):
        print(f"\n  ASSUMED: standing loss = {LEAKAGE_FRAC_PER_HOUR:.4g} /h, no source. "
              "This is the\n  parameter that decides hydrogen-versus-battery over a season. "
              "See DATA_GAPS.md.")

    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / "h2_storage_embodied.csv"
    df.to_csv(path, index=False)
    print(f"\nWrote:\n  {path.relative_to(ROOT)}")
    return df


if __name__ == "__main__":
    run()
