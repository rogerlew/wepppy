# Legacy fork/archive role finding and deferred proposal

Operator disposition (2026-10-27 UTC): “i don’t care about the read only mount.”
Treat this preexisting mount/workflow limitation as outside the catalog release
scope, not a catalog-rollout blocker. No routing or mount change is authorized
or implemented by this disposition. Preserve the proposal below for a separate
request; catalog inventory and refresh still include the legacy namespace.
The actual external catalog guard passed under the existing role.

Actual uid1002/gid130 in wepp3's fork/archive container reads the same scratch
anchor created by wepp1 under the legacy mount. The shared external catalog
guard passes. The next actual `project_config_lifecycle_guard` fails with
`EROFS` opening an already-existing `.config-amendment.lock`. No real project
was modified. [Probe](20261027_legacy_role_probe.json). Archive creation additionally
writes `archives/` under the source; restore also requires source writes.

Current fork/archive/restore submissions all select `fork-archive`, whose only
observed consumer is wepp3. The failure predates this remediation: neither
thread offload nor inventory changes alter the project-config guard or mount.
It is a role/workflow compatibility failure, not failure of catalog exclusion.

Deferred bounded resolution, requiring separate scope approval and contract review:
route only physically resolved legacy-source fork/archive/restore jobs to the
existing writable `batch` pool on wepp1/wepp2. Keep primary-root jobs on
`fork-archive`. Preserve job functions, IDs, authorization and response schemas.
No new queue, consumer, service, mount or permission. Update duplicate/active
operation detection and target-mutation/cancellation policy for both permitted
origins; do not merely replace three Queue calls. Validate actual guarded
fork/archive/restore on an owned legacy scratch project with existing identities.

Independent routing review additionally requires `rq/cancel_job.py` and
`rq/fork_failure.py`: origin-only checks otherwise weaken started-job cancellation
protection and lose prerequisite failure reporting for batch-origin forks.
Preserve queued-only cancellation for ordinary callers on the three exact
legacy task functions; do not restrict unrelated batch work.

Implementation boundary: rq_engine/fork_archive_routes.py, rq/cancel_job.py,
rq/fork_failure.py, affected canonical
fork/archive/response contracts, dependency catalog and focused route/job-policy
tests. This is outside the approved catalog-inventory checkpoint and requires
its own reviewed ancestor before implementation. Alternative: keep the specific
legacy workflow gate open and handle routing in a separate work package.
Changing wepp3 mount permissions is not proposed.
