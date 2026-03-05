# Decision Record: Why We Are Not Using OSMnx for WEPPpy OSM Roads Module (v1)

**Date**: 2026-03-04  
**Status**: Accepted  
**Scope**: `docs/work-packages/20260304_osm_roads_client_cache/`

## Decision

For the WEPPpy OSM roads module v1, we will **not** use OSMnx as the primary runtime client/caching layer. We will implement a WEPPpy-owned Overpass client and persistent server-side cache module.

## Context

The OSM roads module in this package is a backend service dependency for terrain preprocessing (`roads_source="osm"`) and needs:

- deterministic cache keying by semantic request content,
- server-wide persistence shared across projects/users,
- lock-safe single-flight refresh under concurrency,
- explicit stale-on-error behavior,
- typed error contracts and structured observability,
- predictable output artifacts in requested target CRS.

These are backend contract requirements, not just convenience fetch behavior.

## Why OSMnx Was Not Selected for v1

1. **Cache model mismatch with required contract**
   - WEPPpy requires semantic cache entries keyed by AOI tile coverage + highway filter + contract version, with explicit TTL state transitions and stale-use policy.
   - OSMnx exposes request/session cache controls, but this package requires a stricter module-owned cache contract and index to guarantee deterministic behavior for multi-tenant server workflows.

2. **Concurrency and lock semantics are first-class requirements**
   - This package requires per-key single-flight locking so concurrent identical requests do not issue duplicate upstream fetches.
   - The required lock behavior must be explicit in module tests and contract, rather than inferred from third-party internal cache behavior.

3. **Reproducibility and operational observability requirements**
   - WEPPpy needs contract-level metadata (`cache_key`, `source`, `stale_served`, feature counts, timing) and stable artifact paths for audit and debugging.
   - A WEPPpy-owned cache/index layer provides direct control of this metadata and lifecycle.

4. **Repository dependency/performance policy**
   - Root guidance in `AGENTS.md` requires dependency discipline and discourages speculative new dependencies where owned-stack implementation is viable.
   - Given this package’s concrete requirements and available geospatial stack, adding OSMnx as a hard runtime dependency is not justified for v1.

5. **Upstream control and failure contracts**
   - Overpass timeout/retry/backoff behavior and fallback policy must map to typed WEPPpy exceptions and stable error contracts.
   - We need explicit, testable boundaries for validation, cache failures, and upstream failures.

## Consequences

### Positive
- Full control of keying, locking, TTL, stale policy, and output artifact contract.
- Clear typed errors and observability aligned to WEPPpy conventions.
- No additional runtime dependency burden for this critical backend path.

### Trade-offs
- More implementation work in WEPPpy compared to using a prebuilt fetch client.
- WEPPpy team owns maintenance of Overpass query/normalization internals.

## Revisit Criteria

We should reconsider OSMnx integration only if a dedicated dependency evaluation demonstrates:

- parity with this package’s cache/lock/error contract requirements,
- lower maintenance cost without loss of determinism or observability,
- benchmark and operational evidence on WEPPpy-representative workloads,
- compatibility with dependency/performance policy gates.

## References

- `AGENTS.md` (dependency/performance discipline and ExecPlan guardrails)
- `docs/work-packages/20260304_osm_roads_client_cache/module_contract.md`
- `docs/work-packages/20260304_osm_roads_client_cache/prompts/completed/osm_roads_client_cache_execplan.md`
- `wepppy/topo/wbt/terrain_processor.concept.md` (`OSM Roads Module` section)
