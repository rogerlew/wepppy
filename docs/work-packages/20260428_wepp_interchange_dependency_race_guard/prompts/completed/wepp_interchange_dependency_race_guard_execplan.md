# WEPP Interchange Dependency Race Guard

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, WEPP pipelines that run both hillslope interchange and watershed/post-watershed stages will no longer allow `_post_watershed_interchange_rq` to run concurrently with `_build_hillslope_interchange_rq`. This removes the intermittent tmp-file deletion/commit race that currently appears as `FileNotFoundError` on `H.wat.parquet.tmp`. The result is visible by passing queue-dependency tests and a queue graph that explicitly enforces ordering.

## Progress

- [x] (2026-04-28 23:38 UTC) Created package scaffold and recorded incident signature.
- [x] (2026-04-28 23:38 UTC) Drafted initial tracker, scope, and security gate requirements.
- [x] (2026-04-28 23:54 UTC) Implemented dependency fan-in fix in `wepppy/rq/wepp_rq_pipeline.py` for affected helpers (`enqueue_wepp_pipeline`, `enqueue_wepp_noprep_pipeline`).
- [x] (2026-04-29 00:00 UTC) Added/adjusted regression tests in `tests/rq/test_wepp_rq_pipeline.py` proving dependency edges and helper identity coverage.
- [x] (2026-04-29 00:00 UTC) Ran queue dependency verification (`wctl check-rq-graph`) and synchronized graph/docs artifacts.
- [x] (2026-04-29 00:02 UTC) Completed independent sub-agent code review and QA review artifacts; resolved medium finding `QA-001`.
- [x] (2026-04-29 00:03 UTC) Completed dedicated security review artifact with gate status `pass`.
- [x] (2026-04-29 00:03 UTC) Closed package docs and archived ExecPlan under `prompts/completed/`.

## Surprises & Discoveries

- Observation: The race is amplified for very small watersheds because `run_watershed_rq` and `_post_run_cleanup_out_rq` can complete before hillslope interchange has finished writing `H.wat.parquet`.
  Evidence: production run `predictive-refectory` showed `_post_watershed_interchange_rq` start while `_build_hillslope_interchange_rq` was still running.

- Observation: Current pipeline wiring already models one similar safety edge (`_run_hillslope_watbal_rq` depends on both post dependencies and hillslope interchange), so this package can follow an established dependency-fanin pattern.
  Evidence: `wepppy/rq/wepp_rq_pipeline.py` existing `watbal_dependencies.append(job2_hillslope_interchange)` usage.

- Observation: `enqueue_watershed_pipeline` and `enqueue_watershed_noprep_pipeline` do not enqueue `_build_hillslope_interchange_rq`; they can only assert cleanup dependency identity in scoped unit tests.
  Evidence: `wepppy/rq/wepp_rq_pipeline.py` helpers accept `has_hillslope_outputs` but never enqueue hillslope interchange jobs.

## Decision Log

- Decision: Fix by dependency graph ordering, not delay/sleep heuristics.
  Rationale: deterministic and testable; avoids new timing knobs tied to watershed size.
  Date/Author: 2026-04-28 / Codex

- Decision: Keep scope limited to queue wiring + tests + queue contract docs.
  Rationale: incident-driven mitigation with minimal blast radius and fastest confidence path.
  Date/Author: 2026-04-28 / Codex

- Decision: Require independent `reviewer` and `qa_reviewer` artifacts before closure.
  Rationale: user explicitly requested sub-agent code + QA reviews.
  Date/Author: 2026-04-28 / Codex

## Outcomes & Retrospective

Closed with deterministic serialization in all affected helpers and regression/doc/review gates complete.

Delivered:
- `_post_watershed_interchange_rq` now depends on both cleanup and hillslope interchange in:
  - `enqueue_wepp_pipeline`
  - `enqueue_wepp_noprep_pipeline`
- Regression tests now assert dependency identity for all helpers that enqueue `_post_watershed_interchange_rq`.
- Queue dependency graph and catalog were synchronized and validated.
- Independent `reviewer` and `qa_reviewer` artifacts were completed; QA medium finding `QA-001` was resolved.
- Dedicated security review completed with gate status `pass`.

Validation:
- `wctl run-pytest tests/rq/test_wepp_rq_pipeline.py --maxfail=1` -> `9 passed, 2 warnings`
- `wctl check-rq-graph` -> up to date
- `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md --path docs/work-packages/20260428_wepp_interchange_dependency_race_guard --path PROJECT_TRACKER.md` -> `12 files validated, 0 errors, 0 warnings`
- `git diff --check` -> pass

## Context and Orientation

