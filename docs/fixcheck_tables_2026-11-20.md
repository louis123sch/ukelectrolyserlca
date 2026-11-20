# East Grinstead before/after tables, cluster runs of 19-20 Nov 2026

Made by `scripts/fixcheck_compare.py` from the cluster results (batches 3033334/5, 3034467/8, 3034818/9). Summary and verdict in `docs/SOURCE_DIFF.md`, section "Before/after at East Grinstead".

## 1. Code check: before (c9cc1dc) → after (3154401)

Scenario list: 25 solved in fix-before, 24 in fix-after.

| n | Configuration | Result | Point | Cost £m/yr (change %) | Carbon t/yr (change %) | Sizes that moved |
|---|---|---|---|---|---|---|
| 1 | Grid only (free) | identical | all three | 213.981 | 229,781 | none |
| 2 | Grid + battery (free) | changed | min_cost | 213.981 → 213.981 (+0.000) | 229,781 → 229,781 (-0.000) | batt_e 0.01 → 0.00 |
| 2 | Grid + battery (free) | changed | knee | 227.820 → 227.820 (+0.000) | 222,446 → 222,446 (-0.000) | none |
| 2 | Grid + battery (free) | changed | min_gwp | 257.311 → 257.311 (-0.000) | 218,778 → 218,778 (+0.000) | none |
| 3 | Grid + renewables + battery (free) | identical | all three | 165.474 | 67,540 | none |
| 4 | Grid + H2 (PEM) (baseload) | identical | all three | 214.039 | 229,782 | none |
| 5 | Grid + H2 (PEM) | no result in fix-after | | | | |
| 6 | Grid + H2 (AE) (baseload) | identical | all three | 214.039 | 229,782 | none |
| 7 | Grid + H2 (AE) (flexible → free) | identical | all three | 214.039 | 229,782 | none |
| 8 | Grid + H2 (SOEC) (baseload) | identical | all three | 214.039 | 229,782 | none |
| 9 | Grid + H2 (SOEC) (flexible → free) | identical | all three | 214.039 | 229,782 | none |
| 10 | Renewables + H2 (PEM), islanded (baseload) | identical | all three | 389.650 | 73,730 | none |
| 11 | Renewables + H2 (PEM), islanded (flexible) | changed | min_cost | 380.640 → 380.640 (-0.000) | 73,993 → 73,682 (-0.420) | none |
| 11 | Renewables + H2 (PEM), islanded (flexible) | changed | knee | 387.344 → 396.387 (+2.335) | 72,099 → 71,198 (-1.250) | wind 805.05 → 852.65; solar 181.39 → 159.30; ely 70.86 → 87.93; tank 1,282,445.74 → 1,227,642.53; fc 140.78 → 140.73 |
| 11 | Renewables + H2 (PEM), islanded (flexible) | changed | min_gwp | 409.981 → 447.281 (+9.098) | 71,468 → 70,370 (-1.536) | wind 966.33 → 1,053.87; solar 83.06 → 49.52; ely 93.71 → 184.28; tank 1,152,924.68 → 1,055,875.24; fc 140.61 → 140.54 |
| 12 | Renewables + H2 (AE), islanded (baseload) | identical | all three | 385.212 | 73,979 | none |
| 13 | Renewables + H2 (AE), islanded (flexible) | changed | min_cost | 375.715 → 375.715 (-0.000) | 74,523 → 73,929 (-0.797) | none |
| 13 | Renewables + H2 (AE), islanded (flexible) | changed | knee | 381.653 → 390.481 (+2.313) | 72,565 → 71,456 (-1.527) | wind 793.17 → 843.37; solar 186.70 → 167.64; ely 65.91 → 85.39; tank 1,294,984.49 → 1,230,366.12; fc 140.79 → 140.75 |
| 13 | Renewables + H2 (AE), islanded (flexible) | changed | min_gwp | 398.233 → 434.483 (+9.102) | 71,912 → 70,632 (-1.780) | wind 956.54 → 1,052.67; solar 97.68 → 61.35; ely 67.99 → 170.79; tank 1,163,658.94 → 1,043,958.52; fc 140.63 → 140.55 |
| 14 | Renewables + H2 (SOEC), islanded (baseload) | identical | all three | 415.872 | 83,277 | none |
| 15 | Renewables + H2 (SOEC), islanded (flexible) | changed | min_cost | 406.943 → 406.943 (+0.000) | 82,501 → 82,403 (-0.119) | none |
| 15 | Renewables + H2 (SOEC), islanded (flexible) | changed | knee | 422.876 → 434.599 (+2.772) | 79,568 → 78,720 (-1.065) | wind 958.05 → 1,006.77; solar 255.47 → 246.46; ely 46.62 → 55.75; tank 1,058,876.41 → 1,000,258.25; fc 140.73 → 140.69 |
| 15 | Renewables + H2 (SOEC), islanded (flexible) | changed | min_gwp | 478.000 → 536.180 (+12.172) | 78,590 → 77,493 (-1.396) | wind 1,142.08 → 1,229.05; solar 220.54 → 215.55; ely 92.69 → 155.15; tank 848,485.02 → 718,443.05; fc 140.59 → 140.53 |
| 16 | Grid + bought H2 (grey) (free) | identical | all three | 213.981 | 229,782 | none |
| 17 | Grid + bought H2 (blue) (free) | identical | all three | 236.733 | 227,534 | none |
| 18 | Grid + bought H2 (turquoise) (free) | identical | all three | 237.887 | 228,427 | none |
| 19 | Grid + bought H2 (green) (free) | identical | all three | 481.990 | 158,910 | none |
| 20 | Grid + H2 (PEM) — control (free) | identical | all three | 214.039 | 229,782 | none |
| 21 | Everything available — control (free) | changed | min_cost | 143.606 → 143.606 (+0.000) | 95,742 → 95,742 (-0.000) | none |
| 21 | Everything available — control (free) | changed | knee | 166.641 → 169.074 (+1.460) | 67,179 → 66,464 (-1.065) | wind 450.98 → 462.82; solar 330.45 → 330.52; batt_p 91.53 → 94.75; batt_e 520.56 → 543.76; grid 121.31 → 121.63 |
| 21 | Everything available — control (free) | changed | min_gwp | 270.282 → 291.020 (+7.673) | 57,658 → 56,704 (-1.654) | wind 720.60 → 702.10; solar 213.87 → 193.71; batt_p 20.99 → 12.88; batt_e 61.26 → 36.16; ely 81.77 → 138.70; tank 193,178.12 → 254,801.14; fc 100.09 → 108.48; grid 128.22 → 124.63 |
| 22 | Grid + H2 (SOEC, electric boiler) (baseload) | identical | all three | 214.039 | 229,782 | none |
| 23 | Grid + H2 (SOEC, electric boiler) (flexible → free) | identical | all three | 214.039 | 229,782 | none |
| 24 | Renewables + H2 (SOEC, electric boiler), islanded (baseload) | identical | all three | 413.017 | 74,134 | none |
| 25 | Renewables + H2 (SOEC, electric boiler), islanded (flexible) | changed | min_cost | 406.294 → 406.294 (+0.000) | 74,463 → 74,361 (-0.136) | none |
| 25 | Renewables + H2 (SOEC, electric boiler), islanded (flexible) | changed | knee | 413.788 → 422.133 (+2.017) | 72,567 → 71,967 (-0.826) | wind 846.72 → 854.88; solar 182.14 → 178.62; ely 57.65 → 69.78; tank 1,234,729.70 → 1,211,487.04 |
| 25 | Renewables + H2 (SOEC, electric boiler), islanded (flexible) | changed | min_gwp | 446.984 → 495.382 (+10.828) | 71,935 → 71,169 (-1.064) | wind 968.13 → 1,049.24; solar 104.37 → 77.52; ely 88.14 → 144.16; tank 1,129,235.61 → 1,034,822.41; fc 140.63 → 140.56 |

