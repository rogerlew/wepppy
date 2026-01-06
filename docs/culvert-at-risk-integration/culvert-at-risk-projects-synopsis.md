# Culvert-at-Risk Projects Synopsis

**Generated:** 2026-01-05 17:10:33

This document provides an automated inventory of Culvert-at-Risk projects and their
readiness for wepp.cloud payload generation.

---

## Quick Summary

- Total projects: 36
- Users scanned: 20
- VIABLE projects (WS Deln + Hydro-DEM + Watersheds + Streams + Culverts): 11

| User | Project | WS Deln | Hydro-DEM | Hydro-DEM Res | Watersheds | Streams | Culverts | # Culverts |
|------|---------|---------|-----------|---------------|------------|---------|----------|-----------|
| 1 | Hubbard Brook Experimental Forest | Yes | Yes (374.6 MB) | 1.00m | Polygon (718.0 KB) | Raster (187.3 MB) | Yes (310.0 KB) | 210 |
| 1 | SANEF | Yes | Yes (435.2 MB) | 1.00m | Polygon (810.4 KB) | Vector (40.2 MB) | Yes (64.2 KB) | 63 |
| 1 | Santee Experimental Forest | No | No | — | No | No | No | — |
| 1 | Santee_10m_no_hydroenforcement | Yes | Yes (5.0 MB) | 9.33m | Polygon (268.7 KB) | Raster (2.5 MB) | Yes (64.2 KB) | 63 |
| 1 | Santee_no_pour_point | Yes | Yes (110.4 MB) | 9.20m | Polygon (5.5 MB) | Vector (1.8 MB) | No | — |
| 1 | Santee_vs_streamstats | Yes | Yes (57.8 MB) | 9.16m | Polygon (330.9 KB) | Vector (9.1 MB) | Yes (66.2 KB) | 65 |
| 1 | Tallulah River | Yes | Yes (2.86 GB) | 0.82m | Polygon (379.8 KB) | Raster (1.43 GB) | Yes (228.0 KB) | 49 |
| 1 | Tallulah River Demo | Yes | Yes (2.86 GB) | 0.82m | Polygon (662.9 KB) | Vector (379.0 MB) | Yes (228.0 KB) | 49 |
| 1 | Tallulah River Hurrican Hellen | Yes | Yes (2.86 GB) | 0.82m | Polygon (379.8 KB) | Raster (1.43 GB) | Yes (228.0 KB) | 49 |
| 1 | santee_bayesian_rfa | Yes | No | — | No | No | No | — |
| 2 | Santee Test1 | Yes | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Raster (217.6 MB) | Yes (66.2 KB) | 65 |
| 3 | Santee_Culverts_Test | No | No | — | No | No | No | — |
| 3 | Tallulah_Culvert | No | No | — | No | No | No | — |
| 4 | ___ | Yes | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Raster (217.6 MB) | Yes (66.2 KB) | 65 |
| 4 | test | No | No | — | No | No | No | — |
| 4 | testes | Yes | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Vector (40.2 MB) | Yes (66.2 KB) | 65 |
| 4 | testtesttest | Yes | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Vector (40.2 MB) | Yes (66.2 KB) | 65 |
| 5 | Coweeta | No | No | — | No | No | No | — |
| 6 | Chipola EF P001 | Yes | Yes (74.3 MB) | 1.00m | No | Vector (10.0 MB) | No | — |
| 6 | Deep Creek WS_001 | Yes | Yes (101.5 MB) | 9.41m | Polygon (7.0 MB) | Raster (50.8 MB) | No | — |
| 7 | Apalachicola National Forest | No | No | — | No | No | No | — |
| 8 | Practice-Test | Yes | Yes (98.2 MB) | 9.76m | Polygon (2.9 MB) | Vector (8.8 MB) | No | — |
| 9 | Test_Project | Yes | Yes (10.1 MB) | 9.37m | Polygon (258.3 KB) | Vector (1.4 MB) | No | — |
| 10 | WO_test1 | No | No | — | No | No | No | — |
| 11 | test - nd | No | No | — | No | No | No | — |
| 12 | SSP_Analysis | No | No | — | No | No | No | — |
| 13 | Claremont | Yes | Yes (3.0 MB) | 8.75m | No | Vector (579.7 KB) | No | — |
| 14 | Test | Yes | Yes (51.3 MB) | 7.85m | Polygon (1.8 MB) | Vector (7.1 MB) | No | — |
| 14 | test2 | Yes | Yes (9.3 MB) | 9.24m | No | Vector (2.0 MB) | No | — |
| 15 | Garson | No | No | — | No | No | No | — |
| 16 | N Pebble | No | No | — | No | No | No | — |
| 17 | testing | Yes | No | — | No | No | Yes (1.1 KB) | 8 |
| 17 | testing2 | No | No | — | No | No | No | — |
| 19 | Test Project - Garnet Dike Area | Yes | Yes (5.1 MB) | 9.23m | Polygon (37.8 KB) | Vector (360.8 KB) | No | — |
| 21 | TreatmentArea3 | No | No | — | No | No | No | — |
| 25 | Test | No | No | — | No | No | No | — |

