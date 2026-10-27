# Browse and download filesystem contract

Status: accepted by Roger on 2026-10-26; implemented and locally validated; production rollout pending.

## Authority and intent

Browse and download MUST honestly expose the actual directory contents within
the caller's authorized filesystem boundary. This includes HTML listings,
file metadata/schema inspection, direct previews and downloads, and generated
aria2c inventories. File presence is not a claim of scientific validity.

Only security and PII protections may hide or deny existing files: resource
and token authorization, filesystem containment/traversal and symlink-escape
checks, and sensitive-path/credential/PII controls. These controls must not be
used as a pretext for application freshness or result-eligibility enforcement.
Existing security/PII boundaries remain mandatory.

## Prohibited mechanisms

Do not filter, suppress, relabel as missing, or return lifecycle-based errors
for files because of stale/current status, model completion, failed or partial
runs, missing/malformed publication receipts, unsupported legacy result states,
or an active producer. Do not take model lifecycle locks merely to list,
inspect or download files. Do not add a blanket per-entry path-resolution pass
for model-result eligibility. Security checks may resolve paths where necessary
to enforce containment or sensitive-target access.

Raw files remain accessible even if their extension or former storage format
is retired. An opaque archive file is downloadable as a file; this does not
require implementing virtual archive directories. Raw bytes are not hidden
because an optional formatted preview cannot parse them.

Explicit user-selected search, sorting, pagination and representations are
presentation controls, not implicit availability filters. They must retain
access to the complete authorized inventory. Missing files return the normal
not-found response; read/parse/I/O errors remain honest errors, never silent
empty success or false absence. Listings are observations, not transactional
snapshots: producers can change a file between listing and reading.

## Failure observability

Browse, manifests and download services must return meaningful failure responses.
Known required-secret failures identify the configuration variable and whether it
is missing, unreadable or empty, with an operator recovery instruction. Do not
return secret values, secret file paths or arbitrary exception text. Unexpected
failures include a safe explanation and a request ID linked to full server logs.
Machine 500 responses use `error.message`, `error.code`, `error.details`, and
top-level `request_id`; the same ID appears in `X-Request-Id`. Browser error pages
also display the safe explanation and ID. Existing non-500 access decisions stay
unchanged. Once streaming headers have been sent, a failed stream cannot become
a new JSON response: clients must treat interruption as failure.

Bootstrap clients must display the returned explanation and reference, stop on
failed manifest retrieval, never consume a failed/stale manifest, and propagate
nonzero transfer exits. This applies to Windows and shell wrappers and the legacy
Python archive client. A bare status or apparent empty success is insufficient.
Bound diagnostic bodies; do not print authorization headers or tokens.

Rationale (2026-10-27): a configuration fix alone left the server-to-user failure
path unobservable and prolonged diagnosis. Safe classification plus correlated
logs preserves diagnostics without exposing private exception contents.

## Model consumers and previews

Roads and other model-specific reports, computations, query-backed scientific
views and dashboards may enforce their own current-result requirements. That
policy MUST NOT be pushed into generic browse/download or their manifests.
D-Tale opened from a physical file follows ordinary file-viewer semantics;
Roads receipts cannot gate it. Existing source-byte consistency checks prevent
a lazy viewer mixing generations and remain distinct from model freshness.
An eager viewer remains an explicitly acquired snapshot until reopened.

## Required regression evidence

Exercise existing files with no Roads state, empty directories, legacy outputs,
invalid/stale receipts, active lifecycle locks and permitted symlinks. They must
remain listed and downloadable. Compare manifest paths and downloaded bytes
with actual filesystem contents. Separately verify denied credentials,
traversal, out-of-bound symlinks and sensitive paths still fail. Include a large
ordinary project inventory to catch per-file model-admission amplification.

## Rationale

The October 22 Roads admission mechanism applied realpath and lifecycle checks
to generic browsing. On October 26 a 155,573-file historical manifest collector
took 2.679 seconds, while the new visibility helper alone took 1.514 seconds for
1,000 files. The operator explicitly rejected both the semantic hiding and its
cost. Filesystem access is for inspection and diagnosis, including failed or
stale artifacts; it must not certify results on the user's behalf.
