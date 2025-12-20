# wepppy.climates

> Multi-source climate data integration for erosion modeling, providing unified interfaces to stochastic weather generation (CLIGEN), gridded observations (Daymet, GridMET, PRISM), and specialized datasets for North America, Europe, and Australia.

> **See also:** [AGENTS.md](../../AGENTS.md) § Common Tasks § Adding a New Climate Data Source

## Overview

The `wepppy.climates` package integrates diverse climate data sources into a unified workflow for WEPP (Water Erosion Prediction Project) modeling. Instead of forcing users to manage vendor-specific APIs, data formats, and coordinate transformations, this package abstracts those details behind consistent Python interfaces and standardized output formats.

**Core Problem Solved**: Erosion models require daily precipitation, temperature, wind, solar radiation, and dewpoint data—but obtaining this data involves navigating incompatible APIs (REST vs. NetCDF), different spatial resolutions (1 km Daymet vs. 4 km GridMET), temporal coverage gaps (stochastic generators vs. historical records), and coordinate system transformations. This package harmonizes those differences.

**Primary Users**:
- **NoDb Climate controller** (`wepppy.nodb.core.Climate`) orchestrates climate data retrieval and WEPP `.cli` file generation
- **Background RQ tasks** in `wepppy.rq.project_rq` fetch and process climate data asynchronously
- **Validation workflows** in `wepppy.climates.validation/` benchmark climate datasets against weather station observations

**Key Capabilities**:
- **Stochastic generation** via CLIGEN (Climate Generator) for Monte Carlo simulations
- **Historical observations** from Daymet (1980–present, 1 km, North America), GridMET (1979–present, 4 km, CONUS), PRISM (1981–present, 4 km, CONUS)
- **Spatial interpolation** for hillslope-level climate using Rust-accelerated kernels (`wepppyo3.climate.interpolate_geospatial`)
- **Climate revisions** adjusting stochastic climates with PRISM monthly normals or observed data
- **Unified output** to WEPP `.cli` (Climate) and `.prn` (PRiNted input) formats, plus Parquet archives for analysis

## Components

### Core Module Files

| File | Purpose |
|------|---------|
| `cligen/single_storm.py` | Direct single-storm CLIGEN builder (writes `.cli`/`.par` locally) |
| `metquery_client.py` | Fetches PRISM monthly normals (precipitation, temperature) from `wepp.cloud/webservices/metquery/` |
| `downscaled_nmme_client.py` | Experimental NMME climate projections client |
| `noaa_precip_freqs_client.py` | NOAA precipitation frequency estimates (for storm generation) |
| `holden_wrf_atlas.py` | Holden WRF downscaled climate atlas (Pacific Northwest) |

### Climate Data Source Packages

#### `cligen/` - CLIGEN Statistical Weather Generator
- **Purpose**: Generate synthetic daily weather using statistical parameters from weather station records
- **Spatial Coverage**: Global (where station data exists)
- **Temporal Coverage**: Configurable (typically 30–100 years for Monte Carlo)
- **Resolution**: Point-based (station locations)
- **Key Files**:
  - `cligen.py` - Core CLIGEN wrapper (`Cligen` class, `par_mod()` for PRISM adjustments)
  - `stations.db` - SQLite database of ~15,000 US CLIGEN stations
  - `ghcn_daily/` - GHCN (Global Historical Climatology Network) daily data integration
- **Reference**: CLIGEN station statistics (`.par`) format: [cligenparms.md](../weppcloud/routes/usersum/input-file-specifications/cligenparms.md)
- **Usage Pattern**: Find nearest station → optionally revise with PRISM/Daymet → generate stochastic climate
- **Strengths**: Fast, enables Monte Carlo analysis, creates climate scenarios for unmonitored locations
- **Limitations**: Synthetic (not suitable for validating against streamflow), assumes stationarity

#### `daymet/` - Daymet Gridded Observations
- **Purpose**: Historical daily meteorology at 1 km resolution
- **Spatial Coverage**: North America (Canada, USA, Mexico, Puerto Rico)
- **Temporal Coverage**: 1980–present (updated annually, ~18-month lag)
- **Resolution**: 1 km × 1 km grid
- **Key Files**:
  - `daymet_singlelocation_client.py` - Single-pixel REST API client (`retrieve_historical_timeseries()`)
  - `daily_interpolation.py` - Spatial interpolation for watershed-scale runs using Rust kernel
  - `fast_single_point.py` - Optimized single-location retrieval
