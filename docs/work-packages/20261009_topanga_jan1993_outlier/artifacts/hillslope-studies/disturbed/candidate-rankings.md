# Candidate Disturbed Ranking Validation

2026-10-10. Fresh 96-case, 100-year container run with adopted defaults,
including young forest and low-severity forest RRINIT 6 cm.
Candidate is unreleased CHRQIN normalization; reference is wepp_261009.
Hillslope sensitivity only, not channel validation or promotion approval.

## Test Matrix Analysis Results

Analysis of 96 hillslope simulations across:
- 4 soil textures (clay loam, loam, sand loam, silt loam)
- 6 vegetation types (forest, deciduous forest, mixed forest, shrub, tall grass, young forest)
- 4 burn severities (unburned, low, moderate, high)

**Canonical climate**: MC KENZIE BRIDGE RS, OR - synthetic 2000-2099, seed 26109, 1,205.406 mm/yr precipitation

**Canonical slope**: 87.9 m variable profile (length-weighted average 38.56% grade)

**Soil format**: 9002 with hydrophobicity parameters

### Forest-Family Burn Directionality Assessment

These rows compare the existing generic burned forest managements against each forest-family unburned baseline. Deciduous, mixed and young forest use their distinct unburned managements at severity `0`, then reuse `Low_Severity_Fire.man`, `Moderate_Severity_Fire.man`, and `High_Severity_Fire.man` for burn severities `1..3`.

This diagnostic asks whether burned matched-event sums exceed unburned sums for runoff, sediment delivery and event peaks. It does not establish physical correctness, a full severity ranking, or a peak-flow volume.

| Veg Type | Severity | Runoff Ratio | Runoff Burned> Share | Sediment Ratio | Peakflow Ratio | Burned Higher on All Three? |
|----------|----------|-------------:|---------------------:|---------------:|---------------:|------------------------|
| forest | low | 1.15x | 81.3% | 14.13x | 0.81x | no |
| forest | moderate | 1.16x | 79.0% | 25.05x | 0.58x | no |
| forest | high | 1.21x | 78.8% | 110.33x | 0.89x | no |
| deciduous forest | low | 1.14x | 77.2% | 25.92x | 0.81x | no |
| deciduous forest | moderate | 1.15x | 75.3% | 45.99x | 0.59x | no |
| deciduous forest | high | 1.21x | 76.1% | 201.46x | 0.88x | no |
| mixed forest | low | 1.15x | 79.8% | 28.77x | 0.78x | no |
| mixed forest | moderate | 1.16x | 78.8% | 51.05x | 0.58x | no |
| mixed forest | high | 1.22x | 82.1% | 223.23x | 0.86x | no |
| young forest | low | 1.10x | 84.7% | 5.57x | 0.81x | no |
| young forest | moderate | 1.11x | 80.3% | 9.88x | 0.59x | no |
| young forest | high | 1.16x | 79.9% | 43.83x | 0.84x | no |

These matched-event rankings are descriptive, not an acceptance gate. Use full-record totals and one-sided-event counts below; inspect magnitudes and rare events before drawing a parameterization conclusion.

### Full-Record Totals and One-Sided Events

Full totals include every record independently; paired comparisons do not zero-fill absent events.

