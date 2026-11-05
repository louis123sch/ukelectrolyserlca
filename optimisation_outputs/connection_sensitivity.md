# The grid connection's price, +/-50 %

**Verdict: halving or raising the connection's price by half does not change the design, so by the supervisor's test there is no need to go further on it for now.** The test that counts is the North Norfolk one (5 Nov 2026, the reference site, 150 MW of computing, every asset, the new cost sources, the optimiser choosing the price list): all 12 scaled points pass, no technology appears or disappears, and no built size moves by more than 0.006 % (the electrolyser; everything else by 0.001 % or less). The price does not reach the design because the connection sits on its room limit, 24.5 MW on the 33 kV list at Sall Grid, at every point of every variant, and the rest of the design is set by that limit, not by what the connection costs. What the price does move is the bill: at most 0.53 % of yearly cost (£238.9 m to £241.4 m around £240.1 m at the cheapest point) and nothing in carbon. The list choice was under test this time: each variant priced the six lists alone, dropped the same two 11 kV lists at Stody, and chose the same 33 kV list at Sall Grid from the four that survived, so neither knob moves the choice of substation or voltage either. The run took 4.5 hours (3.4 of them the five three-point frontiers).

The earlier London runs (4 Nov 2026, three fixed-list cases on the costs as they stood that afternoon, before the government and best-source figures) said the same: 35 of 36 points pass, the one failure the size-free 132 kV connection shrinking by 5.06 % at 1.5 times the build cost, with the battery moving up to 3.44 % and cost by up to 2.65 %. The national-grid list stayed dearer than the 132 kV list at every scale, by £3.17 m to £7.18 m a year. Those runs are kept below as they were; they are illustrative only, and their one lesson that survives is that the size limit matters far more than the price: capping London's 132 kV connection at its published 48.2 MW of room costs £84.55 m a year more at the cheapest point, a move no price change here comes near. The same holds at North Norfolk, where the room limit is what sets the design.

The supervisor's test (email of 4 Nov 2026). Full year 2025, hourly, three-point frontier per variant (`optimisation/sensitivity.py`, `connection`). Each row is judged against its case's central row at the same point with the cut-off rule's test: the same technologies built and no built capacity moved by more than 5%.

*One-off build cost* is the yearly annuity on the substation, cable and switchgear (`connection_cost.py`). *Yearly network charges* are the national locational charge on winter-peak demand, the local capacity charge, the national residual and local fixed charges, and the local per-MWh unit rates. The balancing charge, losses and levies are not scaled. No carbon coefficient changes in either knob.

### London, 150 MW of computing, the fixed national-grid price list (T-Demand4)

The price list holds the connection between 240.0 and 257.1 MW.

| Knob | Scale | Point | Grid MW | Wind MW | Solar MW | Battery MW | Battery MWh | Electrolyser MW | Tank kg | Fuel cell MW | Cost £ m/yr | Carbon t/yr | Test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Central | 1.0x | cheapest | 240.0 | 369.0 | 551.7 | 158.6 | 1,097.7 | 0 | 0 | 0 | 146.39 | 103,888 | reference |
| Central | 1.0x | knee | 240.0 | 514.4 | 538.3 | 159.6 | 1,143.8 | 0 | 0 | 0 | 153.10 | 89,347 | reference |
| Central | 1.0x | lowest carbon | 240.0 | 956.6 | 357.5 | 126.1 | 809.2 | 4.1 | 6,021.4 | 6.4 | 198.88 | 82,076 | reference |
| One-off build cost | 0.5x | cheapest | 240.0 | 369.0 | 551.7 | 158.6 | 1,097.7 | 0 | 0 | 0 | 144.92 | 103,888 | pass: battery energy +0.0% |
| One-off build cost | 0.5x | knee | 240.0 | 514.4 | 538.3 | 159.6 | 1,143.8 | 0 | 0 | 0 | 151.63 | 89,347 | pass: battery energy -0.0% |
| One-off build cost | 0.5x | lowest carbon | 240.0 | 956.6 | 357.5 | 126.1 | 809.2 | 4.1 | 6,021.3 | 6.4 | 197.41 | 82,076 | pass: fuel cell -0.0% |
| One-off build cost | 1.5x | cheapest | 240.0 | 369.0 | 551.7 | 158.6 | 1,097.7 | 0 | 0 | 0 | 147.87 | 103,887 | pass: battery energy -0.0% |
| One-off build cost | 1.5x | knee | 240.0 | 514.4 | 538.3 | 159.6 | 1,143.8 | 0 | 0 | 0 | 154.57 | 89,347 | pass: battery energy +0.0% |
| One-off build cost | 1.5x | lowest carbon | 240.0 | 956.6 | 357.5 | 126.1 | 809.2 | 4.1 | 6,021.4 | 6.4 | 200.36 | 82,076 | pass: fuel cell +0.0% |
| Yearly network charges | 0.5x | cheapest | 240.0 | 370.2 | 548.6 | 154.8 | 1,087.0 | 0 | 0 | 0 | 142.52 | 104,004 | pass: battery power -2.4% |
| Yearly network charges | 0.5x | knee | 240.0 | 514.0 | 538.7 | 158.6 | 1,140.0 | 0 | 0 | 0 | 149.19 | 89,385 | pass: battery power -0.6% |
| Yearly network charges | 0.5x | lowest carbon | 240.0 | 956.6 | 357.5 | 126.1 | 809.2 | 4.1 | 6,021.3 | 6.4 | 194.53 | 82,076 | pass: fuel cell -0.0% |
| Yearly network charges | 1.5x | cheapest | 240.0 | 368.6 | 551.4 | 160.9 | 1,101.5 | 0 | 0 | 0 | 150.26 | 103,876 | pass: battery power +1.4% |
| Yearly network charges | 1.5x | knee | 240.0 | 513.4 | 540.0 | 161.0 | 1,153.2 | 0 | 0 | 0 | 156.96 | 89,343 | pass: battery power +0.9% |
| Yearly network charges | 1.5x | lowest carbon | 240.0 | 956.7 | 357.5 | 126.1 | 809.1 | 4.1 | 6,057.9 | 6.4 | 203.24 | 82,076 | pass: electrolyser +0.6% |

