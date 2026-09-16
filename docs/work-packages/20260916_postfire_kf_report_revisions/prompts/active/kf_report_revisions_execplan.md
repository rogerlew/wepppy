# Replace M1 RUSLE K and explain rainfall response


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. The owner
requested execution on 2026-09-16. Source research and canonical amendments passed independent contract review.
Standalone ancestor checkpoint `9395f4722` precedes runtime implementation.
The owner authorized completion after the explicit reviews/checkpoint-commit
request; required review delegation and commits are authorized. No push is authorized.
The owner's follow-up explicitly includes a forest-stack restart and a new M1
run on `nervous-mesquite` during package execution after implementation; do not
perform those operations in the scaffold-editing turn.

## Purpose / Big Picture


An end-user should run M1 without building gridded RUSLE, see a traceable NRCS
fine-earth Kf soil input, and understand how probability changes as rainfall
intensity increases. The existing report gains one duration-linked response
curve with P50 and design-storm markers, not a new dashboard. Dated project-climate
events must distinguish modeled subdaily rainfall from measurements. Existing
watershed delineation, M1/M3 equations and M3 thickness behavior stay unchanged.

## Progress


- [x] (2026-09-16 UTC) Scaffold package, provenance ADR and scope/compatibility plan.
- [x] (2026-09-16 UTC) M1: establish supported Kf source and documented upstream aggregation; independently compare original polygons in two regions and compute a research basin mean.
- [x] M2: independent correctness/security reviews PASS; disposition retained; standalone ancestor `9395f4722`.
- [x] M3: implement and wire Kf preparation, publication and RUSLE decoupling.
- [x] M4: implement response curve, numeric equivalent and rainfall labeling.
- [x] M5: validate generic live behavior and complete independent reviews.
- [x] M5 live gate: restart forest and verify nervous-mesquite end to end with
  new Kf-backed results, report/export/reload and preserved protected inputs.
- [ ] M6: finish durable documentation and implementation closeout.

## Surprises & Discoveries


The 2025 KFFACT COG metadata calls the quantity hydraulic conductivity, but
original USSOILS metadata distinguishes erodibility KFFACT from permeability
PERM. The COG matches independently rasterized original KFFACT polygons in all
301,379 compared cells. Original metadata embeds the complete aggregation
procedure, including missing-value denominators. The endpoint filename uses
lowercase `statsgo`, unlike the existing THICK endpoint. Source research and
failed access diagnostics are retained under `artifacts/source-evidence/`.

The Thomas audit found correct equations but different inputs: POLARIS K
0.337162 versus historical Kf 0.139364; 85.63% versus 69.35% at 24 mm/hour over
15 minutes. Historical metadata names STATSGO, not confirmed SSURGO. Basin
overlap is 96.10%, not identity. This supports changing input provenance, not
fitting parameters to a single observed debris flow. Existing M3 acquisition
supports soil records and THICK, a soil-thickness raster; it is not already a
Kf delivery contract. A curve is useful because the saved NOAA I15 scenarios
start at 36 mm/hour, already 98.89% under the audited legacy inputs.

## Decision Log


2026-09-16 / root, proposed after execution request: use USGS KFFACT COG
policy `statsgo_kffact_1995_cog2025_v1`, documented original aggregation,
unchanged customary Kf units and nearest alignment. Retain the metadata
discrepancy explicitly. Use per-attempt preparation to avoid another mutable
source pointer/cache. ADR-0068 and `docs/kf_source.md` hold the durable proposal.
The report amendment fixes bounded sampling and rainfall provenance. Review
delegation is authorized and underway; no independent approval is yet claimed.

2026-09-16 / owner: replace new M1's RUSLE-derived input with USGS-compatible
fine-earth Kf and eliminate gridded RUSLE dependency. This supersedes the audit's
earlier recommendation to retain POLARIS for future M1 runs. Keep legacy results
readable and honestly labeled; do not mutate their numerical meaning.

2026-09-16 / owner: add a probability/intensity curve; preserve delineation.
2026-09-16 / root: include the accepted rainfall-label clarification, distinguish
source science from source transport, and require evidence before selecting
horizon/component aggregation. Do not transfer M3 strict-material policy to Kf.

2026-09-16 / owner follow-up: require forest-stack restart and nervous-mesquite
end-to-end acceptance after implementation, to prove updated web and worker
processes actually execute the new path. Preserve historical evidence and
protected inputs. This supersedes the earlier exclusion of that named live run
only; no other existing project or host is implicitly authorized.

## Outcomes & Retrospective


