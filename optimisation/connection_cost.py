"""
Grid connection — the capital cost of the connection itself.
=============================================================================

The use-of-system tariffs in ``network_charges`` are what a site pays to *use*
the network. Until 28 Oct 2026 nothing charged for the connection assets the
site pays to *build*: every site, on either tier, got its intake substation and
its cable for £0, while the carbon side charged the same assets
(``grid_connection.py``). The two objectives described different connections.

This module prices the same split the carbon side uses, at the site's own
connection voltage (``network_charges.connection_voltage``), from the
connection charging statement of the site's own DNO (since 29 Oct 2026; until
then NGED South Wales priced every area):

| part | what | scales with | LP term |
|---|---|---|---|
| per MW | the intake substation: two transformers (N-1) and their switchgear | ``cap_grid`` | ``cost_grid_per_mw_year`` |
| fixed | two cable circuits from the network substation, and at 11 kV the metered switchboard | nothing — the cost of reaching the site | ``cost_grid_fixed_per_year`` |

| connection | substation row | firm rating | cable row |
|---|---|---|---|
| 132 kV, or transmission | 132kV/EHV, new double transformer substation | 60 MVA | 132 kV mains, footpath or carriageway |
| 33 kV | EHV/HV primary, new double transformer substation | 29 MVA | 33 kV mains, footpath or carriageway |
| 11 kV | none — an HV metered switchboard (fixed) | — | HV mains, footpath or carriageway |

Every DNO's statement has the same table (the LC14 common format, §7 F5
cables and F7 substations), so the rows match across companies. Outdoor rows
where published, else indoor; external switchgear where published, else
internal. A transmission site is priced on the 132 kV rows: NGED's Data
Centre Impact Study (Nov 2025) says transmission-connected demand energises
"to a 132kV connection bay or new substation at a 400kV grid supply point".

Prices by area (COST_PLAN §1.9 E, decided 29 Oct 2026)
-------------------------------------------------------
Eleven areas have their own price list. Where a company prints POA or N/A
for a row (Northern Powergrid's substations and 33/132 kV cables, SPEN's
substations and 132 kV cable, UKPN London's substations, SSEN North
Scotland's 132 kV rows) the row takes the MEDIAN over the price lists that
publish it, low and high separately, and the result names the row as a
stand-in (``prices(region)["stand_in"]``).

NGED's substation rows are kept for its four areas AND FLAGGED: its 132 kV
double-transformer substation is £1.70-2.79 m against £6.96-13.04 m from
the other four publishers, and its 33 kV primary £1.36-1.50 m against
£1.94-5.80 m. Real North West schemes (ENWL's capital projects list) put a
new primary at £5-10 m, so NGED's rows read as the transformers and
switchgear alone, without civils and land. Replacing them with the median
would raise an NGED 132 kV site's substation about 4x
(``NGED_SUBSTATION_FLAG``; sensitivity in COST_PLAN §1.9 E).

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

Sources (read 28-29 Oct 2026, off the rendered pages; all in OneDrive
"DC optimiser/connection sources/4 connection capital")
--------------------------------------------------------------------
prices       Each DNO's *Statement of Methodology and Charges for Connection*,
             §7 tables F5 (cables) and F7 (substations). £, excl. VAT.
             NGED South Wales June 2026 pp. 164-168 (the same figures in the
             East Midlands, West Midlands and South West statements);
             SSEN SEPD v1.47 pp. 148-152 and SHEPD v1.46 pp. 146-150 (2026);
             UKPN August 2026 pp. 161-167, columns LPN, EPN, SPN;
             ENWL v5.9 June 2026 pp. 156-161 (South and North columns equal);
             SPEN February 2026 pp. 151-153 (one statement for SP
             Distribution and SP Manweb); Northern Powergrid Northeast and
             Yorkshire June 2026. TRANSCRIBED.
ratings      ENWL ES216 Issue 4 (Jul 2024): "a single 132/33kV transformer shall
             not exceed 60 MVA" (§5.2) and "a single 33/11kV transformer shall not
             exceed 29 MVA" (§6.2). With N-1, the pair is firm for one
             transformer's rating — the same basis the carbon side charges two
             transformers per MW on. ASSUMED as the substations' ratings.
route        ``substations.connection_point`` from the site's coordinates;
             2 km (``grid_connection.LINE_KM``) only when no site is placed.
             Two circuits for a dual (N-1) connection. ASSUMED.
annual       NESO, *The Statement of Use of System Charges*, Issue 8.0, effective
charge       1 April 2026, §15-16 and Appendix A: 40-year depreciation;
             site-specific maintenance "0.43%" of GAV; TRC "0.90%"; Table 3.1
             rate of return NGET (TOPI) 5.02 %, SPT 5.14 %, SHET 4.32 %.
             TRANSCRIBED. Applied as a capital recovery factor at the TO's rate
             over 40 years — the level equivalent of Section 14's declining
             return on net asset value.

What errs which way
-------------------
- NGED's substation rows (four areas): LOW, see above.
- 132 kV rows for a 275/400 kV transmission connection: LOW above the DNO's top.
- The remote-end bays at the network substation are not itemised: LOW.
- Underground cable in a road rather than an overhead line: HIGH where an
  overhead line would do (NGED's overhead spans cost about a tenth per km).
- A stand-in median for a POA row is the other companies' price, not that
  company's: either way.

Run:  python optimisation/connection_cost.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CASES = ("low", "central", "high")
PRICE_YEAR = 2026
VOLTAGES = ("132 kV", "33 kV", "11 kV")
CABLE_FIRST_M = {"132 kV": 40.0, "33 kV": 30.0, "11 kV": 20.0}   # the first stretch each row prices


def _mid(lo: float, hi: float) -> dict:
    return {"low": lo, "central": (lo + hi) / 2.0, "high": hi}


Range = tuple[float, float] | None     # (min, max) £ as printed, or None where POA / N/A


@dataclass(frozen=True)
class PriceList:
    """One company's §7 rows: substation £ per substation, switchboard £, cable
    £ for the first stretch and £ per additional metre. None = not published."""
    name: str
    source: str
    substation: dict[str, Range]       # "132 kV", "33 kV": new double transformer substation
    hv_switchboard: Range              # HV only substation: switchgear and metered circuit breaker
    cable_first: dict[str, Range]      # first 40 / 30 / 20 m in footpath or carriageway
    cable_per_m: dict[str, Range]      # each additional metre
    notes: tuple[str, ...] = field(default_factory=tuple)


PRICE_LISTS = {
    "NGED": PriceList(
        "National Grid Electricity Distribution",
        "NGED South Wales, Statement of Methodology and Charges for Connection, June 2026, pp. 164-168 (same in EM, WM, SW)",
        substation={"132 kV": (1_700_792.0, 2_790_945.0),    # 132kV/EHV, new outdoor double transformer
                    "33 kV": (1_359_279.0, 1_501_688.0)},    # EHV/HV primary, new outdoor double transformer
        hv_switchboard=(28_635.0, 40_708.0),                 # external switchgear and metered CB
        cable_first={"132 kV": (126_845.0, 126_845.0), "33 kV": (9_068.0, 19_451.0), "11 kV": (5_163.0, 12_324.0)},
        cable_per_m={"132 kV": (3_171.0, 3_171.0), "33 kV": (221.0, 540.0), "11 kV": (98.0, 261.0)},
        notes=("substation rows 4-5x below the other publishers: read as transformers and switchgear only (FLAGGED)",)),
    "SEPD": PriceList(
        "SSEN Southern Electric Power Distribution",
        "SEPD connection charging statement v1.47 (2026), pp. 148-152",
        substation={"132 kV": (11_495_717.0, 13_043_778.0),  # outdoor double
                    "33 kV": (2_616_172.0, 2_833_817.0)},    # outdoor double
        hv_switchboard=(16_621.0, 40_331.0),                 # external
        cable_first={"132 kV": (57_334.0, 194_474.0), "33 kV": (13_096.0, 47_697.0), "11 kV": (6_074.0, 13_812.0)},
        cable_per_m={"132 kV": (1_405.0, 32_316.0), "33 kV": (437.0, 1_054.0), "11 kV": (304.0, 691.0)},
        notes=("132 kV cable per additional metre printed £1,405-32,316: the top reads as a special case, "
               "so the central (the midpoint) errs HIGH",)),
    "SHEPD": PriceList(
        "SSEN Scottish Hydro Electric Power Distribution",
        "SHEPD connection charging statement v1.46 (2026), pp. 146-150",
        substation={"132 kV": None,                          # N/A: 132 kV is transmission in Scotland
                    "33 kV": (1_939_300.0, 2_852_850.0)},    # indoor double (no outdoor row)
        hv_switchboard=(31_486.0, 53_950.0),                 # external
        cable_first={"132 kV": None, "33 kV": (3_613.0, 9_544.0), "11 kV": (3_614.0, 9_545.0)},
        cable_per_m={"132 kV": None, "33 kV": (141.0, 439.0), "11 kV": (141.0, 439.0)},
        notes=("33 kV and HV cable rows are printed with the same figures",)),
    "UKPN-LPN": PriceList(
        "UK Power Networks, London",
        "UKPN connection charging statement, August 2026, pp. 161-167, LPN column",
        substation={"132 kV": None, "33 kV": None},          # POA
        hv_switchboard=(50_000.0, 270_000.0),                # internal (external N/A)
        cable_first={"132 kV": (22_000.0, 50_000.0), "33 kV": (12_000.0, 40_000.0), "11 kV": (4_600.0, 20_000.0)},
        cable_per_m={"132 kV": (600.0, 900.0), "33 kV": (400.0, 700.0), "11 kV": (400.0, 1_000.0)}),
    "UKPN-EPN": PriceList(
        "UK Power Networks, Eastern",
        "UKPN connection charging statement, August 2026, pp. 161-167, EPN column",
        substation={"132 kV": (8_000_000.0, 9_000_000.0),    # indoor double (outdoor N/A)
                    "33 kV": (5_200_000.0, 5_700_000.0)},    # indoor double
        hv_switchboard=(50_000.0, 90_000.0),                 # internal
        cable_first={"132 kV": (20_000.0, 50_000.0), "33 kV": (11_000.0, 30_000.0), "11 kV": (2_000.0, 17_300.0)},
        cable_per_m={"132 kV": (500.0, 900.0), "33 kV": (400.0, 700.0), "11 kV": (200.0, 900.0)}),
    "UKPN-SPN": PriceList(
        "UK Power Networks, South Eastern",
        "UKPN connection charging statement, August 2026, pp. 161-167, SPN column",
        substation={"132 kV": (8_100_000.0, 9_200_000.0),    # indoor double
                    "33 kV": (5_300_000.0, 5_800_000.0)},    # indoor double
        hv_switchboard=(60_000.0, 90_000.0),                 # internal
        cable_first={"132 kV": (21_000.0, 50_000.0), "33 kV": (11_000.0, 40_000.0), "11 kV": (3_100.0, 14_900.0)},
        cable_per_m={"132 kV": (600.0, 900.0), "33 kV": (400.0, 700.0), "11 kV": (300.0, 800.0)}),
    "ENWL": PriceList(
        "Electricity North West",
        "ENWL connection charging statement v5.9, June 2026, pp. 156-161 (South = North)",
        substation={"132 kV": (6_961_000.0, 11_270_000.0),   # outdoor double
                    "33 kV": (4_039_000.0, 4_767_000.0)},    # indoor double (outdoor N/A)
        hv_switchboard=(64_300.0, 81_800.0),                 # external
        cable_first={"132 kV": (100_000.0, 135_000.0), "33 kV": (74_400.0, 91_400.0), "11 kV": (11_600.0, 18_300.0)},
        cable_per_m={"132 kV": (2_300.0, 3_500.0), "33 kV": (2_300.0, 3_200.0), "11 kV": (200.0, 380.0)}),
    "SPEN": PriceList(
        "SP Energy Networks (SP Distribution and SP Manweb)",
        "SPEN connection charging statement, February 2026, pp. 151-153 (one statement for both licence areas)",
        substation={"132 kV": None, "33 kV": None},          # POA
        hv_switchboard=(26_403.0, 46_776.0),                 # external (the only switchgear row)
        cable_first={"132 kV": None, "33 kV": (10_912.0, 24_119.0), "11 kV": (5_440.0, 15_337.0)},
        cable_per_m={"132 kV": None, "33 kV": (557.0, 722.0), "11 kV": (145.0, 475.0)}),
    "NPG-NE": PriceList(
        "Northern Powergrid, Northeast",
        "Northern Powergrid (Northeast) connection charging statement, June 2026, §7",
        substation={"132 kV": None, "33 kV": None},          # POA
        hv_switchboard=(58_862.0, 68_346.0),                 # internal (external N/A)
        cable_first={"132 kV": None, "33 kV": None, "11 kV": (7_299.0, 14_098.0)},
        cable_per_m={"132 kV": None, "33 kV": None, "11 kV": (146.0, 292.0)}),
    "NPG-Y": PriceList(
        "Northern Powergrid, Yorkshire",
        "Northern Powergrid (Yorkshire) connection charging statement, June 2026, §7",
        substation={"132 kV": None, "33 kV": None},          # POA
        hv_switchboard=(58_947.0, 76_873.0),                 # internal
        cable_first={"132 kV": None, "33 kV": None, "11 kV": (7_099.0, 12_721.0)},
        cable_per_m={"132 kV": None, "33 kV": None, "11 kV": (141.0, 262.0)}),
}

# CI region -> price list. One list per licence area; NGED's four and SPEN's
# two areas share a statement.
AREA_PRICE_LIST = {1: "SHEPD", 2: "SPEN", 3: "ENWL", 4: "NPG-NE", 5: "NPG-Y", 6: "SPEN",
                   7: "NGED", 8: "NGED", 9: "NGED", 10: "UKPN-EPN", 11: "NGED",
                   12: "SEPD", 13: "UKPN-LPN", 14: "UKPN-SPN"}
NGED_SUBSTATION_FLAG = ("NGED's substation rows are kept but are 4-5x below the other four publishers "
                        "(transformers and switchgear only, no civils or land): LOW. COST_PLAN §1.9 E")

SUBSTATION_FIRM_MVA = {"132 kV": 60.0, "33 kV": 29.0}   # ASSUMED, ES216 limits
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
           "the 132 kV rows for a 275/400 kV connection",
           "the publishers' median for a POA row")


def _published(row: str, voltage: str | None = None) -> list[tuple[float, float]]:
    out = []
    for p in PRICE_LISTS.values():
        r = getattr(p, row)
        r = r if voltage is None else r.get(voltage)
        if r is not None:
            out.append(r)
    return out


def median_row(row: str, voltage: str | None = None) -> tuple[float, float]:
    """The median over the price lists that publish this row, low and high separately."""
    pub = _published(row, voltage)
    return median(lo for lo, _ in pub), median(hi for _, hi in pub)


def prices(region: int) -> dict:
    """The resolved rows for a CI region: every row filled, with ``stand_in``
    naming the rows taken from the publishers' median and ``flags`` the
    caveats on the rows that are the company's own."""
    if region not in AREA_PRICE_LIST:
        raise ValueError(f"no connection price list for CI region {region!r}")
    key = AREA_PRICE_LIST[region]
    p = PRICE_LISTS[key]
    stand_in, out = [], {"list": key, "company": p.name, "source": p.source, "flags": list(p.notes),
                         "substation": {}, "cable_first": {}, "cable_per_m": {}}

    def pick(row, voltage, rng):
        if rng is None:
            rng = median_row(row, voltage)
            stand_in.append(f"{row} {voltage}" if voltage else row)
        return _mid(*rng)

    for v in SUBSTATION_FIRM_MVA:
        out["substation"][v] = pick("substation", v, p.substation.get(v))
    out["hv_switchboard"] = pick("hv_switchboard", None, p.hv_switchboard)
    for v in VOLTAGES:
        out["cable_first"][v] = pick("cable_first", v, p.cable_first.get(v))
        out["cable_per_m"][v] = pick("cable_per_m", v, p.cable_per_m.get(v))
    out["stand_in"] = stand_in
    if key == "NGED":
        out["flags"].append(NGED_SUBSTATION_FLAG)
    return out


