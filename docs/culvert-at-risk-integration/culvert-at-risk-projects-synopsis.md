# Culvert-at-Risk Projects Synopsis

**Generated:** 2026-01-05 10:23:53

This document provides an automated inventory of Culvert-at-Risk projects and their
readiness for wepp.cloud payload generation.

---

## Quick Summary

- Total projects: 35
- Users scanned: 20
- VIABLE projects (WS delineation complete): 20

| User | Project | WS Deln | Hydro-DEM | Watersheds | Streams | Culverts |
|------|---------|---------|-----------|------------|---------|----------|
| 1 | Hubbard Brook Experimental Forest | Yes | Yes (374.6 MB) | Polygon (718.0 KB) | Raster (187.3 MB) | Yes (310.0 KB) |
| 1 | Santee Experimental Forest | No | No | No | No | No |
| 1 | Santee_10m_no_hydroenforcement | Yes | Yes (5.0 MB) | Polygon (268.7 KB) | Raster (2.5 MB) | Yes (64.2 KB) |
| 1 | Santee_no_pour_point | Yes | Yes (110.4 MB) | Polygon (5.5 MB) | Vector (1.8 MB) | No |
| 1 | Santee_vs_streamstats | Yes | Yes (57.8 MB) | Polygon (330.9 KB) | Vector (9.1 MB) | Yes (66.2 KB) |
| 1 | Tallulah River | Yes | Yes (2.86 GB) | Polygon (379.8 KB) | Raster (1.43 GB) | Yes (228.0 KB) |
| 1 | Tallulah River Demo | Yes | Yes (2.86 GB) | Polygon (662.9 KB) | Vector (379.0 MB) | Yes (228.0 KB) |
| 1 | Tallulah River Hurrican Hellen | Yes | Yes (2.86 GB) | Polygon (379.8 KB) | Raster (1.43 GB) | Yes (228.0 KB) |
| 1 | santee_bayesian_rfa | No | No | No | No | No |
| 2 | Santee Test1 | Yes | Yes (435.2 MB) | Polygon (475.8 KB) | Raster (217.6 MB) | Yes (66.2 KB) |
| 3 | Santee_Culverts_Test | No | No | No | No | No |
| 3 | Tallulah_Culvert | No | No | No | No | No |
| 4 | ___ | Yes | Yes (435.2 MB) | Polygon (475.8 KB) | Raster (217.6 MB) | Yes (66.2 KB) |
| 4 | test | No | No | No | No | No |
| 4 | testes | Yes | Yes (435.2 MB) | Polygon (475.8 KB) | Vector (40.2 MB) | Yes (66.2 KB) |
| 4 | testtesttest | Yes | Yes (435.2 MB) | Polygon (475.8 KB) | Vector (40.2 MB) | Yes (66.2 KB) |
| 5 | Coweeta | No | No | No | No | No |
| 6 | Chipola EF P001 | Yes | Yes (74.3 MB) | No | Vector (10.0 MB) | No |
| 6 | Deep Creek WS_001 | Yes | Yes (101.5 MB) | Polygon (7.0 MB) | Raster (50.8 MB) | No |
| 7 | Apalachicola National Forest | No | No | No | No | No |
| 8 | Practice-Test | Yes | Yes (98.2 MB) | Polygon (2.9 MB) | Vector (8.8 MB) | No |
| 9 | Test_Project | Yes | Yes (10.1 MB) | Polygon (258.3 KB) | Vector (1.4 MB) | No |
| 10 | WO_test1 | No | No | No | No | No |
| 11 | test - nd | No | No | No | No | No |
| 12 | SSP_Analysis | No | No | No | No | No |
| 13 | Claremont | Yes | Yes (3.0 MB) | No | Vector (579.7 KB) | No |
| 14 | Test | Yes | Yes (51.3 MB) | Polygon (1.8 MB) | Vector (7.1 MB) | No |
| 14 | test2 | Yes | Yes (9.3 MB) | No | Vector (2.0 MB) | No |
| 15 | Garson | No | No | No | No | No |
| 16 | N Pebble | No | No | No | No | No |
| 17 | testing | Yes | No | No | No | Yes (1.1 KB) |
| 17 | testing2 | No | No | No | No | No |
| 19 | Test Project - Garnet Dike Area | Yes | Yes (5.1 MB) | Polygon (37.8 KB) | Vector (360.8 KB) | No |
| 21 | TreatmentArea3 | No | No | No | No | No |
| 25 | Test | No | No | No | No | No |

**Legend:**
- WS Deln: Watershed delineation completed
- Hydro-DEM: Hydro-enforced DEM available
- Watersheds: Watershed polygons available (Polygon = shapefile, needs GeoJSON conversion; raster not required)
- Streams: Stream raster available (Raster/Vector/FlowAcc/No)
- Culverts: Culvert points available (count shown if shapefile exists)

---

## Detailed Project Reports

### [User 1] Hubbard Brook Experimental Forest

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 187.3 MB |
| breached_filled_DEM_UTM.tif | Present, 374.6 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 718.0 KB

**Stream Files:**

- Raster: Present, 187.3 MB
- Vector: Present, 64.7 MB
- Flow Accumulation: Present, 187.3 MB (can derive streams)

**Culvert Points:**

- Present, 310.0 KB
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] Santee Experimental Forest

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 1] Santee_10m_no_hydroenforcement

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 2.5 MB |
| breached_filled_DEM_UTM.tif | Present, 5.0 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 268.7 KB

**Stream Files:**

- Raster: Present, 2.5 MB
- Vector: Present, 415.4 KB
- Flow Accumulation: Present, 2.5 MB (can derive streams)

