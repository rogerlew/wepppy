# NoDb Lock Race Condition Testing

This directory contains test infrastructure for validating NoDb distributed locking mechanisms and reproducing race conditions that can lead to unresolved locks.

## Overview

The NoDb locking system uses Redis-based distributed locks with TTL expiration, singleton patterns, and token-based ownership validation. Under high concurrency or specific timing conditions, race conditions can occur that lead to:

- **504 Gateway Timeouts** (like the build_climate bug)
- **Permanently stuck locks**
- **Lock token mismatches**
- **TTL expiration corruption**
- **Thundering herd contention**

## Test Files

### `test_lock_race_conditions.py`
Comprehensive test suite covering all identified race condition scenarios:

- **Rapid Sequential Lock Acquisition** - Profile playback scenario
- **Singleton Race Conditions** - Multiple getInstance() calls
- **TTL Expiration Races** - Operations exceeding lock timeouts
- **Lock Token Mismatch** - Process crashes and recovery
- **Clear Locks vs Active Operations** - Lock cleanup conflicts

### `test_build_climate_race_conditions.py`
Focused tests reproducing the specific **504 Gateway Timeout bug** in the build_climate endpoint:

- Reproduces exact profile playback scenario
- Tests mitigation delays effectiveness
- Validates gateway timeout thresholds
- Tests concurrent HTTP + RQ worker scenarios

### `lock_contention_utils.py`
Utility library for creating controlled race conditions:

- `LockContentionSimulator` - Orchestrates concurrent lock attempts
- `short_lock_ttl()` - Context manager for TTL testing
- `corrupt_lock_token()` - Simulates process crashes
- `create_orphaned_lock()` - Creates Redis locks without local tokens
- `verify_lock_state_consistency()` - Validates Redis vs local state

### `trigger_lock_scenarios.py`
Manual debugging script for triggering specific race conditions:

```bash
# Run thundering herd scenario
python trigger_lock_scenarios.py thundering_herd /tmp/debug --threads 10

# Test TTL expiration
python trigger_lock_scenarios.py ttl_expiration /tmp/debug

# Create orphaned locks
python trigger_lock_scenarios.py orphaned_locks /tmp/debug
```

## Race Condition Scenarios

### 1. Rapid Sequential Lock Acquisition
**Cause**: Profile playback making rapid API calls to same endpoint
**Symptom**: 504 Gateway Timeout after 30 seconds
**Fix**: `time.sleep(1.0)` delays between requests

```python
# Test reproduces this:
for i in range(5):
    climate = Climate.getInstance(wd)
    with climate.locked():
        climate.parse_inputs()  # Heavy 2s operation
    # Without delays -> lock contention
```

### 2. Singleton Race Conditions
**Cause**: Multiple threads calling `getInstance()` simultaneously
**Symptom**: Multiple instances competing for same lock
**Fix**: Atomic singleton pattern validation

```python
# Test validates this doesn't happen:
def concurrent_getInstance():
    instance = Climate.getInstance(wd)
    assert id(instance) == expected_singleton_id
```

### 3. TTL Expiration During Operations
**Cause**: Lock TTL expires while operation still running
**Symptom**: State corruption, multiple processes thinking they own lock
**Fix**: Proper TTL management, operation timeouts

```python
with short_lock_ttl(1):  # 1 second TTL
    with controller.locked():
        time.sleep(5)  # Exceeds TTL -> corruption
```

### 4. Lock Token Mismatch
**Cause**: Process crash between lock acquire and release
**Symptom**: `unlock() called with non-matching token`
**Fix**: Force unlock capability, token validation

```python
controller.lock()
# Simulate crash
corrupt_lock_token(controller)
controller.unlock()  # Fails
controller.unlock('--force')  # Succeeds
```

### 5. Clear Locks vs Active Operations
**Cause**: `clear_locks()` called while operations hold locks
**Symptom**: `cannot dump to unlocked db`
**Fix**: Coordination between clear_locks and active operations

## Running Tests

### Full Test Suite
```bash
# Run all NoDb lock tests
wctl run-pytest tests/nodb/test_lock_race_conditions.py -v

# Run specific build_climate tests
wctl run-pytest tests/nodb/test_build_climate_race_conditions.py -v

# Run slow tests (includes timing-sensitive scenarios)
wctl run-pytest tests/nodb/ -m slow -v
```

