# Optional module visibility repair

**Status**: Closed locally, 2026-11-05. **Timezone**: UTC.

## Overview

The objectionable-hemline project enables disturbed and roads, yet renders an empty Observed Data Model Fit shell. Ron initializes observed.nodb for ordinary projects; run-page rendering mistakes that empty object for an enabled feature. Repair that mismatch and audit other optional modules and downstream visibility consumers.

## Scope and authority

This is a conformance repair under `docs/standards/contract-first-change-standard.md#conformance-fixes-and-urgent-restoration`. Unchanged authority: `wepppy/weppcloud/feature_registry/specification.md#runtime-semantics` (own feature state, retained readable results, safe optional absence), `docs/schemas/feature-access-governance-contract.md` (FA-01/FA-02 inspection), and `docs/ui-docs/controller-contract.md` (bootstrap idempotence and missing-section no-op).

User authorization on 2026-11-05: scaffold and execute this package, check other modules for the same pattern, scope tests to the changes, and do not run the full suite. No deployment or project-state mutation is included. No normative contract change is intended.

## Complexity budget

Reuse existing run context, registry, templates, controllers and tests. Permit small predicates and regression fixtures only. No new dependency, service, queue, storage, protocol, permission or deployment topology. Do not alter model execution, parameterization, initialization, auth or persistence. Test the simplest visibility correction before considering larger changes.

## Success criteria

An off module with only empty initialized state does not render its control shell or active navigation. Enabled Observed and retained model-fit results stay inspectable; preview remains supported. Missing optional state renders safely. Audit every optional run-page module, template fallback, bootstrap consumer and dynamic-section path; repair confirmed same-class defects and record exclusions. Focused regression tests and independent correctness review pass.

## Security impact and review gate

Triage: none, confirmed by independent review. Only existing presentation predicates and bootstrap selection are in scope; no new endpoint, authorization, input handling, storage or execution boundary. Independent correctness review is required; dedicated security review is unnecessary unless the actual patch expands the attack surface.

## Generated artifact validation

No scientific artifact producer changes. Directly render and inspect HTML and bootstrap JavaScript, the artifacts consumed by the browser. Reuse existing Pure shell markup (Ash/Omni conditional sections as references). Record the reported project's durable mod list and empty results without modifying it. Deployment and live incident resolution are separate claims.

## Hardening and observation

Broken assumption: an optional controller object implies feature activation. Health: no empty off-feature shell, retained results still visible, enabled controls unchanged. Danger: hidden retained data or unintended initialization. Observe through scoped state-matrix tests before handoff; after any later deployment, reload the reported project. No temporary mitigation or cleanup is introduced. Related precedent: current registry own-state rule and Omni Contrasts gating; history is evidence, not authority.

## Deliverables

[Tracker](tracker.md), [ExecPlan](prompts/completed/implementation_execplan.md), bounded consumer audit, focused regression evidence and independent correctness artifact. [Consumer audit](artifacts/consumer_audit.md) and [independent correctness review](artifacts/20261105_correctness_review.md) retained. All confirmed Observed consumers repaired; no second server-side module activation defect found within the audited scope.

## Closure notes

Closed 2026-11-05 17:24 UTC as implemented and locally validated. Validation: 537 scoped Python tests, 90 distinct scoped JavaScript tests, scoped ESLint, docs lint and changed-file broad-exception enforcement passed; controller bundle rebuilt. Independent review passed with no unresolved findings. The user explicitly excluded the full suite.

Durable behavior and rationale are recorded in `wepppy/weppcloud/controllers_js/README.md`, **Observed Controller Reference / Visibility and remounting**, and user guidance in `wepppy/weppcloud/routes/usersum/weppcloud/observed-model-fitting.md`, **Prerequisites** and **Troubleshooting**. Existing registry **Runtime Semantics** and shared **Singleton + bootstrap** contracts remain unchanged.

No deployment or project-state repair was performed. Reload the reported project with authenticated access after deployment to establish live incident resolution. The audit is bounded to run-page module visibility and its consumers; unrelated module workflows and live WebSocket transport are not claimed as validated.
