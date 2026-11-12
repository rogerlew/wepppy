# Isolated OAuth candidate validation

The independently reviewed contract ancestor is `2cae5053f`. Implementation
is retained in detached checkout
`/home/workdir/wepppy-security-oauth-candidate-20261112`, revision
`afe6e7264b469f3cb1bbf111fe4b1473ffe86466`. It has not been integrated into the
running forest dependency environment. Correctness, security, QA and operations
reviews approve bounded candidate testing; none grants M4 or rollout acceptance.

The clean no-cache canonical production/wepp1 Compose build passes in 658.72s
with unchanged pinned base/vendor inputs and UID/GID 1002:130. Image ID:
`sha256:e4e44d496fe0feead2b25e0b7833c86be2b321fcb5f8e9683fb9945c6db42e03`.
Runtime readback confirms exactly two distribution changes from the parser image:
Authlib 1.6.12 to 1.9.1 and joserfc 1.8.0 added. System GDAL remains 3100300;
Rasterio's bundled GDAL remains 3.8.4. No native or service-token migration is
inferred from this OAuth change.

The prebuild runtime passed 50 callback tests in 10.22s. The exact clean image
then passes the same 50 tests in 9.71s, including real Authlib state, PKCE,
signature and claim verification, OAuth-only success and 15 invalid-token cases.
HTTP transport and identity side effects are instrumented; the verifier itself
is real. This is not a live third-party-provider or complete application test.

The first standard isolated stack startup failed its unchanged PostgreSQL health
window during overlapping image export and about 40% host I/O pressure. Retain
that 73.25s failure. After both exports complete and pressure subsides, the same
standard stack starts in 16.89s without threshold changes; tests pass and exact
project cleanup exits zero. Both attempts have separate receipts.

Private evidence is under `evidence/oauth-batch-20261112/`: build receipt/log,
`runtime-version-delta.json`, `focused-candidate-receipt.json` (failed startup),
`focused-retry-candidate-receipt.json` (passing), and the corresponding logs.
The security review SHA-256 is
`4075036eae7ad0a48ba6684fb9d6c53054745eee04c3a1323818174165066ba2`.

Fresh collection completes with zero analysis errors and zero artifact-identity
mismatches. All 704 Python metadata locations, 432 Debian packages and 3,421
native paths reconcile; all 1,316 available SBOM native digests match, and all
15,574 scientific files pass manifest readback. The manifest SHA-256 is
`4f637d13b01ff3a1715c9b7b5647efbdf89730cc2509f7ab77985dfef234935e`;
scan SHA-256 is
`ab874b0768676d4e51843ee9870becbc6ed7b9a7bbf06fb6451d51bb88e2ccc1`.

Authlib and joserfc have no findings; all 18 previous Authlib rows are removed.
The candidate retains 2,998 matches, 330 ignored matches and 19 npm findings.
Maximum alias severity counts for the Grype rows are 126 Critical, 1,198 High,
1,378 Medium, 245 Unknown, 372 Low and 9 Negligible. These are raw rows, not
unique vulnerabilities or approved dispositions.

There are still 2,105 native coverage gaps. Nineteen rebuilt native files at
stable paths have different hashes despite unchanged package versions; uv cache
paths also change. Retain `native-rebuild-delta.json`; prior-image ownership
proposals cannot become approvals for this image merely by version matching.
The actual evaluator with empty approvals rejects this bundle for
`unresolved native executable coverage`; `evaluation.json` retains that result.

Complete advisory/native coverage, actual CI handoff, canonical deployment
integration, final clean image and exact full pytest/npm gates remain required
before M4 acceptance. No policy exception or rollout was authorized.
