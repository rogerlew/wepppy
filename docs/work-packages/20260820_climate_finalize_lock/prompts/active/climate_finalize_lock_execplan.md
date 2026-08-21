# Implement the multiple-climate collect-and-finalize lock pattern

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must remain current
as work proceeds. Maintain it according to
`docs/prompt_templates/codex_exec_plans.md` and update the package tracker at
every stopping point.

## Purpose / Big Picture

After this change, a GridMET or Daymet multiple-interpolated climate build can
perform its expensive parallel work without retaining a stale NoDb mutation
base. At completion it reloads current durable Climate state under a short
lock, verifies that the inputs governing generated outputs have not changed,
and applies only collected derived fields. An unrelated rewrite is preserved;
a relevant input change explicitly supersedes the outdated build.

The visible proof is a deterministic regression reproducing a same-size
`climate.nodb` rewrite during collection. It must fail against the old behavior
and pass after implementation without weakening `NoDbStaleWriteError`.

## Progress

- [x] (2026-08-21 04:23 UTC) Captured the incident and selected the minimal
  collect-and-finalize approach.
- [x] (2026-08-21 04:23 UTC) Scaffolded the governed work package and reviews.
- [x] (2026-08-21 04:43 UTC) Ratified the contract checkpoint in
  `docs/schemas/nodb-persistence-concurrency-contract.md`; production edits may
  proceed.
- [x] (2026-08-21 05:04 UTC) Added real temporary Climate NoDb interleaving
  regressions for unrelated, relevant, and malformed same-size rewrites, plus
  Daymet collection-failure coverage.
- [x] (2026-08-21 05:04 UTC) Implemented explicit GridMET/Daymet collection
  results, captured build inputs, and fresh allowlisted finalization.
- [x] (2026-08-21 05:32 UTC) Completed focused, base-persistence, stub, docs,
  changed-file quality, and repository-wide validation. The repository suite
  completed with `6087 passed, 61 skipped` after excluding two unrelated
  environment-bound tests documented in the QA artifact.
- [x] (2026-08-21 05:32 UTC) Completed correctness, QA, and security reviews
  with no unresolved medium/high findings.
- [x] (2026-08-21 05:45 UTC) Resolved the validation follow-up: Omni now
  restores process CWD on success/failure, peakflow artifact paths are rooted
  from `__file__`, and the combined Omni-then-Topanga regression passes with
  `25 passed, 1 skipped`.
- [x] (2026-08-21 06:00 UTC) Made the Docker canary contract test explicitly
  skip when the Compose v2 plugin is unavailable and documented that expected
  environment condition in the Docker guide and QA artifacts.
- [ ] Record canary deployment and observation under separate authority.

## Surprises & Discoveries

- Observation: The stale-write guard distinguished two same-size payloads by
  mtime and prevented a lost update.
  Evidence: expected `(mtime=1787285526.3880107, size=11334)` and observed
  `(mtime=1787285597.046286, size=11334)`.
- Observation: `Climate._build_climate_observed_gridmet_multiple` holds
  `self.locked()` around all remote retrieval, interpolation, and CLIGEN work.
  Evidence: `wepppy/nodb/core/climate.py` delegates to
  `ClimateGridmetMultipleBuildService.build` inside the lock context.
- Observation: A same-size rewrite must be primed against the serialized
  `_nodb_size` metadata because the first rewrite can change only that metadata
  byte count even when the domain value has the same apparent length.
  Evidence: the real temporary Climate regression primes one no-op dump and
  asserts the final adjacent atomic rewrite has equal `st_size` and changed
  `st_mtime`.
- Observation: The Topanga manifest was present on the host and inside the
  container; the reported missing fixture was caused by an order-sensitive
  process-CWD leak from Omni scenario orchestration combined with a relative
  test path.
  Evidence: `run_omni_scenario()` changed CWD at
  `wepppy/nodb/mods/omni/omni_run_orchestration_service.py:236`, the isolated
  Topanga test passed, and the combined Omni-then-Topanga regression now passes.
- Observation: The Docker smoke test's Compose v2 capability is not available
  in this runner's Docker CLI. The test now skips explicitly when the capability
  probe fails, while real Compose rendering failures still fail the test.
  Evidence: the runner previously reported the unavailable Compose subcommand;
  the expected environment behavior is documented in `docker/README.md`.

## Decision Log

- Decision: Use explicit climate-specific collect and finalize operations; do
  not add generic automatic NoDb object merging.
  Rationale: Only the climate builder can safely define its relevant inputs and
  derived-output allowlist.
  Date/Author: 2026-08-21, Roger Lew and Codex.