### London, 150 MW of computing, connected at LEICESTER SQ 11KV at 132 kV, size free up to 1.43x the load (room ignored)

The price list holds the connection between 20.0 and 240.0 MW.

| Knob | Scale | Point | Grid MW | Wind MW | Solar MW | Battery MW | Battery MWh | Electrolyser MW | Tank kg | Fuel cell MW | Cost £ m/yr | Carbon t/yr | Test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Central | 1.0x | cheapest | 157.6 | 369.5 | 553.5 | 158.3 | 1,096.9 | 0 | 0 | 0 | 141.24 | 103,563 | reference |
| Central | 1.0x | knee | 149.7 | 517.0 | 541.2 | 160.5 | 1,155.1 | 0 | 0 | 0 | 147.92 | 89,179 | reference |
| Central | 1.0x | lowest carbon | 174.5 | 960.3 | 357.6 | 123.8 | 794.0 | 4.8 | 7,167.1 | 7.6 | 194.38 | 81,987 | reference |
| One-off build cost | 0.5x | cheapest | 161.3 | 369.5 | 553.5 | 158.3 | 1,096.9 | 0 | 0 | 0 | 140.49 | 103,562 | pass: grid +2.3% |
| One-off build cost | 0.5x | knee | 154.7 | 516.6 | 541.2 | 160.5 | 1,155.0 | 0 | 0 | 0 | 147.22 | 89,179 | pass: grid +3.3% |
| One-off build cost | 0.5x | lowest carbon | 174.5 | 960.3 | 357.6 | 123.8 | 794.0 | 4.8 | 7,166.4 | 7.6 | 193.57 | 81,987 | pass: electrolyser -0.0% |
| One-off build cost | 1.5x | cheapest | 149.6 | 369.6 | 553.5 | 158.1 | 1,096.3 | 0 | 0 | 0 | 141.95 | 103,554 | FAIL: grid -5.1% |
| One-off build cost | 1.5x | knee | 144.3 | 517.4 | 541.4 | 160.6 | 1,156.1 | 0 | 0 | 0 | 148.61 | 89,176 | pass: grid -3.6% |
| One-off build cost | 1.5x | lowest carbon | 174.5 | 960.3 | 357.6 | 123.8 | 794.0 | 4.8 | 7,168.1 | 7.6 | 195.18 | 81,987 | pass: fuel cell +0.0% |
| Yearly network charges | 0.5x | cheapest | 161.0 | 374.2 | 546.5 | 152.8 | 1,074.8 | 0 | 0 | 0 | 139.36 | 103,452 | pass: battery power -3.4% |
| Yearly network charges | 0.5x | knee | 154.3 | 519.4 | 537.1 | 157.7 | 1,141.1 | 0 | 0 | 0 | 146.14 | 89,142 | pass: grid +3.1% |
| Yearly network charges | 0.5x | lowest carbon | 174.5 | 960.3 | 357.6 | 123.8 | 794.0 | 4.8 | 7,165.6 | 7.6 | 191.95 | 81,987 | pass: electrolyser -0.0% |
| Yearly network charges | 1.5x | cheapest | 151.2 | 368.8 | 559.6 | 162.6 | 1,128.1 | 0 | 0 | 0 | 143.08 | 103,185 | pass: grid -4.1% |
| Yearly network charges | 1.5x | knee | 145.2 | 517.9 | 543.7 | 162.9 | 1,171.7 | 0 | 0 | 0 | 149.90 | 89,053 | pass: grid -3.0% |
| Yearly network charges | 1.5x | lowest carbon | 174.5 | 960.4 | 357.7 | 123.8 | 793.3 | 4.9 | 7,207.4 | 7.6 | 196.79 | 81,987 | pass: fuel cell +0.6% |

