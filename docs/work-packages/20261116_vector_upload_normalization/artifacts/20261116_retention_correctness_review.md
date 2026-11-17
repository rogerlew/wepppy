# Original-upload retention correctness review

Date: 2026-11-16  
Reviewer: independent `retention_correctness_review`  
Scope: operator-selected retention of complete original vector uploads,
failed/hostile quarantine, SHA-256 provenance and abuse-review identity  
Initial verdict: **HOLD — two High and three Medium findings**  
Focused remediation verdict: **PASS — no unresolved High or Medium findings**

## Findings

| ID | Severity | Finding | Required closure |
| --- | --- | --- | --- |
| VUN-RET-COR-01 | High | The contract says the entire `upload_attempts` subtree is sensitive, but Omni originals live under `_pups/omni/contrasts/_uploads/<uuid>`. The actual run and Batch browse/download handlers authorize anonymous access for public resources (`browse.py:_handle_browse_request`, `browse_batch_*`, `_download.py:download_with_subpath`, `download_batch_with_subpath`, and `aria2c_spec`). A name-based guard for `upload_attempts` would miss Omni and public file inventories; a generated project archive can also contain the evidence and then be downloaded as an ordinary project file. | Define one canonical sensitive-attempt classifier covering all four exact roots and descendants, including receipts/candidates/originals. Require it at every browse tree, direct download, `aria2c.spec`, files/report/schema/D-Tale/GDAL/preview entry point and Batch equivalent. Define how archives containing sensitive attempts are marked and denied to anonymous/public-run download while remaining available to an authenticated owner/root. Test every exact root, root listing, guessed direct URL, generated archive and restored archive. |
| VUN-RET-COR-02 | High | Per-request byte limits do not bound persistent evidence. A permitted user can submit unlimited failing 10/30/100 MiB files and exhaust run/host storage. The archive implementation counts/disk-preflights the current tree but there is no upload-attempt count or aggregate retained-byte quota in the reviewed source or contract. | Add an ADR-backed per-project/per-workflow retained-attempt count and aggregate-byte budget, with atomic admission under a shared lock. At capacity, reject before converter work and before accepted-resource mutation with a stable quota error; do not delete older evidence silently. Define operator/user cleanup authority and prove concurrent attempts cannot exceed the budget. Include retained originals, candidates, receipts and archive overhead in the aggregate invariant. |
| VUN-RET-COR-03 | Medium | The receiving boundary hashes the retained project file, but the converter contract does not require shape-converter to hash the exact request bytes and return that digest for comparison. “The same immutable bytes are sent” is an assertion across HTTP/process boundaries, not executable provenance. A receipt could bind canonical output to the stored original while the converter processed different bytes. | Shape-converter must compute `source_sha256` and `source_size` while staging its own complete request snapshot and return them in the strict response. The receiver must compare them with its descriptor-bound project artifact before accepting canonical output or writing a terminal accepted receipt. Add mismatch tests; a mismatch is a stable converter-integrity failure and leaves the prior accepted resource unchanged. |
| VUN-RET-COR-04 | Medium | Attempt publication is underspecified. The contract does not say when an initial receipt exists, what happens if original or terminal-receipt persistence fails, or how an orphan original is classified after interruption. That conflicts with the artifact-observability requirement for explicit working/failed states. | Atomically create a private attempt directory and `normalization.json` with `status=working` before conversion. Publish the complete original and descriptor/hash fields before invoking the converter. Replace the receipt atomically with terminal `accepted`/`rejected`/`incomplete`; a receipt-write or original-persistence failure must stop before accepted workflow mutation. Recovery/reload must classify an interrupted working receipt without parsing/reusing its original. |
| VUN-RET-COR-05 | Medium | The receipt supports investigation while the project exists, but the uploader may delete the project or its evidence before review. The contract correctly excludes a new surveillance/ban store, yet “evidence for ... account-governance action” can be read as durable ban evidence. | State that project artifacts are project-lifetime evidence only and cannot independently prove a durable ban case after authorized deletion. Name the existing operator audit/log record, if any, that may retain the attempt ID, actor ID, source SHA-256, error ID and action without raw bytes. If no such governed record exists, limit this package’s claim to owner/operator review while the project survives and defer durable ban evidence to a separate access-governance change. |

## Correct design elements retained

- The original upload is stored with a terminal `.upload` suffix, so the current
  browse download code will not enter its extension-triggered Parquet CSV/filter
  branches. The contract must still enforce path-based download-only behavior;
  filename neutralization alone cannot cover schema, D-Tale, GDAL, archive or
  future format sniffers.
- Complete within-limit uploads receive a full-file SHA-256. Oversize partial
  bytes are deleted and never mislabeled with a prefix digest. Authentication and
  multipart failures before an authorized project context remain operational
  logs rather than invented project artifacts.
