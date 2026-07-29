# Test and repair Pure UI controllers one at a time

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current in accordance with
`docs/prompt_templates/codex_exec_plans.md`. Keep the umbrella tracker,
controller register, child-package register, and active child tracker current.

## Purpose / Big Picture

Work through the Pure UI inventory one controller at a time. Each controller
package establishes intent, tests actual rendered and downstream behavior,
reproduces contract mismatches, patches them minimally, and retains regression
coverage before the next controller begins.

The initiative's output is safer controller behavior and executable tests. It
is not a contract registry or enforcement platform.

## Progress

- [x] (2026-07-17) Created and independently reviewed the controller inventory
  and bounded package register.
- [x] (2026-07-17 through 2026-07-28) Recorded contract-first governance and
  bounded-remediation milestones REM-01 through REM-05 at their independently
  documented states.
- [x] (2026-07-28) Scaffolded a registry/enforcement dependency platform.
- [x] (2026-07-28) Operator rejected that platform-first direction and required
  a low-regression, controller-by-controller tests-and-repair loop.
- [x] (2026-07-28) Removed seven speculative shared/enforcement scaffolds,
  retained DOM-01 as the first controller, and deferred GOV-01.
- [x] (2026-07-28 10:20Z) Closed the simplified GOV-00A test convention after
  proportional independent review.
- [x] (2026-07-28) Executed and closed DOM-01 WATAR/Ash with direct regression
  tests and no production mismatch.
- [x] (2026-07-28) Executed and closed DOM-05 Channel Delineation with direct
  regression tests and no production mismatch.
- [x] (2026-07-28) Executed and closed DOM-04A Map Orchestration with direct
  rendered-action and exact elevation-request regression tests and no
  production mismatch.
- [x] (2026-07-28) Executed and closed DOM-04B Map Layers and Feature UI with
  direct rendered-default/legend regression evidence and no production mismatch.
- [x] (2026-07-28) Executed and closed DOM-06 Outlet with direct rendered-mode
  and manual-entry payload regression evidence and no production mismatch.
- [x] (2026-07-28) Executed and closed DOM-07 Subcatchment with direct
  WBT/MOFE rendered identity, exact payload, and ordered worker-chain evidence
  and no production mismatch.
- [x] (2026-07-28) Executed and closed DOM-08A Landuse Build with direct
  upload-mode rendered identity, exact multipart payload, and route
  normalization evidence and no production mismatch.
- [x] (2026-07-28) Executed and closed DOM-08B Landuse Catalog and Map Editor
  with actual endpoint/upload/control/precondition rendering and existing
  browser/RQ-engine mutation evidence; no production mismatch.
- [x] (2026-07-28) Executed and closed DOM-09 Landuse Modifier with actual
  selection/value/action rendering and exact synchronous mutation evidence; no
  production mismatch.
- [x] (2026-07-28) Executed and closed DOM-10 Soils with actual
  mode/selection/option/lifecycle rendering and downstream state/queue evidence;
  no production mismatch.
- [x] (2026-07-28) Completed all 39 run-domain controller packages with direct
  rendered-template and applicable downstream evidence.
- [x] (2026-07-28) Reviewed measured value after five controller domains.
- [x] (2026-07-28) Registered the autonomous serial remaining run-domain
  execution plan with a per-package commit restore point.
- [x] (2026-07-28) Reconciled the run-domain registers and completed broad
  closeout validation; the known unrelated GridMET `_FakeUnits.degC` fixture
  failure recurred after 2,452 passes and 40 skips.
- [x] (2026-07-28) Executed SHR-04A from measured DOM evidence, adding direct
  base and material macro-family render coverage; 105 tests pass and no
  production mismatch was found.
- [x] (2026-07-28) Executed SHR-04B with direct modal/details/theme/console
  JavaScript and rendered-template evidence; repaired three duplicate
  initializers and one dropped table-page caller.
- [x] (2026-07-28) Executed SURF-12 with direct Pure/legacy report-shell,
  readonly/PUP/runtime and all 19 direct-consumer evidence; no production
  mismatch was found.
- [x] (2026-07-28) Executed SHR-05 with rendered/client/Project/route/NoDb/map
  evidence; repaired Unitizer global selection, selector, and event ownership
  and passed independent security review.
- [x] (2026-07-28) Executed SURF-11 with direct Geneva summary rendering,
  controller lifecycle, route/service/map/Unitizer evidence, and independent
  security review; no production repair was retained.
