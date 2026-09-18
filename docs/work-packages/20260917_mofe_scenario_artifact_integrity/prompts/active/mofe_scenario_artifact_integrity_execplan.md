# Restore MOFE scenario inputs and repair the Rithet Creek runs

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be updated at
every stopping point. Maintain this plan in accordance with
`docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, a WEPPcloud user who selects a fire severity, an SBS raster, a
prescribed burn, or a canopy-thinning percentage will get MOFE management files
and prepared WEPP inputs that encode that selection. The result will be visible
in the project artifacts, not merely in controller metadata. A real Rithet Creek
project will prove this on Forest test production before the operator deploys to
WEPPcloud. After that separate operator deployment, all eight affected Abdisa
runs will be manually rebuilt and rerun on wepp1 with a retained audit trail.

The release gate is intentionally stronger than “the job completed.” Acceptance
requires agreement among persisted intent, generated landuse files, prepared WEPP
files, and completed result summaries.

## Progress

- [x] (2026-09-17 22:39 UTC) Reproduce the incident from reporter and production
  artifacts, isolate three source boundaries, and scaffold this work package.
- [x] (2026-09-17 22:55 UTC) Promote repository-wide generated-artifact evidence
  and completion-claim guidance into canonical agent-discoverable documentation.
- [x] (2026-09-18 UTC) Remove the rejected transaction/storage/recovery design
  and replace it with a compact contract limited to the three propagation bugs,
  existing failure behavior, focused tests, and Forest acceptance.
- [x] Ratify the bounded contract through ancestors `ecda89e45` and `f1a4a75b4`;
  both independent reviews PASS, takeover execution authorized.
- [x] Add failing regressions for classified SBS input, global mapping file
  regeneration, explicit 0.30/0.50 canopy propagation, and writer failure.
- [x] Implement the propagation corrections, including the missing public canopy
  writer call and preservation of MOFE canopy overrides during summary rebuild.
- [x] Pass focused (91), related (4,192), full-suite (8,994), correctness, QA,
  and documentation gates; full suite also passed 12 subtests, with 99 skipped.
- [ ] Deploy the exact accepted candidate to `forest1.local` and exercise an
  actual Rithet Creek clone or supported restored archive through all scenarios.
- [ ] Record Forest artifacts and present the hard-gate evidence to the operator.
- [ ] Stop until Roger explicitly confirms his WEPPcloud deployment is complete.
- [ ] Preflight wepp1, preserve pre-repair evidence, manually rebuild/rerun all
  eight Abdisa runs, and validate the refreshed hillslope response summary.
- [ ] Close reviews, update package/tracker/root board, and archive this plan under
  `prompts/completed/`.

## Surprises & Discoveries

- Takeover review found that `modify_coverage` never invoked the MOFE writer,
  and `build_managements` discarded persisted canopy overrides. Fixing synthesis
  alone would not repair the public thinning workflow. The reviewed clarification
  in `f1a4a75b4` covers those two existing links without new runtime machinery.
- Forest's `.local` name does not resolve here. Its documented address
  `192.168.1.108` works with `HostKeyAlias=forest1.local`, preserving saved-key
  verification. The host is on `feature/project-owned-config`, whose revision is
  an ancestor of the candidate: use a fast-forward and canonical `--skip-pull`,
  preserving the branch name. `wctl rq-info --detailed` is unsupported there; plain
  `wctl rq-info` confirmed zero executing jobs.

- Observation: `SoilBurnSeverityMap.data` reclassifies the source raster to codes
  130 through 133 before inherited zonal dominance runs. The full landuse builder
  then tries to map those codes again through `class_pixel_map`, which is keyed by
  raw source pixels such as 0, 1, 2, and 3. Missing keys default to 130, so burned
  segments become unburned during management-file generation.
  Evidence: `wepppy/nodb/mods/baer/sbs_map.py` defines the classified `data`
  property; `wepppy/nodb/core/landuse.py` currently calls
  `class_pixel_map.get(val, '130')` after `build_lcgrid()`.

- Observation: the existing SBS regression encodes the opposite contract. Its
  test double returns raw values `11` and `12`, then maps them to 131 and 132.
  That double lets the broken production code pass.
  Evidence: `tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py`, test
  `test_build_multiple_ofe_sbs_remap_reuses_existing_management_summaries`.

- Observation: `modify_landuse_mapping_rq` updates both `domlc_d` and
  `domlc_mofe_d`, then calls only `build_managements()`. That refreshes summaries
  but does not synthesize `landuse/hill_*.mofe.man` from the new segment map.
  Evidence: `wepppy/rq/project_rq.py` in `modify_landuse_mapping_rq`; the selected-
  hillslope `Landuse.modify()` path already demonstrates regeneration with
  `_build_multiple_ofe(domlc_mofe_override=...)`.

- Observation: `_build_multiple_ofe` initializes `cancov_override` to `None` and
  only sets it from RAP. It does not use `summary.cancov_override`, so 0.30 and
  0.50 thinning selections that share management class 424 both use the source
  management's 0.40 canopy value.
  Evidence: `wepppy/nodb/core/landuse.py` segment-plan construction and production
  file readback from `acetic-surprise` and `uncrowned-bolt`.

- Observation: the September 7 clone was a false positive even though it was an
  actual project and the job completed. `aliquot-shoji/landuse.nodb` holds the
  expected C3S severity classes, but all 167 generated MOFE management files are
  byte-identical to baseline `honorable-pin` and retain baseline cover.
  Evidence: incident artifact and the prior package's validation statement that
  it did not perform a complete live landuse or WEPP replay.

- Observation: attempting to guarantee cross-file publication, recovery, event
  delivery, and retained attempt evidence expanded a three-edit propagation fix
  into a new runtime subsystem and increased fragility.
  Evidence: Roger rejected that design on 2026-09-18 and directed the work back
  to the simplest correction.

## Decision Log

- Decision: include the public canopy mutation's existing-writer call and retain
  explicit canopy overrides when rebuilding MOFE summaries. Preserve single-OFE
  behavior and RAP precedence. Two independent reviewers accepted the delta.
  Rationale: direct caller inspection proved the three original edits alone
  would leave the user workflow broken. Date/Author: 2026-09-18 UTC, Codex.

- Decision: treat this as a new recurrence package rather than reopening the
  closed September 7 package.
  Rationale: the hardening standard says the first recurrence invalidates the
  prior completeness claim and requires a new incident record.
  Date/Author: 2026-09-17 22:39 UTC, Codex.

- Decision: create a canonical contract covering generated MOFE management
  artifacts instead of broadening the narrow selected-hillslope contract by
  implication.
  Rationale: current contracts explicitly separate selected-hillslope editing
  from global class-to-class mapping, while no current contract states the SBS
  builder and cover-override obligations together.
  Date/Author: 2026-09-17 22:39 UTC, Codex.

- Decision: preserve scientific parameterization. Initialize MOFE canopy
  synthesis from `summary.cancov_override`; when RAP is active, preserve current
  behavior by allowing its segment-specific cover to replace that initial value.
  Rationale: this fixes missing propagation for the reported 30%/50% scenarios
  without changing RAP formulas or precedence.
  Date/Author: 2026-09-17 22:39 UTC, Codex.

- Decision: use `forest1.local`, the production-compose test-production host, for
  the acceptance gate. Do not use a fixture-only test or the source-mounted
  development host as the deployment proof.
  Rationale: the user explicitly requires actual Forest validation before
  deploying to WEPPcloud.
  Date/Author: 2026-09-17 22:39 UTC, Codex.

- Decision: stop after Forest acceptance. Roger deploys the accepted revision to
  WEPPcloud; Codex performs the named wepp1 run repair only after explicit
  confirmation of that deployment.
  Rationale: this is the authority boundary the operator specified.
  Date/Author: 2026-09-17 22:39 UTC, Codex.

- Decision: process all eight named production runs, including baseline, after
  deployment.
  Rationale: a single generation revision and complete ledger make the repaired
  comparison reproducible; no run from the supplied set is silently omitted.
  Date/Author: 2026-09-17 22:39 UTC, Codex.

- Decision: promote the consumed-artifact evidence chain and strict completion
  vocabulary into `docs/standards/generated-artifact-validation-standard.md` and
  make it a required root/template review input.
  Rationale: retaining the lesson only in this incident package would make it
  historical context rather than durable agent governance.
  Date/Author: 2026-09-17 22:55 UTC, Codex.

- Decision: use no new runtime mechanism for this remediation. Reuse the current
  MOFE writer, NoDb/RQ flow, status messages, locks, and WEPP preparation path.
  Change only SBS classified-value consumption, post-mapping MOFE regeneration,
  and canopy-override initialization while retaining RAP precedence.
  Rationale: the operator rejected the expanded robustness design as a source of
  fragility. Direct generated-file tests and actual Forest acceptance provide the
  required evidence without adding a second publication/recovery architecture.
  Date/Author: 2026-09-18 UTC, Roger and Codex.

## Outcomes & Retrospective

The bounded source correction is committed as `f4152ac69` and 91 focused tests passed;
broader validation passed; Forest acceptance remains pending. No production data has
been changed. Independent correctness and QA passed with no High/Medium code findings.
The
expanded unapproved design and its proposed ADR/review artifacts were removed;
the replacement contract adds no runtime mechanism. The earlier fix is now
correctly classified as partial: it
corrected a mapping lookup but did not prove that a live build wrote those
assignments into management files. Update this section after each milestone with
exact commits, test counts, Forest run IDs, production job IDs, and unresolved
gaps. Do not describe the incident as fixed until the production repair phase and
refreshed summary are complete.

The broader lesson is now durable outside this package. Root agent guidance and
the work-package/correctness templates require agents to trace intent through
persisted state, generated intermediate, consumed input, fresh output, and the
user-facing result. They also prohibit status language that exceeds those gates.
All 14 changed governance/package Markdown files pass `wctl doc-lint`; root
`AGENTS.md` passes its 160-line size cap, and inbound-reference inspection confirms
the new standard is reachable from the main agent and review entry points.

## Context and Orientation

MOFE means multiple overland-flow elements. A MOFE project divides a hillslope
into ordered segments and writes one combined management file per hillslope at
`landuse/hill_<topaz_id>.mofe.man`. WEPP preparation later copies or materializes
those managements into `wepp/runs/p<wepp_id>.man`. The controlling assignments
are stored in `landuse.nodb` under `domlc_mofe_d`; management summaries, including
optional canopy overrides, are stored under `managements`.

`wepppy/nodb/core/landuse.py` builds landuse. Its
`Landuse._build_multiple_ofe(*, domlc_mofe_override=None)` method obtains segment
classes, optionally applies SBS severity, builds a management plan for each
segment, and writes the combined hillslope files. When an explicit assignment map
is supplied, it must be used as the source of truth and must not be overwritten by
a fresh raster classification.

`wepppy/nodb/mods/baer/sbs_map.py` defines `SoilBurnSeverityMap`. Its `data`
property already returns reclassified 130 (unburned), 131 (low), 132 (moderate),
and 133 (high). The inherited `LandcoverMap.build_lcgrid()` performs zonal
dominance over that `data`, so its result is already in the 130-to-133 namespace.
`class_pixel_map` is different: it maps raw source raster values to those codes
and must not be applied to a `build_lcgrid()` result a second time.

`wepppy/rq/project_rq.py` defines `modify_landuse_mapping_rq`. The browser-facing
mapping operation reaches this worker, which updates every matching dominant
hillslope and MOFE assignment. A successful MOFE mutation must also regenerate
the combined management files before publishing
`LANDUSE_MODIFY_MAPPING_TASK_COMPLETED`.

`ManagementSummary.cancov_override` is an explicitly persisted fractional canopy
selection. It already affects ordinary management loading. The MOFE segment-plan
path must also use it. RAP is a separate data-driven segment cover source; this
package preserves its current behavior when present.

The affected production inventory is:

- baseline: `ventilated-gag`;
- low severity: `equestrian-bonheur`;
- moderate severity: `tactful-aging`;
- high severity: `incorporate-cerebrum`;
- SBS: `choice-feminist`;
- prescribed burn: `neoliberal-dictate`;
- 30% thinning: `acetic-surprise`;
- 50% thinning: `uncrowned-bolt`.

The reporter file `/tmp/hillslope_response_summary.csv` has SHA-256
`042c546ee7ea9c61daf63967d2cc7ffcf4de2881739df31a95c0aa8c37bac063` and contains
one header plus eight scenario rows. It shows exact equality among low, moderate,
and prescribed-burn metrics, and exact equality between the two thinning rows.

The current production evidence is read-only. Low, moderate, prescribed, and
baseline management files use the same effective management content despite
different intended NoDb assignments. The SBS run contains mixed persisted burn
classes but management files were built as unburned; soil differences account for
its small result change. The 30% and 50% runs persist 0.30 and 0.50 overrides but
both generated management files use 0.40 canopy from the shared thinning source.

## Plan of Work

Milestone 1 establishes normative intent before source edits. Add the compact
`docs/schemas/mofe-management-artifact-contract.md` and cross-link it from the
existing disturbed MOFE and selected-hillslope contracts where their boundaries
meet. The new contract must state that classified SBS zonal results are consumed
once; every successful MOFE assignment mutation regenerates management files from
the final segment map; explicit summary cover overrides propagate to MOFE files;
RAP's current segment-specific precedence remains unchanged; and success is not
published when the existing writer path raises. It must not add persistence,
staging, recovery, event, retention, or downstream transaction machinery. Complete
`artifacts/20260917_contract_decision.md`, obtain two independent read-only
reviews, disposition every finding, obtain the operator's approval of the exact
contract, and commit that checkpoint as a standalone ancestor. Record its full
revision in this plan and the tracker. Do not edit implementation first.

Milestone 2 writes the incident regressions before the correction where
practical. In `tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py`, replace or
supplement the misleading raw-pixel stub with a real or production-faithful
`SoilBurnSeverityMap` path whose `build_lcgrid()` result is 130 through 133. Assert
that low, moderate, and high segments select the effective mapping classes and
that nodata/unburned stays 130. Add coverage showing an explicit management
summary canopy override reaches both the combined MOFE file and the prepared
`wepp/runs` file; use 0.30 and 0.50 as separate cases. Retain the RAP regression
and assert its existing value still wins when RAP is active.

In `tests/rq/test_project_rq_mutation_guards.py`, extend the global mapping tests
so they use a real temporary run boundary far enough to inspect regenerated file
content. Assert completion is published only after regeneration succeeds. Inject
a real writer failure at the management-file boundary, verify no completion event
is published, preserve diagnostics, and assert retry can converge. Reuse relevant
validation helpers from `tests/nodb/test_landuse_modify.py` rather than inventing
another assignment schema.

Milestone 3 makes the smallest implementation changes. In
`Landuse._build_multiple_ofe`, treat values returned by the SBS `build_lcgrid()`
call as classified burn codes directly. Keep normalization to string, allowed
codes 130 through 133, the existing effective mapping lookup, burn-shrub/grass
eligibility behavior, and nodata handling. Do not apply `class_pixel_map` again.

In the same segment-plan loop, initialize the local `cancov_override` from
`summary.cancov_override`. Leave it `None` when no explicit override exists. If
RAP is active, keep the current calculation and assignment so RAP remains the
segment-specific value. Pass the resulting value through the existing writer; do
not change the source management files or stored selection.

In `modify_landuse_mapping_rq`, after validation and final assignment mutation,
regenerate MOFE files from a deep copy of the final `domlc_mofe_d` through the
existing explicit-assignment builder path. Preserve single-OFE behavior, locking,
cache invalidation, stale-job gates, request/response shape, and completion event.
Define and test rollback/failure behavior before choosing call order: a failed
writer must not report success or silently bless mixed-generation files. Do not
add a new queue edge. Update `wepppy/rq/job-dependencies-catalog.md` only if an
enqueue site or dependency edge actually changes; none is expected.

Milestone 4 completes local evidence. Run focused tests first, then related NoDb,
Disturbed, RQ, and WEPP-preparation tests. Run the full repository suite, test-stub
check if test doubles change, broad-exception enforcement, code-quality
observability, and documentation lint. Generate temporary actual files and parse
their content; assertions on method calls alone are insufficient. Complete the
correctness and QA artifacts with independent reviews and resolve all high/medium
findings.

Milestone 5 is the Forest hard gate. Confirm the candidate commit is pushed and
available to `forest1.local`. On Forest, verify identity, current revision, queue
state, and service health. Deploy only through
`/workdir/wepppy/scripts/deploy-production.sh`; do not invent a parallel compose
workflow. Record the pre/post revision, deployment transcript, image/container
identity, and rollback revision in `artifacts/20260917_forest_acceptance.md`.

Use the supported project clone or archive/restore workflow to place the actual
Rithet Creek project on Forest under disposable run IDs. Do not use ad hoc file
copying that bypasses normal project initialization. Preserve the source read-
only and record archive SHA-256/provenance. Exercise baseline, low, moderate,
high, SBS, prescribed burn, 30% thinning, and 50% thinning through the same public
workflow users invoke. Capture every RQ job ID and terminal state.

For each Forest scenario, record a sorted content manifest for
`landuse/hill_*.mofe.man`, relevant soils, and `wepp/runs/*.man`; parse the segment
managements to prove effective class and cover; and run WEPP to completion. The
baseline and each scenario must agree with its persisted intent. Low, moderate,
high, SBS, and prescribed inputs must show their selected effective class where
eligible. The thinning inputs must show 0.30 versus 0.50 canopy. Compare results
without assuming every numeric metric must differ; if equal outputs remain, trace
them to verified equivalent model inputs and document that scientific reason.
Exercise one controlled writer failure/retry if it can be done without corrupting
the disposable project, and retain the failed artifacts.

After Forest acceptance, stop. Present the exact revision and evidence to Roger.
Do not deploy to wepp1/wepp2 and do not touch the eight production runs. Record
Roger's later deployment confirmation, timestamp, and deployed revision in the
repair ledger before proceeding.

Milestone 6 performs the wepp1 repair after that confirmation. Apply the
`wepp1-operator` procedure: verify `hostname`, `pwd`, run paths in host and
container views, relevant service health, and RQ state. Before mutation, produce
a per-run snapshot of persisted intent, current landuse/WEPP input manifests,
outputs, timestamps, and status. Keep those records in the normal project/archive
boundary and in the package ledger; do not delete the old evidence.

Process each of the eight runs individually. Rebuild landuse from its persisted
scenario intent through the corrected supported operation, regenerate dependent
soils where that scenario workflow requires it, prepare WEPP inputs, and rerun
WEPP in canonical dependency order. Record each submitted job ID, job tree,
terminal state, artifact manifest, representative parsed values, and output
freshness before advancing. A failure stops that run's sequence and remains
visible; diagnose and retry the same bounded run rather than launching broad
repairs. Do not use direct NoDb or generated-file edits as the repair.

Finally regenerate the hillslope response summary from the repaired outputs,
retain it with a checksum, and compare all eight rows against both intended input
differences and the reporter's original file. Complete correctness and QA review,
update operator/developer docs and the root tracker, then close the package and
move this plan to `prompts/completed/`.

## Concrete Steps

Run local commands from `/home/workdir/wepppy`. Before implementation, capture
the starting state:

    git status --short --branch
    git rev-parse HEAD
    sha256sum /tmp/hillslope_response_summary.csv

After the reviewed contract checkpoint exists, run the focused tests before and
after the correction:

    wctl run-pytest tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py --maxfail=1
    wctl run-pytest tests/nodb/test_landuse_modify.py --maxfail=1
    wctl run-pytest tests/rq/test_project_rq_mutation_guards.py -k modify_landuse_mapping --maxfail=1
    wctl run-pytest tests/nodb/mods/disturbed/test_landuse_remap.py --maxfail=1
    wctl run-pytest tests/nodb/test_landuse_mofe_process_pool.py --maxfail=1

Then run the related and repository gates:

    wctl run-pytest tests/nodb tests/rq tests/microservices/test_rq_engine_landuse_routes.py --maxfail=1
    wctl check-test-stubs
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master

Run `wctl check-rq-graph` if the RQ file changed, even though no dependency edge is
expected. If it reports catalog drift caused by a real enqueue/dependency change,
stop and reconcile scope before using the documented regeneration command.

Lint each changed Markdown file and preview spelling normalization:

    wctl doc-lint --path docs/work-packages/20260917_mofe_scenario_artifact_integrity/package.md
    wctl doc-lint --path docs/work-packages/20260917_mofe_scenario_artifact_integrity/tracker.md
    wctl doc-lint --path docs/work-packages/20260917_mofe_scenario_artifact_integrity/prompts/active/mofe_scenario_artifact_integrity_execplan.md
    wctl doc-lint --path docs/schemas/mofe-management-artifact-contract.md
    diff -u docs/schemas/mofe-management-artifact-contract.md <(uk2us docs/schemas/mofe-management-artifact-contract.md)

On `forest1.local`, first perform only read-only preflight. The installed preset
must identify the production-compose test stack:

    ssh forest1.local
    hostname
    cd /workdir/wepppy
    pwd
    git status --short --branch
    git rev-parse HEAD
    wctl rq-info --detailed
    wctl docker compose ps
    scripts/deploy-production.sh --print-plan

If the host identity, worktree, preset, queue gate, or planned revision is wrong,
stop. When they are correct and the Forest deployment phase is active, deploy
with the canonical command:

    cd /workdir/wepppy
    scripts/deploy-production.sh

Record the deployment transcript and rerun the revision, queue, service, and
health checks. Use public UI/RQ workflows for the project clone/restore and
scenario jobs. Add the exact resulting commands, run IDs, job IDs, and expected
terminal messages to this section as the milestone proceeds; they are dynamic
outputs and must not be invented in advance.

After Roger confirms production deployment, preflight each wepp1 run path. Run ID
prefixes are the first two characters and the host root is `/geodata/wc1/runs`:

    ssh wepp1
    hostname
    cd /workdir/wepppy
    pwd
    git rev-parse HEAD
    wctl rq-info --detailed
    wctl docker compose ps

For every run ID, verify both host and container views before any job is submitted.
For example, baseline uses prefix `ve`:

    ls -la /geodata/wc1/runs/ve/ventilated-gag/
    wctl docker compose exec rq-worker sh -lc 'ls -la /wc1/runs/ve/ventilated-gag/'

Repeat with prefixes `eq`, `ta`, `in`, `ch`, `ne`, `ac`, and `un` for the other
seven runs. Add exact supported job-submission commands only after reading the
deployed route/operation contract; capture returned job IDs and inspect their
public job trees or canonical RQ records. Never derive success from file mtime
alone.

## Validation and Acceptance

The local regression is accepted only if it fails against the pre-fix code for
the incident reason and passes after the correction. A test that merely observes
a mocked method call does not count. At least one test must instantiate or
faithfully exercise the real SBS reclassification and zonal-output namespace. At
least one must inspect generated combined management text and its prepared
`wepp/runs` copy. The mapping mutation test must exercise a real file writer and a
failure path.

Local acceptance also requires no new schema keys, payload fields, queue edges,
storage, event formats, or parameter values. Focus compatibility tests on the
changed paths: single-OFE, SBS absent/unburned, explicit MOFE assignments, RAP,
stale jobs, unknown mapping classes, and writer failure without completion.

Forest acceptance requires all of the following:

- Forest runs the exact reviewed candidate revision in the relevant web, RQ, and
  worker containers.
- The test uses an actual Rithet Creek clone or supported restored archive, not a
  synthetic-only fixture.
- All scenario roles complete through landuse generation, WEPP preparation, WEPP
  execution, and summary generation with recorded job IDs.
- Persisted assignment/override state agrees with parsed
  `landuse/hill_*.mofe.man` content and parsed `wepp/runs/*.man` content.
- SBS produces the actual spatial mix of 130 through 133 and eligible effective
  management classes; it does not collapse to baseline management files.
- Global low, moderate, high, and prescribed mapping operations produce their
  intended management classes.
- Thinning produces 0.30 and 0.50 canopy in the applicable generated segments.
- Hash manifests show expected distinctions and document expected shared files;
  no assertion relies solely on filenames, timestamps, NoDb, or job completion.
- Failure evidence remains inspectable and normal archive/restore retains the
  relevant project records byte-for-byte.

Production repair acceptance requires all eight ledger rows to contain deployment
revision, preflight, pre/post hashes, parsed input values, job IDs, terminal
states, output freshness, and reviewer disposition. The refreshed hillslope
summary must be traceable to those repaired outputs. Exact equality is a warning
that requires input-level explanation, not an automatic pass or automatic
scientific change.

## Idempotence and Recovery

Local tests use temporary directories and are repeatable. Forest run IDs must be
disposable and recorded; do not overwrite the production source. Repeating a
Forest scenario should converge to the same generated-input manifest for the same
revision and inputs.

Contract and implementation changes are additive corrections without data-schema
migration. If the candidate fails Forest, preserve the failed run and artifacts,
roll Forest back through the canonical deployment path to its recorded prior
revision, and reopen the relevant milestone. Do not advance to production.

On wepp1, preserve a pre-repair snapshot before each run. A failed run remains
failed and inspectable; do not delete partial artifacts or edit success markers.
Retry only after identifying the failed leaf job and confirming the supported
rebuild can be safely repeated. Do not manually patch `landuse.nodb`, combined
management files, or `wepp/runs` files. If a repair produces mixed generations,
mark that run incomplete and rebuild from its persisted scenario through the
corrected workflow.

The operator's WEPPcloud deployment is not an action this plan delegates to
Codex. Absence of explicit deployment confirmation is a hard stop, not permission
to infer rollout from a Git revision or file timestamp.

## Artifacts and Notes

The scaffolded records are:

- `artifacts/20260917_incident_evidence.md` for immutable starting evidence;
- `artifacts/20260917_contract_decision.md` for the pre-implementation checkpoint;
- `artifacts/20260917_correctness_review.md` for independent correctness review;
- `artifacts/20260917_forest_acceptance.md` for deployed actual-project evidence;
- `artifacts/20260917_wepp1_repair_ledger.md` for post-deployment production work.

Add a QA review artifact before implementation closeout. If security triage rises
to high, add the repository security-review template and block release until all
high/medium findings are resolved.

Important known fingerprints at scaffold time are recorded in the incident
artifact. Update artifacts with full hashes rather than abbreviations whenever a
new snapshot is taken. Do not edit the historical closed package to make its
claims match this recurrence.

## Interfaces and Dependencies

Preserve these callable boundaries unless the reviewed contract explicitly
requires otherwise:

- `Landuse._build_multiple_ofe(*, domlc_mofe_override: Optional[Mapping[str,
  Mapping[str, Any]]] = None) -> None`;
- `modify_landuse_mapping_rq(runid: str, edits_or_dom, newdom=None) -> None`,
  including its supported legacy three-argument form;
- `SoilBurnSeverityMap.build_lcgrid(...)` returning classified zonal values;
- `ManagementSummary.cancov_override: Optional[float]`;
- existing RQ completion/error envelope and
  `LANDUSE_MODIFY_MAPPING_TASK_COMPLETED` event;
- existing NoDb keys, landuse parquet columns, run paths, authorization, locking,
  cache invalidation, and archive behavior.

Use existing libraries and project services only. No new dependency, queue,
worker type, database, cache, or storage location is permitted. Relevant current
contracts include `docs/schemas/disturbed-mofe-mapping-contract.md`,
`docs/schemas/landuse-modification-contract.md`,
`docs/schemas/nodb-persistence-concurrency-contract.md`,
`docs/schemas/rq-response-contract.md`, and the new canonical MOFE artifact
contract ratified by Milestone 1.

`docs/standards/generated-artifact-validation-standard.md` governs the evidence
chain and the maximum completion claim at every milestone.

Revision note (2026-09-17 22:39 UTC): initial plan created from the confirmed
recurrence. It makes actual Forest generated-output evidence and operator-owned
production deployment non-negotiable gates before the eight-run repair.

Revision note (2026-09-17 22:47 UTC): recorded successful Markdown validation
for the complete scaffold; implementation and every runtime gate remain pending.

Revision note (2026-09-17 22:55 UTC): promoted the incident's general lesson into
canonical generated-artifact validation guidance and wired it into agent entry
points and review templates. Runtime status remains diagnosed only.

Revision note (2026-09-17 22:57 UTC): recorded clean Markdown, root size, spelling
preview, and inbound-reference validation for the new guidance.

Revision note (2026-09-18 UTC): Roger rejected the expanded robustness design as
fragile. Removed the proposed attempt store, publication/recovery protocol,
retention and event machinery, workflow fencing, ADR-0069, and their review
artifacts. Restored the bounded plan and drafted a compact no-new-mechanism
contract for the three confirmed propagation defects.
The simplified contract SHA-256 is
`aab2b182422f900a5a4d8ce96d09b475bc77bdee3ac904e580e2fecb5361e896`;
both required independent reviews returned PASS with zero unresolved High or
Medium findings. Exact operator approval and the standalone commit are pending.
