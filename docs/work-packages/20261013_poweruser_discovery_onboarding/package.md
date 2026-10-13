# PowerUser discovery and onboarding (PUUX-01)

Status: **Closed 2026-10-13 — Forest implementation and validation complete. Production rollout remains separate.**
Owner: WEPPcloud maintainer. Primary users: signed-in users discovering advanced workflows and newly activated PowerUsers.

## Problem and outcome

Users must currently know to visit Profile before they can discover several PowerUser tools. The form asks whether they need access without concrete examples, implies an application despite automatic approval, and ends with a manual refresh. Internal-access acknowledgment competes with ordinary onboarding. The panel exposes implementation terms before user tasks.

Deliver a connected journey: Runs → Advanced features → Profile onboarding → immediate activation → a useful destination. Preserve server authorization, project permissions and separate internal-feature membership. The operator selected the Runs page for the discovery notice and requested this scaffold after a static human-factors review; this request does not authorize production deployment.

## Scope and design decisions

1. Add a compact, nonmodal **Advanced features** notice on the signed-in user's Runs page, below the header and above the table/map panel. It appears in both views and with zero runs. It does not depend on catalog loading or search results. Show it only when the viewer lacks all three roles PowerUser, Admin and Root, matching current panel eligibility. Dev-only users remain eligible for this notice; Dev is not panel access. Use the viewer, never the selected catalog owner. No persistent dismissal preference in this increment.
2. Link to Profile's PowerUser section, not directly to a privileged operation. Explain concrete capabilities before acknowledgment: Config Builder, project inspection/troubleshooting and personal API tokens. State that compatible projects and separate approval may still be required. Use **Explore PowerUser access** for the notice link and **Enable PowerUser access** for the form submission. Do not open a modal or force activation.
3. Preserve the two affirmative answers, automatic approval, current-user-only target, versioned acceptance, transaction and duplicate-submission behavior. Explain immediate activation. After confirmed success, replace the form with active status and refresh server-rendered account/navigation state through a normal Profile reload anchored to that section. Provide server-generated links to Config Builder, Runs and the getting-started guide. Do not introduce arbitrary return URLs or return-token storage.
4. Keep internal permissions separate. Users without memberships see a short explanation and a deliberate expandable path to the internal statement; membership holders needing acknowledgment see that action prominently. Voluntary acknowledgment remains available. Existing internal operational-role paths and memberships do not change. Legacy PowerUsers see active access and “no action required,” without fabricated acceptance or compulsory retraining.
5. Improve the existing panel's presentation: task-oriented groups for inspection, analysis and troubleshooting; expand technical state/log resources on demand; describe recovery action purpose and consequences. Preserve action handlers and permissions. Keep the established “PowerUser Panel” name consistent in buttons, dialog title and help. Add a getting-started link before developer documentation.
6. Correct the shared report header's unconditional PowerUser button to match the existing panel role guard. Ordinary users must receive neither panel markup nor a dead panel trigger. The main run-page guard remains unchanged.
7. Add a short PowerUser getting-started guide; update user-guide and lock-recovery links. Separate permission, maturity and project prerequisites in explanations. This package replaces the review's broad discovery-menu proposal with the operator-selected Runs notice; it does not reveal all gated feature controls or change registry eligibility.

Proposed notice: **Advanced features** — “Explore PowerUser tools for custom project configurations, project troubleshooting, and API access. Enable access from your profile after reviewing the responsibilities.” Link: **Explore PowerUser access**. Copy must not imply larger compute allocations or blanket access to internal workflows.

## GL Dashboard amendment (PUUX-01A)

Operator clarification on 2026-10-13: GL Dashboard belongs to regular authorized project viewers. Move its link from the PowerUser Panel to More on run and shared report pages. This bounded navigation correction may execute before broader onboarding; do not market dashboard access as a PowerUser benefit. Route authorization and private-run boundaries remain unchanged. See [bounded decision](artifacts/2026-10-13_dashboard_navigation_decision.md) and `docs/ui-docs/contracts/gl-dashboard-navigation-contract.md`.

## Complexity budget and exclusions

