# Tracker – Topanga Peak-Flow Audit Phase 1

> Living record for Gates 0–2 implementation.

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-08 20:11 UTC
**Current phase**: Complete — Gates 0–2 passed
**Last updated**: 2026-08-08 22:00 UTC
**Next milestone**: Human review before any Phase 2 authorization
**Security impact**: `none`
**Dedicated security review**: `no`
**Security artifact**: N/A

## Task Board

### Ready / Backlog

- [ ] Import accepted compact regressions into openWEPP assurance ownership.

### In Progress

- [ ] None.

### Blocked

- [ ] Full Topanga census — intentionally blocked until Gates 0–2 pass and are
  reviewed.

### Done

- [x] Package, tracker, and active ExecPlan scaffolded (2026-08-08 20:11 UTC).
- [x] Authoritative local Topanga run and pinned source located (2026-08-08
  20:11 UTC).
- [x] Eleven Gate 0 schemas generated and validated (2026-08-08 21:05 UTC).
- [x] Compact 1980 Ksat fixture reconstructed and checked (2026-08-08 21:15 UTC).
- [x] Observational trace passes seven-file byte parity (2026-08-08 21:30 UTC).
- [x] Process-isolated APPMTH/HDRIVE replay matches both selected peaks exactly
  (2026-08-08 21:35 UTC).
- [x] 1986 canopy and ground-cover anomalies frozen as unresolved fixtures
  (2026-08-08 21:45 UTC).
- [x] Inactive version-9002 Ksat-factor control passes (2026-08-08 21:50 UTC).
- [x] Gates 0–2 evidence and investigation status synchronized (2026-08-08
  22:00 UTC).

## Timeline

- **2026-08-08 20:11 UTC** – Phase 1 work package opened.
- **2026-08-08 22:00 UTC** – Gates 0–2 passed; Phase 2 remains blocked.

## Decisions Log

### 2026-08-08 20:11 UTC: Diagnostic architecture

**Decision**: Observational WEPP runs the selected solver once and writes an
immutable event packet. All additional solver executions occur in a separate
process.

**Impact**: An executable that calls an extra `HDRIVE` inline cannot qualify as
logging-only evidence.

### 2026-08-08 20:11 UTC: Acceptance boundary

**Decision**: This package ends at Gate 2 and cannot authorize the census.

**Impact**: Phase 2 remains blocked even if candidate-screen tooling exists.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Logging changes legacy output | High | Medium | Exact/numeric parity policy and isolated worktree | Closed: byte parity |
| Event packet omits solver state | High | Medium | Selected-method replay is the packet completeness test | Closed: exact replay |
| Ksat mutant is not self-contained | High | Confirmed | Rebuild from burned deck and assert a one-token soil diff | Closed |
| Shared-state replay contaminates WEPP | High | Medium | Separate-process replay only | Mitigated by design |

## Discoveries

- **2026-08-08 20:15 UTC** – WEPPpy pins `jsonschema 3.2.0`, whose newest
  validator is Draft 7. Gate 0 uses Draft 7 rather than adding a dependency;
  the required grains and field constraints do not require newer vocabulary.
- **2026-08-08 20:35 UTC** – The accepted 1980 event used restrictive-layer
  record `1 10 0.0000108`. The synchronized project now contains the later
  no-restrictive-layer state, explaining why a direct copy initially missed
  the archived event values.
- **2026-08-08 20:40 UTC** – The `wepp_260803` sidecar identifies source commit
  `f24c957e…` on the default comparator line. Phase 1 acceptance uses that
  commit; `2f65506d…` remains historical trace provenance.
- **2026-08-08 21:35 UTC** – The two legacy APPMTH summaries have `v* = 1.3753`
  and `4.4017`; both are outside the documented domain. Harmonizing `remax` to
  the post-surplus forcing gives `0.7449` and `0.9026`.
- **2026-08-08 21:50 UTC** – Version-9002 `ksatfac` is a valid negative control:
  a one-token `1.3 → 9.3` change produced byte-identical canonical outputs.

## Verification Checklist

### Documentation

- [x] Package, tracker, ExecPlan, and investigation are synchronized.
- [x] Documentation lint passes.

### Testing

- [x] Schema tests pass.
- [x] Fixture checkers pass.
- [x] Reference/logging parity passes.
- [x] Selected-method offline replay passes.
- [x] Negative-control assertions pass.

## Progress Notes

### 2026-08-08 22:00 UTC: Gates 0–2 closure

**Agent/Contributor**: Codex

**Work completed**:

- Generated and validated eleven protocol schemas.
- Reconstructed the restrictive-layer 1980 Ksat fixture and froze both 1986
  anomaly lanes.
- Built the observational trace and proved seven-file byte parity with tracing
  disabled.
- Captured two immutable event packets and reproduced both selected peaks
  exactly in a standalone process.
- Passed the inactive version-9002 Ksat-factor negative control.

**Test results**:

- `wctl run-pytest tests/investigations` — passed.
- 1980 one-command fixture — passed (`47.709` and `92.716 mm/h`).
- 1986 fixture — passed (`3.563`, `294.416`, and `312.292 mm/h`).
- Ksat-factor negative control — seven canonical files byte-identical.
- Scoped documentation lint — zero errors and zero warnings.

**Next steps**:

- Hold Phase 2 until explicit human review and authorization.

### 2026-08-08 20:11 UTC: Package initialization

**Agent/Contributor**: Codex

**Work completed**:

- Read the work-package and ExecPlan standards.
- Located the burned and unburned Topanga Hill 106 decks under `/wc1/runs`.
- Confirmed the committed 1986 reproducer exists and the compact 1980 mutant
  still needs to be frozen.

**Next steps**:

- Finish Gate 0 schemas.
- Reconstruct and validate the Ksat-35 fixture.

**Test results**: discovery only.

## Watch List

- **Public reproducibility**: internal WEPP-Forest execution does not by itself
  satisfy a public rebuild requirement.
