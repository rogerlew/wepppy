# Culvert-at-Risk Projects Synopsis

**Generated:** 2026-01-10 08:26:04

This document provides an automated inventory of Culvert-at-Risk projects and their
readiness for wepp.cloud payload generation.

---

## Quick Summary

- Total projects: 32
- Users scanned: 24
- VIABLE projects (WS Deln + Hydro-DEM + Nested WS + Streams + Culverts): 1

| User | Project | WS Deln | WS Method | FlowAccum | Hydro-DEM | Hydro-DEM Res | Watersheds | Streams | Culverts | # Culverts |
|------|---------|---------|-----------|-----------|-----------|---------------|------------|---------|----------|-----------|
| 1 | SANTEE | Yes | Nested | 100 | Yes (435.2 MB) | 1.00m | Polygon (810.4 KB) | Raster (217.6 MB) | Yes (64.2 KB) | 63 |
| 1 | Santee Experimental Forest | No | — | — | No | — | No | No | No | — |
| 2 | Santee Test1 | Yes | Partitioned | 100 | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Raster (217.6 MB) | Yes (66.2 KB) | 65 |
| 3 | Santee_Culverts_Test | No | — | — | No | — | No | No | No | — |
| 3 | Tallulah_Culvert | No | — | — | No | — | No | No | No | — |
| 4 | ___ | Yes | Partitioned | 100 | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Raster (217.6 MB) | Yes (66.2 KB) | 65 |
| 4 | test | No | — | — | No | — | No | No | No | — |
| 4 | testes | Yes | Partitioned | 100 | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Vector (40.2 MB) | Yes (66.2 KB) | 65 |
| 4 | testtesttest | Yes | Partitioned | 100 | Yes (435.2 MB) | 1.00m | Polygon (475.8 KB) | Vector (40.2 MB) | Yes (66.2 KB) | 65 |
| 5 | Coweeta | No | — | — | No | — | No | No | No | — |
| 6 | Chipola EF P001 | Yes | — | 100 | Yes (74.3 MB) | 1.00m | No | Vector (10.0 MB) | No | — |
| 6 | Deep Creek WS_001 | Yes | Partitioned | 100 | Yes (101.5 MB) | 9.41m | Polygon (7.0 MB) | Raster (50.8 MB) | No | — |
| 7 | Apalachicola National Forest | No | — | — | No | — | No | No | No | — |
| 8 | Practice-Test | Yes | Partitioned | 100 | Yes (98.2 MB) | 9.76m | Polygon (2.9 MB) | Vector (8.8 MB) | No | — |
| 9 | Test_Project | Yes | Partitioned | 100 | Yes (10.1 MB) | 9.37m | Polygon (258.3 KB) | Vector (1.4 MB) | No | — |
| 10 | WO_test1 | No | — | — | No | — | No | No | No | — |
| 11 | test - nd | No | — | — | No | — | No | No | No | — |
| 12 | SSP_Analysis | No | — | — | No | — | No | No | No | — |
| 13 | Claremont | Yes | — | — | Yes (3.0 MB) | 8.75m | No | Vector (579.7 KB) | No | — |
| 14 | Test | Yes | Partitioned | 100 | Yes (51.3 MB) | 7.85m | Polygon (1.8 MB) | Vector (7.1 MB) | No | — |
| 14 | test2 | Yes | — | 100 | Yes (9.3 MB) | 9.24m | No | Vector (2.0 MB) | No | — |
| 15 | Garson | No | — | — | No | — | No | No | No | — |
| 16 | N Pebble | No | — | — | No | — | No | No | No | — |
| 17 | testing | Yes | — | 100 | No | — | No | No | Yes (1.1 KB) | 8 |
| 17 | testing2 | No | — | — | No | — | No | No | No | — |
| 19 | Test Project - Garnet Dike Area | Yes | Partitioned | 100 | Yes (5.1 MB) | 9.23m | Polygon (37.8 KB) | Vector (360.8 KB) | No | — |
| 21 | TreatmentArea3 | No | — | — | No | — | No | No | No | — |
| 25 | Test | No | — | — | No | — | No | No | No | — |
| 27 | Lansing test case | Yes | Nested | 100 | Yes (7.1 MB) | 8.44m | Polygon (1.4 MB) | Raster (3.6 MB) | No | — |
| 28 | Test Data | No | — | — | No | — | No | No | No | — |
| 29 | Oklahoma Culverts | No | — | — | No | — | No | No | No | — |
| 30 | Modoc NF Trial | Yes | Nested | 100 | Yes (22.0 MB) | 8.75m | Polygon (959.0 KB) | Vector (5.7 MB) | No | — |