Reuse Flask/Jinja, shared Pure UI components, current feature-access endpoints and JavaScript, existing roles and documentation renderer. No new service, queue, datastore, dependency, privilege, endpoint, feature flag, tracking system, migration, or persistent dismissal state. No model/scientific parameter changes; parameterization ADR not applicable. No permission grants by viewing a page; no changes to suspension/reapplication policy, internal approval, or project visibility. Escalation requires evidence that this bounded approach failed an acceptance condition and a recorded smallest alternative.

## Security impact and review gate

Triage: **high** because role-sensitive discovery, onboarding success handling and privileged-panel entry points are touched, even though authority is intentionally unchanged. Dedicated independent security and correctness/UX reviews are required. A security PASS cannot substitute for evidence that ordinary, empty-account and legacy states work. Independent correctness/UX and security reviews are retained below; no production deployment authority is implied.

## Milestones and success criteria

- M0: promote the intended presentation changes to current contracts, obtain two independent contract reviews, disposition findings and commit the standalone ancestor checkpoint before runtime edits.
- M1: Runs notice, Profile explanation, activation completion and fixed destinations; validate ordinary and privileged role matrices.
- M2: internal-access presentation, task-oriented panel, consistent report trigger and user documentation.
- M3: focused/broad regression gates, rebuilt assets when needed, Forest browser evidence and independent final correctness/security review. Record optional observed-user testing separately from static/browser conformance.

Acceptance: a regular user with zero or populated runs can find the notice, explain the capability boundary, activate once, see correct status and use a destination. After reload the notice disappears. Existing PowerUser/Admin/Root users never see the acquisition notice. Legacy access still works. Dev-only status is tested explicitly. Acknowledgment alone never grants internal membership. Keyboard navigation reaches the notice, form, feedback and completion destinations. Ordinary report viewers have no dangling panel control. Runs sorting, filtering, owner scope, pagination and map selection continue working.

## Evidence and rollout

No WEPP output writer or run schema changes are intended, so a new native model simulation is not an acceptance gate. The relevant chain is rendered notice → real authenticated POST → durable role/acceptance readback → fresh Profile/Runs rendering → destination authorization. If generated frontend assets change, rebuild and verify the actual served asset. Use a disposable ordinary account for activation, plus existing legacy and privileged states; never remove a live user's roles to manufacture a fixture. Retain revision, identity class, screenshots and nonsecret results under artifacts. Highest completion claim: Forest implementation and served-browser/durable-database validation complete. Candidate `3df2ec482` contains runtime `ed80608fe` and final test-fixture/evidence corrections. Broad coverage completed in segments: 10,723 distinct passed, 126 skipped; frontend 118 suites/980 tests passed. Existing lint and test-order/timing limitations are retained in the validation receipt.

Forest validation and production deployment are separate. Inspect the canonical deployment entry point before any later rollout proposal. No wepp.cloud changes are authorized by this scaffold. Rollback restores paired templates/JS/docs; it must not erase valid role grants or acknowledgment records.

## Execution and references

- [ExecPlan](prompts/completed/poweruser_discovery_onboarding_execplan.md)
- [Tracker](tracker.md)
- [Contract decision and state matrix](artifacts/2026-10-13_contract_decision.md)
- [Correctness review gate](artifacts/2026-10-13_correctness_review.md)
- [Security review gate](artifacts/2026-10-13_security_review.md)
- Current authority: `docs/schemas/feature-access-governance-contract.md`, `docs/ui-docs/controller-contract.md`, `wepppy/weppcloud/feature_registry/specification.md` and registry YAML. Related governance history is `docs/work-packages/20261001_feature_access_governance/`; do not amend it to define current rules.

## Closure and follow-ups

Delivered the Runs notice, clear immediate Profile activation and real refresh,
legacy/Admin/Root distinctions, secondary internal-access details, task-first
panel, guarded report trigger and registered getting-started guide. All 18
disposable Forest identities are inactive; sessions and temporary project
associations were removed while all three acceptance records were retained.

See [validation and rollout](artifacts/2026-10-13_validation.md),
[source identity](artifacts/source-identity.json) and
[broad coverage accounting](artifacts/broad-coverage.json). Production rollout
must rebuild the usersum index and verify the served guide as specified in the
canonical contract's Delivery and recovery section. No migration or backfill.

Nonblocking follow-ups: existing JWT test-module replacement/order sensitivity,
catalog timing stability, preexisting climate-test lint, existing narrow Runs
search/table/theme overflow, and using the panel's unused desktop grid columns.
No human-participant usability metrics are claimed.
