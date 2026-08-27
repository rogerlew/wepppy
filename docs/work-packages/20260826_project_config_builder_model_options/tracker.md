# Tracker - Project Config Builder Model Options

## Quick Status

**Timezone**: UTC
**Started**: 2026-08-27 03:36 UTC
**Current phase**: Implementation validation
**Last updated**: 2026-08-27 04:42 UTC
**Next milestone**: Forest acceptance
**Security impact**: `low`
**Dedicated security review**: `no`
**Parameterization ADR**: `docs/adrs/ADR-0046-config-builder-wbt-and-wepp-260803-defaults.md`

## Task Board

### In Progress

- [ ] Run the ten-tuple Forest acceptance gate, including WBT Multiple OFE.

### Blocked

- None.

### Done

- [x] Recorded operator approval and scaffolded the package (2026-08-27 03:36 UTC).
- [x] Corrected and passed two independent contract reviews (2026-08-27 04:00 UTC).
- [x] Committed standalone checkpoint `95559bc6f` (2026-08-27 04:00 UTC).
- [x] Implemented registered Multiple OFE and WEPP binary components (2026-08-27 04:20 UTC).
- [x] Wired explicit WBT/`wepp_260803` defaults, dependency clearing, persistence,
  and Preview run-header maturity (2026-08-27 04:20 UTC).
- [x] Added generated-config, real binary execution, legacy-manifest, API, UI,
  and maturity tests (2026-08-27 04:30 UTC).
- [x] Passed independent implementation correctness review, conditional on
  Forest acceptance before exposure (2026-08-27 04:30 UTC).
- [x] Passed the full Python suite after isolating the project-creation fixture:
  6,962 passed and 63 skipped (2026-08-27 04:42 UTC).

## Decisions Log

### 2026-08-27 03:36 UTC: Registered compatibility, not filesystem discovery

**Decision**: Treat WEPP binaries as versioned registry components. The initial
set is `wepp_dcc52a6` for legacy parity and `wepp_260803` as the default for new
Builder projects. Multiple OFE requires both WhiteboxTools and `wepp_260803`;
Single OFE supports either binary and either delineation backend. WhiteboxTools
is the default backend.

**Rationale**: Registry-backed choices preserve deterministic schema revisions,
provenance, and server validation. Enumerating every executable present on one
host would make valid Builder payloads deployment-dependent. The operator
explicitly selected WhiteboxTools and `wepp_260803` as Builder defaults.

### 2026-08-27 04:00 UTC: Builder projects are Preview

**Decision**: Every project created from Config Builder has Preview interface
maturity, regardless of its representation. The run header derives this from
the project-owned manifest when the fixed config token is `config`.

**Rationale**: Builder is a new creation surface whose component matrix has not
completed production promotion. The fixed token cannot be registered as a
shared Interfaces preset.

## Compatibility and Data Impact

This is additive for Builder payloads and generated project config. Existing
project-owned runs and legacy Interfaces runs are not migrated. New Builder
submissions require `wepp_binary`; old stored manifests remain readable and
runnable, but update preview/apply is unavailable for pre-change Builder
manifests because their immutable parent chain has no binary component. The
generated `config.cfg` must contain the selected `[wepp] bin` and
`[wepp] multi_ofe` values, and the manifest must record both component
provenance entries.

## Valid-State Matrix

- Absent selection: new submissions fail with a field-addressable required-field error.
- Present-empty or unknown selection: fail without creating a run.
- Populated supported selection: resolve and persist exactly.
- Supported legacy run/manifests: remain readable and runnable, receive no
  migration, and report configuration update unavailable when their Builder
  parent chain predates the binary component.
- Hostile value: fail registry allowlist validation and never become a path or command.

## Communication Log

### 2026-08-27 03:36 UTC: Operator authorization

**Participants**: User and Codex
**Outcome**: The operator requested WhiteboxTools-only Multiple OFE, selected
WhiteboxTools and `wepp_260803` as defaults, classified every Builder project as
Preview, and confirmed governance-required reviewer delegation is standing
authority.

## Validation Evidence

- Focused Python: 83 passed before review hardening; post-review focused sets
  passed 53 tests plus the targeted legacy-manifest case.
- Frontend focused: 7 passed; full frontend: 107 suites, 792 tests passed.
- Frontend lint: passed.
- Stubtest: schema, resolver, and project-config reader passed; stub inventory passed.
- Broad-exception changed-file enforcement: passed with zero delta.
- Real WEPP execution: both `wepp_dcc52a6` and `wepp_260803`, watershed and
  hillslope binaries, completed the four-year `p1` fixture successfully.
- Full Python suite: 6,962 passed and 63 skipped in 678.16 seconds. The rerun
  passed after the project-creation fixture was made independent of the dev
  stack's enabled project-config writer flag.
- Forest ten-tuple and WBT Multiple OFE execution: pending; no exposure claimed.
