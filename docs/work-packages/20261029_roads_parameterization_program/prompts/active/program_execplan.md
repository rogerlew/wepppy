# Establish modern Roads parameterization and an editable configuration view

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Deliver a WEPPcloud-generated-soil Roads parameterization that is within an order
of magnitude of FSWEPP2 Roads over a declared, representative matrix, then let users
adjust its supported parameters through a Roads configuration view. The operator
has authorized autonomous experiment selection, replacing repeated requests to run
one more experiment. No CSV editing is required. Success is a scientifically accepted
parameter set plus a working browser-to-native-output workflow.

## Progress


- [x] (2026-10-30 UTC) Record autonomous program authority and configuration-view clarification.
- [x] Inspect prior evidence, canonical Roads design/surface/traffic behavior and Disturbed editor precedent.
- [x] Snapshot acceptance rules and distinct seven-development/six-withheld soil split; full case panel pending.
- [x] Reproduce two distinct negative-flux inputs with current/source drainage and UI mode off/on (eight native runs).
- [x] Declare and launch 576 development runs separating road erosion, surface rock and upper-200mm hydraulic effects; seven new scope tests pass (14 with runtime checks).
- [x] Audit all 576 surface-screen-v4 cases; reject all six UI-only treatments, retaining native failures in every gate.
- [x] Complete 20 runtime diagnostic cases and explain one report discrepancy with clean exact-binary trace and seven-file byte parity.
- [x] Complete and verify all 288 project-runtime-screen-v2 cases; reject all three treatments.
- [x] Complete 18-case fill/buffer boundary diagnostic; resolve one failure class only, retaining remaining failures.
- [x] Complete 30-case role-flag diagnostic and 384-case engineered-surface screen; road-only cap policy passes numerical gates but remains physically rejected.
- [x] Explain all four nonnegative accounting cases using exact-binary traces; retain negative-flux cases as rejected.
- [x] Complete 18 combined-boundary and 18 initial-state cases; remaining native stop persists.
- [x] Prove negative-FIN loss of 38.576 mm net local rainfall; prepare minimal proposed patch and portable, byte-verified reproducer.
- [x] Operator authorized native fix and release wepp_261029, Disturbed matrix, Cedar semantic analysis and illustrated release notes; native implementation now active in WEPP-forest.
- [x] Full Python sanity suite completed: 12,209 passed, 298 skipped, 5,830 warnings in 3454.64 seconds; `/tmp/roads-program-full-pytest.log` (session 23368 terminal).
- [ ] Freeze numerical criteria, physical gates, independent sampling and benchmark manifest.
- [ ] Establish runtime- and configuration-faithful modern/legacy baselines; diagnose negative flux.
- [ ] Search supported parameter families and freeze a successful candidate.
- [ ] Pass independent validation and document the accepted physical/model limits.
- [ ] Prepare canonical contracts, ADR, required reviews and standalone ancestor checkpoint.
- [ ] Implement the user-facing view and Roads-specific parameter application.
- [ ] Validate actual project/browser/native/report workflow, regression coverage and closeout.

## Surprises & Discoveries


The preceding broad study had 960 labeled profiles but only 210 distinct material
and input configurations per treatment. Surface and traffic distinctions were lost
in its generic bare/bare/forest preparation. The actual Roads contract applies
surface rock/cover and traffic-dependent erodibility; restoring these distinctions
is a baseline task, not parameter fitting.

Those simplified studies also omitted `wepp_ui.txt`, which changes native water
balance behavior. Real Roads copies project runtime files. Prior loam/holdout soils
duplicate material; they are not independent validation. Six Flagstaff/new-lithic/
no-traffic source-drainage cases emit negative sediment fluxes. These facts prohibit
promoting the earlier source-drainage alternative as a default.

The new eight-run mode diagnostic reproduced all four mode-off controls exactly.
With `wepp_ui.txt`, both source-drainage inputs stopped emitting negative sediment;
all four UI-mode runs reconciled reports and had zero EBE mismatch events. This
isolates a runtime dependency for those inputs, not a general source-drainage remedy.
Retained results: `artifacts/mode-diagnostic.json` in this package.

