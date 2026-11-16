# Rust CLI final-4 remediation requalification

Date: 2026-11-14

Status: local exact-image qualification passed. Independent final-4 re-review
and any production rollout remain open.

## Candidate identity

- Source commit: `a6be89141c234727bb5d89aa5a4b3c2ec51dc284`.
- Image: `sha256:b9e78b16718911ff16dc213b27d719477d95880ebcdca500cc858cea13c05ae8`.
- Image size: 397,880,382 bytes.
- Release label: `wepppy-a6be89141c23`.
- Build timestamp: `2026-11-14T16:50:22-08:00`.
- Parser binary SHA-256:
  `1b9b719b9b6633684addd117be01dd7754b648f0a45ab27eea644185a30b70b3`.

## Final-4 blocker closure

- Process-group termination now runs in a shielded drain task. Every repeated
  cancellation is deferred until the SIGTERM grace period, required SIGKILL,
  and live-member verification finish; the original cancellation outcome is
  then preserved. The real-process regression cancels twice while a descendant
  ignores SIGTERM.
- Full-preset Compose render, build-set derivation, expected-service derivation,
  and runtime-contract failures all invoke label-based fail-closed takedown.
- Preset-query failure during `--print-plan` or targeted web/CAP/batch work now
  fails without discovering or stopping the unrelated converter. Every path
  that may perform takedown holds the deployment lock.
- `wctl` retry helpers now preserve the failed command's real status; the prior
  status-loss bug could otherwise turn a failed preset query into empty output.
- The exit-88 runbook is catalogued in `docs/infrastructure/README.md`.

## Exact-image behavior and validation

The no-network container ran as UID/GID 10001 with a read-only root, all
capabilities dropped, no-new-privileges, 256 PIDs, 1.5 GiB memory, 1.5 CPUs,
and bounded tmpfs. Readiness reported `binary_binding_verified`; Fiona, GDAL,
and pip were absent. A parsed Point returned `[10, 20]` and request scratch was
empty afterward.

- Shape-converter suite: 296 passed.
- Deploy execution suite: 55 passed.
- Focused repeated-cancellation and timeout termination tests: 2 passed.
- Broad-exception enforcement, shell syntax, diff whitespace, and documentation
  lint passed.

The retained final-3 semantic, GeoParquet, saturation, child-limit, MultiPatch,
and `wctl` evidence remains applicable; the parser binary is byte-identical.

## SBOM and vulnerability evidence

Pinned Syft 1.57.1 and Grype 0.121.3 scanned the exact image.

| Artifact | SHA-256 |
|---|---|
| `20261114_rust_cli_final4_remediation_syft.json` | `04ed020f7bd0d842a7ae3bce06bf62bc7b8caf53bcc0b1ea7c9cfeffde49a3f7` |
| `20261114_rust_cli_final4_remediation_grype.json` | `92d715928083d95653b0fbea095347b79b96bdd54c561bae285ad556bd196dff` |

The result remains 0 Critical, 59 High, 67 Medium, 17 Low, 50 Negligible,
and 16 Unknown records: 96 unique IDs, including 17 unique High and 37 unique
Medium. No advisory ID changed from final-3, so existing reachability
dispositions remain unchanged.

## Remaining gate

No image was published and no production deployment occurred. Independent
code, correctness, QA, operations, and security re-review must accept this exact
candidate before issue #656 can close. Rollout remains separately authorized.
