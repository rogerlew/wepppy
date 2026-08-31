# Correctness and User-Experience Review - Builder Automatic Validation

## Metadata

- **Package**:
  `docs/work-packages/20260827_project_config_run_ui_authority/`
- **Amendment**: `PC-13/WP12D-20260828-6`
- **Reviewer**: Codex independent correctness reviewer
- **Date**: 2026-08-28
- **Scope reviewed**: amendment decision, canonical project-config contract,
  active ExecPlan, tracker, Config Builder controller/template, controller Jest
  suite, rendered-template pytest, and controller developer documentation
- **Commit/branch context**: `feature/project-owned-config`, starting revision
  `b772877c443ae21697a4eed5d51827cc806afc52`
- **Canonical contract**:
  `docs/schemas/project-owned-config-contract.md`, section 7.4, "Validation and
  review" plus "Accessibility and responsive behavior"
- **Related QA/security artifacts**: governance review is ready; exact operator
  cross-owner ratification was recorded at 2026-08-28 19:59 UTC; the amendment
  classifies its changed attack surface as low

## User Outcome

- **User goal**: open Config Builder and receive a server-resolved review of the
  complete default proposal without clicking a redundant validation button,
  then keep that review synchronized with later selections.
- **Success presented to the user as**: one description request hydrates the
  controls, one validation request renders the authoritative review, and Create
  becomes available without moving focus.
- **Failures that may reach the user**: invalid selections, validation transport
  or server errors, malformed Builder descriptions, and a stale registry found
  during creation.
- **Partial-state behavior**: selections and linked errors remain visible;
  Create stays disabled until the latest hydrated proposal validates; reload or
  a later form change retries validation without creating a project.

## Valid-State Matrix

| State | Valid? | Required behavior | Direct evidence |
| --- | --- | --- | --- |
| Description absent or still loading | yes | Controls and Create are unavailable; no validation begins before successful hydration | Decision lines 56-64 and 77-79; proposed description-load diagnostic and zero-validation tests at lines 145-155 |
| Complete description and default proposal | yes | Hydrate defaults and dependencies, validate exactly once, render review, enable Create, and preserve focus | Decision lines 37-51 and 77-82; proposed initialization and focus tests at lines 135-139 and 149-150 |
| Complete description with user-modified proposal | yes | Invalidate the prior review, settle dependencies, validate the latest proposal, and ignore obsolete responses | Decision lines 40-42 and 81-82; proposed controlled-overlap evidence at lines 142-144 |
| Stale registry during Create | yes | Invalidate old responses, disable controls during description reload, preserve registered selections, default and explain only invalidated selections, and validate once against the refreshed description | Decision lines 48-64 and 87-99; proposed change-during-reload test at lines 145-148 |
| Validation failure | yes | Preserve selections, announce and link errors without moving focus, keep Create disabled, and permit change/reload retry | Decision lines 48-54 and 83-86; proposed focus, retry, and diagnostic tests at lines 149-155 |
| Description rejected by the existing hydration boundary | no | Fail explicitly and issue no validation or creation request | Decision lines 89-94 define the exact boundary; proposed zero-validation cases at lines 151-153 |
| Overlapping or out-of-order validation/description responses | valid asynchronous state | Only the latest proposal under the latest completed description may render review/errors or enable Create | Decision lines 56-64 and 95-99; proposed initial/change and description-generation race tests at lines 142-148 |

## User-Reachable Error Policy

| Condition | Expected or exceptional? | User-visible result | Justification |
| --- | --- | --- | --- |
| Server rejects a complete proposal | expected | Linked page/field errors, live announcement, retained selections, disabled Create | Decision lines 48-51 and 83-84 |
| Validation transport/server failure | exceptional | Diagnostic status and summary, retained selections, disabled Create; change or reload retries | Decision lines 52-54 and 85-86 |
| Creation returns `stale_builder_schema` | expected concurrency | Refreshed controls automatically revalidate against the new registry before Create is re-enabled | Decision lines 48-64 and 87-88 |
| Description fails the existing hydration boundary | exceptional | Explicit diagnostic and zero validation/creation requests | Decision lines 89-94 and proposed direct evidence at lines 151-155 |

## Review Checks

- [x] Canonical intent is named; implementation and tests are treated as
  observed constraints and evidence, not normative authority.
- [x] Absent, complete, hydration-rejected, stale, failed, and overlapping
  asynchronous states are specified with direct planned regression evidence.
- [x] Request/input combinations and browser lifecycle states were reviewed as
  separate dimensions.
- [x] No changed persistence, filesystem, queue, or executable boundary exists.
- [x] Existing server revalidation, authentication, and creation idempotency
  remain unchanged.
- [x] Partial success, freshness binding, retry, and focus semantics are
  unambiguous across the validation and accessibility clauses.
