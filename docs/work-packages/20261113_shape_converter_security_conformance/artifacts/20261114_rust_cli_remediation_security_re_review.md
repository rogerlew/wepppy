# Rust CLI remediation security re-review

Date: 2026-11-14

Reviewer: independent security reviewer

Review target: `2bbf8498e`

Verdict: **FAIL / HOLD** for rollout and #656 closure. Critical 0; High 0;
Medium 4; Low 0.

## Findings

| ID | Severity | Finding | Required action |
|---|---|---|---|
| SEC-RR-01 | Medium | The aggregate memory invariant is a default, not an enforced contract. Environment overrides can restore concurrency above one or exceed reviewed parser ceilings without startup failure. | Reject unsafe effective values during startup/deploy or hard-cap production values at the ADR maxima; add override-rejection tests. |
| SEC-RR-02 | Medium | Rust validates paths/sizes and scans hostile SHP records before applying address-space, CPU, and core limits; the alignment scan checks the feature limit only after allocating the full offset vector. | Apply limits immediately after argument parsing and stop scanning when `max_features` is exceeded; retain a constrained large-record regression. |
| SEC-RR-03 | Medium | The exact scan contains 72 Medium records / 42 unique IDs without traceable dispositions. | Map every unique Medium advisory to package/path, reachability class, owner, rationale, and remediation or acceptance status. |
| SEC-RR-04 | Medium | Fail-closed takedown has no retained fault-injection execution test. | Exercise readiness/build failure, stop verification, stop-failure detection, and unrelated-service preservation in the deploy harness or authorized production-equivalent dry run. |

## Prior finding disposition

- SEC-RUST-02 provenance: closed.
- SEC-RUST-03 inherited internal-network contract: closed.
- SEC-RUST-04 path confinement: closed.
- High scanner findings: prior non-reachability dispositions remain acceptable
  for the unchanged exact-image classes.
- Same-container UID/mount/internal-network residual: acceptable as documented;
  it is not a second sandbox.
- SEC-RUST-01 aggregate memory: remains open because effective production
  overrides are not constrained to the reviewed envelope.

Focused rerun: 96 passed, 3 environment skips.
