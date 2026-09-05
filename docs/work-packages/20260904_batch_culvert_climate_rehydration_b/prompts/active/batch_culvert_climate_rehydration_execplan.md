# Rehydrate Climate at the batch and culvert mutation boundary

This ExecPlan is a living document maintained according to
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current. Update
`docs/work-packages/20260904_batch_culvert_climate_rehydration_b/tracker.md`
at every stopping point.

## Purpose / Big Picture

Batch watershed and culvert jobs should finish climate generation even when
the durable `climate.nodb` generation advances during earlier watershed,
landuse, or soils processing. After this work, both orchestration paths will
discard their early mutable Climate reference and use the same safe boundary
as the standalone project climate worker: accept the climate directory root,
lock it, clear only the Climate cache entry, hydrate current state, and build.
The NoDb stale-write guard remains strict and will continue rejecting genuine
stale writers.

The result is visible through deterministic tests that rewrite a populated
`climate.nodb` with the same serialized size between orchestration startup and
the climate stage. Those tests fail with the current code and pass after the
change. Representative batch and culvert runs on Forest must then complete
climate and downstream interchange without the incident signature.

## Progress

- [x] (2026-09-05 00:29 UTC) Captured the production incident and scaffolded
  the package for Forest dispatch.
- [ ] Verify current `master`, package authority, applicable nested
  `AGENTS.md`, and the exact current implementations before editing.
- [ ] Add failing batch and culvert interleaving regressions.
- [ ] Implement exact-scope cache invalidation and fresh Climate hydration
  inside both existing climate root-lock callbacks.
- [ ] Prove downstream readers use current post-build Climate state.
- [ ] Run focused and repository validation.
- [ ] Complete independent correctness, QA, and security review and resolve
  every medium/high finding.
- [ ] Deploy only to Forest, capture representative evidence, and record the
  exact rollback procedure.
- [ ] Close and archive this plan after all acceptance criteria are satisfied.

## Surprises & Discoveries

- Observation: the affected openWEPP batch contained no duplicate `OR-10` RQ
  job, so duplicate leaf dispatch is not required to reproduce the failure.
  Evidence: RQ job inspection for parent
  `30edcfbe-297a-4326-a048-a5397410d69e` mapped leaf
  `ddc253a4-e30b-46dc-a819-3d2f3ec85064` to the only affected-batch `OR-10`
  execution.
- Observation: the expected Climate mtime corresponds to leaf startup, while
  the observed mtime advanced roughly 38.75 seconds later and the build began
  roughly 150 seconds after startup. Evidence: the exception signature and
  Kubernetes worker timestamps recorded in `package.md`.
- Observation: worker logger names displayed an older `202606` batch runid
  while paths correctly referenced `202608` and `202609`. This is a diagnostic
  ambiguity, not yet evidence of a persistence-identity defect. Keep it out of
  scope unless a direct causal link is proven.

## Decision Log

- Decision: conform both runners to the placement already used by
  `wepppy/rq/project_rq.py::build_climate_rq`.
  Rationale: it is the repository-standard exact-scope cache guard and avoids
  inventing a second recovery mechanism.
  Date/Author: 2026-09-05 / Roger Lew and Codex.
- Decision: do not add a `NoDbStaleWriteError` retry around a stale object.
  Rationale: the NoDb contract requires discarding the stale mutation base;
  redumping it risks lost updates.
  Date/Author: 2026-09-05 / Codex.
- Decision: keep live execution limited to Forest.
  Rationale: the user requested Forest dispatch; production deployment and
  historical run repair require separate authorization.
  Date/Author: 2026-09-05 / Codex.

## Outcomes & Retrospective

Only the work-package scaffold is complete. Implementation, tests, reviews,
and Forest evidence remain pending. At closeout, summarize the exact code
shape, regression evidence, Forest job/run IDs, any deviations, and whether
the logger/runid ambiguity became a separate follow-up.

## Context and Orientation

NoDb controllers serialize an entire controller to `<run directory>/<name>.nodb`.
Each hydrated instance records the file's mtime and size. On dump,
`wepppy/nodb/base.py::NoDbBase.dump` compares those values with the current
file and raises `NoDbStaleWriteError` if another write advanced the generation.
This is a lost-update guard and must not be weakened.