18 configurations identical (cost and carbon within one part in a million, no size moved).

| Reference case | Point | Cost £m/yr (change %) | Carbon t/yr (change %) | Sizes that moved |
|---|---|---|---|---|
| islanded_h2 | min_cost | 382.041 → 382.041 (-0.000) | 87,479 → 87,468 (-0.012) | none |
| islanded_h2 | min_gwp | 434.313 → 474.046 (+9.148) | 75,401 → 74,257 (-1.517) | wind 1,030.95 → 1,114.37; solar 89.41 → 56.43; batt_p 12.59 → 6.81; batt_e 43.69 → 25.54; ely 96.10 → 192.96; tank 1,227,453.05 → 1,138,439.48; fc 140.96 → 144.01 |
| eastgrinstead_grid | min_cost | 153.681 → 153.681 (+0.000) | 101,479 → 101,479 (+0.000) | none |
| eastgrinstead_grid | min_gwp | 289.409 → 311.629 (+7.678) | 60,674 → 59,652 (-1.685) | wind 772.09 → 752.25; solar 229.14 → 207.55; batt_p 22.49 → 13.80; batt_e 65.61 → 38.74; ely 87.62 → 148.62; tank 206,973.50 → 273,001.94; fc 107.24 → 116.23; grid 137.38 → 133.53 |