| Texture | Vegetation | Severity | Burned-only EBE | Unburned-only EBE | Burned-only peak | Unburned-only peak | Full runoff ratio | Full sediment ratio |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| clay loam | forest | low | 788 | 175 | 730 | 170 | 1.28x | 15.47x |
| clay loam | forest | moderate | 933 | 281 | 851 | 281 | 1.30x | 25.66x |
| clay loam | forest | high | 1553 | 371 | 1394 | 368 | 1.45x | 98.34x |
| clay loam | deciduous forest | low | 850 | 207 | 789 | 205 | 1.28x | 39.52x |
| clay loam | deciduous forest | moderate | 936 | 254 | 852 | 258 | 1.30x | 65.55x |
| clay loam | deciduous forest | high | 1503 | 291 | 1343 | 293 | 1.45x | 251.18x |
| clay loam | mixed forest | low | 795 | 73 | 718 | 79 | 1.30x | 49.58x |
| clay loam | mixed forest | moderate | 880 | 119 | 778 | 129 | 1.33x | 82.23x |
| clay loam | mixed forest | high | 1493 | 202 | 1315 | 210 | 1.48x | 315.12x |
| clay loam | shrub | low | 849 | 254 | 776 | 255 | 1.24x | 2.59x |
| clay loam | shrub | moderate | 1023 | 274 | 913 | 280 | 1.28x | 4.07x |
| clay loam | shrub | high | 1453 | 350 | 1281 | 355 | 1.39x | 14.86x |
| clay loam | tall grass | low | 227 | 74 | 208 | 69 | 1.06x | 1.32x |
| clay loam | tall grass | moderate | 288 | 94 | 253 | 90 | 1.07x | 2.18x |
| clay loam | tall grass | high | 826 | 186 | 741 | 189 | 1.23x | 25.10x |
| clay loam | young forest | low | 384 | 57 | 340 | 70 | 1.12x | 5.32x |
| clay loam | young forest | moderate | 553 | 187 | 482 | 202 | 1.14x | 8.82x |
| clay loam | young forest | high | 1196 | 300 | 1044 | 308 | 1.28x | 33.79x |
| loam | forest | low | 890 | 132 | 822 | 131 | 1.41x | 14.47x |
| loam | forest | moderate | 1050 | 230 | 938 | 231 | 1.45x | 28.92x |
| loam | forest | high | 2144 | 309 | 1844 | 311 | 1.75x | 318.72x |
| loam | deciduous forest | low | 931 | 161 | 881 | 160 | 1.41x | 17.18x |
| loam | deciduous forest | moderate | 1033 | 201 | 941 | 204 | 1.45x | 34.33x |
| loam | deciduous forest | high | 2092 | 245 | 1815 | 252 | 1.75x | 378.32x |
| loam | mixed forest | low | 898 | 53 | 821 | 55 | 1.44x | 16.90x |
| loam | mixed forest | moderate | 1002 | 95 | 882 | 100 | 1.48x | 33.78x |
| loam | mixed forest | high | 2099 | 177 | 1787 | 179 | 1.79x | 372.26x |
| loam | shrub | low | 871 | 225 | 789 | 220 | 1.30x | 3.52x |
| loam | shrub | moderate | 1008 | 243 | 901 | 243 | 1.35x | 6.97x |
| loam | shrub | high | 1810 | 315 | 1575 | 319 | 1.54x | 49.06x |
| loam | tall grass | low | 246 | 63 | 223 | 63 | 1.08x | 1.22x |
| loam | tall grass | moderate | 290 | 83 | 255 | 75 | 1.08x | 2.20x |
| loam | tall grass | high | 760 | 163 | 690 | 164 | 1.27x | 22.05x |
| loam | young forest | low | 413 | 43 | 388 | 56 | 1.17x | 8.13x |
| loam | young forest | moderate | 595 | 163 | 524 | 176 | 1.19x | 16.24x |
| loam | young forest | high | 1713 | 266 | 1455 | 281 | 1.45x | 178.97x |
| sand loam | forest | low | 282 | 81 | 253 | 76 | 1.29x | n/a |
| sand loam | forest | moderate | 331 | 131 | 308 | 123 | 1.31x | n/a |
| sand loam | forest | high | 3260 | 221 | 2709 | 209 | 4.06x | n/a |
| sand loam | deciduous forest | low | 312 | 88 | 286 | 93 | 1.31x | n/a |
| sand loam | deciduous forest | moderate | 322 | 99 | 304 | 103 | 1.33x | n/a |
| sand loam | deciduous forest | high | 3245 | 183 | 2699 | 183 | 4.13x | n/a |
| sand loam | mixed forest | low | 257 | 24 | 233 | 28 | 1.32x | n/a |
| sand loam | mixed forest | moderate | 280 | 48 | 266 | 53 | 1.34x | n/a |
| sand loam | mixed forest | high | 3232 | 161 | 2686 | 158 | 4.16x | n/a |
| sand loam | shrub | low | 334 | 126 | 302 | 125 | 1.22x | 54.83x |
| sand loam | shrub | moderate | 364 | 138 | 330 | 134 | 1.25x | 119.50x |
| sand loam | shrub | high | 2892 | 266 | 2417 | 248 | 3.29x | 9380.50x |
| sand loam | tall grass | low | 75 | 32 | 71 | 31 | 1.04x | 1.04x |
| sand loam | tall grass | moderate | 98 | 44 | 94 | 46 | 1.03x | 1.87x |
| sand loam | tall grass | high | 236 | 113 | 223 | 109 | 1.15x | 35.13x |
| sand loam | young forest | low | 161 | 30 | 134 | 33 | 1.15x | n/a |
| sand loam | young forest | moderate | 229 | 99 | 206 | 97 | 1.17x | n/a |
| sand loam | young forest | high | 3211 | 242 | 2664 | 240 | 3.62x | n/a |
| silt loam | forest | low | 525 | 118 | 502 | 117 | 1.33x | 7.95x |
| silt loam | forest | moderate | 643 | 203 | 597 | 207 | 1.36x | 19.72x |
| silt loam | forest | high | 1831 | 268 | 1571 | 266 | 1.82x | 354.79x |
| silt loam | deciduous forest | low | 549 | 133 | 533 | 131 | 1.33x | 7.16x |
| silt loam | deciduous forest | moderate | 622 | 173 | 585 | 178 | 1.36x | 17.75x |
| silt loam | deciduous forest | high | 1777 | 205 | 1527 | 205 | 1.82x | 319.31x |
| silt loam | mixed forest | low | 511 | 46 | 488 | 46 | 1.36x | 6.93x |
| silt loam | mixed forest | moderate | 585 | 87 | 541 | 94 | 1.39x | 17.18x |
| silt loam | mixed forest | high | 1777 | 156 | 1516 | 154 | 1.85x | 309.01x |
| silt loam | shrub | low | 592 | 185 | 557 | 187 | 1.25x | 6.25x |
| silt loam | shrub | moderate | 678 | 208 | 644 | 201 | 1.29x | 14.24x |
| silt loam | shrub | high | 1588 | 263 | 1367 | 266 | 1.58x | 150.19x |
| silt loam | tall grass | low | 142 | 61 | 135 | 54 | 1.06x | 1.12x |
| silt loam | tall grass | moderate | 182 | 67 | 177 | 69 | 1.07x | 2.16x |
| silt loam | tall grass | high | 520 | 145 | 488 | 154 | 1.23x | 9.31x |
| silt loam | young forest | low | 242 | 44 | 242 | 44 | 1.13x | 5.02x |
| silt loam | young forest | moderate | 375 | 144 | 355 | 152 | 1.16x | 12.46x |
| silt loam | young forest | high | 1595 | 241 | 1359 | 241 | 1.55x | 224.08x |