- Decision: Preserve strict stale detection and rehydrate before applying the
  final mutation.
  Rationale: Retrying a stale object dump violates the canonical NoDb contract.
  Date/Author: 2026-08-21, Codex.
- Decision: Exclude manifests, generation directories, resumability, and queue
  redesign.
  Rationale: The operator rejected unnecessary complexity; the confirmed defect
  requires only a bounded finalization transaction.
  Date/Author: 2026-08-21, Roger Lew and Codex.
- Decision: Surface relevant-input conflicts as
  `ClimateMultipleBuildSupersededError` and an RQ `SUPERSEDED` status while
  re-raising the exception.
  Rationale: A stale derived result must not be reported as a successful build,
  but operators need a distinct diagnostic outcome from generic worker failure.
  Date/Author: 2026-08-21, Codex.
- Decision: Restore the caller process CWD at the Omni scenario boundary and
  root peakflow repository artifact paths from `__file__`.
  Rationale: Legacy scenario code still needs a temporary CWD, but leaking it
  makes later tests and callers resolve relative repository paths incorrectly;
  explicit artifact roots make the test hermetic.
  Date/Author: 2026-08-21, Codex.

## Outcomes & Retrospective

The contract checkpoint, production implementation, focused regressions,
repository-wide environment-qualified validation, the CWD/fixture validation
follow-up, and correctness/QA/security reviews are complete. GridMET and
Daymet now collect derived results without holding the Climate NoDb lock and
finalize against refreshed durable state with explicit input conflict handling.
Deployment and canary observation remain outside this package execution.

## Context and Orientation

`NoDbBase`, in `wepppy/nodb/base.py`, serializes an entire controller to one
`.nodb` file. Its stale-write guard rejects a dump when the file's current
mtime and size differ from the signature captured when the object was loaded.
The canonical behavior is defined in
`docs/schemas/nodb-persistence-concurrency-contract.md`: expensive work occurs
outside the lock, then the writer locks, refreshes durable state, applies an
idempotent mutation, and dumps.

The RQ entry point is `build_climate_rq` in `wepppy/rq/project_rq.py`. It loads
`Climate`, reapplies the enqueue-time payload, and invokes `Climate.build()`.
Mode routing reaches either the GridMET service in
`wepppy/nodb/core/climate_gridmet_multiple_build_service.py` or Daymet helpers
in `wepppy/nodb/core/climate_build_helpers.py`. Both paths currently mutate the
passed Climate facade around expensive parallel processing.

Here, collection means computing files and derived values without persisting a
Climate controller. Finalization means acquiring the Climate distributed lock,
rehydrating the latest durable controller, comparing relevant build inputs,
applying only derived results, and committing once.

## Plan of Work

First amend the canonical NoDb contract with a small climate-neutral statement
that a long-running workflow may snapshot relevant inputs, collect outside the
lock, and finalize against freshly hydrated state. State that the finalizer
must reject changed relevant inputs and must explicitly allowlist its mutation;
it may not merge arbitrary object state. Commit or otherwise establish this
contract checkpoint before changing production implementation.

Next add regressions. Construct a real temporary Climate NoDb file rather than
mocking the persistence boundary. Arrange for collection to complete, perform
an intervening atomic same-size rewrite, then finalize. One test changes only
an unrelated field and proves it survives alongside derived results. Another
changes a relevant climate input and proves finalization explicitly refuses to
publish stale derived controller state. Cover GridMET and Daymet delegation so
they share the same semantics.

Then introduce the smallest explicit result value needed by the two multiple
builders. It should contain only currently persisted derived fields such as
`monthlies`, `cli_fn`, `par_fn`, `sub_cli_fns`, `sub_par_fns`, and quality-guard
state. Do not serialize the whole Climate object and do not add a dependency.
Refactor services so expensive work returns this value without triggering the
final controller dump.

Finally, add a climate-specific finalizer near the Climate facade or its build
collaborator. It must acquire the existing distributed lock, refresh from the
durable file while locked, compare an explicit relevant-input snapshot, apply
the derived-field allowlist, and dump once. Define a specific conflict outcome
that the RQ boundary can report without treating the stale build as success.
Do not retry by dumping the original object.

Update NoDb and climate documentation, stubs if public interfaces change, and
the package review artifacts. Avoid changes to enqueue wiring unless the
implementation demonstrates they are necessary; if wiring changes, update the
RQ dependency catalog and run its graph check.

## Concrete Steps

Work from the repository root `/workdir/wepppy` in the standard Linux
development environment.

