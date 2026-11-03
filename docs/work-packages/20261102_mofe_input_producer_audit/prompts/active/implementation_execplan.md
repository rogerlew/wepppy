# Repair MOFE input completeness and identity


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Keep
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective
current. The 2026-11-02 execution request starts M1; the former audit-only session
restriction is superseded. The user ratified MIPA-01 with “approved. proceed”; contract ancestor
`4579b11ce` precedes all production implementation. Bounded MIPA-02 acceptance is recorded below; specialized 9005/RAP acceptance remains HOLD.

## Purpose / Big Picture


A multiple-overland-flow-element (MOFE) hillslope has successive modeled elements
with potentially different soil, management and crops. Users must receive those
inputs on the intended elements. Penman–Monteith evapotranspiration coefficients
in `pmetpara.txt` are keyed by crop name, not OFE number. The current general
Python writer discovers only the first plant in each management file. Native
WEPP applies PMET on downstream OFEs but substitutes the first table row for a
missing crop. Repair acceptance must demonstrate the coefficients actually
selected by each element and rotation, not only successful model completion.

## Progress


- [x] (2026-11-02 19:32 UTC) Establish audit/scaffold authority and dispatch four agents.
- [x] (2026-11-02 19:32 UTC) Create package, tracker and initial findings register.
- [x] (2026-11-02 UTC) Reconcile all four audit lanes and bound additional repair milestones.
- [x] (2026-11-02 19:38 UTC) Validate documentation, register package on the project board and reconcile independent scaffold review.
- [x] (2026-11-02 UTC) Incorporate S01 as NATIVE-03 with bound runtime evidence and separate native acceptance; no repair or rerun.
- [x] Native authority: user authorized MIPA-02 contract-first repair and revision of undeployed 261029.
- [x] MIPA-02: reviewed ancestors, native correction, selected-source discrepancy validation and local revision 6 matched release/report delivery.
- [x] Complete configured copied-project rerun and r5 comparison after identifying omitted UI/baseflow companions in partial preparation.
- [x] Broad WEPPpy sanity: 9899 passes before test-isolation failure, repaired ordered sequence 43 passes, terminal continuation 3623 passes/7 skips; local source-control handoff.
- [ ] Separate remaining9005/revegetation/RAP native support decision and compatible-consumer validation.
- [x] (2026-11-02 22:49 UTC) M1 renewed management and installed-Rust reproductions through the running Compose application container; existing focused suites pass 21 tests despite reproduced failures.
- [x] (2026-11-02 UTC) Draft MIPA-01 canonical identity contract and compatibility/regression checkpoint.
- [x] (2026-11-02 UTC) Two independent contract reviews pass after bounded-calendar, token-safe-alias and idempotence clarifications; documentation and baseline integrity checks pass.
- [x] M1: operator approved; standalone contract ancestor `4579b11ce` committed before implementation.
- [x] Implementation committed locally as `390bc4f59`; paired Rust `5e3540f` pushed and verified upstream.
- [x] M2: implement all-crop PMET coverage, native-safe aliases, per-OFE Disturbed context and retry/archive identity.
- [x] M3: implement calendar/residue, per-OFE soil/cover and paired Rust slope/map repairs; source and actual-writer tests pass.
- [x] M4 producer portion: supported actual-project fork, 72 hills/235 elements prepared and reparsed; original source unchanged; PMET retry byte-identical.
- [x] M4 bounded native acceptance: selected 261029 capacity/mapping, FC/HK repair and fresh copied-project outputs/reports.
- [ ] M4 complete compatibility:9005/revegetation/RAP native consumer remains HOLD.
- [x] Final independent correctness, QA and security review: no unresolved source findings; final focused suite 306 passed.
- [x] Extended regression and benchmark refresh complete: terminal continuation 2529 passed; prior failures fixed and retested. Segmented validation, not one uninterrupted full-suite pass.

## Surprises & Discoveries

The broad regression stopped after 9,899 passes at an order-dependent test fixture:
`test_managements_module.py` replaced/deleted the canonical management module,
splitting class identities. The PMET suite passes alone; the two-module order
reproduces failure and passes all 43 tests after normal-import fixture repair.
The continuation reran the affected fixture and all later test paths successfully
(3623 passed, 7 skipped).