### London, 150 MW of computing, connected at LEICESTER SQ 11KV at 132 kV, capped at the room it publishes

The price list holds the connection between 20.0 and 48.2 MW.

| Knob | Scale | Point | Grid MW | Wind MW | Solar MW | Battery MW | Battery MWh | Electrolyser MW | Tank kg | Fuel cell MW | Cost £ m/yr | Carbon t/yr | Test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Central | 1.0x | cheapest | 48.2 | 577.7 | 764.5 | 154.0 | 2,004.5 | 12.7 | 774,743.7 | 60.3 | 225.79 | 146,834 | reference |
| Central | 1.0x | knee | 48.2 | 860.4 | 916.9 | 204.8 | 3,280.8 | 5.0 | 193,479.8 | 23.7 | 241.08 | 115,565 | reference |
| Central | 1.0x | lowest carbon | 48.2 | 1,433.9 | 393.9 | 135.5 | 1,607.8 | 95.7 | 108,353.6 | 39.3 | 295.71 | 99,931 | reference |
| One-off build cost | 0.5x | cheapest | 48.2 | 577.7 | 764.5 | 154.0 | 2,004.5 | 12.7 | 774,745.3 | 60.3 | 225.55 | 146,834 | pass: battery power +0.0% |
| One-off build cost | 0.5x | knee | 48.2 | 860.4 | 916.9 | 204.8 | 3,280.8 | 5.0 | 193,480.3 | 23.7 | 240.84 | 115,565 | pass: tank +0.0% |
| One-off build cost | 0.5x | lowest carbon | 48.2 | 1,433.9 | 393.9 | 135.5 | 1,607.8 | 95.7 | 108,353.6 | 39.3 | 295.48 | 99,931 | pass: battery energy +0.0% |
| One-off build cost | 1.5x | cheapest | 48.2 | 577.7 | 764.5 | 154.0 | 2,004.5 | 12.7 | 774,742.1 | 60.3 | 226.03 | 146,834 | pass: battery power -0.0% |
| One-off build cost | 1.5x | knee | 48.2 | 860.4 | 916.9 | 204.8 | 3,280.8 | 5.0 | 193,479.2 | 23.7 | 241.31 | 115,565 | pass: tank -0.0% |
| One-off build cost | 1.5x | lowest carbon | 48.2 | 1,433.9 | 393.9 | 135.5 | 1,607.8 | 95.7 | 108,353.6 | 39.3 | 295.95 | 99,931 | pass: battery energy -0.0% |
| Yearly network charges | 0.5x | cheapest | 48.2 | 577.7 | 764.5 | 154.0 | 2,004.5 | 12.7 | 774,754.5 | 60.3 | 224.28 | 146,835 | pass: battery power +0.0% |
| Yearly network charges | 0.5x | knee | 48.2 | 860.3 | 916.9 | 204.8 | 3,280.8 | 5.0 | 193,483.4 | 23.7 | 239.57 | 115,565 | pass: tank +0.0% |
| Yearly network charges | 0.5x | lowest carbon | 48.2 | 1,433.9 | 393.9 | 135.5 | 1,607.8 | 95.7 | 108,353.6 | 39.3 | 294.21 | 99,931 | pass: battery energy +0.0% |
| Yearly network charges | 1.5x | cheapest | 48.2 | 577.7 | 764.5 | 154.0 | 2,004.5 | 12.7 | 774,732.9 | 60.3 | 227.30 | 146,833 | pass: battery power -0.0% |
| Yearly network charges | 1.5x | knee | 48.2 | 860.4 | 916.8 | 204.8 | 3,280.8 | 5.0 | 193,476.1 | 23.7 | 242.58 | 115,565 | pass: tank -0.0% |
| Yearly network charges | 1.5x | lowest carbon | 48.2 | 1,433.9 | 393.9 | 135.5 | 1,607.8 | 95.7 | 108,353.6 | 39.3 | 297.22 | 99,931 | pass: battery energy -0.0% |

### North Norfolk, 150 MW of computing, the optimiser choosing the price list, each capped at the room its substation publishes (the reference site for conclusions)

