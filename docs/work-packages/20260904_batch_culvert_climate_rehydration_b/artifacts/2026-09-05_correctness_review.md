# Correctness and User-Experience Review - Batch and Culvert Climate Rehydration

## Metadata

- **Package**: `docs/work-packages/20260904_batch_culvert_climate_rehydration_b/`
- **Reviewer**: Codex (independent review pass)
- **Date**: 2026-09-05
- **Scope reviewed**: batch and culvert RQ Climate mutation boundaries,
  downstream RAP/OpenET/WEPP interchange consumers, tests, and Forest rollout
  contract
- **Commit/branch context**: `master` at `87559fe26`; implementation is an
  uncommitted working-tree change on Forest
- **Canonical contract(s)**:
  `docs/schemas/nodb-persistence-concurrency-contract.md` and
  `docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`
- **Related QA/security artifacts**:
  `artifacts/2026-09-05_qa_review.md` and
  `artifacts/2026-09-05_security_review.md`

## User Outcome

- **User goal**: Complete batch watershed and culvert runs when Climate state
  advances during earlier long-running stages.
- **Success presented to the user as**: Climate builds successfully and later
  RAP/OpenET/WEPP interchange stages consume the post-build Climate state.
- **Failures that may reach the user**: Existing explicit `FileNotFoundError`,
  decode/type/value errors for missing or malformed required Climate state, and
  the existing `NoDbStaleWriteError` for a genuine concurrent writer.
- **Partial-state behavior**: The existing root lock, atomic NoDb dump, status,
  and exception boundaries remain in place. No stale-controller retry or
  exception suppression was added.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Optional RAP/OpenET absent | yes | `tryGetInstance` returns `None`; batch continues without optional work | `tests/rq/test_batch_rq_retry_selection.py:763-828` |
| Optional RAP/OpenET empty | yes | Existing optional-controller behavior remains unchanged; no new hydration or error path | `wepppy/nodb/batch_runner.py:648-665` |
| Climate populated/current | yes | Clear exact cache entry, hydrate current state under climate root lock, build, return that controller | `tests/rq/test_climate_rehydration.py:106-129` |
| Supported legacy Climate state | yes | Existing legacy station-mode decoding remains accepted | `tests/rq/test_batch_rq_retry_selection.py:466-500` |
| Climate absent, empty, or malformed required state | no | Fail explicitly; never silently create valid state | `tests/rq/test_climate_rehydration.py:181-212` |
| Same-size intervening generation | valid concurrent event | Reject the stale early writer, then allow the mutation boundary to reload and persist current state | `tests/rq/test_climate_rehydration.py:51-129` |
| Hostile cache path | no | Canonical cache helper retains relative run-root validation; caller supplies fixed `climate.nodb` only | `wepppy/nodb/base.py:2853-2938` |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Optional RAP/OpenET controller absent | Expected | Batch proceeds without optional stage | Existing `tryGetInstance` contract is preserved |
| Climate file missing/empty/malformed | Exceptional | Existing explicit exception reaches the worker boundary | Required Climate state cannot be fabricated; regression covers both runners |
| Climate generation advances before the mutation boundary | Expected concurrent event | Fresh state is rehydrated and build proceeds | Exact scoped cache clear and root lock follow the `project_rq` precedent |
| True concurrent write during the locked mutation | Exceptional | Existing `NoDbStaleWriteError` remains visible | Strict persistence contract is intentionally unchanged |

## Review Checks

- [x] Canonical intent is named; implementation and tests are not treated as
  the authority for user behavior.
- [x] Absent, empty, populated, supported legacy, and hostile/invalid states
  are either tested or explicitly ruled out by the contract.
- [x] Input/flag combinations and stored/filesystem state combinations were
  reviewed separately.
- [x] Direct, unmocked tests exercise the real NoDb signature and file
  persistence boundary.
- [x] Mocks are limited to orchestration call-order and downstream identity
  proof; they do not replace the direct persistence test.
- [x] Existing partial-success, cleanup, locking, and exception semantics are
  preserved.
- [x] No user-visible contract or scientific parameterization changed.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Low | Repository-wide validation | Full suite stops on the pre-existing shape-converter compose contract mismatch; it is outside the changed files and does not affect the Climate tests. | `tests/shape_converter/unit/test_runtime_hardening.py::test_prod_wepp1_overlay_does_not_override_shape_converter_hardening`; committed `docker/docker-compose.prod.wepp1.yml` contains `shape-converter` | Record as a baseline deviation; do not broaden this package into shape-converter remediation | Resolved by disposition |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: `ship-with-conditions`: the successful Forest
  batch receipt is recorded; culvert full-workflow evidence is limited by
  existing missing-artifact and raster-shape fixture conditions, and the
  unrelated repository baseline remains separate.
- **Reviewer sign-off**: Codex, 2026-09-05
