# Resumed independent security review

Date: 2026-11-17. Independent reviewer: `security_reviewer` (`frozen_security`).
Final reviewed source: `54ee356fd16845e7abf6da59d7df616f8b5fa6ce`.
Comparison source: `0e861887e132b41b00a108292d7833d21750b146`.
Sharing decision: `bbb216c0bc48674f8b24f5e69f20ec58e57b795a`.
Exact local converter image:
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.

## Findings and disposition

**PASS for the frozen source security review. No unresolved High or Medium
source security finding remains in the reviewed package scope.** This supersedes
this artifact's earlier HOLD at `ee26389f0`. The reviewer changed no production
code or tests. Final runtime acceptance remains subject to the integrator's
immutable-source validation receipt; this source-qualified verdict does not
assert that the still-running combined/full suites passed.

**SEC-RESUME-01, public/team fork inheritance: resolved by explicit operator
policy.** The initial review demonstrated that ordinary public-run forking copies
originals, rejected attempts and private archives to the new owner. The operator
explicitly accepted this sharing behavior. The authoritative exception and its
rationale are recorded in
[the canonical contract, “Sharing, copies, and existing workspace resets”](../../../schemas/vector-upload-normalization-contract.md#sharing-copies-and-existing-workspace-resets)
and [the sharing decision](20261117_sharing_contract_decision.md).
Existing public/team fork access and destination ownership remain intact; direct
source sensitive browse/download restrictions remain unchanged. The former
filter/source-only recommendation is superseded and is not an open defect.

**SEC-RESUME-02, unaccounted copies and workspace removal: closed in reviewed
source.** Actual fork rsync, Batch leaf copy/reset, Batch Omni/base reset,
developer smoke clone, Omni child cleanup and profile promotion/reentry now use
the shared retention lifecycle at their existing filesystem boundary. The
[consumer inventory](20261117_vector_retention_copy_reset_inventory.md) identifies
each caller, tests and explicit exclusions. The helper admits incoming retained
bytes, holds global/project authority, records durable repair identity, verifies
copied bytes, rebuilds exact accounting and clears repair only after readback.
Normal generated cleanup preserves the owning project's retained-attempt roots.

**COPY-ACCOUNTING-01, charging another principal for a copy: closed.** Immutable
upload `actor`, source hash, project identity and attempt identity remain source
provenance. Additive `retention_actor` charges the verified copying principal,
or the existing unattributed bucket for automated/legacy callers. Fork admission
derives that identity from verified claims/user resolution and puts minimized
metadata in the job; request-supplied actor fields do not control it. Rebuild
uses that attribution with legacy `actor` fallback. Bounded `copied_from` and
`copy-source-receipt.json` record inheritance without claiming another upload.

## Implementation findings closed during this review

| Confirmed issue | Final disposition and evidence |
| --- | --- |
| Linked ordinary model subtree could materialize uncharged retained evidence | `_reject_linked_evidence()` rejects sensitive roots or receipt parents reached through directory links; `_roots()` and regular-tree checks reject sensitive symlinks. `test_linked_model_subtree_cannot_materialize_uncharged_evidence` covers the alias path. Ordinary non-evidence model links remain supported. |
| Copy callback could return success after omitting a receipt but copying its payload | `_publish_copy_provenance()` rejects that partial subtree and post-copy `_inventory(target)` requires complete receipt coverage. `test_successful_callback_with_missing_receipt_leaves_repair_obligation` retains the marker. Deliberate omission of an entire model root remains valid. |
| Explicit export flag could bypass missing identity for a known in-root destination | `_configured_root()` checks resolved containment when the root is known. `test_explicit_export_inside_root_requires_identity` covers the bypass. Both configured root and identity establish an ordinary external execution destination; absent settings do not prove that boundary. |
| Speculative deletion credit could under-admit a replacement whose old workspace remains stale | `_admit_copy()` includes all existing committed/reserved bytes and incoming allowance, without reclaim credit. `test_replacement_requires_headroom_for_old_bytes_and_reservations` rejects before callback mutation. |
| One lease-release exception could abandon other renewable scopes and global maintenance | `ExitStack` registers each acquired lease immediately and releases all owned leases. `test_release_failure_still_releases_all_owned_leases` verifies cleanup despite one release failure. Borrowed scopes stay with their owner. |
| Failed Batch copy could become stale on retry, leaving uncharged bytes and source-actor attribution beside the replacement | With acquired `repair_pending`, Batch requires successful removal of the incomplete target before copying. It cannot defer that removal through stale rename. `test_batch_copy_retry_requires_partial_removal_before_recopy` creates complete copied receipts before failure, proves no recopy after removal failure, and checks no new stale sibling plus exact source/unattributed totals after retry. Normal completed-workspace resets retain existing deferred cleanup. |

The final successor removes a speculative blanket rule requiring every existing
destination receipt to appear in the current source during retry. That rule would
have changed established profile `dirs_exist_ok=True` merge semantics and blocked
legitimate older snapshot records. The confirmed partial-stale defect is closed
at its actual Batch consumer; this review requires no new merge policy, receipt
state machine or workflow permission.

## Security controls rechecked

- Global maintenance precedes project scopes. Borrowing an already-owned Omni
  scope uses nonblocking global acquisition and cannot create a wait cycle.
  Ownership checks protect mutation, publication, rebuild and marker clearance.
  Whole-Batch deletion also fences independently writable child-run scopes.
- Filesystem and Redis pending identities are combined. Another operation cannot
  remove the workspace needed by pending repair; the identical operation can
  retry from either authority. Stable tombstones/stale siblings remain part of
  configuration checks when the target is absent. Deferred completed-workspace
  bytes remain charged.
- Source/destination overlap is rejected. Raw uploads remain opaque. Bounded
  terminal receipts and complete tree sizes govern managed copies; copied files
  are hashed against source, receipts privately published, and evidence synced.
  Exact-root rebuild preserves unrelated active reservations. Flattened profile
  archive exports remain discoverable through receipt-parent inventory.
- Established profile execution/fork roots outside the configured ledger remain
  on current storage. In-root reentry is charged; missing settings do not prove
  an external destination. Explicit offline exports retain their existing
  ownership boundary. No mount, identity, runtime root or permission changed.
- Owner/root private-archive checks, JWT scopes/run binding, signed-session
  provenance and direct sensitive-artifact restrictions remain. Receipts retain
  minimized attribution; security events omit submitted filenames, raw claims,
  tokens, email and client IP. No parser, converter image, dependency, public URL,
  privilege or Python hostile-parser fallback changed in this successor.

Earlier SEC-REREVIEW-01 archive lease/disclosure, SEC-REREVIEW-02 private archive
integrity/authority and SEC-REREVIEW-03 Redis-loss/rebuild findings remain closed.
Their regression coverage and exact converter qualification remain required.

## Evidence and validation boundary

The reviewer inspected the committed successor, lifecycle helper/normalizer,
confirmed copy/reset wrappers, canonical amendments, prior dispositions and new
regression assertions. Relevant suites include lifecycle, copy consumers, fork
retention, profile lifecycle, deletion, archive recovery, session provenance,
private archive/auth, sensitive-artifact, normalizer and readiness tests.

Direct Docker image readback returned the exact final5 ID above. These SHA-256
values independently matched the frozen worktree and immutable
`weppcloud:/tmp/vun-final-acceptance` validation snapshot:

| File | SHA-256 |
| --- | --- |
| `vector_retention_lifecycle.py` | `73fcd237c3cb571066735561d079c7b6200fe504710eac621e03635c49b15100` |
| `vector_upload_normalization.py` | `9bc5a34bdf61ae8a1ebbc1f318995907277d0d5ab9db161ffaf1297511c09719` |
| Canonical vector-upload contract | `9d1be8cd69cdae60727d74de80fd027d6c1f4b9c436ba62731ff5b6d07805ad5` |

`git diff --check 0e861887e..54ee356fd -- wepppy tests services` passed. The wider
documentation diff contains three Markdown hard-break trailing spaces in an
earlier correctness checkpoint; the integrator was notified. This reviewer did
not initiate runtime tests. At review cutoff, `/tmp/vun-final-focused.log` showed
the immutable-source combined selection running; `/tmp/vun-final-full.log` had
no completion result. Final results, exclusions and semantic artifact readback
belong in the retained final validation receipt. Earlier mutable-tree totals are
not promoted to frozen acceptance here.

## Residual limitations

Previously recorded Low internal-peer hardening remains nonblocking: receiver
HTTP uses connect/per-read limits rather than an independent absolute wall-clock
deadline, and trusted-converter unknown error-code bounds merit later cleanup.
The qualified converter and byte-bounded response constrain those cases.

Filesystem race protection assumes the established service identity and private
artifact roots. This is not containment of a hostile process already able to
mutate those roots as the service user. Consumer inventory exclusions remain.
Production parity must exercise real mounts, groups, umask, auth storage and
orchestration; publication requires the documented fresh scan. This source
review neither performs nor authorizes deployment or publication.
