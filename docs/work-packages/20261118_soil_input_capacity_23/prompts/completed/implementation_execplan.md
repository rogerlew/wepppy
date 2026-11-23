# Implement and validate 23 soil input horizons

This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.
Maintain Progress, Surprises & Discoveries, Decision Log and Outcomes throughout.

## Purpose / Big Picture

A project with ten SSURGO horizons currently fails when the required 200 mm
split creates eleven. The national source needs up to twenty-one generated
horizons. Allow selected compatible executables to read up to twenty-three
source records while keeping the ten-layer calculation storage and existing
physics. An isolated original project must produce correct generated inputs
and complete model outputs. Prepare a paired Linux release and rollout with
honest separation of validation, integration and production recovery.

## Progress

- [x] (2026-11-19 UTC) Read repository/release instructions and prior evidence.
- [x] Scaffold package and dedicated implementation worktrees.
- [x] Establish ADR/contracts and map every affected writer/consumer.
- [x] Extend native limit, reader tests, real fixtures and release metadata.
- [x] Complete native full suite, smoke/watchlist and paired output comparisons.
- [x] Wire Python capacity selection through raw/prepared/channel/upload paths.
- [x] Complete focused checks, reconciled segmented broad coverage and stub gates.
- [x] Complete independent review artifacts and isolated real-project validation.
- [x] Prepare paired Linux release and rollback instructions.
- [x] Final segmented-coverage receipts, independent assessment and source/evidence handoff.

## Surprises & Discoveries

The shared checkouts have unrelated WIP. Native default is
`wepp_260430_negmeltfix_comparator`, not `kernelized-abandoned`. Existing native
release rules require default-branch lineage before ordinary vendoring. The
larger delicate_game fixture lacks routing inputs; use the committed complete
physical_water fixture for watershed tests. Native exit zero can accompany an
incomplete run, so check success markers and semantic artifacts.

## Decision Log

2026-11-19 UTC, operator/Codex: implement twenty-three input horizons, based on
the full national inventory, with twenty-three being raw maximum twenty-two
plus one split. Reject global mxnsl increase and horizon merging to preserve
calculation/output layouts and physical formulas. Do not silently change saved
binary selections or defaults. Implement on task branches and retain acceptance
and remote integration as separate claims.

## Context and Orientation

WEPPpy implementation root: `/workdir/wepppy-soil-input-capacity-23`, branch
`feat/soil-input-capacity-23`, based on evaluation evidence commit `d228fe0a5`.
Native root: `/workdir/wepp-forest-soil-input-capacity-23`, same task branch,
based on native prototype plus watershed evaluator `530ffb2be`. Native
`src/input.for` already separates local input arrays/depths from shared
calculation storage, but the experiment permits only eleven. Tests execute the
real reader with bounds checks and inspect all calculation-layer properties.
WEPPpy `wepppy/wepp/soils/horizon_boundary.py` currently hardcodes ten; its
consumers include SSURGO, other dataset writers, general soil utilities, multi-
OFE assembly, roads and channel generation. `wepp_runner` reads adjacent JSON
release metadata and resolves matched hill/watershed binaries. NoDb Wepp stores
the selected binary; Soils builds the raw files used by later preparation.

## Plan of Work

Milestone 1 establishes ADR-0150, updates canonical soil/executable contracts,
and records a file-level consumer matrix. Trace capacity from saved binary to
both serialization and execution, including process boundaries and uploaded
copy paths. Prefer explicit existing interfaces; unknown historical binaries
retain ten and invalid declarations fail without silently substituting a build.

Milestone 2 changes only native input capacity to twenty-three and extends
actual-reader tests for 21/22/23, rejects 24, and checks mixed OFEs. Commit the
national Puaulu fixture and validate its properties after aggregation. Extend
the sidecar generator with the integer capacity and exercise metadata validation.
Build with pinned system compiler, preserving matched role artifacts, run all
mandatory native gates and old-input parity, then retain hashes and logs.

Milestone 3 implements Python capacity resolution and propagation at existing
writer/preparation boundaries, plus a final consumer check so switching to an
old executable cannot silently truncate previously built soils. Keep normalizer
property-copying/idempotence and uploaded-file byte preservation. Test old,
new, missing, malformed and mismatched declarations; generated raw, Disturbed,
multi-OFE, channel and uploaded paths; and no overwrite after rejected input.
Use full real writer serialization, not mock-only assertions.

Milestone 4 validates a matched binary pair using canonical provenance/smoke
checks and source-lineage release requirements. Run focused tests followed by
`wctl run-pytest tests --maxfail=1` from the explicit task project. Review all
findings. Use an isolated actual-run copy with separate filesystem and Redis
identity, candidate code and matched binaries under production-equivalent
runtime identities/mounts. Read raw/prepared/consumed artifacts and fresh outputs.
Prepare canonical release activation and retained-version rollback instructions;
do not claim original production incident repaired from a disposable replay.

## Concrete Steps

