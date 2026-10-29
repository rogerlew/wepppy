# Project developer mode

**Status**: Open — implementation and local environment validation complete, 2026-10-29 UTC; full Python gate and closeout in progress. No production deployment.

## Overview

Allow a Dev user to activate developer mode without an off toggle on a project through the PowerUser panel. Ron owns the state, clones retain it, and anisotropy maximum enforcement follows project mode without a submission-time Dev check.

## Authority and scope

[DM-01](../../schemas/project-developer-mode-contract.md) owns lifecycle and activation; [SA-01](../../schemas/soil-anisotropy-contract.md) owns soil behavior; [ADR-0088](../../adrs/ADR-0088-soil-anisotropy-overrides.md) records parameterization rationale. Execute only the [implementation ExecPlan](prompts/active/implementation_execplan.md) for this package, not unrelated active plans.

Included: Ron state/stubs, one activation route and panel action, visible mode status, policy propagation to Python/Rust, cloning and archive/restore conformance, tests and user/operator/developer docs. Excluded: deployment, account-role assignment, scientific model changes, new generic developer bypasses, queue topology, bulk project migration and edits to closed work packages.

The operator has authorized execution of this work package. Implementation follows a standalone reviewed contract ancestor commit; production deployment remains out of scope.

## Complexity budget

Reuse Ron/NoDb locking, existing project authorization/CSRF, PowerUser presentation and native soil preparation. Permit one boolean, one activation action and an additive explicit native policy argument. No new dependencies, services, queues, datastores, global audit system, role hierarchy or deployment topology. Test this bounded approach first; escalation requires retained evidence that it fails the actual acceptance condition.

## Compatibility and regression plan

Add missing-false Ron state without migrations; retain all existing inputs and default native call behavior. Verify real lock/reload and clone/archive boundaries before changing data flow. Default projects retain exact numeric limits and output parity. Activated projects accept finite values >=1 and propagate elevated overrides to generated files. Test every normal/dev, role and malformed-state case in DM-01 and the checkpoint before broad gates. Native/Python versions must be paired; reverting code must not reset activated project data.

## Generated artifact validation gate

Applicable: yes. Trace authorized activation and anisotropy submission through durable Ron/Wepp reload, prepared `wepp/runs/p*.sol`, actual model-consumed input, fresh execution output and normal browse/download/report presentation. Record revisions, native build hash, run id, runtime identity/groups/mounts/umask and source/output semantic comparisons. Use an isolated representative project and real native writer and clone/archive paths. Validate upper=101 and lower=11 reach the correct classes; numerical instability is reported, never silently clamped. Retain failed-job evidence and distinguish preparation acceptance from successful simulation. Highest current evidence: implemented and locally/environment validated for the bounded workflow in artifacts/validation.md; not deployed to production.

## Security and review gates

Security impact: **high**, because a new privileged public route and panel-access boundary are involved. Dedicated [security review](artifacts/20261029_security_review.md) and independent [correctness review](artifacts/20261029_correctness_review.md) are required; design review cannot close runtime gates. Two independent read-only contract reviews and primary-agent dispositions must precede the ancestor commit. No unresolved medium/high implementation findings at closure.

## Parameterization ADR gate

Parameterization threshold change: yes. ADR required: yes. Amend existing ADR-0088 with DM-01 scope and conversation provenance; implementation conformance remains pending. This changes accepted experimental inputs, not defaults or model equations.

## Stakeholders and success criteria

Decision owner: requesting operator. Intended experimenter: Anurag. Implementer: future assigned agent/developer. Reviewers: independent correctness and security agents.

- [ ] Reviewed contract checkpoint committed before implementation.
- [ ] Dev-only activation is enable-only, idempotent and durable; no unrelated privilege expansion.
- [ ] Ordinary authorized non-Dev callers can submit elevated overrides on activated projects.
- [ ] Clones inherit source mode/settings; archive restore and failed-fork recovery use incoming state, including normal mode, through real boundaries.
- [ ] Real generated input, fresh execution and project-tool evidence retained.
- [ ] Focused/native/frontend/broad checks and independent runtime reviews complete.
- [ ] Affected user/operator/developer docs updated and deployment status explicit.

## Related work and tracking

The original soil-anisotropy package is historical provenance only. Feature access governance and project config remain separate owners and are not advanced or closed by this package. See [tracker](tracker.md), [contract checkpoint](artifacts/20261029_contract_decision.md) and [review dispositions](artifacts/20261029_review_disposition.md).

## Approved lifecycle replacement exception

On 2026-10-29 UTC the operator approved incoming archive/source mode replacing the destination mode during archive restore and existing failed-fork recovery. Do not add sticky-state preservation, mode-based denial or extra Dev checks to recovery. No off toggle exists; a recovered normal project follows normal bounds and Dev can enable it again. This keeps established recovery available and minimizes implementation risk.
