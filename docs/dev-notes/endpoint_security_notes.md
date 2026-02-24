# Endpoint Security Notes

> **See also:** [AGENTS.md](../../AGENTS.md), `docs/schemas/weppcloud-csrf-contract.md`, and `docs/dev-notes/auth-token.spec.md`.

## High-Risk Endpoints (run/RQ management)
- rq-engine run-scoped POST routes under `wepppy/microservices/rq_engine/` (fetch-dem-and-build-channels, set-outlet, build-landuse/soils/climate, run-wepp/omni/ash/debris/rhem, fork, archive, etc.) mutate run state and enqueue jobs. Ensure every route enforces JWT and run access checks before accepting work.
- `wepppy/microservices/rq_engine/job_routes.py` – `/rq-engine/api/canceljob/<job_id>` is now JWT-protected; keep it that way and avoid anonymous access.

## Medium-Risk Endpoints
- `wepppy/microservices/browse/*` (browse/download/files handlers) enforce token-class and run-scope gating when auth is present. `/files/` routes require JWT auth (`user` or `service`) and reject anonymous/session tokens. Run browse/download routes still allow anonymous access for public runs on non-root-only paths; private runs and root-only paths require valid run-scoped tokens (`session`, `user`, or `service`).
- `POST /weppcloud/api/auth/rq-engine-token` (Flask `weppcloud_site`) mints
  browser fallback JWTs for transparent rq-engine renewal. It must remain
  authenticated-session only (`401` for anonymous), same-origin, and CSRF-protected.
- `wepppy/weppcloud/routes/diff.py:20,25`, `gdalinfo.py:19,24`, `jsoncrack.py:82,87`, `pivottable.py:166,171`, `wepprepr.py:19,24` – stream run outputs (diffs, JSON/CSV, management files) without ensuring ownership.
- `wepppy/weppcloud/routes/weppcloudr.py:196,209` – run exports and `/WEPPcloudR/proxy/<routine>` execute heavy processing and leak metadata with no auth.
- `wepppy/weppcloud/routes/rq/job_dashboard/routes.py:18` now uses `requires_cap`, but rq-engine `jobstatus`/`jobinfo` endpoints remain intentionally public for read-only polling.
- `wepppy/microservices/rq_engine/export_routes.py` – `/rq-engine/api/runs/<runid>/<config>/export/*` performs long-running export work; keep JWT + run access checks enforced.
- `wepppy/microservices/rq_engine/landuse_soils_routes.py` allows public landuse/soil extraction job submission and archive download by UUID; decide whether that stays public or needs JWT scopes.

## Follow-Up Actions
1. Decide which endpoints should call `authorize`, require `@login_required`, or enforce stronger role checks (start with RQ run-management routes and job cancellation API).
2. Add tests that assert unauthenticated/unauthorized callers are blocked once protections are in place.

## Dependency Alerts (Acknowledged)
- Dependabot alert #1044 (nbconvert uncontrolled search path on Windows, `docker/requirements-uv.txt`): not applicable to Linux deployments and no patched version is available; ignore until upstream ships a fix.
