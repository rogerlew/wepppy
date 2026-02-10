# Composite Runid Slugs

> Specification for grouped run identifiers used in WEPPcloud URLs, RQ endpoints, and WebSocket channels.

## Overview

WEPPcloud uses `runid` as the primary identifier in routes like `/runs/<runid>/<config>/...`. A **composite runid slug** is a `;;`-delimited runid slug (3+ segments; common forms are 3 or 5 segments) that encodes a grouping or child-run context while still fitting in the `runid` slot. Composite slugs are parsed by `wepppy.weppcloud.utils.helpers.get_wd` and resolve to a working directory (WD).

Composite slugs are used for:
- batch and culvert grouped runs,
- profile playback runs,
- Omni child projects (scenarios and contrasts).

## Syntax

Composite runids are `;;`-delimited strings with 3+ segments:

```
composite-runid = segment ";;" segment ";;" segment *( ";;" segment )
segment         = <non-empty string>
```

Runtime validation in `wepppy/weppcloud/utils/helpers.py:get_wd` enforces:
- Segments MUST be non-empty and MUST NOT be `.` or `..`.
- Segments MUST NOT contain `/`, `\`, or NUL (`\x00`).

Recommendations:
- Prefer portable segment characters like `[A-Za-z0-9_.-]` when possible.
- URL-encode each segment when embedding a composite runid in a URL path (spaces, `#`, `?`, etc.).

## Resolution Rules

Composite runids resolve to a WD using `get_wd(runid)`:

| Type | Runid format | Resolved working directory |
| --- | --- | --- |
| Batch run | `batch;;<batch_name>;;<runid>` | `${BATCH_RUNNER_ROOT}/<batch_name>/runs/<runid>` (default `BATCH_RUNNER_ROOT=/wc1/batch`) |
| Batch base | `batch;;<batch_name>;;_base` | `${BATCH_RUNNER_ROOT}/<batch_name>/_base` (default `BATCH_RUNNER_ROOT=/wc1/batch`) |
| Culvert | `culvert;;<batch_uuid>;;<runid>` | `${CULVERTS_ROOT}/<batch_uuid>/runs/<runid>` (default `CULVERTS_ROOT=/wc1/culverts`) |
| Profile tmp | `profile;;tmp;;<runid>` | `${PROFILE_PLAYBACK_RUN_ROOT}/<runid>` |
| Profile fork | `profile;;fork;;<runid>` | `${PROFILE_PLAYBACK_FORK_ROOT}/<runid>` |
| Profile archive | `profile;;archive;;<runid>` | `${PROFILE_PLAYBACK_ARCHIVE_ROOT}/<runid>` |
| Omni scenario | `<parent_runid>;;omni;;<scenario_name>` | `<parent_wd>/_pups/omni/scenarios/<scenario_name>` |
| Omni contrast | `<parent_runid>;;omni-contrast;;<contrast_id>` | `<parent_wd>/_pups/omni/contrasts/<contrast_id>` |
| Batch omni scenario | `batch;;<batch_name>;;<runid>;;omni;;<scenario_name>` | `${BATCH_RUNNER_ROOT}/<batch_name>/runs/<runid>/_pups/omni/scenarios/<scenario_name>` (default `BATCH_RUNNER_ROOT=/wc1/batch`) |
| Batch omni contrast | `batch;;<batch_name>;;<runid>;;omni-contrast;;<contrast_id>` | `${BATCH_RUNNER_ROOT}/<batch_name>/runs/<runid>/_pups/omni/contrasts/<contrast_id>` (default `BATCH_RUNNER_ROOT=/wc1/batch`) |

Notes:
- For simple parents, `<parent_wd>` resolves via the canonical run root `/wc1/runs/<prefix>/<parent_runid>` with a legacy fallback to `/geodata/weppcloud_runs/<parent_runid>` if present.
- For batch parents, `<parent_wd>` resolves under `${BATCH_RUNNER_ROOT}/<batch_name>/runs/<runid>`.
- Omni child runs link shared inputs (`climate/`, `dem/`, `watershed/`) from the parent if missing.
- Omni suffix slugs may be applied to batch composite parents (for example `batch;;spring-2025;;run-001;;omni-contrast;;3`). Nested omni suffixes are not supported for other composite parents (for example `culvert` or `profile`).

## Behavior and Semantics

