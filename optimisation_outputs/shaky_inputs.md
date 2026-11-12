# The screened inputs at their ranges

The inputs `scripts/screen_inputs.py` picked (`input_screen.md`), one at a time at their ranges (`sensitivity.SHAKY_KNOBS`). The test: the same technologies built and no built size moved by more than 5 % at the same anchor. Rig rows compare rig with rig and only chose what was solved hourly; the verdicts are the hourly ones.

## Hourly, norfolk_grid_green

| Variant | Anchor | Same technologies? | Largest size move | Cost | Carbon | |
|---|---|---|---|---|---|---|
| push=cost.fuel_cell.capex_per_kW*0.5 | min_cost | yes | ely +128.3% | -4.67 % | +0.29 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*0.5 | min_gwp | yes | batt_e -0.7% | -8.84 % | -0.00 % | holds |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_cost | yes | tank -71.7% | +4.53 % | -0.41 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_gwp | yes | batt_e +0.5% | +8.84 % | -0.00 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_cost | yes | ely -0.0% | -0.00 % | -8.51 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_gwp | yes | batt_e +1594.5% | -5.75 % | -1.16 % | **moves** |
| push=battery.energy_per_usable_kWh*1.5 | min_cost | yes | ely -0.0% | +0.00 % | +8.51 % | holds |
| push=battery.energy_per_usable_kWh*1.5 | min_gwp | yes | batt_e -93.3% | +1.28 % | +0.09 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_cost | yes | ely +1301.8% | -0.26 % | +0.21 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_gwp | yes | batt_p +0.4% | -3.09 % | +0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_cost | no: -ely, tank | solar -0.5% | +0.01 % | -0.10 % | **moves** |
| push=coefficient.cost_ely*1.5 | min_gwp | yes | batt_p +0.5% | +3.09 % | -0.00 % | holds |
| push=cost.bought_h2.green.delivered*0.5 | min_cost | no: -ely, tank | fc +13.2% | -6.92 % | +2.29 % | **moves** |
| push=cost.bought_h2.green.delivered*0.5 | min_gwp | yes | batt_e -0.8% | -10.22 % | -0.00 % | holds |
| push=cost.bought_h2.green.delivered*1.5 | min_cost | yes | tank +843.2% | +4.43 % | -0.47 % | **moves** |
| push=cost.bought_h2.green.delivered*1.5 | min_gwp | yes | batt_p +0.6% | +10.20 % | +0.00 % | holds |
| push=coefficient.gwp_tank*0.5 | min_cost | yes | ely -0.0% | +0.00 % | -0.05 % | holds |
| push=coefficient.gwp_tank*0.5 | min_gwp | yes | tank +126.8% | +0.55 % | -1.43 % | **moves** |
| push=coefficient.gwp_tank*1.5 | min_cost | yes | ely -0.0% | +0.00 % | +0.05 % | holds |
| push=coefficient.gwp_tank*1.5 | min_gwp | yes | tank -39.6% | +0.10 % | +0.83 % | **moves** |
| push=onshore_wind.parts_fraction*0.5 | min_cost | yes | ely -0.0% | +0.00 % | -1.40 % | holds |
| push=onshore_wind.parts_fraction*0.5 | min_gwp | yes | batt_e -28.6% | +1.22 % | -2.99 % | **moves** |
| push=onshore_wind.parts_fraction*1.5 | min_cost | yes | ely -0.0% | +0.00 % | +1.40 % | holds |
| push=onshore_wind.parts_fraction*1.5 | min_gwp | yes | batt_e +22.7% | -0.81 % | +2.84 % | **moves** |
| push=coefficient.gwp_fc_stack_per_mw*0.5 | min_cost | yes | ely -0.0% | +0.00 % | -0.48 % | holds |
| push=coefficient.gwp_fc_stack_per_mw*0.5 | min_gwp | yes | batt_e -42.7% | +0.47 % | -1.55 % | **moves** |
| push=coefficient.gwp_fc_stack_per_mw*1.5 | min_cost | yes | ely -0.0% | +0.00 % | +0.48 % | holds |
| push=coefficient.gwp_fc_stack_per_mw*1.5 | min_gwp | yes | grid +3983.4% | -2.80 % | +1.49 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*0.5 | min_cost | yes | fc -0.8% | -1.95 % | -2.02 % | holds |
| push=battery.capacity_fade_at_end_of_life*0.5 | min_gwp | yes | batt_e +33.6% | -0.41 % | -0.07 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*1.5 | min_cost | yes | ely +52.8% | +2.50 % | +2.52 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*1.5 | min_gwp | yes | batt_e -42.6% | +0.50 % | +0.05 % | **moves** |
| green_h2_grid_share=0.0 | min_cost | yes | tank -0.0% | +0.00 % | -0.32 % | holds |
| green_h2_grid_share=0.0 | min_gwp | yes | tank -12.8% | +0.57 % | -1.05 % | **moves** |
| green_h2_grid_share=1.0 | min_cost | yes | ely -0.0% | +0.00 % | +0.14 % | holds |
| green_h2_grid_share=1.0 | min_gwp | yes | batt_e +7.6% | -0.12 % | +0.42 % | **moves** |
| fc_stack_calendar_years=5.0 | min_cost | yes | ely -3.0% | +1.44 % | +0.90 % | holds |
| fc_stack_calendar_years=5.0 | min_gwp | yes | grid +3983.4% | -1.11 % | +2.75 % | **moves** |
| fc_stack_calendar_years=15.0 | min_cost | yes | ely +6.8% | -0.48 % | -0.32 % | **moves** |
| fc_stack_calendar_years=15.0 | min_gwp | yes | batt_e -31.8% | -0.59 % | -1.03 % | **moves** |
| fc_stack_duty_hours=20000.0 | min_cost | yes | ely -0.0% | +0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=20000.0 | min_gwp | yes | wind +0.0% | +0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_cost | yes | ely -0.0% | +0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_gwp | yes | wind +0.0% | +0.00 % | +0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_cost | yes | ely -0.6% | -0.00 % | -0.01 % | holds |
| tank_leakage_per_hour=0.0 | min_gwp | yes | batt_p -4.7% | +0.05 % | -0.11 % | holds |
| tank_leakage_per_hour=0.0001 | min_cost | yes | ely +0.2% | +0.00 % | +0.01 % | holds |
| tank_leakage_per_hour=0.0001 | min_gwp | yes | batt_e +21.7% | -0.27 % | +0.10 % | **moves** |
| batt_standing_loss_per_hour=0.0 | min_cost | yes | fc -0.2% | -0.05 % | -0.03 % | holds |
| batt_standing_loss_per_hour=0.0 | min_gwp | yes | batt_e +0.9% | -0.01 % | -0.00 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_cost | yes | ely +1.5% | +0.05 % | +0.03 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_gwp | yes | batt_e -0.5% | +0.00 % | +0.00 % | holds |
| batt_tx_x_eff=1.0 | min_cost | yes | tank +3.2% | +0.11 % | +0.10 % | holds |
| batt_tx_x_eff=1.0 | min_gwp | yes | batt_e -1.5% | +0.01 % | +0.00 % | holds |
| fc_tx_x_eff=0.5 | min_cost | yes | tank +1.9% | -0.09 % | -0.02 % | holds |
| fc_tx_x_eff=0.5 | min_gwp | yes | batt_p -2.2% | -0.18 % | -0.09 % | holds |

