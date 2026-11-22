# Omni test refactor

**Status** Closed for local validation on 2026-11-22 UTC

**Started** 2026-11-22 05:34 UTC

The Omni controller test module covers scenarios, workspace copying, contrast selection, artifact export and execution in one 3,687-line file. Group the tests so maintainers can locate and run the cases for one responsibility.

## Scope and acceptance

Move the tests from `tests/nodb/mods/test_omni.py` into focused modules under `tests/nodb/mods/`. Preserve assertions, test names, parametrization, markers and artifact readback. Compare case names and outcomes before and after, and measure each resulting module against the repository's code quality thresholds. Run the focused Omni suite as requested.

The complexity budget is pytest, monkeypatch and the existing isolated runner. The package permits test-local helpers and fixtures. Production code, shared test infrastructure and new dependencies are outside scope.

## Review

The audience is maintainers of Omni and its tests. Security impact is none because only tests and documentation change. Focused validation exercises the existing artifact assertions.

See the [tracker](tracker.md) and [completed ExecPlan](prompts/completed/implementation_execplan.md).

## Outcome

Six controller modules preserve the original 83 cases. The focused Omni run passed
all 229 cases before and after the split. All resulting Python files are below
the repository's red thresholds. See the [validation record](artifacts/validation.md).
