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
1.60e9 kWh over 25 years — and it is the only US-*grid* input in the activity
(the concrete is RNA, i.e. North American, as the audit noted).
The swap is applied two ways, which agree to 1e-4 %: the full Brightway
substitution above, and the `fixed + Σ kWh×EF` decomposition
`baseline_grid.py` uses so the optimiser can treat the facility as linear
coefficients.

*Residual*: the remaining twelve exchanges are **global-market** datasets —
`GLO` for reinforcing and structural steel, copper, aluminium, tap water, the
diesel genset, the UPS battery and R134a; `RoW` for PUR foam and sodium
hypochlorite. So they are not US-specific, but they are not GB-specific either,
and no transport leg is modelled at all. Together with the materials they are
about 963 t CO2e/y charged at the reference facility (14 Oct 2026, after the
refrigerant leakage was added), plus the 32.5 t genset the LP excludes.
Sourcing them to GB/European supply chains is a known, unmodelled refinement.
The R134a top-up is also emitted as HFC-134a: Zhang derive it as leakage
replacement (see SOURCES.md).

*Scope*: the activity is **Material Production + Construction + Operation**
(construction energy and water in since 21 Oct 2026: they are in the source
and inside the boundary). Transportation (delivery to site), disposal and
recycling are outside the boundary — so the facility carries no
decommissioning or demolition burden. See §6. Zhang's own figures put the
facility at 7.53 MW with 5.38 MW of IT; the 7,306 / 5,219 kW read out of the
1.60e9 kWh they print sit 3 % under those (7.53 MW × 8,760 h × 25 y is 1.649e9,
printed rounded down). The energy-driven part is charged per MWh of that printed
electricity, so it is unaffected. The IT-driven part (servers, UPS, building,
construction) was sized on 5.38 MW of IT, so since 26 Oct 2026 it is normalised
by 5.38 MW, not by the 5.219 MW read back (`data_centre.ZHANG_IT_MW`; it was 3.1 %
high per MW of IT before). Zhang's §2.2b names chillers, cooling towers, pumps and
piping as in scope but S1 does not disaggregate them, and the 2,000 kg initial
R134a charge is a sizing note, not an inventory row: both are taken as inside
Zhang's own rows and not added (user, 26 Oct 2026).

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
`h2_storage.compression_kwh_per_kg` from the electrolyser's delivery pressure
to the tank's — zero for the 28 bar design, since the electrolyser already
delivers at ~30 bar.

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
periods (`grid_build.normalise_elexon`). The DUoS bands run all year (red
weekdays 11:00–14:00 and 16:00–19:00), so in summer every band moves by an hour.

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

