# NoDb ACID Transaction Update with Redis

**Status**: Cancelled (2025-10-24) - Abandoned after design review

## Overview

The current NoDb architecture uses file-based JSON persistence with Redis caching and distributed locking. While this provides a working foundation, it lacks true ACID guarantees and suffers from cache invalidation complexity. This work package originally aimed to implement Redis-backed ACID transactions for NoDb controllers with intelligent, event-driven cache invalidation powered by the existing RedisPrep timestamp infrastructure and preflight2 dependency evaluation logic.

During design review we determined the proposal could not deliver true ACID semantics while `.nodb` files remain the source of truth, and the cache invalidation plan duplicated the existing `dump()` cache refresh without addressing demonstrated stale-cache incidents. Pursuing the package would have added complexity (removal of TTLs, new invalidation pathways) without solving the consistency issues, so the initiative was cancelled before implementation.

The remainder of this document is preserved for historical reference only.

## Objectives (superseded)

- Implement Redis MULTI/EXEC transactions for atomic NoDb state changes *(cancelled)*
- Add intelligent cache invalidation using centralized dependency rules *(cancelled)*
- Leverage existing RedisPrep timestamp infrastructure as the event source *(cancelled)*
- Maintain backward compatibility with existing .nodb file persistence *(cancelled)*
- Eliminate 72-hour TTL-based cache invalidation in favor of event-driven invalidation *(cancelled)*
- Preserve distributed locking semantics while reducing complexity *(cancelled)*
- Document the new transaction patterns and migration path for existing controllers *(cancelled)*

## Scope (no longer pursued)

### Included (never executed)

- Design and implement Redis transaction wrapper for NoDb base class *(cancelled)*
- Create centralized cache invalidation rules (JSON configuration) *(cancelled)*
- Extend RedisPrep with cache invalidation methods that consume the rules *(cancelled)*
- Modify RQ API task completion handlers to trigger cache invalidation *(cancelled)*
- Update NoDb.dump_and_unlock() to use Redis transactions for atomicity *(cancelled)*
- Add comprehensive tests for transaction guarantees and cache invalidation *(cancelled)*
- Document the new patterns in AGENTS.md and relevant controller READMEs *(cancelled)*
- Migration guide for converting existing controllers to use transactions *(cancelled)*

### Explicitly Out of Scope

- Complete removal of file-based persistence (files remain primary source of truth)
- Rewriting existing NoDb controllers (migration is optional and incremental)
- Changes to preflight2 service logic (we leverage existing dependency evaluation)
- Modifications to Redis database allocation scheme
- Performance optimization beyond what transactions naturally provide
- Multi-run transactions or cross-controller atomic operations

## Stakeholders

- **Primary**: NoDb controller developers, RQ task authors
- **Reviewers**: System architects, database infrastructure team
- **Informed**: Frontend developers (cache behavior affects UI responsiveness)

## Success Criteria (void)

- [ ] Redis MULTI/EXEC transactions implemented in NoDb base class with `dump_and_unlock_with_transaction()` method *(not pursued)*
- [ ] Cache invalidation rules JSON schema defined and documented with version 1.0 *(not pursued)*
- [ ] RedisPrep extended with `invalidate_caches_for_task(task_enum)` method that loads rules and deletes cache keys *(not pursued)*
- [ ] At least 3 RQ API endpoints updated to use new invalidation system (Climate, Wepp, and Watershed controllers) *(not pursued)*
- [ ] Comprehensive test suite covering transaction guarantees and cache invalidation (unit + integration tests) *(not pursued)*
- [ ] Documentation complete (AGENTS.md patterns, migration guide, inline comments) *(not pursued)*
- [ ] Backward compatibility verified (existing controllers work unchanged via `dump_and_unlock()`) *(not pursued)*
- [ ] Zero regressions in existing test suite (`wctl run-pytest tests --maxfail=1`) *(not pursued)*
- [ ] Manual smoke testing confirms cache invalidation works end-to-end *(not pursued)*
- [ ] Performance benchmarks show no significant regression (<5% latency increase) *(not pursued)*

## Dependencies

### Prerequisites

- Existing RedisPrep timestamp infrastructure (already in place)
- Preflight2 dependency evaluation logic (already implemented)
- Redis DB 0 and DB 13 allocation (already configured)
- Understanding of current NoDb locking and persistence patterns

### Blocks

- None (this is foundational work for future controller improvements)

## Related Packages

- **Related**: [20251023_frontend_integration](../20251023_frontend_integration/package.md) - Cache behavior affects UI refresh patterns *(no action taken; reference only)*
- **Follow-up**: Future package for migrating high-traffic controllers (Climate, Wepp, Watershed) to use transactions *(cancelled alongside this effort)*

## Timeline Estimate

- **Complexity**: High (touches core persistence layer, requires careful testing)
- **Risk level**: Medium-High (architectural change but with backward compatibility escape hatch)

## Invalidation Signaling Strategy (archived proposal)

### Why Cache Invalidation Matters (The Multi-Process Problem)

**The Core Problem**: NoDb controllers are singletons per working directory, but multiple processes (web requests, RQ workers, background tasks) can access the same run simultaneously. Without cache invalidation, processes would see stale cached data even after other processes updated the underlying .nodb files.

