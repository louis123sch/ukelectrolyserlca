# The screened inputs at their ranges

The inputs `scripts/screen_inputs.py` picked (`input_screen.md`), one at a time at their ranges (`sensitivity.SHAKY_KNOBS`). The test: the same technologies built and no built size moved by more than 5 % at the same anchor. Rig rows compare rig with rig and only chose what was solved hourly; the verdicts are the hourly ones.

## Hourly, norfolk_grid_green

| Variant | Anchor | Same technologies? | Largest size move | Cost | Carbon | |
|---|---|---|---|---|---|---|
| push=cost.fuel_cell.capex_per_kW*0.5 | min_cost | yes | solar -3.3% | -5.68 % | +0.84 % | holds |
| push=cost.fuel_cell.capex_per_kW*0.5 | min_gwp | yes | solar +0.0% | -9.79 % | +0.00 % | holds |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_cost | yes | batt_e +6.1% | +5.52 % | -0.82 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_gwp | yes | batt_e +0.3% | +9.79 % | +0.00 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_cost | yes | batt_p +0.0% | +0.00 % | -6.30 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_gwp | yes | batt_e +1657.0% | -7.90 % | -1.93 % | **moves** |
| push=battery.energy_per_usable_kWh*1.5 | min_cost | yes | batt_p -0.0% | -0.00 % | +6.30 % | holds |
| push=battery.energy_per_usable_kWh*1.5 | min_gwp | yes | batt_e -88.6% | +1.38 % | +0.16 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| push=coefficient.cost_ely*0.5 | min_gwp | yes | ely +0.6% | -2.62 % | -0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_gwp | yes | ely -0.2% | +2.61 % | -0.00 % | holds |
| push=cost.bought_h2.green.delivered*0.5 | min_cost | yes | batt_p -18.1% | -6.30 % | -2.93 % | **moves** |
| push=cost.bought_h2.green.delivered*0.5 | min_gwp | yes | solar -0.0% | -7.37 % | +0.00 % | holds |
| push=cost.bought_h2.green.delivered*1.5 | min_cost | yes | batt_e +11.1% | +4.06 % | -1.35 % | **moves** |
| push=cost.bought_h2.green.delivered*1.5 | min_gwp | yes | batt_e +1.2% | +7.36 % | +0.00 % | holds |
| batt_cell_basis=voss_de | min_cost | yes | grid +0.0% | +0.00 % | -0.97 % | holds |
| batt_cell_basis=voss_de | min_gwp | yes | batt_e +66.7% | -0.71 % | -0.06 % | **moves** |
| green_h2_grid_share=0.0 | min_cost | yes | batt_p -5.1% | -1.53 % | +0.46 % | **moves** |
| green_h2_grid_share=0.0 | min_gwp | yes | batt_e -17.7% | -2.49 % | -0.94 % | **moves** |
| green_h2_grid_share=1.0 | min_cost | yes | wind +3.5% | +1.40 % | -0.58 % | holds |
| green_h2_grid_share=1.0 | min_gwp | yes | tank +16.6% | +2.49 % | +0.85 % | **moves** |
| wind_life_extension=none | min_cost | yes | grid +0.0% | +0.00 % | -2.63 % | holds |
| wind_life_extension=none | min_gwp | yes | solar -24.8% | +3.69 % | -6.12 % | **moves** |
| wind_life_extension=servicing | min_cost | yes | grid +0.0% | +0.00 % | -1.96 % | holds |
| wind_life_extension=servicing | min_gwp | yes | batt_e -20.3% | +2.54 % | -4.50 % | **moves** |
| tank_design=gandiglio_28bar | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| tank_design=gandiglio_28bar | min_gwp | no: -ely, tank | batt_e +229.8% | -3.40 % | +0.92 % | **moves** |
| fc_stack_calendar_years=5.0 | min_cost | yes | solar +0.7% | +1.79 % | +0.86 % | holds |
| fc_stack_calendar_years=5.0 | min_gwp | yes | grid +3983.4% | -1.88 % | +2.77 % | **moves** |
| fc_stack_calendar_years=15.0 | min_cost | yes | wind -0.3% | -0.60 % | -0.27 % | holds |
| fc_stack_calendar_years=15.0 | min_gwp | yes | batt_e -19.6% | -0.87 % | -1.04 % | **moves** |
| fc_stack_duty_hours=20000.0 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=20000.0 | min_gwp | yes | solar +0.0% | -0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_gwp | yes | grid +0.0% | -0.00 % | +0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_gwp | yes | batt_e -8.3% | -0.08 % | -0.07 % | **moves** |
| tank_leakage_per_hour=0.0001 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| tank_leakage_per_hour=0.0001 | min_gwp | yes | batt_e +4.5% | -0.03 % | +0.07 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_cost | yes | batt_p -0.3% | +0.05 % | +0.04 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_gwp | yes | ely +0.1% | +0.02 % | +0.00 % | holds |
| batt_tx_x_eff=1.0 | min_cost | yes | batt_e +0.3% | +0.10 % | +0.09 % | holds |
| batt_tx_x_eff=1.0 | min_gwp | yes | batt_e -4.6% | +0.10 % | +0.00 % | holds |
| fc_tx_x_eff=0.5 | min_cost | yes | fc -0.2% | -0.09 % | +0.02 % | holds |
| fc_tx_x_eff=0.5 | min_gwp | yes | batt_e -5.8% | -0.15 % | -0.09 % | **moves** |

