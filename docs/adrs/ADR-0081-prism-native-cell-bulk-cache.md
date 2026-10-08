# ADR-0081: Historic PRISM native-cell extraction and cache

Status: Accepted for standalone client delivery

Date: 2026-10-08

## Context

The 800 m daily PRISM bulk study demonstrated practical extraction but found masked-cell omissions and incomplete revision identity. Watersheds can share cells, so coordinate-based cache keys would duplicate data. The existing legacy PRISM client is 4 km/interpolated; it must retain its behavior.

## Decision

Add a separate raw-data API using nearest native NAD83 cells, no interpolation, and no substitution for masked cells. Convert WGS84 coordinates through existing PyProj; exact internal grid-edge ties belong to the east/south cell. Remove only affine arithmetic noise within 1e-9 pixels of an integer boundary. Cache keys include schema, grid geometry, cell and exact inclusive date interval, split at calendar years. The fixed variable set and SI units are part of schema v1.

Expose `PRISM_CACHE_DIR` in Docker `.env`, default `/wc1/cache/prism` on the existing persistent mount. Recheck five complete daily release manifests on every cache read; no time-to-live is assumed. Compare before/after manifests for fresh extraction, retry a revision race once, and fail if it repeats. An unchanged manifest supports conservative cache freshness, not immutable provider revision proof.

## Decision Provenance

Decision Venue: user/Codex conversation, 2026-10-08, America/Los_Angeles.

Participants Present: repository operator and Codex.

Decision Owner: operator selected nearest-cell bulk extraction and Docker-configured caching.

Implementer: Codex selected bounded batching, exact date partitions and per-use freshness checks within that scope.

## Change Summary

New API only: up to 500 native cells and one calendar year per request; raw `ppt`, `tmin`, `tmax`, `tdmean`, `soltotal` values. No unit scaling, dewpoint clipping, monthly normal adjustment, rainfall disaggregation, existing climate-mode changes or model defaults change. The new acquisition path implements the earlier nearest-cell decision rather than changing an existing method's sampling.

## Rationale and Alternatives

Cell identity preserves source daily precipitation and wet/dry patterns while allowing reuse between projects. Bulk acquisition avoids one national raster download per variable/day. Year partitions bound requests. Exact partial intervals avoid unsupported overlap-merging machinery. POSIX file locks and atomic references are sufficient for the existing shared-filesystem environment; no service or distributed datastore is introduced. Always checking metadata avoids inventing a stability-based refresh schedule without evidence.

## Consequences

Freshness requires provider availability even on a cache hit. Different exact partial intervals do not share entries. Failed attempts and old successful versions remain inspectable and consume disk until an operator-reviewed retention policy is introduced. Cache files are shared public source data, not project archives; future model consumers must snapshot inputs and provenance into the run before use. The Explorer RPC is unversioned.

## Evidence

- [Bulk investigation](../investigations/20261008_prism_800m_bulk/findings.md)
- [Current client contract](../dev-notes/prism-800m-client-design.md)
- [Implementation package](../work-packages/20261008_prism_bulk_client/package.md)

## Risk and Rollback Notes

Protocol drift, unknown freshness, bad/missing cells and cache corruption fail explicitly. No stale fallback or source repair is performed. Stop calling the new API to roll back; existing climate workflows remain unchanged. No deployment is part of this delivery. Custom cache paths must be mounted and writable under actual worker identities; `.env` alone does not create mounts or change running containers.
