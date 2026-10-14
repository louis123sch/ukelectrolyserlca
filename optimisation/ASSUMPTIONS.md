# Optimisation study — scope assumptions

Decisions that are not derivable from the inventories or the code, recorded
here so the write-up and the optimiser cannot disagree about them.

## 1. Data centre runs flat at 100 %

Continuous draw of **7,306 kW**. This is not an added assumption: the Zhang et
al. foreground's own operation exchange is 1.60e9 kWh over a 25-year life,
which is 7,306 kW continuous. It is where the old `dashboard_config.SYS_DC_DEMAND_MW
= 7.31` came from.

That figure is the **whole facility**, at Zhang's own PUE of 1.4, so the IT load
behind it is **5,219 kW**. The two must not be confused: `size_mw_it` is an IT
load and is multiplied by the caller's PUE to get demand, so passing 7.31 with a
PUE above 1.0 models a facility larger than Zhang's. `DC_REFERENCE_PUE` exists to
make the conversion explicit and is the only place Zhang's PUE is used — the
facility's embodied burden is anchored on IT capacity, not on facility draw, so
improving PUE no longer shrinks the building.

*Consequence*: no load-shifting option, and no diurnal or seasonal demand
shape. Storage is therefore sized purely against supply variability, never
against demand variability — which makes renewables+storage look somewhat
harder than it would with a flexible AI training load.

## 2. Geography is GB, via the electricity exchange

The data centre foreground is authored in Virginia against `market for
electricity, medium voltage [US-SERC]`. Rather than re-authoring the
inventory, that electricity is swapped for the half-hourly GB grid mix from the
Carbon Intensity API (`optimisation/grid_build.py`, originally notebook 3.1),
by the exact `fixed + Σ kWh×EF` decomposition in `baseline_grid.py`.

The inventory has **exactly one** electricity exchange — IT + cooling/aux,
1.60e9 kWh over 25 years — and it is the only US-located input in the activity.
The swap is applied two ways, which agree to 1e-4 %: the full Brightway
substitution above, and the `fixed + Σ kWh×EF` decomposition
`baseline_grid.py` uses so the optimiser can treat the facility as linear
coefficients.

*Residual*: the remaining twelve exchanges are **global-market** datasets —
`GLO` for reinforcing and structural steel, copper, aluminium, tap water, the
diesel genset, the UPS battery and R134a; `RoW` for PUR foam and sodium
hypochlorite. So they are not US-specific, but they are not GB-specific either,
and no transport leg is modelled at all. Together they are 841 t CO2e/y
amortised, 5.3 % of baseline 1. Sourcing them to GB/European supply chains is a
known, unmodelled refinement.

*Scope*: the activity is **Material Production + Operation only**.
Transportation, construction energy and water, disposal and recycling are
excluded by scope choice, as the foreground's own comment records — so the
facility carries no decommissioning or demolition burden. See §6.

## 3. Hydrogen the study *makes* is co-located with its use; hydrogen it *buys* is compressed but not hauled

No hydrogen transport, distribution or liquefaction is modelled, for any
hydrogen pathway — green, grey, blue or turquoise. Self-production assumes a
plant adjacent to the data centre, feeding the fuel cell (or the storage tank)
directly at the plant gate.

**Delivery compression is no longer excluded.** It used to be, on the same
co-location argument — but that argument covers hydrogen this study produces and
not hydrogen it purchases, which by definition comes from somebody else's plant.
Meanwhile self-produced hydrogen was charged a compression parasitic to enter
the tank and bought hydrogen was not, so the exclusion was also an asymmetry
that favoured buying. Every bought colour now carries the work of compressing it
to 200 bar tube-trailer pressure at the seller's gate, in both objectives —
`h2_prices.bought_h2_compression_*`, detailed in `SOURCES.md`. Road haulage
itself is still excluded, and is registered in `DATA_GAPS.md` rather than
justified here.

*Verified*: no H2 distribution exchange exists in `hydrogen foreground`,
`fuel cell foreground` or `hydrogen storage foreground`, so nothing is being
double-counted. The two transport exchanges that do exist are unrelated —
CO2-to-storage pipeline inside the CCS chain, and the negative passenger-car
term that removes ecoinvent's domestic-micro-CHP service-visit artefact.

*Consequence*: the SMR / SMR-CCS / MP-E options implicitly site a reformer or
pyrolysis unit on the data centre campus, fed from the gas grid. Plausible at
this scale, but it is an assumption, not a finding. The "off-site green
hydrogen" option is now "green hydrogen bought at a price, with its production
burden and its compression, but no haulage".

Storage compression is still counted where it applies, via
`dc_config.TANK_COMPRESSION_KWH_PER_KG` — zero for the 28 bar design,
since the electrolyser already delivers at ~30 bar.