- **Data Source**: Oak Ridge National Laboratory (ORNL) REST API (`daymet.ornl.gov/single-pixel/api/data`)
- **Variables**: Precipitation, tmax, tmin, solar radiation, vapor pressure, snow water equivalent
- **Usage Pattern**: Query by lon/lat → convert to WEPP `.cli` format → optionally blend with GridMET wind
- **Strengths**: High spatial resolution, covers full historical period, widely validated
- **Limitations**: North America only, 18-month data lag, no sub-daily timesteps

#### `gridmet/` - GridMET Gridded Surface Meteorology
- **Purpose**: Daily surface meteorology for hydrologic modeling
- **Spatial Coverage**: CONUS (Contiguous United States)
- **Temporal Coverage**: 1979–present (near real-time updates)
- **Resolution**: ~4 km grid
- **Key Files**:
  - `client.py` - NetCDF downloader and interpolator (`retrieve_timeseries()`, `interpolate_daily_timeseries_for_location()`)
  - `gridmet_singlelocation_client.py` - Single-pixel convenience wrapper
- **Data Source**: University of Idaho (climatologylab.org), served via THREDDS
- **Variables**: Precipitation, tmax, tmin, wind speed, wind direction, humidity, solar radiation, vapor pressure
- **Usage Pattern**: Download NetCDF for bounding box → interpolate to hillslope centroids → generate `.cli` files
- **Strengths**: Near real-time, includes wind (critical for Daymet workflows), CONUS-wide coverage
- **Limitations**: Coarser resolution than Daymet, CONUS only

#### `prism/` - PRISM Climate Normals and Daily Data
- **Purpose**: Parameter-elevation Regressions on Independent Slopes Model for climate normals and daily observations
- **Spatial Coverage**: CONUS
- **Temporal Coverage**: 1981–present (daily); 1895–present (monthly normals)
- **Resolution**: ~4 km grid
- **Key Files**:
  - `daily_client.py` - Daily PRISM data via Oregon State web service (`retrieve_historical_timeseries()`)
  - `__init__.py` - PRISM revision utilities (`prism_mod()`, `prism_revision()`)
- **Data Source**: Oregon State University PRISM Climate Group
- **Variables**: Precipitation, tmax, tmin, tdew (mean dewpoint)
- **Usage Pattern**: Typically used to *revise* stochastic CLIGEN climates by adjusting monthly means to match PRISM normals
- **Strengths**: Robust elevation adjustments, widely used for baseline climatology
- **Limitations**: Daily data access is rate-limited, coarser than Daymet

#### `snotel/` - SNOTEL/SCAN Weather Station Data
- **Purpose**: Natural Resources Conservation Service (NRCS) snow telemetry and soil climate stations
- **Spatial Coverage**: Western US mountains (SNOTEL), nationwide agricultural areas (SCAN)
- **Key Files**: Station metadata and retrieval wrappers
- **Usage Pattern**: Validation and comparison against gridded datasets

#### `validation/` - Climate Dataset Benchmarking
- **Purpose**: Compare Daymet, GridMET, PRISM, and CLIGEN outputs against weather station observations
- **Key Files**:
  - `24_us_stations/build_us_climates.py` - Generates climate files for 24 benchmark US stations
- **Usage Pattern**: Generate `.cli` files from each source → compare against SNOTEL/SCAN observations → assess bias/RMSE

### Regional Specializations
- **`climatena_ca/`** - ClimateNA dataset (Canada)
- **`wepppy.eu.climates.eobs`** (not in this package, imported) - E-OBS gridded observations (Europe)
- **`wepppy.au.climates.agdc`** (not in this package, imported) - Australian Gridded Climate Data

## Quick Start

### Example 1: Generate Stochastic CLIGEN Climate

```python
from wepppy.climates.cligen import Cligen, CligenStationsManager

# Find nearest CLIGEN station
mgr = CligenStationsManager(version='2015')
stations = mgr.find_closest(lng=-116.5, lat=43.8, n=1)
par_id = stations[0]['par']

# Generate 30-year synthetic climate
cligen = Cligen(station=par_id, wd='/tmp/climate_test')
cligen.run_multiple_year(years=30, cli_fn='stochastic.cli')

# Files created:
#   /tmp/climate_test/stochastic.cli  (WEPP climate file)
```

