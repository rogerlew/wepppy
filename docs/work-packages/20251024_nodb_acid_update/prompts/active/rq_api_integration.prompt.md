# RQ API Cache Invalidation Integration

> **Purpose**: Update RQ API endpoints to trigger cache invalidation when tasks complete, replacing manual timestamp management with automatic invalidation
> **Target**: GitHub Copilot / Codex
> **Created**: 2025-10-24
> **Status**: Active

## Context

RQ API endpoints currently call `prep.remove_timestamp()` and `prep.timestamp()` manually. With the new cache invalidation system, we need to update these endpoints to use the automatic invalidation that happens in `prep.timestamp()`.

## Context

Current RQ API pattern uses manual `remove_timestamp()` calls after task completion. We need to remove these and rely on automatic cache invalidation triggered by `prep.timestamp()`.

**Important**: Remove manual `remove_timestamp()` calls. Cache invalidation is now automatic via RedisPrep's extended `timestamp()` method. Controllers handle cache misses gracefully.

Current pattern (to be removed):
```python
# Manual timestamp removal (REMOVE THIS)
prep.remove_timestamp(TaskEnum.build_climate)
```

New pattern (automatic):
```python
# Automatic cache invalidation via timestamp()
prep.timestamp(TaskEnum.build_climate)  # This now also invalidates caches
```

## Prerequisites

- [x] RedisPrep invalidation extension is implemented
- [x] cache_invalidation_rules.json exists
- [x] Controllers implement graceful cache miss handling
- [x] Tests pass in baseline: `wctl run-pytest tests/rq/test_*_rq.py`

## Prerequisites

- [x] RedisPrep invalidation methods implemented
- [x] cache_invalidation_rules.json validated
- [x] Tests pass in baseline: `wctl run-pytest tests/weppcloud/routes/test_rq_api.py`

## Objective

Update at least 3 RQ API endpoints (Climate, Wepp, Watershed) to use automatic cache invalidation instead of manual timestamp management.

**Success looks like**: Task completion automatically invalidates dependent caches without manual `remove_timestamp()` calls.

## Reference Documents

- `wepppy/weppcloud/routes/rq/api/api.py` – Current RQ API endpoints
- `wepppy/nodb/redis_prep.py` – New invalidation methods
- `wepppy/nodb/cache_invalidation_rules.json` – Task → controller mappings

## Working Set

### Files to Read (Inputs)
- `wepppy/weppcloud/routes/rq/api/api.py` – Current timestamp management patterns
- `wepppy/nodb/redis_prep.py` – New timestamp() method with invalidation

### Files to Modify (Outputs)
- `wepppy/weppcloud/routes/rq/api/api.py` – Update 3+ endpoints to use automatic invalidation

### Files to Reference (Dependencies)
- `tests/weppcloud/routes/test_rq_api.py` – Existing test patterns

## Step-by-Step Instructions

1. **Analyze current timestamp usage**
   - Search for `remove_timestamp()` calls in RQ API
   - Identify patterns: `remove_timestamp()` before job enqueue, `timestamp()` after completion
   - Note which endpoints to update first (Climate, Wepp, Watershed)

2. **Update Climate endpoint** (`api_build_climate`)
   ```python
   # Before
   prep.remove_timestamp(TaskEnum.build_climate)
   
   # After - remove manual invalidation, let timestamp() handle it
   # prep.remove_timestamp(TaskEnum.build_climate)  # Removed
   ```

3. **Update Wepp endpoints** (`api_run_wepp`)
   ```python
   # Before
   prep.remove_timestamp(TaskEnum.run_wepp_hillslopes)
   prep.remove_timestamp(TaskEnum.run_wepp_watershed)
   
   # After - remove manual invalidation
   # prep.remove_timestamp(TaskEnum.run_wepp_hillslopes)  # Removed
   # prep.remove_timestamp(TaskEnum.run_wepp_watershed)  # Removed
   ```

4. **Update Watershed endpoint** (`api_abstract_watershed`)
   ```python
   # Before
   prep.remove_timestamp(TaskEnum.abstract_watershed)
   
   # After - remove manual invalidation
   # prep.remove_timestamp(TaskEnum.abstract_watershed)  # Removed
   ```

