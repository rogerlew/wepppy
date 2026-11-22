# Refactor the feature export service tests

Split `tests/nodb/mods/test_features_export_service.py` by responsibility so that a maintainer can locate cases for one service concern without scanning the entire file. Start from revision `89f796ef10e69c4a805e106c41e288970df5ebf5`. The sibling `test_features_export_*.py` modules already test individual production collaborators and stay outside the refactor.

## Progress

- [x] 2026-11-22 05:24 UTC. Establish focused baseline results and code-quality measurements.
- [x] 2026-11-22 05:25 UTC. Move groups and their local helpers into focused modules.
- [x] 2026-11-22 05:26 UTC. Verify preserved cases and capture candidate test and quality evidence.

## Surprises & Discoveries

The isolated baseline passed all 79 cases. The original module measures 3,243 source lines, a longest function of 116 lines and maximum cyclomatic complexity of 26. The measurements use the Python analyzer from `tools/code_quality_observability.py`.

## Decision Log

Keep the original module for execution, cache reuse, artifact construction and publication. Those tests share helpers that should stay local. Use sibling modules for submission, carrier materialization, source joins, spatial identity and temporal layouts. Move whole definitions so decorators, setup, patch targets and assertions are preserved.

## Plan of Work

Move test functions, helper functions and imports to the module that uses them. Retain the module-level `unit` pytest marker in every file. Keep helpers private and local. Add a focused command to the test suite guide.

## Validation and Acceptance

Run both commands from their respective source states and capture a JUnit XML report from each.

    wctl run-pytest --profile python -- tests/nodb/mods/test_features_export_service.py -q --junitxml=.wctl-test-runs/features-export-before.xml
    wctl run-pytest --profile python -- tests/nodb/mods/test_features_export_service*.py -q --junitxml=.wctl-test-runs/features-export-after.xml

Compare case names including parameter IDs, allowing module paths to change. Check the moved definitions against the baseline and keep their decorators, fixture calls and assertions intact. Record Python source lines, longest function and cyclomatic complexity for all files. Lint changed Markdown with `wctl doc-lint --path`. The user requested focused validation.

## Idempotence and Recovery

The changes are confined to a task worktree. Rerun the focused command after any correction and write fresh results before updating the tracker.

## Outcomes & Retrospective

The baseline and candidate passed the same 79 cases. All 83 top-level test and helper definitions retained their source text. The largest module now contains 964 source lines, and no file exceeds a red threshold. The longest function still measures 116 lines because the extraction preserved its fixture and artifact assertions. The [validation record](../../artifacts/validation.md) contains the commands and receipts. The [test guide](../../../../../tests/README.md#feature-export-service-tests) records the new selection.