`wepppy/nodb/batch_runner.py::BatchRunner.run_batch_project` currently
hydrates `Climate` with the other controllers before executing potentially
long watershed, landuse, and soils stages. It later calls `climate.build()`
inside `_run_with_directory_root_lock(..., "climate", ...)`. RAP and OpenET
then read observed-year fields from the retained object, and later WEPP work
may also consume Climate state.

`wepppy/rq/culvert_rq.py::_process_culvert_run` has the same shape. It hydrates
Climate near function entry, performs watershed and combined landuse/soils
work, then invokes `climate.build()` in a climate root-lock callback. The same
variable is passed to `ensure_hillslope_interchange`, `ensure_totalwatsed3`,
and `ensure_watershed_interchange`.

`wepppy/rq/project_rq.py::build_climate_rq` is the implementation precedent.
Its climate root-lock callback first calls
`clear_nodb_file_cache(runid, pup_relpath="climate.nodb")`, then calls
`Climate.getInstance(wd)`, applies any job payload, and invokes `build()`.
The standard governing this placement is
`docs/standards/rq-scoped-nodb-mutation-cache-guard-standard.md`. Writer and
stale-generation rules are in
`docs/schemas/nodb-persistence-concurrency-contract.md`.

Read root `AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md`, the two
canonical documents above, and the full package/tracker before edits. Treat
the package as incident hardening under
`docs/standards/hardening-lifecycle-standard.md`.

## Plan of Work

First inspect current `master` and locate the smallest existing test seams for
`BatchRunner.run_batch_project` and `_process_culvert_run`. Build a call-order
regression for each path. The test must demonstrate that the climate cache
clear uses the composite runid and exact `pup_relpath="climate.nodb"`, occurs
inside the accepted climate directory-root callback, precedes
`Climate.getInstance`, and that `build()` receives the freshly hydrated
instance. Preserve root/archive rejection ordering.

Add a direct persistence-boundary regression for each orchestration family.
Use a temporary run directory containing a valid, populated Climate NoDb
document. Hydrate an early instance, rewrite the durable document to a new
same-size generation, and exercise the climate-stage callback. Before the fix,
the old orchestration shape should reproduce `NoDbStaleWriteError`; after the
fix, the callback must reload and successfully mutate current state. Do not
mock `NoDbBase.dump`, its signature comparison, filesystem stat, cache clear,
or the Climate hydration boundary in this direct test. A narrower call-order
unit test may use mocks in addition to, not instead of, this evidence.

Then edit `wepppy/nodb/batch_runner.py`. Remove the early mutable Climate
hydration unless an earlier stage has a proven read dependency. Replace the
lambda climate callback with a small local function that clears the exact
cache entry, hydrates current Climate, and builds it while the existing
climate root lock is held. Ensure RAP and OpenET use current post-build state;
prefer an explicit post-stage hydration/reference rather than retaining a
pre-stage object. Do not introduce a broad exception handler or stale-object
retry.

Apply the equivalent minimal change to
`wepppy/rq/culvert_rq.py::_process_culvert_run`. Preserve the combined
landuse/soils lock, climate root lock, WEPP call order, metadata outcomes, and
exception contracts. Ensure the Climate passed to hillslope and watershed
interchange is the post-build current instance. Use the existing imported
cache helper if present; otherwise add only the canonical import.

Update tests and any affected developer/operator documentation. Do not update
`wepppy/rq/job-dependencies-catalog.md` unless queue/dependency wiring actually
changes. If implementation reveals that early Climate state is intentionally
used before the climate stage, record the dependency in this plan and design a
fresh read that does not retain a mutable stale base.

Finally run focused tests and the repository sanity gate. Create independent
correctness, QA, and security review artifacts from repository templates and
resolve all medium/high findings. Deploy the reviewed commit only to Forest
using the current canonical deployment procedure. Record the commit, image
digest, commands, representative batch and culvert identifiers, status/log
evidence, impact, and rollback. Do not touch production.

## Concrete Steps

From the repository root on Forest, first synchronize and inspect:

    git status --short --branch
    git pull --ff-only origin master
    rg -n "Climate.getInstance|climate.build|clear_nodb_file_cache" \
      wepppy/nodb/batch_runner.py wepppy/rq/culvert_rq.py \
      wepppy/rq/project_rq.py tests/rq tests/culverts