### Example 2: Retrieve Daymet Historical Data

```python
from wepppy.climates.daymet import retrieve_historical_timeseries

# Get 2010-2020 Daymet data for Moscow, Idaho
df = retrieve_historical_timeseries(
    lon=-116.97, 
    lat=46.73, 
    start_year=2010, 
    end_year=2020,
    gridmet_wind=True  # Blend in GridMET wind data
)

# DataFrame columns: 'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)', 
#                    'srad(l/day)', 'tdew(degc)', 'vs(m/s)', 'th(DegreesClockwisefromnorth)'
print(df.head())
```

### Example 3: Spatial Interpolation for Watershed

```python
from wepppy.climates.daymet.daily_interpolation import interpolate_daily_timeseries

# Hillslope centroid locations (from watershed delineation)
hillslope_locations = {
    "1": {"longitude": -116.5, "latitude": 43.8},
    "2": {"longitude": -116.51, "latitude": 43.81},
    # ... more hillslopes
}

# Generate per-hillslope climate files
interpolate_daily_timeseries(
    hillslope_locations=hillslope_locations,
    start_year=2018,
    end_year=2020,
    output_dir='/path/to/wepp/runs',
    output_type='prn parquet',  # Both .prn and .parquet outputs
    max_workers=12
)

# Creates:
#   /path/to/wepp/runs/daymet_observed_1_2018-2020.prn
#   /path/to/wepp/runs/daymet_observed_1_2018-2020.parquet
#   (and similarly for hillslope 2, 3, ...)
```

### Example 4: PRISM Climate Revision

```python
from wepppy.climates.prism import prism_mod
from wepppy.climates.cligen import Cligen

# Generate baseline CLIGEN climate
cligen = Cligen(station=106152, wd='/tmp/climate')
cligen.run_multiple_year(years=30, cli_fn='baseline.cli')

# Adjust monthly precipitation/temperature to PRISM normals
prism_mod(
    par=106152, 
    years=30, 
    lng=-116.5, 
    lat=43.8, 
    wd='/tmp/climate',
    suffix='_prism'  # Creates 106152_prism.cli
)
```

### Example 5: GridMET Data Retrieval

```python
from wepppy.climates.gridmet import retrieve_timeseries, GridMetVariable

locations = {
    'site1': [-116.5, 43.8],
    'site2': [-116.6, 43.9]
}

variables = [
    GridMetVariable.Precipitation,
    GridMetVariable.MinimumTemperature,
    GridMetVariable.MaximumTemperature,
    GridMetVariable.WindSpeed
]

# Download GridMET NetCDF files and extract timeseries
timeseries = retrieve_timeseries(
    variables=variables,
    locations=locations,
    start_year=2015,
    end_year=2020,
    met_dir='/tmp/gridmet_cache'
)

# timeseries structure:
# {
#   'site1': {
#     'pr': [date -> precipitation values],
#     'tmmn': [date -> min temp values],
#     ...
#   },
#   'site2': { ... }
# }
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SCRATCH_DIR` | `/dev/shm` | Temporary storage for NetCDF downloads (GridMET) |

### Climate Data Endpoints (Production)

| Service | Endpoint | Purpose |
|---------|----------|---------|
| MetQuery | `https://wepp.cloud/webservices/metquery/` | PRISM monthly normals |
| Daymet | `https://daymet.ornl.gov/single-pixel/api/data` | Daymet single-pixel API |
| GridMET | `http://www.climatologylab.org/gridmet.html` | GridMET THREDDS catalog |
| PRISM Daily | `http://www.prism.oregonstate.edu/explorer/` | PRISM web explorer API |

### CLIGEN Station Database Versions

The `CligenStationsManager` supports multiple station database versions:

| Version | Stations | Coverage | Notes |
|---------|----------|----------|-------|
| `2015` | ~14,000 | US + select international | Default, widely validated |
| `au` | ~1,000 | Australia | Australian Bureau of Meteorology stations |
| `chili` | ~200 | Chili | Chilean stations |
| `ghcn` | ~25,000 | Global | GHCN International Stations |

```python
# Example: Use Australian stations
mgr = CligenStationsManager(version='au')
stations = mgr.find_closest(lng=149.1, lat=-35.3, n=3)
```

## Key Concepts

### Climate File Formats

