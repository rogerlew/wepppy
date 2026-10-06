# Correctness and User-Experience Review - Omni dynamic timeout

## Metadata

- **Package**: `docs/work-packages/20261006_omni_dynamic_timeout/`
- **Reviewer**: `/root/wrt02_contract_correctness`, independent correctness review
- **Date**: 2026-10-06
- **Scope reviewed**: WRT-02 contract, Omni scenario/contrast coordinators,
  timeout helper, RQ metadata/dependencies, focused tests, and live Redis evidence
- **Commit context**: checkpoint `3c8c9c622ce722180c837e641b6d3bfbe9d67df3`;
  implementation candidate `adff42d6d9e38f561d41cc681e89f3386ef888c0`
- **Canonical contract**:
  `docs/schemas/wepp-run-input-contract.md#omni-leaf-application-wrt-02`
- **Related artifact**: `20261006_security_review.md`

## User Outcome

- **User goal**: allow valid long-running continuous Omni scenario and contrast
  leaves to use the existing workload-derived watershed allowance.
- **Success presented to the user**: newly serialized leaves carry the WRT-01
  timeout and inspectable metadata; workflow topology and non-leaf timeouts are
  unchanged.
- **Failures that may reach the user**: malformed required workload fails
  explicitly before an affected graph or contrast hillslope rerun is created.
- **Partial-state behavior**: no affected child identity, parent job metadata,
  Redis graph, or new executable artifact is left by workload admission failure.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| No scenarios or contrasts | Existing workflow-specific state | Preserve existing return/error behavior without reading timeout workload | Existing empty-path tests in `tests/rq/test_omni_rq.py` |
| Populated but fully skipped | Yes | Do not read workload or enqueue leaves; preserve existing fixed compile/finalizer behavior where applicable | Scenario and contrast skip-trap regressions |
| Continuous workload above floor | Yes | Every scenario/contrast leaf receives calculated timeout and exact WRT-01 metadata | Focused tests and `live_rq.json` |
| Single storm | Yes | Preserve 43,200-second base timeout without WRT metadata | `_omni_timeout_options` single-storm regression |
| Existing queued/failed job | Yes | Do not mutate serialized timeout or retry automatically | WRT-02 contract and implementation scope |
| Malformed required continuous workload | No | Fail before affected child/parent/Redis/rerun mutation | Invalid scenario and contrast admission regressions |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Required workload malformed | Exceptional invalid state | Existing explicit WRT-01 validation failure | WRT-01/WRT-02 contract |
| Work is empty or fully current | Expected | Existing no-work behavior | WRT-02 forbids unused workload reads |
| Leaf exceeds allowance after deployment | Exceptional runtime state | Existing RQ timeout reporting | WRT-02 changes allowance only, not cleanup or error contracts |

## Generated Artifact Evidence Chain

| Stage | Expected semantics | Direct evidence | Result |
| --- | --- | --- | --- |
| User/request intent | Existing Omni selections determine leaves | Coordinator unit regressions | Pass |
| Reloaded persisted state | Climate years and watershed hill count use normal controllers | `_omni_timeout_options` controller-shaped test | Pass |
| Generated intermediate | No changed run-tree intermediate | Not applicable: enqueue-only change | N/A |
| Prepared/executable input | No changed model input | Contract and source review | N/A |
| Execution output | Serialized RQ timeout, metadata, and dependencies match WRT-02 | Candidate-bound `live_rq.json` | Pass |
| User-facing result | Existing `job_info` exposes unchanged lineage | `live_rq.json` readback | Pass |

- **Direct unmocked boundary**: real RQ serialization/fetch and `job_info`
  readback on a UUID-scoped Redis queue, followed by verified cleanup.
- **Actual-project/environment evidence**: production failure supplies diagnosis;
  execution of the patched workload awaits separately authorized deployment.
- **Highest completion claim supported**: implemented and locally validated.
- **Deployment/recovery still outstanding**: wepp1 deploy and named production
  rerun under the operator gate.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Fully skipped scenario | Initial evidence did not prove an all-skipped scenario avoided workload reads | Added skip-trap regression; focused suite `97 passed` | Add focused test | Resolved |
| COR-02 | Medium | Exact candidate evidence | Initial live artifact did not identify the source revision | `live_rq.json` records `adff42d6d9e38f561d41cc681e89f3386ef888c0` | Bind and rerun harness | Resolved |
| COR-03 | Low | Closure evidence | Candidate-bound `live_rq.json` must be retained | Included in closure change set | Retain artifact | Resolved |

## Verdict

- **Gate status**: pass
- **Unresolved findings**: Critical 0; High 0; Medium 0; Low 0
- **Release recommendation**: approve local package closure after the full-suite
  gate; deployment and production retry remain separate.
- **Reviewer sign-off**: `/root/wrt02_contract_correctness`, 2026-10-06

## Review Checks and Residual Limitation

The canonical contract, valid/invalid states, admission ordering, non-leaf
compatibility, partial-state behavior, queue graph, and status language were
reviewed. The live harness manually assembles the expected real-RQ graphs rather
than invoking the coordinators. This is accepted split proof with coordinator
tests: it proves serialization and topology but does not prove leaf execution or
scientific-output correctness. The full suite and production-equivalent
post-deployment rerun remain separate gates.

## Artifact Observability Gate

The changed artifact is RQ job serialization, visible through existing
`job_info`/dashboard authorization and retained as sanitized real-Redis evidence.
No new run-tree input, intermediate, output, or archive member is introduced;
scientific artifact archive/browser gates therefore do not apply.
