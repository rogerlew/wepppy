# Forked Batch Identity Normalization

**Status**: Closed (2026-07-16)
**Timezone**: UTC

## Overview

An interactive project fork on `wepp1` retained Batch Runner identity in its
root NoDb controllers. The ash route therefore accepted inputs but refused to
enqueue WATAR, returning `Set ash inputs for batch processing`. This package
repairs the affected run, provides a guarded reusable repair CLI, and changes
the canonical fork path so future interactive forks cannot inherit batch
identity or active batch execution metadata.

## Objectives

- Repair `subsequent-hotbed` on `wepp1` without rebuilding model inputs.
- Add a dry-run-first CLI with validation, timestamped backups, atomic writes,
  cache invalidation, and idempotent verification.
- Normalize root NoDb `_run_group` and `_group_name` during every interactive
  fork while leaving `_pups/` child workspaces unchanged.
- Remove copied batch `run_metadata.json` from the active destination root.
- Add exact regression coverage and complete code, QA, and security reviews.

## Scope

### Included

- `tools/repair_forked_run_identity.py` and focused tests.
- `wepppy/rq/project_rq_fork.py` destination identity normalization.
- Fork and operator documentation.
- A targeted production repair of `/wc1/runs/su/subsequent-hotbed` on `wepp1`.

### Explicitly Out of Scope

- Rebuilding WEPP, ash, climate, soils, or landuse inputs.
- Changing native Batch Runner leaf identity or behavior.
- Changing fork authorization, queue topology, UI, or API payloads.
- Deploying the permanent fork patch to production in this package.

## Stakeholders

- **Primary**: Alex and WEPPcloud operators running WATAR from interactive forks.
- **Reviewers**: WEPPpy RQ/NoDb maintainers and independent code/QA reviewers.
- **Security Reviewer**: Codex security review with independent QA evidence.
- **Informed**: Batch Runner maintainers.

## Success Criteria

- [x] The production run has timestamped backups and no active batch identity.
- [x] `Ash.run_group` is unset for `subsequent-hotbed` and the ash endpoint is
      eligible to enqueue WATAR.
- [x] The CLI is dry-run-first, scoped to one explicit run root, and idempotent.
- [x] Future interactive forks clear root controller batch identity and discard
      copied batch execution metadata without touching `_pups/`.
- [x] Targeted and full Python tests, documentation lint, and review gates pass.

## Parameterization ADR Gate

- **Parameterization change present**: no
- **ADR required**: no
- **ADR links**: N/A
- **Decision provenance captured**: yes; Roger Lew requested the repair and
  permanent fork normalization, and Codex is the implementer.

## Dependencies

### Prerequisites

- Existing project fork implementation in `wepppy/rq/project_rq_fork.py`.
- Existing NoDb cache invalidation in `wepppy.nodb.base.clear_nodb_file_cache`.
- Production access to `wepp1` and the canonical run root.

### Blocks

- Reliable use of WATAR and other interactive routes on forks sourced from
  Batch Runner leaves.

## Related Packages

- **Related**: [`20260506_fork_skip_wepp_copy`](../20260506_fork_skip_wepp_copy/package.md)
- **Related**: [`20260715_fork_console_status_backpressure`](../20260715_fork_console_status_backpressure/package.md)
- **Standard**: [`hardening-lifecycle-standard.md`](../../standards/hardening-lifecycle-standard.md)

## Timeline Estimate

- **Expected duration**: One focused implementation and production-repair session.
- **Complexity**: Medium.
- **Risk level**: High because the package mutates production NoDb files.

## Security Impact and Review Gate

- **Security impact triage**: high
- **Dedicated security review required**: yes
- **Triage rationale**: The CLI accepts filesystem paths and performs atomic
  mutation of run-scoped production state. The fork worker also mutates copied
  NoDb payloads.
- **Security review artifact**:
  `docs/work-packages/20260716_fork_batch_identity_normalization/artifacts/2026-07-16_security_review.md`

## Hardening and Callus Softening

- **Failure signature**: The ash route returned `Set ash inputs for batch
  processing` for primary run `subsequent-hotbed` because root NoDb payloads
  retained `_run_group: "batch"` and `_group_name:
  "nasa-roses-202606-psbs"` from source leaf `WA-10`.
- **Scope boundary**: Fix copied orchestration identity without changing model
  parameters, scientific inputs, native batch leaves, auth, or queue wiring.
- **Related prior hardening efforts**: Reuse atomic NoDb write precedent and the
  existing scoped cache invalidation contract; retain the current fork rsync
  path and status behavior.
- **Hypothesis**: If interactive forks clear copied batch identity before they
  are exposed, ash and other interactive routes will enqueue normally while
  native Batch Runner leaves remain unchanged.
- **Health signals**: WATAR eligibility, zero root controllers with batch
  identity, idempotent repeat repair, and passing fork regressions.
- **Danger signals**: `_pups/` mutation, model artifact drift, stale cache reads,
  partial writes, or normalization of non-batch group identity.
- **Observation window**: 14 days after the permanent patch reaches production.
- **Temporary calluses introduced**: Timestamped repair backups for the one
  production run; owner Codex/operator, retain through the observation window
  and remove only after operator review.
- **Callus softening hypothesis**: The manual CLI remains an operator recovery
  tool, but the one-run backup directory may be archived after 14 stable days.

## References

- `docs/ui-docs/weppcloud-project-forking.md`
- `wepppy/rq/project_rq_fork.py`
- `wepppy/microservices/rq_engine/ash_routes.py`
- `wepppy/nodb/base.py`

## Deliverables

- Guarded repair CLI and tests.
- Permanent fork normalization and regressions.
- Production repair evidence.
- Code, QA, and security review artifacts.

## Follow-up Work

- Deploy the permanent fork patch through the normal production release path
  when requested.
- Review the `subsequent-hotbed` timestamped backup after the 14-day observation
  window.

## Closeout

The production run was repaired and independently verified without rebuilding
scientific inputs or submitting WATAR. The final script remains staged on `wepp1`
and reports an idempotent zero-change dry-run. Permanent fork prevention is complete
locally, with 55 focused and 4,948 full-suite tests passing. Separate code and
QA/security reviews pass with no unresolved high or medium findings. Production
deployment of the permanent patch is deliberately outside this package.
