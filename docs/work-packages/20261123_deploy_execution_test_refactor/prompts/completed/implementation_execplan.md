# Extract the deploy execution test harness

## Purpose and approach

Keep tests/scripts/test_deploy_production_execution.py as the scenario entry point. Extract embedded executable text into tests/data/deploy_execution, install copies under the same temporary paths and permissions, and factor the subprocess driver into a sibling helper. Preserve the build/resume sequence, output concatenation, lock lifetime, environment, and command log.

## Progress

- [x] Inspect the module on local master and identify fixture setup boundaries.
- [x] Extract and compare the original command doubles and test functions.
- [x] Validate the candidate for local integration.

## Surprises & Discoveries

The helper includes a fake python3 launcher and an independent controller builder. Their installation paths and interpreters matter to the scenarios.

## Decision Log

Keep test names and module paths stable because they are directly selectable by pytest. Keep the subprocess doubles under tests/data so they can be read as ordinary scripts.

## Validation and recovery

From the candidate checkout run `wctl run-pytest --profile python -- tests/scripts/test_deploy_production_execution.py -q`. Compare all scenario definitions and fixture bytes to the parent revision. Revert the test-only commit to restore the inline harness if necessary.

## Outcomes & Retrospective

All 75 scoped cases passed on both revisions. Each extracted script matched its original bytes, and the 59 test definitions matched in order, including decorators. The subprocess harness fell from 733 to 208 lines in its main entry point. Validation and receipt identifiers are in the [tracker](../../tracker.md).
