# Defect Log

- Generated: 2026-03-29T04:32:25.804067+00:00

## Fixed During Execution

1. Return-period selector failed with materialization errors on `wepp.temporal.events`.
   - Fix: derive selector filtering from rank lookup source, inject deterministic `return_period` token, and exclude lookup-only rank source from carrier joins.
   - Evidence: `b3_event_selector_return_period` passed.

2. Unit conversions were not applied to exported numeric values.
   - Fix: integrate `Unitizer.convert_table` into materialization paths before unit-suffix naming.
   - Evidence: `g1` numeric oracle checks.

3. UI copy typo in Features Export controls.
   - Fix: `Unitzer Selections` -> `Unitizer Selections` + route render test coverage.

## Outstanding Failures

- None. All matrix cases passed.

## Numeric Oracle Summary

- Passed: `True`
- Details: `{'hill_pass_values': {'project': 19.465325, 'si': 19.465325, 'english': 687.4114645821775}, 'event_values': {'si': 4.965503055552293, 'english': 0.19549235184739933}}`
- Failures: `[]`
