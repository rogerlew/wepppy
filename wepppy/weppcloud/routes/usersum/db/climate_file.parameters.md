# CLIGEN Climate File Parameters
Derived from `wepppy/weppcloud/routes/usersum/input-file-specifications/climate-file.spec.md`.
Line numbers reference the CLIGEN climate file format; the heading supplies the default `usersum <parameter>` description.

## Header
### Line 1 — CLIGEN Metadata
#### `datver` — CLIGEN version selector (real)
- **Line**: 1
- **Extended**: Version code controlling rainfall intensity handling (e.g., 0.0 uses raw ip, 4.x applies legacy adjustments).

### Line 2 — Simulation Flags
#### `itemp` — Simulation mode flag (integer)
- **Line**: 2
- **Extended**: Selects continuous (1) vs. single-storm (2) climate generation.

#### `ibrkpt` — Breakpoint data flag (integer)
- **Line**: 2
- **Extended**: Indicates whether precipitation breakpoint data are included (0=no, 1=yes).

#### `iwind` — Wind/ET equation flag (integer)
- **Line**: 2
- **Extended**: Specifies availability of wind data and ET method: 0=Penman with wind, 1=Priestley–Taylor without wind.

### Line 3 — Station Identification
#### `stmid` — Station identifier & metadata (text)
- **Line**: 3
- **Extended**: Free-form station ID string plus ancillary information as provided by CLIGEN.

### Line 5 — Station Characteristics
#### `deglat` — Station latitude (degrees, real)
- **Line**: 5a
- **Extended**: Signed latitude in degrees (positive north, negative south).

#### `deglon` — Station longitude (degrees, real)
- **Line**: 5b
- **Extended**: Signed longitude in degrees (positive east, negative west).

#### `elev` — Station elevation (m, real)
- **Line**: 5c
- **Extended**: Elevation of the climate station in meters above mean sea level.

#### `obsyrs` — Years of observation (integer)
- **Line**: 5d
- **Extended**: Number of years of observed data supporting the CLIGEN statistics.

#### `ibyear` — Simulation begin year (integer)
- **Line**: 5e
- **Extended**: First year represented in the CLIGEN simulation.

#### `numyr` — Number of simulated years (integer)
- **Line**: 5f
- **Extended**: Total climate years generated and stored in the file.

#### `cmdline` — CLIGEN command line (text, optional)
- **Line**: 5g
- **Extended**: Command used to run CLIGEN (present in version 5.1 and newer files).


## Monthly Averages
### Line 7 — Observed Monthly Average Maximum Temperature
#### `obmaxt` — Monthly average max temperature (°C, real)
- **Line**: 7
- **Extended**: Array of 12 values giving the observed monthly average maximum temperatures.

### Line 9 — Observed Monthly Average Minimum Temperature
#### `obmint` — Monthly average min temperature (°C, real)
- **Line**: 9
- **Extended**: Array of 12 values giving the observed monthly average minimum temperatures.

### Line 11 — Observed Monthly Average Daily Solar Radiation
#### `radave` — Monthly average solar radiation (langleys, real)
- **Line**: 11
- **Extended**: Array of 12 daily-average solar radiation values in langleys.

### Line 13 — Observed Monthly Average Precipitation
#### `obrain` — Monthly average precipitation (mm, real)
- **Line**: 13
- **Extended**: Array of 12 values giving observed monthly average precipitation depths.


## Daily Records — CLIGEN Generated (No Breakpoints)
### Line 16 — Daily Values (Repeated per Simulation Day)
#### `day` — Simulation day of month (integer)
- **Line**: 16a
- **Extended**: Day number within the month for the simulated record.

#### `mon` — Simulation month (integer)
- **Line**: 16b
- **Extended**: Calendar month number for the simulated record.

#### `year` — Simulation year (integer)
- **Line**: 16c
- **Extended**: Calendar year for the simulated record.

#### `prcp` — Daily precipitation depth (mm, real)
- **Line**: 16d
- **Extended**: Total precipitation for the simulated day.

#### `stmdur` — Storm duration (hours, real)
- **Line**: 16e
- **Extended**: Duration of rainfall for the day (hours).

#### `timep` — Time-to-peak ratio (real)
- **Line**: 16f
- **Extended**: Ratio of time to peak intensity divided by storm duration.

#### `ip` — Peak-to-average intensity ratio (real)
- **Line**: 16g
- **Extended**: Maximum rainfall intensity divided by the average intensity.

#### `tmax` — Maximum daily temperature (°C, real)
- **Line**: 16h
- **Extended**: Maximum air temperature for the day.

#### `tmin` — Minimum daily temperature (°C, real)
- **Line**: 16i
- **Extended**: Minimum air temperature for the day.

#### `rad` — Daily solar radiation (langleys/day, real)
- **Line**: 16j
- **Extended**: Total solar radiation for the day.

#### `vwind` — Wind velocity (m/s, real)
- **Line**: 16k
- **Extended**: Windspeed measured for the day.

#### `wind` — Wind direction (degrees, real)
- **Line**: 16l
- **Extended**: Wind direction in degrees clockwise from north.

#### `tdpt` — Dew point temperature (°C, real)
- **Line**: 16m
- **Extended**: Dew point temperature for the simulated day.


## Daily Records — Breakpoint Precipitation
### Line 16 — Daily Summary (Repeated per Simulation Day)
#### `day` — Simulation day of month (integer)
- **Line**: 16a
- **Extended**: Day number within the month for the simulated record.

#### `mon` — Simulation month (integer)
- **Line**: 16b
- **Extended**: Calendar month number for the simulated record.

#### `year` — Simulation year (integer)
- **Line**: 16c
- **Extended**: Calendar year for the simulated record.

#### `nbrkpt` — Number of precipitation breakpoints (integer)
- **Line**: 16d
- **Extended**: Count of intra-day breakpoint entries following on line 17.

#### `tmax` — Maximum daily temperature (°C, real)
- **Line**: 16e
- **Extended**: Maximum air temperature for the day.

#### `tmin` — Minimum daily temperature (°C, real)
- **Line**: 16f
- **Extended**: Minimum air temperature for the day.

#### `rad` — Daily solar radiation (langleys/day, real)
- **Line**: 16g
- **Extended**: Total solar radiation for the day.

#### `vwind` — Wind velocity (m/s, real)
- **Line**: 16h
- **Extended**: Windspeed measured for the day.

#### `wind` — Wind direction (degrees, real)
- **Line**: 16i
- **Extended**: Wind direction in degrees clockwise from north.

#### `tdpt` — Dew point temperature (°C, real)
- **Line**: 16j
- **Extended**: Dew point temperature for the simulated day.

### Line 17 — Breakpoint Detail (Repeated per Breakpoint)
#### `timem` — Hours since midnight (real)
- **Line**: 17a
- **Extended**: Elapsed hours after midnight for the breakpoint record.

#### `pptcum` — Cumulative precipitation at breakpoint (mm, real)
- **Line**: 17b
- **Extended**: Cumulative precipitation depth at the given breakpoint time.
