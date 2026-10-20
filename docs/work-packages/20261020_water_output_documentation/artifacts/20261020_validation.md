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

The browser uses an isolated Flask process and a fresh temporary catalog, leaving
the dirty active index untouched. Screenshots are retained alongside
[browser_checks.json](browser_checks.json). This is not deployed catalog evidence.

The full repository pytest sweep initially passed 506 tests with 28 skips before
a stale literal expected binary hash failed. The expected hash now matches the
paired release. The sweep resumed after the 45 fully completed files, rerunning
the entire startup-contract file. It remains ongoing; do not count it as passed
until the final outcome is recorded. No Python execution errors remain in the
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

The active `generated/docs_index.json` was already dirty and root AGENTS explicitly
forbids editing it without a request. Permission to merge only affected entries
while preserving unrelated changes has been requested. Until approved and applied,
normal catalog navigation/search cannot be claimed complete. After publication,
reload catalog-caching processes through the normal deployment workflow and verify
normal-user routes/search against the published catalog. No service restart or
production write is included here.

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
