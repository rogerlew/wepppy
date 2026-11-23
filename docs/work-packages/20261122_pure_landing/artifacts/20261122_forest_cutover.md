# Forest landing cutover

Home now serves the approved Jinja landing at
[Forest](https://forest.tail305ec9.ts.net/weppcloud/). The operator approved
preserving the Atlas as reviewed. The implementation is `c234f659f` on
`task/pure-landing`. Forest development serves `faa6cc2b4` on
`deploy/forest-pure-landing-cutover`, a scoped deployment on its existing
`6c1847dc5` base. No production deployment was performed.

## Served evidence

- Home and landing returned 200 with no-store caching. The three old page
  URLs redirected to mount-aware home. A browser preserved repeated and
  encoded query parameters and navigated to the hero, about and map anchors.
- Forest's prior snapshot had 101 records, 23 with a current PUBLIC marker.
  One run of the existing compiler with its normal Forest batch identity,
  inputs, output paths and publication lock produced 23 entries. All 23
  resolved to explicitly public projects. All four existing JSON aliases
  served the 23 records; the old static snapshot returned 404. The daily
  scheduler continues using that compiler. The indexable Jinja home embeds
  the published public snapshot, and search engines can retain indexed copies.
- The old export and Vite icon/asset URLs returned 404. The temporary Caddy
  review rule and review container were retired. The cutover adds no
  environment configuration. The Git history retains the prior releases.
- The vendored MapLibre 5.24.1 JS, CSS and license returned 200 with the
  hashes in the [assessment](20261122_cutover_assessment.md). Chromium
  rendered the Atlas with Deck.gl and real CARTO vector tiles and exercised
  zoom and reset. On a Run and a GL dashboard, Terrain and Forest Service
  switching worked. The browser recorded 43 Forest Service resource
  requests and zero page errors.
- Focused Python suites passed 53 tests; six Forest Service Node tests
  passed. Full-page Chromium axe reported zero automated violations on
  the deployed home across the five supported AA themes. Axe left contrast
  checks for manual review. Manual assistive-technology conformance remains
  open. The earlier broad pytest preflight is documented in the assessment.
- The updated Playwright keyboard smoke passed against Forest's canonical
  home, including the skip link, About links, Atlas focus and its buttons.
