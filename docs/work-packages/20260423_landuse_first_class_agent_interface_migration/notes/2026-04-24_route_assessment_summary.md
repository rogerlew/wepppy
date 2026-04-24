# 2026-04-24 Route Assessment Summary

## Question

Should `landuse_bp` routes be moved to rq-engine to provide a first-class agent interface for state reads/writes?

## Recommendation

- Do **not** move `landuse_bp` wholesale in one cut.
- Keep UI/render routes in WEPPcloud.
- Migrate machine/state APIs to rq-engine in phases with explicit security and compatibility gates.

## Route Boundary

### Keep in WEPPcloud
- `/runs/{runid}/{config}/report/landuse`
- `/runs/{runid}/{config}/landuse-user-defined`
- `/runs/{runid}/{config}/landuse-map`

### Migrate to rq-engine (phased)
- Lower-risk mutators first:
  - `tasks/set_landuse_mode/`
  - `tasks/set_landuse_db/`
  - `tasks/modify_landuse_coverage/`
- Add first-class read:
  - `GET /api/runs/{runid}/{config}/controllers/landuse/state` (contract-aligned)
- High-risk map/catalog/file endpoints only after hardening parity:
  - `api/landuse/user_defined/catalog`
  - `api/landuse/map_snapshot`
  - `tasks/landuse/user_defined/upload|delete|update-description`
  - `tasks/landuse/map/save|clear-override`
  - `tasks/modify_landuse/`

## Critical Findings Driving Phasing

1. `High` - PUP/active-root scope drift risk when moving from WEPPcloud context-aware resolution to rq-engine runid-only resolution.
2. `High` - Existing map/catalog route hardening (path/archive/concurrency/atomicity) is strong and must not regress.
3. `Medium` - Current standalone page transport uses CSRF-header `fetch`; migrated rq-engine mutators require session-token bridge transport.
4. `Medium` - JWT token-class policy (`service`/`mcp`) can widen mutation access unless explicitly constrained.
5. `Medium` - Endpoint discoverability drift exists (`modify-landuse-mapping` route not represented in endpoint-doc builder).

## Required Gate Themes

- Route ownership gate (render vs state APIs).
- Auth/transport gate (session-token bridge for browser; bearer-only mutators in rq-engine).
- Discovery gate (endpoint catalogs include migrated operations).
- Hardening parity gate (path/archive/concurrency/atomicity).
- Security closure gate (no unresolved medium/high findings before package closeout).