### Runoff Event Counts (Burned vs Unburned)

Event counts compare burned vs unburned runoff by matching day/month/year across
all 4 soil textures. Results aggregated from 100-year simulations (96 total runs).

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 5,685 | 4,570 | 65 | 1,050 |
| forest | moderate | 5,346 | 4,163 | 74 | 1,109 |
| forest | high | 5,022 | 3,927 | 37 | 1,058 |
| deciduous forest | low | 5,528 | 4,218 | 64 | 1,246 |
| deciduous forest | moderate | 5,390 | 4,001 | 75 | 1,314 |
| deciduous forest | high | 5,193 | 3,915 | 51 | 1,227 |
| mixed forest | low | 5,709 | 4,503 | 64 | 1,142 |
| mixed forest | moderate | 5,556 | 4,297 | 106 | 1,153 |
| mixed forest | high | 5,209 | 4,240 | 43 | 926 |
| shrub | low | 6,343 | 4,782 | 123 | 1,438 |
| shrub | moderate | 6,270 | 4,762 | 140 | 1,368 |
| shrub | high | 5,939 | 4,507 | 105 | 1,327 |
| tall grass | low | 6,943 | 2,669 | 1,587 | 2,687 |
| tall grass | moderate | 6,885 | 2,852 | 1,093 | 2,940 |
| tall grass | high | 6,566 | 3,100 | 461 | 3,005 |
| young forest | low | 6,970 | 5,818 | 98 | 1,054 |
| young forest | moderate | 6,551 | 5,179 | 99 | 1,273 |
| young forest | high | 6,095 | 4,809 | 75 | 1,211 |

### Sediment Delivery Event Counts (Burned vs Unburned)

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 5,685 | 549 | 5,115 | 21 |
| forest | moderate | 5,346 | 556 | 4,762 | 28 |
| forest | high | 5,022 | 1,113 | 3,901 | 8 |
| deciduous forest | low | 5,528 | 545 | 4,979 | 4 |
| deciduous forest | moderate | 5,390 | 561 | 4,825 | 4 |
| deciduous forest | high | 5,193 | 1,132 | 4,061 | 0 |
| mixed forest | low | 5,709 | 550 | 5,156 | 3 |
| mixed forest | moderate | 5,556 | 564 | 4,990 | 2 |
| mixed forest | high | 5,209 | 1,126 | 4,083 | 0 |
| shrub | low | 6,343 | 1,413 | 4,432 | 498 |
| shrub | moderate | 6,270 | 1,471 | 4,199 | 600 |
| shrub | high | 5,939 | 2,686 | 3,031 | 222 |
| tall grass | low | 6,943 | 164 | 6,765 | 14 |
| tall grass | moderate | 6,885 | 194 | 6,680 | 11 |
| tall grass | high | 6,566 | 1,164 | 5,393 | 9 |
| young forest | low | 6,970 | 542 | 6,254 | 174 |
| young forest | moderate | 6,551 | 567 | 5,719 | 265 |
| young forest | high | 6,095 | 1,194 | 4,796 | 105 |

### Peakflow Event Counts (Burned vs Unburned)

Event counts compare burned vs unburned peak discharge by matching
simulation year/julian day in `H*.pass.dat` EVENT records.

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 5,247 | 2,334 | 22 | 2,891 |
| forest | moderate | 4,899 | 1,843 | 16 | 3,040 |
| forest | high | 4,587 | 1,658 | 19 | 2,910 |
| deciduous forest | low | 5,065 | 1,679 | 18 | 3,368 |
| deciduous forest | moderate | 4,911 | 1,310 | 20 | 3,581 |
| deciduous forest | high | 4,721 | 1,330 | 27 | 3,364 |
| mixed forest | low | 5,294 | 1,745 | 37 | 3,512 |
| mixed forest | moderate | 5,126 | 1,701 | 31 | 3,394 |
| mixed forest | high | 4,801 | 1,829 | 19 | 2,953 |
| shrub | low | 5,846 | 2,198 | 29 | 3,619 |
| shrub | moderate | 5,775 | 1,872 | 28 | 3,875 |
| shrub | high | 5,445 | 1,817 | 29 | 3,599 |
| tall grass | low | 6,424 | 1,806 | 392 | 4,226 |
| tall grass | moderate | 6,361 | 1,608 | 377 | 4,376 |
| tall grass | high | 6,025 | 1,504 | 361 | 4,160 |
| young forest | low | 6,450 | 2,859 | 50 | 3,541 |
| young forest | moderate | 6,026 | 2,364 | 29 | 3,633 |
| young forest | high | 5,583 | 2,110 | 20 | 3,453 |

### Runoff Descriptive Statistics (mm)

