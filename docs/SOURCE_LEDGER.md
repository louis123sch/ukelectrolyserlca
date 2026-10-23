# Source ledger — every inventory row and where it came from

Generated 2026-10-23 10:44 by `scripts/source_ledger.py` from the modules in `optimiser_lca/`. Regenerate after any inventory edit; do not edit by hand.

| Rows | Of the activity's own table | Own locator | ADDED | ASSUMED | DERIVED | TRANSCRIBED | Unaccounted |
|---|---|---|---|---|---|---|---|
| 870 | 584 | 263 | 5 | 15 | 3 | 0 | 0 |

A row *of the activity's own table* is located by the source its activity's comment names; a row with its *own locator* starts with another source, table or figure; a graded row is the module's own addition or derivation and says so. **Unaccounted** rows have an empty note and must be zero.

## upv — utility-scale PV (Smith 2024 on apos)

Database `solar foreground`; source of the activities' own tables: Smith 2024 Appendix A (table named in the activity) / IEA PVPS Z-PV-239.

### `upv_silica_sand` — UPV, silica sand

tonne, GB; production amount 92500. Comment: Smith 2024 Table A1, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `building_hall` | building construction, hall | 48.4 | square meter | 48.4 | building, hall | activity's table |
| `conveyor_belt` | market for conveyor belt | 9.15 | meter | 9.15 | conveyor belt | activity's table |
| `diesel` | diesel production, petroleum refinery operation | 31600 | kilogram | 31600 | diesel | activity's table |
| `electricity_mv_cn` | market group for electricity, medium voltage | 262000 | kilowatt hour | 262000 | electricity, medium voltage | activity's table |
| `quarry_infrastructure` | gravel/sand quarry construction | 0.00457 | unit | 0.00457 | gravel/sand quarry infrastructure | activity's table |
| `heat_hfo` | heat production, heavy fuel oil, at industrial furnace 1MW | 1.85e+07 | megajoule | 1.85e+07 | heat, district or industrial, other than natural gas | activity's table |
| `heavy_fuel_oil` | heavy fuel oil production, petroleum refinery operation | 5250 | kilogram | 5250 | heavy fuel oil | activity's table |
| `industrial_machine` | industrial machine production, heavy, unspecified | 1080 | kilogram | 1080 | industrial machine, heavy, unspecified | activity's table |
| `lime_packed` | lime production, milled, packed | 2720 | kilogram | 2720 | lime, packed | activity's table |
| `lubricating_oil_production` | lubricating oil production | 118 | kilogram | 118 | lubricating oil | activity's table |
| `steel_unalloyed_converter` | steel production, converter, unalloyed | 1250 | kilogram | 1250 | steel, unalloyed | activity's table |
| `synthetic_rubber` | synthetic rubber production | 192 | kilogram | 192 | synthetic rubber | activity's table |
| `light_commercial_vehicle` | transport, freight, light commercial vehicle | 1490 | ton kilometer | 1490 | transport, freight, light commercial vehicle | activity's table |
| `lorry` | market group for transport, freight, lorry, unspecified | 10100 | ton kilometer | 10100 | transport, freight, lorry, unspecified | activity's table |
| `sand_quartz_resource` | Sand, unspecified | 1e+08 | kilogram | 1e+08 | sand, quartz (printed 1.00E+05 t) - in since 22 Oct 2026 | activity's table |
| `water_natural` | Water, unspecified natural origin | 133000 | cubic meter | 133000 | Water, process and cooling, unspecified natural origin - in since 22 Oct | activity's table |
| `water_natural` | Water, unspecified natural origin | 971000 | cubic meter | 971000 | Water, process, unspecified natural origin - in since 22 Oct 2026 | activity's table |

### `upv_silicon_metal` — UPV, silicon, metallurgical grade

kilogram, GB. Comment: Smith 2024 Table A2, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_silica_sand` | → UPV, silica sand | 0.0027 | tonne | 0.0027 | silica sand - 2.7 kg as printed | activity's table |
| `charcoal` | market for charcoal | 0.17 | kilogram | 0.17 | charcoal | activity's table |
| `coke` | market for coke | 23.1 | megajoule | 23.1 | coke | activity's table |
| `eaf_converter` | market for electric arc furnace converter | 1e-11 | unit | 1e-11 | electric arc furnace converter | activity's table |
| `electricity_mv_cn` | market group for electricity, medium voltage | 13 | kilowatt hour | 13 | electricity, medium voltage | activity's table |
| `graphite` | market for graphite | 0.1 | kilogram | 0.1 | graphite | activity's table |
| `oxygen_liquid` | market for oxygen, liquid | 0.02 | kilogram | 0.02 | oxygen, liquid | activity's table |
| `petroleum_coke` | market for petroleum coke | 0.5 | kilogram | 0.5 | petroleum coke | activity's table |
| `freight_train_us` | market for transport, freight train | 0.069 | ton kilometer | 0.069 | transport, freight train | activity's table |
| `lorry` | market group for transport, freight, lorry, unspecified | 0.156 | ton kilometer | 0.156 | transport, freight, lorry, unspecified | activity's table |
| `wood_chips` | market for wood chips, wet, measured as dry mass | 0.00325 | kilogram | 0.00325 | wood chips, wet, measured as dry mass | activity's table |
| `slag_mg_silicon` | market for slag from metallurgical grade silicon production | -0.025 | kilogram | -0.025 | slag from metallurgical grade silicon production | activity's table |
| `antimony` | Antimony | 7.85e-09 | kilogram | 7.85e-09 | antimony | activity's table |
| `arsenic` | Arsenic | 9.42e-09 | kilogram | 9.42e-09 | arsenic | activity's table |
| `boron` | Boron | 2.79e-07 | kilogram | 2.79e-07 | boron | activity's table |
| `cadmium` | Cadmium | 3.14e-10 | kilogram | 3.14e-10 | cadmium | activity's table |
| `calcium` | Calcium | 7.75e-07 | kilogram | 7.75e-07 | calcium | activity's table |
| `co2_biogenic` | Carbon dioxide, non-fossil | 1.61 | kilogram | 1.61 | carbon dioxide, biogenic | activity's table |
| `co2_fossil` | Carbon dioxide, fossil | 3.58 | kilogram | 3.58 | carbon dioxide, fossil | activity's table |
| `co_fossil` | Carbon monoxide, fossil | 0.00138 | kilogram | 0.00138 | carbon monoxide, fossil | activity's table |
| `chlorine` | Chlorine | 7.85e-08 | kilogram | 7.85e-08 | chlorine | activity's table |
| `chromium_iii` | Chromium III | 7.85e-09 | kilogram | 7.85e-09 | chromium III | activity's table |
| `cyanide` | Cyanide | 6.87e-06 | kilogram | 6.87e-06 | cyanide | activity's table |
| `fluorine` | Fluorine | 3.88e-08 | kilogram | 3.88e-08 | fluorine | activity's table |
| `heat_waste` | Heat, waste | 71.3 | megajoule | 71.3 | heat, waste | activity's table |
| `hf` | Hydrogen fluoride | 0.0005 | kilogram | 0.0005 | hydrogen fluoride | activity's table |
| `h2s` | Hydrogen sulfide | 0.0005 | kilogram | 0.0005 | hydrogen sulfide | activity's table |
| `iron` | Iron | 3.88e-06 | kilogram | 3.88e-06 | iron | activity's table |
| `lead_resource` | Lead | 3.44e-07 | kilogram | 3.44e-07 | lead | activity's table |
| `mercury` | Mercury | 7.85e-09 | kilogram | 7.85e-09 | mercury | activity's table |
| `nox` | Nitrogen oxides | 0.00974 | kilogram | 0.00974 | nitrogen oxides | activity's table |
| `pm10` | Particulate Matter, > 10 um | 0.00775 | kilogram | 0.00775 | particulates, >10 μm | activity's table |
| `potassium` | Potassium | 6.2e-05 | kilogram | 6.2e-05 | potassium | activity's table |
| `silicon` | Silicon | 0.00751 | kilogram | 0.00751 | silicon | activity's table |
| `sodium_soil` | Sodium | 7.75e-07 | kilogram | 7.75e-07 | sodium | activity's table |
| `so2` | Sulfur dioxide | 0.0122 | kilogram | 0.0122 | sulfur dioxide | activity's table |
| `tin_resource` | Tin | 7.85e-09 | kilogram | 7.85e-09 | tin | activity's table |
| `co_soil_biomass` | Carbon monoxide, from soil or biomass stock | 0.00062 | kilogram | 0.00062 | carbon monoxide, land transformation - v2 name; in since 22 Oct 2026 | activity's table |
| `nmvoc` | NMVOC, non-methane volatile organic compounds | 9.6e-05 | kilogram | 9.6e-05 | NMVOC, unspecified origin - v2 name; in since 22 Oct 2026 | activity's table |

### `upv_polysilicon` — UPV, silicon, solar grade

kilogram, GB. Comment: Smith 2024 Table A3, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_silicon_metal` | → UPV, silicon, metallurgical grade | 1.26 | kilogram | 1.26 | silicon, metallurgical grade | activity's table |
| `chlorine_gas` | market for chlorine, gaseous | 0.215 | kilogram | 0.215 | chlorine, gaseous | activity's table |
| `electricity_hv_cn` | market group for electricity, high voltage | 72 | kilowatt hour | 72 | electricity, high voltage | activity's table |
| `graphite` | market for graphite | 0.0054 | kilogram | 0.0054 | graphite | activity's table |
| `heat_gas` | heat production, natural gas, at industrial furnace >100kW | 70 | megajoule | 70 | heat, district or industrial, natural gas | activity's table |
| `hydrogen_liquid` | market for hydrogen, liquid | 0.0536 | kilogram | 0.0536 | hydrogen, liquid | activity's table |
| `nitrogen_liquid` | market for nitrogen, liquid | 12.9 | kilogram | 12.9 | nitrogen, liquid | activity's table |
| `quicklime_packed` | market for quicklime, milled, packed | 0.58 | kilogram | 0.58 | quicklime, milled, packed | activity's table |
| `silicone_factory` | market for silicone factory | 1e-11 | unit | 1e-11 | silicone factory | activity's table |
| `naoh_50pct` | market for sodium hydroxide, without water, in 50% solution state | 0.35 | kilogram | 0.35 | sodium hydroxide, without water, in 50% solution state | activity's table |
| `freight_train_us` | market for transport, freight train | 3.65 | ton kilometer | 3.65 | transport, freight train | activity's table |
| `lorry` | market group for transport, freight, lorry, unspecified | 2.87 | ton kilometer | 2.87 | transport, freight, lorry, unspecified | activity's table |
| `bod5` | BOD5, Biological Oxygen Demand | 0.000205 | kilogram | 0.000205 | BOD5, biological oxygen demand | activity's table |
| `chloride` | Chloride | 0.036 | kilogram | 0.036 | chloride | activity's table |
| `cod` | COD, Chemical Oxygen Demand | 0.00202 | kilogram | 0.00202 | COD, chemical oxygen demand | activity's table |
| `doc` | DOC, Dissolved Organic Carbon | 0.00091 | kilogram | 0.00091 | DOC, dissolved organic carbon | activity's table |
| `heat_waste` | Heat, waste | 396 | megajoule | 396 | heat, waste | activity's table |
| `nitrogen` | Nitrogen | 0.000208 | kilogram | 0.000208 | nitrogen | activity's table |
| `phosphate` | Phosphate | 2.8e-06 | kilogram | 2.8e-06 | phosphate | activity's table |
| `toc` | TOC, Total Organic Carbon | 0.00091 | kilogram | 0.00091 | TOC, total organic carbon | activity's table |
| `aox_water` | AOX, Adsorbable Organic Halogen | 1.26e-05 | kilogram | 1.26e-05 | AOX, adsorbable organic halogen as Cl - v2 name; in since 22 Oct 2026 | activity's table |
| `copper_ion_water` | Copper ion | 1.02e-07 | kilogram | 1.02e-07 | copper, ion - v2 name; in since 22 Oct 2026 | activity's table |
| `iron_ion_water` | Iron ion | 5.61e-06 | kilogram | 5.61e-06 | iron, ion - v2 name; in since 22 Oct 2026 | activity's table |
| `sodium_ion_water` | Sodium I | 0.0338 | kilogram | 0.0338 | sodium, ion - v2 name; in since 22 Oct 2026 | activity's table |
| `zinc_ion_water` | Zinc II | 1.96e-06 | kilogram | 1.96e-06 | zinc, ion - v2 name; in since 22 Oct 2026 | activity's table |

### `upv_cz_ingot` — UPV, silicon, single crystal, Czochralski

kilogram, GB. Comment: Smith 2024 Table A4, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_polysilicon` | → UPV, silicon, solar grade | 1.03 | kilogram | 1.03 | silicon, solar grade | activity's table |
| `acetone` | market for acetone, liquid | 0.049 | kilogram | 0.049 | acetone, liquid | activity's table |
| `argon_liquid` | market for argon, liquid | 0.046 | kilogram | 0.046 | argon, liquid | activity's table |
| `ceramic_tile` | market for ceramic tile | 0.062 | kilogram | 0.062 | ceramic tile | activity's table |
| `electricity_mv_cn` | market group for electricity, medium voltage | 38.4 | kilowatt hour | 38.4 | electricity, medium voltage | activity's table |
| `hcl_30pct_production` | hydrochloric acid production, from the reaction of hydrogen with chlorine | 0.000438 | kilogram | 0.000438 | hydrochloric acid, without water, in 30% solution state | activity's table |
| `hydrogen_fluoride` | market for hydrogen fluoride | 0.00351 | kilogram | 0.00351 | hydrogen fluoride | activity's table |
| `lime_hydrated` | market for lime, hydrated, packed | 0.022 | kilogram | 0.022 | lime, hydrated, packed | activity's table |
| `nitric_acid_50pct` | market for nitric acid, without water, in 50% solution state | 0.00778 | kilogram | 0.00778 | nitric acid, without water, in 50% solution state | activity's table |
| `silicone_factory` | market for silicone factory | 5e-12 | unit | 5e-12 | silicone factory | activity's table |
| `naoh_50pct` | market for sodium hydroxide, without water, in 50% solution state | 0.00478 | kilogram | 0.00478 | sodium hydroxide, without water, in 50% solution state | activity's table |
| `freight_train_us` | market for transport, freight train | 1.41 | ton kilometer | 1.41 | transport, freight train | activity's table |
| `lorry` | market group for transport, freight, lorry, unspecified | 1.13 | ton kilometer | 1.13 | transport, freight, lorry, unspecified | activity's table |
| `water_softened_us` | market for water, completely softened | 0.0684 | kilogram | 0.0684 | water, completely softened | activity's table |
| `waste_wafer_inorganic` | market for waste, from silicon wafer production, inorganic | -0.1 | kilogram | -0.1 | waste, from silicon wafer production, inorganic | activity's table |
| `bod5` | BOD5, Biological Oxygen Demand | 0.13 | kilogram | 0.13 | BOD5, biological oxygen demand | activity's table |
| `cod` | COD, Chemical Oxygen Demand | 0.13 | kilogram | 0.13 | COD, chemical oxygen demand | activity's table |
| `doc` | DOC, Dissolved Organic Carbon | 0.0405 | kilogram | 0.0405 | DOC, dissolved organic carbon | activity's table |
| `fluoride` | Fluoride | 0.00237 | kilogram | 0.00237 | fluoride | activity's table |
| `heat_waste` | Heat, waste | 115 | megajoule | 115 | heat, waste | activity's table |
| `hydrocarbons` | Hydrocarbons, unspecified | 0.0228 | kilogram | 0.0228 | hydrocarbons, unspecified | activity's table |
| `hydroxide` | Hydroxide | 0.00742 | kilogram | 0.00742 | hydroxide | activity's table |
| `nitrogen` | Nitrogen | 0.0091 | kilogram | 0.0091 | nitrogen | activity's table |
| `toc` | TOC, Total Organic Carbon | 0.0405 | kilogram | 0.0405 | TOC, total organic carbon | activity's table |
| `water` | Water | 0.3 | cubic meter | 0.3 | water | activity's table |
| `water` | Water | 2.2 | cubic meter | 2.2 | water | activity's table |
| `water_cooling_natural` | Water, cooling, unspecified natural origin | 2.33 | cubic meter | 2.33 | Water, cooling, unspecified natural origin - v2 name; in since 22 Oct 2026 | activity's table |

### `upv_wafer` — UPV, single-Si wafer, photovoltaic

square meter, GB. Comment: Smith 2024 Table A5, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_cz_ingot` | → UPV, silicon, single crystal, Czochralski | 0.595 | kilogram | 0.595 | silicon, single crystal, Czochralski process, photovoltaics | activity's table |
| `acrylic_binder_54pct` | market for acrylic binder, with water, in 54% solution state | 0.002 | kilogram | 0.002 | acrylic binder, with water, in 54% solution state | activity's table |
| `alkylbenzene_sulfonate` | market for alkylbenzene sulfonate, linear, petrochemical | 0.034 | kilogram | 0.034 | alkylbenzene sulfonate, linear, petrochemical | activity's table |
| `brass` | market for brass | 0.00745 | kilogram | 0.00745 | brass | activity's table |
| `citric_acid` | market for citric acid | 0.187 | kilogram | 0.187 | citric acid | activity's table |
| `electricity_mv_cn` | market group for electricity, medium voltage | 2.35 | kilowatt hour | 2.35 | electricity, medium voltage | activity's table |
| `glass_wool_mat` | market for glass wool mat | 0.0106 | kilogram | 0.0106 | glass wool mat | activity's table |
| `heat_gas` | heat production, natural gas, at industrial furnace >100kW | 1.8 | megajoule | 1.8 | heat, district or industrial, natural gas | activity's table |
| `h2o2_50pct` | hydrogen peroxide production, product in 50% solution state | 0.0253 | kilogram | 0.0253 | hydrogen peroxide, without water, in 50% solution state | activity's table |
| `koh` | market for potassium hydroxide | 0.00381 | kilogram | 0.00381 | potassium hydroxide | activity's table |
| `naoh_50pct` | market for sodium hydroxide, without water, in 50% solution state | 0.015 | kilogram | 0.015 | sodium hydroxide, without water, in 50% solution state | activity's table |
| `steel_low_alloyed_hr` | market for steel, low-alloyed, hot rolled | 0.000896 | kilogram | 0.000896 | steel, low-alloyed, hot rolled | activity's table |
| `wafer_factory` | market for wafer factory | 2e-06 | unit | 2e-06 | wafer factory | activity's table |
| `water_softened_us` | market for water, completely softened | 21.7 | kilogram | 21.7 | water, completely softened | activity's table |
| `wire_drawing_steel` | market for wire drawing, steel | 0.000896 | kilogram | 0.000896 | wire drawing, steel | activity's table |
| `waste_wafer` | market for waste, from silicon wafer production | -0.02 | kilogram | -0.02 | waste, from silicon wafer production | activity's table |
| `bod5` | BOD5, Biological Oxygen Demand | 0.0296 | kilogram | 0.0296 | BOD5, biological oxygen demand | activity's table |
| `cod` | COD, Chemical Oxygen Demand | 0.0296 | kilogram | 0.0296 | COD, chemical oxygen demand | activity's table |
| `doc` | DOC, Dissolved Organic Carbon | 0.0111 | kilogram | 0.0111 | DOC, dissolved organic carbon | activity's table |
| `heat_waste` | Heat, waste | 8 | megajoule | 8 | heat, waste | activity's table |
| `nitrogen` | Nitrogen | 0.00994 | kilogram | 0.00994 | nitrogen | activity's table |
| `toc` | TOC, Total Organic Carbon | 0.0111 | kilogram | 0.0111 | TOC, total organic carbon | activity's table |
| `water` | Water | 0.00975 | cubic meter | 0.00975 | water | activity's table |
| `water` | Water | 0.0553 | cubic meter | 0.0553 | water | activity's table |
| `aox_water` | AOX, Adsorbable Organic Halogen | 0.000501 | kilogram | 0.000501 | AOX, adsorbable organic halogen as Cl - v2 name; in since 22 Oct 2026 | activity's table |
| `copper_ion_water` | Copper ion | 6.05e-05 | kilogram | 6.05e-05 | copper, ion - v2 name; in since 22 Oct 2026 | activity's table |

### `upv_trimethylaluminum` — UPV, trimethylaluminum, purified

