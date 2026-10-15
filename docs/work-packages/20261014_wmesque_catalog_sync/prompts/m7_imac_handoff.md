# M7 handoff: receiving deployment canary from the administrative iMac

Carry out the WMesque M7 receiving-deployment canary using the open-wepp-org
repository's governed deployment workflow. Keep this operationally simple.
M8 recurring synchronization is outside this task.

## Authority and working location

Discover the actual local checkouts on the iMac; do not assume forest's
`/workdir/` paths exist there. Read open-wepp-org `AGENTS.md`, `AGENTS_RIGHTS.md`,
`docs/work-packages/README.md`, the deployment roadmap, applicable ADRs, and
nearest instructions before editing. Read the WEPPpy active plan at
`docs/work-packages/20261014_wmesque_catalog_sync/prompts/active/wmesque_catalog_sync_execplan.md`.
Use or create the receiving repository's required work-package record and keep
both repositories' handoff status current.

This handoff does not establish live-change authorization. The prior grant
covered M6 on wepp1/wepp2/wepp3. Establish the operator's current M7 grant and
follow applicable live-change and independent-control gates. Complete concrete
configuration and validation preparation before requesting any missing final
approval; do not ask again for actions already covered by the current grant.
Do not create or switch Git branches without an explicit request.

The iMac is the documented management root of trust. Use the existing protected
Kubernetes context and verify its target before mutations. Read
`docs/operations/flux-gitops.md`, `docs/operations/dev-01.md`, and
`docs/operations/sops-age-secret-management.md`. Follow the current image build,
publication, immutable-digest promotion, and Flux reconciliation workflow.
Application build steps must not receive cluster-admin credentials. Do not
invent a forest-based administration path or copy management secrets there.
No Talos/node/control-plane change is required by this application milestone.

## Verified starting point

WEPPpy implementation: `c138a8bab`; deployed M6 candidate: `052019426`;
M6 evidence commit: `3b1fcacce`. Inspect current repository/image state rather
than downgrading an existing deployment to these historical references.
Read `docs/infrastructure/wmesque-operations.md`,
`docs/schemas/wmesque-catalog-contract.md`, and the M6 artifact
`docs/work-packages/20261014_wmesque_catalog_sync/artifacts/20261015_master_rollout.md`.

wepp.cloud is master; receivers may extend its catalog but may not override
master resources. Adoption of a local ID by master uses ordinary next-sync
behavior, with no ownership database or special migration machinery.
All initial deployments share one tailnet. Unconfigured clients use wepp.cloud.

The initial managed resource is `tenerife/136_MDT25_TF`, revision
`aa96d31fe8aff11778b84be268798c04295e0d3de758649ec6e666d854fee295`.
Its two-file release totals 37,493,165 bytes. The public manifest endpoint is
`https://wepp.cloud/webservices/wmesque2/catalog/manifest`.
M6 verified operator rsync/SSH access to `roger@wepp1:/geodata` over the tailnet,
with strict host verification. This is not a provisioned receiver credential.
No operator private key was copied into a task container. Actual receiver
credentials, known-host trust, and destination write access remain unverified.
Do not interpret this handoff as permission to modify master accounts or SSH
policy; obtain any additional master-side grant if provisioning requires it.

Only the Tenerife resource was published in M6. Other datasets remain legacy
resources. Remote NED VRT dependencies must be materialized before managed
publication; expanding the master catalog is not required for this canary.
The sync helper pulls the managed catalog, not a per-dataset selection flag.
Recheck the live inventory and transfer size before copying if master has grown.

## Execution sequence

1. Inspect live cluster health, image digests, WMesque service, task identities,
   mounts, NFS permissions, network policy, and active RQ jobs. Retain baseline
   configuration and rollback references. Static forest observations found
   read-only compute geodata mounts and a dry-run scheduler with a three-task
   readiness assertion; verify these against current state.
2. Prepare the smallest receiving configuration that supports a sync writer.
   Keep ordinary compute-worker geodata mounts read-only. Prove the actual
   writer's UID/GID, passwd/home, umask, NFS writes, SSH/rsync availability,
   tailnet route, credentials, and strict known-host verification. Use the
   repository's encrypted-secret and review procedures; never print secrets.
   Do not introduce a new queue, daemon, or broader privileges without evidence
   that the existing bounded arrangement cannot meet acceptance.
3. Deploy compatible code through the existing pinned-image/GitOps procedure.
   Preserve active jobs and existing service identities. Keep recurring sync
   disabled and default routing unchanged while validating the receiver.
4. Invoke one manual sync under the actual receiving task identity. Run dry-run
   first, then a real transfer. Verify manifests, file hashes, revision, and
   full raster readability. Repeat to prove convergence. Retain task/job IDs
   where RQ is used, and inspect actual artifacts rather than only job status.
5. Retrieve the resource through the receiving WMesque service and compare
   pixels, CRS, bounds, resolution, nodata, and revision with master. The M6
   bbox `[-16.65, 28.25, -16.60, 28.30]` at 30 m produced a 187 by 161 raster
   in EPSG:32628. Confirm local extensions survive. Use isolated fixtures for
   adoption/interruption checks; never publish a fake resource to live master.
6. Test an explicit ordered endpoint list: actual internal local service first,
   `https://wepp.cloud/webservices/wmesque2` second. Prove local success,
   missing-resource fallback, and simulated local outage fallback without
   disrupting unrelated users. Check actual endpoint/revision provenance and
   wrong-revision rejection. Only after these pass, promote local-first to the
   receiving deployment under the authorized scope.
7. Run the repository's validation, secret scans, manifest rendering, and
   required reviews. Retain live rollout and rollback evidence. Record the
   resulting image/config revisions, transfer source, non-secret identity and
   mount facts, artifact checks, and any limitations. Update the receiving
   roadmap/package and WEPPpy M7 plan/tracker, or provide an exact cross-repo
   handoff if one checkout is unavailable.

## Rollback and exit criteria

Restore wepp.cloud-only client routing and the previous image/configuration
through the canonical GitOps recovery procedure. Account for any active manual
sync before changing its writer configuration. Retain verified releases,
original datasets, and local extensions; do not delete data for rollback.
Local-only extensions still require explicit local access if remote-only routing
is restored. Test recovery without changing master production services.

M7 is complete when the real receiving task can copy and verify master data,
the local server serves that revision, catalog extension/adoption behavior is
validated safely, local-first retrieval and fallback work, and rollback evidence
is retained. Keep `WMESQUE_SYNC_ENABLED=false`. Do not enable unrelated scheduler
tasks, update scheduler readiness to activate recurrence, or declare M8 complete.
