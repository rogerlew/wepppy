# Composite Runid Slugs

> Specification for grouped run identifiers used in WEPPcloud URLs, RQ endpoints, and WebSocket channels.

## Overview

WEPPcloud uses `runid` as the primary identifier in routes like `/runs/<runid>/<config>/...`. A **composite runid slug** is a three-part runid that encodes a grouping or child-run context while still fitting in the `runid` slot. Composite slugs are parsed by `wepppy.weppcloud.utils.helpers.get_wd` and resolve to a working directory (WD).

Composite slugs are used for:
- batch and culvert grouped runs,
- profile playback runs,
- Omni child projects (scenarios and contrasts).

## Syntax

```
composite-runid = segment ";;" segment ";;" segment
segment         = 1*(ALNUM / "_" / "-" / ".")
```

Constraints:
- `;;` is reserved and MUST NOT appear inside a segment.
- Segments MUST NOT contain `/` or `\`.
- Keep segments ASCII; avoid whitespace.

## Resolution Rules

Composite runids resolve to a WD using `get_wd(runid)`:

| Type | Runid format | Resolved working directory |
| --- | --- | --- |
| Batch run | `batch;;<batch_name>;;<runid>` | `/wc1/batch/<batch_name>/runs/<runid>` |
| Batch base | `batch;;<batch_name>;;_base` | `/wc1/batch/<batch_name>/_base` |
| Culvert | `culvert;;<batch_uuid>;;<runid>` | `${CULVERTS_ROOT}/<batch_uuid>/runs/<runid>` (default `CULVERTS_ROOT=/wc1/culverts`) |
| Profile tmp | `profile;;tmp;;<runid>` | `${PROFILE_PLAYBACK_RUN_ROOT}/<runid>` |
| Profile fork | `profile;;fork;;<runid>` | `${PROFILE_PLAYBACK_FORK_ROOT}/<runid>` |
| Profile archive | `profile;;archive;;<runid>` | `${PROFILE_PLAYBACK_ARCHIVE_ROOT}/<runid>` |
| Omni scenario | `<parent_runid>;;omni;;<scenario_name>` | `<parent_wd>/_pups/omni/scenarios/<scenario_name>` |
| Omni contrast | `<parent_runid>;;omni-contrast;;<contrast_id>` | `<parent_wd>/_pups/omni/contrasts/<contrast_id>` |

Notes:
- `<parent_wd>` resolves via the canonical run root `/wc1/runs/<prefix>/<parent_runid>` with a legacy fallback to `/geodata/weppcloud_runs/<parent_runid>` if present.
- Omni child runs link shared inputs (`climate/`, `dem/`, `watershed/`) from the parent if missing.
- The parent segment can itself be composite (for example `batch;;spring-2025;;run-001;;omni-contrast;;3`); resolvers should strip the trailing `;;omni;;...`/`;;omni-contrast;;...` suffix and resolve the parent runid first.

## Behavior and Semantics

- **Pup query ignored**: for composite runids, `load_run_context` ignores the `?pup=` query parameter.
- **NoDb runid**: Omni child NoDb controllers keep `NoDbBase.runid` equal to the parent runid (because `_parent_wd` is set). Redis keys, status channels, and preflight updates therefore use the parent runid.
- **Authorization**: ownership and access checks are based on the parent runid. Composite runids are not stored as separate `Run` records.

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
/weppcloud/runs/culvert;;6d2a2c2b;;pt-001/0/
/weppcloud/runs/profile;;tmp;;playback-01/0/
```

The same composite runid string is valid for RQ endpoints:

```
/rq-engine/api/runs/decimal-pleasing;;omni;;undisturbed/0/run-wepp-watershed
```

## Implementation Touchpoints

- Resolver: `wepppy/weppcloud/utils/helpers.py:get_wd`
- Run context: `wepppy/weppcloud/routes/_run_context.py:load_run_context`
- NoDb runid behavior: `wepppy/nodb/base.py:NoDbBase.runid`
- weppcloudR resolver: `weppcloudR/plumber.R:resolve_run_root`, `weppcloudR/templates/scripts/users/*/weppcloudr_report_functions.R:resolve_run_root`

## Resolution by Service

This is the current map of how services resolve a runid into a working directory. Composite slugs work only where `get_wd` is used (directly or indirectly).

| Service | Entry point | Resolver | Notes |
| --- | --- | --- | --- |
| Web app (Flask routes) | `wepppy/weppcloud/routes/*` | `load_run_context()` → `get_wd()` | `load_run_context` ignores `?pup=` for composite runids; `ctx.run_root` vs `ctx.active_root` separates run root/pup. |
| Browse microservice | `wepppy/microservices/browse/browse.py` | `get_wd()` | Uses `runid`/`diff` directly; no `RunContext` wrapper. |
| RQ engine API | `wepppy/microservices/rq_engine/*` | `get_wd()` | Endpoints resolve the composite runid before dispatching jobs. |
| RQ worker (single runs) | `wepppy/rq/*.py`, `wepppy/rq/rq_worker.py` | `get_wd()` | Worker tasks resolve the same composite slug used by the API. |
| RQ worker (batch) | `wepppy/nodb/batch_runner.py` | `get_wd()` | Batch runner constructs `batch;;<batch_name>;;<runid>` and relies on `get_wd` to target `/wc1/batch/...`. |
| Query engine | `wepppy/query_engine/app/helpers.py` | `get_wd()` | Accepts `runid` or `runid/config`; scenario strings resolved under `_pups/omni`. |
| Elevation query (Starlette) | `wepppy/microservices/elevationquery.py` | `get_wd()` | Resolves `runid` and optional `?pup=` directly; **does not** ignore `pup` when `runid` is composite (needs patch). |
| weppcloudR (R renderer) | `weppcloudR/plumber.R`, `weppcloudR/templates/scripts/users/*/weppcloudr_report_functions.R` | `resolve_run_root()` | Used by DEVAL and report helper scripts; now supports omni scenarios/contrasts (including composite parents) plus batch/culvert/profile slugs. |

## Preflight and Telemetry Routing

Preflight updates and status channels are keyed off `NoDbBase.runid` (parent runid for omni child runs). This is why preflight and WebSocket status streams target the parent run even when the URL uses a composite slug.

## Legacy `?pup=` Query Parameter

`?pup=` predates composite runids and was used to point routes at a child project under `_pups`. It is still supported in some places, but it is fragile because it is not part of the `runid` itself and is easy to drop when passing URLs between services.

Example:

```
/weppcloud/runs/<runid>/<config>/?pup=omni/scenarios/<scenario_name>
```

Current usages (non-exhaustive, but the primary ones to keep in mind):
- `wepppy/weppcloud/routes/_run_context.py` honors `?pup=` for non-composite runids.
- `wepppy/weppcloud/templates/header/_run_header_fixed.htm` and `wepppy/weppcloud/templates/reports/_base_report.htm` patch `fetch`/XHR to append `?pup=` when `current_ron.pup_relpath` is set.
- `wepppy/weppcloud/static/js/gl-dashboard/scenario/manager.js` builds scenario URLs using `?pup=` for base-run comparisons.
- `wepppy/microservices/elevationquery.py` and `wepppy/microservices/rq_engine/export_routes.py` resolve `?pup=` directly (no composite-slug guard).

Guidance:
- Prefer composite runid slugs for omni scenarios/contrasts and any new child-run access.
- Avoid introducing new `?pup=` dependencies. If a service must support it, ensure it also accepts composite runids.
- Treat `?pup=` as legacy: it is not guaranteed to propagate across microservices or RQ pipelines.
