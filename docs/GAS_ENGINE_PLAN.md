# Gas engines — decision record (13 Nov 2026)

A new optional technology: natural-gas reciprocating engine generators on the data-centre site,
behind the meter, competing with the hydrogen fuel cell as dispatchable backup. Agreed with the
user in a design discussion on 13 Nov 2026, checked against the project's past mistakes and by an
independent review before any code. This file is the brief the build follows; anything not here
is not part of the change.

## 1. What it is
- Gas engine generators ("gas engines"; not combined heat and power — no heat is used), modular
  ~3.45 MW engines, generating at up to 11 kV (Jenbacher J620 data: 600 V – 11 kV), with
  **no step-up transformer** (user, 13 Nov, after the build review found the model's bus is
  "20 kV"): the 20 kV of `stepup_transformers.TX_SITE_COLLECTION_KV` is an assumed point in the
  medium-voltage band (1–24 kV), chosen because the IEA PVPS unit is wound 20/0.4 kV; a GB site
  would more likely run at 11 kV, which the engines generate at. The other step-ups stand: they
  take low voltage (400–690 V) to medium voltage at any bus voltage, their mass is set by their
  rating, and Reg. 548/2014 Tier 2 sets the same loss limits for every winding up to 24 kV. Had an
  11/20 kV unit been charged: about 0.6 t CO2e per MW a year and about 0.8 % of output.
- Asset flag `gas_engine`, **off in every existing scenario**; available as a tick-box.
- LP: capacity `cap_ge` (MW), dispatch `p_ge` (MW per step), replacement count `ge_units`.
  Linear: no minimum load, no start-up cost (engines come in small blocks). No availability
  derating (the fuel cell has none either; the study's 95 % is stated, not applied).

## 2. Costs — UK government first
Source: DESNZ, *Unabated gas: electricity generation cost study* (CEPA and GHD), gov.uk,
14 January 2026, 2024 prices, Generation Option 5 "Reciprocating engines", 20 MW reference plant
(six 3.45 MW containerised engines), section 3.5 and Table 5.4.

| Item | Low / central / high | Table |
|---|---|---|
| Capital (EPC, excludes connections) | £450 / 529 / 609 per kW | 3.25, 5.4 |
| Development, **land included** | £12.7 / 29.5 / 34.6 per kW (user, 13 Nov: land is sourced, so it is in) | 3.25, 5.4 |
| Fixed fee | £12,400 / 14,630 / 16,820 per MW per year | 3.27 |
| Variable fee, split into fixed + per MWh from the 500 h and 1,500 h rows | £1,700 / 2,002 / 2,300 per MW-yr + £2.32 / 2.73 / 3.14 per MWh | 3.27, 3.28 |
| Insurance | 0.3 / 0.4 / 0.5 % of capital and development per year | 3.27 |
| Construction | 0.4 / 1.0 / 1.3 years; the study's finance factor takes whole years, so all three are carried as one (×1.0436) | 3.23 |
| Life | 25 years calendar, 100,000 running hours (whichever first) | §3.5 |

- The study's own range sets the three cost cases (no ×0.5/×1.5 on these).
- Discount rate 8.9 %: CEPA for DESNZ 2025, Table E.1 "Gas generation – unabated" (defined to
  include gas reciprocating engines) — the same report every other asset's rate comes from.
- Business rates: the hydrogen plant's estimate (`h2_capex.rates_frac`), user 13 Nov, on capital and development.
- **Land (decided 13 Nov, after the build):** first taken excluding land, on the mistaken reading that
  the fuel cell and battery leave land out by rule (they leave it out only because their unsourced
  estimates passed 1 %). The study itemises the engines' land (Table 5.4: £3.8–22.4/kW), and a sourced
  cost inside the boundary goes in whatever its size, so development is taken **including land**
  (about 2 % of the engines' full yearly cost). Spread over 25 years with the capital, as the study's
  cost basis does, though land does not wear out.
- The levy exemption and carbon price support apply to stations of **2 MW or more**, and the UK ETS
  to combustion of more than **20 MW thermal** (~9 MW of engines); the linear model applies the GB
  total carbon price at any size. Stated, not modelled.
- Inflated 2024 → 2025 → 2026 pounds through `price_base`.
- The variable-fee split is extrapolated beyond 1,500 h when the engine runs more; stated.
- **Left out (user decision, recorded for later):** the study's "infrastructure" line (gas and
  power connection, £1.1 / 2.1 / 4.2 m per 20 MW). The power side is not needed behind the meter;
  the gas pipe is left out as a user decision, not as delivery to site (the grid cable is costed,
  so this errs in favour of gas). TODO.md carries it.
- Gas network capacity charges for low-running plant: not modelled (user: ignore).

**Gas.** `dc_inputs.engine_gas_gbp_per_mwh`: the site gas price (DESNZ non-domestic table 3.4.2,
large band, 2025, inflated, DESNZ 2026 market ratio, gas price case) **without** the Climate
Change Levy — fuel for a generating station of 2 MW or more, auto-generators included, is exempt
from the main rates and liable to carbon price support instead (HMRC Excise Notice CCL1/6,
§4.1, §6). Its own function, so the levy-agreement switch cannot touch it. Gas is priced on the
higher heating value, the engine's efficiency is on the lower: one conversion constant.

**Carbon price.** NESO's GB total carbon price for 2026 (UK ETS plus carbon price support,
`h2_prices.carbon_gbp_per_t_2026()`, already 2026 pounds) on the burning CO2 only.

