# Contract decision — 2026-09-11

Base: `e534fab6c`. Operator reports failed dNBR upload and requires visible job
ID, restored failure on refresh, and separated status/timestamps. This repair
is authorized by that request; no new user-facing workflow or model policy.

UI: conformance repair to shared controller contract and PFDF reload section.
Internal raster delta: the local M1 boundary may ignore only a regular,
bounded statistics-only PAM .aux.xml after structural validation. Disable PAM
for decoding; reject entities, georeferencing, NoData, scale/offset, references,
and any other metadata. Uploaded-raster boundary remains self-contained-only.
Production stages a self-contained DEM before invoking the upload decoder.

Why: standard project DEM generation writes inert statistics, so rejecting it
blocks the promised project-watershed workflow. Blanket sidecar allowance or
silently ignoring all metadata would change scientific inputs and is rejected.

Compatibility/regression plan: no persisted field removal or rename; add the
prepared DEM to accepted artifact signatures. Existing failed attempts can be
retried through the existing action. Local M1 API retains all numeric, mask,
encoding and reference restrictions. Test valid/empty/malformed/hostile PAM,
unchanged grid/support/samples, strict uploads, failure reload, linked job IDs,
status layout and retry via the actual proxy/RQ workflow. No scientific
parameterization or queue-edge change; no ADR needed for this representation fix.

Review disposition: pending two independent read-only reviews. Implementation
conformance for internal raster amendment is pending.

## Independent review disposition

Both reviews accepted before backend implementation. `contract_correctness`
identified ambiguity in cache freshness and scope; canonical docs now explicitly
apply the exception to trusted local M1 rasters and exclude validated inert
statistics from expected hashes/scientific freshness. Uploaded companions remain
hashed. Reviewer accepted that resolution. `contract_security` accepted the
bounded schema with PAM disabled and unchanged upload restrictions; requires
parser attack cases, cache invariance, parity and artifact propagation evidence.
No blocking findings remain. See final validation for implementation review.
