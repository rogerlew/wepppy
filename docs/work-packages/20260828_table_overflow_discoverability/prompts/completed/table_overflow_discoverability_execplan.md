# Make horizontally scrollable tables discoverable and keyboard reachable

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current while executing it.

## Purpose / Big Picture

WEPPcloud data tables can contain more columns than fit on screen. The shared
wrapper already permits horizontal scrolling, but users may see no scrollbar
and receive no instruction that more columns exist. After this change, an
overflowing wrapped table explains how to move horizontally and becomes a
visible keyboard focus stop; a fitting table remains exactly as it was.

## Progress

- [x] (2026-08-29 01:25 UTC) Trace the WEPP summary and shared table contracts.
- [x] (2026-08-29 01:25 UTC) Scaffold the package and document operator authority.
- [x] (2026-08-29 01:38 UTC) Add exact three-decimal slope display scope.
- [x] (2026-08-29 02:04 UTC) Complete two independent read-only contract reviews and commit checkpoint `a1db47377033431e77b96a8bda2f3da8c3f5ab92`.
- [x] (2026-08-29 02:05 UTC) Implement the dependency-free shared browser behavior and CSS.
- [x] (2026-08-29 02:05 UTC) Add Jest, template/CSS, and rendered-browser regression coverage.
- [x] (2026-08-29 02:05 UTC) Run focused and broad validation successfully.
- [x] (2026-08-29 02:16 UTC) Resolve review findings, receive READY with no findings, and close the package.

## Surprises & Discoveries

- Observation: `reports/wepp/summary.htm` does not use the shared Jinja table
  macro, but all three tables use `.wc-table-wrapper`, which is the actual
  reusable behavior seam.
  Evidence: wrappers surround the outlet, hillslope, and channel tables.
- Observation: `.wc-table-wrapper` already declares `overflow-x: auto`; the
  missing behavior is discovery and reliable keyboard focus, not scrolling.
  Evidence: `static/css/ui-foundation.css` table component rules.
- Observation: the shared wrapper is not focusable by default, so users cannot
  reliably reach it with Tab before using arrow keys.
- Observation: production report headers are generator-backed, so templates
  must materialize them before indexed column-identity lookup.
  Evidence: final-review regression now mirrors `ReportBase.hdr` semantics.

## Decision Log

- Decision: Load one module from `base_pure.htm` and target the established
  `.wc-table-wrapper` contract rather than editing individual reports.
  Rationale: this covers existing and future conforming tables without template
  duplication.
- Decision: Add instructions and a generated tab stop only when horizontal
  overflow exists.
  Rationale: fitting tables should not add visual noise or keyboard stops.
- Decision: Preserve authored `tabindex`, `role`, `aria-label`, and
  `aria-describedby` values; cleanup may remove only module-generated values.
  Rationale: shared enhancement must compose with specialized tables.
- Decision: Use native scrolling after focus rather than intercepting arrow-key
  events unless rendered-browser evidence proves native behavior insufficient.
  Rationale: native behavior minimizes input conflicts and regression surface.
- Decision: Apply three-decimal formatting by exact `Slope` header identity in
  the two requested tables while retaining the raw sort key and CSV path.
  Rationale: units such as `ratio` are shared by unrelated fields and are too
  broad a formatting selector.

## Outcomes & Retrospective

The shared Pure UI shell now enhances only measurably overflowing canonical
wrappers. Focused Chromium evidence directly exercised Arrow and Shift-wheel
movement, all five AA focus styles, 200-percent zoom, document containment, and
Axe. WEPP summary slope cells use exact-header fixed three-decimal display while
retaining raw sorting and CSV wiring. The full Python and frontend suites pass.
Final independent review is READY with High 0, Medium 0, and Low 0.

## Context and Orientation

The canonical behavior is owned by
`docs/ui-docs/contracts/table-overflow-discoverability-contract.md`; the style
and accessibility guides are synchronized guidance only. Shared visual rules are in
`wepppy/weppcloud/static/css/ui-foundation.css`. The Pure UI shell is
`wepppy/weppcloud/templates/base_pure.htm`; loading the module there reaches
report and non-report Pure UI pages. Frontend unit tests use Jest with jsdom
under `wepppy/weppcloud/controllers_js/__tests__/`. Rendered smoke tests live in
`wepppy/weppcloud/static-src/tests/smoke/` and run through `wctl`.

An “overflowing wrapper” means an element whose `scrollWidth` exceeds its
visible `clientWidth` by more than one CSS pixel. A “generated attribute” means
an attribute the module added because no author-provided value existed. The
module must remember that ownership so later cleanup never removes authored
semantics.

## Plan of Work

First, amend the canonical contract and synchronize the two guidance files. Record the
exact delta in `artifacts/20260829_contract_decision.md`, obtain two independent
read-only reviews, disposition findings, and commit only the documentation
checkpoint. The operator's 2026-08-29 directions are the explicit approvals; do
not request another ratification. The two review artifacts are
`artifacts/20260829_contract_correctness_review.md` and
`artifacts/20260829_contract_governance_review.md`.

