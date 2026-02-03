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
| shrub | low | 1,406 | 1,216 | 3 | 187 |
| shrub | moderate | 1,391 | 1,081 | 65 | 245 |
| shrub | high | 1,380 | 957 | 43 | 380 |
| tall grass | low | 1,493 | 359 | 981 | 153 |
| tall grass | moderate | 1,480 | 746 | 181 | 553 |
| tall grass | high | 1,459 | 773 | 73 | 613 |

### Sediment Delivery Event Counts (Burned vs Unburned)

| Veg Type | Severity | Total Events | Burned > Unburned | Equal | Unburned > Burned |
|----------|----------|-------------:|------------------:|------:|------------------:|
| forest | low | 1,308 | 114 | 1,191 | 3 |
| forest | moderate | 1,240 | 134 | 1,104 | 2 |
| forest | high | 1,202 | 236 | 966 | 0 |
| shrub | low | 1,406 | 51 | 1,191 | 164 |
| shrub | moderate | 1,391 | 86 | 1,170 | 135 |
| shrub | high | 1,380 | 255 | 1,093 | 32 |
| tall grass | low | 1,493 | 80 | 1,405 | 8 |
| tall grass | moderate | 1,480 | 87 | 1,388 | 5 |
| tall grass | high | 1,459 | 278 | 1,181 | 0 |

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
| shrub | low | burned | 19.82 | 18.52 | 14.53 | 27,638 |
| | | unburned | 19.05 | 18.51 | 13.60 | 26,581 |
| shrub | moderate | burned | 19.85 | 18.48 | 14.60 | 27,393 |
| | | unburned | 19.17 | 18.56 | 13.79 | 26,468 |
| shrub | high | burned | 19.73 | 18.36 | 14.78 | 27,038 |
| | | unburned | 19.24 | 18.60 | 13.93 | 26,366 |
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
| shrub | low | burned | 0.099 | 0.433 | 0.000 | 149.0 |
| | | unburned | 0.118 | 0.402 | 0.000 | 188.4 |
| shrub | moderate | burned | 0.230 | 1.019 | 0.000 | 350.7 |
| | | unburned | 0.119 | 0.404 | 0.000 | 188.4 |
| shrub | high | burned | 1.874 | 5.836 | 0.000 | 2775.7 |
| | | unburned | 0.120 | 0.406 | 0.000 | 188.4 |
| tall grass | low | burned | 0.179 | 0.923 | 0.000 | 291.6 |
| | | unburned | 0.149 | 0.775 | 0.000 | 242.7 |
| tall grass | moderate | burned | 0.330 | 1.742 | 0.000 | 537.4 |
| | | unburned | 0.151 | 0.779 | 0.000 | 242.7 |
| tall grass | high | burned | 3.941 | 12.201 | 0.000 | 6398.5 |
| | | unburned | 0.153 | 0.784 | 0.000 | 242.7 |

### Detailed Results by Soil Texture

