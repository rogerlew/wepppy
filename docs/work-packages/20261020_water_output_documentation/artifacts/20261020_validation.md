# Water output documentation validation

## Revisions and scope

WEPPpy starting revision `1ecf04735`, contract checkpoint `14c7eebb1`.
Paired native descriptive-metadata release `3b630643ba06bd40262285f206112c9d3ee32b21`;
interchange binary SHA-256 `1cb2cec6ecba762362d117982d448b397c900b9c3a1be742a0c3bbea16e3e62b`.
No formula, field identity/type, machine-unit, cache marker or numerical behavior
changes. No production deployment or existing run regeneration.

## Completed evidence

| Check | Result |
| --- | --- |
| Initial documentation/Usersum/template suite | 281 passed |
| Final affected route/template/README suite, including guide search and Roads readiness | 270 passed |
| Final missing-manifest README refinement | 6 passed |
| Final targeted guide discovery including ET, H.wat and H.pass | 7 passed |
| Interchange and hillslope/total water reports | 105 passed, 1 skipped |
| Native Python interchange suite | 163 passed |
| Native Rust suite | 107 unit + 17 integration passed |
| Changed native schema formatting | `rustfmt --check --edition 2021 wepp_interchange/src/schema.rs` passed |
| Paired native service startup preflight | Import/path/hash checks passed |
| Frontend ESLint | Passed |
| Frontend Jest | 119 suites, 987 tests passed |
| Usersum manifest/nav/vendor validation | 78 documents, 78 nav leaves, 2 vendors |
| Changed documentation lint | Passed; corrected initial relative-link errors |
| New-guide uk2us preview | No spelling changes |
| Native generated Parquet metadata readback | Both 6,576-row files exactly match Python schema metadata; independently verified |
| Isolated Chromium Usersum guide/reference and seven searches | HTTP 200, normal user role, prefix-safe guide links, no page-width overflow at 1440 px |

The final browser check uses a fresh Flask process with the unmodified runtime
loader reading the published repository index. Both guides and all seven searches
returned HTTP 200 as a normal user under `/weppcloud`. Screenshots and
[browser_checks.json](browser_checks.json) record that boundary; this is repository
catalog publication evidence, not production deployment.

The full repository pytest sweep initially passed 506 tests with 28 skips before
a stale literal expected binary hash failed. The expected hash now matches the
paired release. The sweep resumed after the 45 fully completed files, rerunning
the entire startup-contract file. Subsequent chunks and final completion are
recorded below. No Python execution errors remain in the
focused checks. Two initial new-test harness errors (boolean instead of string
configuration, HTML role-label matching) were corrected and rerun successfully.

## Audit disposition

DOC-01–10: addressed through metadata descriptions, two guides, report/source
context, worked example, corrected links and status, and explicit producer/layout/
accounting version distinctions. DOC-11: complete field reference and verified
physical units; existing machine-unit labels intentionally unchanged because
correcting them changes downstream export conversion/suffix behavior. A future
compatibility change must test SI/project-unit exports and cache/name effects.
DOC-12: historical vendor lineage is qualified in user guidance; synced historical
sources remain unchanged.

## Publication and operational gate

The operator explicitly authorized updating Usersum and committing. Four affected
document entries and two navigation leaves were published while preserving all
74 other document entries exactly. The original bytes were backed up before the
write; a concurrent-change check guarded publication. See
[catalog_publication.json](catalog_publication.json). No vendor sync occurred.
The pre-existing generated-index updates are retained in the commit. Their origin
is unverified; the current scheduled task sets `write_index: false`.

Fresh-process catalog, normal-user routes/search and browser validation pass.
Existing production workers receive the catalog through the normal deployment
and process reload workflow; no production restart or deployment was performed.

Old Parquet metadata and report caches are not rewritten. Known machine-unit
labels for PASS sediment fractions remain flagged; groundwater volume units are
provided in descriptions/reference, not newly added machine metadata. Model
contour and six-year replay limitations remain those of the prior accounting
release, independent of this documentation correction.

Repository-wide `cargo fmt --check` reports pre-existing formatting differences
outside the changed schema (including ashpost.rs). The changed schema passes its
standalone formatting check; unrelated native source was not reformatted.

An ET-only query initially ranked the reference below the first page because the
existing in-memory search also matches ET inside unrelated words. A descriptive
reference subtitle now includes ET/Dp/runoff; all seven first-page discovery
checks pass without changing ranking code. Browser screenshots/results were
refreshed after this authoring correction.

## Final publication checks

The resumed broad sweep passed 10,299 tests with 99 skips before exposing the
dashboard test fixture's missing Usersum helper. The fixture now registers the
real helper and Usersum blueprint, matching production wiring; no production
fallback was added. The focused dashboard/Usersum/template suite passed 66 tests.
The remaining broad files were checked separately without repeating the
683 completed files. Final successful outcome is recorded below.

## Final broad outcome and publication approval (2026-10-21 UTC)

Broad coverage completed in resumed chunks: 499 passes in fully completed initial
files (the first run's 506 included seven startup-file cases subsequently rerun),
10,299 passes/99 skips in the next chunk, and final 186 + 60 passes. Initial
skips were 28; the repeated collection skip is counted once, yielding 126 unique
skips across broad coverage. Three additional guide-query cases added after
broad collection pass in the 66-test publication suite. No unresolved test
failure remains in the selected coverage.

The all-tree resumption with 683 ignore flags was stopped during collection to
avoid unnecessary traversal; the remaining 186 top-level WEPPcloud cases and 60
utility cases were run directly. One unrelated run-catalog browser check initially
failed because its environment pointed at an absent Chromium directory. Rerunning
with PLAYWRIGHT_BROWSERS_PATH=/workdir/wepppy/wepppy/weppcloud/static-src/.playwright-browsers
passed. No application/browser installation changes were made.

Independent publication reviewer B approved the actual index, unchanged 74
unrelated entries, affected source hashes, and two intended nav additions.
Repository publication is complete; production deployment is not claimed.