Electricity is priced at the Elexon APXMIDP half-hourly wholesale price plus
the demand-side network charges `network_charges.py` builds (TNUoS, BSUoS,
DUoS) and, since 28 Oct 2026, the FY2026/27 policy levies and losses
`levies.py` builds: RO, FiT, CfD, AAHEDC, Nuclear RAB and CCL as one flat
£/MWh, the Capacity Market levy on its 16:00–19:00 winter working-day window,
and wholesale and BSUoS grossed up for losses: the site's own area's line loss
factor for the connection voltage and time period, times the offtaking
transmission loss multiplier for its zone and season (1 + zonal TLF read from
Elexon's 2026/27 report charts + an assumed national adjustment of 0.011).
**Assumed**: the site holds no Climate Change Agreement (`CCL_UNDER_CCA`;
with one, CCL falls from £7.75 to £0.62/MWh). Supplier margin is not included.
The connection and UoS figures in the DESNZ tables are *generator*-side and
are not a substitute.

**The national grid's location charge** (HH locational TNUoS) is charged on winter-evening demand, as the tariff is: the most the site imports in any weekday half-hour from 16:30 to 18:30, November to February, the window every Triad of the last seven winters fell in. A battery or fuel cell that covers that window saves it; the charge for the connection itself (DUoS capacity, connection capital) stays on the connection size.

**One tariff year.** Every network charge — TNUoS, the residual and its band
boundaries, BSUoS and every area's DUoS — is the **2026/27** tariff (`network_charges.TARIFF_FY`),
applied to whatever weather and wholesale window is solved. The levies are 2026/27
too (`levies.LEVY_FY`) since 28 Oct 2026.

**Where the connection runs to** (since 29 Oct 2026): the nearest substation at the connection voltage in the substation register, with the cable priced on the straight-line distance times an **assumed 1.3** route factor (no UK figure found). If the substation's published spare capacity is below the connection the run is flagged, and both routes round it are reported; the model builds at the nearest substation unless `shortfall_route="next"`. A 33 or 132 kV site's local network charges are set for its own nearest price node plus its area's **calibrated** add-on (`ehv_charges`), except in SSEN's two areas, which charged outside the method for 2026/27 and keep the listed-site median.

**The connection voltage** of a distribution site is the lowest its area's DNO connects it at, by that DNO's own published rule where there is one (`network_charges.AREA_RULES`): 11 kV up to 12 MVA by default (15 in the North West, under 8 in London), then 33 kV (up to 120 MVA, and always in Scotland), then 132 kV up to 240 MVA (250 in the NGED areas). Where a DNO publishes nothing the default stands in, and says so. Sizes the rules leave open can be solved both ways — an option, not the default. An 11 kV site takes HV residual bands and its grid electricity at medium voltage; 33 and 132 kV sites take EHV bands and high voltage.

**The connection tier** follows GB's voltage rule, not a size threshold: a DNO
connects demand up to 240 MVA in England and Wales and up to 120 MVA in
Scotland, where 132 kV is transmission (ENWL ES216; the Scottish figure is a
proxy). Above that the site is transmission-connected and pays no DUoS. Below it the site
pays its own area's DUoS (`duos_areas`): an 11 kV site its area's HV Site Specific
row, a 33 or 132 kV site the median of its area's listed EHV sites in the same
band, each in that area's own time bands, and its area's line loss factors.
`Site.transmission_connected` overrides the rule — a real connection offer
beats it. The TDR band is read from the connection ceiling and the built
connection is held inside that band (`floor ≤ cap_grid ≤ ceiling`); a run
whose connection sits on the floor is flagged, and re-running with a lower
ceiling is the user's call.

**The connection's capital** (`connection_cost.py`) is charged on the same
split as its carbon: the intake substation per MW of `cap_grid` and the cable
to the network as a fixed annual cost, annualised the way CUSC Section 14
charges connection assets. Under the Access SCR a demand customer pays for its
extension assets only, so no reinforcement contribution is added.

## 5. Emissions are IPCC 2021 GWP100, attributional

Grid electricity uses the **average** attributional intensity of the regional
mix, not short-run marginal intensity. This is the right basis for reporting
the facility's footprint; it is the wrong basis for claiming that shifting a
load reduces real-world emissions. Any timing-based result should be reported
against both.

**No credits anywhere; co-products carry no burden away.** Decided 21 Oct
2026. The study takes no avoided-burden credits: not for recycling (§6), and
not for co-products. Two cases in the inventories: methane pyrolysis, where
Hermesmann & Müller credit the 3 kg of solid carbon per kg H₂ against carbon
black, and SMR / SMR-CCS, where they credit the excess electricity (1.10 and
0.05 kWh per kg) as an avoided burden — the second was carried "as the source
does" until 22 Oct 2026 and is now dropped too (+1.4 % on grey). Here the whole
burden sits on the hydrogen. Electrolysis oxygen is likewise an unallocated
co-product. This keeps the study attributional throughout, at the cost of
making turquoise hydrogen look worse than its source reports.

## 6. No end-of-life, anywhere

The study is **cradle-to-gate on every input**, with the functional unit being
the data centre powered at a given size, year and location. Nothing is followed
past the site gate on the way out: no demolition, decommissioning, disposal or
recycling, and no recycling credit, for the facility or for any energy asset.

**Transport to site is outside the boundary, and nothing else is.** No capital
good, cable or hydrogen is carried to the site, for any technology, because
where the site will be is not known. Transport further up the supply chain does
not depend on the site and is kept: ecoinvent's market transport, legs between
manufacturing stages, materials to a factory.

Every foreground already meets this without modification:

| Foreground | Position |
|---|---|
| Data centre | Material production, construction and operation; transportation (delivery to site), disposal and recycling outside the boundary |
| H2 storage tank | Shell, its forming, frame and pad; valves and compressor hardware on the cut-off register; end-of-life out |
| Grid connection | Transformer materials (Leng 2026's 100 MVA, 110 kV main transformer, per MVA, × 2 for N-1) and the switchyard's civils per MW of connection (Leng's outdoor venue, D2), plus a line term reported but not charged per MW; switchgear, protection and manufacturing energy carried as cut-off estimates (§8); losses in the LP; no end-of-life |
| Generation step-up transformers | Transformer capital (wind materials-only; solar with IEA PVPS process energy); no switchgear, protection or civils. Losses are charged as energy in the LP (`conversion_losses.py`), not as a coefficient |
| Battery and fuel-cell step-ups (15 Oct) | Jasper 2026's container transformer mass on the IEA PVPS composition (with its process energy), a stated substitution for Jasper's own Hunziker-derived recipe on representativeness (SOURCES.md, 22 Oct), per MW of inverter rating, over the asset's own life; no switchgear, protection or civils. Losses in the LP at ASSUMED loadings (0.5 battery, 1.0 fuel cell), the fuel cell's unit energised on standby |
| Grid battery | Jasper/Voß cradle-to-gate manufacture including the cell factory's energy and upstream transport; Jasper's EOL sheet not taken, his delivery-to-site rows left out (Voß's legs to a German factory not taken, and subtracted where folded into a factor), no foundation |
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

<!-- cutoff:begin -->
## 8. Cut-off rule

A flow that is in a held source and inside the boundary is always in; the
boundary excludes only end-of-life, delivery to site and the standby generator
(§6–7). The cut-off test below applies to flows no held source itemises: each
may stay out only if its upper estimate is under 1% of its technology's
carbon (rule 1), all of a technology's together under 5% (rule 2), and
adding them all back must not change the best design (rule 3, the `cutoff`
sensitivity knob). Criteria after PAS 2050 and Vestas V162 §3.3, applied per
technology; rule 3 is this study's addition under ISO 14044's sensitivity
requirement for comparative assertions. Not ecoinvent's "cut-off" system model.
Battery power-side flows are tested at a 1 h floor; energy-side flows at their
ceiling. A flow that fails is included (status below). Register:
`optimiser_lca/exclusions.py`; this section is generated by
`python optimisation/cutoff.py --write`.

### Rule 1 — per flow

| Technology | Flow | Kind | Status | Central | Upper | Unit | Share at upper | Verdict |
|---|---|---|---|---|---|---|---|---|
| battery | cell processing materials (NMP make-up, argon, nitrogen, compressed air) | cutoff | excluded | 9.47 | 47.4 | kg CO2e per usable MWh per year | 0.62% | pass |
| battery | site installation (crane and commissioning diesel) | cutoff | excluded | 7.77 | 15.5 | kg CO2e per usable MWh per year | 0.20% | pass |
| battery | container switchgear (MV, one per container) | cutoff | included_estimate | 102 | 186 | kg CO2e per MW per year | 1.70% | included (estimate) |
| fuel cell | container switchgear (MV, one per container) | cutoff | included_estimate | 76.2 | 139 | kg CO2e per MW per year, calendar replacements | 1.06% | included (estimate) |
| fuel cell | balance-of-plant assembly energy | cutoff | excluded | 50.8 | 127 | kg CO2e per MW per year, calendar replacements | 0.97% | pass |
| hydrogen tank | forming of the vessel steel (rolling, welding) | cutoff | included_inventory | 8.02 | 33.9 | kg CO2e per kg of capacity per year | — | in the inventory |
| hydrogen tank | valves, pipework and fittings | cutoff | included_estimate | 0.639 | 1.28 | kg CO2e per kg of capacity per year | 1.58% | included (estimate) |
| hydrogen tank | compressor hardware | cutoff | excluded | 0.01 | 0.03 | kg CO2e per kg of capacity per year | 0.04% | pass |
| wind | step-up switchgear (turbine MV switchgear) | cutoff | excluded | 43.6 | 79.6 | kg CO2e per MW per year (turbine + step-ups) | 0.32% | pass |
| wind | step-up transformer replacement rate | cutoff | excluded | 0 | 98.2 | kg CO2e per MW per year (turbine + step-ups) | 0.40% | pass |
| wind | Leng's electrical installation beyond its four printed rows | cutoff | excluded | 0 | 125 | kg CO2e per MW per year (turbine + step-ups) | 0.51% | pass |
| wind | step-up transformer factory energy | cutoff | excluded | 17.3 | 34.2 | kg CO2e per MW per year (turbine + step-ups) | 0.14% | pass |
| solar | step-up switchgear (inverter-station MV switchgear) | cutoff | excluded | 40.1 | 73.4 | kg CO2e per MWp per year (plant + step-ups) | 0.30% | pass |
| grid connection | switchgear and protection (MV + HV devices) | cutoff | included_estimate | 38.1 | 69.7 | kg CO2e per MW of connection per year | 22.85% | included (estimate) |
| grid connection | HV bay steelwork and grid-connection hardware (Teffera) | cutoff | included_estimate | 18.1 | 33 | kg CO2e per MW of connection per year | 10.83% | included (estimate) |
| grid connection | intake transformer factory energy | cutoff | included_estimate | 7.67 | 15.1 | kg CO2e per MW of connection per year | 4.96% | included (estimate) |
| grid connection | substation civils — Leng's outdoor venue (switchyard formation, concrete, rebar) | sourced | included_inventory | 98.6 | 98.6 | kg CO2e per MW of connection per year | — | sourced — built as inventory rows |
| grid connection | booster-station construction machinery (Leng S3), the switchyard's share | sourced | included_estimate | 4.85 | 14.1 | kg CO2e per MW of connection per year | 4.63% | sourced — carried as the source's own figure |
| electrolyser | SOEC electrolyte layer — lanthanum oxide and strontium carbonate | cutoff | included_inventory | 75 | 150 | kg CO2e per MW per year | — | in the inventory |
| facility | internal MV/LV electrical distribution (transformers, switchgear) | cutoff | excluded | 4.6e+04 | 9.3e+04 | kg CO2e per year | 0.60% | pass |

### Rule 2 — per technology

| Technology | Denominator | Unit | Cut-off entries | Still excluded | Sum of upper shares | Verdict |
|---|---|---|---|---|---|---|
| wind | 2.47e+04 | kg CO2e/MW/yr | 4 | 4 | 1.36% | pass |
| solar | 2.41e+04 | kg CO2e/MWp/yr | 1 | 1 | 0.30% | pass |
| battery | 3.27e+03 | kg CO2e/MW/yr (p) and per usable MWh/yr (e) | 3 | 2 | 0.82% | pass |
| electrolyser | 1.98e+04 | kg CO2e/MW/yr | 1 | 0 | 0.00% | n/a |
| hydrogen tank | 80.8 | kg CO2e per kg capacity/yr | 3 | 1 | 0.04% | pass |
| fuel cell | 1.31e+04 | kg CO2e/MW/yr, calendar replacements | 2 | 1 | 0.97% | pass |
| grid connection | 305 | kg CO2e/MW/yr | 3 | 0 | 0.00% | n/a |
| grid electricity | — | kg CO2e/kWh (series mean; no entries) | 0 | 0 | 0.00% | n/a |
| bought hydrogen | 1.14 | kg CO2e/kg | 0 | 0 | 0.00% | n/a |
| facility | 1.54e+07 | kg CO2e/yr | 1 | 1 | 0.60% | pass |

### Boundary items — reported, not tested

| Technology | What | Why |
|---|---|---|
| all | end-of-life of every asset | ASSUMPTIONS.md §6 — cradle-to-gate throughout; APOS carries some EoL in the background |
| electrolyser | delivery to site — Gerloff's second 250 km lorry leg | ASSUMPTIONS.md §6; Gerloff 2021 §2.1 — the first leg, to assembly, is in |
| solar | delivery to site — Z-PV-239's 100 km light-commercial leg 'to construction place' | ASSUMPTIONS.md §6; IEA PVPS workbook remark O29 — out since 22 Oct 2026; was in from 21 Oct |
| battery | delivery to site — Jasper's China-to-Germany lorry, sea and rail legs for finished parts | ASSUMPTIONS.md §6; Jasper et al. 2026 SI transport rows — upstream legs to the module and rack factories are in |
| solar | delivery to site — Smith A14 rail, lorry and sea rows | ASSUMPTIONS.md §6; Smith 2024 Table A14 — the sea leg alone is 201 t·km/m² for the import chain (~1.5 % of the plant) |
| facility | delivery to site — Zhang's Transportation phase | ASSUMPTIONS.md §6; Zhang et al. 2025 Table S1 |
| wind | delivery to site — Leng Table S2 to-site legs (both transformers) | ASSUMPTIONS.md §6; Leng et al. 2026 Table S2 |
| wind | on-site transport — Leng Table S2 'intra-site transport' (300 km) and the booster station's 3 km on-site construction leg | ASSUMPTIONS.md §6; Leng et al. 2026 Table S2 and SI p. 4 — read as part of getting the equipment to and around a site that is not known: the same boundary as delivery to site (user, 26 Oct 2026). Serves the step-ups and the grid connection |
| bought hydrogen | road haulage from the seller to the site | ASSUMPTIONS.md §3; TODO.md (parked) — trailer compression is charged; the journey depends on where the seller is |
| facility | standby diesel generator — Zhang's 8.6e6 MJ | ASSUMPTIONS.md §7 — scored and reported by data_centre.py / dc_inputs; out of every objective because backup is a decision variable |

### Rule 3 — the design-change test

The two reference cases re-solved at both anchors with every still-excluded flow added at its
upper estimate (`dc_inputs.build_tech(cutoff="upper")`, sensitivity knob `cutoff`), against the
central model. Q4's test: the same technologies are built and no built capacity moves by more than
5 %. Solved 23 Oct 2026; `optimisation_outputs/sensitivity_cutoff_*.csv`.

| Case | Anchor | Technologies built | Same with upper? | Largest capacity move | GWP t/yr, central → upper | Verdict |
|---|---|---|---|---|---|---|
| london_grid | min_cost | batt_e, batt_p, grid, solar, wind | yes | grid -0.0% | 108,904 → 109,096 | pass |
| london_grid | min_gwp | batt_e, batt_p, fc, grid, solar, wind | yes | grid +3.0% | 52,926 → 53,193 | pass |
| islanded_h2 | min_cost | batt_e, batt_p, ely, fc, solar, tank, wind | yes | batt_e +0.0% | 71,895 → 72,285 | pass |
| islanded_h2 | min_gwp | batt_e, batt_p, ely, fc, solar, tank, wind | yes | batt_e -1.1% | 63,828 → 64,148 | pass |

**Rule 3 passes**: at both anchors of both cases the upper-estimate run builds the same technologies and moves no capacity by more than 5 %.

The London case was solved with the grid connection at 282.0 kg CO2e per MW per year; the switchyard's
share of Leng's construction machinery (+4.85, carried since 22 Oct 2026) was added while it ran. At the
145 MW connection the minimum-cost design builds that is 0.7 t CO2e a year, under a millionth of the
system, so it cannot move a design. The islanded case has no grid connection.

<!-- cutoff:end -->
