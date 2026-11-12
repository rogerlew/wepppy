# Mistune and PyCurl remediation candidate

Status: implemented candidate pins; final common-image build, collection and
full gates remain open. Deployment resume is deferred by Roger. NFS cleanup
failures require manual recovery without waiting or retries.

## Changes and consumer evidence

Upgrade Mistune 3.2.1 to 3.4.0 and PyCurl 7.45.6 to 7.49.0 in
`docker/requirements-uv.txt`. Trials extend the exact OAuth candidate image
`sha256:e4e44d496fe0feead2b25e0b7833c86be2b321fcb5f8e9683fb9945c6db42e03`
with verified wheels, without changing the running forest environment.

Mistune trial image
`sha256:ef29937b0c6656e1df3d8bc8f1890a2bd09880e8da7d64717722cf5ea1531e79`
passes all 19 new real nbconvert consumer cases, as does the baseline. These
cover supported Markdown, all custom math forms, existing raw HTML/link policy,
and independent notebook attachments with identical filenames. The verified
upstream security unittest modules pass 35 cases; a separate pytest invocation passes all
65 inline-limit/recovery cases (unittest does not collect those functions). The old version fails the upstream
encoded-URL and reference-link growth cases; its generic deep-emphasis case
passes, so that case is not a before/after vulnerability reproduction.

The exact GHSA-6m44-fpc8-c3rq example (1,000 asterisks) completes through both
Mistune 3.4.0 HTML and the nbconvert adapter. The original repository advisory still says no confirmed patched version,
while the [reviewed advisory database](https://github.com/advisories/GHSA-6m44-fpc8-c3rq)
identifies 3.3.3 as fixed and links the upstream depth-limit repair. The retained
3.4.0 source contains that protection. Final-image evidence remains required.
nbconvert intentionally allows raw HTML and harmful URL schemes in its existing
renderer. This upgrade preserves that policy; do not claim it sanitizes notebooks.

PyCurl trial image
`sha256:0357c8f6b868dc6ce259f3f17ad6ee4f9855552a54eafe643f25ef9440156efa`
and baseline each initially pass 11 real loopback consumer cases: HTTP/HTTPS Brotli bytes,
Basic/Digest authentication, malformed and incomplete transfers, CA/hostname
verification, and Tornado CurlAsyncHTTPClient success/error behavior. Compressed
transfer failures are compatibility checks, not an exact advisory reproduction.

The wheel bundles Brotli 1.2.1. Independent security review links the exact wheel
to upstream build provenance and verifies the corrected decoder instructions.
The wheel also removes SMB/SMBS, NTLM and TLS-SRP capabilities. Repository and
installed Tornado consumer review found no use; existing HTTP/TLS consumers pass.
External custom curl callbacks are outside that demonstrated scope. Other bundled
Brotli copies remain separate open findings.

## Retained evidence and next gate

Private evidence root:
`/workdir/weppcloud-deployments/.local/dependency-security/evidence/`.
The `mistune-batch-20261112/consumer-validation/` and
`pycurl-batch-20261112/consumer-validation/` directories retain logs and SHA-256
indexes. The latter retains independent native review packet v2 with SHA-256
`d3da63c874a46dc67ff7e4087d115e8c1c709e3fbdacc37c5461e9cbda6e930c`.

Review added exact Tornado curl error numbers, explicit proxy isolation,
Tornado TLS rejection, gzip/deflate decoding, raw compressed-byte preservation
and echoed Accept-Encoding assertions. The expanded 19 cases pass on baseline
PyCurl 7.45.6 in the Mistune trial image; the PyCurl 7.49.0 trial also passes all 19 (9.95s).

These focused checks qualify the bounded candidate batch. They do not replace
clean canonical build, actual installed/cache native readback, fresh scanner
collection, reviewed dispositions, or mandatory full pytest/npm gates. MariaDB,
Pillow and unresolved native coverage remain open. No risk approval is implied.

Independent QA review closed all three focused-test gaps with no remaining
Medium/High findings: private packet `pycurl-batch-20261112/qa-consumer-tests-20261112/review-packet-v2.json`,
SHA-256 `e7d54cc5a2440b8ce8d0322835c9f4355cfc86da3db31ea46e0eadbb1519f937`.

Independent security source review reports zero Medium/High findings. Retained
packet `pycurl-batch-20261112/consumer-validation/security-implementation-review.json`
has SHA-256 `911c10e7fdcf763355d9604c87e8f2546a7cdb16091289d5e098097e3d263556`.
Its Low advisory-source clarification is incorporated above.
