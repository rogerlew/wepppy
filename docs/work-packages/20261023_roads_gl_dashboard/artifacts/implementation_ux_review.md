# Roads GL implementation UX review

Reviewed 2026-10-24 05:57 UTC against the implementation worktree based on
checkpoint `2399f835c3637f47468f98cf694089891ca34cc1`. This review follows the
accepted Roads GL contract and the earlier `ux_review.md`; UX-01/02 remain closed.
No runtime files or project artifacts were changed by this reviewer.

## Evidence and limits

Read `roads.js`, dashboard initialization, scenario guards, dashboard templates,
state defaults, layer detectors and graph controller paths. Independently read
the three smoke-test definitions and `/tmp/roads-browser-final.log`: all three tests
passed (42.6 seconds), covering the actual resource's aggregation oracle, rendered Roads layer,
keyboard table selection, scope navigation in both directions, literal hostile
labels and optional 503 isolation from Baseline results. This reviewer did not
execute those browser tests. Parent-reported counts of 39 features/34 complete
lines are not independently established by that summary log.

The additional browser test retains the first available yearly selection, its
loaded summary and active yearly graph, and a maximum of 27 across both scope
directions. The broad suite remains in progress; its result is not claimed here.
Static review plus these smoke results is not a human
usability study, accessibility certification, production deployment validation,
or evidence for every graph, narrow-screen layout or unavailable-state branch.

## Findings and disposition

| ID | Severity | Exact surface and user consequence | Smallest correction and disposition | Observable acceptance check |
| --- | --- | --- | --- | --- |
| UX-03 | High | `gl-dashboard.js::initializeDashboard`, original post-detection `restoreDisplay`; selected year/statistic could disagree with already loaded map values. | **Resolved in code.** Validated preferences now restore before detector/basemap initialization; dynamic visible layers use activation or refresh after detection. | Change year/statistic, switch scope and compare selected values with actual loaded summary/year; exercise a nondefault yearly value. |
| UX-04 | Medium | `roads.js::buildLegend`; missing or negative-only results previously received a measured-zero legend and numeric maximum editor. | **Resolved in code.** No-complete and negative-only states now have explicit text without a nonnegative scale or override. Remainder counts precede this branch. | Empty, partial-only, single-storm and negative-only payloads never claim measured zero; genuine zero data remains distinguishable. |
| UX-05 | Medium | `roads.js::scopeNavigationUrl`, `DISPLAY_KEYS`, and initialization; compatible graph options, Roads maximum and rendered basemap were lost across scope navigation. | **Resolved in code.** Graph preferences and Roads maximum serialize with explicit nullable type validation; restoration precedes basemap construction. | Round-trip a custom maximum, nondefault basemap and supported graph options; verify both controls and rendered content retain the compatible choices. |
| UX-06 | Low | `roads.js::buildLegend`; replacing the maximum editor/reset removed the focused element. | **Resolved in code.** Maximum changes/reset now update the existing input and range label in place, preserving DOM focus without a forced focus jump. The browser round-trip test edits the maximum and presses Tab successfully. | Edit maximum and reset using keyboard; focus remains visible and users can continue forward and backward through controls. |
| UX-07 | Low | `roads.js::buildLegend`, early return for no-complete/negative-only data; the line-width interpretation disappears while gray/purple lines still render. | **Resolved in code.** The existing line-width sentence now precedes the early return, alongside the remainder count; it remains present for every legend state. | No-complete and negative-only legends retain both remainder exclusion count and the note that line width is a visibility aid rather than modeled width. |

## User task assessment

The native Output scope selector identifies the current scope and remains
separate from Roads soil detachment visibility. Roads mode disables incompatible
map scenario/comparison controls with a visible reason; the scenario manager also
guards programmatic activation. Unsupported Flow Duration is cleared during scope
navigation. Compatible graph settings retain their existing semantics.

Table buttons provide a keyboard route to persistent details and move focus to
the selected segment. Text construction preserves labels as literal content.
Details distinguish modeled source road-segment length, annual mass, modeled area
and full-profile detachment. The implementation draws centerlines and uses jet2;
it introduces no inferred off-road footprint or new configuration system.

Optional-layer failures clear Roads output without poisoning baseline results.
The unavailable entry template preserves a Baseline navigation link. These
patterns satisfy the reviewed task flow; remaining browser checks should verify
the specific restored selections rather than just the presence of a layer.

## Reviewed snapshot and verdict

- `wepppy/weppcloud/static/js/gl-dashboard/roads.js`: `b3841ff287b1bd62653bf6aae44780e5ad5e54717e6d652965471133b0006f9f`
- `wepppy/weppcloud/static/js/gl-dashboard.js`: `d456c2d8735f6482d9bc1f112b928399c84d57fd86eb0859bf9c820face37528`
- `wepppy/weppcloud/templates/gl_dashboard.htm`: `f17dbcba987dcd92f6714b3a2db3fe68184e5dca135598c5ae0627e8d665a63e`

**Pass; UX-03 through UX-07 resolved.** No unresolved UX findings in the
reviewed code. Final recheck includes the in-place maximum editor, all-state
line-width note, updated source hash and three passing browser tests. This verdict does not waive the implementation plan's remaining
browser, regression or artifact-validation gates.

## Final bounded correction recheck

Independently inspected the maximum-input rejection branch: blank, zero and
other invalid edits restore the displayed active maximum without replacing the
control or changing the applied scale. This preserves UX-06 closure and prevents
a misleading zero entry beside an unchanged positive legend. The reviewed
`roads.test.js` regression checks zero rejection, a valid override, retained
focus and blank rejection after that override. Additional scenario-manager test
cases verify that root and child Roads scopes reject programmatic map scenario
and comparison re-entry without queries or state changes. These are inspected
test definitions, not a newly executed test run by this reviewer. The source
hash above includes this correction. UX verdict remains **pass**, with all
findings closed; the broad Python suite is still pending.
