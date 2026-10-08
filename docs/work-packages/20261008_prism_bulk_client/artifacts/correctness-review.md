# Correctness review: historic PRISM bulk client

Reviewer: Codex (self-review; no independent reviewer requested). Date: 2026-10-08 UTC.
Scope: four new PRISM client modules, their tests, Docker cache-path configuration.
Base: `44c1d6d13`; exact candidate source hashes are in `final-candidate-validation.json`.
Authority: [client contract](../../../dev-notes/prism-800m-client-design.md#implemented-bulk-api-and-docker-configuration)
and [ADR-0081](../../../adrs/ADR-0081-prism-native-cell-bulk-cache.md).

## User outcome and compatibility

Named geographic locations produce raw native-cell daily tables with retained source provenance. Same-cell points share cache entries. The cache path is operator-configurable through Docker `.env`. This API is additive: legacy PRISM, Daymet/GridMET, climate enums, persisted projects and model preprocessing do not change. Model-mode/UI integration remains outside delivery scope.

## State and error review

| State | Behavior | Evidence |
|---|---|---|
| Unconfigured or relative path | Explicit configuration error | `test_configuration_and_env` |
| Empty persistent cache | Acquire, validate CSV, write/read parquet, publish references | Live cold worker extraction |
| Valid populated cache | Fetch current manifests; reuse exact stored values | Live warm and second-worker checks |
| Same-cell aliases | One unique cell series | Focused and live tests |
| Changed source release or count | Entry is stale; acquire replacement, retain old source | Revision inequality/count tests |
| Revision race | Retain attempt; retry once, then explicit freshness error | Repeated and single-race tests |
| Freshness service failure | Fail; do not serve cached values | Warm-cache malformed-manifest test |
| Missing/malformed cells or dates | Coverage/protocol failure; retain raw CSV | Recorded masked cells, real mixed land/ocean batch rejection, leap calendar and malformed payload tests |
| Corrupt cache | Explicit cache error; no silent repair | Persisted parquet corruption test |
| Partial reference publication | Published references already name validated data; retry fetches only missing cells | Real staged artifacts, injected second-rename failure |
| Concurrent same-partition clients | POSIX lock serializes acquisition; one bulk call | Concurrent filesystem test |
| Lock timeout | Explicit bounded timeout | Real held-lock test |
| Untrusted download path | Reject absolute/external/traversal path | Protocol tests |
| Legacy shared cache | Separate schema/grid namespace; no migration | New `v1/<grid-id>` layout; old clients untouched |

The deliberate broad attempt boundary retains failure status and re-raises the original exception. No exception is swallowed. Bounded network requests and polling use explicit errors rather than fallback weather or stale data.

## Generated-artifact evidence chain

The real provider received snapped native centers and explicit interpolation-off requests. CSV inventories, calendars, coordinates, units and values are parsed before publication. Parquet is read back and compared to the in-memory parsed table. Warm reads verify original compressed CSV, manifest and parquet checksums, then revalidate calendar/value semantics. The returned table and immutable source references are the consumer boundary for this slice.

Live evidence includes three cells over all 366 days of 2020, an alias sharing one cell, exact comparison with the independently retained prior PRISM sample, a December/January split, a recent partial-year request, reuse in a second worker container, and a real mixed land/ocean request that retained its failed CSV without publishing any cache entry. Final source candidate cold/warm validation covers a new ten-day interval. The worker runs as UID 1000/GID 993 with umask 022 and the normal `/wc1` bind mount. No service identity, permission, mount or running-service environment was changed; scoped exec supplied the configured env value.

Normal Compose rendering passes default/custom `PRISM_CACHE_DIR` values for dev, production and worker stacks. Runtime propagation to newly recreated production containers is not claimed; no deployment was performed.

## Findings and resolution

The first live request failed on the first poll at the provider's five-second keep-alive boundary. Its failed attempt remains in the cache. The client now sends `Connection: close`; rerun and final candidate validation pass. The polling test asserts ticket propagation and that header. No automatic retry of an ambiguously submitted new bulk job was introduced.

Point mapping initially recreated the datum transformer for each point. A direct 100-point measurement took 3.17 seconds. Reusing the identical transformer reduced this to 0.050 seconds with unchanged cells. Finite positive timeout configuration is validated explicitly. The 500-cell recorded payload passes exact every-value parity; grouping rows once reduces production-parser time from 8.23 to 2.35 seconds. The API checker also identified an unnecessary ordered-dataclass TypeVar; using plain frozen cells and explicit row/column sorting preserves batching semantics and passes stubtest.

## Observability and limits

The comparable source layout is GridMET/Daymet climate-source parquet with visible attempt evidence. This slice writes a shared public-source cache, not project-owned artifacts. All attempt paths are ordinary visible directories; failed payloads and earlier successful versions remain available. There is no cleanup or hidden-download exception. Project browser/archive tests are not applicable until a consumer writes run artifacts; the canonical contract requires source/provenance snapshots and downstream CLI/archive validation before that later integration.

Unchanged release manifests cannot prove an atomic bulk/backend revision identity. Provider scientific accuracy, long-duration availability and distributed filesystems without working POSIX locks are not certified. Exact partial intervals do not merge. The cache is operator-owned, not a writable upload surface.

## Verdict

Client behavior, real persistence boundaries, Docker path rendering and current worker/mount execution are validated. Focused suite: 39 passing tests. Full suite: 10,253 passed, 126 skipped, one unchanged PostgreSQL latency-test failure. Rerun of the complete failed module and remaining tail: 207 passed. The original invocation was not green. API/stub, broad-exception and documentation checks pass. No unresolved correctness finding from this review; no deployment or WEPP integration approval is implied.
