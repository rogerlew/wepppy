# Tracker - Dedicated Download Service for Critical Run Artifacts

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC
**Started**: 2026-06-19 16:52 UTC
**Current phase**: Implementation, QA/security disposition, and local Caddy full/range/resume smoke complete / production rollout pending
**Last updated**: 2026-06-19 17:32 UTC
**Next milestone**: Cut over on wepp1 and capture live `HEAD`, full `GET`, and range `GET` smoke evidence.
**Security impact**: high
**Dedicated security review**: yes
**Security artifact**: `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_security_review.md`
**QA artifact**: `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_qa_review.md`

## Task Board

### Ready / Backlog

- [ ] Cut over on wepp1 and capture live archive `HEAD`, full `GET`, and range `GET` smoke evidence.
- [ ] Observe archive download service logs for 14 days after production cutover.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Scaffolded package, active ExecPlan, tracker, and initial security artifact. (2026-06-19 16:52 UTC)
- [x] Updated browse README with planned service boundary and target shape. (2026-06-19 16:52 UTC)
- [x] Inventoried existing browse download, auth, path-security, Docker, and Caddy behavior. (2026-06-19 17:11 UTC)
- [x] Implemented `wepppy.microservices.download` with archive-only `GET`/`HEAD`, single-range support, invalid-range `416`, and `/health`. (2026-06-19 17:11 UTC)
- [x] Reused canonical `browse.auth` and `browse.security` helpers without forking auth logic. (2026-06-19 17:11 UTC)
- [x] Added structured `download.complete` logs with bytes, duration, status, range metadata, client identity fields, and sanitized artifact identity. (2026-06-19 17:11 UTC)
- [x] Wired Docker Compose and Caddy for exact archive ZIP route cutover to `download:9011`. (2026-06-19 17:11 UTC)
- [x] Added focused service and routing tests. (2026-06-19 17:11 UTC)
- [x] Completed implementation security review with no unresolved high/medium findings. (2026-06-19 17:11 UTC)
- [x] Completed QA review and dispositioned QA-01/QA-02. (2026-06-19 17:24 UTC)
- [x] Re-reviewed security after QA fixes and dispositioned SEC-05. (2026-06-19 17:24 UTC)

## Timeline

- **2026-06-19 16:52 UTC** - Package created from incident follow-up discussion about isolating critical archive downloads from browse.
- **2026-06-19 17:11 UTC** - Local implementation completed and focused tests/config validation passed; production rollout remains pending.
- **2026-06-19 17:32 UTC** - Local Caddy `HEAD`, full `GET`, range, sparse-resume, and service-log smoke evidence captured against a 2.5 GB archive.

## Decisions Log

### 2026-06-19 16:52 UTC: Start with archive ZIP downloads only

**Context**: The reliability concern is most acute for completed run archive downloads. Existing `/download/*` also includes parquet-to-CSV transforms, culvert artifacts, batch artifacts, and aria2c manifest generation.

**Options considered**:
1. Move every download route immediately - broadest isolation but highest auth/routing regression risk.
2. Move only archive ZIP delivery first - isolates the critical path while keeping transform-heavy compatibility routes stable.
3. Keep downloads in browse and only add logging - lowest implementation cost but does not remove non-NFS common-cause vectors.

**Decision**: Move exact archive ZIP delivery first and leave other route families on `browse` until separately scoped.

**Impact**: The first implementation must make route matching precise and must prove non-archive browse/download behavior is unchanged.

---

### 2026-06-19 16:52 UTC: Treat this as high security impact

**Context**: The package adds a public-facing file-serving service and changes Caddy routing for run-scoped artifacts.

**Options considered**:
1. Routine review only - faster, but too weak for auth/path/proxy changes.
2. Dedicated security review artifact - more ceremony, but creates an explicit gate for sensitive file delivery.

**Decision**: Require a dedicated security review artifact.

**Impact**: No production rollout should happen until the security artifact has no unresolved high or medium findings.

---

### 2026-06-19 17:11 UTC: Reuse browse auth/security directly

**Context**: The new service needs to preserve browse's public/private run behavior, bearer/cookie fallback, root-only path handling, and path security rules.

**Options considered**:
1. Copy current auth/path code into `download` - quick but risks drift.
2. Move helpers into a new neutral module - clean long-term boundary but higher churn for this incident-driven package.
3. Import `browse.auth` and `browse.security` directly - smallest behavior-preserving change.

**Decision**: Import and reuse `browse.auth` and `browse.security` directly.

**Impact**: The first service avoids auth drift. A future refactor can centralize helper names once more services share the same contract.

---

### 2026-06-19 17:11 UTC: Reject raw traversal syntax inside archive route

**Context**: Legacy broad download paths normalize some safe `..` cases after joining against the run root. The new service has a narrower exact archive contract.

**Options considered**:
1. Preserve broad-route normalization behavior exactly.
2. Reject raw `.`, `..`, empty path segments, and backslashes in archive subpaths.

**Decision**: Reject raw traversal syntax for the archive service.

