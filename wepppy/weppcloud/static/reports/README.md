# Published Scientific Reports

Caddy serves this tree at `/weppcloud/static/reports/` using the existing
static-file route. Only publication-approved PDFs and public provenance records
belong here. Do not add legacy source, internal review records or raw run data.

- `wepp/release-notes/wepp_261010/`: revision 1, approved by Roger Lew on
  2026-10-10. LaTeX and authoring evidence remain in wepp-forest under
  `docs/release-notes/wepp_261010/`.
- `investigations/topanga-small-mutation-census-report.pdf`: unchanged version
  0.2 (October 6, 2026), copied from the retained WEPPpy investigation. Historical
  evidence, not final 261010 validation. Its bibliography includes internal
  work-package paths; those are provenance references, not public downloads.

Use explicit revision filenames for future updates; do not silently replace
issued PDFs. Copy approved bytes rather than rebuilding in WEPPpy, update the
adjacent manifest, and verify the downloaded SHA256 and PDF content type through
Caddy. Public URLs become available on each host when these files are deployed.
Document publication does not authorize model deployment or imply peer review.

## Technical Briefs

Approved WEPPpy Technical Briefs use
`wepppy/technical-briefs/<date-topic>/<date-topic>-r1.pdf` with an adjacent
`publication-manifest-r1.json`. Authoring sources, templates and guidance live
in `docs/technical-briefs/` at the repository root. Briefs explain point-in-time
user-facing changes and are distinct from binary release notes. The first
RRINIT brief, revision 1, was approved by Roger Lew on 2026-10-10 and is
published under `wepppy/technical-briefs/20261009-rrinit/`.
