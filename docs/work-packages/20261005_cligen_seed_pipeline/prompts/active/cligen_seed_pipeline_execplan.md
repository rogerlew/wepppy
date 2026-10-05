# Expose and Propagate the CLIGEN Seed End to End

This ExecPlan is a living document. The sections `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be maintained
as work proceeds. It follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this work, an advanced Climate Options field lets a user choose an exact
CLIGEN random seed. That integer survives browser serialization, authorized
request parsing, `climate.nodb`, queued-job replay, mode routing, nested workers,
and the native CLIGEN command. Leaving it blank preserves current behavior. A
real build on a normalized disposable `canine-liar` fork will prove the path by
reading persisted state, consumed argv, and deterministic generated climate
output.

## Progress

- [x] (2026-10-05 18:40Z) Traced UI, route, NoDb, RQ replay, build snapshot,
  adapter, and subprocess boundaries.
- [x] (2026-10-05 18:40Z) Created the package, compatibility plan, canonical
  contract draft, correctness gate, and this ExecPlan.
- [x] (2026-10-05 19:01Z) Completed two independent contract reviews and
  corrected the proposal to preserve effective defaults.
- [x] (2026-10-05 19:43Z) Obtained exact operator approval after both reviewers
  confirmed the corrected contract.
- [ ] Commit the standalone contract checkpoint.
- [ ] Implement UI parsing/persistence and seed propagation.
- [ ] Add focused tests across every boundary.
- [ ] Validate generated output and deterministic replay on `canine-liar`.
- [ ] Run broad gates, close reviews and package records, and archive this plan.

## Surprises & Discoveries

- Observation: Climate already initializes `_cligen_seed = None` and modified
  stochastic builds allocate a random five-digit seed, but the value is not
  consistently passed to the downstream CLIGEN call.
  Evidence: `_ensure_cligen_seed` and `_build_climate_prism` assign the field;
  `prism_mod`/`run_multiple_year`/`run_observed` call sites omit it.

- Observation: CLIGEN adapter defaults are path-specific.
  Evidence: `par_mod` substitutes `12345` when `randseed is None`, while vanilla
  and observed commands currently omit `-r`. Preserving defaults therefore
  requires forwarding only the explicit override and leaving `None` untouched.

- Observation: observed multiple builds snapshot all output-determining inputs
  except the explicit `_cligen_seed_override`.
  Evidence: `ClimateMultipleBuildInputs` includes years, station, guards, mode,
  and spatial mode but no `_cligen_seed`.

- Observation: Existing `_cligen_seed` values cannot prove explicit user intent.
  Evidence: modified paths generate/persist the value but do not consume it;
  the actual native argument is the `par_mod` fallback `-r12345`.

- Observation: Direct mutation of the original `canine-liar` climate tree is
  unnecessarily risky.
  Evidence: a build may clear or replace hundreds of climate artifacts; the
  corrected plan uses a complete normalized disposable fork and manifests the
  source.

## Decision Log

- Decision: Use a single `cligen_seed` request key backed by a new additive
  `_cligen_seed_override` state field, leaving `_cligen_seed` runtime-only.
  Rationale: This is additive, avoids a migration, preserves effective defaults,
  and distinguishes user intent from legacy generated values.
  Date/Author: 2026-10-05 / Codex.

- Decision: Omission preserves state; present empty resets to automatic; valid
  integers are restricted to `0..99999`.
  Rationale: It supports legacy/RQ clients, gives the UI an explicit reset, and
  matches WEPPpy's existing five-digit application policy; it is not a native
  CLIGEN range limit.
  Date/Author: 2026-10-05 / Codex.

- Decision: Add the seed to immutable multiple-build snapshots.
  Rationale: A seed change changes generated output and must supersede stale
  collection instead of publishing it.
  Date/Author: 2026-10-05 / Codex.

- Decision: Validate against a complete disposable `fork_rq` destination made
  from `canine-liar`.
  Rationale: The supported fork workflow normalizes run identity and orchestration
  state while keeping mutation away from the original climate tree.
  Date/Author: 2026-10-05 / Codex.

- Decision: Invoke the supported fork with
  `skip_omni_scenarios_contrasts=True`.
  Rationale: The Climate pipeline evidence uses the normalized root project and
  does not require copying `canine-liar` Omni scenarios or contrasts.
  Date/Author: 2026-10-05 / Operator and Codex.

## Outcomes & Retrospective

No implementation outcome yet. The source trace establishes that the minimal
change is optional-argument propagation through existing interfaces, with no
new service, queue, or dependency.

## Context and Orientation

`wepppy/weppcloud/templates/controls/climate_pure.htm` renders Climate Options.
`wepppy/weppcloud/controllers_js/climate.js` serializes the form and posts JSON
to rq-engine. `wepppy/microservices/rq_engine/climate_routes.py` parses inputs,
calls `Climate.parse_inputs`, then stores the same payload in job metadata.
`wepppy/rq/project_rq.py::build_climate_rq` reloads and replays that payload
before building.

`wepppy/nodb/core/climate_input_parser.py` owns transactional input mutation.
`wepppy/nodb/core/climate.py` and its helper/service modules route climate modes
to `Cligen.run_multiple_year`, `Cligen.run_observed`, `par_mod`, or the direct
single-storm subprocess. `ClimateMultipleBuildInputs` fences asynchronous
observed output against changed durable inputs.

The seed is an integer passed to the native executable as one argument such as
`-r31415`. An explicit seed is output-determining. `None` means the preexisting
path-specific automatic/default behavior, not a new numeric default.

## Plan of Work

Milestone 1 completes the contract-first checkpoint. Obtain the required two
independent read-only reviews of `CLIMATE-SEED-01`, disposition findings, amend
the canonical contract if necessary, then commit only package/checkpoint and
contract documents. Record that ancestor commit before touching implementation.

Milestone 2 adds the advanced UI and transactional NoDb parsing. Render a
numeric `cligen_seed` field from a public `Climate.cligen_seed` property. Let
normal form serialization carry it. Parse omission, empty/null, valid integer,
and invalid input exactly as the canonical contract specifies, including the
field in rollback snapshots. Add template/Jest, parser, disk-reload, and route
tests.

Milestone 3 propagates the optional override. Add `randseed: int | None` to the
relevant CLIGEN interfaces and helpers. Append `-rN` only for non-`None` values.
Pass the captured value through vanilla, modified stochastic, observed, future,
interpolated paths and the dormant single-storm helper without enabling its
Climate modes. Include the override in `ClimateMultipleBuildInputs` and every
worker submission. Preserve existing default behavior for `None` and use one
override for every child of a logical build.

Milestone 4 proves the pipeline. Focused tests must assert exact argv at each
adapter family and job payload replay. For actual-project evidence, first retain
a complete source-project manifest, then enqueue the supported `fork_rq`
workflow with `skip_omni_scenarios_contrasts=True` from `canine-liar` to a
verified unique destination run ID. Wait for
fork completion and normal identity, RedisPrep, Omni-link, marker, TTL, cache,
and readiness normalization before resolving the returned destination working
directory. Confine all mutation to that normalized fork. Submit a bounded
explicit seed through the rq-engine request path, reload `climate.nodb`, capture
and replay the queued job metadata through `build_climate_rq`, reach
`Climate.build`, and execute a short supported real CLIGEN build twice. Parse
both fresh `.cli` files and compare bytes. Read the retained CLIGEN log to
confirm the exact `-rN` consumer argument, then clean up only after re-verifying
the unique fork identity and prove the source manifest is unchanged.

Milestone 5 runs frontend lint/tests, focused and full Python gates, stubs,
isolation, docs lint, and patch hygiene. Complete correctness review, update
the user Climate Options guide and controller documentation, close package and
tracker records, remove this plan from root active listings, and move it with
`wctl doc-mv --force` to `prompts/completed/`.

## Concrete Steps

Run from `/workdir/wepppy`:

    wctl run-npm lint
    wctl run-npm test -- climate
    python wepppy/weppcloud/controllers_js/build_controllers_js.py
    wctl run-pytest tests/nodb tests/weppcloud/routes/test_climate_bp.py \
      tests/rq --maxfail=1
    wctl run-pytest tests --maxfail=1
    wctl check-test-stubs
    wctl doc-lint --path docs/work-packages/20261005_cligen_seed_pipeline
    wctl doc-lint --path docs/ui-docs/contracts/climate-cligen-seed-contract.md
    git diff --check

Use narrower focused files during development, then record exact final counts.
Do not use host Python for WEPPpy integration when container dependencies are
required.

## Validation and Acceptance

Acceptance requires more than a saved field. A rendered form must serialize an
explicit integer; the authorized route must persist it and enqueue the same
payload; the worker must reload/replay it; the mode builder must pass it to the
native adapter; and the subprocess argv must contain exactly one matching
`-rN`. Invalid values must return the normal validation response without any
partial NoDb mutation.

For the `canine-liar` fork, reload the normal `Climate` singleton from disk after
input parsing, not the same in-memory object. Generate a fresh parseable `.cli` twice
under otherwise identical state and require byte equality. Retain compact hashes
and log excerpts, not duplicate climate datasets, in the package artifact.

## Idempotence and Recovery

Code/test steps are repeatable. Before actual-project mutation, save exact
manifest and hash the complete original project tree, create a normalized fork
through `fork_rq`, wait for its standard post-fork readiness checks, and confine
all request/build mutation to that returned destination. After retaining compact
evidence, clear NoDb caches and clean up only the destination whose unique run
identity and resolved path were verified immediately beforehand. Require an
exact original before/after manifest. Never delete or overwrite original
`canine-liar` artifacts.

## Artifacts and Notes

Retain the contract decision, review disposition, correctness review, test
summary, and actual-project evidence under this package's `artifacts/` folder.
Evidence must name the code revision, project, explicit seed, persisted value,
command argument, output hashes, parse result, and restoration result.

## Interfaces and Dependencies

Use only existing repository and standard-library facilities. The stable public
NoDb accessor is:

    @property
    def cligen_seed(self) -> int | None: ...

CLIGEN-facing methods accept a keyword-compatible optional seed:

    randseed: int | None = None

No shell command construction, external dependency, schema migration, or queue
topology change is permitted.

---

Revision note (2026-10-05 18:40Z): Initial self-contained plan created after
tracing the existing seed state and all Climate-owned CLIGEN boundaries.

Revision note (2026-10-05 19:01Z): Incorporated both independent contract
reviews by separating explicit override state, preserving effective defaults,
clarifying batch/single-storm/multiple-build scope, and moving project evidence
to a complete normalized disposable fork.
