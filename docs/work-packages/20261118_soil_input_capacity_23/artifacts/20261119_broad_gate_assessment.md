# Independent assessment of segmented broad validation

Reviewer: `/root/correctness_review`, 2026-11-19 UTC.

## Finding

Completing the canonical broad suite in a retained passed prefix plus a clean
remainder is a reasonable validation disposition here. The required full
`wctl run-pytest tests --maxfail=1` invocation was performed; repository guidance
does not explicitly demand a single uninterrupted green receipt after a
module-local test-fixture repair. This is conditional on complete coverage
reconciliation and a passing remainder, not permission to omit failing tests.

## Evidence inspected

- Full invocation `python-full5.log`: 6503 passed, 225 skipped, 99 deselected;
  one failure in the first case of `tests/nodb/test_single_input_artifacts.py`.
  Total collection: 15158 items, 99 deselected, one collection skip, 15059 selected.
- Receipt `.wctl-test-runs/7a6bb7729836498c995b07e269177b48/receipt.json` accurately
  records failure; its entire `source_before` and `source_after` maps match.
- Remainder receipt `.wctl-test-runs/ac2993c89cdc4e86b45dcc2bf1a14191/receipt.json`
  starts from the same source except **one file**:
  `tests/nodb/test_single_input_artifacts.py`.
- That change supplies a fixture-scoped `Soils.wepp_instance` with the existing
  `wepp_260803` selection. Actual capacity resolution remains exercised; it does
  not stub the changed capacity validator or modify production behavior.
- `full-suite-passed-prefix.json` contains 354 unique modules. These exactly
  equal the 355 modules logged during full5 execution minus the failing module.
  No unexecuted or failed module was excluded from the remainder by this manifest.

## Minimal completion conditions

1. Remainder reaches normal completion with zero failures/errors and a stable
   source receipt. The entire formerly failing module must pass.
2. Reconcile initial selected test inventory against the completed prefix and
   remainder. Account separately for collection skips, runtime skips and the
   intentionally opt-in native matrix deselections. Do not double count a failed
   attempt as a passed test.
3. Keep production hashes unchanged across the validated segments. If later
   production changes affect passed-prefix consumers, rerun those affected
   consumers; a global fixture or collection change requires renewed assessment.
4. Retain original failed receipts and report **segmented broad coverage**.
   Do not claim that full5 passed, that a single uninterrupted full run passed,
   or that native opt-in coverage is part of ordinary broad discovery.

## Limits and verdict

Conditional acceptance of the segmented validation approach. At review time the
remainder was running, so broad-gate completion is not yet established. Test
ordering across the segment boundary and collection effects of ignored prefix
modules are not reproduced in the remainder; disclose that limit. There is no
observed production regression or known order-dependent failure requiring an
additional full restart at this checkpoint. The separate native matrix and
artifact/replay evidence remain necessary and are not replaced by broad tests.

This assessment does not waive unresolved test failures, source stability,
production deployment parity, or independent security review.

## Remainder disposition and minimal hygiene repair

The remainder completed with 8050 passes, 282 reported skips, 99 deselections
and one failed Roads publication source-review check. Its source receipt reports
`source_changed`; independently comparing maps shows exactly one changed file:
`wepppy/wepp/management/scripts/man42_5.man.json`. The delta adds only
`_pmet_plant_names: null`. This receipt must remain labeled `source_changed`.

Confirmed cause: existing `tests/test_imports.py` recursively imports developer
utilities. `management/scripts/export_covers.py` changes cwd to its source
directory and writes exports at import time; `management/data/UnDisturbed/
dump_to_json.py` subsequently serializes all cwd `*.man` files. No production
capacity source changed. Recommended and inspected bounded test repair excludes
only those two known management utility roots (three Python scripts total),
restores cwd and sys.path in fixture teardown, and retains all other discovered
import targets. A generic repository-wide scripts/data exclusion would remove
more coverage than justified and is unnecessary. This diagnostic test still
reports import failures without asserting their count; no claim of all imports
succeeding is made.

The Roads review update records the three already-reviewed changed source
identities and preserves `stale_full_project_routing`, published report/results
and original execution provenance. The remainder exercised the 516 native Roads
profiles; that does not refresh the historical full-project routing claim.

Minimum closeout: restore the tracked management JSON exactly; run the import
diagnostic and complete Roads publication module under canonical wctl with a
stable passing source receipt; confirm the only remaining differences from
remainder-tested source are these bounded test/review changes. No production
code or shared test fixture is changed by this repair. Do not recast the earlier
source-changed receipt as passing.

Selected test counts reconcile exactly: prefix 6503 passes + 224 runtime skips
= 6727; remainder 8050 passes + 281 runtime skips + one failure = 8332;
6727 + 8332 = the original 15059 selected tests. Each session separately reports
the same one collection skip and 99 opt-in deselections. If the Roads failed
case passes on repair, unique ordinary outcomes are 14554 passed and 505 runtime
skips, plus one collection skip and 99 deselections. Repeated focused cases are
not added to that unique total. Cross-segment ordering remains an explicit limit.

## Final gate disposition

**Accepted: segmented broad validation complete for implementation and local
release preparation.** Independently inspected final receipt
`.wctl-test-runs/99650b889c0a4f90bcc2ef2574ec0dc4/receipt.json`: `status=passed`,
`pytest_exitstatus=0`, `exitstatus=0`, and identical source-before/source-after
maps. `final-publication-imports.log` records four passing cases in 17.36 seconds.
The entire Roads publication module and corrected import diagnostic passed.

Compared with the remainder's starting source, final source differs only in
`tests/roads/analysis_staleness_current.json` and `tests/test_imports.py`—the two
reviewed bounded repairs. The management JSON is restored exactly; production
source is unchanged. Therefore the retained prefix, remainder and repaired-module
receipts support **14,554 unique passed tests, 505 runtime skips, one collection
skip and 99 opt-in deselections** under the disclosed segmented execution.

No unresolved correctness finding or remaining ordinary broad-test failure is
established by these receipts. The implementation/release-preparation package
may close with its native, targeted, security and artifact evidence. This is not
a single uninterrupted green full-suite run; cross-segment ordering remains
unverified. Production deployment, original-project repair and scientific
approval of disposable replay outputs remain outside this gate's claim.

Final independent disposition: `/root/correctness_review`, 2026-11-19 UTC.