**Bought green hydrogen is green by definition, and that rests on certificates.**
Decided 2–3 Sep. The grid-connected share of bought green
(`h2_prices.GREEN_H2_GRID_SHARE`, 0.5) is scored on a *renewable* electricity
basis plus the grid's high-voltage delivery terms — 1.107 kg CO₂e/kg against
0.976 behind the meter — not on the grid mix the electrolyser physically draws from. That is a
market-based reading, and it holds only if the seller's grid electricity is
backed by matched renewable certificates (REGOs, or an RFNBO-style hourly match).
Two things follow that the numbers do not show on their own:

- The price carries **no certificate premium**. NESO's and EHO's grid-connected
  LCOH are priced on wholesale power, so the bought-green price is the cost of
  the electricity, not of the claim to it.
- The LP's **own** grid electrolyser (`grid_h2`) is scored on the real
  location-based grid mix instead. Same physical setup, two bases: about
  **8.8 kg CO₂e/kg** made on site at London's 2025 annual mean against **1.06**
  bought. The asymmetry favours
  buying, and it is deliberate — the study assumes a buyer can contract for
  certified green hydrogen but does not assume the data centre certifies its own
  imports. Anyone comparing `grid_h2` with bought green should read the gap as
  partly an accounting convention, not only physics. Audit §3.6.

## 2b. Grid carbon is an average, attributional, life-cycle figure

**Average, not marginal.** Every grid import is charged the half-hour's
*average* life-cycle intensity of the region's generation mix, never the
marginal plant's. That is the attributional reading, and it matches every
other coefficient in the study: an asset is charged its own inventory, not the
change it causes elsewhere. A marginal (consequential) factor answers a
different question — what the system emits *because* the data centre draws one
more kWh — and would change what avoiding an import is worth: Hawkes puts GB's
long-run marginal at 0.26–0.53 kg CO₂/kWh now against a 0.69 short-run, both
well above today's average. Using it would need a consequential treatment of
every asset as well, so it is out of scope, and the Overview lists it as an
extension. Which way it would move the answer is not one-signed — a marginal
factor values an avoided import differently and swings differently across the
day — so this is recorded as a limitation, not a bias of known direction.

**Delivered at the connection voltage.** A kWh imported carries the losses and
the network's embodied carbon down to the voltage the site connects at
(`optimiser_lca.grid.DELIVERY`, ecoinvent's GB voltage chain). Every site this
study prices connects at high voltage — transmission, or an EHV distribution
band — so imports pay ×1.0338 on generation plus 1.93 g/kWh. A bought-hydrogen
seller's grid electricity is delivered on the same constants
(`h2_prices.GREEN_H2_SELLER_VOLTAGE`), so the two grid users share one basis.

**Imports follow the flows that reach the region.** The API reports a region's
imports as one figure. It is split across exporting countries each half-hour by
Elexon's interconnector flows, weighted by a per-region attribution fitted to
NESO's own regional import share (`optimiser_lca.grid.IMPORT_ATTRIBUTION`). The
fit is a calibration to NESO's regional model, not a physical flow trace;
every exporter is scored on its own country's average HV market, not on the
plant at its margin.

## 3a. The site is a coordinate, and everything follows from it

`sites.resolve(lat, lon)` derives the Carbon Intensity region and the TNUoS
demand zone from the coordinate, so the weather, the grid mix and the network
bill cannot drift apart from one another. Two real lookups
(postcodes.io → Carbon Intensity API) plus a fixed GSP-group correspondence for
the TNUoS zone, checked against presets set independently from published
sources.

*Consequence, and it is a correction*: the old `dashboard_config.WIND_LAT / WIND_LON`
(51.7320, -0.3711) is a field near **St Albans** — Carbon Intensity region 10,
TNUoS zone 9. Every cached grid series in this repo is **region 13, London**,
TNUoS zone 12. So the study as it previously stood paired London's grid carbon
intensity and London's £7.41/kW demand tariff with a Hertfordshire wind site.

Carbon-wise the two regions are similar and the error is small. The network
charge is not: zone 12 is £7.41/kW against zone 9's £1.11/kW. Nothing warned
about it because nothing connected the wind coordinate to the grid region.
`require_grid_region()` now refuses the combination outright, and the matrix is
run at a coordinate genuinely inside region 13.

## 3b. Every half-hourly series is on UTC

Grid carbon, wholesale price and wind/solar are joined on naive UTC timestamps,
and a requested window is read as UTC. Until 12 Oct 2026 the grid series was
London local time while price and weather were UTC, so from late March to late
October intraday grid carbon sat an hour late against everything else (Audit
§3.5). Every saved grid file was rebuilt on UTC that day and carries a
`clock = UTC` column; `profiles.py` ignores grid files without it.

Rules published on the UK clock convert from UTC where they are applied: the
DUoS red/amber/green bands (`network_charges.duos_band`) and Elexon settlement
periods (`grid_build.normalise_elexon`). The DUoS red band is November-February
only, so it never moved; amber did, by an hour, all summer.

## 3c. Generation is onshore wind and ground-mount solar only

Every site is on land (decided 3 Sep), so offshore wind is out of scope and
`dc_architectures.OFFSHORE_IN_SCOPE` holds it off for every architecture and
every caller. It used to be unlocked wherever `sites.Site.offshore_wind` flagged
a coastal region, and the LP has no offshore profile — `cap_offshore` ran on the
*onshore* capacity-factor series, so in the high cost case it built offshore on
onshore yield. The offshore coefficients are still built and reported; turning
the switch back on needs an offshore series first.

## 4. Cost basis

DESNZ/Arup 2024 Cost of Electricity reports, **2023 real prices**, with each
technology's own pre-tax real hurdle rate (onshore wind 5.8 %, offshore wind
6.2 %, solar PV 5.0 %) rather than a single project WACC. Set
`optimisation.tech_costs.DISCOUNT_RATE_OVERRIDE` to impose one rate instead.