**These move the design and are reported with the result:** fc_stack_calendar_years=15.0, fc_stack_calendar_years=5.0, green_h2_grid_share=0.0, green_h2_grid_share=1.0, push=battery.capacity_fade_at_end_of_life*0.5, push=battery.capacity_fade_at_end_of_life*1.5, push=battery.energy_per_usable_kWh*0.5, push=battery.energy_per_usable_kWh*1.5, push=coefficient.cost_ely*0.5, push=coefficient.cost_ely*1.5, push=coefficient.gwp_fc_stack_per_mw*0.5, push=coefficient.gwp_fc_stack_per_mw*1.5, push=coefficient.gwp_tank*0.5, push=coefficient.gwp_tank*1.5, push=cost.bought_h2.green.delivered*0.5, push=cost.bought_h2.green.delivered*1.5, push=cost.fuel_cell.capex_per_kW*0.5, push=cost.fuel_cell.capex_per_kW*1.5, push=onshore_wind.parts_fraction*0.5, push=onshore_wind.parts_fraction*1.5, tank_leakage_per_hour=0.0001

## Rig (4-hour steps), islanded_h2

Flag at 3 % on the rig.

| Variant | Anchor | Same technologies? | Largest size move | Cost | Carbon | |
|---|---|---|---|---|---|---|
| push=cost.fuel_cell.capex_per_kW*0.5 | min_cost | yes | ely +66.4% | -3.45 % | -2.16 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*0.5 | min_gwp | yes | batt_p -0.6% | -7.62 % | -0.00 % | holds |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_cost | yes | fc -24.3% | +2.92 % | +3.96 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_gwp | yes | batt_p +0.0% | +7.62 % | -0.00 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_cost | yes | solar -0.2% | +0.00 % | -11.41 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_gwp | yes | batt_e +2988.6% | -4.23 % | -1.04 % | **moves** |
| push=battery.energy_per_usable_kWh*1.5 | min_cost | yes | batt_e -0.0% | +0.00 % | +11.39 % | holds |
| push=battery.energy_per_usable_kWh*1.5 | min_gwp | no: -batt_e, batt_p | fc +1.8% | +0.40 % | +0.00 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_cost | yes | ely +202.0% | -0.60 % | -3.41 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_gwp | yes | batt_p -1.0% | -5.43 % | +0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_cost | yes | batt_e -0.0% | +0.46 % | -0.00 % | holds |
| push=coefficient.cost_ely*1.5 | min_gwp | yes | batt_p -2.3% | +5.43 % | -0.00 % | holds |
| push=coefficient.gwp_tank*0.5 | min_cost | yes | batt_p -0.0% | +0.00 % | -3.64 % | holds |
| push=coefficient.gwp_tank*0.5 | min_gwp | yes | batt_p +248.2% | -2.23 % | -6.73 % | **moves** |
| push=coefficient.gwp_tank*1.5 | min_cost | yes | batt_e -0.0% | +0.00 % | +3.64 % | holds |
| push=coefficient.gwp_tank*1.5 | min_gwp | yes | batt_p -97.0% | +1.46 % | +5.45 % | **moves** |
| push=onshore_wind.parts_fraction*0.5 | min_cost | yes | batt_e -0.0% | +0.00 % | -2.46 % | holds |
| push=onshore_wind.parts_fraction*0.5 | min_gwp | yes | batt_p -99.7% | +1.57 % | -3.79 % | **moves** |
| push=onshore_wind.parts_fraction*1.5 | min_cost | yes | batt_e -0.0% | +0.00 % | +2.46 % | holds |
| push=onshore_wind.parts_fraction*1.5 | min_gwp | yes | batt_e +220.8% | -2.98 % | +3.55 % | **moves** |
| push=coefficient.gwp_fc_stack_per_mw*0.5 | min_cost | yes | batt_e -0.0% | +0.00 % | -0.42 % | holds |
| push=coefficient.gwp_fc_stack_per_mw*0.5 | min_gwp | no: -batt_e, batt_p | fc +1.8% | +0.40 % | -1.38 % | **moves** |
| push=coefficient.gwp_fc_stack_per_mw*1.5 | min_cost | yes | batt_p +0.0% | +0.00 % | +0.42 % | holds |
| push=coefficient.gwp_fc_stack_per_mw*1.5 | min_gwp | yes | batt_e +229.2% | -0.93 % | +1.31 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*0.5 | min_cost | yes | batt_e +12.3% | -2.29 % | -1.84 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*0.5 | min_gwp | yes | batt_e +229.2% | -0.97 % | -0.07 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*1.5 | min_cost | yes | ely +13.6% | +2.65 % | +2.53 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*1.5 | min_gwp | no: -batt_e, batt_p | fc +1.8% | +0.40 % | +0.00 % | **moves** |
| fc_stack_calendar_years=5.0 | min_cost | yes | fc -7.1% | +1.01 % | +1.90 % | **moves** |
| fc_stack_calendar_years=5.0 | min_gwp | yes | batt_e +229.2% | +1.36 % | +2.62 % | **moves** |
| fc_stack_calendar_years=15.0 | min_cost | yes | ely +1.3% | -0.34 % | -0.37 % | holds |
| fc_stack_calendar_years=15.0 | min_gwp | no: -batt_e, batt_p | fc +1.8% | -0.41 % | -0.92 % | **moves** |
| fc_stack_duty_hours=20000.0 | min_cost | yes | batt_e +0.0% | +0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=20000.0 | min_gwp | yes | batt_p -0.1% | -0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_cost | yes | batt_p -0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_gwp | yes | batt_e +0.0% | -0.00 % | +0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_cost | yes | fc +2.5% | -0.12 % | -1.16 % | holds |
| tank_leakage_per_hour=0.0 | min_gwp | yes | batt_e +203.6% | -0.71 % | -0.49 % | **moves** |
| tank_leakage_per_hour=0.0001 | min_cost | yes | batt_p +3.0% | +0.12 % | +1.18 % | holds |
| tank_leakage_per_hour=0.0001 | min_gwp | yes | batt_p -16.3% | +1.63 % | +0.47 % | **moves** |
| batt_standing_loss_per_hour=0.0 | min_cost | yes | tank -0.2% | -0.08 % | -0.06 % | holds |
| batt_standing_loss_per_hour=0.0 | min_gwp | yes | batt_p +50.4% | -0.22 % | -0.00 % | **moves** |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_cost | yes | fc +0.3% | +0.07 % | +0.04 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_gwp | yes | batt_p -22.1% | +0.09 % | +0.00 % | **moves** |
| batt_tx_x_eff=1.0 | min_cost | yes | batt_p +0.3% | +0.10 % | +0.09 % | holds |
| batt_tx_x_eff=1.0 | min_gwp | yes | batt_p -39.4% | +0.17 % | +0.00 % | **moves** |
| fc_tx_x_eff=0.5 | min_cost | yes | tank -0.4% | -0.07 % | -0.05 % | holds |
| fc_tx_x_eff=0.5 | min_gwp | yes | batt_p -37.9% | +0.00 % | -0.09 % | **moves** |