Statistics aggregated across all 4 soil textures for 100-year simulations.

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 17.32 | 17.93 | 11.74 | 96,021 |
| | | unburned | 15.02 | 16.64 | 9.72 | 83,633 |
| forest | moderate | burned | 17.83 | 18.63 | 11.99 | 92,716 |
| | | unburned | 15.40 | 17.04 | 9.81 | 79,985 |
| forest | high | burned | 19.48 | 19.86 | 12.90 | 92,192 |
| | | unburned | 15.91 | 17.63 | 9.97 | 76,075 |
| deciduous forest | low | burned | 17.56 | 18.14 | 11.96 | 94,184 |
| | | unburned | 15.35 | 17.36 | 9.59 | 82,750 |
| deciduous forest | moderate | burned | 17.94 | 18.62 | 12.06 | 93,862 |
| | | unburned | 15.53 | 17.52 | 9.65 | 81,386 |
| deciduous forest | high | burned | 19.42 | 19.67 | 13.00 | 95,395 |
| | | unburned | 15.98 | 17.96 | 9.80 | 79,076 |
| mixed forest | low | burned | 17.47 | 17.83 | 11.93 | 97,472 |
| | | unburned | 15.07 | 16.96 | 9.60 | 84,533 |
| mixed forest | moderate | burned | 17.80 | 18.30 | 12.12 | 96,667 |
| | | unburned | 15.27 | 17.17 | 9.82 | 83,105 |
| mixed forest | high | burned | 19.47 | 19.52 | 13.15 | 96,308 |
| | | unburned | 15.88 | 17.78 | 10.07 | 79,223 |
| shrub | low | burned | 17.34 | 18.28 | 11.75 | 107,695 |
| | | unburned | 15.52 | 17.19 | 10.04 | 95,842 |
| shrub | moderate | burned | 17.53 | 18.55 | 11.59 | 107,703 |
| | | unburned | 15.54 | 17.27 | 10.01 | 94,723 |
| shrub | high | burned | 19.22 | 20.13 | 12.30 | 107,038 |
| | | unburned | 16.15 | 17.85 | 10.35 | 90,585 |
| tall grass | low | burned | 15.82 | 17.09 | 10.60 | 107,993 |
| | | unburned | 15.35 | 16.77 | 10.02 | 104,626 |
| tall grass | moderate | burned | 15.87 | 17.21 | 10.45 | 107,492 |
| | | unburned | 15.43 | 16.83 | 10.10 | 104,182 |
| tall grass | high | burned | 16.94 | 18.48 | 10.98 | 109,133 |
| | | unburned | 15.68 | 17.21 | 10.07 | 100,303 |
| young forest | low | burned | 16.25 | 16.85 | 11.12 | 110,818 |
| | | unburned | 14.79 | 16.41 | 9.73 | 101,172 |
| young forest | moderate | burned | 16.96 | 17.52 | 11.67 | 108,274 |
| | | unburned | 15.28 | 16.82 | 10.07 | 97,524 |
| young forest | high | burned | 18.53 | 18.84 | 12.64 | 106,586 |
| | | unburned | 15.90 | 17.54 | 10.21 | 92,137 |

### Sediment Delivery Descriptive Statistics (kg/m)

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 0.170 | 0.857 | 0.000 | 1353.2 |
| | | unburned | 0.012 | 0.079 | 0.000 | 95.8 |
| forest | moderate | burned | 0.329 | 1.523 | 0.000 | 2395.2 |
| | | unburned | 0.013 | 0.082 | 0.000 | 95.6 |
| forest | high | burned | 1.985 | 5.744 | 0.000 | 10547.4 |
| | | unburned | 0.014 | 0.084 | 0.000 | 95.6 |
| deciduous forest | low | burned | 0.174 | 0.868 | 0.000 | 1345.3 |
| | | unburned | 0.008 | 0.072 | 0.000 | 51.9 |
| deciduous forest | moderate | burned | 0.326 | 1.517 | 0.000 | 2387.0 |
| | | unburned | 0.008 | 0.073 | 0.000 | 51.9 |
| deciduous forest | high | burned | 1.873 | 5.590 | 0.000 | 10455.7 |
| | | unburned | 0.008 | 0.074 | 0.000 | 51.9 |
| mixed forest | low | burned | 0.170 | 0.856 | 0.000 | 1349.3 |
| | | unburned | 0.007 | 0.070 | 0.000 | 46.9 |
| mixed forest | moderate | burned | 0.318 | 1.496 | 0.000 | 2394.2 |
| | | unburned | 0.007 | 0.071 | 0.000 | 46.9 |
| mixed forest | high | burned | 1.860 | 5.575 | 0.000 | 10469.7 |
| | | unburned | 0.007 | 0.072 | 0.000 | 46.9 |
| shrub | low | burned | 0.299 | 0.919 | 0.025 | 2519.0 |
| | | unburned | 0.102 | 0.315 | 0.025 | 926.4 |
| shrub | moderate | burned | 0.529 | 1.604 | 0.000 | 4266.1 |
| | | unburned | 0.103 | 0.317 | 0.025 | 924.2 |
| shrub | high | burned | 2.895 | 5.833 | 0.425 | 17989.3 |
| | | unburned | 0.106 | 0.323 | 0.025 | 920.3 |
| tall grass | low | burned | 0.069 | 0.527 | 0.000 | 622.4 |
| | | unburned | 0.056 | 0.442 | 0.000 | 492.6 |
| tall grass | moderate | burned | 0.122 | 0.907 | 0.000 | 1073.4 |
| | | unburned | 0.056 | 0.443 | 0.000 | 492.6 |
| tall grass | high | burned | 1.153 | 4.440 | 0.000 | 10197.4 |
| | | unburned | 0.059 | 0.453 | 0.000 | 492.6 |
| young forest | low | burned | 0.144 | 0.783 | 0.000 | 1382.6 |
| | | unburned | 0.026 | 0.127 | 0.000 | 248.3 |
| young forest | moderate | burned | 0.278 | 1.390 | 0.000 | 2441.1 |
| | | unburned | 0.027 | 0.130 | 0.000 | 247.2 |
| young forest | high | burned | 1.685 | 5.271 | 0.000 | 10791.5 |
| | | unburned | 0.028 | 0.134 | 0.000 | 246.2 |