Run focused tests during implementation. Confirm the exact current culvert
test paths rather than guessing a deleted or renamed module:

    wctl run-pytest tests/rq/test_batch_rq_retry_selection.py --maxfail=1
    rg -l "_process_culvert_run|culvert_run" tests/culverts tests/rq
    wctl run-pytest <identified-culvert-test-paths> --maxfail=1

After implementation, run:

    wctl run-pytest tests/rq/test_batch_rq_retry_selection.py <identified-culvert-test-paths> --maxfail=1
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    wctl doc-lint --path docs/work-packages/20260904_batch_culvert_climate_rehydration_b --path PROJECT_TRACKER.md
    git diff --check

Run `wctl check-rq-graph` only if the final diff changes an enqueue site,
function target, dependency, or queue wiring. Otherwise record that the graph
gate is not applicable and cite the diff.

Use the canonical Forest deployment entry point discovered from `AGENTS.md`,
deployment documentation, and repository scripts. Do not invent a parallel
image or deployment flow. Record the exact safe command before executing it.

## Validation and Acceptance

The batch unit regression must fail if the cache clear is removed, broadened
from exact Climate scope, moved outside the climate root lock, or ordered after
hydration. The culvert regression must enforce the same properties. Both must
prove that downstream consumers see current post-build Climate state.

The direct filesystem tests must start from populated valid state and advance
mtime while preserving serialized size, matching the production signature.
They must exercise real NoDb signature validation. Separately cover absent
optional RAP/OpenET state, populated current state, supported legacy Climate
state, and malformed/missing required Climate state. The fix must not convert
invalid state into silent success.

Existing successful batch and culvert tests must retain status events,
timestamps, metadata results, directory-root locking, and output order. No RQ
dependency graph change should appear in the final diff.

Forest acceptance requires one representative batch leaf and one culvert leaf
to build climate and progress through their expected downstream stage. Worker
logs must contain no target `NoDbStaleWriteError`; durable run metadata must
agree with RQ/status output. Record any unrelated failure separately rather
than claiming the target fix failed or passed without evidence.

## Idempotence and Recovery

Code and test steps are repeatable. Tests must use temporary directories and
must not mutate `/wc1` production data. Exact cache clearing is scoped to the
active run and is safe to repeat inside the accepted root-lock callback.

If implementation fails after edits, revert only the package implementation
commit or restore the changed files through a reviewed patch; do not reset a
dirty worktree or discard unrelated changes. If Forest rollout fails, use the
documented deployment rollback to the previously recorded image digest and
retain logs and failed metadata as evidence. Never recover by disabling the
stale-write guard or manually rewriting a live `climate.nodb`.

## Artifacts and Notes

Create and maintain:

- `artifacts/2026-09-05_correctness_review.md` from the correctness template.
- `artifacts/2026-09-05_qa_review.md` containing test/state/Forest evidence and
  findings dispositions.
- `artifacts/2026-09-05_security_review.md` from the security template.
- `artifacts/2026-09-05_forest_acceptance.md` with deployed revision, image,
  job/run identifiers, log excerpts, impact, and rollback.

Keep evidence concise and redact credentials. Hostnames, runids, job IDs, and
documented paths are acceptable.

## Interfaces and Dependencies

Do not add external dependencies or public APIs. Reuse:

- `wepppy.nodb.base.clear_nodb_file_cache` for exact cache invalidation.
- `Climate.getInstance(wd)` for fresh hydration.
- Existing `_run_with_directory_root_lock` helpers for precondition and lock
  ordering.
- Existing `Climate.build()` and downstream interchange APIs unchanged.

At completion, both orchestration paths must have the semantic shape:

    def _build_climate() -> None:
        clear_nodb_file_cache(runid, pup_relpath="climate.nodb")
        current_climate = Climate.getInstance(wd)
        current_climate.build()

The actual implementation may return/store `current_climate` for downstream
readers, or reacquire after build, but it must not rely on an instance hydrated
before unrelated long-running stages. Any deviation must be recorded with
tests and rationale in the Decision Log.

Revision note (2026-09-05): initial Forest-dispatch scaffold based on the
openWEPP `nasa-roses-202608-psbs` OR-10 incident.
