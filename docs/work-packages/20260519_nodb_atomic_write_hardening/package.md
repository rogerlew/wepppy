# NoDb Atomic Write Replace Hardening

**Status**: Closed (2026-05-20)  
**Timezone**: UTC

## Overview

This package addresses a production NoDb race observed on wepp1 where concurrent `omni` contrast jobs hit `JSONDecodeError` while reloading `omni.nodb`. The hardening scope is intentionally narrow: implement atomic file replacement in NoDb persistence so readers never observe a truncated or partially written JSON payload.

## Objectives

- Replace in-place truncate writes in `NoDbBase.dump()` with atomic temp-file + `os.replace` semantics.
- Preserve existing lock ownership and stale-writer signature contracts while changing write mechanics.
- Add focused regression coverage that exercises concurrent read/write boundaries around the atomic write path.
- Capture implementation and review evidence in package docs and artifacts.
- Require iterative review/disposition cycles until fixes are verified and no unresolved High/Medium findings remain.

## Scope

### Included

- `wepppy/nodb/base.py` write-path hardening in `NoDbBase.dump()`.
- Targeted test additions/updates in `tests/nodb/test_base_boundary_characterization.py` (or a tightly scoped companion test file in `tests/nodb/`).
- Package lifecycle docs (`package.md`, `tracker.md`, active ExecPlan, `PROJECT_TRACKER.md`) and review disposition artifact.

### Explicitly Out of Scope

- Decode retry/backoff behavior changes after read failure.
- Caller-layer retry policies in `omni` orchestration (`_update_contrast_dependency_tree`).
- Dependency-tree sharding or broader NoDb schema/layout changes.
- Queue orchestration redesign beyond NoDb write atomicity.

## Stakeholders

- **Primary**: NoDb maintainers, RQ maintainers, production operators.
- **Reviewers**: `reviewer` (correctness/race safety), `qa_reviewer` (test quality and maintainability).
- **Security Reviewer**: not required for this scoped reliability hardening.
- **Informed**: Omni workflow maintainers and incident responders.

## Success Criteria

- [x] `NoDbBase.dump()` writes through an atomic replace path rather than in-place truncate/write.
- [x] Post-write durability boundaries are explicit and verified by deterministic test evidence:
  - temp payload file fsync is invoked before replace,
  - parent directory fsync is invoked after replace,
  - concurrent-read boundary test demonstrates no empty/partial JSON payload visibility.
- [x] Existing stale-writer rejection behavior remains intact in targeted NoDb boundary tests.
- [x] New regression test(s) cover the empty/partial read hazard class and pass with the new implementation.
- [x] Package docs and tracker remain current, and independent `reviewer` + `qa_reviewer` findings are dispositioned in artifacts.
- [x] Iterative review loop is executed to closure:
  - each review round has a disposition entry,
  - every remediation round includes rerun validation evidence,
  - final round has zero unresolved High/Medium findings across both reviewers.

## Dependencies

### Prerequisites

- Existing NoDb boundary test scaffolding in `tests/nodb/test_base_boundary_characterization.py`.
- Current NoDb lock/signature behavior in `wepppy/nodb/base.py`.

### Blocks

- Follow-on retry hardening packages that depend on a stable atomic-write baseline.

## Related Packages

- **Depends on**: [20260425_nodb_atomicity_observability_followups_a](../20260425_nodb_atomicity_observability_followups_a/package.md)
- **Related**: [20260425_nodb_lock_dump_efficiency_refactor](../20260425_nodb_lock_dump_efficiency_refactor/package.md)
- **Follow-up**: potential decode-retry package for `getInstance()`/`load_detached()` read-transient handling.

## Timeline Estimate

- **Expected duration**: 1-2 focused sessions.
- **Complexity**: Medium.
- **Risk level**: High (core persistence path in a production-shared NoDb base class).

## Security Impact and Review Gate

- **Security impact triage**: `low`
- **Dedicated security review required**: `no`
- **Triage rationale**: this change is internal reliability hardening in NoDb persistence and does not introduce new external auth/input/egress surfaces.
- **Security review artifact**: `N/A`

## Hardening and Callus Softening (Required for incident/remediation packages)

- **Failure signature(s)**:
  - `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` during `Omni.getInstance()` decode.
  - Production evidence: failed RQ job `a3990dee-cdcc-4d55-9332-9103e6d9e28d` (`strategic-eloquence`) on wepp1 while sibling contrasts completed concurrently.
- **Related prior hardening efforts**:
  - `20260425_nodb_atomicity_observability_followups_a`
  - `20260425_nodb_lock_dump_efficiency_refactor`
- **Health signals**:
  - No reader-visible empty/partial JSON payloads under concurrent write/read tests.
  - No regression in stale-writer rejection and lock contracts.
  - Targeted Omni contrast completion no longer fails from transient decode windows caused by write truncation.
- **Danger signals**:
  - Accidental weakening of stale-write or lock ownership safeguards.
  - Atomic write implementation bypasses expected signature tracking.
  - New flaky timing assumptions in tests.
  - Review findings are acknowledged but not re-verified with rerun evidence.
- **Observation window**: package execution plus first post-merge production Omni contrast cycle.
- **Temporary calluses introduced**: none planned.
- **Callus softening hypothesis (if applicable)**: if atomic replacement removes transient decode races, decode-retry logic can remain optional rather than mandatory.

## References

- `wepppy/nodb/base.py`
- `tests/nodb/test_base_boundary_characterization.py`
- `wepppy/nodb/mods/omni/omni_state_contrast_mixin.py`
- `wepppy/nodb/mods/omni/omni_run_orchestration_service.py`
- `docs/standards/hardening-lifecycle-standard.md`

## Deliverables

- Atomic NoDb write/replace implementation in `NoDbBase.dump()`.
- Focused boundary regression tests for write/read race safety.
- Review disposition artifact under `docs/work-packages/20260519_nodb_atomic_write_hardening/artifacts/`.
- Iterative multi-round review/disposition artifacts showing closure verification.
- Updated package/tracker/ExecPlan + project tracker entries.

## Follow-up Work

- Optional follow-up package for bounded decode retry on read-transient failures.
- Optional Omni-specific retry hardening for dependency-tree update paths.

## Kickoff Prompt

- Active ExecPlan: `docs/work-packages/20260519_nodb_atomic_write_hardening/prompts/active/nodb_atomic_write_hardening_execplan.md`