### Peakflow Descriptive Statistics (m^3/s)

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 0.005 | 0.008 | 0.004 | 26.350 |
| | | unburned | 0.006 | 0.005 | 0.007 | 32.481 |
| forest | moderate | burned | 0.004 | 0.009 | 0.002 | 18.288 |
| | | unburned | 0.006 | 0.006 | 0.007 | 31.339 |
| forest | high | burned | 0.007 | 0.019 | 0.002 | 27.389 |
| | | unburned | 0.007 | 0.006 | 0.007 | 30.637 |
| deciduous forest | low | burned | 0.005 | 0.008 | 0.004 | 25.464 |
| | | unburned | 0.006 | 0.005 | 0.007 | 31.442 |
| deciduous forest | moderate | burned | 0.004 | 0.009 | 0.002 | 18.192 |
| | | unburned | 0.006 | 0.005 | 0.007 | 30.891 |
| deciduous forest | high | burned | 0.007 | 0.018 | 0.002 | 26.564 |
| | | unburned | 0.006 | 0.005 | 0.007 | 30.310 |
| mixed forest | low | burned | 0.005 | 0.008 | 0.004 | 25.943 |
| | | unburned | 0.006 | 0.005 | 0.007 | 33.204 |
| mixed forest | moderate | burned | 0.004 | 0.008 | 0.002 | 18.620 |
| | | unburned | 0.006 | 0.005 | 0.007 | 32.232 |
| mixed forest | high | burned | 0.007 | 0.018 | 0.002 | 26.803 |
| | | unburned | 0.006 | 0.005 | 0.007 | 31.146 |
| shrub | low | burned | 0.004 | 0.008 | 0.003 | 24.330 |
| | | unburned | 0.005 | 0.005 | 0.005 | 31.270 |
| shrub | moderate | burned | 0.004 | 0.009 | 0.002 | 19.918 |
| | | unburned | 0.005 | 0.005 | 0.005 | 31.081 |
| shrub | high | burned | 0.007 | 0.017 | 0.002 | 28.166 |
| | | unburned | 0.006 | 0.005 | 0.005 | 30.306 |
| tall grass | low | burned | 0.003 | 0.006 | 0.002 | 21.774 |
| | | unburned | 0.004 | 0.006 | 0.003 | 23.767 |
| tall grass | moderate | burned | 0.003 | 0.006 | 0.002 | 18.135 |
| | | unburned | 0.004 | 0.006 | 0.003 | 23.614 |
| tall grass | high | burned | 0.003 | 0.007 | 0.002 | 18.889 |
| | | unburned | 0.004 | 0.006 | 0.003 | 22.932 |
| young forest | low | burned | 0.005 | 0.007 | 0.004 | 29.883 |
| | | unburned | 0.006 | 0.005 | 0.006 | 36.843 |
| young forest | moderate | burned | 0.004 | 0.008 | 0.002 | 20.558 |
| | | unburned | 0.006 | 0.005 | 0.006 | 35.132 |
| young forest | high | burned | 0.006 | 0.017 | 0.002 | 28.387 |
| | | unburned | 0.006 | 0.005 | 0.006 | 33.793 |

### Detailed Results by Soil Texture

