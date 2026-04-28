# wepppyo3 Codebase Posture Review (2026-04-28)

## Posture

`confirmed`: `/workdir/wepppyo3` is a Rust workspace that builds Python extension modules used by WEPPpy.

`confirmed`: The canonical release package is `/workdir/wepppyo3/release/linux/py312/wepppyo3/` and currently includes nine deployable extension modules.

`confirmed`: WEPPpy imports `wepppyo3` across production climate, raster, WEPP/SWAT interchange, roads, MOFE, BAER/SBS, RHEM, RAP, Omni, and visualization paths.

`inference`: The correct posture is **WEPPpy native kernel and interchange substrate**. It is not just a set of optional speedups; it is a contract-backed owned-stack layer that keeps Python orchestration while moving hot kernels, parsers, raster scans, and interchange writers into Rust.

`hypothesis`: Explicit repositioning will reduce duplicate Python implementations, improve release discipline, and make future work-routing decisions easier.

## Clean Claim Statement

`wepppyo3 is WEPPpy's native kernel and interchange substrate: Python-callable Rust modules for contract-sensitive hydrology, climate, raster, WEPP/SWAT interchange, roads, MOFE, SBS, and visualization workloads where Python orchestration should remain but the hot path belongs in owned Rust.`

## Legacy vs Current Framing

| Legacy framing | Current posture |
| --- | --- |
| Rust/PyO3 extension modules for WEPPpy | WEPPpy native kernel and interchange substrate |
| Optional accelerators where available | Owned production contract layer for selected hot paths |
| Flat function catalog | Module registry with maturity, callsites, release artifacts, tests, and evidence |
| Manual release copy instructions | Release provenance contract with explicit gaps and follow-up path |
| Per-module speedup notes | Claim discipline using `confirmed`, `inference`, and `hypothesis` |

## Evidence Inventory

### Workspace Shape

`confirmed`: Workspace members from `/workdir/wepppyo3/Cargo.toml`:

- `cli_revision`
- `geneva_core`
- `roads_flowpath`
- `raster`
- `raster_characteristics`
- `sbs_map`
- `swat_interchange`
- `swat_utils`
- `watershed_abstraction`
- `wepp_viz`
- `wepp_interchange`

### Code Size and PyO3 Surface

`confirmed`: Approximate nonblank/non-comment Rust LOC and exported PyO3 markers from local scan:

| Crate | Rust files | LOC | `#[pyfunction]` | `#[pymodule]` |
| --- | ---: | ---: | ---: | ---: |
| `cli_revision` | 3 | 1925 | 20 | 1 |
| `geneva_core` | 9 | 4747 | 0 | 0 |
| `raster` | 2 | 710 | 0 | 0 |
| `raster_characteristics` | 1 | 407 | 5 | 1 |
| `roads_flowpath` | 1 | 111 | 1 | 1 |
| `sbs_map` | 1 | 941 | 6 | 1 |
| `swat_interchange` | 6 | 3950 | 3 | 1 |
| `swat_utils` | 8 | 2668 | 1 | 1 |
| `watershed_abstraction` | 1 | 381 | 1 | 1 |
| `wepp_interchange` | 23 | 9505 | 16 | 1 |
| `wepp_viz` | 1 | 262 | 2 | 1 |

### Release Package

`confirmed`: `/workdir/wepppyo3/release/linux/py312/wepppyo3/` contains these shared libraries:

- `climate/cli_revision_rust.so`
- `raster_characteristics/raster_characteristics_rust.so`
- `roads_flowpath/roads_flowpath_rust.so`
- `sbs_map/sbs_map_rust.so`
- `swat_interchange/swat_interchange_rust.so`
- `swat_utils/swat_utils_rust.so`
- `watershed_abstraction/watershed_abstraction_rust.so`
- `wepp_interchange/wepp_interchange_rust.so`
- `wepp_viz/wepp_viz_rust.so`

`confirmed`: The release package root `__init__.py` currently reports `__version__ = "2026.01.30"`, while Rust crates generally report `0.1.0`; this is enough for human context but not full binary provenance.

### WEPPpy Adoption Map

`confirmed`: Approximate WEPPpy Python callsite counts from local scan:

| Module | Callsite files | Main production domains observed |
| --- | ---: | --- |
| `wepppyo3.climate` | 14 | climate build/scaling, CLIGEN, Daymet/Gridmet interpolation, RHEM, Geneva collaborators |
| `wepppyo3.raster_characteristics` | 12 | landuse, soils, disturbed, RAP, Omni, ash transport, treatments |
| `wepppyo3.wepp_interchange` | 6 | WEPP interchange, slope segmentation, Roads pass combination, catalog scan |
| `wepppyo3.swat_utils` | 2 | SWAT recall generation |
| `wepppyo3.swat_interchange` | 1 | SWAT output interchange |
| `wepppyo3.roads_flowpath` | 2 | Roads downslope tracing |
| `wepppyo3.watershed_abstraction` | 2 | MOFE map assignment |
| `wepppyo3.sbs_map` | 2 | BAER/SBS map processing and tests |
| `wepppyo3.wepp_viz` | 2 | WEPP soil-loss visualization grids |

