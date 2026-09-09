# Staley M1 prepared predictor integration

Status: scaffolded 2026-09-09 15:06 UTC; execution not started.
Baseline WEPPpy `2c4d1a94f`; WBT slope backend `a97abb7`.

## Purpose and scope

Compose the completed Horn/SBS, dNBR and numerical backends into one local
M1 predictor build for the existing project watershed/outlet. Consume prepared
WEPP Soils, SBS, dNBR and RUSLE Nomograph K artifacts read-only. Produce an
inspectable new artifact bundle containing T/F/S, independent coverage,
unavailable reasons and reproducible source identity. Demonstrate explicit
rainfall scenarios through the existing engine; climate ingestion is later work.

Read the [ExecPlan](prompts/active/m1_predictors_execplan.md),
[tracker](tracker.md), and [decision register](artifacts/decision_register.md).
Canonical proposal: [M1 predictor contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/m1_predictors.md).
Update it and the module specification/roadmap together as decisions are made.

## Boundaries

This is local backend integration, not NoDb/UI/RQ publication or deployment.
No automatic soils/POLARIS/RUSLE rebuild, external acquisition, climate export,
M3 fallback integration, nested catchments or alteration of previous run data.
Do not relax WBT input restrictions or replace Rust raster traversal with Python.
The installed production binary is not assumed to contain StaleySlopeSbs.

## Acceptance

- K convention verified from publication/source metadata and the actual RUSLE
  formula/output; accepted coverage and dependency contract/ADR before code.
- Prepared grayscale WBT-compatible DEM/SBS/mask copies preserve source values,
  masks and exact grid. Actual rebuilt binary is invoked and identified.
- One versioned predictor bundle, independent T/F/S support, immutable source
  fingerprints and distinguishable complete/partial/unavailable results.
- Real-project read-only artifact evidence plus labeled controlled fixtures;
  successful explicit-scenario evaluation and unavailable-input preservation.
- Focused/full tests and independent correctness/security reviews, no unresolved
  medium/high findings; generated output and failure evidence retained.

Security impact: **high** for new file preparation, binary invocation and local
publication boundaries. Dedicated security artifact required. No production
process/mount installation is claimed; shipping a future cross-container caller
requires its own end-to-end identity/mount evidence and contract checkpoint.

Completes the local M1 composition portion of stage 3 when validated. Live
prepared-input publication, controller readiness/invalidation and orchestration
remain stage 5 work. Package scaffolding alone completes no implementation stage.
