# ExecPlan: Automated RQ Dependency Graph Extraction and Drift Guardrails

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a contributor will be able to run one command, `wctl check-rq-graph`, and verify that RQ dependency documentation matches the enqueue logic in code. Today that graph is manually maintained and review-heavy. After this change, the graph will be generated from source code, written to a canonical artifact, rendered into the catalog, and checked for drift in automation.

The user-visible proof is straightforward: when queue wiring changes without regenerating the graph outputs, the check fails with a clear drift message; when graph outputs are regenerated, the check passes. This reduces regression risk in queue orchestration and makes dependency reviews faster.

## Progress

- [x] (2026-02-19 00:00Z) Converted this document from a mini work package format into an ExecPlan format aligned to `docs/prompt_templates/codex_exec_plans.md`.
- [x] (2026-02-19 00:00Z) Added a temporary root `AGENTS.md` pointer so agents could discover this ExecPlan as the active ad hoc plan during implementation.
- [x] (2026-02-19 04:52Z) Implemented `tools/extract_rq_dependency_graph.py`, generated `wepppy/rq/job-dependency-graph.static.json`, and added targeted parser/regression coverage in `tests/rq/test_dependency_graph_tools.py`.
- [x] (2026-02-19 04:56Z) Implemented `tools/render_rq_dependency_graph_docs.py`, inserted managed markers, and rendered the automated catalog block in `wepppy/rq/job-dependencies-catalog.md`.
- [x] (2026-02-19 05:01Z) Implemented `tools/check_rq_dependency_graph.py`, wired `wctl check-rq-graph`, and updated `tools/wctl2/tests/test_python_tasks_commands.py`.
- [x] (2026-02-19 05:08Z) Added opt-in runtime enqueue tracing in `wepppy/rq/auth_actor.py`, implemented `tools/export_rq_observed_graph.py`, and generated `wepppy/rq/job-dependency-graph.observed.json`.
- [x] (2026-02-19 05:28Z) Completed plan validation gates (`wctl run-pytest tests/rq -k dependency_graph`, `wctl run-pytest tools/wctl2/tests/test_python_tasks_commands.py`, `wctl check-rq-graph`, `wctl run-pytest tests --maxfail=1`, and doc lint), and finalized docs updates in `wepppy/rq/README.md` and `AGENTS.md`.
- [x] (2026-02-19 05:37Z) Removed the ad hoc active ExecPlan pointer from `AGENTS.md` after completion (`Current ad hoc active ExecPlan: none designated`).
- [x] (2026-02-19 05:43Z) Addressed post-review issues: made observed-graph drift checks time-stable, added enqueue trace de-duplication for `Queue.enqueue` delegation, and normalized host-side command examples to `python`.
- [x] (2026-02-19 06:18Z) Addressed follow-up review findings by expanding extractor coverage to include rq-initiated WEPPcloud route/bootstrap enqueue sites, refreshing generated artifacts, and reconciling catalog/ExecPlan wording.
- [x] (2026-02-19 06:24Z) Marked the work package complete after final review round, with all planned milestones implemented and validation gates passing.

## Surprises & Discoveries

- (2026-02-19 00:00Z) Observation: Existing queue-tree traversal already depends on `job.meta["jobs:*"]`, which means stage metadata can be extracted without adding a new metadata format.
  Evidence: `wepppy/rq/job_info.py` recursively scans `job.meta` keys beginning with `jobs:`.

- (2026-02-19 00:00Z) Observation: The current dependency catalog explicitly states manual maintenance and low testability, so automated extraction can directly address a known documentation gap.
  Evidence: `wepppy/rq/job-dependencies-catalog.md` documents manual derivation and cognitive review limits.

- (2026-02-19 05:28Z) Observation: Some rq-engine helpers enqueue through injected callable parameters (for example `job_fn`), so static extraction cannot always resolve a single concrete function name.
  Evidence: `wepppy/microservices/rq_engine/wepp_routes.py::_handle_run_wepp_request` and `wepppy/microservices/rq_engine/bootstrap_routes.py::_enqueue_no_prep_job` call `q.enqueue_call(job_fn, ...)`.

- (2026-02-19 05:28Z) Observation: The host shell in this environment does not expose `/opt/venv/bin/python`; direct script runs must use `python`, while canonical `/opt/venv/bin/python` execution remains available inside `wctl` container commands.
  Evidence: Running `/opt/venv/bin/python tools/extract_rq_dependency_graph.py --write` failed with “No such file or directory”, while `wctl` commands executed `/opt/venv/bin/python` successfully inside `weppcloud`.

