# Add current configuration hints to Config Builder run pages

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to
date as work proceeds. Maintain it according to
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, a user opening
`/weppcloud/runs/<runid>/config/` can see the effective project locale beside
the projection and can open More -> Config Summary to review the six settings
most useful for understanding how the project was configured. The summary is
read-only and reflects the current run rather than whatever defaults the
Config Builder registry happens to contain today.

## Progress

- [x] (2026-09-01 18:03 UTC) Read repository planning, documentation,
  contract-first, and WEPPcloud instructions.
- [x] (2026-09-01 18:03 UTC) Locate the fixed header, More menu, run-page
  context assembly, project-config authority, and focused rendering tests.
- [x] (2026-09-01 18:03 UTC) Scaffold the work package, tracker, draft contract
  decision, correctness artifact, and this ExecPlan.
- [x] (2026-09-01 18:07 UTC) Confirm that the pill uses the effective canonical
  locale ID, for example `locale: continental-us`.
- [x] (2026-09-01 18:09 UTC) Finalize the `Not available` state policy and add
  canonical section 7.8 for independent review.
- [x] (2026-09-01 18:18 UTC) Disposition initial Not Ready reviews by correcting
  scope eligibility, field precedence, state matrices, security triage, and
  durable regression obligations.
- [x] (2026-09-01 18:24 UTC) Obtain explicit operator approval for the complete
  corrected edge-policy matrix.
- [x] (2026-09-01 18:31 UTC) Obtain renewed Ready confirmations from both
  independent reviewers with no medium/high findings.
- [x] (2026-09-01 18:32 UTC) Commit standalone contract checkpoint
  `790f34207` after approval and independent review.
- [x] (2026-09-01 18:39 UTC) Implement the presentation model, locale pill,
  Config Summary modal, theme styles, and user guidance.
- [x] (2026-09-01 18:43 UTC) Add focused route/template, authorization,
  nested/PUP, accessibility, and regression evidence; pass independent review.
- [x] (2026-09-01 19:05 UTC) Complete broad validation, record the
  browser-environment limitation, and close the package.

## Surprises & Discoveries

- Observation: The example `us-contintental` is neither the canonical locale ID
  nor correctly spelled; the current canonical Config Builder ID is
  `continental-us`.
  Evidence: `wepppy/nodb/locales/capability_graph.py` and existing Config
  Builder tests use `continental-us`.
- Observation: The requested header is shared through
  `templates/header/_run_header_fixed.htm`, so unconditional markup could
  expose summary UI outside the requested Config Builder route.
  Evidence: both the run route and other header includes reference that
  template.
- Observation: Run-page assembly already resolves stored/live capability
  authority and the active watershed representation, so a second browser fetch
  is unnecessary.
  Evidence: `run_0_bp.py` resolves `run_capability_authority`,
  `stored_wepp_authority`, delineation backend, and `wepp.multi_ofe` before
  rendering.

## Decision Log

- Decision: Display the effective canonical locale ID; Continental US reads
  `locale: continental-us`.
  Rationale: The operator confirmed canonical IDs, preserving the stored
  identifier and avoiding a new display alias.
  Date/Author: 2026-09-01 / Codex.
- Decision: Render one server-built presentation model rather than loading the
  summary asynchronously.
  Rationale: The current run page already loads the owning NoDb objects and
  resolved config authority; one model prevents pill/modal divergence and adds
  no transport failure state.
  Date/Author: 2026-09-01 / Codex.
- Decision: Use an honest unavailable marker for a field that has no effective
  value, subject to contract approval; never substitute a live Builder default.
  Rationale: The modal describes the current run and must not imply provenance
  the run does not possess.
  Date/Author: 2026-09-01 / Codex.

## Outcomes & Retrospective

The locale pill and six-row Config Summary modal are implemented from effective
run authority, documented, and covered across populated, absent, legacy,
nested/PUP, hostile-value, and non-target states. The complete Python suite
passed with 7,313 tests and 63 skips; all 108 frontend suites/833 tests, lint,
documentation, syntax, and diff gates also passed. Independent correctness
review is Ready after resolving dark-theme and authorization-boundary findings.

The only residual evidence limitation is environmental: the new authenticated
Playwright modal branch could not execute because available smoke targets could
not provision or locate a usable Config Builder run. The branch remains in the
suite and asserts 640-pixel reflow, focus movement/return, Escape dismissal, and
axe results when such a fixture is available.

## Context and Orientation

The target page is the Config Builder run page at
`/weppcloud/runs/<runid>/config/`. Its route is assembled in
`wepppy/weppcloud/routes/run_0/run_0_bp.py`, rendered by
`wepppy/weppcloud/routes/run_0/templates/runs0_pure.htm`, and includes
`wepppy/weppcloud/templates/header/_run_header_fixed.htm`. The fixed header
currently renders an `EPSG:<srid>` projection pill and contains the More menu
plus existing modal markup. A presentation model means a small dictionary of
already-formatted, read-only labels and values passed from Flask to Jinja; it
does not become a persistence or API contract.

The canonical project configuration contract is
`docs/schemas/project-owned-config-contract.md`. Because that contract does not
yet specify this user-facing summary, the contract-first standard requires an
approved and independently reviewed canonical UI contract amendment in
`docs/ui-docs/contracts/` before implementation. The draft decision artifact is
`artifacts/20260901_contract_decision.md`.