- **Pup query ignored**: for composite runids, `load_run_context` ignores the `?pup=` query parameter.
- **Playback clone override**: when `PROFILE_PLAYBACK_USE_CLONE=true`, `get_wd` will resolve a non-composite runid to `${PROFILE_PLAYBACK_RUN_ROOT}/<runid>` *if that directory exists*, before falling back to `/wc1/runs/<prefix>/<runid>`.
- **WD cache (Redis DB 11)**: `get_wd` caches `runid -> WD` lookups for 72 hours (only when the resolved path exists). Composite slugs cache under their full slug string; omni child slugs still authorize and emit telemetry using the stripped parent runid.
- **NoDb runid**: Omni child NoDb controllers keep `NoDbBase.runid` equal to the parent runid (because `_parent_wd` is set). Redis keys, status channels, and preflight updates therefore use the parent runid.
- **Authorization**: Omni scenario/contrast slugs authorize against the parent runid (strip the trailing `;;omni;;...` / `;;omni-contrast;;...` suffix) and inherit the parent run's access controls. Batch slugs (`batch;;...`) are Admin/Root-only because batch runs are not tracked in the `Run` ownership table.

## Omni Monkey Patching

Omni child runs use legacy layouts that may omit shared inputs at the child root. To keep existing controllers and UI assumptions working, WEPPcloud applies targeted fixups when resolving omni composite slugs.

Patch behaviors:
- **Shared input symlinks**: `get_wd` calls `_ensure_omni_shared_inputs()` for omni scenarios/contrasts. It creates `climate/`, `dem/`, and `watershed/` symlinks from the parent run when missing. The operation is best-effort and logs a warning if linking fails.
- **Child-run detection**: `is_omni_child_run(runid, wd, pup_relpath)` centralizes detection using the composite slug, `?pup=` relpath, or `_pups/omni` in the resolved path. UI/route gating (runs0_pure, gl-dashboard, reports) should consult this helper instead of re-parsing `runid`.
- **Parent-run semantics**: Omni child NoDb instances continue to report the parent `runid` for status, preflight, and Redis channel routing. This is intentional and keeps the telemetry pipeline consistent.

## Examples

```
/weppcloud/runs/decimal-pleasing/0/
/weppcloud/runs/decimal-pleasing;;omni;;undisturbed/0/
/weppcloud/runs/decimal-pleasing;;omni-contrast;;12/0/
/weppcloud/runs/batch;;spring-2025;;_base/0/
/weppcloud/runs/batch;;spring-2025;;run-001;;omni;;treated/0/
/weppcloud/runs/batch;;spring-2025;;run-001;;omni-contrast;;3/0/
/weppcloud/runs/culvert;;6d2a2c2b;;pt-001/0/
/weppcloud/runs/profile;;tmp;;playback-01/0/
```

The same composite runid string is valid for RQ endpoints:

```
/rq-engine/api/runs/decimal-pleasing;;omni;;undisturbed/0/run-wepp-watershed
```

## Implementation Touchpoints

- Resolver: `wepppy/weppcloud/utils/helpers.py:get_wd`
- Omni suffix handling: `wepppy/weppcloud/utils/helpers.py:_strip_omni_suffix_runid`, `wepppy/weppcloud/utils/helpers.py:is_omni_child_run`
- Auth: `wepppy/weppcloud/utils/helpers.py:authorize`
- Run context: `wepppy/weppcloud/routes/_run_context.py:load_run_context`
- NoDb runid behavior: `wepppy/nodb/base.py:NoDbBase.runid`
- Composite runid generators (selected):
  - Batch: `wepppy/rq/batch_rq.py`, `wepppy/nodb/batch_runner.py`, `wepppy/weppcloud/routes/batch_runner/batch_runner_bp.py`
  - Culverts: `wepppy/microservices/rq_engine/culvert_routes.py`, `wepppy/rq/culvert_rq.py`, `wepppy/nodb/culverts_runner.py`
  - Omni (UI): `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js`, `wepppy/weppcloud/static/js/gl-dashboard/data/query-engine.js`, `wepppy/weppcloud/templates/reports/omni/*.htm`
  - Profile playback: `services/profile_playback/app.py`, `wepppy/profile_recorder/playback.py`
- weppcloudR resolver: `weppcloudR/plumber.R:resolve_run_root`, `weppcloudR/templates/scripts/users/*/weppcloudr_report_functions.R:resolve_run_root`

## Resolution by Service

This is the current map of how services resolve a runid into a working directory. Composite slugs work only where `get_wd` is used (directly or indirectly).

