# Correct and validate MOFE ground-cover propagation


This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Ground-cover selections must reach every overland-flow segment assigned the
selected landuse class. Users should see the selected fractions in generated
management files and actual WEPP inputs, not just saved summaries. This is a
wired correction, not a surrogate or redesign.

## Progress


- [x] (2026-09-19 UTC) Identified four propagation seams; scaffolded package and contract amendment.
- [x] (2026-09-19 UTC) Both contract reviews approved; ancestor `824457074` committed.
- [x] (2026-09-19 UTC) Failing regression reproduced 0.75 instead of selected 0.0; implemented four-seam fix in `0fd1a6eca`; 62 focused and 3 archive tests pass.
- [x] (2026-09-19 UTC) Broad suite: 9,044 passed, 99 skipped; late-added cases pass in the separate 93-test run.
- [x] (2026-09-19 04:32 UTC) Corrected Forest WEPP tree completed; 455-hillslope soil/climate/slope parity and ground-only management change proved.
- [x] (2026-09-19 04:38 UTC) Browser/download and canonical archive checks pass; supported restore completed; 93 focused/archive tests pass.
- [x] (2026-09-19 UTC) Post-restore semantic/hash readback passes; complete pre/post JSON is byte-identical.
- [x] (2026-09-19 UTC) Final independent correctness/evidence review passes; documentation gates and handoff completed.

## Surprises & Discoveries


The current contract explicitly excludes ground overrides, so this requires an
amendment rather than silently treating implementation as normative. MOFE
summary rebuild also preserves only canopy; generation alone is insufficient.
Archive/restore operation discovery returns 404 despite documented live routes;
retain this metadata limitation without expanding the runtime repair. Initial
prepared readback correctly failed while preparation was still incomplete, then
passed after the preparation child finished. This was timing, not bad inputs.
The first empty WEPP submission cleared saved kslast through existing parser
behavior; input parity caught this. Superseded by explicit kslast=0.0001 and
initial_sat=0.75 submission, which passed exact prepared-soil parity. Do not
attribute the first attempt's outputs solely to ground cover or expand this
package into API repair.

## Decision Log


2026-09-18, user/Codex: honor existing independent ground selections, preserving
defaults and RAP canopy precedence. Use a supported disposable Forest fork to
protect the source low-severity comparison. No production deployment authorized.

## Outcomes & Retrospective


Implementation and focused tests pass. Independent correctness review found no
production blocker and one validator inventory gap, corrected with exact key-set
and 455/1,065 count assertions. Forest execution and fresh-result checks pass;
post-restore readback and broad suite also pass. Independent reviewer reran the
post-restore validation successfully. Authorized Forest scope complete; source
project unchanged and production deployment/repair excluded.

## Context and Orientation


`wepppy/nodb/core/landuse.py` builds segment plans, materializes managements,
accepts coverage edits and rebuilds summaries. Saved `inrcov_override` means
interrill ground cover, `rilcov_override` rill ground cover; both are fractions
from zero to one. `cancov_override` is canopy cover. MOFE combines segment
managements into `landuse/hill_*.mofe.man`; WEPP preparation produces
`wepp/runs/p*.man`. Source project is `/wc1/runs/eq/equestrian-bonheur` on Forest.

## Plan of Work


Milestone 1: amend `docs/schemas/mofe-management-artifact-contract.md`, retain
ADR-0069 and checkpoint, obtain two independent read-only contract reviews and
commit them before implementation. Record ancestor revision in tracker.

Milestone 2: extend `tests/nodb/test_mofe_scenario_artifacts.py` with real parser
coverage for independent ground fractions, zero/one, absent values, summary
preservation, missing assignment rejection and prepared propagation. Check
process-pool and RAP tests. Add ground values to segment plans and apply after
disturbed replacements in both materialization paths. Generalize canopy-only
regeneration/precheck and summary preservation to all three supported covers.

Milestone 3: create a supported disposable fork using the existing fork workflow,
record its identity, and edit ground cover through the normal coverage method.
Preserve source inputs/state. Use existing cache invalidation and locks, no raw
NoDb edits. Parse every combined and prepared segment, run WEPP with 260803,
record job terminal state and real outputs. Restart only necessary idle Forest
services if required to load candidate source. No production changes.
Validate existing browser/download access to management artifacts and perform a
canonical archive/restore round trip on the disposable fork, comparing retained
management bytes. Do not restore over the named source.

## Concrete Steps


From `/home/workdir/wepppy`, run focused tests with `wctl run-pytest
tests/nodb/test_mofe_scenario_artifacts.py
tests/nodb/test_landuse_mofe_disturbed_scalar_lookup.py
tests/nodb/test_landuse_mofe_process_pool.py --maxfail=1`, then
`wctl run-pytest tests --maxfail=1`. Use rq-agent-operator discovery before API
mutations and record actual job ids. Run `wctl doc-lint --path` on changed docs.

## Validation and Acceptance


Require actual emitted values in combined and prepared inputs, with unaffected
classes/canopy unchanged, including explicit zero and one. Require fresh Forest
WEPP success and parsed output evidence, source preservation, focused tests and
independent correctness review. Report broad-test failures honestly with scope.
No expected numerical sediment direction is asserted for the validation edit.

## Idempotence and Recovery


Retain the disposable fork for inspection; never overwrite the named source.
Coverage edits can be repeated. Writer errors may leave partial files: preserve
diagnostics and retry the supported operation before preparing WEPP. Do not
invent transactional publication or hand-edit generated files.

## Artifacts and Notes


Store compact evidence and reusable validation script under this package's
`artifacts/`. Keep tracker and these living sections current at every milestone.

## Interfaces and Dependencies


Reuse Landuse coverage/build methods, existing Management parser/writer, WEPP
preparation, supported fork and run workflow. No new dependency, schema or API.

Revision note: initial scaffold captures authorized scope and artifact acceptance.
Closure revision: recorded passing tests, Forest artifact checks and independent
final acceptance; retained validation fork for inspection.