The price list holds the connection between 0.0 and 24.5 MW.

| Knob | Scale | Point | Grid MW | Wind MW | Solar MW | Battery MW | Battery MWh | Electrolyser MW | Tank kg | Fuel cell MW | Cost £ m/yr | Carbon t/yr | Test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Central | 1.0x | cheapest | 24.5 | 589.9 | 330.3 | 121.2 | 2,211.2 | 6.3 | 197,495.3 | 34.0 | 240.14 | 75,474 | reference |
| Central | 1.0x | knee | 24.5 | 662.9 | 280.4 | 77.7 | 916.5 | 29.0 | 299,125.3 | 86.0 | 256.42 | 68,797 | reference |
| Central | 1.0x | lowest carbon | 24.5 | 841.0 | 207.8 | 28.3 | 113.9 | 110.7 | 260,849.2 | 135.8 | 307.94 | 65,458 | reference |
| One-off build cost | 0.5x | cheapest | 24.5 | 589.9 | 330.3 | 121.2 | 2,211.2 | 6.3 | 197,495.2 | 34.0 | 239.49 | 75,475 | pass: electrolyser -0.0% |
| One-off build cost | 0.5x | knee | 24.5 | 662.9 | 280.4 | 77.7 | 916.5 | 29.0 | 299,125.5 | 86.0 | 255.77 | 68,797 | pass: electrolyser -0.0% |
| One-off build cost | 0.5x | lowest carbon | 24.5 | 841.0 | 207.8 | 28.3 | 113.9 | 110.7 | 260,849.2 | 135.8 | 307.29 | 65,458 | pass: battery power -0.0% |
| One-off build cost | 1.5x | cheapest | 24.5 | 589.9 | 330.3 | 121.2 | 2,211.2 | 6.3 | 197,495.5 | 34.0 | 240.80 | 75,474 | pass: electrolyser +0.0% |
| One-off build cost | 1.5x | knee | 24.5 | 662.9 | 280.4 | 77.7 | 916.5 | 29.0 | 299,125.2 | 86.0 | 257.07 | 68,797 | pass: electrolyser +0.0% |
| One-off build cost | 1.5x | lowest carbon | 24.5 | 841.0 | 207.8 | 28.3 | 113.9 | 110.7 | 260,849.9 | 135.8 | 308.59 | 65,458 | pass: battery power -0.0% |
| Yearly network charges | 0.5x | cheapest | 24.5 | 589.9 | 330.3 | 121.2 | 2,211.2 | 6.3 | 197,495.1 | 34.0 | 238.88 | 75,475 | pass: electrolyser -0.0% |
| Yearly network charges | 0.5x | knee | 24.5 | 662.9 | 280.4 | 77.7 | 916.5 | 29.0 | 299,125.5 | 86.0 | 255.16 | 68,797 | pass: electrolyser -0.0% |
| Yearly network charges | 0.5x | lowest carbon | 24.5 | 841.0 | 207.8 | 28.3 | 113.9 | 110.7 | 260,849.2 | 135.8 | 306.68 | 65,458 | pass: battery power -0.0% |
| Yearly network charges | 1.5x | cheapest | 24.5 | 589.9 | 330.3 | 121.2 | 2,211.2 | 6.3 | 197,495.6 | 34.0 | 241.40 | 75,474 | pass: electrolyser +0.0% |
| Yearly network charges | 1.5x | knee | 24.5 | 662.9 | 280.4 | 77.7 | 916.5 | 29.0 | 299,125.1 | 86.0 | 257.68 | 68,797 | pass: electrolyser +0.0% |
| Yearly network charges | 1.5x | lowest carbon | 24.5 | 841.0 | 207.8 | 28.3 | 113.9 | 110.7 | 260,849.2 | 135.8 | 309.20 | 65,458 | pass: battery power +0.0% |

### Which price list is cheaper at each scale

The cheapest point on each of the two lists, £ m a year. The fixed-list runs cannot switch list themselves, so this is the check on whether the choice would flip.

| Knob | Scale | National-grid list | 132 kV list | Gap (national less 132 kV) |
|---|---|---|---|---|
| Central | 1.0x | 146.39 | 141.24 | +5.16 |
| One-off build cost | 0.5x | 144.92 | 140.49 | +4.43 |
| One-off build cost | 1.5x | 147.87 | 141.95 | +5.92 |
| Yearly network charges | 0.5x | 142.52 | 139.36 | +3.17 |
| Yearly network charges | 1.5x | 150.26 | 143.08 | +7.18 |

### Summary

47 of 48 points pass the test.
- london_150_leicester_sq_cap, one-off build cost at 1.5x, cheapest: grid -5.1%
