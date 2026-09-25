# Validation evidence

Candidate implementation: `9a5eb0813`; contract ancestor: `b63e738d0`.

Retained command logs have trailing whitespace normalized; results are unchanged.

## Completed checks

- `red-tests.log`: before implementation, both single/MOFE 9002 thinning_30_90
  fail direct artifact checks (missing converted thinning file / fallback class).
- `focused-tests.log`: 123 passed across lookup, single/MOFE, PMET, Treatments,
  archive/restore, browse and download.
- `archive-final-tests.log`: 3 passed in 35.97 seconds, including the final
  diagnostic-byte assertion and both intermediate/prepared soil copies.
- `broad-exceptions.log`: PASS, zero added broad catches.
- Changed Markdown doc-lint and spelling previews pass; git diff whitespace check passes.
- `artifact-tests.log`: 198 passed in 939.01 seconds, including the full
  thinning/mulch real-writer matrix, operator values and nonprefix/empty states.
- `local-project-result.json`: PASS at 2026-09-25 16:08:21 UTC using candidate
  `9a5eb08137d572ef437764515144b8fba2134c64`, container uid 1000/gid 993.
  Supported fork/rebuild of the local choice-feminist copy rebuilt 455 hillslopes
  and 1065 segments, then applied thinning_30_90 to hill 71. All five OFEs in
  intermediate and prepared p10.sol have upper Ksat 40, kr 0.00004, metadata
  1.3/0.3. Twelve source NoDb hashes remained unchanged. Relative paths, content
  hashes and exact parsed values are retained in the JSON.

## Broad-suite outcome

`broad-tests.log`: required `wctl run-pytest tests --maxfail=1` stopped with
5,286 passed, 54 skipped and one failure in 1995.69 seconds. All 198 new soil
artifact cases passed within this run. Later tests were not executed.

Failure: `test_run_hillslopes_uses_mofe_timeout_for_continuous_hillslopes[False-60]`
expects 60 seconds; the runner and accepted ADR-0072 specify 120 seconds.
`timeout-baseline-identity.json` proves runner, test and ADR Git blobs are
identical at starting revision `2b0c3e30d` and candidate `9a5eb0813`.
`timeout-baseline-repro.log` independently reproduces the mismatch (one failed,
one passed). The stubbed runner test does not invoke either changed soil method.
Both reviewers independently confirmed this is preexisting. Leave the unrelated
literal test correction to repository maintainers; full-suite success is not claimed.

## Remaining release evidence

The local project is an older choice-feminist copy, not the current wepp1
scenario. No fresh model execution is claimed.

## Quality telemetry

Observe-only report, base `b63e738d0`: production file SLOC 2351 to 2355 and
maximum function length 378 to 382; no radon available for complexity metrics.
The existing file is over the red size band. The four executable lines are
duplicated deliberately at two soil consumers to avoid changing shared RUSLE
key normalization or introducing another abstraction for a bounded correction.
No broad refactor is warranted for this fix. New artifact test module is green
(115 SLOC, maximum function length 26).

## Coverage boundaries

The new numerical fixtures use loam and soil formats 9002/9005, all 16 catalog
thinning combinations plus bare/custom prefixes, and forest/shrub/grass ×
low/moderate/high × mulch15/30/60. Nonprefix strings, None/empty and an edited
operator lookup row are covered. Existing 7778 routing coverage is retained;
the new direct artifact matrix does not claim every texture or soil format.

Archive cases are labeled artifact snapshots with actual soil/log byte checks,
not live scenario lifecycle execution. Production identity/mount validation,
deployment, existing-run recovery, fresh reports and live browser acceptance
remain operator release/recovery gates. Source or local tests alone do not
resolve the production incident.
