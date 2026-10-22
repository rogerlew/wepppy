# WEPP 261021 reissue and technical release report

Status: complete (bounded binary reissue and approved report publication). The operator explicitly authorizes replacing the undeployed
261021 pair with the reviewed physical-water repairs and requests detailed
release notes explaining the defects, investigation and figures. This supersedes
the earlier prohibition on overwriting that artifact name for this reissue only.
The closed initial release package remains immutable history.

[Plan](prompts/active/rerelease_execplan.md) · [Tracker](tracker.md).

Ship source d354e3c99 from native default branch, retaining ASCII PASS v3,
calendar fixes, existing capacities, banner and default binary selection. Keep
MC dynamics/storage authority; disclose unresolved signed exchange and clipping.
This is release of validated implementation fixes, not completion of the physical
water-closure work package. Regenerate every contributing hill/PASS/watershed
output with the same reissued pair; identical filenames do not establish identity.

Build and validate through the existing release tooling, then vendor both
binaries and complete sidecars together. Preserve previous hashes and source
identity in the release ledger. No production deployment is requested.
Prepare a detailed TeX/PDF report following native release-note authoring policy,
with scientific, implementation and disclosure review. Public PDF distribution
is separate from authoring and binary vendoring; keep the review PDF outside
public static paths until its reviewed edition has owner approval.

## Approved report

Roger Lew approved publication on 2026-10-21: “Publish the reviewed report.”
The [24-page report, revision 1 (PDF)](/weppcloud/static/reports/wepp/release-notes/wepp_261021/wepp_261021_release-notes-r1.pdf) includes nine figures.
The paired public manifest and downloaded PDF agree on SHA256
`b4e894d013e4858e410ff8e2d265095ebebcde04fe68e3c25a665e3a9027f82c`.
Existing Usersum changelog navigation and local Caddy download return 200;
prior 261010 reports and links are unchanged. See
[download receipt](artifacts/report-download-check.json).

## Final validation

Fresh native 527 tests, watchlist 12, both profile smokes and provenance pass.
Post-vendor 21 tests and both container smokes pass. Segmented WEPPpy coverage
accounts for all 11173 nodes: 11052 passes/122 skips. The known combined-run
feature-access Redis failure is retained; its 52-case isolated rerun passes.
See [validation receipt](artifacts/validation.md) and
[coverage ledger](artifacts/coverage-summary.json). Physical-water closure
remains a separate open package.