Surface-screen preflight exposed two representational differences: historical
WEPP2010 references predate the shared fill/buffer 200 mm normalization, and the
9002 parser stores conductivity-adjustment metadata as strings. The v3 driver
requires exact reference equality after canonical normalization and exact treatment
readback using native parser types. Earlier failed roots are retained. Physical
context and limits are in `artifacts/surface-screen-rationale.md`.

V3 stopped on two paved/loam/site `compact3` native water-balance failures after
128 other cases completed. V4 records failed cases explicitly and reuses only
hash-verified completed cases. The panel and parameter hypotheses are unchanged;
the failed treatment is disqualified, regardless of sediment ratios.

The completed UI-only screen has native failures even in the generic roles baseline.
A 20-case sidecar diagnostic resolves some failures but not all. V7 debugger evidence
proves one report/ELEMENT discrepancy is the explicit `qout` export gate; all seven
native outputs match exactly using container runtime libraries. Host-library traces
have rounding drift and are not parity evidence. Details and rejection counts are
in `artifacts/surface-screen-results.md`. No blanket reconciliation rule is accepted.

The full-runtime screen also fails. Fill-boundary changes resolve Birmingham/sand
but leave Birmingham/clay and Flagstaff failures. Pinned `infpar.for` confirms that
9002 applies a forest saturation-dependent conductivity relation when `ksatadj=1`;
the generic bare soil preparation carries that flag into road/fill. The separate
9001 `ksatfac/ksatrec` formula is not active. This provides the next role-specific
mechanism to test without replacing generated material or weakening acceptance.

The road-only saturation adjustment removal plus surface cap reaches 93/96
magnitude passes with no negative flux. Two native stops remain; four accounting
differences are now individually source-explained with seven-file byte parity.
An exact failure trace observes FIN changing from -22.576984 to -61.1533709 mm,
dropping net local rainfall of 38.57638615 mm. This is a native accounting defect,
not evidence to adjust soil parameters further around the failing case. See
`artifacts/native-water-accounting-decision.md`; proposed fix is unbuilt.

## Decision Log


2026-10-30 UTC, operator/Codex: use one program with delegated experimental choices.
The terminal product is accepted parameterization and an editable Roads configuration
view. Storage is an implementation detail; no CSV-facing requirement.

2026-10-30 UTC, Codex working assumption after optional steering request: use 95%
overall and 90% per major group factor-ten gates with a declared small-load rule.
These are practical engineering acceptance targets, not field-calibration claims.
Freeze them before selecting candidates. Do not revise them silently using results.

Preserve exact `wepp_261026`, generated-soil lineage and the 200 mm normalization.
Parameter changes remain Roads-scoped. Existing projects require explicit adoption
of a new version; shared non-Roads defaults remain unchanged. Deployment is separate.

2026-10-30 UTC: explicit native scope decision requested after exact-binary defect
proof. The requested 261026 identity remains authoritative until the operator
responds. Proposed action is an isolated fix/control investigation and a new native
identity only if validated; preserve all physical gates, old controls and withheld
sampling. Silence is not approval. Source proposal and reproducer are reviewable;
no shared native source, executable or production parameterization has changed.

## Outcomes & Retrospective


2026-10-29 local: the operator resolved the native-pin decision by directing a
WEPP-forest fix and wepp_261029 release. Execute the native package at
`/workdir/wepp-forest-release-20261009/docs/work-packages/20261029-negative-fin-water-accounting/`.
Retain 261026 as control; no acceptance thresholds or withheld soils change.
The following blocked status is historical and superseded by that authorization.

Program blocked awaiting the explicit native-pin decision after repeated goal turns
with the same unresolved authority boundary. No new parameter set accepted and no
production view implemented. The full sanity process remains live (session 23368,
host pytest PID 2947211); latest observation reached the Disturbed soil-artifact
tests at 21% without a reported failure. This is not a full-suite pass or a stopped
process. On resumption, poll the existing handle/log before starting any replacement.
Completed new evidence includes 576 surface-screen cases, 20 runtime diagnostic
cases, 288 full-runtime cases, 18 boundary diagnostic cases and one parity-verified
source-level trace. All candidate families evaluated so far fail; generated material
and withheld sampling remain intact. Combined focused tests: 21 passed.

