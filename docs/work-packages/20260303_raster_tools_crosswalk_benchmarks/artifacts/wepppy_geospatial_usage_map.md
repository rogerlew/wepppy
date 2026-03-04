# WEPPpy Geospatial Usage Map (Milestone 1)

## Evidence Base
- Raw callpath anchors:
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_weppcloud_callpath_evidence.txt:1`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_weppcloud_callpath_evidence.txt:34`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_weppcloud_callpath_evidence.txt:44`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_weppcloud_callpath_evidence.txt:66`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/orchestration_geospatial_refs.txt:7`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/weppcloud_geospatial_refs.txt:38`
- Direct WEPPpy sources: `/workdir/wepppy/wepppy/**`
- Direct dependency sources: `/home/workdir/{weppcloud-wbt,peridot,wepppyo3}`

## Operation Family: Delineation and Outlet-Finding
Call path:
- WEPPpy entrypoints:
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:154`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:160`
  - `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.py:720`
  - `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.py:910`
  - `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.py:1214`
- Dependency/tool implementation:
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/find_outlet.rs:22`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/watershed.rs:68`

## Operation Family: Subcatchment/Hillslope Abstraction
Call path:
- WEPPpy abstraction dispatch:
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:410`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:423`
  - `/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py:124`
- Peridot abstraction implementation:
  - `/home/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs:81`
  - `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs:171`
  - `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs:437`

## Operation Family: Stream Order Pruning and Junction Mutation (RQ)
Call path:
- WEPPpy RQ/topology utilities:
  - `/workdir/wepppy/wepppy/rq/topo_utils.py:46`
  - `/workdir/wepppy/wepppy/rq/topo_utils.py:69`
  - `/workdir/wepppy/wepppy/rq/culvert_rq.py:821`
  - `/workdir/wepppy/wepppy/rq/culvert_rq.py:853`
  - `/workdir/wepppy/wepppy/rq/culvert_rq.py:885`
- Dependency/tool implementation:
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/prune_strahler_order.rs:29`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/remove_short_streams.rs:30`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/stream_junctions.rs:8`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/gis_analysis/clip_raster_to_raster.rs:16`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/mod.rs:1078`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/mod.rs:1075`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/mod.rs:1102`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/mod.rs:576`

## Operation Family: DEM Ingest, Warp, and VRT Packaging
Call path:
- WEPPpy microservice ingest path:
  - `/workdir/wepppy/wepppy/microservices/rq_engine/watershed_routes.py:392`
  - `/workdir/wepppy/wepppy/microservices/rq_engine/watershed_routes.py:396`
  - `/workdir/wepppy/wepppy/microservices/rq_engine/watershed_routes.py:451`
- Additional runtime translate in culvert flow:
  - `/workdir/wepppy/wepppy/rq/culvert_rq.py:1188`

## Operation Family: Hillslope-Keyed Raster Classification (Landuse/Soils/Treatments)
Call path:
- WEPPpy module usage:
  - `/workdir/wepppy/wepppy/nodb/core/landuse.py:109`
  - `/workdir/wepppy/wepppy/nodb/core/landuse.py:732`
  - `/workdir/wepppy/wepppy/nodb/core/soils.py:499`
  - `/workdir/wepppy/wepppy/nodb/mods/disturbed/disturbed.py:814`
  - `/workdir/wepppy/wepppy/nodb/mods/treatments/treatments.py:171`
- Dependency implementation:
  - `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs:57`
  - `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs:537`

## Operation Family: SBS Reclassification and Export
Call path:
- WEPPpy BAER wrappers:
  - `/workdir/wepppy/wepppy/nodb/mods/baer/sbs_map.py:197`
  - `/workdir/wepppy/wepppy/nodb/mods/baer/sbs_map.py:212`
  - `/workdir/wepppy/wepppy/nodb/mods/baer/sbs_map.py:234`
  - `/workdir/wepppy/wepppy/nodb/mods/baer/sbs_map.py:249`
- Dependency implementation:
  - `/home/workdir/wepppyo3/sbs_map/src/lib.rs:894`
  - `/home/workdir/wepppyo3/sbs_map/src/lib.rs:948`
  - `/home/workdir/wepppyo3/sbs_map/src/lib.rs:1049`

## Operation Family: Geospatial API Serving and Browser Rendering
Call path:
- WEPPcloud API/resource routes:
  - `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/watershed_bp.py:36`
  - `/workdir/wepppy/wepppy/weppcloud/routes/nodb_api/watershed_bp.py:55`
  - `/workdir/wepppy/wepppy/weppcloud/routes/run_0/run_0_bp.py:639`
- GL dashboard raster/vector rendering:
  - `/workdir/wepppy/wepppy/weppcloud/static/js/gl-dashboard/map/raster-utils.js:49`
  - `/workdir/wepppy/wepppy/weppcloud/static/js/gl-dashboard/map/raster-utils.js:98`
  - `/workdir/wepppy/wepppy/weppcloud/static/js/gl-dashboard/map/layers.js:554`
  - `/workdir/wepppy/wepppy/weppcloud/static/js/gl-dashboard/map/layers.js:1036`

## Crosswalk Status (Observed in WEPPpy code paths)
- `weppcloud-wbt`: active usage observed.
- `peridot`: active usage observed.
- `wepppyo3`: active usage observed.
- `raster_tools`: not observed as a direct import/call under scanned `wepppy/**` code paths in this milestone pass.
- `oxidized-rasterstats`: not observed as a direct import/call under scanned `wepppy/**` code paths in this milestone pass.