*One asymmetry, deliberate*: generation step-up transformers
(`transformers.py`) are charged in **carbon and not in cost**. The DESNZ/Arup
capex is plant-plus-connection-to-the-point-of-connection, so it already
contains the electrical balance of plant; a separate £/MW transformer charge
would double count, while the carbon side has no such term anywhere — none of
the generation inventories contains a transformer, and ecoinvent has no power
transformer at any rating to supply one. See SOURCES.md.

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

## 6. No end-of-life, anywhere

The study is **cradle-to-gate on every input**, with the functional unit being
the data centre powered at a given size, year and location. Nothing is followed
past the site gate on the way out: no demolition, decommissioning, disposal or
recycling, and no recycling credit, for the facility or for any energy asset.

Every foreground already meets this without modification:

| Foreground | Position |
|---|---|
| Data centre | Material production + operation only; disposal and recycling excluded by scope choice |
| H2 storage tank | Steel mass only; end-of-life listed among its stated omissions |
| Grid connection | Transformer materials only (Leng 2026's 100 MVA, 110 kV main transformer, per MVA, × 2 for N-1), plus a line term reported but not charged per MW; no switchgear, protection, civils, manufacturing energy, losses or end-of-life |
| Generation step-up transformers | Transformer capital only; no switchgear, protection or civils, no manufacturing energy, and no losses |
| Grid battery | Jasper/Voß cradle-to-gate manufacture including the cell factory's energy; Jasper's EOL sheet not taken, every delivery-transport row left out (and subtracted where a source folded it into a factor), no foundation |
| Electrolysers | Capital good plus consumables; no end-of-life exchange |
| Fuel cell stack | Babatunde et al. cradle-to-gate manufacture, no use or end-of-life phase |
| Fuel cell BoP / maintenance | Usai et al. 2021 process loops + inverter + container, cradle-to-gate; service consumables only. No end-of-life, no delivery transport |

The SMR-CCS chain's "CCS waste treatment" activity is **not** an exception: it
is the capture and storage leg of a production route, inside the gate.

*Residual, and it cannot be declared away*: coefficients scored on **ecoinvent
3.9.1 apos** carry end-of-life inside their background datasets, because the
APOS system model allocates waste-treatment burdens back into the product
system. This affects the wind, offshore, battery pack, inverter, transformer
and tank-steel terms, and cannot be stripped exchange-by-exchange from outside.
The cut-off system model is the one that corresponds to a strict cradle-to-gate
rule; moving to it would break the "3.9.1 apos throughout" consistency claim and
every pinned constant, so the embedded share is declared here rather than
removed.

## 7. The facility's standby generator is excluded

Zhang's inventory carries a diesel standby generator — 8.6e6 MJ over the life,
**32.5 t CO2e/yr** at his facility size. It is scored, reported by
`dc_inputs.data_centre_coefficients()` as
`backup_kgco2e_per_year_excluded`, and **left out of every objective**.

Backup is a *decision variable* in this study: the optimiser sizes a fuel cell,
a battery, a grid connection and an unserved-energy allowance to provide exactly
the resilience the genset provides. Charging Zhang's genset on top would bill
every architecture for a second backup system, and would bill the islanded ones
twice over for a function they were built to supply.

*Consequence*: the grid-connected baselines lose an asset a real site would
probably have. The number is preserved rather than deleted so it can be added
back for a like-for-like comparison against a conventional facility.

The UPS battery is **not** treated this way and stays in. Ride-through over
seconds is a different function from bulk storage, so it is not a double count.

