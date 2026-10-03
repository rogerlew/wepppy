# Milestone five forest acceptance

Date: 2026-10-03 UTC  
Environment: `forest` development deployment at `https://wc.bearhive.duckdns.org`

## Compatibility and regression plan

The first deployed real-workflow attempt found that project fork copied regular
Omni child NoDb files without rebasing their source-run paths. The stricter
project-config authority correctly rejected those children because their
persisted parent directory still named the source project.

The repair is a copy-time compatibility normalization, not a schema change.
Rebase the exact source working-directory and run-ID strings in regular copied
Omni scenario and contrast `.nodb` files. Do not follow or rewrite symlinks, do
not alter the source project, and do not clear the child controllers' batch
identity. Bind root and child paths through no-follow directory descriptors,
verify device/inode identity before each read and publication, preflight every
payload before publishing any rewrite, and include every published file in the
conflict-aware rollback.

Regression evidence must show that a copied child names the destination parent
and child working directory, retains its group identity, and leaves linked
shared controllers alone. A fresh deployed fork must then prepare and execute a
real Omni workflow under project-config authority. Validate its generated
artifact semantics, report rendering, public read-only access, and archive and
restore byte integrity. Existing fork tests and the full Python regression must
remain green.

## Deployment and initial observations

Forest restarted from revision `ccd94f671`. WEPPcloud, RQ Engine, Query Engine,
Browse, Download, D-Tale, and all three workers reported that exact revision and
healthy processes. The deployed PostgreSQL migration is `e7a1c9d204bf`.
`rogerlew@gmail.com` is the sole member of both `batch_runner` and `openet_ts`;
no internal-statement acceptance is recorded, so a signed OpenET request was
correctly denied with `internal_acknowledgment_required` and created no queue
job.

The retained M3 service/browser canary passed after restart, including live
membership removal and restoration, private-resource denial, declared-query
success, and anonymous public-grid access. The authenticated Profile axe scan
reported zero violations.

Three bounded Omni attempts supplied useful negative evidence. A legacy source
lacked the selected contrast output; another copied source lacked rerun inputs;
and the current prepared source reached execution but failed because the copied
child retained its source `wd` and `_parent_wd`. The latter is the compatibility
defect covered by the plan above. Final workflow, artifact, archive/restore,
staged rollout, and review evidence will be appended after remediation.

## Remediation and staged rollout

`project_rq_fork.prepare_fork_run` now inventories regular `.nodb` files below
copied Omni `scenarios` and `contrasts` trees without following symlinks. It
rebases the source working directory and run ID while preserving child group
identity. Root and child payloads are preflighted and accessed through retained,
root-anchored no-follow descriptors. Device/inode checks reject path swaps, and
publication identity is recorded before directory sync so a post-replace error
also rolls back. The focused fork suite passed 107 tests; the affected
authorization and service suite passed 601 tests. Frontend lint passed and all
113 suites / 922 tests passed. Changed-code broad-exception and test-stub gates
passed.

The executing candidate is ancestor `ccd94f671bf45726fbed840e72fb4543a8028fed`
plus an uncommitted reviewed worktree. The executing fork module SHA-256 is
`16b3d8648aef7e1118e8aa453b3f29f3ed5db3c2dc71a91d2213d8133421f22d`;
the feature-access form script SHA-256 is
`d859d9c512a8bb8c4dc638cb5007d3e541a674d9783ac6ace64a1b717794fe61`.
No production revision is claimed.

The automatic database backup
`weppcloud-20261003-011207.dump` is mode `0600`, 792,483 bytes, has SHA-256
`e8cb5cd08cf42cd784e72b06cd819ba2e64504c2d4018a7ad5d88c9bbf602fdb`,
and produced a readable 129-entry `pg_restore --list` catalog. It was restored
with `--exit-on-error` into disposable database
`m5_feature_access_restore_20261003`. Readback found migration
`e7a1c9d204bf`, 15 public tables, six active feature groups, two memberships,
12 retained access events and zero fabricated acceptances. The disposable
database and password file were removed by the command's exit trap.

To close the mixed-version finding, WEPPcloud was stopped before restarting
Browse, Query Engine, D-Tale, Download, RQ Engine, all three workers, and the
scheduler. Those consumers started between 01:37:46 and 01:37:55 UTC;
WEPPcloud started last at 01:38:07 UTC. The queues were idle before and after.
The post-stage M3 canary then passed private member access, anonymous and
removed-member denial, declared-query access, external-path denial, restored
membership, and public anonymous grid access. After final fork hardening, the
web service was stopped again. RQ Engine and the fork/archive worker were
restarted and checked ready first; the worker listened at 02:20:32 UTC and
WEPPcloud listened at 02:20:47 UTC. Fork job
`9f4ec0a5-0430-4865-8db6-34b7293b80e4` then copied `listless-fantasy` to
`feature-access-m5-staged` successfully. All 11 regular child NoDb files had
destination-bound paths, two shared-controller symlinks remained symlinks, and
no source path remained. A new anonymous contrast action returned HTTP 401
while the default, fork/archive and Omni queues remained at zero.

