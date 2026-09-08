# Native totalwatsed3 release integration

The daily watershed producer now requires
`wepppyo3.wepp_interchange.totalwatsed3_to_parquet`. The public
`run_totalwatsed3()` facade retains its arguments, schema and output `Path`;
Python resolves paths/scalars/ash metadata and Rust performs all table work.
The Python/DuckDB/pandas producer is removed without a runtime fallback.
See the [runtime contract](../../wepppy/wepp/interchange/wepppyo3-interchange-spec.md#native-daily-watershed-producer).

## Paired release

The py312 release shared-object SHA-256 is
`bf21f5e5aea9a7c690b7f48926d74f8bb412269d4127b74a166a1e0ef598a354`.
The Docker startup preflight pins this hash and requires the new API. Update
WEPPpy and the native release together. Missing or stale support fails through
the existing required-native error contract before output replacement.

The paired native release revision is
`bb7451eeb83690e0ffc5f5eed7c4f4c9c1688d23`. The common runtime
[publication workflow](../../.github/workflows/publish-weppcloud-image.yml) pins
that exact revision and publishes an immutable commit-derived image tag on a
trusted master push. The native package's artifacts/publication.json records
repository/LFS verification and the final image digest once publication finishes.
Per-file source and binary hashes are preserved in its
artifacts/release-integration-manifest.json. This note does not claim a production
deployment. User authorization and compatibility decisions are in the native
package's release/integration and review/publication authorization sections.

## Compatibility and validation

Preserve all 79 columns, metadata, units, nulls, subsets, ash semantics, and MOFE
outlet lateral flow. The approved current-producer single-OFE oracle is retained
beside the original historical fixture. There are no formula or default changes.
Installed native-release tests pass 89 cases; the public facade matches 25 frozen
oracles. Targeted downstream suites cover return periods, water balance, DSS,
WATAR, RQ stage, batch/culvert retries, migration and query-engine consumption.

The real Forest Compose worker, UID 1000/GID 993 and umask 0022, completed the
5,860-hillslope production RQ stage, dependent parity/water-balance/query-catalog
processing, and a subsequent 586-hillslope job under a 12 GiB limit. Final reviewed-release peak was
903,184,384 bytes (861.34 MiB), with no OOM events or restarts in the passing run.

The first workflow attempt exposed a separate documentation OOM after native
publication: README generation loaded entire input Parquet tables to show three
rows. It now reads only the schema and the first three-row batch. Regression
coverage includes empty inputs and previews spanning multiple row groups.
Raw failed/passing workflow evidence and remaining review/publication status are
in the native package's artifacts/forest-compose-integration.md and tracker.md.

The final broad WEPPpy sanity run passed 7,723 tests with 72 skips, including
all three bounded-preview regressions. The targeted interchange/startup suite
passed 83 tests with one skip. Stub completeness, changed-file broad-exception
enforcement and documentation lint pass. Independent correctness, QA and security
reviews closed nullable-area, first-NaN ash metadata and malformed-footer error
handling defects. Three extra frozen parity cases and eleven malformed-footer
regressions cover these repairs. Completion logs report native output paths
correctly for the three-path call.
