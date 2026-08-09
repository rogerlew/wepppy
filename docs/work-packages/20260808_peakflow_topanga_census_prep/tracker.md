# Tracker - Prepare the Durable Topanga Peak-Flow Census

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-09 04:22 UTC
**Current phase**: Complete - preparation GO published
**Last updated**: 2026-08-09 06:22 UTC
**Next milestone**: Separate `20260809_peakflow_topanga_census_execution` package
**Security impact**: `high`
**Dedicated security review**: `yes`
**Security artifact**: `artifacts/20260809_security_review.md`

## Task Board

### Ready / Backlog

- None.

### In Progress

- None.

### Blocked

- [ ] Full Topanga matrix execution - intentionally prohibited within this
  closed package and authorized only after the separate execution package is
  created.

### Done

- [x] Two-package sequence accepted and preparation package scaffolded
  (2026-08-09 04:22 UTC).
- [x] Data-contract compatibility and regression plan written before code or
  schema edits (2026-08-09 04:39 UTC).
- [x] Phase 2A assumption inventory and reusable engine completed
  (2026-08-09 05:28 UTC).
- [x] Pilot and generated-output parity plus synthetic planning proved
  (2026-08-09 05:59 UTC).
- [x] Topanga plan frozen with 1,088 eligible and 32 excluded records
  (2026-08-09 06:09 UTC).
- [x] Security, code, QA, and disposition gates completed with GO
  (2026-08-09 06:22 UTC).

## Timeline

- **2026-08-09 04:22 UTC** - Package created; preparation and execution scopes
  separated.
- **2026-08-09 04:39 UTC** - Compatibility strategy, Phase 2A schema inventory,
  and generated-run regression checks frozen in
  `artifacts/data-contract-compatibility-plan.md`.
- **2026-08-09 05:59 UTC** - Bounded h106 execution reproduced Phase 2A trace
  and hillslope-pass hashes exactly.
- **2026-08-09 06:09 UTC** - Canonical plan
  `b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de`
  frozen without executing the census.
- **2026-08-09 06:22 UTC** - Preparation GO and immutable execution handoff
  published.

## Decisions Log

### 2026-08-09 04:22 UTC: Prepare first, execute separately

**Context**: The Phase 2A mechanics are proven, but the current orchestration
hard-codes Topanga paths, 140 hillslopes, an eight-hillslope selection, and a
64-trial assertion.

**Options considered**:

1. Patch the pilot script and immediately run Topanga - fastest initially but
   creates another site-specific workflow.
2. Prepare a durable engine and execute in the same package - fewer documents
   but allows implementation decisions to drift after outcomes exist.
3. Prepare and freeze first, then execute from a separate package - preserves
   reuse, preregistration, and a clean computational authorization boundary.

**Decision**: Use option 3. This package ends at a frozen, validated trial plan
and GO/NO-GO disposition. A separate package performs the full run.

**Impact**: No full-matrix mutation outcome may be produced during preparation.
The later execution package must consume the frozen plan unchanged.

## Risks and Issues

| Risk | Severity | Likelihood | Mitigation | Status |
| --- | --- | --- | --- | --- |
| Pilot-specific assumptions leak into reusable code | High | Medium | Synthetic second-site planning test and hard-code inventory | Closed |
| Plan changes after outcomes are visible | High | Low | Content-addressed frozen plan and separate execution package | Closed |
| Boundary cover values are clipped | High | Medium | Planner excludes with explicit reason; no clipping permitted | Closed |
| Existing pilot metrics drift during extraction | High | Medium | Full pilot parity gate before Topanga freeze | Closed |
| Unsafe manifest paths or binary execution | High | Medium | Canonical roots, no shell, binary hash pinning, security review | Closed |
| Partial execution is mistaken for complete | High | Medium | Terminal ledger completeness and fail-closed disposition | Closed |

## Verification Checklist

### Code and Data

- [x] Focused tests pass locally; canonical `wctl run-pytest` is blocked by the
  recorded container `/tmp` capacity condition.
- [x] Pilot parity and a synthetic second-site plan pass.
- [x] Schema validation and external artifact hashes pass.
- [x] Changed-file broad-exception enforcement passes.
- [x] Data compatibility and downstream propagation checks pass.

### Security

- [x] High security impact recorded for path and subprocess surfaces.
- [x] Dedicated security review has no unresolved medium/high findings.
- [x] Manifest paths are canonicalized and constrained to declared roots.
- [x] Subprocess execution uses argument arrays, no shell, and a pinned binary
  hash.

### Documentation

- [x] Package, tracker, active ExecPlan, and security review scaffold exist.
- [x] Study design, operator guide, and execution handoff are synchronized.
- [x] Documentation lint and spelling normalization pass.

## Progress Notes

### 2026-08-09 04:22 UTC: Package scaffold

**Agent/Contributor**: Codex

**Work completed**:

- Recorded the preparation-then-execution sequence.
- Defined the preparation boundary, durable-engine outcome, and security gate.
- Created an active ExecPlan that prohibits full-matrix execution.

**Next steps**:

- Execute the compatibility-plan milestone before editing schemas or code.

**Test results**: Documentation scaffold only; package and linked-document lint,
spelling preview, and root AGENTS size checks pass.

### 2026-08-09 06:22 UTC: Preparation closed with GO

**Agent/Contributor**: Codex

**Work completed**:

- Implemented the manifest-driven engine and explicit-selection CLI.
- Proved immutable and newly generated Phase 2A parity.
- Froze the Topanga plan and completed all review artifacts.
- Archived the completed ExecPlan under `prompts/completed/`.

**Next steps**:

- Create the separate execution package and consume the frozen plan unchanged.

**Test results**: 9 new and 5 existing focused tests pass locally; canonical
container pytest is blocked by the documented full `/tmp` condition. All other
acceptance gates pass.

## Watch List

- **Pilot immutability**: do not rewrite Phase 2A evidence to demonstrate parity.
- **No routing**: the reusable local census engine must not acquire watershed
  routing stages.
- **No early outcomes**: preparation may reuse pilot evidence and run synthetic
  fixtures, but may not execute new full-matrix Topanga trials.
