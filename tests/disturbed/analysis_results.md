## Test Matrix Analysis Results

Analysis of 48 hillslope simulations across:
- 4 soil textures (clay loam, loam, sand loam, silt loam)
- 3 vegetation types (forest, shrub, tall grass)
- 4 burn severities (unburned, low, moderate, high)

**Climate**: MC KENZIE BRIDGE RS, OR - 100 years, ~1,194 mm/yr precipitation

**Slope**: 201.68m variable profile (avg ~43% grade)

**Soil format**: 9002 with hydrophobicity parameters

### Runoff Event Counts (Burned vs Unburned)

Event counts compare burned vs unburned runoff by matching day/month/year across
all 4 soil textures. Results aggregated from 100-year simulations (48 total runs).

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 1,308 | 1,122 | 17 | 169 |
| forest | moderate | 1,240 | 966 | 31 | 243 |
| forest | high | 1,202 | 912 | 22 | 268 |
| shrub | low | 1,404 | 1,017 | 60 | 327 |
| shrub | moderate | 1,392 | 1,007 | 51 | 334 |
| shrub | high | 1,387 | 1,009 | 37 | 341 |
| tall grass | low | 1,493 | 359 | 981 | 153 |
| tall grass | moderate | 1,480 | 746 | 181 | 553 |
| tall grass | high | 1,459 | 773 | 73 | 613 |

### Sediment Delivery Event Counts (Burned vs Unburned)

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 1,308 | 114 | 1,191 | 3 |
| forest | moderate | 1,240 | 134 | 1,104 | 2 |
| forest | high | 1,202 | 236 | 966 | 0 |
| shrub | low | 1,404 | 289 | 1,072 | 43 |
| shrub | moderate | 1,392 | 181 | 1,146 | 65 |
| shrub | high | 1,387 | 353 | 1,029 | 5 |
| tall grass | low | 1,493 | 80 | 1,405 | 8 |
| tall grass | moderate | 1,480 | 87 | 1,388 | 5 |
| tall grass | high | 1,459 | 278 | 1,181 | 0 |

### Peakflow Event Counts (Burned vs Unburned)

Event counts compare burned vs unburned peak discharge by matching
simulation year/julian day in `H*.pass.dat` EVENT records.

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 1,242 | 1,078 | 8 | 156 |
| forest | moderate | 1,186 | 980 | 6 | 200 |
| forest | high | 1,148 | 955 | 6 | 187 |
| shrub | low | 1,322 | 1,035 | 10 | 277 |
| shrub | moderate | 1,313 | 1,030 | 10 | 273 |
| shrub | high | 1,303 | 1,028 | 10 | 265 |
| tall grass | low | 1,415 | 820 | 80 | 515 |
| tall grass | moderate | 1,400 | 828 | 18 | 554 |
| tall grass | high | 1,378 | 828 | 12 | 538 |

### Runoff Descriptive Statistics (mm)

Statistics aggregated across all 4 soil textures for 100-year simulations.

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 20.26 | 19.00 | 15.03 | 26,344 |
| | | unburned | 18.90 | 17.45 | 14.09 | 24,633 |
| forest | moderate | burned | 20.91 | 19.19 | 15.34 | 25,765 |
| | | unburned | 19.15 | 17.69 | 14.26 | 23,663 |
| forest | high | burned | 21.07 | 19.15 | 15.47 | 25,159 |
| | | unburned | 19.23 | 17.86 | 14.30 | 23,023 |
| shrub | low | burned | 20.10 | 18.49 | 14.80 | 27,996 |
| | | unburned | 19.05 | 18.53 | 13.62 | 26,554 |
| shrub | moderate | burned | 20.11 | 18.44 | 15.05 | 27,791 |
| | | unburned | 19.14 | 18.57 | 13.81 | 26,463 |
| shrub | high | burned | 19.85 | 18.34 | 14.91 | 27,332 |
| | | unburned | 19.17 | 18.59 | 13.84 | 26,396 |
| tall grass | low | burned | 19.00 | 18.29 | 13.51 | 28,191 |
| | | unburned | 18.65 | 18.05 | 13.15 | 27,694 |
| tall grass | moderate | burned | 19.15 | 18.33 | 13.65 | 28,185 |
| | | unburned | 18.77 | 18.07 | 13.35 | 27,658 |
| tall grass | high | burned | 19.29 | 18.35 | 14.16 | 27,972 |
| | | unburned | 19.00 | 18.10 | 13.64 | 27,562 |

