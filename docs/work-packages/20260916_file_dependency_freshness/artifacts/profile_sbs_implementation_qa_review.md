# S02 final implementation QA and performance

**Scoped quality and component performance: PASS.** The actual implementation
passes all 27 retained gates on two real uploaded SBS files and the labeled
16 MiB stress fixture. This closes the prototype's missing complete first-capture
measurement. It does not establish live HTTP/RQ/profile playback acceptance.

## Actual implementation evidence

`benchmark_profile_sbs_implementation.py` and
`profile_sbs_implementation_performance.json/.log` retain samples, byte counts,
source hashes, limits and wire verification. Fixtures, captured event history,
receipts, config seeds and module snapshots are browsable at
`/wc1/batch/qa-profile-sbs-implementation-1b0e41d3d584/benchmark-manifest.json`.
All original fixture/named config versions and hashes, and all measured source
modules, remain unchanged. Identity is UID 1000/GID 993.

The benchmark executes real copied NoDb owner discovery and
`ProfileAssembler.handle_event`, including event append, configuration, legacy
copies, descriptor-bound event copies, content verification and status/receipt
publication. First capture uses three separately named new owners/drafts per
fixture; setup/copy preparation is outside the timed callback, while actual
owner hydration is inside. Every fixture includes the real Grizzly
34,830-byte `config.cfg`, plus the normal default/active config work. Rattlesnake's
original lacks that file; using the real Grizzly config here is explicitly a
representative configured-capture workload, not a claim about its original data.

Playback invokes actual `_execute_request`, event receipt/byte acquisition,
form reconstruction and inherited `requests.Session.request` preparation. A
local `send` override returns only after the real multipart body is constructed;
it performs no network request. This measures the specified dispatch-preparation
boundary, including selected-file descriptor/path checks, rather than a
hand-built multipart prototype. Pairing, promotion and error propagation have
separate independent correctness coverage.

## Complete measured means

| Operation | Grizzly 599,196 B | Rattlesnake 747,242 B | Stress 16,779,862 B | Gate real /stress |
| --- | ---: | ---: | ---: | ---: |
| First configured controller/draft capture | 107.00 ms | 109.14 ms | 545.60 ms | 125 /550 ms |
| Established capture, cold digest | 49.41 ms | 53.33 ms | 342.29 ms | 100 /450 ms |
| Established capture, settled digest | 40.80 ms | 53.90 ms | 291.74 ms | 100 /450 ms |
| Complete verified dispatch through Requests preparation | 8.78 ms | 8.51 ms | 95.51 ms | 20 /150 ms |

First capture uses three samples; established capture and dispatch use five per
fixture/state. **Stress first-capture margin is small:** mean 545.60 ms against
550 ms, with individual samples 525.27–582.45 ms. The reviewed gate is a mean;
this does not claim every first capture completes under 550 ms. Retain that
sensitivity and remeasure if further work enters this boundary. No samples were
dropped and no threshold was changed.

Captured source/file verification reads three payload equivalents while the
source digest is cold and two when settled. Legacy kernel fast copies are
additional logical transfers, outside Python read counters. Dispatch reads
exactly one retained payload in every sample; no extra payload read was hidden
behind a pathname reopen. Parsed actual multipart bodies have exact source
SHA-256, field `input_upload_sbs`, filename `input_upload_sbs.tif` and MIME
`application/octet-stream`.

Python allocation peak for stress dispatch is 35,662,779 bytes, about 2.13
payloads, consistent with existing Requests buffering. This is not process RSS.
The ordinary digest cache remains bounded and its existing admission behavior
is used; there is no added file-size cap or transport.

## Retention cost and quality

Eleven same-byte events in the final stress draft retain 218,177,657 bytes of
seed data: distinct event copies plus the existing named/canonical snapshots and
small configuration/receipt/status files. Equivalent real-upload drafts retain
7.83/9.75 MB. Aggregate profile seed growth is therefore material even when
individual uploads are below 50 MB. Follow the existing profile seed/LFS-review
guidance when promoting large profiles; immutable event evidence must not be
discarded or silently deduplicated to hide that cost. Benchmark files remain in
the disposable artifact tree, not as large repository blobs.

The new `sbs_seed` module keeps event path derivation, descriptor lifetime,
opened-byte validation and receipt publication cohesive. `SbsSeed` explicitly
carries the verified bytes into existing Requests encoding. Capture expectation
is recorded in the original append, so failures before directory creation remain
distinguishable from unmarked history. Failed/incomplete/mismatched new evidence
uses the request failure boundary rather than a canonical-seed fallback.

Meaningful independent coverage includes real append and promotion, paired
`PlaybackSession.run`, actual Requests encoding, duplicate IDs, source and
receipt generation drift, malformed/failed evidence and path/access authority.
Correctness reports 11 passing probes and security revision 3 reports 8 passing
probes; the root's combined Geneva/profile/archive suite has 135 passes. Those
counts cover distinct scopes and are not summed as one S02 suite. Actual
archive producer/restore security evidence is separately owned.

A small nonblocking typing follow-up remains in `playback.py`:
the form-file annotations still describe the first tuple member as only `Path`,
while the implementation also intentionally returns `SbsSeed`. Declare that
union when touching this interface next, so static readers do not assume every
member supports path operations. Runtime discrimination and current behavior
are clear; this does not invalidate measured byte preparation.

## Limits and pending acceptance

Inputs are copied and filesystem pages are warm. First owner/draft initialization
is measured; process imports precede timing. No cold-storage/percentile or full
HTTP latency guarantee is inferred. The stress TIFF is derived from real class
pixels and labeled synthetic, not represented as an actual user upload.

Actual authenticated `wctl run-test-profile` on a disposable original and sandbox,
normal HTTP/RQ behavior, final service identity/group parity and package-wide
runtime acceptance remain pending their dedicated evidence. Neither the local
prepare-only boundary nor the passing scoped tests substitute for that workflow.