**Impact**: The route is stricter than legacy broad download behavior, which is acceptable because it only serves exact archive ZIPs and must avoid ambiguity.

---

### 2026-06-19 17:24 UTC: QA dispositions

**Context**: Formal QA review found two implementation gaps: synchronous file reads inside the ASGI response loop and lowercase-only Caddy ZIP routing.

**Options considered**:
1. Accept both as residual risk - would leave concurrency and observability gaps in the critical path.
2. Fix both before handoff - small localized changes with clear tests.

**Decision**: Fix both before handoff.

**Impact**: File reads now run through `asyncio.to_thread(...)`, and both Caddyfiles route `.zip` and `.ZIP` variants to `download:9011`.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Auth behavior drifts between `browse` and `download`. | High | Medium | Share or faithfully extract current helpers; add auth/public/private tests. | Mitigated |
| Caddy route matcher accidentally captures non-archive downloads. | High | Medium | Use exact archive matcher first; add negative route tests for archive and non-archive paths. | Mitigated |
| Range support is implemented but not actually resume friendly in browsers. | Medium | Medium | Add `curl -H Range` tests plus browser/manual resume validation where practical. | Partially mitigated; live smoke pending |
| Byte/abort logging is incomplete because streaming responses hide disconnect details. | Medium | Medium | Instrument the streaming generator and document that disconnect classification is best-effort. | Mitigated |
| Blocking file reads reduce download-service concurrency on slow storage. | Medium | Medium | Move archive file open/seek/read/close operations to worker threads. | Mitigated |
| NFS remains the bottleneck after split. | Medium | Medium | Treat split as isolation, not NFS remediation; collect service telemetry before considering object storage/local cache. | Open |

## Hardening Signal Log

- **Baseline health signals**: Browse previously showed high worker RSS before PyArrow-to-pandas remediation; operators still need clear bytes/duration/abort evidence for critical archive downloads.
- **Post-change health signals**: Local tests verify full/range/HEAD behavior and structured log fields; production signals pending rollout.
- **Danger signals observed**: No route-shadowing or auth drift found in focused tests. Caddy validation reports preexisting formatting/header warnings, not route invalidity.
- **Temporary callus register**:
  - Exact archive route matcher, owner WEPPcloud operators, introduced 2026-06-19, sunset/review after 14-day production observation.
- **Softening experiments**:
  - Hypothesis: If archive delivery is stable and route telemetry is clean, exact-route special cases can be simplified or expanded to other exact downloads under a follow-up package.
  - Gate results: Pending.
  - Decision: Pending.

## Verification Checklist

### Code Quality

- [x] Focused tests passing (`wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/docker/unit/test_download_service_routing.py -q`).
- [x] Relevant microservice tests passing (`wctl run-pytest tests/microservices/test_download.py ... -q` focused legacy download/auth subset).
- [ ] Type checking clean if a new typed module surface is added (`wctl run-stubtest <module>`).
- [ ] No new security vulnerabilities.

### Security

- [x] Security impact triage recorded as high with rationale.
- [x] Dedicated security review artifact is present.
- [x] No unresolved medium/high security findings remain in the security artifact.
- [x] Attack-surface changes are explicitly reviewed.
- [x] Residual risks and follow-up mitigation actions are recorded.

### Documentation

- [x] Browse README updated for the planned service boundary.
- [x] New download service README added or equivalent operator docs updated.
- [ ] Work package closure notes complete.
- [x] Parameterization ADR gate recorded as not required.

### Testing

- [x] Unit test coverage for full, `HEAD`, valid range, invalid range, unauthorized, public-run, and traversal cases.
- [x] Integration or configuration tests for Docker/Caddy route assumptions.
- [x] Manual `HEAD`, full `GET`, range, and sparse-resume smoke testing performed through local Caddy.
- [x] Backward compatibility verified for non-migrated browse/download route families with focused legacy tests.

### Deployment

- [x] Tested in `docker/docker-compose.dev.yml` configuration with `docker compose config --quiet`.
- [x] wepp1 rollout and rollback plan documented.
- [ ] Production smoke evidence captured after cutover.

## Progress Notes

### 2026-06-19 16:52 UTC: Package scaffold

**Agent/Contributor**: Codex

**Work completed**:
- Created work package, tracker, active ExecPlan, and initial security artifact.
- Updated `wepppy/microservices/browse/README.md` to document the planned dedicated download service boundary.
- Added package to `PROJECT_TRACKER.md` backlog.

**Blockers encountered**:
- None.

**Next steps**:
- Inventory `_download.py`, current Caddy matchers, and auth/path helpers before writing code.
- Decide exact service module name and route matcher shape.

**Test results**: Documentation lint to be run after scaffold edits.

### 2026-06-19 17:11 UTC: Local implementation

**Agent/Contributor**: Codex

