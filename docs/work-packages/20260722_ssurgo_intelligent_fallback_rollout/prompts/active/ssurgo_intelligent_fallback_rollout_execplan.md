# Execute SSURGO Intelligent Fallback M4 Rollout

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` current. Follow
`docs/prompt_templates/codex_exec_plans.md` when revising it.

## Purpose / Big Picture

After this package, gridded SSURGO builds retain source MUKEYs recovered by the
ordinary converter, select a locally similar already-built soil for eligible
remaining failures, and visibly use the present global donor otherwise. The
local RQ `plastic-bundling` job proves the same worker path used in normal runs.

## Progress

- [x] (2026-07-22 UTC) Scaffolded package, tracker, review artifacts, and plan.
- [x] (2026-07-22 UTC) Completed independent scaffold review and recorded
  accepted-pending findings; implementation is held pending M1 contracts.
- [x] M1: Implemented compatibility contract, native padded crop/WGS84
  geometry, canonical artifact publication, config binding, and all-valid
  status coverage. Adversarial and generated-output fixtures move to M3.
- [x] M2: Implemented vector selection, primary-only global fallback,
  selected-donor materialization, and additive provenance.
- [ ] M3: In progress — add generated-output/adversarial compatibility tests
  and validate the complete RQ contract.
- [x] M4: Ran `plastic-bundling` / `disturbed9002` through RQ and captured
  all-valid no-op evidence.
- [ ] M5: Complete code, QA, security review, finding disposition, and gates.

## Surprises & Discoveries

- Observation: local run `/wc1/runs/pl/plastic-bundling` records config
  `disturbed9002.cfg`.
  Evidence: the run's NoDb controller state has `_config: "disturbed9002.cfg"`.
  The RQ endpoint config token must still be confirmed through endpoint schema
  discovery before submitting the job.
- Observation: review found the documented RQ operation ID was wrong:
  `rq_engine_build_soils`, not `build_soils`; its POST requires the current
  resolved default body and terminal success is `finished`.
  Evidence: independent security/operations review, OPS-01.
- Observation: primary and added candidates are both eligible when valid;
  however, only valid primary outcomes calculate the global baseline.
  Evidence: independent code and QA reviews, CR-01 / CR-02 / QA-01.

## Decision Log

- Decision: Reuse `wepppy/rq/project_rq.py::build_soils_rq` as the sole worker
  boundary; do not add a new RQ task.
  Rationale: it already owns directory locking, status events, NoDb cache
  clearing, and `Soils.build()` invocation.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Candidate work is conditional on residual-invalid dominant
  hillslopes after primary conversion.
  Rationale: ADR-0025 requires all-valid runs to preserve current work/cost.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Agents may restart the local Docker Compose stack during M4.
  Rationale: the user explicitly granted this authority; it is limited to local
  development and does not authorize production-host changes.
  Date/Author: 2026-07-22 / user and Codex.
- Decision: Hold implementation until the high review findings have an
  implementation contract and deterministic verification.
  Rationale: candidate artifact provenance/atomicity, canonical source trust,
  primary-versus-added eligibility, and the RQ procedure are correctness
  boundaries, not post-implementation polish.
  Date/Author: 2026-07-22 / Codex, after independent review.

## Outcomes & Retrospective

M1/M2 are implemented and independently re-reviewed. The deployable py312
native artifact is refreshed and its provenance is committed in wepppyo3.
Focused native/WEPPpy/RQ-route acceptance is green. M4 remains held: closure
still requires adversarial/generated-output evidence, an RQ run, and complete
review disposition.

M3 now includes a real Parquet round-trip fixture for local fallback
provenance and referenced `.sol` output. M4 preflight found an idle healthy
local stack with no queued work. The operator supplied a short-lived scoped JWT,
which enabled the documented discovery, wrong-config non-mutation, submission,
polling, and output inspection sequence. The M4 all-valid no-op result passed;
see `artifacts/2026-07-22_rq_acceptance.md`. M3 adversarial/scoring coverage
and M5 review closure still hold the package release.

## Context and Orientation

`wepppy/nodb/core/soils.py::Soils._build_gridded()` converts MUKEYs from the
project raster, then currently assigns residual-invalid dominant MUKEYs to a
watershed-global valid donor. `wepppy/soils/ssurgo/fallback.py` is the
low-level categorical-support boundary. `build_soils_rq` locks the run soils
directory and calls `Soils.build()` in an RQ worker.

ADR-0025 and `wepppy/soils/ssurgo/fallback.md` are normative: ordinary source
recovery first; 2 km padded map only for affected runs; local radii 250 m,
500 m, 1 km, 2 km; at least three valid direct shallow-profile fields; pixel
support then numeric MUKEY ties; and global fallback when local evidence or
buildability is insufficient. The primary collection covers the project map;
the separate candidate collection covers added padded-map MUKEYs. Only selected
donors become final generated soils.

## Plan of Work

M1 writes the compatibility note before persistence code changes, then extends
the SSURGO fallback module with persisted padded-map creation and bounded
categorical support from WGS84 locations. `Soils._build_gridded()` must finish
primary build/raw dominant determination first, then skip candidate work when
no **dominant hillslope** is residual-invalid. An invalid non-dominant map
MUKEY is not a trigger. Add an all-valid and invalid-non-dominant fixture
proving no candidate-source open, crop, enumeration, or added build occurs and
that `candidate_preparation=not_attempted` is persisted with before/after
primary/final mappings and candidate-manifest state.

M1 defines one configured canonical gNATSGO 2025 source resolver. It accepts
no caller or NoDb source path, resolves to a regular readable file inside the
approved configured root, records a non-sensitive source identity/version, and
permits a source mount symlink only when its resolved file remains inside that
root. Candidate output symlinks are forbidden. The fixed active artifact is
`soils/ssurgo_candidate_mukey/active.json`; it names immutable versioned map
and metadata siblings under that directory. Reject traversal and symlink escape;
create same-directory temporary files, close/fsync, atomically replace each
sibling, checksum/validate the pair, then atomically replace the active manifest.
A failed publication preserves the preceding active pair. Source/version/bounds/
checksum mismatch makes candidates unavailable for that record and selects the
global path, never a stale crop. Keep source preparation, replacement, candidate build,
selected-donor materialization, and persistence under the existing soils root
lock. Add a normalized config-match precondition before the existing mutable
RQ operation; a wrong config produces its canonical non-mutating error.

M2 builds added candidate MUKEYs under the primary source/settings/defaults and
reuses primary outcomes. A valid primary-map MUKEY and a valid added MUKEY are
both eligible; collection origin never excludes a candidate. The global donor
is computed once from valid primary outcomes only and cannot be changed by
added candidates. It validates the stored first OM-valid horizon, direct values
only, all specified ranges, sand-plus-clay balance, at least three shared
fields, the exact prescribed scale/distance, first successful radius, support
tie, then numeric-MUKEY tie. It materializes only selected added donors and
records additive provenance. Any missing/corrupt candidate map, unavailable
candidate collection, profile-free source, no-comparable donor, or donor
materialization failure takes the existing global donor. A missing native
categorical dependency remains an explicit build error; a single nonbuildable
candidate is excluded so another valid candidate may win.

M3 adds unit, legacy-hydration, Parquet propagation, and hermetic generated-
output tests. The helper verifies raw assignment preservation, final mapping /
NoDb / Parquet agreement, a `.sol` for every final assignment, local-selection
provenance, and absence of unused added donors. Add failure injection for
materialization: no partial `.sol`, dangling final mapping, or published
Parquet provenance; global selection has `donor_materialization_failed`; a
clean retry is coherent. Cover primary and added donors, profile/range/texture/
scale/radius/support/tie matrix, disconnected locations for one MUKEY, corrupt
candidate collection, unavailable source, and missing native support. If RQ
enqueue/dependency code changes, update
`wepppy/rq/job-dependencies-catalog.md`, run `wctl check-rq-graph`, and inspect
the job tree. Run stub checks for changed public/stubbed surfaces.

M4 checks the local stack. Before any restart, record `wctl ps`, local active
jobs, and `wctl rq-info`; do not restart while an unrelated local mutation is
active unless the user explicitly accepts it, and never flush Redis DB9. Prefer
targeted service recreation. If a full user-authorized local restart is needed,
run `wctl down`, `wctl up -d`, wait for documented service health, verify
`rq-engine` and `rq-worker` connectivity/logs, and rediscover the API because
old tokens/jobs may be stale. Use the RQ API: inspect pipeline/readiness and
the `rq_engine_build_soils` schema/defaults/error catalog; obtain an authorized
local token; copy only the current resolved default fields into a JSON POST
body with `rq:enqueue`; submit `plastic-bundling` / `disturbed9002`; poll to
terminal `finished`; and inspect final NoDb, Parquet, and soil artifacts. Do
not call `Soils.build()` directly. Store only redacted/non-sensitive job IDs,
checksums/counts, and command summaries in artifacts.

M5 obtains independent code, QA, and security reviews. Code review covers
policy/path/locking/persistence; QA covers fixtures/RQ/generated output; and
security covers worker/run-tree boundaries. Each review records reviewer,
independent turn, scope/base commit SHA, evidence, and verification. The
append-only ledger records every finding ID, owner, disposition rationale,
implementation commit, and result. Closure requires zero unresolved
critical/high/medium findings; `accepted-pending` is unresolved and cannot
close the package.

## Concrete Steps

Run from `/home/workdir/wepppy`.

1. Baseline and implementation validation:

       wctl run-pytest <changed SSURGO tests> --maxfail=1
       wctl run-stubtest wepppy.nodb.core.soils
       wctl check-test-stubs
       python3 tools/check_broad_exceptions.py --enforce-changed --base-ref origin/master

2. If queue wiring changes:

       wctl check-rq-graph

   Regenerate the graph only if this intended change produces drift.

3. RQ proof after pipeline/readiness and error-catalog discovery, using the
   exact fields returned by the endpoint rather than invented payload keys:

       GET /rq-engine/api/runs/plastic-bundling/disturbed9002/pipeline
       GET /rq-engine/api/runs/plastic-bundling/disturbed9002/readiness
       GET /rq-engine/api/runs/plastic-bundling/disturbed9002/endpoints/rq_engine_build_soils/schema
       GET /rq-engine/api/runs/plastic-bundling/disturbed9002/endpoints/rq_engine_build_soils/defaults
       GET /rq-engine/api/runs/plastic-bundling/disturbed9002/endpoints/rq_engine_build_soils/errors
       POST /rq-engine/api/runs/plastic-bundling/disturbed9002/build-soils
       GET /rq-engine/api/jobstatus/<job_id>
       GET /rq-engine/api/jobinfo/<job_id>

   POST JSON contains the currently resolved required fields (including
   `initial_sat` and `sol_ver`) plus `rq:enqueue`; capture its correlation ID.
   Expected success is canonical JSON with `job_id`, followed by terminal
   `finished` and valid run artifacts. First prove a wrong normalized config
   returns the canonical non-mutating config-mismatch error; otherwise do not
   claim config-bound acceptance.

4. Final gates:

       wctl run-pytest tests --maxfail=1
       wctl doc-lint --path docs/work-packages/20260722_ssurgo_intelligent_fallback_rollout
       git diff --check origin/master

## Validation and Acceptance

The hermetic invalid fixture must prove recovery first, local vector selection
when eligible, primary and added donor eligibility, and global fallback for all
insufficient-evidence cases. The local RQ run must complete and prove all-valid
no-op behavior: no padded candidate artifact or added candidate collection.
NoDb, Parquet, and generated soil references must agree. Candidate selection
must read only the persisted, validated padded map. Reviews and disposition
must be complete.

## Idempotence and Recovery

Candidate map generation uses the root-containment and atomic-publish contract
in the fallback specification. Adversarial symlink, `..`, stale map, crop/write
failure, concurrent retry, source-path traversal, and source-identity mismatch
tests are mandatory. Candidate writes stay under the run soils directory and
use the existing RQ root lock. On an RQ failure, save job information, repair
code, and enqueue a new job; do not edit assignments directly. Rollback
disables local-vector selection, leaving ordinary recovery and global fallback
intact.

## Artifacts and Notes

Never commit local run contents, tokens, or raw SSURGO responses. Review
templates are in `artifacts/`; use them for non-sensitive validation evidence.

## Interfaces and Dependencies

Keep the raster primitive generic in `wepppyo3.raster_characteristics`:
categorical raster plus WGS84 point, radius, and exclusions returns supported
categories without national cell iteration. SSURGO source selection, candidate
building, profile scoring, and provenance belong in `wepppy/soils/ssurgo/`.
`Soils` orchestrates persistence; `build_soils_rq` remains the worker boundary.
No new dependency is authorized.

Updated 2026-07-22: M1/M2 implementation completed; independent re-review
allows advance to M3, while M4 remains held on its explicit acceptance evidence.
