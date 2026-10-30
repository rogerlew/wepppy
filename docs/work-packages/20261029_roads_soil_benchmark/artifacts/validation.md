# Benchmark validation

Date: 2026-10-29. Repository validation complete: **12,076 passed, 298 skipped, no failures** across disjoint groups.

## Scientific artifact checks

All 2,880 main native runs passed the retained report generator's identity,
consumed-input/output hash, calendar, finite-value and annual-summary checks.
The 96-case screen, ten original-duration reference runs, fifteen modern PASS
diagnostics and six long-road stress probes are retained separately. See the
[report](../report.md) for scientific acceptance and limitations. Successful
execution does not imply that generated-soil candidates meet the factor-ten band.

## Repository coverage

Commands use `wctl run-pytest`. The full repository suite was partitioned into
four disjoint groups for runtime; original sequential and intermediate attempts
were stopped and are not counted as completed gates. No observed test failure
motivated partitioning. No required cases were intentionally omitted.

| Group | Arguments | Result |
| --- | --- | --- |
| Roads | `tests/roads --maxfail=1` | 530 passed, 5 skipped |
| Disturbed matrix | `tests/disturbed/test_disturbed_matrix.py -q` | 99 passed |
| Soil-treatment artifacts | `tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py` with disjoint selectors below | 230 passed |
| Remaining repository | `tests --ignore=tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py --ignore=tests/disturbed/test_disturbed_matrix.py --ignore=tests/roads --maxfail=1` | 11,217 passed, 293 skipped |

Soil-treatment selectors cross `9002`/`9005`, `single`/`mofe`, and
`thinning`/`not thinning`: eight groups of 27 passed. The ninth selector,
`not 9002 and not 9005`, passed 14. Each command and its result are retained in
[validation-logs](validation-logs/); deselected cases are covered by the other
selectors and are not counted as skips.

Focused `tests/tools/test_roads_soil_benchmark.py -q`: 4 passed, also included
in the repository remainder and therefore not added twice to aggregate coverage.
These tests exercise spatial integration, legitimate native zero profiles,
missing annual summaries and missing climate days using retained native evidence.

## Additional checks and boundaries

- Python compilation passed for study scripts.
- Broad exception changed-production-file gate passed; it scanned zero changed
  production Python files and does not establish coverage of study scripts.
- Markdown lint passed for the package, `PROJECT_TRACKER.md` and `tests/AGENTS.md`; `git diff --check` passed.
- No production defaults, deployed binaries, source run data or fswepp2 files
  were changed. Full-project generated-soil Roads integration was not entered
  because no candidate passed scientific acceptance.

This is an isolated parameterization study with a recorded self-review, not an
independent scientific validation against field measurements.

Log SHA-256 identities and command/result summaries are retained in
[validation.json](validation.json). Aggregate coverage excludes the repeated
focused test run. The remaining repository group includes one collection-time
skip in its reported 293 skipped. Warnings remain visible in the full logs.
