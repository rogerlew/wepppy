# Endpoint Security Notes

> **See also:** [AGENTS.md](../../AGENTS.md) for Security Considerations and Input Validation sections.

## High-Risk Endpoints (run/RQ management)
- rq-engine run-scoped POST routes under `wepppy/microservices/rq_engine/` (fetch-dem-and-build-channels, set-outlet, build-landuse/soils/climate, run-wepp/omni/ash/debris/rhem, fork, archive, etc.) mutate run state and enqueue jobs. Ensure every route enforces JWT and run access checks before accepting work.
- `wepppy/microservices/rq_engine/job_routes.py` – `/rq-engine/api/canceljob/<job_id>` is now JWT-protected; keep it that way and avoid anonymous access.

## Medium-Risk Endpoints
- `wepppy/weppcloud/routes/download.py` and `wepppy/weppcloud/routes/browse/__init__.py` – browse/download expose full run directories with no auth check.
- `wepppy/weppcloud/routes/diff.py:20,25`, `gdalinfo.py:19,24`, `jsoncrack.py:82,87`, `pivottable.py:166,171`, `wepprepr.py:19,24` – stream run outputs (diffs, JSON/CSV, management files) without ensuring ownership.
- `wepppy/weppcloud/routes/weppcloudr.py:196,209` – run exports and `/WEPPcloudR/proxy/<routine>` execute heavy processing and leak metadata with no auth.
- `wepppy/weppcloud/routes/rq/job_dashboard/routes.py:18` now uses `requires_cap`, but rq-engine `jobstatus`/`jobinfo` endpoints remain intentionally public for read-only polling.
- `wepppy/microservices/rq_engine/landuse_soils_routes.py` allows public landuse/soil extraction job submission and archive download by UUID; decide whether that stays public or needs JWT scopes.

## Follow-Up Actions
1. Decide which endpoints should call `authorize`, require `@login_required`, or enforce stronger role checks (start with RQ run-management routes and job cancellation API).
2. Add tests that assert unauthenticated/unauthorized callers are blocked once protections are in place.