The initial actual-project native run used partial preparation and omitted enabled
baseflow/UI companion files. Preserve its exact results as limited evidence;
complete configured-workflow acceptance requires canonical `prep_hillslopes` and
fresh execution/readback. The complete rerun passes: 363 model inputs, 72 successful installed-name runs,
confirmed UI/baseflow consumption, 504 outputs and installed report readback.
Full configured r5/r6 outputs are exact; 433 outputs differ between partial and
full configurations, so the two comparisons must remain distinct.

Implementation review found PMET publication must replace hardlinked generated
destinations rather than truncate them, and reject symlinks. Visible temporary
attempts preserve failed writes and survive the canonical archive/restore path.
Secondary synthesis also exposed stale provenance: scenario-carried identity now
survives MOFE/rotation rename/copy/dedup and mixed prepared/unprepared inputs.
Safe duplicate native plant labels remain supported without rewriting when their
coefficient context is identical; ambiguous graphs requiring rewriting fail.

The first actual-project candidate (calm-amalgamation) lacks its MOFE soil files;
retain that failed selection and use the complete awake-versatility fork instead.
An evidence-script attribute typo failed after preparation; its log is retained,
and the corrected readback succeeded. No source project was regenerated.



Renewed actual-writer evidence under Python 3.12.16 reproduces the original
failures although all 21 focused existing tests pass. Retained baseline:
`artifacts/m1_management_baseline_v1/observations.json`. Source inspection also
shows `build_multiple_year_man` expands every stored rotation to N years,
rather than emitting N years total. The management serializer emits a year-count
record for every rotation while the parser consumes that count once before all
rotations. These are additional MAN-03 mechanisms requiring independent regression
coverage; later MIPA-02 full-history evidence supplies bounded native acceptance.


The reported first-OFE symptom is not a first-OFE-only native PMET implementation.
Native `evappm` uses `itype(nowcrp,iplane)`. Incomplete producer crop discovery
instead invokes the reader's first-row fallback. Native names are eight characters,
so full Python-string uniqueness is not sufficient evidence of consumer uniqueness.

S01 additionally proves a native ownership failure downstream of correct soil
production. FC (field-capacity water depth above the dry reference) and HK (the
unsaturated conductivity exponent) are stored by layer alone. Sequential OFE
initialization overwrites them, while water states retain OFE indexing. Actual
PURK/PERC consumers used another OFE's values under both retention policies;
10/15 observed slots were wrong-owned per policy. Identical initialized values
can conceal the error, so repeated-material parity alone is insufficient.

## Decision Log

2026-11-03 UTC: retain partial-preparation inputs/outputs before complete copied-project
preparation. Use the installed revision 6 name and all saved configuration flags,
then compare retained revision 5 with those identical inputs. No original project
mutation or model/configuration change is authorized by this validation.

2026-11-02 implementation: accepted MIPA-01 and ancestor `4579b11ce` authorize
bounded producer repairs and copied-project validation. Keep no-N landuse
synthesis at the full reusable common period because it has no simulation horizon;
explicit `build/render/write(sim_years=N)` can handle coprime long source cycles
without constructing that period. No parameter values or fallback policy changed.
Do not impose one audited binary's scenario capacity on all supported engines;
selected native capacity remains an explicit acceptance prerequisite.



2026-11-02 execution: honor the user's request to execute this package by starting
M1 in the running `weppcloud` container. Preserve existing dirty work and historical
evidence, writing fresh baseline directories. The proposed MIPA-01 contract makes
calendar, collision and buffer choices concrete before asking for the missing
ratification/commit authority required by the contract-first standard. No production
edits precede that gate; separate native authority remains necessary.


On 2026-11-02 19:32 UTC the user requested parallel audits and a work-package
scaffold. Codex confined current work to read-only inspection and docs. Production
repairs, new defaults and native changes are not implied by that request.

The original separation protected the running rock/water program's tests. Its
authorized local closeout is now complete, while native correctness and package
closure remain HOLD. Preserve its sources, binaries, inputs and retained evidence.

On 2026-11-02 the user requested incorporation of S01 as NATIVE-03. Reuse its
runtime finding as a native consumer dependency because even faithful producer
output can reach wrong-owner coefficients. Keep producer acceptance and native
acceptance separate; a producer-only fix or a change of retention policy cannot
close COR-S01-01. This update authorizes documentation/planning only, not native
repair, a new restriction, default changes or existing-project regeneration.

