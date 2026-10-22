# Reissue validation and publication receipt

## Artifact identity

The owner authorized replacing the undeployed calendar-only 261021 pair.
Revision 2 uses committed native source
`d354e3c998f81955f9d9e5ca7d01ca56e1a9f04b` on the remote-default branch
`wepp_260430_negmeltfix_comparator`.

| Profile | SHA256 |
| --- | --- |
| Watershed | `e2c83b1a691fad3ffe29acf1588dadbecfeec9b027391df8b7fddcf4908d2971` |
| Hillslope | `81591bf0301604aa25002d641e3c8e5d22e15c747b179f1613e7c329233f4965` |

Native release, native `src/` and WEPPpy vendored files match exactly. Paired
sidecars preserve ASCII PASS v3, HBP-disabled status, MOFE/single-input support,
Gregorian validation and the existing interchange reader identity. Old hashes
and source are retained in `superseded-release.json`, both sidecars and native
release validation. No selected default or production deployment changed.

## Release gates

- Fresh native suite: **527 passed**, two existing tarfile warnings, 718.13 s.
  The 100-year watershed fixture retains its 900-second timeout.
- Native watchlist: **12/12**; both host profile smokes, artifact policy and ELF
  provenance pass.
- Post-vendor: both host and running-container profile smokes and provenance pass.
  Runner/output/binary-policy tests: **21 passed**, two existing warnings.
- Independent comparison confirms all 26 allocated ELF sections match the
  Cedar-tested d354 candidate, excluding GNU build ID. Whole-file normalized
  comparison also matches. This supports the retained 29 paired replays,
  400-year/146097-day run and 24-year Cedar study without substituting them for
  the fresh native suite.

## Broad WEPPpy coverage

The initial `wctl run-pytest tests --maxfail=1` was intentionally interrupted
inside the slow 230-case soil-artifact module after 2434 passes/48 skips in 661.49 s.
All completed modules are retained; the partial soil module is rerun in four
independent wctl processes. Its 230 cases pass (58,58,57,57). The remaining 8492
nodes are checked separately, with per-node report logs and an explicit
11173-node collection ledger. This is segmented validation, not an
uninterrupted full-suite pass. Final coverage: **11052 unique passes/122 skips**, every collected node
accounted for, including one collection skip.

The first shard launch used a report-log location outside the container mount
and stopped before executing tests. The retry uses the existing mounted pytest
cache. No application configuration, auth setting or test timeout was changed.

The combined remainder reports 8108 passes/74 skips and one failure in
`test_openet_signed_token_live_membership_admission`: Redis authentication
returns HTTP 503 instead of 403. This reproduces the initial 261021 release's
known combined-run isolation problem. The full feature-access module passes
**52/52** in isolation. The final **258 tests** pass with the existing installed
browser cache selected only for that process. No authentication or application
configuration was changed. The combined failure is retained, not relabeled a
clean single-process suite. See `coverage-summary.json`; the retained failure
log redacts synthetic JWT strings and records the original log hash.

## Approved technical report

Roger Lew approved the completed report: “Publish the reviewed report.”
Approved revision 1 has 24 pages and nine original figures. The 21-ID change
register, implementation/scientific review, original TeX/figures, sanitized data,
primary-reference checks and source freeze live in native
`docs/release-notes/wepp_261021/`. The reviewed draft hash remains in the receipt.
Only publication-status/revision text changed before final publication.

Public PDF SHA256:
`b4e894d013e4858e410ff8e2d265095ebebcde04fe68e3c25a665e3a9027f82c`.
The approved PDF and manifest are vendored under
`wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261021/`.
Local Caddy returns 200/application/pdf with the exact approved bytes; the served
manifest also matches. The existing Usersum changelog page returns 200 and links
to the new PDF. Prior 261010 reports and revision 2 link remain unchanged.
This verifies local publication mechanics, not production deployment.

Scientific/numerical review found no blocking report/source issue. Independent
raw-data checks cover all 24 annual integrals/maxima and 6048 plotted Cedar samples.
The report distinguishes source-cell integration, MC numerical storage,
geometric diagnostic volume, clipped rates and publication. Signed soil/routing
acceptance and negative-discharge clipping remain open. No field calibration,
universal physical closure or comprehensive sediment/nutrient validation claim.

## Retention and workflow observations

Detailed execution logs and per-node reports are retained under
`/workdir/wepp-261021-rerelease-20261021` and the local pytest cache; compact
receipts and release-gate logs accompany this package. Native source and figure
bytes in the Git index match the approved source freeze, including retained CSV
record endings. Earlier closed release packages remain immutable.

Usersum's configured full-vendor source points at a different historical checkout.
A wholesale synchronization would remove existing public history/report links.
This release copies the canonical 10/21 entries and current release note while
preserving older public rows. A future full-vendor-sync cleanup should reconcile
those lineages first; no persistent source-selection setting was changed here.

The WEPPpy test workspace retained preexisting UI and documentation edits;
those changes are excluded from the release commits. Native model source
identity and executable equivalence are independently pinned as described above.