#### Runoff Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 2,191 | 1,717 | 46 | 428 |
| clay loam | forest | moderate | 2,085 | 1,586 | 50 | 449 |
| clay loam | forest | high | 1,995 | 1,552 | 26 | 417 |
| clay loam | deciduous forest | low | 2,129 | 1,591 | 41 | 497 |
| clay loam | deciduous forest | moderate | 2,082 | 1,492 | 60 | 530 |
| clay loam | deciduous forest | high | 2,045 | 1,514 | 33 | 498 |
| clay loam | mixed forest | low | 2,184 | 1,683 | 45 | 456 |
| clay loam | mixed forest | moderate | 2,138 | 1,604 | 60 | 474 |
| clay loam | mixed forest | high | 2,055 | 1,665 | 25 | 365 |
| clay loam | shrub | low | 2,396 | 1,779 | 62 | 555 |
| clay loam | shrub | moderate | 2,376 | 1,773 | 72 | 531 |
| clay loam | shrub | high | 2,300 | 1,740 | 54 | 506 |
| clay loam | tall grass | low | 2,577 | 944 | 645 | 988 |
| clay loam | tall grass | moderate | 2,557 | 1,033 | 449 | 1,075 |
| clay loam | tall grass | high | 2,465 | 1,170 | 190 | 1,105 |
| clay loam | young forest | low | 2,595 | 2,142 | 48 | 405 |
| clay loam | young forest | moderate | 2,465 | 1,940 | 48 | 477 |
| clay loam | young forest | high | 2,352 | 1,862 | 42 | 448 |
| loam | forest | low | 1,739 | 1,447 | 12 | 280 |
| loam | forest | moderate | 1,641 | 1,329 | 12 | 300 |
| loam | forest | high | 1,562 | 1,269 | 5 | 288 |
| loam | deciduous forest | low | 1,698 | 1,353 | 11 | 334 |
| loam | deciduous forest | moderate | 1,658 | 1,300 | 7 | 351 |
| loam | deciduous forest | high | 1,614 | 1,279 | 8 | 327 |
| loam | mixed forest | low | 1,731 | 1,408 | 10 | 313 |
| loam | mixed forest | moderate | 1,689 | 1,363 | 27 | 299 |
| loam | mixed forest | high | 1,607 | 1,348 | 11 | 248 |
| loam | shrub | low | 2,036 | 1,596 | 40 | 400 |
| loam | shrub | moderate | 2,018 | 1,591 | 37 | 390 |
| loam | shrub | high | 1,946 | 1,537 | 29 | 380 |
| loam | tall grass | low | 2,196 | 833 | 502 | 861 |
| loam | tall grass | moderate | 2,176 | 899 | 352 | 925 |
| loam | tall grass | high | 2,096 | 974 | 154 | 968 |
| loam | young forest | low | 2,216 | 1,893 | 28 | 295 |
| loam | young forest | moderate | 2,096 | 1,705 | 25 | 366 |
| loam | young forest | high | 1,993 | 1,632 | 15 | 346 |
| sand loam | forest | low | 526 | 414 | 2 | 110 |
| sand loam | forest | moderate | 476 | 348 | 3 | 125 |
| sand loam | forest | high | 386 | 256 | 1 | 129 |
| sand loam | deciduous forest | low | 496 | 362 | 1 | 133 |
| sand loam | deciduous forest | moderate | 485 | 340 | 3 | 142 |
| sand loam | deciduous forest | high | 401 | 256 | 2 | 143 |
| sand loam | mixed forest | low | 551 | 422 | 5 | 124 |
| sand loam | mixed forest | moderate | 527 | 391 | 4 | 132 |
| sand loam | mixed forest | high | 414 | 292 | 1 | 121 |
| sand loam | shrub | low | 552 | 404 | 3 | 145 |
| sand loam | shrub | moderate | 540 | 396 | 6 | 138 |
| sand loam | shrub | high | 412 | 275 | 1 | 136 |
| sand loam | tall grass | low | 667 | 281 | 116 | 270 |
| sand loam | tall grass | moderate | 655 | 278 | 82 | 295 |
| sand loam | tall grass | high | 586 | 273 | 32 | 281 |
| sand loam | young forest | low | 647 | 529 | 3 | 115 |
| sand loam | young forest | moderate | 578 | 435 | 2 | 141 |
| sand loam | young forest | high | 435 | 290 | 3 | 142 |
| silt loam | forest | low | 1,229 | 992 | 5 | 232 |
| silt loam | forest | moderate | 1,144 | 900 | 9 | 235 |
| silt loam | forest | high | 1,079 | 850 | 5 | 224 |
| silt loam | deciduous forest | low | 1,205 | 912 | 11 | 282 |
| silt loam | deciduous forest | moderate | 1,165 | 869 | 5 | 291 |
| silt loam | deciduous forest | high | 1,133 | 866 | 8 | 259 |
| silt loam | mixed forest | low | 1,243 | 990 | 4 | 249 |
| silt loam | mixed forest | moderate | 1,202 | 939 | 15 | 248 |
| silt loam | mixed forest | high | 1,133 | 935 | 6 | 192 |
| silt loam | shrub | low | 1,359 | 1,003 | 18 | 338 |
| silt loam | shrub | moderate | 1,336 | 1,002 | 25 | 309 |
| silt loam | shrub | high | 1,281 | 955 | 21 | 305 |
| silt loam | tall grass | low | 1,503 | 611 | 324 | 568 |
| silt loam | tall grass | moderate | 1,497 | 642 | 210 | 645 |
| silt loam | tall grass | high | 1,419 | 683 | 85 | 651 |
| silt loam | young forest | low | 1,512 | 1,254 | 19 | 239 |
| silt loam | young forest | moderate | 1,412 | 1,099 | 24 | 289 |
| silt loam | young forest | high | 1,315 | 1,025 | 15 | 275 |