**These move the design and are reported with the result:** batt_cell_basis=voss_de, fc_stack_calendar_years=15.0, fc_stack_calendar_years=5.0, fc_tx_x_eff=0.5, green_h2_grid_share=0.0, green_h2_grid_share=1.0, push=battery.energy_per_usable_kWh*0.5, push=battery.energy_per_usable_kWh*1.5, push=cost.bought_h2.green.delivered*0.5, push=cost.bought_h2.green.delivered*1.5, push=cost.fuel_cell.capex_per_kW*1.5, tank_design=gandiglio_28bar, tank_leakage_per_hour=0.0, wind_life_extension=none, wind_life_extension=servicing

## Rig (4-hour steps), islanded_h2

Flag at 3 % on the rig.

| Variant | Anchor | Same technologies? | Largest size move | Cost | Carbon | |
|---|---|---|---|---|---|---|
| push=cost.fuel_cell.capex_per_kW*0.5 | min_cost | yes | fc +34.5% | -3.03 % | -2.50 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*0.5 | min_gwp | yes | ely -0.0% | -7.19 % | +0.00 % | holds |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_cost | yes | fc -17.2% | +2.05 % | +1.39 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_gwp | yes | ely -0.0% | +7.19 % | +0.00 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_cost | yes | fc -0.0% | -0.00 % | -12.90 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_gwp | yes | batt_e +1622.6% | -7.91 % | -1.63 % | **moves** |
| push=battery.energy_per_usable_kWh*1.5 | min_cost | yes | fc +0.0% | -0.00 % | +12.90 % | holds |
| push=battery.energy_per_usable_kWh*1.5 | min_gwp | no: -batt_e, batt_p | fc +6.2% | +1.35 % | +0.08 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_cost | yes | fc +24.5% | -0.42 % | -1.78 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_gwp | yes | ely +0.3% | -5.07 % | -0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_cost | yes | fc -12.2% | +0.38 % | +0.89 % | **moves** |
| push=coefficient.cost_ely*1.5 | min_gwp | yes | ely -0.0% | +5.06 % | -0.00 % | holds |
| batt_cell_basis=voss_de | min_cost | yes | fc -0.0% | -0.00 % | -1.99 % | holds |
| batt_cell_basis=voss_de | min_gwp | yes | batt_p +42.5% | -0.30 % | -0.04 % | **moves** |
| batt_cell_basis=jasper_fig4_311 | min_cost | yes | fc +0.0% | +0.00 % | +3.12 % | holds |
| batt_cell_basis=jasper_fig4_311 | min_gwp | yes | ely +0.1% | +0.00 % | +0.06 % | holds |
| wind_life_extension=none | min_cost | yes | fc +0.0% | +0.00 % | -4.85 % | holds |
| wind_life_extension=none | min_gwp | yes | ely -9.4% | -0.16 % | -7.64 % | **moves** |
| wind_life_extension=servicing | min_cost | yes | fc +0.0% | -0.00 % | -3.61 % | holds |
| wind_life_extension=servicing | min_gwp | yes | ely -9.4% | -0.16 % | -5.69 % | **moves** |
| tank_design=gandiglio_28bar | min_cost | yes | solar +0.5% | -0.00 % | +19.51 % | holds |
| tank_design=gandiglio_28bar | min_gwp | yes | batt_e +1433.5% | -2.57 % | +23.33 % | **moves** |
| fc_stack_basis=gramc_2025 | min_cost | yes | fc +0.0% | +0.00 % | -0.30 % | holds |
| fc_stack_basis=gramc_2025 | min_gwp | yes | ely +0.3% | +0.01 % | -1.31 % | holds |
| fc_stack_calendar_years=5.0 | min_cost | yes | fc -13.3% | +0.70 % | +1.49 % | **moves** |
| fc_stack_calendar_years=5.0 | min_gwp | yes | batt_p +77.0% | +1.68 % | +2.53 % | **moves** |
| fc_stack_calendar_years=15.0 | min_cost | yes | fc +23.9% | -0.28 % | -1.95 % | **moves** |
| fc_stack_calendar_years=15.0 | min_gwp | yes | ely +0.1% | -0.76 % | -0.85 % | holds |
| fc_stack_duty_hours=20000.0 | min_cost | yes | ely +0.0% | +0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=20000.0 | min_gwp | yes | ely +0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_cost | yes | ely +0.0% | +0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_gwp | yes | ely -0.0% | -0.00 % | -0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_cost | yes | fc +4.8% | -0.10 % | -0.98 % | **moves** |
| tank_leakage_per_hour=0.0 | min_gwp | yes | ely +4.5% | +0.04 % | -0.43 % | **moves** |
| tank_leakage_per_hour=0.0001 | min_cost | yes | tank -2.8% | +0.10 % | +0.75 % | holds |
| tank_leakage_per_hour=0.0001 | min_gwp | yes | ely -2.9% | +0.04 % | +0.42 % | holds |
| batt_standing_loss_per_hour=0.0 | min_cost | yes | fc -0.2% | -0.11 % | -0.08 % | holds |
| batt_standing_loss_per_hour=0.0 | min_gwp | yes | batt_e -0.0% | -0.00 % | -0.00 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_cost | yes | fc +5.3% | +0.10 % | -0.29 % | **moves** |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_gwp | yes | batt_e +0.0% | +0.00 % | +0.00 % | holds |
| batt_tx_x_eff=1.0 | min_cost | yes | fc +5.0% | +0.11 % | -0.26 % | **moves** |
| batt_tx_x_eff=1.0 | min_gwp | yes | batt_p +0.4% | +0.00 % | +0.00 % | holds |
| fc_tx_x_eff=0.5 | min_cost | yes | fc +4.5% | -0.06 % | -0.38 % | **moves** |
| fc_tx_x_eff=0.5 | min_gwp | yes | fc -0.4% | -0.16 % | -0.09 % | holds |

