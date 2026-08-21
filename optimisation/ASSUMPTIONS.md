# Optimisation study — scope assumptions

Decisions that are not derivable from the inventories or the code, recorded
here so the write-up and the optimiser cannot disagree about them.

## 1. Data centre runs flat at 100 %

Continuous draw of **7,306 kW**. This is not an added assumption: the Zhang et
al. foreground's own operation exchange is 1.60e9 kWh over a 25-year life,
which is 7,306 kW continuous. It is where `dashboard_config.SYS_DC_DEMAND_MW
= 7.31` came from.

*Consequence*: no load-shifting option, and no diurnal or seasonal demand
shape. Storage is therefore sized purely against supply variability, never
against demand variability — which makes renewables+storage look somewhat
harder than it would with a flexible AI training load.

## 2. Geography is GB, via the electricity exchange

The data centre foreground is authored in Virginia against `market for
electricity, medium voltage [US-SERC]`. Rather than re-authoring the
inventory, all three of its electricity exchanges are swapped for the
half-hourly GB grid mix from the Carbon Intensity API
(`3.1.custom_grid_carbon_intensity_api.ipynb`), using
`lca_helpers.run_lca_with_custom_elec()`.

The three swapped exchanges are IT + cooling/aux (1.60e9 kWh), construction
(7.8e4 kWh) and demolition (1.4e4 kWh). The latter two are 0.006 % of the
total and are GB-appropriate anyway once the facility is notionally sited in
GB, so all three are swapped rather than only the operational one.

*Residual*: the facility's **materials** remain US-authored — concrete [RNA],
sea freight tagged "Asia to US", US freight rail. These are one-off embodied
burdens (841 t CO2e/y amortised, 5.3 % of baseline 1) and are left as-is.
Re-siting the supply chain to GB is a known, unmodelled refinement.

## 3. Hydrogen is always co-located with its use

No hydrogen transport, distribution, liquefaction or delivery compression is
modelled, for any hydrogen pathway — green, grey, blue or turquoise. Every
pathway assumes production adjacent to the data centre, feeding the fuel cell
(or the storage tank) directly at the plant gate.

*Verified*: no H2 distribution exchange exists in `hydrogen foreground`,
`fuel cell foreground` or `hydrogen storage foreground`, so nothing is being
double-counted. The two transport exchanges that do exist are unrelated —
CO2-to-storage pipeline inside the CCS chain, and the negative passenger-car
term that removes ecoinvent's domestic-micro-CHP service-visit artefact.

*Consequence*: the SMR / SMR-CCS / MP-E options implicitly site a reformer or
pyrolysis unit on the data centre campus, fed from the gas grid. Plausible at
this scale, but it is an assumption, not a finding. It also means the "off-site
green hydrogen" option collapses into "green hydrogen bought at a price with
its production burden and no delivery burden".

Storage compression is still counted where it applies, via
`dashboard_config.TANK_COMPRESSION_KWH_PER_KG` — zero for the 28 bar design,
since the electrolyser already delivers at ~30 bar.

## 4. Cost basis

DESNZ/Arup 2024 Cost of Electricity reports, **2023 real prices**, with each
technology's own pre-tax real hurdle rate (onshore wind 5.8 %, offshore wind
6.2 %, solar PV 5.0 %) rather than a single project WACC. Set
`optimisation.tech_costs.DISCOUNT_RATE_OVERRIDE` to impose one rate instead.

Electricity is priced at the Elexon APXMIDP half-hourly wholesale price. No
demand-side network charges (DUoS/TNUoS), levies or supplier margin are
included yet, so absolute £/MWh understates a real import bill. The
connection and UoS figures in the DESNZ tables are *generator*-side and are
not a substitute.

## 5. Emissions are IPCC 2021 GWP100, attributional

Grid electricity uses the **average** attributional intensity of the regional
mix, not short-run marginal intensity. This is the right basis for reporting
the facility's footprint; it is the wrong basis for claiming that shifting a
load reduces real-world emissions. Any timing-based result should be reported
against both.