**Power the engine makes is not charged the electricity levy** (like wind, solar and fuel cell).

## 3. Carbon — running, per MWh of net electricity
Efficiency 44.6 % on the lower heating value (study Table 3.24) and ecoinvent's GB gas (net 36.0,
gross 40.0 MJ/m³; 0.735 kg/m³; 74.1 % fossil carbon) give 224.2 m³ per MWh.

- 224.2 m³ `market for natural gas, high pressure` | GB — supply chain and leaks (the same gas the
  hydrogen inventories use). High pressure, stated (local low-pressure gas would add ~2.6 %).
- CO2 from the carbon balance of that gas, less the carbon leaving as methane and carbon monoxide.
- Engine exhaust per m³ copied from `heat and power co-generation, natural gas, 1MW electrical,
  lean burn` | Europe without Switzerland: methane (the engine line, "estimate based on different
  references"), dinitrogen monoxide, carbon monoxide, nitrogen oxides, NMVOC, particulates,
  sulphur dioxide; lubricating oil in, waste mineral oil out.
- Dropped from that dataset: its CO2 (its v2 figure exceeds the gas's carbon content); its
  low-pressure network methane line (the plant takes high-pressure gas, whose leaks are already in
  the GB market); its European gas; its construction lines.
- Maintenance per running hour: the set's `maintenance, heat and power co-generation unit, 160kW
  electrical` (2.89 per 1 MW set) over ecoinvent's 100,000 h unit life, its car trips out — about
  0.77 kg CO2e per MWh.
- Check against DESNZ GHG conversion factors 2026 (fossil gas burning 0.18442, well-to-tank
  0.03021 kg CO2e per kWh gross): a test, not an input.

## 4. Carbon — building, per MW, charged on `ge_units` (25 y or 100,000 h, whichever first)
- 1 × `…unit construction, 1MW electrical, common components for heat+electricity` | RER
- 1 × `…unit construction, 1MW electrical, components for electricity only` | RER
- not the `…components for heat only` (hot-water storage, heating equipment, heat pump)
- less the set's maintenance (moved to per running hour, §3)
- 166.7 m² `market for building, hall, steel construction` | GLO: the 500 m² building of ecoinvent's
  3 MW organic Rankine cycle power unit, per MW — a stand-in (no gas-engine hall in ecoinvent).
  Charged with the plant over 25 years (user), not the hall's own 50.
- Both the engine set's concrete pads and the hall's floor are kept; the floor under the engines
  is counted twice, which errs against gas (user).
- Car trips: the set's construction work and start-up trips (4,698 km per MW) and its maintenance
  trips are travel to site and are removed (boundary rows). The trips inside the *production* of
  the electric parts and the air units (22,707 km per MW) are upstream and stay.
- When duty binds the whole plant is replaced, hall included — errs against gas, as the fuel cell's
  balance of plant does.
- The hall is carbon only: the study prices six containerised engines and its capital (with its
  "buildings and structures" line) is taken whole, so no hall is added on the cost side.

## 5. Boundary, rules, checks
- Data centre's emergency diesel standby generator stays excluded (ASSUMPTIONS §7): the gas engines
  are a separate plant the optimiser chooses.
- Every ecoinvent pick by exact identity; transport audit test; carbon balance test; band test;
  government figures pinned in tests; no London; no solves until the user says.
