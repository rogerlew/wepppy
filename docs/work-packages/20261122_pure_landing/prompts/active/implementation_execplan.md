# Deliver a theme-aware WEPPcloud landing page

This ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
Progress, Surprises & Discoveries, Decision Log, and Outcomes &
Retrospective current.

## Purpose

Render `/weppcloud/landing/preview/` so visitors can review a maintainable
WEPPcloud home page that uses the same navigation and theme as Interfaces,
Runs and reports. Preserve the current public landing throughout review.

## Progress

- [x] (2026-11-22 19:02 UTC) Inventory content, shared shell and UI Lab consumers.
- [x] Commit the reviewed contract and record its revision in the tracker.
- [x] Verify the locally served route, data states, theme and keyboard behavior.
- [x] Restore the Deck.gl Atlas, preserve ordering and verify the Forest review deployment.
- [x] Verify Ctrl-wheel zoom and the overlaid legend and tip on Forest.
- [x] Filter Atlas rows at normal compilation and verify the resulting public feeds.
- [x] Disposition desktop/mobile design findings and verify the revised Forest preview.
- [x] Restore the shared site masthead and verify Interfaces style parity on Forest.
- [x] Verify the four direct desktop destinations and mobile hamburger on Forest.
- [x] Restore the original text introduction without its action row.
- [x] Remove decorative link arrows and restore shared link decoration.
- [x] Verify inline funding, credits and legal text on Forest at desktop, phone and 200% zoom.
- [x] Restore the nine original affiliation captions and inspect the rendered cards on Forest.
- [x] Restore the resource marks and inspect the three cards on Forest.
- [x] Add the WEPPcloud Stack repository directory under Help and resources.
- [x] Verify the 13-row GitHub table, private-model notes and phone layout on Forest.
- [x] List the Rust CLIGEN port beside the Fortran generator.
- [x] Checkpoint the accepted preview design and assess cutover and retirement.
- [ ] Complete manual assistive-technology review.
- [ ] After human approval, cut over and retire UI Lab.

## Surprises & Discoveries

Forest Service run and dashboard maps load MapLibre from
`wepppy/weppcloud/static/ui-lab/maplibre/`. The landing migration and
retirement must preserve this independently used renderer.

## Decision Log

2026-11-22 UTC. Use `base_pure.htm` and a scoped stylesheet for consistent
layout and themes. Use a native year filter and paginated atlas table for
access to the existing snapshot without a map renderer or client package.
The operator subsequently clarified that the Atlas is the visual hero.
The operator rejected the CSS-map preview and requested reuse of the
Deck.gl map, removal of access-year controls, and original section order.
Reuse the production CARTO Positron vector basemap and Deck map controller.
The raster CARTO trial returned a watermark, and the temporary Terrain
candidate was superseded by the operator's request for the production
basemap. Keep the Atlas's on-map run ID labels, geographic text summary,
and keyboard navigation. The operator removed the project-details
disclosure and inspection paragraph. Restore the original Ctrl-wheel gesture and
upper-left run-type chips, with the scroll tip in the lower right.

The operator chose normal scheduled snapshot rollover for Atlas publication.
Check explicit visibility during compilation before writing each location row.

## Outcomes & Retrospective

The operator accepted the Forest preview design. The [cutover assessment](../../artifacts/20261122_cutover_assessment.md) records the remaining release work. Focused pytest,
frontend lint and tests, and the public-page browser checks passed.
The public cutover remains pending human approval and manual
assistive-technology evidence. See the package tracker for the
blocked broad preflight and the review artifact for direct evidence.

## Plan and validation

Review and commit the checkpoint under `artifacts/` with the canonical
contract before editing templates, routes or tests. Add a preview handler
in `wepppy/weppcloud/routes/weppcloud_site.py`. Add Jinja and scoped CSS
under `wepppy/weppcloud/templates/` and `wepppy/weppcloud/static/css/`.
Reuse the site's existing route mount and theme controls. Use the snapshot
resolver already used by the public atlas. Verify real populated, empty,
missing and malformed snapshot states and bounded year and page inputs.
Use a snapshot fixture to verify data escapes at the rendered response.

Run focused landing route pytest checks and existing CSS/frontend gates
through `wctl`. Load the preview on a development instance and inspect
the real DOM, stylesheet, assets, signed-in links and persisted theme.
Capture wide and narrow layouts, keyboard focus and axe results for all
five AA themes. Add manual accessibility evidence following the Access
Board baseline and report any unavailable checks in the tracker.

After human acceptance, record approved URL compatibility, move the
locked shared renderer and license to WEPPcloud's static vendor path and
verify its served boundary. Remove Vite code, generated landing assets,
environment and build wiring, stale live docs and obsolete tests. Verify
the new home and landing URL, saved bookmarks per the approved disposition,
and real Forest Service rendering on Runs and dashboards. Use the current
task branch for review and integration.

The isolated development instance can use a disposable mount for a synthetic
snapshot and the checked-out app, without remounting the shared development
stack. Build the existing Pure CSS vendor assets using
`wctl --project-dir /home/workdir/wepppy-pure-landing run-npm build` when
the development checkout lacks those ignored artifacts. Serve the generated
Pure CSS files through the shared static path before judging the rendered
preview. The preview adds no asset build to that existing setup.
