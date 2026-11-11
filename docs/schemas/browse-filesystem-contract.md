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

## Pickle artifacts

Status of the 2026-11-10 Pacific amendment: approved restriction; implemented and locally validated; deployment pending.

Existing `.pkl` and `.pickle` artifacts, case-insensitively, MUST remain listable
and downloadable byte-for-byte within existing authorization, containment and
sensitive-path controls. They MUST NOT advertise preview or D-Tale actions in
directory listings or file metadata. Direct browse preview and browse-to-D-Tale
requests MUST return HTTP 415 before reader invocation, NoDir materialization,
or outbound loader calls. The D-Tale internal loader MUST also return HTTP 415
and MUST NOT register or call a pickle reader. This applies to physical files and any supported virtual file representation; raw authorized download remains available,
including existing raw query/header byte-delivery modes. Representation or
preview requests return 415; they must not fall through to generic text rendering.
Opaque retired archives remain downloadable as whole files; this restriction
does not restore virtual archive traversal or replace existing retirement errors.
Existing authentication, authorization and containment decisions retain
precedence, and missing files retain their normal 404 response.

This is a security exception for interactive parsing, not a visibility or
model-lifecycle restriction. Pickle loading can execute code, while serving the
original bytes does not deserialize them. CSV, TSV, Feather, Arrow and Parquet
behavior remains unchanged. No fallback parser, converter, scanner, feature
flag, or migration is introduced. Application-owned internal serialization is
outside this bounded contract. Restoring interactive pickle loading requires a
new approved security decision. New Bootstrap admission follows the
[Bootstrap Git input contract](bootstrap-git-input-contract.md).
The [D-Tale generation contract](file-dependency-freshness-contract.md#d-tale-dataset-generations-implemented)
explicitly permits this bounded reader removal; its source-consistency rules
for supported formats remain unchanged.

Regression evidence must cover both suffixes and case variants, absent preview
metadata and links, 415 responses with zero reader/materializer/forwarder calls,
byte-identical legacy downloads, and supported-format controls. Use inert bytes;
never execute a pickle payload as a test. The operator waived full Python and
frontend suites for the 2026-11-10 restriction in favor of focused Bootstrap,
browse/files, D-Tale, stub, documentation and source-search checks. Separately
authorized scoped deployment evidence is required for a rollout claim.

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
