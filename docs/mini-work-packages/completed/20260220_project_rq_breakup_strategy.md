# ExecPlan: Break Up `wepppy/rq/project_rq.py` While Preserving Contracts

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept current as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, `wepppy/rq/project_rq.py` remains the stable public import surface, but its largest internal responsibility clusters are split into focused sibling modules. The change should reduce file size and complexity without changing runtime behavior, queue dependency semantics, or status/error/auth/locking expectations.

User-visible proof is behavioral parity: the existing archive/fork/delete/debris tests keep passing, queue dependency checks remain green, and full `tests/rq --maxfail=1` still passes after the breakup.

## Progress

- [x] (2026-02-20 02:30Z) Read root `AGENTS.md`, `tests/AGENTS.md`, and `docs/prompt_templates/codex_exec_plans.md`; mapped initial repository constraints and required validation gates.
- [x] (2026-02-20 02:31Z) Audited `wepppy/rq/project_rq.py` and identified extraction seams (archive/restore internals, fork internals, delete/gc maintenance flows).
- [x] (2026-02-20 02:32Z) Authored this ExecPlan at `docs/mini-work-packages/20260220_project_rq_breakup_strategy.md`.
- [x] (2026-02-20 02:38Z) Extracted archive/restore internals to `wepppy/rq/project_rq_archive.py` and delegated from `project_rq.py` with compatibility helper aliases.
- [x] (2026-02-20 02:39Z) Extracted fork internals to `wepppy/rq/project_rq_fork.py`; kept queue dependency enqueue in `project_rq.fork_rq` to preserve public task wiring semantics.
- [x] (2026-02-20 02:39Z) Extracted delete/gc/maintenance internals to `wepppy/rq/project_rq_delete.py` with runtime dependency injection from wrappers.
- [x] (2026-02-20 02:39Z) Added `.pyi` stubs for new modules (`project_rq_archive.pyi`, `project_rq_delete.pyi`, `project_rq_fork.pyi`) and preserved `project_rq.py` public entry points.
- [x] (2026-02-20 02:40Z) Added targeted regression tests: `tests/rq/test_project_rq_archive_helpers.py`, extra non-retryable delete branch assertion in `tests/rq/test_project_rq_delete_run.py`, and env-sanitization coverage in `tests/rq/test_project_rq_fork.py`.
- [x] (2026-02-20 02:42Z) Completed required test/gate suite, including targeted pytest runs, `wctl run-pytest tests/rq --maxfail=1`, `wctl check-rq-graph` + artifact regeneration, `wctl check-test-stubs`, and doc-lint checks.
- [x] (2026-02-20 02:43Z) Moved this mini work package to `docs/mini-work-packages/completed/` after validation gates passed.
- [ ] Commit and push branch.

## Surprises & Discoveries

- (2026-02-20 02:31Z) Observation: Existing tests monkeypatch module-level attributes on `wepppy.rq.project_rq` (for example `shutil.rmtree`, `zipfile.ZipFile`, `get_current_job`) rather than patching imported helper modules.
  Evidence: `tests/rq/test_project_rq_archive.py`, `tests/rq/test_project_rq_delete_run.py`, and `tests/rq/test_project_rq_debris_flow.py` patch attributes directly on `project_rq`.

- (2026-02-20 02:41Z) Observation: The generated dependency graph drifted even without semantic queue changes because source line numbers moved after extraction.
  Evidence: Initial `wctl check-rq-graph` failed and listed `wepppy/rq/job-dependency-graph.static.json` and `wepppy/rq/job-dependencies-catalog.md` as drifted artifacts.

- (2026-02-20 02:41Z) Observation: New helper test expectation initially assumed `.\\` Windows-style relpaths preserved a leading dot, but normalization intentionally strips `./` prefixes.
  Evidence: First `wctl run-pytest tests/rq --maxfail=1` failed in `tests/rq/test_project_rq_archive_helpers.py::test_normalize_relpath_and_exclusion_rules` until the assertion was corrected.

