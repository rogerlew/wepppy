# Publication Review: TB-20261009-RRINIT

Status: revision 1 approved by Roger Lew on 2026-10-10.
Decision: "i approve the technical brief for publication". This document-specific
decision supersedes the prior draft hold. Parameter adoption (ADR-0083), brief
publication and model deployment remain separate.

Author checks cover retained study numbers, source identity, units, scope,
template/lookup precedence, PDF layout and AI disclosure. No new model runs.
No raw legacy code, internal absolute paths or raw data attachments are included.

The literature review is not re-presented as a new independent literature
assessment. Model-mechanism statements cite the retained source analysis.
No claim of field calibration, universal ranking or deployment is made.

Publication owner: Roger Lew. Decision/date: approved, 2026-10-10.
Independent peer review: not performed or claimed.
Approved PDF/manifest are vendored in the static reports tree. User-facing
links are added to Disturbed ENDUSER and the existing Usersum WEPP page.

## Author Verification: 2026-10-10

- Five-page PDF and reusable template compile without warnings or unresolved references.
- All five brief pages visually inspected; table labels and units are readable.
- `python verify.py` checks 16 retained comparisons, rounded numeric anchors,
  source identity, PDF text bounds, publication markings and absence of attachments.
- Scoped `wctl doc-lint` passes. No model code, defaults, binaries or historical
  work-package artifacts changed; no new simulations or private fixture gates.
- Source/PDF/evidence hashes are recorded in `document-checks.json` and
  `publication-manifest.json`; these are author checks, not independent review.

## Publication Handoff: 2026-10-10

Revision 1 is copied to the intended static path with its public manifest.
Local Caddy returned HTTP 200 and `application/pdf`; the downloaded hash is
`612c14bdfbee0018f2088abbfa2411f7ceb5c22c91b2f47f92478a30bd4f9e75`, matching
both the vendored PDF and manifest. The served manifest is byte-identical to
the authoring manifest. No new Caddy route or service was needed.

The generated Usersum index was left untouched. No model implementation,
parameter changes, simulation reruns or production deployment occurred.
