# M2 independent security review

## Scope and method

This review covers the M2 change from `eb6b0d3fb` through `0e58feced`, plus
the exact-image evidence in `20261116_m2_validation.md`. It inspected the
GeoParquet upload dispatch, source staging and digest reconciliation, parser
argv/environment/process lifecycle, IPC schema and readback, CRS handling,
readiness/provenance, cleanup, container construction and hostile-input tests.

The M1 Rust parser and dependency graph were not re-approved here; this review
relies on their separate final correctness/security acceptance and checks how M2
constrains and invokes that accepted binary.

## Findings

| ID | Severity | Surface | Evidence and exploit path | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| M2-SEC-01 | Low | Readiness observability | `app.py` correctly blocks only GeoParquet requests when its parser/canary is unavailable, but `/health/ready` remains HTTP 200 and the generic `provenance` value still reads `binary_binding_verified`. The separate `geoparquet_parser: unavailable` field prevents an unsafe invocation, so this is not an input-bypass finding. A rollout monitor that checks only the HTTP status or generic provenance field could nevertheless miss loss of the new capability. | Before rollout, make the deployment/preflight gate assert `geoparquet_parser == ready`; retain the format-specific 503 regression. Do not change whole-service readiness unless operators intentionally choose that availability contract. | Open rollout gate; no M2 code hold |
| M2-SEC-02 | Low | Network/containment evidence | The exact API smoke used a bridge network for loopback access. The image was also exercised with `--network none`, and the unchanged canonical Compose files attach shape-converter only to the inherited internal network, but the M2 artifact does not yet contain a merged-Compose egress probe for this exact image. A parser compromise therefore retains the predecessor's explicitly accepted same-container UID/mount/internal-network authority rather than gaining a newly proved sandbox. | At rollout qualification, resolve the production Compose model with this exact image and prove internal/no-egress networking, mounts, identity, read-only root, caps, seccomp/runtime and resource limits. | Open rollout gate; inherited accepted residual |
| M2-SEC-03 | Low | Supply-chain evidence retention | The exact Cargo.lock has a fresh zero-advisory RustSec result and the candidate has hashed Rust/Debian/Python inventories. The inventory bodies currently live only as local temporary evidence and no Syft/Grype/Trivy or Docker SBOM plugin is installed. This does not change the pinned build or embedded binary provenance, but the package cannot claim a durable publication-grade image SBOM/scan from the recorded hashes alone. | Retain reproducible inventory commands or bodies with final evidence and require the publication pipeline SBOM/vulnerability scan before image publication. | Open rollout/publication gate; no M2 code hold |

No High or Medium security finding was identified.

## Threat-control readback

- Format dispatch is extension-gated and binary admission rechecks Parquet magic;
  unsupported content has no Python parser fallback.
- Complete upload bytes are staged under a fixed name with `O_EXCL`,
  `O_NOFOLLOW`, `O_CLOEXEC` and mode `0600`. SHA-256 and length are reconciled
  before and after the child runs using a no-follow regular-file descriptor.
- The child receives fixed argument names and reviewed numeric limits, no shell,
  a fixed request-directory working directory, only `LC_ALL`/`LANG`, discarded
  stdout/stderr and a new process session.
- Timeout and cancellation synchronously drain the entire process group through
  the predecessor's shielded termination helper before scratch ownership is
  released. Parser output is removed after interrupted execution; the request
  `finally` path cleans the whole private request directory on every outcome.
- IPC is a no-follow regular file, bounded to 16 MiB, parsed with duplicate-key
  and nonfinite-constant rejection, exact top-level keys, cardinality/type/bounds
  reconciliation and canonical GeoJSON semantic readback.
- GeoParquet CRS parsing is bounded by M1 metadata limits. PyProj network access
  is disabled in the reviewed runtime, and M2 requests best-only,
  no-ballpark transformation; the missing-grid fixture fails closed.
- Startup validates the adjacent binary provenance sidecar and executes a real
  polygon canary. A failed GeoParquet binary/canary sets format-specific
  unavailability, and request dispatch returns 503 before launch.
- Exact-image evidence confirms non-root UID/GID 10001, read-only root,
  no-new-privileges, dropped capabilities, bounded PID/memory/CPU/tmpfs,
  successful valid/projected readback, hostile 413, missing-grid 400 and empty
  request scratch after all cases.
- Public errors for parser rejection, resource exhaustion and CRS failure are
  bounded and do not echo attacker metadata, source bytes or filesystem paths.

## Verdict

**PASS for M2 implementation security.** Unresolved findings: High 0, Medium 0,
Low 3. The three Low items are explicit rollout/publication evidence gates and
do not permit deployment or publication under the current authorization.

The security pass is limited to local M2 implementation and exact-image
qualification. It does not approve receiver retention/authorization work,
production rollout, image publication, remote integration, or automated account
action for hostile uploads; those require their own M3-M5 and operator gates.
