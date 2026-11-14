# Rust CLI Security Review

Date: 2026-11-14

Reviewer: Codex implementation self-review. This is the required dedicated
security artifact, but it is deliberately not labeled independent; genuinely
independent M6 acceptance remains the final package blocker.

Disposition: PASS for local implementation with no confirmed reachable
Critical/High finding. Independent signoff required before issue closure or
rollout.

## Trust boundary

Raw production Shapefile bytes reach only `shape_parser_cli`. The CLI is a
short-lived process under the same container UID, mounts, and internal-network
authority as the API. It narrows the broad memory-unsafe driver attack surface
and bounds failure propagation; it does not contain arbitrary code execution.
The outer non-root, read-only, capability-free, no-new-privileges, PID/memory/
CPU, tmpfs, and internal-network controls remain mandatory.

Parser output is untrusted. Strict JSON validation precedes CRS/Shapely/PyArrow
construction. The CLI cannot select drivers, open URLs, load plugins, spawn
helpers, inherit secrets, or publish partial output. Wall timeout and process-
group termination remain parent-owned. CPU, address-space, file-size, open-file,
core, input, output, feature, and vertex bounds are directly evidenced.

## Supply-chain and image findings

The locked Rust graph has no RustSec advisory as of the retained audit. Unsafe
code exists in the one owned `setrlimit` call and encoding/DBF ecosystem
optimizations; it is included in the trusted computing base and documented in
the dependency evaluation.

Exact Syft/Grype reports are retained and hashed in the qualification artifact.
There are zero Critical findings. Two High zlib findings with a fixed package
were remediated by pinning the Debian security build. The remaining 17 unique
High IDs are non-reachable under the current contract:

- ncurses `infocmp`, Perl POD/Tar, util-linux mount/nsenter, and privileged ACL
  operations are never invoked and cannot gain privilege in this container;
- system SQLite FTS5/session accepts no attacker database;
- affected glibc functions are not called, and the child environment fixes
  `LC_ALL`/`LANG` with no `LANGUAGE` inheritance;
- affected libstdc++ priority-queue/aligned-allocation paths are not selected by
  conversion, while input/vertex/memory/CPU/output ceilings block the stated
  unbounded-allocation preconditions.

These dispositions must be re-reviewed if commands, database inputs, locale
passthrough, privileges, network, native formats, or ceilings change. Medium
findings are similarly retained in the complete report rather than suppressed.

## Provenance and recovery

The executable-specific sidecar detects accidental/stale/mismatched artifacts
and readiness performs a real bounded parse. It is not cryptographic publisher
attestation; immutable image digest verification supplies authenticity. Missing,
malformed, tampered, incompatible, or failing parser artifacts make readiness
fail closed.

Rollback remains image-level: restore the prior reviewed service image/config.
There is intentionally no runtime Fiona/GDAL fallback. The retained oracle image
is test evidence only and must not be silently selected in production.

## Open gate

An independent security reviewer must confirm the same-container residual-risk
acceptance, high-finding reachability dispositions, and no-fallback proof before
#656 or the package is closed. This self-review found no reason to redesign the
CLI into a new service, but it cannot satisfy its own independence requirement.