kilogram, GB; production amount 18. Comment: Smith 2024 Table A6, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `aluminium_chloride` | aluminium chloride production | 1.34 | kilogram | 1.34 | aluminium chloride | activity's table |
| `aluminium_wrought` | market for aluminium, wrought alloy | 21.6 | kilogram | 21.6 | aluminium, wrought alloy | activity's table |
| `electricity_mv_cn` | market group for electricity, medium voltage | 5.57 | kilowatt hour | 5.57 | electricity, medium voltage | activity's table |
| `helium` | market for helium | 0.12 | kilogram | 0.12 | helium | activity's table |
| `methylchloride` | market for methylchloride | 60.9 | kilogram | 60.9 | methylchloride | activity's table |
| `nitrogen_liquid` | market for nitrogen, liquid | 0.825 | kilogram | 0.825 | nitrogen, liquid | activity's table |
| `paraffin` | market for paraffin | 0.153 | kilogram | 0.153 | paraffin | activity's table |
| `sodium` | market for sodium | 33 | kilogram | 33 | sodium | activity's table |
| `fly_ash_incineration` | treatment of fly ash and scrubber sludge, hazardous waste incineration | -3.8 | kilogram | -3.8 | fly ash and scrubber sludge | activity's table |
| `hazardous_waste_incineration` | treatment of hazardous waste, hazardous waste incineration | -107 | kilogram | -107 | hazardous waste, for incineration | activity's table |

### `upv_perc_cell` — UPV, photovoltaic cell, single-Si wafer

square meter, GB. Comment: Smith 2024 Table A7, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_wafer` | → UPV, single-Si wafer, photovoltaic | 1.02 | square meter | 1.02 | single-Si wafer, photovoltaic | activity's table |
| `FG:upv_trimethylaluminum` | → UPV, trimethylaluminum, purified | 0.000288 | kilogram | 0.000288 | trimethylaluminum | activity's table |
| `ammonia` | market for ammonia, anhydrous, liquid | 0.0165 | kilogram | 0.0165 | ammonia, anhydrous, liquid | activity's table |
| `calcium_chloride` | market for calcium chloride | 0.0207 | kilogram | 0.0207 | calcium chloride | activity's table |
| `electricity_mv_th` | market for electricity, medium voltage | 6.03 | kilowatt hour | 6.03 | electricity, medium voltage | activity's table |
| `heat_gas` | heat production, natural gas, at industrial furnace >100kW | 3.55 | megajoule | 3.55 | heat, district or industrial, natural gas | activity's table |
| `hcl_30pct` | market for hydrochloric acid, without water, in 30% solution state | 0.0681 | kilogram | 0.0681 | hydrochloric acid, without water, in 30% solution state | activity's table |
| `hydrogen_fluoride` | market for hydrogen fluoride | 0.0747 | kilogram | 0.0747 | hydrogen fluoride | activity's table |
| `paste_back` | market for metallization paste, back side | 0.00102 | kilogram | 0.00102 | metallization paste, back side | activity's table |
| `paste_back_aluminium` | market for metallization paste, back side, aluminium | 0.00901 | kilogram | 0.00901 | metallization paste, back side, aluminium | activity's table |
| `paste_front` | market for metallization paste, front side | 0.00348 | kilogram | 0.00348 | metallization paste, front side | activity's table |
| `nitric_acid_50pct` | market for nitric acid, without water, in 50% solution state | 0.0822 | kilogram | 0.0822 | nitric acid, without water, in 50% solution state | activity's table |
| `nitrogen_liquid` | market for nitrogen, liquid | 2.62 | kilogram | 2.62 | nitrogen, liquid | activity's table |
| `nitrous_oxide` | market for nitrous oxide | 0.00766 | kilogram | 0.00766 | nitrous oxide | activity's table |
| `oxygen_liquid` | market for oxygen, liquid | 0.334 | kilogram | 0.334 | oxygen, liquid | activity's table |
| `phosphorus_oxychloride` | market for phosphorus oxychloride | 0.000182 | kilogram | 0.000182 | phosphorus oxychloride | activity's table |
| `cell_factory` | market for photovoltaic cell factory | 4e-07 | unit | 4e-07 | photovoltaic cell factory | activity's table |
| `koh` | market for potassium hydroxide | 0.151 | kilogram | 0.151 | potassium hydroxide | activity's table |
| `propane` | market for propane | 0.0414 | kilogram | 0.0414 | propane | activity's table |
| `silane` | market for silicon tetrahydride | 0.00283 | kilogram | 0.00283 | silicon tetrahydride | activity's table |
| `solvent_organic` | market for solvent, organic | 0.0123 | kilogram | 0.0123 | solvent, organic | activity's table |
| `sulfuric_acid` | sulfuric acid production | 0.0206 | kilogram | 0.0206 | sulfuric acid | activity's table |
| `freight_train_row` | market for transport, freight train | 1.52 | ton kilometer | 1.52 | transport, freight train | activity's table |
| `lorry` | market group for transport, freight, lorry, unspecified | 0.274 | ton kilometer | 0.274 | transport, freight, lorry, unspecified | activity's table |
| `container_ship` | transport, freight, sea, container ship | 1.57 | ton kilometer | 1.57 | transport, freight, sea, container ship | activity's table |
| `water_softened_row` | market for water, completely softened | 23.2 | kilogram | 23.2 | water, completely softened | activity's table |
| `water_deionised` | water production, deionised | 39.4 | kilogram | 39.4 | water, deionised | activity's table |
| `waste_wafer_inorganic` | market for waste, from silicon wafer production, inorganic | -0.00641 | kilogram | -0.00641 | waste, from silicon wafer production, inorganic | activity's table |
| `wastewater_pv_cell` | market for wastewater from PV cell production | -0.0132 | cubic meter | -0.0132 | wastewater from PV cell production | activity's table |
| `aluminium` | Aluminium | 0.000773 | kilogram | 0.000773 | aluminium | activity's table |
| `c2f6` | Ethane, hexafluoro-, HFC-116 | 0.000119 | kilogram | 0.000119 | ethane, hexafluoro-, HFC-116 | activity's table |
| `heat_waste` | Heat, waste | 51.8 | megajoule | 51.8 | heat, waste | activity's table |
| `hf` | Hydrogen fluoride | 4.85e-06 | kilogram | 4.85e-06 | hydrogen fluoride | activity's table |
| `lead_resource` | Lead | 3.48e-07 | kilogram | 3.48e-07 | lead | activity's table |
| `cf4` | Methane, tetrafluoro-, R-14 | 0.000248 | kilogram | 0.000248 | methane, tetrafluoro-, R-14 | activity's table |
| `nox` | Nitrogen oxides | 5e-05 | kilogram | 5e-05 | nitrogen oxides | activity's table |
| `silicon` | Silicon | 7.27e-05 | kilogram | 7.27e-05 | silicon | activity's table |
| `silver` | Silver | 6.6e-06 | kilogram | 6.6e-06 | silver | activity's table |
| `water` | Water | 0.0168 | cubic meter | 0.0168 | water | activity's table |
| `water` | Water | 0.277 | cubic meter | 0.277 | water | activity's table |
| `water_cooling_natural` | Water, cooling, unspecified natural origin | 0.231 | cubic meter | 0.231 | Water, cooling, unspecified natural origin - v2 name; in since 22 Oct 2026 | activity's table |
| `hcl_air` | Hydrochloric acid | 0.000266 | kilogram | 0.000266 | hydrogen chloride - v2 name; in since 22 Oct 2026 | activity's table |
| `nmvoc` | NMVOC, non-methane volatile organic compounds | 0.194 | kilogram | 0.194 | NMVOC, unspecified origin - v2 name; in since 22 Oct 2026 | activity's table |
| `pm25_air` | Particulate Matter, < 2.5 um | 0.00266 | kilogram | 0.00266 | particulates, <2.5 um - v2 name; in since 22 Oct 2026 | activity's table |

### `upv_perc_module` — UPV, photovoltaic panel, PERC

square meter, GB. Comment: Smith 2024 Table A8, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_perc_cell` | → UPV, photovoltaic cell, single-Si wafer | 0.9 | square meter | 0.9 | photovoltaic cell, single-Si wafer | activity's table |
| `adipic_acid` | market for adipic acid | 0.000369 | kilogram | 0.000369 | adipic acid | activity's table |
| `aluminium_almg3` | market for aluminium alloy, AlMg3 | 1.51 | kilogram | 1.51 | aluminium alloy, AlMg3 | activity's table |
| `copper_cathode` | market for copper, cathode | 0.148 | kilogram | 0.148 | copper, cathode | activity's table |
| `corrugated_board_box` | market for corrugated board box | 0.763 | kilogram | 0.763 | corrugated board box | activity's table |
| `diode` | diode production, auxilliaries and energy use | 0.00281 | kilogram | 0.00281 | diode, auxilliaries and energy use | activity's table |
| `electricity_mv_th` | market for electricity, medium voltage | 3.32 | kilowatt hour | 3.32 | electricity, medium voltage | activity's table |
| `eva_foil` | market for ethylvinylacetate, foil | 0.793 | kilogram | 0.793 | ethylvinylacetate, foil | activity's table |
| `eur_pallet` | EUR-flat pallet production | 0.05 | unit | 0.05 | EUR-flat pallet | activity's table |
| `gfrp_polyamide` | market for glass fibre reinforced plastic, polyamide, injection moulded | 0.188 | kilogram | 0.188 | glass fibre reinforced plastic, polyamide, injection moulded | activity's table |
| `lead` | market for lead | 0.0108 | kilogram | 0.0108 | lead | activity's table |
| `lubricating_oil` | market for lubricating oil | 0.00161 | kilogram | 0.00161 | lubricating oil | activity's table |
| `metal_working_aluminium` | market for metal working, average for aluminium product manufacturing | 1.51 | kilogram | 1.51 | metal working, average for aluminium product manufacturing | activity's table |
| `ldpe_film` | market for packaging film, low density polyethylene | 0.0401 | kilogram | 0.0401 | packaging film, low density polyethylene | activity's table |
| `panel_factory` | market for photovoltaic panel factory | 4e-06 | unit | 4e-06 | photovoltaic panel factory | activity's table |
| `pet_granulate` | market for polyethylene terephthalate, granulate, amorphous | 0.281 | kilogram | 0.281 | polyethylene terephthalate, granulate, amorphous | activity's table |
| `hdpe_granulate` | market for polyethylene, high density, granulate | 0.0242 | kilogram | 0.0242 | polyethylene, high density, granulate | activity's table |
| `ldpe_granulate` | market for polyethylene, low density, granulate | 0.0548 | kilogram | 0.0548 | polyethylene, low density, granulate | activity's table |
| `pvf_film` | market for polyvinylfluoride, film | 0.0451 | kilogram | 0.0451 | polyvinylfluoride, film | activity's table |
| `silicone_product` | market for silicone product | 0.144 | kilogram | 0.144 | silicone product | activity's table |
| `solar_glass` | market for solar glass, low-iron | 8 | kilogram | 8 | solar glass, low-iron | activity's table |
| `glass_tempering` | market for tempering, flat glass | 8 | kilogram | 8 | tempering, flat glass | activity's table |
| `tin` | market for tin | 0.0104 | kilogram | 0.0104 | tin | activity's table |
| `freight_train_row` | market for transport, freight train | 16.6 | ton kilometer | 16.6 | transport, freight train | activity's table |
| `lorry` | market group for transport, freight, lorry, unspecified | 2.99 | ton kilometer | 2.99 | transport, freight, lorry, unspecified | activity's table |
| `wire_drawing_copper` | market for wire drawing, copper | 0.148 | kilogram | 0.148 | wire drawing, copper | activity's table |
| `municipal_solid_waste` | market for municipal solid waste | -0.0934 | kilogram | -0.0934 | municipal solid waste | activity's table |
| `waste_mineral_oil` | market for waste mineral oil | -0.00161 | kilogram | -0.00161 | waste mineral oil | activity's table |
| `waste_plastic` | market for waste plastic, mixture | -0.0248 | kilogram | -0.0248 | waste plastic, mixture | activity's table |
| `waste_pvf` | market for waste polyvinylfluoride | -0.000902 | kilogram | -0.000902 | waste polyvinylfluoride | activity's table |
| `waste_wafer` | market for waste, from silicon wafer production | -0.00352 | kilogram | -0.00352 | waste, from silicon wafer production | activity's table |
| `co2_fossil` | Carbon dioxide, fossil | 0.0218 | kilogram | 0.0218 | carbon dioxide, fossil | activity's table |
| `heat_waste` | Heat, waste | 13.4 | megajoule | 13.4 | heat, waste | activity's table |
| `water` | Water | 0.0279 | kilogram | 0.0279 | water | activity's table |
| `water_cooling_natural` | Water, cooling, unspecified natural origin | 0.0716 | cubic meter | 0.0716 | Water, cooling, unspecified natural origin - v2 name; in since 22 Oct 2026 | activity's table |
| `nmvoc` | NMVOC, non-methane volatile organic compounds | 0.00806 | kilogram | 0.00806 | NMVOC, unspecified origin - v2 name; in since 22 Oct 2026 | activity's table |

### `upv_inverter_2700kva` — UPV, inverter, 2.7 MWac

unit, GB. Comment: Smith 2024 Table A10, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitution…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `aluminium_wrought` | market for aluminium, wrought alloy | 80 | kilogram | 80 | aluminium, wrought alloy | activity's table |
| `cable_cat5` | market for cable, network cable, category 5, without plugs | 940 | meter | 940 | cable, network cable, category 5, without plugs | activity's table |
| `cable_three_conductor` | market for cable, three-conductor cable | 61 | meter | 61 | cable, three-conductor cable | activity's table |
| `capacitor_electrolyte` | market for capacitor, electrolyte type, > 2cm height | 5 | kilogram | 5 | capacitor, electrolyte type, >2 cm height | activity's table |
| `capacitor_film` | market for capacitor, film type, for through-hole mounting | 50 | kilogram | 50 | capacitor, film type, for through-hole mounting | activity's table |
| `concrete_slab` | market for concrete slab | 1.1 | cubic meter | 1.1 | concrete slab | activity's table |
| `copper_cathode` | market for copper, cathode | 430 | kilogram | 430 | copper, cathode | activity's table |
| `gfrp_polyamide` | market for glass fibre reinforced plastic, polyamide, injection moulded | 30 | kilogram | 30 | glass fibre reinforced plastic, polyamide, injection moulded | activity's table |
| `inductor` | market for inductor, ring core choke type | 650 | kilogram | 650 | inductor, ring core choke type | activity's table |
| `integrated_circuit` | market for integrated circuit, logic type | 0.2 | kilogram | 0.2 | integrated circuit, logic type | activity's table |
| `lubricating_oil` | market for lubricating oil | 1 | kilogram | 1 | lubricating oil | activity's table |
| `pwb_through_hole` | market for printed wiring board, through-hole mounted, unspecified, Pb free | 3 | kilogram | 3 | printed wiring board, through- hole mounted, unspecified, Pb free | activity's table |
| `reinforcing_steel` | market for reinforcing steel | 1200 | kilogram | 1200 | reinforcing steel | activity's table |
| `transformer_hv` | market for transformer, high voltage use | 100 | kilogram | 100 | transformer, high voltage use | activity's table |
| `transistor` | market for transistor, wired, big size, through-hole mounting | 0.3 | kilogram | 0.3 | transistor, wired, big size, through-hole mounting | activity's table |
| `fan` | market for fan, for power supply unit, desktop computer | 0.2 | kilogram | 0.2 | fan, for power supply unit, desktop computer | activity's table |

### `upv_electrical_bos` — UPV, electrical balance of system

square meter, GB. Comment: Smith 2024 Table A12, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitution…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `aluminium_wrought` | market for aluminium, wrought alloy | 0.4 | kilogram | 0.4 | aluminium, wrought alloy | activity's table |
| `epoxy_resin` | market for epoxy resin, liquid | 4.9e-05 | kilogram | 4.9e-05 | epoxy resin, liquid | activity's table |
| `nylon_6` | market for nylon 6 | 0.0064 | kilogram | 0.0064 | nylon 6 | activity's table |
| `polycarbonate` | market for polycarbonate | 6.1e-05 | kilogram | 6.1e-05 | polycarbonate | activity's table |
| `pvc` | market for polyvinylchloride, bulk polymerised | 0.11 | kilogram | 0.11 | polyvinylchloride, bulk polymerised | activity's table |
| `wire_drawing_copper` | market for wire drawing, copper | 0.4 | kilogram | 0.4 | wire drawing, copper | activity's table |

### `upv_fence` — UPV, fence

square meter, GB. Comment: Smith 2024 Table A13, every row at the printed amount. Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitution…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `concrete_25mpa` | market for concrete, 25MPa | 2.9e-05 | cubic meter | 2.9e-05 | concrete, 25MPa | activity's table |
| `section_bar_rolling_steel` | market for section bar rolling, steel | 0.046 | kilogram | 0.046 | section bar rolling, steel | activity's table |
| `steel_low_alloyed` | market for steel, low-alloyed | 0.099 | kilogram | 0.099 | steel, low-alloyed | activity's table |
| `wire_drawing_steel` | market for wire drawing, steel | 0.053 | kilogram | 0.053 | wire drawing, steel | activity's table |
| `zinc_coat_coils` | market for zinc coat, coils | 0.0033 | square meter | 0.0033 | zinc coat, coils | activity's table |

### `upv_fixed_tilt_mounting` — UPV, fixed-tilt mounting structure, 20 deg

square meter, GB. Comment: IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239: the pile-driven 20 deg steel table, per m2 of module - materials, their forming and galvanising, packaging and its disposal, the upstream lorry and rail legs, and the land the table occupies, every r…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `steel_low_alloyed` | market for steel, low-alloyed | 9.23544 | kilogram | 9.23544 | table and piles - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | own locator |
| `aluminium_wrought` | market for aluminium, wrought alloy | 0.284936 | kilogram | 0.284936 | clamps - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `chromium_steel` | market for steel, chromium steel 18/8 | 0.204341 | kilogram | 0.204341 | fasteners - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `polypropylene` | market for polypropylene, granulate | 0.00533838 | kilogram | 0.00533838 | spacers - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `corrugated_board_box_rer` | market for corrugated board box | 0.0925926 | kilogram | 0.0925926 | packaging, not in the stated structure mass - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `section_bar_rolling_steel` | market for section bar rolling, steel | 9.23544 | kilogram | 9.23544 | forming of the steel already counted - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `sheet_rolling_aluminium` | market for sheet rolling, aluminium | 0.284936 | kilogram | 0.284936 | forming of the aluminium already counted - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `wire_drawing_steel` | market for wire drawing, steel | 0.204341 | kilogram | 0.204341 | forming of the chromium steel already counted - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `zinc_coat_pieces` | market for zinc coat, pieces | 0.514042 | square meter | 0.514042 | galvanising of the steel already counted - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `lorry` | market group for transport, freight, lorry, unspecified | 1.946 | ton kilometer | 1.946 | materials to the factory, lorry, 200 km - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `freight_train_rer` | market group for transport, freight train | 5.838 | ton kilometer | 5.838 | materials to the factory, rail, 600 km - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `waste_paperboard_incineration_row` | treatment of waste paperboard, municipal incineration | -0.0926 | kilogram | -0.0926 | packaging cardboard to incineration - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `transformation_from_pasture` | Transformation, from pasture, man made | 2.25 | square meter | 2.25 | land transformation from pasture - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `transformation_to_industrial` | Transformation, to industrial area | 2.25 | square meter | 2.25 | land transformation to industrial area, built-up 0.25 + vegetation 2 - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |
| `occupation_industrial` | Occupation, industrial area | 67.5 | square meter-year | 67.5 | occupation, industrial area, built-up 7.5 + vegetation 60 - IEA PVPS Task 12, Report T12-33:2026, Table 44 / workbook sheet X-Montage-utility, dataset Z-PV-239 | activity's table |

### `upv_fixed_tilt_plant_per_mwp` — UPV, utility-scale PV plant, fixed tilt, per MWp

