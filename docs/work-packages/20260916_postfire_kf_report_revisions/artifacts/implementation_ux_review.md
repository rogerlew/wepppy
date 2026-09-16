# Independent implementation UX review

Date: 2026-09-16. Reviewer: dedicated `ux_reviewer` agent.

Final disposition: **PASS; no unresolved blocking UX findings**.
The initial findings below are retained with their final disposition recorded
in the follow-up section.

## Scope and evidence

Read-only implementation review of `response_curve.py`, `postfire_report.js`,
the report/control templates, scalar inverse states and the accepted report
contract's “Kf, response curve and rainfall provenance amendment — 2026-09-16”.
The control contract and active ExecPlan govern the run-control workflow.
Only this review artifact was written by this reviewer.

This is an agent source review, not a human usability study, accessibility
certification, owner ratification, or proof that the restarted interface works.
Desktop/narrow layouts, supported themes, focus visibility, deployed assets and
real keyboard/export behavior await retained browser evidence.

## Blocking findings

### UX-01 — Medium — Control still requires RUSLE in its explanation

- Location: `wepppy/weppcloud/templates/controls/postfire_debris_flow_pure.htm:9`,
  model input comparison table, M1 Soil cell.
- Observed implementation: “Mean soil erodibility (K), prepared through RUSLE”.
- Accepted behavior: M1 prepares NRCS-derived STATSGO fine-earth Kf automatically
  and does not require the RUSLE mod.
- User consequence: a user following the table will enable an unnecessary mod
  or interpret its removal as invalidating M1; this contradicts the reported
  remove-RUSLE workflow and the new prerequisite feedback.
- Smallest improvement: identify NRCS-derived STATSGO fine-earth Kf and state
  that it is prepared automatically when running M1.
- Observable acceptance: the rendered comparison table and required-data row
  agree; removing RUSLE preserves the post-fire control immediately and after
  first/second reload, and the normal M1 action works without RUSLE.

### UX-02 — Medium — Valid P50 states collapse to generic missing information

- Location: `wepppy/weppcloud/controllers_js/postfire_report.js:5`, `reasons`,
  and `renderChart`'s response-curve status paragraph.
- Observed implementation: scalar `constant_probability`,
  `constant_probability_mismatch`, `negative_rainfall`, `arithmetic_overflow`
  and `arithmetic_underflow` lack readable mappings. The new P50 paragraph
  presents all non-available states as “Unavailable” with a generic instruction
  to inspect the saved manifest.
- Accepted behavior: constant/decreasing response and nonunique/unavailable P50
  remain explicit, understandable states; valid saved results remain usable.
- User consequence: users cannot distinguish a valid constant model or absence
  of a nonnegative equality from missing/broken input data, and have no reason
  to know that rerunning the model will not necessarily produce a unique P50.
- Smallest improvement: map those finite scalar reasons to ordinary-language
  explanations and describe nonunique P50 as having no single intensity rather
  than implying missing information. Do not alter the scalar calculation.
- Observable acceptance: constant-at-target, constant-off-target, negative
  equality and arithmetic fixtures display distinct explanations; a valid
  response line and saved tables remain available when only P50 is unavailable.

## Optional polish

### UX-03 — Low — Replace equation jargon in the chart help

- Location: `wepppy/weppcloud/templates/reports/postfire_debris_flow/report.htm`,
  paragraph immediately after `data-pfr-chart`.
- “Unique 50% equality” is precise but harder to understand than “rainfall
  intensity associated with 50% modeled likelihood, when one exists”.
- Acceptance: the help introduces P50 without requiring mathematical vocabulary;
  existing warnings against warning-trigger interpretation remain visible.

## Source-level strengths and task walkthrough

The accepted design uses one existing duration selector and one chart rather
than adding a dashboard or redundant settings. The backend samples the accepted
model over a range including P50/P99 and saved scenarios; this addresses the
otherwise uninformative cluster of high-probability design storms. A labeled
diamond distinguishes P50 from saved scenario circles. Keyboard Enter/Space
handlers retain saved-marker selection and link it to ordinary table buttons.

An expandable ordinary table includes all curve samples, and its CSV retains
full numeric precision and unit/context fields. Chart, P50, tables and CSV use
the same Unitizer presentation path. These are implemented affordances visible
in source; their deployed/browser behavior is not established by this review.

The report separates rainfall recurrence from debris-flow probability, keeps
fixed-postfire/no-recovery and runout limitations visible, and labels known
event subdaily peaks as modeled/disaggregated even with calendar dates. Missing
origin remains explicitly unrecorded. Accepted soil source appears in Methods;
source labels derive from the accepted snapshot rather than current controls.

## Required follow-up evidence

After the stack restart, retain desktop and narrow screenshots plus keyboard
checks for duration, saved marker/table selection, numeric-details expansion
and CSV download. Show the default curve/P50, all durations, English/SI display
equivalence, accepted-source labels and reload persistence. Exercise the
immediate/first/second-reload RUSLE removal regression and normal UI/RQ run.
Re-review UX-01/UX-02 after their changes, and record any remaining evidence
limitations explicitly in the final disposition.

## Final follow-up — 2026-09-16

- **UX-01 resolved.** The deployed fixture control screenshot shows
  “NRCS-derived STATSGO fine-earth Kf, prepared automatically when you run M1”
  and a consistent required-data row. The fixture evidence records dNBR upload
  with RUSLE absent, a completed normal submission, and post-fire visible/current
  after RUSLE removal immediately and after both reloads.
- **UX-02 resolved.** The reason map now explains constant-at-target,
  constant-off-target, no nonnegative solution and numerical range failures;
  the P50 paragraph separately labels nonunique results. This closure is based
  on the changed rendering source. The live examples are ordinary increasing
  curves, not browser reproductions of every exceptional scalar state.
- **UX-03 resolved.** Chart help now describes rainfall intensity associated
  with 50% modeled likelihood instead of “unique 50% equality”.

Inspected with the image viewer: `browser/nervous-mesquite/report-si.png`,
`report-english.png`, `report-mobile.png`,
`browser/pfdf-kf-e5c25f5b/control.png` and
`browser_m3/cursor-dark-midnight.png`. The curve exposes the rising transition,
P50 is distinct from design circles, units agree across chart/tables and the
narrow layout retains the ordinary numeric alternative. The M3 screenshot
also visibly labels stale results and unknown subdaily origin rather than
guessing a source. The chart becomes small on a narrow screen; the expandable
table is the usable alternative specified by the accepted contract.

Reviewed both M1 `evidence.json` files, the associated three-duration payloads
and the retained `browser_e2e.cjs` assertions. The harness checks every duration's
numeric row population, source identity, actual CSV download, P50 focus,
saved-marker Enter activation/pressed state, and report persistence. Expansion
of the numeric details uses the native element's `open` property in this
harness; it is not evidence of a complete keyboard-only task walkthrough.
The shared Unitizer's existing conversion factor is a display convention;
neither this review nor the implementation changes scientific input units.

The M3 `browser_m3/browser.json` records a completed saved-report regression,
successful event-detail recovery, no page errors or model mutations, and
unchanged protected files. Theme screenshots supplement the default-theme M1
evidence, but this review is not a measured contrast audit or certification.

No additional blocking usability defect was observed in this bounded review.
Browser evidence is automated agent evidence, not a human usability study;
owner ratification and accessibility certification are not claimed.
