"""
GB grid electricity, 2025 annual mean, delivered at high voltage.
=============================================================================

Source and scope
----------------
One kWh of the grid this study scores everywhere else (``optimiser_lca.grid``),
as a foreground activity, so that an inventory which takes GB grid power can
link to it instead of ecoinvent's own GB market.

Why it exists: the fossil hydrogen routes (Hermesmann's SMR, SMR-CCS and
methane pyrolysis) linked their electricity to ecoinvent 3.9.1's ``market for
electricity, high voltage`` [GB] — a 2018 mix, with gas on the conventional
plant this study rejected for its own grid on 13 Oct (558 against 387 g/kWh),
and the low-voltage market behind it at 311 g/kWh. Turquoise takes 10.29 kWh
per kg, so that dataset was 60 % of its burden. Relinked here, every grid kWh
in the study is on one basis.

Composition: the 2025 time-mean of NESO's GB-wide generation mix (Carbon
Intensity API region 18, built by ``grid_build.build_grid(18, ...)``),
each fuel on its ``grid.SOURCES`` activity, wind split by
``grid.WIND_GROUP_WEIGHTS``, imports by the national interconnector flows
recorded in the series. Shares are kept exactly as the series averages them
(they sum to 0.99974, as the API's own percentages do), so the activity scores
to the series mean.

Delivery: ``grid.DELIVERY["high"]`` — every source amount grossed up by the
high-voltage losses, plus the GB high-voltage market's own non-electricity
exchanges (HVDC lines, N2O from corona discharge, ozone) per kWh of
throughput, which is what ``grid.derive_delivery`` measures as the network
term. A seller of fossil hydrogen is an industrial plant at transmission
voltage, as Hermesmann's comment on the SMR plant says.

Checked: ``check_against_series()`` re-derives the shares from the CSV;
``optimiser_lca.validate`` scores the activity against the series mean.
"""
from __future__ import annotations

from optimiser_lca import grid as G
from optimiser_lca import registry as R
from optimiser_lca.common import Activity, Flow, Inventory, Process

# =============================================================================
# Parameters
# =============================================================================
SERIES_CSV = ("custom_grid_lca_outputs/custom_grid_lca_carbon_api_regional_auto_"
              "r18_cheap_2025-01-01T_to_T2025-12-31T23-30-00.csv")

# Time-mean share of each API fuel over 2025, as a fraction (the CSV's
# <fuel>_perc / 100). TRANSCRIBED from SERIES_CSV by check_against_series().
MIX_2025 = {
    "GAS": 0.281626, "NUCLEAR": 0.132925, "WIND": 0.321019, "HYDRO": 0.000379,
    "BIOMASS": 0.076279, "SOLAR": 0.062683,
    # coal, embedded wind, oil ("other") and pumped storage: zero in every
    # half-hour of 2025's GB series
}
# Imports by exporting country, as a share of all GB supply: mean over the
# year of IMPORTS_perc x imp_<CC>. They sum to the 12.48 % import share.
IMPORTS_2025 = {"FR": 0.065531, "BE": 0.010611, "NL": 0.007941,
                "NO": 0.027286, "DK": 0.012305, "IE": 0.001151}

# The GB high-voltage market's own exchanges per kWh *out*, other than
# electricity — ecoinvent 3.9.1 apos, read 14 Oct 2026. TRANSCRIBED.
HV_MARKET_NETWORK = {
    "hvdc_aerial": 2.16707783900465e-09,     # km
    "hvdc_land":   1.41928136392641e-10,     # km
    "hvdc_subsea": 2.69652501674501e-10,     # km
}
HV_MARKET_N2O_KG = 5e-06
HV_MARKET_OZONE_KG = 4.15772755242894e-06

# What the activity scores, IPCC 2021 GWP100 with long-term emissions. Pinned
# so h2_prices can charge fossil sellers' compression on it without Brightway;
# optimiser_lca.validate re-scores the activity and fails if it has moved. It
# equals the series' own mean delivered intensity, as it should.
GB_GRID_2025_HV_GCO2E_PER_KWH = 141.87395819488424

GROSS_UP = G.DELIVERY["high"]["gross_up"]
# The market's exchanges are per kWh it delivers; a kWh delivered here has
# passed through the market once, so they are taken at throughput, which at
# high voltage is the gross-up itself (grid.derive_delivery).
THROUGHPUT = GROSS_UP

# =============================================================================
# Processes
# =============================================================================
_needed = [k for k in MIX_2025 if k != "WIND"] + list(G.WIND_GROUP_WEIGHTS) + \
          [G.COUNTRY_SOURCE[c] for c in IMPORTS_2025]
