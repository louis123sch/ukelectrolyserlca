"""
Local network (DUoS) charges and line loss factors for every licence area, 2026/27.
=============================================================================

One table per Carbon Intensity API region; each region is one DNO licence area
(``sites.REGION_NAMES``). Until 29 Oct 2026 every distribution-connected site
was charged on London Power Networks' tables, and every 33 and 132 kV site on
London's *HV* tariff row, which is not the tariff such a site pays at all.

Sources
-------
Each area's *Schedule of charges and other tables 2026/27* (the workbook every
DNO publishes with its LC14 charging statement), in OneDrive "DC optimiser/
connection sources/3 DUoS/2026-27 schedules" (London: "3 DUoS"). ``FILES``
names the workbook for each region. ``scripts/check_duos_areas.py`` re-reads
every workbook and compares every number below with it.

What a site pays, by connection voltage
---------------------------------------
Each area's "TNUoS Mapping" sheet confirms the band families: "HV Site Specific
Band n" is HVn, "Designated EHV Site Specific Band n" is EHVn. Each area's
"Residual Charging Bands" sheet gives the band thresholds — the same in all 14
(HV 500 / 1,100 / 2,000 kVA, EHV 3,500 / 11,000 / 20,000 kVA), and the same as
NESO's Table TB that ``network_charges`` bands on.

11 kV   (HV bands) Annex 1, row "HV Site Specific Band n": red / amber / green
        p/kWh in the area's own time bands, fixed p/MPAN/day, capacity
        p/kVA/day. TRANSCRIBED.
33 and  (EHV bands) Annex 2, "Designated EHV charges": a site-specific tariff
132 kV  for every existing EHV site — super-red p/kWh in the area's own
        super-red window, fixed p/day (which carries the EHV residual for the
        site's band), capacity p/kVA/day. A new site's tariff is set by the DNO
        for its own node, so no row is "the" tariff of a hypothetical site.
        Used here: the quartiles over the area's existing import sites in the
        same residual band — median central, 25th and 75th percentiles low and
        high. DERIVED. A blank super-red cell is a zero charge.

Line loss factors
-----------------
Annex 5, generic demand LLFs by metered voltage, in the area's own time
periods (``LLF_PERIOD_RULES``). 11 kV takes the "HV network" row, 33 kV the
33 kV (or ">22 kV demand", or NGED's "EHV connected") row, 132 kV the 132 kV
row. Most areas mark their table "illustrative" until the BSC Panel approves the
year's values; TRANSCRIBED as published. The four NGED areas leave Annex 5 of
the schedule blank and publish it as a separate workbook, "LLFs for year
beginning 1 April 2026" (``LLF_FILES``), transcribed from those since 29 Oct
2026 (until then the mean of the other England and Wales areas).

All times are UK clock, as every schedule states. "Monday to Friday (Including
Bank Holidays)" is taken as Monday to Friday.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

SCHEDULE_YEAR = "2026/27"
CASES = ("low", "central", "high")

FILES = {
    1: "SSEN North Scotland 2026-27 v1.2.xlsx",
    2: "SPEN South Scotland 2026-27 v0.6.xlsx",
    3: "ENWL North West 2026-27 v1.1.xlsx",
    4: "Northern Powergrid North East 2026-27 v0.2.xlsx",
    5: "Northern Powergrid Yorkshire 2026-27 v0.2.xlsx",
    6: "SPEN North Wales and Merseyside 2026-27 v0.5.xlsx",
    7: "NGED South Wales 2026-27 v0.1.xlsx",
    8: "NGED West Midlands 2026-27 v0.1.xlsx",
    9: "NGED East Midlands 2026-27 v0.1.xlsx",
    10: "UKPN East 2026-27 v1.7.xlsx",
    11: "NGED South West 2026-27 v0.1.xlsx",
    12: "SSEN Southern England 2026-27 v1.2.xlsx",
    13: "UKPN London Power Networks Schedule of charges and other tables 2026-27 v1.3.xlsx",
    14: "UKPN South East 2026-27 v1.4.xlsx",
}
AREA_NAMES = {
    1: "Scottish Hydro Electric Power Distribution (North Scotland)",
    2: "SP Distribution (South Scotland)",
    3: "Electricity North West",
    4: "Northern Powergrid (Northeast)",
    5: "Northern Powergrid (Yorkshire)",
    6: "SP Manweb (North Wales and Merseyside)",
    7: "NGED (South Wales)",
    8: "NGED (West Midlands)",
    9: "NGED (East Midlands)",
    10: "Eastern Power Networks",
    11: "NGED (South West)",
    12: "Southern Electric Power Distribution",
    13: "London Power Networks",
    14: "South Eastern Power Networks",
}


@dataclass(frozen=True)
class HvRow:
    """Annex 1 "HV Site Specific Band n"."""
    red_p_per_kwh: float
    amber_p_per_kwh: float
    green_p_per_kwh: float
    fixed_p_per_day: float
    capacity_p_per_kva_day: float


@dataclass(frozen=True)
class EhvBand:
    """Annex 2 import sites in one residual band: (25th, median, 75th) of each charge."""
    n_sites: int
    super_red_p_per_kwh: tuple
    fixed_p_per_day: tuple
    capacity_p_per_kva_day: tuple


# --- 11 kV: Annex 1, "HV Site Specific Band 1-4" --------------------------------
HV_ROWS = {
    1: {1: HvRow(1.97, 0.525, 0.323, 111.58, 20.1), 2: HvRow(1.463, 0.018, 0, 0, 20.1), 3: HvRow(0.657, 0, 0, 0, 20.1), 4: HvRow(0, 0, 0, 0, 20.1)},
    2: {1: HvRow(4.377, 0.322, 0.01, 1809.84, 8.99), 2: HvRow(4.377, 0.322, 0.01, 5424.49, 8.99), 3: HvRow(4.377, 0.322, 0.01, 10544.78, 8.99), 4: HvRow(4.377, 0.322, 0.01, 27740.35, 8.99)},
    3: {1: HvRow(1.998, 0, 0, 0, 7.79), 2: HvRow(0.64, 0, 0, 0, 7.79), 3: HvRow(0.363, 0, 0, 0, 7.79), 4: HvRow(0, 0, 0, 0, 7.79)},
    4: {1: HvRow(3.403, 0.427, 0.066, 681.69, 5.6), 2: HvRow(3.403, 0.427, 0.066, 1316.4, 5.6), 3: HvRow(3.403, 0.427, 0.066, 2103.42, 5.6), 4: HvRow(3.403, 0.427, 0.066, 5182.22, 5.6)},
    5: {1: HvRow(2.514, 0.588, 0.052, 1251.41, 3.78), 2: HvRow(2.514, 0.588, 0.052, 2908.28, 3.78), 3: HvRow(2.514, 0.588, 0.052, 5506.52, 3.78), 4: HvRow(2.514, 0.588, 0.052, 12820.57, 3.78)},
    6: {1: HvRow(7.151, 0.974, 0.102, 2890.46, 10), 2: HvRow(7.151, 0.974, 0.102, 8585.39, 10), 3: HvRow(7.151, 0.974, 0.102, 18470.93, 10), 4: HvRow(7.151, 0.974, 0.102, 33825.46, 10)},
    7: {1: HvRow(5.953, 0.327, 0.096, 692.19, 10.43), 2: HvRow(5.953, 0.327, 0.096, 1590.95, 10.43), 3: HvRow(5.953, 0.327, 0.096, 2871.8, 10.43), 4: HvRow(5.953, 0.327, 0.096, 6566.48, 10.43)},
    8: {1: HvRow(1.764, 0.205, 0.011, 824.91, 9.26), 2: HvRow(1.764, 0.205, 0.011, 2275.43, 9.26), 3: HvRow(1.764, 0.205, 0.011, 4427.24, 9.26), 4: HvRow(1.764, 0.205, 0.011, 9823.45, 9.26)},
    9: {1: HvRow(2.837, 0.257, 0.009, 360.65, 8.57), 2: HvRow(2.837, 0.257, 0.009, 866.35, 8.57), 3: HvRow(2.837, 0.257, 0.009, 1543.02, 8.57), 4: HvRow(2.837, 0.257, 0.009, 3736.24, 8.57)},
    10: {1: HvRow(4.837, 0.457, 0.038, 240.75, 5.31), 2: HvRow(4.837, 0.457, 0.038, 305.47, 5.31), 3: HvRow(4.837, 0.457, 0.038, 408.23, 5.31), 4: HvRow(4.837, 0.457, 0.038, 855.53, 5.31)},
    11: {1: HvRow(7.242, 0.302, 0.028, 298.61, 10.06), 2: HvRow(7.242, 0.302, 0.028, 525.1, 10.06), 3: HvRow(7.242, 0.302, 0.028, 1016.12, 10.06), 4: HvRow(7.242, 0.302, 0.028, 1908.16, 10.06)},
    12: {1: HvRow(1.266, 0, 0, 0, 10.06), 2: HvRow(0.377, 0, 0, 0, 10.06), 3: HvRow(0.191, 0, 0, 0, 10.06), 4: HvRow(0, 0, 0, 0, 10.06)},
    13: {1: HvRow(0.23, 0, 0, 0, 9.19), 2: HvRow(0.009, 0, 0, 0, 9.19), 3: HvRow(0.104, 0, 0, 0, 9.19), 4: HvRow(0.021, 0, 0, 0, 9.19)},
    14: {1: HvRow(6.01, 0.177, 0.056, 360.69, 6.66), 2: HvRow(6.01, 0.177, 0.056, 636.85, 6.66), 3: HvRow(6.01, 0.177, 0.056, 832.37, 6.66), 4: HvRow(6.01, 0.177, 0.056, 2071.8, 6.66)},
}

# Annex 1 "Time Bands for LV and HV Designated Properties", all year:
# (weekday red, weekday amber, weekend amber), hours on the UK clock; green otherwise.
HV_TIME_BANDS = {
    1: (((16, 19),), ((7, 16), (19, 21)), ((12, 20),)),
    2: (((16.5, 19.5),), ((8, 16.5), (19.5, 22.5)), ((16, 20),)),
    3: (((16, 19),), ((9, 16), (19, 20.5)), ((16, 19),)),
    4: (((16, 19.5),), ((8, 16), (19.5, 22)), ()),
    5: (((16, 19.5),), ((8, 16), (19.5, 22)), ()),
    6: (((16.5, 19.5),), ((8, 16.5), (19.5, 22.5)), ((16, 20),)),
    7: (((17, 19.5),), ((7.5, 17), (19.5, 22)), ((12, 13), (16, 21))),
    8: (((16, 19),), ((7.5, 16), (19, 21)), ()),
    9: (((16, 19),), ((7.5, 16), (19, 21)), ()),
    10: (((16, 19),), ((7, 16), (19, 23)), ()),
    11: (((17, 19),), ((7.5, 17), (19, 21.5)), ((16.5, 19.5),)),
    12: (((16.5, 19.5),), ((7, 16.5), (19.5, 22)), ((9.5, 21.5),)),
    13: (((11, 14), (16, 19)), ((7, 11), (14, 16), (19, 23)), ()),
    14: (((16, 19),), ((7, 16), (19, 23)), ()),
}

# --- 33 and 132 kV: Annex 2, import sites by residual band ----------------------
# (25th percentile, median, 75th percentile) over the area's listed import sites.
EHV_BANDS = {
    1: {1: EhvBand(41, (0.0, 0.0, 0.0), (33.35, 308.6, 1217.85), (1.05, 1.46, 2.67)), 2: EhvBand(8, (0.0, 0.0, 0.0), (1034.65, 2031.715, 12921.1025), (2.37, 2.895, 3.3125)), 3: EhvBand(4, (0.0, 0.0, 0.0), (5910.08, 11431.4, 16780.1625), (1.5225, 2.03, 2.7375)), 4: EhvBand(2, (0.0, 0.0, 0.0), (18105.6275, 28416.725, 38727.8225), (0.775, 1.0, 1.225))},
    2: {1: EhvBand(13, (0.0, 0.0, 0.0), (1636.12, 1916.53, 1916.53), (1.47, 1.74, 2.08)), 2: EhvBand(16, (0.0, 0.0, 0.0), (10990.84, 12080.8, 24066.2375), (1.2975, 2.91, 4.01)), 3: EhvBand(5, (0.0, 0.0, 0.0), (26525.36, 31567.11, 50420.57), (1.79, 2.27, 2.3)), 4: EhvBand(3, (0.0, 0.0, 0.0), (39485.595, 46320.46, 49800.695), (1.375, 2.01, 2.3))},
    3: {1: EhvBand(15, (0.0695, 0.203, 0.8805), (1017.46, 1017.46, 1938.7), (2.395, 2.87, 3.175)), 2: EhvBand(20, (0.2635, 1.7785, 3.3355), (2306.785, 5669.935, 11049.76), (2.715, 4.115, 5.45)), 3: EhvBand(17, (0.0, 0.171, 0.445), (5589.22, 12727.35, 23423.78), (3.11, 3.72, 4.49)), 4: EhvBand(9, (0.228, 1.593, 3.297), (4556.42, 7934.9, 11739.03), (1.87, 4.41, 4.8))},
    4: {1: EhvBand(11, (0.0305, 0.14, 0.2705), (2741.02, 2790.93, 3064.55), (0.54, 0.71, 2.035)), 2: EhvBand(11, (0.0, 0.011, 0.0655), (5671.5, 6158.44, 7798.225), (0.59, 0.77, 1.38)), 3: EhvBand(17, (0.0, 0.0, 0.042), (19508.04, 20238.26, 22048.76), (0.88, 1.12, 1.42)), 4: EhvBand(6, (0.0, 0.0, 0.0023), (74194.8475, 75269.6, 78314.6625), (1.015, 1.235, 1.395))},
    5: {1: EhvBand(35, (0.0, 0.015, 0.17), (2202.435, 2265.24, 2335.94), (0.425, 0.68, 1.075)), 2: EhvBand(31, (0.0205, 0.087, 0.283), (13311.76, 13311.76, 13453.18), (0.815, 1.13, 1.72)), 3: EhvBand(14, (0.003, 0.056, 0.2243), (36452.34, 36629.105, 36853.1325), (0.505, 0.99, 1.585)), 4: EhvBand(12, (0.0, 0.0015, 0.018), (104133.9675, 105261.87, 107381.4875), (0.5825, 0.81, 0.975))},
    6: {1: EhvBand(90, (0.0, 0.0, 0.5885), (13978.99, 13978.99, 13978.99), (2.64, 3.76, 4.85)), 2: EhvBand(58, (0.0, 0.0, 0.5835), (42804.75, 42886.335, 45006.515), (2.3525, 3.54, 4.3)), 3: EhvBand(12, (0.0, 0.0, 0.0), (84571.79, 89128.145, 96047.8525), (3.005, 3.875, 4.815)), 4: EhvBand(12, (0.0, 0.0, 0.0), (216519.3084, 224163.68, 230925.3813), (2.8975, 3.395, 3.8525))},
    7: {1: EhvBand(23, (0.0205, 0.075, 2.749), (1615.96, 1755.37, 2240.13), (1.21, 1.89, 3.25)), 2: EhvBand(12, (0.0, 0.2315, 1.0297), (17238.1875, 17889.28, 18857.0725), (2.175, 2.96, 3.4875)), 3: EhvBand(7, (0.0, 0.0, 0.0185), (40134.015, 41057.68, 42547.665), (2.405, 2.54, 3.315)), 4: EhvBand(16, (0.0, 0.007, 0.8297), (94414.89, 96126.585, 110126.0575), (2.335, 2.885, 3.3975))},
    8: {1: EhvBand(12, (0.0, 0.8795, 1.3958), (955.6275, 981.065, 1166.0825), (1.39, 2.235, 2.8475)), 2: EhvBand(12, (0.0, 1.288, 1.8388), (8235.3975, 8704.275, 11978.96), (0.8275, 1.37, 2.04)), 3: EhvBand(11, (0.0, 0.0, 1.9715), (22345.31, 22859.83, 24222.96), (1.03, 1.28, 1.575)), 4: EhvBand(5, (0.0, 0.0, 0.0), (85393.34, 89873.76, 91614.42), (2.25, 2.4, 3.11))},
    9: {1: EhvBand(24, (0.3315, 3.1345, 3.5325), (916.15, 990.725, 1041.46), (1.215, 1.48, 1.9025)), 2: EhvBand(23, (0.4945, 1.112, 2.7775), (6811.97, 6971.67, 11396.535), (1.32, 1.62, 2.335)), 3: EhvBand(9, (0.698, 3.511, 3.686), (10041.92, 10201.62, 22165.59), (0.87, 1.12, 1.32)), 4: EhvBand(14, (0.9788, 2.8215, 3.2965), (25730.615, 26158.395, 27400.735), (1.375, 1.685, 1.7525))},
    10: {1: EhvBand(52, (0.0585, 0.4435, 1.7425), (5035.3375, 5208.44, 5649.73), (1.605, 2.255, 3.27)), 2: EhvBand(37, (0.159, 1.212, 2.133), (24713.06, 25481.04, 30905.86), (1.38, 2.5, 3.29)), 3: EhvBand(20, (0.0063, 0.665, 1.587), (59229.6975, 69379.185, 71584.87), (2.5875, 2.995, 3.4075)), 4: EhvBand(16, (0.0, 0.149, 0.833), (76912.9525, 80495.95, 115769.755), (1.34, 1.815, 2.5725))},
    11: {1: EhvBand(26, (0.3297, 1.2405, 3.8508), (1102.02, 1323.12, 1896.3075), (1.355, 1.945, 2.97)), 2: EhvBand(26, (0.3778, 2.024, 4.7025), (7324.9475, 7751.835, 8933.065), (1.52, 2.22, 3.2575)), 3: EhvBand(6, (0.0, 0.777, 2.9775), (10827.08, 11181.245, 13887.155), (1.725, 1.81, 2.0)), 4: EhvBand(4, (0.2435, 0.475, 1.0585), (41899.51, 49027.05, 62744.5975), (1.2275, 1.495, 1.695))},
    12: {1: EhvBand(21, (0.0, 0.0, 0.398), (1015.35, 1127.12, 1309.45), (0.95, 1.61, 2.43)), 2: EhvBand(27, (0.0, 0.0, 0.5205), (6919.955, 7667.07, 12385.465), (1.29, 2.12, 3.37)), 3: EhvBand(18, (0.0, 0.229, 0.7902), (18134.535, 18673.12, 20270.87), (1.5925, 1.975, 2.2675)), 4: EhvBand(22, (0.0, 0.0, 0.0), (74548.405, 81142.13, 92226.55), (1.5425, 1.775, 2.4475))},
    13: {1: EhvBand(10, (0.0192, 0.2095, 0.2633), (1073.99, 1205.39, 1513.2725), (0.93, 1.29, 1.935)), 2: EhvBand(14, (0.1882, 0.2165, 0.2243), (9297.23, 9297.23, 9297.23), (2.2325, 2.45, 2.7525)), 3: EhvBand(5, (0.006, 0.012, 0.197), (26051.02, 33714.26, 34363.43), (2.58, 2.98, 4.58)), 4: EhvBand(16, (0.0, 0.001, 0.03), (57429.7, 63517.91, 66122.31), (1.7225, 2.225, 3.2925))},
    14: {1: EhvBand(13, (0.0, 0.003, 0.195), (2554.48, 2924.71, 3001.92), (1.27, 1.58, 2.23)), 2: EhvBand(16, (0.0, 0.2525, 1.0815), (12942.2375, 13076.04, 14970.095), (1.7025, 1.865, 2.4375)), 3: EhvBand(9, (0.08, 0.699, 2.118), (33778.28, 33778.28, 33778.28), (1.76, 2.25, 2.38)), 4: EhvBand(12, (0.0, 0.039, 0.6893), (63091.39, 63537.2, 65541.865), (1.545, 2.12, 2.3325))},
}

# Annex 2 "Time Periods for Designated EHV Properties": super-red windows, weekdays.
# (months, ((start, end), ...)); an exclusion is ((month, first day), (month, last day)).
_NOV_FEB = (11, 12, 1, 2)
SUPER_RED = {
    1: ((_NOV_FEB, ((16, 19),)),),
    2: ((_NOV_FEB, ((16.5, 19.5),)),),
    3: ((_NOV_FEB, ((16, 19),)),),
    4: ((_NOV_FEB, ((16, 19.5),)),),
    5: ((_NOV_FEB, ((16, 19.5),)),),
    6: ((_NOV_FEB, ((16.5, 19.5),)),),
    7: ((_NOV_FEB, ((17, 19.5),)),),
    8: ((_NOV_FEB, ((16, 19),)),),
    9: ((_NOV_FEB, ((16, 19),)),),
    10: ((_NOV_FEB, ((16, 19),)),),
    11: ((_NOV_FEB, ((17, 19),)),),
    12: ((_NOV_FEB, ((16.5, 19.5),)),),
    13: (((6, 7, 8), ((11, 14),)), (_NOV_FEB, ((16, 19),))),
    14: ((_NOV_FEB, ((16, 19),)),),
}
# "excluding 22nd Dec to 4th Jan inclusive" (NGED South Wales and South West).
SUPER_RED_EXCLUDED = {7: ((12, 22), (1, 4)), 11: ((12, 22), (1, 4))}

# --- Line loss factors: Annex 5 ---------------------------------------------------
# Period rules, first match wins: (months or None for all, "wd"/"we"/None, start, end, period).
# A window ending at 24 runs to midnight; one starting before 0 is split by the caller.
_ALL = None
LLF_PERIOD_RULES = {
    # Scottish and Southern: 1 winter weekday peak, 2 winter weekday, 3 other, 4 night
    "SSEN": ((_ALL, None, 0.5, 7.5, 4), (_NOV_FEB, "wd", 16, 19, 1),
             (_NOV_FEB, "wd", 7.5, 16, 2), (_NOV_FEB, "wd", 19, 20, 2)),
    "SSEN_default": 3,
    # SP Energy Networks: 1 night 23:30-07:30, 4 Nov-Feb weekday 16-19, 3 Nov-Feb
    # weekday 07:30-16 and 19-20, 2 otherwise
    "SPEN": ((_ALL, None, 23.5, 24, 1), (_ALL, None, 0, 7.5, 1), (_NOV_FEB, "wd", 16, 19, 4),
             (_NOV_FEB, "wd", 7.5, 16, 3), (_NOV_FEB, "wd", 19, 20, 3)),
    "SPEN_default": 2,
    # Electricity North West: 3 night 00-07, 1 Nov-Feb weekday 16-19, 2 Nov-Feb weekday
    # 07-16 and 19-24, 4 otherwise
    "ENWL": ((_ALL, None, 0, 7, 3), (_NOV_FEB, "wd", 16, 19, 1),
             (_NOV_FEB, "wd", 7, 16, 2), (_NOV_FEB, "wd", 19, 24, 2)),
    "ENWL_default": 4,
    # Northern Powergrid Northeast: 3 night 00:30-07:30; Nov weekday 07:30-20 is 2;
    # Dec-Feb weekday 16:30-18:30 is 1, 07:30-16:30 and 18:30-20 is 2; 4 otherwise
    "NPGN": ((_ALL, None, 0.5, 7.5, 3), ((12, 1, 2), "wd", 16.5, 18.5, 1),
             ((11, 12, 1, 2), "wd", 7.5, 20, 2)),
    "NPGN_default": 4,
    # Northern Powergrid Yorkshire: 3 night 00-07, 1 Nov-Feb weekday 16-19, 2 Nov-Feb
    # weekday 07-16 and 19-20, 4 otherwise
    "NPGY": ((_ALL, None, 0, 7, 3), (_NOV_FEB, "wd", 16, 19, 1),
             (_NOV_FEB, "wd", 7, 16, 2), (_NOV_FEB, "wd", 19, 20, 2)),
    "NPGY_default": 4,
    # UK Power Networks: 4 night 00-07, 1 winter peak Nov-Feb weekday 16-20, 3 winter
    # shoulder Nov-Feb weekday 07-16 and March weekday 07-20, 2 summer peak Jun-Aug
    # weekday 07-20, 5 otherwise
    "UKPN": ((_ALL, None, 0, 7, 4), (_NOV_FEB, "wd", 16, 20, 1), (_NOV_FEB, "wd", 7, 16, 3),
             ((3,), "wd", 7, 20, 3), ((6, 7, 8), "wd", 7, 20, 2)),
    "UKPN_default": 5,
    # NGED East and West Midlands: 3 night 00:30-07:30, 1 Nov-Feb weekday 16-19,
    # 2 Nov-Feb weekday 07:30-16 and 19-20, 4 otherwise
    "NGEDM": ((_ALL, None, 0.5, 7.5, 3), (_NOV_FEB, "wd", 16, 19, 1),
              (_NOV_FEB, "wd", 7.5, 16, 2), (_NOV_FEB, "wd", 19, 20, 2)),
    "NGEDM_default": 4,
    # NGED South Wales: 3 night 00:30-07:30, 1 Nov-Feb weekday 16-19, 2 Nov-Feb
    # weekday 07:30-16, 4 otherwise
    "NGEDSW": ((_ALL, None, 0.5, 7.5, 3), (_NOV_FEB, "wd", 16, 19, 1),
               (_NOV_FEB, "wd", 7.5, 16, 2)),
    "NGEDSW_default": 4,
    # NGED South West: 3 night 23:30-06:30, 1 Nov-Feb weekday 16-19, 2 Nov-Feb
    # weekday 06:30-16, 4 otherwise
    "NGEDSWEB": ((_ALL, None, 0, 6.5, 3), (_ALL, None, 23.5, 24, 3),
                 (_NOV_FEB, "wd", 16, 19, 1), (_NOV_FEB, "wd", 6.5, 16, 2)),
    "NGEDSWEB_default": 4,
}
LLF_SCHEME = {1: "SSEN", 2: "SPEN", 3: "ENWL", 4: "NPGN", 5: "NPGY", 6: "SPEN",
              7: "NGEDSW", 8: "NGEDM", 9: "NGEDM", 10: "UKPN", 11: "NGEDSWEB",
              12: "SSEN", 13: "UKPN", 14: "UKPN"}

# Generic demand LLFs by connection voltage, by period (1, 2, ...). TRANSCRIBED.
LLF = {
    1: {"11 kV": (1.007, 1.007, 1.01, 1.015), "33 kV": (0.991, 0.991, 0.991, 0.996)},
    2: {"11 kV": (1.023, 1.025, 1.028, 1.029), "33 kV": (1.003, 1.003, 1.004, 1.005)},
    3: {"11 kV": (1.038, 1.036, 1.03, 1.033), "33 kV": (1.021, 1.02, 1.017, 1.018),
        "132 kV": (1.009, 1.009, 1.006, 1.007)},
    4: {"11 kV": (1.023, 1.022, 1.018, 1.02), "33 kV": (1.008, 1.008, 1.007, 1.008),
        "132 kV": (1.008, 1.008, 1.007, 1.008)},          # ">22kV connected - demand"
    5: {"11 kV": (1.029, 1.028, 1.022, 1.024), "33 kV": (1.013, 1.012, 1.009, 1.01),
        "132 kV": (1.013, 1.012, 1.009, 1.01)},           # ">22kV connected - demand"
    6: {"11 kV": (1.032, 1.036, 1.041, 1.044), "33 kV": (1.016, 1.017, 1.019, 1.02),
        "132 kV": (1.003, 1.004, 1.005, 1.005)},
    # NGED: "High Voltage Network", "EHV connected", "132kV connected"
    7: {"11 kV": (1.057, 1.053, 1.044, 1.048), "33 kV": (1.037, 1.034, 1.031, 1.032),
        "132 kV": (1.024, 1.021, 1.015, 1.018)},
    8: {"11 kV": (1.069, 1.06, 1.042, 1.047), "33 kV": (1.066, 1.05, 1.04, 1.035),
        "132 kV": (1.011, 1.011, 1.007, 1.008)},
    9: {"11 kV": (1.048, 1.045, 1.036, 1.04), "33 kV": (1.023, 1.022, 1.018, 1.019),
        "132 kV": (1.009, 1.008, 1.006, 1.007)},
    10: {"11 kV": (1.036, 1.028, 1.033, 1.027, 1.029), "33 kV": (1.022, 1.016, 1.02, 1.016, 1.018),
         "132 kV": (1.007, 1.005, 1.006, 1.005, 1.005)},
    12: {"11 kV": (1.023, 1.023, 1.023, 1.024), "33 kV": (1.007, 1.007, 1.007, 1.006),
         "132 kV": (1.004, 1.004, 1.004, 1.005)},
    13: {"11 kV": (1.036, 1.03, 1.034, 1.024, 1.029), "33 kV": (1.017, 1.015, 1.017, 1.014, 1.015),
         "132 kV": (1.003, 1.003, 1.003, 1.002, 1.002)},
    11: {"11 kV": (1.034, 1.032, 1.027, 1.031), "33 kV": (1.012, 1.013, 1.011, 1.014),
         "132 kV": (1.001, 1.001, 1.001, 1.001)},
    14: {"11 kV": (1.033, 1.025, 1.03, 1.024, 1.027), "33 kV": (1.017, 1.013, 1.016, 1.013, 1.014),
         "132 kV": (1.007, 1.005, 1.006, 1.005, 1.006)},
}
# NGED leave Annex 5 of their schedules blank and publish the LLFs separately:
# "LLFs for year beginning 1 April 2026", one workbook per area (29 Oct 2026).
LLF_FILES = {7: "NGED South Wales 2026-27 Annex 5 LLFs.xlsx",
             8: "NGED West Midlands 2026-27 Annex 5 LLFs.xlsx",
             9: "NGED East Midlands 2026-27 Annex 5 LLFs.xlsx",
             11: "NGED South West 2026-27 Annex 5 LLFs.xlsx"}
LLF_ASSUMED_REGIONS = ()      # none since 29 Oct 2026, when NGED's LLF workbooks came in


# =============================================================================
def _clock(index):
    c = pd.DatetimeIndex(index)
    c = (c.tz_localize("UTC") if c.tz is None else c).tz_convert("Europe/London")
    return (np.asarray(c.month), np.asarray(c.day), np.asarray(c.dayofweek < 5),
            np.asarray(c.hour + c.minute / 60.0))


def _within(hour, windows):
    if not windows:
        return np.zeros(len(hour), dtype=bool)
    return np.logical_or.reduce([(hour >= a) & (hour < b) for a, b in windows])


def _region(region: int) -> int:
    if region not in FILES:
        raise ValueError(f"no DUoS tables for region {region!r}")
    return region


def hv_band_series(index, region: int) -> np.ndarray:
    """'red' / 'amber' / 'green' for every step, in the area's own HV time bands."""
    red_wd, amber_wd, amber_we = HV_TIME_BANDS[_region(region)]
    _, _, wd, h = _clock(index)
    red = wd & _within(h, red_wd)
    amber = ~red & ((wd & _within(h, amber_wd)) | (~wd & _within(h, amber_we)))
    return np.where(red, "red", np.where(amber, "amber", "green"))