### Sediment Delivery Descriptive Statistics (kg/m)

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 0.334 | 1.447 | 0.000 | 468.5 |
| | | unburned | 0.021 | 0.129 | 0.000 | 30.6 |
| forest | moderate | burned | 0.888 | 3.366 | 0.000 | 1229.2 |
| | | unburned | 0.022 | 0.132 | 0.000 | 30.6 |
| forest | high | burned | 4.072 | 12.020 | 0.000 | 5338.0 |
| | | unburned | 0.023 | 0.134 | 0.000 | 30.6 |
| shrub | low | burned | 0.402 | 1.307 | 0.000 | 613.8 |
| | | unburned | 0.118 | 0.403 | 0.000 | 188.4 |
| shrub | moderate | burned | 0.819 | 3.023 | 0.000 | 1232.3 |
| | | unburned | 0.120 | 0.404 | 0.000 | 188.4 |
| shrub | high | burned | 2.925 | 7.970 | 0.000 | 4341.9 |
| | | unburned | 0.120 | 0.405 | 0.000 | 188.4 |
| tall grass | low | burned | 0.179 | 0.923 | 0.000 | 291.6 |
| | | unburned | 0.149 | 0.775 | 0.000 | 242.7 |
| tall grass | moderate | burned | 0.330 | 1.742 | 0.000 | 537.4 |
| | | unburned | 0.151 | 0.779 | 0.000 | 242.7 |
| tall grass | high | burned | 3.941 | 12.201 | 0.000 | 6398.5 |
| | | unburned | 0.153 | 0.784 | 0.000 | 242.7 |

### Peakflow Descriptive Statistics (m^3/s)

| Veg Type | Severity | Condition | Mean | Std Dev | Median | Total |
|----------|----------|-----------|-----:|--------:|-------:|------:|
| forest | low | burned | 0.010 | 0.035 | 0.003 | 13.017 |
| | | unburned | 0.007 | 0.022 | 0.003 | 9.364 |
| forest | moderate | burned | 264.812 | 4961.073 | 0.003 | 372852.725 |
| | | unburned | 0.008 | 0.023 | 0.003 | 9.263 |
| forest | high | burned | 1446.719 | 16722.634 | 0.004 | 1771635.174 |
| | | unburned | 0.008 | 0.023 | 0.003 | 9.181 |
| shrub | low | burned | 820.003 | 12806.408 | 0.003 | 1198135.224 |
| | | unburned | 0.008 | 0.024 | 0.003 | 10.588 |
| shrub | moderate | burned | 1045.652 | 14386.683 | 0.003 | 1474013.109 |
| | | unburned | 0.008 | 0.024 | 0.003 | 10.576 |
| shrub | high | burned | 3033.479 | 24672.485 | 0.004 | 4227064.262 |
| | | unburned | 0.008 | 0.024 | 0.003 | 10.562 |
| tall grass | low | burned | 0.009 | 0.038 | 0.003 | 13.501 |
| | | unburned | 0.010 | 0.042 | 0.003 | 14.482 |
| tall grass | moderate | burned | 235.805 | 4727.188 | 0.003 | 380113.192 |
| | | unburned | 0.010 | 0.042 | 0.003 | 14.467 |
| tall grass | high | burned | 1877.968 | 16388.666 | 0.003 | 2935836.255 |
| | | unburned | 0.010 | 0.042 | 0.003 | 14.439 |

### Detailed Results by Soil Texture