The six modal rows are Locale, Delineation Backend, Representation, DEM Data
Source, Cell Size (m), and CLIGEN Database. Representation maps the effective
boolean/model state to exactly `Single OFE` or `Multiple OFE`. Other values
should retain stable canonical IDs unless the approved contract defines an
existing authoritative display label. Cell size is the effective numeric value
in meters, not merely the selected DEM's current registry default.

## Plan of Work

First complete the contract decision. Inventory applicable current contracts,
record the exact behavior and state matrix, obtain operator approval, add a
small canonical contract under `docs/ui-docs/contracts/`, obtain two independent
read-only reviews, disposition findings, and commit all checkpoint artifacts as
a standalone ancestor. Do not edit production implementation before that
revision exists.

Then add a narrowly named helper or presentation-model builder near the run-page
context assembly in `wepppy/weppcloud/routes/run_0/run_0_bp.py`. It must read the
effective locale and effective settings already owned by the loaded run/config
objects. It must not consult current Builder defaults to fill missing stored
state. Pass both a route-scope availability flag and the six formatted values
to the Jinja template.

Update `wepppy/weppcloud/templates/header/_run_header_fixed.htm` so the locale
pill follows the projection pill when the approved Config Builder summary
context is available. Add a Config Summary button to More and an accessible
modal using the existing `data-modal-open`, `data-modal`, overlay, dialog,
labeling, close, and dismissal conventions. Render a two-column table with row
headers and the six requested fields. Avoid custom JavaScript unless the
existing modal framework cannot satisfy the approved interaction.

Add focused tests in `tests/weppcloud/routes/test_pure_controls_render.py` and,
if the helper is nontrivial, a focused route/helper test beside existing run
route tests. Prove exact row labels/order, representation formatting, locale
pill placement, HTML escaping, modal semantics, unavailable-state behavior,
and absence outside the approved surface. Extend the authenticated Config
Builder axe/reflow smoke only if existing coverage does not exercise the open
modal. Update affected user-facing and developer documentation in the same
change set.

Finally run focused and frontend gates, exercise the modal manually at narrow
and normal widths, complete the correctness review artifact, update this plan
and the tracker, and close the package only with no unresolved medium/high
finding.

## Concrete Steps

Work from `/home/workdir/wepppy`.

Before implementation, inspect and complete the checkpoint with:

    git rev-parse HEAD
    wctl doc-lint --path docs/work-packages/20260901_project_config_run_summary
    wctl doc-lint --path docs/ui-docs/contracts/<approved-contract>.md

After the standalone contract checkpoint is committed, run focused iteration
checks with:

    wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py -k "run_header or config_summary" --maxfail=1
    wctl run-npm lint
    wctl run-npm test

Run the production-change handoff checks with:

    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260901_project_config_run_summary
    git diff --check

Record exact commands, counts, failures, and dispositions in the tracker. Do
not claim a broad pass if a command was not completed.

## Validation and Acceptance

With a populated Config Builder run open, the header shows the existing
projection pill followed immediately by `locale: <effective-locale>`. Opening
More and choosing Config Summary opens a labeled modal whose table has exactly
six rows in the requested order. The values match the run's effective config;
Multiple OFE and single-OFE runs display `Multiple OFE` and `Single OFE`
respectively, and cell size is numeric meters.

The page remains usable by keyboard: the launcher opens the modal, focus follows
the repository modal convention, Escape/dismiss controls close it, and its
dialog has an accessible name. At narrow viewport widths neither the new pill
nor table makes content unreachable. Supported legacy/absent state follows the
approved unavailable policy without a server error, and hostile display text
is escaped.

Acceptance also requires proof that pages outside the approved Config Builder
surface do not gain misleading summary UI, all scoped and frontend gates pass,
user/developer documentation is current, and the correctness review has no
unresolved medium/high findings.

## Idempotence and Recovery

The contract and implementation edits are additive and tests are repeatable.
If presentation-model construction fails during development, revert only this
package's small changes; do not change persisted run data. If a value cannot be
resolved, follow the approved unavailable policy rather than catching broad
exceptions or deriving a replacement default. The modal performs no mutation,
so closing or reopening it has no recovery semantics.

## Artifacts and Notes

Keep the contract decision, independent contract reviews, review disposition,
test evidence, screenshots or concise manual smoke notes, and final correctness
review under this package's `artifacts/` directory. Do not store run secrets or
private project content.

## Interfaces and Dependencies

The implementation should use the existing Flask/Jinja render path, the loaded
NoDb objects and resolved project-config authority in `run_0_bp.py`, the shared
run-header template, and the repository modal contract already used in that
template. It adds no external dependency, HTTP endpoint, persistence key,
queue job, or schema migration.

At the template boundary, provide a single optional object such as
`run_config_summary` only on the approved surface. It contains ordered display
rows plus the locale pill text/value; settle its exact Python shape during the
contract checkpoint and test it directly enough that the pill and table cannot
drift.

Plan revision note (2026-09-01 18:03 UTC): Initial ExecPlan created from the
user request and repository contract-first/work-package guidance. Locale label
wording remains an explicit pre-implementation decision.

Plan revision note (2026-09-01 18:07 UTC): Recorded operator confirmation that
the locale pill uses effective canonical locale IDs such as `continental-us`.

Plan revision note (2026-09-01 18:43 UTC): Recorded checkpoint revision,
implementation, focused validation, independent review findings and fixes, and
the remaining broad-validation/closeout work.

Plan revision note (2026-09-01 19:05 UTC): Recorded the full-suite pass, final
documentation/diff gates, browser-fixture limitation, and package closure.

Plan revision note (2026-09-01 19:07 UTC): Recorded implementation and package
closeout revision `2887b74ec`.