- [x] (2026-07-28) Executed SURF-16 with direct ERMiT launcher/client,
  route/session/RQ/worker evidence; repaired rejected-token retry recovery and
  passed independent security review.
- [x] (2026-07-28) Executed SURF-09 with direct README viewer/editor renders,
  real inline-client, route/Redis/filesystem/reload evidence; repaired
  authority, path, concurrency, resource-boundary, Jinja, and client response
  contracts and passed independent security review.
- [x] (2026-07-28) Executed SURF-17 with Admin/Root route, real RQ producer,
  hostile render, queue-isolation, empty-state, and failure evidence; separated
  default and batch active panels under checkpoint `cf20ef0b0` and passed
  independent correctness and security reviews.
- [x] (2026-07-28) Executed SURF-18 with direct DEVAL rendering and inline
  client execution, CAP plus run authorization, parent-owned PUP tracking,
  owned-job validation, fail-closed status/error behavior, confined worker and
  artifact paths, and independent correctness/security reviews.
- [x] (2026-07-28) Executed SURF-13 with direct evidence for every security
  form/email family, actual CAP/password-toggle script execution, and retained
  CSRF, cookie/session, OAuth, configuration, and log-redaction evidence;
  independent review passed and no production repair was required.
- [x] (2026-07-28) Executed SURF-14 with direct profile/provider/hostile
  rendering, actual token mint/copy/fallback/error execution, and retained
  OAuth, CSRF, token, cookie/session, logout, and Diagnostics evidence; removed
  the misowned Dev role mutation, repaired proxy-prefix password navigation,
  and passed independent correctness/security reviews.
- [x] (2026-07-28) Executed SURF-15 with actual Root/Admin/inventory/hostile/
  empty rendering, real inline client, CSRF/validation/datastore/reload
  evidence; repaired Root authority, strict request types, self-Root
  protection, HTTP errors, and visible safe feedback; security review passed.
- [ ] Close the initiative when the registered inventory has executable
  regression coverage or explicit operator-approved exclusions.

## Surprises & Discoveries

- Observation: WATAR and channel depression smoothing both failed because tests
  did not cross actual rendered name/value into downstream parsing and reload.

- Observation: The controller count created planning anxiety and caused an
  architecture with two registries, a generated index, a manifest, change-aware
  enforcement, consumer fan-out, attestations, and prerequisite shared audits.

- Observation: That trajectory matched the negative-value TESTGATE assessment:
  control-plane assurance was being built before a thin product slice proved
  benefit.

- Observation: The useful loop is independent of controller count and can be
  applied sequentially with existing Jinja, Jest/jsdom, pytest, controller
  build, and stale-bundle checks.

- Observation: The full run-domain sequence confirmed that direct assertions
  and existing focused suites were sufficient; it introduced no shared helper,
  registry, generator, or false tooling failure.

- Observation: The same direct-assertion approach scaled to the 1,227-line
  shared macro producer without requiring a registry or production repair.

- Observation: Direct duplicate-execution tests found real singleton defects
  in three shared browser producers, and direct rendering found a nested Jinja
  caller defect in the unused-but-contractual table macro.

- Observation: Report-shell conformance was provable with five direct
  regressions plus retained Project and route suites; no producer registry or
  domain-test duplication was needed.

- Observation: SHR-05 found source/generated selector drift and duplicate
  legacy event ownership that could race preference persistence; direct
  rendering plus single-dispatch tests exposed both without changing units.

- Observation: SURF-11's independent review caught a proposed second
  initialization owner that direct template-string inspection could not see.
  Lifecycle ownership must be tested at the loaded controller boundary when a
  deferred bundle already registers document events.

- Observation: SURF-16's visible Retry button was not evidence of recovery;
  executing the real inline script showed that a rejected cached token promise
  made every later attempt fail without another request.

- Observation: SURF-13 showed that direct framework-owned form coverage must
  assert positive field and escaped-value presence; absence-only XSS checks can
  pass when required output disappears.

- Observation: SURF-14 showed that browser-relative links can silently escape
  the `/weppcloud` deployment prefix and that visible privilege controls must
  be checked against the owning route's role boundary.

- Observation: SURF-15 showed that `roles_required('Admin', 'Root')` means both
  roles, not either role, and that a disabled privilege checkbox must have a
  matching server invariant.

## Decision Log

### 2026-07-28: Controller count is inventory

**Decision**: Do not use the number of controllers to justify orchestration,
schemas, dependency gates, or broad up-front audits.

### 2026-07-28: One-controller tests-first execution

**Decision**: One controller is active at a time. Actual-render and focused
downstream tests precede minimal compatible repair when practical.