**Legend:**
- WS Deln: Watershed delineation completed
- Hydro-DEM: Hydro-enforced DEM available
- Hydro-DEM Res: Hydro-enforced DEM pixel resolution
- Watersheds: Watershed polygons available (Polygon = shapefile, needs GeoJSON conversion; raster not required)
- Streams: Stream raster available (Raster/Vector/FlowAcc/No)
- Culverts: Culvert points available
- # Culverts: Feature count from culvert points file

---

## Detailed Project Reports

### [User 1] Hubbard Brook Experimental Forest

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 187.3 MB, 1.00m, EPSG:32619 |
| breached_filled_DEM_UTM.tif | Present, 374.6 MB, 1.00m, EPSG:32619 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 718.0 KB, 187 features, EPSG:32619, has Point_ID

**Stream Files:**

- Raster: Present, 187.3 MB, 1.00m, EPSG:32619
- Vector: Present, 64.7 MB, 137378 features, EPSG:32619
- Flow Accumulation: Present, 187.3 MB, 1.00m, EPSG:32619 (can derive streams)

**Culvert Points:**

- Present, 310.0 KB, 210 features, EPSG:32619, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] SANEF

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB, 1.00m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB, 1.00m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 810.4 KB, 59 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 40.2 MB, 91703 features, EPSG:32617
- Flow Accumulation: Present, 217.6 MB, 1.00m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 64.2 KB, 63 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] Santee Experimental Forest

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 1] Santee_10m_no_hydroenforcement

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 2.5 MB, 9.33m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 5.0 MB, 9.33m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 268.7 KB, 36 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: Present, 2.5 MB, 9.33m, EPSG:32617
- Vector: Present, 415.4 KB, 1047 features, EPSG:32617
- Flow Accumulation: Present, 2.5 MB, 9.33m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 64.2 KB, 63 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] Santee_no_pour_point

**Status: INCOMPLETE** - Missing: Culverts

---

### [User 1] Santee_vs_streamstats

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 28.9 MB, 9.16m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 57.8 MB, 9.16m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 330.9 KB, 31 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 9.1 MB, 22384 features, EPSG:32617
- Flow Accumulation: Present, 28.9 MB, 9.16m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 66.2 KB, 65 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] Tallulah River

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 1.43 GB, 0.82m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 2.86 GB, 0.82m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 379.8 KB, 49 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: Present, 1.43 GB, 0.82m, EPSG:32617
- Vector: Present, 379.0 MB, 1023449 features, EPSG:32617
- Flow Accumulation: Present, 1.43 GB, 0.82m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 228.0 KB, 49 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] Tallulah River Demo

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 1.43 GB, 0.82m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 2.86 GB, 0.82m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 662.9 KB, 49 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 379.0 MB, 1023449 features, EPSG:32617
- Flow Accumulation: Present, 1.43 GB, 0.82m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 228.0 KB, 49 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] Tallulah River Hurrican Hellen

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 1.43 GB, 0.82m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 2.86 GB, 0.82m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 379.8 KB, 49 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: Present, 1.43 GB, 0.82m, EPSG:32617
- Vector: Present, 379.0 MB, 1023449 features, EPSG:32617
- Flow Accumulation: Present, 1.43 GB, 0.82m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 228.0 KB, 49 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] santee_bayesian_rfa