**Example Scenario Without Invalidation**:
1. **Process A** (RQ worker) runs climate build task → updates `Climate` controller → writes `climate.nodb` → caches JSON in Redis DB 13
2. **Process B** (web request) accesses `Climate` controller → **reads stale cached data** instead of fresh `climate.nodb`
3. **Result**: UI shows old climate data, user sees inconsistent state

**How Cache Invalidation Fixes This**:
1. **Process A** completes climate build → `prep.timestamp(TaskEnum.build_climate)` → **invalidates climate cache**
2. **Process B** accesses `Climate` controller → cache miss → **reloads from updated climate.nodb file**
3. **Result**: UI shows fresh climate data, cross-process consistency maintained

**Why Not Just Load From Disk Always?** While controllers could always load from disk, Redis caching provides significant performance benefits (sub-millisecond access vs file I/O). Cache invalidation ensures the cache stays fresh without sacrificing performance.

### Cache Invalidation vs Attribute Deletion (archived reasoning)

**Cache-only invalidation**: RedisPrep invalidates Redis cache keys, not controller attributes. Controllers handle cache misses by reloading from disk.

**Why this approach**:
- NoDb controllers maintain their in-memory state intact
- File-based persistence remains the source of truth
- Controllers can implement smart cache miss handling
- Users can override invalidation by manually refreshing caches

### User Override Mechanisms

Users can override invalidation decisions through:
- **Manual cache refresh**: Force reload specific controllers
- **Understanding dependency rules**: Users can see invalidation rules in `cache_invalidation_rules.json`
- **Selective cache clearing**: Clear specific cache keys if invalidation was incorrect
- **Controller-specific refresh**: Individual controllers can implement refresh methods

### Controller Cache Miss Handling

Controllers should implement graceful cache miss handling:
```python
@property
def some_expensive_property(self):
    cache_key = f"nodb_cache:{self.run_id}:{self.__class__.__name__.lower()}"
    cached = self.redis.get(cache_key)
    if cached is None:
        # Cache miss - recompute and cache
        value = self._compute_expensive_property()
        self.redis.set(cache_key, self._serialize_for_cache())
        return value
    return self._deserialize_from_cache(cached)
```

### Task Disabling vs Cache Invalidation (archived reasoning)

**Use cache invalidation, not task disabling**: 
- Tasks remain runnable but dependent data refreshes automatically
- Users can run tasks even if "invalidated" (they know their domain)
- Cache miss triggers automatic refresh on next access
- NoDb state stays consistent, only cache is invalidated

## References

- `wepppy/nodb/base.py` - Core NoDb implementation with locking and caching
- `wepppy/nodb/redis_prep.py` - Timestamp tracking and task lifecycle management
- `wepppy/weppcloud/routes/rq/api/api.py` - RQ API endpoints that trigger tasks
- `services/preflight2/internal/checklist/checklist.go` - Dependency evaluation logic
- `wepppy/nodb/cache_invalidation_rules.json` - Centralized invalidation rules (created in this package)
- `docs/dev-notes/redis_dev_notes.md` - Redis usage patterns and conventions

## Deliverables (not executed)

- **Code Changes**:
  - `wepppy/nodb/base.py`: New `dump_and_unlock_with_transaction()` method *(not implemented)*
  - `wepppy/nodb/redis_prep.py`: New cache invalidation methods *(not implemented)*
  - `wepppy/weppcloud/routes/rq/api/api.py`: Updated task completion handlers *(not implemented)*
  - `wepppy/nodb/cache_invalidation_rules.json`: Centralized invalidation rules *(not adopted)*

- **Test Files**:
  - `tests/nodb/test_redis_transactions.py`: Transaction guarantee tests *(not written)*
  - `tests/nodb/test_cache_invalidation.py`: Cache invalidation tests *(not written)*
  - `tests/weppcloud/routes/test_rq_cache_invalidation.py`: Integration tests *(not written)*

- **Documentation**:
  - AGENTS.md section on Redis transaction patterns *(not added)*
  - Migration guide for existing controllers *(not added)*
  - API documentation for new methods *(not added)*

- **Configuration**:
  - `cache_invalidation_rules.json` schema documentation *(not published)*
  - Performance benchmarks baseline *(not collected)*

## Testing Strategy (not executed)

- **Unit Tests**: Mock Redis for transaction wrapper and invalidation logic *(not run)*
- **Integration Tests**: Real Redis for end-to-end RQ API → invalidation flow *(not run)*
- **Performance Tests**: Benchmark transaction overhead vs current implementation *(not run)*
- **Backward Compatibility**: Ensure existing controllers work without changes *(not verified)*
- **Failure Scenarios**: Test transaction failures, Redis unavailability, partial writes *(not verified)*

## Closure Notes

- **2025-10-24** – Package cancelled during design review. Proposal could not deliver ACID guarantees without replacing file persistence, and the cache invalidation scheme duplicated existing cache refresh behaviour while removing TTL safeguards. Recommendation: document real failure modes (fsync errors, concurrency edges) before revisiting transactional persistence or cache redesign.
