# Tracker - Dedicated Download Service for Critical Run Artifacts

> Living document tracking progress, decisions, risks, and communication for this work package.

## Quick Status

**Timezone**: UTC  
**Started**: 2026-06-19 16:52 UTC  
**Current phase**: Scaffolded / ready for implementation  
**Last updated**: 2026-06-19 16:52 UTC  
**Next milestone**: Inventory existing browse download/auth behavior and draft the extraction boundary.  
**Security impact**: high  
**Dedicated security review**: yes  
**Security artifact**: `docs/work-packages/20260619_dedicated_download_service/artifacts/20260619_security_review.md`

## Task Board

### Ready / Backlog

- [ ] Inventory current archive route behavior in `wepppy/microservices/browse/_download.py`.
- [ ] Identify the minimal shared auth/path resolver needed by both `browse` and the new download service.
- [ ] Implement a dedicated archive download service with `HEAD`, full `GET`, valid range, and invalid range handling.
- [ ] Add structured download logging and abort/error classification.
- [ ] Wire Docker Compose and Caddy for exact archive route cutover.
- [ ] Add focused unit/integration tests for auth, path safety, range behavior, and routing assumptions.
- [ ] Complete security review before production rollout.
- [ ] Capture local docker/Caddy smoke evidence and wepp1 rollout/rollback notes.

### In Progress

- [ ] None.

### Blocked

- [ ] None.

### Done

- [x] Scaffolded package, active ExecPlan, tracker, and initial security artifact. (2026-06-19 16:52 UTC)
- [x] Updated browse README with planned service boundary and target shape. (2026-06-19 16:52 UTC)

## Timeline

- **2026-06-19 16:52 UTC** - Package created from incident follow-up discussion about isolating critical archive downloads from browse.

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

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
|------|----------|------------|------------|--------|
| Auth behavior drifts between `browse` and `download`. | High | Medium | Share or faithfully extract current helpers; add auth/public/private tests. | Open |
| Caddy route matcher accidentally captures non-archive downloads. | High | Medium | Use exact archive matcher first; add negative smoke probes for schema, dtale, files, parquet CSV, culvert, and batch routes. | Open |
| Range support is implemented but not actually resume friendly in browsers. | Medium | Medium | Add `curl -H Range` tests plus browser/manual resume validation where practical. | Open |
| Byte/abort logging is incomplete because streaming responses hide disconnect details. | Medium | Medium | Instrument at the ASGI response layer or combine app logs with Caddy access logs; document limitations. | Open |
| NFS remains the bottleneck after split. | Medium | Medium | Treat split as isolation, not NFS remediation; collect service telemetry before considering object storage/local cache. | Open |

## Hardening Signal Log

- **Baseline health signals**: Browse previously showed high worker RSS before PyArrow-to-pandas remediation; operators still need clear bytes/duration/abort evidence for critical archive downloads.
- **Post-change health signals**: Pending implementation and rollout.
- **Danger signals observed**: None yet; scaffold only.
- **Temporary callus register**:
  - Exact archive route matcher, owner WEPPcloud operators, introduced with implementation, sunset/review after 14-day production observation.
- **Softening experiments**:
  - Hypothesis: If archive delivery is stable and route telemetry is clean, exact-route special cases can be simplified or expanded to other exact downloads under a follow-up package.
  - Gate results: Pending.
  - Decision: Pending.

## Verification Checklist

### Code Quality

- [ ] Focused tests passing (`wctl run-pytest <new download tests>`).
- [ ] Relevant microservice tests passing (`wctl run-pytest tests/microservices --maxfail=1` or narrower equivalent).
- [ ] Type checking clean if a new typed module surface is added (`wctl run-stubtest <module>`).
- [ ] No new security vulnerabilities.

### Security

- [x] Security impact triage recorded as high with rationale.
- [x] Dedicated security review artifact is present.
- [ ] No unresolved medium/high security findings remain in the security artifact.
- [ ] Attack-surface changes are explicitly reviewed.
- [ ] Residual risks and follow-up mitigation actions are recorded.

### Documentation

- [x] Browse README updated for the planned service boundary.
- [ ] New download service README added or equivalent operator docs updated.
- [ ] Work package closure notes complete.
- [x] Parameterization ADR gate recorded as not required.

### Testing

- [ ] Unit test coverage for full, `HEAD`, valid range, invalid range, missing file, unauthorized, public-run, and traversal cases.
- [ ] Integration or configuration tests for Docker/Caddy route assumptions.
- [ ] Manual smoke testing performed through local Caddy.
- [ ] Backward compatibility verified for non-migrated browse/download route families.

### Deployment

- [ ] Tested in `docker/docker-compose.dev.yml` environment.
- [ ] wepp1 rollout and rollback plan documented.
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

## Watch List

- **NFS dependency**: The split isolates process/proxy/common-cause issues but does not eliminate NFS as a shared backend.
- **Route precision**: Caddy matchers must keep transform downloads and grouped-run route families on browse until intentionally migrated.
- **Logging privacy**: Logs need operational evidence without exposing tokens, raw query filters, or sensitive full paths.

## Communication Log

### 2026-06-19 16:52 UTC: Target shape selected

**Participants**: Human operator, Codex  
**Question/Topic**: Whether to separate download from browse for critical reliability.  
**Outcome**: Scaffold the dedicated download service package around the target shape: browse remains interactive, download service handles exact archive delivery, and downloads get independent process controls plus range/resume-friendly observability.