Second, add a small dependency-free browser module. On DOM readiness it finds
each `.wc-table-wrapper`, measures overflow, and synchronizes state. Overflowing
wrappers receive a generated instruction immediately before the wrapper,
keyboard focus when no author focus policy exists, accessible-region semantics
when no author semantics exist, and an accessible description that composes
with an existing description. Fitting wrappers lose only values generated by
the module. Resize observation updates geometry changes; DOM observation
registers newly inserted wrappers. Expose a narrow refresh method for tests and
deliberate dynamic consumers.

Third, add CSS for the short hint and an unmistakable `:focus-visible` outline.
Do not alter widths, wrapping, overflow mechanics, or table cells.

Also extend the summary template's display helper so the Hillslope Summary and
Channel Summary loops pass the current header identity. Only a numeric value
under the exact `Slope` header receives fixed-point `%.3f` presentation. The
existing raw value remains in `sorttable_customkey`; CSV downloads continue to
come from the server report route and are out of scope.

Fourth, add deterministic Jest tests for fitting, overflowing, resize cleanup,
dynamic insertion, idempotence, and authored-attribute preservation. Add a
shell/template assertion and a rendered-browser test whose fixed-width fixture
proves the hint, focus, native arrow scrolling, and lack of document overflow.
Run axe against the representative page.

Finally, obtain an independent correctness/UX review, disposition findings,
update the living tracker and this plan, and close the package only when the
behavior and proportional validation pass. Do not deploy, merge, or push unless
the operator separately requests it.

## Concrete Steps

Work from `/home/workdir/wepppy` on the existing branch.

1. Review and commit the documentation-only checkpoint using hunk-aware staging
   for `PROJECT_TRACKER.md` and `docs/ui-docs/accessiblity.md`. Record the full
   SHA in `tracker.md`, then prove it is an ancestor before implementation with
   `git merge-base --is-ancestor <checkpoint-sha> HEAD`.
2. Implement only the exact production and test paths listed in
   `artifacts/20260829_contract_decision.md`.
3. Run focused checks:

       wctl run-npm test -- table_overflow
       wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py
       wctl run-pytest tests/weppcloud/test_ui_foundation_css.py

4. Run frontend gates:

       wctl run-npm lint
       wctl run-npm test

5. Run the focused rendered-browser case and Axe scan:

       wctl run-playwright --suite full --playwright-args "tests/smoke/table-overflow-accessibility.spec.js" --workers 1
       wctl run-playwright --suite full --grep "axe accessibility scan for report accessibility probe" --workers 1
       wctl run-playwright --suite theme-metrics --workers 1

6. Run the required pre-handoff Python gate:

       wctl run-pytest tests --maxfail=1

   If infrastructure prevents that gate, record the exact failure and a
   concrete proportional-validation rationale in the tracker; do not claim the
   full gate passed.
7. Run documentation and diff checks:

       wctl doc-lint --path docs/work-packages/20260828_table_overflow_discoverability
       wctl doc-lint --path docs/ui-docs/ui-style-guide.md
       wctl doc-lint --path docs/ui-docs/accessiblity.md
       git diff --check

## Validation and Acceptance

The feature is accepted only when a rendered fixed-width overflowing table has
a visible instruction, can be reached with Tab, shows a focus indicator across
the AA-validated theme set, and moves horizontally after Right Arrow and Shift
plus mouse wheel. The same test must show that the document does not acquire
horizontal overflow. A fitting table must have no generated instruction or
generated tab stop. Unit evidence must prove cleanup, idempotence, dynamic
insertion, and preservation of authored attributes.
`artifacts/20260829_implementation_correctness_review.md` must be READY with no
unresolved High or Medium finding before closure.

The state matrix is: wrapper absent, fitting wrapper, overflowing wrapper,
overflow removed after resize, overflow introduced after resize, wrapper added
dynamically, authored accessibility attributes present, hidden or zero-width
wrapper, and malformed wrapper without a table. These latter states are safe
no-ops. Overflow means `scrollWidth > clientWidth + 1`.

For slope formatting, render numeric, missing, and zero slope values in both
requested tables plus a non-slope ratio column. Numeric slope values, including
zero, show exactly three decimals; missing values retain the em dash; other
columns retain existing rendering. Verify raw sort keys and CSV wiring remain
unchanged. No network, persistence, filesystem, authorization, user-input, or
scientific parameterization boundary changes.

## Idempotence and Recovery

Initialization and refresh must be safe to call repeatedly without duplicate
hints, duplicated description IDs, or extra observers. Removing overflow must
restore only module-owned attributes. If browser observation APIs are absent,
initial enhancement still runs and the exported refresh method remains usable.
Removing the module script and its CSS fully rolls back the feature without
changing table markup or data.

## Artifacts and Notes

Record the checkpoint revision, implementation revision if committed, exact
test commands, results, and any skipped environment-dependent checks in
`tracker.md`. Keep review artifacts under this package's `artifacts/` directory.
