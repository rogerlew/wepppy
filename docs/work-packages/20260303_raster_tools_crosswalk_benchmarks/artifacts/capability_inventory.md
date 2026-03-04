# Capability Inventory (Milestone 1)

## Evidence Base
- Raw note anchors:
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_capability_evidence.txt:1`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_capability_evidence.txt:11`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_capability_evidence.txt:25`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_capability_evidence.txt:53`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_capability_evidence.txt:105`
  - `docs/work-packages/20260303_raster_tools_crosswalk_benchmarks/notes/raw/m1_capability_evidence.txt:125`
- Direct source trees scanned:
  - `/home/workdir/raster_tools`
  - `/home/workdir/weppcloud-wbt`
  - `/home/workdir/peridot`
  - `/home/workdir/wepppyo3`
  - `/home/workdir/oxidized-rasterstats`
- WEPPpy integration surface scanned: `/workdir/wepppy/wepppy/**`

## Operation Family: Raster Reprojection and Grid Alignment
- `raster_tools` exposes reprojection as a first-class API:
  - `/home/workdir/raster_tools/raster_tools/warp.py:14`
  - `/home/workdir/raster_tools/raster_tools/raster.py:2188`
- WEPPpy runtime paths use GDAL reprojection/translation directly:
  - `/workdir/wepppy/wepppy/microservices/rq_engine/watershed_routes.py:392`
  - `/workdir/wepppy/wepppy/microservices/rq_engine/watershed_routes.py:396`
  - `/workdir/wepppy/wepppy/microservices/rq_engine/watershed_routes.py:451`
  - `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.py:589`

## Operation Family: Raster Clip/Mask/Rasterize
- `raster_tools` has explicit clip/mask/rasterize primitives:
  - `/home/workdir/raster_tools/raster_tools/clipping.py:81`
  - `/home/workdir/raster_tools/raster_tools/clipping.py:143`
  - `/home/workdir/raster_tools/raster_tools/rasterize.py:530`
- WEPPpy WBT orchestration relies on clip-to-mask operations:
  - `/workdir/wepppy/wepppy/topo/wbt/wbt_topaz_emulator.py:1352`
  - `/workdir/wepppy/wepppy/rq/culvert_rq.py:865`
  - `/workdir/wepppy/wepppy/rq/culvert_rq.py:885`
- `oxidized-rasterstats` zonal path rasterizes polygon masks before stats:
  - `/home/workdir/oxidized-rasterstats/src/zonal.rs:9`

## Operation Family: Hydrology and Watershed Delineation
- `weppcloud-wbt` exposes watershed toolchain primitives:
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/watershed.rs:68`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/find_outlet.rs:22`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/hydro_analysis/hillslopes_topaz.rs:127`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/stream_network_analysis/prune_strahler_order.rs:29`
  - `/home/workdir/weppcloud-wbt/whitebox-tools-app/src/tools/mod.rs:437`
- `peridot` contributes abstraction and flowpath construction:
  - `/home/workdir/peridot/src/wbt/wbt_watershed_abstraction.rs:81`
  - `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs:171`
  - `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs:437`
  - `/home/workdir/peridot/src/watershed_abstraction/watershed_abstraction.rs:470`
  - `/home/workdir/peridot/src/rasters/d8_wbt_to_topaz.rs:3`
- WEPPpy calls these paths through NoDb and RQ orchestration:
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:154`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:160`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:354`
  - `/workdir/wepppy/wepppy/rq/topo_utils.py:46`
  - `/workdir/wepppy/wepppy/rq/topo_utils.py:69`

## Operation Family: Raster Summaries, Zonal Stats, and Classification
- `raster_tools` zonal and terrain summary primitives:
  - `/home/workdir/raster_tools/raster_tools/zonal.py:300`
  - `/home/workdir/raster_tools/raster_tools/surface.py:168`
- `wepppyo3` keyed mode, SBS classification/export, and terrain point-aspect helper coverage:
  - `/home/workdir/wepppyo3/raster_characteristics/src/lib.rs:57`
  - `/home/workdir/wepppyo3/sbs_map/src/lib.rs:894`
  - `/home/workdir/wepppyo3/sbs_map/src/lib.rs:948`
  - `/home/workdir/wepppyo3/raster/src/raster.rs:590`
- `oxidized-rasterstats` Rust-backed zonal/point stats and percentile handling:
  - `/home/workdir/oxidized-rasterstats/src/lib.rs:36`
  - `/home/workdir/oxidized-rasterstats/src/lib.rs:86`
  - `/home/workdir/oxidized-rasterstats/src/stats.rs:159`
  - `/home/workdir/oxidized-rasterstats/python/rasterstats/_dispatch.py:79`
  - `/home/workdir/oxidized-rasterstats/python/rasterstats/_dispatch.py:187`

## Operation Family: WEPPpy-Coupled Capability Signal (from M1 scan)
- Active coupling observed to `weppcloud-wbt` (via WhiteboxTools paths), `peridot`, and `wepppyo3`:
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:54`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:154`
  - `/workdir/wepppy/wepppy/rq/topo_utils.py:7`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:36`
  - `/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py:37`
  - `/workdir/wepppy/wepppy/nodb/core/landuse.py:109`
  - `/workdir/wepppy/wepppy/nodb/core/soils.py:113`
- No direct in-tree imports/calls surfaced for `raster_tools` or `oxidized-rasterstats` under the scanned WEPPpy code paths during this milestone pass.
