# ISRIC WMS Service - Missing CRS Metadata Issue

## Email to ISRIC Support

**To:** ISRIC SoilGrids Support  
**Subject:** Missing CRS Metadata in WMS GetMap Response for EPSG:152160  
**Date:** November 15, 2025

---

Dear ISRIC SoilGrids Team,

I hope this message finds you well. I am writing to report an issue we have encountered with the ISRIC SoilGrids WMS service that has recently begun affecting our production workflows.

### Issue Summary

When requesting GeoTIFF data via WMS GetMap using **EPSG:152160** (Homolosine projection), the returned GeoTIFF files are missing embedded CRS/projection metadata (empty WKT string). This same request returns complete projection metadata when using **EPSG:4326**.

### Impact

This issue causes GDAL/OGR operations that depend on projection metadata to fail with "Corrupt data" errors. Our application uses `osr.SpatialReference.ImportFromWkt()` to extract projection information from the downloaded rasters, which fails when the WKT string is empty.

### Timeline

This behavior appears to have started approximately one week ago (early November 2025). Our code has been using EPSG:152160 successfully since September 2025 without issues.

**Note:** We initially suspected typehint changes made to the ISRIC module on November 9, 2025 (commit 727fbb7210d2ad79963c4b45ba7999f3a7cb83d4), but review of that commit confirms it contained only cosmetic changes (import reorganization, type annotations, docstring formatting). No functional changes were made to the WMS request logic, CRS handling, or data processing. The timing correlation is coincidental - this is a server-side issue at ISRIC.

### Test Results

We conducted comprehensive testing that revealed:

1. **EPSG:152160 (Homolosine)**: Returns GeoTIFF with **empty WKT projection string** (length 0)
2. **EPSG:4326 (WGS84)**: Returns GeoTIFF with **complete projection metadata** (WKT length 302 characters)

Importantly, we verified that the **pixel data itself is correct** for EPSG:152160 by comparing WRB classification distributions between both projections. The distributions match within 1-2%, confirming the geographic data is properly registered - only the metadata is missing.

**WRB Classification Comparison (British Columbia test area):**
- EPSG:152160: 88.8% Podzols (value 23), 11.2% Cambisols (value 6)
- EPSG:4326: 89.9% Podzols (value 23), 10.1% Cambisols (value 6)

### Reproduction Script

Below is a standalone Python script that demonstrates the issue. This script requires only `owslib` and `gdal` (GDAL 3.x):

