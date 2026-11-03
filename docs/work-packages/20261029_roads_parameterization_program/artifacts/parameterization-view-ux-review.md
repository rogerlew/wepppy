# Dedicated parameterization view independent UX/QA review

Status: **PASS for the corrected static proposal; no unresolved findings**. Review scope is the
static proposal, not production API, NoDb, native workflow or accessibility
certification. Human specification/layout approval remains absent.

## Evidence and method

Independently inspected the current project/view contract, static HTML and author
notes, then ran a separate Playwright inspection against the local HTML. Raw
review script, desktop/mobile screenshots and readback are retained under
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-view-review-v1/`.
The review did not reuse the author's output assertions. No production files or
project state were changed. Screenshots were visually inspected.

The dedicated view clearly separates saved configuration, source/adjustment
arithmetic, role-wide override intent, unresolved/prepared evidence and output
comparison. It labels the demonstration and illustrative groups explicitly.
Actual field values match the gravel/loam and paved/loam templates. It does not
invent run outputs or prepared readback. Native role scope excludes upstream
landuse and inspection groups do not pretend to select override scope.

## Findings

- UX-01, medium: entering finite Ki multiplier `1e308` displays `Invalid draft`
  because the resolved value overflows, but Save remains enabled. Requested-value
  validation alone is insufficient. Validate resolved values across all demo
  groups/roles and disable both Save entry points. Native real/serialization
  validation remains a server implementation obligation.
- UX-02, low: the sticky save bar follows all role sections and uses `top:0`,
  so editing near the top of a long mobile page does not expose Save/Cancel/Reset.
  Place the bar before the roles or use a persistent bottom action arrangement.
- UX-03, low: `Unavailable — not prepared` can imply geometry Prepare materializes
  soil files. The current pipeline assembles those during Run. Describe unavailable
  native input assembly/readback explicitly and distinguish the two phases.
- UX-04, low: repeated shared validity caveats in all12 rows enlarge the mobile
  page unnecessarily. Put common validity guidance once above the roles while
  preserving per-field units/errors.

## Initial independent readback

Desktop1440 and mobile390 both have exact viewport/document widths, three visible
role sections and zero JavaScript errors. Ki multiplier2 changes gravel preview
from500000 to1000000 and paved preview to10; the draft survives group switching.
Dirty return navigation offers Save/Discard/Stay. During pending Save, Cancel,
Reset and inputs are disabled. Readonly has zero enabled role controls. Invalid
saved-state preview has zero resolved numeric fields and explicit repair wording.
Unbound preview allows first explicit Save without changes. The nonfinite resolved
value case reproduces UX-01.

## Final disposition

All four findings are resolved in the corrected artifact. Independent fresh
Playwright rerun and screenshots are retained under
`/wc1/runs/ro/roads-parameterization-program-20261103/parameterization-view-review-v2/`.
The original failed v1 readback remains retained.

UX-01: both Save paths reject invalid requested or resolved values across every
applicable role in both illustrative groups. The same `1e308` reproduction now
shows Invalid draft with Save disabled. Server native-representation checks remain
explicitly outside this prototype. UX-02: action bar precedes the roles, and Edit
scrolls/focuses its controls. At390px it is visible at y0, width366, height189px.
UX-03: the page now explicitly says native soil/management assembly occurs during
Run and geometry Prepare alone is not emitted-input evidence. UX-04: shared
validity guidance appears once, with per-field errors preserved.

Final desktop1440/mobile390 show no page overflow or JavaScript errors. Prior
arithmetic/navigation/pending/readonly/unbound/invalid checks continue to pass.
Added absent/disabled preview exposes zero numeric values and enabled role controls,
hides Edit, and explains that merely visiting the view creates no Roads state.

This approves the static design within its stated scope. Actual authorization,
persistence, native representability, passive response ownership, repair, completed
run readback and comparisons require implementation tests and independent final
workflow review. No production workflow or accessibility conformance certification
is implied. Explicit human specification/layout approval remains required.


## Reviewed artifact identities

- `docs/work-packages/20261029_roads_parameterization_program/artifacts/parameterization-view-draft.html`: `7a8b69ba1d234ab0cb73eeca0ae288cab353b120269c2c7c90f9e2b29ab21a80`.
- `docs/work-packages/20261029_roads_parameterization_program/artifacts/parameterization-view-notes.md`: `ee361bc968c84a7ac2ab10b92fffd0bb63a15910d61211f963297fd63fd46bcb`.
- `docs/schemas/roads-settings-contract.md`: `8c849bbc6ee34926caa505d78c6c076407a440cee75fc64ad659107110d18ed7`.