## Outcomes & Retrospective


M2/M3 producer repairs are implemented. See
`artifacts/20261102_producer_execution.md` for source coverage, exact checks,
copied-project evidence and limitations. A supported fork of awake-versatility
prepared 72 hills/235 elements with matching slope/soil/management counts; direct
serialized year-to-crop joins match every intended lookup and repeat preparation
is stable. Actual-project coefficients are uniform, so discriminating mixed-pair
proof comes from the real Disturbed writer regression, not that project alone.

MIPA-02 resolves NATIVE-01/02/03 with selected-source conformance, the FC/HK
ownership repair and discriminating native histories. The package remains open
for specialized 9005/RAP native acceptance; correct producer files alone cannot
resolve that missing consumer support. The installed Rust release was not replaced. Broad
pytest reached a report-source freshness pin affected by this writer change;
a fresh 96-case rerun now matches all 768 retained outputs, and its report/provenance
refresh passes 16 contract/Usersum tests. No historical output was relabeled.

## Context and Orientation


Work in `/home/workdir/wepppy`; the Rust repository is `/workdir/wepppyo3` and
native consumer reference is `/workdir/wepp-forest`. Read the nearest `AGENTS.md`
before editing any module. `wepppy/wepp/management/managements.py` parses and
stacks managements; `get_plant_loop_names()` feeds the generic
`wepppy/wepp/management/pmetpara.py` writer. The Disturbed writer lives in
`wepppy/nodb/mods/disturbed/disturbed.py`. NoDb `wepp.py` and its preparation
services stage files for execution. Rust `wepp_interchange/src/mofe.rs` writes
segmented slope files through the bindings in `wepp_interchange/src/lib.rs`.
`wepppy/wepp/soils/utils/wepp_soil_util.py` transforms and serializes stacked
soils; `wepppy/nodb/mods/rap/rap_ts.py` writes ordered cover blocks. These are
additional confirmed repair targets in the audit register.

Native `infile.for` loads crop coefficients through `pmetcoef.for`; the latter
compares eight-character names and uses its first row on a miss. `evappm.for`
indexes the coefficient arrays with the current OFE's crop type. Table row numbers
are not an OFE-to-coefficient mapping. Preserve this interface unless a separate
native change is explicitly authorized.

## Plan of Work


M1 establishes reproducible failing cases and normative intent. Reconcile each
agent report into `artifacts/audit_findings.md` with severity, source evidence,
reachable trigger, affected consumers and a direct acceptance test. Separate
unproven risks. Before implementation, create or amend the canonical MOFE input
contract under `docs/schemas/`, recording crop identity, intentional global
sidecars, element order/counts, valid legacy states and malformed-input behavior.
Extend `docs/schemas/mofe-management-artifact-contract.md` for management/PMET
identity and temporal schedules, retaining the existing Disturbed mapping contract.
Add only uncovered input invariants to an appropriate canonical schema. Follow
contract-first sequencing for NoDb/UI-coupled paths. Record a compatibility
plan before any run-data/schema mutation; do not rename user-visible keys.

Before M2's native acceptance, resolve NATIVE-01 and NATIVE-02 for the selected
binary: inspected source accepts 20 plant scenarios while PMET arrays hold six,
and existing adapter coefficient arguments use a different index from EVAPPM.
Missing PMET rows do not avoid the capacity defect because fallback also writes
the indexed arrays. Obtain separate authority for native correction or a new
compatibility restriction; do not silently cap crops or alter global capacities.
Use direct EVAPPM observation until adapter equivalence is established. This
dependency does not prevent preparing isolated producer repairs, but prevents an
end-to-end claim for unsupported scenario counts.

NATIVE-03 is a separate prerequisite for M4's unrestricted heterogeneous native
acceptance. Reuse the [S01 final report](../../../20261101_rock_water_development/artifacts/S01-final-disposition.md)
and its evidence summary; its four ownership histories used H11 geometry and
H11/H28/H40 materials, default/optional policies and exact plain/observer output
parity. Runtime provenance is release source `d2e14d96af5942409c9a315dc8594fcc164a702a`
in `/workdir/wepp-forest-release-20261009`, not this audit's native reference
`04f1c4d26bcef217009c124151f877dcbf3985cb`. Bind any future selected binary anew.

