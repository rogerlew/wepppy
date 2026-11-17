# ADR-0145: Bound GeoParquet upload decoding

Status: Accepted for implementation; exact-image qualification pending  
Date: 2026-11-16

## Context

GeoParquet pages, dictionaries, metadata and WKB can allocate before application
row validation. The sibling CLI must fit the accepted shape-converter envelope
without increasing concurrency, privileges or container resources.

## Decision

Use the following hard ceilings. Exceeding a ceiling rejects the whole input;
no truncation or fallback is allowed. Acceptance authorizes implementation only;
exact-image qualification remains required before release.

| Boundary | Proposed maximum | Rationale and enforcement |
| --- | --- | --- |
| Input | 100 MiB and receiving endpoint cap, whichever is smaller | Accommodates the largest existing endpoint without raising its policy; before staging |
| Footer | 1 MiB | Limits Thrift metadata; trailer checked before reader construction |
| Page header | 64 KiB | Compact-Thrift scan must stop before variable-length allocation |
| Schema | 64 scalar columns, root plus primitive children only | Bounds per-row/property fanout; reject nested schema before row reader |
| Row groups | 128 | Bounds metadata and decoder setup |
| Rows | 100,000 total | Bounded conversion scope; checked against decoded cardinality |
| Page body | 8 MiB compressed and 8 MiB uncompressed | Reject declarations before upstream page allocation; measure codec output |
| Aggregate decoded pages | 128 MiB | Checked sum of declarations plus actual decode accounting |
| Dictionary entries | 100,000 per column chunk | Also bounded by body size and physical type; before dictionary allocation |
| Geo metadata | 64 KiB | Limits JSON parsing and CRS metadata |
| WKB value | 4 MiB | Check length before geometry traversal; supports 250,000 2D vertices plus framing |
| Geometry vertices | 250,000 per feature | Inherits converter maximum; checked before coordinate allocation |
| JSON IPC | 16 MiB, depth 16, 2,000,000 values | Inherits ADR-0142; counted while serializing and before parent decoding |
| Final GeoJSON | 32 MiB and endpoint cap, whichever is smaller | Preserves receiving policy; binary compression does not bypass it |
| Parser address space | 384 MiB | Inherits ADR-0142; direct OS limit before any file parsing |
| CPU / wall | 60 / 90 seconds | Inherits existing parser process budget |
| Descriptors | 32 | Inherits existing parser process budget |
| Scratch / concurrency | 320 MiB / one request globally and per client | Inherits accepted container aggregate invariant |
| Retained attempts | 50 per run or Batch project scope | Bounds inode/receipt growth across all covered workflows; no automatic eviction |
| Retained original bytes | 1 GiB per run or Batch project scope | Aggregate complete source bytes across accepted/rejected attempts |
| Live attempt tree | 1.25 GiB per run or Batch project scope | Includes originals, receipts and rejected normalized candidates plus working reservations |
| Sensitive private archives | 1.25 GiB per run or Batch project scope | Aggregate on-disk archives containing retained attempts |
| Total retained evidence | 2.5 GiB per run or Batch project scope | Live attempts plus sensitive private archives; checked before upload/archive publication |
| Filesystem retained evidence | 100 GiB committed plus reserved across all run and Batch projects | Shared atomic admission prevents project creation from multiplying storage without bound |
| Verified-principal retained evidence | 10 GiB committed plus reserved across all projects | Account or registered-service subject budget; root/operator recovery is separately audited |
| Unattributed retained evidence | 1 GiB committed plus reserved in one shared bucket | Preserves existing anonymous/session-authorized workflows without creating a cross-project identity store |
| Filesystem in-flight reservations | 8 | Bounds concurrent worst-case source/candidate/archive reservations before filesystem writes |
| Free-space reserve | 10 GiB after all committed and worst-case reserved publication | Fail before source/archive bytes when the shared filesystem cannot retain evidence safely |
| Retention lock | one run/Batch scope, 600-second lease | Serializes quota accounting, source publication, conversion and terminal receipt/state commit |

UNCOMPRESSED and SNAPPY are the codec allowlist. Only PLAIN, RLE,
PLAIN_DICTIONARY and RLE_DICTIONARY encodings are admitted. An owned bounded
Compact-Thrift/footer/page/schema preflight must validate page version, counts,
offsets, ranges, dictionary sizes, byte lengths, per-page sizes and aggregate
decoded sizes before any upstream Parquet decoder sees the data. Preflight and
decode must use the same opened immutable regular-file descriptor, with identity
and size rechecked before decode. Direct `SerializedFileReader` use on
unpreflighted hostile bytes is forbidden. Outer resource limits contain bugs but
do not substitute for these checks. Keep inherited container and launcher
controls unchanged.

