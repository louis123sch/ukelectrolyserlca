# Fixes from the REopt comparison (20 Nov 2026)

The comparison is `Claude outputs/reopt_cost_comparison.md` in the main checkout. The user said "implement everything" on 20 Nov 2026. Nothing below has been solved on a real site yet; the tests in `tests/test_reopt_fixes.py` use toy models only.

## 1. Solar's cost per MWh sees discounted ageing

- **What:** the dispatch keeps the plain life-average output (0.8705, right for carbon). Solar's yearly cost is multiplied by plain ÷ discounted = 0.8705 / 0.9254 = **0.941**. The discounted figure is the discount-weighted mean at solar's 7.6 % over 38 years, REopt's `levelization_factor`.
- **Where:** `optimisation/profiles.py` `solar_discounted_ageing_factor`; `optimisation/dc_inputs.py` `build_tech` (`cost.solar_pv.ageing_discount_correction`, used in `cost_solar`).
- **Effect:** solar's line falls about £4.5k per MWp a year (2026 pounds, central). It follows any `solar_ageing_factor` override: 1.0 means no correction.

## 2. Spare power held off grid

- **What:** with no grid, every step must hold spare output ≥ 10 % of demand + 50 % of wind delivered + 25 % of solar delivered. These are REopt's off-grid defaults (`electric_load.jl:20`, `wind.jl:36`, `pv.jl:46`); no UK figure was found. Counting towards it:
  - the fuel cells' and engines' unused size;
  - the electrolyser's draw;
  - spilled wind and solar, less their own share;
  - the battery: stopping its charge, plus more discharge, up to its unused power and to what it holds for one hour on top of its current discharge.
- **Where:**
  - `optimisation/dc_model.py`: `Tech.reserve_*` fields, default 0 so older setups reproduce, and `build_model` (10b), constraints `reserve_battery_power` and `reserve_battery_energy`.
  - `optimisation/dc_inputs.py`: `RESERVE_*` constants and the traced steps `reserve.load_fraction`, `reserve.wind_fraction`, `reserve.solar_fraction` and `reserve.battery_hours`.
- **Off with a grid**, as in REopt. The fuel cell's part assumes the tank holds an hour of hydrogen. Maintenance outages are not modelled.
- **Tests:** `reserve.load_fraction` and `reserve.wind_fraction` are pushed ×0.5/×1.5 in `sensitivity.SHAKY_KNOBS`, on islanded cases only.

## 3. Solar losses test

`build_series(pv_system_loss=)` rescales the cached solar series by (1 − value) ÷ (1 − 0.10). It is in `sensitivity.SERIES_KNOBS`, and `SHAKY_KNOBS["pv_system_loss"] = [0.05, 0.15]`. Ninja's inverter step moves a little with loading, so this is close, not exact.

## 4. Battery cycles reported

Each Pareto point carries `batt_cycles_per_year` (solved) and `batt_cycles_assumed` (`battery.CYCLES_PER_YEAR_IN_USE`, 180). `dc_pareto.summarise` prints the knee battery's cycles beside the 180. The oversize itself is unchanged.

## 5. Carbon-price point

Each point carries `ge_co2_carbon_priced_kg_per_year`. `special_points` adds the carbon price only on carbon net of it, so engine CO2 is not priced twice. Fronts saved before this column existed are read as before.

## Pages

`docs/model_equations_explorer.html` has section 4.6b and the symbols `rl`, `rw`, `rs`, `Hres` and `Gpr`, and the carbon-price point now reads net. The model explainer was rebuilt.

## Still to do, on the user's word

Before/after solves at East Grinstead (51.2, 0.0), islanded and grid-connected, to size the effect of #1 and #2. Sign-off as in `docs/TESTING.md`. `DATA_GAPS.md` was not edited, because another session had uncommitted changes in it; the limitations (no maintenance outages; REopt's shares, not a UK figure) are recorded here for now.
