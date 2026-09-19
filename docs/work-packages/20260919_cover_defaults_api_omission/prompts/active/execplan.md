# Correct cover-default and omitted-input propagation


This living ExecPlan follows `docs/prompt_templates/codex_exec_plans.md`.

## Purpose / Big Picture


Configured cover fractions must reach the actual multiple-overland-flow-element
(MOFE) management files. Submitting a WEPP request without kslast, the bottom
soil conductivity override, must not silently clear its saved value. Deliver
wired fixes with actual-file evidence, not a scaffold or surrogate. Compiler
identification/rejection and production rollout are excluded.

## Progress


- [x] (2026-09-19 UTC) Located both boundaries and drafted scope/contracts.
- [x] (2026-09-19 UTC) Two independent contract reviews passed; ancestor `acc192323` committed.
- [ ] Reproduce both failures; implement bounded fixes and direct regressions.
- [ ] Validate disposable Forest project, generated/prepared files, downloads and archive/restore.
- [ ] Run focused/broad gates, independent correctness review, and close docs.

## Surprises & Discoveries


Skipping unchanged defaults is unsafe after a writer failure: saved intent may
already equal defaults while output is incomplete. Retry must regenerate once
whenever defaults apply. The confirmed API bug is in the shared NoDb parser,
not JSON transport; other optional fields are not in this repair.

## Decision Log


2026-09-19, user/Codex: execute cover-default and API-omission fixes, defer WEPP
executable work. Preserve existing default precedence and explicit clearing
semantics; regenerate once per applicable default application for retry safety.
Use disposable validation data and never overwrite the user's source project.

## Outcomes & Retrospective


Scaffolded; no implementation or validation claim yet.

## Context and Orientation


`wepppy/nodb/core/landuse.py` applies configured defaults in
`Landuse.set_cover_defaults`, after normal builds and selected-hillslope edits.
It currently updates only summary overrides. `_build_multiple_ofe` can reuse
`domlc_mofe_d` (per-segment class assignments) and writes combined managements.
`wepppy/nodb/core/wepp_input_parser.py` currently substitutes an empty string
for omitted kslast, making omission indistinguishable from explicit clearing.
The existing API adapter `wepp_run_payload.py` calls this parser through
`Wepp.parse_inputs`, which owns the persistence lock.

## Plan of Work


Milestone 1 promotes the intended delta into the MOFE artifact contract and a
bounded WEPP run-input contract, with ADR-0070. Two independent read-only reviews
must approve before a standalone ancestor checkpoint commit and code edits.

Milestone 2 adds failing regressions in the existing MOFE and parser suites,
then regenerates once after applicable defaults and guards kslast parsing on
key presence. Preserve existing lock scopes and writer failure propagation.
Test default absence/empty/unmatched, initial build, selected edits, zero/one,
RAP, retry, single-OFE, omitted/explicit kslast encodings and durable reload.
Read real combined and prepared management/soil files; do not mock the failing
writer, parser or persistence boundary in the direct acceptance cases.

Milestone 3 uses the existing supported Forest fork workflow with source
equestrian-bonheur. Set validation-only configured defaults through locked NoDb
fixture setup, then invoke the normal default/build and API paths. Run the
existing 260803 executable unchanged. Inspect fresh results and all generated
and prepared inputs; verify omitted kslast retains 0.0001 through soil preparation.
Use normal browser/download and canonical archive/restore on the disposable
fork. Record exact revision, service identity, jobs, hashes and source preservation.

Milestone 4 completes focused and broad tests, docs lint and independent review;
close with the achieved validation level, not a production-resolution claim.

## Concrete Steps


From `/home/workdir/wepppy`, use `wctl run-pytest
tests/nodb/test_mofe_scenario_artifacts.py tests/nodb/test_wepp_input_parser.py
tests/microservices/test_rq_engine_wepp_routes.py --maxfail=1`, then
`wctl run-pytest tests --maxfail=1`. Run `wctl check-test-stubs`,
`git diff --check` and scoped `wctl doc-lint --path`. Read rq-agent-operator
instructions before live requests; use only supported fork/run/archive endpoints.

## Validation and Acceptance


Require parsed configured cover values in `landuse/hill_*.mofe.man` and
`wepp/runs/p*.man`, retained omitted kslast in freshly reloaded `wepp.nodb` and
prepared `p*.sol`, and correct explicit clear/set behavior. Require visible
failure and successful retry from already-saved defaults. Reuse existing
artifact inventory, job status and archive paths; no hidden diagnostics.
Forest actual-file evidence is required because earlier fixture checks missed
related propagation defects. Broad tests support but cannot replace that gate.

## Idempotence and Recovery


Default application regenerates from saved assignments even when values match.
Failed writers remain failed with diagnostics; retry the supported operation,
never hand-edit derived files. Restore only the disposable fork's own archive.
No production or original project mutation; preserve unrelated working changes.

## Artifacts and Notes


Keep concise evidence and reusable scripts in `artifacts/`, updating this plan
and tracker at each milestone. Canonical rules live outside this package.

## Interfaces and Dependencies


Reuse existing Management/WeppSoilUtil readers, NoDb locks, MOFE builder,
WEPP payload adapter, and archive/browser mechanisms. No signature changes,
dependencies, schema migrations or new runtime subsystems are planned.

Revision note: initial scaffold records exact authorized scope and retry correction.
