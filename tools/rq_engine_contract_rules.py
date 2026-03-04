from __future__ import annotations

SUCCESS_STATUS_OVERRIDES: dict[tuple[str, str], int] = {
    ("POST", "/api/runs/{runid}/{config}/run-omni"): 202,
    ("POST", "/api/runs/{runid}/{config}/run-omni-contrasts"): 202,
    ("POST", "/create/"): 303,
}

PATHS_REQUIRING_400 = {
    "/api/culverts-wepp-batch/",
    "/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}",
    "/api/runs/{runid}/{config}/acquire-rap-ts",
    "/api/runs/{runid}/{config}/archive",
    "/api/runs/{runid}/{config}/bootstrap/checkout",
    "/api/runs/{runid}/{config}/bootstrap/commits",
    "/api/runs/{runid}/{config}/bootstrap/current-ref",
    "/api/runs/{runid}/{config}/bootstrap/enable",
    "/api/runs/{runid}/{config}/bootstrap/mint-token",
    "/api/runs/{runid}/{config}/build-climate",
    "/api/runs/{runid}/{config}/build-landuse",
    "/api/runs/{runid}/{config}/build-soils",
    "/api/runs/{runid}/{config}/build-subcatchments-and-abstract-watershed",
    "/api/runs/{runid}/{config}/build-treatments",
    "/api/runs/{runid}/{config}/delete-archive",
    "/api/runs/{runid}/{config}/fetch-dem-and-build-channels",
    "/api/runs/{runid}/{config}/post-dss-export-rq",
    "/api/runs/{runid}/{config}/prep-wepp-watershed",
    "/api/runs/{runid}/{config}/restore-archive",
    "/api/runs/{runid}/{config}/run-ash",
    "/api/runs/{runid}/{config}/run-debris-flow",
    "/api/runs/{runid}/{config}/run-omni",
    "/api/runs/{runid}/{config}/run-omni-contrasts",
    "/api/runs/{runid}/{config}/run-omni-contrasts-dry-run",
    "/api/runs/{runid}/{config}/run-wepp",
    "/api/runs/{runid}/{config}/run-wepp-npprep",
    "/api/runs/{runid}/{config}/run-wepp-watershed",
    "/api/runs/{runid}/{config}/run-wepp-watershed-no-prep",
    "/api/runs/{runid}/{config}/run-swat-noprep",
    "/api/runs/{runid}/{config}/set-outlet",
    "/api/runs/{runid}/{config}/swat/print-prt",
    "/api/runs/{runid}/{config}/swat/print-prt/meta",
    "/api/runs/{runid}/{config}/tasks/upload-cli/",
    "/api/runs/{runid}/{config}/tasks/upload-cover-transform",
    "/api/runs/{runid}/{config}/tasks/upload-dem/",
    "/api/runs/{runid}/{config}/tasks/upload-sbs/",
    "/create/",
}

PATHS_REQUIRING_404 = {
    "/api/canceljob/{job_id}",
    "/api/culverts-wepp-batch/{batch_uuid}/finalize",
    "/api/culverts-wepp-batch/{batch_uuid}/retry/{point_id}",
    "/api/jobinfo/{job_id}",
    "/api/jobstatus/{job_id}",
    "/api/runs/{runid}/{config}/archive",
    "/api/runs/{runid}/{config}/delete-archive",
    "/api/runs/{runid}/{config}/export/ermit",
    "/api/runs/{runid}/{config}/export/geodatabase",
    "/api/runs/{runid}/{config}/export/geopackage",
    "/api/runs/{runid}/{config}/export/prep_details",
    "/api/runs/{runid}/{config}/export/prep_details/",
    "/api/runs/{runid}/{config}/fork",
    "/api/runs/{runid}/{config}/restore-archive",
}

PATHS_REQUIRING_409 = {
    "/api/runs/{runid}/{config}/bootstrap/checkout",
    "/api/runs/{runid}/{config}/bootstrap/enable",
}

PATHS_REQUIRING_429 = {
    "/api/jobinfo",
    "/api/jobinfo/{job_id}",
    "/api/jobstatus/{job_id}",
}

PATHS_REQUIRING_EXTRA_202 = {
    "/api/runs/{runid}/{config}/bootstrap/enable",
}


def required_response_codes(method: str, path: str) -> set[int]:
    success_code = SUCCESS_STATUS_OVERRIDES.get((method, path), 200)
    required = {success_code, 401, 403, 500}

    if path in PATHS_REQUIRING_400:
        required.add(400)
    if path in PATHS_REQUIRING_404:
        required.add(404)
    if path in PATHS_REQUIRING_409:
        required.add(409)
    if path in PATHS_REQUIRING_429:
        required.add(429)
    if path in PATHS_REQUIRING_EXTRA_202:
        required.add(202)

    return required


__all__ = ["required_response_codes"]
