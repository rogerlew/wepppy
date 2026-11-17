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
- [ ] M1 remaining: exact formula ratification and standalone checkpoint commit.
- [ ] M2: Implement design-specific preparation and simplified strip accounting.
- [ ] M3: Wire native inputs, strip execution, replacement PASS and provenance.
- [ ] M4: Complete scoped tests, generated-artifact acceptance and independent reviews.

## Surprises & Discoveries


The existing Roads Step-4 path already implements affected strips and unaffected
remainder contributors. Its specification says monotonic geometry is unnecessary,
but shared preparation still splits before branching by design. Reuse this path
rather than introducing a new workflow.

Marta's rerun has nine prepared segments rather than 38. One crossing of hillslope
141 passed coverage but failed for missing fill/buffer inputs. Geometry changes
alone cannot resolve that missing-parameter failure. Details are retained in
`artifacts/20261117_incident_evidence.md` relative to this package.

## Decision Log


2026-11-17, Roger Lew with Codex: replace the 60% gate and use intentionally
simplified strips; preserve hillslope area and road area where feasible. Exclude
flowpath tracing and switchback connectivity to bound the task. Mathematical
allocation and infeasibility policy still require the contract checkpoint.

2026-11-17, Roger Lew: scope tests to implementation changes. Do not run the full
repository suite. Run targeted affected-path regression and native artifact checks;
add UI, RQ, stub or Rust checks only where implementation changes affect them.

## Outcomes & Retrospective


Canonical amendment drafts and ADR-0146 are prepared; both independent contract
reviews pass. Exact formula ratification, checkpoint commit, implementation and
runtime acceptance remain pending.
The successor implementation work is M2–M4 in this package, not an implicit
claim that scaffolding delivered the feature. The operator permits forest run mutation/forking; no wepp1 rollout is authorized.

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
