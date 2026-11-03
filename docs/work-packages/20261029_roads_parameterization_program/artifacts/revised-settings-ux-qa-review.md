# Independent Roads settings UX and QA review

Reviewer: independent `settings_ux_qa` agent, 2026-11-03. Scope: proposed
`docs/schemas/roads-settings-contract.md`, ADR-0135, workflow design draft and
`revised-settings-layout-draft.html`. This is proposal review, not implemented
workflow acceptance or human approval. The final study-copy disposition and artifact hashes are recorded below.

## User outcome and existing conventions

A normal user can edit five supported fallback settings without editing CSV or
native files. Valid uploaded feature values remain authoritative. Width changes
modeled footprint; fill defaults apply only to rutted roads; traffic/surface are
coupled model choices. The proposed inline fieldset after Attribute Mapping,
shared control/field/button macros, saved view and Edit/Save/Cancel/Reset sequence
fit the existing Roads control and shared controller presentation contract.
The first editor does not need an optimizer, raw erosion coefficients, global
override mode or another navigation destination.

Inspected existing `roads_pure.htm` and controller presentation guidance. The
proposal correctly avoids duplicating surface/traffic fields, names units beside
numeric inputs, separates draft Reset from Save, preserves unrelated mappings,
and distinguishes actual completed-run usage from a predicted preparation count.
Its mixed-upload applicability and valid feature precedence are explicit.

## Findings

| ID | Severity | Finding and minimum correction | Status |
| --- | --- | --- | --- |
| UQ-01 | Medium | Static copy says only custom settings are not field-calibrated, which may imply defaults are calibrated. State that this study establishes no field calibration for either default or custom settings. | Resolved; independently rechecked |
| UQ-02 | Medium | The initial layout only illustrates normal default/view/edit/saved states. Add compact explicitly illustrative actual-use/no-use, invalid-field, busy, stale and readonly messages so human layout review can assess the consequences already specified in the contract. No fabricated study counts. | Resolved; independently rechecked |
| UQ-03 | Low | “Existing road-template policy” in the main settings status is implementation jargon. Keep Default/Custom status there; place policy/provenance details under Details. | Resolved; independently rechecked |

Help text is visibly adjacent to every field but the standalone illustration does
not associate it using `aria-describedby`. Production implementation must use the
shared field macros and their accessible help/error association, as the proposal
requires. All five explicit labels are correctly associated in this draft. This
observation is not an accessibility certification of an unimplemented view.

## Static rendering evidence

Rendered the actual HTML with the repository-installed Playwright and local
Chromium 1217 at desktop 1280×1000 and mobile 375×900. Both document scroll widths
equal their viewport widths; all five fields have associated labels, and all six
action buttons are disabled as appropriate for a static nonfunctional artifact.
The mobile grid becomes one column without horizontal overflow or clipped actions.
View and edit examples are clearly labeled as separate illustrated modes; they
must not appear simultaneously in the implemented editor.

Retained initial screenshots and DOM readback:
`/wc1/runs/ro/roads-parameterization-program-20261103/revised-settings-ux-v1/`.
No application server, production route or saved project was exercised. The local
render reads only the static file; it cannot prove event handlers, focus behavior,
server validation, authorization or persistence.

## Required QA after human approval

| User path | Required observation |
| --- | --- |
| Default/custom/legacy saved values | Reloaded numbers and labels match saved state; Default means equality, never calibration or verified legacy provenance |
| Change one fallback with valid feature attributes | Usage explains feature precedence; no automatic override or false claim every segment changed |
| Fill fields on mixed/inslope/unrutted uploads | Explicit applicability; no fake fill role or implicit satisfaction of required unrutted geometry |
| Unchanged draft | Save disabled without a request; existing server semantics remain distinct |
| Reset, then Cancel | Draft resets only; Cancel restores saved values and old results remain current |
| Reset, then Save | Five baseline values saved together; mappings and unrelated parameters preserved; Roads results invalidated visibly |
| Invalid field or busy response | Draft retained, actionable message, focus to first invalid field; no silent retry or mutation |
| Readonly/unauthorized | Inspection follows access policy; edit actions unavailable and actual request denied |
| Save followed by reload/run | Fresh inputs/native/report artifacts carry saved choices; old usage/results are not shown as current |
| Failure/fork/restore | Error and diagnostic artifacts remain inspectable; selections/provenance and coherent currentness survive canonical operations |

Verify browser keyboard/focus/live-status behavior and the real request/save/native
chain after implementation. Unit assertions and this static rendering cannot close
those future gates. The scientific report must separately state studied values,
responses, unsupported contexts and uncalibrated limits before the human proposal
is considered ready.

