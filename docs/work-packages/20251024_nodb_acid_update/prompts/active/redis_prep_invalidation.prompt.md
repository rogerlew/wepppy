# RedisPrep Cache Invalidation Methods

> **Purpose**: Extend RedisPrep with cache invalidation methods that consume centralized rules to clear NoDb cache entries when tasks complete
> **Target**: GitHub Copilot / Codex
> **Created**: 2025-10-24
> **Status**: Active

## Context

**Why Cache Invalidation Matters**: NoDb controllers are singletons per working directory, but multiple processes can access the same run simultaneously. Without cache invalidation, processes would see stale cached data even after other processes updated the underlying .nodb files.

**Example Problem**:
1. Process A (RQ worker) runs climate build → updates Climate controller → writes climate.nodb → caches in Redis
2. Process B (web request) accesses Climate controller → reads stale cached data instead of fresh climate.nodb
3. Result: UI shows old climate data, inconsistent state across processes

**How Invalidation Fixes This**:
1. Process A completes climate build → prep.timestamp() → invalidates climate cache
2. Process B accesses Climate controller → cache miss → reloads from updated climate.nodb
3. Result: Cross-process consistency, fresh data everywhere

RedisPrep currently tracks task timestamps for dependency evaluation. We need to extend it to also handle cache invalidation when tasks complete, using the centralized `cache_invalidation_rules.json` to determine which controller caches to clear.

**Important**: Use cache-only invalidation. Delete Redis cache keys but do NOT modify controller attributes or disable tasks. Controllers handle cache misses gracefully and users can override invalidation decisions.

Current flow:
```
RQ task completes → prep.timestamp(TaskEnum.build_climate) → timestamp stored
```

Proposed flow:
```
RQ task completes → prep.timestamp(TaskEnum.build_climate) → prep.invalidate_caches_for_task('build_climate') → load rules → delete cache keys (cache-only)
```

## Prerequisites

- [x] cache_invalidation_rules.json exists and is validated
- [x] RedisPrep timestamp methods are understood
- [x] Controllers implement graceful cache miss handling
- [x] Tests pass in baseline: `wctl run-pytest tests/nodb/test_redis_prep.py`
- [x] Tests pass in baseline: `wctl run-pytest tests/nodb/test_redis_prep.py`

## Objective

Extend RedisPrep with `invalidate_caches_for_task(task_enum)` method that loads invalidation rules and deletes affected cache keys atomically.

**Success looks like**: When tasks complete, dependent controller caches are automatically invalidated using centralized rules.

## Reference Documents

- `wepppy/nodb/redis_prep.py` – Current RedisPrep implementation
- `wepppy/nodb/cache_invalidation_rules.json` – Invalidation rules schema
- `wepppy/config/redis_settings.py` – Redis client setup

## Working Set

### Files to Read (Inputs)
- `wepppy/nodb/redis_prep.py` – Current timestamp methods and Redis client usage
- `wepppy/nodb/cache_invalidation_rules.json` – Rules structure and cache key templates

### Files to Modify (Outputs)
- `wepppy/nodb/redis_prep.py` – Add cache invalidation methods

### Files to Reference (Dependencies)
- `wepppy/nodb/base.py` – NoDb cache key patterns (for consistency)

## Step-by-Step Instructions

1. **Analyze current RedisPrep structure**
   - Read existing timestamp methods (`timestamp()`, `remove_timestamp()`)
   - Understand Redis client usage and DB selection
   - Note error handling patterns

2. **Add rules loading method**
   ```python
   @staticmethod
   def _load_invalidation_rules() -> Dict[str, Any]:
       """Load cache invalidation rules from JSON file."""
       rules_path = _join(_thisdir, 'cache_invalidation_rules.json')
       with open(rules_path, 'r') as f:
           return json.load(f)
   ```

3. **Add cache key generation**
   ```python
   def _generate_cache_key(self, controller_name: str) -> str:
       """Generate cache key for a controller."""
       rules = self._load_invalidation_rules()
       template = rules['cache_keys'][controller_name]
       return template.format(run_id=self.run_id)
   ```