Rollback retains migration `e7a1c9d204bf`, membership and event history, and
the private-consumer containment floor. The executable emergency boundary is
`wctl stop weppcloud`, which stops new web admissions while consumers retain
the containment floor. Restore only reviewed admission-facing web code, then
start WEPPcloud after affected consumers report ready. Do not downgrade the
schema or restore a consumer older than containment revision `794c26c42`.

## Real workflow and generated artifacts

The supported fork API copied `listless-fantasy` to
`feature-access-m5-final2`; fork job
`a0df3208-acff-449d-93b1-f9105a82f2ee` finished. All 11 regular copied Omni
child controllers named `/wc1/runs/fe/feature-access-m5-final2` as their parent
and destination prefix. Shared-controller symlinks were not rewritten.

A stream-order dry run for `sbs_map` to `undisturbed` returned eight items:
seven `needs_run` and one `skipped`. Job
`c5d85719-eeaf-42db-afc9-97067ce263ea` ran through the existing Dev/Root legacy
entitlement for Omni Contrasts. Seven child contrast jobs and finalizer
`1965b03f-a5b2-4156-9a4f-9df58ff9f36e` finished; the empty group remained
skipped. Each `contrast_*.tsv` contains 68 destination-bound hillslope rows.
The seven status files say `completed`, and the retained skipped item has no
invented completion record. The authenticated report returned HTTP 200 and
rendered outlet water-discharge and soil-loss metrics for the generated groups.

No OpenET or Batch call was made. Those groups still contain only
`rogerlew@gmail.com`, and the account has no `internal-2026-10-01`
acknowledgment. This correctly prevents actions until the user personally
accepts the statement. An earlier signed OpenET attempt returned 403
`internal_acknowledgment_required` with no queue change.

## Public read-only sharing and archive/restore

The project was made public through the authenticated, CSRF-protected
`tasks/set_public` endpoint. A new anonymous browser completed the existing CAP
challenge and rendered the contrast report with the generated values. An
anonymous contrast execution request returned 401 and the queue counts did not
change. This demonstrates public inspection without public execution.

Archive job `83c0e48a-00e5-4dcd-931f-41fa55185cd2` produced
`feature-access-m5-final2.20261003T015155Z.zip`, 561,890,150 bytes, SHA-256
`e6978d8f57fe717bfabe07868cbab071e21bf4e9a5dda6610716f66f895af5ff`.
An anonymous range request returned HTTP 206 and ZIP magic `504b0304`.
Restore job `ae901416-112e-438a-8d6f-34d6eeeda62f` finished through the
supported endpoint. SHA-256 manifests for every retained contrast TSV and
status JSON were byte-identical before and after restore. The `PUBLIC` marker
survived, and the project and contrast report remained available under the
same CAP-gated public read policy.

## Final validation and review repairs

The feature-access form now requires a valid JSON success body with a nonempty
message before displaying success. Focused Jest coverage proves non-JSON HTTP
200 and 500 responses both remain errors and do not expose the refresh action;
a valid JSON success retains the intended message. Frontend lint passed and the
complete frontend run passed 113 suites / 922 tests.

The descriptor-bound fork regression suite passed 107 tests, including final
entry and directory swaps, rollback across root and nested child rewrites, and
a forced directory-sync failure after publication. Changed-code broad-exception
enforcement, test-stub validation, Python compilation, documentation lint and
diff whitespace checks passed. The first complete Python regression attempt
stopped after 3,598 passes and 51 skips on one unrelated stale test-only NoDb
lock. The exact failed parameter passed alone; the two lock keys both named the
same dead test-process owner and were removed. The clean complete rerun then
exited successfully. Its terminal summary was lost after the PTY output exceeded
the capture limit, so no inferred pass count is recorded. Independent review
disposition is recorded in the companion final-review artifact.

## Remaining environment limits

Forest is environment validated and deployed at this worktree candidate.
Forest1 and production were not authorized or changed. Positive Culvert client
compatibility remains blocked by the separately expired wepp2 operation
credential. Positive OpenET and Batch actions remain intentionally pending the
designated user's personal acknowledgment and the existing API/compute limits.
Neither limitation weakens the deployed denial and sharing evidence above.