#### Sediment Delivery Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 2,191 | 430 | 1,741 | 20 |
| clay loam | forest | moderate | 2,085 | 412 | 1,646 | 27 |
| clay loam | forest | high | 1,995 | 689 | 1,298 | 8 |
| clay loam | deciduous forest | low | 2,129 | 427 | 1,699 | 3 |
| clay loam | deciduous forest | moderate | 2,082 | 419 | 1,660 | 3 |
| clay loam | deciduous forest | high | 2,045 | 720 | 1,325 | 0 |
| clay loam | mixed forest | low | 2,184 | 431 | 1,751 | 2 |
| clay loam | mixed forest | moderate | 2,138 | 421 | 1,716 | 1 |
| clay loam | mixed forest | high | 2,055 | 718 | 1,337 | 0 |
| clay loam | shrub | low | 2,396 | 1,102 | 836 | 458 |
| clay loam | shrub | moderate | 2,376 | 1,055 | 746 | 575 |
| clay loam | shrub | high | 2,300 | 1,606 | 477 | 217 |
| clay loam | tall grass | low | 2,577 | 95 | 2,474 | 8 |
| clay loam | tall grass | moderate | 2,557 | 119 | 2,433 | 5 |
| clay loam | tall grass | high | 2,465 | 926 | 1,538 | 1 |
| clay loam | young forest | low | 2,595 | 419 | 2,003 | 173 |
| clay loam | young forest | moderate | 2,465 | 419 | 1,782 | 264 |
| clay loam | young forest | high | 2,352 | 767 | 1,480 | 105 |
| loam | forest | low | 1,739 | 68 | 1,671 | 0 |
| loam | forest | moderate | 1,641 | 81 | 1,559 | 1 |
| loam | forest | high | 1,562 | 197 | 1,365 | 0 |
| loam | deciduous forest | low | 1,698 | 68 | 1,630 | 0 |
| loam | deciduous forest | moderate | 1,658 | 81 | 1,576 | 1 |
| loam | deciduous forest | high | 1,614 | 193 | 1,421 | 0 |
| loam | mixed forest | low | 1,731 | 69 | 1,662 | 0 |
| loam | mixed forest | moderate | 1,689 | 82 | 1,606 | 1 |
| loam | mixed forest | high | 1,607 | 192 | 1,415 | 0 |
| loam | shrub | low | 2,036 | 213 | 1,783 | 40 |
| loam | shrub | moderate | 2,018 | 285 | 1,708 | 25 |
| loam | shrub | high | 1,946 | 693 | 1,248 | 5 |
| loam | tall grass | low | 2,196 | 47 | 2,145 | 4 |
| loam | tall grass | moderate | 2,176 | 48 | 2,123 | 5 |
| loam | tall grass | high | 2,096 | 183 | 1,906 | 7 |
| loam | young forest | low | 2,216 | 70 | 2,146 | 0 |
| loam | young forest | moderate | 2,096 | 83 | 2,012 | 1 |
| loam | young forest | high | 1,993 | 198 | 1,795 | 0 |
| sand loam | forest | low | 526 | 2 | 524 | 0 |
| sand loam | forest | moderate | 476 | 7 | 469 | 0 |
| sand loam | forest | high | 386 | 71 | 315 | 0 |
| sand loam | deciduous forest | low | 496 | 2 | 494 | 0 |
| sand loam | deciduous forest | moderate | 485 | 7 | 478 | 0 |
| sand loam | deciduous forest | high | 401 | 67 | 334 | 0 |
| sand loam | mixed forest | low | 551 | 2 | 549 | 0 |
| sand loam | mixed forest | moderate | 527 | 7 | 520 | 0 |
| sand loam | mixed forest | high | 414 | 67 | 347 | 0 |
| sand loam | shrub | low | 552 | 15 | 537 | 0 |
| sand loam | shrub | moderate | 540 | 20 | 520 | 0 |
| sand loam | shrub | high | 412 | 120 | 292 | 0 |
| sand loam | tall grass | low | 667 | 2 | 664 | 1 |
| sand loam | tall grass | moderate | 655 | 6 | 648 | 1 |
| sand loam | tall grass | high | 586 | 12 | 573 | 1 |
| sand loam | young forest | low | 647 | 4 | 643 | 0 |
| sand loam | young forest | moderate | 578 | 9 | 569 | 0 |
| sand loam | young forest | high | 435 | 72 | 363 | 0 |
| silt loam | forest | low | 1,229 | 49 | 1,179 | 1 |
| silt loam | forest | moderate | 1,144 | 56 | 1,088 | 0 |
| silt loam | forest | high | 1,079 | 156 | 923 | 0 |
| silt loam | deciduous forest | low | 1,205 | 48 | 1,156 | 1 |
| silt loam | deciduous forest | moderate | 1,165 | 54 | 1,111 | 0 |
| silt loam | deciduous forest | high | 1,133 | 152 | 981 | 0 |
| silt loam | mixed forest | low | 1,243 | 48 | 1,194 | 1 |
| silt loam | mixed forest | moderate | 1,202 | 54 | 1,148 | 0 |
| silt loam | mixed forest | high | 1,133 | 149 | 984 | 0 |
| silt loam | shrub | low | 1,359 | 83 | 1,276 | 0 |
| silt loam | shrub | moderate | 1,336 | 111 | 1,225 | 0 |
| silt loam | shrub | high | 1,281 | 267 | 1,014 | 0 |
| silt loam | tall grass | low | 1,503 | 20 | 1,482 | 1 |
| silt loam | tall grass | moderate | 1,497 | 21 | 1,476 | 0 |
| silt loam | tall grass | high | 1,419 | 43 | 1,376 | 0 |
| silt loam | young forest | low | 1,512 | 49 | 1,462 | 1 |
| silt loam | young forest | moderate | 1,412 | 56 | 1,356 | 0 |
| silt loam | young forest | high | 1,315 | 157 | 1,158 | 0 |

