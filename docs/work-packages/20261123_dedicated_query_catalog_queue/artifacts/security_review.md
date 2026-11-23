# Dedicated catalog queue security review

The change moves maintenance with write access to production project storage onto the wepp3 NFS client. Security impact is high. This review covers the queue claim, storage identity, pilot, worker profile and release controls at `c0259be33341114dc13d6c0bcf602136b36c1e61` against baseline `160fb12b1`.

## Findings

| Severity | Finding and disposition |
| --- | --- |
| Medium, remediated in code | A mixed-queue subscriber could start after admission and take an already admitted job. Refresh and inventory now claim their ticket in a Redis transaction that watches the executing worker registration as well as the job and ledger. The claim requires a live heartbeat, no death marker, exclusive `query-catalog` subscription, matching advertised configuration, started status and an unused ticket. A refresh also verifies the admitted scope and path. See `wepppy/rq/_query_catalog_admission.py` and `wepppy/rq/query_catalog_rq.py`. |
| Low, resolved in operator contract | The optional owned-fixture pilot records a directory inode in its manifest and checks it again when authorizing a receipt and execution. Production wepp3 and wepp1/2 report different inode values for the same Rocket test directory. Register the pilot and perform path-validating controller operations from the same wepp3 NFS client as the worker. General managed refresh binds a namespace, relative scope and persisted incarnation. [Pilot operator contract](../../../schemas/query-catalog-pilot-deployment-contract.md) |

## Storage and authority

The wepp3 worker runs as numeric UID 1002 and GID 130. The catalog service needs write access at the configured Rocket roots and their canonical aliases so that admission on one client and publication on another refer to the same project. Its Compose service binds `/geodata` read-only and overlays the two explicit writable trees `/geodata/wc1` and `/geodata/weppcloud_runs`. The equivalent `/wc1` spelling stays writable. The fork/archive service retains its original mounts and exclusive FIFO consumer. Verify actual mount sources and effective flags in the candidate container when accepting these permissions. [wepp3 Compose](../../../../docker/docker-compose.prod.wepp3.yml)

The new worker shares the established worker trust boundary. Redis access authorizes job dispatch. The existing PostgreSQL commit-mode startup advertises its deployment identity. The service reuses the file-backed worker credentials and mounts no Docker socket. The code introduces no browser endpoint, dependency, shell command derived from a job argument, or external destination. Review assumes the existing deployment restricts Redis producers and host administrators. [Worker](../../../../wepppy/rq/rq_worker.py) · [Logging profiles](../../../../wepppy/observability/secret_profiles.py)

## Migration and recovery

Old and new producers share the admission ledger across the queue change. Outstanding legacy tickets count toward capacity and uncertain execution blocks subsequent admission. New bootstrap inspects ready and intermediate fetch lists and the started, scheduled and deferred registries across old and new origins. Missing evidence for a claimed and canceled job requires reconciliation. The durable filesystem receipt remains available to the new configuration's discovery cycle. The administrative pause requires an owned expiry during the rollout. Recheck ownership before release, preserve the ledger, and avoid flushing Redis. [Queue contract](../../../schemas/query-engine-catalog-refresh-contract.md#dedicated-catalog-queue-on-wepp3)

Each dedicated worker must register exclusively under the actual container hostname. Rollback uses the retained image and service counts to restore the previous fork worker and retire a newly introduced catalog service when its prior count was zero. For the transition back to legacy producers, pause catalog admission, settle new-queue executions and confirm that the old consumers rediscover outstanding receipts. Acceptance reads queue membership and heartbeats directly. The existing admin page's default-worker row cannot establish the dedicated consumer's health. [Deploy entry point](../../../../scripts/deploy-production.sh)

## Validation and residual risk

Nine independent `wctl run-pytest` cases passed on the frozen revision. Eight exercised mixed/dead/expired registrations after enqueue, both obsolete execution bindings, stale incarnation rejection, rediscovery of old receipts and alternation of inventory and refresh through one slot. Each used an isolated Redis 7.4.12 instance. The ninth exercised concurrent browser preparation, actual RQ publication, a stale dataset and SQL readback. Its private Unix-socket fixture covered both RQ and the HTTP authorization dependencies. The two evidence receipts are `51a1c09cb08e4c2f8b79c78850db0ffc` and `c6800a7da4e44a28960d16e1519c7ce9` under `.wctl-test-runs/`. Both report zero skips, a successful pytest exit and stable source/runtime. [Test module](../../../../tests/rq/test_query_catalog_rq.py)

The production acceptance operator observed all three clients contending correctly for the same POSIX record lock in turn. The scratch run also exercised read-only marker propagation, file fsync and replace, and matching managed scope and incarnation. The production mount options differ between wepp3 (NFSv3 soft) and wepp1/2 (NFSv4.2 hard). The available-client scratch check establishes current coherence. During a transport interruption, retain the receipt and reconcile the actual catalog bytes before any replay or acknowledgment. [Production evidence](production_acceptance.md)

One compatible process yields one shared inventory/refresh permit. A second explicitly configured compatible process can increase general admission up to the existing global ceiling. The release checks for one global registration. Under refresh contention the inventory worker checkpoints a bounded number of completed directories and yields the slot. A slow directory can still delay the next handoff. Capture actual publication readback, oldest receipt age and independent fork/archive completion under overlap. [Inventory worker](../../../../wepppy/rq/_query_catalog_inventory.py)

## Verdict

Implementation security review passes for `c0259be33`. Zero open medium or high findings. The deployment acceptance operator owns candidate mount/identity readback, source image verification, actual receipt publication and the independent archive canary. The gate for release acceptance remains open until those observations are recorded. [Package tracker](../tracker.md)