### 2026-07-28: Shared behavior is encountered, not prerequisite

**Decision**: Shared packages do not block controller tests. If a controller
exposes a shared mismatch, test the controller and direct consumers before a
shared patch. Narrow or defer the shared patch when coverage is unavailable.

### 2026-07-28: Tooling must earn its existence

**Decision**: Direct assertions first. Extract a stateless test helper after at
least two repeated tests. Defer GOV-01 until five controllers show a measured
miss or repeated burden and the operator explicitly approves a proposal.

### 2026-07-28: Profile is not a role-mutation owner

**Decision**: Keep the user profile read-only and leave role/account mutation
to the Root-only SURF-15 boundary. Generate security continuations from their
Flask endpoints so proxy prefixes remain authoritative.

### 2026-07-28: Privileged mutation types are literal

**Decision**: SURF-15 accepts only a JSON object, allowlisted role, valid
target, and literal boolean state; its Root authority and self-Root protection
are enforced by the server rather than inferred from visible controls.

### 2026-07-28: Autonomous run-domain execution remains serial

**Decision**: Execute the remaining run-domain packages under
`prompts/active/remaining_run_domain_autonomous_execution_execplan.md`, with
one active child and a commit after every closeout.

**Rationale**: The operator authorized autonomous completion and restore
points; serial execution preserves low regression risk and clear ownership.

### 2026-07-28: Run-domain inventory is complete

**Decision**: Mark all 39 DOM packages verified while leaving SHR, SURF,
governance, and remediation packages at their independently recorded states.

**Rationale**: Completion of the finite run-domain queue does not imply
completion or exclusion of separately owned non-run inventory.

### 2026-07-28: SHR-04A is verified without producer changes

**Decision**: Retain the direct producer matrix in the existing rendered
template suite and leave conforming base/macro APIs unchanged.

**Rationale**: The 105-test suite proves exact metadata, identity, state, ARIA,
lifecycle, structural, and empty-state output while preserving completed-DOM
consumer behavior.

### 2026-07-28: SHR-04B restores shared idempotence and table content

**Decision**: Keep public APIs unchanged, add producer-local duplicate-load
guards, and capture table-page caller content before nested macro calls.

**Rationale**: These are the smallest repairs to canonical singleton behavior
and the existing macro signature; direct regressions fail without them.

### 2026-07-28: SURF-12 verifies shell presentation without domain duplication

**Decision**: Verify the two report producers and their finite direct-consumer
inheritance while retaining report-body behavior under its existing DOM/SURF
owners.

**Rationale**: Direct shell, Project, and route evidence proves readonly and
runtime contracts without creating a second owner for domain outputs.

### 2026-07-28: Project exclusively owns Unitizer change events

**Decision**: Retain report-shell initial preference synchronization but remove
shell-local change listeners in favor of Project's delegated global/category
handlers.

**Rationale**: One event owner prevents redundant asynchronous persistence and
stale-state races while preserving reload hydration and public hooks.

### 2026-07-28: Geneva controller owns report initialization

**Decision**: Preserve `geneva_summary_report.js` as the sole
`DOMContentLoaded` initialization owner and test its listener registration
directly.

**Rationale**: A second template bootstrap would call non-idempotent `init()`
twice and duplicate filter and map request handlers.

### 2026-07-28: ERMiT tokens are cached per explicit attempt

**Decision**: Clear the launcher token-promise cache when `startExport()` begins
and reuse the resulting token only within that submit/poll/download attempt.

**Rationale**: Retry must recover from a rejected token request without
changing token scopes, claims, route authorization, or queue behavior.

## Context and Orientation

The reviewed inventory remains in:

- `artifacts/controller_audit_register.md`;
- `artifacts/child_package_register.md`; and
- `artifacts/controller_contract_test_roadmap.md`.

The execution protocol is:

`prompts/active/controller_contract_audit_iteration_prompt.md`.

GOV-00A publishes the concise convention. DOM-01 at
`docs/work-packages/20260727_watar_ui_contract_pilot/` is first.

## Plan of Work

### Milestone 1: Close the concise convention

Remove current-authority requirements for obligation registries, generated
indexes, manifests, diff engines, consumer graphs, attestations, and new CI.
Publish the exact one-controller test seam and simplicity/stop-loss rules.

Acceptance: DOM-01 can begin without SHR or GOV-01 prerequisites.

### Milestone 2: Execute one controller

For the selected controller:

1. record concise intended fields/actions;
2. inspect actual template/controller/parser/state/RQ/reload paths;
3. write actual-render and applicable focused downstream tests;
4. reproduce confirmed mismatches;
5. patch one mismatch at a time;
6. run cheap focused checks before existing broad gates;
7. review actual production patches proportionally; and
8. close the package with runtime, mismatch, helper, and remaining-gap results.

If no mismatch exists, retain the tests and close the covered behavior.

### Milestone 3: Continue sequentially

Choose the next register entry after the current controller closes. Incidents or
operator priorities may reorder the backlog. Do not activate multiple controller
packages merely to accelerate the inventory.

### Milestone 4: Five-controller value review

After five controllers, measure:

- mismatches found;
- regressions sensitive to reintroduced defects;
- focused/broad runtime;
- helper lines versus controller-test lines;
- false tooling failures; and
- operator effort.

Continue the loop if it provides positive value. Tooling expansion requires a
specific measured miss or repeated burden, two simpler alternatives, and
explicit operator approval.

## Concrete Steps

For each controller, begin with repository search and focused tests. The WATAR
package contains its exact first command set. Common closeout gates are:

    wctl run-npm lint
    wctl run-npm test
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-pytest <exact-affected-tests>
    wctl doc-lint --path <changed-doc>
    git diff --check

Run the controller build only after controller source changes. Run
`wctl check-rq-graph` only after enqueue/dependency changes. Cheap render, lint,
and focused tests always precede broad execution.

## Validation and Acceptance

A controller is verified only when actual-render tests cover risk-bearing field
identity/state and applicable downstream tests cover serialization, parsing,
persistence/reload, and RQ. Inapplicable layers need no artificial N/A artifact.

Production patches must be limited to confirmed mismatches, preserve
compatibility by default, and carry required correctness/security review based
on actual changed behavior.

## Idempotence and Recovery

Use isolated fixtures and preserve unrelated worktree changes. Never edit
generated bundles directly. If intent is ambiguous, stop. If shared changes lack
direct-consumer coverage, narrow or defer them. If tooling triggers a stop-loss,
remove or simplify it before continuing.

## Interfaces and Dependencies

GOV-00A produces the test convention. The register supplies backlog identity.
Each controller package produces tests, minimal repairs, measured runtime, and
evidence about whether a small helper is useful.

No controller depends on GOV-01. Shared package references describe code context,
not completion gates.

## Outcomes & Retrospective

DOM-01 closed with actual-render, controller, route, persistence, and RQ
coverage; its historical selector mismatch was already fixed, so it needed no
production repair. The affected Python set (111 tests), frontend lint, and full
frontend suite (88 suites, 662 tests) passed. It introduced no test helper or
false tooling failure. Preserve the initial scaffold as superseded history in
git rather than current authority. At each five-controller review, record
whether the loop remains net-positive and whether any tooling proposal passes
the simplicity budget.

DOM-05 closed with actual-render, legacy/GL payload, and RQ persistence-order
coverage; REM-05 supplied its already-fixed depression-smoothing seam. The
affected Python set (124 tests), frontend lint, and the full frontend suite (88
suites, 662 tests) passed. It introduced no helper, false tooling failure, or
production patch. Its audit ledger remains `documented` until the work receives
a named revision.

DOM-04A closed with actual-render map action/target coverage and exact
run-scoped elevation `{lat, lng}` request evidence. Existing coordinate,
TOPAZ/WEPP lookup, drilldown, elevation-service, and report-route coverage
conformed. The focused Python set (121 tests), frontend lint, focused Map Jest
(38 tests), and full frontend suite passed. It introduced no helper, false
tooling failure, or production patch; DOM-04B remains the layer/feature owner.
The repository-wide Python sweep stopped after 2,451 passes and 40 skips on an
unrelated GridMET `_FakeUnits.degC` fixture failure; DOM-04A's focused 121-test
Python evidence passed.

DOM-04B closed with actual-render evidence for the SBS toggle, default
subcatchment colormap, and legend hosts. Existing Map helper tests conformed
for layers, SBS presentation, scale, and feature-modal accessibility. Focused
Python (72 tests), lint, focused Map Jest (38 tests), and full frontend results
passed. It introduced no helper or production patch.

DOM-06 closed with actual-render outlet mode/lifecycle evidence and an exact
manual-entry coordinate payload regression. Existing cursor, route validation/
enqueue, worker mutation, and reload evidence conformed. Focused Python (167
tests), lint, focused Outlet Jest (5 tests), and full frontend results passed.
It introduced no helper or production patch.

