# Extract climate render setup

## Purpose and milestones

Maintainers should be able to find the inputs specific to each climate render
case without comparing five long constructors. First capture the focused
baseline from local master. Then extract the shared fields into a function-scoped
fixture in `tests/weppcloud/routes/test_pure_controls_render.py`. Leave each
scenario's selections and mutations visible. Finally repeat the baseline command
from the candidate checkout and compare the ordered PASSED records.

    wctl run-pytest --profile python -- tests/weppcloud/routes/test_pure_controls_render.py -q -rA

## Progress

- [x] Inventory repeated climate constructors.
- [x] Extract the fixture and verify parity.

## Surprises & Discoveries

The climate summary report uses a separate, smaller model with different fields.

## Decision Log

Use the dataset-switching case as the baseline model. Allocate its nested
namespaces and dataset map on each invocation because cases mutate selections.
Keep the report test independent.

## Outcomes & Retrospective

The baseline passed all 303 cases in 37.90s. Candidate result: 303 passed, 4 warnings in 35.36s.
The ordered case IDs matched. Syntax-tree comparison matched the assertions
and decorators in all 161 tests and the exact input fields for all five climate
models. The module shrank by 74 lines.
