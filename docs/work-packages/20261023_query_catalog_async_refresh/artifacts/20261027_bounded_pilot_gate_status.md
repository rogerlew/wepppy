# Bounded pilot gate status

Current disposition (2026-10-27): **bounded execution PASS; general enablement HOLD**.
Full canonical deployment of `0da9c9071` and actual shared-batch execution are
complete. The active-job deployment hold below is historical. All local gates
remain passed; deployed source/configuration, genuine worker lineage, both
artifact waves, pause/resume, budgets and scratch retirement now pass.
[Acceptance](20261027_shared_pilot_acceptance.md) retains the exact limits;
[results](20261027_shared_pilot/summary.json) retain sanitized evidence.
Whole-fleet capacity and new-arrival delay are not established.

## Historical pre-deployment checkpoint

Current operator decision (2026-10-27 UTC): remain on standby and use the full canonical deployment after default and batch jobs clear. No active-job exception is approved or implemented. The scoped batch candidate remains retained evidence, not the selected rollout path. Deployment and actual pilot execution remain pending; general asynchronous refresh stays disabled.
The operator authorized implementation and an actual pilot on the existing batch
queue. General asynchronous refresh remains disabled. This file does not claim
that the shared production pilot has executed.

| Gate | Evidence | State |
| --- | --- | --- |
| Contract before implementation | checkpoint `5c1edb22a`, independent contract reviews | PASS |
| RQ admission/inventory/worker boundaries | `pilot-rq-final-tests.log`: 72 final tests | PASS |
| Controller and artifact-before-consumer acceptance | `pilot-operator-tests.log`: 24 tests | PASS |
| Canonical batch deployment | independent 56-test deployment/helper run; exact 813d backport checks | PASS |
| Independent correctness | RQ, controller and deployment review artifacts | PASS |
| Independent security | `20261027_pilot_implementation_security_review.md`: 86 RQ/disclosure plus 80 operator/deployment checks; cancellation repro closed | PASS |
| Final source-only image mechanism | `20261027_source_image_final_build.json`; native/dependency/configuration/source metadata parity | PASS locally; each production image pending |
| Queue graph, stubs, exception boundaries, docs | retained logs and scoped checks | PASS |
| Broad regression | `20261027_pilot_broad_regression.log`: 11,862 passed, 201 skipped in 54m14s; final RQ changes separately validated | PASS, segmented source evidence |
| Production active-job preflight | one live default watershed job; eight idle batch workers | BLOCKED |
| Actual source installation and worker cutover | no production source/image/service mutation | NOT STARTED |
| Eight-scope shared-batch pilot and excluded sentinel | final CLI/manifest ready | NOT STARTED |

## Source and recovery

The prepared patch is bound by
`20261027_pilot_production_candidate_manifest.json`, with per-host image manifests.
It backports only the approved five application files and two deployment files
onto `813d912be1c8f6f13b6fc60cecebbef9259cd36e`. Production remains on that clean
baseline. Unrelated current-HEAD source and dependency changes are excluded.

The final cancellation fix was made after broad-test collection. Its final-source
72-test RQ gate and independent 86-test security gate are retained separately;
a broad pass must not be described as a single final-source run. The earlier
collection attempt stopped on duplicate test basenames; renaming the new CLI
test resolved that test-harness collision.

Follow the canonical active-job gate and recovery order in
`20261027_pilot_deployment_preparation.md`. The existing watershed job is not a
pilot fixture and must not be canceled or stopped to clear this gate. The
preexisting legacy read-only mount limitation is outside scope and is not a blocker.

## Final local gate and production hold

The broad run completed successfully. Each production host was rechecked at
clean tracked revision `813d912be1c8f6f13b6fc60cecebbef9259cd36e`.
The latest raw active-job check still finds the same default watershed job,
started 2026-10-26 at 18:31:16 UTC, with a fresh 2026-10-27 at 04:30:22 UTC heartbeat;
batch has no started jobs. No pilot source or image has been installed.

The current operator skill and canonical script require an empty default/batch
started set. Proceeding during this job requires an explicit operator decision
on a narrow one-job exception; none is implemented or assumed by this evidence.
The reviewed batch-only path preserves the default worker/container. General
asynchronous refresh remains disabled and actual pilot acceptance remains open.