processes = {k: G.SOURCES[k] for k in _needed}
processes.update({
    "hvdc_aerial": Process(
        identity=("market for transmission network, electricity, high voltage direct "
                  "current aerial line", "GLO",
                  "transmission network, electricity, high voltage direct current aerial line"),
        query="market for transmission network electricity high voltage direct current aerial line"),
    "hvdc_land": Process(
        identity=("market for transmission network, electricity, high voltage direct "
                  "current land cable", "GLO",
                  "transmission network, electricity, high voltage direct current land cable"),
        query="market for transmission network electricity high voltage direct current land cable"),
    "hvdc_subsea": Process(
        identity=("market for transmission network, electricity, high voltage direct "
                  "current subsea cable", "GLO",
                  "transmission network, electricity, high voltage direct current subsea cable"),
        query="market for transmission network electricity high voltage direct current subsea cable"),
})

flows = {
    "n2o": Flow(query="Dinitrogen monoxide", identity=("Dinitrogen monoxide", ("air",))),
    "ozone": Flow(query="Ozone", identity=("Ozone", ("air",))),
}

# =============================================================================
# Activities
# =============================================================================
_kwh = "kilowatt hour"


def _source_rows():
    rows = []
    for k, share in MIX_2025.items():
        if k == "WIND":
            for w, frac in G.WIND_GROUP_WEIGHTS.items():
                rows.append((w, share * frac * GROSS_UP, _kwh,
                             f"wind {share:.4f} x {frac:.4f} of the wind group, grossed up"))
        else:
            rows.append((k, share * GROSS_UP, _kwh, f"{k.lower()} {share:.4f}, grossed up"))
    for c, share in IMPORTS_2025.items():
        rows.append((G.COUNTRY_SOURCE[c], share * GROSS_UP, _kwh,
                     f"imports from {c} {share:.4f}, grossed up"))
    rows += [(k, v * THROUGHPUT, "kilometer", "GB HV market's own network, per kWh delivered")
             for k, v in HV_MARKET_NETWORK.items()]
    return rows


activities = [
    Activity(
        code=R.GB_GRID_HV_2025,
        name="electricity, high voltage, GB 2025 study grid, delivered",
        reference_product="electricity, high voltage",
        unit=_kwh, location="GB",
        comment="One kWh of GB grid electricity on this study's own basis "
                "(optimiser_lca.grid): NESO's GB-wide 2025 mix, time-mean, each fuel on "
                "its grid.SOURCES activity, imports split by the 2025 interconnector "
                "flows, delivered at high voltage (losses and the HV market's network "
                "exchanges). Replaces ecoinvent's 2018 GB market for the fossil "
                "hydrogen routes.",
        technosphere=_source_rows(),
        biosphere=[
            ("n2o", HV_MARKET_N2O_KG * THROUGHPUT, "kilogram",
             "corona discharge, from the GB HV market"),
            ("ozone", HV_MARKET_OZONE_KG * THROUGHPUT, "kilogram",
             "from the GB HV market"),
        ],
    ),
]


def check_against_series(root=None, tol=1e-5) -> str:
    """Re-derive MIX_2025 and IMPORTS_2025 from the series; fail if they moved."""
    from pathlib import Path
    import pandas as pd
    root = Path(root) if root else Path(__file__).resolve().parent.parent
    df = pd.read_csv(root / SERIES_CSV)
    problems = []
    for k, want in MIX_2025.items():
        got = df[f"{k}_perc"].mean() / 100.0
        if abs(got - want) > tol:
            problems.append(f"{k}: series {got:.6f}, constant {want:.6f}")
    for k in ("COAL", "WIND_EMB", "OTHER", "STORAGE"):
        if df[f"{k}_perc"].abs().max() > 0:
            problems.append(f"{k} is not zero in the series")
    for c, want in IMPORTS_2025.items():
        got = (df["IMPORTS_perc"] * df[f"imp_{c}"]).mean() / 100.0
        if abs(got - want) > tol:
            problems.append(f"imports {c}: series {got:.6f}, constant {want:.6f}")
    if problems:
        raise AssertionError("gb_grid shares are stale:\n  " + "\n  ".join(problems))
    return (f"OK — shares match {len(df):,} half-hours; series mean "
            f"{df['custom_electricity_score'].mean() * 1000:.2f} g CO2e/kWh delivered")


def inventory() -> Inventory:
    return Inventory(name="GB grid, 2025 study basis", database=R.GRID_DB,
                     processes=processes, flows=flows, activities=activities)
