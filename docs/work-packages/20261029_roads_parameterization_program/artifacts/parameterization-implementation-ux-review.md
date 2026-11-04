# Roads parameterization implementation UX/frontend review

Status: **passed independent final local UX review, 2026-11-03 (operator date)**. Approved ancestor:
`73b5da4ac`. This review assesses the actual controller, Jinja view, route payloads
and rendered interface, not the superseded static proposal.

## Scope and method

Review `roads_parameterization.js`, `templates/roads/parameterization.htm`, Roads
route handlers, actual `query_parameterization` shape, and focused frontend/route
coverage against the accepted project/view contract. Use a separate authenticated
browser inspection on the disposable workflow project after coordinated code
reload. No production edits are made by this reviewer.

The dedicated route receives server-derived seed data through Jinja `tojson`;
controller rendering uses textContent, not interpolated HTML. Source baseline,
adjustment and resolved values come from backend groups, not hard-coded demo
numbers. Overrides submit the complete role/parameter object through the existing
parameter route; pending requests have local ownership and mutation controls lock.

## Findings and disposition
All findings below are closed for the approved local implementation scope.
Historical reproductions and diagnosis sections remain retained below; their
pending wording describes earlier checkpoints, not this final disposition.

| ID | Severity | Location and user consequence | Final disposition and acceptance |
| --- | --- | --- | --- |
| IU-01 | Medium | Controller `controls()`: editing was available during native work. | Actual custom Run busy GET returned a disabled Edit button and a clear active-operation message. |
| IU-02 | Medium | Controller `onInput()`: transient numeric input was rewritten. | Actual empty input stayed empty with Save disabled; typing `0.125` preserved the text and preview. |
| IU-03 | Medium | Controller `renderComparison()`: backend/display shape mismatch hid actual comparisons. | All 12 rendered baseline/custom/difference cells match the populated query; units, years, area, provenance and PASS EVENT scope are visible. |
| IU-04 | Medium | Controller `render()` and Roads `query_parameterization()`: design alone implied actual role use. | Actual groups 1/2 label road/fill/buffer used; group 3 labels all three unused. Pre-execution roles are explicitly potential. |
| IU-05 | Medium | Roads historical discovery and controller `renderReadback()`: Save could lose or mislabel prior actual inputs. | Custom Save retained 35 default profile readbacks with explicit Historical settings text; completed custom run displays its own current snapshot and 420 emitted values. |
| IU-06 | Low | Source cells and readback: opaque keys/hidden source identity obscured meaning. | Visible source filenames, adjustment arithmetic, units, profile/input identifiers and completion time match actual data. |
| IU-07 | Medium | Template `.rp-table-wrap` and `[data-rp-group]`: page overflow at narrow widths. | Containing-block and select-width fixes yield 390/390 and 1440/1440 viewport/document widths with populated data; tables retain their own keyboard-focusable scroll region. |
| IU-08 | Medium | Controller `sameOverrides()`: object key order misclassified default state. | Canonical value comparison is covered by frontend tests; actual custom state matches saved entries. Independently inspected `ui-reset-desktop.png` says Default inputs after all 12 entries reset to default; mobile remains 390/390. |
| IU-09 | Medium | Route `roads_parameterization`: busy GET returned raw 409 JSON. | Actual busy GET returned HTTP 200, a complete page and explicit reload-after-completion guidance, with zero JavaScript errors. |
| IU-10 | Medium | Template `script_extras`: missing shared stale-bundle guard could leave users on outdated controls without reload guidance. | Added the established deferred guard after the bundle. Actual final page loads it, expected/actual build IDs match, and no false update banner appears; complete populated UX rerun passes. |

The final review also confirmed the corrected repository-default status and native
conversion disclosure requested by correctness review. The displayed matching
status is actual live evidence; changed/unavailable repository states have source
and frontend/backend test coverage, not a live repository mutation experiment.
No new blocking usability finding remains. Profile details keep 35 completed
readbacks collapsed by default, and the existing group selector distinguishes
mixed templates without adding tabs or duplicate controls.

## Evidence and limits

