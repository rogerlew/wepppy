# Security Review - Dedicated Download Service for Critical Run Artifacts

> Security artifact for the dedicated download service package. Implementation findings are resolved; production rollout still requires live smoke evidence.

## Metadata

- **Package**: `docs/work-packages/20260619_dedicated_download_service/`
- **Reviewer**: Codex implementation review
- **Date**: 2026-06-19
- **Scope reviewed**: Dedicated archive download service, browse auth/path reuse, Docker Compose service wiring, Caddy route changes, focused tests, and service documentation.
- **Commit/branch context**: local `master` worktree during implementation.
- **Related artifacts**:
  - Code review: no separate code-review artifact was requested for this pass; implementation findings are dispositioned through the QA and security reviews.
  - QA review: `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_qa_review.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The package introduces a new externally reachable file-serving service and changes proxy routing for run-scoped artifacts. Auth, path traversal, route shadowing, logging privacy, and operational rollback must be reviewed explicitly.
- **Threat model assumptions**:
  - Attackers may know or guess public route shapes and may try traversal, symlink, encoded-path, or range-header abuse.
  - Some runs are public, while private and root-only paths must remain protected by the canonical browse auth contract.
  - Reverse proxy routing mistakes can expose unintended files or bypass existing browse checks even if service code is correct.
  - Logs may be accessible to operators and must not contain secrets, raw JWTs, raw query filters, or sensitive full filesystem paths.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Auth/path extraction | New service could drift from canonical browse auth and path-boundary behavior. | `wepppy/microservices/download/app.py` imports `browse.auth` and `browse.security`; `tests/microservices/test_dedicated_download_service.py` covers public, private, bearer, traversal, hidden, non-zip, and range behavior. | Reuse or faithfully extract existing helpers; add regression tests for private, public, traversal, missing/non-archive, and path-boundary cases. | Resolved |
| SEC-02 | High | Caddy routing | Exact archive matcher could accidentally capture non-archive downloads or route broader `/download/*` traffic to incomplete service behavior. | `docker/caddy/Caddyfile` and `docker/caddy/Caddyfile.wepp1` add `archive_download_proxy` before `browse_proxy`; `tests/docker/unit/test_download_service_routing.py` proves archive-only matching and non-archive fallback. | Add precise route matcher before broad browse matcher; add negative route probes for browse/schema and non-archive downloads. | Resolved |
| SEC-03 | Medium | Logging privacy | Enhanced observability could log raw tokens, raw query strings, or full sensitive filesystem paths. | `download.complete` logs sanitized category/basename and client fields only; `test_archive_download_logs_range_completion_without_full_path_or_token` verifies full run root and `Authorization` are absent. | Use sanitized path category and basename only; explicitly exclude Authorization, cookies, raw JWTs, raw filters, and full absolute paths from logs. | Resolved |
| SEC-04 | Medium | Range handling | Malformed or extreme range headers could trigger resource waste or incorrect responses. | `_parse_range_header` handles single closed/open/suffix ranges and rejects invalid/multi-range requests with `416`; focused tests cover valid and unsatisfiable ranges. | Parse single ranges defensively; reject invalid ranges with `416`; test open-ended, suffix, and unsatisfiable ranges. | Resolved |
| SEC-05 | Low | Route consistency | Lowercase-only Caddy ZIP matching could route uppercase `.ZIP` archives through browse instead of the dedicated service, reducing isolation and audit consistency. | QA review found Caddy regex `\.zip$` while the service accepted ZIP extensions case-insensitively. | Updated both Caddyfiles to `[Zz][Ii][Pp]` and added routing test coverage for uppercase `.ZIP`. | Resolved |

Risk acceptance authority: `Accepted-risk` requires security reviewer recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: pass for local implementation; production cutover remains conditional on live smoke validation.
- **Unresolved findings**:
  - High: 0
  - Medium: 0
  - Low: 0
- **Release recommendation**: ship with conditions. Before considering production complete, start the service on wepp1, reload Caddy, and capture `HEAD`, full `GET`, ranged `GET`, and log evidence for a representative archive.

## Surface Checks

### 1) Auth, Session, and Authorization

- [x] Entry points enforce expected authn/authz checks for changed routes/services.
- [x] Role checks and scope checks are explicit, least-privilege, and regression-tested.
- [x] Session/JWT token validation paths preserve canonical contracts.
- [x] CSRF protections are preserved for browser session mutation paths; the new route is read-only.
- [x] Cross-service auth token mint/verify flows are not widened unintentionally.
- [x] Error paths do not disclose token contents or auth internals.

### 2) Secrets and Credential Handling

- [x] No new plaintext secrets in repository files, env defaults, or docs examples.
- [x] `*_FILE` secret-file contract is preserved where applicable.
- [x] No secrets passed in argv, query params, or logs.
- [x] Added/changed services mount only required secrets.
- [x] Rotation and rollback behavior are documented for new secret dependencies; no new secret dependency was introduced.
- [x] Changed code avoids fallback wrappers that silently skip missing secrets.

### 3) Input Validation and Output Safety

- [x] Untrusted input is validated at boundaries (types, ranges, enum membership).
- [x] File/path inputs block traversal and out-of-scope path access.
- [x] Rendered output paths avoid unsafe HTML/markdown/script injection; the route does not render user content.
- [x] URL fetch/download flows enforce allowlist or explicit safety constraints.
- [x] Unsafe deserialization and shell interpolation patterns are absent.
- [x] Failing validation returns explicit contract-compliant errors.

### 4) File System and Run-Tree Boundaries

- [x] Writes remain inside intended run roots (`/wc1/runs/...`) and approved paths; the new service is read-only.
- [x] No new path joins allow escaping run scope via symlink or relative path tricks.
- [x] Export/download paths avoid leaking unrelated files.
- [x] Temporary files and artifacts are cleaned up or intentionally retained with policy; the service creates none.
- [x] Permissions for generated files/directories are least-privilege; the service generates none.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] Enqueue sites and dependency edges remain intentional and documented; no queue wiring changed.
- [x] Worker task inputs are validated before shell/subprocess/file operations; no worker/subprocess path was added.
- [x] Subprocess invocation avoids shell injection and unbounded command composition; no subprocess call was added.
- [x] Queue cancellation/retry paths cannot bypass auth or data ownership boundaries; no queue path was added.
- [x] `wctl check-rq-graph` has been run when queue wiring changed; not applicable because no queue wiring changed.
- [x] Failure handling preserves canonical response/error contracts.

### 6) Agentic Tooling and MCP Surfaces

- [x] Agent/tool calls do not grant broader permissions than the parent request needs.
- [x] No path for implicit privilege escalation through subagents or helper tools introduced by scaffold-only docs.
- [x] MCP/tool tokens and credentials are scoped and not leaked in logs/artifacts.
- [x] Tool execution constraints are explicit when running commands or file writes.
- [x] Guardrails block unauthorized network egress or public artifact publication.

### 7) Network and External Integrations

- [x] New outbound calls are justified, constrained, and observable; no outbound calls were added.
- [x] Timeouts/retries avoid denial-of-service amplification and unsafe fallback loops.
- [x] Internal-only endpoints are not exposed through new proxy/route changes.
- [x] Rate limits/throttles are considered for high-cost or abuse-prone endpoints; this package isolates worker/timeouts but does not add rate limiting.
- [x] External dependency trust assumptions are documented; no new dependency was added.

### 8) CI/CD and Supply Chain

- [x] Self-hosted runner access scope is unchanged or tightened.
- [x] Workflow token permissions are minimal for changed jobs; no workflow changed.
- [x] Build/test scripts avoid exposing credentials in logs.
- [x] New third-party dependencies passed precedent and risk checks; no new dependency was added.
- [x] Pinned versions/digests are used where policy requires.

### 9) Data Integrity, Locking, and Concurrency

- [x] NoDb lock/dump contracts are preserved (`dump_and_unlock`, lock scope); no NoDb mutation path changed.
- [x] Cross-process shared state updates remain atomic and auditable; no shared-state mutation path was added.
- [x] Redis keyspaces and TTL behavior are unchanged unless explicitly planned.
- [x] Concurrent mutation paths include regression coverage for race conditions; no mutation path was added.
- [x] Recovery after partial failure leaves state consistent and diagnosable.

### 10) Logging, Monitoring, and Incident Readiness

- [x] Logs include enough context for incident triage without exposing secrets.
- [x] Security-relevant events have observable signals (auth failures, denials, exfil attempts).
- [x] New error handlers do not swallow exceptions silently.
- [x] Alerting/operational checks are updated for new high-risk surfaces; health check and service logs are available, production alerting remains operator-owned.
- [x] Rollback and containment steps are documented for the changed scope.

## Validation Evidence

- Automated checks run:
  - `wctl run-pytest tests/microservices/test_dedicated_download_service.py -q` - 14 passed.
  - `wctl run-pytest tests/docker/unit/test_download_service_routing.py -q` - 5 passed.
  - `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/docker/unit/test_download_service_routing.py -q` - 19 passed.
  - `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/docker/unit/test_download_service_routing.py -q` - 19 passed after QA dispositions.
  - `wctl run-pytest tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py::test_private_download_redirects_only_for_navigation tests/microservices/test_browse_auth_routes.py::test_private_download_uses_bearer_when_cookie_run_scope_mismatch tests/microservices/test_browse_auth_routes.py::test_run_download_root_only_path_uses_bearer_when_cookie_lacks_root_role -q` - 9 passed.
  - `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_browse_security.py tests/microservices/test_browse_routes.py tests/docker/unit/test_download_service_routing.py -q` - 140 passed.
  - `PYTHONPATH=/home/workdir/wepppy .venv/bin/pytest tests/microservices/test_dedicated_download_service.py tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_browse_security.py tests/microservices/test_browse_routes.py tests/docker/unit/test_download_service_routing.py -q` - 140 passed after QA/security dispositions.
  - `wctl run-pytest tests/microservices/test_dedicated_download_service.py tests/microservices/test_download.py tests/microservices/test_browse_auth_routes.py tests/microservices/test_browse_security.py tests/microservices/test_browse_routes.py tests/docker/unit/test_download_service_routing.py -q` - 140 passed after the local stack was restarted.
  - `docker compose --env-file docker/.env -f docker/docker-compose.dev.yml config --quiet` - passed.
  - `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml config --quiet` - passed.
  - `docker compose --env-file docker/.env -f docker/docker-compose.prod.yml -f docker/docker-compose.prod.wepp1.yml config --quiet` - passed.
  - `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` - passed for tracked changed Python files; new service files were manually inspected for broad exception handlers.
- Manual checks run:
  - `docker run --rm -v /workdir/wepppy/docker/caddy/Caddyfile:/etc/caddy/Caddyfile:ro caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile` - valid configuration with preexisting warnings.
  - `docker run --rm -v /workdir/wepppy/docker/caddy/Caddyfile.wepp1:/etc/caddy/Caddyfile:ro caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile` - valid configuration with preexisting warnings.
  - Local Caddy `HEAD` smoke against `honeyed-marathoner/disturbed9002` returned `200`, `Accept-Ranges: bytes`, `Content-Length: 2516876934`, `Server: uvicorn`, `Via: 1.1 Caddy`, and request id `43dc51062fa54ab3a3a61bc0bc3836ec`.
  - Local Caddy full `GET` smoke returned `200` and downloaded `2516876934` bytes in `12.207687` seconds at reported curl speed `206171483` bytes/s.
  - Local Caddy `Range: bytes=0-1048575` smoke returned `206`, `Content-Range: bytes 0-1048575/2516876934`, and downloaded `1048576` bytes.
  - Local Caddy sparse resume smoke from byte `2515828358` returned `206`, `Content-Range: bytes 2515828358-2516876933/2516876934`, and completed by downloading only the final `1048576` bytes.
  - Download service logs showed matching `download.complete` events for `HEAD`, full `GET`, and both ranged probes with sanitized artifact identity and no tokens or absolute run-root paths.

## Residual Risk

- **Accepted residual risks**:
  - Client disconnect classification is best-effort from the Starlette streaming generator. Operators should correlate app logs with Caddy access logs for edge-level disconnect detail.
  - NFS remains a shared backend dependency. The service split removes browse worker/proxy common-cause vectors but does not guarantee recovery from NFS stalls.
- **Follow-up packages/issues**:
  - Potential follow-up for non-NFS/object-storage archive publication if service telemetry shows NFS remains the main reliability limit.
  - Potential follow-up to migrate other exact non-transforming downloads after archive ZIP telemetry is clean.

## Sign-off

- **Security reviewer**: Codex implementation review, 2026-06-19
- **Package owner**: WEPPcloud operators, pending production rollout acknowledgment