The queue wiring lives in `wepppy/rq/wepp_rq_pipeline.py`. Four helpers can enqueue `_post_watershed_interchange_rq`: `enqueue_wepp_pipeline`, `enqueue_wepp_noprep_pipeline`, `enqueue_watershed_pipeline`, and `enqueue_watershed_noprep_pipeline`. In all current variants, that stage depends only on `_post_run_cleanup_out_rq`, which allows overlap with `_build_hillslope_interchange_rq` whenever hillslope interchange is still running.

`_post_watershed_interchange_rq` calls watershed interchange code that may reset the interchange directory when the version manifest is missing or incompatible. Hillslope interchange writes `H.wat.parquet` through a tmp file and only writes the manifest after successful completion. That ordering allows destructive overlap under current queue dependencies.

Tests for pipeline dependency wiring live in `tests/rq/test_wepp_rq_pipeline.py`. Queue dependency contract docs live in `wepppy/rq/job-dependencies-catalog.md`, and queue graph verification is run through `wctl check-rq-graph`.

## Plan of Work

Apply a small wiring change: wherever `_post_watershed_interchange_rq` is enqueued in paths that also have a hillslope-interchange job reference, extend `depends_on` to include both cleanup and hillslope interchange. Use list fan-in in the same style as existing watbal dependencies.

Then update `tests/rq/test_wepp_rq_pipeline.py` to assert this dependency relationship in each affected helper. Keep assertions strict enough to prevent accidental reversion to cleanup-only dependencies.

After code/tests, run queue graph verification. If drift is reported, regenerate graph artifacts with `python tools/check_rq_dependency_graph.py --write` and synchronize `wepppy/rq/job-dependencies-catalog.md` with the new edges.

Finally, run sub-agent reviews:
- `reviewer` for correctness/regression risk findings.
- `qa_reviewer` for test sufficiency and validation-quality findings.

Record findings/resolutions in `artifacts/2026-04-28_code_review.md` and `artifacts/2026-04-28_qa_review.md`, then complete `artifacts/2026-04-28_security_review.md`.

## Sub-Agent Execution Model

1. Code implementation sub-agent (`worker`)
   - Prompt file: `prompts/active/subagent_worker_patch_prompt.md`
   - Output: code/test patch touching only scoped files.

2. Correctness review sub-agent (`reviewer`)
   - Prompt file: `prompts/active/subagent_reviewer_prompt.md`
   - Output: finding list with severity and required actions.

3. QA review sub-agent (`qa_reviewer`)
   - Prompt file: `prompts/active/subagent_qa_reviewer_prompt.md`
   - Output: test matrix sufficiency findings and closure recommendation.

All medium/high findings from reviewer and QA reviewer must be resolved or explicitly risk-accepted in artifacts before package closure.

## Concrete Steps

Run from `/workdir/wepppy`.

1. Implement dependency wiring updates in:
   - `wepppy/rq/wepp_rq_pipeline.py`

2. Update regression tests in:
   - `tests/rq/test_wepp_rq_pipeline.py`

3. Validate queue wiring and docs:
   - `wctl run-pytest tests/rq/test_wepp_rq_pipeline.py --maxfail=1`
   - `wctl check-rq-graph`
   - if drift: `python tools/check_rq_dependency_graph.py --write`
   - `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md --path docs/work-packages/20260428_wepp_interchange_dependency_race_guard --path PROJECT_TRACKER.md`
   - `git diff --check`

4. Complete review artifacts:
   - `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/artifacts/2026-04-28_code_review.md`
   - `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/artifacts/2026-04-28_qa_review.md`
   - `docs/work-packages/20260428_wepp_interchange_dependency_race_guard/artifacts/2026-04-28_security_review.md`

5. Update lifecycle docs and archive this plan to `prompts/completed/` at closure.

## Validation and Acceptance

Acceptance requires all items below:
- `_post_watershed_interchange_rq` dependency fan-in includes hillslope interchange job for every affected pipeline helper.
- Updated pipeline tests pass and explicitly verify the new dependency relationships.
- Queue graph check passes, and queue dependency docs are synchronized.
- Reviewer + QA reviewer artifacts show no unresolved medium/high findings.
- Security artifact gate status is `pass`.

## Idempotence and Recovery

The change is additive and safe to rerun. If tests or queue graph checks fail:
- revert only the affected dependency-edge edits,
- restore passing tests before broadening,
- rerun `wctl check-rq-graph` after each dependency update,
- keep tracker and artifact logs current with failure details and next attempts.

## Artifacts and Notes

Required closure artifacts:
- `artifacts/2026-04-28_code_review.md`
- `artifacts/2026-04-28_qa_review.md`
- `artifacts/2026-04-28_security_review.md`
- Validation summaries in `tracker.md` and `package.md`.

## Revision Notes

- 2026-04-28: Initial ExecPlan authored during package preparation.
- 2026-04-29: Finalized outcomes, validation evidence, and closure state before archive.