Use `/usr/bin/gfortran` and `PATH=/usr/bin:/bin:$PATH` for native build/tests.
Build watershed and hill roles sequentially, then restore watershed includes.
Run `python -m pytest tests/test_native_soil_input_capacity.py`, both host smoke
gates, `python tools/run_hillslope_watchlist.py`, ablation policy and full pytest.
Retain paired runs of committed physical_water and Puaulu cases with fresh PASS
files; verify actual completion and finite complete channel records.

WEPPpy tests use `wctl run-pytest --checkout /workdir/wepppy-soil-input-capacity-23
--runtime-root /workdir/wepppy <parser options> -- <targets>`, then the full required suite. Use explicit project-dir for
doc lint too; the installed wrapper otherwise targets the shared checkout.
Read `wepp_runner/AGENTS.md`, `wepppy/nodb/AGENTS.md`, `tests/AGENTS.md` and
nearest local instructions before edits. Record exact commands/results in the
package as implementation establishes the concrete interfaces.

## Validation and Acceptance

For compatible binaries, Puaulu's twenty-one records and original Zepol's eleven
must be serialized and consumed intact. Count twenty-three must succeed and
twenty-four must fail explicitly. Old inputs preserve baseline output. Old or
unknown binaries reject oversized inputs before native invocation. New metadata
must match both binary roles and existing source/digest validation. Failures
must preserve prior generated files and never mutate uploaded source bytes.
Only direct generated-artifact evidence and complete native output satisfy the
workflow gate; suite success and RQ completion are supplementary signals.

## Idempotence and Recovery

Work only in task checkouts and fresh evidence directories. Do not overwrite
existing release tags, production runs, or shared WIP. Source acquisition and
run-copy commands must be read-only at origin. Validate isolated identities
before execution. Preserve prior binary pair and selection for rollback; never
mix role builds or generated passes. Retry failed diagnostic runs in new output
paths and retain failure evidence. Canonical deployment governance governs any
later activation; do not invent an alternate image or compose workflow.

## Interfaces and Dependencies

Reuse the existing JSON release sidecar, strict paired capability resolver and
canonical generated-soil normalizer. Introduce an integer soil-input capacity
feature and keyword propagation only where required by confirmed consumers.
No dependency or persisted NoDb schema migration is needed; capability derives
from installed selected executables. Record concrete APIs after consumer audit.

## Artifacts and Notes

Retain ADR/contracts, consumer matrix, source and binary identities, actual
soils, targeted/full gate logs, native state and output comparisons, isolated
workflow receipts and review artifacts. Closed evaluation history is immutable.

## Outcomes & Retrospective

Completed 2026-11-19 UTC. Native input capacity is 23 with calculation capacity 10
and unchanged physics. Matched final Linux pair is locally vendored; defaults
and saved project selections remain unchanged. No production deployment or
original-project recovery occurred.

Native full suite 1824 passed, reader 72, metadata 14, watchlist 31; legacy reader
states 80/80 exact. Twenty native watershed executions completed with legacy
control output bytes identical. Disturbed matrix/locale authority 186 passed;
768 native output files match the previous reviewed results.

The operator approved nearest CLIGEN station for the disposable clone. ALCALDE
NM supplied 100 years. All 355 hillslopes and 144 channels completed; canonical
post-jobs and frontend report readers passed. Readback verified 5,259,456 finite
channel daily records against all 36,524 climate days. See project-replay.md for
identity/cache setup, development-runtime limitations and the repaired manual
post-processing omission. Original project remained unchanged.

Independent correctness review identified three omitted derivative consumers:
Treatments, shared location modifiers, and AgFields parent synthesis. All now
forward selected capacity. Real 21-horizon Puaulu regressions pass through each.
Correctness and security reviews pass with no unresolved findings.

Broad validation completed in segments, with independent acceptance of exact
coverage reconciliation: 14,554 passes, 505 runtime skips, one collection skip and
99 opt-in deselections. Earlier full sweeps exposed detached test fixtures;
the remainder exposed a Roads stale-evidence review and an import smoke script
writing a tracked example. Repairs passed focused canonical checks with stable
source. Preserve the failed and source_changed receipts: this is not a single
uninterrupted green sweep, and cross-segment ordering was not re-exercised.
Production hashes match independent reviews. See validation.json and the broad
gate assessment for denominators and source identities.

Six-module stubtest, test-stub completeness, changed broad-exception enforcement
and documentation lint passed. Durable contracts are ADR-0150, the soil boundary
contract and executable selection contract. The user help and binary lifecycle
ledger explain the opt-in release; rollout retains the compatible pair whenever
larger inputs exist.

Tooling lessons: wctl doc commands need explicit --project-dir for task
worktrees; otherwise the installed preset can lint the wrong checkout. The
import diagnostic must exclude known executable management utilities, which
change cwd and write at import time. Review only the bounded fixture changes;
no claim that every diagnostic import succeeds is supported by that test.