#### `.cli` (WEPP Climate File)
- **Purpose**: Binary-compatible input for WEPP model
- **Structure**: Header + daily records (da, mo, year, prcp, dur, tp, ip, tmax, tmin, rad, w-vl, w-dir, tdew)
- **Units**: Precipitation (mm), temperature (°C), radiation (Langleys/day), wind velocity (m/s), wind direction (degrees)
- **Generation**: Created by CLIGEN binary (`cligen532`) or via `ClimateFile` class programmatic manipulation

#### `.prn` (PRiNted Input File)
- **Purpose**: Human-readable intermediate format for CLIGEN observed data mode
- **Structure**: CSV-like columns (date, prcp, tmax, tmin)
- **Usage**: Convert Daymet/GridMET/PRISM dataframes → `.prn` → CLIGEN → `.cli`

#### `.parquet` (Archive Format)
- **Purpose**: Efficient storage and query of climate timeseries
- **Structure**: Pandas DataFrame serialized with PyArrow
- **Usage**: Archive raw climate data for debugging, reprocessing, or analysis (e.g., via D-Tale explorer)

### Spatial Modes

Defined in `wepppy.nodb.core.Climate.ClimateSpatialMode`:

| Mode | Value | Description |
|------|-------|-------------|
| `SINGLE` | 0 | Single climate file for entire watershed (uses centroid or outlet location) |
| `MULTIPLE` | 1 | One climate file per hillslope (spatially interpolated) |
| `GRIDDED` | 2 | Grid-based interpolation (experimental, Daymet only) |

### Climate Modes

Defined in `wepppy.nodb.core.Climate.ClimateMode`:

| Mode | Value | Dataset | Stochastic | Historical | Typical Use Case |
|------|-------|---------|------------|------------|------------------|
| `CLIGEN` | 0 | CLIGEN | ✓ | ✗ | Monte Carlo sensitivity analysis |
| `OBSERVED` | 1 | Weather station | ✗ | ✓ | Validation against streamflow |
| `PRISM_ADJUSTED` | 3 | CLIGEN + PRISM | ✓ | ✗ | BAER (Burned Area Emergency Response) |
| `OBSERVED_DAYMET` | 9 | Daymet | ✗ | ✓ | High-resolution historical runs |
| `OBSERVED_GRIDMET` | 10 | GridMET | ✗ | ✓ | CONUS historical runs |
| `OBSERVED_PRISM` | 12 | PRISM | ✗ | ✓ | Climate normal-based runs |

### Climate Revision Workflow

Many workflows start with a **stochastic CLIGEN climate** and then **revise** it with observed data to preserve CLIGEN's realistic storm structure while matching observed precipitation/temperature statistics:

```
1. Generate CLIGEN climate (synthetic storms, wind, radiation)
2. Query PRISM monthly normals for target location
3. Adjust CLIGEN monthly precipitation/temperature means to match PRISM
4. Replace temperature/dewpoint with Daymet or PRISM daily values (optional)
5. Replace wind with GridMET (optional)
```

This is implemented in:
- `wepppy.climates.prism.prism_mod()` - Adjust CLIGEN .par file, regenerate
- `wepppy.climates.prism.prism_revision()` - Post-process existing `.cli` file
- `wepppy.nodb.core.Climate._build_climate_depnexrad()` - Full revision pipeline for DEP/NEXRAD workflows

### Spatial Interpolation with Rust

For watershed-scale runs (potentially hundreds of hillslopes), Python-based interpolation is too slow. The `wepppyo3.climate.interpolate_geospatial()` function (Rust FFI) uses `scipy`-style regular grid interpolation but runs 10–50× faster:

```python
from wepppyo3.climate import interpolate_geospatial

# Prepare spatial grids (from NetCDF or raster)
longitudes = np.array([-117.0, -116.5, -116.0])  # 1D array
latitudes = np.array([43.5, 44.0, 44.5])         # 1D array
values = np.random.rand(3, 3)                    # 2D grid

# Interpolate to hillslope points
hillslope_lngs = np.array([-116.75, -116.25])
hillslope_lats = np.array([43.75, 44.25])

result = interpolate_geospatial(
    longitudes, latitudes, values,
    hillslope_lngs, hillslope_lats
)
# result: array of interpolated values for each hillslope
```

This is called internally by `daymet.daily_interpolation.interpolate_daily_timeseries()` and `gridmet.client.interpolate_daily_timeseries_for_location()`.

