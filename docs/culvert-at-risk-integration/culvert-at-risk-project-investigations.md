# Culvert-at-Risk Project Investigations

**Date:** 2026-01-05
**Purpose:** Determine which files from transferred Culvert_web_app projects can populate the wepp.cloud payload (DEM, streams, watersheds, culvert points)

## Projects Investigated

- Hubbard Brook Experimental Forest
- santee_bayesian_rfa
- Santee_10m_no_hydroenforcement

**Data Locations:**
- Inputs: `/wc1/culvert_app_instance_dir/user_data/1_inputs/`
- Outputs: `/wc1/culvert_app_instance_dir/user_data/1_outputs/`

---

## Summary

| Project | WS Delineation | Hydro-enforced DEM | Watersheds Raster | Streams Raster | Culvert Points |
|---------|----------------|-------------------|-------------------|----------------|----------------|
| Hubbard Brook Experimental Forest | Complete | Present | Missing (polygon only) | Missing | Shapefile (210 pts) |
| santee_bayesian_rfa | **Not run** | N/A | N/A | N/A | Input only |
| Santee_10m_no_hydroenforcement | Complete | **Present** (despite name) | Missing (polygon only) | Present | Shapefile (63 pts) |

---

## Project 1: Hubbard Brook Experimental Forest

### Files Available

| Payload Target | File Path | CRS | Resolution | Status |
|----------------|-----------|-----|------------|--------|
| `topo/hydro-enforced-dem.tif` | `WS_deln/breached_filled_DEM_UTM.tif` | EPSG:32619 (WGS84/UTM 19N) | 1m | Ready |
| `topo/dem.tif` (fallback) | `WS_deln/DEM_UTM.tif` | EPSG:32619 | 1m | Ready |
| `topo/watersheds.tif` | **MISSING** | - | - | Only `all_ws_polygon_UTM.shp` available |
| `topo/streams.tif` | **MISSING** | - | - | No stream raster; only flow accumulation |
| `culverts/culvert_points.geojson` | `WS_deln/Pour_Point_UTM.shp` | EPSG:32619 | - | Needs shp→geojson conversion |

### Detailed File Inventory

**DEM Files (WS_deln/):**
- `DEM_UTM.tif` - Original DEM, 8910x5510 pixels, 1m resolution
- `breached_filled_DEM_UTM.tif` - Hydro-enforced DEM, same dimensions

**Watershed Files (WS_deln/):**
- `all_ws_polygon_UTM.shp` - 187 watershed polygons with `Point_ID` attribute
- No raster version exists

**Stream Files:**
- `bD8Flow_accum_UTM.tif` - Flow accumulation (can be thresholded to derive streams)
- `D8flow_dir_UTM.tif` - Flow direction
- No stream raster or vector exists

**Culvert Points (WS_deln/):**
- `Pour_Point_UTM.shp` - 210 points
- Attributes include: `Point_ID`, `Point_Name`, `Width_ft`, `Height_ft`, `Longitude`, `Latitude`, `Material`, `Condition`

### Blockers

1. **No watersheds raster** - Must rasterize `all_ws_polygon_UTM.shp` using `Point_ID` as burn value
2. **No streams raster** - Must either:
   - Threshold `bD8Flow_accum_UTM.tif` to create binary streams raster
   - Or re-run WS delineation with stream raster export enabled

---

## Project 2: santee_bayesian_rfa

### Status: NOT VIABLE

The outputs folder is **empty** - watershed delineation was never completed.

### Inputs Available (for reference)

| File | Location | CRS | Resolution |
|------|----------|-----|------------|
| dem.tif | `inputs/santee_bayesian_rfa/dem.tif` | EPSG:26917 (NAD83/UTM 17N) | 1m |
| pour_point.zip | `inputs/santee_bayesian_rfa/pour_point.zip` | Unknown | - |
| boundary.zip | `inputs/santee_bayesian_rfa/boundary.zip` | Unknown | - |

### Blockers

- **Complete blocker**: Must run WS delineation before payload can be created
- Note: Input DEM uses NAD83 (EPSG:26917) vs WGS84 used by other projects - CRS transformation will occur during processing

