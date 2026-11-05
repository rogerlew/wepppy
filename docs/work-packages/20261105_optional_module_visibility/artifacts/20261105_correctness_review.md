# Correctness review: optional module visibility

## Metadata

- Reviewer: independent `visibility_audit` reviewer agent.
- Reviewed: 2026-11-05 17:21 UTC, with final finding-disposition confirmation afterward; working diff from `9cd9efb467099406ab9f42db297158f75148fdd6`.
- Scope: Observed run-context predicate, page/bootstrap templates, Observed controller binding and completion visibility, focused regressions and supporting documentation.
- Authority: feature-registry specification **Runtime Semantics**, feature-access-governance-contract FA-01/FA-02 retained inspection, controller-contract **Singleton + bootstrap**. Normative intent remains unchanged.
- Security triage: none. This patch changes presentation and existing DOM lifecycle, not authorization, request parsing, persistence, paths or job execution. Dedicated security review is not required for this delta.

## User outcome and failure class

The reported project should have no empty Observed control shell when its module is off and initialized state has no results. Enabled controls, retained results and authorized preview remain usable. No project data is deleted or initialized to implement visibility.

The broken assumption is that an optional controller object's existence means the feature is active. The [consumer audit](consumer_audit.md) records all 18 registry entries, non-registry optional sections, template and bootstrap consumers, dynamic activation and WEPP completion. Following load guards shows no second server-side off-plus-empty activation defect: Debris Flow's apparently similar predicate has a mod-gated loader. Peer dispositions are source audits and scoped existing regression evidence, not claims that every peer workflow was exercised live.

Observed's downstream repairs are necessary: missing state previously advertised results, initial bootstrap created an absent controller, cached form references survived replacement, and enabled-empty/retained sections could be hidden after WEPP completion. The replacement binding removes old delegates, refreshes all adapters and attaches to the new form. Repeated bootstrap with the same form does not duplicate delegates or attachment.

## Valid-state matrix

| Stored/runtime state | Valid | Required behavior | Evidence |
| --- | --- | --- | --- |
| No Observed object, module off | yes | Hidden empty placeholder; no form, false hasResults, no initial bootstrap entry | Predicate matrix, real page/bootstrap renders, executable bootstrap selection |
| Initialized object, results None, module off | yes | Same hidden outcome despite persisted object | Predicate and page-render matrices |
| Enabled module with absent or initialized state | yes | Control renders, remains usable, no optional-state initialization during presentation | Render matrix; enabled-empty Jest completion test |
| Populated results without enabled mod | yes | Retained control/report stays inspectable | Render matrix and retained-results Jest test |
| Legacy empty result mapping | yes | Preserve existing results-is-not-None interpretation | Predicate, page/bootstrap matrix |
| Form removed, inserted or replaced | yes | No absent-form network probe; refresh current form; one action per click; release stale status handle | First-enable/replacement, WEPP-before-enable and real StatusStream handle regressions |
| Malformed serialized NoDb state | no | Existing loader/error contract remains authoritative | No serializer/parser/loading boundary changed; hostile-state injection not claimed |

Input dimensions are enabled/off and preview on/off, independently combined with absent, initialized-empty, empty-results and populated state. Runtime dimensions additionally cover repeated bootstrap, replacement and WEPP notification. Unknown module names, role/back-end combinations and arbitrary malformed persisted objects are not claimed as exhaustively covered by these new tests.

## User-reachable error policy

Optional absence is expected: render a hidden placeholder and no-op the controller when there is no form. Existing model-fit HTTP errors continue through the existing stacktrace and event contract. Missing required JavaScript helpers still fail explicitly. The patch adds no new user-facing error or recovery operation. Invalid NoDb data is not silently converted into healthy empty state.

## Generated artifact evidence chain

| Stage | Expected semantics | Evidence | Result |
| --- | --- | --- | --- |
| User intent | Off/unused Observed has no visible empty shell | Supplied DOM and package symptom | confirmed |
| Persisted state | Reported run has disturbed/roads, results None | Primary agent's read-only project inspection | confirmed diagnosis |
| Generated intermediate | Page conditionally includes the real Observed control and shared macros | `test_runs0_observed_shell_requires_own_state` | scoped tests pass |
| Browser input | Bootstrap JSON has correct flags/results and skips absent controller selection | Render assertions plus Node execution of actual selection function | scoped tests pass |
| Controller output | Existing/new form receives one delegated action; missing form no-ops | Observed Jest regressions with real DOM helpers | scoped tests pass |
| Live user-facing page | Fresh authenticated browser verifies reported run | Not executed in this review; anonymous request reaches CAP gate | outstanding environment validation |

Scientific execution, generated model outputs and archives are unchanged and therefore not relevant proof targets for this presentation repair. No safety or persistence boundary was changed. Jinja page decisions, shared control macros and controller binding functions execute directly in the new tests; unrelated page sections and HTTP responses are test doubles. A dedicated lifecycle regression executes real controlBase and StatusStream against actual status/stacktrace DOM panels, proving handle release on absence, new-panel attachment after replacement and stable handles on repeated bootstrap. It does not connect a live WebSocket or establish end-to-end authenticated Mods-menu behavior.

Primary agent reports 537 scoped Python tests and 89 scoped Jest tests passing, followed by all 9 Observed tests passing after adding the status lifecycle regression (90 distinct scoped Jest cases across Observed, Project and WEPP). Scoped ESLint, documentation lint and changed-file broad-exception enforcement pass; bundle rebuilt through `wctl` after the final change. The lifecycle regression failed before the detach fix and passed afterward. This reviewer inspected the tests and final production diff; did not rerun those suites. Reviewer `git diff --check` on implementation and regression files passed. No full suite was run, as explicitly directed by the user.

Highest supported claim: implemented and locally validated. Deployment, browser verification of the reported project and incident resolution are not claimed.

## Findings

| ID | Severity | Surface | Finding and action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | Low | Remount status lifecycle | Disposal disconnected but retained the previous status handle. Changed to existing `detach_status_stream`; the real controlBase/StatusStream regression now covers absence, replacement and repeated bootstrap. | Resolved; reviewer verified final code/test |
| COR-02 | Low | Documentation hygiene | Documentation editing removed blank lines and left `.bak` files. Blank lines restored and generated backups removed. | Resolved; reviewer verified final files/status |

No high or medium correctness, authorization, persistence or compatibility finding was identified. Residual risks are the unexecuted authenticated browser flow and live WebSocket transport, explicitly limited above.

## Review checks and artifact observability

- Canonical intent and unchanged retained-result semantics are identified; code is not used as normative authority.
- Valid persisted states and flags are independently enumerated; missing optional state remains safe.
- Direct rendered output and executed controller selection cover the failure boundary.
- Existing hidden-placeholder and Pure shell conventions are preserved, with Ash/Omni as comparable modules.
- Existing scientific files, reports, browse, download and archive behavior are unchanged. No new hidden-only artifact or observability exception is introduced.
- Test counts are scoped evidence, not substitutes for deployment or live output inspection.

## Verdict

Gate: pass. Unresolved high: 0; medium: 0; low: 0. Recommendation: accept the bounded local implementation; perform authenticated run-page acceptance before claiming the live incident resolved. Sign-off: independent `visibility_audit` reviewer, 2026-11-05 UTC.
