# Redis Transaction Wrapper Implementation

> **Purpose**: Implement Redis MULTI/EXEC transaction wrapper for NoDb base class to provide ACID guarantees for cache operations
> **Target**: GitHub Copilot / Codex
> **Created**: 2025-10-24
> **Status**: Active

## Context

The current NoDb architecture uses file-based JSON persistence with Redis caching. While this works, it lacks ACID guarantees for cache invalidation operations. This prompt implements Redis transactions to ensure atomic cache updates and invalidation.

Current flow:
```
controller.dump_and_unlock() → write file → update Redis cache → release lock
```

Proposed flow:
```
controller.dump_and_unlock_with_transaction() → MULTI → write file → SET cache → DEL invalidations → EXEC → release lock
```

## Prerequisites

- [x] cache_invalidation_rules.json exists and is validated
- [x] RedisPrep timestamp infrastructure is understood
- [x] NoDb locking patterns are understood
- [x] Tests pass in baseline: `wctl run-pytest tests/nodb/test_base.py`

## Objective

Implement Redis MULTI/EXEC transaction wrapper in NoDb base class that provides atomic cache operations while maintaining backward compatibility.

**Success looks like**: NoDb controllers can use `dump_and_unlock_with_transaction()` for ACID cache operations, while existing `dump_and_unlock()` continues to work.

## Reference Documents

- `wepppy/nodb/base.py` – Current NoDb implementation with locking
- `wepppy/nodb/redis_prep.py` – Redis client setup and DB allocation
- `wepppy/nodb/cache_invalidation_rules.json` – Cache key templates
- `docs/dev-notes/redis_dev_notes.md` – Redis usage patterns

## Working Set

### Files to Read (Inputs)
- `wepppy/nodb/base.py` – Understand current dump_and_unlock() implementation
- `wepppy/nodb/redis_prep.py` – See Redis client setup and DB constants
- `wepppy/config/redis_settings.py` – Redis configuration and client factory

### Files to Modify (Outputs)
- `wepppy/nodb/base.py` – Add transaction wrapper method

### Files to Reference (Dependencies)
- `wepppy/nodb/cache_invalidation_rules.json` – Cache key templates (read at runtime)

## Step-by-Step Instructions

1. **Analyze current dump_and_unlock() method**
   - Read the current implementation in `wepppy/nodb/base.py`
   - Understand the file write + Redis cache update + lock release sequence
   - Note any error handling patterns

2. **Design transaction wrapper API**
   - Add `dump_and_unlock_with_transaction(self, invalidation_tasks: List[str] = None) -> None`
   - Method should wrap cache operations in MULTI/EXEC while keeping file I/O outside transaction
   - Maintain same error handling as current method

3. **Implement Redis transaction logic**
   ```python
   def dump_and_unlock_with_transaction(self, invalidation_tasks: List[str] = None) -> None:
       # File write happens outside transaction (can't rollback)
       self._dump_to_file()
       
       # Redis operations happen in transaction
       with self.redis.pipeline() as pipe:
           pipe.multi()
           # Update own cache
           pipe.set(self._cache_key(), self._serialize_for_cache())
           # Invalidate dependent caches if specified
           if invalidation_tasks:
               for task in invalidation_tasks:
                   # Load rules and delete cache keys
                   pass
           pipe.execute()
       
       # Release lock (unchanged)
       self._unlock()
   ```

4. **Add cache key generation**
   - Add `_cache_key(self) -> str` method to generate controller-specific cache keys
   - Use pattern: `nodb_cache:{run_id}:{controller_name}`

5. **Add invalidation logic**
   - Load `cache_invalidation_rules.json` at method call time
   - For each invalidation_task, find affected controllers
   - Generate and delete cache keys for affected controllers

6. **Add error handling**
   - If transaction fails, log error but don't fail the operation (file was already written)
   - Consider alerting for transaction failures
   - Ensure lock is always released in finally block

## Observable Outputs

### Before (Current State)
```python
def dump_and_unlock(self) -> None:
    """Write to file and update cache, then release lock."""
    self._dump_to_file()
    self.redis.set(self._cache_key(), self._serialize_for_cache())
    self._unlock()
```

### After (Target State)
```python
def dump_and_unlock_with_transaction(self, invalidation_tasks: List[str] = None) -> None:
    """Write to file, update cache atomically with invalidations, then release lock."""
    self._dump_to_file()
    
    try:
        with self.redis.pipeline() as pipe:
            pipe.multi()
            pipe.set(self._cache_key(), self._serialize_for_cache())
            if invalidation_tasks:
                for task in invalidation_tasks:
                    # Delete dependent cache keys
                    pass
            pipe.execute()
    except Exception as e:
        # Log but don't fail - file was written successfully
        logger.warning(f"Cache transaction failed: {e}")
    
    self._unlock()

def dump_and_unlock(self) -> None:
    """Backward compatibility - no transactions."""
    self._dump_to_file()
    self.redis.set(self._cache_key(), self._serialize_for_cache())
    self._unlock()
```

## Anti-Patterns to Avoid

❌ **Don't wrap file I/O in transaction**:
```python
# Wrong - file operations can't be rolled back
with pipe.pipeline() as pipe:
    pipe.multi()
    self._dump_to_file()  # Can't rollback file writes!
    pipe.set(cache_key, data)
    pipe.execute()
```

✅ **Do file I/O outside transaction**:
```python
# Correct - file write first, then atomic cache operations
self._dump_to_file()  # Commit file changes
with pipe.pipeline() as pipe:
    pipe.multi()
    pipe.set(cache_key, data)  # Atomic cache operations
    pipe.execute()
```

## Validation Gates

### Automated Checks
```bash
# Unit tests for transaction wrapper
wctl run-pytest tests/nodb/test_redis_transactions.py -v

# Integration tests with real Redis
wctl run-pytest tests/nodb/test_base.py::test_dump_and_unlock_with_transaction -v

# Backward compatibility
wctl run-pytest tests/nodb/test_base.py::test_dump_and_unlock_backward_compatibility -v
```

### Manual Verification
- [ ] Redis transactions work in docker-compose.dev.yml
- [ ] File writes succeed even if Redis fails
- [ ] Locks are always released
- [ ] Performance impact is minimal (<5% regression)

## Deliverables

1. `dump_and_unlock_with_transaction()` method in NoDb base class
2. `_cache_key()` helper method for cache key generation
3. Cache invalidation logic that loads rules and deletes keys
4. Comprehensive error handling and logging
5. Unit tests for transaction wrapper
6. Backward compatibility preserved

## Handoff Format

**Completed**: YYYY-MM-DD

**Changes Made**:
- Added Redis transaction wrapper to NoDb base class
- Implemented cache invalidation logic
- Added comprehensive error handling

**Files Modified**:
- `wepppy/nodb/base.py`

**Test Results**:
```
[Paste test output showing transaction tests pass]
```

**Validation Status**:
- [x] Automated checks passed
- [x] Manual verification complete
- [x] Success criteria met

**Issues Encountered**:
- [Issue 1 and resolution]
- [Issue 2 and resolution]

**Next**: Ready for RedisPrep cache invalidation methods