DOM-07 closed with actual WBT/MOFE rendered identity and exact GL payload
evidence. Existing route tests proved coercion and grouped updates before parent
enqueue; a direct worker test now proves subcatchment build precedes dependent
abstraction. Focused Python (169 tests), lint, focused Subcatchment Jest (12
tests), and the full frontend suite (88 suites, 663 tests) passed. It introduced
no helper or production patch.

Five-controller-domain value checkpoint: WATAR/Ash, Channel, Map, Outlet, and
Subcatchment completed with direct template/controller/downstream tests. The
audit loop has retained regressions at each observed seam, introduced no shared
helper or registry, and had no false tooling failure. Focused Python sets took
roughly 11--16 seconds; full frontend validation took roughly 7--8 seconds.
The observed result supports continuing the same direct-test loop, not adding
tooling.

DOM-08A closed with actual upload-mode render and exact browser multipart
payload evidence. Existing mode, user-defined upload, grouped update, worker
cache/timestamp, and completion reload tests conformed; a route regression now
proves multipart boolean normalization before persistence. Focused Python (190
tests), lint, focused Landuse Jest (29 tests), and the full frontend suite (88
suites, 663 tests) passed. It introduced no helper or production patch.

DOM-08B closed with actual catalog/map endpoint, upload/control, and snapshot
precondition rendering. Existing inline browser and RQ-engine suites proved
authenticated upload/edit/delete, save/conflict/clear, atomic persistence, and
refreshed state. Focused Python (169 tests), lint, focused inline Jest (4 tests),
and the full frontend suite (88 suites, 663 tests) passed. It introduced no
helper or production patch.

DOM-09 closed with actual selection/value/action/lifecycle rendering. Existing
Jest and RQ-engine tests proved map selection, exact `{topaz_ids, landuse}`
submission, authorization, validation, and synchronous Landuse mutation.
Focused Python (138 tests), lint, focused Jest (3 tests), and documentation lint
passed; the unchanged frontend tree's preceding full sweep passed 88 suites and
663 tests. It introduced no helper or production patch.

DOM-10 closed with actual Soil mode, selection, option, and lifecycle rendering.
Existing controller, route, schema, enqueue, worker, and reload evidence
conformed. Focused Python (204 tests), lint, focused Jest (7 tests), and docs
lint passed; the unchanged frontend tree's preceding full sweep passed 88
suites/663 tests. It introduced no helper or production patch.

SURF-11 closed with direct Geneva summary payload/filter/URL/map/accessibility
rendering, one controller-owned initialization regression, and retained route,
service, Unitizer, selection, and map evidence. Focused Python passed 144
tests across the render/route and service sets; focused Jest passed 7 tests;
frontend lint and the full 89-suite/671-test frontend sweep passed. Independent
review caught and rejected a proposed duplicate template bootstrap before
commit, then passed the corrected test-only closeout with zero unresolved
findings. No production repair was retained.

SURF-16 closed with direct ERMiT launcher targets, real inline token/submit/
poll/download/retry execution, Flask and rq-engine authorization/run/job-state
tests, and worker artifact-metadata evidence. Focused render/Flask tests passed
161; backend route/session/worker tests passed 63; focused Jest passed 2; and
frontend lint plus the full 90-suite/673-test frontend sweep passed. The
one-line production repair makes an explicit Retry mint a fresh token after a
rejected token promise while retaining one token within an attempt. Independent
security review passed with zero unresolved findings.

SURF-14 closed with ordinary, privileged, linked-provider, empty, hostile, and
proxy-prefixed actual renders; real token mint/copy/fallback/error execution;
and retained OAuth, CSRF, token, cookie/session, logout, and Diagnostics
evidence. Focused Python passed 70 tests, and frontend lint plus all 96
suites/695 tests passed; broad Python passed 5,522 tests with 58 skips. The
profile's Dev-visible PowerUser mutation was removed because its route is
Root-only and owned by SURF-15; the password link was made proxy-prefix aware.
Independent correctness/security reviews passed with no unresolved findings.

SURF-15 closed with actual Root/Admin, inventory, hostile, empty, selected,
self-disabled, client, CSRF, validation, datastore, persistence, and reload
evidence. Focused Python passed 28 tests, frontend lint plus all 97 suites/699
tests passed, and broad Python passed 5,534 tests with 58 skips. Production
repairs aligned GET authority with Root ownership, required strict JSON and
boolean inputs, prevented self-Root removal, returned canonical 400 errors, and
replaced console-only results with escaped live feedback and rollback.
Dedicated security review passed with no unresolved findings.