**Status: INCOMPLETE** - Missing: Hydro-DEM, Watersheds, Streams, Culverts

---

### [User 2] Santee Test1

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB, 1.00m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB, 1.00m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB, 54 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: Present, 217.6 MB, 1.00m, EPSG:32617
- Vector: Present, 40.2 MB, 91714 features, EPSG:32617
- Flow Accumulation: Present, 217.6 MB, 1.00m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 66.2 KB, 65 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 3] Santee_Culverts_Test

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 3] Tallulah_Culvert

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 4] ___

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB, 1.00m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB, 1.00m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB, 54 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: Present, 217.6 MB, 1.00m, EPSG:32617
- Vector: Present, 40.2 MB, 91714 features, EPSG:32617
- Flow Accumulation: Present, 217.6 MB, 1.00m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 66.2 KB, 65 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 4] test

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 4] testes

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB, 1.00m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB, 1.00m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB, 54 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 40.2 MB, 91714 features, EPSG:32617
- Flow Accumulation: Present, 217.6 MB, 1.00m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 66.2 KB, 65 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 4] testtesttest

**Status: VIABLE** - WS Deln, Hydro-DEM, Watersheds, Streams, Culverts available

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB, 1.00m, EPSG:32617 |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB, 1.00m, EPSG:32617 |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB, 54 features, EPSG:32617, has Point_ID

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 40.2 MB, 91714 features, EPSG:32617
- Flow Accumulation: Present, 217.6 MB, 1.00m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 66.2 KB, 65 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 5] Coweeta

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 6] Chipola EF P001

**Status: INCOMPLETE** - Missing: Watersheds, Culverts

---

### [User 6] Deep Creek WS_001

**Status: INCOMPLETE** - Missing: Culverts

---

### [User 7] Apalachicola National Forest

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 8] Practice-Test

**Status: INCOMPLETE** - Missing: Culverts

---

### [User 9] Test_Project

**Status: INCOMPLETE** - Missing: Culverts

---

### [User 10] WO_test1

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 11] test - nd

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 12] SSP_Analysis

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 13] Claremont

**Status: INCOMPLETE** - Missing: Watersheds, Culverts

---

### [User 14] Test

**Status: INCOMPLETE** - Missing: Culverts

---

### [User 14] test2

**Status: INCOMPLETE** - Missing: Watersheds, Culverts

---

### [User 15] Garson

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 16] N Pebble

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 17] testing

**Status: INCOMPLETE** - Missing: Hydro-DEM, Watersheds, Streams

---

### [User 17] testing2

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 19] Test Project - Garnet Dike Area

**Status: INCOMPLETE** - Missing: Culverts

---

### [User 21] TreatmentArea3

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 25] Test

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

## Common Processing Commands

### Convert Watershed Polygons to GeoJSON

```bash
ogr2ogr -f GeoJSON \
  culverts/watersheds.geojson \
  WS_deln/all_ws_polygon_UTM.shp
```

### Convert Culvert Points to GeoJSON

```bash
ogr2ogr -f GeoJSON \
  culverts/culvert_points.geojson \
  WS_deln/Pour_Point_UTM.shp
```

### Derive Streams from Flow Accumulation (if stream raster missing)

```bash
# Threshold value (e.g., 1000) determines stream density
gdal_calc.py -A WS_deln/bD8Flow_accum_UTM.tif \
  --outfile=topo/streams.tif \
  --calc="(A>1000)*1" \
  --type=Byte --NoDataValue=0
```