4. **Implement invalidation method**
   ```python
   def invalidate_caches_for_task(self, task_enum: TaskEnum) -> None:
       """Invalidate caches for controllers affected by the given task."""
       rules = self._load_invalidation_rules()
       task_name = str(task_enum)
       
       if task_name not in rules['rules']:
           return  # No invalidation rules for this task
       
       affected_controllers = rules['rules'][task_name]['invalidates_cache']
       
       # Delete cache keys for affected controllers
       cache_keys = [self._generate_cache_key(ctrl) for ctrl in affected_controllers]
       if cache_keys:
           self.redis.delete(*cache_keys)
       
       self.dump()  # Persist metadata changes
   ```

5. **Integrate with timestamp method**
   ```python
   def timestamp(self, key: TaskEnum) -> None:
       """Set timestamp and invalidate dependent caches."""
       now = int(time.time())
       self.__setitem__(str(key), now)
       
       # Invalidate caches for dependent controllers
       self.invalidate_caches_for_task(key)
   ```

6. **Add error handling**
   - If rules file is missing/corrupt, log warning but don't fail
   - If cache deletion fails, log error but continue
   - Ensure dump() always called to persist metadata

## Observable Outputs

### Before (Current State)
```python
def timestamp(self, key: TaskEnum) -> None:
    now = int(time.time())
    self.__setitem__(str(key), now)
```

### After (Target State)
```python
def timestamp(self, key: TaskEnum) -> None:
    now = int(time.time())
    self.__setitem__(str(key), now)
    
    # Invalidate dependent caches
    self.invalidate_caches_for_task(key)

def invalidate_caches_for_task(self, task_enum: TaskEnum) -> None:
    """Invalidate caches for controllers affected by the given task."""
    try:
        rules = self._load_invalidation_rules()
        task_name = str(task_enum)
        
        if task_name in rules['rules']:
            affected_controllers = rules['rules'][task_name]['invalidates_cache']
            cache_keys = [self._generate_cache_key(ctrl) for ctrl in affected_controllers]
            if cache_keys:
                self.redis.delete(*cache_keys)
    except Exception as e:
        logger.warning(f"Cache invalidation failed for {task_enum}: {e}")
    
    self.dump()
```

## Anti-Patterns to Avoid

❌ **Don't delete controller attributes** - Use cache-only invalidation
❌ **Don't disable tasks** - Let controllers handle invalid state gracefully
❌ **Don't load rules on every call**:
```python
# Wrong - inefficient for high-frequency calls
def invalidate_caches_for_task(self, task_enum: TaskEnum) -> None:
    with open('rules.json', 'r') as f:  # File I/O on every call!
        rules = json.load(f)
```

✅ **Cache rules or handle errors gracefully**:
```python
# Correct - load once with error handling
@staticmethod
@lru_cache(maxsize=1)
def _load_invalidation_rules() -> Dict[str, Any]:
    try:
        with open(rules_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load invalidation rules: {e}")
        return {'rules': {}, 'cache_keys': {}}
```

## Validation Gates

### Automated Checks
```bash
# Unit tests for invalidation methods
wctl run-pytest tests/nodb/test_cache_invalidation.py -v

# Integration tests with timestamp calls
wctl run-pytest tests/nodb/test_redis_prep.py::test_timestamp_with_invalidation -v

# Rules validation
wctl run-pytest tests/nodb/test_cache_invalidation_rules.py -v
```

### Manual Verification
- [ ] Cache keys are deleted when tasks complete
- [ ] Rules file changes are picked up (no caching issues)
- [ ] Invalid task names don't cause errors
- [ ] Redis errors are logged but don't break functionality

## Deliverables

1. `invalidate_caches_for_task()` method in RedisPrep
2. `_load_invalidation_rules()` static method with caching
3. `_generate_cache_key()` helper method
4. Integration with existing `timestamp()` method
5. Comprehensive error handling and logging
6. Unit tests for invalidation logic

## Handoff Format

**Completed**: YYYY-MM-DD

**Changes Made**:
- Extended RedisPrep with cache invalidation methods
- Integrated invalidation with timestamp setting
- Added rules loading and cache key generation

**Files Modified**:
- `wepppy/nodb/redis_prep.py`

**Test Results**:
```
[Paste test output showing invalidation tests pass]
```

**Validation Status**:
- [x] Automated checks passed
- [x] Manual verification complete
- [x] Success criteria met

**Issues Encountered**:
- [Issue 1 and resolution]
- [Issue 2 and resolution]

**Next**: Ready for RQ API endpoint updates