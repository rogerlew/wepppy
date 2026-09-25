# Dead Horse Creek M3 audit

Status: Closed, 2026-09-17 UTC. Started 2026-09-16 Pacific.

## Purpose and scope

Audit the saved M3 assessment for `thespian-cleanness` (Dead Horse Creek,
Grizzly Creek Fire) and compare with Rengers et al. (2024),
https://nhess.copernicus.org/articles/24/2093/2024/ . The owner requested this
work package and explicitly selected that paper as the comparison reference.
Verify saved numerical results, raster predictors, source lineage, coverage,
report projection and what the published observations can actually validate.

Read the existing run without rerunning or changing its inputs, settings or
accepted results. Retain independent audit scripts, checksums and findings here.
Production remediation, model recalibration, stack restart and new model runs
are outside this audit. Distinguish implementation correctness, input
representativeness and predictive validation. The paper evaluates M1, not M3;
its volume results are not M3 probability predictions.

## Complexity budget and review

Reuse existing Python/raster/parquet tools, public scientific sources and local
read access. New dependencies and infrastructure: none. Security impact: low,
read-only authorized run inspection and public-source retrieval; no security
boundary change or dedicated security review required. No parameterization
change; no ADR required. Stakeholder: requesting owner. Audit conducted locally.

## Acceptance

Identify exact accepted attempt and source hashes, independently recompute M3
predictors and all tables, inspect report payload, determine SBS lineage and
coverage exclusions, and compare basin/storm/model scope against the paper.
Record limitations and actionable findings without forcing numerical agreement.
Verify protected run artifacts remain unchanged. Lint package docs and close
the execution plan when findings and reproducible evidence are complete.

[Tracker](tracker.md) · [ExecPlan](prompts/completed/audit_execplan.md)

## Outcome

[Findings](artifacts/findings.md): saved calculations, SBS lineage and authenticated
report pass. Four scientific validation/provenance limitations are documented,
including 45.53% missing SBS, basin size and uncertain observed storm pairing.
All 181 protected files remain unchanged. No production changes or model rerun.
