# Bounded pilot contract security review

Date: 2026-10-27 UTC. **PASS for the final refined pre-implementation contract
checkpoint.** This supersedes the earlier skip-build activation sign-off.
Independent reviewer: inventory/security review agent. Scope is the now-authorized
bounded shared-batch pilot under the active query-catalog work package. General
async enablement remains outside this authorization. No implementation or
production action is performed by this reviewer.

## Findings and closure

1. **PILOT-SEC-01 — Medium, CLOSED.** The first canonical draft omitted
   monitor-through-drain and controller-loss policy, allowing ordinary-wait
   failure to go unrecorded after observer loss. The canonical “Pilot observation
   and controller loss” section and ADR now require 10-second observation, a
   60-second owned lease renewed only after successful observation, admission
   fencing by owner/generation, explicit recovery and retained gaps/failures.
   Observation continues through pause/drain to terminal jobs and readback.
   Resume cannot reset counters/deadline or turn a recorded failure into a pass.
2. **PILOT-SEC-02 — Medium, CLOSED.** The first draft placed targeted deployment
   only in work-package prose. The new canonical
   [scoped deployment contract](../../../schemas/query-catalog-pilot-deployment-contract.md)
   and ADR now specify exact batch-only recreation, unchanged defaults,
   no dependency/Redis recreation, existing owned fence/drain semantics,
   source-baseline patch provenance and rollback. Actual production cutover
   remains subject to its separate operational control review and evidence.
3. **PILOT-SEC-03 — Medium, CLOSED after activation re-review.** Correctness
   review proved the workers have no repository bind mount: host patch plus
   `--skip-build` would retain old code. That discovery invalidated the earlier
   activation sign-off. The ordinary baseline Dockerfile also contains mutable
   vendor/base references and installers, so merely rebuilding it would not
   prove the authorized native/dependency scope. The final canonical
   “Source-only image derivation” section now requires a derivative of each
   host's exact inspected running local image, with no registry pull,
   network/installer/vendor/native step. Only the five checkpoint-listed Python
   files, their stale derived bytecode and immutable overlay provenance may
   differ. Strict paths/no symlinks/content hashes, a trusted generated recipe,
   base-ID binding, candidate import/runtime fingerprints and exact original-image
   rollback are required. This closes the contract gap; implementation must
   still prove those boundaries against the actual image and source manifest.

No unresolved medium/high contract finding or risk acceptance remains. The
[decision artifact](20261027_pilot_contract_decision.md) now records operator
authorization, canonical/source matrix, starting revision, compatibility impact,
valid/hostile states and direct regression/production evidence requirements.
The second independent review and standalone ancestor commit remain sequencing
requirements; this PASS does not permit implementation before that commit.

## Contract clauses assessed as adequate

- Operator-created immutable manifest binds exact owned fixture scopes,
  generation, configuration/capability, incarnation and directory identity.
  `pilot_id` alone is not authority. Fixtures use existing canonical namespaces;
  unrelated projects and unlisted descendants remain excluded before metadata or
  receipt work. Initialization is an explicit operator preparation step.
- General async remains false; normal producers and scheduler keep disabled-mode
  behavior. Only explicit pilot admission and recorded admitted jobs receive the
  exception. Authentic installed worker capabilities are required; private-pool
  substitution, spoofed registration and arbitrary source bootstrap are excluded.
- The queue-wide cap includes all nonterminal/reserved catalog work across
  scopes, configurations, pilots and hosts. Permits and cumulative counters
  commit with enqueue; coalescing does not double-count, and ambiguity does not
  free capacity. Missing/corrupt state fails closed rather than refreshing quotas.
- Paused/expired admission allows already-recorded jobs to drain while blocking
  replacement attempts. Retry uses new budgeted job IDs; counters/window survive
  restart and resume. Redis-loss recovery is explicit operator reconciliation.
- Inventory starts from approved locators only, cannot expand to unrelated nested
  scopes or consume ordinary dirty indexes, and retains ordinary nofollow,
  identity, READONLY and publication safeguards.
- Ordinary backlog blocks new catalog admission through the same atomic decision.
  Unknown/corrupt queue entries are conservative; policy inspection uses raw
  identifiers and primitive fields rather than task deserialization.
- Existing reserved maintenance IDs retain generic polling. Manifest, scope and
  accounting details stay operator-only; existing Admin/Root cancellation
  authority remains unchanged. No new public control endpoint is introduced.
- Source-only image derivation preserves the inspected base's runtime identity,
  dependencies and entrypoint/command contracts. Neither arbitrary Dockerfile
  input nor job-time source execution is accepted. Batch-only recreation and
  unchanged unrelated running image IDs remain mandatory. The recorded matching
  nine native hashes and 307-distribution fingerprint are baseline evidence,
  not a substitute for candidate-image readback. Vendor revisions marked
  unavailable are not inferred from package versions or mutable branch names.

## Reviewed sources and provenance

- Canonical query-catalog contract: “Bounded admission and disabled-mode pilot.”
- ADR-0104: “October 27 bounded pilot decision.”
- RQ response contract: “Bounded query-catalog pilot maintenance.”
- Canonical scoped batch deployment contract and its ADR cross-link.
- [Actual runtime provenance](20261027_pilot_runtime_baseline_provenance.json),
  including distinct per-host image IDs and absent repository mounts.
- [Implementation design](20261027_bounded_pilot_implementation_spec.md).
- [Proposal provenance](20261027_bounded_admission_proposal.md) and the recorded
  operator authorization in the new decision artifact.

Starting revision is `f8f956c7a`. Existing streaming-inventory/HTTP remediation
remains separately bound to `09ce55d1d` and the retained source manifest.
Independent readback found the RQ/helper hashes still at their pre-pilot values
(`839bafc4…` / `d39f056e…`), no pilot helper/operator implementation files, and no
deployment-script diff at review. No new pilot implementation was reviewed or
claimed to pass.

Reviewed canonical SHA256 values:

| Document | SHA256 |
| --- | --- |
| query-engine-catalog-refresh-contract.md | `bf0e7a68e4656d01a3cd1354b72399950a1bd297b5e44f035f024d92eb71936d` |
| query-catalog-pilot-deployment-contract.md | `a023e97af8728725ec5fa9e68b265d193cdfd4747d8cbfdba95dd5fd82715148` |
| rq-response-contract.md | `4f3f680610d36fbda2c725a90fe9be8a3342d14575d2f16be19e0fb01862ca56` |
| ADR-0104-query-catalog-refresh-operational-bounds.md | `777f32ddb48d0d684af4dca652d58a0a6c5e523d3efde883687f0ac8bcffc40e` |

Decision artifact reviewed hash:
`044c29c2ab3b68876a7875652db17fcf2acd4ea50331656a7446831e75a2ef6a`.
Later disposition/status-only edits do not retroactively establish an ancestor;
record the actual checkpoint revision in the tracker and verify ancestry before
implementation. Code review, real Redis/filesystem tests, default-mode deployment
regressions, exact production candidate closure and actual eight-consumer pilot
evidence remain required after the checkpoint. Contract PASS is not a runtime,
deployment, pilot outcome or fleet-capacity PASS.
