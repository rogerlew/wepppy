# Build a Dedicated Download Service for Critical Run Archives

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`. The plan is self-contained: a contributor should be able to start from this file, inspect the named repository files, and deliver a working archive download service without relying on chat history.

## Purpose / Big Picture

WEPPcloud users need completed run archive downloads to be reliable even when the browse UI is busy, crawlers are listing directories, D-Tale is loading tables, or parquet preview/export work is happening. Today the same `browse` service owns directory listings and `/download/*`, so long archive streams share process capacity and logging boundaries with interactive browse behavior.

After this work, exact run archive ZIP URLs such as `/weppcloud/runs/{runid}/{config}/download/archives/{name}.zip` will keep the same public URL but be served by a dedicated download service. A human can see the change working by starting the Docker/Caddy stack and using `curl` to verify `HEAD`, full `GET`, and ranged `GET` responses through the normal public path while non-archive browse routes still reach `browse`.

## Progress

- [x] (2026-06-19 16:52Z) Created the work package scaffold, tracker, security artifact, and this active ExecPlan.
- [x] (2026-06-19 16:52Z) Updated `wepppy/microservices/browse/README.md` with the planned dedicated download service boundary.
- [ ] Inventory existing browse download, auth, path security, Docker, and Caddy behavior.
- [ ] Design the minimal shared helper boundary so auth/path semantics do not drift.
- [ ] Implement the dedicated archive download service.
- [ ] Add structured download observability.
- [ ] Wire Docker Compose and Caddy for exact archive route cutover.
- [ ] Add tests and local route-smoke evidence.
- [ ] Complete security review and production rollout notes.

## Surprises & Discoveries

- Observation: None yet; scaffold only.
  Evidence: Implementation inventory has not started.

## Decision Log

- Decision: Move only exact archive ZIP downloads first.
  Rationale: The incident concern is critical completed-run archive delivery. Moving every `/download/*` path at once would mix exact file serving with parquet-to-CSV transforms, culvert/batch artifacts, and aria2c behavior, increasing regression risk.
  Date/Author: 2026-06-19 / Codex

- Decision: Keep public URLs stable and make Caddy route to the new backend.
  Rationale: Users, browser links, and generated browse links should not change. Backend routing can isolate the service without changing the external contract.
  Date/Author: 2026-06-19 / Codex

- Decision: Treat the package as high security impact.
  Rationale: It changes externally reachable file delivery and proxy routing for run-scoped artifacts. Auth, path traversal, and sensitive-path behavior require explicit review.
  Date/Author: 2026-06-19 / Codex

## Outcomes & Retrospective

No implementation outcome yet. The package is scaffolded and ready for discovery and implementation.

## Context and Orientation

The current browse service is a Starlette application under `wepppy/microservices/browse/browse.py`. It runs on port 9009 in Docker and registers browse UI routes, schema/files helper routes, D-Tale bridge routes, gdalinfo routes, and download routes. The download routes are implemented in `wepppy/microservices/browse/_download.py`.

The public WEPPcloud path prefix is normally `/weppcloud`. Current Caddy route matchers in `docker/caddy/Caddyfile` and `docker/caddy/Caddyfile.wepp1` send run paths matching `browse`, `schema`, `dtale`, `download`, `files`, `aria2c.spec`, and `gdalinfo` to `browse:9009`. Docker Compose service definitions for browse live in `docker/docker-compose.dev.yml`, `docker/docker-compose.prod.yml`, and `docker/docker-compose.prod.wepp1.yml`.

Authorization means deciding whether a caller is allowed to access a run artifact. The canonical contract is `docs/schemas/weppcloud-browse-auth-contract.md`; implementation helpers live in `wepppy/microservices/browse/auth.py`. Path-boundary protection means ensuring a requested `subpath` cannot escape the intended run tree through `..`, absolute paths, or symlink tricks; helpers live in `wepppy/microservices/browse/security.py`. These contracts must remain authoritative for the new service.

Range/resume friendly means the service supports HTTP range requests used by browsers and download clients to resume partial files. For a valid `Range: bytes=start-end` request, the service returns `206 Partial Content`, `Accept-Ranges: bytes`, `Content-Range: bytes start-end/size`, and a `Content-Length` equal to the bytes returned. For an unsatisfiable range, it returns `416 Range Not Satisfiable` and `Content-Range: bytes */size`. `HEAD` must return the same metadata as `GET` without streaming the body.

Observable means operators can answer, from logs, whether a download succeeded, how many bytes were sent or attempted, how long it took, whether it was a full or partial response, what status was returned, and whether the client disconnected or the server failed. Logs must not include secrets, raw JWTs, raw filter payloads, or sensitive full filesystem paths.

## Plan of Work

First, inventory the existing implementation. Read `wepppy/microservices/browse/_download.py`, `wepppy/microservices/browse/auth.py`, `wepppy/microservices/browse/security.py`, `docs/schemas/weppcloud-browse-auth-contract.md`, and the Caddy/Docker files listed above. Record any behavior that the new service must preserve in this ExecPlan and in `tracker.md` if it affects decisions or risk.

Second, design a minimal shared helper boundary. Prefer reusing existing helpers directly if they are already independent of browse UI state. If a helper must move, keep the change mechanical and behavior-preserving. Do not fork auth or path traversal logic into a similar-but-separate copy. At the end of this milestone, there should be a clear module path that both browse and download can import without circular imports.

Third, implement the new service. Create a new module under `wepppy/microservices/`, expected to be `wepppy/microservices/download/` unless inventory reveals an existing convention that fits better. Use Starlette, matching browse's stack. Add `/health` returning `OK`. Add the exact run archive route for `/weppcloud/runs/{runid}/{config}/download/archives/{subpath:path}` or the site-prefix-aware equivalent used by current services. The route must resolve only archive paths under the intended run tree and should reject directory targets, non-existent files, traversal attempts, and paths outside the archive scope.

Fourth, add HTTP file-serving behavior that is explicit about range handling. Do not rely on a framework default unless tests prove it returns the expected headers and statuses. Implement `HEAD`, full `GET`, single-range `GET`, and invalid range behavior. Multi-range requests may be rejected or treated as unsupported if documented and tested; do not silently return misleading headers.

Fifth, add structured logging. Use one completion log per request. Include request id if available or generate one if absent, route family `run_archive`, run id, config, sanitized path category `archives`, basename, file size, request method, response status, range start/end when present, bytes sent or best available byte count, duration, client address, user agent, and outcome such as `success`, `client_aborted`, `not_found`, `forbidden`, `range_not_satisfiable`, or `server_error`. If exact client abort detection is not reliable from Starlette/gunicorn alone, combine application evidence with Caddy access logs and document the limitation rather than inventing a false signal.

Sixth, wire Docker and Caddy. Add a service with its own port, health check, worker/process command, and environment consistent with browse. In Caddy, route the exact archive pattern before the broader browse matcher so archive ZIP downloads go to the new service and everything else remains unchanged. Add equivalent changes for dev, prod, and wepp1 production files.

Seventh, add tests. Cover route resolution and auth/path safety without needing production data. Use temporary files for archive fixtures. Tests must include full `GET`, `HEAD`, valid range, suffix/open-ended range if supported, invalid range, missing file, traversal, unauthorized/private run, allowed public run if practical, and non-archive denial or non-match behavior. Add route/config tests or smoke scripts for Caddy matcher assumptions if the repo has an existing pattern; otherwise document manual `curl` commands in the package.

Eighth, complete review and rollout artifacts. Update `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_security_review.md` with actual findings and evidence. Add closeout notes to `package.md` and `tracker.md`. Document wepp1 rollout and rollback: rollback should be able to return archive paths to `browse:9009` by reverting or disabling the exact Caddy matcher and stopping the new service.

## Concrete Steps

Work from repository root:

    cd /workdir/wepppy

Inventory commands:

    rg -n "download|archives|Range|StreamingResponse|FileResponse" wepppy/microservices/browse
    sed -n '1,260p' wepppy/microservices/browse/_download.py
    sed -n '1,260p' wepppy/microservices/browse/auth.py
    sed -n '1,220p' wepppy/microservices/browse/security.py
    rg -n "browse_proxy|download|9009|reverse_proxy browse" docker/caddy docker/docker-compose*.yml

Implementation commands will be added as the module path is finalized. Expected validation commands are:

    wctl run-pytest <focused new download tests>
    wctl run-pytest tests/microservices --maxfail=1
    wctl doc-lint --path docs/work-packages/20260619_dedicated_download_service
    wctl doc-lint --path wepppy/microservices/browse/README.md

Local smoke commands after Docker/Caddy wiring should include, with a real or fixture archive URL:

    curl -I http://localhost/weppcloud/runs/<runid>/<config>/download/archives/<archive>.zip
    curl -H 'Range: bytes=0-1023' -o /tmp/archive.part http://localhost/weppcloud/runs/<runid>/<config>/download/archives/<archive>.zip
    curl -o /tmp/archive.zip http://localhost/weppcloud/runs/<runid>/<config>/download/archives/<archive>.zip

The `curl -I` response should include `200` or an expected auth redirect/denial depending on the fixture. An authorized range request should return `206`, `Accept-Ranges: bytes`, and `Content-Range`. A full authorized request should return `200` and the full file length.

## Validation and Acceptance

Acceptance is behavioral, not only structural. A local test run must prove the new service can serve archive files and rejects unsafe requests. A local Caddy smoke must prove the public archive URL reaches the new service without changing the URL. Negative probes must prove browse UI, schema, D-Tale, files, gdalinfo, parquet CSV, culvert, and batch route families are not accidentally captured by the archive matcher.

Before production rollout, the security artifact must show no unresolved high or medium findings. After production rollout, capture wepp1 smoke evidence for `HEAD`, full `GET`, and ranged `GET` against a representative archive. The logs should show completion events with status, bytes, duration, range metadata when present, user agent, and sanitized path category.

## Idempotence and Recovery

The implementation should be additive until cutover. The browse route should remain available in code so rollback can be done by reverting or disabling the Caddy exact archive matcher and stopping the download service. Tests should use temporary fixture files and not require mutation of `/wc1/runs`.

If Docker/Caddy wiring fails, revert only the new service route matcher and service dependency changes; do not alter the existing broad browse matcher. If auth/path helper extraction causes circular imports, stop and refactor the helper into a neutral module imported by both services instead of copying logic.

## Artifacts and Notes

The work package lives at `docs/work-packages/20260619_dedicated_download_service/`.

Update these files as evidence accumulates:

- `docs/work-packages/20260619_dedicated_download_service/tracker.md`
- `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_security_review.md`
- `docs/work-packages/20260619_dedicated_download_service/package.md`
- `wepppy/microservices/browse/README.md`

## Interfaces and Dependencies

Use Starlette and the same gunicorn/uvicorn deployment style as browse. Do not introduce a new external download framework unless `docs/standards/dependency-evaluation-standard.md` is completed and the package records the decision.

The new service must expose:

- `GET /health` returning status `200` with body `OK`.
- `HEAD` and `GET` for exact run archive paths under the normal site prefix.

The new implementation must preserve or reuse these existing contracts:

- `docs/schemas/weppcloud-browse-auth-contract.md`
- `wepppy/microservices/browse/auth.py`
- `wepppy/microservices/browse/security.py`

Revision note, 2026-06-19: Initial ExecPlan created to scaffold the dedicated download service package and record the target shape before implementation begins.