def crf(rate: float, years: float) -> float:
    return rate / (1.0 - (1.0 + rate) ** -years)


def annual_factor(region: int, transmission_connected: bool) -> float:
    """Annual charge per £ of capital: recovery at the TO's rate over 40 years,
    plus maintenance, plus TRC on the transmission tier."""
    r = RATE_OF_RETURN.get(region, RATE_OF_RETURN_DEFAULT)
    return (crf(r, ASSET_LIFE_YEARS) + MAINTENANCE_FRAC
            + (TRC_FRAC if transmission_connected else 0.0))


def _priced_at(voltage: str) -> str:
    """The rows a connection is priced on: transmission takes 132 kV."""
    v = "132 kV" if voltage == "transmission" else voltage
    if v not in VOLTAGES:
        raise ValueError(f"no connection prices for {voltage!r}")
    return v


def capital(voltage: str = "132 kV", case: str = "central", route_km: float | None = None,
            region: int = 7) -> dict:
    """Capital, £: per MW of connection, and the fixed part, on the area's prices.

    ``route_km`` is the cable route to the substation; since 29 Oct 2026
    ``substations.connection_point`` gives it from the site's coordinates, and
    ``ROUTE_KM`` is only the default when no site is placed. ``region`` is the
    CI region; the default is NGED South Wales, the module's basis until 29
    Oct 2026."""
    v = _priced_at(voltage)
    pr = prices(region)
    first_m = CABLE_FIRST_M[v]
    r = ROUTE_KM if route_km is None else max(float(route_km), first_m / 1000.0)
    per_circuit = pr["cable_first"][v][case] + (r * 1000.0 - first_m) * pr["cable_per_m"][v][case]
    fixed = per_circuit * CIRCUITS + (pr["hv_switchboard"][case] if v == "11 kV" else 0.0)
    per_mw = (pr["substation"][v][case] / SUBSTATION_FIRM_MVA[v]) if v in SUBSTATION_FIRM_MVA else 0.0
    used = [s for s in pr["stand_in"] if s.endswith(v) or (v == "11 kV" and s == "hv_switchboard")]
    return {"per_MW_GBP": per_mw, "fixed_GBP": fixed, "priced_at": v, "route_km": r,
            "price_list": pr["list"], "stand_in": used, "flags": pr["flags"]}


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
    cap = capital(voltage, case, route_km, region)
    f = annual_factor(region, transmission_connected)
    return {
        "per_MW_year_GBP": cap["per_MW_GBP"] / power_factor * f,
        "fixed_per_year_GBP": cap["fixed_GBP"] * f,
        "per_MW_GBP": cap["per_MW_GBP"] / power_factor,
        "fixed_GBP": cap["fixed_GBP"],
        "annual_factor": f,
        "rate_of_return": RATE_OF_RETURN.get(region, RATE_OF_RETURN_DEFAULT),
        "connection_voltage": voltage, "priced_at": cap["priced_at"], "route_km": cap["route_km"],
        "price_list": cap["price_list"], "stand_in": cap["stand_in"], "flags": cap["flags"],
        "case": case, "price_year": PRICE_YEAR,
    }


