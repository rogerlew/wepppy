# Security Review - CAP Runtime and Deployment Hardening

## Metadata

- **Package**:
  `docs/work-packages/20260825_cap_runtime_deploy_hardening/`
- **Reviewer**: Codex security reviewer (`cap_security_review`)
- **Date**: 2026-08-25
- **Scope reviewed**: CAP production image and server wrapper, upstream CAP token
  storage implementation, production Compose and wepp1 override, Caddy CAP
  proxy, `wctl` environment construction, production deploy script, existing
  CAP tests and documentation, and the proposed package/ExecPlan
- **Commit/branch context**: `075910aff`, local working tree before durable
  implementation
- **Related artifacts**:
  - Correctness review: pending
  - QA review: pending
  - Operations review: pending

## Security Triage Decision

- **Security impact level**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: The package changes a production secret ACL, introduces
  or invokes a privileged persistent-volume migration, and changes deployment
  acceptance for a public authentication dependency.
- **Threat model assumptions**:
  - Internet clients can call the public CAP challenge, redeem, health, and
    site-verification routes but cannot directly write the Docker named volume
    or host secret file.
  - The production host administrator and members of the Docker-controlling
    group are trusted and already have root-equivalent authority. A host-root
    compromise is out of scope.
  - CAP's unprivileged runtime is not trusted to prepare input for a later
    root migration. A CAP compromise could create hostile entries inside the
    writable CAP volume, so the migrator must treat volume contents as
    untrusted.
  - `tokensList.json` contains hashes and expirations for one-time CAP
    verification tokens, not WEPPcloud login sessions. Preserving it avoids
    invalidating in-flight CAPTCHA submissions; it does not require session or
    browser-cookie migration.
- **Valid states that controls must preserve**: a fresh absent token ledger; an
  empty CAP volume; a populated valid legacy root-owned ledger; a populated
  valid `10001:10001` ledger; and an already-canonical rerun. Unreadable
  secrets, unwritable volumes, symlinks, non-regular ledgers, malformed JSON,
  unexpected volume entries, and ambiguous host UID/ACL state must fail before
  public activation without changing contents.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | High | Token-ledger integrity and readiness | CAP can listen and return a healthy response even when token-store initialization failed. The upstream constructor starts `_loadTokens()` without awaiting it, catches the rejection, and converts read, parse, or write errors to empty in-memory state. Its nested catch can overwrite malformed populated JSON with `{}`. The wrapper's health route is unconditional. An unreadable or malformed ledger can therefore destroy active CAP state or leave redeem operations failing while deployment health is green. | `services/cap/server.js:58-62`, `services/cap/server.js:99-101`, `services/cap/node_modules/@cap.js/server/index.js:201-203`, `services/cap/node_modules/@cap.js/server/index.js:444-472`; the package requires an unwritable/malformed resource to fail explicitly. | Before constructing CAP or listening, validate that the data root is the exact expected directory, the optional ledger is a non-symlink regular file with valid object-shaped JSON, and the runtime identity can perform a create/fsync/remove probe in that directory without touching the ledger. Fence migration while CAP is stopped and compare a non-secret integrity marker before/after. Make readiness depend on completed validation; retain an opaque liveness response only if it cannot be mistaken for readiness. Add direct tests for unreadable, unwritable, malformed, symlink, fresh, empty, populated, and canonical states. | Open |