- (2026-02-19 05:43Z) Observation: Wrapping both `Queue.enqueue` and `Queue.enqueue_call` without nesting guards can double-count observed events because `enqueue` delegates to `enqueue_call`.
  Evidence: Review identified duplicate trace potential at `wepppy/rq/auth_actor.py` wrapper sites.

- (2026-02-19 06:18Z) Observation: Restricting static extraction to only `wepppy/rq/*.py` and `wepppy/microservices/rq_engine/*.py` misses enqueue drift in rq-initiated Flask route handlers and bootstrap helpers.
  Evidence: Review identified enqueue sites under `wepppy/weppcloud/routes/**` and `wepppy/weppcloud/bootstrap/enable_jobs.py` that were outside prior `SOURCE_GLOBS`.

## Decision Log

- Decision: Treat the static graph artifact as the canonical CI input, and keep runtime-observed graph data optional.
  Rationale: Static extraction is deterministic and CI-friendly; runtime observations are valuable diagnostics but environment-dependent.
  Date/Author: 2026-02-19 00:00Z / Codex

- Decision: Keep the plan in `docs/mini-work-packages/` as an ad hoc ExecPlan instead of moving to `docs/work-packages/*/prompts/active/`.
  Rationale: Scope is substantial but still bounded and single-threaded; the user explicitly requested a mini-work-package-based ExecPlan.
  Date/Author: 2026-02-19 00:00Z / Codex

- Decision: Use sentinel markers inside `wepppy/rq/job-dependencies-catalog.md` and replace only that managed section.
  Rationale: This preserves analyst-authored narrative context while making graph content reproducible.
  Date/Author: 2026-02-19 00:00Z / Codex

- Decision: Preserve unresolved enqueue targets as symbolic labels (for example `job_fn`) instead of guessing branch outcomes.
  Rationale: Callable injection in route helpers is runtime-dependent; preserving symbolic labels is contract-preserving and avoids false precision in the generated graph.
  Date/Author: 2026-02-19 05:28Z / Codex

- Decision: Keep runtime observation capture append-only via JSONL (`/tmp/wepppy_rq_enqueue_trace.jsonl` by default) and generate the observed graph as a separate artifact.
  Rationale: Append-only tracing is low risk to queue behavior and keeps runtime diagnostics optional while static drift checks remain deterministic.
  Date/Author: 2026-02-19 05:28Z / Codex

- Decision: De-duplicate runtime trace recording by logging only at the outermost wrapped enqueue invocation.
  Rationale: This preserves optional tracing behavior while preventing inflated observed edge counts when `Queue.enqueue` delegates to `Queue.enqueue_call`.
  Date/Author: 2026-02-19 05:43Z / Codex

- Decision: Expand static extractor coverage to include `wepppy/weppcloud/routes/**/*.py` and `wepppy/weppcloud/bootstrap/*.py`.
  Rationale: Repository contracts require catalog/drift coverage for rq-initiated route handlers; including these globs closes a real drift-detection gap.
  Date/Author: 2026-02-19 06:18Z / Codex

## Outcomes & Retrospective

- (2026-02-19 05:28Z) Outcome: The full ExecPlan scope was implemented end-to-end. Contributors can now run `wctl check-rq-graph` to detect drift between enqueue wiring and generated graph artifacts, regenerate artifacts deterministically via `python tools/check_rq_dependency_graph.py --write`, and inspect optional runtime enqueue observations through `python tools/export_rq_observed_graph.py --write` when tracing is enabled.

- (2026-02-19 05:28Z) Outcome: The static extractor and renderer now provide a deterministic, reviewable dependency snapshot in `wepppy/rq/job-dependency-graph.static.json` and the managed catalog section in `wepppy/rq/job-dependencies-catalog.md`; the drift checker and `wctl` command wrapper passed targeted tests and runtime checks.

- (2026-02-19 05:28Z) Retrospective: Validation outcomes were strong (`wctl check-rq-graph` passed and `wctl run-pytest tests --maxfail=1` ended with `1725 passed, 27 skipped`). Remaining gaps are observational rather than functional: the observed graph artifact currently contains zero observations because no traced enqueue workload was executed during this run.
- (2026-02-19 05:43Z) Retrospective: Follow-up review findings were resolved by stabilizing observed-graph checks against timestamp-only drift and preventing duplicate enqueue trace rows for delegated `enqueue` calls; targeted dependency-graph tests remained green.
- (2026-02-19 06:18Z) Retrospective: A second review surfaced extraction-scope drift risk; widening source globs to include rq-initiated WEPPcloud handlers closed the coverage gap and kept check-rq-graph aligned with repository contracts.
- (2026-02-19 06:24Z) Retrospective: This work package is complete; remaining risk is limited to runtime observation depth until traced production-like workloads are captured.

