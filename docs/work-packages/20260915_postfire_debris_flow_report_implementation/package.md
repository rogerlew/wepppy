# Post-fire debris-flow report implementation

Status: Active, 2026-09-16 UTC (package date: September 15 Pacific).

## Scope and authority

Implement the owner-approved saved-assessment report described in the current
[contract](../../ui-docs/contracts/postfire-debris-flow-report-contract.md).
The owner requested execution of the closed design package and answered “yes”
to creating a successor package and making required checkpoint/implementation
commits. This excludes push, deployment, model reruns and source acquisition.
The [design package](../20260915_postfire_debris_flow_report/package.md) remains
unchanged historical evidence, not an active execution record.

## Complexity and compatibility

One additive Flask report/read blueprint, one minimal validated-table projection,
one Pure template/controller, one control link, and focused tests. No new service,
queue, dependency, data store, model formula, file schema or scientific default.
Keep accepted bytes, normal artifact browsing/archive, existing control behavior,
run access and Unitizer authority unchanged. No parameterization ADR is needed.

Security impact: **high**, authenticated read and artifact-download surface.
Dedicated correctness and security artifacts plus independent intuitive-UX review
are required; all medium/high findings must close. Contract-first ancestor must
exist before implementation. Reviews cannot authorize deployment.

## Acceptance

Implemented means the reader/routes/template/controller and tests exist. Wired
means the blueprint, browser bundle and existing control link work together.
Verified means saved M1/M3 values, both frequency sources and the valid/hostile
state matrix have evidence, including real-file boundaries and browser tasks.
Missing live saved bundles are evidence gaps, not authority to create new runs.
Run full Python/frontend gates and retain failures honestly before closure.

See [tracker](tracker.md), [active ExecPlan](prompts/active/report_implementation_execplan.md)
and [checkpoint](artifacts/20260915_contract_decision.md).
