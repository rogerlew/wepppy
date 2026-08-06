# Add a coherent skip-Omni fork option

This ExecPlan is a living document. Maintain it according to
`docs/prompt_templates/codex_exec_plans.md`, including `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` at every stopping
point.

## Purpose / Big Picture

Users need to fork a project without copying potentially large or stale Omni
scenario and contrast child projects. After this work, checking **Skip Omni
Scenarios/Contrasts and reset controllers** creates a normal fork whose base
project remains usable while its Omni subsystem is fresh and empty. The source
is unchanged. Leaving the box unchecked behaves exactly as today.

## Progress

- [x] (2026-08-06 14:55 UTC) Scaffolded package, draft contract, security
  review artifact, tracker, and this ExecPlan.
- [x] (2026-08-06 UTC) Incorporated findings REV-01 through REV-10 and
  registered/cross-linked SURF-04B.
- [x] (2026-08-06 UTC) Selected rewrite-in-place reset semantics and added
  verified ancestors, Omni RedisPrep timestamp removal, and query catalog/cache
  invalidation after follow-up review.
- [x] (2026-08-06 UTC) Inventoried canonical fresh state and expanded reset
  equivalence to remove optional copied Omni-owned keys absent from fresh state.
- [x] (2026-08-06 UTC) Obtained post-fix PASS confirmation for COR-01 through
  COR-03 and SEC-01 through SEC-07; zero medium/high findings remain.
- [ ] Ratify and commit the contract-first checkpoint (ratified; commit pending).
- [ ] Implement the UI/API/RQ field without changing existing defaults.
- [ ] Implement exact copy exclusion and one bounded destination reset operation.
- [ ] Add exhaustive property and integration evidence.
- [ ] Complete documentation, full validation, and independent final reviews.

## Surprises & Discoveries

- Observation: the fork path already transports `undisturbify` and
  `skip_wepp_runs_output` from Jinja data attributes through URL-encoded form
  data, rq-engine parsing, enqueue arguments, and `fork_rq`.
  Evidence: `fork_console_control.htm`, `fork_console.js`,
  `fork_archive_routes.py`, and `project_rq.py` use the same ordered pair.
- Observation: Omni state spans `omni.nodb`, aggregate/sidecar content under
  `omni/`, and complete child projects under `_pups/omni/{scenarios,contrasts}`.
  Evidence: `wepppy/nodb/mods/omni/README.md` and `Omni.omni_dir`.
- Observation: `_use_rq_job_pool_concurrency` can be persisted although fresh
  `Omni.__init__` state omits it.
  Evidence: its getter defaults on absence but its setter stores the optional key.
- Observation: path-based query-engine and RedisPrep operations can follow
  copied symlink/special entries, and profile destination helpers can resolve
  different roots.
  Evidence: checkpoint security findings SEC-01, SEC-02, and SEC-05.

## Decision Log

- Decision: use canonical field `skip_omni_scenarios_contrasts`, default false.
  Rationale: it names the omitted data and avoids coupling to existing flags.
  Date/Author: 2026-08-06, operator direction captured by Codex.
- Decision: reset only Omni and its owned directories.
  Rationale: unrelated controllers remain valid and were not authorized for
  reset.
  Date/Author: 2026-08-06, Codex.
- Decision: exhaustively generate the eight boolean combinations with existing
  pytest/Jest primitives.
  Rationale: the domain is finite; a new dependency adds no value.
  Date/Author: 2026-08-06, Codex.
- Decision: exclude the two collection nodes themselves and recreate real empty
  directories under a verified parent.
  Rationale: descendant-only excludes could copy a symlink or special node.
  Date/Author: 2026-08-06, independent review disposition.
- Decision: reset after destination identity rewrite and optional undisturbify,
  but before general job-marker reset and completion.
  Rationale: copied Omni state must not be hydrated with source identity.
  Date/Author: 2026-08-06, independent review disposition.
- Decision: retain existing unready registered partial-destination behavior.
  Rationale: this package adds no whole-run rollback or tombstoning transaction.
  Date/Author: 2026-08-06, independent review disposition.
- Decision: add `Omni.reset_for_fork()` as a rewrite-in-place, single-dump
  operation using the identity-rewritten controller's actual config.
  Rationale: this fixes the controller mechanism before checkpoint and avoids
  replacement/cache ambiguity.
  Date/Author: 2026-08-06, follow-up review disposition.