#### Runoff Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 388 | 322 | 11 | 55 |
| clay loam | forest | moderate | 368 | 267 | 20 | 81 |
| clay loam | forest | high | 357 | 256 | 10 | 91 |
| clay loam | shrub | low | 413 | 286 | 21 | 106 |
| clay loam | shrub | moderate | 409 | 288 | 17 | 104 |
| clay loam | shrub | high | 408 | 293 | 11 | 104 |
| clay loam | tall grass | low | 434 | 94 | 298 | 42 |
| clay loam | tall grass | moderate | 427 | 204 | 64 | 159 |
| clay loam | tall grass | high | 421 | 222 | 22 | 177 |
| loam | forest | low | 349 | 301 | 4 | 44 |
| loam | forest | moderate | 332 | 267 | 4 | 61 |
| loam | forest | high | 323 | 253 | 2 | 68 |
| loam | shrub | low | 385 | 285 | 18 | 82 |
| loam | shrub | moderate | 382 | 283 | 15 | 84 |
| loam | shrub | high | 382 | 286 | 10 | 86 |
| loam | tall grass | low | 405 | 95 | 271 | 39 |
| loam | tall grass | moderate | 401 | 200 | 52 | 149 |
| loam | tall grass | high | 397 | 205 | 24 | 168 |
| sand loam | forest | low | 249 | 219 | 0 | 30 |
| sand loam | forest | moderate | 235 | 192 | 2 | 41 |
| sand loam | forest | high | 227 | 181 | 4 | 42 |
| sand loam | shrub | low | 266 | 204 | 7 | 55 |
| sand loam | shrub | moderate | 264 | 199 | 5 | 60 |
| sand loam | shrub | high | 262 | 194 | 5 | 63 |
| sand loam | tall grass | low | 289 | 79 | 177 | 33 |
| sand loam | tall grass | moderate | 289 | 154 | 25 | 110 |
| sand loam | tall grass | high | 281 | 153 | 11 | 117 |
| silt loam | forest | low | 322 | 280 | 2 | 40 |
| silt loam | forest | moderate | 305 | 240 | 5 | 60 |
| silt loam | forest | high | 295 | 222 | 6 | 67 |
| silt loam | shrub | low | 340 | 242 | 14 | 84 |
| silt loam | shrub | moderate | 337 | 237 | 14 | 86 |
| silt loam | shrub | high | 335 | 236 | 11 | 88 |
| silt loam | tall grass | low | 365 | 91 | 235 | 39 |
| silt loam | tall grass | moderate | 363 | 188 | 40 | 135 |
| silt loam | tall grass | high | 360 | 193 | 16 | 151 |

#### Sediment Delivery Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 388 | 68 | 319 | 1 |
| clay loam | forest | moderate | 368 | 78 | 289 | 1 |
| clay loam | forest | high | 357 | 134 | 223 | 0 |
| clay loam | shrub | low | 413 | 194 | 181 | 38 |
| clay loam | shrub | moderate | 409 | 94 | 257 | 58 |
| clay loam | shrub | high | 408 | 190 | 214 | 4 |
| clay loam | tall grass | low | 434 | 49 | 381 | 4 |
| clay loam | tall grass | moderate | 427 | 51 | 373 | 3 |
| clay loam | tall grass | high | 421 | 195 | 226 | 0 |
| loam | forest | low | 349 | 23 | 324 | 2 |
| loam | forest | moderate | 332 | 32 | 299 | 1 |
| loam | forest | high | 323 | 43 | 280 | 0 |
| loam | shrub | low | 385 | 59 | 322 | 4 |
| loam | shrub | moderate | 382 | 45 | 332 | 5 |
| loam | shrub | high | 382 | 65 | 317 | 0 |
| loam | tall grass | low | 405 | 21 | 381 | 3 |
| loam | tall grass | moderate | 401 | 25 | 374 | 2 |
| loam | tall grass | high | 397 | 53 | 344 | 0 |
| sand loam | forest | low | 249 | 6 | 243 | 0 |
| sand loam | forest | moderate | 235 | 6 | 229 | 0 |
| sand loam | forest | high | 227 | 19 | 208 | 0 |
| sand loam | shrub | low | 266 | 11 | 255 | 0 |
| sand loam | shrub | moderate | 264 | 13 | 251 | 0 |
| sand loam | shrub | high | 262 | 39 | 223 | 0 |
| sand loam | tall grass | low | 289 | 2 | 287 | 0 |
| sand loam | tall grass | moderate | 289 | 2 | 287 | 0 |
| sand loam | tall grass | high | 281 | 12 | 269 | 0 |
| silt loam | forest | low | 322 | 17 | 305 | 0 |
| silt loam | forest | moderate | 305 | 18 | 287 | 0 |
| silt loam | forest | high | 295 | 40 | 255 | 0 |
| silt loam | shrub | low | 340 | 25 | 314 | 1 |
| silt loam | shrub | moderate | 337 | 29 | 306 | 2 |
| silt loam | shrub | high | 335 | 59 | 275 | 1 |
| silt loam | tall grass | low | 365 | 8 | 356 | 1 |
| silt loam | tall grass | moderate | 363 | 9 | 354 | 0 |
| silt loam | tall grass | high | 360 | 18 | 342 | 0 |