## Verdict

Final UX/QA proposal review: **PASS after corrections and final study-copy
readback**, with no unresolved medium/high UX finding. Completed-study citations
and range wording are now present and appropriate for human proposal review.
Human approval is absent; no production configuration view or persistence/application
wiring or runtime workflow is approved by this review.

## Post-correction readback

The author resolved UQ-01 through UQ-03. Independent desktop/mobile rerender
confirms blanket calibration wording, policy detail moved out of the primary
status, and clearly illustrative fallback-unused, validation-error, busy, stale,
readonly and malformed-saved-value states. The examples contain no fabricated
run counts. The invalid-field example has an explicit error association.
Both viewport scroll widths still equal their viewport widths and every displayed
input/select has an associated label.

Revised layout SHA256:
`d2e51740f622629eb5cf2965abd02b4ad9eefc06ebc4eb5ddc1a53dd7cdde9f7`.
Retained v2 screenshots/readback:
`/wc1/runs/ro/roads-parameterization-program-20261103/revised-settings-ux-v2/`.
The initial v1 rendering remains retained separately. These checks assess the
static proposal only. Future changed layout or final study-copy amendments need
a focused readback before using this review as their approval.

## Adjacent-action amendment review

The subsequent “Adjacent actions and draft ownership” addition passes UX/QA
proposal review. The current mapping action's surface/traffic coupling makes this
a concrete integration concern. Mapping now submits mapping only; Settings Save
submits the five settings only. A dirty settings draft blocks adjacent upload,
mapping, preparation and execution with an inline Save/Cancel explanation. This
preserves the user's unfinished choices without a confirmation modal or silent
autosave. Existing busy/readonly restrictions still take precedence.

Passive summary responses cannot replace a dirty draft. Matching-request Save
hydration, double-submit suppression, draft retention on failure and explicit
Cancel reload are understandable local interaction rules; they do not promise
cross-session conflict detection. Required browser tests in the amendment cover
these exact interactions. Production evidence remains pending approval and wiring.

Independently rerendered the amended layout at 1280 and 375 pixels; no horizontal
overflow, all labels associated, and the unsaved-settings inline explanation
appears in the clearly illustrative state examples. Current reviewed layout SHA256:
`5f33ec1f0b0b356b92b725474832334378dd33e5aaa2ffbfc4bcef2840f494bf`.
Evidence is retained under
`/wc1/runs/ro/roads-parameterization-program-20261103/revised-settings-ux-v3/`.
Scientific response citations remain pending and human approval remains absent.

## Final study-copy and rendering review

Final focused review confirms the contract and ADR cite the completed 47-profile
and four-project studies, retain their separate scope, and do not convert those
results into field calibration or default adoption. Surface remains an existing
supported field; the contract explicitly says this panel did not isolate its
sensitivity. The layout presents exact studied width 2/4/8 m, fill length
10/30/60 m and fill slope 2/10/30% separately from allowed limits and expressly
says these are not recommended ranges. Traffic help now warns that a lower modeled
category does not always predict less erosion. Neither default nor custom settings
are presented as field-calibrated. No structural control changes were introduced.

Independently rendered the final HTML at 1280×1000 and 375×900. Both layouts have
no horizontal overflow, every field is labeled, and the final help text is present
without pending-study placeholders. Desktop screenshot inspected visually; state
examples remain explicitly illustrative and do not claim observed run counts.
The UX proposal has no remaining study-copy condition. Scientific validity remains
the independent scientific review's responsibility; this review assesses faithful,
understandable presentation of the declared evidence and its limits.

Final reviewed SHA256 bindings:

| Artifact | SHA256 |
| --- | --- |
| `docs/schemas/roads-settings-contract.md` | `7bd11c84814707480656f7b26ab9abd5b63962bd7c2836424a069ffb07a291ca` |
| `docs/adrs/ADR-0135-roads-settings-controls.md` | `1693bcac4ff41f8c75bcfb8a7761fe429dbe5e69bf39b040276a75e484511bc4` |
| `artifacts/revised-settings-layout-draft.html` | `e6acb4990e7c79adae37560a8db3d8de11bd1f46cc1a423440a7887ea048b910` |

Reproducible renderer, screenshots and DOM readback are retained under
`/wc1/runs/ro/roads-parameterization-program-20261103/revised-settings-ux-v4/`.
Prior v1–v3 render evidence remains retained as review history; earlier pending
study statements describe those earlier checkpoints, not the final verdict.
Explicit human approval and actual implemented browser/save/native/report workflow
validation remain absent and are not waived.
