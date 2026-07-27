# Tracker - Authentication Session Persistence Hardening

## Quick Status

**Timezone**: UTC

**Started**: 2026-07-27 19:12 UTC

**Current phase**: Complete

**Last updated**: 2026-07-27 20:31 UTC

**Next milestone**: Production deployment and observation through 2026-10-25

**Security impact**: `high`

**Dedicated security review**: `yes`

**Security artifact**: `artifacts/2026-07-27_security_review.md`

## Task Board

### Done

- [x] Production evidence collected (2026-07-27 19:12 UTC).
- [x] Package, ExecPlan, contract decision, contract amendment, and ADR drafted
  (2026-07-27 19:12 UTC).
- [x] Initial dual checkpoint reviews completed with blocking findings
  (2026-07-27 19:29 UTC).
- [x] Operator made UX-first policy and copied-token residual-risk decision
  (2026-07-27 19:45 UTC).
- [x] Dual checkpoint reviews passed with no unresolved findings and the
  standalone checkpoint ancestor was committed as `4fd02a7e1`
  (2026-07-27 19:57 UTC).
- [x] Implemented remembered-login, logout, logging, rotation, and containment
  changes with regression coverage (2026-07-27 20:31 UTC).
- [x] Final security review passed with zero unresolved findings
  (2026-07-27 20:28 UTC).
- [x] Final correctness review passed with zero unresolved findings
  (2026-07-27 20:35 UTC).

## Timeline

- **2026-07-27 19:09 UTC** - Production inspection began on `wepp1`.
- **2026-07-27 19:12 UTC** - Package and contract checkpoint drafted.
- **2026-07-27 19:57 UTC** - Reviewed checkpoint committed at `4fd02a7e1`.

## Decision Log

### 2026-07-27 19:12 UTC: Separate active session from remembered identity

**Context**: Redis sessions expire after 12 hours, browser session cookies are
nonpermanent, and the configured remember default did not render checked.

**Decision**: Preserve rolling 12-hour Redis sessions and use an explicit,
opt-out, rolling 90-day browser inactivity cookie.

**Impact**: Active-session storage remains bounded; remembered identity becomes
durable for active users.

### 2026-07-27 19:12 UTC: Persist logs under `/wc1`

**Context**: Production runs as uid 1002. `/workdir/wepppy` and `/var/log` are
not writable, while `/wc1` is writable and host-mounted.

**Decision**: Use `/wc1/logs/weppcloud/security.log`.

**Impact**: The app can create the directory without a container privilege
change, and logs survive container recreation.

## Risks

| Risk | Severity | Mitigation | Status |
| --- | --- | --- | --- |
| Copied-token replay | High | Exposure controls, redaction, explicit residual-risk acceptance, and `fs_uniquifier` containment | Accepted |
| User opt-out ignored | High | Real endpoint-ordering and deletion regressions | Closed |
| Tokens remain in logs | High | Safe-field output and final-record sentinel tests | Closed |
| Persistent path unavailable | Medium | Mode/write/reopen tests plus wepp1 uid 1002 probe | Closed |
| Misleading cookie telemetry | Medium | Log `_remember` action, never cookie values | Closed |

## Checkpoint Review Disposition

| Finding | Disposition |
| --- | --- |
| CHK-SEC-01 / COR-01 / RER-COR-06 | Accepted-fixed: use opt-in-aware rolling refresh, document browser-only expiry, and accept copied-token replay with `fs_uniquifier` containment. |
| CHK-SEC-02 | Accepted-fixed in plan: require successful login, later-request, and logout response cookie assertions. |
| CHK-SEC-03 / COR-02 | Accepted-fixed in plan: allowlist diagnostics and assert unique secret sentinels are absent from final records across every input sink. |
| CHK-SEC-04 / COR-05 | Accepted-fixed in contract: append-only worker logging, host-coordinated rotation, restricted modes, and production-path validation. |
| CHK-SEC-05 / RER-COR-07 | Accepted-fixed: register REM-03 under GOV-00A-M1C with SURF-13, SHR-02, and SHR-04A plus exact boundary and exclusions. |
| COR-03 | Accepted-fixed: separate behavior rollback from durable logging; document already-issued cookie limitation and `fs_uniquifier` containment. |
| COR-04 | Accepted-fixed: retain the explicit duration override, disable unsafe global refresh, and implement opt-in-aware refresh. |
| RER-COR-08 | Accepted-fixed: reconcile policy, counts, authority links, timestamps, and progress metadata. |
| RER-COR-09 | Accepted-fixed: expand the normative conformance manifest and require reviewed `N/A` rationales plus regression runs. |

## Hardening Signal Log

- **Baseline**: 405 Redis sessions had TTL <=12 hours; login checkbox unchecked;
  file log disabled; CAPTCHA tokens present in container log.
- **Post-change**: 40 focused tests and 90 adjacent session tests pass; wepp1
  uid 1002 created, reopened, and removed a canonical-path probe.
- **Danger signals**: pending.
- **Temporary callus register**: none.

## Verification Checklist

- [x] Focused Python tests.
- [x] Template rendering test.
- [x] Security logging negative secret tests.
- [x] Configuration tests.
- [x] Documentation lint.
- [x] Broad exception enforcement.
- [x] Compose and logrotate configuration validation.
- [x] Dual final review.

## Progress Notes

### 2026-07-27 19:12 UTC: Discovery and checkpoint

Production inspection confirmed that configuration intent and rendered form
behavior diverged. It also exposed a broken file-log path and incomplete token
redaction. The operator authorized a work package and dual-agent verification.

### 2026-07-27 20:35 UTC: Implementation closeout

Implemented UX-led remembered login, real opt-out and logout boundaries,
secret-safe durable logging, host rotation policy, and per-user token
containment. Validation passed: 44 focused tests, 90 adjacent session tests, 15
JavaScript tests, documentation lint, broad-exception enforcement, logrotate
parsing, and the wepp1 uid 1002 canonical-path write/reopen probe. Both final
reviewers passed with no unresolved findings.

## Communication Log

### 2026-07-27 19:09 UTC: Operator authorization

**Participants**: WEPPcloud operator, Codex

**Outcome**: Implement the recommended persistence and logging fixes in a work
package and dispatch dual-agent review.
