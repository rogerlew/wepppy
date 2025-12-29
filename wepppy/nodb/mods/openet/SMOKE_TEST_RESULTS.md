# Climate Engine OpenET API - Smoke Test Results

**Date**: 2025-12-29
**Status**: ✅ PASSING

## Summary

The Climate Engine API integration with OpenET datasets is **working correctly**. The API key is valid, the dataset identifier has been corrected, and the service is returning actual evapotranspiration data from OpenET as expected.

## Key Findings

### 1. API Key Status
- ✅ API key loads correctly from `docker/.env` (CLIMATE_ENGINE_API_KEY)
- ✅ Authentication successful (returning 200 status codes)
- ✅ All API endpoints accessible

### 2. Dataset Configuration - CORRECTED

**Original (Incorrect) Configuration**:
```python
"ensemble": {
    "id": "OpenET/ENSEMBLE/CONUS/GRIDMET/MONTHLY/v2_0",  # ❌ WRONG
    "variables": ["et_ensemble_mad"],
},
```

**Corrected Configuration**:
```python
"ensemble": {
    "id": "OPENET_CONUS",  # ✅ CORRECT
    "variables": ["et_ensemble_mad"],
    "description": "OpenET Ensemble Median (MAD)"
},
"eemetric": {
    "id": "OPENET_CONUS",  # ✅ CORRECT
    "variables": ["et_eemetric"],
    "description": "OpenET eeMETRIC model"
},
"ssebop": {
    "id": "OPENET_CONUS",  # ✅ CORRECT
    "variables": ["et_ssebop"],
    "description": "OpenET SSEBop model"
},
```

**Key Discovery**: The Climate Engine API uses `OPENET_CONUS` as the dataset identifier, NOT the full Google Earth Engine path `OpenET/ENSEMBLE/CONUS/GRIDMET/MONTHLY/v2_0`.

### 3. Available OpenET Variables

All 9 OpenET variables are available through `OPENET_CONUS`:

**Individual Models** (6 satellite-driven ET models):
- `et_eemetric` - Evapotranspiration eeMETRIC
- `et_sims` - Evapotranspiration SIMS
- `et_ssebop` - Evapotranspiration SSEBop
- `et_geesebal` - Evapotranspiration geeSEBAL
- `et_ptjpl` - Evapotranspiration PT-JPL
- `et_disalexi` - Evapotranspiration DisALEXI

**Ensemble Statistics** (computed from the 6 models):
- `et_ensemble_mad` - Evapotranspiration Ensemble **Median** (MAD = Median Absolute Deviation)
- `et_ensemble_mad_min` - Evapotranspiration Ensemble **Minimum**
- `et_ensemble_mad_max` - Evapotranspiration Ensemble **Maximum**

### 4. Data Specifications

**Temporal Coverage**:
- Start: October 1, 1999
- End: December 1, 2024 (and ongoing)
- Interval: Monthly

**Spatial Coverage**:
- Region: CONUS (Continental United States)
- Resolution: 30 meters
- Reference ET: gridMET

**Units**:
- All ET values are in **millimeters per month**

### 5. Data Format

The Climate Engine API returns OpenET data in this structure:

```json
{
  "Request": {
    "dataset": "OPENET_CONUS",
    "variable": ["et_ensemble_mad"],
    "start_date": "2023-06-01",
    "end_date": "2023-08-31",
    ...
  },
  "Data": [
    {
      "Metadata": {
        "DRI_OBJECTID": "[coordinates]",
        "Statistic over region": "median"
      },
      "Data": [
        {
          "Date": "2023-06-01",
          "et_ensemble_mad (mm)": 94.0
        },
        {
          "Date": "2023-07-01",
          "et_ensemble_mad (mm)": 124.0
        },
        {
          "Date": "2023-08-01",
          "et_ensemble_mad (mm)": 87.0
        }
      ]
    }
  ]
}
```

**Important**: Variable names include units in parentheses (e.g., `"et_ensemble_mad (mm)"` not just `"et_ensemble_mad"`)

### 6. Test Results

**Test Configuration**:
- Dataset: OPENET_CONUS
- Date range: 2023-01-01 to 2023-12-31 (12 months)
- Features: 2 polygons from test GeoJSON (TopazID: 643, 23)
- Area reducer: median

**Results by Model**:

| Model | TopazID | Rows | Missing | Avg (mm/month) | Sample Values |
|-------|---------|------|---------|----------------|---------------|
| ensemble (median) | 643 | 12 | 0 | 15.17 | [4.0, 27.0, 4.0] |
| ensemble (median) | 23 | 12 | 0 | 18.67 | [6.0, 26.0, 4.0] |
| eemetric | 643 | 12 | 0 | 23.42 | [16.0, 27.0, 4.0] |
| eemetric | 23 | 12 | 0 | 33.58 | [16.0, 26.0, 4.0] |
| ssebop | 643 | 12 | 2 | 7.60 | [0.0, 0.0, 17.0] |
| ssebop | 23 | 12 | 0 | 14.58 | [3.0, 9.0, 27.0] |

**Summer Month Example** (June-August 2023):
```
2023-06-01: 94 mm
2023-07-01: 124 mm
2023-08-01: 87 mm
```

These values are reasonable for monthly actual ET in summer months.

## Code Changes Made

1. **Updated dataset configuration** (`smoke_climate_engine_openet.py:24-40`):
   - Changed from invalid `OpenET/ENSEMBLE/CONUS/GRIDMET/MONTHLY/v2_0` to correct `OPENET_CONUS`
   - Added three OpenET models: ensemble, eemetric, ssebop
   - Added descriptions for clarity

2. **Fixed variable parsing** (`smoke_climate_engine_openet.py:176-204`):
   - Added logic to find variable keys with units (e.g., "et_ensemble_mad (mm)")
   - Enhanced output with average calculation and sample values
   - Better error messages showing available keys

## Comparison: Two Different APIs

**Climate Engine API** (tested in this smoke test):
- URL: `https://api.climateengine.org/`
- Dataset: `OPENET_CONUS`
- Format: REST API with GET requests
- Returns: Monthly ET data (mm/month)
- Best for: Batch processing, automated workflows, GIS integration

**OpenET Direct API** (already implemented in `openet_client.py`):
- URL: `https://openet-api.org/`
- Format: REST API with POST requests
- Returns: Monthly ET data (mm/month)
- Best for: Direct OpenET integration, may have different features

Both APIs provide access to OpenET data but use different endpoints and request formats.

## Recommendations

1. ✅ Use `OPENET_CONUS` as the dataset identifier for Climate Engine API
2. ✅ Available variables match the specification (ensemble and individual models)
3. ✅ Data quality is good (minimal missing values)
4. ⚠️ Note: Data is monthly, not daily (one value per month)
5. ⚠️ Remember to handle variable names with units when parsing responses

## References

- [Climate Engine OpenET Documentation](https://support.climateengine.org/article/78-openet)
- [Climate Engine API Documentation](https://docs.climateengine.org/)
- [OpenET Official Website](https://etdata.org/)
- [Google Earth Engine OpenET Dataset](https://developers.google.com/earth-engine/datasets/catalog/OpenET_ENSEMBLE_CONUS_GRIDMET_MONTHLY_v2_0)
