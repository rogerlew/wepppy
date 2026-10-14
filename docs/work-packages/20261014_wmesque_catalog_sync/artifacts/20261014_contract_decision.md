# WMesque Contract Decision Checkpoint

Starting revision: `487791df31e7874f0f1f1275ac93d51f16655788`.

Operator explicitly authorized execution of M1–M5 and forest stack restarts.
Production rollout remains excluded. Normative delta: ordered opt-in v2 endpoints,
wepp.cloud default, additive immutable manifests, verified one-way sync, existing
scheduled RQ execution, and automatic adoption by master membership.

Authority: `docs/schemas/wmesque-catalog-contract.md`, catalog governance, ADR-0094.
Classification: intended additive behavior, not correction of existing semantics.
Compatibility: preserve v1, explicit endpoints, legacy retrieval, old catalog list,
and original data directories. New managed publication refuses mutable external
VRT sources until materialized; it does not disable legacy retrieval.

Security impact is high: paths, SSH/rsync, file publication, and RQ enqueueing.
Regression evidence will include real GDAL fixtures, path rejection, source
mutation/corruption, interruption, concurrency, automatic adoption, legacy clients,
and real forest RQ/scheduler and downstream readback. Two independent contract
reviews requested; findings and disposition recorded before implementation.

Inventory evidence: forest container UID 1000/GID 993. NLCD 2019 references local
Annual_NLCD_LndCov_2019_CU_C1V1.tif; NED 2024 references remote /vsicurl/ S3 sources.
No master export or Kubernetes writable access has been provisioned.

## Independent review disposition

Correctness reviewer approved after logical legacy catalog paths, contained
VRT-relative references, shared catalog locking, and canonical JSON were clarified.
Security reviewer approved after pre-GDAL dependency validation, shared lock, and
strict SSH host verification were specified. No unresolved medium/high contract
findings. These approvals do not replace implementation reviews.
