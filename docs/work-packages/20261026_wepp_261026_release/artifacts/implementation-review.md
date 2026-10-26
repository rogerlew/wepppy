# Independent implementation and release-linkage review

Date: 2026-10-26. Reviewer: science_review agent. Scope: numerical implementation,
candidate-to-release executable identity, and permanent regression. This is a
conditional review while complete release gates remain in progress.

No new numerical implementation finding. Exact U1 remains a bounded late-source
classification correction with separate reset state, direct terminal runvol,
native component validation, and unchanged physical peak/erosion paths. Prior
independent source probes and full first-watershed artifact checks remain
applicable to its numerical behavior.

Independently normalized both U1 and dated binaries with system objcopy, removing
only debug data and the GNU build-ID section. Complete normalized files match
byte-for-byte for both profiles. Normalized SHA-256 values agree with the
maintainer's equivalence receipt. Actual dated-file hashes agree with their
JSON sidecars and identify source b73e93b19a724d1991d341d38a18d11e742231bd on
the configured default branch. Retained independent evidence is
`independent-binary-linkage.json`. This establishes executable linkage; it is
not a substitute for complete runtime/release gates.

Reviewed the permanent generated candidate tests and the seven-test passing
receipt. They execute the candidate fixture over the full period, compare
observer output, assert generated SRC3 and hourly-bin operands, exercise the
actual native consumer via the independent probe, and require exact non-target
and legacy-record parity against a freshly generated baseline. The original
failing-baseline characterization remains separately pinned. Source diff from
the recorded build commit contains only rebuilt tracked executables, not
additional numerical source edits.

The newly introduced source path is supportable for the authorized release
scope, conditional on completing the full pinned-toolchain suite, both-profile
smokes/watchlist/provenance/artifact gates, second watershed, and
production-equivalent workflow checks. Results from an unpinned compiler
environment must remain recorded and attributed; do not classify that failed
attempt as passed. No unconditional release signoff is issued by this artifact.

## Release-runtime evidence checkpoint

Reviewed the completed pinned native receipt (534 passed, two warnings), dated
pair smoke/watchlist receipts, and second-project worker-container evidence.
Independently checked the second project's 491 unique successful hillslope rows:
all 2946 non-PASS comparisons and all legacy PASS comparisons are exact; only
H1, H327 and H394 gain one SRC3 record each. The fresh baseline reproduces
CHRQIN_INVALID_DURATION 534/394/0; the actual dated pair completes nine years
with exit zero and empty watershed stderr. Its hashes match the independently
verified release identities.

The retained output validator confirms complete 3288-day PASS calendars and
693768 finite daily channel rows across 211 channels. The production native
interchange receipt contains 16 readable finite Parquet outputs, including
1614408 rows each in hillslope PASS and watershed PASS event datasets and
693768 CHNWB rows. These are reviewed receipts, distinct from my independent
remote raw-artifact audit of the first experimental watershed. They establish
the requested second-project/runtime and generated-artifact evidence within
their documented bounds, not universal physical conservation.

No remaining numerical implementation or disclosure blocker identified for the
authorized source scope. Broad WEPPpy gate completion, final report gate counts,
metadata freezing and final artifact checks remain required before unconditional
release completion. Pending checks have not been relabeled as passed.

## Final implementation closure

Final disposition: **PASS for the reviewed source and dated binary pair**.
All previously pending gate-evidence conditions are satisfied. The broad ledger
covers all 11941 collected nodes: 11791 passes, 150 existing-condition test skips,
and one separate collection-module skip, with no missing nodes or unresolved
failures. Independently checked arithmetic and the 13 report-file hashes plus
the final collection hash, and inspected the summarizer's successful-teardown
and later-pass requirements. The earlier three failures are explicitly retained
and each has a later passing result; segmented execution is accurately disclosed.

Together with 534 native passes, the 12-case watchlist, generated regressions,
both-profile smoke/provenance checks, post-vendor compatibility tests, full
same-build watershed validation, and production-runtime interchange evidence,
the retained gates support the authorized bounded release. No numerical source
or runtime code changed after the previously reviewed build linkage. Final
report identity is SHA-256
`57320794cd53e86cb0d4ce699f635042f5d52b306ca279cfaee33cf1220e3d2c`.
No implementation blocker remains. Publication/download freeze and copying
verified artifacts may proceed under the user's existing authorization;
deployment remains outside this review's approval scope.