## Context and Orientation

RQ (Redis Queue) orchestration in this repository is primarily defined in `wepppy/rq/*.py` with additional enqueue routes in `wepppy/microservices/rq_engine/*.py` and rq-initiated Flask handlers under `wepppy/weppcloud/routes/**/*.py` plus `wepppy/weppcloud/bootstrap/*.py`. A dependency edge means one enqueued job must wait for another job through `depends_on`, or is registered as a child through `job.meta["jobs:<order>,..."]`. The existing catalog at `wepppy/rq/job-dependencies-catalog.md` combines generated graph output with analyst-authored narrative.

Three tool layers already exist and should be reused. The `tools/` directory contains source-based guard scripts, for example route-inventory drift checks. The `tools/wctl2/commands/python_tasks.py` file exposes those checks as `wctl` commands. The `wepppy/rq/auth_actor.py` file already wraps queue enqueue methods, which is a natural insertion point for optional runtime dependency tracing.

The implementation must be additive and safe. No queue behavior changes are required for the static extractor. Runtime tracing must be opt-in and disabled by default.

## Plan of Work

Milestone 1 creates a static dependency graph extractor. The extractor will parse enqueue calls, normalize dependency expressions, and emit a stable JSON file at `wepppy/rq/job-dependency-graph.static.json`. It scans `wepppy/rq/*.py`, `wepppy/microservices/rq_engine/*.py`, `wepppy/weppcloud/routes/**/*.py`, and `wepppy/weppcloud/bootstrap/*.py`. This milestone includes tests that exercise common enqueue patterns in local fixtures so parser behavior remains stable.

Milestone 2 creates a documentation renderer that converts the static JSON graph into an auto-managed section inside `wepppy/rq/job-dependencies-catalog.md`. The renderer will replace only text between explicit markers, leaving all surrounding narrative untouched. This milestone makes graph output human-readable and reviewable in pull requests.

Milestone 3 introduces an enforcement check and CLI wrapper. The check script regenerates graph artifacts and fails when the working tree changes. The CLI wrapper adds `wctl check-rq-graph` so contributors and CI can run the same workflow. Command tests in `tools/wctl2/tests/test_python_tasks_commands.py` must be updated accordingly.

Milestone 4 adds optional runtime tracing. The enqueue wrapper in `wepppy/rq/auth_actor.py` will write parent-child enqueue observations when enabled by environment variable. A normalization script then emits `wepppy/rq/job-dependency-graph.observed.json` for diagnostics and reconciliation with static edges.

Milestone 5 performs validation and documentation hardening. This includes running targeted tests, updating `wepppy/rq/README.md` to describe the new workflow, and ensuring `AGENTS.md` guidance points contributors to the automated graph tools.

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Implement static extractor and tests.

       python tools/extract_rq_dependency_graph.py --write
       wctl run-pytest tests/rq -k dependency_graph

   The extractor command should print a short summary like “wrote N edges to wepppy/rq/job-dependency-graph.static.json”.
   Executed: `python tools/extract_rq_dependency_graph.py --write` regenerated the static edge artifact; `wctl run-pytest tests/rq -k dependency_graph` passed (dependency_graph selection).

2. Implement catalog renderer and refresh docs section.

       python tools/render_rq_dependency_graph_docs.py --write
       wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md

   The renderer should report which marker section was updated and how many nodes/edges were rendered.
   Executed: `python tools/render_rq_dependency_graph_docs.py --write` updated the managed marker section from the static graph artifact.

3. Implement drift check and CLI wrapper.

       python tools/check_rq_dependency_graph.py
       wctl check-rq-graph
       wctl run-pytest tools/wctl2/tests/test_python_tasks_commands.py

   On a clean tree this should exit zero. If outputs are stale, this must exit non-zero and list changed files.
   Executed: `python tools/check_rq_dependency_graph.py` and `wctl check-rq-graph` both exited zero; `wctl run-pytest tools/wctl2/tests/test_python_tasks_commands.py` passed (2 tests).

4. Implement optional runtime tracer and observed-graph export.

       WEPPPY_RQ_TRACE_ENQUEUE=1 python tools/export_rq_observed_graph.py --write

   This should create or update `wepppy/rq/job-dependency-graph.observed.json` with observed enqueue edges.
   Executed: `WEPPPY_RQ_TRACE_ENQUEUE=1 python tools/export_rq_observed_graph.py --write` wrote the observed graph artifact (0 observations in this run).

