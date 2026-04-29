# WEPP Interchange Dependency Race Guard

**Status**: Closed (2026-04-29)
**Timezone**: UTC

## Overview
This package addresses an intermittent WEPP pipeline failure on wepp1 where `_build_hillslope_interchange_rq` failed while committing `H.wat.parquet.tmp` because `_post_watershed_interchange_rq` started concurrently and touched the same interchange directory. The objective is to remove this race by tightening RQ dependencies instead of adding timing delays.

## Objectives
- Serialize `_post_watershed_interchange_rq` after `_build_hillslope_interchange_rq` in WEPP pipelines that can run both paths.
- Preserve existing pipeline behavior and contracts outside the dependency ordering fix.
- Add regression tests proving the dependency edge in all affected enqueue helpers.
- Execute independent sub-agent implementation and QA/correctness reviews with recorded artifacts.

## Scope
This package is scoped to queue dependency wiring and required regression/docs updates for the confirmed race condition.

### Included
- Queue wiring in `wepppy/rq/wepp_rq_pipeline.py` for:
  - `enqueue_wepp_pipeline`
  - `enqueue_wepp_noprep_pipeline`
  - Dependency-identity verification in watershed-only helpers:
    - `enqueue_watershed_pipeline`
    - `enqueue_watershed_noprep_pipeline`
- Regression coverage updates in `tests/rq/test_wepp_rq_pipeline.py`.
- Queue dependency contract updates in `wepppy/rq/job-dependencies-catalog.md` and graph regeneration if needed.
- Sub-agent execution/review prompts and artifacts for code review + QA review.
- Package lifecycle docs (`package.md`, `tracker.md`, active ExecPlan, `PROJECT_TRACKER.md`).

### Explicitly Out of Scope
- Changes to interchange parser/writer internals (`wepppy/wepp/interchange/*`) beyond ordering safeguards.
- Changes to operational host tooling or runbook automation.
- Broader NoDb/RQ architecture redesign beyond this specific dependency race.

## Stakeholders
- **Primary**: RQ/WEPP pipeline maintainers and production operators.
- **Reviewers**: `reviewer` and `qa_reviewer` sub-agents (independent passes).
- **Security Reviewer**: required (queue-wiring attack-surface class).
- **Informed**: wepp1 operators tracking run reliability for short watershed runs.

## Success Criteria
- [x] `_post_watershed_interchange_rq` no longer starts before `_build_hillslope_interchange_rq` in affected pipelines.
- [x] Regression tests cover the new dependency edge(s) and pass.
- [x] `wctl check-rq-graph` passes and dependency docs are synchronized.
- [x] Sub-agent code review and QA review artifacts are completed with no unresolved medium/high findings.
- [x] Security review artifact is completed with gate status `pass`.

## Dependencies

### Prerequisites
- Existing queue helper patterns in `wepppy/rq/wepp_rq_pipeline.py`.
- Existing pipeline tests in `tests/rq/test_wepp_rq_pipeline.py`.
- Queue graph tooling (`wctl check-rq-graph`, `tools/check_rq_dependency_graph.py`).

### Blocks
- None currently identified.

## Related Packages
- **Related**: [20260427_wepp_runner_traceability_hardening](../20260427_wepp_runner_traceability_hardening/package.md)
- **Related**: [20260428_build_soils_rq_stale_cache_guard](../20260428_build_soils_rq_stale_cache_guard/package.md)

## Timeline Estimate
- **Expected duration**: 1-2 focused sessions.
- **Complexity**: Medium.
- **Risk level**: Medium-High (production queue topology change).

## Security Impact and Review Gate
- **Security impact triage**: `high`
- **Dedicated security review required**: `yes`
- **Triage rationale**: queue dependency wiring changes can alter execution ordering and failure boundaries in production worker paths.
- **Security review artifact**: `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/artifacts/2026-04-28_security_review.md`

## Hardening and Callus Softening (Required for incident/remediation packages)
- **Failure signature(s)**:
  - `FileNotFoundError: ... H.wat.parquet.tmp -> H.wat.parquet`
  - Failing job observed: `fd1cb34d-c6fc-4bea-a785-b2a094ab24bc` (`runid=predictive-refectory`, 2026-04-28 21:42 UTC).
