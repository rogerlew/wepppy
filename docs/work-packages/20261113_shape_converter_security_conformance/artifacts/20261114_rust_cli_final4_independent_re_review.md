# Rust CLI final-4 independent re-review

Date: 2026-11-14

Candidate source: `a6be89141c234727bb5d89aa5a4b3c2ec51dc284`

Exact image:
`sha256:b9e78b16718911ff16dc213b27d719477d95880ebcdca500cc858cea13c05ae8`

Evidence commit: `26d907667`

## Verdict

PASS. Independent code, correctness, QA, operations, and security reviewers
reported zero Critical, High, Medium, or Low findings.

| Review lane | Verdict | Key independent evidence |
|---|---|---|
| Code | PASS | Repeated-cancellation child gone; render failure, topology downgrade, orphan stop, and scoped preset failure gates passed. |
| Correctness | PASS | Three-cancellation and timeout/cancel probes preserved canonical outcomes only after the live process group disappeared; retained semantic parity passed. |
| QA | PASS | 296 shape tests; 64 deploy/Compose tests with 3 environment skips; exact image and hardening independently reconciled. |
| Operations | PASS | All full-preset render/contract failures use secure-or-stop; read-only/targeted failures do not mutate; exit-88 runbook is catalogued. |
| Security | PASS | Former High findings reproduced as closed; exact image and unchanged scanner inventory accepted; SEC-RUST-01 through SEC-RUST-04 remain closed. |

## Closed final findings

- Repeated cancellation cannot interrupt parser process-group termination or
  release request/scratch ownership early.
- Full-preset service rendering, build-set derivation, expected-service
  derivation, and runtime validation fail closed through independent label-based
  discovery, stop, and stopped-state verification.
- Dirty topology cannot downgrade full deployment intent into worker mode.
- Missing service definitions cannot hide a previously running converter.
- Preset-query failure during read-only or targeted work cannot stop the
  unrelated converter; mutating paths hold the deployment lock.
- Retry helpers preserve actual command failures.

## Residual risk and disposition

The Rust CLI shares the API container's UID, mounts, and internal-network
authority. It is a bounded parser process, not a second sandbox. All reviewers
accepted this explicit residual because the implementation removes GDAL/Fiona,
uses strict data-only IPC, enforces process and aggregate limits, admits one
conversion at a time, hardens the container, and fails closed during release.

Issue #656 is ready to close as superseded by removal of the GDAL/Fiona failure
class. Closure must not claim second-sandbox conformance. No issue mutation,
image publication, or production deployment was performed by this review.

Production rollout remains separately authorized and must retain installed
preset output, clean-input evidence, the deployed image ID and sidecar revision,
public readiness and conversion readback, unrelated-service health, and the
exit-88 recovery receipt.
