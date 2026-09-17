# Thomas Fire saved-assessment verification audit

Status: Complete (audit only), 2026-09-16 UTC. Remediation not authorized or implemented.

## Objective and authority

Audit the owner's completed `nervous-mesquite` Thomas Fire assessment and identify
actionable model shortcomings. Distinguish implementation errors, input-source
and delineation differences, scientific limitations, and missing comparison
evidence. This is an audit, not permission to fix production code or rerun models.

## Scope and complexity budget

Read existing run artifacts on forest at `/wc1/runs/ne/nervous-mesquite`;
independently check saved predictors, equation outputs, rainfall semantics and
report projection. Retrieve bounded public USGS reference evidence when useful.
Write only package-owned audit scripts, derived evidence and documentation.
No run writes, cache repairs, jobs, new dependencies, source substitutions,
deployments, commits or push. Existing numerical/geospatial libraries are reused.
No scientific policy changes or parameterization ADR are required for this audit.

Security impact: none (no application/attack-surface change). No dedicated
security review is required. Credentials and private user metadata are excluded
from retained evidence. Independent agent work is not requested for this audit.

## Acceptance and deliverables

Record accepted attempt identity, source hashes, coverage, all saved probability
and threshold numerical checks, a matched-rainfall USGS comparison with explicit
basin/input compatibility limits, and prioritized recommendations with evidence.
Prove inspected scientific/project files are unchanged. An honest finding of
insufficient external parity evidence is acceptable; unsupported validation is not.
Retain reproducible audit artifacts and a concise findings report. Audit closure
does not mean any diagnosed shortcomings have been remediated.

## Outcome

All saved numerical/raster/report checks passed. Matched USGS basin 19384 has
96.10% polygon intersection/union; at I15=24 mm/hour the run predicts 85.63%
versus USGS 69.35%. Soil-input difference explains most of the logit difference.
Priorities: source-comparability disclosure, modeled-subdaily-rainfall provenance,
and historical terrain/input benchmarking. No strict soil gate is proposed.
Read [findings and recommendations](artifacts/findings.md) for evidence and limits.

See [tracker](tracker.md) and [ExecPlan](prompts/completed/verification_execplan.md).
