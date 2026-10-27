# Bounded pilot contract correctness review

Independent reviewer: `roads_contract_review`. Date: 2026-10-27 UTC.
Disposition: **PASS after verified C1 correction**. No unresolved correctness
contract findings. This approves the intended contract for its checkpoint, not
implementation conformance or production cutover.

## Finding

**C1 (resolved): host source patch plus `--skip-build` could not install the
candidate in the observed batch containers.** The original draft mandated
existing-image recreation after host-only patching. Actual read-only Docker
mount inspection found no `/workdir` mounts in wepp1's batch container and only
the Discord secret under `/workdir` on wepp2; neither mounts the repository.
The imported RQ module resolves to
`/workdir/wepppy/wepppy/rq/query_catalog_rq.py`, inside the image filesystem.
Baseline `docker/Dockerfile` copies repository source into that image. Therefore
recreating the retained image would launch the old implementation and fail genuine
candidate capability/readback acceptance. No registration override can fix this.

Independent readback confirms the canonical deployment contract, ADR and decision
now require a scoped task-only candidate image build, pinned/verified existing
native and dependency inputs, exact built-image imports/readback before cutover,
and an owned old-image rollback reference. Unexplained drift blocks cutover.
The original skip-build activation claim is removed. This resolves C1 at the
contract level; actual build parity remains an implementation/operations gate.

Final refinement reviewed: the canonical target now derives its source-only
image from each host's exact retained local batch image, with no network,
installer, vendor checkout or native rebuild. Only the five decision-listed
Python files, their stale derived bytecode and retained overlay provenance may
differ. Strict manifest destinations/hashes and preserved runtime configuration
make the activation mechanism concrete while retaining measured dependencies.
This satisfies C1 without relying on mutable baseline build inputs. No new
correctness finding arises from this refinement.

[Runtime baseline evidence](20261027_pilot_runtime_baseline_provenance.json)
records distinct host image IDs, matching 307-distribution fingerprints and nine
matching native extension hashes. Baseline Docker inputs include mutable image
tags, apt repositories and vendor branch refs; an unchanged Dockerfile/no-cache
rebuild alone cannot satisfy the new parity requirement. Runtime vendor Git
metadata was intentionally removed by the baseline image build, so unavailable
vendor revisions must not be invented.

## Otherwise accepted correctness and authority

The disabled-mode exception is explicit and bounded by an operator manifest,
exact owned fixture identity and admitted job binding. Ordinary disabled producers
and scheduler behavior remain unchanged. Inventory seeds are restricted to
approved locators and cannot consume ordinary dirty indexes or unlisted nested
scopes. Scientific outputs, filesystem protocol and public response shapes remain
unchanged.

Queue-wide atomic permits and retry-inclusive budgets cover configurations and
pilot generations; coalescing cannot spend additional quota, and worker loss
cannot free uncertain reservations. The 25-refresh/two-inventory cumulative
limits and fixed 1800-second window survive restart. Pause/expiry blocks new
attempts while already admitted jobs drain with retained receipts. Implementations
must reject automatic/manual same-ID retry that bypasses the stated retry budget.

Observation every 10 seconds, renewal only after a successful observation, and
the 60-second owned lease provide explicit controller-loss handling without
blind heartbeats. The ordinary-wait monitor continues through paused/expired
drain; gaps cannot be reported as healthy capacity evidence. This resolves the
earlier monitor-ownership ambiguity. The 300-second trigger is correctly a failure
condition rather than a scheduling guarantee.

The valid-state matrix covers absent, paused, populated, expired/exhausted,
backlogged, mixed/dead-worker, stale-controller, corrupt-accounting and hostile
scope conditions. It distinguishes valid disabled producer behavior from invalid
pilot authority. Candidate-only source provenance, exact batch-only service scope,
default-mode preservation, existing global deploy fence/drain and no destructive
Redis cleanup are appropriate with the corrected image activation requirement.

## Reviewed corrected hashes

These bind the independently reviewed corrected documents before the standalone
checkpoint. Any subsequent normative delta requires review disposition:

| Document | SHA-256 |
| --- | --- |
| `docs/schemas/query-engine-catalog-refresh-contract.md` | `bf0e7a68e4656d01a3cd1354b72399950a1bd297b5e44f035f024d92eb71936d` |
| `docs/adrs/ADR-0104-query-catalog-refresh-operational-bounds.md` | `777f32ddb48d0d684af4dca652d58a0a6c5e523d3efde883687f0ac8bcffc40e` |
| `docs/schemas/rq-response-contract.md` | `4f3f680610d36fbda2c725a90fe9be8a3342d14575d2f16be19e0fb01862ca56` |
| `docs/schemas/query-catalog-pilot-deployment-contract.md` | `a023e97af8728725ec5fa9e68b265d193cdfd4747d8cbfdba95dd5fd82715148` |
| `artifacts/20261027_pilot_contract_decision.md` | `044c29c2ab3b68876a7875652db17fcf2acd4ea50331656a7446831e75a2ef6a` |