Subsequent work adds 450 development cases, four complete accounting traces and
an exact native failure trace. Best candidate meets numerical criteria but still
fails physical acceptance. Combined focused tests now pass 30; full suite running.
Native pin decision pending, independent validation and user view still incomplete.
The preceding studies are development evidence only. This package cannot close on
an isolated favorable panel, a plan, or an unwired editor scaffold.

## Context and Orientation


`wepppy/nodb/mods/roads/specification.md` defines actual road configurations and
builders in `roads.py`. Insloped bare/rocked ditches differ; paved/gravel and high/
low/no traffic have explicit parameter rules. Routed outputs may include road,
fill and buffer overland-flow elements (OFE: one modeled surface segment). Their
outlets differ from direct road delivery, so comparisons must align geometry and
contributing area before evaluating sediment.

`tests/roads/roads_matrix.py` exercises production builders and copies canonical
shared runtime files. `tests/roads/roads_project.py` covers full-project workflows.
`/workdir/fswepp2` supplies the reference API, soil/management assets and validation
infrastructure. Previous frozen references and generated specimens remain under
`/wc1/runs/ro/roads-soil-benchmark-20261029` and related Roads study roots.

Exact modern binary is `wepp_runner/bin/wepp_261026`, SHA256
`a6351d371030f702be5eb0d727d8e7181eeb9d60e9ddf6ce05d9616e5d759d48`.
Its source identity is `b73e93b19a724d1991d341d38a18d11e742231bd` in the host
`/workdir/wepp-forest` checkout. Legacy WEPP2010 reference binary SHA256 is
`a12976166deb2b2d7c9adc0e0f23bac24d54057031a5072b4bb0a176c7c730b8`.
No native rebuild is part of the current authority.

The existing Disturbed user editor is in
`wepppy/weppcloud/routes/nodb_api/disturbed_bp.py`; its model lives in
`wepppy/nodb/mods/disturbed`. Use its save/reload/reset interaction as precedent,
not its CSV representation as a product requirement. Read nearest AGENTS before
editing any production subsystem. All durable UX, persistence and parameter rules
must be promoted into current canonical contracts outside this work package.

## Milestone 1: acceptance and faithful baselines


Freeze `acceptance.md`, `autonomy.md` and a machine-readable panel manifest in a new
scratch root, `/wc1/runs/ro/roads-parameterization-program-20261029/`. Preserve previous
roots. Inventory source soils by semantic material, texture and restriction class.
Select new, distinct specimens and withheld combinations without inspecting their
native outputs. Existing five climates and all previously tested cases are known
development evidence; a withheld panel needs genuinely unused combinations/profiles.

Create an audit mapping user configuration to actual management, slope, soil and
runtime files. Exercise production Roads builders in disposable contexts, preserving
surface/traffic/ditch distinctions and outlet semantics. Establish legacy2010,
modern-binary legacy-soil, current project and generated-soil baselines with matched
geometry. Run UI/non-UI negative-flux reproduction for the known Flagstaff case;
retain invalid outputs rather than clipping them. This milestone is exploratory
scaffolding, not a production implementation or closeable deliverable.

## Milestone 2: autonomous parameter search


Use a persistent candidate ledger and bounded batches. Start with faithful Roads
role/surface/traffic composition on generated soils; do not carry forward the generic
bare/bare/forest surrogate as if it already represented all configurations. Explore
physically justified road erosion, critical shear, surface rock/cover and compacted
layer hydraulics, then fill/buffer behavior and source-informed lower boundaries
where evidence warrants. Declare parameter meanings/ranges before each batch.