Inspect the baseline and add tests:

    wctl run-pytest tests/nodb/test_climate_gridmet_multiple_build_service.py tests/nodb/test_climate_build_helpers.py --maxfail=1

Implement the contract and code in small increments, rerunning those tests plus
the Climate facade coverage:

    wctl run-pytest tests/nodb/test_climate_gridmet_multiple_build_service.py tests/nodb/test_climate_build_helpers.py tests/nodb/test_climate_facade_collaborators.py --maxfail=1

Before handoff run:

    wctl run-pytest tests/nodb/test_base_boundary_characterization.py tests/nodb/test_base_unit.py tests/nodb/test_base_misc.py --maxfail=1
    wctl run-pytest tests --maxfail=1
    python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master
    python3 tools/code_quality_observability.py --base-ref origin/master
    git diff --check

Run `wctl check-rq-graph` only if enqueue sites or dependency edges change.
Run `wctl run-stubtest wepppy.nodb.core.climate` if the public Climate surface
or stub changes.

## Validation and Acceptance

The exact same-size interleaving test must exercise real `NoDbBase.dump()` and
fail before implementation. Afterward, an unrelated rewrite remains present
and the collected outputs are committed. A relevant input rewrite causes a
specific conflict/superseded result and does not alter durable state.

Both GridMET and Daymet tests must prove collection returns equivalent derived
state and invokes the shared finalization semantics. Existing output filename,
quality-warning, and generated-content tests must remain green. The full suite
must pass before package review; any environmental blocker must be recorded in
the tracker rather than silently waived.

Independent correctness review must cover absent, empty, populated, supported
legacy, malformed, concurrent-unrelated, and concurrent-relevant states.
Security review must cover NoDb ownership, subprocess inputs, run-tree paths,
partial failure, and diagnostic leakage. No unresolved medium/high finding may
remain at closeout.

## Idempotence and Recovery

Tests and documentation steps are repeatable. Collection must not persist
controller state, so it can fail without requiring NoDb repair. Finalization is
a single bounded transaction; after conflict, a new build from current inputs
is the recovery path. Rollback reverts the implementation commit and restores
the prior long-held-lock behavior; it must never disable the stale-write guard.

Deployment is not authorized by this scaffold. Any canary rollout must name the
rebuilt image digest, preserve the prior deployment revision, and verify a
rollback before beginning the observation window.

## Artifacts and Notes

Incident job: `a2d23f26-8386-433a-9df7-d5f3a03c8d96`, run
`manly-systematization`, 2026-08-21 04:12-04:15 UTC. The controller file changed
approximately 71 seconds after initial hydration while output generation was
still active.

## Interfaces and Dependencies

Use the existing Python standard library, NoDb lock implementation, and current
Climate collaborators. Add no third-party dependency. The final design must
provide explicit concepts equivalent to:

    snapshot = capture_relevant_climate_inputs(climate)
    result = collect_multiple_climate_outputs(climate, snapshot)
    finalize_multiple_climate_outputs(wd, snapshot, result)

Names may follow existing repository conventions, but the separation and
semantics are required. The result object must contain derived outputs only;
the finalizer must load current durable state under lock and apply an explicit
allowlist.

Revision note (2026-08-21): Initial ExecPlan created to implement the operator-
selected minimal finalize-lock pattern following the observed canary incident.

Revision note (2026-08-21 04:43 UTC): Added the climate-neutral
collect-then-finalize contract checkpoint before implementation, including
fresh-state hydration, relevant-input conflict rejection, and derived-field
allowlisting.

Revision note (2026-08-21 05:04 UTC): Implemented the shared Climate
collect/finalize collaborator, refactored GridMET and Daymet multiple builds,
added real NoDb interleaving regressions, and added an explicit RQ superseded
boundary outcome.

Revision note (2026-08-21 05:32 UTC): Completed focused and environment-
qualified repository validation, updated the broad-exception allowlist for the
line-preserving RQ boundary insertion, and closed correctness, QA, and security
review artifacts with no unresolved medium/high findings.

Revision note (2026-08-21 05:45 UTC): Resolved the Topanga validation follow-up
by restoring Omni's process CWD in a `finally` boundary, rooting peakflow
artifact paths from the test file, adding success/failure CWD regressions, and
recording the combined `25 passed, 1 skipped` result.

Revision note (2026-08-21 06:00 UTC): The Docker canary contract test now
explicitly skips when Docker Compose v2 is unavailable; the expected local
environment limitation is documented in the Docker guide and QA artifacts.