**Legend:**
- WS Deln: Watershed delineation completed
- WS Method: Watershed processing method
  - **Nested (N)**: `nested_basin_delineation()` - overlapping watersheds with hierarchy (N = count marked nested)
  - **Partitioned**: `delineate_watersheds_for_pour_points()` - non-overlapping partitioned watersheds
- FlowAccum: Flow accumulation threshold used for stream extraction (from `user_ws_deln_responses.txt`)
- Hydro-DEM: Hydro-enforced DEM available
- Hydro-DEM Res: Hydro-enforced DEM pixel resolution
- Watersheds: Watershed polygons available (Polygon = shapefile, needs GeoJSON conversion; raster not required)
- Streams: Stream raster available (Raster/Vector/FlowAcc/No)
- Culverts: Culvert points available
- # Culverts: Feature count from culvert points file

## Payload metadata note
- `metadata.json` should include `hydro_enforcement_select` (normalized from `hydroEnforcementSelect` in `user_ws_deln_responses.txt`) for traceability only; no branching depends on it yet.

---

## Detailed Project Reports

### [User 1] SANTEE

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
- Processing: **Nested** (`nested_basin_delineation`) - overlapping watersheds with hierarchy

**Stream Files:**

- Raster: Present, 217.6 MB, 1.00m, EPSG:32617
- Vector: Present, 40.2 MB, 91703 features, EPSG:32617
- Flow Accumulation: Present, 217.6 MB, 1.00m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 64.2 KB, 63 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/breached_filled_DEM_UTM.tif` - Ready (copy WS_deln/breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### [User 1] Santee Experimental Forest

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 2] Santee Test1

**Status: INCOMPLETE** - Missing: Nested WS

---

### [User 3] Santee_Culverts_Test

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 3] Tallulah_Culvert

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 4] ___

**Status: INCOMPLETE** - Missing: Nested WS

---

### [User 4] test

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 4] testes

**Status: INCOMPLETE** - Missing: Nested WS

---

### [User 4] testtesttest

**Status: INCOMPLETE** - Missing: Nested WS

---

### [User 5] Coweeta

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 6] Chipola EF P001

**Status: INCOMPLETE** - Missing: Watersheds, Nested WS, Culverts

---

### [User 6] Deep Creek WS_001

**Status: INCOMPLETE** - Missing: Nested WS, Culverts

---

### [User 7] Apalachicola National Forest

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 8] Practice-Test

**Status: INCOMPLETE** - Missing: Nested WS, Culverts

---

### [User 9] Test_Project

**Status: INCOMPLETE** - Missing: Nested WS, Culverts

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

**Status: INCOMPLETE** - Missing: Watersheds, Nested WS, Culverts

---

### [User 14] Test

**Status: INCOMPLETE** - Missing: Nested WS, Culverts

---

### [User 14] test2

**Status: INCOMPLETE** - Missing: Watersheds, Nested WS, Culverts

---

### [User 15] Garson

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 16] N Pebble

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 17] testing

**Status: INCOMPLETE** - Missing: Hydro-DEM, Watersheds, Nested WS, Streams

---

### [User 17] testing2

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 19] Test Project - Garnet Dike Area

**Status: INCOMPLETE** - Missing: Nested WS, Culverts

---

### [User 21] TreatmentArea3

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### [User 25] Test

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 27] Lansing test case

**Status: INCOMPLETE** - Missing: Culverts

---

### [User 28] Test Data

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 29] Oklahoma Culverts

**Status: NOT VIABLE** - No outputs exist. Watershed delineation has not been run.

**Inputs available:** Yes (dem.tif, pour_point.zip)

---

### [User 30] Modoc NF Trial

**Status: INCOMPLETE** - Missing: Culverts

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