## 2. Fuel-cell stack fix: after (3154401) → fc (bbb4505), with --fc-check

Scenario list: 24 solved in fix-after, 24 in fix-fc.

Fuel-cell check: an unchanged design's bill should rise by cap_fc × £42,925 a year.

| n | Configuration | Result | Point | Cost £m/yr (change %) | Carbon t/yr (change %) | Sizes that moved | Expected rise £m | Check |
|---|---|---|---|---|---|---|---|---|
| 1 | Grid only (free) | identical | all three | 213.981 | 229,781 | none | | ok |
| 2 | Grid + battery (free) | identical | all three | 227.820 | 222,446 | none | | ok |
| 3 | Grid + renewables + battery (free) | identical | all three | 165.474 | 67,540 | none | | ok |
| 4 | Grid + H2 (PEM) (baseload) | identical | all three | 214.039 | 229,782 | none | | ok |
| 6 | Grid + H2 (AE) (baseload) | identical | all three | 214.039 | 229,782 | none | | ok |
| 7 | Grid + H2 (AE) (free) | identical | all three | 214.039 | 229,782 | none | | ok |
| 8 | Grid + H2 (SOEC) (baseload) | identical | all three | 214.039 | 229,782 | none | | ok |
| 9 | Grid + H2 (SOEC) (free) | identical | all three | 214.039 | 229,782 | none | | ok |
| 10 | Renewables + H2 (PEM), islanded (baseload) | changed | min_cost | 384.306 → 390.357 (+1.575) | 75,819 → 75,819 (-0.001) | none | 6.051 | LOOK: rise 6.051 |
| 10 | Renewables + H2 (PEM), islanded (baseload) | changed | knee | 389.650 → 395.695 (+1.552) | 73,730 → 73,730 (-0.000) | none | 6.044 | LOOK: rise 6.046 |
| 10 | Renewables + H2 (PEM), islanded (baseload) | changed | min_gwp | 409.826 → 415.862 (+1.473) | 73,034 → 73,034 (+0.000) | none | 6.036 | ok: rise = cap_fc × term |
| 11 | Renewables + H2 (PEM), islanded (flexible) | changed | min_cost | 380.640 → 386.691 (+1.590) | 73,682 → 73,681 (-0.001) | wind 686.39 → 686.51; ely 77.66 → 77.63; tank 1,320,487.42 → 1,320,347.37 | 6.051 | design moved |
| 11 | Renewables + H2 (PEM), islanded (flexible) | changed | knee | 396.387 → 402.432 (+1.525) | 71,198 → 71,198 (-0.000) | solar 159.30 → 159.29 | 6.041 | design moved |
| 11 | Renewables + H2 (PEM), islanded (flexible) | changed | min_gwp | 447.281 → 453.314 (+1.349) | 70,370 → 70,370 (+0.000) | none | 6.033 | ok: rise = cap_fc × term |
| 12 | Renewables + H2 (AE), islanded (baseload) | changed | min_cost | 379.341 → 385.392 (+1.595) | 76,137 → 76,136 (-0.001) | solar 406.76 → 406.70 | 6.051 | design moved |
| 12 | Renewables + H2 (AE), islanded (baseload) | changed | knee | 385.212 → 391.259 (+1.570) | 73,979 → 73,978 (-0.000) | solar 266.56 → 266.46 | 6.044 | design moved |
| 12 | Renewables + H2 (AE), islanded (baseload) | changed | min_gwp | 404.156 → 410.192 (+1.494) | 73,259 → 73,259 (-0.000) | none | 6.036 | ok: rise = cap_fc × term |
| 13 | Renewables + H2 (AE), islanded (flexible) | changed | min_cost | 375.715 → 381.766 (+1.611) | 73,929 → 73,928 (-0.001) | solar 343.26 → 343.19 | 6.051 | design moved |
| 13 | Renewables + H2 (AE), islanded (flexible) | changed | knee | 390.481 → 396.527 (+1.548) | 71,456 → 71,456 (-0.000) | solar 167.64 → 167.61 | 6.042 | design moved |
| 13 | Renewables + H2 (AE), islanded (flexible) | changed | min_gwp | 434.483 → 440.516 (+1.389) | 70,632 → 70,632 (+0.000) | none | 6.033 | ok: rise = cap_fc × term |
| 14 | Renewables + H2 (SOEC), islanded (baseload) | changed | min_cost | 408.793 → 414.842 (+1.480) | 87,086 → 87,082 (-0.004) | wind 762.09 → 762.18; solar 370.67 → 370.61; ely 48.73 → 48.72 | 6.049 | design moved |
| 14 | Renewables + H2 (SOEC), islanded (baseload) | changed | knee | 415.872 → 421.919 (+1.454) | 83,277 → 83,276 (-0.001) | solar 278.52 → 278.46 | 6.042 | design moved |
| 14 | Renewables + H2 (SOEC), islanded (baseload) | changed | min_gwp | 437.491 → 443.525 (+1.379) | 82,007 → 82,007 (+0.000) | none | 6.034 | ok: rise = cap_fc × term |
| 15 | Renewables + H2 (SOEC), islanded (flexible) | changed | min_cost | 406.943 → 412.993 (+1.487) | 82,403 → 82,401 (-0.003) | wind 755.39 → 755.61; solar 363.03 → 363.14; ely 49.82 → 49.79; tank 1,228,686.99 → 1,228,396.95 | 6.049 | design moved |
| 15 | Renewables + H2 (SOEC), islanded (flexible) | changed | knee | 434.599 → 440.653 (+1.393) | 78,720 → 78,720 (-0.001) | ely 55.75 → 55.77 | 6.039 | design moved |
| 15 | Renewables + H2 (SOEC), islanded (flexible) | changed | min_gwp | 536.180 → 542.213 (+1.125) | 77,493 → 77,493 (+0.000) | none | 6.032 | ok: rise = cap_fc × term |
| 16 | Grid + bought H2 (grey) (free) | changed | min_cost | 213.981 → 213.981 (+0.000) | 229,782 → 229,782 (+0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 16 | Grid + bought H2 (grey) (free) | changed | knee | 213.981 → 213.981 (+0.000) | 229,782 → 229,782 (+0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 16 | Grid + bought H2 (grey) (free) | changed | min_gwp | 213.981 → 213.981 (+0.000) | 229,782 → 229,782 (+0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 17 | Grid + bought H2 (blue) (free) | changed | min_cost | 213.981 → 213.981 (+0.000) | 229,782 → 229,782 (+0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 17 | Grid + bought H2 (blue) (free) | changed | knee | 236.733 → 239.846 (+1.315) | 227,534 → 227,534 (+0.000) | fc 72.60 → 72.41 | 3.117 | design moved |
| 17 | Grid + bought H2 (blue) (free) | changed | min_gwp | 261.115 → 267.180 (+2.323) | 225,287 → 225,287 (-0.000) | none | 6.065 | ok: rise = cap_fc × term |
| 18 | Grid + bought H2 (turquoise) (free) | changed | min_cost | 213.981 → 213.981 (+0.000) | 229,782 → 229,782 (+0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 18 | Grid + bought H2 (turquoise) (free) | changed | knee | 237.887 → 240.970 (+1.296) | 228,427 → 228,427 (+0.000) | fc 71.84 → 71.72 | 3.084 | design moved |
| 18 | Grid + bought H2 (turquoise) (free) | changed | min_gwp | 262.498 → 268.563 (+2.311) | 227,072 → 227,072 (-0.000) | none | 6.065 | ok: rise = cap_fc × term |
| 19 | Grid + bought H2 (green) (free) | changed | min_cost | 213.981 → 213.981 (+0.000) | 229,781 → 229,781 (+0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 19 | Grid + bought H2 (green) (free) | changed | knee | 481.990 → 488.056 (+1.258) | 158,910 → 158,910 (+0.000) | none | 6.065 | ok: rise = cap_fc × term |
| 19 | Grid + bought H2 (green) (free) | changed | min_gwp | 874.333 → 880.398 (+0.694) | 123,474 → 123,474 (-0.000) | none | 6.065 | ok: rise = cap_fc × term |
| 20 | Grid + H2 (PEM) — control (free) | identical | all three | 214.039 | 229,782 | none | | ok |
| 21 | Everything available — control (free) | changed | min_cost | 143.606 → 143.606 (-0.000) | 95,742 → 95,742 (-0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 21 | Everything available — control (free) | changed | knee | 169.074 → 169.074 (+0.000) | 66,464 → 66,464 (-0.000) | none | 0.000 | ok: rise = cap_fc × term |
| 21 | Everything available — control (free) | changed | min_gwp | 291.020 → 295.676 (+1.600) | 56,704 → 56,704 (-0.000) | none | 4.657 | ok: rise = cap_fc × term |
| 22 | Grid + H2 (SOEC, electric boiler) (baseload) | identical | all three | 214.039 | 229,782 | none | | ok |
| 23 | Grid + H2 (SOEC, electric boiler) (free) | identical | all three | 214.039 | 229,782 | none | | ok |
| 24 | Renewables + H2 (SOEC, electric boiler), islanded (baseload) | changed | min_cost | 407.614 → 413.664 (+1.484) | 75,783 → 75,783 (-0.000) | none | 6.049 | LOOK: rise 6.049 |
| 24 | Renewables + H2 (SOEC, electric boiler), islanded (baseload) | changed | knee | 413.017 → 419.060 (+1.463) | 74,134 → 74,134 (-0.000) | none | 6.043 | ok: rise = cap_fc × term |
| 24 | Renewables + H2 (SOEC, electric boiler), islanded (baseload) | changed | min_gwp | 428.654 → 434.690 (+1.408) | 73,584 → 73,584 (-0.000) | none | 6.037 | ok: rise = cap_fc × term |
| 25 | Renewables + H2 (SOEC, electric boiler), islanded (flexible) | changed | min_cost | 406.294 → 412.343 (+1.489) | 74,361 → 74,361 (-0.000) | none | 6.049 | ok: rise = cap_fc × term |
| 25 | Renewables + H2 (SOEC, electric boiler), islanded (flexible) | changed | knee | 422.133 → 428.175 (+1.431) | 71,967 → 71,967 (-0.000) | none | 6.042 | ok: rise = cap_fc × term |
| 25 | Renewables + H2 (SOEC, electric boiler), islanded (flexible) | changed | min_gwp | 495.382 → 501.416 (+1.218) | 71,169 → 71,169 (-0.000) | none | 6.034 | ok: rise = cap_fc × term |

11 configurations with no fuel cell identical; 24 fuel-cell points rose by exactly cap_fc × the term; 12 fuel-cell points changed design; 3 need a look.

| Reference case | Point | Cost £m/yr (change %) | Carbon t/yr (change %) | Sizes that moved |
|---|---|---|---|---|
| islanded_h2 | min_cost | 382.041 → 386.055 (+1.051) | 87,468 → 88,292 (+0.942) | wind 595.67 → 588.63; solar 712.08 → 733.15; batt_p 138.03 → 144.98; batt_e 954.80 → 1,029.48; ely 26.09 → 23.87; tank 1,253,651.95 → 1,240,096.92; fc 94.41 → 92.80 |
| islanded_h2 | min_gwp | 474.046 → 480.228 (+1.304) | 74,257 → 74,257 (+0.000) | none |
| eastgrinstead_grid | min_cost | 153.681 → 153.681 (+0.000) | 101,479 → 101,479 (-0.000) | none |
| eastgrinstead_grid | min_gwp | 311.629 → 316.618 (+1.601) | 59,652 → 59,652 (+0.000) | none |