#### Peakflow Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 2,002 | 831 | 11 | 1,160 |
| clay loam | forest | moderate | 1,891 | 678 | 9 | 1,204 |
| clay loam | forest | high | 1,804 | 588 | 9 | 1,207 |
| clay loam | deciduous forest | low | 1,943 | 620 | 9 | 1,314 |
| clay loam | deciduous forest | moderate | 1,890 | 496 | 9 | 1,385 |
| clay loam | deciduous forest | high | 1,855 | 464 | 12 | 1,379 |
| clay loam | mixed forest | low | 2,014 | 616 | 15 | 1,383 |
| clay loam | mixed forest | moderate | 1,964 | 596 | 12 | 1,356 |
| clay loam | mixed forest | high | 1,883 | 642 | 8 | 1,233 |
| clay loam | shrub | low | 2,202 | 787 | 13 | 1,402 |
| clay loam | shrub | moderate | 2,177 | 681 | 13 | 1,483 |
| clay loam | shrub | high | 2,102 | 638 | 14 | 1,450 |
| clay loam | tall grass | low | 2,374 | 634 | 149 | 1,591 |
| clay loam | tall grass | moderate | 2,353 | 576 | 144 | 1,633 |
| clay loam | tall grass | high | 2,254 | 562 | 140 | 1,552 |
| clay loam | young forest | low | 2,392 | 992 | 19 | 1,381 |
| clay loam | young forest | moderate | 2,260 | 849 | 12 | 1,399 |
| clay loam | young forest | high | 2,154 | 739 | 9 | 1,406 |
| loam | forest | low | 1,614 | 695 | 5 | 914 |
| loam | forest | moderate | 1,514 | 545 | 2 | 967 |
| loam | forest | high | 1,434 | 487 | 3 | 944 |
| loam | deciduous forest | low | 1,555 | 504 | 3 | 1,048 |
| loam | deciduous forest | moderate | 1,511 | 391 | 4 | 1,116 |
| loam | deciduous forest | high | 1,463 | 394 | 5 | 1,064 |
| loam | mixed forest | low | 1,615 | 521 | 10 | 1,084 |
| loam | mixed forest | moderate | 1,570 | 516 | 8 | 1,046 |
| loam | mixed forest | high | 1,491 | 544 | 3 | 944 |
| loam | shrub | low | 1,882 | 694 | 9 | 1,179 |
| loam | shrub | moderate | 1,859 | 588 | 8 | 1,263 |
| loam | shrub | high | 1,783 | 557 | 8 | 1,218 |
| loam | tall grass | low | 2,031 | 549 | 123 | 1,359 |
| loam | tall grass | moderate | 2,019 | 488 | 120 | 1,411 |
| loam | tall grass | high | 1,930 | 464 | 116 | 1,350 |
| loam | young forest | low | 2,048 | 874 | 19 | 1,155 |
| loam | young forest | moderate | 1,928 | 728 | 10 | 1,190 |
| loam | young forest | high | 1,823 | 653 | 6 | 1,164 |
| sand loam | forest | low | 490 | 268 | 1 | 221 |
| sand loam | forest | moderate | 443 | 197 | 1 | 245 |
| sand loam | forest | high | 357 | 192 | 2 | 163 |
| sand loam | deciduous forest | low | 457 | 173 | 1 | 283 |
| sand loam | deciduous forest | moderate | 447 | 133 | 2 | 312 |
| sand loam | deciduous forest | high | 367 | 159 | 3 | 205 |
| sand loam | mixed forest | low | 510 | 210 | 3 | 297 |
| sand loam | mixed forest | moderate | 485 | 197 | 1 | 287 |
| sand loam | mixed forest | high | 380 | 211 | 1 | 168 |
| sand loam | shrub | low | 512 | 226 | 3 | 283 |
| sand loam | shrub | moderate | 503 | 186 | 3 | 314 |
| sand loam | shrub | high | 389 | 194 | 2 | 193 |
| sand loam | tall grass | low | 617 | 216 | 37 | 364 |
| sand loam | tall grass | moderate | 602 | 185 | 34 | 383 |
| sand loam | tall grass | high | 539 | 157 | 31 | 351 |
| sand loam | young forest | low | 609 | 332 | 4 | 273 |
| sand loam | young forest | moderate | 545 | 251 | 1 | 293 |
| sand loam | young forest | high | 402 | 226 | 1 | 175 |
| silt loam | forest | low | 1,141 | 540 | 5 | 596 |
| silt loam | forest | moderate | 1,051 | 423 | 4 | 624 |
| silt loam | forest | high | 992 | 391 | 5 | 596 |
| silt loam | deciduous forest | low | 1,110 | 382 | 5 | 723 |
| silt loam | deciduous forest | moderate | 1,063 | 290 | 5 | 768 |
| silt loam | deciduous forest | high | 1,036 | 313 | 7 | 716 |
| silt loam | mixed forest | low | 1,155 | 398 | 9 | 748 |
| silt loam | mixed forest | moderate | 1,107 | 392 | 10 | 705 |
| silt loam | mixed forest | high | 1,047 | 432 | 7 | 608 |
| silt loam | shrub | low | 1,250 | 491 | 4 | 755 |
| silt loam | shrub | moderate | 1,236 | 417 | 4 | 815 |
| silt loam | shrub | high | 1,171 | 428 | 5 | 738 |
| silt loam | tall grass | low | 1,402 | 407 | 83 | 912 |
| silt loam | tall grass | moderate | 1,387 | 359 | 79 | 949 |
| silt loam | tall grass | high | 1,302 | 321 | 74 | 907 |
| silt loam | young forest | low | 1,401 | 661 | 8 | 732 |
| silt loam | young forest | moderate | 1,293 | 536 | 6 | 751 |
| silt loam | young forest | high | 1,204 | 492 | 4 | 708 |