---

## Project 3: Santee_10m_no_hydroenforcement

### Key Finding

**Despite the project name, a hydro-enforced DEM (`breached_filled_DEM_UTM.tif`) EXISTS** and was used for watershed delineation. The "no_hydroenforcement" likely refers to the original input DEM characteristic, not the processed outputs.

### Files Available

| Payload Target | File Path | CRS | Resolution | Status |
|----------------|-----------|-----|------------|--------|
| `topo/hydro-enforced-dem.tif` | `WS_deln/breached_filled_DEM_UTM.tif` | EPSG:32617 (WGS84/UTM 17N) | ~9.3m | Ready |
| `topo/dem.tif` (original) | `WS_deln/DEM_UTM.tif` | EPSG:32617 | ~9.3m | Ready |
| `topo/watersheds.tif` | **MISSING** | - | - | Only `all_ws_polygon_UTM.shp` available |
| `topo/streams.tif` | `hydrogeo_vuln/main_stream_raster_UTM.tif` | EPSG:32617 | ~9.3m | Ready, aligned with DEM |
| `culverts/culvert_points.geojson` | `WS_deln/Pour_Point_UTM.shp` | EPSG:32617 | - | Needs shp→geojson conversion |

### Detailed File Inventory

**DEM Files (WS_deln/):**
- `DEM_UTM.tif` - Original DEM, 833x789 pixels, ~9.33m resolution
- `breached_filled_DEM_UTM.tif` - Hydro-enforced DEM (breached and filled)
- `breaklines_burned_DEM_UTM.tif` - DEM with stream breaklines burned in
- `road_elevated_DEM_UTM.tif` - DEM with road elevations modified

**Watershed Files (WS_deln/):**
- `all_ws_polygon_UTM.shp` - 36 watershed polygons with `Point_ID` attribute
- `ws_polygon_filtered_by_area_UTM.shp` - Filtered watersheds
- `final_flag_removed_ws_polygon_filtered_by_area_UTM.shp` - Final filtered watersheds
- No raster version exists

**Stream Files:**
- `hydrogeo_vuln/main_stream_raster_UTM.tif` - Stream raster, Float32, NoData=-32768
- `WS_deln/stream_vector_UTM.shp` - Stream vector, 1047 line features

**Culvert Points (WS_deln/):**
- `Pour_Point_UTM.shp` - 63 points
- `Pour_Point_UTM_clipped.shp` - Clipped version
- `pour_point_filtered_UTM.shp` - Filtered version
- Attributes include: `Point_ID`, `Point_Name`, `Longitude`, `Latitude`, `Material`, `Condition`, `Rte_No`, `Milepost`

### Blockers

1. **No watersheds raster** - Must rasterize `all_ws_polygon_UTM.shp` using `Point_ID` as burn value

---

## Alignment Verification

### Extent and Resolution Consistency

| Project | Layer | Origin | Pixel Size | Dimensions |
|---------|-------|--------|------------|------------|
| Hubbard Brook | DEM_UTM.tif | (274818, 4871590) | 1.0m | 8910x5510 |
| Hubbard Brook | breached_filled_DEM_UTM.tif | (274818, 4871590) | 1.0m | 8910x5510 |
| Santee_10m | DEM_UTM.tif | (608473.6, 3673080.7) | 9.326m | 833x789 |
| Santee_10m | breached_filled_DEM_UTM.tif | (608473.6, 3673080.7) | 9.326m | 833x789 |
| Santee_10m | main_stream_raster_UTM.tif | (608473.6, 3673080.7) | 9.326m | 833x789 |

All layers within each project are properly aligned.

---

## Payload Mapping Recommendations

### For Santee_10m_no_hydroenforcement (Most Complete)

This project is recommended as the primary candidate for payload assembly.

```
topo/
├── hydro-enforced-dem.tif    ← breached_filled_DEM_UTM.tif (copy)
├── streams.tif               ← main_stream_raster_UTM.tif (copy)
└── watersheds.tif            ← GENERATE: rasterize all_ws_polygon_UTM.shp

culverts/
└── culvert_points.geojson    ← CONVERT: ogr2ogr from Pour_Point_UTM.shp
```