Prefer screening panels and sensitivity analysis that eliminate failing mechanisms
before a broad confirmation sweep. The agent may choose the next experiment without
operator approval. Every batch names its hypothesis, changed inputs, expected
interpretation and rejection criteria. No climate-, specimen- or case-specific output
multipliers. Do not replace generated soil material with legacy templates as the
candidate; legacy templates remain controls. No new optimizer dependency is needed.

Reject candidates with invalid physics/artifacts before ranking fit. Rank valid
candidates by group coverage, worst departures, bias, hydrologic plausibility and
simplicity. Keep all failures in the ledger, including zero-reference behavior.
When a candidate passes development confirmation, freeze its complete rule set and
inputs before running withheld validation. If that validation drives a revision,
reclassify it as development data and select a new withheld panel.

## Milestone 3: accepted model and product contract


Only a model meeting `acceptance.md` may become the proposed default. Prepare a
parameterization ADR with exact old/new rules, evidence, rationale, alternatives,
uncertainty, decision provenance, migration and rollback. Define the exact fields
that users can edit, their units/ranges/applicability and parameter-set versioning.

Prepare a contract-decision checkpoint under this package. Amend applicable canonical
Roads, UI, API/persistence and artifact contracts with implementation pending.
Enumerate absent, empty, populated, legacy, readonly and malformed states. Preserve
existing projects until explicit adoption; store overrides additively and carry them
through reload/fork/restore. Use current run authorization and CSRF rules. Obtain the
two independent read-only reviews required by the contract-first standard and retain
dispositions. Commit the complete reviewed checkpoint as a standalone ancestor before
production edits; resolve commit authority then if it has not already been granted.
Scientific study work can continue independently of that future gate.

## Milestone 4: configuration view and model wiring


Build a Roads parameterization view organized around road configurations. Show
relevant fields, units, defaults/overrides and concise meaning; validate/save/reset
without requiring native-file or CSV editing. Avoid exposing every WEPP field or
creating a generic optimization dashboard. Custom configurations must be labeled
custom rather than automatically benchmark-validated.

Wire saved choices through the actual Roads preparation path, including routed and
direct branches. Mark affected results stale after edits; saving does not claim to
have rerun WEPP. Produce versioned provenance with generated inputs and reports.
The internal persistence format is selected for the simplest compatible implementation.
Do not change general soil writers, uploaded topology, Disturbed defaults or execution
identity. Complete both implemented and wired behavior before declaring success.

## Milestone 5: end-to-end acceptance


On disposable representative projects, use the browser/API to edit, save, reload,
reset and run Roads. Parse resulting prepared soils/managements, execute the pinned
native binary under real runtime settings and regenerate reports. Demonstrate that
changed values reach the relevant configurations and leave unrelated configurations
and non-Roads state unchanged. Validate fork/restore and explicit version adoption.
Exercise authorization, readonly, invalid-input atomicity and stale-result behavior
through actual persistence/filesystem boundaries, not only mocks.

Run focused tests through `wctl`, then full appropriate Python/frontend/stub/docs
checks. Required independent contract and implementation reviews are part of product
acceptance. No production deployment is implied. Update package, tracker and canonical
user/developer documentation with exact evidence and remaining physical limits.

## Concrete Steps


From `/workdir/wepppy`, discovery begins with `tests/roads/roads_matrix.py`,
`wepppy/nodb/mods/roads/specification.md` and `/workdir/fswepp2` validation entry points.
Use `wctl exec weppcloud python ...` for model/tool execution and
`wctl run-pytest tests/roads ...` for focused validation. Native-source Git reads may
use the host checkout; do not rebuild it. Record actual new driver commands here
when their bounded interfaces are defined. This plan does not invent a CLI before
inspecting the existing infrastructure.

For docs use `wctl doc-lint --path docs/work-packages/20261029_roads_parameterization_program`.
Current screen command: `wctl exec weppcloud python docs/work-packages/20261029_roads_parameterization_program/artifacts/screen.py`.
It refuses an existing batch root. Inspect `/tmp/roads-surface-screen-v4.log` and
scratch `surface-screen-v4/partial-results.json` before any recovery action.
Read canonical contract-first and parameterization ADR standards before production
work. Keep one tracker and candidate ledger rather than opening an approval cycle
for each experiment.

