# Independent unrutted fixture adjustment review

Date: 2026-10-23. Reviewer: `accounting_contract_review`.

**Approved bounded test-design adjustment; no production geometry change.**
Reviewed suite contract SHA-256:
`4cc8731d2ec5301596be19544226049100ea28978bb44cc7c8588fbf2f21231c`;
fixture decision SHA-256:
`71970a183536b60adf7420c774a0d54a982e2b91c247c7cd25ad0260e0757138`.

The full-upload failed manifest contains exactly two failures for prepared
`roads-seg-000001`, source OSUNUM `6`, Topaz 271/272 (WEPP 61/62), and the current
receipt is absent. Retain this as negative acceptance evidence. A new positive
project may exclude that exact hash-bound source feature, with declared counts
and exclusions. It still must complete real replacement routing, summaries and
accounting. Further automatic exclusions or silent successful-row filtering are
not approved. The 516-case portable matrix remains complete and unchanged.

Independent read-only production-helper calculations reproduce the rejection;
see [geometry diagnostic](20261023_unrutted_geometry_diagnostic.json). Both
crossings sample distance-to-channel 188.450790405 m, yielding downstream landuse
158.450790405 m with fill length 30 m. The representative hillslope lengths are
140.509667992 and 69.053322936 m; transformed road lengths are only 5.771508086 and
9.467096210 m. Resulting upstream lengths are -53.712630500 and -128.864563679 m.
Thus this is a limitation of the current combination of sampled downstream
distance and representative hillslope geometry. A 300 m road-clamp explanation
or claim of physical road infeasibility is unsupported. The original `Length`
attribute is 1004.06 m; the prepared segment measures 204.012211698 m.

Keep the failed full-upload and positive subset outcomes visible in the report.
The four project cases test controller/accounting behavior; their watershed
differences are not pure design effects because the unrutted road inventory
differs. No unmodified whole-site unrutted success is certified. Source and
baseline hashes must remain unchanged in both attempts. This approval concerns
the revised fixture scope; positive execution evidence is still required.
