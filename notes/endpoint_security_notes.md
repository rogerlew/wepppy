# Endpoint Security Notes

## High-Risk Endpoints (no @login_required / @roles_required and no authorize)
- `wepppy/weppcloud/routes/rq/api/api.py:237,265,287,384,476,540,570,599,660,797,867,936,1026,1046,1065,1084,1164` – run/RQ management POST routes (fetch_dem…, set_outlet, build_landuse/soils/climate, run_wepp/omni/ash/debris/rhem, fork, archive, etc.) enqueue jobs or mutate run files for any caller who knows a run id, including anonymous runs.
- `wepppy/weppcloud/routes/rq/api/jobinfo.py:51` – `/rq/api/canceljob/<job_id>` lets unauthenticated users cancel arbitrary RQ jobs.

## Medium-Risk Endpoints
- `wepppy/weppcloud/routes/download.py` and `wepppy/weppcloud/routes/browse/__init__.py` – browse/download expose full run directories with no auth check.
- `wepppy/weppcloud/routes/diff.py:20,25`, `gdalinfo.py:19,24`, `jsoncrack.py:82,87`, `pivottable.py:166,171`, `wepprepr.py:19,24` – stream run outputs (diffs, JSON/CSV, management files) without ensuring ownership.
- `wepppy/weppcloud/routes/weppcloudr.py:196,209` – run exports and `/WEPPcloudR/proxy/<routine>` execute heavy processing and leak metadata with no auth.
- `wepppy/weppcloud/routes/rq/job_dashboard/routes.py:17` and `rq/api/jobinfo.py:41,61` – expose job dashboards/status for any job id.
- `wepppy/weppcloud/routes/rq/api/api.py:195,222` – allow public landuse/soil extraction job submission and archive download by UUID.

## Follow-Up Actions
1. Decide which endpoints should call `authorize`, require `@login_required`, or enforce stronger role checks (start with RQ run-management routes and job cancellation API).
2. Add tests that assert unauthenticated/unauthorized callers are blocked once protections are in place.