| SEC-02 | High | Deployment activation and public exposure | The planned public health check occurs after `docker compose up -d`, but Caddy currently starts when CAP is merely `service_started`; CAP has no Compose health check. Users can reach a broken CAP before the deploy script detects it, contradicting the package promise to fail before exposure. A post-start script failure reports damage but does not prevent it. | `docker/docker-compose.prod.yml:711-737`, `docker/docker-compose.prod.yml:748-758`, `scripts/deploy-production.sh:560-651`; Caddy proxies `/cap*` immediately in `docker/caddy/Caddyfile.wepp1:18-23`. | Add a bounded internal CAP readiness check and make Caddy activation depend on CAP being healthy, or explicitly stage CAP readiness before starting/restarting the public proxy. Then run the external `/cap/health` check as end-to-end confirmation. Failure must leave Caddy unexposed or restore the last known-good CAP path; add a rehearsal proving `/weppcloud/health` can be 200 while deliberately broken CAP prevents successful activation. | Open |
| SEC-03 | High | Privileged migration, ACL, and filesystem containment | The plan defers selection of the migration mechanism. A root helper that accepts arbitrary paths, recursively changes ownership, follows a symlink, or grants an ACL to an ambiguous host UID could convert a CAP runtime compromise or operator path mistake into host-file ownership changes or secret disclosure. The current plan's broad phrase “resource names/paths” is not a sufficient privilege boundary. | `cap_runtime_deploy_hardening_execplan.md:104-110` and `:207-214`; production mounts `cap-data` at `/var/lib/cap` and binds `docker/secrets/cap_secret`; image runtime is `10001:10001` in `services/cap/Dockerfile:23-32`. | Ratify the exact mechanism before implementation. The privileged step must be one-shot, network-disabled, mount only the named CAP volume at a fixed in-container path, receive no free-form host path/UID, and change only the volume root plus the one expected ledger entry without recursive traversal. Reject symlink/non-regular/unexpected entries before mutation. For the host secret, require a regular non-symlink file at the canonical path, verify parent/file ownership and POSIX ACL support, reserve/check UID `10001`, grant only that named UID read access, and assert no group/other effective read access. Record pre-state and make rollback/idempotence tests prove no content or unrelated metadata changed. | Open |
| SEC-04 | Medium | Secret source precedence | `server.js` prefers inline `CAP_SECRET` over `CAP_SECRET_FILE`. Thus a legacy host override silently bypasses the mounted-file contract, remains visible through container environment inspection, and can make ACL/readability validation a false assurance. A local ignored legacy worker env file contains inline secrets and is mode `0664`; it is not tracked, is not generated by current `wctl`, and the production incident proves the active CAP attempted `CAP_SECRET_FILE`, so there is no evidence of current production override or git-history exposure. | `services/cap/server.js:9-18`; `tools/wctl2/context.py:94-103` creates current temporary env files; `docker/README.md:336-355` says manual worker env files must be non-secret; `docs/infrastructure/secrets.md` requires file-backed secrets. | When `CAP_SECRET_FILE` is configured, require it and reject simultaneous inline `CAP_SECRET` instead of silently preferring the environment. Add a deploy/preflight assertion that the effective CAP service has the file path but no inline secret without printing either value. Add a sentinel test proving container inspection/config output contains only the path. Keep cleanup of ignored host-local legacy files as an explicit operator action, not a repository mutation. | Open |
| SEC-05 | Medium | Failure diagnostics and health exposure | The plan proposes bounded recent container logs on deployment failure but does not define how secret-bearing or request-bearing output is excluded. Blind `docker compose logs --tail` can publish application-controlled exception text into deployment logs. A deeper public readiness endpoint could likewise leak filesystem paths, ownership, or ACL detail if implementation returns diagnostic reasons. | `cap_runtime_deploy_hardening_execplan.md:120-127` and `:199-205`; current CAP secret-read failure logs an error object and path in `services/cap/server.js:11-16`. | Keep the public health response to a fixed minimal success/failure schema. Emit detailed reason codes only to local operator diagnostics, never request bodies, environment dumps, secret values, or unrestricted exceptions. If deploy automation prints logs, allowlist known CAP diagnostic codes or apply tested redaction with a secret sentinel; prefer service state and explicit preflight reason codes over arbitrary log tails. | Open |

Risk acceptance authority: `Accepted-risk` requires security reviewer
recommendation plus explicit package owner acknowledgment in Sign-off.

## Verdict

- **Gate status**: `fail`
- **Unresolved findings**:
  - Critical: 0
  - High: 3
  - Medium: 2
  - Low: 0
- **Release recommendation**: hold implementation and release until the three
  high findings are incorporated into the design and independently re-reviewed;
  repository policy also requires both medium findings closed before package
  closeout.

## Surface Checks

### 0) Valid-State Non-Interference and User Experience

- [ ] The pending correctness review enumerates absent, empty, populated,
  supported legacy, and hostile states.
- [ ] Security controls preserve every valid state's contracted user-visible
  outcome; implementation does not yet exist.
- [x] Fresh/absent and empty CAP state are explicitly valid in the ExecPlan.
- [ ] New exceptions are proven limited to malformed or hostile state.
- [ ] Direct unmocked tests exercise valid and hostile states.
- [x] This security review does not claim correctness or UX approval.

### 1) Auth, Session, and Authorization

- [x] The package explicitly excludes changes to CAPTCHA semantics, OAuth,
  Flask authentication, sessions, JWTs, and CSRF.
- [ ] Local-login CAP challenge/redeem/siteverify behavior remains functional
  after the changed persistence/readiness boundary.
- [ ] OAuth remains independent of CAP while local login fails closed during a
  CAP outage.
- [ ] Error paths are proven not to disclose CAP tokens or the verification
  secret.

### 2) Secrets and Credential Handling

- [x] The proposed design retains the mounted `CAP_SECRET_FILE` contract and
  does not add a new secret.
- [ ] The implementation rejects inline `CAP_SECRET` when the file contract is
  configured (SEC-04).
- [ ] The host ACL grants effective read access only to the intended CAP
  identity while preserving existing required consumers (SEC-03).
- [ ] Rotation and rollback preserve the existing secret value and do not copy
  it into the writable CAP data volume.