## Integration with WEPPcloud Workflow

The `wepppy.nodb.core.Climate` NoDb controller orchestrates climate data retrieval and `.cli` file generation:

```python
from wepppy.nodb.core import Climate

# Load existing run
climate = Climate.getInstance('/geodata/weppcloud_runs/abc123/CurCond')

# Configure climate source
climate.climate_mode = 9  # ClimateMode.OBSERVED_DAYMET
climate.climate_spatialmode = 1  # ClimateSpatialMode.MULTIPLE (per-hillslope)
climate.input_years = (2018, 2020)

# Fetch data and build .cli files (runs asynchronously via RQ)
climate.build_climate()
```

Under the hood, this:
1. Reads hillslope locations from `Watershed` controller
2. Calls `daymet.daily_interpolation.interpolate_daily_timeseries()`
3. Generates `.prn` files for each hillslope
4. Invokes CLIGEN binary to convert `.prn` → `.cli`
5. Archives raw data as `.parquet` in `wepp/runs/`
6. Updates `Climate` state and logs progress to Redis pub/sub

See `wepppy.nodb.core.climate` and `wepppy.rq.project_rq` for full implementation.

## Developer Notes

### Adding a New Climate Data Source

Follow the pattern established by existing sources:

1. **Create package**: `wepppy/climates/newsource/`
2. **Implement retrieval function**: 
   ```python
   def retrieve_historical_timeseries(lng, lat, start_year, end_year, **kwargs):
       # Query API, parse response
       # Return pandas DataFrame with columns:
       #   'prcp(mm/day)', 'tmax(degc)', 'tmin(degc)', 'srad(l/day)', 'tdew(degc)'
       pass
   ```
3. **Add to `Climate` controller**: 
   - Define new `ClimateMode` enum value in `wepppy.nodb.core.climate`
   - Add branch in `Climate._build_climate()` method
   - Update `wepppy.nodb.locales.climate_catalog` with dataset metadata
4. **Update `__all__` exports**: Add new module to `wepppy.climates.__init__.py` (currently empty, but future-proof)
5. **Add tests**: `tests/climates/test_newsource.py` with fixtures in `tests/data/`
6. **Document**: Update this README and `AGENTS.md § Common Tasks`

### Testing Patterns

Climate modules involve network I/O, so tests should:
- **Mock external APIs**: Use `responses` library or `httpx.MockTransport`
- **Cache fixtures**: Store sample API responses in `tests/data/climates/` as JSON/CSV
- **Test coordinate transformations**: Verify lat/lon → grid index conversions
- **Validate output formats**: Ensure `.prn` and `.cli` files match expected structure

Example test structure:
```python
import pytest
from responses import RequestsMock
from wepppy.climates.newsource import retrieve_historical_timeseries

@pytest.mark.unit
def test_retrieve_timeseries_mock(responses):
    # Mock API response
    responses.add(
        responses.GET,
        'https://api.newsource.org/data',
        json={'data': [...]},
        status=200
    )
    
    df = retrieve_historical_timeseries(-116.5, 43.8, 2010, 2015)
    
    assert 'prcp(mm/day)' in df.columns
    assert len(df) == 2192  # 6 years * 365.33 days
```

### Performance Considerations

- **Cache NetCDF files**: GridMET downloads can be large (100+ MB); cache in `/dev/shm` or persistent storage
- **Parallelize hillslope processing**: Use `ProcessPoolExecutor` or RQ tasks for multi-hillslope runs
- **Avoid redundant API calls**: Check for existing `.parquet` archives before re-downloading
- **Use Rust interpolation**: Always delegate spatial interpolation to `wepppyo3.climate.interpolate_geospatial()`

### Known Limitations

- **Daymet lag**: Daymet data typically has an 18-month lag (e.g., 2025 data available in mid-2026)
- **GridMET CONUS-only**: GridMET does not cover Alaska, Hawaii, or territories
- **PRISM rate limits**: PRISM daily explorer API is not intended for bulk downloads; use sparingly
- **CLIGEN station coverage**: CLIGEN stations are sparse in some regions (e.g., Alaska, international)
- **No sub-daily data**: All sources provide daily timesteps; WEPP does not support sub-daily climate

### Common Pitfalls