**Culvert Points:**

- Present, 64.2 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 55.2 MB |
| breached_filled_DEM_UTM.tif | Present, 110.4 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 5.5 MB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 1.8 MB
- Flow Accumulation: Present, 55.2 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Missing

---

### [User 1] Santee_vs_streamstats

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 28.9 MB |
| breached_filled_DEM_UTM.tif | Present, 57.8 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 330.9 KB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 9.1 MB
- Flow Accumulation: Present, 28.9 MB (can derive streams)

**Culvert Points:**

- Present, 66.2 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 1.43 GB |
| breached_filled_DEM_UTM.tif | Present, 2.86 GB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 379.8 KB

**Stream Files:**

- Raster: Present, 1.43 GB
- Vector: Present, 379.0 MB
- Flow Accumulation: Present, 1.43 GB (can derive streams)

**Culvert Points:**

- Present, 228.0 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 1.43 GB |
| breached_filled_DEM_UTM.tif | Present, 2.86 GB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 662.9 KB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 379.0 MB
- Flow Accumulation: Present, 1.43 GB (can derive streams)

**Culvert Points:**

- Present, 228.0 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 1.43 GB |
| breached_filled_DEM_UTM.tif | Present, 2.86 GB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 379.8 KB

**Stream Files:**

- Raster: Present, 1.43 GB
- Vector: Present, 379.0 MB
- Flow Accumulation: Present, 1.43 GB (can derive streams)

**Culvert Points:**

- Present, 228.0 KB
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

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 2] Santee Test1

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB

**Stream Files:**

- Raster: Present, 217.6 MB
- Vector: Present, 40.2 MB
- Flow Accumulation: Present, 217.6 MB (can derive streams)

**Culvert Points:**

- Present, 66.2 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB

**Stream Files:**

- Raster: Present, 217.6 MB
- Vector: Present, 40.2 MB
- Flow Accumulation: Present, 217.6 MB (can derive streams)

**Culvert Points:**

- Present, 66.2 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 40.2 MB
- Flow Accumulation: Present, 217.6 MB (can derive streams)

**Culvert Points:**

- Present, 66.2 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 217.6 MB |
| breached_filled_DEM_UTM.tif | Present, 435.2 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 475.8 KB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 40.2 MB
- Flow Accumulation: Present, 217.6 MB (can derive streams)

**Culvert Points:**

- Present, 66.2 KB
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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 37.1 MB |
| breached_filled_DEM_UTM.tif | Present, 74.3 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Missing

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 10.0 MB
- Flow Accumulation: Present, 37.1 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Missing (no watershed polygons)
- `culverts/culvert_points.geojson` - Missing

---

### [User 6] Deep Creek WS_001

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 50.8 MB |
| breached_filled_DEM_UTM.tif | Present, 101.5 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 7.0 MB

**Stream Files:**

- Raster: Present, 50.8 MB
- Vector: Present, 16.4 MB
- Flow Accumulation: Present, 50.8 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Missing

---

### [User 7] Apalachicola National Forest

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 8] Practice-Test

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 49.1 MB |
| breached_filled_DEM_UTM.tif | Present, 98.2 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 2.9 MB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 8.8 MB
- Flow Accumulation: Present, 49.1 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Missing

---

### [User 9] Test_Project

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 5.1 MB |
| breached_filled_DEM_UTM.tif | Present, 10.1 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 258.3 KB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 1.4 MB
- Flow Accumulation: Present, 5.1 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Missing

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

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 1.5 MB |
| breached_filled_DEM_UTM.tif | Present, 3.0 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Missing

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 579.7 KB
- Flow Accumulation: Present, 1.5 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Missing (no watershed polygons)
- `culverts/culvert_points.geojson` - Missing

---

### [User 14] Test

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 25.7 MB |
| breached_filled_DEM_UTM.tif | Present, 51.3 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 1.8 MB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 7.1 MB
- Flow Accumulation: Present, 25.7 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Missing

---

### [User 14] test2

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 4.7 MB |
| breached_filled_DEM_UTM.tif | Present, 9.3 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Missing

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 2.0 MB
- Flow Accumulation: Present, 4.7 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Missing (no watershed polygons)
- `culverts/culvert_points.geojson` - Missing

---

### [User 15] Garson

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 16] N Pebble

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 17] testing

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 7.2 MB |
| breached_filled_DEM_UTM.tif | Missing |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Missing

**Stream Files:**

- Raster: **Missing**

**Culvert Points:**

- Present, 1.1 KB
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Requires Processing:**
- `topo/hydro-enforced-dem.tif` - Missing hydro-enforced DEM
- `topo/streams.tif` - Missing (no source available)
- `culverts/watersheds.geojson` - Missing (no watershed polygons)
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 17] testing2

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 19] Test Project - Garnet Dike Area

**Status: VIABLE** - Watershed delineation complete

#### File Inventory

**DEM Files:**

| File | Status |
|------|--------|
| DEM_UTM.tif | Present, 2.6 MB |
| breached_filled_DEM_UTM.tif | Present, 5.1 MB |

**Watershed Files:**

- Raster: Missing (not required; polygons are used for payload)
- Polygon: Present, 37.8 KB

**Stream Files:**

- Raster: **Missing**
- Vector: Present, 360.8 KB
- Flow Accumulation: Present, 2.6 MB (can derive streams)

**Culvert Points:**

- **Missing**

#### Payload Readiness

**Ready:**
- `topo/hydro-enforced-dem.tif` - Ready (copy breached_filled_DEM_UTM.tif)

**Requires Processing:**
- `topo/streams.tif` - Generate by thresholding flow accumulation
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Missing

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
