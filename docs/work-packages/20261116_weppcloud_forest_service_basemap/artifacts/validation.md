# Validation receipts

## Scope and environment

Development host: `forest.tail305ec9.ts.net`; representative populated run:
`mipa-awake-20261102/config`. Chromium software GPU, actual Flask/deck assets,
normal project access; dev-agent login used only for pointer selection. No
landuse modification was submitted. No production deployment occurred.

FSBASE-01 ancestor: `277d55fba`; FSBASE-02 ancestor: `abd9f6156`. Source/artifact identity is recorded by the package commit and hashes; `asset_manifest.json`
retains generated and served SHA-256 values. The controller bundle is generated
and ignored by Git; the landing export and local renderer distribution are tracked.

## Commands and outcomes

| Check | Outcome | Receipt |
| --- | --- | --- |
| `wctl exec weppcloud python wepppy/weppcloud/controllers_js/build_controllers_js.py` | Rebuilt served controller bundle | asset_manifest.json |
| `npm run lint` and `npm run export:landing` in weppcloud-ui-lab | Pass; normal large-chunk warning | fs-landing-lint.log, fs-landing-build.log |
| `wctl run-npm lint` | Pass | fs-lint-final.log |
| `wctl run-npm test` | 126 suites, 1,083 Jest tests and 9 Node tests pass | fs-tests-final3.log |
| Scoped Python: landing, Pure controls, dashboard template and route | 327 pass | fs-pytest-scoped-final.log |
| Scoped map Jest / adapter Node | 43 / 6 pass | fs-jest-scoped.log, fs-node-scoped.log |
| `wctl run-pytest tests --maxfail=1` | Stopped at operator request after 3,171 pass / 126 skip; no failures | fs-pytest-full.log |
| `python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master` | Pass; no changed production Python | fs-exceptions.log |
| `python3 tools/code_quality_observability.py --base-ref origin/master` | Observe-only report generated; no threshold failure | fs-code-quality-summary.md |
| Scoped `wctl doc-lint`, spelling previews, `git diff --check` | Pass; existing shared-doc spelling suggestions preserved | final closeout |

The host Python lacks Jinja2; the canonical container provides the controller
build environment. No dependency wrapper or production exception was added.

## Browser coverage

- `fs-acceptance.cjs/json`: actual run/dashboard selection, Terrain default,
  official resources, unchanged layer/view state, rapid switching and visible
  failure/recovery. All external-header captures use awaited allHeaders().
- `fs-deep.cjs/json`: real official labels/symbols, camera alignment, pan/resize,
  Deck picking, readable mobile credit, hostile attribution, rejected foreign
  resource URL and rejected redirect. Headers retain only absence booleans.
- `fs-edge.cjs/json`: wait for fully loaded out-of-coverage, zoom 19 and overzoom
  20 views; no unavailable status or global controller-limit change. Programmatic
  zoom 20 tests the adapter beyond the current UI limits.
- `fs-hydration.cjs/json`: missing/empty/unknown inherited initial selection,
  explicit Satellite/OSM/Forest Service, and unknown interactive no-op.
- `fs-edit.cjs/json/png`: authenticated Shift-drag hillslope selection and pointer
  click toggle over Forest Service; cancel selection and recover Terrain. No
  landuse-modification submission. Existing local credentials are read in memory.
- `fs-landing.cjs/json`: live exported light/dark pages, keyboard disclosures,
  and screenshots after visible animation completion.
- `fs-landing-route-check.py/json`: actual Flask routing and export reading;
  four supported routes serve their exported pages, and real absent, directory
  (unreadable), and invalid UTF-8 files return plain 503 without path disclosure.
  Only the export location is redirected for controlled failure cases.
- `fs-navigation.log`: retained legacy header resolves the existing user-guide
  endpoint with real Flask URL building. The obsolete fallback template is deleted.

Run retained browser scripts with Node from the repository root; they use the
existing static-src Playwright installation and write receipts/screenshots under
`/tmp`. Run the route-check script using `wctl exec weppcloud python -` with its
contents on stdin. These scripts are validation, not deployment commands.

## Broader smoke isolation

The existing dashboard-state-transitions and landing-keyboard suites produced
6 pass, 4 skip, 4 fail on this run. The four failures are missing Omni Scenarios
(two tests), cumulative graph title remaining “Graph,” and missing WEPP Yearly.
They reproduce identically when the four modified dashboard JS modules are
served from pre-implementation revision 277d55fba. See fs-existing-smoke.log and
fs-baseline-smoke.log. The retained fs-baseline-audit.spec.js was temporarily
placed beside the smoke suite, then removed after isolation. No baseline source
or live project state was rewritten.

## Limits and artifact observability

Default Terrain does not load the additional renderer. Selecting Forest Service
adds a second renderer/context and approximately 1.13 MB local JS/CSS transfer.
The active-camera software-GPU sample is quantified in renderer_evaluation.md;
it is not a general performance guarantee. No cross-browser or production rollout
claim is made. No project file, archive member or persistence schema is added;
existing archive/restore behavior therefore has no new migration obligation.

Correctness/security reviews independently pass for the source and browser scope.
The operator requested scoped tests on 2026-11-16; the broad run was interrupted
and the scoped checks above all passed. Full-suite completion is not claimed.


Source/documentation whitespace checks pass. Generated Vite shader strings retain
upstream trailing spaces so exported bytes and recorded served hashes stay exact;
these generated strings are excluded from the whitespace-only check. Retained
console logs have trailing whitespace normalized, without changing their results.
