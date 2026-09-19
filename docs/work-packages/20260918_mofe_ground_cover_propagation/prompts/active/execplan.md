# Correct and validate MOFE ground-cover propagation


This living plan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Ground-cover selections must reach every overland-flow segment assigned the
selected landuse class. Users should see the selected fractions in generated
management files and actual WEPP inputs, not just saved summaries. This is a
wired correction, not a surrogate or redesign.

## Progress


- [x] (2026-09-19 UTC) Identified four propagation seams; scaffolded package and contract amendment.
- [ ] Obtain two independent contract reviews and commit checkpoint ancestor.
- [ ] Add failing regression tests, implement minimal fix, run focused and broad tests.
- [ ] Validate supported Forest fork of equestrian-bonheur through fresh WEPP execution.
- [ ] Final independent correctness review, documentation gates and handoff.

## Surprises & Discoveries


The current contract explicitly excludes ground overrides, so this requires an
amendment rather than silently treating implementation as normative. MOFE
summary rebuild also preserves only canopy; generation alone is insufficient.

## Decision Log


2026-09-18, user/Codex: honor existing independent ground selections, preserving
defaults and RAP canopy precedence. Use a supported disposable Forest fork to
protect the source low-severity comparison. No production deployment authorized.

## Outcomes & Retrospective


Scaffold complete; implementation and acceptance pending.

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
