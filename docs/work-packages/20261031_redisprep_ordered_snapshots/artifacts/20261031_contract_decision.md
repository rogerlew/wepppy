# RPS-01 contract decision

Prepared 2026-10-31 14:32 UTC. Starting branch `master`, revision
`967627f4c1afa3bfbae687bb99b76bd18bce5a7d`. Preserve pre-existing Roads research,
SSURGO, PROJECT_TRACKER changes and ignored generated docs index. See
`starting-status.txt`; the package itself was created when that listing was saved.

## Authorization and classification

Operator explicitly requested execution of the retained repair prompt and
"atomic and ordered RedisPrep snapshot publication and the necessary coherent
recovery behavior across confirmed consumers." That authorizes this bounded
behavior. It explicitly does not grant commit authority. No implementation edits
are authorized before the required standalone contract ancestor exists.

Classification: confirmed unsafe source mechanisms plus intended contract
extension, not an unchanged NoDbBase conformance fix. RedisPrep does not inherit
NoDbBase; its live source of truth differs. Production corruption is not proven.

## Authority matrix

| Current authority | Disposition / delta |
| --- | --- |
| `docs/schemas/redisprep-snapshot-contract.md` | New RPS-01 authority: serialized capture/publication, coherent conditional restore, lifecycle/field/failure/access obligations and regression limits. |
| `docs/schemas/nodb-persistence-concurrency-contract.md` | Cross-link separate RedisPrep authority; NoDbBase/NFMS-01 unchanged. |
| `docs/schemas/query-engine-catalog-refresh-contract.md` | Existing lifecycle/lock-order and managed/standalone obligations preserved; reuse is a design candidate, not permission to weaken publisher constraints. |
| `docs/schemas/wepp-run-input-contract.md` | WAM-01 leases/admission and batch/base semantics unchanged. |
| `docs/schemas/request-payload-contract.md` | MRS-01 early rejection and valid defaults unchanged. |
| `docs/schemas/rq-response-contract.md` | Existing error envelopes, missing-job reconciliation and lifecycle response semantics unchanged. |
| `docs/schemas/rq-webhook-contract.md` | Receipt replay and uncertain enqueue handling unchanged; snapshot cannot manufacture RQ jobs. |
| `docs/schemas/project-owned-config-contract.md` | Fork/archive lifecycle ordering and incoming replacement semantics unchanged. |
| `docs/schemas/project-developer-mode-contract.md` | Incoming fork/restore state remains authoritative; no sticky-state change. |
| Artifact observability/generated-artifact standards | Existing visible snapshot retention, direct consumer and environment evidence required. |

## Exact delta and rationale

The new contract defines file replacement as publication linearization and later
serialized HGETALL as newer capture. Restoration exposes all fields and loaded
marker atomically, conditioned against intervening live changes. Missing paths
remain no-op late writes; malformed recovery remains an error. Unrelated hash
fields are preserved, locks excluded, copied destination reset retained. File
mode/access and cross-host locking are acceptance constraints, not new privileges.

Atomic rename alone was rejected because capture A can otherwise replace B.
Expiring Redis leases plus pre-rename token checks were rejected because a pause
between check and rename defeats fencing. Per-process mutex and mtime/counter-only
schemes lack cross-process/lifecycle proof. Existing catalog POSIX record locks
are the leading reuse candidate; their lock-order and scope constraints must be
proven before adopting them. No protocol metadata/envelope is authorized here.

Legacy partial restore with an already-visible true loaded marker cannot be
distinguished from valid live deletion using existing state. The contract names
that limit instead of claiming detection. Known partial legacy recovery is proposed to require
explicit reconciliation, an unresolved acceptance limit requiring explicit
operator disposition before this checkpoint is accepted; new recovery must never produce the ambiguity. Any
migration that rejects healthy loaded legacy hashes requires another decision.

## Compatibility and regression plan (before persisted-state edits)

Keep flat JSON and existing namespace/key meanings. Validate legacy Redis scalar
values, empty object, fresh/missing directory and live populated states separately.
Do not replace shared hashes or restore ownership. Trace profile, ordinary,
batch/pup/scenario aliases and archive/fork transitions before choosing identity.
No namespace migration is authorized; collision evidence must remain explicit.

Use barriers to pause capture A, mutate/delete B, contend publication and inspect
final JSON, then restore and inspect actual receipts/timestamps. Add separate
atomic-restore races with direct HGETALL readers, live writers and two loaders.
Exercise every write stage, process kill, mode/umask, lost coordination/release,
incarnation replacement, copied reset and archive readback. Use real Redis only
with disposable keys, never FLUSHDB, and retain actual RQ jobs for metadata-loss
reconciliation. Run WAM/MRS/NFMS focused and required broad/static gates after
implementation. Measure common setters/startup. Retain skipped environment gates.

## Security and review

High impact due to path/inode/restore handling; preserve existing access boundaries
and require final security review. Two independent contract reviews and disposition are complete in
`20261031_contract_reviews.md`; checkpoint presentation is approved, while
explicit operator acceptance of the historic damaged-state limit remains pending. No implementation, deployment or repaired-run claim is made.

## Review corrections

Both reviewers identified cold hashes containing only NoDb lock mirrors and
last_modified as valid recovery. The canonical contract now explicitly permits
that state and preserves live unrelated values. Security review also required
the already-damaged loaded legacy hash limit to be marked as pending operator
acceptance; it is now explicit. New-reader interruption testing with a legacy
loaded marker remains mandatory and is not satisfied by documenting the limit.

## Operator approval — 2026-10-31 UTC

Operator answered "yes" to committing this reviewed checkpoint and proceeding,
including explicit reconciliation for already-partial legacy hashes with a true
loaded marker. Commit authority and that acceptance disposition are granted.
Implementation and environment validation remain pending.
