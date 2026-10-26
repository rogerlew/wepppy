# Release gate evidence

Native model source: b73e93b19a724d1991d341d38a18d11e742231bd on verified
remote-default branch wepp_260430_negmeltfix_comparator. Tests/replay correction:
d2f227244. Both full normalized executables match the reviewed U1 candidate;
only debug information and GNU build IDs were removed for comparison.

Native gate: **534 passed**, two warnings,513.08s; required system compiler in
PATH. Watchlist12/12; both profile smokes, artifact policy and provenance pass.
Post-vendor host/container smokes and provenance pass. Compatibility:89 passed,
one existing skip because the old watershed-PASS fixture lacks pass_pw0 data.
The real generated watershed PASS is additionally read by the production native
reader below; no parser tolerance or model guard was relaxed.

Second isolated production-container replay:491 hills,211 channels,nine years,
empty stderr; baseline reproduces534/394/zero duration. All2,946 non-PASS files
and legacy PASS lines match exactly; three SRC3 records change. All3,288 dates
per hill and693,768 channel daily rows validate; no negative reported channel
fields. All16 final Parquet artifacts contain finite floats:1,614,408 H.pass
rows and1,614,408 watershed-PASS event rows. No global closure or physical
within-day timing claim. Original production projects/services were unchanged.

Harness corrections retained: first reader call omitted normal `.out` promotion;
subsequent bare hillslope converter lacked the version manifest supplied by the
normal aggregate workflow, allowing watershed compatibility cleanup to remove
H.pass. Mirrored those existing lifecycle steps and regenerated/verifiably read
H.pass alongside all other artifacts. No production code changes were needed.

Broad suite: all 11,941 collected nodes are covered by retained segmented runs:
**11,791 unique passes, 150 test skips**, plus one collection-module skip.
The canonical run was interrupted in the slow Rosetta matrix; the remaining
segments cover every collected node. Stale installed-binary expectations were
updated, and the browser chain was rerun with the existing installed Playwright
cache. All earlier failures have later successful runs, including teardown.
No exclusions or numeric tolerance changes. See `coverage-summary.json` for
collection/report hashes and the complete coverage ledger. Selection and old
project persistence: **40 passed**.

Report: final **49 pages, 13 figures**, derived from 261010 with inherited 261021
methods and fresh 261026 evidence. Independent scientific, implementation and
disclosure reviews pass for the frozen edition. Document validation passes
numeric anchors, identities, coverage, source hashes, page bounds and absence of
attachments/scripts. Two Poppler XML-invalid math glyph codes on page 36 retain
their word bounds during parsing; visual inspection confirms correct rendering.
PDF SHA256: `57320794cd53e86cb0d4ce699f635042f5d52b306ca279cfaee33cf1220e3d2c`.
Local Caddy download returns HTTP 200/application/pdf with matching bytes and
manifest; Usersum navigation resolves and previous report links are preserved.
See `report-download-check.json` and final review artifacts. Owner authorization
covers this release and revised report, not a separate human final-PDF review.

Native release/artifact commit: `8d89b0c194e09504f6d4bba0a985ce48debdea86`.
All 109 incident checksums and frozen report sources matched staged Git bytes;
raw evidence attributes preserve CSV/log bytes. Both paired sidecars and binaries
match the native release. Source and binary identities are retained in sidecars.
No production deployment or default switch was performed. Effective support
still starts at midnight; these gates do not establish actual subdaily timing or
universal conservation. See ADR-0107 for the accepted scope and rationale.
