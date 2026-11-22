# Omni test refactor validation

Baseline commit `94ab2b77ed5145c94e6754f0e705f10d25fc3941` and the refactor ran in the isolated development container with the Python profile. Each receipt records exit status 0 and a passing source integrity check. JUnit reports and runner receipts are under `.wctl-test-runs/` in the task worktree.

| Run | Result | Local wctl receipt |
| --- | --- | --- |
| Baseline Omni suite | 229 passed in 13.03 s | `ae839290a763420db9f47e23cd733da1` |
| Refactored Omni suite | 229 passed in 11.68 s | `c7cadd5b78a44189b90039c9bb885fd9` |
| Refactored controller files in reverse order | 83 passed in 10.56 s | `6eb9931d1c974c4bafac8066a24b0be4` |

Each run reported two dependency deprecation warnings. Validation was scoped to the Omni tests.

## Commands

Run the first command on the baseline, the second on the candidate and the third to exercise controller tests with the stream-order module first.

    wctl run-pytest --profile python -- tests/nodb/mods/test_omni*.py -q --junitxml=.wctl-test-runs/omni-before.xml
    wctl run-pytest --profile python -- tests/nodb/mods/test_omni*.py -q --junitxml=.wctl-test-runs/omni-after.xml
    wctl run-pytest --profile python -- \
      tests/nodb/mods/test_omni_stream_order.py \
      tests/nodb/mods/test_omni_contrast_selection.py \
      tests/nodb/mods/test_omni_contrast_execution.py \
      tests/nodb/mods/test_omni_contrast_artifacts.py \
      tests/nodb/mods/test_omni_clone.py tests/nodb/mods/test_omni.py \
      -q --junitxml=.wctl-test-runs/omni-reverse.xml

## Coverage review

JUnit comparison matched all 229 case names, parameter IDs and outcomes after accounting for moved file paths. The 83 original cases are distributed across six controller modules. An AST comparison matched all 76 test definitions by name, with identical assertions, pytest calls and decorators. Seventy-one definitions are identical in full. The two changed GeoJSON cases and three stream-order cases use scoped dependency patches and preserve their fixture data and output checks. Each module retains the unit marker. The shared fixture supplies the legacy controller policy only for tests that request it.

Existing tests still read the generated contrast sidecar, definition tables and GeoJSON, verify copied workspace contents and check the stream-order grouping report. Moved cases have new node IDs. The [test guide](../../../../tests/README.md#omni-controller-tests) lists the modules and the complete Omni selection.

The repository checker `python3 tools/check_stubs.py` passed in the task worktree. The changed Python files contain zero broad exception handlers.

## Quality measurements

The Python analyzer in `tools/code_quality_observability.py` measured source lines, maximum function length and maximum cyclomatic complexity with Radon installed. Red begins at 1,200 source lines, 150 function lines and complexity 30.

| Module | Source lines | Longest function | Max complexity |
| --- | ---: | ---: | ---: |
| Original baseline | 2,973 | 153 | 17 |
| `test_omni.py` | 216 | 84 | 5 |
| `test_omni_clone.py` | 316 | 60 | 12 |
| `test_omni_contrast_artifacts.py` | 647 | 119 | 11 |
| `test_omni_contrast_execution.py` | 627 | 94 | 12 |
| `test_omni_contrast_selection.py` | 709 | 85 | 8 |
| `test_omni_stream_order.py` | 231 | 115 | 15 |
| `_omni_test_support.py` | 132 | 59 | 7 |

## Documentation check

The package, test guide and project tracker passed Markdown lint.

    wctl --project-dir "$PWD" doc-lint --path docs/work-packages/20261121_omni_test_refactor --path tests/README.md --path PROJECT_TRACKER.md
