# Staley rainfall adapters and M1 results

Status: scaffolded 2026-09-10 05:15 UTC (2026-09-09 Pacific); not executing.
Starting WEPPpy revision: `264b54845`. Roadmap stage 4, local M1 scope.

## Purpose

Consume a completed M1 predictor bundle and existing Climate-owned artifacts to
produce individual wet-event probabilities, short-return-interval design-storm
comparisons and inverse rainfall thresholds for the existing project watershed.
Deliver reproducible machine-readable results and a bounded local query interface
for later dashboard use, preserving input provenance and unavailable states.

Read the [ExecPlan](prompts/active/rainfall_results_execplan.md),
[tracker](tracker.md), [readiness review](artifacts/predecessor_review.md), and
[decision register](artifacts/decision_register.md). The
[proposed contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/rainfall_results.md)
is current design, not approved new parameterization.

## Boundaries and acceptance

Use existing event intensities; do not reconstruct CLIGEN storms or modify the
Climate frequency estimator. No network acquisition, climate/predictor rebuild,
NoDb/RQ/UI, public query endpoint, installation or deployment. M3 numerical
support exists, but M3 predictor-bundle integration remains separately scoped.

Acceptance requires verified predictor/Climate input identity, event and design
source separation, correct mm/hour-to-mm conversion, independent scalar parity,
explicit missing/invalid cases, inverse statuses, reproducible output and local
query behavior, realistic catalog performance, full validation and independent
correctness/security reviews. Reuse authentic Wallow predictor evidence and
obtain matching genuine Climate artifact snapshots read-only; no synthetic
fixture may masquerade as authentic Climate/NOAA acceptance.

Security impact: **high** for new parquet/CSV/JSON loading, local result writing
and query boundaries. Dedicated security artifact required; close all medium/
high findings. Querying is local only and must not admit arbitrary SQL or follow
untrusted manifest paths. Unrelated dirty quality-report files are outside scope.