5. **Verify RQ job completion still sets timestamps**
   - Check that RQ worker still calls `prep.timestamp()` when jobs complete
   - Ensure invalidation happens at job completion, not job start

6. **Add integration tests**
   - Test that cache invalidation happens when tasks complete
   - Verify dependent controllers see cache misses after invalidation

## Observable Outputs

### Before (Current State)
```python
@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_climate', methods=['POST'])
def api_build_climate(runid, config):
    # ... validation ...
    prep = RedisPrep.getInstance(wd)
    prep.remove_timestamp(TaskEnum.build_climate)  # Manual invalidation
    
    with _redis_conn() as redis_conn:
        q = Queue(connection=redis_conn)
        job = q.enqueue_call(build_climate_rq, (runid,), timeout=TIMEOUT)
        prep.set_rq_job_id('build_climate_rq', job.id)
    # ... response ...
```

### After (Target State)
```python
@rq_api_bp.route('/runs/<string:runid>/<config>/rq/api/build_climate', methods=['POST'])
def api_build_climate(runid, config):
    # ... validation ...
    prep = RedisPrep.getInstance(wd)
    # prep.remove_timestamp(TaskEnum.build_climate)  # Removed - automatic invalidation now
    
    with _redis_conn() as redis_conn:
        q = Queue(connection=redis_conn)
        job = q.enqueue_call(build_climate_rq, (runid,), timeout=TIMEOUT)
        prep.set_rq_job_id('build_climate_rq', job.id)
    # ... response ...
    
    # RQ worker will call prep.timestamp(TaskEnum.build_climate) when job completes
    # which automatically invalidates dependent caches
```

## Anti-Patterns to Avoid

❌ **Don't remove timestamp() calls from RQ workers**:
```python
# Wrong - breaks dependency evaluation
def build_climate_rq(runid):
    # ... do work ...
    # prep.timestamp(TaskEnum.build_climate)  # Don't remove this!
```

✅ **Keep timestamp() calls in RQ workers, remove manual remove_timestamp()**:
```python
# Correct - timestamp() now handles invalidation
def build_climate_rq(runid):
    # ... do work ...
    prep = RedisPrep.getInstance(get_wd(runid))
    prep.timestamp(TaskEnum.build_climate)  # Keeps dependency tracking + invalidation
```

❌ **Don't add manual cache clearing** - Let automatic invalidation handle it
❌ **Don't modify controller state** - Cache-only invalidation with graceful misses

## Validation Gates

### Automated Checks
```bash
# RQ API tests still pass
wctl run-pytest tests/weppcloud/routes/test_rq_api.py -v

# Cache invalidation integration tests
wctl run-pytest tests/weppcloud/routes/test_rq_cache_invalidation.py -v

# End-to-end invalidation tests
wctl run-pytest tests/nodb/test_end_to_end_invalidation.py -v
```

### Manual Verification
- [ ] Climate build invalidates climate controller cache
- [ ] Wepp run invalidates wepp controller cache
- [ ] Watershed abstraction invalidates watershed controller cache
- [ ] UI updates correctly after cache invalidation
- [ ] No performance regression in RQ job processing

## Deliverables

1. Updated Climate, Wepp, and Watershed RQ API endpoints
2. Removed manual `remove_timestamp()` calls
3. Verified RQ workers still call `timestamp()` for dependency tracking
4. Integration tests for cache invalidation on task completion
5. Documentation of changed patterns

## Handoff Format

**Completed**: YYYY-MM-DD

**Changes Made**:
- Updated RQ API endpoints to use automatic cache invalidation
- Removed manual timestamp management calls
- Added integration tests for end-to-end invalidation

**Files Modified**:
- `wepppy/weppcloud/routes/rq/api/api.py`

**Test Results**:
```
[Paste test output showing RQ and invalidation tests pass]
```

**Validation Status**:
- [x] Automated checks passed
- [x] Manual verification complete
- [x] Success criteria met

**Issues Encountered**:
- [Issue 1 and resolution]
- [Issue 2 and resolution]

**Next**: Ready for comprehensive testing and documentation