### Individual Scenarios
```bash
# Lock cache refresh regression
wctl run-pytest tests/nodb/test_lock_race_conditions.py::test_getinstance_refreshes_after_external_dump -v

# Rapid sequential requests with mitigation
wctl run-pytest tests/nodb/test_build_climate_race_conditions.py::TestBuildClimateRaceCondition::test_regression_profile_playback_without_delays -v
```

### Manual Debugging
```bash
# Interactive debugging
python tests/nodb/trigger_lock_scenarios.py thundering_herd
python tests/nodb/trigger_lock_scenarios.py rapid_sequential --requests 20
python tests/nodb/trigger_lock_scenarios.py ttl_expiration
```

## Mitigation Strategies

### 1. Temporal Separation
Add delays between rapid sequential requests:
```python
# In API endpoints
time.sleep(1.0)  # After heavy operations

# In profile playback
time.sleep(1.0)  # Between requests
```

### 2. Lock Validation
Verify lock state consistency:
```python
state = verify_lock_state_consistency(controller)
assert state['states_consistent'], "Lock state corrupted"
```

### 3. TTL Management
Monitor operation duration vs TTL:
```python
start_time = time.time()
with controller.locked():
    heavy_operation()
assert time.time() - start_time < LOCK_DEFAULT_TTL
```

### 4. Recovery Mechanisms
Provide force unlock and clear locks:
```python
# Force unlock stuck locks
controller.unlock('--force')

# Clear all locks for runid
clear_locks(runid)
```

### 5. Singleton Cache Refresh
Ensure cached controllers pick up on-disk changes:
- `test_getinstance_refreshes_after_external_dump` verifies cached instances merge refreshed state
- `test_getinstance_ignore_lock_bypasses_cache` confirms `ignore_lock=True` rehydrates without polluting the cache
- `test_getinstance_readonly_not_cached` ensures READONLY runs never populate `_instances`

Use these tests as guardrails when modifying `wepppy/nodb/base.py` caching logic.

## Test Markers

- `@pytest.mark.nodb` - All NoDb-related tests
- `@pytest.mark.slow` - Tests with timing dependencies (>2s)
- `@pytest.mark.integration` - Tests requiring Redis/external services

## Expected Test Results

### Before Fixes (Reproducing Bugs)
- Thundering herd: 1 success, N-1 lock errors
- Rapid sequential: First succeeds, others fail quickly
- TTL expiration: State corruption detected
- Token corruption: Unlock failures without force

### After Fixes (Validating Solutions)
- With delays: All requests succeed
- Proper TTL: No corruption
- Force unlock: Stuck locks recoverable
- Clear locks: Clean recovery

## Contributing

When adding new race condition tests:

1. **Reproduce the bug first** - Show the race condition occurs
2. **Test the fix** - Show mitigation prevents the race
3. **Add timing assertions** - Validate performance characteristics
4. **Use realistic scenarios** - Match actual usage patterns
5. **Document the race** - Explain timing windows and triggers

## Debugging Tips

### Redis Inspection
```bash
# Check active locks
redis-cli -n 0 KEYS "nodb-lock:*"

# Check lock payload
redis-cli -n 0 GET "nodb-lock:runid:climate.nodb"

# Check hash fields
redis-cli -n 0 HGETALL "runid"
```

### Lock State Analysis
```python
from tests.nodb.lock_contention_utils import verify_lock_state_consistency
state = verify_lock_state_consistency(controller)
print(f"Consistent: {state['states_consistent']}")
```

### Performance Profiling
```python
import time
start = time.time()
with controller.locked():
    operation()
duration = time.time() - start
print(f"Operation took {duration:.2f}s (TTL: {LOCK_DEFAULT_TTL}s)")
```

## References

- [AGENTS.md](../../AGENTS.md#race-contention-scenarios-in-nodb-distributed-locking) - Full race condition analysis
- [wepppy/nodb/base.py](../../wepppy/nodb/base.py) - NoDb locking implementation
- [wepppy/weppcloud/routes/rq/api/api.py](../../wepppy/weppcloud/routes/rq/api/api.py) - Fixed build_climate endpoint
- [wepppy/profile_recorder/playback.py](../../wepppy/profile_recorder/playback.py) - Fixed playback delays