if __name__ == "__main__":
    from optimisation import duos_areas
    print("=" * 96)
    print(f"GRID CONNECTION CAPITAL BY AREA — each DNO's {PRICE_YEAR} statement; central case, 2 km route")
    print("=" * 96)
    print(f"  {'area':<28} {'list':<9} {'132 kV £/MW':>12} {'33 kV £/MW':>11} {'132 fixed':>10} {'33 fixed':>9} {'11 fixed':>9}  stand-in rows")
    for region in sorted(AREA_PRICE_LIST):
        c = {v: capital(v, "central", region=region) for v in VOLTAGES}
        pr = prices(region)
        print(f"  {duos_areas.AREA_NAMES[region]:<28} {pr['list']:<9} £{c['132 kV']['per_MW_GBP']:>10,.0f} £{c['33 kV']['per_MW_GBP']:>9,.0f} "
              f"£{c['132 kV']['fixed_GBP'] / 1e6:>6.2f} m £{c['33 kV']['fixed_GBP'] / 1e6:>5.2f} m £{c['11 kV']['fixed_GBP'] / 1e6:>5.2f} m  "
              f"{', '.join(pr['stand_in']) or '-'}")
    print()
    for row, v in (("substation", "132 kV"), ("substation", "33 kV"), ("hv_switchboard", None),
                   ("cable_first", "132 kV"), ("cable_per_m", "132 kV"), ("cable_first", "33 kV"),
                   ("cable_per_m", "33 kV"), ("cable_first", "11 kV"), ("cable_per_m", "11 kV")):
        lo, hi = median_row(row, v)
        print(f"  median {row} {v or '':<7} over {len(_published(row, v))} lists: £{lo:,.0f} - £{hi:,.0f}")
    print(f"\n  {NGED_SUBSTATION_FLAG}")
    print(f"  ASSUMED: {', '.join(ASSUMED)}.")
