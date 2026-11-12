"""
Hydrogen leaked outside the tank, charged at hydrogen's warming potential.
=============================================================================

Added 12 Nov 2026 (user: "do what gov does"). Until then only the tank's own
leakage was charged (dc_model, ``gwp_h2_leaked_per_kg`` on ``tank_leakage_per_hour``).

Source: Frazer-Nash Consultancy for BEIS, *Fugitive Hydrogen Emissions in a Future
Hydrogen Economy* (March 2022, FNC 012865-53172R Issue 1), summary table p. 6 and
Table 4 p. 39: emissions as a share of the hydrogen produced, carried or used in each
element, at 50 % confidence (the central estimate). The study's central scenario
assumes vented and purged hydrogen is recombined to water at the electrolyser and the
fuel cell, so those rows are the central figures here; its "with venting and purging"
rows are the upper bound, recorded and not charged.

=====================  =========  ====================  ======================
element                central    upper (recorded)      where charged
=====================  =========  ====================  ======================
electrolytic,          0.24 %     3.32 % (venting and   the electrolyser's kg
recombined                        purging)              made; a bought green kg
reformer with capture  0.25 %     0.50 % (99 %)         a bought blue or grey kg
road trailer, gas      0.30 %     0.66 % (99 %)         every bought kg
fuel cell, recombined  0.56 %     1.36 % (venting and   every kg made or bought
                                  purging)
=====================  =========  ====================  ======================

The fuel cell row is charged per kg made or bought rather than per kg burnt: the
fuel cell is the only use of hydrogen here, so the two differ only by what the tank
leaks first. The study's fuel cell row includes a vehicle's compressed tank (0.12-0.24
% a day for 0.5-3 days, its Table 3), which a stationary fuel cell fed just in time
or from the modelled tank does not have, so it errs high. Each kilogram leaked is
charged at ``dc_model.H2_GWP100``, the factor the tank's leakage already uses.
"""
from __future__ import annotations

from optimisation import trace as T
from optimisation.dc_model import H2_GWP100, H2_GWP100_SOURCE

SOURCE = "frazer_nash_beis_fugitive_h2_2022"
_AT = "summary table p. 6 and Table 4 p. 39, 50 % confidence"

ELECTROLYTIC = 0.0024          # recombined; 0.0332 with venting and purging
REFORMER_WITH_CAPTURE = 0.0025  # 0.0050 at 99 %
ROAD_TRAILER_GAS = 0.0030      # 0.0066 at 99 %; 0.12-0.24 %/day for 0.5-3 days
FUEL_CELL = 0.0056             # recombined; 0.0136 with venting and purging

UPPER = {"electrolytic": 0.0332, "reformer_with_capture": 0.0050,
         "road_trailer_gas": 0.0066, "fuel_cell": 0.0136}


def _kg(share: float) -> float:
    return share * H2_GWP100


def electrolyser_per_kg() -> float:
    """kg CO2e per kg made on site: the electrolyser's own leak and the fuel cell's."""
    return T.step("h2_leakage.electrolyser_per_kg", _kg(ELECTROLYTIC + FUEL_CELL), "kg CO2e per kg H2",
                  "Hydrogen leaked at the electrolyser and the fuel cell, per kg made on site",
                  grade="transcribed",
                  inputs={"electrolytic_share": ELECTROLYTIC, "fuel_cell_share": FUEL_CELL,
                          "h2_gwp100": H2_GWP100},
                  cites=[(SOURCE, _AT)],
                  note=f"Recombined vents, the study's central case; warming factor {H2_GWP100_SOURCE}")


def bought_per_kg(colour: str | None) -> float:
    """kg CO2e per kg bought: the seller's production leak by colour, the road trailer
    and the fuel cell. Zero when nothing is bought."""
    if not colour:
        return 0.0
    production = ELECTROLYTIC if colour == "green" else REFORMER_WITH_CAPTURE
    share = production + ROAD_TRAILER_GAS + FUEL_CELL
    return T.step(f"h2_leakage.bought_{colour}_per_kg", _kg(share), "kg CO2e per kg H2",
                  f"Hydrogen leaked making ({colour}), trucking and burning a bought kg",
                  grade="transcribed",
                  inputs={"production_share": production, "road_trailer_share": ROAD_TRAILER_GAS,
                          "fuel_cell_share": FUEL_CELL, "h2_gwp100": H2_GWP100},
                  cites=[(SOURCE, _AT)],
                  note=f"Recombined vents, the study's central case; warming factor {H2_GWP100_SOURCE}")