- **Coordinate system mismatches**: Daymet uses Lambert Conformal Conic (LCC); must transform from lon/lat. Use `pyproj.Proj` for conversions.
- **Leap year handling**: WEPP expects 365-day years. Most sources support `fill_leap_years=True` to duplicate Feb 28 → Feb 29.
- **Unit conversions**: Daymet returns precipitation in mm/day; CLIGEN uses mm; WEPP .cli expects mm. GridMET returns kg/m²/day (= mm/day). Always verify units.
- **Wind direction convention**: GridMET uses meteorological convention (direction wind comes *from*); WEPP uses the same. Daymet lacks wind (must blend GridMET).
- **Missing data**: Handle API failures gracefully; retry with exponential backoff (see `daymet_singlelocation_client.py` retry logic).

### Code Organization

```
climates/
├── __init__.py                 # Empty (future: aggregate exports)
├── metquery_client.py          # PRISM monthly normals client
├── noaa_precip_freqs_client.py # NOAA precipitation frequencies
├── cligen/                     # CLIGEN package
│   ├── __init__.py
│   ├── cligen.py               # Core Cligen class
│   ├── single_storm.py         # Direct single-storm builder
│   ├── stations.db             # US stations SQLite
│   ├── ghcn_daily/             # GHCN integration
│   └── tests/
├── daymet/                     # Daymet package
│   ├── __init__.py
│   ├── daymet_singlelocation_client.py
│   ├── daily_interpolation.py  # Spatial interpolation
│   └── fast_single_point.py
├── gridmet/                    # GridMET package
│   ├── __init__.py
│   ├── client.py               # NetCDF downloader
│   └── gridmet_singlelocation_client.py
├── prism/                      # PRISM package
│   ├── __init__.py
│   ├── daily_client.py
│   └── prism.csv               # Station metadata
├── snotel/                     # SNOTEL/SCAN package
└── validation/                 # Benchmarking workflows
    └── 24_us_stations/
```

## Troubleshooting

### "CLIGEN binary not found"
- Ensure `wepppy/climates/cligen/bin/cligen532` is executable and in the correct location
- Check `cligen.py` for `_bin_dir` path configuration
- Verify Docker container has binary bundled (see `docker/Dockerfile`)

### "Daymet API timeout"
- ORNL API can be slow during peak usage
- Increase retry attempts in `daymet_singlelocation_client.py`
- Consider caching results to `.parquet` files for reuse

### "GridMET NetCDF download failed"
- Check network connectivity to `climatologylab.org`
- Verify `/dev/shm` has sufficient space (NetCDF files can be 100+ MB)
- Confirm bounding box is within CONUS

### "PRISM revision produced NaN values"
- PRISM monthly normals may be missing for oceanic locations
- Check that lon/lat is within CONUS
- Verify `metquery_client` is pointing to correct endpoint

### "Interpolation produced incorrect values"
- Verify grid orientation (is latitude ascending or descending?)
- Check for coordinate system mismatches (lon/lat vs. projected)
- Confirm grid dimensions match data array shape

## Further Reading

- **AGENTS.md** § Common Tasks § Adding a New Climate Data Source
- **AGENTS.md** § Integration with External Tools (WEPP Fortran, Rust bindings)
- `wepppy/nodb/core/climate.py` - Climate NoDb controller implementation
- `wepppy/nodb/locales/climate_catalog.py` - Climate dataset metadata catalog
- `wepppy/wepp/README.md` - WEPP model file formats and interchange
- `docs/dev-notes/climate_data_sources.md` (if exists) - Detailed provider notes
- **External Resources**:
  - [Daymet Documentation](https://daymet.ornl.gov/)
  - [GridMET Information](http://www.climatologylab.org/gridmet.html)
  - [PRISM Climate Group](https://prism.oregonstate.edu/)
  - [CLIGEN Documentation](https://www.ars.usda.gov/research/software/download/?softwareid=411)

## Credits

**University of Idaho** (2015–Present): Roger Lew, Erin Brooks  
**USDA ARS**: CLIGEN development team, WEPP model development  
**ORNL**: Daymet dataset (Thornton et al.)  
**University of Idaho**: GridMET dataset (Abatzoglou)  
**Oregon State University**: PRISM dataset (Daly et al.)  

**License**: BSD-3 Clause (see `license.txt` in repository root)

**Funding**: NSF Idaho EPSCoR (IIA-1301792), USDA Forest Service, USGS, NASA
