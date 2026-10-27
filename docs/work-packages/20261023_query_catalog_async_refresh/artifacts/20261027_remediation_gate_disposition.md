# October 27 remediation gate disposition

**Implementation checks pass; general async enablement remains HOLD.**
The original implementation remains deployed with async disabled. This remediation
is not deployed. No production project, runtime identity, mount permission or
service configuration was changed by these probes.

## Closed remediation checks

- Reviewed contract checkpoint `09ce55d1d` precedes streaming-inventory changes.
  Existing batch workers now perform discovery with durable Redis checkpoints,
  job/cycle fencing, retry recovery and capability parity; scheduler stream
  acknowledgment and pending-scope publication are atomic. No queue/service was
  added. Independent containment, missing-root and alias findings are closed.
- Complete [four-root discovery](20261027_full_inventory.md): 30,891 distinct
  scopes, no errors, empty frontiers and exact stream/set equality. Legacy
  enumeration retained progress across a fenced restart. The separate
  [actual RQ timeout/retry canary](20261027_inventory_rq_timeout_canary.md) passed,
  including fresh catalog readback and cleanup; its shortened test timeout is
  not a claim that a full inventory fits one production attempt.
- HTTP/MCP catalog/query work runs in the existing thread pool; freshness,
  authorization and error behavior remain synchronous from the caller's view.
  Final-source [production-equivalent ASGI canaries](http-health-canary.md)
  kept health responses at 1.52–2.63 ms during 30-second cross-host guard waits,
  including a saturated one-token test pool. This was a private ASGI process,
  not a deployed listener or a fleet load test.
- Independent reviews passed 66 inventory/filesystem/privacy tests and eight
  focused HTTP checks; local HTTP/query suite passed 199 tests. Broad regression
  passed in segments: 11,621 passed/170 skipped before a stale local browser-path
  failure, then 183 failed-module/remainder tests passed with a process-local
  correction. These counts overlap and are not one green full-suite total.
  Final-source focused checks cover edits made during the broad run.
- RQ graph, changed exception inventory, test-stub check and documentation checks
  pass. [Source manifest](20261027_remediation_source_manifest.json) binds the
  reviewed candidate; unrelated concurrent workspace edits are outside this claim.

## Remaining release gates

### Shared-worker capacity and queue delay

Completed [classification](20261027_scope_classification.md) identifies 18,514
writable and 12,377 READONLY scopes. The eight-scope normal-worker canary passes,
but its shared-owner/hardlinked dataset is not a fleet service distribution.
The final [48-scope component profile](service-component-final-profile.md)
completed all collections and 47 first verifications; two 300-second process
bounds interrupted verification (one first pass, one repeat). No schema error
was observed. These are censored measurements, not observed job failures. Strict
refresh verifies twice, whereas each probe pass verifies once, so the component
figures cannot alone certify whole-job capacity.

Observed batch load varies: the earlier 9.5-minute window had all eight consumers
busy while the queue fell from 80 to 54; a later 19.5-minute window had no queued
work, seven idle consumers for six samples and eight idle for 34 samples. These
point observations do not establish daily headroom. Incomplete retained history
is likewise not an upper bound on ordinary work.

A stable cycle needs at least 49,405 candidate considerations (one per READONLY
scope and at least two per writable scope): about 16.47 hours at nominal cadence.
[Full 25-candidate tick measurements](20261027_inventory_scheduler_tick_canary.md)
were below 30 seconds for the scratch cases, including new admission (11.67 s),
queued rechecks (0.79 s), retirement (0.62 s) and READONLY skips (0.14 s). These
measurements exclude large pending lists and competing scheduler work.

Before a shared-queue rollout trial, establish a concrete accepted backlog/wait
limit and stop condition, then measure whole-job work, ordinary arrivals and
complete-cycle convergence under that limit. Preserve unfinished receipts on
stop. Do not infer failure merely from the nominal admission ceiling, or success
from an idle window. [Independent capacity assessment](capacity-independent-assessment.md)
records the quantitative conditions. Operational defaults remain unchanged.

### Preexisting legacy mount limitation: outside release scope

The operator responded “i don’t care about the read only mount” to the proposed
legacy routing scope question. Record this as exclusion of the preexisting
fork/archive placement limitation from this catalog release, not permission to
change mounts, routing or cancellation policy. The external catalog guard passed
under the existing role; its later project-config `EROFS` is retained as an
unrelated preexisting workflow limitation. All legacy scopes remain included in
inventory and writable-worker refresh. The [routing proposal](20261027_legacy_routing_proposal.md)
is deferred and is not a remaining catalog-rollout gate.

### Coordinated deployment and effective configuration

After the open gates pass, use the canonical deployment entry point and verify
all four namespaces, shared coordination and inventory capability on every
participant before enabling. This record does not authorize deploying unrelated
Roads, secret-dependency or other concurrent workspace changes. Do not mark M6
or the package complete while these gates remain open.

## Final live readback

[All nine checked runtime roles](20261027_final_rollout_state.json) still have
async disabled by default and no explicit roots configured. Their on-disk source
remains the original release; the new inventory helper is absent. This confirms
no remediation deployment or enablement occurred during validation. It does not
inspect already-loaded Python function objects.

## Recommended next decision

The independent assessment recommends a bounded shared-queue pilot rather than
further component-only measurements. The [concrete admission proposal](20261027_bounded_admission_proposal.md)
limits outstanding catalog work, pauses on ordinary backlog, preserves pending
intent and defines pilot bounds/recovery. It is not implemented; operator policy
approval is pending. Current code and rollout settings remain unchanged.
