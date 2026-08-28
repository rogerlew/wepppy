# Correctness and User-Experience Review - Run Page Document Title

## Metadata

- **Package**:
  `docs/work-packages/20260827_project_config_run_ui_authority/`
- **Amendment**: `PC-13/WP12D-20260828-7`
- **Reviewer**: Codex independent correctness reviewer
- **Date**: 2026-08-28
- **Scope reviewed**: proposed canonical section 7.7, amendment decision,
  active ExecPlan, tracker, established run-page template/context, live Project
  controller title consumers, and proposed rendered-title evidence
- **Commit/branch context**: `feature/project-owned-config`, starting revision
  `5bb8676bb5b6dca2a71d9bb84f658f9bdf0811e6`
- **Canonical contract**:
  `docs/schemas/project-owned-config-contract.md`, section 7.7, "Run page
  document identity"
- **Related review artifact**:
  `artifacts/20260828_run_page_title_governance_review.md`

## User Outcome

- **User goal**: identify the open run by its run ID in the browser title
  instead of seeing optional configuration metadata or `None`.
- **Success presented to the user as**: an established run-page title equal to
  the exact route run ID throughout initial render and later project-name or
  scenario changes, with no metadata suffix.
- **Failures that may reach the user**: no new server error is intended. Invalid
  or path-dangerous route IDs retain their existing rejection behavior.
- **Partial-state behavior**: title rendering is presentation-only; no project,
  config, route, queue, or filesystem state changes on title failure.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Named-preset run with populated config name and no project name | yes | Title is exactly the route run ID; config name is absent | Decision lines 56-57; actual-title-block regression required at lines 105-107 |
| Project-local or flattened run with absent/`None` config name | yes | Title is exactly the route run ID; literal `None` is absent | Decision lines 58-59; actual-title-block regression required at lines 105-107 |
| Absent, `None`, empty, or non-empty project display name | yes | Title remains exactly the route run ID, without suffix or placeholder | Decision lines 60-62; rendered and Project controller evidence at lines 105-115 |
| Project name or scenario saved or cleared without navigation | yes | Existing persistence/feedback remains; title does not mutate | Decision lines 61-64; Project controller save/clear evidence at lines 113-115 |
| Parent route with active pup or differing current Ron identity | yes | Title remains exactly the parent route run ID | Decision lines 65-66; differing nested/PUP evidence at lines 108-110 |
| Invalid or path-dangerous route run ID | no | Existing route rejection remains unchanged | Decision lines 67-69; no route implementation change is authorized |
| HTML-significant title value reaching rendering | bounded input state | Preserve exact decoded browser text through autoescaping; never interpret it as executable markup | Decision lines 67-69 and autoescape evidence at lines 111-112 |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Optional config/project/scenario metadata is absent or empty | expected | Exact route run ID without `None`, `Untitled`, or an empty suffix | Canonical section 7.7, lines 970-976 |
| Project-name or scenario update succeeds | expected | Existing field/event/notification behavior; unchanged exact run-ID title | Decision lines 61-64 and 113-115 |
| Invalid or path-dangerous route run ID | expected rejection | Existing route failure; no title render | Canonical section 7.7, lines 981-982 |
| Title value contains HTML-significant characters | bounded input | Autoescaped browser text; no executable markup | Canonical section 7.7, lines 982-983; proposed direct evidence |

## Review Checks

- [x] Canonical intent is named; source and tests are treated as observed
  constraints and evidence rather than normative authority.
- [x] Server-rendered and live-mutated document-title states have one complete,
  deterministic lifetime contract.
- [x] Absent, empty, populated, legacy, pup/current-Ron, and hostile states are
  covered by the valid-state matrix and direct evidence.
- [x] No persistence, filesystem, queue, request, or authorization mutation is
  introduced by the proposed title behavior.
- [x] Canonical contract, decision matrix, and regression evidence consistently
  prohibit every config/project/scenario suffix.
- [x] The hostile-state policy accurately describes the existing route and
  autoescaping boundaries.
- [x] Operator approval satisfies the applicable bounded cross-owner standard
  for this exact amendment and matrix.
- [x] The active ExecPlan contains an executable amendment-7 checkpoint,
  implementation, validation, and no-deploy handoff sequence.
- [x] Baseline comparison confirms no amendment-7 implementation or test file
  was edited before this review.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TITLE-COR-01 | Medium | Title after live project-name/scenario changes | The corrected contract now defines one exact full-page-lifetime title. The boundary includes the Project controller, its Jest test, README, and generated bundle; the matrix and evidence cover name/scenario saves and clears plus differing nested/PUP controller identity while preserving existing non-title behavior. | Canonical lines 970-984; decision lines 36-44, 54-69, 84-101, and 103-118 | No further contract action. Implement only after the accepted checkpoint and execute the named rendered/Jest regressions. | Resolved |
| TITLE-COR-02 | Medium | Populated project display name | Canonical and decision text now require exactly the route run ID for the complete page lifetime and consistently prohibit project/config/scenario suffixes. The matrix and evidence match that obligation. | Canonical lines 970-980; decision lines 36-44 and 54-66 | No further contract action. | Resolved |
| TITLE-COR-03 | Medium | Invalid/path-dangerous and HTML-significant values | The corrected contract separates existing route rejection for invalid/path-dangerous IDs from Jinja autoescaping for values that reach rendering. The matrix and proposed evidence require an autoescape-enabled actual-title-block assertion with encoded markup and exact decoded text. | Canonical lines 981-984; decision lines 67-69 and 111-112 | No further contract action. Execute the named direct render evidence after checkpoint. | Resolved |
| TITLE-COR-04 | Medium | Borrowed PC-13 ownership and checkpoint authority | The operator's exact 2026-08-28 23:06 UTC ratification closes the cross-owner gate. It covers the completed amendment-7 matrix, active WP12D authority to carry the bounded WP07/PC-13 change without advancing or closing WP07, PC-13, WP12D, or WP12, the standalone checkpoint and subsequent exact-source implementation, and WP12's exclusive merge and production authority. | Decision lines 7-11 and 27-34; ExecPlan lines 192-197; tracker lines 7-11 and 38-50; `docs/standards/contract-first-change-standard.md:153-184` | No further contract action. Commit the exact documentation-only checkpoint and verify it as an ancestor before any implementation or test edit. | Resolved |
| TITLE-COR-05 | Medium | Execution sequence and acceptance | The ExecPlan now has an amendment-7 baseline and Plan of Work continuation, Milestone 6, test-first Concrete Steps with exact focused/broad commands, full title-lifetime and autoescape acceptance, bundle parity, exact path comparison, independent implementation review, and no-push/no-deploy WP12 handoff. | ExecPlan lines 595-616, 663-674, 717-734, and 807-816 | No further technical plan action. | Resolved |

## Verdict

- **Gate status**: `pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: `checkpoint-ready`
- **Reviewer sign-off**: Codex independent correctness reviewer, 2026-08-28

The ratified amendment is **BINDING READY** for its exact standalone
documentation-only checkpoint. TITLE-COR-01 through TITLE-COR-05 are resolved.
The worktree remains at starting revision
`5bb8676bb5b6dca2a71d9bb84f658f9bdf0811e6`; comparison against that revision
shows no amendment-7 template, controller, controller test, controller README,
generated-bundle, or route-test edit. The checkpoint must be committed and
verified as an ancestor before implementation begins. Proposed regression
evidence remains prospective until that implementation is complete.