Implementation and live acceptance passed. After a full forest restart, normal
UI/RQ runs produced schema-3 Kf on nervous-mesquite and a no-RUSLE fixture.
Independent raster/table/CSV checks and real generated-file archive/restore pass;
M3 browser compatibility passes. Named K changed from 0.337162 to 0.139396 and
I15=24 mm/hour probability from 85.63% to 72.19%, preserving T/F/support.
Initial review issues (native snapshot integrity, selection races, POLARIS
freshness and UX labels) are repaired with regression evidence. Full repository
sanity passes: 8,693 passed, 103 skipped (18:29); all final reviews PASS.
M6 records the final implementation revision and closes the package.

## Context and Orientation


Work from `/workdir/wepppy` (also exposed as `/home/workdir/wepppy`). Read root
and nearest AGENTS plus applicable skills before changing files. The owned
module is `wepppy/nodb/mods/postfire_debris_flow/`. `staley2017.py` evaluates
duration-specific logistic equations: accumulation R = intensity × minutes/60;
M1 uses T (steep/moderate-high burn fraction), F (mean normalized dNBR), and S
(mean fine-earth soil erodibility). Kf is not whole-soil Kw or WEPP Ki/Kr.

`m1_inputs.py`, `integration.py` and `predictor_v2.py` prepare predictors;
`preflight.py`, `production.py`, `run_preparation.py`, `publication.py` and
`migration.py` govern readiness, attempt identity and accepted output. Inspect
`source_acquisition.py`, `source_preparation.py`, `source_transport.py` and
`production_soils.py` for reusable source boundaries, not reusable thickness
science. NoDb and RQ interfaces live in this module, `wepppy/rq/` and
`wepppy/microservices/rq_engine/`.

`report.py` reads accepted results; UI is
`wepppy/weppcloud/controllers_js/postfire_report.js` and
`wepppy/weppcloud/templates/reports/postfire_debris_flow/report.htm`.
Feature prerequisites live in `wepppy/weppcloud/feature_registry/`.
The domain `specification.md`, `docs/m1_predictors.md`, `docs/production_m1.md`,
`docs/production_m3.md`, `docs/production_m3_runtime.md`, `docs/rainfall_results.md`
and the two `docs/ui-docs/contracts/postfire-debris-flow-*-contract.md` contracts
must be reconciled before code changes. ADR-0059 documents the old K choice;
ADR-0068 records the accepted replacement policy and scientific evidence.

## Plan of Work


### M1 — Evidence-backed Kf policy


Research primary USGS workflow/source-product documentation and NRCS field
definitions. Independently reproduce a small authoritative Kf example, then a
basin aggregate. Resolve product/version and source hierarchy, field and units,
depth/horizon selection, component/map-unit weighting, NoData and coverage,
spatial alignment, validity limits and provenance. Preserve the difference
between historical STATSGO inputs and current products; do not advertise exact
USGS parity without evidence. Do not invent a thickness average, mix Kf with Kw,
use the Thomas scalar as an input, or silently fall back to POLARIS. Existing
common-valid support is the starting spatial policy; any change needs its own
explicit rationale. Missing Kf must have a usable, specific unavailable state.

Prefer an existing authoritative Kf product with documented aggregation when
available; otherwise derive from authoritative records only with an evidence-
backed recipe. Retain `artifacts/kf_source_policy.md` and finish ADR-0068. If no
defensible source/recipe is available within scope, report that precise blocker
before implementation rather than adding services or claiming compatibility.

### M2 — Contract and compatibility checkpoint


Write `artifacts/20260916_contract_decision.md`, the exact affected-contract
matrix and valid-state matrix. Cover absent, empty, populated, legacy, partial,
malformed and hostile source/state; changed inputs during preparation; failed
replacement; archived/restored projects; local-only report/preflight reads.
Specify new predictor/source schema, immutable old bundle support, old/new
freshness dispatch, invalidation and human-facing unavailable messages.

Amend all applicable canonical contracts before implementation, marking new
behavior pending conformance. Obtain two independent read-only contract reviews
and disposition findings. The standalone checkpoint must be an ancestor commit
before UI/NoDb/RQ changes. Obtain commit authority if absent; scaffold permission
is not commit authority. Record the checkpoint revision and accepted recipe.

Define the curve payload/range/sampling and bounded request behavior here. Use
accepted model/predictors and existing duration selection (15/30/60 minutes).
Keep probability in [0,1], canonical intensity in mm/hour, Unitizer presentation,
and no modifications to persisted design/event tables. Choose a range exposing
the transition and saved design markers; document deterministic sampling rather
than arbitrary hidden scientific thresholds. Unavailable/non-increasing models
must retain scalar-engine semantics, not fabricate monotonicity or a P50.