- **Related prior hardening efforts**:
  - `docs/standards/hardening-lifecycle-standard.md`
  - `docs/work-packages/20260428_build_soils_rq_stale_cache_guard/package.md`
- **Health signals**:
  - No recurrence of interchange tmp-file commit failures for overlapping hillslope/watershed stages.
  - Dependency graph shows explicit `_post_watershed_interchange_rq` dependency on hillslope interchange.
- **Danger signals**:
  - New stalled/deferred jobs caused by incorrect dependency fan-in.
  - Regression in legacy pathways that expect watershed-only execution.
- **Observation window**: first production reruns on short/small watersheds after deployment.
- **Temporary calluses introduced**: none planned (ordering fix intended to be durable).
- **Callus softening hypothesis (if applicable)**: not applicable.

## References
- `wepppy/rq/wepp_rq_pipeline.py` - queue dependency definitions.
- `wepppy/wepp/interchange/versioning.py` - interchange directory refresh behavior.
- `tests/rq/test_wepp_rq_pipeline.py` - pipeline dependency regression tests.
- `wepppy/rq/job-dependencies-catalog.md` - documented enqueue dependency contract.
- `docs/prompt_templates/codex_exec_plans.md` - ExecPlan authoring standard.

## Deliverables
- Queue dependency fix + regression tests.
- Updated queue dependency catalog/graph artifacts.
- Sub-agent review artifacts:
  - `artifacts/2026-04-28_code_review.md`
  - `artifacts/2026-04-28_qa_review.md`
  - `artifacts/2026-04-28_security_review.md`
- Updated package lifecycle docs and tracker states.

## Closure Notes (2026-04-29 UTC)

### Delivered
- Added explicit dependency fan-in so `_post_watershed_interchange_rq` waits for both:
  - `_post_run_cleanup_out_rq`
  - `_build_hillslope_interchange_rq`
- Applied in:
  - `enqueue_wepp_pipeline`
  - `enqueue_wepp_noprep_pipeline`
- Added regression tests that lock dependency identity for all four helpers that enqueue `_post_watershed_interchange_rq`, including watershed-only helpers that correctly remain cleanup-only.
- Synchronized queue dependency artifacts:
  - `wepppy/rq/job-dependency-graph.static.json`
  - `wepppy/rq/job-dependencies-catalog.md`
- Completed independent review artifacts and dedicated security gate artifact.

### Validation Evidence
- `wctl run-pytest tests/rq/test_wepp_rq_pipeline.py --maxfail=1` -> `9 passed, 2 warnings`
- `wctl check-rq-graph` -> `RQ dependency graph artifacts are up to date`
- `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md --path docs/work-packages/20260428_wepp_interchange_dependency_race_guard --path PROJECT_TRACKER.md` -> `12 files validated, 0 errors, 0 warnings`
- `git diff --check` -> pass

### Review and Security Gates
- Code review artifact: `artifacts/2026-04-28_code_review.md` (`pass`, no findings)
- QA review artifact: `artifacts/2026-04-28_qa_review.md` (`closure-ready`, one medium finding resolved in-package)
- Security review artifact: `artifacts/2026-04-28_security_review.md` (`pass`, no unresolved medium/high findings)

### Residual Risk
- Accepted low residual risk: no integration-level concurrency replay in this package scope.

## Follow-up Work
- If additional races are observed in other enqueue paths, spin off a dedicated queue-serialization audit package rather than broadening this one.

## Kickoff Prompt
- Main execution prompt: `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/prompts/active/execute_wepp_interchange_dependency_race_guard_prompt.md`
- Archived ExecPlan: `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/prompts/completed/wepp_interchange_dependency_race_guard_execplan.md`
- Sub-agent prompts:
  - `prompts/active/subagent_worker_patch_prompt.md`
  - `prompts/active/subagent_reviewer_prompt.md`
  - `prompts/active/subagent_qa_reviewer_prompt.md`
