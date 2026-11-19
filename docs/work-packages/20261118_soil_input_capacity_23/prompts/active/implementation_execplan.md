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
- [ ] Establish ADR/contracts and map every affected writer/consumer.
- [ ] Extend native limit, reader tests, real fixtures and release metadata.
- [ ] Complete native full suite, smoke/watchlist and paired output comparisons.
- [ ] Wire Python capacity selection through raw/prepared/channel/upload paths.
- [ ] Complete focused and full wctl gates, stub checks where applicable.
- [ ] Complete review artifacts and isolated real-project validation.
- [ ] Prepare eligible paired release, rollback instructions and final handoff.

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

Milestone 1 establishes ADR-0148, updates canonical soil/executable contracts,
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

WEPPpy tests use `wctl --project-dir /workdir/wepppy-soil-input-capacity-23
run-pytest <targets>`, then the full required suite. Use explicit project-dir for
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

Scaffold complete; implementation and acceptance gates remain pending. No
production behavior changed. Revision 2026-11-19 UTC: initial executable plan
created from authorized scope and completed capacity inventory.
