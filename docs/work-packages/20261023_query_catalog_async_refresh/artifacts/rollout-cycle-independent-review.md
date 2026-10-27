# Independent rollout-cycle and final gate review

Date: 2026-10-26. Reviewer: `/root/science_review`.

**Controlled reconciliation/RQ canary PASS; unrestricted production rollout NOT
READY on this evidence.** This review covers `rollout-cycle-probe.py`,
`rollout-readback-probe.py`, `20261026_rollout_cycle.json`,
`20261026_rollout_readback.json`, the normal-worker repeat, candidate-root parity,
parent gate disposition, deployed HTTP source readback and the independent
lock campaign. No production deployment or implementation edits were performed.

## What the evidence establishes

The canary uses uid 1002/gid 130, a unique scratch root/namespace, process-local
configuration, and a unique RQ queue. It copies at most 512 MiB from explicitly
selected Parquet directories, does not hydrate NoDb state, and never writes back
to the source. It registers a dedicated worker only for the unique queue; shared
batch history is read-only. The script refuses to reuse an existing scratch root.
These are appropriate boundaries for the authorized functional acceptance test.

Actual inventory first discovered the receipt-free project and admitted one job;
the actual refresh function ran through RQ. A second inventory tick reported
completion. Seventy-nine copied Parquets total 73,328,103 bytes; all are present
among 80 catalog entries; no pending receipt remains. Completion took 6.955 s.
The independent readback script queries all 79 original/copy tables and verifies
matching row counts under the same identity. Copy hashes are retained, although
this readback is row-count parity, not a full value-by-value comparison. No science
artifact regeneration occurs in this test.

The first canary used injected `_default_queue` and a custom `SimpleWorker`.
The added `rollout-workhorse-probe.py` instead subclasses normal RQ `Worker`,
overriding registration only to advertise the candidate configuration; normal
forked execution is retained. Its result, `20261026_rollout_workhorse.json`,
completes discovery/admission/workhorse/second-tick convergence in 7.762 s, with
zero pending receipts and 80 catalog entries. Its 79-file path/size/hash manifest
is exactly equal to the first canary's manifest. **The normal forked workhorse
canary gap is resolved.** Both runs still use isolated queues and controlled
compatible workers; they do not establish production shared-batch scheduling or
multi-consumer contention. Retain that distinction in acceptance claims.

The 169 retained finished batch jobs supply useful historical queue/service
observations. They exclude unfinished jobs from completed-duration statistics,
reflect retention selection, and mix workloads. The observed queue tail and long
service durations cannot establish future spare capacity or a maintenance SLO.

## Remaining gates and minimum next steps

1. **Namespace/configuration readiness.** The owning review reports active owned
   legacy projects. They must remain in the explicit managed configuration;
   omitting them to make the three-namespace candidate pass would change behavior
   and hide unreconciled work. Earlier preflight already records read-only legacy
   access on wepp3. Establish role-specific compatibility before cutover: every
   eligible refresh consumer needs the required writable scope/coordination
   access, while read-only archive participants need their actual guarded
   lifecycle workflow validated. A read-only archive participant is not, by itself,
   proof that every worker needs new write permission. Preserve current access;
   do not silently chmod/remount, omit legacy, or alter queue membership. Use the
   existing env-file mechanism for an explicitly reviewed complete mapping.
2. **Fleet-scale capacity.** One flat scratch project is a full cycle only for
   that fixture. It does not count all owned projects/nested scopes, measure a
   complete production reconciliation cycle, or establish oldest-unreconciled age
   under competing batch load. Those ADR-0104 obligations remain. Retain the
   controlled service measurement and historical queue distribution as inputs;
   obtain bounded production inventory/cycle evidence before claiming the 24-hour
   target is attainable. Do not extrapolate 6.955 s to every scope.
3. **Request/readiness responsiveness.** The separate lock campaign passes
   exclusion and worker liveness but reproduces approximately 23–24 s of
   post-release handoff delay on one directed topology. Producer receipt
   persistence also waits on the guard. Deployed async query handlers call the
   synchronous barrier directly; a pending/stale refresh can block their event
   loop even while another Python thread remains healthy. Static source plus
   actual syscall timing establishes the exposure; no production outage was
   induced. Close this with explicit accepted request-tail bounds or a bounded
   isolated actual-handler contention test. If responsiveness fails the chosen
   requirement, the smallest candidate is moving that existing blocking barrier
   off the event loop with preserved error/readiness semantics, followed by the
   same acceptance test. This is a candidate for authorized work, not an approved
   implementation, fallback, storage-tuning change or new service.

No blanket PASS follows from a healthy heartbeat or a successful controlled RQ
cycle. No evidence here justifies replacing the guard, changing storage settings,
or deploying around an unconfigured owned namespace. Keep rollout disabled until
the owning review closes the specific remaining gates.

## Candidate-root and parent-disposition review

`20261026_candidate_root_parity.json` reports identical protocol-1, enabled
candidate configuration on all three hosts, SHA256
`02d605c5c8a13a1210ac866e879cb38fff5d6afbb04d8e73e394a28a8c23c2f8`.
It includes all four namespaces, explicitly including `legacy:runs`, with shared
external `/wc1/query-engine-coordination/locks`. All four roots exist and are
readable/searchable; coordination is writable. Only wepp3 legacy root write
access is false. This is consistent with the role-specific readiness concern,
not grounds to omit legacy or change permissions. These are process-local parsing
and root-access checks, not persisted deployment settings, every-child permission
coverage, real archive/fork acceptance, or enabled fleet registration.

Reviewed `20261026_rollout_gate_disposition.md`: its HOLD conclusion is appropriate.
It accurately distinguishes the two controlled RQ cycles, root parsing parity,
historical batch observations and independent lock evidence from the unclosed
fleet inventory and request-readiness gates. The reported legacy enumeration
stall strengthens the need for resumable production inventory evidence; extending
a lease without checkpoint progress would not establish completion. No new
scientific or security-boundary objection to the retained canaries was found.
No additional tests were run for this follow-up review.
