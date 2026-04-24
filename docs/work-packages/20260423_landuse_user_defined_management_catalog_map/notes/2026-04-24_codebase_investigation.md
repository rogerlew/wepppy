# Codebase Investigation - 2026-04-24

## Goal
Validate whether a run-scoped user-defined management catalog + mapping editor can be implemented cleanly in the current stack without architectural blockers.

## Confirmed Touchpoints

## PowerUser Entry Points
- `wepppy/weppcloud/templates/controls/poweruser_panel.htm`
  - Existing Actions list already supports links/buttons and is the correct insertion point for:
    - `Landuse User-Defined`
    - `Landuse Map`

## Existing Landuse UI/Route Stack
- `wepppy/weppcloud/templates/controls/landuse_pure.htm`
  - Uses static `landuse_management_mapping_options` for mapping selection.
- `wepppy/weppcloud/templates/reports/landuse.htm`
  - Already supports staged mapping submit UX and sorted options.
- `wepppy/weppcloud/controllers_js/landuse.js`
  - Handles staged mapping interactions and API submission.
- `wepppy/microservices/rq_engine/landuse_routes.py`
  - Existing mapping mutation route and user-defined raster upload route patterns.

## Reusable Editable-Table Pattern
- `wepppy/weppcloud/templates/controls/edit_csv.htm`
- `wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`
- `wepppy/weppcloud/routes/nodb_api/geneva_bp.py`
  - These provide snapshot metadata + optimistic concurrency patterns suitable for mapping editor save semantics.

## Upload/Archive Security Primitives
- `wepppy/microservices/upload_boundary.py`
  - secure filename, extension checks, streaming size caps.
- `wepppy/microservices/shape_converter/archive_validation.py`
  - ZIP signature/member/path/compression/encryption/quota protections and controlled extraction.
- `wepppy/microservices/rq_engine/culvert_routes.py`
  - Example of production-grade ZIP ingestion flow using shared validator.

## NoDb + Management Mapping Core
- `wepppy/nodb/core/landuse.py`
  - `mapping` property, `get_mapping_dict()`, `landuseoptions`, `build_managements()`, multi-OFE synthesis.
- `wepppy/wepp/management/managements.py`
  - `load_map()`, `ManagementSummary`, `Management`.
  - Supports `SoilFile` and `ManagementDir` metadata per map entry.

## Prep-Time Multi-Year Behavior
- `wepppy/nodb/core/wepp_prep_service.py`
  - Single hillslope prep calls `build_multiple_year_man(years)`.
- `wepppy/nodb/core/wepp.py`
  - Multi-OFE prep calls `build_multiple_year_man(sim_years)` on synthesized managements.

## Key Gap Identified
- `load_map(_map)` currently does not support explicit run-local map JSON paths.
- To satisfy “mapping file should be saved in project landuse directory and preferred by NoDb”, mapping resolution needs an explicit run-local map path contract.

## Feasibility Conclusion
No architectural blocker found. The feature is implementable by combining existing upload security primitives, editable-table UX patterns, and a focused extension of NoDb mapping source resolution.