```python
#!/usr/bin/env python3
"""
Test script to reproduce missing CRS metadata in ISRIC WMS GetMap responses
when using EPSG:152160 (Homolosine projection).

Requirements:
    pip install owslib
    # GDAL 3.x (system package)

Contact: [Your Organization]
Date: November 15, 2025
"""

from owslib.wms import WebMapService
import tempfile
import os
from osgeo import gdal

# WMS endpoint for bulk density layer
wms_url = 'https://maps.isric.org/mapserv?map=/map/bdod.map'
wms = WebMapService(wms_url)
layer = 'bdod_0-5cm_Q0.5'

# Test area: British Columbia, Canada
# Both requests cover the same geographic area but use different CRS

print('=' * 60)
print('ISRIC WMS GetMap CRS Metadata Test')
print('=' * 60)

# Test 1: EPSG:152160 (Homolosine - ISRIC native projection)
print('\n[TEST 1] Requesting with EPSG:152160 (Homolosine)')
print('-' * 60)

crs1 = 'EPSG:152160'
bbox1 = (-12774700, 5511400, -12767800, 5516600)  # Projected coordinates in meters
size1 = (69, 52)  # Width x Height in pixels

response1 = wms.getmap(
    layers=[layer],
    srs=crs1,
    bbox=bbox1,
    size=size1,
    format='image/tiff'
)

with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
    tmp.write(response1.read())
    tmp_path1 = tmp.name

ds1 = gdal.Open(tmp_path1)
wkt1 = ds1.GetProjection()
gt1 = ds1.GetGeoTransform()

print(f'Response file: {tmp_path1}')
print(f'Raster size: {ds1.RasterXSize} x {ds1.RasterYSize}')
print(f'GeoTransform: {gt1}')
print(f'WKT Projection length: {len(wkt1)} characters')
print(f'WKT content: "{wkt1}"')

if len(wkt1) == 0:
    print('❌ ISSUE DETECTED: WKT projection string is EMPTY')
else:
    print('✓ WKT projection metadata present')

ds1 = None  # Close dataset
os.unlink(tmp_path1)

# Test 2: EPSG:4326 (WGS84 - standard lat/lon)
print('\n[TEST 2] Requesting with EPSG:4326 (WGS84)')
print('-' * 60)

crs2 = 'EPSG:4326'
bbox2 = (-121.5286159515381, 49.758813146320044, 
         -121.45308494567873, 49.80769290775831)  # Same area in degrees
size2 = (69, 52)  # Same raster size

response2 = wms.getmap(
    layers=[layer],
    srs=crs2,
    bbox=bbox2,
    size=size2,
    format='image/tiff'
)

with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
    tmp.write(response2.read())
    tmp_path2 = tmp.name

ds2 = gdal.Open(tmp_path2)
wkt2 = ds2.GetProjection()
gt2 = ds2.GetGeoTransform()

print(f'Response file: {tmp_path2}')
print(f'Raster size: {ds2.RasterXSize} x {ds2.RasterYSize}')
print(f'GeoTransform: {gt2}')
print(f'WKT Projection length: {len(wkt2)} characters')
print(f'WKT content (first 100 chars): "{wkt2[:100]}..."')

if len(wkt2) > 0:
    print('✓ WKT projection metadata present')
else:
    print('❌ WKT projection string is EMPTY')

ds2 = None  # Close dataset
os.unlink(tmp_path2)

# Summary
print('\n' + '=' * 60)
print('SUMMARY')
print('=' * 60)
print(f'EPSG:152160 WKT length: {len(wkt1)} (Expected: >0)')
print(f'EPSG:4326 WKT length:   {len(wkt2)} (Expected: >0)')

if len(wkt1) == 0 and len(wkt2) > 0:
    print('\n⚠️  CONFIRMED: EPSG:152160 returns GeoTIFFs without CRS metadata')
    print('    while EPSG:4326 includes complete projection information.')
elif len(wkt1) > 0 and len(wkt2) > 0:
    print('\n✓ Both projections return complete CRS metadata')
else:
    print('\n❌ Unexpected result - both projections missing metadata')

print('=' * 60)
```

### Request

Could you please investigate why EPSG:152160 requests are no longer returning embedded CRS metadata? We would greatly appreciate any insight into:

1. Whether this is a known issue or recent configuration change
2. Expected timeline for restoration of CRS metadata in EPSG:152160 responses
3. Any recommended workarounds while this issue is being addressed

### Workaround

As an interim solution, we are planning to switch our implementation to use EPSG:4326, which currently provides complete metadata. According to your FAQ documentation (https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html), EPSG:4326 is explicitly listed as a supported alternative SRS for WMS/WCS access, and the documentation states that "The Homolosine projection is not mandatory in any way."

We note that EPSG:152160 is described in your documentation as a "pseudo EPSG code" created for MapServer compatibility rather than an official EPSG code. This may be relevant to the current issue.

### System Information

- WMS Endpoint: https://maps.isric.org/mapserv
- Tested layers: bdod, clay, sand, wrb (all show same behavior)
- Client: Python with OWSLib 0.29.x and GDAL 3.10.3
- Tested dates: November 13-15, 2025

Thank you very much for your time and assistance. We appreciate the excellent SoilGrids service and look forward to your response.

Best regards,

[Your Name]  
[Your Organization]  
[Contact Information]

---

## Internal Notes

### Decision Log

**Date:** November 15, 2025  
**Decision:** Switch to EPSG:4326 for production use  
**Rationale:**
1. Returns complete CRS metadata (fixes immediate error)
2. Data accuracy verified via WRB classification comparison
3. More widely supported standard projection
4. Unknown timeline for ISRIC fix

### Code Changes Required

Modify `/workdir/wepppy/wepppy/locales/earth/soils/isric/__init__.py`:

1. Line 198: Change `crs = 'EPSG:152160'` to `crs = 'EPSG:4326'`
2. Line 164: Use `wgs_bbox` instead of `adj_bbox` for WMS request
3. Line 164: Use geographic size calculation instead of projected grid
4. Line 252: Same changes for `fetch_isric_wrb()`

### Testing Checklist

- [ ] Verify profile playback tests pass
- [ ] Check production runs complete successfully
- [ ] Validate soil property values are reasonable
- [ ] Monitor for any coordinate transformation errors
- [ ] Update documentation to note EPSG:4326 usage

### References

- Original implementation: Commit 54a73714bc (September 2025)
- Issue first observed: ~November 8, 2025
- Diagnosis session: November 13-15, 2025
