# Fork Omni Empty-State Conformance Fix

**Package ID**: SURF-04B-C1
**Status**: Closed (2026-08-11 00:50 UTC)
**Timezone**: UTC

## Overview

Three production forks of `histological-censer` failed on wepp1 because the
checked `skip_omni_scenarios_contrasts` path treated a legitimately absent
`_pups` directory as fatal. This package restores the unchanged SURF-04B
contract: optional Omni child workspaces may be absent, and a checked fork must
safely establish the required empty destination directories before success.

## Objectives

- Make missing `_pups` and `_pups/omni` ancestors a safe, idempotent creation
  case while preserving no-follow rejection of hostile existing entries.
- Add direct and orchestration regression evidence for absent, empty,
  populated, legacy, and hostile directory states.
- Correct the review governance that allowed security containment evidence to
  substitute for valid-state and user-experience evidence.
- Obtain independent correctness, QA, and security review before closure.

## Scope

### Included

- `wepppy/rq/project_rq_fork.py::_reset_fork_omni_directories` and focused RQ
  tests.
- SURF-04B user/developer documentation and incident retrospective.
- Contract-first, hardening, work-package, and security-review guidance needed
  to require valid-state/noninterference review evidence.
- Work-package tracking, validation, and review artifacts.

### Explicitly Out of Scope

- Fork UI/API fields, defaults, authorization, queue topology, or job wiring.
- Automatic Omni rebuilds or changes to Omni model semantics.
- Cleanup or reuse of the three partial production destinations.
- Production deployment or job retry without separate operator direction.

## Canonical Contract and Discrepancy

The accepted SURF-04B contract at
`docs/work-packages/20260806_fork_skip_omni_reset/artifacts/2026-08-06_contract_decision.md`
requires checked destinations to contain real empty `omni`,
`_pups/omni/scenarios`, and `_pups/omni/contrasts` directories, declares all
eight boolean combinations valid, and requires an idempotent reset. The
incident implementation instead required `_pups/omni` to preexist. This is a
conformance fix under `docs/standards/contract-first-change-standard.md`;
normative product intent is unchanged.

## Valid-State and Error Matrix

| Initial destination state | Classification | Required outcome | Evidence |
| --- | --- | --- | --- |
| `_pups` absent; feature never materialized | Valid normal state | Create real hierarchy and complete | Direct incident regression and orchestration test |
| Real `_pups` exists but `_pups/omni` is absent | Valid supported legacy/partial state | Preserve siblings and ancestor metadata; create nested hierarchy | Direct preservation test |
| Required hierarchy exists and is empty | Valid idempotent state | Remain real and empty on repeated reset | Double-invocation test |
| Exact reset targets are populated | Valid populated state | Empty exact targets; preserve unrelated siblings | Populated-target test |
| Ancestor/reset target is a symlink or special entry | Invalid hostile state | Fail explicitly without external mutation | Symlink/file/FIFO/socket and swap tests |

## Trigger and Failure Signature

- Host: `wepp1`
- Source run: `histological-censer`
- Jobs: `fd3ae74fa63044c291bf1bcc6364c567`,
  `fde6857b3f86408abec75f54a8f5b28c`, and
  `493227771e514c87a1655ec3c5454595`
- End times: 2026-08-10 21:28:02, 21:48:46, and 22:09:08 UTC
- Signature: `FileNotFoundError: [Errno 2] No such file or directory: '_pups'`
- User impact: three registered partial destinations and no completed fork.

Scope boundary: fix the confirmed missing-optional-ancestor failure without
changing fork inputs, outputs, queue behavior, or unrelated run-tree handling.

## Success Criteria

- [x] A checked fork with no source `_pups` completes and establishes the three
  required real empty destination directories.
- [x] Missing `_pups/omni` is created without deleting unrelated `_pups`
  siblings, and repeated reset is idempotent.
