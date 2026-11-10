# Which inputs could matter: the screen, 10 Nov 2026

`python scripts/screen_inputs.py --series` on the newest saved run (North Norfolk, 100 MW of computing, every
asset, bought green hydrogen on offer, 2025 hourly; the run the maps and workbooks are built from). No
optimiser run: each recorded number is pushed to half and to one and a half times its value through the real
cost and carbon code, and the run's three designs (lowest cost, knee, lowest carbon) are re-scored **with the
design held fixed**. The figure below is the most either total (cost or carbon) moves at any of the three
points. It ranks candidates for the ±30–50 % runs. It does not say whether the design changes: that needs a
solve.

Full table: `input_screen.csv` (315 rows). Each technology's share of each total: `input_screen_shares.csv`.

## What came out

Of 146 numbers taken from a source or assumed, **29 move a total by 1 % or more** when pushed ±50 %
(19 read from a source, 10 assumed). **84 move it by under 1 %** and are screened out by the cut-off rule's own
yardstick. The rest could not be pushed this way (below).

### 1. Unsure and influential: the shortlist for the ±30–50 % runs

| Input | Grade | Most a total moves | Note |
|---|---|---|---|
| Fuel cell capital (Baringa, one 80 MW plant) | read from one source, "thin evidence" in DATA_GAPS | cost 9.8 % | |
| Bought green hydrogen price (Hydrogen Observatory) | read from a source | cost 8.1 % | **named by the supervisor** |
| Battery carbon per usable kWh (Jasper's container, grossed up) | assumed | carbon 6.1 % | **named by the supervisor**; the cell-source choice moves it 1.5 % |
| Electricity the green-hydrogen seller runs on (half over the network) | assumed | carbon 5.7 %, cost 2.5 % | the register's "weakest input" in bought hydrogen |
| Wind servicing to reach 35 years | assumed | carbon 2.8–5.6 % | |
| Tank vessel (carbon steel vs stainless) | a choice between sources | carbon 4.6 %; the tank's own carbon ×3.6 | already known to change the low-carbon design; tank not built at lowest cost or knee |
| Electrolyser capital and stack share (NESO, one figure, no range) | read from a source | cost 2.6 % | electrolyser not built at lowest cost or knee: could tip in |
| Fuel cell stack carbon source | a choice between sources | carbon 1.6 % | |

### 2. Need a solve: they act through how the plant runs

With the running held fixed they move nothing, so the screen cannot judge them. They go straight to the
4-hour runs: fuel cell stack life in years and in running hours, tank leakage, battery self-discharge, the
container transformers' loadings.

### 3. Influential but from UK government sources: vary on their published ranges, not ±50 %

Wind capital (DESNZ/Arup, 17.8 %), CEPA's discount rates (wind 16.6 %, hydrogen plant 8.0 %, solar 5.8 %,
battery 4.5 %), wind life (9.9 %), battery life (7.8 %) and capital (NESO, 6.6 %), solar capital (6.4 %), wind
and solar carbon (13.2 % and 7.1 %). The capital costs are what the low/high cost case moves; on 4–5 Nov that
moved the bill −28 % / +42 % and no size by more than 2–3 %. The discount rates are not in the cost case.

### 4. Large but cannot change the design

The data centre's own carbon (18 %: the same for every design), its cooling consumables (3 %), and the price
base (every pound together).

### 5. The grid

Its prices and carbon are year-long series, not single numbers, so they are judged by share: grid import is
19 % of carbon and grid energy and network charges 6 % of cost at the lowest-cost point, so ±50 % moves those
totals by about 10 % and 3 %. Both shares are small at the other two points, where the connection is held to
its 24.5 MW limit.

## What the screen could not push

- **Recorded only (74):** the code reads a table or a figure made from the number rather than the number
  itself (fuel cell capital as Baringa prints it, NESO's battery table, the network charge schedules). The
  figure made from it was pushed instead, which is how fuel cell and battery capital appear above.
- **Not pushed (67):** flags, labels and tables (the levies, loss factors, the connection price lists). The
  connection's price has its own ±50 % test (`connection_sensitivity.md`).
