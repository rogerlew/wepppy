# Run sync contract

## Replacement semantics

Implementation conformance: implemented locally and regression-tested
(2026-09-09); live browser workflow validation remains pending.

A requested sync treats the source manifest as authoritative for listed files.
Before payload downloading, validate the entire manifest and all destination paths.
Cleanup must be limited to manifest-listed files under the resolved local run
root. Reject absolute paths, traversal, symlink destinations or ancestors,
directories at file destinations, duplicate destinations, and collisions between
payload names and generated `.aria2` sidecars before deleting any file.
These checks apply to both payload and sidecar paths; existing targets must be
regular files, with directory ancestors. Reject ancestor/descendant
conflicts across the combined set (for example `a` and `a/b`, or `a` and
`a.aria2/b`), even when those paths do not yet exist.
The downloaded manifest itself must not be a payload destination. Manifest
staging must use safe exclusive creation before writing remote bytes; do not
follow a pre-existing staging symlink. Reserve `.aria2c.spec` and generated
control paths from payload use. Source manifests containing these collisions
fail explicitly, even if produced by an older source export.

An empty manifest is a successful transfer no-op and leaves local payloads
untouched; normal provenance/registration may follow. Accept a final manifest
record without a trailing newline.

For each listed payload, remove its existing `.aria2` control file and associated
partial payload before transfer. Missing payloads or control files are normal.
Completed files may be retained only when their content matches an explicit
supported source checksum; size alone is insufficient. Without a source checksum,
download the listed file fresh, replacing any existing copy. Do not resume bytes
from a previous sync attempt. Do not delete unlisted local files.

The current browse manifest contains URLs and `out` paths without checksums, so
all listed payloads must be refreshed. Adding source checksums is outside this
change. Unsupported manifest directives must fail explicitly before cleanup;
do not pass destination-changing directives through unchecked.

Rationale: stale resume metadata caused `climate.log` total-length mismatch in
job `13783040-6204-4ad7-a699-1be9ea698923`. Repeated resume attempts cannot satisfy
replacement semantics. A size-only shortcut also misses same-size content edits.
Fresh transfer avoids that ambiguity without changing the source service.

## Failure and compatibility

This is a file-by-file pull, not a transactional snapshot or deletion mirror.
An interrupted attempt can leave missing or partial listed files; a retry starts
those transfers fresh. Permission, invalid-manifest, and transfer errors fail
the job explicitly. No registration or COMPLETE event follows failed transfer.
Source changes during transfer may still cause failure; no automatic retry loop
beyond the existing downloader retry policy is added.

Authentication, source token handling, queue wiring, path normalization after
transfer, and the [RQ response contract](rq-response-contract.md) remain unchanged.
`.nodir` archives remain opaque manifest files per the
[NoDir contract](nodir-contract-spec.md#aria2cspec).

## Regression obligations

Exercise real filesystem cleanup and real aria2 transfers against a local HTTP
fixture: absent files, empty files, matching completed files without checksums,
same-size changed files, different-size files, orphan control files, and the
incident's stale partial/control pair. Verify unlisted files survive. Invalid
paths, staging and sidecar symlinks, directory targets and sidecar collisions must fail before any
cleanup. Confirm failures cannot register success. Before rollout, exercise the
browser sync workflow with the actual worker identity and mounts.
