# Deliver simplified unrutted partial-crossing strips


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`. Maintain
Progress, Surprises & Discoveries, Decision Log, and Outcomes & Retrospective.
The operator authorized proceeding on 2026-11-17 and permits mutation or forking
of the synced forest run. Roger subsequently approved the exact formula and instructed implementation.
Both reviews pass; commit the checkpoint before implementation.

## Purpose / Big Picture


Users should be able to model contour-following unrutted roads that cross only
part of a hillslope, without a 60% whole-hillslope coverage gate or artificial
splitting at longitudinal road elevation reversals. Use separate simplified
hillslope strips and combine their outputs into one replacement hillslope PASS
file for the watershed. An OFE is a modeled profile section; a multi-OFE strip
contains landuse, road, fill and, where supported, downstream landuse. A PASS
file carries a hillslope's water/sediment response to the watershed model.

Preserve total hillslope area, and road area where feasible. This is an intentional
abstraction: no terrain flowpath walking, switchback connectivity reconstruction,
or sequential routing through multiple crossings. Document that area closure
does not establish correct physical allocation of contributing area.

## Progress


- [x] (2026-11-17 17:45 UTC) Scaffold scope, incident record and acceptance matrix.
- [x] (2026-11-17 UTC) M1 draft formulas, canonical amendments and ADR-0146;
  both independent reviews pass after findings resolved.
- [x] (2026-11-17 UTC) Exact formula approved; checkpoint `8e87b2363` committed before code.
- [x] (2026-11-17 UTC) M2 preparation, normalization and strip accounting implemented.
- [x] (2026-11-17 UTC) M3 native execution, replacement PASS, provenance and shared-source presentation wired.
- [x] (2026-11-17 UTC) M4: 191 scoped tests; fresh native forest slices/control; correctness/security reviews pass.

- [x] (2026-11-17 UTC) RUPC-02 top-placement amendment drafted at operator direction.
- [x] RUPC-02 independent contract reviews pass; checkpoint `f46d59422` committed.
- [x] (2026-11-17 UTC) RUPC-02 implemented; 199 scoped tests, fresh native full-upload/shape evidence and both reviews pass.

- [x] (2026-11-17 19:00 UTC) M6 forest test deployment, input completion and requested RQ run; native/report readback passes.

## Surprises & Discoveries


The existing Roads Step-4 path already implements affected strips and unaffected
remainder contributors. Its specification says monotonic geometry is unnecessary,
but shared preparation still splits before branching by design. Reuse this path
rather than introducing a new workflow.

Marta's rerun has nine prepared segments rather than 38. One crossing of hillslope
141 passed coverage but failed for missing fill/buffer inputs. Geometry changes
alone cannot resolve that missing-parameter failure. Details are retained in
`artifacts/20261117_incident_evidence.md` relative to this package.

The retained full upload has eight non-positive upstream profiles: terrain
distance anchors can exceed the representative WEPP profile length. This is an
abstraction mismatch, not proof of physically impossible roads.

## Decision Log


2026-11-17, Roger Lew with Codex: replace the 60% gate and use intentionally
simplified strips; preserve hillslope area and road area where feasible. Exclude
flowpath tracing and switchback connectivity to bound the task. Mathematical
allocation and infeasibility policy still require the contract checkpoint.

2026-11-17, Roger Lew: scope tests to implementation changes. Do not run the full
repository suite. Run targeted affected-path regression and native artifact checks;
add UI, RQ, stub or Rust checks only where implementation changes affect them.

2026-11-17, Roger Lew with Codex: amend this package to allow explicit top
placement when ordinary upstream length is non-positive. Preserve road/fill
dimensions, omit upstream OFE, conserve area downhill and disclose absent
upstream runon. Code conformance remains pending.

## Outcomes & Retrospective


Implemented and locally validated after checkpoint `8e87b2363`. Two valid real
partial-crossing slices (141/42) complete native execution, replacement aggregation,
watershed and reports; emitted geometry closes within 1e-6 m². Source baseline
and upload hashes remain unchanged. The no-road partition control shows runoff
differences of about 5–6 ppm; it is a diagnostic, not proof of physical connectivity.

The full copied upload retains eight non-positive-upstream failures. Synthetic
fixture fill/buffer inputs were used explicitly; neither full-site repair nor site
calibration is claimed. Review caught costly linework grouping and secondary-source
result joins; endpoint traversal/spatial indexing and membership-aware readers fix
these with regressions. Both reviewers pass, 191 scoped tests pass. Deployment,
integration and publication remain separate. See tracker and retained artifacts.

RUPC-02 follow-up is now implemented and locally validated. Original RUPC-01
receipts remain historical; the separate RUPC-02 receipts establish new conformance.

## Context and Orientation


Work starts at `e4eafdd3e2115c527bf30e56b0fbae9f59ec3a57` on branch
`work/roads-unrutted-strip-contract`, worktree
`/tmp/wepppy-roads-unrutted-strip-contract`. Read root and nearest NoDb/test
AGENTS instructions before editing those areas.

`wepppy/nodb/mods/roads/monotonic_segments.py` performs shared elevation splitting.
`wepppy/nodb/mods/roads/roads.py` owns `prepare_segments`,
`_select_outslope_unrutted_hillslope_segments`, geometry/profile writers, and
`run_roads_wepp`. The latter assembles strips, remainder, and replacement outputs.
`wepppy/nodb/mods/roads/specification.md` describes the existing 60%, minimum-length,
parity-transform, area-closure and three-crossing rules and PASS combiner semantics.
`wepppyo3` is the owned native combiner dependency; do not substitute a Python
combiner or alter shared hydrology formulas without specific evidence and scope.

Read the complete contract inventory in this package's
`artifacts/20261117_contract_decision.md`, particularly Roads baseline, settings,
preparation lifecycle and output-scope contracts. Existing scientific contracts
remain controlling until explicitly amended in the checkpoint.

## Plan of Work


### M1 — Ratify the bounded geometry contract


Inspect current strip allocation and native PASS interfaces. Write exact formulas
for crossing identity, modeled width/length and placement, with positive OFE
requirements. Define target road area from in-hillslope geometry and width, how
representation duplicates are treated, and what happens if road area cannot fit.
Choose an absolute closure tolerance before validation. Resolve existing 4% parity,
10 m minima and the three-crossing cap explicitly; removal of 60% does not authorize
removing those other rules. Define deterministic abstraction for multiple portions
without adding physical connectivity reconstruction. No mandatory switchback
classifier or terrain partitioner belongs in this milestone.

Amend every affected canonical contract outside this package and mark conformance
pending. Draft an ADR with actual decision provenance, old/new behavior,
alternatives, limitations, rollback and evidence. Define schema additions and
legacy preparation invalidation before code edits. Define actionable missing-input,
no-overlap and infeasible-area behavior without inventing defaults.

Record operator ratification of the exact delta, obtain two independent read-only
contract reviews, resolve findings, and commit the checkpoint, canonical amendments,
ADR and review disposition as a standalone ancestor. If commit authority is not
available, leave the reviewed checkpoint prepared and request that authority at
that point. No implementation may begin before this gate. Record its SHA in tracker.

### M2 — Implement minimal preparation and allocation changes


Write focused failing tests, then separate unrutted crossing preparation from
longitudinal monotonic splitting. Preserve source attributes and deterministic
source-to-hillslope identity. Group multipart geometry by original hillslope ID.
Keep point-source design preparation unchanged. Reuse the existing strip path to
replace whole-hillslope ratio exclusion with the approved area-allocation rule.

Implement original-area = affected-area + remainder-area by construction, with
positive valid native profiles. Retain road target, modeled area, residual and
reason under the ratified additive schema. Ensure equivalent feature subdivision
does not silently alter accounting. Do not add flowpath walking to resolve
ambiguous repeated crossings; apply the approved simplified policy and disclosure.

### M3 — Execute and expose the actual replacement


Reuse native soil, management and slope writers plus separate contributor runs.
Use the existing replacement combiner for strips and remainder, preserving event
alignment and PASS quantity semantics. Replace the original hillslope contribution
once; do not add its baseline response again. Do not change watershed topology.

Wire preparation invalidation, inspection, failure retention, summaries and
archive/restore for changed artifacts. Keep metadata additive and retained old
results identifiable as historical. Update Roads README, ENDUSER, specification
and affected operator guidance with the limitations and missing-parameter recovery.
Validate exact files consumed by the watershed rather than only manifest counts.

### M4 — Prove the changed paths and hand off


Execute the package acceptance matrix using scoped tests and disposable project
copies. Use hillslopes 141 and 42 from `misty-eyed-divorcee` after recording source
hashes and obtaining defensible required fill/buffer values; do not silently guess
values or rerun production. Run a no-road control with actual baseline inputs split into two equal-width
profiles. Report annual/whole-period runoff volume and sediment mass differences
and calendar completeness. Treat response differences as diagnostic, not a
scientific equivalence gate; enforce geometry closure and correct aggregation.
Conservation alone does not guarantee identical nonlinear model response.

Retain direct native input, PASS combination, watershed-consumption and fresh
report evidence under the package artifacts. Obtain independent correctness and
security reviews using repository templates, close medium/high findings, and
update tracker and plan. Report implementation, local/environment validation,
integration and deployment separately. Production rollout is a separate action.

## Concrete Steps


From the task worktree, discover exact existing tests before selecting node IDs:

    rg -n 'unrutted|replacement|strip|monotonic' tests/nodb/mods/test_roads_controller.py tests/nodb/mods/test_roads_monotonic_segments.py
    rg -n 'combine|phase4|replacement' wepppy/nodb/mods/roads/roads.py wepppy/nodb/mods/roads/specification.md

After M1, use `wctl run-pytest` with selected changed-path node IDs. Candidate
modules are `tests/nodb/mods/test_roads_controller.py`,
`tests/nodb/mods/test_roads_monotonic_segments.py`, and affected tests in
`tests/wepp/interchange/test_roads_accounting.py` and `test_roads_lifecycle.py`.
Record the exact commands after the implementation diff determines scope. Ensure
the test container consumes this checkout; do not remount another task's stack.
For docs run:

    wctl doc-lint --path docs/work-packages/20261117_roads_unrutted_partial_crossings

Expected result is no doc errors; implementation tests must fail on the old path
for the new behavior and pass after the change. No full-suite command is authorized.

## Validation and Acceptance


Use `artifacts/acceptance_matrix.md` in this package. Separate geometry inputs
from absent, empty, populated, legacy, working, failed, completed, restored and
malformed runtime states. Check changed writer/combiner boundaries unmocked.

Acceptance requires a valid partial-crossing road below 60% to execute, reversal
splitting to stop only for unrutted roads, total area to close, feasible road area
to be preserved, infeasibility to remain visible, and native strip PASS outputs
to reach the original hillslope's watershed input without double counting.
Inspect normal project reports and browse/archive artifacts; saved state, file
existence and RQ success alone do not prove correctness.

## Idempotence and Recovery


Work in the task branch and preserve unrelated master WIP. Run experiments on
identified disposable copies; retain original upload and prior generated evidence
before reprepare. Use existing lifecycle retention and explicit stale-input handling.
After partial failure, leave the prior result historical and the new attempt visibly
failed; do not publish partially combined inputs as current. Revert through normal
commit-preserving integration if needed; never reset shared master or rewrite live
project data as a rollback shortcut.

## Artifacts and Notes


The package includes a contract-decision draft, incident evidence and acceptance
matrix. Later retain contract reviews, ADR reference, ancestor SHA, exact scoped
commands/results, native evidence manifest, and independent correctness/security
reviews. Existing incident evidence is a summarized observation, not a fixture or
proof of candidate behavior.

## Interfaces and Dependencies


Preserve public Roads and RQ signatures, original hillslope IDs and baseline/output
scope. Use additive accounting fields settled at M1; do not rename public keys.
Use existing owned geometry and native execution dependencies. Changes to combiner
internals require demonstrated inability of the existing interface to satisfy the
ratified area/event contract, plus scoped native regression evidence. This plan
permits no new infrastructure or silent scientific fallback.

Revision note: 2026-11-17 scaffold captures the agreed simplified scope and the
operator's implementation-scoped testing direction; exact geometry policy remains
an explicit pre-implementation decision rather than an invented approved formula.

Revision note: 2026-11-17 execution completed locally with scoped evidence and
explicit full-upload limitation; no relaxation of the approved placement failure policy.

## M5 — RUPC-02 contract checkpoint and implementation follow-up


Start from implementation `e6989a622f7aea86126d098f48e2e57c15f35b61` in the same
worktree/branch. Amend the canonical strip contract and ADR-0146, update the Roads
specification and affected lifecycle/settings/accounting cross-references. Record
approval and two independent read-only reviews in `artifacts/20261117_top_placement_contract.md`.
Standalone checkpoint `f46d59422` was committed before code; the operator then
approved implementation, now locally complete.

For later implementation, edit the placement branch in `Roads.run_roads_wepp`
in `wepppy/nodb/mods/roads/roads.py`: ordinary upstream <= 0 selects top placement;
require road + fill <= H, omit upstream, use downhill H-road-fill. Positive short
downhill landuse stays; exact fit emits road/fill. Adjust native role builders and
comparison consumers to use the actual OFE roles. Preserve area with any tiny
remainder transferred downhill for top-placed strips. Never emit zero lengths.
Append original/final placement provenance and execution policy markers from the
canonical contract. Preserve prepared geometry and use existing result admission
to require rerunning old execution outputs, retaining them as historical.

Scope tests to the placement, writers, comparison and lifecycle paths actually
changed. Start with `wctl run-pytest tests/nodb/mods/test_roads_controller.py
tests/nodb/mods/test_roads_unrutted_strips.py`; add specific affected comparison,
accounting/lifecycle tests as the diff requires. Run through a container verified
to mount this worktree. No full repository suite. Exercise exact fit, short downhill,
road/fill overflow, rounding, remainder absorption, unchanged positive upstream,
missing inputs and old prepared/current/archived states. Parse native soil,
management and slope roles, run real two/three-OFE contributors, combine PASS and
read the actual watershed inputs and fresh reports. Retry the retained full upload
on a disposable copy, preserving old evidence and recording all eight crossings'
new dispositions. Keep synthetic validation dimensions explicit; do not promise
all eight succeed before testing. Obtain fresh correctness/security reviews and
update user/operator help before claiming completion. New deployment is outside scope.

Revision note: 2026-11-17 RUPC-02 adds operator-requested top placement as a
contract-only amendment; implementation/native conformance remain pending.

## RUPC-02 execution retrospective


The top-placement branch is wired through native role selection, PASS aggregation,
inspection and current-result admission. Decimal exact-fit arithmetic prevents a
false tiny OFE; failure records preserve known placement and null unavailable
values. Historical archive policy downgrade follows ordinary corruption checks;
prepared-source design, not a mutable manifest label alone, determines provenance
requirements. These were independent-review findings, all closed with regressions.

199 scoped tests pass. Native exact-fit road/fill and road/fill/1 m landuse produce
5,844 daily rows each. Full copied upload with 30 m synthetic fills resolves three
of eight old failures, retaining five real dimension-fit failures. A separately
labeled 5 m-fill experiment completes 24 profiles and watershed/report generation.
Area/PASS/consumer readback and unchanged source inventories are retained. Tests
remain limited to changed paths and affected consumers. No deployment or site
calibration is claimed. This completes M5 implementation and local conformance.

Revision note: 2026-11-17 operator approved implementation after checkpoint;
progress, discoveries, outcomes and evidence now distinguish both native experiments.

## M6 — Forest test deployment and RQ execution


Operator authorized this follow-up and clarified forest's bind-mounted test-server
role. Local master fast-forwarded to the reviewed source while retaining unrelated
WIP; targeted services restarted with idle queues under the existing deployment
fence, then workers resumed. This is forest activation, not production rollout or
remote Git integration. Input mutation was additive: preserve 55 geometries and
prior fields, back up input/NoDb and baseline inventory, materialize existing
width/soil/rock defaults, and use disclosed provisional 5 m fill / 30 m buffer at
10% for this test. No site-calibration claim.

Both preparation and Roads run were submitted by authenticated, run-scoped RQ
HTTP API and reached finished. Preparation produces 7 segments without elevation
splitting; native execution produces 15 road and 9 remainder profiles, watershed
and 5,844 daily report rows. Verify baseline hashes, native profiles, area closure,
PASS receipts, actual watershed consumers and current inspection rather than job
success alone. The retained rollout receipt records exact job IDs, timestamps,
source/runtime identities, backup path and detailed verification hash. All checks
passed. Roads schema metadata returned 404 despite OpenAPI/pipeline availability;
used the declared empty-body endpoints and retained this bounded tooling gap.

Revision note: 2026-11-17 forest deployment and requested RQ execution completed;
this supersedes earlier no-deployment statements only for the forest test server.
