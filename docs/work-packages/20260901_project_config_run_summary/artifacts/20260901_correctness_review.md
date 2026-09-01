# Correctness and User-Experience Review - Project Config Run Summary

> Complete this artifact after implementation. Correctness review owns valid
> user states and user-reachable failure behavior.

## Metadata

- **Package**: `docs/work-packages/20260901_project_config_run_summary/`
- **Reviewer**: Independent Codex correctness reviewer
- **Date**: 2026-09-01
- **Scope reviewed**: Config Builder run-summary helper, active-root integration,
  run header, Config Summary modal, theme styles, and focused regressions
- **Commit/branch context**: `master`; contract checkpoint `790f34207` plus
  uncommitted implementation diff
- **Canonical contract(s)**:
  `docs/schemas/project-owned-config-contract.md`, sections 7.8 and 15
- **Related QA/security artifacts**: Security artifact N/A unless re-triaged

## User Outcome

- **User goal**: Quickly understand the current run's key configuration.
- **Success presented to the user as**: Locale pill plus an accessible six-row
  Config Summary modal.
- **Failures that may reach the user**: No new exception; missing or empty
  effective values render as `Not available`.
- **Partial-state behavior**: The modal retains all six rows; the locale pill is
  omitted only when locale is unavailable.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Summary context absent / non-target page | yes | No summary UI | Exact-stem helper/template tests |
| Summary present with an empty optional value | yes | `Not available`; all rows retained | Helper and template absent-state tests |
| Populated Config Builder run | yes | Pill and six accurate rows | Stored-authority helper and template tests |
| Supported legacy state | yes | Honest effective values; no registry-default substitution | Legacy-authority helper test |
| Malformed or hostile display value | no | Escaped, bounded rendering | NaN/empty helper and autoescaped template tests |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Optional summary value unavailable | expected | `Not available` | Approved section 7.8 policy |
| Summary context absent outside target surface | expected | Summary UI omitted | Package scope |
| Existing run-load failure | exceptional | Existing run-page behavior | No contract change intended |

## Review Checks

- [x] Canonical intent is named; implementation and tests are not treated as
  authority for user behavior.
- [x] Absent, empty, populated, supported legacy, and hostile states are tested
  or explicitly ruled out by the contract.
- [x] Input combinations and runtime state combinations are reviewed separately.
- [x] No mock replaces a changed production boundary.
- [x] Valid states remain compatible and hostile text remains contained.
- [x] Modal labeling, focus, dismissal, reflow, and error text are usable by
  existing modal behavior plus focused markup/theme evidence; live Config
  Builder modal smoke remains an environment-limited residual gap.
- [x] Existing user workflows remain compatible.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Dark themes | Pure CSS caption color would remain black on a dark surface | CSS review | Apply active theme tokens and focused assertion | Resolved |
| COR-02 | Medium | Route/context boundary | Initial tests did not prove nested/PUP active-root selection or denial ordering | Test review | Add direct active-root and authorization tests | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: `ship`
- **Reviewer sign-off**: Independent Codex reviewer, 2026-09-01
