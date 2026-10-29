"""
Grid connection — the capital cost of the connection itself.
=============================================================================

The use-of-system tariffs in ``network_charges`` are what a site pays to *use*
the network. Until 28 Oct 2026 nothing charged for the connection assets the
site pays to *build*: every site, on either tier, got its intake substation and
its cable for £0, while the carbon side charged the same assets
(``grid_connection.py``). The two objectives described different connections.

This module prices the same split the carbon side uses, at the site's own
connection voltage (``network_charges.connection_voltage``):

| part | what | scales with | LP term |
|---|---|---|---|
| per MW | the intake substation: two transformers (N-1) and their switchgear | ``cap_grid`` | ``cost_grid_per_mw_year`` |
| fixed | two cable circuits from the network substation, and at 11 kV the metered switchboard | nothing — the cost of reaching the site | ``cost_grid_fixed_per_year`` |

| connection | substation (NGED row) | firm rating | cable (NGED row) |
|---|---|---|---|
| 132 kV, or transmission | 132kV/EHV, new outdoor double transformer | 60 MVA | 132 kV mains, footpath or carriageway |
| 33 kV | EHV/HV primary, new outdoor double transformer | 29 MVA | 33 kV mains, footpath or carriageway |
| 11 kV | none — an HV metered switchboard (fixed) | — | HV mains, footpath or carriageway |

A transmission site is priced on the 132 kV rows: NGED's Data Centre Impact Study
(Nov 2025) says transmission-connected demand energises "to a 132kV connection bay
or new substation at a 400kV grid supply point".

Who pays
--------
Distribution: since the Access SCR (Ofgem final decision, 3 May 2022, in force
1 April 2023) demand has a "fully shallow" boundary — the customer pays for its
extension assets only, and the DNO pays for reinforcement unless it exceeds the
£1,720/kVA High Cost Cap. So the customer's capital is exactly the substation
and cable priced here, and no reinforcement contribution is added.

Transmission: CUSC Section 14 charges connection assets as an annual charge on
their Gross Asset Value — depreciation over 40 years, a return at the TO's rate,
site-specific maintenance, and a Transmission Running Cost. That formula is the
annualisation used here for both tiers: it is the one GB regulation sets for
connection assets, and it keeps the two tiers on one basis. TRC is added on the
transmission tier only. (For a distribution site, which pays its capital up
front, the study's own discount rate would fit better — open, COST_PLAN §4.1.)

Sources (read 28 Oct 2026, off the rendered pages)
--------------------------------------------------
prices       NGED (South Wales), *Statement of Methodology and Charges for
             Connection*, June 2026, §7 F5 cables (pp. 164-165) and F7
             substations (pp. 167-168). £, excl. VAT, June 2026. The same
             prices appear in the South West and East Midlands June 2026
             statements. Rows and values below. TRANSCRIBED. Until 28 Oct 2026
             the August 2023 edition, every site at 132 kV.
ratings      ENWL ES216 Issue 4 (Jul 2024): "a single 132/33kV transformer shall
             not exceed 60 MVA" (§5.2) and "a single 33/11kV transformer shall not
             exceed 29 MVA" (§6.2). With N-1, the pair is firm for one
             transformer's rating — the same basis the carbon side charges two
             transformers per MW on. ASSUMED as the substations' ratings.
route        2 km, as ``grid_connection.LINE_KM``, two circuits for a dual (N-1)
             connection. ASSUMED, and site-specific in reality.
annual       NESO, *The Statement of Use of System Charges*, Issue 8.0, effective
charge       1 April 2026, §15-16 and Appendix A: 40-year depreciation;
             site-specific maintenance "0.43%" of GAV; TRC "0.90%"; Table 3.1
             rate of return NGET (TOPI) 5.02 %, SPT 5.14 %, SHET 4.32 %.
             TRANSCRIBED. Applied as a capital recovery factor at the TO's rate
             over 40 years — the level equivalent of Section 14's declining
             return on net asset value.

What errs which way
-------------------
- 132 kV rows for a 275/400 kV transmission connection: LOW above the DNO's top.
- The remote-end bays at the network substation are not itemised: LOW.
- Underground cable in a road rather than an overhead line: HIGH where an
  overhead line would do (NGED's overhead spans cost about a tenth per km).

Run:  python optimisation/connection_cost.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CASES = ("low", "central", "high")
PRICE_YEAR = 2026


def _mid(lo: float, hi: float) -> dict:
    return {"low": lo, "central": (lo + hi) / 2.0, "high": hi}


# NGED South Wales, June 2026. Substation £ per substation; cable £ for the
# first stretch (its length in metres) and £ per additional metre.
SUBSTATION_GBP = {
    "132 kV": _mid(1_700_792.0, 2_790_945.0),   # 132kV/EHV, new outdoor double transformer
    "33 kV": _mid(1_359_279.0, 1_501_688.0),    # EHV/HV primary, new outdoor double transformer
}
SUBSTATION_FIRM_MVA = {"132 kV": 60.0, "33 kV": 29.0}   # ASSUMED, ES216 limits
HV_SWITCHBOARD_GBP = _mid(28_635.0, 40_708.0)  # "HV only substation": external switchgear and metered CB
CABLE = {   # (first metres, £ for them, £ per additional metre)
    "132 kV": (40.0, _mid(126_845.0, 126_845.0), _mid(3_171.0, 3_171.0)),
    "33 kV": (30.0, _mid(9_068.0, 19_451.0), _mid(221.0, 540.0)),
    "11 kV": (20.0, _mid(5_163.0, 12_324.0), _mid(98.0, 261.0)),
}
ROUTE_KM = 2.0                                 # ASSUMED, as grid_connection.LINE_KM
CIRCUITS = 2                                   # ASSUMED: dual connection, N-1

ASSET_LIFE_YEARS = 40.0
MAINTENANCE_FRAC = 0.0043
TRC_FRAC = 0.0090                              # transmission tier only
# TO rate of return by CI region: North Scotland is SHET's, South Scotland SPT's,
# England and Wales NGET's (TOPI).
RATE_OF_RETURN = {1: 0.0432, 2: 0.0514}
RATE_OF_RETURN_DEFAULT = 0.0502

ASSUMED = ("SUBSTATION_FIRM_MVA", "ROUTE_KM", "CIRCUITS",
           "the 132 kV rows for a 275/400 kV connection")


def crf(rate: float, years: float) -> float:
    return rate / (1.0 - (1.0 + rate) ** -years)


def annual_factor(region: int, transmission_connected: bool) -> float:
    """Annual charge per £ of capital: recovery at the TO's rate over 40 years,
    plus maintenance, plus TRC on the transmission tier."""
    r = RATE_OF_RETURN.get(region, RATE_OF_RETURN_DEFAULT)
    return (crf(r, ASSET_LIFE_YEARS) + MAINTENANCE_FRAC
            + (TRC_FRAC if transmission_connected else 0.0))


def _priced_at(voltage: str) -> str:
    """The NGED rows a connection is priced on: transmission takes 132 kV."""
    v = "132 kV" if voltage == "transmission" else voltage
    if v not in CABLE:
        raise ValueError(f"no connection prices for {voltage!r}")
    return v


def capital(voltage: str = "132 kV", case: str = "central", route_km: float | None = None) -> dict:
    """Capital, £: per MW of connection, and the fixed part.

    ``route_km`` is the cable route to the substation; since 29 Oct 2026
    ``substations.connection_point`` gives it from the site's coordinates, and
    ``ROUTE_KM`` is only the default when no site is placed."""
    v = _priced_at(voltage)
    first_m, first_gbp, per_m = CABLE[v]
    r = ROUTE_KM if route_km is None else max(float(route_km), first_m / 1000.0)
    per_circuit = first_gbp[case] + (r * 1000.0 - first_m) * per_m[case]
    fixed = per_circuit * CIRCUITS + (HV_SWITCHBOARD_GBP[case] if v == "11 kV" else 0.0)
    per_mw = (SUBSTATION_GBP[v][case] / SUBSTATION_FIRM_MVA[v]) if v in SUBSTATION_GBP else 0.0
    return {"per_MW_GBP": per_mw, "fixed_GBP": fixed, "priced_at": v, "route_km": r}


def connection_costs(region: int, transmission_connected: bool,
                     case: str = "central", power_factor: float = 1.0,
                     connection_voltage: str | None = None,
                     route_km: float | None = None) -> dict:
    """The connection's annual cost: £/MW/year on ``cap_grid`` and £/year fixed.

    ``connection_voltage`` is ``network_charges.connection_voltage``'s answer;
    without it a distribution site is taken at 132 kV, as before 28 Oct 2026.
    ``route_km`` is the cable route from ``substations.connection_point``."""
    if case not in CASES:
        raise ValueError(f"case must be one of {CASES}, got {case!r}")
    voltage = connection_voltage or ("transmission" if transmission_connected else "132 kV")
    cap = capital(voltage, case, route_km)
    f = annual_factor(region, transmission_connected)
    return {
        "per_MW_year_GBP": cap["per_MW_GBP"] / power_factor * f,
        "fixed_per_year_GBP": cap["fixed_GBP"] * f,
        "per_MW_GBP": cap["per_MW_GBP"] / power_factor,
        "fixed_GBP": cap["fixed_GBP"],
        "annual_factor": f,
        "rate_of_return": RATE_OF_RETURN.get(region, RATE_OF_RETURN_DEFAULT),
        "connection_voltage": voltage, "priced_at": cap["priced_at"], "route_km": cap["route_km"],
        "case": case, "price_year": PRICE_YEAR,
    }


if __name__ == "__main__":
    print("=" * 84)
    print(f"GRID CONNECTION CAPITAL — NGED South Wales, June {PRICE_YEAR} £; NESO §14 annuity")
    print("=" * 84)
    for v in ("132 kV", "33 kV", "11 kV"):
        for case in CASES:
            c = capital(v, case)
            print(f"  {v:<7} {case:<8} substation £{c['per_MW_GBP']:>9,.0f}/MW   "
                  f"fixed £{c['fixed_GBP'] / 1e6:>5.2f} m")
    print()
    for label, region, trans, v in (("London, 11 kV", 13, False, "11 kV"),
                                    ("London, 33 kV", 13, False, "33 kV"),
                                    ("London, 132 kV", 13, False, "132 kV"),
                                    ("London, transmission", 13, True, "transmission"),
                                    ("North Scotland, transmission", 1, True, "transmission")):
        k = connection_costs(region, trans, connection_voltage=v)
        print(f"  {label:<30} factor {k['annual_factor']:.4f}  "
              f"£{k['per_MW_year_GBP']:>7,.0f}/MW/yr  £{k['fixed_per_year_GBP'] / 1e3:>6,.0f}k/yr fixed")
    print(f"\n  ASSUMED: {', '.join(ASSUMED)}.")