#### Runoff Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 388 | 322 | 11 | 55 |
| clay loam | forest | moderate | 368 | 267 | 20 | 81 |
| clay loam | forest | high | 357 | 256 | 10 | 91 |
| clay loam | shrub | low | 415 | 363 | 1 | 51 |
| clay loam | shrub | moderate | 410 | 305 | 22 | 83 |
| clay loam | shrub | high | 406 | 276 | 16 | 114 |
| clay loam | tall grass | low | 434 | 94 | 298 | 42 |
| clay loam | tall grass | moderate | 427 | 204 | 64 | 159 |
| clay loam | tall grass | high | 421 | 222 | 22 | 177 |
| loam | forest | low | 349 | 301 | 4 | 44 |
| loam | forest | moderate | 332 | 267 | 4 | 61 |
| loam | forest | high | 323 | 253 | 2 | 68 |
| loam | shrub | low | 385 | 336 | 1 | 48 |
| loam | shrub | moderate | 380 | 310 | 15 | 55 |
| loam | shrub | high | 378 | 270 | 13 | 95 |
| loam | tall grass | low | 405 | 95 | 271 | 39 |
| loam | tall grass | moderate | 401 | 200 | 52 | 149 |
| loam | tall grass | high | 397 | 205 | 24 | 168 |
| sand loam | forest | low | 249 | 219 | 0 | 30 |
| sand loam | forest | moderate | 235 | 192 | 2 | 41 |
| sand loam | forest | high | 227 | 181 | 4 | 42 |
| sand loam | shrub | low | 265 | 223 | 0 | 42 |
| sand loam | shrub | moderate | 263 | 213 | 4 | 46 |
| sand loam | shrub | high | 261 | 186 | 5 | 70 |
| sand loam | tall grass | low | 289 | 79 | 177 | 33 |
| sand loam | tall grass | moderate | 289 | 154 | 25 | 110 |
| sand loam | tall grass | high | 281 | 153 | 11 | 117 |
| silt loam | forest | low | 322 | 280 | 2 | 40 |
| silt loam | forest | moderate | 305 | 240 | 5 | 60 |
| silt loam | forest | high | 295 | 222 | 6 | 67 |
| silt loam | shrub | low | 341 | 294 | 1 | 46 |
| silt loam | shrub | moderate | 338 | 253 | 24 | 61 |
| silt loam | shrub | high | 335 | 225 | 9 | 101 |
| silt loam | tall grass | low | 365 | 91 | 235 | 39 |
| silt loam | tall grass | moderate | 363 | 188 | 40 | 135 |
| silt loam | tall grass | high | 360 | 193 | 16 | 151 |

#### Sediment Delivery Event Counts by Texture

| Texture | Veg Type | Severity | Total | Burned > | Equal | Unburned > |
|---------|----------|----------|------:|---------:|------:|-----------:|
| clay loam | forest | low | 388 | 68 | 319 | 1 |
| clay loam | forest | moderate | 368 | 78 | 289 | 1 |
| clay loam | forest | high | 357 | 134 | 223 | 0 |
| clay loam | shrub | low | 415 | 20 | 265 | 130 |
| clay loam | shrub | moderate | 410 | 30 | 258 | 122 |
| clay loam | shrub | high | 406 | 133 | 243 | 30 |
| clay loam | tall grass | low | 434 | 49 | 381 | 4 |
| clay loam | tall grass | moderate | 427 | 51 | 373 | 3 |
| clay loam | tall grass | high | 421 | 195 | 226 | 0 |
| loam | forest | low | 349 | 23 | 324 | 2 |
| loam | forest | moderate | 332 | 32 | 299 | 1 |
| loam | forest | high | 323 | 43 | 280 | 0 |
| loam | shrub | low | 385 | 6 | 351 | 28 |
| loam | shrub | moderate | 380 | 25 | 345 | 10 |
| loam | shrub | high | 378 | 49 | 329 | 0 |
| loam | tall grass | low | 405 | 21 | 381 | 3 |
| loam | tall grass | moderate | 401 | 25 | 374 | 2 |
| loam | tall grass | high | 397 | 53 | 344 | 0 |
| sand loam | forest | low | 249 | 6 | 243 | 0 |
| sand loam | forest | moderate | 235 | 6 | 229 | 0 |
| sand loam | forest | high | 227 | 19 | 208 | 0 |
| sand loam | shrub | low | 265 | 8 | 257 | 0 |
| sand loam | shrub | moderate | 263 | 9 | 254 | 0 |
| sand loam | shrub | high | 261 | 25 | 236 | 0 |
| sand loam | tall grass | low | 289 | 2 | 287 | 0 |
| sand loam | tall grass | moderate | 289 | 2 | 287 | 0 |
| sand loam | tall grass | high | 281 | 12 | 269 | 0 |
| silt loam | forest | low | 322 | 17 | 305 | 0 |
| silt loam | forest | moderate | 305 | 18 | 287 | 0 |
| silt loam | forest | high | 295 | 40 | 255 | 0 |
| silt loam | shrub | low | 341 | 17 | 318 | 6 |
| silt loam | shrub | moderate | 338 | 22 | 313 | 3 |
| silt loam | shrub | high | 335 | 48 | 285 | 2 |
| silt loam | tall grass | low | 365 | 8 | 356 | 1 |
| silt loam | tall grass | moderate | 363 | 9 | 354 | 0 |
| silt loam | tall grass | high | 360 | 18 | 342 | 0 |