# Unrutted Roads partial-crossing strips

**Status:** Implemented and validated locally on forest; deployment and full-site repair not claimed.
Operator authorized plan execution and forest run mutation/forking on 2026-11-17.
**Created:** 2026-11-17 17:45 UTC
**Owner:** Roger Lew; implementer: unassigned. Scaffold author: Codex.

## Purpose

Allow contour-following `Outslope_unrutted` roads that partially cross a hillslope
to participate in a simplified multi-OFE replacement model. An OFE is a profile
section with its own geometry, soil, and management. Run affected strips and
unaffected remainder separately, then combine their PASS outputs into the original
hillslope input consumed by the watershed run. Reuse the existing replacement path.

## Agreed scope and rationale

- Replace the 60% road-overlap / whole-hillslope-width eligibility gate.
- Do not split unrutted crossings merely at longitudinal elevation reversals.
  Model downslope flow across a contour-following road.
- Preserve total original hillslope area by construction across all contributors.
- Preserve road area where feasible; quantify and explain any target/model discrepancy.
- Use deliberately simplified strips. They are profile/area abstractions, not
  verified terrain drainage partitions or map north–south slices.
- Keep switchback connectivity, flowpath walking, shared contributing-area detection,
  and sequential routing across multiple road crossings out of scope. Document the
  limitation explicitly in user-facing help and output provenance.
- Scope tests to implementation changes and directly affected consumers, as
  explicitly directed by the operator. No repository-wide test suite is required.

The alternative of resolving terrain connectivity first was rejected because it
expands this bounded abstraction into a substantially larger hydrology project.
Conservation of total area does not prove correct allocation of contributing area.

## Complexity budget and exclusions

Reuse Roads preparation, MOFE writers, area accounting, the owned `wepppyo3` PASS
combiner, and existing watershed execution. No new dependencies, queues, services,
datastores, privileges, or deployment topology. Keep insloped and rutted modeling
behavior unchanged. No production mutation, rerun, deployment, or migration is
part of scaffolding. Missing fill/buffer defaults are a separate issue: do not
invent values or waive required fields to make a case execute.

## Contract-first deliverables

1. Complete [contract decision](artifacts/20261117_contract_decision.md), reconcile
   canonical contracts, and draft a parameterization ADR in `docs/adrs/`.
2. Record exact operator ratification, two independent read-only reviews and their
   dispositions, and a standalone ancestor checkpoint commit before code edits.
3. Execute [the active plan](prompts/active/implementation_execplan.md) only after
   implementation authorization and checkpoint completion.
4. Retain scoped regression, native artifact, and independent correctness evidence;
   update Roads specification, README, ENDUSER, and affected operator documentation.

## Compatibility and regression plan

Preserve original hillslope IDs, watershed topology, public keys, and other road
regimes. New accounting/provenance must be additive. Define an explicit preparation
version/invalidation rule so old monotonic candidates cannot silently masquerade
as new unrutted geometry. Preserve old results as historical evidence; loading an
old project must not silently rerun or rewrite it. Specify lifecycle handling for
reprepare, failed execution, archive/restore and fresh result publication before edits.

Validate changed geometry and accounting directly, parse generated native inputs,
combine real strip PASS files, read back the exact watershed-consumed replacement,
and inspect fresh results. Marta hillslopes 141 and 42 are acceptance cases on a
disposable copy, with required parameters supplied from a documented source.

## Security impact and reviews

Scaffold impact: **none**. Planned implementation triage: **high**, conservatively,
because generated native input/PASS file handling and worker model execution are
involved. Dedicated security review is required before implementation closeout,
using `docs/prompt_templates/security_review_template.md`; assess containment and
valid-state noninterference without broadening auth or infrastructure scope.
Independent correctness review uses
`docs/prompt_templates/correctness_review_template.md`. Two independent contract reviews have occurred; final disposition is recorded in
[review artifact](artifacts/20261117_contract_reviews.md). Implementation reviews remain pending.

## Success criteria

- [x] Approved current contract and ADR specify geometry, area targets, tolerances,
      infeasible-area policy, ambiguity policy, and compatibility.
- [x] Two independent contract reviews dispositioned; checkpoint ancestor recorded.
- [x] Partial crossing executes without the 60% gate or longitudinal reversal split.
- [x] Hillslope area closes; road area is preserved when feasible and discrepancies
      remain visible when not feasible.
- [x] Real strip PASS aggregation and watershed consumption verified without adding
      the original baseline hillslope response a second time.
- [x] Scoped regressions pass; unrelated road regimes remain unchanged.
- [x] Switchback/connectivity limitations appear in help and retained provenance.
- [x] Independent correctness/security findings of medium/high severity closed.

## Evidence and completion boundaries

See [incident evidence](artifacts/20261117_incident_evidence.md) and
[acceptance matrix](artifacts/acceptance_matrix.md). A successful job or saved state
is not artifact correctness. Record local validation, environment validation,
integration, deployment, and affected-run repair separately. Current claim is **implemented and scoped forest validation complete**. Full-upload
placement failures and synthetic fixture inputs remain explicit in the tracker.

## References

- [Tracker](tracker.md)
- [Contract-first standard](../../standards/contract-first-change-standard.md)
- [Parameterization ADR standard](../../standards/parameterization-adr-standard.md)
- [Artifact validation](../../standards/generated-artifact-validation-standard.md)
- [Artifact observability](../../standards/artifact-observability-standard.md)
- [Roads specification](../../../wepppy/nodb/mods/roads/specification.md)

## Local outcome

Checkpoint `8e87b2363` precedes all code changes. 191 scoped tests pass; both
independent reviews pass. Valid 141/42 slices complete native watershed/report
execution; full copied upload retains eight explicit infeasible-profile failures.
See tracker and native evidence for exact limits. No wepp1 deployment.
