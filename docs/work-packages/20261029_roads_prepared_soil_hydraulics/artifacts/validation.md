# Validation evidence

Status: complete. Fresh repository coverage: **12,083 passed, 298 skipped, no failures**.

## Native execution and artifact checks

The study executed 140 diagnostic, 35 subdivision and 1,440 confirmation native
cases: **1,615 successful runs**. An additional two minimal-reproducer native
replays exactly reproduce the subdivision finding. Every case passed complete
calendar/OFE, finite numeric, annual-summary and input/output hash checks.
Cross-binary comparisons verify matching management, slope, climate and run
prompts. All 480 shared raw-soil cases reproduce every original scientific metric
and annual export series from the prior benchmark.

Parallel diagnostic revalidation exactly matched the original serial summary.
The first confirmation analysis failed because old reference records lack the
new annual-mean-delta diagnostic field. The retained corrected analyzer checks
every original metric against fresh strict parsing; it never drops a mismatching
scientific value. The compatibility probe demonstrates that additive diagnostics
are admitted and a changed export is rejected. Failed analysis logs and executed
source snapshots are retained; no native simulation failed.

## Repository checks

Fresh full repository coverage is partitioned into disjoint groups; none of
these group results is reused from the earlier benchmark task.

| Group | Result |
| --- | --- |
| `tests/roads --maxfail=1` | 530 passed, 5 skipped |
| `tests/disturbed/test_disturbed_matrix.py -q` | 99 passed |
| `tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py` | 230 passed across disjoint selectors |
| Remaining repository | 11,224 passed, 293 skipped |

The soil-treatment selectors cross versions 9002/9005, single/mofe, and
thinning/not-thinning: eight groups of 27. A ninth selector excludes both versions
and passes 14. Deselections are covered by the other groups, not omitted cases.
The remainder command is:

```bash
wctl run-pytest tests --ignore=tests/nodb/mods/disturbed/test_treatment_soil_artifacts.py --ignore=tests/disturbed/test_disturbed_matrix.py --ignore=tests/roads --maxfail=1
```

Focused tests also pass: seven new depth-treatment cases and four existing
report/calendar cases, **11 passed**. These are included in the repository
remainder and must not be counted twice. Compatibility probe, native replays and
artifact checks are supplementary validations, not pytest counts.

Python compilation and the changed-production broad-exception gate pass. That
gate scans zero changed production Python files and does not imply study-script
coverage. Package documentation lint passes. Whitespace and package spelling-preview checks pass; the completed plan link
is updated and checked at closeout.

Exact commands, outcomes and warnings remain in [validation-logs](validation-logs/).
No physical field validation, native repair, production change or full-project
Roads integration is claimed. Passing tests do not establish candidate acceptance.

The remaining group includes one collection-time skip in its reported 293
skipped. Aggregate counts exclude the repeated focused run. Commands and log
SHA-256 identities are retained in [validation.json](validation.json).