5. Run final validation pass.

       wctl run-pytest tests --maxfail=1
       wctl doc-lint --path docs/mini-work-packages/20260219_rq_dependency_graph_automation.md --path AGENTS.md --path wepppy/rq/job-dependencies-catalog.md

   Executed: `wctl run-pytest tests --maxfail=1` passed (`1725 passed, 27 skipped`); `wctl doc-lint --path AGENTS.md --path docs/mini-work-packages/20260219_rq_dependency_graph_automation.md --path wepppy/rq/job-dependencies-catalog.md --path wepppy/rq/README.md` passed (4 files validated).

## Validation and Acceptance

Acceptance is behavioral and must be demonstrated with commands and observable outcomes.

The first required behavior is deterministic generation. Running the extractor twice without code changes must produce identical static JSON output byte-for-byte. The second required behavior is documentation reproducibility. Running the renderer must update only the managed section in `wepppy/rq/job-dependencies-catalog.md`, and rerunning it immediately must yield no diff. The third required behavior is drift detection. If a contributor edits an enqueue dependency in source code and does not regenerate artifacts, `wctl check-rq-graph` must fail and identify stale outputs. The fourth required behavior is optional runtime visibility. With tracing enabled, runtime enqueue activity must produce observed edge records that include parent and child job identifiers.

## Idempotence and Recovery

All generator and check commands in this plan must be idempotent. Re-running the extractor, renderer, and check should not create additional drift when source code is unchanged.

If a command fails midway, fix the reported issue and rerun the same command; do not manually edit generated artifacts unless the generator logic is updated first. If runtime tracing causes unexpected overhead or log volume, disable it by unsetting `WEPPPY_RQ_TRACE_ENQUEUE` and rerun without tracing.

If a generated artifact is accidentally corrupted, restore it by rerunning the corresponding generator command rather than hand-editing the file.

## Artifacts and Notes

The static graph JSON should include records shaped like this:

    {
      "source_module": "wepppy/rq/wepp_rq.py",
      "source_function": "run_wepp_rq",
      "source_lineno": 516,
      "enqueue_target": "_prep_remaining_rq",
      "depends_on": ["jobs0_hillslopes_prep"],
      "job_meta_stage": "jobs:0",
      "queue_name": "default",
      "notes": []
    }

The catalog should contain explicit managed markers, for example:

    <!-- AUTO-GENERATED: RQ DEPENDENCY GRAPH START -->
    ... generated graph content ...
    <!-- AUTO-GENERATED: RQ DEPENDENCY GRAPH END -->

The check output should explicitly identify stale files, for example:

    RQ dependency graph drift detected:
    - wepppy/rq/job-dependency-graph.static.json
    - wepppy/rq/job-dependencies-catalog.md

## Interfaces and Dependencies

`tools/extract_rq_dependency_graph.py` must provide a CLI entrypoint with `--write` and `--check` modes and must exit non-zero on parser failures. It should expose an internal function that returns normalized edge dictionaries from repository source paths so tests can call it directly.

`tools/render_rq_dependency_graph_docs.py` must read `wepppy/rq/job-dependency-graph.static.json`, render deterministic Markdown, and replace only the section between sentinel markers in `wepppy/rq/job-dependencies-catalog.md`.

`tools/check_rq_dependency_graph.py` must orchestrate extractor plus renderer and fail when regeneration changes tracked files.

`tools/wctl2/commands/python_tasks.py` must register a new command named `check-rq-graph` that runs the check script in the container context, matching existing command style and return-code handling.

`wepppy/rq/auth_actor.py` must keep existing auth actor behavior intact while adding optional tracing hooks guarded by `WEPPPY_RQ_TRACE_ENQUEUE`. Tracing must not run unless the variable is set.

Revision Note (2026-02-19, Codex): Replaced the original mini-work-package checklist document with a full ExecPlan structure to satisfy `docs/prompt_templates/codex_exec_plans.md`, and aligned it with current repository RQ tooling and validation entry points.
Revision Note (2026-02-19 05:28Z, Codex): Updated this living ExecPlan after implementation to capture milestone-complete progress, runtime/tooling discoveries, decision rationales, and concrete validation evidence for all five milestones.
Revision Note (2026-02-19 05:37Z, Codex): Normalized living section entries to explicit UTC timestamps, documented removal of the temporary ad hoc pointer, and aligned timestamp formatting in `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective`.
Revision Note (2026-02-19 05:43Z, Codex): Applied follow-up review fixes for trace de-duplication and observed-graph check stability; updated host-executable command examples in `Concrete Steps`.
Revision Note (2026-02-19 06:18Z, Codex): Expanded extractor scope to include rq-initiated WEPPcloud route/bootstrap enqueue handlers, refreshed generated artifacts, and reconciled catalog/ExecPlan wording after another review round.
Revision Note (2026-02-19 06:24Z, Codex): Marked the ExecPlan complete after final review and validation confirmation.