megawatt, GB. Comment: Smith 2024 Table A14 (installation), one MWp DC of the plant: the module chain (A8), the IEA mounting in place of A9, electrical BoS (A12), fence (A13), inverters at the stated ILR, installation diesel and land occupation. Not carried from A14: the delivery legs (rail 2.2 + 2.0, lorry 3.3e-3 + 0.51 …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_perc_module` | → UPV, photovoltaic panel, PERC | 4913.58 | square meter | 4913.58 | PV modules, 4,914 m2 at 203.5 W/m2 | activity's table |
| `FG:upv_fixed_tilt_mounting` | → UPV, fixed-tilt mounting structure, 20 deg | 4913.58 | square meter | 4913.58 | fixed-tilt mounting, 20 deg (IEA PVPS T12-33:2026) | activity's table |
| `FG:upv_electrical_bos` | → UPV, electrical balance of system | 4913.58 | square meter | 4913.58 | electrical balance of system | activity's table |
| `FG:upv_fence` | → UPV, fence | 4913.58 | square meter | 4913.58 | perimeter fence | activity's table |
| `FG:upv_inverter_2700kva` | → UPV, inverter, 2.7 MWac | 0.276396 | unit | 0.276396 | inverters, 0.2764 x 2.7 MVA at the STATED ILR 1.34 (Smith's own count implies 1.75) | activity's table |
| `diesel_building_machine` | market for diesel, burned in building machine | 12775.3 | megajoule | 12775.3 | installation energy - Smith A14 diesel only; his transport rows are delivery to site (outside the boundary) and his component rows are counted above | activity's table |
| `occupation_natural` | Occupation, unspecified, natural (non-use) | 14740.7 | square meter-year | 14740.7 | Smith A14: 3 m2*a of 'Occupation, unspecified, natural (non-use)' per m2 of module; zero GWP100, in since 21 Oct 2026 | own locator |

### `upv_fixed_tilt_om30_per_mwp` — UPV, 30 years of operation and maintenance, per MWp

megawatt, GB. Comment: Smith 2024 Table A15, thirty years of O&M per MWp: vegetation-management petrol, panel replacement at 0.05 %/yr, inverter replacement at 30.2 % of the installed count. Not carried from A15: the tracker motor (0.017 kg electric motor per m2; the tracker is substituted) and the transformer replacement…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `petrol_low_sulfur` | petrol production, low-sulfur | 270.247 | kilogram | 270.247 | vegetation management - Smith A15 | activity's table |
| `FG:upv_perc_module` | → UPV, photovoltaic panel, PERC | 73.7037 | square meter | 73.7037 | panel replacement, 0.05 %/yr over 30 y - Smith A15 | activity's table |
| `FG:upv_inverter_2700kva` | → UPV, inverter, 2.7 MWac | 0.0835615 | unit | 0.0835615 | inverter replacement, 30.2% of the installed count over 30 y (Mason 10 %/decade) - Smith A15 | activity's table |

### `upv_gb_grid_fleet_1kwh` — UPV, GB grid solar fleet, electricity per kWh

kilowatt hour, GB. Comment: Smith et al. (2024), NREL/TP-7A40-87372, Appendix A (inventory rescored on ecoinvent 3.9.1 apos). Smith publishes on ecoinvent cut-off; his inventory is rescored here on 3.9.1 apos and his results are never transcribed. Boundary and substitutions: UPV_PV_SCOPE (end-of-life and delivery to site out; …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:upv_fixed_tilt_plant_per_mwp` | → UPV, utility-scale PV plant, fixed tilt, per MWp | 3.46717e-08 | megawatt | 3.46717e-08 | plant, per MWp, over its lifetime yield | activity's table |
| `FG:upv_fixed_tilt_om30_per_mwp` | → UPV, 30 years of operation and maintenance, per MWp | 3.46717e-08 | megawatt | 3.46717e-08 | 30 years of O&M, per MWp, over the same yield | activity's table |

## gb_grid — GB grid, 2025 study basis

Database `grid foreground`; source of the activities' own tables: the study's own grid basis (optimiser_lca/grid.py) and the 2025 series.

### `gb_grid_2025_hv_delivered` — electricity, high voltage, GB 2025 study grid, delivered

kilowatt hour, GB. Comment: One kWh of GB grid electricity on this study's own basis (optimiser_lca.grid): NESO's GB-wide 2025 mix, time-mean, each fuel on its grid.SOURCES activity, imports split by the 2025 interconnector flows, delivered at high voltage (losses and the HV market's network exchanges). Replaces ecoinvent's 20…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `GAS` | electricity production, natural gas, combined cycle power plant | 0.291145 | kilowatt hour | 0.291145 | gas 0.2816, grossed up | activity's table |
| `NUCLEAR` | electricity production, nuclear, boiling water reactor | 0.137418 | kilowatt hour | 0.137418 | nuclear 0.1329, grossed up | activity's table |
| `WIND_GT3_ONSHORE` | electricity production, wind, >3MW turbine, onshore | 0.0141701 | kilowatt hour | 0.0141701 | wind 0.3210 x 0.0427 of the wind group, grossed up | activity's table |
| `WIND_13_OFFSHORE` | electricity production, wind, 1-3MW turbine, offshore | 0.11601 | kilowatt hour | 0.11601 | wind 0.3210 x 0.3496 of the wind group, grossed up | activity's table |
| `WIND_13_ONSHORE` | electricity production, wind, 1-3MW turbine, onshore | 0.201689 | kilowatt hour | 0.201689 | wind 0.3210 x 0.6077 of the wind group, grossed up | activity's table |
| `HYDRO` | electricity production, hydro, run-of-river | 0.00039181 | kilowatt hour | 0.00039181 | hydro 0.0004, grossed up | activity's table |
| `BIOMASS` | heat and power co-generation, wood chips, 6667 kW, state-of-the-art 2014 | 0.0788572 | kilowatt hour | 0.0788572 | biomass 0.0763, grossed up | activity's table |
| `SOLAR` | UPV, GB grid solar fleet, electricity per kWh | 0.0648016 | kilowatt hour | 0.0648016 | solar 0.0627, grossed up | activity's table |
| `IMPORTS_FR` | electricity, high voltage, import from FR | 0.0677459 | kilowatt hour | 0.0677459 | imports from FR 0.0655, grossed up | activity's table |
| `IMPORTS_BE` | electricity, high voltage, import from BE | 0.0109696 | kilowatt hour | 0.0109696 | imports from BE 0.0106, grossed up | activity's table |
| `IMPORTS_NL` | electricity, high voltage, import from NL | 0.0082094 | kilowatt hour | 0.0082094 | imports from NL 0.0079, grossed up | activity's table |
| `IMPORTS_NO` | market for electricity, high voltage | 0.0282082 | kilowatt hour | 0.0282082 | imports from NO 0.0273, grossed up | activity's table |
| `IMPORTS_DK` | market for electricity, high voltage | 0.0127209 | kilowatt hour | 0.0127209 | imports from DK 0.0123, grossed up | activity's table |
| `IMPORTS_IE` | electricity, high voltage, import from IE | 0.0011899 | kilowatt hour | 0.0011899 | imports from IE 0.0012, grossed up | activity's table |
| `hvdc_aerial` | market for transmission network, electricity, high voltage direct current aerial line | 2.24032e-09 | kilometer | 2.24032e-09 | GB HV market's own network, per kWh delivered | activity's table |
| `hvdc_land` | market for transmission network, electricity, high voltage direct current land cable | 1.46725e-10 | kilometer | 1.46725e-10 | GB HV market's own network, per kWh delivered | activity's table |
| `hvdc_subsea` | market for transmission network, electricity, high voltage direct current subsea cable | 2.78767e-10 | kilometer | 2.78767e-10 | GB HV market's own network, per kWh delivered | activity's table |
| `n2o` | Dinitrogen monoxide | 5.169e-06 | kilogram | 5.169e-06 | corona discharge, from the GB HV market | activity's table |
| `ozone` | Ozone | 4.29826e-06 | kilogram | 4.29826e-06 | from the GB HV market | activity's table |

## hydrogen — hydrogen (Hermesmann & Müller 2022 fossil routes, Gerloff 2021 electrolysers)

Database `hydrogen foreground`; source of the activities' own tables: Hermesmann & Müller 2022 Tables 2–3 / Gerloff 2021 SI Figs 1–5, Tables 3–6.

### `smr_hermesmann_1kg_h2` — Hydrogen production, SMR (Hermesmann & Müller 2022)

kilogram, GB. Comment: Steam methane reforming, 1 kg H2 at the plant: Hermesmann & Müller 2022 Table 2, every row at the printed amount (through SMR.XLSX), gas and electricity on GB datasets. The paper's excess-electricity credit is not taken; a carbon-balance closure on the gas's own carbon is added (DERIVED). No end-of-…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `gas_hp_gb` | market for natural gas, high pressure | 4.85 | cubic meter | 4.85 | Natural gas, high pressure (Table 2) | activity's table |
| `tap_water` | market for tap water | 6.64 | kilogram | 6.64 | Tap water | activity's table |
| `concrete_normal` | concrete, all types to generic market for concrete, normal strength | 6.6e-06 | cubic meter | 6.6e-06 | Concrete, plant | activity's table |
| `steel_unalloyed` | market for steel, unalloyed | 0.00506 | kilogram | 0.00506 | Steel, unalloyed, plant | activity's table |
| `aluminium_cast` | market for aluminium, primary, cast alloy slab from continuous casting | 4.17e-05 | kilogram | 4.17e-05 | Aluminium, primary, cast alloy slab, plant | activity's table |
| `cast_iron_glo` | market for cast iron | 6.18e-05 | kilogram | 6.18e-05 | Cast iron, plant | activity's table |
| `gas_turbine` | market for gas turbine, 10MW electrical | 7.9e-10 | unit | 7.9e-10 | Gas turbine, 10MW — the paper's proxy for the steam turbine | activity's table |
| `wastewater` | market for wastewater, average | 0.00172 | cubic meter | 0.00172 | Wastewater, average | activity's table |
| `co2` | Carbon dioxide, fossil | 9 | kilogram | 9 | Carbon dioxide (Table 2); modelled as fossil | activity's table |
| `co2` | Carbon dioxide, fossil | 0.678685 | kilogram | 0.678685 | DERIVED — carbon-balance closure on the linked gas's own carbon content, all to air | DERIVED |
| `oxygen_air` | Oxygen | 0.31 | kilogram | 0.31 | Oxygen to air | activity's table |
| `nitrogen_air` | Nitrogen | 16.41 | kilogram | 16.41 | Nitrogen to air (Table 2); zero GWP | activity's table |
| `water_air` | Water, in air | 2.93 | kilogram | 2.93 | Water to air | activity's table |
| `water_resource` | Water, cooling, unspecified natural origin | 0.38 | cubic meter | 0.38 | Water, cooling | activity's table |

### `smr_ccs_hermesmann_1kg_h2` — Hydrogen production, SMR with 90 % CCS (Hermesmann & Müller 2022)

kilogram, GB. Comment: SMR with post-combustion MEA capture at 90 %, 1 kg H2 at the plant: Hermesmann & Müller 2022 Table 2 at the printed amounts, the captured CO2 (8.90 kg, the paper's 90 % of 9.89) sent to the foreground CCS treatment. The excess-electricity credit is not taken; the carbon-balance gap to the gas's own …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:ccs_hermesmann_1kg_co2` | → Carbon capture and storage, per kg CO2 (Hermesmann & Müller 2022 §3.2.3) | 8.9 | kilogram | 8.9 | CO2 captured, to the foreground CCS treatment: 90 % of 9.00 x 5.33/4.85 (Table 2, §4.1.1) | activity's table |
| `FG:ccs_hermesmann_1kg_co2` | → Carbon capture and storage, per kg CO2 (Hermesmann & Müller 2022 §3.2.3) | 0.671918 | kilogram | 0.671918 | DERIVED — the closure gap's captured share (90 %) | DERIVED |
| `gas_hp_gb` | market for natural gas, high pressure | 5.33 | cubic meter | 5.33 | Natural gas, high pressure (Table 2) | activity's table |
| `tap_water` | market for tap water | 4.68 | kilogram | 4.68 | Tap water | activity's table |
| `concrete_normal` | concrete, all types to generic market for concrete, normal strength | 6.6e-06 | cubic meter | 6.6e-06 | Concrete, plant | activity's table |
| `steel_unalloyed` | market for steel, unalloyed | 0.00506 | kilogram | 0.00506 | Steel, unalloyed, plant | activity's table |
| `aluminium_cast` | market for aluminium, primary, cast alloy slab from continuous casting | 4.17e-05 | kilogram | 4.17e-05 | Aluminium, primary, cast alloy slab, plant | activity's table |
| `cast_iron_glo` | market for cast iron | 6.18e-05 | kilogram | 6.18e-05 | Cast iron, plant | activity's table |
| `gas_turbine` | market for gas turbine, 10MW electrical | 7.9e-10 | unit | 7.9e-10 | Gas turbine, 10MW — the paper's proxy for the steam turbine | activity's table |
| `wastewater` | market for wastewater, average | 0.00183 | cubic meter | 0.00183 | Wastewater, average | activity's table |
| `co2` | Carbon dioxide, fossil | 0.99 | kilogram | 0.99 | Carbon dioxide, the 10 % not captured (Table 2) | activity's table |
| `co2` | Carbon dioxide, fossil | 0.0746576 | kilogram | 0.0746576 | DERIVED — the closure gap's emitted share (10 %) | DERIVED |
| `oxygen_air` | Oxygen | 0.41 | kilogram | 0.41 | Oxygen to air | activity's table |
| `nitrogen_air` | Nitrogen | 20.84 | kilogram | 20.84 | Nitrogen to air (Table 2, SMR-CCS 90 %); zero GWP | activity's table |
| `water_air` | Water, in air | 1.33 | kilogram | 1.33 | Water to air | activity's table |
| `water_resource` | Water, cooling, unspecified natural origin | 1.18 | cubic meter | 1.18 | Water, cooling | activity's table |

### `ccs_hermesmann_1kg_co2` — Carbon capture and storage, per kg CO2 (Hermesmann & Müller 2022 §3.2.3)

kilogram, GB. Comment: Transport and storage of 1 kg of captured CO2: Hermesmann & Müller 2022 §3.2.3 (pipeline, injection well, well-drilling diesel at 15.4 kg per tonne, pumping and compression electricity), as the study's SimaPro project transcribed it (ccs.XLSX). A waste treatment the SMR-CCS route links to.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `ccs_pipeline` | market for pipeline, natural gas, long distance, low capacity, onshore | 2.34666e-09 | kilometer | 2.34666e-09 | Pipeline, natural gas, long distance — the CO2 pipeline | activity's table |
| `ccs_well` | market for onshore well, oil/gas | 9.863e-08 | meter | 9.863e-08 | Onshore well, oil/gas — the injection well | activity's table |
| `ccs_diesel_burned` | market for diesel, burned in building machine | 0.65912 | megajoule | 0.65912 | SUBSTITUTED — well drilling, Verma's 15.4 kg diesel read per tonne of CO2 and burned (the export linked it unburned) | activity's table |
| `FG:gb_grid_2025_hv_delivered` | → gb_grid_2025_hv_delivered | 0.0171 | kilowatt hour | 0.0171 | Electricity — pipeline pumping, on the study's GB grid | activity's table |
| `FG:gb_grid_2025_hv_delivered` | → gb_grid_2025_hv_delivered | 0.007 | kilowatt hour | 0.007 | Electricity — compressor to 150 bar, on the study's GB grid | activity's table |
| `co2` | Carbon dioxide, fossil | 1.36106e-07 | kilogram | 1.36106e-07 | CO2 fugitive emissions from pipeline and well | activity's table |

### `mp_e_1kg_h2` — Hydrogen production, methane pyrolysis MP-E (Hermesmann & Müller 2022)

kilogram, GB. Comment: Electrically heated methane pyrolysis, 1 kg H2 at the plant: Hermesmann & Müller 2022 Table 3, every row at the printed amount, gas and electricity on GB datasets. The 3.00 kg of solid carbon per kg H2 (Table 3 'Output flows: Carbon') is not credited against carbon black as §3.2.4 do: the whole burd…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `gas_hp_gb` | market for natural gas, high pressure | 5.72 | cubic meter | 5.72 | Natural gas, high pressure (Table 3) | activity's table |
| `FG:gb_grid_2025_hv_delivered` | → gb_grid_2025_hv_delivered | 10.29 | kilowatt hour | 10.29 | Electricity — electric heating, on the study's GB grid | activity's table |
| `palladium` | palladium to generic market for metal catalyst for catalytic converter | 8.45e-06 | kilogram | 8.45e-06 | Palladium, catalyst | activity's table |
| `copper_cathode` | market for copper, cathode | 5.63e-06 | kilogram | 5.63e-06 | Copper, plant | activity's table |
| `steel_low_alloyed` | market for steel, low-alloyed | 0.00199 | kilogram | 0.00199 | Steel, low-alloyed, plant | activity's table |
| `steel_chromium_188` | market for steel, chromium steel 18/8 | 0.000389 | kilogram | 0.000389 | Steel, chromium 18/8, plant | activity's table |
| `silica_sand` | market for silica sand | 6.18e-05 | kilogram | 6.18e-05 | Silica sand | activity's table |
| `tin` | market for tin | 0.0258 | kilogram | 0.0258 | Tin, the molten-metal medium make-up | activity's table |
| `silicon_carbide` | market for silicon carbide | 3.23e-06 | kilogram | 3.23e-06 | Silicon carbide | activity's table |

### `ae_gerloff_1unit` — Alkaline electrolyser, 1 MW, 20-year life (Gerloff 2021)

unit, GLO. Comment: One 1 MW alkaline electrolyser over its 20-year life: Gerloff 2021 SI Fig. 1 (18 BoP and 3 stack components, every row at the printed amount, RoW datasets as exported), the stack's rows three times over (§2.1.3), SI Table 3's manufacturing electricity (already x3 on the stack) on the German LV marke…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `polyethylene_ld_row` | polyethylene production, low density, granulate | 464.6 | kilogram | 464.6 | Water purifier / feed tank (SI Fig. 1 names LD polyethylene) | activity's table |
| `extrusion_pipes` | market for extrusion, plastic pipes | 464.6 | kilogram | 464.6 | Water purifier / feed tank | activity's table |
| `reinforcing_steel_row` | reinforcing steel production | 5134.4 | kilogram | 5134.4 | Reinforcing steel, BoP (aggregated as printed) | activity's table |
| `sheet_rolling_steel` | market for sheet rolling, steel | 10130 | kilogram | 10130 | Sheet rolling, steel, BoP (aggregated) | activity's table |
| `electronics_row` | electronics production, for control units | 100 | kilogram | 100 | Control panel / electronics | activity's table |
| `aluminium_wrought` | market for aluminium, wrought alloy | 160 | kilogram | 160 | Transformer + frequency converter | activity's table |
| `copper_cathode` | market for copper, cathode | 616.7 | kilogram | 616.7 | Transformer + compressor + tubing/cables | activity's table |
| `sheet_rolling_aluminium` | market for sheet rolling, aluminium | 100 | kilogram | 100 | Transformer and rectifier | activity's table |
| `tube_insulation` | tube insulation production, elastomere | 207.9 | kilogram | 207.9 | Transformer + compressor + tubing | activity's table |
| `wire_drawing_copper` | market for wire drawing, copper | 616.7 | kilogram | 616.7 | Transformer + compressor + tubing | activity's table |
| `glass_fibre_row` | glass fibre production | 464.6 | kilogram | 464.6 | H2 drier and deoxidiser | activity's table |
| `sheet_rolling_cr_steel` | market for sheet rolling, chromium steel | 6697.8 | kilogram | 6697.8 | Sheet rolling, chromium steel, BoP (26,892.2 less the stack's 20,194.4) | activity's table |
| `cr_steel_hot_rolled_row` | steel production, chromium steel 18/8, hot rolled | 6697.8 | kilogram | 6697.8 | Chromium steel 18/8 hot rolled, BoP (as above) | activity's table |
| `cast_iron_row` | cast iron production | 716.1 | kilogram | 716.1 | Compressor + pumps and coolers | activity's table |
| `ethylene_glycol_row` | ethylene glycol production | 7 | kilogram | 7 | Diaphragm for compressor | activity's table |
| `welding_arc_steel` | market for welding, arc, steel | 29 | meter | 29 | Buffer tank (SI prints m) | activity's table |
| `polypropylene_row` | polypropylene production, granulate | 3 | kilogram | 3 | Alkali-resistant rotary pump | activity's table |
| `injection_moulding` | market for injection moulding | 3 | kilogram | 3 | Alkali-resistant rotary pump | activity's table |
| `low_alloyed_steel_hr_row` | steel production, low-alloyed, hot rolled | 6075.6 | kilogram | 6075.6 | Container | activity's table |
| `concrete_35mpa_cem3` | concrete production, 35MPa, for building construction, with cement, CEM III/A | 7.7 | cubic meter | 7.7 | Foundation | activity's table |
| `sheet_rolling_cr_steel` | market for sheet rolling, chromium steel | 60583.2 | kilogram | 60583.2 | Stack x3 — anode and cathode with frame, sheet rolling, chromium steel (20,194.4 per stack) | activity's table |
| `cr_steel_hot_rolled_row` | steel production, chromium steel 18/8, hot rolled | 60583.2 | kilogram | 60583.2 | Stack x3 — anode and cathode with frame, chromium steel 18/8 hot rolled | activity's table |
| `nickel_class1` | market for nickel, class 1 | 8654.7 | kilogram | 8654.7 | Stack x3 — anode + cathode, nickel (2,884.9 per stack) | activity's table |
| `tetrafluoroethylene_row` | tetrafluoroethylene production | 432.6 | kilogram | 432.6 | Stack x3 — gasket (144.2 per stack) | activity's table |
| `polysulfone` | polysulfone production, for membrane filtration production | 146.4 | kilogram | 146.4 | Stack x3 — diaphragm, Zirfon (48.8 per stack) | activity's table |
| `zirconium_oxide_row` | zirconium oxide production | 219 | kilogram | 219 | Stack x3 — diaphragm, Zirfon (73.0 per stack) | activity's table |
| `electricity_lv_de` | market for electricity, low voltage | 323773 | kilowatt hour | 323773 | SI Table 3: BoP 37,113.5 + stack 286,659.9 kWh (the stack x3 already) | own locator |
| `lorry_32t_euro6` | market for transport, freight, lorry >32 metric ton, EURO6 | 22670.9 | ton kilometer | 22670.9 | ADDED — Gerloff §2.1: materials to assembly, 250 km on the unit's mass with three stacks | ADDED |

### `ae_op_gerloff_1kg_h2` — Hydrogen production, alkaline electrolysis (Gerloff 2021)

kilogram, DE. Comment: 1 kg H2 from the alkaline unit: Gerloff 2021 SI Table 6 operating data at the printed amounts, the capital good at 1 unit per lifetime output (SI Table 4), electricity as exported on the German LV market (electrolysers.py strips it out and the LP charges the site's own power).

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:ae_gerloff_1unit` | → Alkaline electrolyser, 1 MW, 20-year life (Gerloff 2021) | 3.24e-07 | unit | 3.24e-07 | Capital good: 1 unit per lifetime H2 (SI Table 4, as exported) | activity's table |
| `water_deionised` | market for water, deionised | 8.9 | kilogram | 8.9 | Water, deionised (SI Table 6: 8.9 l) | activity's table |
| `water_softened` | market for water, completely softened | 88.1 | kilogram | 88.1 | Water, completely softened | activity's table |
| `electrolyte_koh` | market for electrolyte, KOH, LiOH additive | 0.0037 | kilogram | 0.0037 | Electrolyte KOH/LiOH | activity's table |
| `electricity_lv_de` | market for electricity, low voltage | 51.8 | kilowatt hour | 51.8 | Electricity LV DE — electrolysis, as exported (SI Table 6) | activity's table |

### `pem_gerloff_1unit` — PEM electrolyser, 1 MW, 20-year life (Gerloff 2021)

unit, GB. Comment: One 1 MW PEM electrolyser over its 20-year life: Gerloff 2021 SI Fig. 2 (17 BoP and 8 stack components at the printed amounts, RER datasets as exported), the stack's rows three times over (§2.1.3), SI Table 3's manufacturing electricity on GB LV, and the 250 km assembly leg. Platinum stands in for t…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `extrusion_pipes` | market for extrusion, plastic pipes | 464.6 | kilogram | 464.6 | Water purifier / feed tank | activity's table |
| `polyethylene_ld_rer` | polyethylene production, low density, granulate | 464.6 | kilogram | 464.6 | Water purifier / feed tank | activity's table |
| `aluminium_wrought` | market for aluminium, wrought alloy | 260 | kilogram | 260 | Power electronics + purification, BoP (287.0 less the end plate's 27.0) | activity's table |
| `sheet_rolling_aluminium` | market for sheet rolling, aluminium | 200 | kilogram | 200 | Power electronics + purification, BoP (227.0 less the end plate's 27.0) | activity's table |
| `electronics_rer` | electronics production, for control units | 100 | kilogram | 100 | Control panel / electronics | activity's table |
| `cast_iron_rer` | cast iron production | 600 | kilogram | 600 | Diaphragm compressor | activity's table |
| `ethylene_glycol_rer` | ethylene glycol production | 7 | kilogram | 7 | Diaphragm compressor | activity's table |
| `copper_cathode` | market for copper, cathode | 345 | kilogram | 345 | Power electronics + gas separator + compressor, BoP (349.5 less the collector's 4.5) | activity's table |
| `sheet_rolling_copper` | market for sheet rolling, copper | 100 | kilogram | 100 | Water gas separator, BoP (104.5 less the collector's 4.5) | activity's table |
| `wire_drawing_copper` | market for wire drawing, copper | 245 | kilogram | 245 | Power electronics + compressor | activity's table |
| `injection_moulding` | market for injection moulding | 300 | kilogram | 300 | Valve | activity's table |
| `polypropylene_rer` | polypropylene production, granulate | 300 | kilogram | 300 | Valve | activity's table |
| `lubricating_oil` | market for lubricating oil | 100 | kilogram | 100 | Back pressure regulator | activity's table |
| `reinforcing_steel_eur` | reinforcing steel production | 3312.3 | kilogram | 3312.3 | Power electronics + water purifier + compressor + container | activity's table |
| `sheet_rolling_cr_steel` | market for sheet rolling, chromium steel | 4327 | kilogram | 4327 | Steel + heat exchanger + compressor + buffer, BoP (4,427.0 less the bolts' 100.0) | activity's table |
| `sheet_rolling_steel` | market for sheet rolling, steel | 5382.3 | kilogram | 5382.3 | Power electronics + tubing + water purifier + compressor | activity's table |
| `cr_steel_hr_rer` | steel production, chromium steel 18/8, hot rolled | 4327 | kilogram | 4327 | Chromium steel 18/8 hot rolled, BoP (as above) | activity's table |
| `low_alloyed_steel_hr_rer` | steel production, low-alloyed, hot rolled | 3150 | kilogram | 3150 | Tubing/pump + container | activity's table |
| `welding_arc_steel` | market for welding, arc, steel | 29 | meter | 29 | Buffer tank (SI prints kg; welding is per metre) | activity's table |
| `tube_insulation` | tube insulation production, elastomere | 115 | kilogram | 115 | Power electronics + compressor | activity's table |
| `zeolite` | zeolite production, powder | 100 | kilogram | 100 | Ion exchanger | activity's table |
| `concrete_35mpa_cem2` | concrete production, 35MPa, with cement, CEM II/B | 2.3 | cubic meter | 2.3 | Foundation | activity's table |
| `aluminium_wrought` | market for aluminium, wrought alloy | 81 | kilogram | 81 | Stack x3 — end plate, aluminium (27.0 per stack) | activity's table |
| `sheet_rolling_aluminium` | market for sheet rolling, aluminium | 81 | kilogram | 81 | Stack x3 — end plate, sheet rolling | activity's table |
| `titanium` | titanium production | 1584 | kilogram | 1584 | Stack x3 — bipolar plates (528.0 per stack) | activity's table |
| `tetrafluoroethylene_rer` | tetrafluoroethylene production | 48 | kilogram | 48 | Stack x3 — membrane polymer, Nafion proxy (16.0 per stack) | activity's table |
| `carbon_black` | carbon black production | 27 | kilogram | 27 | Stack x3 — electrocatalyst support, anode + cathode (4.5 + 4.5 per stack) | activity's table |
| `platinum` | market for platinum | 2.625 | kilogram | 2.625 | SUBSTITUTED — Stack x3: 0.075 kg platinum (cathode) + 0.8 kg iridium (anode) per stack, both as platinum | activity's table |
| `copper_cathode` | market for copper, cathode | 13.5 | kilogram | 13.5 | Stack x3 — current collector, copper (4.5 per stack) | activity's table |
| `sheet_rolling_copper` | market for sheet rolling, copper | 13.5 | kilogram | 13.5 | Stack x3 — current collector, sheet rolling | activity's table |
| `sheet_rolling_cr_steel` | market for sheet rolling, chromium steel | 300 | kilogram | 300 | Stack x3 — bolts and screws, sheet rolling (100.0 per stack) | activity's table |
| `cr_steel_hr_rer` | steel production, chromium steel 18/8, hot rolled | 300 | kilogram | 300 | Stack x3 — bolts and screws, chromium steel | activity's table |
| `synthetic_rubber` | synthetic rubber production | 14.4 | kilogram | 14.4 | Stack x3 — gasket (4.8 per stack) | activity's table |
| `electricity_lv_gb` | market for electricity, low voltage | 361672 | kilowatt hour | 361672 | SI Table 3: BoP 50,000 + stack 311,672.3 kWh (the stack x3 already) | own locator |
| `lorry_32t_euro6` | market for transport, freight, lorry >32 metric ton, EURO6 | 3812.84 | ton kilometer | 3812.84 | ADDED — Gerloff §2.1: materials to assembly, 250 km on the unit's mass with three stacks | ADDED |

### `pem_op_gerloff_1kg_h2` — Hydrogen production, PEM electrolysis (Gerloff 2021)

kilogram, GB. Comment: 1 kg H2 from the PEM unit: Gerloff 2021 SI Table 6 operating data at the printed amounts, the capital good at 1 unit per lifetime output (SI Table 4), electricity on GB LV as exported (stripped out by electrolysers.py; the LP charges the site's own power), heat on the dataset Gerloff export.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:pem_gerloff_1unit` | → PEM electrolyser, 1 MW, 20-year life (Gerloff 2021) | 3.37e-07 | unit | 3.37e-07 | Capital good: 1 unit per lifetime H2 (SI Table 4, as exported) | activity's table |
| `water_deionised` | market for water, deionised | 8.9 | kilogram | 8.9 | Water, deionised (SI Table 6: 8.9 l) | activity's table |
| `water_softened` | market for water, completely softened | 88.1 | kilogram | 88.1 | Water, completely softened | activity's table |
| `electricity_lv_gb` | market for electricity, low voltage | 54 | kilowatt hour | 54 | Electricity LV GB — electrolysis (SI Table 6) | activity's table |
| `heat_rer` | market group for heat, district or industrial, other than natural gas | 1.008 | megajoule | 1.008 | Heat, district or industrial (SI Table 6: 0.28 kWh = 1.008 MJ) | activity's table |

### `soec_gerloff_1unit` — SOEC electrolyser, 1 MW, 20-year life (Gerloff 2021)

unit, GB. Comment: One 1 MW solid-oxide electrolyser over its 20-year life: Gerloff 2021 SI Figs 3-5 (48 BoP and 7 stack components at the printed amounts, RER datasets as exported), the stack's rows three times over (§2.1.3), SI Table 3's manufacturing electricity on GB LV, the 250 km assembly leg, and ASSUMED La2O3 …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `extrusion_pipes` | market for extrusion, plastic pipes | 534 | kilogram | 534 | Water purifier / pre-heating | activity's table |
| `polyethylene_ld_rer` | polyethylene production, low density, granulate | 534 | kilogram | 534 | Water purifier / pre-heating | activity's table |
| `aluminium_wrought` | market for aluminium, wrought alloy | 401 | kilogram | 401 | Frequency converters + power electronics + water pump | activity's table |
| `sheet_rolling_aluminium` | market for sheet rolling, aluminium | 100 | kilogram | 100 | Power electronics | activity's table |
| `electronics_rer` | electronics production, for control units | 100 | kilogram | 100 | Control electronics | activity's table |
| `abs_row` | acrylonitrile-butadiene-styrene copolymer production | 1.4 | kilogram | 1.4 | Control panel / heater | activity's table |
| `injection_moulding` | market for injection moulding | 1.4 | kilogram | 1.4 | Control panel / heater | activity's table |
| `cast_iron_rer` | cast iron production | 3000 | kilogram | 3000 | Diaphragm compressors 1-5 | activity's table |
| `ethylene_glycol_rer` | ethylene glycol production | 35 | kilogram | 35 | Diaphragm compressors 1-5 | activity's table |
| `copper_cathode` | market for copper, cathode | 428.5 | kilogram | 428.5 | Control + frequency converters + power electronics + pump | activity's table |
| `wire_drawing_copper` | market for wire drawing, copper | 428.5 | kilogram | 428.5 | Control + frequency converters + power electronics + pump | activity's table |
| `tube_insulation` | tube insulation production, elastomere | 176.6 | kilogram | 176.6 | Frequency converters + power electronics + control + pump | activity's table |
| `reinforcing_steel_eur` | reinforcing steel production | 13730.6 | kilogram | 13730.6 | BoP steel components | activity's table |
| `sheet_rolling_cr_steel` | market for sheet rolling, chromium steel | 16621.4 | kilogram | 16621.4 | BoP chromium steel components, sheet rolling (25,597.5 less the air electrode's 8,976.1) | activity's table |
| `sheet_rolling_steel` | market for sheet rolling, steel | 12081.2 | kilogram | 12081.2 | BoP steel components | activity's table |
| `cr_steel_hr_rer` | steel production, chromium steel 18/8, hot rolled | 16621.4 | kilogram | 16621.4 | BoP chromium steel 18/8 hot rolled (as above) | activity's table |
| `low_alloyed_steel_hr_rer` | steel production, low-alloyed, hot rolled | 3753.6 | kilogram | 3753.6 | Tubing + container — pre-heating | activity's table |
| `welding_arc_steel` | market for welding, arc, steel | 33.3 | meter | 33.3 | Buffer tank (pre-heating) | activity's table |
| `concrete_35mpa_cem2` | concrete production, 35MPa, with cement, CEM II/B | 2.3 | cubic meter | 2.3 | Foundation | activity's table |
| `sheet_rolling_cr_steel` | market for sheet rolling, chromium steel | 26928.3 | kilogram | 26928.3 | Stack x3 — air electrode / interconnect, sheet rolling, chromium steel (8,976.1 per stack) | activity's table |
| `cr_steel_hr_rer` | steel production, chromium steel 18/8, hot rolled | 26928.3 | kilogram | 26928.3 | Stack x3 — air electrode / interconnect, chromium steel 18/8 hot rolled | activity's table |
| `praseodymium_oxide` | market for praseodymium-neodymium oxide | 27 | kilogram | 27 | Stack x3 — air electrode screen printing (9.0 per stack) | activity's table |
| `nickel_class1` | market for nickel, class 1 | 432.3 | kilogram | 432.3 | Stack x3 — air electrode 7.5 + firing 136.6 per stack | activity's table |
| `zirconium_oxide_row` | zirconium oxide production | 512.1 | kilogram | 512.1 | Stack x3 — blocking layer (170.7 per stack) | activity's table |
| `samarium_seg_oxide` | market for samarium-europium-gadolinium oxide | 113.1 | kilogram | 113.1 | Stack x3 — blocking layer 14.8 + screen printing 22.9 per stack | activity's table |
| `cerium_oxide` | cerium oxide to generic market for mischmetal | 274.5 | kilogram | 274.5 | Stack x3 — blocking layer screen printing (91.5 per stack) | activity's table |
| `aluminium_oxide` | aluminium oxide, non-metallurgical to generic market for refractory material, acid | 19.2 | kilogram | 19.2 | Stack x3 — electrolyte + H2 electrode, glass sealant (6.4 per stack) | activity's table |
| `boric_oxide` | boric oxide production | 19.2 | kilogram | 19.2 | Stack x3 — electrolyte + H2 electrode (6.4 per stack) | activity's table |
| `barium_oxide` | barium oxide production | 19.2 | kilogram | 19.2 | Stack x3 — electrolyte + H2 electrode (6.4 per stack) | activity's table |
| `silicone_product` | silicone product production | 19.2 | kilogram | 19.2 | Stack x3 — electrolyte sealant (6.4 per stack; the figure's dataset) | activity's table |
| `lanthanum_oxide` | market for lanthanum oxide | 32.9355 | kilogram | 32.9355 | ASSUMED — Stack x3: LSM layer's La2O3, 0.563 of a 19.5 kg layer per stack (Gerloff row 53 gives no amount) | ASSUMED |
| `strontium_carbonate` | market for strontium carbonate | 7.488 | kilogram | 7.488 | ASSUMED — Stack x3: LSM layer's SrCO3, 0.128 of a 19.5 kg layer per stack | ASSUMED |
| `electricity_lv_gb` | market for electricity, low voltage | 443094 | kilowatt hour | 443094 | SI Table 3: BoP 76,420.2 + stack 366,673.3 kWh (the stack x3 already) | own locator |
| `lorry_32t_euro6` | market for transport, freight, lorry >32 metric ton, EURO6 | 16786.6 | ton kilometer | 16786.6 | ADDED — Gerloff §2.1: materials to assembly, 250 km on the unit's mass with three stacks | ADDED |

### `soec_op_gerloff_1kg_h2` — Hydrogen production, SOEC electrolysis (Gerloff 2021)

kilogram, GB. Comment: 1 kg H2 from the SOEC unit: Gerloff 2021 SI Table 6 operating data at the printed amounts, the capital good at 1 unit per lifetime output (SI Table 4), electricity on GB LV as exported (stripped out by electrolysers.py), and the 5.24 kWh of heat on Mehmeti et al. 2018's natural-gas boiler, the sourc…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:soec_gerloff_1unit` | → SOEC electrolyser, 1 MW, 20-year life (Gerloff 2021) | 2.645e-07 | unit | 2.645e-07 | Capital good: 1 unit per lifetime H2 (SI Table 4, as exported) | activity's table |
| `water_deionised` | market for water, deionised | 8.9 | kilogram | 8.9 | Water, deionised (SI Table 6: 8.9 l) | activity's table |
| `water_softened` | market for water, completely softened | 644.7 | kilogram | 644.7 | Water, completely softened | activity's table |
| `electricity_lv_gb` | market for electricity, low voltage | 42.3 | kilowatt hour | 42.3 | Electricity LV GB — electrolysis (SI Table 6) | activity's table |
| `heat_ng_boiler` | heat production, natural gas, at boiler modulating >100kW | 18.864 | megajoule | 18.864 | SUBSTITUTED — heat on Mehmeti 2018's natural-gas boiler (5.24 kWh = 18.864 MJ), not Gerloff's coal-heavy heat | activity's table |

## data_centre — data centre (Zhang 2025)

Database `data centre foreground`; source of the activities' own tables: Zhang et al. 2025 Table 1 / S1.

### `dc_zhang_virginia_baseline_25y` — Data centre facility, hyperscale, Virginia (Zhang et al. 2025)

unit, US-SERC. Comment: 25-year hyperscale data centre (10,000 m^2 white space), Virginia US, SERC grid, PUE 1.4 baseline. Zhang et al. 2025, Cleaner Energy Systems 12, 100223, Table 1 / supplementary Table S1: Material Production, Construction and Operation at the printed amounts, plus the refrigerant top-up emitted as a …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `concrete` | market for concrete, 30-32MPa | 4000 | cubic meter | 4000 | Concrete, 30-32MPa, building shell and foundation | activity's table |
| `reinforcing_steel` | market for reinforcing steel | 480000 | kilogram | 480000 | Reinforcing steel | activity's table |
| `structural_steel` | market for steel, low-alloyed, hot rolled | 120000 | kilogram | 120000 | Structural steel | activity's table |
| `copper` | market for copper, cathode | 20000 | kilogram | 20000 | Copper, cabling and architectural elements | activity's table |
| `aluminium_alloy` | market for aluminium alloy, metal matrix composite | 15000 | kilogram | 15000 | Aluminium alloy | activity's table |
| `insulation_pur` | market for polyurethane, rigid foam | 25000 | kilogram | 25000 | Insulation, rigid PUR foam | activity's table |
| `diesel_construction` | market for diesel, burned in building machine | 2.1e+06 | megajoule | 2.1e+06 | Diesel, burned in building machine — construction | activity's table |
| `electricity_mv_gb` | market for electricity, medium voltage | 78000 | kilowatt hour | 78000 | Electricity MV — construction (Zhang's 78,000 kWh, 2.80e5 MJ) | activity's table |
| `tap_water` | market group for tap water | 1.2e+06 | kilogram | 1.2e+06 | Tap water — construction | activity's table |
| `electricity_mv_serc` | market for electricity, medium voltage | 1.6e+09 | kilowatt hour | 1.6e+09 | Electricity MV, US-SERC — IT + cooling over 25y (5.76e9 MJ as kWh) | activity's table |
| `tap_water` | market group for tap water | 2.9e+09 | kilogram | 2.9e+09 | Tap water — cooling, WUE 1.8 L/kWh over 25y (Zhang's rounded 2.9e9) | activity's table |
| `diesel_generator` | market for diesel, burned in diesel-electric generating set, 10MW | 8.6e+06 | megajoule | 8.6e+06 | Diesel, burned in diesel-electric generating set 10MW — backup gen | activity's table |
| `servers` | market for computer, laptop | 100000 | unit | 100000 | Computer/laptop (ecoinvent proxy for IT servers, incl. refresh cycles) | activity's table |
| `battery` | market for battery, Li-ion, NMC111, rechargeable, prismatic | 20000 | kilogram | 20000 | Battery, Li-ion, rechargeable, prismatic — UPS | activity's table |
| `sodium_hypochlorite` | market for sodium hypochlorite, without water, in 15% solution state | 130000 | kilogram | 130000 | Sodium hypochlorite — cooling water treatment | activity's table |
| `refrigerant_r134a` | market for refrigerant R134a | 450 | kilogram | 450 | Tetrafluoroethane / R134a — cooling-system refrigerant top-up | activity's table |
| `hfc134a_air` | Ethane, 1,1,1,2-tetrafluoro-, HFC-134a | 450 | kilogram | 450 | ADDED — R134a leaked: the 450 kg top-up replaces leakage at 0.9 %/yr (Zhang Table S1: 2,000 kg x 0.009 x 25 y) | ADDED |

## bess — grid battery (Jasper 2026 container, Voß 2025 cell)

Database `battery foreground`; source of the activities' own tables: Jasper et al. 2026 SI (container) / Voß et al. 2025 Table 3 and ESI (cell).

### `bess_synthetic_graphite_1kg` — Synthetic graphite, battery grade, Acheson powder route (Voß 2025)

kilogram, CN; scale ×0.988 (Voß's economic allocation: 98.8 % to graphite, 1.2 % to incinerator heat). Comment: Voß et al. 2025 ESI Table S5, from Carrère et al.'s industrial data: calcination of needle-coke feed, then graphitisation at ~3,000 C on the Chinese grid. ecoinvent 3.9.1's own synthetic graphite models the Acheson BLOCK route, which Voß show underestimates battery-grade graphite. The crucible and p…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `petroleum_coke` | market for petroleum coke | 1.179 | kilogram | 1.16485 | Table S5 calcination: green coke ('needle coke feed') | own locator |
| `heat_gas_small_row` | market for heat, central or small-scale, natural gas | 2 | megajoule | 1.976 | Table S5 calcination: natural gas | own locator |
| `electricity_mv_cn` | market group for electricity, medium voltage | 16 | kilowatt hour | 15.808 | Table S5 graphitisation: electricity, CN | own locator |
| `lorry_euro3_row` | market for transport, freight, lorry 16-32 metric ton, EURO3 | 1 | ton kilometer | 0.988 | Table S5 'Truck China', 1,000 km: upstream, kept | own locator |
| `co2` | Carbon dioxide, fossil | 0.19 | kilogram | 0.18772 | Table S5: direct CO2, calcination (rotary kiln and incinerator) | own locator |
| `co2` | Carbon dioxide, fossil | 0.725 | kilogram | 0.7163 | Table S5: direct CO2, graphitisation | own locator |
| `co2` | Carbon dioxide, fossil | 7.346 | kilogram | 7.25785 | Table S5: crucible production, Carrère 11.9 kg CO2e/kg / 1.62 - a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only | own locator |
| `co2` | Carbon dioxide, fossil | 0.432 | kilogram | 0.426816 | Table S5: packaging media and graphite block, Carrère 0.7 / 1.62 - a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only | own locator |

### `bess_natural_graphite_1kg` — Natural graphite, battery grade (Engels 2022 via Voß 2025)

kilogram, CN. Comment: Voß ESI §3.1.1.2: Engels et al. 2022's 9.62 kg CO2e/kg from a Chinese producer, less the coating step and 25 % of spheronisation = 5.19 kg CO2e/kg, the figure BEFORE transport (the main text's 5.7, Fig. 6 and §4.2.2, is 5.19 plus Voß's three legs). a published carbon footprint, entered as fossil CO2…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `lorry_euro3_row` | market for transport, freight, lorry 16-32 metric ton, EURO3 | 1 | ton kilometer | 1 | §3.1.3 'Truck China', 1,000 km: upstream, kept | own locator |
| `co2` | Carbon dioxide, fossil | 5.19 | kilogram | 5.19 | Voß §3.1.1.2, 5.19 kg CO2e/kg before transport - a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only | own locator |

### `bess_iron_phosphate_0p91kg` — Iron phosphate, LFP precursor (Voß 2025)

kilogram, CN; production amount 0.91. Comment: Voß ESI Table S32, as printed: the inputs make 0.91 kg of FePO4, which is the amount one kg of LFP-C consumes (Table S31).

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `iron_sulfate` | market for iron sulfate | 1 | kilogram | 1 | Table S32: FeSO4 | own locator |
| `phosphoric_acid` | market for phosphoric acid, industrial grade, without water, in 85% solution state | 0.65 | kilogram | 0.65 | Table S32: H3PO4, 85 % | own locator |
| `hydrogen_peroxide` | market for hydrogen peroxide, without water, in 50% solution state | 0.11 | kilogram | 0.11 | Table S32: H2O2, 50 % | own locator |
| `sodium_hydroxide` | market for sodium hydroxide, without water, in 50% solution state | 0.27 | kilogram | 0.27 | Table S32: NaOH, 50 % | own locator |
| `water_softened` | market for water, completely softened | 50 | kilogram | 50 | Table S32: water | own locator |
| `electricity_mv_cn` | market group for electricity, medium voltage | 0.972 | kilowatt hour | 0.972 | Table S32: electricity, CN | own locator |
| `heat_gas_small_row` | market for heat, central or small-scale, natural gas | 8.1 | megajoule | 8.1 | Table S32: natural gas | own locator |

### `bess_lfp_cam_1kg` — LFP cathode active material, carbon coated (Voß 2025)

kilogram, CN. Comment: Voß ESI Table S31, after Quan et al.'s spray-drying and calcination route, with stoichiometric precursors. The in-China lorry leg is kept; Voß's sea and European legs serve their German factory and are not taken.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `lorry_euro3_row` | market for transport, freight, lorry 16-32 metric ton, EURO3 | 1 | ton kilometer | 1 | Table S31 'Truck China', 1,000 km: upstream, kept | own locator |
| `FG:bess_iron_phosphate_0p91kg` | → Iron phosphate, LFP precursor (Voß 2025) | 0.91 | kilogram | 0.91 | Table S31: FePO4 | own locator |
| `lithium_carbonate` | market for lithium carbonate | 0.22 | kilogram | 0.22 | Table S31: Li2CO3 | own locator |
| `glucose` | market for glucose | 0.13 | kilogram | 0.13 | Table S31: glucose (the carbon coating) | own locator |
| `nitrogen_liquid` | market for nitrogen, liquid | 0.21 | kilogram | 0.21 | Table S31: nitrogen, inert atmosphere | own locator |
| `water_deionised` | market for water, deionised | 3.05 | kilogram | 3.05 | Table S31: deionised water | own locator |
| `electricity_mv_cn` | market group for electricity, medium voltage | 0.496 | kilowatt hour | 0.496 | Table S31: electricity, CN | own locator |
| `heat_gas_small_row` | market for heat, central or small-scale, natural gas | 18.72 | megajoule | 18.72 | Table S31: natural gas | own locator |
| `co2` | Carbon dioxide, fossil | 0.17 | kilogram | 0.17 | Table S31: direct CO2 | own locator |

### `bess_sbr_1kg` — Styrene-butadiene rubber binder (Voß 2025)

kilogram, CN. Comment: Voß ESI Table S35, after Chordia et al. The in-China lorry leg is kept; the sea and European legs serve Voß's German factory and are not taken.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `lorry_euro3_row` | market for transport, freight, lorry 16-32 metric ton, EURO3 | 1 | ton kilometer | 1 | Table S35 'Truck China', 1,000 km: upstream, kept | own locator |
| `butadiene` | market for butadiene | 0.757 | kilogram | 0.757 | Table S35 | own locator |
| `styrene` | market for styrene | 0.252 | kilogram | 0.252 | Table S35 | own locator |
| `chemical_organic` | market for chemical, organic | 0.008 | kilogram | 0.008 | Table S35: DDM | own locator |
| `fatty_acid` | market for fatty acid | 0.051 | kilogram | 0.051 | Table S35 | own locator |
| `chemical_inorganic` | market for chemical, inorganic | 3e-06 | kilogram | 3e-06 | Table S35: potassium persulfate | own locator |
| `water_deionised` | market for water, deionised | 27.5 | kilogram | 27.5 | Table S35 | own locator |
| `electricity_mv_cn` | market group for electricity, medium voltage | 0.0004 | kilowatt hour | 0.0004 | Table S35 | own locator |
| `steam_chemical_row` | market for steam, in chemical industry | 0.0055 | kilogram | 0.0055 | Table S35 | own locator |

### `bess_pvdf_1kg` — PVDF binder (Hu et al. via Voß 2025)

kilogram, CN. Comment: Voß ESI §3.1.3.1: Hu et al.'s 60.6 kg CO2e/kg for PVDF made in China. ecoinvent 3.9.1 has no PVDF. a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `co2` | Carbon dioxide, fossil | 60.6 | kilogram | 60.6 | Hu et al., 60.6 kg CO2e/kg - a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only | own locator |

### `bess_separator_1kg` — Battery separator, PE/PP (ecoinvent 3.8 via Voß 2025)

kilogram, CN. Comment: Voß ESI §3.1.3.4 take ecoinvent 3.8's 'battery separator production - CN' at 5.06 kg CO2e/kg, judging 3.9.1's 39.6 'unrealistically high', after Peters et al. 3.9.1 scores 34.4 (market) and 39.5 (CN) here. a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `co2` | Carbon dioxide, fossil | 5.06 | kilogram | 5.06 | ecoinvent 3.8 value, 5.06 kg CO2e/kg - a published carbon footprint, entered as fossil CO2 of its own size: GWP100 only | own locator |

### `bess_cell_housing_1kg` — Prismatic cell housing (Voß 2025)

kilogram, CN. Comment: Voß ESI Table S36, the weight distribution of Fraunhofer FFB's large prismatic cell. The table repeats its first two rows after the material block (ESI p. 27; cap sheet 0.204, busbar copper 0.061/0.062); they are taken once, which is what makes the rows sum to 0.987 kg per kg as printed rather than …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `lorry_euro3_row` | market for transport, freight, lorry 16-32 metric ton, EURO3 | 1 | ton kilometer | 1 | S36 'Truck China', 1,000 km: upstream, kept | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.204 | kilogram | 0.204 | S36 cap metal sheet | own locator |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 0.204 | kilogram | 0.204 | S36 cap metal sheet | own locator |
| `cu_anode` | market for copper, anode | 0.061 | kilogram | 0.061 | S36 busbar anode, copper | own locator |
| `sheet_rolling_cu` | market for sheet rolling, copper | 0.061 | kilogram | 0.061 | S36 busbar anode, copper | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.032 | kilogram | 0.032 | S36 busbar anode, aluminium | own locator |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 0.032 | kilogram | 0.032 | S36 busbar anode, aluminium | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.006 | kilogram | 0.006 | S36 connection terminals | own locator |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 0.006 | kilogram | 0.006 | S36 connection terminals | own locator |
| `pet_bottle` | market for polyethylene terephthalate, granulate, bottle grade | 0.029 | kilogram | 0.029 | S36 isolation busbars | own locator |
| `pet_bottle` | market for polyethylene terephthalate, granulate, bottle grade | 0.013 | kilogram | 0.013 | S36 isolation terminal anode | own locator |
| `pet_bottle` | market for polyethylene terephthalate, granulate, bottle grade | 0.006 | kilogram | 0.006 | S36 isolation terminal cathode | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.006 | kilogram | 0.006 | S36 bursting membrane | own locator |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 0.006 | kilogram | 0.006 | S36 bursting membrane | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.042 | kilogram | 0.042 | S36 terminal anode | own locator |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 0.042 | kilogram | 0.042 | S36 terminal anode | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.045 | kilogram | 0.045 | S36 terminal cathode | own locator |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 0.045 | kilogram | 0.045 | S36 terminal cathode | own locator |
| `pet_bottle` | market for polyethylene terephthalate, granulate, bottle grade | 0.003 | kilogram | 0.003 | S36 sealing rubber | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.003 | kilogram | 0.003 | S36 sealing plate | own locator |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 0.003 | kilogram | 0.003 | S36 sealing plate | own locator |
| `al_wrought` | market for aluminium, wrought alloy | 0.537 | kilogram | 0.537 | S36 housing | own locator |
| `impact_extrusion_al` | market for impact extrusion of aluminium, 1 stroke | 0.537 | kilogram | 0.537 | S36 housing | own locator |

### `bess_lfp_cell_materials_1unit` — LFP/graphite prismatic cell, materials (Voß 2025)

unit, CN. Comment: Voß et al. 2025 Table 3, LFP/graphite: one 383.4 Wh, 2,170.8 g prismatic cell (176.6 Wh/kg), the cell Jasper et al. 2026 put in their container. Materials only - the factory energy is added per kWh in bess_lfp_cell_1kwh_cn / bess_lfp_cell_1kwh_de. Graphite 75% synthetic / 25% natural, Voß's market-s…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_synthetic_graphite_1kg` | → Synthetic graphite, battery grade, Acheson powder route (Voß 2025) | 0.2907 | kilogram | 0.2907 | Table 3 anode active material 387.6 g x 75% synthetic | own locator |
| `FG:bess_natural_graphite_1kg` | → Natural graphite, battery grade (Engels 2022 via Voß 2025) | 0.0969 | kilogram | 0.0969 | Table 3 anode active material 387.6 g x 25% natural | own locator |
| `cmc` | carboxymethyl cellulose production, powder | 0.0081 | kilogram | 0.0081 | Table 3 anode CMC | own locator |
| `FG:bess_sbr_1kg` | → Styrene-butadiene rubber binder (Voß 2025) | 0.0061 | kilogram | 0.0061 | Table 3 anode SBR | own locator |
| `carbon_black` | carbon black production | 0.002 | kilogram | 0.002 | Table 3 anode carbon black | own locator |
| `cu_collector_foil` | copper collector foil production, for Li-ion battery | 0.1649 | kilogram | 0.1649 | Table 3 anode current collector, copper | own locator |
| `FG:bess_lfp_cam_1kg` | → LFP cathode active material, carbon coated (Voß 2025) | 0.726 | kilogram | 0.726 | Table 3 cathode active material, LFP-C | own locator |
| `FG:bess_pvdf_1kg` | → PVDF binder (Hu et al. via Voß 2025) | 0.0151 | kilogram | 0.0151 | Table 3 cathode PVDF | own locator |
| `carbon_black` | carbon black production | 0.0151 | kilogram | 0.0151 | Table 3 cathode carbon black | own locator |
| `al_collector_foil` | aluminium collector foil production, for Li-ion battery | 0.0452 | kilogram | 0.0452 | Table 3 cathode current collector, aluminium | own locator |
| `electrolyte` | electrolyte production, for Li-ion battery | 0.4236 | kilogram | 0.4236 | Table 3 electrolyte | own locator |
| `FG:bess_separator_1kg` | → Battery separator, PE/PP (ecoinvent 3.8 via Voß 2025) | 0.047 | kilogram | 0.047 | Table 3 separator | own locator |
| `FG:bess_cell_housing_1kg` | → Prismatic cell housing (Voß 2025) | 0.33 | kilogram | 0.33 | Table 3 cell housing | own locator |
| `lorry_euro3_row` | market for transport, freight, lorry 16-32 metric ton, EURO3 | 0.721 | ton kilometer | 0.721 | §3.1.3 'Truck China', 1,000 km, on CMC, carbon black, both foils, PVDF, electrolyte and separator | own locator |

### `bess_lfp_cell_1kwh_cn` — LFP/graphite prismatic cell, per kWh, made in CN (Voß 2025)

kilowatt hour, CN. Comment: 2.6082 Voß cells of 383.4 Wh make one kWh of NAMEPLATE cell capacity, plus Degen et al. 2023's gigafactory energy as restated by Jasper §2.4.1: 18 kWh electricity and 19 kWh natural gas per kWh, the gas charged as 68.4 MJ of heat. Factory in CN. Excludes Voß's processing materials (NMP, argon, N2, c…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_lfp_cell_materials_1unit` | → LFP/graphite prismatic cell, materials (Voß 2025) | 2.60824 | unit | 2.60824 | 1000 / 383.4 Wh per cell | activity's table |
| `electricity_mv_cn` | market group for electricity, medium voltage | 18 | kilowatt hour | 18 | cell factory electricity, CN | activity's table |
| `heat_gas_industrial_row` | market for heat, district or industrial, natural gas | 68.4 | megajoule | 68.4 | cell factory gas, CN | activity's table |

### `bess_lfp_cell_1kwh_de` — LFP/graphite prismatic cell, per kWh, made in DE (Voß 2025)

kilowatt hour, DE. Comment: 2.6082 Voß cells of 383.4 Wh make one kWh of NAMEPLATE cell capacity, plus Degen et al. 2023's gigafactory energy as restated by Jasper §2.4.1: 18 kWh electricity and 19 kWh natural gas per kWh, the gas charged as 68.4 MJ of heat. Factory in DE. Excludes Voß's processing materials (NMP, argon, N2, c…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_lfp_cell_materials_1unit` | → LFP/graphite prismatic cell, materials (Voß 2025) | 2.60824 | unit | 2.60824 | 1000 / 383.4 Wh per cell | activity's table |
| `electricity_mv_de` | market for electricity, medium voltage | 18 | kilowatt hour | 18 | cell factory electricity, DE | activity's table |
| `heat_gas_industrial_rer` | market group for heat, district or industrial, natural gas | 68.4 | megajoule | 68.4 | cell factory gas, DE | activity's table |

### `bess_module_47kwh_liquid` — Battery module, 47 kWh, for liquid-cooled container (Jasper 2026)

unit, CN. Comment: Jasper et al. 2026 SI, 'production of battery module for CSS', liquid-cooled: 48 LFP cells in series, module packaging after Baumann et al. (2020) and Ellingsen et al. (2014). The cells are Voß's, made in CN. Ellingsen's busbars are not in the SI and are mapped to their metals (ASSUMED, 50% copper f…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_lfp_cell_1kwh_cn` | → LFP/graphite prismatic cell, per kWh, made in CN (Voß 2025) | 47 | kilowatt hour | 47 | 'LFP based LIB (Voß et al.)', 47000/176.6 kg = 47 kWh | activity's table |
| `al_wrought` | market for aluminium, wrought alloy | 3.1302 | kilogram | 3.1302 | Aluminium endbars (Ellingsen) - ASSUMED wrought Al | ASSUMED |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 3.1302 | kilogram | 3.1302 | Aluminium endbars (Ellingsen) - ASSUMED rolled | ASSUMED |
| `cu_cathode` | market for copper, cathode | 3.32585 | kilogram | 3.32585 | Bimetallic busbars and washers (Ellingsen) - copper share | activity's table |
| `sheet_rolling_cu` | market for sheet rolling, copper | 3.32585 | kilogram | 3.32585 | Bimetallic busbars and washers (Ellingsen) - copper share | activity's table |
| `al_wrought` | market for aluminium, wrought alloy | 3.32585 | kilogram | 3.32585 | Bimetallic busbars and washers (Ellingsen) - aluminium share | activity's table |
| `sheet_rolling_al` | market for sheet rolling, aluminium | 3.32585 | kilogram | 3.32585 | Bimetallic busbars and washers (Ellingsen) - aluminium share | activity's table |
| `cu_cathode` | market for copper, cathode | 0.9586 | kilogram | 0.9586 | Copper end-busbars (Ellingsen) - ASSUMED copper | ASSUMED |
| `sheet_rolling_cu` | market for sheet rolling, copper | 0.9586 | kilogram | 0.9586 | Copper end-busbars (Ellingsen) - ASSUMED rolled | ASSUMED |
| `injection_moulding` | market for injection moulding | 2.7838 | kilogram | 2.7838 | Jasper et al. 2026 SI | own locator |
| `metal_working_factory` | market for metal working factory | 4.58e-10 | unit | 4.58e-10 | Jasper et al. 2026 SI | own locator |
| `mw_steel` | market for metal working, average for steel product manufacturing | 28.4727 | kilogram | 28.4727 | Jasper et al. 2026 SI | own locator |
| `polypropylene` | market for polypropylene, granulate | 2.7838 | kilogram | 2.7838 | Jasper et al. 2026 SI | own locator |
| `pwb_through_hole` | market for printed wiring board, through-hole mounted, unspecified, Pb free | 0.6442 | kilogram | 0.6442 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 28.4727 | kilogram | 28.4727 | Jasper et al. 2026 SI | own locator |
| `lorry_euro5_row` | market for transport, freight, lorry 16-32 metric ton, EURO5 | 3.9857 | ton kilometer | 3.9857 | Jasper et al. 2026 SI, upstream: materials to the module factory | own locator |
| `train_glo` | market group for transport, freight train | 23.9144 | ton kilometer | 23.9144 | Jasper et al. 2026 SI, upstream: materials to the module factory | own locator |

### `bess_rack_housing_1kg` — Battery rack housing, steel, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, 'Rack, 48x43, for stationary battery storage system'. Jasper's upstream material legs kept; no delivery to site.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `metal_working_factory` | market for metal working factory | 4.58e-10 | unit | 4.58e-10 | Jasper et al. 2026 SI | own locator |
| `mw_steel` | market for metal working, average for steel product manufacturing | 1 | kilogram | 1 | Jasper et al. 2026 SI | own locator |
| `powder_coat_steel` | market for powder coat, steel | 0.055 | square meter | 0.055 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 1 | kilogram | 1 | Jasper et al. 2026 SI | own locator |
| `lorry_euro5_row` | market for transport, freight, lorry 16-32 metric ton, EURO5 | 0.100531 | ton kilometer | 0.100531 | Jasper et al. 2026 SI, upstream: materials to the rack factory | own locator |
| `train_glo` | market group for transport, freight train | 0.603185 | ton kilometer | 0.603185 | Jasper et al. 2026 SI, upstream: materials to the rack factory | own locator |

### `bess_rack_liquid_1unit` — Battery rack, liquid-cooled, 8 modules, 376 kWh (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI, 'Battery rack (liquid cooled)'. The HV control box is ecoinvent's electronics for control units, as Jasper name it. Jasper's upstream material legs kept; no delivery to site.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_module_47kwh_liquid` | → Battery module, 47 kWh, for liquid-cooled container (Jasper 2026) | 8 | unit | 8 | Jasper et al. 2026 SI | own locator |
| `cable` | market for cable, unspecified | 17.907 | kilogram | 17.907 | Jasper et al. 2026 SI | own locator |
| `electronics_control` | market for electronics, for control units | 15.5 | kilogram | 15.5 | High voltage control box (electronics for control units) | activity's table |
| `FG:bess_rack_housing_1kg` | → Battery rack housing, steel, per kg (Jasper 2026) | 431.8 | kilogram | 431.8 | Jasper et al. 2026 SI | own locator |
| `lorry_euro6_row` | market for transport, freight, lorry 16-32 metric ton, EURO6 | 0.0962 | ton kilometer | 0.0962 | Jasper et al. 2026 SI, upstream | own locator |
| `train_glo` | market group for transport, freight train | 0.58 | ton kilometer | 0.58 | Jasper et al. 2026 SI, upstream | own locator |

### `bess_cooling_plate_1unit` — Cooling plate in battery module, liquid cooling (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI, 'cooling plate': one AlMg3 plate per module with its rubber seal, the metal worked; 64 per liquid-cooled container (Jasper's num_powersection x num_batterypack; their EoL sheet uses the air-cooled count of 144).

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `al_almg3` | market for aluminium alloy, AlMg3 | 5.2 | kilogram | 5.2 | Jasper et al. 2026 SI | own locator |
| `mw_al` | market for metal working, average for aluminium product manufacturing | 5.2 | kilogram | 5.2 | Jasper et al. 2026 SI | own locator |
| `synthetic_rubber` | market for synthetic rubber | 0.32 | kilogram | 0.32 | Jasper et al. 2026 SI | own locator |

### `bess_compressor_1kg` — Chiller compressor, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, after Catrini et al. (2018).

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `base_oil` | market for base oil | 0.0404 | kilogram | 0.0404 | Jasper et al. 2026 SI | own locator |
| `cu_anode` | market for copper, anode | 0.1442 | kilogram | 0.1442 | Jasper et al. 2026 SI | own locator |
| `mw_cr` | market for metal working, average for chromium steel product manufacturing | 0.8154 | kilogram | 0.8154 | Jasper et al. 2026 SI | own locator |
| `mw_cu` | market for metal working, average for copper product manufacturing | 0.1442 | kilogram | 0.1442 | Jasper et al. 2026 SI | own locator |
| `reinforcing_steel` | market for reinforcing steel | 0.8154 | kilogram | 0.8154 | Jasper et al. 2026 SI | own locator |

### `bess_filter_drier_1kg` — Chiller filter drier, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, 'filter drier' of the 40 kW chiller: a chromium-steel shell holding zeolite desiccant, per kg, after Catrini et al. (2018).

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `mw_cr` | market for metal working, average for chromium steel product manufacturing | 0.5325 | kilogram | 0.5325 | Jasper et al. 2026 SI | own locator |
| `steel_cr` | market for steel, chromium steel 18/8 | 0.5325 | kilogram | 0.5325 | Jasper et al. 2026 SI | own locator |
| `zeolite` | market for zeolite, powder | 0.4675 | kilogram | 0.4675 | Jasper et al. 2026 SI | own locator |

### `bess_pump_1kg` — Coolant pump, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, 'pump' of the liquid cooling unit: cast aluminium, cast iron and copper, each with its metal working, per kg, after Catrini et al. (2018).

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `al_cast` | market for aluminium, cast alloy | 0.4402 | kilogram | 0.4402 | Jasper et al. 2026 SI | own locator |
| `cast_iron` | market for cast iron | 0.4821 | kilogram | 0.4821 | Jasper et al. 2026 SI | own locator |
| `cu_anode` | market for copper, anode | 0.0777 | kilogram | 0.0777 | Jasper et al. 2026 SI | own locator |
| `mw_al` | market for metal working, average for aluminium product manufacturing | 0.4402 | kilogram | 0.4402 | Jasper et al. 2026 SI | own locator |
| `mw_cu` | market for metal working, average for copper product manufacturing | 0.0777 | kilogram | 0.0777 | Jasper et al. 2026 SI | own locator |
| `mw_metal` | market for metal working, average for metal product manufacturing | 0.4821 | kilogram | 0.4821 | Jasper et al. 2026 SI | own locator |

### `bess_secondary_coolant_1kg` — Secondary coolant, 50:50 ethylene glycol and water (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, 'secondary coolant': the glycol-water mix in the cooling loop, 126 kg per container, per kg.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `ethylene_glycol` | market for ethylene glycol | 0.5 | kilogram | 0.5 | Jasper et al. 2026 SI (RoW market in the source, GLO in 3.9.1) | own locator |
| `water_deionised` | market for water, deionised | 0.5 | kilogram | 0.5 | Jasper et al. 2026 SI | own locator |

### `bess_ac_indoor_unit_1kg` — Air conditioner indoor unit, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, from the EPD of a 3.6 kW, 37 kg unit.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `abs_row` | acrylonitrile-butadiene-styrene copolymer production | 0.1158 | kilogram | 0.1158 | Jasper et al. 2026 SI | own locator |
| `al_cast_primary` | aluminium ingot, primary, to aluminium, cast alloy market | 0.0979 | kilogram | 0.0979 | Jasper et al. 2026 SI | own locator |
| `capacitor_electrolyte` | market for capacitor, electrolyte type, > 2cm height | 0.0125 | kilogram | 0.0125 | Jasper et al. 2026 SI | own locator |
| `cu_anode` | market for copper, anode | 0.1392 | kilogram | 0.1392 | Jasper et al. 2026 SI | own locator |
| `electronics_control_row` | electronics production, for control units | 0.0552 | kilogram | 0.0552 | Jasper et al. 2026 SI | own locator |
| `injection_moulding` | market for injection moulding | 0.5654 | kilogram | 0.5654 | Jasper et al. 2026 SI | own locator |
| `mw_al_row` | metal working, average for aluminium product manufacturing | 0.0979 | kilogram | 0.0979 | Jasper et al. 2026 SI | own locator |
| `mw_cu_row` | metal working, average for copper product manufacturing | 0.1392 | kilogram | 0.1392 | Jasper et al. 2026 SI | own locator |
| `mw_steel_row` | metal working, average for steel product manufacturing | 0.1298 | kilogram | 0.1298 | Jasper et al. 2026 SI | own locator |
| `plastic_recycled_in` | market for plastic granulate, unspecified, recycled | 0.0097 | kilogram | 0.0097 | Jasper et al. 2026 SI | own locator |
| `polyester_resin_row` | polyester resin production, unsaturated | 0.0656 | kilogram | 0.0656 | Jasper et al. 2026 SI | own locator |
| `hdpe_row` | polyethylene production, high density, granulate | 0.0662 | kilogram | 0.0662 | Jasper et al. 2026 SI | own locator |
| `polypropylene_row` | polypropylene production, granulate | 0.0406 | kilogram | 0.0406 | Jasper et al. 2026 SI | own locator |
| `hips_row` | polystyrene production, high impact | 0.1668 | kilogram | 0.1668 | Jasper et al. 2026 SI | own locator |
| `pu_flexible_row` | market for polyurethane, flexible foam | 0.0501 | kilogram | 0.0501 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 0.1298 | kilogram | 0.1298 | Jasper et al. 2026 SI | own locator |
| `san_row` | styrene-acrylonitrile copolymer production | 0.0505 | kilogram | 0.0505 | Jasper et al. 2026 SI | own locator |

### `bess_ac_outdoor_unit_1kg` — Air conditioner outdoor unit, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, from the EPD of a 3.6 kW, 37 kg unit.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `al_cast_primary` | aluminium ingot, primary, to aluminium, cast alloy market | 0.0648 | kilogram | 0.0648 | Jasper et al. 2026 SI | own locator |
| `capacitor_electrolyte` | market for capacitor, electrolyte type, > 2cm height | 0.0259 | kilogram | 0.0259 | Jasper et al. 2026 SI | own locator |
| `cast_iron_row` | cast iron production | 0.0523 | kilogram | 0.0523 | Jasper et al. 2026 SI | own locator |
| `cu_anode` | market for copper, anode | 0.206 | kilogram | 0.206 | Jasper et al. 2026 SI | own locator |
| `electronics_control_row` | electronics production, for control units | 0.0301 | kilogram | 0.0301 | Jasper et al. 2026 SI | own locator |
| `inductor_choke` | market for inductor, ring core choke type | 0.0829 | kilogram | 0.0829 | Jasper et al. 2026 SI | own locator |
| `injection_moulding_row` | injection moulding | 0.0645 | kilogram | 0.0645 | Jasper et al. 2026 SI | own locator |
| `mw_al_row` | metal working, average for aluminium product manufacturing | 0.0648 | kilogram | 0.0648 | Jasper et al. 2026 SI | own locator |
| `mw_cu_row` | metal working, average for copper product manufacturing | 0.206 | kilogram | 0.206 | Jasper et al. 2026 SI | own locator |
| `mw_metal_row` | metal working, average for metal product manufacturing | 0.0523 | kilogram | 0.0523 | Jasper et al. 2026 SI | own locator |
| `mw_steel_row` | metal working, average for steel product manufacturing | 0.4736 | kilogram | 0.4736 | Jasper et al. 2026 SI | own locator |
| `plastic_recycled_in` | market for plastic granulate, unspecified, recycled | 0.0101 | kilogram | 0.0101 | Jasper et al. 2026 SI | own locator |
| `polypropylene_row` | polypropylene production, granulate | 0.0188 | kilogram | 0.0188 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 0.4736 | kilogram | 0.4736 | Jasper et al. 2026 SI | own locator |
| `san_row` | styrene-acrylonitrile copolymer production | 0.0147 | kilogram | 0.0147 | Jasper et al. 2026 SI | own locator |
| `r134a_row` | refrigerant R134a production | 0.021 | kilogram | 0.021 | Jasper et al. 2026 SI | own locator |

### `bess_air_conditioner_1kg` — Air conditioner, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, 'air conditioner': the 3.6 kW split unit for the balance-of-system cabinet, 27 % indoor and 73 % outdoor unit by mass, per kg.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_ac_indoor_unit_1kg` | → Air conditioner indoor unit, per kg (Jasper 2026) | 0.27 | kilogram | 0.27 | Jasper et al. 2026 SI | own locator |
| `FG:bess_ac_outdoor_unit_1kg` | → Air conditioner outdoor unit, per kg (Jasper 2026) | 0.73 | kilogram | 0.73 | Jasper et al. 2026 SI | own locator |

### `bess_liquid_cooling_unit_1unit` — Liquid cooling unit, 40 kW chiller (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI: condenser, evaporator, compressor, pump and PTC heater, after Catrini et al. (2018) scaled to 40 kW, plus three 5 kW auxiliary heaters. R134a is the charge, not a leak.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `aux_heater_5kw` | market for auxiliary heating unit, electric, 5kW | 3 | unit | 3 | Jasper et al. 2026 SI | own locator |
| `brass` | market for brass | 0.4 | kilogram | 0.4 | Jasper et al. 2026 SI | own locator |
| `FG:bess_compressor_1kg` | → Chiller compressor, per kg (Jasper 2026) | 44.36 | kilogram | 44.36 | Jasper et al. 2026 SI | own locator |
| `cu_anode` | market for copper, anode | 7.44 | kilogram | 7.44 | Jasper et al. 2026 SI | own locator |
| `FG:bess_filter_drier_1kg` | → Chiller filter drier, per kg (Jasper 2026) | 0.73 | kilogram | 0.73 | Jasper et al. 2026 SI | own locator |
| `mw_cr` | market for metal working, average for chromium steel product manufacturing | 153.18 | kilogram | 153.18 | Jasper et al. 2026 SI | own locator |
| `mw_cu` | market for metal working, average for copper product manufacturing | 7.44 | kilogram | 7.44 | Jasper et al. 2026 SI | own locator |
| `mw_metal` | market for metal working, average for metal product manufacturing | 0.4 | kilogram | 0.4 | Jasper et al. 2026 SI | own locator |
| `FG:bess_pump_1kg` | → Coolant pump, per kg (Jasper 2026) | 29.96 | kilogram | 29.96 | Jasper et al. 2026 SI | own locator |
| `steel_cr` | market for steel, chromium steel 18/8 | 37.83 | kilogram | 37.83 | Jasper et al. 2026 SI | own locator |
| `steel_cr` | market for steel, chromium steel 18/8 | 34.46 | kilogram | 34.46 | Jasper et al. 2026 SI | own locator |
| `steel_cr_hr` | market for steel, chromium steel 18/8, hot rolled | 80.89 | kilogram | 80.89 | Jasper et al. 2026 SI | own locator |
| `synthetic_rubber` | market for synthetic rubber | 0.068 | kilogram | 0.068 | Jasper et al. 2026 SI | own locator |
| `r134a` | market for refrigerant R134a | 9 | kilogram | 9 | Jasper et al. 2026 SI ('market for tetrafluoroethane, R134a' in 3.11) | own locator |

### `bess_liquid_cooling_system_1unit` — Liquid cooling system for 20 ft container (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI: one cooling plate per module, nitrile hoses, steel pipework, the 40 kW chiller, 126 kg of coolant, and one 3.6 kW air conditioner for the balance-of-system cabinet. Jasper's delivery-to-site rows excluded.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_air_conditioner_1kg` | → Air conditioner, per kg (Jasper 2026) | 37 | kilogram | 37 | Jasper et al. 2026 SI | own locator |
| `cable_connector` | market for cable, connector for computer, without plugs | 8 | meter | 8 | Jasper et al. 2026 SI | own locator |
| `FG:bess_cooling_plate_1unit` | → Cooling plate in battery module, liquid cooling (Jasper 2026) | 64 | unit | 64 | Jasper et al. 2026 SI - num_powersection x num_batterypack | own locator |
| `drawing_pipe_steel` | market for drawing of pipe, steel | 138.92 | kilogram | 138.92 | Jasper et al. 2026 SI | own locator |
| `FG:bess_liquid_cooling_unit_1unit` | → Liquid cooling unit, 40 kW chiller (Jasper 2026) | 1 | unit | 1 | Jasper et al. 2026 SI | own locator |
| `nitrile` | market for nitrile-compound | 48 | kilogram | 48 | Jasper et al. 2026 SI - 0.75 kg x 64 modules | own locator |
| `hdpe` | market for polyethylene, high density, granulate | 1.37 | kilogram | 1.37 | Jasper et al. 2026 SI | own locator |
| `FG:bess_secondary_coolant_1kg` | → Secondary coolant, 50:50 ethylene glycol and water (Jasper 2026) | 126.43 | kilogram | 126.43 | Jasper et al. 2026 SI | own locator |
| `steel_cr` | market for steel, chromium steel 18/8 | 138.92 | kilogram | 138.92 | Jasper et al. 2026 SI | own locator |

### `bess_fire_damper_1unit` — Fire damper (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI, 'fire damper': a galvanised steel damper with its actuator motor (ecoinvent's scooter motor, as Jasper name it), two per container.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `chemical_inorganic` | market for chemical, inorganic | 0.9 | kilogram | 0.9 | Jasper et al. 2026 SI | own locator |
| `e_motor_scooter` | market for electric motor, for electric scooter | 1.2 | kilogram | 1.2 | Jasper et al. 2026 SI | own locator |
| `gfrp_pa` | market for glass fibre reinforced plastic, polyamide, injection moulded | 0.09 | kilogram | 0.09 | Jasper et al. 2026 SI | own locator |
| `injection_moulding` | market for injection moulding | 0.09 | kilogram | 0.09 | Jasper et al. 2026 SI | own locator |
| `plastic_recycled_in` | market for plastic granulate, unspecified, recycled | 0.09 | kilogram | 0.09 | Jasper et al. 2026 SI | own locator |
| `steel_cr` | market for steel, chromium steel 18/8 | 0.06 | kilogram | 0.06 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 0.12 | kilogram | 0.12 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed_hr` | market for steel, low-alloyed, hot rolled | 4.14 | kilogram | 4.14 | Jasper et al. 2026 SI | own locator |
| `synthetic_rubber` | market for synthetic rubber | 0.02 | kilogram | 0.02 | Jasper et al. 2026 SI | own locator |
| `zinc_coat` | market for zinc coat, coils | 0.5 | square meter | 0.5 | Jasper et al. 2026 SI | own locator |

### `bess_container_20ft_1unit` — 20 ft battery container, fire-lined (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI: ecoinvent's 20 ft intermodal container lined with cement board, OSB and flame-retardant PU after McKinnon et al. (2022), with two fire dampers. ecoinvent 3.9.1's container scores ~2.9 t CO2e; Jasper's container line on 3.11 is ~3x this inventory's. Jasper's delivery-to-site ro…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_fire_damper_1unit` | → Fire damper (Jasper 2026) | 2 | unit | 2 | Jasper et al. 2026 SI | own locator |
| `gypsum_board` | market for gypsum plasterboard | 664.66 | kilogram | 664.66 | Jasper et al. 2026 SI | own locator |
| `iso_container_20ft` | market for intermodal shipping container, 20-foot | 1 | unit | 1 | Jasper et al. 2026 SI | own locator |
| `osb` | market for oriented strand board | 0.76 | cubic meter | 0.76 | Jasper et al. 2026 SI | own locator |
| `plywood` | market for plywood | 0.14 | cubic meter | 0.14 | Jasper et al. 2026 SI | own locator |
| `pu_flexible_fr` | market for polyurethane, flexible foam, flame retardant | 2.5 | kilogram | 2.5 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed_hr` | market for steel, low-alloyed, hot rolled | 5 | kilogram | 5 | Jasper et al. 2026 SI | own locator |
| `wood_wool_board` | market for wood wool boards, cement bonded | 0.19 | cubic meter | 0.19 | Jasper et al. 2026 SI | own locator |
| `zinc_coat` | market for zinc coat, coils | 3.18 | square meter | 3.18 | Jasper et al. 2026 SI | own locator |
| `concrete_block_de` | concrete block production | 43900 | kilogram | 43900 | Jasper et al. 2026 SI, 'concrete block' 43.9 t on the CSS (liquid cooled) | own locator |

### `bess_hfc227ea_1kg` — Heptafluoropropane (HFC-227ea) fire suppressant, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI. The 0.1 kg of tetrafluoroethylene is the source's avoided co-product and is kept as it is printed, the way SMR keeps its avoided electricity. The suppressant is the charge, not a release - nothing is emitted here.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `electricity_mv_glo` | market group for electricity, medium voltage | 5 | kilowatt hour | 5 | Jasper et al. 2026 SI | own locator |
| `steam_heat_row` | steam production, as energy carrier, in chemical industry | 20 | megajoule | 20 | Jasper et al. 2026 SI | own locator |
| `hydrogen_fluoride` | market for hydrogen fluoride | 0.131 | kilogram | 0.131 | Jasper et al. 2026 SI | own locator |
| `tetrafluoroethylene` | market for tetrafluoroethylene | 0.981 | kilogram | 0.981 | Jasper et al. 2026 SI | own locator |
| `tetrafluoroethylene` | market for tetrafluoroethylene | -0.1 | kilogram | -0.1 | Jasper et al. 2026 SI - avoided product | own locator |
| `hazardous_waste_incineration` | market for hazardous waste, for incineration | -0.02 | kilogram | -0.02 | Jasper et al. 2026 SI - production waste sent to treatment | own locator |

### `bess_extinguisher_tank_1kg` — Fire extinguisher tank, charged, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, 'tank' of the suppression system: 70 % HFC-227ea charge, 30 % steel cylinder, per kg; 21 kg per container.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_hfc227ea_1kg` | → Heptafluoropropane (HFC-227ea) fire suppressant, per kg (Jasper 2026) | 0.7 | kilogram | 0.7 | Jasper et al. 2026 SI | own locator |
| `steel_unalloyed` | market for steel, unalloyed | 0.3 | kilogram | 0.3 | Jasper et al. 2026 SI | own locator |

### `bess_suppression_panel_1kg` — Fire suppression panel, per kg (Jasper 2026)

kilogram, GLO. Comment: Jasper et al. 2026 SI, 'control panel' of the suppression system: ABS housing, cable, polycarbonate and a surface-mounted printed wiring board, per kg; 2.5 kg per container.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `abs` | market for acrylonitrile-butadiene-styrene copolymer | 0.5472 | kilogram | 0.5472 | Jasper et al. 2026 SI | own locator |
| `cable` | market for cable, unspecified | 0.088 | kilogram | 0.088 | Jasper et al. 2026 SI | own locator |
| `polycarbonate` | market for polycarbonate | 0.1159 | kilogram | 0.1159 | Jasper et al. 2026 SI (RoW market in the source, GLO in 3.9.1) | own locator |
| `pwb_surface` | market for printed wiring board, surface mounted, unspecified, Pb free | 0.2488 | kilogram | 0.2488 | Jasper et al. 2026 SI | own locator |

### `bess_fire_suppression_1unit` — Fire suppression system for 20 ft container (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI. Jasper's delivery-to-site rows excluded.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_extinguisher_tank_1kg` | → Fire extinguisher tank, charged, per kg (Jasper 2026) | 21 | kilogram | 21 | Jasper et al. 2026 SI | own locator |
| `FG:bess_suppression_panel_1kg` | → Fire suppression panel, per kg (Jasper 2026) | 2.5 | kilogram | 2.5 | Jasper et al. 2026 SI | own locator |
| `mw_steel` | market for metal working, average for steel product manufacturing | 30 | kilogram | 30 | Jasper et al. 2026 SI | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 30 | kilogram | 30 | Jasper et al. 2026 SI | own locator |

### `bess_dc_block_liquid_1unit` — Battery DC block, liquid-cooled LFP container, 3,008 kWh (Jasper 2026)

unit, GLO. Comment: Jasper et al. 2026 SI, 'CSS (liquid cooled)': 8 racks of 8 modules, 3,008 kWh nameplate, 1,600 kW. The BESS controller has no inventory in the SI and is charged as electronics for control units (ASSUMED). EXCLUDES, from Jasper's own CSS: the 800 kg power conversion system (battery.py charges the pow…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_rack_liquid_1unit` | → Battery rack, liquid-cooled, 8 modules, 376 kWh (Jasper 2026) | 8 | unit | 8 | Jasper et al. 2026 SI | own locator |
| `electronics_control` | market for electronics, for control units | 30 | kilogram | 30 | ASSUMED - BESS controller as electronics for control units; the SI carries no inventory (Jasper 2022's HSS controller, their ref. 12, would give one, ~28 % lower per kg) | ASSUMED |
| `FG:bess_container_20ft_1unit` | → 20 ft battery container, fire-lined (Jasper 2026) | 1 | unit | 1 | Jasper et al. 2026 SI | own locator |
| `FG:bess_fire_suppression_1unit` | → Fire suppression system for 20 ft container (Jasper 2026) | 1 | unit | 1 | Jasper et al. 2026 SI | own locator |
| `FG:bess_liquid_cooling_system_1unit` | → Liquid cooling system for 20 ft container (Jasper 2026) | 1 | unit | 1 | Jasper et al. 2026 SI | own locator |

### `bess_dc_block_per_kwh` — Battery DC block, liquid-cooled LFP, per kWh nameplate (Jasper 2026 / Voß 2025)

kilowatt hour, GLO. Comment: One kWh of NAMEPLATE cell capacity in Jasper's liquid-cooled container: 1/3,008 of the DC block. This is what optimisation/battery.py scores for the energy term, and it divides by battery.USABLE_FRACTION because cap_batt_e is the energy the battery can swing, not the cells it holds.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:bess_dc_block_liquid_1unit` | → Battery DC block, liquid-cooled LFP container, 3,008 kWh (Jasper 2026) | 0.000332447 | unit | 0.000332447 | 1 / 3,008 kWh | activity's table |

## fuel_cell — PEM fuel cell (Babatunde 2024 stack, Usai 2021 BoP)

Database `fuel cell foreground`; source of the activities' own tables: Babatunde 2024 Table S1 / Usai 2021 SI Table 1 / Gramc 2025.

### `pemfc_stack_1kw_babatunde` — Fuel cell stack production, PEM, 1 kW (Babatunde et al. 2024)

unit, GLO; scale ×0.939303117 ((FC_KW_SCALE x FC_S1_SCALE)). Comment: Cradle-to-gate manufacture of one 1 kW PEM fuel cell stack. Babatunde et al. 2024, Hydrogen 5(2), 352-373, supplementary Table S1 (which documents the ecoinvent 3.7.1 dataset 'fuel cell production, stack polymer electrolyte membrane, 2kW electrical, future'). Amounts as printed in Table S1, scaled b…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `activated_carbon` | market for activated carbon, granular | 0.0008 | kilogram | 0.000751442 | Activated carbon, granular | activity's table |
| `aluminium_wrought` | market for aluminium, wrought alloy | 0.3 | kilogram | 0.281791 | Aluminium, wrought alloy — end plates / housing | activity's table |
| `building_hall` | market for building, hall, steel construction | 0.00022 | square meter | 0.000206647 | Building, hall, steel construction — factory infrastructure | activity's table |
| `building_multi` | market for building, multi-storey | 0.0013 | cubic meter | 0.00122109 | Building, multi-storey — factory infrastructure | activity's table |
| `electricity_mv` | market group for electricity, medium voltage | 16.9 | kilowatt hour | 15.8742 | Electricity, medium voltage — stack manufacturing | activity's table |
| `glass_fibre` | market for glass fibre | 0.1 | kilogram | 0.0939303 | Glass fibre | activity's table |
| `graphite` | market for graphite | 4.5 | kilogram | 4.22686 | Graphite — bipolar plates | activity's table |
| `heat_natural_gas` | market group for heat, district or industrial, natural gas | 22.3 | megajoule | 20.9465 | Heat, district or industrial, natural gas — stack manufacturing | activity's table |
| `isopropanol` | market for isopropanol | 0.0095 | kilogram | 0.00892338 | Isopropanol — electrode ink solvent | activity's table |
| `phenolic_resin` | market for phenolic resin | 1.1 | kilogram | 1.03323 | Phenolic resin — bipolar plate binder | activity's table |
| `platinum` | market for platinum | 0.00075 | kilogram | 0.000704477 | Platinum — anode + cathode catalyst | activity's table |
| `steel_chromium_188` | market for steel, chromium steel 18/8, hot rolled | 0.1 | kilogram | 0.0939303 | Steel, chromium steel 18/8, hot rolled — tie rods / current collectors | activity's table |
| `tetrafluoroethylene` | market for tetrafluoroethylene | 0.052 | kilogram | 0.0488438 | Tetrafluoroethylene — PFSA (Nafion) membrane precursor | activity's table |
| `water_deionised` | market for water, deionised | 0.006 | kilogram | 0.00563582 | Water, deionised | activity's table |
| `waste_plastic` | market for waste plastic, industrial electronics | -6.6 | kilogram | -6.1994 | Waste plastic, industrial electronics — to treatment | activity's table |
| `waste_pvf` | market for waste polyvinylfluoride | -0.052 | kilogram | -0.0488438 | Waste polyvinylfluoride — to treatment | activity's table |
| `propanol_air` | Propanol | 0.0095 | kilogram | 0.00892338 | Propanol to air — the isopropanol input, evaporated | activity's table |
| `water_air` | Water | 9e-07 | cubic meter | 8.45373e-07 | Water to air | activity's table |
| `water_water` | Water | 5.1e-06 | cubic meter | 4.79045e-06 | Water to water | activity's table |
| `occupation_industrial` | Occupation, industrial area | 0.0395 | square meter-year | 0.0371025 | Occupation, industrial area | activity's table |
| `transformation_from` | Transformation, from unspecified | 0.0008 | square meter | 0.000751442 | Transformation, from unspecified | activity's table |
| `transformation_to` | Transformation, to industrial area | 0.0008 | square meter | 0.000751442 | Transformation, to industrial area | activity's table |

### `pemfc_stack_1kw_gramc` — Fuel cell stack production, PEM, 1 kW (Gramc et al. 2025, 48 kW automotive)

unit, GLO; scale ×0.0208333333 ((per 48 kWe stack -> per kW)). Comment: 1 kW of the 48 kWe reference stack in Gramc et al. 2025 (IJHE 104:623, Table 3), amounts as printed per stack x 1/48. Cradle-to-gate; no end-of-life, no recycling credit. Sensitivity basis for the Babatunde stack.

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `platinum` | market for platinum | 0.026 | kilogram | 0.000541667 | Pt, virgin - 26 g, 0.465 mg/cm2 | activity's table |
| `carbon_black` | market for carbon black | 0.039 | kilogram | 0.0008125 | Carbon black - catalyst support | activity's table |
| `tetrafluoroethylene` | market for tetrafluoroethylene | 0.144 | kilogram | 0.003 | PFSA ionomer - Nafion precursor proxy | activity's table |
| `water_deionised` | market for water, deionised | 0.49 | kilogram | 0.0102083 | Water - ink | activity's table |
| `isopropanol` | market for isopropanol | 0.22 | kilogram | 0.00458333 | Alcohol - ink solvent | activity's table |
| `pet_amorphous` | market for polyethylene terephthalate, granulate, amorphous | 1.82 | kilogram | 0.0379167 | PEN/PET subgasket film | activity's table |
| `bop_extrusion_film` | market for extrusion, plastic film | 1.82 | kilogram | 0.0379167 | Subgasket film extrusion | activity's table |
| `cfrp_proxy` | market for carbon fibre reinforced plastic, injection moulded | 1.249 | kilogram | 0.0260208 | Carbon cloth GDL - CFRP proxy | activity's table |
| `steel_chromium_188` | market for steel, chromium steel 18/8, hot rolled | 21.623 | kilogram | 0.450479 | Bipolar plates, stainless steel | activity's table |
| `silicone_rer` | market for silicone product | 1.265 | kilogram | 0.0263542 | Gaskets, silicone | activity's table |
| `grtp` | market for glass fibre reinforced plastic, polyamide, injection moulded | 3.8 | kilogram | 0.0791667 | Endplates, glass-fibre-reinforced thermoplastic | activity's table |
| `copper_cathode` | market for copper, cathode | 0.95 | kilogram | 0.0197917 | Current collectors, copper | activity's table |
| `steel_chromium_188` | market for steel, chromium steel 18/8, hot rolled | 0.852 | kilogram | 0.01775 | Connecting components, chromium steel | activity's table |
| `steel_unalloyed` | market for steel, unalloyed | 2.82 | kilogram | 0.05875 | Connecting components, steel | activity's table |
| `electricity_mv_rer` | market group for electricity, medium voltage | 410 | kilowatt hour | 8.54167 | Stack production, European grid mix | activity's table |
| `propanol_air` | Propanol | 0.22 | kilogram | 0.00458333 | ink alcohol, evaporated | activity's table |

### `pemfc_bop_stationary_1kw` — Fuel cell balance of plant, stationary, hydrogen-fed, per kW

unit, GLO. Comment: Everything a hydrogen-fed PEM fuel cell needs besides its stack, for 1 kW net. Process loops from Usai et al. 2021 (J Cleaner Prod 280:125086) SI Table 1, an 80 kW H2 system, per kW net, each line on the ecoinvent process Usai name: air management (compression-expansion motor, filter, ducting, mass-…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `steel_chromium_188` | market for steel, chromium steel 18/8, hot rolled | 0.02 | kilogram | 0.02 | Usai et al. 2021 SI Table 1, per kW net: compression-expansion motor, chromium steel | own locator |
| `bop_al_cast` | market for aluminium, cast alloy | 0.04 | kilogram | 0.04 | Usai et al. 2021 SI Table 1, per kW net: compression-expansion motor, aluminium | own locator |
| `bop_steel_la_hr` | market for steel, low-alloyed, hot rolled | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: compression-expansion motor, low-alloyed steel | own locator |
| `bop_magnet` | permanent magnet production, for electric motor | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: compression-expansion motor, permanent magnet | own locator |
| `bop_air_filter` | market for air filter, in exhaust air valve | 0.013 | unit | 0.013 | Usai et al. 2021 SI Table 1, per kW net: air filter | own locator |
| `tetrafluoroethylene` | market for tetrafluoroethylene | 0.001 | kilogram | 0.001 | Usai et al. 2021 SI Table 1, per kW net: air ducting | own locator |
| `bop_extrusion_pipes` | market for extrusion, plastic pipes | 0.03 | kilogram | 0.03 | Usai et al. 2021 SI Table 1, per kW net: air ducting, plastic pipes | own locator |
| `bop_electronics` | market for electronics, for control units | 0.004 | kilogram | 0.004 | Usai et al. 2021 SI Table 1, per kW net: mass flow sensor | own locator |
| `bop_pps` | market for polyphenylene sulfide | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: humidifier housing | own locator |
| `bop_so3` | market for sulfur trioxide | 0 | kilogram | 0 | Usai et al. 2021 SI Table 1, per kW net: Nafion tubes, sulfur trioxide (printed 0.00) | own locator |
| `tetrafluoroethylene` | market for tetrafluoroethylene | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: Nafion tubes | own locator |
| `bop_extrusion_film` | market for extrusion, plastic film | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: Nafion tubes, extrusion | own locator |
| `aluminium_wrought` | market for aluminium, wrought alloy | 0.08825 | kilogram | 0.08825 | Usai et al. 2021 SI Table 1, per kW net: air pre-cooler | own locator |
| `bop_pu_rigid` | market for polyurethane, rigid foam | 0.019 | kilogram | 0.019 | Usai et al. 2021 SI Table 1, per kW net: humidifier honeycomb, proxy for cordierite | own locator |
| `bop_nylon6` | market for nylon 6 | 0.03 | kilogram | 0.03 | Usai et al. 2021 SI Table 1, per kW net: demister | own locator |
| `bop_hdpe` | market for polyethylene, high density, granulate | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: fan | own locator |
| `bop_pump_40w` | market for pump, 40W | 0.0375 | unit | 0.0375 | Usai et al. 2021 SI Table 1, per kW net: coolant pumps, printed '3' - per system, so / 80 kW | own locator |
| `bop_al_cast` | market for aluminium, cast alloy | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: radiators | own locator |
| `bop_ethylene_glycol` | market for ethylene glycol | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: antifreeze | own locator |
| `bop_steel_la_hr` | market for steel, low-alloyed, hot rolled | 0.06 | kilogram | 0.06 | Usai et al. 2021 SI Table 1, per kW net: hydrogen blower | own locator |
| `steel_chromium_188` | market for steel, chromium steel 18/8, hot rolled | 0.02 | kilogram | 0.02 | Usai et al. 2021 SI Table 1, per kW net: hydrogen blower | own locator |
| `aluminium_wrought` | market for aluminium, wrought alloy | 0.03 | kilogram | 0.03 | Usai et al. 2021 SI Table 1, per kW net: blower, ejectors, pipes | own locator |
| `bop_electronics` | market for electronics, for control units | 0.03 | kilogram | 0.03 | Usai et al. 2021 SI Table 1, per kW net: controller | own locator |
| `bop_cable` | market for cable, three-conductor cable | 0.2 | meter | 0.2 | Usai et al. 2021 SI Table 1, per kW net: wiring, printed '16 m' - per system (Miotti), so / 80 kW | own locator |
| `aluminium_wrought` | market for aluminium, wrought alloy | 0.1 | kilogram | 0.1 | Usai et al. 2021 SI Table 1, per kW net: mounting and belly pan - the module frame here | own locator |
| `bop_steel_la_hr` | market for steel, low-alloyed, hot rolled | 0.013 | kilogram | 0.013 | Usai et al. 2021 SI Table 1, per kW net: fasteners | own locator |
| `inverter_500kw` | market for inverter, 500kW | 0.002 | unit | 0.002 | Power conversion to AC: ecoinvent's 500 kW inverter, per kW | activity's table |
| `FG:bess_container_20ft_1unit` | → bess_container_20ft_1unit | 0.001 | unit | 0.001 | Enclosure: the battery's fire-lined 20 ft container (Jasper 2026), one per 1,000 kW - ASSUMED | ASSUMED |

### `pemfc_service_stationary_1kw` — Fuel cell service, stationary, hydrogen-fed, per kW

unit, GLO. Comment: One service of 1 kW of a hydrogen-fed PEM fuel cell: the air filter and the antifreeze replaced, in Usai et al. 2021's own amounts. Battelle 2016 lists these, with a de-ionisation polisher whose resin no source quantifies, as the recurring items of an H2 backup unit. No reformer catalyst, no platinu…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `bop_air_filter` | market for air filter, in exhaust air valve | 0.013 | unit | 0.013 | Usai et al. 2021 SI Table 1, per kW net: air filter, replaced | own locator |
| `bop_ethylene_glycol` | market for ethylene glycol | 0.01 | kilogram | 0.01 | Usai et al. 2021 SI Table 1, per kW net: antifreeze, replaced | own locator |

### `pemfc_op_1kwh_h2` — Electricity, low voltage, from PEM fuel cell (hydrogen)

kilowatt hour, GB. Comment: 1 kWh net AC from a 1 kW hydrogen-fed PEMFC system. Hydrogen 0.06316 kg/kWh = 1/(eta 0.475 x LHV 33.33 kWh/kg), where eta is a NET AC efficiency (0.50 at beginning of life x 0.95 for degradation to a 10% cell-voltage end-of-life criterion), so parasitic loads are inside it. Stack (Babatunde et al. 2…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `FG:pem_op_gerloff_1kg_h2` | → pem_op_gerloff_1kg_h2 | 0.0631642 | kilogram | 0.0631642 | Hydrogen — 1 / (eta 0.475 x LHV 33.33 kWh/kg) | activity's table |
| `FG:pemfc_stack_1kw_babatunde` | → Fuel cell stack production, PEM, 1 kW (Babatunde et al. 2024) | 3.33333e-05 | unit | 3.33333e-05 | Stack (Babatunde et al. 2024) over 30,000 h | activity's table |
| `FG:pemfc_bop_stationary_1kw` | → Fuel cell balance of plant, stationary, hydrogen-fed, per kW | 1.25e-05 | unit | 1.25e-05 | Balance of plant over 80,000 h | activity's table |
| `FG:pemfc_service_stationary_1kw` | → Fuel cell service, stationary, hydrogen-fed, per kW | 0.000125 | unit | 0.000125 | One service every 8,000 h | activity's table |

## h2_tank — hydrogen tank (Gandiglio 2022)

Database `hydrogen storage foreground`; source of the activities' own tables: Gandiglio et al. 2022 Table 5.

### `h2_tank_steel_1kg_capacity` — Hydrogen storage tank, steel vessel, per kg capacity (gandiglio_28bar)

kilogram, GLO. Comment: One kg of hydrogen storage capacity: Gandiglio et al. 2022 Table 5's vessel (15,652 kg chromium steel 18/8, 21.6 m3, 28 bar, 50.0 kg of H2) per kg stored, the forming of that steel (ADDED), and a frame and reinforced pad from the vessel's geometry (ASSUMED). Design 'gandiglio_28bar': 312.8 kg steel …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `steel_chromium_188` | market for steel, chromium steel 18/8 | 312.764 | kilogram | 312.764 | Gandiglio Table 5 — vessel steel, gandiglio_28bar, 28 bar | own locator |
| `sheet_rolling_cr_steel` | market for sheet rolling, chromium steel | 312.764 | kilogram | 312.764 | ADDED — forming of the shell: sheet rolling, chromium steel, on the shell mass (22 Oct 2026) | ADDED |
| `steel_low_alloyed_hr` | market for steel, low-alloyed, hot rolled | 31.2764 | kilogram | 31.2764 | ASSUMED — saddles and frame, 10% of the shell mass | ASSUMED |
| `concrete_normal` | concrete, all types to generic market for concrete, normal strength | 0.237589 | cubic meter | 0.237589 | ASSUMED — pad, 0.5 m slab with 0.5 m clearance round the vessel | ASSUMED |
| `reinforcing_steel` | market for reinforcing steel | 23.7589 | kilogram | 23.7589 | ASSUMED — pad reinforcement, 100 kg per m3 of concrete | ASSUMED |

## stepup_transformers — power transformers (Leng 2026 wind + grid intake, IEA PVPS 2026 solar, Jasper 2026 container step-up)

Database `transformer foreground`; source of the activities' own tables: Leng 2026 Table S1/S3 / IEA PVPS Table 49–50 / Jasper 2026 / Smith A15.

### `wind_turbine_stepup_per_mw` — Wind turbine step-up transformers, per MW of wind connected

megawatt, GLO. Comment: The transformers at the foot of each turbine tower, which step 690 V (LOW, <1 kV) up to the site collection voltage so the data centre can draw at MEDIUM voltage (1-24 kV). One unit per TURBINE, not one per farm. Not optional: 100 MW at 690 V is 83,674 A. ecoinvent 3.9.1 has no power transformer at …

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `steel_low_alloyed` | market for steel, low-alloyed | 1635 | kilogram | 1635 | steel in the turbine step-up transformers — Leng Table S1, 163,500 kg per 100 MW farm | activity's table |
| `sheet_rolling_steel` | market for sheet rolling, steel | 1635 | kilogram | 1635 | steel in the turbine step-up transformers — Leng Table S1, 163,500 kg per 100 MW farm | activity's table |
| `steel_low_alloyed` | market for steel, low-alloyed | 533 | kilogram | 533 | iron in the turbine step-up transformers — Leng Table S1, 53,300 kg per 100 MW farm | activity's table |
| `sheet_rolling_steel` | market for sheet rolling, steel | 533 | kilogram | 533 | iron in the turbine step-up transformers — Leng Table S1, 53,300 kg per 100 MW farm | activity's table |
| `copper_cathode` | market for copper, cathode | 468 | kilogram | 468 | copper in the turbine step-up transformers — Leng Table S1, 46,800 kg per 100 MW farm | activity's table |
| `wire_drawing_copper` | market for wire drawing, copper | 468 | kilogram | 468 | copper in the turbine step-up transformers — Leng Table S1, 46,800 kg per 100 MW farm | activity's table |
| `lubricating_oil` | market for lubricating oil | 176 | kilogram | 176 | oil in the turbine step-up transformers — Leng Table S1, 17,600 kg per 100 MW farm | activity's table |
| `silica_sand` | market for silica sand | 11.43 | kilogram | 11.43 | silica in the turbine step-up transformers — Leng Table S1, 1,143 kg per 100 MW farm | activity's table |
| `excavation` | market for excavation, hydraulic digger | 7.28 | cubic meter | 7.28 | Leng S3 pad: earthwork backfill | own locator |
| `concrete_20mpa` | market for concrete, 20MPa | 0.56 | cubic meter | 0.56 | Leng S3 pad: cushion concrete C15 | own locator |
| `concrete_normal` | market for concrete, normal strength | 2.8 | cubic meter | 2.8 | Leng S3 pad: cushion concrete C30 | own locator |
| `reinforcing_steel_glo` | market for reinforcing steel | 196 | kilogram | 196 | Leng S3 pad: reinforcement | own locator |
| `upv_electricity` | market for electricity, medium voltage | 1.50675 | kilowatt hour | 1.50675 | Leng S3 pad: AC welding (unit ASSUMED kWh) | ASSUMED |
| `diesel_building_machine` | market for diesel, burned in building machine | 2343.52 | megajoule | 2343.52 | Leng S3 pad: heavy truck 5 t (litres per machine-team, Eq. S2) | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 2.61 | kilogram | 2.61 | Leng S3 electrical installation: section steel | own locator |
| `sheet_rolling_steel` | market for sheet rolling, steel | 2.61 | kilogram | 2.61 | Leng S3 electrical installation: section steel, formed | own locator |
| `copper_cathode` | market for copper, cathode | 3.75 | kilogram | 3.75 | Leng S3 electrical installation: terminal blocks (ASSUMED copper; Leng's dataset is not stated) | ASSUMED |
| `steel_low_alloyed` | market for steel, low-alloyed | 0.18 | kilogram | 0.18 | Leng S3 electrical installation: welding rod | own locator |
| `lead` | market for lead | 1.1415 | kilogram | 1.1415 | Leng S3 electrical installation: lead seals | own locator |

### `solar_inverter_stepup_per_mwp` — Solar inverter-station step-up transformers, per MWp of PV connected

megawatt, GLO. Comment: The oil-immersed transformers in a utility PV plant's inverter stations, stepping the inverters' 400 V (LOW, <1 kV) up to the site collection voltage so the data centre can draw at MEDIUM voltage (1-24 kV). The source unit is wound 20/0.4 kV, which is TX_SITE_COLLECTION_KV (20 kV) exactly, so no vol…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `upv_steel_converter` | steel production, converter, unalloyed | 831.92 | kilogram | 831.92 | steel_converter in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 2,079.800 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_mg_silicon` | market for silicon, metallurgical grade | 29.2808 | kilogram | 29.2808 | mg_silicon in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 73.202 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_oil` | market for lubricating oil | 424 | kilogram | 424 | oil in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 1,060.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_aluminium` | market for aluminium, wrought alloy | 247.2 | kilogram | 247.2 | aluminium in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 618.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_steel_lowalloy` | market for steel, low-alloyed | 693.808 | kilogram | 693.808 | steel_lowalloy in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 1,734.520 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_kraft_paper` | market for kraft paper | 13.644 | kilogram | 13.644 | kraft_paper in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 34.110 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_epoxy` | market for epoxy resin, liquid | 6 | kilogram | 6 | epoxy in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 15.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_copper` | market for copper, cathode | 0.84 | kilogram | 0.84 | copper in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 2.100 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_chromium_steel` | market for steel, chromium steel 18/8 | 1 | kilogram | 1 | chromium_steel in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 2.500 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_rubber` | market for synthetic rubber | 0.08 | kilogram | 0.08 | rubber in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 0.200 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_paint` | market for alkyd paint, white, without water, in 60% solution state | 5.444 | kilogram | 5.444 | paint in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 13.610 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_fibreboard` | market for fibreboard, hard | 0.0116409 | cubic meter | 0.0116409 | hardboard pressboard (workbook '36.96 m3' is 36.96 kg; see docstring) - IEA PVPS T12-33:2026 Table 49, 0.029 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_hot_rolling` | market for hot rolling, steel | 861.2 | kilogram | 861.2 | hot_rolling, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 2,153.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_sheet_rolling_steel` | market for sheet rolling, steel | 1722.4 | kilogram | 1722.4 | sheet_rolling_steel, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 4,306.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_sheet_rolling_alu` | market for sheet rolling, aluminium | 247.2 | kilogram | 247.2 | sheet_rolling_alu, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 618.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_alu_metalworking` | market for metal working, average for aluminium product manufacturing | 247.2 | kilogram | 247.2 | alu_metalworking, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 618.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_electricity` | market for electricity, medium voltage | 947.32 | kilowatt hour | 947.32 | factory electricity - IEA PVPS T12-33:2026 Table 49, 2,368.300 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_heat` | heat production, natural gas, at industrial furnace >100kW | 3961.52 | megajoule | 3961.52 | factory heat - IEA PVPS T12-33:2026 Table 49, 9,903.800 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `building_hall` | market for building, hall, steel construction | 4 | square meter | 4 | transformer station building - IEA PVPS T12-33:2026 Z-PV-238, 10 m2 per unit x 0.4 units/MWp | activity's table |

### `solar_inverter_stepup_replacements_30y_per_mwp` — Solar inverter-station step-up transformer replacements, 30 years, per MWp of PV connected

megawatt, GLO. Comment: Smith 2024 Table A15 charges 1.30E-05 transformer replacements per m2 of module over 30 years against 4.30E-05 installed (A14): 30.2% of the fleet, the same fraction upv.py keeps for the inverters in the same row. The fraction transfers to this study's unit and count where Smith's absolute number (f…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `upv_steel_converter` | steel production, converter, unalloyed | 251.511 | kilogram | 251.511 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - steel_converter in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 2,079.800 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_mg_silicon` | market for silicon, metallurgical grade | 8.85233 | kilogram | 8.85233 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - mg_silicon in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 73.202 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_oil` | market for lubricating oil | 128.186 | kilogram | 128.186 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - oil in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 1,060.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_aluminium` | market for aluminium, wrought alloy | 74.7349 | kilogram | 74.7349 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - aluminium in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 618.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_steel_lowalloy` | market for steel, low-alloyed | 209.756 | kilogram | 209.756 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - steel_lowalloy in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 1,734.520 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_kraft_paper` | market for kraft paper | 4.12493 | kilogram | 4.12493 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - kraft_paper in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 34.110 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_epoxy` | market for epoxy resin, liquid | 1.81395 | kilogram | 1.81395 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - epoxy in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 15.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_copper` | market for copper, cathode | 0.253953 | kilogram | 0.253953 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - copper in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 2.100 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_chromium_steel` | market for steel, chromium steel 18/8 | 0.302326 | kilogram | 0.302326 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - chromium_steel in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 2.500 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_rubber` | market for synthetic rubber | 0.024186 | kilogram | 0.024186 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - rubber in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 0.200 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_paint` | market for alkyd paint, white, without water, in 60% solution state | 1.64586 | kilogram | 1.64586 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - paint in the solar inverter-station step-ups - IEA PVPS T12-33:2026 Table 49, 13.610 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_fibreboard` | market for fibreboard, hard | 0.00351936 | cubic meter | 0.00351936 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - hardboard pressboard (workbook '36.96 m3' is 36.96 kg; see docstring) - IEA PVPS T12-33:2026 Table 49, 0.029 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_hot_rolling` | market for hot rolling, steel | 260.363 | kilogram | 260.363 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - hot_rolling, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 2,153.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_sheet_rolling_steel` | market for sheet rolling, steel | 520.726 | kilogram | 520.726 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - sheet_rolling_steel, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 4,306.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_sheet_rolling_alu` | market for sheet rolling, aluminium | 74.7349 | kilogram | 74.7349 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - sheet_rolling_alu, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 618.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_alu_metalworking` | market for metal working, average for aluminium product manufacturing | 74.7349 | kilogram | 74.7349 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - alu_metalworking, forming of mass already counted - IEA PVPS T12-33:2026 Table 49, 618.000 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_electricity` | market for electricity, medium voltage | 286.399 | kilowatt hour | 286.399 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - factory electricity - IEA PVPS T12-33:2026 Table 49, 2,368.300 per 2.5 MVA unit x 0.4 units/MWp | activity's table |
| `upv_heat` | heat production, natural gas, at industrial furnace >100kW | 1197.67 | megajoule | 1197.67 | replacement over 30 y, 30.2% of the installed units (Smith 2024 A15) - factory heat - IEA PVPS T12-33:2026 Table 49, 9,903.800 per 2.5 MVA unit x 0.4 units/MWp | activity's table |

### `grid_intake_transformer_per_mva` — Grid-intake transformer, per MVA of grid-intake transformer capacity

megavolt ampere, GLO. Comment: The power transformer that steps the network's high voltage down onto the site, sized by cap_grid. Functional unit is 1 MVA of rating; grid_connection.py turns it into a per-MW figure with N-1 redundancy and the power factor, and amortises it over its own ASSET_LIFE_YEARS. ecoinvent 3.9.1 has no pow…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `steel_low_alloyed` | market for steel, low-alloyed | 302 | kilogram | 302 | steel in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 30,200.0 kg per 100 MVA unit | activity's table |
| `sheet_rolling_steel` | market for sheet rolling, steel | 302 | kilogram | 302 | steel in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 30,200.0 kg per 100 MVA unit | activity's table |
| `steel_low_alloyed` | market for steel, low-alloyed | 208 | kilogram | 208 | iron in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 20,800.0 kg per 100 MVA unit | activity's table |
| `sheet_rolling_steel` | market for sheet rolling, steel | 208 | kilogram | 208 | iron in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 20,800.0 kg per 100 MVA unit | activity's table |
| `copper_cathode` | market for copper, cathode | 168 | kilogram | 168 | copper in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 16,800.0 kg per 100 MVA unit | activity's table |
| `wire_drawing_copper` | market for wire drawing, copper | 168 | kilogram | 168 | copper in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 16,800.0 kg per 100 MVA unit | activity's table |
| `lubricating_oil` | market for lubricating oil | 34.3 | kilogram | 34.3 | oil in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 3,430.0 kg per 100 MVA unit | activity's table |
| `silica_sand` | market for silica sand | 2.286 | kilogram | 2.286 | silica in the grid-intake transformer — Leng Table S1 main transformer XZ11-100000/110, 228.6 kg per 100 MVA unit | activity's table |

### `grid_intake_substation_civils_per_mw` — Grid-intake substation civils (switchyard), per MW of connection

megawatt, GLO. Comment: The civils of the intake substation's switchyard, per MW of connection: Leng et al. (2026) Table S3 'outdoor venue project' of the Gaoyou farm's 110 kV booster station - site formation, foundation beams, steel formwork, board, nails and wire, concrete, water and reinforcement, every row at the print…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `excavation` | market for excavation, hydraulic digger | 236.5 | cubic meter | 236.5 | Leng S3 venue: site formation, loose-rock excavation | own locator |
| `concrete_normal` | market for concrete, normal strength | 0.291 | cubic meter | 0.291 | Leng S3 venue: foundation beams, the concrete (97 % by volume, ASSUMED split) | ASSUMED |
| `reinforcing_steel_glo` | market for reinforcing steel | 70.65 | kilogram | 70.65 | Leng S3 venue: foundation beams, the rebar (3 % by volume, ASSUMED split) | ASSUMED |
| `steel_low_alloyed` | market for steel, low-alloyed | 136.59 | kilogram | 136.59 | Leng S3 venue: steel formwork (temporary works, as Leng count them) | own locator |
| `sheet_rolling_steel` | market for sheet rolling, steel | 136.59 | kilogram | 136.59 | Leng S3 venue: steel formwork, formed | own locator |
| `sawnwood_board` | market for sawnwood, board, softwood, raw, dried (u=20%) | 0.191 | cubic meter | 0.191 | Leng S3 venue: board material | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 2.575 | kilogram | 2.575 | Leng S3 venue: iron nails | own locator |
| `steel_low_alloyed` | market for steel, low-alloyed | 3.01 | kilogram | 3.01 | Leng S3 venue: iron wire | own locator |
| `wire_drawing_steel` | market for wire drawing, steel | 3.01 | kilogram | 3.01 | Leng S3 venue: iron wire, drawn | own locator |
| `concrete_normal` | market for concrete, normal strength | 8.961 | cubic meter | 8.961 | Leng S3 venue: concrete | own locator |
| `tap_water_row` | market for tap water | 12180 | kilogram | 12180 | Leng S3 venue: water (1 m3 = 1,000 kg) | own locator |
| `reinforcing_steel_glo` | market for reinforcing steel | 120 | kilogram | 120 | Leng S3 venue: reinforcement steel | own locator |

### `containerised_lv_stepup_per_mw` — Containerised LV step-up transformer, per MW of inverter rating (battery PCS, fuel cell)

megawatt, GLO. Comment: The transformer that steps a battery container's PCS output, or a fuel-cell container's inverter output, from LOW voltage (400 V) up to the site collection voltage (20 kV). Functional unit is 1 MW of inverter rating: transformers.py charges it per MW of cap_batt_p and per MW of cap_fc, each amortise…

| Key | Input | Printed amount | Unit | After scale | Note | Located by |
|---|---|---|---|---|---|---|
| `upv_steel_converter` | steel production, converter, unalloyed | 1260.9 | kilogram | 1260.9 | steel_converter in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (2,079.800 per 5,670 kg unit) | activity's table |
| `upv_mg_silicon` | market for silicon, metallurgical grade | 44.3795 | kilogram | 44.3795 | mg_silicon in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (73.202 per 5,670 kg unit) | activity's table |
| `upv_oil` | market for lubricating oil | 642.636 | kilogram | 642.636 | oil in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (1,060.000 per 5,670 kg unit) | activity's table |
| `upv_aluminium` | market for aluminium, wrought alloy | 374.669 | kilogram | 374.669 | aluminium in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (618.000 per 5,670 kg unit) | activity's table |
| `upv_steel_lowalloy` | market for steel, low-alloyed | 1051.57 | kilogram | 1051.57 | steel_lowalloy in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (1,734.520 per 5,670 kg unit) | activity's table |
| `upv_kraft_paper` | market for kraft paper | 20.6796 | kilogram | 20.6796 | kraft_paper in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (34.110 per 5,670 kg unit) | activity's table |
| `upv_epoxy` | market for epoxy resin, liquid | 9.09391 | kilogram | 9.09391 | epoxy in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (15.000 per 5,670 kg unit) | activity's table |
| `upv_copper` | market for copper, cathode | 1.27315 | kilogram | 1.27315 | copper in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (2.100 per 5,670 kg unit) | activity's table |
| `upv_chromium_steel` | market for steel, chromium steel 18/8 | 1.51565 | kilogram | 1.51565 | chromium_steel in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (2.500 per 5,670 kg unit) | activity's table |
| `upv_rubber` | market for synthetic rubber | 0.121252 | kilogram | 0.121252 | rubber in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (0.200 per 5,670 kg unit) | activity's table |
| `upv_paint` | market for alkyd paint, white, without water, in 60% solution state | 8.25121 | kilogram | 8.25121 | paint in the battery / fuel-cell container step-up - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (13.610 per 5,670 kg unit) | activity's table |
| `upv_fibreboard` | market for fibreboard, hard | 0.0176436 | cubic meter | 0.0176436 | hardboard pressboard - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (0.029 per 5,670 kg unit) | activity's table |
| `upv_hot_rolling` | market for hot rolling, steel | 1305.28 | kilogram | 1305.28 | hot_rolling, forming of mass already counted - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (2,153.000 per 5,670 kg unit) | activity's table |
| `upv_sheet_rolling_steel` | market for sheet rolling, steel | 2610.56 | kilogram | 2610.56 | sheet_rolling_steel, forming of mass already counted - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (4,306.000 per 5,670 kg unit) | activity's table |
| `upv_sheet_rolling_alu` | market for sheet rolling, aluminium | 374.669 | kilogram | 374.669 | sheet_rolling_alu, forming of mass already counted - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (618.000 per 5,670 kg unit) | activity's table |
| `upv_alu_metalworking` | market for metal working, average for aluminium product manufacturing | 374.669 | kilogram | 374.669 | alu_metalworking, forming of mass already counted - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (618.000 per 5,670 kg unit) | activity's table |
| `upv_electricity` | market for electricity, medium voltage | 1435.81 | kilowatt hour | 1435.81 | factory electricity - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (2,368.300 per 5,670 kg unit) | activity's table |
| `upv_heat` | heat production, natural gas, at industrial furnace >100kW | 6004.29 | megajoule | 6004.29 | factory heat - Jasper et al. 2026, CSS (liquid cooled) bill, 'transformer, for grid connection': 5,500 kg per 1,600 kW = 3,437.5 kg/MW, as 0.6063 of the IEA PVPS Table 49 unit's composition (9,903.800 per 5,670 kg unit) | activity's table |

