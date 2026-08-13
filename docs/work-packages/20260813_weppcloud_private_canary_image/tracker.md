# Tracker – WEPPcloud private-canary image compatibility

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-13 19:36 UTC
**Current phase**: Publication evidence
**Last updated**: 2026-08-13 20:02 UTC
**Next milestone**: Push the branch, read back the private GHCR digest, and finalize the PR
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `docs/work-packages/20260813_weppcloud_private_canary_image/artifacts/2026-08-13_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Finalize security review and governance with GHCR readback.
- [ ] Open a ready-for-review PR and capture its URL.

### In Progress

- [ ] Commit and push the branch; capture workflow image tag/digest/privacy evidence.

### Blocked

- [ ] None.

### Done

- [x] Read repository, Docker/workflow, ExecPlan, and paired-package governance (2026-08-13 19:36 UTC).
- [x] Created branch `weppcloud-private-canary-image` from `2dedf916cb5ba430454dccc437ff0eb8fcb11daa` (2026-08-13 19:36 UTC).
- [x] Completed production inventory and compatibility matrix (2026-08-13 20:02 UTC).
- [x] Implemented the minimal-permission, full-SHA-pinned GHCR workflow and immutable build inputs (2026-08-13 20:02 UTC).
- [x] Built the common image and passed isolated Caddy + WEPPcloud + Redis runtime smoke checks (2026-08-13 20:02 UTC).
- [x] Proved protected production Compose/Caddy files have an empty baseline diff (2026-08-13 20:02 UTC).
- [x] Completed preliminary security and secret-sensitive diff review; final GHCR readback remains (2026-08-13 20:02 UTC).

## Timeline

- **2026-08-13 19:36 UTC** – Package created; non-live implementation began.
- **2026-08-13 20:02 UTC** – Local image build and isolated runtime compatibility passed; publication evidence began.

## Decisions Log

### 2026-08-13 19:36 UTC: Additive web-only compatibility surface

**Context**: Production Compose includes many auxiliary services, workers, persistent data, and secrets that are prohibited or unnecessary for this phase.

**Decision**: Add a standalone Caddy + WEPPcloud + ephemeral Redis smoke contract and leave every existing production Compose file untouched.

**Impact**: The phase can prove image and web-route compatibility without production mutation, Docker socket access, workers, or durable Redis.

### 2026-08-13 20:02 UTC: Pin publication inputs without changing Compose defaults

**Context**: The existing Dockerfile accepts sibling-repository refs but defaulted to branches and used floating base/installer inputs.

**Decision**: Add default-preserving Dockerfile arguments for base images, uv, and Rosetta, then supply digests/versioned URL/full Git SHAs only from the publication workflow.

**Impact**: Normal production Compose builds retain their current defaults. The publication run records substantially tighter immutable inputs and always reports the final manifest digest; Debian/DuckDB network resolution remains a documented non-hermetic limit.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Shared runtime image build regresses production consumers | High | Medium | Build common Dockerfile, retain default args, and record production-file hashes/diff | Mitigated; CI run pending |
| Workflow authority or tags are broader/mutable | High | Medium | Minimum permissions, full Action SHAs, commit tag, digest output, private package readback | CI readback pending |
| Flask startup requires more services/secrets than the minimum design | High | Medium | Synthetic inputs and `/dev/null` for legacy Discord import; PostgreSQL explicitly deferred | Mitigated/documented |
| Smoke stack accidentally includes workers/socket/public exposure | High | Low | Static assertions, rendered negative checks, loopback-only edge | Closed |

## Verification Checklist

### Code Quality

- [x] Focused tests pass.
- [x] Workflow and Compose lint/render checks pass.
- [x] No unpinned Actions or new dependency were introduced; existing npm findings recorded.

### Security

- [ ] Dedicated security review has no unresolved medium/high findings.
- [x] No production secret was accessed or retained.
- [x] Secret-sensitive diff review passes.

### Documentation

- [x] Compatibility inventory and matrix record exact contracts and evidence.
- [ ] Active ExecPlan and tracker reflect final state (publication/PR pending).
- [ ] Exact source SHA, image tag/digest, permissions, inputs, tests, and startup needs are recorded (GHCR digest pending).

### Testing

- [x] Additive Compose config renders.
- [x] Runtime smoke passes; first-start failures and resolutions are captured.
- [x] Protected production Compose files are byte-for-byte unchanged.

## Progress Notes

### 2026-08-13 19:36 UTC: Governance and baseline

**Agent/Contributor**: Codex

**Work completed**:

- Read applicable root, Docker, workflow, work-package, and ExecPlan instructions.
- Read the paired `open-wepp-org` package, tracker, security review, and dispatch.
- Confirmed a clean `master` baseline and created the authorized feature branch.

**Blockers encountered**: None.

**Next steps**: Finish the exact inventory, then implement the additive workflow and smoke harness.

**Test results**: No implementation tests run yet.

### 2026-08-13 20:02 UTC: Local implementation and validation

**Agent/Contributor**: Codex

**Work completed**:

- Added publication workflow, immutable build-input hooks, additive smoke Compose/Caddy configuration, static contract tests, inventory, and security review.
- Built a 2,663,253,220-byte local image and obtained local manifest digest `sha256:f70d212bd5d75ade2d183f807899bd00bf7f6c89b65029ae196dc53a1e626296`.
- Passed health, root, static, Redis, filesystem, port, socket, and teardown checks.

**Blockers encountered**:

- `wctl` is not installed on `dev-01`, despite the documented baseline. Focused checks ran directly and one pytest selection ran inside the built image.
- Initial web startup failed because a vendored Discord module opens a fixed token path; `/dev/null` satisfies the import without a credential.
- An internal-only network suppressed the host loopback publish; the final design attaches only Caddy to a loopback edge network while Redis/web remain on the internal backend.
- First GitHub run `31739044295` failed before compilation because `RUNTIME_BASE_IMAGE` was declared after the first Dockerfile stage and was blank in the second `FROM`; both base arguments were moved to global Dockerfile scope for the retry.

**Next steps**: Commit/push, observe GHCR workflow, verify privacy and digest, remove the transient feature-branch push trigger, finalize governance, and open the PR.

**Test results**: Local build pass; runtime smoke pass; static contracts 2 pass; focused pytest 1 pass/1 deselected; Caddy valid; protected diff and secret-pattern check pass. GitHub run `31739044295` failed with the exact global-ARG issue above; retry pending.

## Watch List

- **GHCR visibility**: workflow publication must not change repository/package settings; existing GitHub defaults must yield a private package.
- **Image size/build duration**: capture the precise failure if a complete build cannot finish on `dev-01`.
