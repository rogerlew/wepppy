# Delay digest-cache admission across filesystem timestamp quanta

Status: accepted and implemented; scoped validation and runtime evidence retained in the freshness work package.

## Context and evidence

The freshness audit reproduced different file bytes under identical device,
inode, size, nanosecond mtime and ctime on both container overlayfs and the
repository filesystem. Immediate stat-keyed SHA-256 reuse therefore returned an
old digest after an equal-size rewrite with restored mtime. This is a real
counterexample to the initial checkpoint's cache assumption. The retained
correctness review and collision probe are in
`docs/work-packages/20260916_file_dependency_freshness/artifacts/`.

## Decision and parameter delta

Replace immediate cache admission with a **1-second monotonic observation
interval** for each newly observed path/version. During that interval hash the
file uncached on every access. Do not insert those digests into the reusable
cache. After the interval, the first access computes a fresh digest and only
then admits it to the existing bounded cache. Keep all descriptor/path checks,
read-access checks and explicit failures. Bound each read by captured file size.

The observation timestamp uses a companion 512-entry LRU with the same
path/version key and eviction discipline. Eviction restarts observation and
uncached verification. Include the unique monotonic observation-generation value
in the digest cache key so a surviving old digest cannot reappear when the new
observation interval ends. This is bounded process
memory, with no persistent project files, service or watcher. Use monotonic
elapsed time rather than comparing local wall time with NFS-server ctime.

One second exceeds the observed subsecond timestamp collision windows and
covers second-resolution filesystem timestamp quanta. The supported runtime
still requires normal coherent metadata on open, including NFS close-to-open
semantics; this interval is not a remedy for an incoherent or disconnected
filesystem. Do not claim support for a filesystem with coarser version quanta
without separate evidence and a revised contract.

## Alternatives and rationale

Immediate full-stat caching is rejected by the retained failing probe. Sleeping
in tests would only conceal the failure. Hashing every large input on every
status poll violates the package's repeated-read budget. Wall-clock timestamp
age would add NFS/client clock-synchronization assumptions. A new watcher,
persistent version store or writer protocol is disproportionate before testing
this bounded admission rule.

Cold and newly changed files may be reread during the observation interval;
settled unchanged inputs must satisfy the original zero-warm-content-read gate.
No model formula, scientific threshold, parser or result value changes.

## Decision provenance

Venue: owner-authorized repository execution session, 2026-09-17 UTC
(2026-09-16 America/Los_Angeles). Participants: owner, primary Codex agent and
independent correctness/security review agents. Owner authorized the audit/fix
package; the primary agent selected this bounded implementation strategy within
that scope. Independent correctness/security reviews pass the checkpoint; no separate human approval of this
specific heuristic is claimed. Implementer: primary Codex agent.

## Validation, risk and rollback

Retain and rerun rapid equal-size/restored-mtime probes on container, repository
and disposable NFS run directories. Test that no digest becomes reusable before
the interval, the first admitted digest is freshly read, eviction restarts
observation, failed reads are not cached, and stable repeated reads do not hash.
Use deterministic clock injection only for interval branch coverage; keep the
original real-clock collision probe as acceptance evidence.

Reverting the admission rule restores a demonstrated false-current defect;
do not roll back this rule alone while keeping content-based currentness.
If these acceptance conditions fail, retain the failure, hold runtime rollout,
and revise the checkpoint. This ADR does not close other inventory findings.