## Validation and Acceptance


`acceptance.md` defines all scientific and product gates. Working numerical targets
are 95% overall and 90% per major group within factor ten for reference exports above
1 kg/year. Smaller loads require candidate no greater than `max(1 kg/year, 10*reference)`
and are reported separately. These rules are explicit engineering criteria and must
be frozen before fitting. Every accepted case must have valid executable artifacts,
complete finite calendars and no negative sediment flux or unexplained accounting
failure. Require both development and withheld confirmation and actual production
builder/full-project evidence.

No completion claim is permitted while only experiments, an ADR or a UI scaffold
exist. Acceptance of the user view requires real generated-output propagation and
fresh Roads reports as well as regression tests and reviews.

## Idempotence and Recovery


Use new scratch batch directories and immutable manifests. Resume only completed
cases whose declarations, actual inputs, mode, output hashes and audit results verify.
Retain failed batches, source snapshots and provenance. Never overwrite production
projects or closed studies. Existing working-tree changes belong to earlier work;
preserve them. Ignore generated docs-index drift. Keep the current git branch.

## Artifacts and Notes


Retain acceptance snapshots, split manifests, candidate ledger, per-case metrics,
physical diagnostics, source/binary hashes, runtime sidecars, review artifacts and
validation logs. Portable summaries live in this package; large native outputs remain
under its declared scratch root and are indexed by manifests. Explain unresolved
failure classes rather than replacing negative results with a favorable aggregate.

## Interfaces and Dependencies


Use existing Roads builders, `WeppSoilUtil`, the shared horizon-boundary helper,
`make_hillslope_run`/native execution and Rust-backed WEPP interchange. Reference
FSWEPP2 artifacts and prior audited accounting are evidence; never silently relax
those validators. Use existing NoDb locking, API/error/CSRF contracts and frontend
patterns for the product. No new external dependency or service is authorized.

Initial revision: 2026-10-30 UTC; one autonomous model-to-product program with explicit
working gates and configuration-view clarification. Production work remains behind
its reviewed canonical-contract ancestor checkpoint.

### Native timing ablation results (2026-10-30)

The explicitly authorized child package implements source-timed upstream return
partitioning and adds a permanent 16-year fixture. Exact tracing exposed shared
ET duplicate-input and root-integral defects; separate ablation lanes correct
them. Fixed-width overflow formatting preserves Rust ELEMENT interchange.

The unchanged 96-case Roads development panel now passes 96/96 magnitude
criteria and all negative-water/sediment and report-accounting checks. Native
validation: 663 tests, 13 watchlist cases, both smokes; Disturbed: 99 tests, with
maximum full-record changes of 0.7603% runoff and 2.2523% sediment versus 261026.
Cedar completes 864 freshly regenerated hillslopes and all 24 watershed years.
All 16,690,464 audited water records are finite and nonnegative.

Cedar total published volume changes -0.41035%, sediment +0.13751%, and maximum
reported peak -0.13860% versus 261026. Event-level changes are larger (screened
peak changes -10.68% to +4.25%), retained for scientific review. Portability-only
control separates inherited changes; do not attribute its +0.66654% sediment
change to the accounting repair. The native child review packet and evidence
reside in `20261030-hourly-return-flow-timing/`. Independent scientific review
remains required by the native physical-water contract before promotion.

No production Roads defaults, editor, binary selection or withheld-soil results
are changed by this study. Continue the parent broader validation/editor work
after accepting and releasing the reviewed native pair.


2026-10-30 UTC release promotion: independent AI scientific, implementation and
publication reviews accepted the bounded261029 release; owner read and accepted
the illustrated report. The matched Linux pair is vendored and passes actual
selected-runner/production-reader and host/container checks. The shared native
blocker is repaired; the Roads development treatment passes96/96 frozen cases.
This does not accept Roads defaults or the user-facing editor: withheld-soil and
broader-geometry validation, parameterization contract and UI work remain in
this program. Release work and final repository gates are tracked in
../20261030_wepp_261029_release/package.md.
