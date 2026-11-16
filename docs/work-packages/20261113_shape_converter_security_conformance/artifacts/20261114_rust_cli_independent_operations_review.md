# Independent Rust CLI Operations Review

Date: 2026-11-14

Reviewer: independent `ops_security_control_agent`

Commit: `fe5ac7c1c`

Verdict: **FAIL / HOLD**. High 2; Medium 4.

## Findings

| ID | Severity | Finding | Required action |
|---|---|---|---|
| OPS-01 | High | Canonical deployment can succeed without proving parser readiness: no shape-converter healthcheck or deploy canary consumes `/health/ready`. | Add a production healthcheck/canonical parser canary and make activation fail before success or pruning. |
| OPS-02 | High | Promised image rollback is not retained or executable. Deploy rebuilds `wepppy-shape-converter:latest`, lacks a rescue tag/config, then runs `docker system prune -a`. | Retain the running image and resolved configuration across pruning; document and test shape-converter-only restore or disable behavior on forest1. |
| OPS-03 | Medium | Production provenance defaults to development labels and does not identify the released source. | Inject and reject missing post-pull commit/release identity. |
| OPS-04 | Medium | Builder/runtime APT repositories and sidecar wall time are mutable, so the exact image is not rebuild-reproducible. | Use a dated Debian snapshot or fixed base and a deterministic release timestamp. |
| OPS-05 | Medium | The 72 Medium scanner records lack the required traceable disposition. | Disposition each unique Medium or a clearly traceable class with reachability, owner, rationale, target date, and acceptance. |
| OPS-06 | Medium | Public `/health/ready` synchronously launches a parser on every call outside conversion abuse controls; with one worker it is an availability surface. | Make the deep probe internal/startup-only or cache and bound it. |

## Positive controls

Production resolves to one non-root worker with a read-only root, dropped
capabilities, no-new-privileges, PID/memory/CPU limits, hardened tmpfs, no
volumes, and an internal-only network. The sidecar binds the installed binary,
and exact SBOM/Grype artifacts are retained.

Rollout conditions are closure and re-review of OPS-01/OPS-02, explicit
disposition of OPS-03 through OPS-06, authorized forest1 validation through the
canonical deploy entry point, tested rollback, and exact post-build image,
sidecar, readiness, GeoJSON, and GeoParquet receipts.