- Decision: remove exactly the two Omni RedisPrep timestamps and invalidate the
  copied query-engine catalog/cache for every checked tuple.
  Rationale: otherwise the destination advertises removed Omni work/artifacts.
  Date/Author: 2026-08-06, follow-up review disposition.
- Decision: reject unknown, structured, repeated, and numeric JSON values for
  the new boolean before registration or enqueue.
  Rationale: the common parser otherwise preserves values that Python truthiness
  could misclassify.
  Date/Author: 2026-08-06, checkpoint review disposition.
- Decision: resolve one canonical destination and hold destination-rooted
  no-follow descriptors across destructive reset operations; reject active
  Omni locks rather than clearing them.
  Rationale: copied nodes and concurrent writers must not redirect or race a
  public fork reset.
  Date/Author: 2026-08-06, security review disposition.

## Outcomes & Retrospective

Scaffolding is complete. No production implementation has started. Closure
requires a coherent checked fork, exact unchecked compatibility, and observable
source immutability.

## Context and Orientation

The fork form is rendered by
`wepppy/weppcloud/templates/controls/fork_console_control.htm`. Its JavaScript
is `wepppy/weppcloud/static/js/fork_console.js`. The POST endpoint is
`fork_project` in
`wepppy/microservices/rq_engine/fork_archive_routes.py`; the agent schema and
defaults live in `schema_defaults_routes.py`. The endpoint enqueues `fork_rq`
in `wepppy/rq/project_rq.py`, which delegates filesystem preparation to
`prepare_fork_run` in `project_rq_fork.py`.

Omni is a NoDb controller implemented under `wepppy/nodb/mods/omni/`. Its
persisted controller is `omni.nodb`; aggregate results and contrast sidecars
are under `<run>/omni`; complete child projects are under
`<run>/_pups/omni/scenarios` and `<run>/_pups/omni/contrasts`. A "fresh"
controller means the same persisted state produced by initializing Omni for a
new run, not a hand-maintained partial list of fields.

Property-style tests here mean tests that generate every member of the finite
three-boolean input domain and assert general invariants. They do not require a
third-party property-testing library.

## Plan of Work

First, inventory fresh Omni state. Create a focused NoDb test that initializes
Omni, populates scenario and contrast state plus artifacts, invokes a proposed
single reset API, reloads through the normal singleton/cache boundary, and
compares its complete persisted key set with a freshly initialized controller,
including removal of optional copied Omni-owned keys absent from fresh state. Define
the reset in the Omni subsystem rather than editing private fields from RQ.
Confirm required config/run identity fields remain destination-specific.

Then finalize `artifacts/2026-08-06_contract_decision.md`. Dispatch independent
contract/correctness and security reviews, disposition findings, obtain final
operator acceptance if the reviewed matrix changes, and commit the complete
checkpoint as a standalone ancestor. Do not edit production implementation
files before this point.

After the checkpoint, thread `skip_omni_scenarios_contrasts: bool = False`
through the existing fork surfaces. Update Jinja data, the checkbox, JavaScript
initialization and URL-encoded payload, Flask console query hydration,
rq-engine boolean parsing/response, schema/default discovery, enqueue args,
`fork_rq`, and `prepare_fork_run`. Preserve compatibility for callers that omit
the argument.

Extend the rsync command builder with exact anchored exclusions for the two
collection entries themselves. Add command and real-rsync tests before relying
on the patterns. Follow the normative sequence: copy, existing link
normalization, root NoDb identity rewrite, filesystem marker cleanup, optional
undisturbify, destination Omni cache/exact-lock clearing, one canonical reset,
exact Omni RedisPrep timestamp removal, query-engine catalog/cache invalidation,
general job-marker reset, then completion. Never hydrate copied Omni before its
identity rewrite. Verify every reset ancestor with no-follow real-directory
checks. Any failure propagates through existing failure handling and may retain
an unready registered partial destination.

Strengthen readiness only for checked five-argument jobs. Preserve legacy
four-argument inspection. Deploy worker-first after draining/restarting the
fork/archive consumers, then enable the updated producer. Update the RQ catalog
and validate the graph even when dependency topology does not change.

