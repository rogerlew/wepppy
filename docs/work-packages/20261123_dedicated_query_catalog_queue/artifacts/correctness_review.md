# Independent correctness review

Reviewed 2026-11-23 UTC against the dedicated queue contract on `feat/catalog-queue-wepp3`, based on `160fb12b1`. The scope includes refresh admission and execution, inventory, ordinary worker isolation, scheduler dispatch, pilot compatibility, first installation and rollback. [Routing contract](../../../schemas/query-engine-catalog-refresh-contract.md#dedicated-catalog-queue-on-wepp3) · [Separate security review](security_review.md)

## Findings and disposition

| Finding | Impact | Disposition |
| --- | --- | --- |
| Continuous inventory could occupy the sole worker for an entire fleet traversal while dirty projects waited. | Newly added or changed data could remain absent from query results. | Inventory now yields at completed directory boundaries when dirty work exists. Reconciliation gives refresh a turn before resuming that frontier. The singleton regression observed inventory, refresh, inventory, cycle completion and readable catalogs for three projects. A very large directory and an already active refresh can still delay a turn. |
| A single-queue RQ worker moves a job through its intermediate list between the ready queue and the started registry. | Lost-ledger bootstrap could initialize fresh accounting while an existing catalog job was in transit. | Bootstrap now watches and inspects ready and intermediate lists on all three origins alongside started, deferred and scheduled registries. The Redis regression moves the ID with LMOVE and checks that bootstrap refuses to create the ledger. |
| The previous release advertised `queue=default` in the configuration digest. | A test with an omitted queue field would miss the actual retained cursor namespace. | The compatibility test now derives the actual legacy digest, preserves the old cursor and rediscovers a filesystem receipt under the new digest. Legacy tickets and manifests have no new execution authority. |
| The existing admin panel estimates catalog capacity using default workers. | Its compatibility summary can disagree with dedicated admission. | The operator requested the page be left alone. The observation below documents this boundary. Use actual worker registrations and jobs for release acceptance. |

[Admission and worker claim](../../../../wepppy/rq/_query_catalog_admission.py) · [Inventory checkpoints](../../../../wepppy/rq/_query_catalog_inventory.py) · [Redis-backed regression tests](../../../../tests/rq/test_query_catalog_rq.py)

## Direct observations

An independent local run used Redis on a disposable loopback port, installed RQ 2.12.0, the actual `WepppyRqWorker` and a temporary managed project with a six-byte CSV. With zero dedicated workers the enqueue attempt returned `query_catalog_workers_unavailable` and preserved the receipt. With one compatible dedicated registration the job entered `query-catalog`. A real default worker in burst mode left it queued and the catalog absent. A dedicated worker's forked workhorse then finished the job, published `values.csv` with size 6 in `_query_engine/catalog.json`, and acknowledged the receipt. Dispatching the task loaded from the shipped scheduler YAML enqueued `inventory_query_catalog_rq` on the same queue. A second dedicated workhorse completed it. [Shipped scheduler configuration](../../../../docker/scheduled-tasks.yml) · [Worker](../../../../wepppy/rq/rq_worker.py)

Real worker births and the unchanged admin panel on the same RQ version produced the following results with no ready backlog or reservations.

| Live subscriptions | Panel report | Dedicated registry |
| --- | --- | --- |
| One default | One compatible, no observed blocker | Zero compatible |
| One catalog | Zero compatible, compatibility blocks admission | One compatible |
| One catalog and one mixed default/catalog | One compatible, no observed blocker | One compatible and one incompatible, admission blocked |

The default-worker row counts advertised configuration among default subscribers. The displayed denominator of seven is the global ledger ceiling. The deployed singleton admits one outstanding inventory or refresh reservation in total, regardless of additional default capacity. Pauses, ledger records, default-ready backlog and the configuration-specific scheduler summary retain separate meanings. For readiness, compare the producer's expected configuration with the exclusive wepp3 registration and check the actual job origin and project publication. [Existing admin panel](../../../../wepppy/rq/query_catalog_monitor.py)

## Release disposition

Code correctness review passes. The implementation retains the fork/archive service's exclusive FIFO subscription and permits overlap on separate RQ processes. Missing or incompatible consumers defer work. Failed claims and interrupted attempts retain the project receipt. First installation records the prior absence of the catalog service for rollback. Historical owned pilot manifests remain inspectable. The new pilot controller runs on wepp3 because its directory inode is client-specific. [Worker guide](../../../../docker/prod-worker-deploy-guide.md#wepp3-dedicated-workers) · [Pilot controller contract](../../../schemas/query-catalog-pilot-deployment-contract.md#dedicated-catalog-queue-amendment)

The independent local check establishes routing and file publication. Production acceptance requires the candidate's real default and dedicated registrations, peer-visible catalog contents for the canary and overlapping fork/archive execution on the actual storage. The pre-release sample recorded 7 of 12 default processes in catalog work with empty ready queues. Follow receipt age and arrival/service rates over time to evaluate the cost of reducing execution to one slot. Revisit the limit on wpc1 with measurements from that mount. [Production validation evidence and limits](production_acceptance.md)
