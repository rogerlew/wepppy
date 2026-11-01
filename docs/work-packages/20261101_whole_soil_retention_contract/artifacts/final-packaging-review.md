# Final retention audit packaging review

Disposition: **PASS for the reviewed public packet and private archive.** No material publication blocker found. Final publication-manifest generation and staged-byte verification remain the publishing operator's steps; this review does not bind a future manifest or itself.

The public package contains authored audit/acquisition/control helpers, declarations, findings, bounded readback summaries, provenance receipts and independent reviews. It contains no copied legacy native source/includes, native patch, object, executable, compiler output or runtime model assets. “Source-free” here means free of legacy native/model source; the authored Python helpers are intentionally public. The copied production dependency/model assets remain within the private archive.

Findings, scientific review and implementation review consistently report 39 current source horizons plus 33 synthetic cases, 60 serialized files and 120 emitted rows, with twelve explicit source exclusions/failures. Controlled single-horizon serialization is not represented as actual mapunit selection. The metadata erratum and post-execution runtime-provenance limitation remain explicit. The durable capacity contract is an evidence/change-admission contract, not a runtime correction or approval of a replacement retention law. No native invocation or production parameter change occurred in this phase.

Independently verified the compressed archive hash and size, manifest hash, complete current raw-file inventory and every archived file's hash without extracting or writing into the frozen root: **272 files, 39,774,855 uncompressed bytes, 19,784,790 compressed bytes**. No duplicate or nonregular file members were accepted. Public domain-controls, reader-controls, runtime-receipt and prior-preservation receipts are byte-identical to their archived raw counterparts. The retained prior-preservation receipt reports 5,802 unchanged files across six prior roots; this packaging review did not repeat those earlier-root scans.

## Bound archive identities

- Archive: `/wc1/runs/ro/whole-soil-retention-20261101/whole-soil-retention-checkpoint.tar.gz`.
- Archive SHA-256: `bda16b066e560379c0cd8b9e8bdb445792dc7808103bbd2cd36709b68c5adc23`.
- Adjacent manifest SHA-256: `d11955ca51d10e39e88b7974d73073369ef3833f55f331e75b2524d59f25d2f8`.
- Public archive-receipt.json SHA-256: `17316ee0114ebac70c4879b2eff51a2881a63210b73f8eccea932e5784c81bd1`.

Production source and executed readback identities remain bound in implementation-review.md and final-science-review.md. Unrelated dirty ssurgo.md and generated docs_index.json are outside this publication scope and were not modified. No raw/native writes, builder reruns or model runs were performed by this review. Reviewer writers are clear after scoped lint.