## Rig (4-hour steps), norfolk_grid_green

Flag at 3 % on the rig.

| Variant | Anchor | Same technologies? | Largest size move | Cost | Carbon | |
|---|---|---|---|---|---|---|
| push=cost.fuel_cell.capex_per_kW*0.5 | min_cost | yes | ely +71.7% | -4.76 % | +0.07 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*0.5 | min_gwp | yes | batt_p -1.0% | -8.98 % | +0.00 % | holds |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_cost | yes | ely -31.1% | +4.60 % | -0.26 % | **moves** |
| push=cost.fuel_cell.capex_per_kW*1.5 | min_gwp | yes | batt_e +5.3% | +8.96 % | +0.00 % | **moves** |
| push=battery.energy_per_usable_kWh*0.5 | min_cost | yes | tank -0.0% | -0.00 % | -8.11 % | holds |
| push=battery.energy_per_usable_kWh*0.5 | min_gwp | yes | batt_e +1698.8% | -5.09 % | -0.90 % | **moves** |
| push=battery.energy_per_usable_kWh*1.5 | min_cost | yes | tank -0.0% | -0.00 % | +8.11 % | holds |
| push=battery.energy_per_usable_kWh*1.5 | min_gwp | no: -batt_e, batt_p | ely +4.0% | +1.00 % | +0.01 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_cost | yes | ely +1819.1% | -0.28 % | +0.19 % | **moves** |
| push=coefficient.cost_ely*0.5 | min_gwp | yes | batt_e +5.3% | -2.77 % | +0.00 % | **moves** |
| push=coefficient.cost_ely*1.5 | min_cost | no: -ely, tank | wind +1.0% | +0.01 % | -0.19 % | **moves** |
| push=coefficient.cost_ely*1.5 | min_gwp | yes | batt_p +0.2% | +2.75 % | +0.00 % | holds |
| push=cost.bought_h2.green.delivered*0.5 | min_cost | no: -ely, tank | solar -13.4% | -6.86 % | +2.20 % | **moves** |
| push=cost.bought_h2.green.delivered*0.5 | min_gwp | yes | tank -1.6% | -10.35 % | -0.00 % | holds |
| push=cost.bought_h2.green.delivered*1.5 | min_cost | yes | tank +1445.0% | +4.37 % | -0.11 % | **moves** |
| push=cost.bought_h2.green.delivered*1.5 | min_gwp | yes | batt_e +5.7% | +10.28 % | +0.00 % | **moves** |
| push=coefficient.gwp_tank*0.5 | min_cost | yes | tank -0.0% | +0.00 % | -0.04 % | holds |
| push=coefficient.gwp_tank*0.5 | min_gwp | no: -batt_e, batt_p | tank +128.0% | +1.22 % | -1.39 % | **moves** |
| push=coefficient.gwp_tank*1.5 | min_cost | yes | tank -0.0% | +0.00 % | +0.04 % | holds |
| push=coefficient.gwp_tank*1.5 | min_gwp | yes | batt_e +43.7% | -0.12 % | +0.77 % | **moves** |
| push=onshore_wind.parts_fraction*0.5 | min_cost | yes | tank -0.0% | +0.00 % | -1.37 % | holds |
| push=onshore_wind.parts_fraction*0.5 | min_gwp | yes | batt_p -87.4% | +1.94 % | -3.02 % | **moves** |
| push=onshore_wind.parts_fraction*1.5 | min_cost | yes | tank -0.0% | +0.00 % | +1.37 % | holds |
| push=onshore_wind.parts_fraction*1.5 | min_gwp | yes | batt_e +38.8% | -0.98 % | +2.88 % | **moves** |
| push=coefficient.gwp_fc_stack_per_mw*0.5 | min_cost | yes | tank -0.0% | -0.00 % | -0.48 % | holds |
| push=coefficient.gwp_fc_stack_per_mw*0.5 | min_gwp | no: -batt_e, batt_p | ely +4.1% | +0.99 % | -1.59 % | **moves** |
| push=coefficient.gwp_fc_stack_per_mw*1.5 | min_cost | yes | tank -0.0% | -0.00 % | +0.48 % | holds |
| push=coefficient.gwp_fc_stack_per_mw*1.5 | min_gwp | yes | grid +3983.4% | -2.32 % | +1.43 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*0.5 | min_cost | yes | tank -5.3% | -1.87 % | -1.97 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*0.5 | min_gwp | yes | batt_e +41.6% | -0.52 % | -0.06 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*1.5 | min_cost | yes | ely +27.5% | +2.39 % | +2.38 % | **moves** |
| push=battery.capacity_fade_at_end_of_life*1.5 | min_gwp | no: -batt_e, batt_p | ely +4.0% | +1.00 % | +0.01 % | **moves** |
| green_h2_grid_share=0.0 | min_cost | yes | tank -0.0% | -0.00 % | -0.32 % | holds |
| green_h2_grid_share=0.0 | min_gwp | yes | batt_e +10.2% | +0.50 % | -1.03 % | **moves** |
| green_h2_grid_share=1.0 | min_cost | yes | tank -0.0% | -0.00 % | +0.14 % | holds |
| green_h2_grid_share=1.0 | min_gwp | yes | batt_e +5.1% | -0.15 % | +0.42 % | **moves** |
| fc_stack_calendar_years=5.0 | min_cost | yes | tank -13.7% | +1.46 % | +0.83 % | **moves** |
| fc_stack_calendar_years=5.0 | min_gwp | yes | grid +3983.4% | -0.82 % | +2.71 % | **moves** |
| fc_stack_calendar_years=15.0 | min_cost | yes | ely +2.1% | -0.49 % | -0.33 % | holds |
| fc_stack_calendar_years=15.0 | min_gwp | no: -batt_e, batt_p | ely +4.2% | +0.03 % | -1.05 % | **moves** |
| fc_stack_duty_hours=20000.0 | min_cost | yes | tank -0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=20000.0 | min_gwp | yes | batt_e +0.0% | -0.00 % | +0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_cost | yes | tank -0.0% | +0.00 % | -0.00 % | holds |
| fc_stack_duty_hours=40000.0 | min_gwp | yes | batt_p -0.0% | +0.00 % | +0.00 % | holds |
| tank_leakage_per_hour=0.0 | min_cost | yes | ely -0.6% | -0.00 % | -0.01 % | holds |
| tank_leakage_per_hour=0.0 | min_gwp | yes | batt_p -8.2% | -0.12 % | -0.10 % | **moves** |
| tank_leakage_per_hour=0.0001 | min_cost | yes | ely +0.6% | +0.00 % | +0.01 % | holds |
| tank_leakage_per_hour=0.0001 | min_gwp | yes | batt_e +14.1% | -0.17 % | +0.09 % | **moves** |
| batt_standing_loss_per_hour=0.0 | min_cost | yes | tank -0.9% | -0.05 % | -0.01 % | holds |
| batt_standing_loss_per_hour=0.0 | min_gwp | yes | batt_e +6.1% | -0.01 % | -0.00 % | **moves** |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_cost | yes | ely +1.2% | +0.05 % | +0.01 % | holds |
| batt_standing_loss_per_hour=0.0002860814760438586 | min_gwp | yes | batt_p -1.1% | +0.01 % | +0.00 % | holds |
| batt_tx_x_eff=1.0 | min_cost | yes | tank -2.1% | +0.10 % | +0.08 % | holds |
| batt_tx_x_eff=1.0 | min_gwp | yes | batt_p -8.5% | +0.08 % | +0.00 % | **moves** |
| fc_tx_x_eff=0.5 | min_cost | yes | fc -0.4% | -0.09 % | -0.03 % | holds |
| fc_tx_x_eff=0.5 | min_gwp | yes | batt_p -4.3% | -0.17 % | -0.09 % | **moves** |
