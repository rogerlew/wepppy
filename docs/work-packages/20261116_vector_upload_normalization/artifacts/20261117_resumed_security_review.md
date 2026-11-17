# Resumed independent security review

Date: 2026-11-17. Independent reviewer: `security_reviewer` (`frozen_security`).
Final reviewed source: `f964831084159eb4cf68cb533dc48235cb580989`.
Comparison source: `0e861887e132b41b00a108292d7833d21750b146`.
Sharing decision: `bbb216c0bc48674f8b24f5e69f20ec58e57b795a`.
Exact local converter image:
`sha256:4487dec16cdb1a0ed735e60f10672c646ecc3b26d0586dbfce93479b9eae98fa`.

## Findings and disposition

**PASS for the frozen source security review. No unresolved High or Medium
security finding remains in the reviewed scope.** `f96483108` closes
SEC-COPY-PENDING-01 with a tested preflight; the bounded private writer and
cleanup-fault accounting findings remain closed. This source verdict does not
waive the separate full-suite failure under QA investigation.
The reviewer changed no production
code or tests. Final runtime acceptance remains subject to the integrator's
immutable-source validation receipt. No combined/full-suite success is inferred.

### SEC-COPY-PENDING-01: Medium - closed in `f96483108`

At `467e9db1b`, a terminal `incomplete` source receipt can still have pending
accounting and a live reserved Redis record. A copy inherits its `reservation_id`.
Committed-only rebuild skips both receipts because that reservation is not yet
committed, so the helper can clear its operation marker while the copier's bucket
remains zero. The contract permits reconciled terminal incomplete records only.

The final preflight rejects an explicit noncommitted `accounting_status` and
checks each bounded source reservation identity under global maintenance/source
scopes. A present Redis reservation must itself be committed: receipt status
alone is insufficient because reconciliation writes it before Lua commit.
Legacy terminal receipts without the newer field/reservation remain compatible.
The checks precede admission, obligation creation and destination mutation.

`test_copy_requires_source_reservation_reconciliation` covers a pending receipt
and a misleading committed receipt with an unreconciled Redis reservation; it
requires no destination/marker, then reconciles and checks exact source/copier/
global bytes. The retained red run demonstrates admission without the fix.
The first green run rejected correctly but failed its case-sensitive message
regex; the corrected suite passed **19 tests** in
`/tmp/vun-copy-pending-green2.log`. Both receipt variants reject before copying
and succeed with exact accounting after reconciliation. The reviewed helper and
test hashes match the immutable final checkout. This finding is closed; no
policy, threshold or ledger API changed.

### SEC-ARCHIVE-GROWTH-01: Medium - closed in `111dd982c`

At `13feaac92`, `archive_rq()` measured payload before classification/reservation. An existing
sensitive project can gain a child upload after that measurement; its private
ZIP accepts the additional members. The reservation still uses the earlier
`required_bytes + 1 MiB`, while `_COMMIT_LUA` records actual bytes without checking
them against that allowance. Thus this race can complete above global admission
and consume space already reserved for other work.

An independent actual-ledger probe on `13feaac92` added 3 MiB of real opaque
terminal child source after the payload measurement. Only test archive headroom
and quota were scaled down. The archive reserved **1,051,767 bytes** but committed
**3,150,169 bytes**; global committed storage reached **6,296,118 bytes** against
an admitted limit of **5,243,101 bytes**. ZIP output, source files, renewable parent
scope, Lua reservation/commit, reconciliation and final counters were real.
The late child terminal receipt was a fixture charged by real reconciliation,
rather than an HTTP upload. No user files or production source were modified.

Retained probe: `/tmp/vun-security-private-growth.py`; measured result, exact
command and limitations: `/tmp/vun-security-private-growth-result.json`.
It runs against `weppcloud:/tmp/vun-13feaac92`. The final bounded writer checks
the current file offset plus `memoryview(data).nbytes` before each underlying
write against the existing `required_bytes` budget. This covers compressed data,
header rewrites after seeks and central-directory output. `ExitStack` closes the
ZIP before its stream. Cleanup releases its uncommitted reservation only after
temporary-file removal is durable, as verified below. Public handling and the extra
receipt allowance are unchanged; no Lua API, quota threshold or authorization
policy changed.

The actual-ledger regression now rejects the same late 3 MiB growth, observes
that every flushed temporary-file extent stays within the allowance, preserves
both source originals, leaves no ZIP/temp/reservation, and reads exact prior
source committed bytes with zero reserved/inflight counters. Three additional
tests verify exact-size successful ZIP output with header rewrites, rejection
of central-directory overflow before growth, and extent bounds after seeks.
The bounded-writer checkpoint matched its retained 95-pass run by SHA-256;
the final cleanup successor matches its 98-pass archive run. No unresolved
finding remains from this bounded review.

### OPS-ARCHIVE-02: Medium - independently confirmed closed in `467e9db1b`

The narrow `111dd982c..467e9db1b` review covers the archive cleanup combination
identified by operations. Failed temporary-file unlink now logs and keeps its
bound reservation. Successful unlink must also sync the containing directory
before reservation release. Either failure attempts a private incomplete receipt
carrying the verified archive actor, project identity, reservation identity and
pending accounting state; the existing reservation includes its bounded metadata.
Receipt persistence failure is logged and also keeps the charge. These paths do
not reinterpret source bytes or introduce a new accounting or recovery API.

The actual-ledger fault test covers normal cleanup, unlink failure, directory
sync failure and receipt persistence failure after failed unlink. It checks
physical extents, intact sources, no published ZIP, retained reservation bytes
covering the surviving bundle, minimized actor metadata and error visibility.
For valid incomplete receipts, later reconciliation replaces reserved/inflight
charges with exact surviving bytes under the archive actor while preserving
the source actor's charge. Failed receipt persistence remains explicitly charged
for existing corrupt-receipt recovery; it is not claimed as completed repair.
No High or Medium finding remains in this narrow successor delta.

