# Isolate Pure controls render tests

This living plan follows the [ExecPlan guide](../../../../prompt_templates/codex_exec_plans.md). Maintain Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective during execution.

## Purpose / Big Picture

Make template render regressions reproducible by test node ID. Keep the existing invocation for developers and CI.

## Progress

- [x] (2026-11-22 04:57 UTC) Inspect the render fixture and start focused baseline validation.
- [x] (2026-11-22 04:58 UTC) Consolidate repeated setup and isolate Jinja mutations.
- [x] (2026-11-22 05:02 UTC) Verify node IDs, focused runtime, and reordered cases.

## Surprises & Discoveries

- The module-scoped Jinja fixture shares mutable environment dictionaries and nested render values. The developer indicator case mutates a nested view model across its parameter cases.

- Making every test build a fresh environment raised focused runtime from 32.21
  seconds to 96.57 seconds. Reusing the default template cache brought the final
  run to 35.43 seconds.
- The broad preflight stopped before pytest because the GeoParquet parser or its
  provenance was missing. The Python profile supports this focused selection.

## Decision Log

- 2026-11-22 04:57 UTC, Codex. Keep all collected tests in the existing file. CI and documentation invoke that path directly. Use function scope for cases that modify the environment or nested context. Share the environment across read-only cases to reuse compiled templates.

## Outcomes & Retrospective

All 299 baseline node IDs passed. The reordered selection validated the former
mutation paths. The final fixture keeps the focused runtime near baseline. See the
[tracker](../../tracker.md) for measurements and commands.

## Context and Orientation

`tests/weppcloud/routes/test_pure_controls_render.py` loads production templates from multiple directories, renders them with stub context values and checks markup and source contracts.

## Plan of Work

Build both Jinja fixtures from one factory. Use the function-scoped fixture for cases that write to globals or filters, including mutations of global objects. Group the loader paths and name shared setup used by the run-context and return-period tests. Check that marker, parameter and assertion coverage survives.

## Concrete Steps

From the repository root, run the focused module with
`wctl run-pytest --profile python -- tests/weppcloud/routes/test_pure_controls_render.py -q -rA`.
Compare the ordered node IDs under `PASSED` between runs. Reorder the former mutation
cases by passing explicit node IDs as shown in the tracker. Lint this package with
`wctl doc-lint --path docs/work-packages/20261121_pure_controls_render_refactor`.

## Validation and Acceptance

All baseline nodes must be collected after the change. The focused module and order-sensitive cases must pass. The full suite is outside the requested validation scope.

## Idempotence and Recovery

The test wrapper uses an isolated runtime. Re-run focused commands from the task branch. The test-file diff can be reverted independently of the package record.

## Artifacts and Notes

Record test counts and selection evidence in the tracker.

## Interfaces and Dependencies

Reuse pytest, Jinja and the existing test wrapper. Retain the existing file path and test node IDs.

## Revision note

At closeout, the plan records the switch to selective fixture isolation after the
all-function-scoped trial increased runtime. The test summary supplied the node
IDs used for the collection comparison.
