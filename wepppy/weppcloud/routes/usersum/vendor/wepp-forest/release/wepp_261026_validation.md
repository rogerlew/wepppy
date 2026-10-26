# WEPP 261026 validation

Status: all scoped release gates pass. Release/vendoring and report publication
are complete; no project-default switch or production deployment is included.

## Identities and build

- Model source: `b73e93b19a724d1991d341d38a18d11e742231bd` on verified remote-default branch
  `wepp_260430_negmeltfix_comparator`.
- Portable test/replay checkpoint: `d2f227244`; no model source change afterward.
- Watershed SHA-256: `a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48`.
- Hillslope SHA-256: `0955134900c63378d7990a1c36a477dd9056e4c7db8de7528a9b486192f6976d`.
- Report SHA-256: `57320794cd53e86cb0d4ce699f635042f5d52b306ca279cfaee33cf1220e3d2c`.

Build command: `TARGET_TAG=261026 COMPILER=/usr/bin/gfortran tools/build_wepp_dated_release.sh`.
Profiles built sequentially. Generated hill-profile include copies were restored
to the committed watershed copies after building; capacities and banner remain
unchanged. System GCC 13.3 and `/lib64/ld-linux-x86-64.so.2` provenance checks pass.
Complete normalized ELF files match the reviewed U1 pair after removing debug
information and GNU build ID only. Independent review reproduced that result.

## Executed gates

- Full native suite: **534 passed**, two warnings, 513.08s, with system compiler
  pinned in PATH. Portable incident regression: seven passes.
- Permanent watchlist: **12/12**. Both-profile native smokes and artifact policy pass.
- Post-vendor provenance and both host/container profile smokes pass.
- Runner/capability/PASS/AgFields/Roads compatibility: **89 passed**, one existing
  skip because the old watershed fixture lacks its PASS dataset.
- Builder/persistence selection: **40 passed**, including choosing 261026 on an
  older project without rewriting its saved configuration.
- Broad WEPPpy: **11,791 unique passes**, 150 test skips plus one collection-module
  skip. Every one of 11,941 collected test nodes is accounted; no unresolved
  failure. Execution was segmented after interrupting the slow Rosetta matrix.

The broad gate began while native gates finished; the targeted checks ran after
vendoring. Complete node/hash accounting is in `logs/wepppy-coverage-summary.json`.
No collected test was excluded, and no numeric tolerance was relaxed.

## Artifact and production-runtime acceptance

The primary 491-hill/211-channel nine-year U1 replay transfers to the dated release
by exact executable equivalence. All 2,946 non-PASS files and legacy PASS streams
match a fresh same-context 261021 baseline; two SRC3 records change.

The second project ran the actual dated pair inside the production worker
container: 491 hills, 211 channels, 3,288 days; empty stderr, 112.52s watershed time.
Its fresh 261021 baseline reproduces element 534/hill 394/zero duration. All 2,946
non-PASS files and legacy PASS streams match exactly; three SRC3 records change.
All 693,768 channel daily rows are finite, with no negative reported fields.
Outlet dates complete through 2024-12-31. Original projects/services are untouched.

Production native interchange retains 16 finite Parquet files, including 1,614,408
hillslope PASS rows, 1,614,408 watershed PASS event rows and 693,768 channel rows.
The replay harness now mirrors normal `.out` promotion and version-manifest
ordering. Initial omissions are retained in failure logs; no production reader
or model changes were needed to correct the harness.

## Failed attempts and limits

An unpinned Homebrew compiler caused channel-test errors; the complete pinned
system-compiler suite passes. The first new regression used the wrong SRC3
position after a multiline EVENT; corrected record parsing passes. Broad tests
contained stale installed-release lists; expectations now include 261026 and the
new persistence case passes. The browser chain passes using its already installed
cache. Earlier failures remain in evidence and have later passing results.

The source metadata preserves the existing midnight effective-support rule,
not actual hourly placement. Physical hillslope peaks/erosion stay unchanged;
signed exchange and raw-discharge clipping remain open. Artifact completeness
and reader success do not prove universal physical closure or observational fit.

The 49-page/13-figure cumulative report preserves prior study identities and
issued editions. Independent scientific, implementation and disclosure reviews
pass for the frozen PDF. Text/figure/identity checks and a hash-matched local
Caddy download pass; these reviews do not claim human peer-review certification.
