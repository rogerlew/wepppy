# Rust CLI Code Review

Date: 2026-11-14

Reviewer: Codex implementation self-review. This is not the independent M6
approval.

Disposition: PASS for implementation quality; independent signoff pending.

Reviewed `shape_parser_cli`, its launcher, JSON decoder boundary, executable
provenance, readiness, Docker stages, Compose configuration, and direct tests.

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| CR-01 | High | Executable pickle IPC allowed a compromised parser to execute in the parent. | Closed: strict bounded JSON with duplicate/depth/value/schema/finite/cardinality checks; pickle path removed. |
| CR-02 | High | Production raw parsing used the broad native Fiona/GDAL stack. | Closed: only the short-lived Rust CLI receives raw Shapefile bytes; worker and runtime dependency removed; exact image absence proved. |
| CR-03 | Medium | Upstream crate accepted a forged SHP declared file length. | Closed: WEPPpy validates SHP/SHX magic, version, declared length, and actual length before parsing; mutation regression retained. |
| CR-04 | Medium | Counterclockwise first rings were treated as holes and rejected. | Closed: first-ring orientation establishes consistent interpretation for the dataset; unit and endpoint regressions pass. |
| CR-05 | Medium | Parent-side invalid-WKT rejection bypassed established `same_as_shapefile` preservation. | Closed narrowly: only an independently classified invalid `.prj` in explicit no-reprojection mode ignores parser CRS; other invalid payload WKT remains rejected. |
| CR-06 | Low | Allocation-limit abort could be handled by the host core policy. | Closed: `RLIMIT_CORE=0` precedes address-space/CPU/file limits. |

The CLI emits only fixed diagnostics, writes with create-new plus bounded writer
and atomic rename, validates request-root containment and sidecar regular files,
and has dedicated feature/vertex exits. The launcher uses a minimal environment,
new process group, hard timeout, DEVNULL diagnostics, and fixed error mapping.
No broad production exception handler or permissive fallback was added.

The adjacent sidecar binds exact executable and build/source inputs. Runtime
validation intentionally cannot authenticate a maliciously replaced binary and
sidecar under a writable image; the read-only, digest-verified image is the
authenticity boundary.

No unresolved Critical, High, or Medium code finding remains in this self-review.
