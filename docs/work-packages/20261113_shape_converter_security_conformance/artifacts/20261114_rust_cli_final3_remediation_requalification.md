# Rust CLI final-3 remediation requalification

Date: 2026-11-14

Status: local exact-image qualification passed. Independent final-3 re-review
and any production rollout remain open.

## Candidate identity

- Source commit: `4587308ff9357e02c5bbd413bdcfc0cc98ef3d91`.
- Image: `sha256:8c9acdd292a80355c708823f98d3651484667856abfd35b0a28af2b4a3cfc3cf`.
- Image size: 397,879,714 bytes.
- Release label: `wepppy-4587308ff935`.
- Build timestamp: `2026-11-14T16:37:11-08:00`, derived from the commit.
- Parser binary SHA-256:
  `1b9b719b9b6633684addd117be01dd7754b648f0a45ab27eea644185a30b70b3`.

The image was built with required release provenance. Its sidecar binds the
binary and Rust source manifest to the exact commit.

## Final-3 blocker closure

- Deployment intent now comes from `wctl show-compose-files`, which reports the
  installed preset paths independently of mutable rendered services. A full
  preset runs the clean/provenance gate before topology classification.
- Fail-closed takedown discovers, stops, and verifies converter containers by
  Compose service and checkout working-directory labels. It no longer depends
  on the potentially damaged service definition. Discovery, stop, and
  verification failures retain distinct exit `88` behavior.
- Tests cover a dirty full preset reclassified as worker, a clean full preset
  missing the service while a labeled container exists, and all takedown
  failure phases. Canonical recovery guidance is retained in
  `docs/infrastructure/shape-converter-fail-closed-recovery.md`.
- Parser cancellation now observes live process-group membership independently
  of the group leader. It waits through the grace period, sends `SIGKILL` to
  remaining descendants, and does not release request/scratch ownership until
  no non-zombie member remains. The real-process regression uses a child that
  ignores `SIGTERM`.

## Exact-image behavior

The no-network qualification container ran as UID/GID 10001 with a read-only
root, all capabilities dropped, no-new-privileges, 256 PIDs, 1.5 GiB memory,
1.5 CPUs, and bounded tmpfs. Readiness reported `binary_binding_verified`.
Fiona, GDAL, and pip were absent.

A parsed Point conversion returned coordinates `[10, 20]` with `NAME=demo`.
Request scratch was empty after cleanup. The retained final-2 semantic,
GeoParquet, saturation, child-limit, and MultiPatch evidence remains applicable
because the Rust parser binary and source manifest are unchanged.

## Validation

- Shape-converter suite: 296 passed.
- Focused deploy/Compose, `wctl`, and process-group gates: 66 passed, 3
  environment skips.
- Full `wctl` suite: 60 passed.
- Broad-exception changed-file enforcement, shell syntax, diff whitespace, and
  documentation lint passed.

## SBOM and vulnerability evidence

Pinned Syft 1.57.1 and Grype 0.121.3 scanned the exact image.

| Artifact | SHA-256 |
|---|---|
| `20261114_rust_cli_final3_remediation_syft.json` | `e1061747c9c2a2e273cf0f210af053a8040c45b202fb06c63e5e89a25a078307` |
| `20261114_rust_cli_final3_remediation_grype.json` | `24348ef23a1237dbaf6189df0e8ba94d21e16e345f8223b109ac90b275dc0451` |

The scan remains 0 Critical, 59 High, 67 Medium, 17 Low, 50 Negligible,
and 16 Unknown package records: 96 unique IDs, including 17 unique High and 37
unique Medium. No advisory ID was added or removed from final-2. Existing
reachability dispositions therefore remain unchanged.

## Remaining gate

No image was published and no production deployment occurred. Independent
code, correctness, QA, operations, and security re-review must accept this exact
candidate before issue #656 can close. Rollout remains separately authorized.