Retention accounting uses one project-scope lock across Roads, AgFields and Omni
for a run, or one Batch-project lock. While the lock is held, count live attempt
bytes, working reservations and private sensitive archive bytes from descriptor-
verified regular files. A working attempt reserves its endpoint source cap plus
32 MiB candidate output and 1 MiB receipt/diagnostic overhead until terminal.
Stop streaming and remove the partial source if actual bytes would exceed the
source, live-tree or total-evidence ceiling. Quota/free-space exhaustion fails
before converter invocation and accepted-resource mutation. Recheck lock
ownership before every terminal receipt or accepted-state commit. Never evict
older evidence automatically.

Before creating an attempt directory or private archive, use the existing Redis
authority to atomically reserve its worst-case bytes in a filesystem ledger
keyed by the configured canonical run-filesystem ID. One Lua operation checks
the filesystem, verified-principal or shared-unattributed, in-flight and project
limits and creates a 600-second uniquely owned reservation. Redis unavailable,
an absent/mismatched filesystem ID, an unreadable ledger or inability to verify
free space fails closed before bytes are read. The process then checks that
actual free bytes minus every outstanding reservation remain at least 10 GiB.
Only after this admission does it acquire the project lock; failure releases the
reservation with an owner-checked atomic operation.

A source attempt reserves its endpoint cap plus 32 MiB candidate output and
1 MiB receipt/diagnostic overhead. A private archive reserves its bounded output
ceiling. Terminal publication atomically converts reserved bytes to the exact
descriptor-verified committed charge. Deletion decrements committed charge only
after the complete terminal attempt/archive has been durably removed. Crash or
ambiguous commit conservatively retains the charge; recovery reconciles the
reservation with the receipt and verified files and never releases an uncertain
charge. Expired pre-write reservations may be released atomically; a reservation
with any published evidence requires recovery. Cross-project tests must prove
that concurrent admissions cannot breach the 10 GiB reserve and that aggregate
or principal exhaustion preserves all prior evidence and accepted resources.

## Decision Provenance

Decision Venue: Codex execution conversation, 2026-11-16, America/Los_Angeles.  
Participants Present: operator and Codex; independent reviewers assess checkpoint.  
Decision Owner: operator authorized end-to-end execution and ordinary
implementation choices; Codex accepts these bounded values after independent
correctness, operations and Daybreak security review.  
Implementer: Codex.

## Change Summary

There is no current GeoParquet input support. This adds input-specific structural
ceilings inside existing converter limits. Existing GeoJSON uploads retain their
byte policies. A compressed file can fit an upload limit yet fail conversion
because its decoded representation exceeds the separate normalization budget.

## Rationale

Small independent caps prevent one hostile count from consuming the entire
process envelope. The inherited IPC value cap also bounds aggregate coordinates
and properties. Parquet 60.1.0 otherwise attempted 64 GiB and 2 GiB allocations
from retained hostile dictionary/page declarations before application row
limits. The new caps require representative valid and near-ceiling measurements
in M1 and the exact image; acceptance is not a measured capacity claim.

## Alternatives Considered

Row limits alone cannot bound page or dictionary allocation. All default Parquet
features add unused Arrow and codec surfaces. Raising the container budget or
adding a parser service is unnecessary absent measured failure of this proposal.
Project-only retention locking was also rejected: all projects share `/wc1`, so
independent checks race and project creation multiplies the allowed evidence.
The existing Redis authority is the smallest shared atomic primitive. Its cost
is fail-closed availability plus conservative charged bytes after ambiguous
crashes; operator reconciliation is recovery, not automatic evidence deletion.

## Consequences

Valid larger files or files using other codecs/encodings are rejected explicitly.
User help must name that subset and suggest exporting a supported file; it must
not suggest that all GeoParquet files are accepted. Unknown CRS is rejected.
After quota exhaustion, uploads fail with `vector_retention_quota_exceeded` and
preserve accepted state. Root/operator recovery may export then remove one whole
terminal attempt or private sensitive archive under the same lock; partial
artifact deletion and automatic expiry are prohibited.

## Evidence

- [Dependency evaluation](../work-packages/20261116_vector_upload_normalization/artifacts/20261116_dependency_evaluation.md).
- [Independent M0 dependency/security review](../work-packages/20261116_vector_upload_normalization/artifacts/20261116_m0_dependency_security_review.md).
- [Normalization contract](../schemas/vector-upload-normalization-contract.md).
- [Inherited envelope](ADR-0142-shape-parser-ipc-bounds.md).

## Risk and Rollback Notes

M1 edge/near-limit tests and M2 exact-image aggregate qualification remain
prerequisites to release. Disable the new binary upload paths on failure; never
restore an unsafe parser or alter saved projects. No deployment is authorized.
