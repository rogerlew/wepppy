# ExecPlan: Add Optional Fork Copy Skip for `wepp/runs` and `wepp/output`

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan is maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, fork users can choose a new checkbox in the fork console to skip copying `wepp/runs` and `wepp/output` contents while still creating those directories in the destination run. This reduces heavy copy time for large runs. Undisturbify forks remain optimized by skipping those directories as well.

Users can verify the behavior by submitting a fork with the new option, observing a successful job, then inspecting the destination run to confirm `wepp/runs/` and `wepp/output/` exist but do not contain copied baseline payloads.

## Progress

- [x] (2026-05-06 21:06 UTC) Created work package scaffold (`package.md`, `tracker.md`, and this active ExecPlan).
- [x] (2026-05-06 21:13 UTC) Added fork-console checkbox and payload field (`skip_wepp_runs_output`).
- [x] (2026-05-06 21:13 UTC) Added rq-engine route boolean parsing and enqueue argument wiring.
- [x] (2026-05-06 21:13 UTC) Extended RQ helper rsync exclude behavior and directory creation guarantees.
- [x] (2026-05-06 21:14 UTC) Updated schema-default endpoint metadata and defaults.
- [x] (2026-05-06 21:14 UTC) Added/updated focused tests.
- [x] (2026-05-06 21:14 UTC) Ran focused test validation (`90 passed`).
- [x] (2026-05-06 21:20 UTC) Executed subagent review passes, remediated findings, and recorded disposition artifact (`96 passed` rerun).

## Surprises & Discoveries

- Observation: Undisturbify already excludes `wepp/runs` and `wepp/output` from rsync via `_build_fork_rsync_cmd`.
  Evidence: `wepppy/rq/project_rq_fork.py` current exclude logic under `if undisturbify:`.
- Observation: Queue graph tooling detected expected drift after the enqueue argument list changed.
  Evidence: `wctl check-rq-graph` reported drift for `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md`; regeneration with `python tools/check_rq_dependency_graph.py --write` resolved it.

## Decision Log

- Decision: Introduce a dedicated payload flag for explicit copy skipping, independent from undisturbify.
  Rationale: Maintains backward compatibility and lets users request fast copy behavior without forcing undisturbify.
  Date/Author: 2026-05-06 21:06 UTC / Codex.
- Decision: Ensure skipped directories are created explicitly after rsync.
  Rationale: Matches user requirement and avoids downstream assumptions that directory paths exist.
  Date/Author: 2026-05-06 21:06 UTC / Codex.
- Decision: Return `skip_wepp_runs_output` in the fork response payload and include it in schema-default required success fields.
  Rationale: Keeps response self-describing and aligns endpoint contract discovery with actual behavior.
  Date/Author: 2026-05-06 21:14 UTC / Codex.
- Decision: Accept a remaining low-severity UI default-propagation test gap (route->dataset->JS) as deferred follow-up.
  Rationale: Core payload/route/worker contract paths are covered and validated; adding a dedicated UI harness test is useful but not required for correctness of this backend-driven feature change.
  Date/Author: 2026-05-06 21:20 UTC / Codex.

## Outcomes & Retrospective

Implementation, focused validation, and subagent review disposition are complete for this session. Reviewers surfaced medium/low coverage gaps; all medium findings were fixed in the same change set and retested.

## Context and Orientation

Fork UI and submit flow:

- `wepppy/weppcloud/templates/controls/fork_console_control.htm` renders form fields.
- `wepppy/weppcloud/static/js/fork_console.js` builds form payload and submits `/rq-engine/api/runs/<runid>/<config>/fork`.

Fork API and queue wiring:

- `wepppy/microservices/rq_engine/fork_archive_routes.py::fork_project` parses payload and enqueues `fork_rq`.
- `wepppy/microservices/rq_engine/schema_defaults_routes.py` declares discoverable request schema/default metadata.

Fork worker implementation:

- `wepppy/rq/project_rq.py::fork_rq` delegates to `wepppy/rq/project_rq_fork.py::prepare_fork_run`.
- `wepppy/rq/project_rq_fork.py::_build_fork_rsync_cmd` controls exclude rules.

Primary tests:

- `tests/rq/test_project_rq_fork.py`
- `tests/microservices/test_rq_engine_fork_archive_routes.py`
- `tests/microservices/test_rq_engine_schema_defaults_routes.py`

## Plan of Work

Implement a new optional boolean field (default false) across fork console submit payload, rq-engine payload parsing, and worker enqueue arguments. In the worker helper, treat the skip boolean as an additional trigger for excluding `wepp/runs` and `wepp/output` from rsync. After rsync completes, explicitly create `wepp/runs` and `wepp/output` directories when skip mode is active (including undisturbify paths) so directory existence is guaranteed.

Then update schema-default metadata and tests so behavior and discoverability remain aligned.

## Concrete Steps

Work from `/workdir/wepppy`.

1. Update UI template + JS payload submission.
2. Update rq-engine `fork_project` parser and queue enqueue argument list.
3. Update `fork_rq` and helper signatures/logic.
4. Update schema-default descriptor/request/defaults.
5. Update focused tests for helper, route, and schema defaults.
6. Run targeted tests.
7. Run subagent reviewers and publish a disposition file under package `artifacts/`.

## Validation and Acceptance

Acceptance criteria:

- Fork form sends both `undisturbify` and new skip flag when checkbox is toggled.
- Route enqueues `fork_rq` with the new boolean value.
- `_build_fork_rsync_cmd` excludes `wepp/runs` and `wepp/output` when either undisturbify or explicit skip is true.
- `prepare_fork_run` ensures `wepp/runs/` and `wepp/output/` exist in the new run when copy-skip is active.
- Targeted tests pass for changed files.

Executed validation:

- `wctl run-pytest tests/rq/test_project_rq_fork.py tests/microservices/test_rq_engine_fork_archive_routes.py tests/microservices/test_rq_engine_schema_defaults_routes.py`
- `wctl check-rq-graph` (then regenerate with `python tools/check_rq_dependency_graph.py --write`, then re-check)
- `wctl doc-lint --path docs/work-packages/20260506_fork_skip_wepp_copy`
- `wctl doc-lint --path docs/ui-docs/weppcloud-project-forking.md`
- `wctl doc-lint --path PROJECT_TRACKER.md`

## Idempotence and Recovery

The change is additive and backward-compatible. Existing callers that omit the new flag keep prior behavior. Directory creation uses `exist_ok=True`, so re-running fork logic in tests remains safe.

If queue-graph drift appears after future enqueue signature edits, run:

- `wctl check-rq-graph`
- `python tools/check_rq_dependency_graph.py --write`
- `wctl check-rq-graph`

## Artifacts and Notes

- Work package root: `docs/work-packages/20260506_fork_skip_wepp_copy/`
- Review disposition artifact path:
  `docs/work-packages/20260506_fork_skip_wepp_copy/artifacts/20260506_subagent_review_disposition.md`

## Interfaces and Dependencies

No new external dependencies are introduced. Existing fork API response keys remain compatible. The request schema grows by one optional boolean field and one resolved default entry.