**Work completed**:
- Added `wepppy/microservices/download/` Starlette service.
- Added archive-only route for `/weppcloud/runs/{runid}/{config}/download/archives/{subpath}.zip` with `GET`, `HEAD`, single-range `206`, invalid-range `416`, and `/health`.
- Reused browse auth and path security helpers directly.
- Added structured `download.complete` logging.
- Added Docker Compose service wiring and Caddy exact archive matcher before the broad browse matcher.
- Added service README, microservices README entry, focused service tests, and routing/config tests.

**Blockers encountered**:
- Python import shadowing in tests because `wepppy.microservices.download.__init__` exports `app`; fixed the fixture by loading `wepppy.microservices.download.app` through `importlib.import_module`.

**Next steps**:
- Deploy/restart the download service and Caddy on wepp1.
- Smoke test a representative archive with `HEAD`, full `GET`, and `Range: bytes=0-1023`.
- Watch `download.complete` logs through the 14-day observation window.

**Test results**:
- `wctl run-pytest tests/microservices/test_dedicated_download_service.py -q` - 14 passed.
- `wctl run-pytest tests/docker/unit/test_download_service_routing.py -q` - 5 passed.
- `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/docker/unit/test_download_service_routing.py -q` - 19 passed after QA dispositions.
- `wctl run-pytest tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py::test_private_download_redirects_only_for_navigation tests/microservices/test_browse_auth_routes.py::test_private_download_uses_bearer_when_cookie_run_scope_mismatch tests/microservices/test_browse_auth_routes.py::test_run_download_root_only_path_uses_bearer_when_cookie_lacks_root_role -q` - 9 passed.
- `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_browse_security.py tests/microservices/test_browse_routes.py tests/docker/unit/test_download_service_routing.py -q` - 140 passed.
- `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml config --quiet` - passed.
- `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config --quiet` - passed.
- `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml config --quiet` - passed.
- `docker run --rm -v /workdir/wepppy/docker/caddy/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile` - valid configuration with preexisting warnings.
- `docker run --rm -v /workdir/wepppy/docker/caddy/Caddyfile.wepp1:/etc/caddy/Caddyfile:ro caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile` - valid configuration with preexisting warnings.
- `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` - pass for tracked changed Python files; new service files were manually inspected and contain no broad `except Exception` handlers.

### 2026-06-19 17:24 UTC: QA and security review dispositioning

**Agent/Contributor**: Codex

**Work completed**:
- Added `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_qa_review.md`.
- Dispositioned QA-01 by moving file I/O in archive streaming through `asyncio.to_thread(...)`.
- Dispositioned QA-02 by making Caddy ZIP extension matching case-consistent with the service and adding uppercase `.ZIP` route coverage.
- Updated the security review with the QA artifact link and resolved SEC-05.

**Blockers encountered**:
- None.

**Next steps**:
- Production rollout/smoke evidence remains the only open package milestone.

**Test results**:
- `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/docker/unit/test_download_service_routing.py -q` - 19 passed after QA fixes.
- `PYTHONPATH=/home/workdir/wepppy .venv/bin/pytest tests/microservices/test_dedicated_download_service.py tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_browse_security.py tests/microservices/test_browse_routes.py tests/docker/unit/test_download_service_routing.py -q` - 140 passed after QA/security dispositions.
- `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_browse_security.py tests/microservices/test_browse_routes.py tests/docker/unit/test_download_service_routing.py -q` - 140 passed after the local stack was restarted.
- Local Caddy `HEAD` smoke for `honeyed-marathoner/disturbed9002` archive returned `200`, `Accept-Ranges: bytes`, `Content-Length: 2516876934`, `Server: uvicorn`, and `Via: 1.1 Caddy`.
- Local Caddy full `GET` returned `200` and downloaded `2516876934` bytes in `12.207687` seconds at reported curl speed `206171483` bytes/s.
- Local Caddy `Range: bytes=0-1048575` returned `206` with `Content-Range: bytes 0-1048575/2516876934` and `1048576` downloaded bytes.
- Local Caddy sparse resume from byte `2515828358` returned `206` with `Content-Range: bytes 2515828358-2516876933/2516876934` and `1048576` downloaded bytes.
- Download service logs showed matching `download.complete` events for the `HEAD`, full `GET`, and both `206` probes.
- Caddy validation passed for `docker/caddy/Caddyfile` and `docker/caddy/Caddyfile.wepp1` with preexisting warnings.

## Watch List

- **NFS dependency**: The split isolates process/proxy/common-cause issues but does not eliminate NFS as a shared backend.
- **Route precision**: Caddy matchers must keep transform downloads and grouped-run route families on browse until intentionally migrated.
- **Logging privacy**: Logs need operational evidence without exposing tokens, raw query filters, or sensitive full paths.

## Communication Log

### 2026-06-19 16:52 UTC: Target shape selected

**Participants**: Human operator, Codex  
**Question/Topic**: Whether to separate download from browse for critical reliability.  
**Outcome**: Scaffold the dedicated download service package around the target shape: browse remains interactive, download service handles exact archive delivery, and downloads get independent process controls plus range/resume-friendly observability.