Finally update affected fork UI/user docs, Omni developer/end-user docs,
OpenAPI/schema defaults, and `wepppy/rq/job-dependencies-catalog.md` if its
signature or generated inventory changes. Rebuild generated frontend assets
only through the canonical controller build command if the source/build model
requires it.

## Concrete Steps

Work from `/home/workdir/wepppy`.

1. Read the nearest `AGENTS.md` for every implementation/test directory and
   re-read the accepted checkpoint.
2. Add failing focused tests for full persisted fresh Omni equivalence, all
   eight option tuples, exact node exclusions, sibling preservation, unsafe
   target entries, quiescent source immutability, source-helper non-invocation,
   reset failure, checked readiness, legacy jobs, reused-profile stale
   cache/locks, exact RedisPrep timestamp preservation/removal, regenerated
   query catalog discovery, malformed/default/query/session inputs, and
   accessibility.
3. Implement the smallest controller-owned reset and option threading that
   satisfies those tests.
4. Run focused checks:

       wctl run-pytest tests/nodb/mods/test_omni.py
       wctl run-pytest tests/rq/test_project_rq_fork.py
       wctl run-pytest tests/microservices/test_rq_engine_fork_archive_routes.py
       wctl run-pytest tests/microservices/test_rq_engine_schema_defaults_routes.py
       wctl run-pytest tests/weppcloud/routes/test_fork_console_route.py
       wctl run-pytest tests/weppcloud/routes/test_pure_controls_render.py
       wctl run-npm lint
       wctl run-npm test

5. Run repository gates:

       wctl check-rq-graph
       python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
       wctl run-pytest tests --maxfail=1
       wctl doc-lint --path docs/work-packages/20260806_fork_skip_omni_reset

6. Obtain correctness, QA, and security reviews; disposition every finding and
   rerun affected gates.

## Validation and Acceptance

The primary integration fixture starts with a populated source containing at
least one scenario child, one contrast child, aggregate files, sidecars,
non-default Omni fields, and an unrelated `_pups` sibling sentinel. With the
option checked, the fork succeeds, reloads a fresh Omni controller, has empty
real Omni collection/aggregate directories, retains the unrelated sentinel,
and leaves source hashes unchanged except for the existing source
`redisprep.dump` fork-job tracking delta. With the option unchecked, the populated
Omni fixture is copied under existing semantics.

The option matrix generator covers `(undisturbify,
skip_wepp_runs_output, skip_omni_scenarios_contrasts)` for all eight tuples at
UI serialization, route parsing/enqueue, command construction, reset decision,
and worker completion. Each test states an invariant and computes its expected
result from the tuple rather than storing eight snapshots.

Injected reset failure must publish/raise through the canonical fork failure
path and must not publish `FORK_COMPLETE`. Unsafe symlink or special entries at
destination reset roots must be rejected without touching their targets.

Boundary tests also cover omitted, accepted, malformed, and repeated boolean
forms; absent/false/true/hostile query hydration; restored tracked jobs;
returned resolved-value display; native checkbox label/keyboard accessibility;
and legacy four-argument readiness. Source hashes use a quiescent fixture and
exclude only the existing `redisprep.dump` fork-job tracking delta; separate
spies prove no reset/cache/lock helper receives the source ID or path.

## Idempotence and Recovery

Tests use temporary run roots and are repeatable. Reset is destination-only and
must be safe to retry on an unready fork destination. The route may already
have registered that partial destination; this package adds no whole-run
rollback or tombstoning. Do not retry or reuse a destination after a failed
public fork unless the existing target-run contract explicitly permits it.
Never clean the source as recovery.

## Artifacts and Notes

Record the accepted checkpoint SHA, focused/full test summaries, generated
option matrix evidence, and final review dispositions in `tracker.md` and this
plan. Store dedicated security findings in
`artifacts/2026-08-06_security_review.md`.

## Interfaces and Dependencies

The final public field is:

    skip_omni_scenarios_contrasts: bool = False

It must appear in the fork request schema, resolved defaults, success response,
enqueue arguments, `fork_rq`, and `prepare_fork_run`. The Omni reset interface
is the public, controller-owned `Omni.reset_for_fork()` operation with a `.pyi`
signature and documented postcondition. It mutates the identity-correct
destination controller under one lock/dump transaction; it does not substitute
a separately initialized controller or file, and the canonical atomic dump is
required. No external dependency is added.
