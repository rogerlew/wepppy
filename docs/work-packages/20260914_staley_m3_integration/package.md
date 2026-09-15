# Production M3 and valid-support estimates

Status: bounded acquisition and production integration are implemented at
`6f64d45a0` / `b998d44e2`; development multi-basin/browser/archive acceptance
passes. Final regression closeout is in progress. Package archival remains on
hold for owner disposition of SEC-06, the recorded credential exposure.
Strict material rules were rejected and recorded-depth policy accepted.
See [replacement assessment](artifacts/depth_policy_assessment.md),
[inventory](artifacts/source_inventory.md),
[proposal](artifacts/source_delivery_proposal.md) and
[preliminary reviews](artifacts/20260914_preliminary_reviews.md).
Owner: repository user. Starting revision: `97800607c30c0979d422f99b1e2c65f1b8a89ab5`.

## Purpose and scope

Complete scientific M3 execution through the existing control and RQ task, and
implement approved valid-support scalar estimates for both models. Users can run
M1 or M3, inspect actual probabilities, see valid coverage and download the exact
mask plus intermediate records. M3 now executes the scientific model; incomplete
terrain remains explicitly unavailable rather than receiving invented values.

Compose existing thickness, WBT relief and numerical/rainfall components;
preserve Horn and published coefficients. Initial M3 requires 10 m `ned13/2022`.
SSURGO remains primary and original STATSGO THICK fallback. Keep one project
watershed/outlet, existing rainfall choices and SI/English presentation.
The [current contract](../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3.md)
records the approved support, isolated soil policy and source-delivery scope.

Source preparation must be reusable across eligible basins: derive original
map-unit keys and THICK extent from each project, with no named-run branches,
fixed 34-key list or hand-built per-basin manifests. `addicted-reservist` is one
validation case only. The durable [basin-independent preparation requirement](../../../wepppy/nodb/mods/postfire_debris_flow/docs/production_m3_runtime.md#basin-independent-preparation-requirement)
records the owner's 2026-09-14 clarification and rationale.

This is full scientific integration, not another selectable surrogate. Completion
requires outputs from the installed owned WBT path and actual development RQ
jobs. Reports/dashboard, nested basins, additional terrain sources, model
recalibration, soil-builder repair and production deployment are excluded.

## Isolation and complexity budget

**No changes to existing SSURGO/STATSGO soil-building behavior.** Read existing
raw records and original spatial provenance through module-owned adapters.
Do not rebuild Soils, alter `Horizon.valid`, component/donor selection, hydraulic
clipping, shared caches or generated `.sol`/WEPP inputs. Existing offline helper
defaults remain reproducible. The [regression plan](artifacts/soil_regression_plan.md)
requires source preservation and generated-output evidence, including failures.

Budget: existing NoDb, RQ, UI, owned native raster tools and soil helpers only.
No new services, queues, dependencies, schema migration of shared soil caches or
soil acquisition infrastructure. Generic bounded preparation implementation is
authorized by the owner's scope clarification and continuation; the owner
separately authorized bounded network execution at `2de5ca737`. That acquisition
and retained-evidence recovery are complete, without expanding the limits.

## Milestones and decisions

1. Audit real sources, ratify soil material/paired-horizon/component/fallback
   rules, finalize schemas/freshness and commit a reviewed contract checkpoint.
2. Implement isolated M3 thickness preparation with retained source diagnostics
   and prove SSURGO/STATSGO builder noninterference.
3. Compose full-basin terrain and both models' common valid support; publish
   exact masks and numerically verified predictors.
4. Finish worker/publication/freshness and canonical coverage summaries.
5. Complete independent correctness, QA and security reviews; full tests and
   actual browser/RQ/download/archive acceptance; synchronize living docs.

The [decision register](artifacts/20260914_contract_decision.md) records ratified
soil and source-delivery choices. NRCS documents paired depth records and
percentage totals above 100: the strict offline helper is not an automatic
production usability gate. [Research and fixture audit](artifacts/soil_research.md)
are completed scaffold evidence, not calibration validation.

## Compatibility and exit evidence

Add coverage/source metadata and mask artifacts without deleting or relabeling
legacy results. Preserve public filenames, job lifecycle, selection state,
authorization, locks and failed attempts. Old support-policy predictors must not
be reused as new ones. Full-support M1 stays numerically equivalent; partial M1
changes deliberately under ADR-0066. Valid unburned cells are included.

Acceptance includes genuine M3 SSURGO output, explicit original-THICK fallback,
partial/zero support, stable full-basin ruggedness under soil/SBS masking, source
changes during execution, and unchanged WEPP soil builds before/after integration.
Use `addicted-reservist` for the large 10 m development acceptance if its current
inventory remains suitable; audit first, do not rebuild its soils to make a test
pass. Require another independent basin with different keys and extent through
the same preparation/execution path; include primary/fallback/missing cases.
Use frozen three-site fixtures and isolated projects for destructive cases.

Security impact: **high** (worker subprocesses, source files/SQLite, publication,
download and optional bounded source acquisition). Require independent contract
reviews before the standalone checkpoint and dedicated final correctness and
security artifacts with no open medium/high findings. Independent correctness,
soil-builder QA and security reviews have run; the sole external hold is SEC-06.
See [development acceptance](artifacts/20260914_live_validation.md) and the
[security review](artifacts/20260914_security_review.md). The
[ExecPlan](prompts/active/execplan.md) and [tracker](tracker.md) remain active
until explicit credential-response or risk-acceptance disposition permits closure.
