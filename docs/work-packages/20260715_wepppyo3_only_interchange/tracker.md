# Tracker - WEPPpyo3-Only Interchange Cutover

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-15 17:05 UTC
**Current phase**: Broad validation and independent review
**Last updated**: 2026-07-15 17:54 UTC
**Next milestone**: Run repository-wide gates, complete dual reviews, and close
**Security impact**: `low`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [ ] Run repository-wide gates and dual reviews.

### In Progress

- [ ] Resolve and disposition any review findings.

### Blocked

None.

### Done

- [x] Decision owner authorized native-only retirement, subagent dispatch, and
  local stack restart (2026-07-15 17:05 UTC).
- [x] Inventory identified 13 explicit parser fallbacks, one catalog fallback,
  five missing hillslope bulk writers, one missing TC_OUT writer, and one
  watershed EBE raw-`chan.out` parser (2026-07-15 17:15 UTC).
- [x] Freeze package, ADR, and ExecPlan contracts (2026-07-15 17:15 UTC).
- [x] Add five native hillslope bulk writers, native TC_OUT, PASS hint discovery,
  and EBE raw-channel audit (2026-07-15 17:40 UTC).
- [x] Cut all production facades and query catalog scanning to required native
  operations; delete legacy parsers and fan-in (2026-07-15 17:42 UTC).
- [x] Build/install release SHA
  `92b180d5bc383165eb71e767285bfab1cd3ad24d48fe356145aef645bc185163`
  and restart the local stack (2026-07-15 17:48 UTC).
- [x] Pass 47-test focused suite, native release suite, exact-symbol/provenance
  checks, and generated H1 all-format smoke (2026-07-15 17:54 UTC).
- [x] Rewrite native ownership, failure, release, and test documentation
  (2026-07-15 17:50 UTC).

## Timeline

- **2026-07-15 17:05 UTC** - Package opened from the AgFields fallback incident.
- **2026-07-15 17:15 UTC** - Discovery expanded the native API scope to five
  hillslope bulk writers and TC_OUT so the cutover removes Python writers too.
- **2026-07-15 17:42 UTC** - Native API and WEPPpy facade cutover completed.
- **2026-07-15 17:48 UTC** - Local forest Python services restarted on the exact
  rebuilt extension; all ten RQ workers returned idle.
- **2026-07-15 17:54 UTC** - Generated Concept 2 H1 smoke converted all six
  hillslope formats through native writers with source-ordered row groups.

## Decisions Log

### 2026-07-15 17:05 UTC: Native failures are terminal

**Context**: A logged compatibility fallback still allowed a broken or stale
native release to complete through a materially slower and larger implementation.

**Decision**: Native import, symbol, parse, and write failures are terminal for
production interchange. Public WEPPpy wrapper APIs remain stable.

**Impact**: Deployments must install the matching owned native release before
workers start. Rollback restores the prior paired WEPPpy/wepppyo3 release, not a
runtime parser switch.

### 2026-07-15 17:15 UTC: Native ownership includes primary Parquet writing

**Context**: Five hillslope native APIs still returned column dictionaries to a
Python process-pool/PyArrow writer, and TC_OUT had no native API.

**Decision**: Add direct ordered multi-file native writers for hillslope PASS,
EBE, ELEMENT, LOSS, and SOIL plus a direct TC_OUT writer. Remove the shared
Python primary writer after the facades switch.

**Impact**: The native release must land first and preserve schemas, metadata,
empty output, row ordering, row groups, and atomic publication.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| An old worker imports a release missing one operation | High | Medium | Required-symbol preflight, provenance smoke, worker restart | Mitigated |
| Removing dead parsers changes schema behavior accidentally | High | Low | Existing parity fixtures, schema snapshots, generated smoke | Mitigated |
| Native failure leaves partial output | High | Low | Preserve temp/atomic publication and add exact regressions | Mitigated |
| Scope expands into aggregation/export rewrites | Medium | Medium | Freeze parser/writer boundary in package and ADR | Mitigated |
| Missing direct native writers delay WEPPpy deletion | High | Medium | Land and test six APIs in wepppyo3 before facade cutover | Closed |

## Hardening Signal Log

- **Baseline**: native failures log fallback and continue; generated Python WAT
  handoff peaked at 46,695,247,872 bytes.
- **Target**: zero fallback telemetry; missing/stale/failing native APIs raise
  before publication; generated native conversion completes.
- **Temporary callus register**: none.
- **Softening experiment**: remove the Python compatibility path under focused,
  broad, runtime, and dual-review gates.

## Verification Checklist

### Code Quality

- [x] Focused interchange tests pass.
- [ ] Full WEPPpy pytest gate passes.
- [x] Focused stub/API gates pass for changed public surfaces; package-wide
  stubtest baseline blocker is recorded in the ExecPlan.
- [x] wepppyo3 Rust and release Python tests pass.
- [x] Broad-exception gate passes; code-quality observability remains pending.

### Documentation

- [x] ADR-0020 and ADR index are current.
- [x] Interchange README/spec/plan describe native-only behavior.
- [ ] Work package, tracker, reviews, and root board are current.

### Runtime

- [x] Installed release exposes the complete required symbol set.
- [x] Local stack restart completes and workers load the intended artifact.
- [x] Generated smoke completes with no fallback warning.
- [x] Forced missing/stale API fails explicitly without partial publication.

### Reviews

- [ ] Independent code review complete.
- [ ] Independent QA/runtime review complete.
- [ ] No unresolved medium/high findings.

## Watch List

- Native symbol/provenance drift through 2026-08-14.
- Any reintroduction of Python WEPP text parsing in production modules.
