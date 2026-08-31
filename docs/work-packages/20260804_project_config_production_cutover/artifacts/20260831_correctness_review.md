# Correctness and User-Experience Review - WP12 Production Cutover

## Metadata

- **Package**: `docs/work-packages/20260804_project_config_production_cutover/`
- **Reviewer**: Codex promotion review, retaining independent prerequisite
  reviews
- **Date**: 2026-08-31
- **Scope reviewed**: exact-boundary merge, staged production rollout, legacy
  and project-owned reads, authorized writes, refresh, and rollback
- **Commit/branch context**: `feature/project-owned-config` at the final WP12
  pre-merge checkpoint
- **Canonical contracts**:
  `docs/schemas/project-owned-config-contract.md` and
  `docs/schemas/project-owned-config-implementation-roadmap.md`
- **Related QA/security artifacts**: `20260831_validation.md` and
  `20260831_security_review.md`

## User Outcome

- **User goal**: create, reopen, and run locale-aware projects while legacy
  projects continue to work, with an explicit reviewed capability refresh when
  eligible.
- **Success presented to the user as**: correct locale controls, successful
  authorized operations, diagnostic failures, and stable project provenance.
- **Failures that may reach the user**: explicit registry, ownership,
  authorization, stale-preview, unsupported-capability, provider, and job
  failure contracts already reviewed in prerequisite packages.
- **Partial-state behavior**: project-config apply uses lock/journal recovery;
  failed operations retain or reconcile a valid config/manifest pair and expose
  diagnostic status.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| No project config / feature never used | yes | Legacy `.cfg` opens with localized live authority where contracted | WP12D legacy reopen and full route suites |
| Eligible preset with absent capability graph | yes | Project current locale climate/land-cover authority only in the ratified schema-v1 projection scope | WP12D matrix and preset/capability tests |
| Stored schema-v2/v3 graph | yes | Stored authority remains readable and selections are preserved | WP12D reader-floor/rollback evidence |
| Current Builder schema-v3 project | yes | Explicit acknowledged same-locale refresh may append current authority | Forest refresh/apply/reopen evidence |
| Unsupported/malformed config or manifest | no | Fail closed with diagnostic error and no mutation/enqueue | Security/correctness regressions and full suites |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Registry/provider unavailable | expected operational failure | Diagnostic 503-style contract; no write | Canonical RQ error and Builder contracts |
| Missing/invalid identity | expected security rejection | Diagnostic forbidden/ownership failure | Auth and owner-token tests |
| Stale refresh preview | expected concurrency rejection | Explicit conflict; review again | Capability refresh contract |
| Unsupported locale/capability combination | expected validation rejection | Explicit unsupported selection; no enqueue | Registry and paired route/RQ tests |
| Worker/provider failure after enqueue | exceptional | Failed job with detailed status; consistent project pair | RQ recovery and Forest execution evidence |

## Review Checks

- [x] Canonical intent and exact promotion boundary are named.
- [x] Absent, populated, supported legacy, current stored, and hostile states
  are covered by retained reviews and final regression suites.
- [x] Input/flag combinations and stored/filesystem states are reviewed
  separately in WP11 and WP12D evidence.
- [x] Real Forest provider builds and rollback reads supplement unit/contract
  tests; mocks are not the sole provider-boundary proof.
- [x] Security controls preserve valid authenticated owner/Admin/Root and legacy
  states while rejecting malformed/unauthorized states.
- [x] Partial success, recovery, retry, and stale-preview behavior are explicit.
- [x] Existing legacy workflows were manually reopened and exercised.
- [x] Coverage claims name the five Builder locales and tested provider/mode
  dimensions rather than claiming every hypothetical combination.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Low | Type consumers | Public stub omitted an exported locale-projection helper | Scoped stubtest | Add exact signature and rerun direct tests | Resolved |
| COR-02 | Low | RQ evidence | Generated enqueue source line was stale; edge was unchanged | `wctl check-rq-graph` | Regenerate canonical artifacts | Resolved |

## Verdict

- **Gate status**: pass for merge; production acceptance remains conditional on
  exact-revision deployment and staged observation
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: ship to the WP12 staged production rollout
- **Reviewer sign-off**: Codex, 2026-08-31