- [ ] Sentinel tests prove secrets do not enter argv, Compose output,
  inspection output, logs, or artifacts.

### 3) Input Validation and Output Safety

- [ ] Privileged helper inputs are fixed and reject arbitrary paths, UIDs,
  symlinks, non-regular files, and unexpected volume entries (SEC-03).
- [x] No HTML, markdown, URL fetch, deserialization, or shell-composed user
  input is added by the package.
- [ ] Validation failures return explicit non-secret reason codes.

### 4) File System and Run-Tree Boundaries

- [x] CAP data remains outside `/wc1/runs` in its dedicated named volume.
- [ ] Root migration mounts and mutates only the exact CAP named volume.
- [ ] No recursive ownership change or symlink traversal is possible.
- [ ] The ledger remains least-privilege, content-preserving, and
  integrity-checked through migration and rollback.

### 5) Queue, Worker, and Subprocess Surfaces

- [x] No RQ enqueue, dependency, cancellation, or worker task wiring changes
  are in scope.
- [ ] Failure and rollback leave unselected wepp2/wepp3 workers untouched.

### 6) Agentic Tooling and MCP Surfaces

- [x] No agentic tooling or MCP interface changes are in scope.
- [x] The proposed helper does not require network egress, public
  publication, or a Docker socket inside the helper container.

### 7) Network and External Integrations

- [x] CAP's existing public routes and Caddy proxy path are unchanged in
  purpose.
- [ ] Public activation is gated on internal readiness (SEC-02).
- [ ] Public health output remains fixed and non-diagnostic (SEC-05).
- [x] No new outbound runtime integration is proposed.

### 8) CI/CD and Supply Chain

- [x] The production Node base image is digest-pinned.
- [x] The upstream CAP source defaults to an immutable commit and the build
  verifies checked-out `HEAD` equals `CAP_REF`.
- [x] NPM runtime dependencies are integrity-locked and installed with
  `npm ci --omit=dev`.
- [x] No registry/Kubernetes workflow or new third-party dependency is
  proposed for `wepp.cloud`.
- [ ] Tests assert the effective production CAP reference remains immutable
  and the privileged migration image is the reviewed local build.

### 9) Data Integrity, Locking, and Concurrency

- [ ] CAP is quiesced before recording and changing ledger metadata (SEC-01).
- [ ] Fresh, empty, populated legacy, canonical, malformed, and hostile states
  have independent regression fixtures.
- [ ] A populated ledger's integrity marker is unchanged through forward
  migration, retry, and rollback.
- [ ] Startup cannot silently replace malformed or unreadable populated state
  with an empty ledger.

### 10) Logging, Monitoring, and Incident Readiness

- [x] The package identifies both observed EACCES signatures, CAP restart
  count, and public health as incident signals.
- [ ] Automated diagnostics cannot expose secrets or request tokens (SEC-05).
- [ ] CAP readiness failure has a stable, redacted operator reason code.
- [ ] Rollback is rehearsed after deliberate secret, volume, and readiness
  failure injection.
- [ ] The 14-day production observation window records restart growth,
  readiness failures, and EACCES recurrence without recording credentials.

## Validation Evidence

- Automated checks run before implementation:
  - `bash -n scripts/deploy-production.sh` - passed.
  - `npm test` under `services/cap` - 3 tests passed.
  - `wctl doc-lint --path
    docs/work-packages/20260825_cap_runtime_deploy_hardening/artifacts/2026-08-25_security_review.md`
    - passed before this evidence-only update and rerun after it.
- Manual/static checks run:
  - Confirmed CAP production runtime identity is `10001:10001` and the image
    build pins both its base image digest and upstream CAP commit.
  - Confirmed CAP has no Compose health check and Caddy waits only for
    `service_started` before proxying public CAP traffic.
  - Confirmed upstream token initialization is asynchronous and converts
    read/parse/write failure to empty state while the wrapper health endpoint
    remains successful.
  - Confirmed current `wctl` temporary env files use the operating system's
    secure temporary-file creation and are removed at process exit.
  - Confirmed the observed local legacy worker env is ignored rather than
    tracked; no git-history or current production-secret exposure claim is
    made from that file.

## Residual Risk

- **Accepted residual risks**:
  - None. This is a pre-implementation failing gate; risk acceptance is not
    recommended for SEC-01 through SEC-05.
- **Follow-up packages/issues**:
  - After findings are remediated, repeat this independent security review
    against the implementation, direct Compose tests, forest1 failure
    injection, and rollback evidence.
  - Operators should audit and remove ignored legacy env files containing
    inline secrets under the existing secrets-management policy. This local
    hygiene task must not print, commit, or silently delete their contents.

## Sign-off

- **Security reviewer**: Codex (`cap_security_review`), 2026-08-25
- **Package owner**: pending finding disposition and implementation
