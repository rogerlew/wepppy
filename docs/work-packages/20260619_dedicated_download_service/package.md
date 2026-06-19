# Dedicated Download Service for Critical Run Artifacts

**Status**: Open (2026-06-19) - implementation complete; production rollout pending
**Timezone**: UTC

## Overview

Critical WEPPcloud archive downloads currently share the `browse` service with interactive directory browsing, previews, parquet export, D-Tale handoff, and crawler-facing route families. This package separates exact archive delivery into a dedicated download service so large downloads can be isolated, range/resume friendly, and instrumented with request-level evidence.

The split does not remove shared NFS/run-root risk. It reduces other common-cause vectors so download reliability can be measured and hardened separately from browse UI pressure.

## Objectives

- Create a dedicated download microservice for exact run artifact delivery, starting with archive ZIP downloads at `/weppcloud/runs/{runid}/{config}/download/archives/*.zip`.
- Preserve canonical browse authorization, public-run behavior, root-only path restrictions, and path traversal protections.
- Support range/resume-friendly HTTP behavior for archive downloads, including `HEAD`, `Accept-Ranges`, `206 Partial Content`, `416 Range Not Satisfiable`, `Content-Length`, and `Content-Range`.
- Add structured download logs with request id, run id, config, route family, sanitized path category, basename, file size, range start/end, bytes sent or best available byte count, duration, status, client abort/error reason when known, client address, and user agent.
- Wire Docker and Caddy so the exact archive route can be cut over independently of `browse`, with its own health check, worker/process model, timeouts, and concurrency controls.
- Add focused automated tests and an operator validation checklist that prove full, range, missing-file, unauthorized, traversal, and proxy-routed archive downloads behave correctly.

## Scope

### Included

- New or extracted download service code under `wepppy/microservices/`, using the existing Starlette/gunicorn/uvicorn style already used by `browse`.
- Shared auth/path resolution helpers only where needed to preserve current behavior without broad browse refactoring.
- Caddy and Docker Compose changes in `docker/docker-compose.dev.yml`, `docker/docker-compose.prod.yml`, `docker/docker-compose.prod.wepp1.yml`, `docker/caddy/Caddyfile`, and `docker/caddy/Caddyfile.wepp1`.
- Focused unit/integration tests for service behavior and route wiring.
- Documentation updates for `wepppy/microservices/browse/README.md`, any new download service README, and package closeout artifacts.
- Production rollout notes for wepp1, including a rollback path that returns archive routes to `browse`.

### Explicitly Out of Scope

- Removing NFS as a shared dependency or moving archives to object storage.
- Rewriting the browse UI, D-Tale bridge, parquet preview/export implementation, or manifest listing system.
- Migrating all `/download/*` families in one step. Culvert, batch, parquet-to-CSV, filtered CSV, and aria2c flows remain on `browse` until separately scoped.
- Changing user-visible download URLs.
- Adding new third-party serving frameworks unless the dependency evaluation standard is completed first.

## Implementation Fidelity and Evidence

- **Fidelity target**: faithful extraction for archive delivery semantics.
- **Authoritative source path(s)**: `wepppy/microservices/browse/_download.py`, `wepppy/microservices/browse/auth.py`, `wepppy/microservices/browse/security.py`, and `docs/schemas/weppcloud-browse-auth-contract.md`.
- **Cutover proof required**: Docker/Caddy route evidence showing `/weppcloud/runs/{runid}/{config}/download/archives/*.zip` reaches the new service while other browse route families continue to reach `browse:9009`.
- **Acceptance evidence type**: both generated-output and fixture-only evidence. Fixture tests prove edge cases; generated evidence must include local docker/Caddy `curl` probes for `HEAD`, full GET, and ranged GET.

## Stakeholders

- **Primary**: WEPPcloud operators and users downloading completed run archives.
- **Reviewers**: WEPPcloud maintainers responsible for browse/download and production routing.
- **Security Reviewer**: Required because the package changes externally reachable artifact delivery and proxy routing.
- **Informed**: Incident responders tracking the June 2026 wepp1 browse/download slowdown.

## Success Criteria

- [x] Archive ZIP downloads can be served by the dedicated service without changing the public URL.
- [x] `HEAD`, full `GET`, valid range `GET`, and invalid range `GET` return correct HTTP status and headers.
- [x] Auth, public-run allowance, traversal denial, missing-file, and non-archive route behavior are covered by tests.
- [x] Caddy routes exact archive download traffic to the new service in dev and production configuration, while browse/schema/dtale/files/gdalinfo and non-migrated downloads still route correctly.
- [x] Download logs include bytes, duration, status, range metadata, sanitized path category, client identity fields, and abort/error classification without logging secrets or raw tokens.
- [x] The service has independent health check, worker/process configuration, timeout posture, and documented rollback.
- [x] Work package security review has no unresolved high or medium findings before production rollout.
- [x] Work package QA review has no unresolved high, medium, or low findings before production rollout.
- [x] Local Caddy `HEAD`, full `GET`, range, sparse-resume, and service-log smoke evidence are captured for a 2.5 GB archive.
- [ ] wepp1 production cutover and live archive `HEAD`/full/range smoke evidence are captured.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR link(s)**: N/A
- **Decision provenance captured**: yes

