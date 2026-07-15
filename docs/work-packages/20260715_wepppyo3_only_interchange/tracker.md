# Tracker - WEPPpyo3-Only Interchange Cutover

## Quick Status

**Timezone**: UTC
**Started**: 2026-07-15 17:05 UTC
**Current phase**: Native API expansion
**Last updated**: 2026-07-15 17:15 UTC
**Next milestone**: Add five hillslope bulk writers plus TC_OUT to wepppyo3,
then implement the required-native WEPPpy boundary
**Security impact**: `low`
**Dedicated security review**: `no`
**Security artifact**: `N/A`

## Task Board

### Ready / Backlog

- [ ] Remove watershed Python report parser fallbacks.
- [ ] Remove hillslope Python report parser fallbacks.
- [ ] Remove the shared Python Parquet fan-in and watershed EBE raw parser.
- [ ] Rebuild/install native release and restart the stack.
- [ ] Run generated smoke, broad gates, and dual reviews.

### In Progress

- [ ] Implement five native hillslope bulk writers and native TC_OUT.

### Blocked

None.

### Done

- [x] Decision owner authorized native-only retirement, subagent dispatch, and
  local stack restart (2026-07-15 17:05 UTC).
- [x] Inventory identified 13 explicit parser fallbacks, one catalog fallback,
  five missing hillslope bulk writers, one missing TC_OUT writer, and one
  watershed EBE raw-`chan.out` parser (2026-07-15 17:15 UTC).
- [x] Freeze package, ADR, and ExecPlan contracts (2026-07-15 17:15 UTC).

## Timeline

- **2026-07-15 17:05 UTC** - Package opened from the AgFields fallback incident.
- **2026-07-15 17:15 UTC** - Discovery expanded the native API scope to five
  hillslope bulk writers and TC_OUT so the cutover removes Python writers too.

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
| An old worker imports a release missing one operation | High | Medium | Required-symbol preflight, provenance smoke, worker restart | Open |
| Removing dead parsers changes schema behavior accidentally | High | Low | Existing parity fixtures, schema snapshots, generated smoke | Open |
| Native failure leaves partial output | High | Low | Preserve temp/atomic publication and add exact regressions | Open |
| Scope expands into aggregation/export rewrites | Medium | Medium | Freeze parser/writer boundary in package and ADR | Mitigated |
| Missing direct native writers delay WEPPpy deletion | High | Medium | Land and test six APIs in wepppyo3 before facade cutover | Open |

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

- [ ] Focused interchange tests pass.
- [ ] Full WEPPpy pytest gate passes.
- [ ] Stub/API gates pass for changed public surfaces.
- [ ] wepppyo3 Rust and release Python tests pass.
- [ ] Broad-exception and code-quality observability run.

### Documentation

- [ ] ADR-0020 and ADR index are current.
- [ ] Interchange README/spec/plan describe native-only behavior.
- [ ] Work package, tracker, reviews, and root board are current.

### Runtime

- [ ] Installed release exposes the complete required symbol set.
- [ ] Local stack restart completes and workers load the intended artifact.
- [ ] Generated smoke completes with no fallback warning.
- [ ] Forced missing/stale API fails explicitly without partial publication.

### Reviews

- [ ] Independent code review complete.
- [ ] Independent QA/runtime review complete.
- [ ] No unresolved medium/high findings.

## Watch List

- Native symbol/provenance drift through 2026-08-14.
- Any reintroduction of Python WEPP text parsing in production modules.
