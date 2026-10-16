# WMesque Catalog Governance

> Canonical policy for catalog authority, deployment extensions, and synchronization.

## Status and Scope

Adopted 2026-10-14. This document establishes governance; it does not implement
catalog versioning, endpoint failover, or scheduled synchronization. The initial
participants are wepp.cloud and the deployment maintained at
`/workdir/open-wepp-org/`.
Implementation interfaces and operator procedures are maintained in the
[catalog contract](../schemas/wmesque-catalog-contract.md) and
[operations guide](wmesque-operations.md).

## Catalog Authority and Extensions

- **wepp.cloud is the master catalog and publication authority.** Other
  deployments consume its published resources through one-way synchronization.
- Other deployments may extend the catalog and serve a superset of wepp.cloud's
  resources. Extensions must use distinct identifiers and must not override,
  shadow, or redefine resources in the master catalog.
- A shared identifier must refer to the authoritative resource and revision
  published by wepp.cloud. Local modifications require a distinct extension
  identifier; matching names alone do not establish matching data.
- Resources absent from the master catalog are local extensions and must be
  preserved by synchronization. Resources present in the master catalog are
  master-managed; catalog membership determines ownership.
- Local extensions do not flow upstream automatically. Adoption into the master
  catalog requires an explicit publication decision on wepp.cloud.
- When wepp.cloud adopts a local extension under its existing identifier, the
  receiving deployment automatically transitions it to ordinary master
  synchronization on the next scheduled sync. Keep the identifier and consumer
  references unchanged; no rename, local approval, or separate migration workflow
  is required. The verified master copy becomes authoritative through the normal
  sync publication process, even when the previous local contents differ.
- Operators coordinate identifier meaning when publishing to wepp.cloud. Do not
  introduce runtime conflict arbitration or a separate ownership registry for
  adoption; master catalog membership is the governing rule.

## Revision and Consistency Policy

- Dataset identity must distinguish the logical identifier from its published
  data revision. WMesque API versions and deployment versions do not identify
  dataset contents.
- Replicas may lag the master while synchronization is pending or failing, but
  must identify the revision they actually serve. They must not claim to have
  the current master revision until its data and metadata have been verified.
- A request for a specific revision must not silently receive another revision,
  including during priority-based endpoint failover.
- Synchronization must stage and verify a complete resource revision before
  making it available. An incomplete transfer must not replace the last verified
  published revision.
- Existing datasets on both deployments must be reconciled before being declared
  equivalent. A catalog path or VRT filename alone is insufficient evidence.

The concrete revision format, integrity manifest, historical revision retention,
project pinning, and migration of existing resources remain implementation design
work. This policy does not authorize automatic deletion of historical resources.

## Deployment Endpoint Defaults

Deployments without explicit endpoint configuration must continue to retrieve
from wepp.cloud. Local-first routing requires an explicitly configured ordered
server list; installing a local WMesque service must not change routing by itself.
This preserves existing behavior while allowing each deployment to opt into
local service and priority failover independently of synchronization scheduling.

## Scheduled Synchronization

- For the initial implementation, assume all deployments participate in the same
  tailnet. Use that private network for master-to-receiver synchronization;
  cross-tailnet and public bulk-transfer support are out of scope for now.
  This keeps transfer design bounded without changing public retrieval defaults.
  Actual task connectivity and source/destination permissions still require
  deployment validation; tailnet membership alone does not establish them.
- Non-wepp.cloud deployments may run cron-style scheduled RQ tasks to pull
  changes from wepp.cloud. Scheduling and execution belong to the receiving
  deployment; wepp.cloud remains the publication source. An existing dedicated
  receiver may instead schedule the same sync CLI with its host timer. For
  openwepp, the operator approved the existing hpc writer's daily systemd timer
  on 2026-10-16, preserving read-only Kubernetes geodata rather than adding a
  writable RQ worker solely for scheduling.
- Synchronization must be repeatable and prevent overlapping publication of the
  same resource. Failed attempts must leave previously verified resources usable
  and report failures explicitly. Adoption of a local extension is normal
  synchronization, not a conflict or failure.
- Operators must be able to inspect the last successful synchronization,
  published revisions, pending changes, and failures. Job success alone does not
  prove that the resulting catalog and raster artifacts are valid.
- Schedule frequency, transport, queue placement, retry limits, and artifact
  validation procedures will be defined during implementation using the existing
  deployment and RQ conventions.

## Decision Rationale

A single publication authority avoids divergent meanings for shared dataset
identifiers while allowing deployments to add regional or experimental resources.
One-way scheduled pulls permit asynchronous replication without introducing
multi-master reconciliation. Catalog extensions provide flexibility without
allowing independently modified copies to masquerade as the same resource.
Adoption uses the same synchronization path as subsequent updates, avoiding
special cutover states and manual collision handling. Semantic coordination
belongs to publication governance; transfer verification remains part of normal
synchronization. Prefer this simple ownership rule over speculative conflict
machinery.

## Related References

- [Dataset sync inventory](wmesque-dataset-sync-manifest.md)
- [Generated-artifact validation](../standards/generated-artifact-validation-standard.md)
- [RQ response contract](../schemas/rq-response-contract.md)
- [Implementation and rollout assessment](wmesque-implementation-assessment.md)
