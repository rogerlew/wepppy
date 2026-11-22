# Feature export service test validation

The baseline was `89f796ef10e69c4a805e106c41e288970df5ebf5`. The candidate used the same base with the six test module changes in the task worktree. Both runs used the installed development image and the isolated Python profile.

| Run | Result | Local wctl receipt |
| --- | --- | --- |
| Baseline | 79 passed in 12.36 s | `8dc9d3acbc084efb8a8c8c3081fb27ae` |
| Candidate | 79 passed in 11.61 s | `c2e775a924d4463abd9465c3b8755907` |

Both receipts record exit status 0 and passing source integrity checks. Each run reported the same two dependency deprecation warnings. Receipts and JUnit reports are in the task worktree's `.wctl-test-runs/` directory.

## Commands

Run the first command on the baseline and the second on the candidate.

    wctl run-pytest --profile python -- tests/nodb/mods/test_features_export_service.py -q --junitxml=.wctl-test-runs/features-export-before.xml
    wctl run-pytest --profile python -- tests/nodb/mods/test_features_export_service*.py -q --junitxml=.wctl-test-runs/features-export-after.xml

## Coverage review

The JUnit reports contain the same 79 unique case names and parameter IDs with matching pass outcomes. A Python AST inventory and source comparison confirmed that all 75 test function definitions and eight helper definitions are byte-identical, including decorators. Each file retains the module-level unit marker. The service test for a real GeoPackage still checks the packaged layer and reads two geometries from its SQLite table. The review found no broadened exception handlers or cross-module helper dependencies. Test node IDs for moved cases now have new file paths. The [test guide](../../../../tests/README.md#feature-export-service-tests) gives the updated full service selection.

## Quality measurements

The Python analyzer in `tools/code_quality_observability.py` measured code source lines, the longest Python function and maximum cyclomatic complexity. Red begins at 1,200 source lines, 150 function lines and complexity 30. Every candidate file falls below all three thresholds.

| Module | Source lines | Longest function | Max complexity |
| --- | ---: | ---: | ---: |
| Original baseline | 3,243 | 116 | 26 |
| `test_features_export_service.py` | 964 | 116 | 26 |
| `test_features_export_service_identity_and_units.py` | 330 | 78 | 7 |
| `test_features_export_service_materialization.py` | 743 | 103 | 9 |
| `test_features_export_service_sources.py` | 654 | 89 | 7 |
| `test_features_export_service_submission.py` | 244 | 71 | 7 |
| `test_features_export_service_temporal.py` | 368 | 39 | 6 |

Validation covers the service cases and their existing artifact checks. The full suite was outside the requested scope.

## Documentation check

The package, test guide and project tracker passed Markdown lint with zero errors or warnings across six files.

    wctl --project-dir "$PWD" doc-lint --path docs/work-packages/20261121_features_export_service_test_refactor --path tests/README.md --path PROJECT_TRACKER.md
