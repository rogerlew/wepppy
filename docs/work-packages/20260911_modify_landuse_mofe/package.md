# Modify Landuse MOFE conformance

Status: contract checkpoint in preparation; implementation pending.

The operator requests that selected-hillslope Modify Landuse regenerate MOFE
management files and reflect treatment classes in summaries. Scope is the
selected-hillslope route and Landuse controller, regression tests, and relevant
documentation. Class-to-class mapping, deployments, and production run repair
are excluded. No new infrastructure, dependencies, or model parameterization.

Security impact: low; existing authorized mutation and output paths only.
No dedicated security artifact is required unless implementation expands that scope.

Acceptance is governed by `docs/schemas/landuse-modification-contract.md`.
Implementation must include real file-content and downstream preparation evidence,
focused and broad tests, and independent correctness review.