**Rasterization command (watersheds):**
```bash
gdal_rasterize -a Point_ID \
  -tr 9.325770936 9.325770936 \
  -te 608473.596 3665722.666 616241.963 3673080.699 \
  -ot Int32 -of GTiff \
  WS_deln/all_ws_polygon_UTM.shp \
  topo/watersheds.tif
```

**Conversion command (culverts):**
```bash
ogr2ogr -f GeoJSON \
  culverts/culvert_points.geojson \
  WS_deln/Pour_Point_UTM.shp
```

### For Hubbard Brook Experimental Forest

```
topo/
├── hydro-enforced-dem.tif    ← breached_filled_DEM_UTM.tif (copy)
├── streams.tif               ← GENERATE: threshold bD8Flow_accum_UTM.tif
└── watersheds.tif            ← GENERATE: rasterize all_ws_polygon_UTM.shp

culverts/
└── culvert_points.geojson    ← CONVERT: ogr2ogr from Pour_Point_UTM.shp
```

**Stream derivation from flow accumulation:**
```bash
# Threshold flow accumulation to create binary stream raster
# Threshold value depends on desired stream density (e.g., 1000 cells)
gdal_calc.py -A bD8Flow_accum_UTM.tif \
  --outfile=streams.tif \
  --calc="(A>1000)*1" \
  --type=Byte --NoDataValue=0
```

**Rasterization command (watersheds):**
```bash
gdal_rasterize -a Point_ID \
  -tr 1.0 1.0 \
  -te 274818 4866080 283728 4871590 \
  -ot Int32 -of GTiff \
  WS_deln/all_ws_polygon_UTM.shp \
  topo/watersheds.tif
```

### For santee_bayesian_rfa

**Cannot proceed** - Must re-run watershed delineation in Culvert_web_app first to generate outputs.

---

## DEM Selection Rationale

### Why Use `breached_filled_DEM_UTM.tif`?

For both viable projects, the `breached_filled_DEM_UTM.tif` should be used as the hydro-enforced DEM because:

1. **Consistency**: The watershed delineation was performed using this DEM, so watersheds are topologically consistent with it
2. **Hydrologic correctness**: Breaching and filling removes spurious pits that would create disconnected drainage
3. **Flow routing**: The D8 flow direction and accumulation grids were derived from this DEM

### Santee_10m "no_hydroenforcement" Clarification

The project name is misleading. Investigation confirmed:
- `breached_filled_DEM_UTM.tif` exists and differs from `DEM_UTM.tif`
- Watersheds were derived using the hydro-enforced version
- The payload should use `breached_filled_DEM_UTM.tif` to maintain consistency

---

## Blockers and Inconsistencies Summary

| Project | Blocker | Severity | Resolution |
|---------|---------|----------|------------|
| Hubbard Brook | Missing streams raster | Medium | Derive from flow accumulation |
| Hubbard Brook | Missing watersheds raster | Low | Rasterize polygon |
| Hubbard Brook | Shapefile needs conversion | Low | ogr2ogr to GeoJSON |
| santee_bayesian_rfa | No outputs exist | **Critical** | Re-run WS delineation |
| Santee_10m | Missing watersheds raster | Low | Rasterize polygon |
| Santee_10m | Shapefile needs conversion | Low | ogr2ogr to GeoJSON |

---

## Conclusion

**Santee_10m_no_hydroenforcement** is the most viable project for immediate payload assembly:
- Has hydro-enforced DEM (despite project name suggesting otherwise)
- Has stream raster already generated and aligned
- Only needs watershed polygon-to-raster conversion and shapefile-to-geojson conversion
- All layers are properly aligned in CRS and resolution

**Hubbard Brook** requires additional processing:
- Stream raster must be derived from flow accumulation
- Watershed raster must be generated from polygons
- Higher resolution (1m vs ~9m) means larger file sizes

**santee_bayesian_rfa** is blocked until watershed delineation is executed in the Culvert_web_app.
