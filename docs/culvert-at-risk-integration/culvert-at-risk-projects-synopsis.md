# Culvert-at-Risk Projects Synopsis

**Generated:** 2026-01-10 08:24:44

This document provides an automated inventory of Culvert-at-Risk projects and their
readiness for wepp.cloud payload generation.

---

## Quick Summary

- Total projects: 9
- Users scanned: 1
- VIABLE projects (WS Deln + Hydro-DEM + Nested WS + Streams + Culverts): 2

| Project | WS Deln | WS Method | FlowAccum | Hydro-DEM | Hydro-DEM Res | Watersheds | Streams | Culverts | # Culverts |
|---------|---------|-----------|-----------|-----------|---------------|------------|---------|----------|-----------|
| Hubbard Brook Experimental Forest | Yes | Partitioned | 100 | Yes (374.6 MB) | 1.00m | Polygon (718.0 KB) | Raster (187.3 MB) | Yes (310.0 KB) | 210 |
| Santee_10m_no_hydroenforcement | Yes | Nested (27) | 100 | Yes (5.0 MB) | 9.33m | Polygon (268.7 KB) | Raster (2.5 MB) | Yes (64.2 KB) | 63 |
| Santee_no_pour_point | Yes | Nested (293) | 10000 | Yes (110.4 MB) | 9.20m | Polygon (5.5 MB) | Vector (1.8 MB) | No | — |
| Santee_vs_streamstats | Yes | Partitioned | 100 | Yes (57.8 MB) | 9.16m | Polygon (330.9 KB) | Vector (9.1 MB) | Yes (66.2 KB) | 65 |
| Tallulah River | Yes | Partitioned | 100 | Yes (2.86 GB) | 0.82m | Polygon (379.8 KB) | Raster (1.43 GB) | Yes (228.0 KB) | 49 |
| Tallulah River Demo | Yes | Nested (26) | 100 | Yes (2.86 GB) | 0.82m | Polygon (662.9 KB) | Raster (10.0 MB) | Yes (228.0 KB) | 49 |
| Tallulah River Hurrican Hellen | Yes | Partitioned | 100 | Yes (2.86 GB) | 0.82m | Polygon (379.8 KB) | Raster (1.43 GB) | Yes (228.0 KB) | 49 |
| docs | No | — | — | No | — | No | No | No | — |
| santee_bayesian_rfa | No | — | — | No | — | No | No | No | — |

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

### Hubbard Brook Experimental Forest

**Status: INCOMPLETE** - Missing: Nested WS

---

### Santee_10m_no_hydroenforcement

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
- Processing: **Nested** (`nested_basin_delineation`) - overlapping watersheds with hierarchy, 27 marked nested, 11 with children

**Stream Files:**

- Raster: Present, 2.5 MB, 9.33m, EPSG:32617
- Vector: Present, 415.4 KB, 1047 features, EPSG:32617
- Flow Accumulation: Present, 2.5 MB, 9.33m, EPSG:32617 (can derive streams)

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

### Santee_no_pour_point

**Status: INCOMPLETE** - Missing: Culverts

---

### Santee_vs_streamstats

**Status: INCOMPLETE** - Missing: Nested WS

---

### Tallulah River

**Status: INCOMPLETE** - Missing: Nested WS

---

### Tallulah River Demo

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
- Processing: **Nested** (`nested_basin_delineation`) - overlapping watersheds with hierarchy, 26 marked nested, 4 with children

**Stream Files:**

- Raster: Present, 10.0 MB, 0.82m, EPSG:32617
- Vector: Present, 379.0 MB, 1023449 features, EPSG:32617
- Flow Accumulation: Present, 1.43 GB, 0.82m, EPSG:32617 (can derive streams)

**Culvert Points:**

- Present, 228.0 KB, 49 features, EPSG:32617, has Point_ID
- Format: Shapefile (needs GeoJSON conversion for payload)

#### Payload Readiness

**Ready:**
- `topo/breached_filled_DEM_UTM.tif` - Ready (copy WS_deln/breached_filled_DEM_UTM.tif)
- `topo/streams.tif` - Ready (copy main_stream_raster_UTM.tif)

**Requires Processing:**
- `culverts/watersheds.geojson` - Convert from all_ws_polygon_UTM.shp
- `culverts/culvert_points.geojson` - Convert from shapefile

---

### Tallulah River Hurrican Hellen

**Status: INCOMPLETE** - Missing: Nested WS

---

### docs

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

---

### santee_bayesian_rfa

**Status: INCOMPLETE** - Output folder exists but WS_deln is empty or missing.

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