### Archive confidentiality successor

**VUN-CORRECTNESS-RESUME-05: closed in `13feaac92`.** Every directory/file member
is checked before `zf.write`; a public-classified archive aborts with 507 before
newly discovered sensitive bytes enter even its temporary ZIP. Cleanup removes
that output; the real-ledger regression verifies unchanged source receipt/bytes
and live child lease, then a private retry containing the original. Nested
`archives/private` records use the same sensitivity classification. The relative
target ancestor-sync variant is also closed by resolving the parent before its
walk to the configured root. The separate archive-growth finding is closed by
the bounded writer above.

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

## Successor review: child scopes, recovery and durability

The complete production/test delta `54ee356fd..224184ecd..cfd5329d4` was reviewed.
The High/Medium findings identified after the first checkpoint are closed:

- **VUN-CORRECTNESS-RESUME-03, active child upload deletion: closed.**
  `discover_retention_scopes()` scans at most 10,000 reservations under global
  maintenance and identifies descendants by composite scope and bound attempt
  path. This includes reservations created before their attempt directory.
  Lifecycle callers, direct run/Batch deletion and archive restoration acquire
  the discovered scopes before any destructive mutation. New reservations are
  blocked by global maintenance; malformed escaping reservation paths fail
  closed. Tests cover reserved and prepared children, intact originals/receipts,
  unchanged counters, absence of premature markers and success after release.
- **VUN-CORRECTNESS-RESUME-04, outstanding free-space demand: closed.** Copy
  admission now includes total live reservations alongside incoming allowance
  and protected free space. The regression rejects space sufficient for the
  copy alone but insufficient for all previously admitted writes.
- **SEC-COPY-DURABILITY-01, missing linking-ancestor sync: closed in
  `cfd5329d4`.** The initial successor synced target and its immediate parent,
  omitting directories linking newly created profile/shard ancestors. The final
  helper syncs all linking ancestors through the validated configured root.
  Batch/Omni add retained stale paths to the same sync boundary before rebuild
  and marker clearance. The regression uses two previously absent parent
  directories and asserts bottom-up ordering. An independent disposable
  real-filesystem probe confirmed evidence, target, both parents and configured
  root were synced; no user data or service state was touched.

Authorized fork replacement now completes an interrupted worker's exact
destination `fork_copy` cleanup/rebuild obligation before enqueueing replacement.
The existing destination/principal/failed-job checks remain upstream; this does
not grant a new delete permission. Global/project fences and the union of repair
authorities still reject unrelated identities. The real-rsync failure/recovery
test verifies source preservation, partial-target removal, marker clearance,
exact totals and fresh recipient charging.

Exact downstream tests now use real Redis admission, renewable leases and ledger
commit/rebuild instead of fake ledger/lease objects. Fixture teardown reads
receipts and exact physical/principal/global bytes and requires zero remaining
reserved/inflight charges and repair markers. Test-only connection injection
does not bypass the production accounting boundary.

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
`weppcloud:/tmp/vun-f96483108` validation checkout. Its actual Git HEAD also matched
the reviewed source:

| File | SHA-256 |
| --- | --- |
| `project_rq_archive.py` | `48d8f26bb2fd786f91eefa2454aa688e5a83494deb552ba6473d1c2074773be3` |
| `vector_retention_lifecycle.py` | `083acbf6a8c16eeaf98dea7c8dd9dc9c4a34c405f942308fe3b8c42503c93903` |
| `vector_upload_normalization.py` | `9bc5a34bdf61ae8a1ebbc1f318995907277d0d5ab9db161ffaf1297511c09719` |
| Canonical vector-upload contract | `2495f4b472db881bbde27f57951889f6239ea3dfc73391920ab20cfc14113922` |

The reviewed successor diffs pass `git diff --check`. The reviewer directly read
completed logs: `/tmp/vun-13f-focused.log` (**721 passed**),
`/tmp/vun-111-delta.log` (**142 passed**), and
`/tmp/vun-cleanup-reservation-validation.log` (**98 passed**). The last run's
archive module and both test suites have SHA-256 values identical to the final
commit, recorded in `/tmp/vun-cleanup-reservation-sha256.txt`; it includes the
bounded writer and cleanup faults. The prior 95-pass cap run and earlier
candidate logs (50 lifecycle/fork, 142 direct
deletion/restore and 25 exact downstream passes) remain historical corroboration.

The reviewer ran the disposable actual-ledger reproduction and direct filesystem
sync probe, but did not initiate pytest. The immutable `467e9db1b` archive
selection completed: `/tmp/vun-467-delta.log` reports **98 passed, 94 warnings,
75.83 seconds**, with no failures or skips. The final copy-preflight candidate
suite reports **19 passed, 4 warnings, 23.87 seconds**; the final helper/test
hashes are `083acbf6…93903` and `548bdc33…a3c`. At review cutoff the immutable
`f96483108` copy/helper/exact-integration selection was still running in
`/tmp/vun-f964-delta.log`.

The full `224184ecd` suite stopped with **1 failed, 7,966 passed, 205 skipped**
at `test_published_results_and_sources_are_current_or_explicitly_stale` (Roads
published source-hash drift). Its disposition is under separate QA/integrator
review; this bounded security closure does not dismiss or waive that failure.
Final selections, exclusions and semantic artifact readback remain in the
integrator's retained validation receipt. No incomplete or failed suite is
represented as passed.

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