### M3 — Implement and wire the source replacement


Implement a focused module-owned Kf adapter and provenance artifact using the
accepted policy. Reuse bounded source transport and native raster operations.
Fresh basins should use the normal Run workflow to prepare supported missing
inputs; do not require operator scripts. Keep network acquisition out of state
and report reads. Remove new-run RUSLE prerequisites and fingerprints everywhere,
including UI, feature registration and queue wiring. Do not delete RUSLE outputs
or change standalone RUSLE or shared soil builders. Verify M3 never gains a Kf
prerequisite. Version manifests and retain failed/intermediate artifact visibility.

Use tests that would fail with the old dependency: M1 can prepare and publish
without a `rusle/` directory or RUSLE completion state; altering unrelated RUSLE
does not invalidate new Kf results. Changing actual Kf inputs/policy does. Legacy
POLARIS attempts retain their own identity/freshness interpretation and do not
silently become Kf-backed. Failed replacement leaves previous acceptance intact.

### M4 — Response curve and provenance labels


Add one simple curve tied to the accepted model and existing duration control,
with P50 and saved design markers and a keyboard-accessible numeric equivalent.
Use existing chart conventions, no new plotting dependency or advanced panel.
Changing units changes presentation only. Curves remain available for supported
legacy M1 and M3 through their saved predictors and retain their source labels.
A curve read must not enqueue a job, fetch sources or rewrite a result bundle.

Clearly distinguish NOAA Atlas 14 statistical design rainfall from project-climate
events. For GridMetPRISM/CLIGEN identify modeled/disaggregated subdaily peaks even
with calendar dates; do not globally label all possible event sources synthetic.
Carry provenance into numeric downloads. Retain conditional-probability,
fixed-postfire/no-recovery, coverage-not-confidence and no-runout caveats.

### M5 — Generated outputs and reviews


Use authorized disposable development fixtures plus the explicitly authorized
`nervous-mesquite` M1 acceptance rerun; `overpriced-sprawl` is not authorized by
this amendment. Validate
two materially different basin/source situations through actual source preparation,
worker execution and browser report using production-equivalent identities and
mounts. Compare Kf, valid support, tables, curves and exports independently.
Confirm protected soils, climate, delineation and standalone RUSLE are unchanged.
Retain module artifacts and archive/restore evidence. Real output from the wired
path is mandatory; a locally callable adapter is not completion.

Before live acceptance, confirm the host is forest, inspect its installed wctl
workflow and `docker/docker-compose.dev.yml`, and record stack services, code
revision, active jobs and health. Use applicable operator/RQ skills at execution
time. Let active work finish before restarting; do not cancel unrelated jobs or
remove volumes. Capture the named run's current accepted bundle/attempt identity
and hashes of protected soils, climate, DEM/routing, SBS/dNBR and RUSLE artifacts.
Preserve its previous accepted attempt and a recoverable snapshot of mutable
module publication/state using the repository's supported archive mechanism.

Restart the forest stack through its canonical workflow after code/assets are
ready. Verify services recover and both web and workers load the intended code;
a restart alone is insufficient if an image or generated asset remains stale.
Record actual commands, timestamps and sanitized health evidence. If recovery
fails, stop acceptance and restore service via the documented recovery procedure;
do not expand to another host or erase persistent state.

At `https://wc.bearhive.duckdns.org/weppcloud/runs/nervous-mesquite/`, run M1 via
the normal browser/RQ workflow, including bounded Kf preparation if needed.
Follow the real job tree to completion. Prove the accepted attempt is new and
Kf-backed; validate source identity, coverage and newly published manifest plus
events/design/inverse parquet files. Independently recompute representative
probabilities and P50; compare old/new predictors and the fixed 24 mm/hour
benchmark without requiring historical USGS equality. Confirm the rendered
curve, duration/unit changes, provenance labels, exports and reload all use
the new accepted identity. Verify protected-input hashes remain unchanged.
Do not remove this project's RUSLE data; absence-of-RUSLE proof belongs in the
separate fixture. Retain `artifacts/forest_restart_validation.md` and
`artifacts/nervous_mesquite_e2e.md` with job/attempt IDs, hashes and browser
evidence. Both are mandatory acceptance evidence, not optional follow-ups.

Run independent correctness, security and dedicated UX reviews. UX review must
advocate clear ordinary-language labels, a useful default curve and no unnecessary
controls. Security verifies bounded source fetching, path containment, race-safe
publication and no regression for valid absent/legacy states. Resolve medium/high
findings before closure. Review artifacts use the repository templates.