Obtain separate native repair authority before changing FC/HK ownership. Assess
all confirmed shared consumers, including drainage/lateral paths, and unequal
layer support. After authorization, retain the failing S01 baseline and compare
each OFE/layer's initialized coefficients with actual dynamic operands, using
distinct materials, a repeated-material control and both policies. Require actual
sub-0.95 HK power execution and exact ordinary plain/observer parity. Quantify
before/after runoff, drainage, storage and ET on copied projects. S01 did not run
a repaired model; its coefficient discrepancies are not measured hydrograph errors.
Scheduled tillage/later density, Rosetta2/missing-density and guard activation
remain explicit limits, not implied coverage. The existing
[whole-soil contract](../../../../schemas/whole-soil-water-capacity-contract.md#known-native-coefficient-ownership-defect)
retains the durable HOLD; do not invent a safe-use class or duplicate governance.

M2 begins with the smallest PMET repair: discover every required crop in the
actual staged managements, not just `plants[0]`, and preserve deterministic table
construction. Repair generic and Disturbed consumers proven affected by the same
assumption. Resolve identical native names with conflicting coefficients explicitly
under the canonical contract; do not silently take the first value or invent a
new per-OFE format. Preserve supported missing-file/native behavior. Changing
fallback or parameter selection requires an ADR before merge. Exercise real
management serialization and the actual PMET writer for multiple crops, rotations,
same-crop reuse and a single-OFE control.

M3 has three independently verifiable producer repair slices. In management
`wepppy/wepp/management/utils/multi_ofe.py`, repair MAN-01's missing residue plant
reference remap in the ordinary merge branch using the existing deduplicating
branch pattern. Address MAN-02 in both branches only after specifying schedule
alignment over requested simulation years; preserve each source calendar or
explicitly reject an unsupported combination before writing. Serialize and reparse
distinct operation-10/12 residue definitions and 1/2-year and 2/3-year schedules.
Include MAN-03, the mixed-calendar expansion round-trip failure noted in the management
report; root-cause it rather than assuming a remap alone fixes serialization.

In `wepp_soil_util.py`, repair SOIL-01's developed exemption per OFE while preserving
the explicit preservation mode and top-level restrictive-layer alias contract.
Repair SOIL-02's version-9005 texture enum in ordinary and debug serializers using
the current OFE's texture, subject to uploaded-input preservation rules. In
`rap_ts.py`, repair COVER-01 in both ordinary and transformed writers so numerical
OFE identity matches slope/soil/management order. Use reversed soil orders, mixed
developed/forest stacks, different textures and at least 12 distinct cover blocks.
Select and bind an actual 9005-capable engine; inspected general native source is
not sufficient to validate the newer texture/cover format.

In Rust `wepp_interchange/src/mofe.rs`, repair SLOPE-01/02 at the owned writer
boundary: validate enabled-buffer inputs, retain finite normalized endpoints and
positive lengths at serialized precision, and propagate existing error contracts
through `watershed_mixins.py` and the rq-engine boundary as applicable. Define
zero-buffer behavior in the contract before changing it. Never silently merge
segments, because this changes soil/management identities. Preserve valid existing
automatic and explicit segmentation. Test zero/negative/nonfinite buffers, buffer
equal/greater than hillslope, tiny explicit intervals, normal controls and total
length. Audit map equality-boundary handling and source-profile negative cases as
the same failure class. API-01's ignored `min_length` remains a separate contract
decision; do not begin enforcing a new minimum as an incidental fix.

Every slice needs retained before/after artifact evidence and downstream acceptance.
Also construct stale/mismatched deck counts and a multi-OFE source supplied as one
soil-stack member to assess the two unproven boundary risks. Reuse current modules
and bindings; no infrastructure expansion is authorized. Intentionally global
inputs and unproved risks receive explicit dispositions rather than speculative
fixes. Re-triage implementation security before these file/path and route changes.

M4 validates complete propagation on a copied actual heterogeneous MOFE project
under the normal preparation path. Record durable intent, intermediate and staged
file hashes, semantic element identities/counts, native selected crop/coefficients,
fresh outputs and report readback. Bind installed Python/Rust modules and the exact
native binary; repository HEAD alone does not establish execution provenance.
Exercise all OFEs and a crop transition; use distinct coefficients so incorrect
reuse cannot pass. Record producer identity and native FC/HK ownership as separate
acceptance results. Producer slices can pass their bounded gates while NATIVE-03
remains open; that does not establish complete heterogeneous native correctness. Obtain independent correctness review and QA. Re-triage security
before any file/path, queue or subprocess change and obtain the required dedicated
review. No deployment or existing-project regeneration is part of this plan.

## Concrete Steps


For the current scaffold, run from the WEPPpy root:

    wctl doc-lint --path docs/work-packages/20261102_mofe_input_producer_audit

Before future repair, read `tests/AGENTS.md` and the wepppy-tester skill. Existing
focused suites provide starting points, but new cases must exercise real writers:

    wctl run-pytest tests/wepp/management/test_multiple_ofe.py tests/wepp/management/test_rotation_stack.py
    wctl run-pytest tests/nodb/mods/disturbed/test_pmetpara_prep.py tests/nodb/test_wepp_multi_ofe_management_propagation.py

Additional relevant Python suites are
`tests/wepp/soils/utils/test_wepp_soil_util.py`,
`tests/topo/test_watershed_abstraction_slope_file.py` and
`tests/topo/test_watershed_abstraction_mofe_map.py`; locate RAP tests and add actual
writer coverage for the 12-OFE case. Rust coverage includes
`tests/wepp_interchange/test_segment_single_ofe_slope.py` and
`tests/wepp_interchange/test_ag_fields_native_writers.py` in wepppyo3. Read that
repository's AGENTS and documented environment before running its tests.
Use a private target/output directory
when concurrent work is active; never replace the shared installed extension as a
side effect. Run the substantive Python pre-handoff gate only after coordinating
with the active program:

    wctl run-pytest tests --maxfail=1

Expected outcome is no failing targeted regression, explicit dispositions for
unrelated failures, and native readback matching intended values on every selected
OFE. Do not predict test counts before execution. Record exact commands, revisions,
paths and results in the tracker. Broad tests are not required for this docs-only
scaffold and must not be launched by the audit agents.

## Validation and Acceptance


The original audit task ended when four audits were reconciled, the package was
discoverable and docs checks passed. Execution now proceeds through M1's reviewed,
ratified contract ancestor into M2/M3 and applicable M4 gates. Completion requires a failing-before/passing-after case
for each repaired boundary, unchanged legitimate controls, unmocked generated and
consumed input readback, and an actual-project native history. Validate absent,
empty, populated, supported legacy and malformed states separately from OFE and
crop combinations. Do not hide an unresolved medium/high correctness finding
behind success in unrelated tests. Incorporation of S01 does not resolve
COR-S01-01; native ownership must be corrected and independently validated before
claiming end-to-end heterogeneous correctness or closing that dependency.

## Idempotence and Recovery


Keep every reproduction in a new private output root and leave source runs
unchanged. Do not reset concurrent dirty files, switch branches or overwrite
binary artifacts. A failed validation preserves its inputs and logs for diagnosis.
Later repairs should be separately reversible by producer; retain a hash-bound
baseline and make no bulk existing-project mutation. Coordinate shared tracker
edits by adding only this package's entry.

## Artifacts and Notes


Retain the audit register and any small reproducible probes under this package's
`artifacts/` directory. Large generated outputs belong in a separately identified
private evidence root with a manifest. The previous PMET reader probe demonstrates
distinct named-crop lookup and first-row fallback, not a complete MOFE run.

## Interfaces and Dependencies


Keep existing management parsers, `pmetpara_prep(runs_dir, kcb, rawp)`, NoDb
preparation interfaces and Rust bindings unless a confirmed finding requires a
bounded documented change. No external dependency is needed. The planned durable
MOFE contract must be outside this work package before code changes and package
closure; the package remains an execution record, not permanent governance.

Revision 2026-11-02 19:32 UTC: initial audit and future repair scaffold, preserving
the user's scope and isolation from running rock/water tests.

Revision 2026-11-02 UTC: incorporated four completed audits, concrete additional
repair slices, existing canonical contracts, native capacity/observation gates,
9005 consumer limits and isolated reproduction evidence. No implementation started.

Revision 2026-11-02, S01 incorporation: add runtime-confirmed NATIVE-03, preserve
separate checkout/binary provenance and existing HOLD, distinguish producer/native
acceptance, and update rock/water local-closeout status. Evidence reused; native
repair and new execution remain outside current authority.

Revision 2026-11-02, execution M1: renewed container baselines, recorded passing
existing suites versus failed direct reproductions, and prepared proposed durable
contracts and compatibility decisions. Production implementation awaits the
required reviewed and ratified ancestor checkpoint.


## MIPA-02 native execution extension

The 2026-11-02 request supersedes earlier exclusions of native repair only for
the bounded coefficient/release scope in
`artifacts/20261102_native_contract_decision.md`. Execute this active plan.
Deployment and existing-project mutation remain excluded. The release worktree
is `/workdir/wepp-forest-release-20261009`, on the verified remote-default branch;
the older audit worktree has different code. Current release PMET already uses
ntype (hill32/watershed15000) and has direct EVAPPM calls, so verify conformance
before proposing PMET changes.

First obtain two independent read-only reviews of MIPA-02 and the canonical
contracts in both repositories; disposition findings and commit a standalone
contract ancestor in each before source edits. Preserve the revision-5 matched
pair, sidecars and hashes in a fresh evidence directory. Add committed native
reproductions with distinct and repeated materials, unequal layers and PMET role
boundaries, using the existing S01 observations as historical failing evidence.

Then change cwater.inc FC/HK dimensions and every active reference in daily/hourly
water balance, PURK, PERC and DRAIN. Keep arithmetic and initialization timing
unchanged. Update native source specifications. Test compiled actual consumers
and full histories with observation off/on, recording dynamic operands and
runoff/drainage/storage/ET consequences for both policies. Use separate lanes for
any newly confirmed producer discrepancy; amend contracts before changing intent.

Finally commit tested source, build with `TARGET_TAG=261029
 tools/build_wepp_dated_release.sh` (one shell command without a newline), restore
watershed includes, and run native smoke, watchlist, pytest and artifact-policy
gates from that default-branch checkout. Test actual final binaries and the
canonical WEPPpy selection/preparation/readers with committed fixtures; supplement
with the retained copied project. Vendor only after required gates pass. Create
revision-6 authoring files and a reviewed PDF/manifest, preserving revision 5.
Update binary lifecycle and native change-log, obtain final independent correctness,
QA/security and release-disclosure reviews, and commit the bounded result. Required
native push follows native AGENTS. Do not deploy or change executable defaults.

Decision: ownership is corrected without changing physical formulas or refreshing
coefficients on a newly invented schedule. The existing PMET release implementation
is verified rather than replaced based on obsolete audit source. No conformance
claim precedes dynamic evidence and exact final-pair validation.

Outcome at extension start: contracts prepared; no native implementation edits.
Revision 2026-11-02: added operator-authorized MIPA-02 native/release execution.


MIPA-02 initial progress snapshot: both independent checkpoint reviews PASS; standalone
ancestors `a42b9d640`/`0a8727057` precede native `b581352b6`. Four before failures
prove cross-OFE interference in compiled real PURK/PERC; 22 after checks pass.
Research observer builds, final matched release build and full histories started.
Discovery: selected 261029 lacks 9005 extended-header and RAP cover consumers.
The canonical contract explicitly retains SOIL-02/COVER-01 HOLD and separates any
reader addition from this FC/HK correction. No existing source scenario limit
or native PMET arithmetic changed. At that checkpoint, outcomes were pending full-history evidence; the final
outcome below supersedes that status.


MIPA-02 outcome: locally vendored revision 6 and reviewed three-page report are
complete; current tracker binds exact binaries, PDF and evidence. Independent
reviews pass after correcting the historical Roads count (744 passed, 96 failed).
Full histories prove corrected first-consumer ownership and quantify numerical
changes; no all-time ownership/thermal/field-validation claim. The actual copied
project generated 504 outputs with installed interchange/report readback.
Complete canonical preparation supersedes the initial partial-context evidence: all
72 executions consume enabled UI/baseflow companions, and retained r5 matches all
504 r6 outputs on identical 363 model inputs. Native
suite 1,416 and post-vendor gates pass. Broad WEPPpy validation completes in segments: initial 9899 passes/422 skips,
then a fixture-only module-identity repair and 3623 passes/7 skips through every
remaining path. The independent reproducing order passes 43 tests. These counts
overlap; no uninterrupted full-suite green claim.
The optional reader-scope preference received no response during independent work;
retain the stated separate compatible-engine requirement, with 9005/RAP native
acceptance HOLD. Do not silently port new physics or relabel unsupported inputs.
