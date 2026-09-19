# MOFE ground-cover propagation

Status: Active. User authorized correction and Forest validation on 2026-09-18.

Apply existing saved interrill/rill cover selections to each assigned MOFE
segment, regenerate managements after cover edits, and preserve selections on
summary rebuild. MOFE means multiple overland-flow elements within a hillslope.
No default, schema, API, queue, soil parameter or canopy/RAP formula changes.

Validate a supported disposable fork of Forest `equestrian-bonheur`; preserve
the source's low-severity state. No production deployment or production-project
repair is authorized. See [plan](prompts/active/execplan.md), [tracker](tracker.md),
[checkpoint](artifacts/20260918_contract_decision.md) and
[ADR](../../adrs/ADR-0069-mofe-ground-cover-propagation.md).

Security impact: low; existing authorized mutation and filesystem boundaries,
no new inputs or access. Complexity budget: four local landuse seams, focused
regression tests and validation evidence; no new runtime subsystem/dependency.
