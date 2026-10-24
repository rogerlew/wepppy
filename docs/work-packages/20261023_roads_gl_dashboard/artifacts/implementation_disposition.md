# Implementation review disposition

The reviewed contract ancestor `2399f835c` precedes all runtime edits. Independent
reviewers assessed working implementation and regression evidence; authors did
not approve their own changes. Canonical normative behavior remains unchanged.

| Finding | Severity | Disposition and retained regression |
| --- | --- | --- |
| COR-I01 | Medium | Accepted. Explicit preference validation restores numeric/string fields whose defaults are null. Jest exercises restoration; browser preserves year and maximum across both scope directions. |
| COR-I02 | Medium | Accepted. Reader rejects unsupported profile-scope enums; frontend uses conservative unclassified text. Real Parquet malformed-scope regression retained. |
| COR-I03 | Medium | Accepted. Restored dynamic-layer visibility runs existing activation/data-refresh paths. Live browser verifies yearly summary, graph and selection after both scope transitions. |
| COR-I04 | Medium | Accepted. Forward the server lifecycle reason through the scoped-query callback, including busy wait guidance. Hide the invalid scoped scene/legends/cached plots while retaining the sidebar Baseline escape; browser verifies no reload loop and fresh recovery. |
| SEC-I01 | Medium | Accepted. Generation check immediately follows delayed 409 body await. Independent reproduction and permanent Jest regression prove obsolete failure cannot poison newer success. |
| SEC-I02 | Low | Accepted. Validate nested CRS declaration shape; actual malformed artifact through map route returns sanitized422. |
| UX-03 | High | Accepted. Restore data-driving preferences before detection and basemap initialization; activate dynamic layers after discovery. Controls and fetched data agree. |
| UX-04 | Medium | Accepted. Empty, unavailable, partial-only and negative-only data do not receive a measured-zero scale. Separate state legend remains. |
| UX-05 | Medium | Accepted. Scope snapshot retains compatible graph options, Roads maximum and basemap selection. No cached result data is restored. |
| UX-06 | Low | Accepted. Maximum editing/reset updates existing controls and range label in place, preserving keyboard focus. |
| UX-07 | Low | Accepted. Line-width interpretation and remainder count precede the unavailable/negative-only legend branch. |

Independent correctness, security and UX implementation artifacts record final
passes and reviewed hashes. All eleven implementation findings are closed. These
passes do not replace the broad regression gate or authorize production deployment.
The nine earlier contract-review findings remain separately closed in
review_disposition.md; they are not conflated with runtime evidence.