`inference`: Some modules are mandatory production dependencies in their domains, while others remain optional acceleration boundaries with Python fallback. Repositioning should make that difference explicit.

## Module Posture Draft

| Module | Draft posture | Boundary note |
| --- | --- | --- |
| `climate` | Production climate kernel | Owns CLIGEN parsing/scaling, interpolation, storm/hyetograph helpers, static-R routines; Python remains orchestration/UI. |
| `raster_characteristics` | Production raster aggregation substrate | Owns key/mode/median/pair-count raster scans used by landuse/soils/disturbed/RAP/Omni. |
| `wepp_interchange` | Production WEPP file interchange and transform layer | Owns WEPP output parsing, Parquet conversion, pass combining, and slope segmentation kernels. |
| `swat_interchange` | SWAT output interchange substrate | Owns SWAT+ output-to-Parquet conversion under documented interchange contracts. |
| `swat_utils` | SWAT bridge utility substrate | Owns WEPP pass to SWAT recall conversion; Python controls run orchestration. |
| `roads_flowpath` | Roads native trace helper | Wraps Peridot trace logic for Python-callable Roads workflows. |
| `watershed_abstraction` | Helper kernel namespace, not Peridot replacement | Owns Python-callable helpers such as MOFE map assignment; Peridot owns watershed graph abstraction. |
| `sbs_map` | SBS/BAER raster helper, mixed support status | Some WEPPpy docs still describe Python fallback as authoritative; maturity should be recorded explicitly. |
| `wepp_viz` | Production visualization raster kernel | Owns soil-loss grid construction helpers used from WEPPpy. |
| `geneva_core` | Internal computational core | Rust-only support crate; not a release PyO3 module today. |
| `raster` | Shared internal GDAL/PROJ foundation | Rust support crate used by raster-related modules. |

## Boundary Decisions for Repositioning

`confirmed`: Peridot is a separate Rust repo and should remain positioned as the explicit graph watershed abstraction engine.

`confirmed`: `weppcloud-wbt` is a separate Rust hydrology/delineation toolchain and remains a performance baseline for WBT-derived operations.

`inference`: `wepppyo3` should own Python-callable native kernels and file interchanges that are embedded in WEPPpy workflows, not standalone watershed graph abstraction or full command-line delineation engines.

`inference`: Python should remain responsible for NoDb state, RQ orchestration, run-directory lifecycle, route/UI contracts, and user workflows.

## Communication Kit

### Figure Specification

Create a two-panel architecture figure:

- Left panel: WEPPpy Python orchestration layer with routes, NoDb controllers, RQ workers, run directories, and reports.
- Center band: `wepppyo3` native substrate as Python-callable Rust modules grouped into climate, raster, WEPP/SWAT interchange, roads/MOFE, SBS, and visualization.
- Right panel: external/native peers: Peridot for watershed graph abstraction, `weppcloud-wbt` for WBT/delineation, WEPP/SWAT Fortran executables, GDAL/PROJ, and Parquet outputs.
- Arrows should show Python orchestration calling stable native kernels, not Rust replacing the application.

### Metrics Definitions

- **Adoption surface**: Count of production WEPPpy modules and tests importing each `wepppyo3` module. Use this to classify maturity; do not confuse import count with correctness.
- **Runtime leverage**: Bounded performance gain on a named workload with command, fixture, repetitions, and environment. Use `confirmed` only for measured artifacts.
- **Contract centrality**: Number and importance of downstream outputs or workflows that depend on a module's schema, parser, raster semantics, or failure behavior.

## Repositioning Recommendations

1. Rewrite the README opening around native substrate, not extension modules.
2. Add `docs/module-registry.md` with module maturity, release artifact, callsites, tests, and evidence links.
3. Add `docs/architecture-and-boundaries.md` to define what belongs in `wepppyo3` versus Peridot, `weppcloud-wbt`, and Python.
4. Add `docs/release-provenance.md` to document canonical release package layout and provenance gaps.
5. Update WEPPpy dependency-standard wording to point to the canonical `wepppyo3` docs once they exist.
6. Keep historical benchmark claims bounded to exact workloads and artifacts.

## Residual Gaps

- `confirmed`: Release artifact provenance is currently weaker than the deployment importance of the package.
- `confirmed`: Some WEPPpy docs call `wepppyo3` optional acceleration while other callsites require it.
- `inference`: Module maturity labels will need maintainer judgment after initial evidence-based registry drafting.
- `hypothesis`: A release manifest with source commit, build timestamp, Python ABI, GDAL/PROJ versions, and shared-object hashes would reduce operator risk.
