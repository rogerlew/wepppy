# MOFE ground-cover propagation

Status: Complete (Forest validation), 2026-09-19 UTC. User authorized correction
and Forest validation on 2026-09-18; production deployment remains outside scope.

Apply existing saved interrill/rill cover selections to each assigned MOFE
segment, regenerate managements after cover edits, and preserve selections on
summary rebuild. MOFE means multiple overland-flow elements within a hillslope.
No default, schema, API, queue, soil parameter or canopy/RAP formula changes.

Validate a supported disposable fork of Forest `equestrian-bonheur`; preserve
the source's low-severity state. No production deployment or production-project
repair is authorized. See [plan](prompts/completed/execplan.md), [tracker](tracker.md),
[checkpoint](artifacts/20260918_contract_decision.md) and
[ADR](../../adrs/ADR-0069-mofe-ground-cover-propagation.md).

All 1,065 segments across 455 hillslopes carry the selected 90% ground cover in
generated and prepared files; source project unchanged. WEPP 260803, downloads,
archive/restore and independent review pass. Full suite: 9,044 passed, 99 skipped;
focused suite: 93 passed. See [validation](artifacts/20260919_validation.md).
The durable decision is in the [Ground-cover propagation contract](../../schemas/mofe-management-artifact-contract.md#ground-cover-propagation).

Security impact: low; existing authorized mutation and filesystem boundaries,
no new inputs or access. Complexity budget: four local landuse seams, focused
regression tests and validation evidence; no new runtime subsystem/dependency.
