# Feature export service test refactor

**Status** Closed 2026-11-22 UTC (local validation)
**Started** 2026-11-22 05:23 UTC

The feature export service test module spans submission, materialization and artifact handling. Split it along existing responsibilities so maintainers can locate and run the relevant cases more easily.

## Scope and success criteria

- Move existing tests and local helpers within `tests/nodb/mods/`, preserving case names, parameters, markers, fixture setup, patch targets and assertions.
- Keep execution, caching and publication in the original module, where they share submission and artifact setup.
- Use the existing pytest harness and isolated `wctl` runner. Production code, shared test infrastructure and the full test suite are outside this package's scope.
- Compare focused baseline and candidate case inventories and outcomes. Capture the module and function size and complexity metrics for each file.

## Review

The maintainers of the feature export tests are the audience for this package. Security impact is none because the changes are confined to tests and documentation. Existing artifact readback tests are part of focused validation.

See the [tracker](tracker.md) and [completed ExecPlan](prompts/completed/implementation_execplan.md).

## Outcome

The service cases now span six modules. All 79 cases passed on both source states, every test and helper definition matched the baseline, and all six files fall below the red severity thresholds. See the [validation record](artifacts/validation.md) for measurements, receipt IDs and the updated test selection.
