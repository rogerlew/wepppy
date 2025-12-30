# NOAA Atlas 14 Test Artifacts

This directory contains test scripts and reference artifacts for NOAA Atlas 14 precipitation frequency data.

## Overview

NOAA Atlas 14 provides precipitation frequency estimates (PFEs) for the United States. The data includes:
- **Precipitation Intensity**: Rate of precipitation (mm/hour or inches/hour)
- **Precipitation Depth**: Total precipitation amount (mm or inches)
- **Time Series Types**:
  - PDS (Partial Duration Series)
  - AMS (Annual Maximum Series)
- **Statistics**: Mean, Upper bound (90% CI), Lower bound (90% CI)

## Test Script

### `test_atlas14_download.py`

Test script that verifies the `pfdf.data.noaa.atlas14.download` function and generates reference artifacts.

**Usage:**
```bash
python test_atlas14_download.py
```

**What it tests:**
1. Precipitation intensity download (metric units)
2. Precipitation depth download (metric units)
3. English units download (inches/hour)

## Reference Artifacts

The `artifacts/` directory contains sample downloaded data for reference:

### Intensity Data
- **`atlas14_intensity_pds_mean_metric.csv`**
  - Precipitation intensity in mm/hour
  - Partial Duration Series (PDS)
  - Mean values
  - Metric units

- **`atlas14_intensity_pds_mean_english.csv`**
  - Precipitation intensity in inches/hour
  - English units

### Depth Data
- **`atlas14_depth_pds_mean_metric.csv`**
  - Precipitation depth in mm
  - Partial Duration Series (PDS)
  - Mean values
  - Metric units

All artifacts are for test location: **39.0°N, 105.0°W** (Denver, CO area)

## Data Structure

Each CSV file contains:

1. **Header**: Metadata about the location and data type
   - Volume and version information
   - Data type (intensity or depth)
   - Time series type
   - Project area
   - Coordinates

2. **Frequency Estimates Table**: PFE values for different durations and return periods
   - Rows: Duration (5-min, 10-min, 15-min, 30-min, 1-hr, 2-hr, etc.)
   - Columns: Annual Recurrence Interval (ARI) in years (1, 2, 5, 10, 25, 50, 100, 200, 500, 1000)

## API Documentation

Official API documentation: https://ghsc.code-pages.usgs.gov/lhp/pfdf/api/data/noaa/atlas14.html

### Basic Usage

```python
from pfdf.data.noaa import atlas14

# Download precipitation intensity data
result = atlas14.download(
    lat=39.0,
    lon=-105.0,
    parent='/path/to/save',
    name='precipitation.csv',
    statistic='mean',      # Options: 'mean', 'upper', 'lower', 'all'
    data='intensity',      # Options: 'intensity', 'depth'
    series='pds',          # Options: 'pds', 'ams'
    units='metric',        # Options: 'metric', 'english'
    timeout=30
)
```

## Development Notes

### NumPy Compatibility
The pfdf library was updated to support NumPy 1.26+ by fixing deprecated `copy=None` parameter usage in array operations.

### Test Location
The test uses coordinates 39°N, 105°W which corresponds to:
- Project area: Midwestern States
- NOAA Atlas 14 Volume 8 Version 2

### Future Development
These artifacts can be used for:
- Validating data parsing routines
- Testing integration with WEPPcloud climate data processing
- Benchmarking precipitation frequency estimates
- Developing visualization tools

## Related Files

- `/workdir/pfdf/pfdf/data/noaa/atlas14.py` - Main implementation
- `/workdir/pfdf/tests/data/noaa/test_atlas14.py` - Unit tests
- `https://github.com/rogerlew/usgs-pfdf` - pfdf repository