## Decision Log

- Decision: Keep `wepppy/rq/project_rq.py` as thin wrappers around extracted implementations, with wrappers constructing runtime dependencies from `project_rq` module attributes.
  Rationale: This preserves the public import/API surface and keeps monkeypatch-based tests behaviorally compatible while reducing core file complexity.
  Date/Author: 2026-02-20 02:32Z / Codex

- Decision: Prioritize extraction of archive/restore, fork, and delete/gc/maintenance clusters first.
  Rationale: These are cohesive, high-complexity blocks with minimal coupling to queue orchestrators that must stay visible in `project_rq.py`.
  Date/Author: 2026-02-20 02:32Z / Codex

- Decision: Keep the `_finish_fork_rq` dependency enqueue call in `project_rq.fork_rq` instead of moving it into helper modules.
  Rationale: This retains explicit queue wiring in the stable API module and avoids unnecessary enqueue-target indirection in dependency graph extraction.
  Date/Author: 2026-02-20 02:39Z / Codex

## Outcomes & Retrospective

- (2026-02-20 02:42Z) Outcome: `wepppy/rq/project_rq.py` dropped from 2014 to 1262 lines while preserving the same public RQ entry points; extracted internals now live in focused sibling modules with dedicated stubs (`project_rq_archive*`, `project_rq_delete*`, `project_rq_fork*`).

- (2026-02-20 02:42Z) Outcome: Required validations passed after one test assertion fix and graph artifact regeneration:
  - `wctl run-pytest tests/rq/test_project_rq_archive.py`
  - `wctl run-pytest tests/rq/test_project_rq_fork.py`
  - `wctl run-pytest tests/rq/test_project_rq_delete_run.py`
  - `wctl run-pytest tests/rq/test_project_rq_debris_flow.py`
  - `wctl run-pytest tests/rq --maxfail=1`
  - `wctl check-rq-graph` (after `python tools/check_rq_dependency_graph.py --write`)
  - `wctl check-test-stubs`
  - `wctl doc-lint --path docs/mini-work-packages/20260220_project_rq_breakup_strategy.md`
  - `wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md`

- (2026-02-20 02:42Z) Retrospective: Remaining work is operational closeout only (move plan to completed, commit, push). No functional regressions were observed in the RQ-focused test suite.

## Context and Orientation

`wepppy/rq/project_rq.py` currently contains project lifecycle RQ entry points plus several heavy internal flows: run deletion/GC/maintenance jobs, fork copy and undisturbify logic, and archive/restore utilities. The file exports both public RQ handlers and private helpers used by tests.

This refactor must preserve the stable API contract in `wepppy/rq/project_rq.py`. Public callers should continue importing and enqueueing from the same module. Queue and dependency semantics remain sensitive because dependency graph tooling (`wctl check-rq-graph`) consumes these call sites.

The nearest test coverage for these seams is in `tests/rq/test_project_rq_archive.py`, `tests/rq/test_project_rq_fork.py`, `tests/rq/test_project_rq_delete_run.py`, and `tests/rq/test_project_rq_debris_flow.py`.

## Plan of Work

Milestone 1 extracts archive/restore helpers into a sibling module (`wepppy/rq/project_rq_archive.py`) and keeps `project_rq.py` wrappers that delegate while preserving existing helper names (for example `_calculate_run_payload_bytes`) at the public module level.

Milestone 2 extracts fork internals into `wepppy/rq/project_rq_fork.py`, including rsync command/env helpers and the fork execution workflow. `project_rq.py` keeps wrapper entry points (`fork_rq`, `_finish_fork_rq`, helper exports) so external callers remain unchanged.

Milestone 3 extracts deletion/GC/maintenance flows into `wepppy/rq/project_rq_delete.py` and delegates from wrappers. Runtime dependencies that tests monkeypatch in `project_rq` are passed explicitly from wrappers to preserve behavior.