### M6 — Durable documentation and closeout


Update scientific, user, operator and developer docs, source recipe/ADR, feature
prerequisites and roadmap. Keep closed audit packages immutable. Update tracker
and this plan throughout. Move this plan to completed only after wiring, real
acceptance and review evidence exist, and distinguish deployment from development
acceptance. Commit/push/deployment require the applicable explicit authority.

## Concrete Steps and Validation


Use `rg` to inventory RUSLE coupling and add the file-level impact map to the
contract artifact. Reuse installed dependencies. Read the tester and accessibility
skills when running their corresponding gates. From the repository root:

    wctl run-pytest tests/nodb/mods -k postfire_debris_flow --maxfail=1
    wctl run-pytest tests/microservices/test_rq_engine_postfire_debris_flow.py tests/weppcloud/routes/test_postfire_report_bp.py
    wctl run-npm lint
    wctl run-npm test
    wctl check-rq-graph
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260916_postfire_kf_report_revisions

Update `wepppy/rq/job-dependencies-catalog.md` if queue edges change and inspect
real job trees. Run stub checks if public surfaces change. Add focused tests for
Kf/Kw distinction, source lineage, unit/aggregation boundaries, coverage, absent
RUSLE, old bundles, race/failure preservation and curve/report provenance. Test
curve/sample values against independent published-coefficient calculations,
including mm/hour versus inch/hour equivalence and P50. Expected outcome: no
new regression; retained logs name exact pass counts, skips and limits.

## Idempotence and Recovery


Prepare attempt-local artifacts, then promote only when original source identity
still matches. Retry through the existing workflow. Never repair shared soil
caches, relabel old inputs, or remove prior accepted results. Incompatible or
unavailable Kf prevents a new acceptance with a specific reason. Rollback of new
code must preserve old readable bundles; define schema compatibility before
writing any new schema. Keep failed artifacts inspectable under normal browse
and archive mechanisms; exclude credentials from all retained evidence.

## Artifacts and Interfaces


Retain source policy/evidence, contract checkpoint and reviews, compatibility
matrix, source manifest examples, independent numeric comparison, real job and
browser evidence, and final review dispositions. The exact new callable and
schema names are fixed at M2 after inspecting existing adapters, not invented
as a parallel framework. Input identity must bind source product/field/version,
units, aggregation policy, grid/support and hashes. New-run M1 consumes Kf only;
legacy readers may consume their recorded historical K. No source owns mutations
outside the post-fire module's explicitly contracted output boundary.

Revision 2026-09-16 UTC: scaffolded the owner's Kf replacement and report changes;
no implementation or validation completion is claimed.

Revision 2026-09-16 UTC: owner added forest restart and nervous-mesquite live
acceptance; updated authorization, milestone and evidence requirements. No
restart or rerun performed during this documentation amendment.

Revision 2026-09-16 UTC: execution request received; completed source research
and independent native-field comparison, prepared canonical proposals and state
matrix. Documentation validation passed (20 files) and diff whitespace check
passed. Independent review delegation and checkpoint commit authority are pending.
Resume M2 before any runtime changes; evidence is in `artifacts/checkpoint_validation.md`.

Revision 2026-09-16 UTC: owner reiterated complete-package delivery, restart and
end-to-end acceptance after explicit reviews/commit permission request. Proceed
through required reviews and commits without another permission stop. The user
restarted and reran the old implementation before this continuation; capture the
latest accepted attempt as baseline, not the earlier research attempt.

Revision 2026-09-16 UTC: checkpoint `9395f4722` passed both independent reviews.
M3/M4 implementation and focused tests underway. Every new M1 attempt prepares
fresh Kf and recomputes its predictor bundle so source provenance remains owned
by that attempt; legacy climate-only predictor reuse is not applied to schema 3.

Revision 2026-09-16 UTC: 633 module tests, 250 route/render tests, archive
regression, 112 frontend suites/899 tests and Go tests pass. Forest restarted;
preflight required a second start after Redis finished LOADING. Both live browser
flows pass, including RUSLE removal immediately and after two reloads. Named run
and generic evidence, source receipts and generated-file archive roundtrips are
retained. Full-suite sanity/final review remains in progress.

Revision 2026-09-16 23:27 UTC: full repository gate passed, 8,693 tests with
103 skips and 3,135 retained warnings (1,109.71s). All three final independent
reviews PASS. Complete final telemetry/documentation/commit and move this plan
to completed; no runtime or acceptance work remains.