- Receipts minimize identity data to a verified account/service principal and
  exclude credentials, raw claims, session IDs and client IP. This is sufficient
  for account correlation when a verified human ID exists. Anonymous attempts
  cannot support account banning and the contract says so.
- Quarantined evidence cannot replace accepted workflow state or become an
  automatic retry input. A retry is a new attempt through every admission and
  parser control. Existing projects need no migration.
- Automatic banning, IP blacklists and a new cross-project evidence database are
  correctly outside this work package. Any ban remains a separate human-reviewed
  access-governance mutation with its own audit contract.

## Required executable evidence

Before retention can pass M3–M5, tests must prove complete-byte/SHA equivalence
from project original to converter snapshot and canonical output; interrupted
working-attempt recovery; original/receipt persistence failure before accepted
mutation; aggregate-quota exact edge and concurrent limit behavior; private file
and directory modes; owner/root download with octet-stream, attachment and
`nosniff`; public denial through every route and generated archive; byte- and
mode-preserving archive/restore; and a restored quarantined file that remains
inert. A successful conversion, file existence, or receipt text alone is not
artifact acceptance.

## Verdict

The operator’s decision to preserve originals and hostile failures is compatible
with artifact observability and can provide useful project-lifetime review
evidence. The current amendment is not ready for the M0 ancestor because public
access coverage and cumulative persistent-storage admission are incomplete.
End-to-end source digest reconciliation, crash-state publication and the limited
durability of ban evidence also need canonical disposition. No runtime or release
approval is given by this review.

## Focused remediation re-review

The canonical amendments close the original five findings:

- **VUN-RET-COR-01 resolved.** All workflows now use exact
  `vector_upload_attempts` roots, and the shared normalized sensitive-path
  classifier is required across browse trees, direct download, files/report,
  schema, D-Tale, GDAL, diff, `aria2c.spec`, Batch/group variants and future tool
  dispatch. Private archives and SHA-bound sidecars remain sensitive even after
  live attempts are removed. Public access is explicitly denied.
- **VUN-RET-COR-02 resolved at contract level.** ADR-0145 now bounds attempts,
  source bytes, live evidence, private archives, total evidence and post-write
  free space under one run/Batch retention lock, with working reservations,
  stable 507 failure, no automatic eviction and whole-attempt operator cleanup.
- **VUN-RET-COR-03 resolved.** Shape-converter computes size/SHA-256 from its own
  staged request, and the receiver compares both with the already-open verified
  project original before receiving validation, accepted mutation or terminal
  acceptance. Digest mismatch has a stable 502 contract.
- **VUN-RET-COR-04 substantially resolved.** The working/prepared/terminal state
  machine prevents accepted mutation before complete source/provenance
  publication and recovers uncertain post-mutation receipts without parsing or
  retrying the original. One pre-working interruption gap remains below.
- **VUN-RET-COR-05 resolved.** A minimized structured security event follows
  existing operational-log retention; the contract explicitly limits project
  evidence to project/archive lifetime and does not claim permanent ban evidence.

### Remaining finding

| ID | Severity | Finding | Required closure | Status |
| --- | --- | --- | --- | --- |
| VUN-RET-COR-06 | Medium | The receiver creates and streams into a new attempt directory before it atomically publishes the first `status=working` receipt. A process crash, host loss or write failure during that stream can leave a UUID directory containing a partial `.upload` file with no receipt. The stated recovery rules cover only working/prepared receipts, so this artifact has no explicit status, quota-release rule or safe reload classification. | Publish an initial bounded `status=working`, `stage=receiving`, source-hash-absent receipt immediately after the private UUID directory is created and before streaming source bytes. Atomically replace it after the complete source is fsynced with `stage=source_stored`, size and SHA-256. Recovery treats missing-receipt UUID directories and stale receiving receipts as `incomplete`, removes only a provably partial source or retains it as explicitly partial evidence according to one canonical rule, releases its reservation under the retention lock, never hashes it as complete and never invokes a parser. Add crash/failure tests before first byte, mid-stream and between source fsync and receipt replacement. | Resolved: canonical contract now publishes `receiving` plus reservation before reading bytes, atomically publishes `source_stored` only after source fsync/rename, and defines stale receiving and missing/corrupt-directory recovery without parser use or complete-source hash claims |

The private archive, quota, digest, actor-minimization and project-lifetime abuse
claims are coherent after remediation. VUN-RET-COR-06 is closed: a private UUID
directory receives an atomic `receiving` receipt and reservation before the first
source byte; the complete fsynced/renamed original is followed by an atomic
`source_stored` receipt with full size/SHA-256 before converter work. Stale
receiving attempts retain partial bytes as explicit incomplete evidence with no
complete-source digest and release their reservation under the recovered scope
lock. Missing/corrupt receipt directories count against quota, are never parsed,
and require whole-directory root repair/removal.

No High or Medium correctness finding remains. Implementation still needs the
executable evidence listed above and the parallel security verdict. This is M0
contract approval, not runtime or release approval.
