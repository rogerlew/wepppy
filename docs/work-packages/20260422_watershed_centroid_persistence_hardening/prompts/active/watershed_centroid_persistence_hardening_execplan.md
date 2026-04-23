# Watershed Centroid Persistence Hardening and Climate Build Contract Repair

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan must be maintained in accordance with `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture

After this change, climate builds will no longer fail with a raw `TypeError` when watershed centroid persistence is incomplete. Instead, centroid consumers will use a repair-or-fail contract: when abstraction artifacts are available, centroid is deterministically rebuilt and persisted; when repair is impossible, the system raises an explicit, typed state error with run context.

Users and operators will be able to re-run climate jobs without manual file surgery for the observed failure class, and queue diagnostics will point to durable root causes rather than nullable unpack traces.

## Progress

- [x] (2026-04-23 01:35 UTC) ExecPlan authored and linked from package tracker.
- [x] (2026-04-23 02:03 UTC) Added watershed repair-or-fail centroid contract (`require_centroid`) and typed `WatershedCentroidStateError`.
- [x] (2026-04-23 02:04 UTC) Replaced climate/station centroid call sites with `require_centroid()` in climate build and station catalog flows.
- [x] (2026-04-23 02:05 UTC) Added NoDb stale-write rejection at persistence boundary with typed `NoDbStaleWriteError`.
- [x] (2026-04-23 02:06 UTC) Added post-`abstract_watershed_rq` durability verification with one bounded repair attempt.
- [x] (2026-04-23 02:11 UTC) Added and passed targeted regression suites for centroid self-heal/fail, stale-write rejection, and RQ durability checks.
- [x] (2026-04-23 02:12 UTC) Hardened NoDb lock/cache interplay by forcing unlock on post-body dump failures and stamping mtime/size for Redis-hydrated instances.
- [ ] (2026-04-23 02:12 UTC) Full-repo gate `wctl run-pytest tests --maxfail=1` remains blocked by an unrelated pre-existing Geneva failure in a dirty worktree.
- [x] (2026-04-23 02:12 UTC) Updated ExecPlan/tracker/root tracker entries for handoff.

## Surprises & Discoveries

- Observation: `NoDbBase.locked()` did not guarantee unlock when `dump_and_unlock()` raised after a successful `with` body.
  Evidence: Stale-write rejection surfaced lock leaks during disturbed integration validation until lock-boundary cleanup was added.

- Observation: Redis-hydrated NoDb instances were returning stale `_nodb_mtime/_nodb_size` metadata.
  Evidence: `Disturbed.getInstance('/wc1/runs/le/legato-alkalinity')` returned signature `(mtime=1776793303.822223, size=15433)` while on-disk stat was `(mtime=1776793304.6262271, size=15432)` until hydration signature stamping was added.

- Observation: Required full-suite gate currently fails in an unrelated existing Geneva path.
  Evidence: `tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py::test_wp09_watershed_warning_thresholds_propagate_to_results_query_report[...]` fails with `KeyError: 'severity'` while touched package tests are green.

## Decision Log

- Decision: Prioritize contract hardening over timing/sleep-based mitigation.
  Rationale: Incident evidence showed failures persisted minutes later and after retries, indicating state integrity defect rather than transient readiness delay.
  Date/Author: 2026-04-23 / Codex.

- Decision: Keep external schema/keys additive and stable while strengthening behavior.
  Rationale: The incident is internal state durability; broad schema redesign is unnecessary and riskier.
  Date/Author: 2026-04-23 / Codex.

- Decision: Accept the already-present implementation in the active worktree after explicit verification instead of re-authoring equivalent changes.
  Rationale: Required code and tests were already present in target modules; verification + targeted fixes avoided churn and reduced risk of contract drift.
  Date/Author: 2026-04-23 / Codex.

- Decision: Keep stale-write guard strict (mtime+size signature) but patch lock/cache boundaries for correctness.
  Rationale: Guard strictness is required to reject stale overwrite explicitly; lock cleanup and Redis hydration signature refresh eliminate false-positive leakage without weakening the boundary contract.
  Date/Author: 2026-04-23 / Codex.

## Outcomes & Retrospective

Scoped hardening outcomes are implemented and validated in targeted coverage. Watershed centroid consumers now rely on repair-or-fail semantics with typed errors, NoDb persistence rejects stale overwrites explicitly, and RQ abstraction now verifies persisted centroid durability with one bounded repair attempt.

Observed behavior change matches package intent:
- centroid missing + artifacts present -> deterministic self-heal and persisted centroid
- centroid missing + artifacts missing -> `WatershedCentroidStateError` with run context
- stale writer path -> explicit `NoDbStaleWriteError`
- post-abstraction persistence verification -> one repair attempt then typed fail if still missing

Validation evidence:
- `wctl run-pytest tests/nodb/mods/disturbed/test_sbs_validation.py::TestColorTablePreservation::test_get_sbs_preserves_color_table tests/nodb/test_watershed_runtime_contract.py tests/nodb/test_base_boundary_characterization.py tests/nodb/test_climate_station_catalog_service.py tests/nodb/test_climate_facade_collaborators.py tests/rq/test_project_rq_mutation_guards.py --maxfail=1` -> `43 passed`
- `wctl run-pytest tests --maxfail=1` -> blocked by unrelated existing Geneva failure (`tests/nodb/mods/geneva/test_geneva_wp09_end_to_end.py::test_wp09_watershed_warning_thresholds_propagate_to_results_query_report[...]`, `KeyError: 'severity'`)

Residual risk:
- Package-scoped behavior is green in targeted tests, but full-repo gate remains blocked until the unrelated Geneva worktree failure is fixed.

## Context and Orientation

The failure path spans these modules:

- `/home/workdir/wepppy/wepppy/nodb/core/watershed_mixins.py`
  - `centroid` property currently returns nullable `_centroid` directly.
  - This is where a hardened accessor should live (for example `require_centroid()`).

- `/home/workdir/wepppy/wepppy/nodb/core/watershed.py`
  - `_peridot_post_abstract_watershed()` sets `_centroid`, summaries, and structure inside a lock and dumps state.
  - `post_abstract_watershed()` output is the canonical source for recalculating centroid from artifacts.

- `/home/workdir/wepppy/wepppy/topo/peridot/peridot_runner.py`
  - `post_abstract_watershed(wd)` reads watershed tabular outputs and computes centroid.

- `/home/workdir/wepppy/wepppy/nodb/base.py`
  - `NoDbBase.dump()` writes serialized state to `.nodb` and updates cached metadata.
  - This boundary currently lacks explicit stale-writer rejection.

- `/home/workdir/wepppy/wepppy/nodb/core/climate.py`
  - Climate build methods unpack `watershed.centroid` directly.

- `/home/workdir/wepppy/wepppy/nodb/core/climate_station_catalog_service.py`
  - Some methods guard `centroid is None`; others unpack directly and can still crash.

- `/home/workdir/wepppy/wepppy/rq/project_rq.py`
  - `abstract_watershed_rq()` runs abstraction and timestamps completion.
  - Add post-abstraction durability verification here so incomplete persisted state is caught before downstream jobs.

Observed incident reference:
- Run `immodest-quick` had watershed artifacts present and valid centroid derivable via `post_abstract_watershed()`, but persisted `watershed.nodb` retained `_centroid: null`, causing `build_climate_rq` failures.

## Plan of Work

Milestone 1 establishes a hardened centroid contract in watershed. Add a method that returns centroid or repairs it from canonical abstraction artifacts, then persists repaired state under lock. If repair is impossible, raise a typed `WatershedStateError` (or equivalent existing contract error type) with runid/context.

Milestone 2 migrates centroid consumers in climate and station services to the hardened accessor. Replace direct nullable unpack calls so climate execution never fails with raw `TypeError` for this class.

Milestone 3 adds stale-write protection at NoDb persistence boundary. Before writing, detect whether on-disk file changed relative to instance metadata (`_nodb_mtime`/`_nodb_size`); reject stale overwrite with typed error. Keep behavior explicit and non-silent.

Milestone 4 adds post-abstraction durability verification in `abstract_watershed_rq`. After abstraction, reload detached watershed and assert centroid durability. If missing, perform one bounded repair attempt; if still missing, fail job explicitly.

Milestone 5 adds tests and docs. Cover self-heal success, unrecoverable failure, stale-writer rejection, and queue durability check behavior. Update package docs and any relevant contract docs to document behavior and operator expectations.

## Concrete Steps

Working directory: `/home/workdir/wepppy`.

1. Add watershed hardened centroid accessor and typed error behavior.

    cd /home/workdir/wepppy
    rg -n "def centroid|_peridot_post_abstract_watershed|post_abstract_watershed" wepppy/nodb/core/watershed_mixins.py wepppy/nodb/core/watershed.py wepppy/topo/peridot/peridot_runner.py

2. Update climate and station call sites.

    cd /home/workdir/wepppy
    rg -n "watershed\.centroid" wepppy/nodb/core/climate.py wepppy/nodb/core/climate_station_catalog_service.py

3. Implement stale-write rejection at NoDb dump boundary.

    cd /home/workdir/wepppy
    rg -n "def dump\(|_nodb_mtime|_nodb_size" wepppy/nodb/base.py

4. Add RQ post-abstraction verification.

    cd /home/workdir/wepppy
    rg -n "def abstract_watershed_rq|build_climate_rq" wepppy/rq/project_rq.py

5. Add/update tests.

    cd /home/workdir/wepppy
    rg -n "watershed|climate|abstract_watershed_rq|NoDbBase|stale" tests

6. Run targeted and package-level validation.

    cd /home/workdir/wepppy
    wctl run-pytest tests/<targeted-modules>
    wctl run-pytest tests --maxfail=1
    wctl doc-lint --path docs/work-packages/20260422_watershed_centroid_persistence_hardening --path PROJECT_TRACKER.md

## Validation and Acceptance

Acceptance requires all of the following:

- Climate and station flows no longer emit raw nullable-unpack `TypeError` when centroid state is missing.
- When abstraction artifacts exist, centroid is repaired and persisted before use.
- When artifacts are not available/valid, typed state failure includes run context and is contract-compliant.
- Stale NoDb write attempts are rejected and covered by tests.
- `abstract_watershed_rq` detects missing persisted centroid and either repairs once or fails explicitly.
- Updated tests pass and documentation reflects new behavior.

## Idempotence and Recovery

Changes are additive and should be idempotent for repeated runs:

- Repair path should be safe to call repeatedly; if centroid already exists, no mutation is required.
- Stale-write rejection should prevent silent corruption; retry must occur by reloading fresh instance state.
- RQ durability verification should perform at most one repair attempt to avoid unbounded loops.

If a milestone partially fails, complete one boundary at a time (watershed contract, climate call sites, dump guard, RQ verification) and keep tests green after each boundary.

## Artifacts and Notes

Store execution evidence here:

- `docs/work-packages/20260422_watershed_centroid_persistence_hardening/artifacts/validation_summary.md`
- `docs/work-packages/20260422_watershed_centroid_persistence_hardening/artifacts/incident_repro_notes.md`

Capture concise evidence snippets for:

- incident-like failing baseline,
- post-change repaired climate execution,
- stale-write rejection behavior,
- updated failing-path error contract text.

## Interfaces and Dependencies

Expected interface outcomes:

- Watershed exposes a non-null centroid retrieval contract suitable for climate consumers (repair-or-typed-failure semantics).
- Climate and station services depend on hardened centroid interface rather than nullable field unpack.
- NoDb dump boundary rejects stale writes with explicit error.
- RQ abstraction orchestration validates persisted centroid durability before moving downstream.

## Revision Notes

- 2026-04-23 / Codex: Initial ExecPlan authored from incident analysis and requested hardening scope.
- 2026-04-23 / Codex: Marked milestones complete after implementation/testing; documented lock/cache hardening follow-ups required by stale-write enforcement and recorded external full-suite blocker evidence.
