# Independent Rust CLI Code Review

Date: 2026-11-14

Reviewer: independent `reviewer` agent

Commit: `fe5ac7c1c`

Verdict: **FAIL / HOLD**. Critical 0; High 1; Medium 4; Low 1.

## Findings

| ID | Severity | Finding | Required action |
|---|---|---|---|
| ICR-01 | High | `convert_uploaded_archive()` calls synchronous parser execution, which blocks the sole ASGI worker in `Popen.communicate()`. Task/client cancellation cannot run until the call returns; only the child timeout kills the process group. | Make parser waiting asynchronous with cancellation-safe process-group cleanup and add real concurrent-health and client-cancellation regressions. |
| ICR-02 | Medium | The Rust parser zips shape iteration with DBF rows, then compares only the truncated count with SHX. A direct two-SHP-record/one-SHX/one-DBF probe exited zero and silently emitted one feature. | Exhaust all streams, require exact cardinality, validate SHX offsets/lengths and SHP record numbers, and retain mismatch regressions. |
| ICR-03 | Medium | When `.cpg` is absent, the DBF language-driver byte is ignored and Windows-1252 is assumed. Valid DBFs declaring another LDID can be corrupted or rejected. | Add tested LDID mapping or explicitly reject unsupported/ambiguous encodings and document the narrowed contract. |
| ICR-04 | Medium | Production Compose defaults parser source revision/release label to development values, and the canonical deployment does not inject the post-pull revision. | Inject and validate the released commit and label through the canonical build/deploy path. |
| ICR-05 | Medium | Canonical deployment does not consume the parser readiness attestation; the service has no Compose healthcheck and Caddy waits for `service_started`. | Add a readiness healthcheck or equivalent blocking deploy preflight with rollout-contract coverage. |
| ICR-06 | Low | Runtime provenance binds the binary but does not validate internal source-manifest and Cargo-lock relationships. | Strengthen relationship validation or narrow the readiness claim. |

## Direct evidence

- `cargo test --locked`: 5 passed.
- `cargo clippy --all-targets --locked -- -D warnings`: passed.
- Independent malformed alignment probe reproduced silent feature loss.

#656 cannot close while the High and Medium findings remain.