| Service | Entry point | Resolver | Notes |
| --- | --- | --- | --- |
| Web app (Flask routes) | `wepppy/weppcloud/routes/*` | `load_run_context()` → `get_wd()` | `load_run_context` ignores `?pup=` for composite runids; `ctx.run_root` vs `ctx.active_root` separates run root/pup. |
| Browse microservice | `wepppy/microservices/browse/browse.py` | `get_wd()` | Uses `runid`/`diff` directly; no `RunContext` wrapper. Does **not** honor `?pup=`; use composite runids for omni scenario/contrast browsing. |
| RQ engine API | `wepppy/microservices/rq_engine/*` | `get_wd()` | Endpoints resolve the composite runid before dispatching jobs. |
| RQ worker (single runs) | `wepppy/rq/*.py`, `wepppy/rq/rq_worker.py` | `get_wd()` | Worker tasks resolve the same composite slug used by the API. |
| RQ worker (batch) | `wepppy/nodb/batch_runner.py` | `get_wd()` | Batch runner constructs `batch;;<batch_name>;;<runid>` and relies on `get_wd` to target `${BATCH_RUNNER_ROOT}` (default `/wc1/batch`). |
| Query engine | `wepppy/query_engine/app/server.py`, `wepppy/query_engine/app/helpers.py` | `get_wd()` | Accepts `runid`, `runid/config`, or filesystem paths. Omni scenarios are primarily addressed via POST body `{"scenario": "<scenario_name>"}`; omni contrasts are typically addressed via composite runids (`...;;omni-contrast;;...`). |
| Elevation query (Starlette) | `wepppy/microservices/elevationquery.py` | `get_wd()` | Resolves the run root via `get_wd()`. Does **not** honor `?pup=`; use composite runids for child runs. |
| weppcloudR (R renderer) | `weppcloudR/plumber.R`, `weppcloudR/templates/scripts/users/*/weppcloudr_report_functions.R` | `resolve_run_root()` | Used by DEVAL and report helper scripts; now supports omni scenarios/contrasts (including composite parents) plus batch/culvert/profile slugs. |

## Preflight and Telemetry Routing

Preflight updates and status channels are keyed off `NoDbBase.runid` (parent runid for omni child runs). This is why preflight and WebSocket status streams target the parent run even when the URL uses a composite slug.

## Database and Cache Touchpoints

Composite runid slugs show up in (or influence keys for) these persistence surfaces:

- **Filesystem**: composite slugs resolve to working directories under `/wc1/runs/...`, `${BATCH_RUNNER_ROOT}/...`, `${CULVERTS_ROOT}/...`, or profile playback roots.
- **Redis DB 11 (WD cache)**: `wepppy/weppcloud/utils/helpers.py:get_wd` caches `runid -> WD` for 72 hours when the resolved WD exists.
- **Redis DB 0 (NoDb locks)**: `wepppy/nodb/base.py` lock state is keyed by `NoDbBase.runid` (group-prefixed for batch/culvert/profile; stripped parent runid for omni child runs).
- **Redis DB 13 (NoDb JSON cache)**: serialized NoDb state is cached by `NoDbBase.runid` for 72 hours; omni child controllers share the parent runid key.
- **Redis DB 2 (status pub/sub)**: status channels include `NoDbBase.runid` as a prefix (for example `<runid>:<controller>`), so omni child runs publish on the parent runid channel namespace.
- **Postgres (Run ownership)**: `wepppy/weppcloud/utils/helpers.py:authorize` normalizes omni composite runids to the parent runid via `_strip_omni_suffix_runid`; batch composite slugs are Admin/Root-only.

## Legacy `?pup=` Query Parameter

`?pup=` predates composite runids and was used to point routes at a child project under `_pups`. It is still supported in some places, but it is fragile because it is not part of the `runid` itself and is easy to drop when passing URLs between services.

Example:

```
/weppcloud/runs/<runid>/<config>/?pup=omni/scenarios/<scenario_name>
```

Current usages (non-exhaustive, but the primary ones to keep in mind):
- `wepppy/weppcloud/routes/_run_context.py` honors `?pup=` for non-composite runids.
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm` and `wepppy/weppcloud/templates/reports/_base_report.htm` patch `fetch`/XHR to append `?pup=` when `current_ron.pup_relpath` is set.
- `wepppy/microservices/rq_engine/export_routes.py:_resolve_export_wd` ignores `?pup=` when `runid` is composite (aligns with Flask `load_run_context`).

Guidance:
- Prefer composite runid slugs for omni scenarios/contrasts and any new child-run access.
- Avoid introducing new `?pup=` dependencies. If a service must support it, ensure it also accepts composite runids.
- Treat `?pup=` as legacy: it is not guaranteed to propagate across microservices or RQ pipelines.