- [x] Stale-registry selection/default preservation and diagnostic failure
  behavior have exact proposed regression evidence.
- [x] The exact implementation/documentation/test boundary includes the current
  controller, template, generated bundle, README, and actual-render pytest.
- [x] The active ExecPlan contains an executable amendment-6 checkpoint,
  test-first implementation, focused commands, acceptance, and no-deploy handoff.

## Findings

| ID | Severity | User/state surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| COR-01 | Medium | Automatic validation failure and keyboard focus | The canonical validation clause now forbids focus movement on initial/change success or failure while retaining linked and announced errors; the accessibility clause separately requires no focus movement for failed automatic validation and moves focus only after submission. Direct success/failure focus assertions are proposed. | `docs/schemas/project-owned-config-contract.md:823-827` and `:864-876`; decision lines 48-54 and 149-150 | No further contract action. Implement and execute the named focus tests after the standalone checkpoint. | Resolved |
| COR-02 | Medium | Overlapping validation, stale-registry reload, and retry | Validation is now bound to the latest proposal and latest completed description. Description-load start invalidates old responses and disables controls; stale reload preserves registered selections, defaults and explains only invalidated selections, and retains exact description/revalidation diagnostics. The proposal names direct out-of-order and change-during-reload tests. | Decision lines 56-64 and 95-99; proposed evidence lines 142-155; canonical contract lines 802-811 | No further contract action. Implement the description-generation guard and execute the deferred-response regressions. | Resolved |
| COR-03 | Medium | Description hydration failure | The browser's pre-validation rejection boundary is now exactly the existing hydration boundary: unsupported version, absent locale maps, missing locale component/graph, or dependency-render failure. All other graph/combination validity remains server-owned, avoiding a second browser schema validator. Each retained class has proposed zero-validation evidence. | Decision lines 89-94 and 151-155 | No further contract action. Preserve this bounded division of authority during implementation. | Resolved |
| COR-04 | Medium | Exact source/document/test boundary | The canonical reference now names section 7.4. The exact boundary includes the controller README, generated bundle, and real rendered-template pytest. Acceptance requires removal of both the visible action and dead controller hook while retaining accessible review/error/status/Create surfaces. | Decision lines 18-20, 116-131, and 156-159; ExecPlan lines 536-548 and 692-705 | No further contract action. Update the README with the implementation and execute the exact rendered-template test. | Resolved |
| COR-05 | Medium | Implementation sequencing and acceptance | The active ExecPlan now defines amendment 6's exact baseline, ratification/review/docs-only checkpoint gate, failing-test-first order, implementation scope, generated-bundle update, focused and broad commands, Milestone 5 acceptance, exact asynchronous/focus/hydration criteria, and no-push/no-deploy WP12 handoff. The required operator ratification is recorded. | ExecPlan lines 528-548, 585-593, 623-634, and 692-705; progress lines 170-175 | No further technical plan action. Commit the exact documentation-only checkpoint, verify it as the implementation ancestor, and then execute the plan in order. | Resolved |

## Binding Confirmation

- `HEAD` remains the exact starting implementation revision
  `b772877c443ae21697a4eed5d51827cc806afc52` on
  `feature/project-owned-config`.
- The decision records the operator's exact 2026-08-28 19:59 UTC ratification,
  bounded WP12D carrier authority, no owner advancement/closure, standalone
  checkpoint and implementation authority, and WP12's exclusive merge and
  production authority. The ExecPlan progress and tracker record the same gate.
- A direct baseline comparison reports no change to any amendment-6 controller,
  template, generated bundle, README, controller test, or rendered-template
  pytest path. No `.cfg` or other project configuration is changed.
- The checkpoint staging set is exactly the canonical project-config contract,
  decision artifact, correctness artifact, governance artifact, active ExecPlan,
  and tracker. Every other dirty path remains in the tracker's preexisting
  exclusion list and must be omitted through path-specific staging.
- The current canonical delta, decision, state matrix, implementation boundary,
  regression obligations, and ExecPlan remain mutually consistent after
  ratification. No High, Medium, or Low correctness finding remains.

## Verdict

- **Gate status**: `binding pass`
- **Unresolved findings**: High 0; Medium 0; Low 0
- **Release recommendation**: `checkpoint-ready`
- **Reviewer sign-off**: Codex independent correctness reviewer, binding
  confirmation 2026-08-28

The amendment is **BINDING READY** for its exact documentation-only standalone
checkpoint. COR-01 through COR-05 remain resolved, exact operator ratification
is recorded, and amendment-6 production/test/config implementation paths remain
unchanged from the starting revision. Path-specific checkpoint staging can
proceed. Regression evidence remains prospective until that checkpoint is an
ancestor and the controller/template implementation is executed and reviewed.
