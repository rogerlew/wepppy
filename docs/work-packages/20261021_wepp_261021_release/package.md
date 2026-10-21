# WEPP 261021 release

Status: complete — built and vendored locally, 2026-10-21. Not deployed.

Both binaries and sidecars are installed under `wepp_runner/bin`. Source is
canonical default branch `wepp_260430_negmeltfix_comparator`, commit
`a87925df9ffe6ebb928e126395dd159d484285fa` in
`/workdir/wepp-forest-release-20261009`.

The release fixes century-year Gregorian alignment, stale climate-buffer reads
at EOF and unchecked daily PASS dates. It retains 261010 ASCII PASS v3 and its
existing interchange reader. The native changelog includes both releases.
Regenerate all contributing hillslope and watershed outputs with the paired
release; retain valid Gregorian climate. No default switch or deployment.

Native suite: 232 passed; watchlist: 12/12; host/container smokes, provenance and
8 post-vendor runner tests pass. Fresh paired 400-year outputs contain 146,097
climate-aligned days. Both executables match the earlier validated repair after
excluding debug sections and build IDs.

WEPPpy segmented coverage: **11,052 passed, 122 skipped**, with all 11,173
collected cases accounted for. A combined-suite Redis authentication/test-order
failure passes in the complete isolated feature-access module (52 tests). The
final browser segment uses the existing browser cache with a process-local path
override. This is not a single-process full-green claim. Live-inventory snapshots
include 261021; 39 focused Builder/selection tests pass, including old-project
selection without config migration. See [coverage and limits](artifacts/coverage-plan.json).

[Plan](prompts/completed/release_execplan.md) · [Tracker](tracker.md) ·
[Release log](../../binary-lifecycle.md#vendored-wepp-release-log) ·
[Provenance](artifacts/provenance.json) · [400-year audit](artifacts/replay400-audit.json).