Independent browser driver:
`artifacts/parameterization_implementation_ux.mjs`. It uses the existing canonical
agent login, retains no credentials/tokens, performs only GET requests and local
unsaved edits followed by Cancel, and writes screenshots/readback under
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-implementation-ux-v1/`.
Do not infer persistence/native workflow success from these display checks; the
separate workflow validator owns real Save/Prepare/Run/fork/archive evidence.

Final source hashes and independent rendered results appear in the final evidence
section below. Earlier pending checkpoints are retained as history.

## Independent live unbound readback

Authenticated actual page returned200 with12parameter rows and zero JavaScript
errors. Empty numeric input remained empty and disabled Save; typing `0.125`
retained that text and resolved value. Passive server refresh preserved the draft;
dirty navigation showed Save/Discard/Stay; Cancel reread authoritative state through
GET. No POST or project mutation was performed by the reviewer. Desktop1440px
width matched its document width; mobile390px exposed IU-07.

Raw screenshots/query/readback and overflow element bounds are retained in
`parameterization-implementation-ux-unbound-v1` and
`parameterization-implementation-ux-mobile-diagnosis-v1` below the shared study root.
These initial attempts remain evidence rather than being overwritten by a later
passing render. Populated native readback/comparison is still pending workflow
execution and final review.

## Mobile isolation after initial correction

The scoped grid/min-width correction constrains visible panels, but a second actual
render still reports HTML390/576 while body/main/root client and scroll widths fit.
Independent temporary DOM style isolation shows hiding role table wrappers reduces
HTML width to390; adding only `position:relative` to `.rp-table-wrap` also reduces
576 to390, with internal table scrolling preserved. Width100%, inline-size
containment and overflow:hidden do not resolve the root overflow. This identifies
a containing-block boundary rather than licensing a page-wide overflow mask.
Retained diagnostic: `parameterization-implementation-ux-bound-fixed-v1/overflow-isolation.log`
and its standalone script. All changes in that diagnosis were temporary browser
styles, not production edits.


## Final independent rendered evidence

Reviewer: separate UX agent `/root/ux`, with no production source edits.
The approved workflow was reviewed after the actual custom Run and coordinated
web restart. Raw artifacts are beneath
`/wc1/runs/ro/roads-parameterization-program-20261103/`:

- `parameterization-implementation-ux-busy-v2`: actual busy page, screenshot and
  driver; HTTP 200, disabled editing and zero JavaScript errors.
- `parameterization-implementation-ux-populated-overflow-v2`: diagnostic using
  temporary browser hydration from the exact custom-Save receipt, without server
  mutation. The group selector caused width 532 at viewport 390; its scoped width
  correction restored 390. This diagnostic is not presented as final live proof.
- `parameterization-implementation-ux-final-v2`: actual populated custom view,
  desktop/mobile screenshots, authoritative query, extended independent driver
  and readback; final live dimensions are 1440/1440 and 390/390. All 420 native
  values and 12 comparison values match the server query. Empty-input handling,
  decimal typing, passive-draft preservation, Save/Discard/Stay navigation and
  Cancel reload pass. Read-only browser review made no project Save.

The independent reviewer also inspected workflow-owned `parameterization-workflow-v1/ui-reset.json` and `ui-reset-desktop.png`: all 12 entries are default, the visible label says Default inputs, and retained custom results are explicitly historical. The reset receipt records mobile width 390/390.

The mobile role table has a named, focusable scroll region (tabindex 0), client
width 308 and internal scroll width 682, so horizontal table access remains
available without document overflow. This is a targeted keyboard check, not a
complete accessibility audit. Both screenshots were visually inspected. The
interface separates saved settings, preview and completed native inputs; actual
comparisons label modeled-profile PASS EVENT scope and preserve limitations.
Expanded source provenance now explains AVKE mm/h divided by 3,600,000 to m/s,
input units and the distinction from later native coefficient adjustments.

Final source SHA256 values (also retained with the loaded bundle hash in the
JSON receipt):

| File | SHA256 |
| --- | --- |
| `wepppy/weppcloud/controllers_js/roads_parameterization.js` | `df43f5653dde239ec1b9537afcbd2d56d8568ea1e4ce8693f90bde37c27575f4` |
| `wepppy/weppcloud/templates/roads/parameterization.htm` | `42d271efd290409d6172c4e589db9e61633f252db701a75199f427887f5b1beb` |
| `wepppy/weppcloud/routes/nodb_api/roads_bp.py` | `f35c73ec3a9f5b639575f3cd55de34fdc1c08a54bfc5862046cc165fdf6692fa` |
| `wepppy/nodb/mods/roads/roads.py` | `b65713d1356143ca8ac76c62e5c28437f5e35f439df5c6af771266dd6bc5fb0a` |

This is independent agent review, not a human usability study, accessibility
certification, owner ratification, production deployment or scientific
calibration evidence. Native propagation, archive/restore/fork and authorization
are assessed separately by the workflow, correctness and security reviews.


## Final stale-bundle guard delta and rerun

A later broad regression gate identified omission of the shared stale-bundle
script from this new page. IU-10 records the user consequence and correction.
Independent source review confirmed the only template delta after the prior
review: `script_extras` now loads deferred `controllers_gl_stale_check.js`
immediately after deferred `controllers-gl.js`, matching established pages.

After the coordinated web restart, independent actual browser review passed again
under `parameterization-implementation-ux-final-stale-v3` in the same study root.
The guard loaded, expected and actual bundle identities both equal
`2026-11-04T02:31:24Z`, and the fresh page shows no false update banner. All 420
native readback values and 12 comparison cells still match actual query data;
1440/1440 and 390/390 dimensions, decimal editing, draft preservation, navigation
and Cancel remain passing. The JSON receipt includes final source identities and
the loaded bundle hash; the table above now binds the final template hash.
Prior final-v2 evidence remains retained with its original hashes. The mismatch
banner itself uses the existing shared implementation and regression coverage;
this scoped rerun does not claim a new exhaustive stale-cache/browser test.