def super_red_window(index, region: int) -> np.ndarray:
    """True in the area's EHV super-red window."""
    m, d, wd, h = _clock(index)
    on = np.zeros(len(h), dtype=bool)
    for months, windows in SUPER_RED[_region(region)]:
        on |= wd & np.isin(m, months) & _within(h, windows)
    if region in SUPER_RED_EXCLUDED:
        (m0, d0), (m1, d1) = SUPER_RED_EXCLUDED[region]
        on &= ~(((m == m0) & (d >= d0)) | ((m == m1) & (d <= d1)))
    return on


def _family_band(tdr_band: str) -> tuple[str, int]:
    b = str(tdr_band)
    for fam in ("EHV", "HV"):
        if b.startswith(fam) and b[len(fam):].isdigit():
            return fam, int(b[len(fam):])
    raise ValueError(f"no local network tariff for band {tdr_band!r}")


def _pick(q: tuple, case: str) -> float:
    if case not in CASES:
        raise ValueError(f"case must be one of {CASES}, got {case!r}")
    return float(q[CASES.index(case)])


def charges(index, region: int, tdr_band: str, case: str = "central",
            power_factor: float = 1.0, site: tuple | None = None,
            connection_voltage: str | None = None) -> dict:
    """The area's DUoS for a distribution site in ``tdr_band``: a £/MWh series,
    £/MW/year on the connection, £/year fixed.

    For an EHV band with ``site=(lat, lon)`` and ``connection_voltage`` given,
    the charges are site-specific (``ehv_charges.site_charges``: the nearest
    price node plus the area's calibrated add-on); otherwise the area's
    listed-site quartiles."""
    fam, n = _family_band(tdr_band)
    if fam == "EHV" and site is not None and connection_voltage is not None:
        from optimisation import ehv_charges
        s = ehv_charges.site_charges(site[0], site[1], region, connection_voltage, tdr_band, case, power_factor)
        unit = pd.Series(super_red_window(index, region) * s["super_red_p_per_kwh"] * 10.0, index=index,
                         name="duos_GBP_per_MWh")
        return {"duos_GBP_per_MWh": unit, "capacity_GBP_per_MW_year": s["capacity_GBP_per_MW_year"],
                "fixed_GBP_per_year": s["fixed_GBP_per_year"],
                "tariff": f"Designated EHV Band {n}, {s['how']}" + (f" ({case})" if s["how"] != "site-specific" else ""),
                "area": AREA_NAMES[region], "file": FILES[region], "site_specific": s}
    if fam == "HV":
        row = HV_ROWS[_region(region)][n]
        band = hv_band_series(index, region)
        p = np.select([band == "red", band == "amber"],
                      [row.red_p_per_kwh, row.amber_p_per_kwh], row.green_p_per_kwh)
        unit = pd.Series(p * 10.0, index=index, name="duos_GBP_per_MWh")
        cap, fixed, tariff = row.capacity_p_per_kva_day, row.fixed_p_per_day, f"HV Site Specific Band {n}"
    else:
        b = EHV_BANDS[_region(region)][n]
        sr = _pick(b.super_red_p_per_kwh, case)
        unit = pd.Series(super_red_window(index, region) * sr * 10.0, index=index,
                         name="duos_GBP_per_MWh")
        cap, fixed = _pick(b.capacity_p_per_kva_day, case), _pick(b.fixed_p_per_day, case)
        tariff = f"Designated EHV Band {n}, {case} of {b.n_sites} sites"
    return {"duos_GBP_per_MWh": unit,
            "capacity_GBP_per_MW_year": cap / 100.0 * 365.0 * 1000.0 / power_factor,
            "fixed_GBP_per_year": fixed / 100.0 * 365.0,
            "tariff": tariff, "area": AREA_NAMES[region], "file": FILES[region]}


def llf_period(index, region: int) -> np.ndarray:
    scheme = LLF_SCHEME[region]
    m, _, wd, h = _clock(index)
    period = np.full(len(h), LLF_PERIOD_RULES[scheme + "_default"])
    done = np.zeros(len(h), dtype=bool)
    for months, day, a, b, p in LLF_PERIOD_RULES[scheme]:
        hit = (h >= a) & (h < b) & ~done
        if months is not None:
            hit &= np.isin(m, months)
        if day == "wd":
            hit &= wd
        elif day == "we":
            hit &= ~wd
        period[hit] = p
        done |= hit
    return period


def llf_series(index, region: int, voltage: str) -> pd.Series:
    """The area's generic demand LLF for the connection voltage, every step."""
    if voltage == "transmission":
        return pd.Series(1.0, index=index, name="llf")
    table = LLF[_region(region)]
    if voltage not in table:
        raise ValueError(f"{AREA_NAMES[region]} publishes no {voltage} LLF "
                         f"(it has {sorted(table)})")
    return pd.Series(np.asarray(table[voltage])[llf_period(index, region) - 1],
                     index=index, name="llf")
