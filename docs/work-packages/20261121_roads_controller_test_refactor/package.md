# Roads controller test refactor

**Status** Closed locally on 2026-11-22 UTC

**Started** 2026-11-22 05:08 UTC

## Scope and objectives

Organize the cases in `tests/nodb/mods/test_roads_controller.py` by the Roads
contract they cover. Extract repeated orchestration setup so the tests show the
scenario, action, and artifact assertions together. Use the directory
`tests/nodb/mods/roads_controller/` to run the complete set.

## Complexity budget

Reuse pytest, its function-scoped monkeypatch fixture, and the existing Roads
test doubles. Use focused modules and small setup helpers where they clarify
ownership. Preserve the existing cases, parametrization, markers, failure
injections, and artifact readback. This package covers test code and its
documentation. Validation is scoped to the moved tests.

## Acceptance

- Collect the same cases and parameter variants after accounting for moved paths.
- Pass the Roads controller tests through the isolated `wctl` runner.
- Compare file size, maximum function length, and cyclomatic complexity against
  the baseline. Record any remaining hotspots and the review outcome.
- Update the Roads developer test command and retain evidence with the package.

## Review gates

Security impact is none because the package reorganizes test code. A dedicated
security review and parameterization ADR are unnecessary. Existing generated
test artifacts remain covered by their original assertions.

## Deliverables

- [Tracker](tracker.md)
- [Validation and review](artifacts/validation.md)
- [ExecPlan](prompts/completed/implementation_execplan.md)

The [Roads production refactor](../20261117_roads_code_quality_refactor/package.md)
tracks the separate production implementation.

## Closure

Eight focused test modules replace the original controller test file. All 92
tests passed with matching parameterized case names and results. The largest
replacement file has 553 source lines, the longest function spans 146 lines,
and maximum cyclomatic complexity is 29. Validation covered the refactored
tests and mixed-directory collection. Independent review accepted the change.