Milestone 4 updates stubs and tests, then regenerates/checks RQ dependency graph artifacts if drift appears. Final milestone runs all required quality gates, updates this plan sections, and performs closeout (move plan, commit, push).

## Concrete Steps

Run all commands from `/workdir/wepppy`.

1. Implement extraction modules and wrapper delegation.

       rg -n "^(def|class) " wepppy/rq/project_rq.py

2. Run targeted tests required by the task.

       wctl run-pytest tests/rq/test_project_rq_archive.py
       wctl run-pytest tests/rq/test_project_rq_fork.py
       wctl run-pytest tests/rq/test_project_rq_delete_run.py
       wctl run-pytest tests/rq/test_project_rq_debris_flow.py

3. Run queue graph checks and regenerate artifacts if drift is reported.

       wctl check-rq-graph
       python tools/check_rq_dependency_graph.py --write
       wctl check-rq-graph

4. Run full RQ tests and remaining gates.

       wctl run-pytest tests/rq --maxfail=1
       wctl check-test-stubs
       wctl doc-lint --path docs/mini-work-packages/20260220_project_rq_breakup_strategy.md
       wctl doc-lint --path wepppy/rq/job-dependencies-catalog.md

5. Finalize closeout.

       mv docs/mini-work-packages/20260220_project_rq_breakup_strategy.md docs/mini-work-packages/completed/
       git add -A && git commit -m "Refactor project_rq into focused sibling modules"
       git push

## Validation and Acceptance

Acceptance requires:

- `wepppy/rq/project_rq.py` remains import-compatible for existing callers and tests.
- Extracted modules reduce `project_rq.py` complexity while preserving status/error behavior and queue dependencies.
- Required tests pass:
  - `wctl run-pytest tests/rq/test_project_rq_archive.py`
  - `wctl run-pytest tests/rq/test_project_rq_fork.py`
  - `wctl run-pytest tests/rq/test_project_rq_delete_run.py`
  - `wctl run-pytest tests/rq/test_project_rq_debris_flow.py`
  - `wctl run-pytest tests/rq --maxfail=1`
- RQ dependency drift check passes (`wctl check-rq-graph`) with regenerated artifacts committed when needed.
- `wctl check-test-stubs` and required doc-lint commands pass.

## Idempotence and Recovery

The extraction is additive and wrapper-based, so rerunning tests after each milestone is safe. If a helper extraction causes compatibility issues, keep wrappers intact and move logic back incrementally while preserving function signatures.

Graph artifacts must be regenerated only via `python tools/check_rq_dependency_graph.py --write`; do not hand-edit generated graph sections.

## Artifacts and Notes

Key artifacts expected from this work:

- New implementation modules in `wepppy/rq/` with matching `.pyi` files.
- Updated `wepppy/rq/project_rq.py` wrappers and helper aliases.
- Updated queue graph artifacts if drifted:
  - `wepppy/rq/job-dependency-graph.static.json`
  - `wepppy/rq/job-dependencies-catalog.md`

## Interfaces and Dependencies

New modules should expose implementation functions with explicit runtime dependency inputs so wrappers in `project_rq.py` can inject patched callables/modules during tests. Public API remains at `wepppy.rq.project_rq`.

No change is planned to external queue task names or route contracts. If extraction forces a callable identity change for enqueue wiring, graph artifacts must be regenerated and documented as no-op behavioral drift.

Revision Note (2026-02-20 02:32Z, Codex): Created this ExecPlan from scratch for the `project_rq.py` breakup request and initialized living sections before implementation.
Revision Note (2026-02-20 02:42Z, Codex): Updated living sections after implementation to capture completed extraction milestones, validation outcomes, dependency-graph drift handling, and remaining closeout work.
Revision Note (2026-02-20 02:43Z, Codex): Moved this ExecPlan to `docs/mini-work-packages/completed/` and marked the closeout move step complete.