#### Peakflow Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 367 | 302 | 5 | 60 |
| clay loam | forest | moderate | 352 | 272 | 4 | 76 |
| clay loam | forest | high | 343 | 265 | 4 | 74 |
| clay loam | shrub | low | 388 | 291 | 4 | 93 |
| clay loam | shrub | moderate | 386 | 294 | 4 | 88 |
| clay loam | shrub | high | 384 | 297 | 4 | 83 |
| clay loam | tall grass | low | 407 | 234 | 21 | 152 |
| clay loam | tall grass | moderate | 403 | 234 | 6 | 163 |
| clay loam | tall grass | high | 398 | 239 | 4 | 155 |
| loam | forest | low | 331 | 290 | 1 | 40 |
| loam | forest | moderate | 318 | 266 | 1 | 51 |
| loam | forest | high | 308 | 260 | 1 | 47 |
| loam | shrub | low | 360 | 284 | 2 | 74 |
| loam | shrub | moderate | 358 | 280 | 2 | 76 |
| loam | shrub | high | 356 | 282 | 2 | 72 |
| loam | tall grass | low | 383 | 219 | 19 | 145 |
| loam | tall grass | moderate | 380 | 222 | 4 | 154 |
| loam | tall grass | high | 374 | 220 | 3 | 151 |
| sand loam | forest | low | 241 | 219 | 0 | 22 |
| sand loam | forest | moderate | 226 | 199 | 0 | 27 |
| sand loam | forest | high | 217 | 195 | 0 | 22 |
| sand loam | shrub | low | 255 | 211 | 2 | 42 |
| sand loam | shrub | moderate | 253 | 209 | 2 | 42 |
| sand loam | shrub | high | 248 | 205 | 2 | 41 |
| sand loam | tall grass | low | 280 | 164 | 18 | 98 |
| sand loam | tall grass | moderate | 275 | 171 | 3 | 101 |
| sand loam | tall grass | high | 270 | 163 | 2 | 105 |
| silt loam | forest | low | 303 | 267 | 2 | 34 |
| silt loam | forest | moderate | 290 | 243 | 1 | 46 |
| silt loam | forest | high | 280 | 235 | 1 | 44 |
| silt loam | shrub | low | 319 | 249 | 2 | 68 |
| silt loam | shrub | moderate | 316 | 247 | 2 | 67 |
| silt loam | shrub | high | 315 | 244 | 2 | 69 |
| silt loam | tall grass | low | 345 | 203 | 22 | 120 |
| silt loam | tall grass | moderate | 342 | 201 | 5 | 136 |
| silt loam | tall grass | high | 336 | 206 | 3 | 127 |