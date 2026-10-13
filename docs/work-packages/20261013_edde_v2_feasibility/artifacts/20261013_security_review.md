# Security review — EDDE v2 feasibility

## Metadata and scope

Reviewer: Codex implementer self-review, 2026-10-13 UTC. **Independent security sign-off remains pending**; this document does not claim reviewer independence. Scope: `wepppy/climates/edde/`, its offline tests, public acquisition, standalone file output, and CLIGEN/WEPP study execution. No application routes, authorization, secrets, NoDb persistence, queue wiring, service identity, or deployment changed.

Security impact remains **high** under repository triage because of egress, downloaded files, and executable boundaries. Trusted local callers choose cache/output paths and a canonical station; this is not an untrusted web API. A cache object has one writer. Integration must reassess multi-worker ownership and project paths.

## Findings and controls

| ID | Severity | Surface | Disposition and evidence | Status |
| --- | --- | --- | --- | --- |
| SEC-01 | Medium | Arbitrary endpoint/path selection | Fixed public HTTPS root, validated source components, cache key hashing, no redirects; traversal and changed-object tests pass. No remote key becomes an executable or local path component. | Resolved in implementation |
| SEC-02 | Medium | Partial/stale source cache | Preflight/request byte budget, timeout, ETag `If-Match`, exact size, fresh SHA-256 verification, `.partial` staging, source attempt identity, atomic promotion; corruption/truncation tests exercise real files. | Resolved in implementation |
| SEC-03 | Medium | Existing output overwritten or mislabeled | CLI and CLIGEN require new output directories; PRISM requires a new output file. Incomplete manifests precede generation. No implicit fallback, guard bypass, or nearest-land move. | Resolved in implementation |
| SEC-04 | Low | Concurrent cache writes | Explicit single-writer contract; production multi-worker integration is deferred. Study uses distinct model/scenario/year objects and completed shared static grids. | Integration limitation |

The final EDDE and reference clients explicitly suppress ambient netrc credentials. This implementer review initially missed the default Requests ambient-authentication behavior; the independent review detected and verified its correction. No shell string incorporates source/user values in the new client/adapter. Existing CLIGEN uses argument vectors and a fixed vendored binary; the study WEPP runner uses a fixed repository binary. Fixture extraction in the development-container smoke uses a verified archive and Python's data extraction filter. Native NetCDF/PROJ parsing uses existing installed dependencies.

## Valid states and filesystem evidence

Fresh/empty caches, valid populated caches, corrupt/truncated cache files, missing dates/variables, unsupported scenarios, invalid coordinates, nonland cells, and existing output paths are covered by focused tests or retained live probes. Real public requests, native NetCDF reads, filesystem writes, CLIGEN generation, and WEPP consumption are exercised. Existing project/run directories remain untouched; retained fixtures are verified before copying into new standalone experiment directories.

Every successful source query records exact keys/ETags/hashes and byte metrics. Failed source attempts keep partial records; failed CLIGEN attempts keep PRN, station inputs, normalized data, and logs under the study directory. Generated/source archives and `evidence-index.json` preserve study records. No project browser/archive surface changed; integration must prove those boundaries independently.

## Verdict

Implementer assessment: no unresolved medium/high implementation finding identified in this bounded research interface. **Gate status: pending independent review.** This is not a production-release recommendation. Scientific no-go conditions in `report.md` and the separate correctness review are not security approvals or accepted security risk. No risk acceptance is inferred from user silence.