## Rig (4-hour steps), norfolk_grid_green

Flag at 3 % on the rig.

| Variant | Anchor | Same technologies? | Largest size move | Cost | Carbon | |
|---|---|---|---|---|---|---|
| push=cost.fuel_cell.capex_per_kW*0.5 | min_cost | yes | solar -4.7% | -5.75 % | +1.07 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*0.5 | min_gwp | yes | batt_e -0.0% | -9.90 % | -0.00 % | holds |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_cost | yes | batt_e +5.7% | +5.56 % | -0.55 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_gwp | yes | batt_e +0.7% | +9.90 % | +0.00 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_cost | yes | batt_p +0.0% | +0.00 % | -6.07 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_gwp | yes | batt_e +2209.6% | -7.44 % | -1.66 % | **moves** |
| push=battery.energy_per_usable_kWh*1.5 | min_cost | yes | wind -0.0% | +0.00 % | +6.07 % | holds |
| push=battery.energy_per_usable_kWh*1.5 | min_gwp | no: -batt_e, batt_p | ely +10.7% | +1.38 % | +0.10 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_cost | yes | grid +0.0% | -0.00 % | -0.00 % | holds |
| push=coefficient.cost_ely*0.5 | min_gwp | yes | batt_p -0.2% | -2.39 % | -0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_gwp | yes | batt_p +0.7% | +2.39 % | -0.00 % | holds |
| push=cost.bought_h2.green.delivered*0.5 | min_cost | yes | batt_p -18.3% | -6.11 % | -3.05 % | **moves** |
| push=cost.bought_h2.green.delivered*0.5 | min_gwp | yes | batt_p +0.0% | -7.05 % | +0.00 % | holds |
| push=cost.bought_h2.green.delivered*1.5 | min_cost | yes | batt_e +9.0% | +3.98 % | -1.12 % | **moves** |
| push=cost.bought_h2.green.delivered*1.5 | min_gwp | yes | batt_e +0.6% | +7.05 % | +0.00 % | holds |
| batt_cell_basis=voss_de | min_cost | yes | wind +0.0% | +0.00 % | -0.94 % | holds |
| batt_cell_basis=voss_de | min_gwp | yes | batt_e +63.2% | -0.51 % | -0.04 % | **moves** |
| batt_cell_basis=jasper_fig4_311 | min_cost | yes | wind -0.0% | +0.00 % | +1.47 % | holds |
| batt_cell_basis=jasper_fig4_311 | min_gwp | yes | batt_p -1.4% | +0.01 % | +0.05 % | holds |
| green_h2_grid_share=0.0 | min_cost | yes | batt_p -5.0% | -1.49 % | +0.70 % | **moves** |
| green_h2_grid_share=0.0 | min_gwp | yes | solar -14.3% | -2.51 % | -0.91 % | **moves** |
| green_h2_grid_share=1.0 | min_cost | yes | solar +2.7% | +1.34 % | -0.24 % | holds |
| green_h2_grid_share=1.0 | min_gwp | yes | tank +16.5% | +2.45 % | +0.82 % | **moves** |
| wind_life_extension=none | min_cost | yes | wind +0.0% | +0.00 % | -2.60 % | holds |
| wind_life_extension=none | min_gwp | yes | solar -33.7% | +4.01 % | -6.20 % | **moves** |
| wind_life_extension=servicing | min_cost | yes | wind +0.0% | +0.00 % | -1.94 % | holds |
| wind_life_extension=servicing | min_gwp | yes | solar -24.0% | +2.44 % | -4.55 % | **moves** |
| tank_design=gandiglio_28bar | min_cost | yes | wind +0.0% | +0.00 % | -0.00 % | holds |
| tank_design=gandiglio_28bar | min_gwp | no: -ely, tank | batt_e +212.2% | -2.54 % | +0.84 % | **moves** |
| fc_stack_basis=gramc_2025 | min_cost | yes | wind +0.0% | +0.00 % | -0.56 % | holds |
| fc_stack_basis=gramc_2025 | min_gwp | yes | batt_p -1.4% | +0.00 % | -1.61 % | holds |
| fc_stack_calendar_years=5.0 | min_cost | yes | solar +1.6% | +1.80 % | +0.81 % | holds |
| fc_stack_calendar_years=5.0 | min_gwp | yes | grid +3983.5% | -1.11 % | +2.77 % | **moves** |
| fc_stack_calendar_years=15.0 | min_cost | yes | batt_p -1.4% | -0.60 % | -0.30 % | holds |
| fc_stack_calendar_years=15.0 | min_gwp | yes | batt_p -1.4% | -1.05 % | -1.05 % | holds |
| fc_stack_duty_hours=20000.0 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=20000.0 | min_gwp | yes | batt_e +0.0% | -0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_cost | yes | wind +0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_gwp | yes | batt_e +0.0% | -0.00 % | +0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_gwp | yes | batt_p +0.5% | -0.01 % | -0.07 % | holds |
| tank_leakage_per_hour=0.0001 | min_cost | yes | grid +0.0% | +0.00 % | -0.00 % | holds |
| tank_leakage_per_hour=0.0001 | min_gwp | yes | tank -3.2% | -0.01 % | +0.07 % | **moves** |
| batt_standing_loss_per_hour=0.0 | min_cost | yes | fc -0.2% | -0.05 % | -0.01 % | holds |
| batt_standing_loss_per_hour=0.0 | min_gwp | yes | batt_e +0.9% | -0.00 % | -0.00 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_cost | yes | batt_p +0.3% | +0.05 % | +0.03 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_gwp | yes | batt_p -0.1% | +0.00 % | +0.00 % | holds |
| batt_tx_x_eff=1.0 | min_cost | yes | batt_p -0.9% | +0.09 % | +0.11 % | holds |
| batt_tx_x_eff=1.0 | min_gwp | yes | batt_e -0.3% | +0.01 % | +0.00 % | holds |
| fc_tx_x_eff=0.5 | min_cost | yes | batt_p -0.6% | -0.09 % | +0.01 % | holds |
| fc_tx_x_eff=0.5 | min_gwp | yes | batt_e +1.3% | -0.16 % | -0.09 % | holds |