- [x] Existing symlink, file, FIFO, socket, or other special ancestors remain
  explicit failures and external targets remain untouched.
- [x] Direct helper tests and one orchestration test that keeps the failing
  directory helper real cover the incident.
- [x] Focused suite passes; repository-wide validation was attempted through
  both monolithic and canonical sharded runners, with unrelated test-isolation
  blockers documented below.
- [x] Correctness, QA, and security reviews have no unresolved medium/high
  findings.
- [x] Governance docs require valid-state, user-reachable-error, and security
  noninterference evidence.

## Security Impact and Review Gate

- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: the patch creates descriptor-relative directories in a
  run tree and must preserve the existing symlink/special-entry containment
  boundary.
- **Security review artifact**:
  `docs/work-packages/20260810_fork_omni_empty_state_fix/artifacts/2026-08-11_security_review.md`

## Hardening Hypothesis and Signals

- **Hypothesis**: safely creating missing real ancestors while retaining
  no-follow verification will reduce this exact failure signature to zero over
  30 days without increasing out-of-root mutations or false rejection of valid
  layouts.
- **Health signals**: zero new `FileNotFoundError('_pups')` fork failures; direct
  empty-state regressions remain green; fewer user retries.
- **Danger signals**: new symlink traversal findings, deletion of unrelated
  `_pups` siblings, silent fallback after malformed entries, or new valid-state
  failures.
- **Observation window**: 30 days after production deployment.
- **Temporary calluses introduced**: none. Safe creation is canonical behavior,
  not a retry, fallback, feature flag, or compatibility wrapper.

## Related Work

- **Originating package**:
  `docs/work-packages/20260806_fork_skip_omni_reset/`
- **Related hardening**:
  `docs/work-packages/20260802_omni_fork_symlink_retarget_hardening/`
- **Standards**: `docs/standards/contract-first-change-standard.md` and
  `docs/standards/hardening-lifecycle-standard.md`

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **Decision provenance captured**: yes; production incident and operator
  direction on 2026-08-10 PDT / 2026-08-11 UTC

## Rollback

The code patch is isolated to ancestor creation in one fork reset helper and can
be reverted without data migration. Rollback restores the known production
failure for missing optional ancestors, so deployment rollback is appropriate
only if the patch violates containment or preservation tests.

## Deliverables

- Reset-only descriptor-relative ancestor creation in
  `wepppy/rq/project_rq_fork.py`.
- 17 new direct/orchestration cases within the 102-test focused RQ module,
  covering valid, hostile, race, retry, and terminal behavior.
- Correctness, QA, and security review artifacts with no unresolved findings.
- Governance amendments requiring valid-state, user-reachable-error, direct
  boundary, and security noninterference evidence.
- Originating-package and user/developer documentation corrections.

## Closure Notes

**Closed**: 2026-08-11 00:50 UTC

The fork conformance defect is fixed and reviewed. The focused RQ module passes
102 tests. Correctness, QA, and security gates pass with no unresolved
findings; broad-exception enforcement, diff checks, and scoped documentation
lint also pass.

Repository-wide validation was attempted repeatedly and did not expose a fork
regression. A monolithic run reached 4,463 passed / 61 skipped before a
peakflow test failed to resolve an existing manifest through its leaked current
working directory; the exact test passes alone. The canonical two-shard runner
then produced 3,016 passed / 23 skipped in one clean shard and 2,220 passed / 32
skipped in the other before an opt-in real-WBT integration test ran and failed;
that exact test correctly skips when run alone without the opt-in flag. These
are confirmed cross-module test-isolation defects outside this package. The
hardening standard permits a documented external blocker at pre-handoff; this
package does not alter or hide either failure.

No production deployment, job retry, partial-destination cleanup, commit, or
push was performed.

**Lessons learned**: flag matrices are not state matrices. Security containment
evidence must prove it preserves absent/empty/populated/legacy valid states, and
orchestration tests must not mock the production failure boundary.