Reference: `docs/standards/parameterization-adr-standard.md`

## Dependencies

### Prerequisites

- Current browse auth and path-boundary contracts remain canonical.
- Docker/Caddy development stack can be used for route validation.
- Operators can provide or confirm a representative archive ZIP under `/wc1/runs/` for production smoke testing.

### Blocks

- Production cutover of critical run archive downloads to an isolated service.
- Follow-up work to decide whether all non-transforming downloads should move out of `browse`.
- Any later object-storage or non-NFS download architecture evaluation.

## Related Packages

- **Depends on**: `docs/work-packages/20260616_browse_arrow_pandas_elimination/` for browse RSS remediation context.
- **Related**: `docs/work-packages/20260616_dtale_lazy_parquet_backend/` for D-Tale pandas memory isolation context.
- **Related**: `docs/infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md` for the incident record motivating this package.
- **Follow-up**: A separate package may evaluate object storage or non-NFS archive publication if evidence shows NFS remains the dominant reliability limit.

## Timeline Estimate

- **Expected duration**: 2-4 focused sessions.
- **Complexity**: Medium-High.
- **Risk level**: High, because this changes production download routing and authorization-sensitive file delivery.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package adds an externally reachable artifact-serving service, changes proxy routing, and reuses sensitive run-scoped authorization/path logic.
- **Security review artifact**: `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_security_review.md`
- **QA review artifact**: `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_qa_review.md`

## Hardening and Callus Softening

- **Failure signature(s)**: Slow or timed-out archive downloads on wepp1; browse worker RSS growth previously observed around 45-49 GiB; Caddy/browser downloads lacking service-level byte/duration/abort evidence; mixed browse UI and long download load on the same worker pool.
- **Related prior hardening efforts**: `docs/work-packages/20260616_browse_arrow_pandas_elimination/`, `docs/work-packages/20260616_dtale_lazy_parquet_backend/`, and `docs/infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md`.
- **Health signals**: Stable archive download throughput under browse UI/crawler load, low download worker RSS, clear `2xx`/`206`/`4xx`/`5xx`/abort logs, and successful browser resume/range probes.
- **Danger signals**: Duplicate auth logic drifting from browse, route shadowing that breaks non-archive downloads, logs containing tokens or sensitive full paths, or a new service that still lacks byte/duration evidence.
- **Observation window**: 14 days after production cutover.
- **Temporary calluses introduced**: Route-specific Caddy matcher and independent service knobs, owner WEPPcloud operators, review after the observation window.
- **Callus softening hypothesis**: If the dedicated service proves stable and route matching is clean, archive-specific Caddy exceptions can be simplified or generalized only after tests and security review cover the broader route family.

## References

- `wepppy/microservices/browse/README.md` - Current browse service contract and planned download service boundary.
- `wepppy/microservices/browse/_download.py` - Current download route implementation and archive serving behavior.
- `wepppy/microservices/browse/auth.py` - Browse authorization helpers that must remain authoritative or be shared safely.
- `wepppy/microservices/browse/security.py` - Path-boundary helpers for run-scoped files.
- `docs/schemas/weppcloud-browse-auth-contract.md` - Canonical browse/download authorization contract.
- `docker/docker-compose.dev.yml` - Development service wiring.
- `docker/docker-compose.prod.yml` - Production service wiring.
- `docker/docker-compose.prod.wepp1.yml` - wepp1 production override.
- `docker/caddy/Caddyfile` - Default Caddy route wiring.
- `docker/caddy/Caddyfile.wepp1` - wepp1 Caddy route wiring.
- `docs/infrastructure/incident-2026-06-16-wepp1-browse-download-slowdown.md` - Incident timeline and operational evidence.

## Deliverables

- Dedicated download service code and tests in `wepppy/microservices/download/` and `tests/microservices/test_dedicated_download_service.py`.
- Docker Compose and Caddy route updates in dev, prod, and wepp1 configuration files.
- New service README at `wepppy/microservices/download/README.md` plus updated browse and microservices READMEs.
- QA and security review artifacts with implementation findings resolved.
- Local config validation for Compose and Caddy.
- Production validation notes with full/range/HEAD smoke evidence remain pending until wepp1 cutover.

## Follow-up Work

- Decide whether other exact non-transforming downloads should migrate after archive cutover evidence.
- Evaluate object storage, local archive cache, or other non-NFS approaches if NFS remains a dominant bottleneck.
- Revisit bot/rate-limit policies only after critical download service telemetry shows request classes clearly.
