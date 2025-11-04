# NoDb Lock Race Condition Resolution - Agent Prompt

> **God-Tier Agent Prompt for resolving NoDb distributed locking race conditions and ensuring full tests/nodb suite passes**

**Task:** Analyze, debug, and fix all NoDb lock race conditions, ensuring the complete `tests/nodb/` test suite passes without failures or intermittent issues.

**Context:** The WEPPcloud NoDb system uses Redis-based distributed locks with TTL expiration, singleton patterns, and token-based ownership validation. Recent work identified and partially fixed race conditions that caused 504 Gateway Timeouts in the build_climate endpoint during profile playback scenarios. However, the test suite may still have intermittent failures due to remaining lock contention issues.

---

## 1. Anchor Documents (READ THESE FIRST)

**Primary References:**
1. **[AGENTS.md](../../AGENTS.md)** - NoDb locking guidance and architecture
   - Search for "distributed lock", "NoDb locking", and "with self.locked()" patterns
   - Redis DB allocation (DB 0 for locks, DB 13 for cache)
   - General NoDb conventions and singleton patterns

2. **[tests/nodb/README.md](README.md)** - Complete test infrastructure guide
   - Test file organization and purpose
   - Race condition scenarios and expected results
   - Running tests and debugging tips
   - Mitigation strategies documentation

3. **[wepppy/nodb/base.py](../../wepppy/nodb/base.py)** - NoDb locking implementation
   - `locked()` context manager (lines ~957-978)
   - `lock()` and `unlock()` methods (lines ~1314-1370)
   - `getInstance()` singleton pattern (lines ~830-890)
   - Redis lock key management and TTL handling

4. **[wepppy/weppcloud/routes/rq/api/api.py](../../wepppy/weppcloud/routes/rq/api/api.py)** - Fixed build_climate endpoint
   - Contains implemented `time.sleep(1.0)` mitigation
   - Shows pattern for preventing rapid sequential lock acquisition

5. **[wepppy/profile_recorder/playback.py](../../wepppy/profile_recorder/playback.py)** - Fixed playback delays
   - Contains response time tracking and race condition delays
   - Shows how profile playback was causing thundering herd scenarios

**Supporting Documents:**
- **[tests/conftest.py](../conftest.py)** - Pytest configuration and custom markers
- **[docs/dev-notes/redis_dev_notes.md](../../docs/dev-notes/redis_dev_notes.md)** - Redis usage patterns
- **[wepppy/nodb/core/climate.py](../../wepppy/nodb/core/climate.py)** - Climate controller (original bug source)

---

## 2. Working Set (Explicit File Scope)

**Input Files (Read and Analyze):**
```
tests/nodb/test_lock_race_conditions.py          # Main race condition test suite
tests/nodb/test_build_climate_race_conditions.py # Build_climate specific tests  
tests/nodb/lock_contention_utils.py              # Testing utilities
tests/nodb/trigger_lock_scenarios.py             # Manual debugging script
tests/nodb/test_locked.py                        # Basic lock tests
tests/nodb/test_base_unit.py                     # Base functionality tests
tests/nodb/test_*.py                             # All other nodb tests
wepppy/nodb/base.py                              # Core locking implementation
wepppy/nodb/core/*.py                            # NoDb controllers
tests/conftest.py                                # Pytest configuration
```

**Output Files (Modify as Needed):**
```
tests/nodb/test_lock_race_conditions.py          # Fix failing tests
tests/nodb/test_build_climate_race_conditions.py # Fix climate-specific issues
tests/nodb/lock_contention_utils.py              # Enhance utilities if needed
wepppy/nodb/base.py                              # Fix core locking bugs
tests/conftest.py                                # Add fixtures/stubs if needed
Any other test files that fail                   # Fix specific issues
```

**Reference Files (Dependencies):**
```
wepppy/weppcloud/routes/rq/api/api.py            # Shows working mitigation pattern
wepppy/profile_recorder/playback.py              # Shows delay implementation
wepppy/nodb/core/climate.py                      # Example NoDb controller
wepppy/all_your_base/*.py                        # Utility functions
```

**Exclusions (Do Not Modify):**
```
wepppy/nodb/core/ron.py                          # Leave existing controllers alone
wepppy/nodb/mods/*                               # Don't modify mod controllers
docker/ configuration files                      # Don't change infrastructure
Production deployment scripts                     # Don't touch deployment
```

---

## 3. Identified Race Condition Types

**From AGENTS.md analysis, these are the 5 race conditions to resolve:**

### 3.1 Rapid Sequential Lock Acquisition Race (PRIMARY ISSUE)
**Trigger:** Multiple rapid API calls to same endpoint (profile playback scenario)
**Manifestation:** `NoDbAlreadyLockedError` exceptions, 30+ second delays, 504 Gateway Timeouts
**Root Cause:** Multiple processes hit same Redis `SET NX EX` window simultaneously
**Current Fix:** `time.sleep(1.0)` delays in api.py and playback.py
**Test Location:** `test_lock_race_conditions.py::TestRapidSequentialLockAcquisition`

### 3.2 getInstance() Singleton Race
**Trigger:** Multiple threads calling `Climate.getInstance(wd)` simultaneously  
**Manifestation:** Multiple instances competing for same distributed lock
**Root Cause:** Cache check and population not atomic
**Test Location:** `test_lock_race_conditions.py::TestSingletonRaceConditions`

### 3.3 TTL Expiration During Operations
**Trigger:** Lock TTL expires while legitimate operation still running
**Manifestation:** Data corruption, `RuntimeError("cannot dump to unlocked db")`
**Root Cause:** Default 6-hour TTL can be exceeded by long operations
**Test Location:** `test_lock_race_conditions.py::TestTTLExpirationRace`

### 3.4 Lock Token Mismatch Race  
**Trigger:** Process crashes or network partition during lock ownership
**Manifestation:** `RuntimeError('unlock() called with non-matching token')`
**Root Cause:** Local token storage corrupted, Redis key expires but process thinks it owns lock
**Test Location:** `test_lock_race_conditions.py::TestLockTokenMismatchRace`

### 3.5 Clear Locks vs Active Operations Race
**Trigger:** `clear_locks()` utility runs while active operations hold locks
**Manifestation:** Operations fail with "cannot dump to unlocked db"
**Root Cause:** No coordination between clear_locks and active `locked()` contexts
**Test Location:** `test_lock_race_conditions.py::TestClearLocksVsActiveOperations`

---

## 4. Expected Test Results (Validation Gates)

**Bug Reproduction Tests (Before Fixes Applied):**
```bash
# These tests should PASS by reproducing the race conditions (demonstrating the bugs exist)
test_thundering_herd_lock_acquisition                 # 1 success, N-1 lock errors
test_rapid_sequential_without_delays                  # First succeeds, others fail quickly  
test_reproduce_original_bug_scenario                  # 1 success, 4 failures (demonstrates bug)
test_operation_exceeds_lock_ttl                       # TTL expiry detected
test_stale_token_unlock_attempt                       # RuntimeError on unlock
test_clear_locks_during_active_operation               # Operation fails after lock cleared
```

**Prevention Tests (After Fixes Applied):**
```bash
# These tests should PASS by preventing the race conditions (validating fixes work)
test_rapid_sequential_with_delays                     # All requests succeed with delays
test_build_climate_with_mitigation_delays             # All requests succeed 
test_concurrent_getinstance_calls                     # All get same singleton instance
test_force_unlock_recovery                            # Stuck locks recoverable
test_clear_locks_cleanup                              # Clean recovery possible
```

**Test Evolution Strategy:**
- **Reproduction tests** (test_reproduce_*, test_*_without_delays) should be converted to regression tests
- **After fixes are applied:** Modify these tests to assert the NEW fixed behavior instead of the old buggy behavior
- **Keep test names descriptive:** Rename to test_regression_* or test_fixed_* to reflect their new purpose
- **Example transformation:**
  ```python
  # BEFORE (reproduces bug):
  assert len(successful_requests) == 1  # Only first succeeds, others fail
  
  # AFTER (validates fix):
  assert len(successful_requests) == request_count  # All succeed with proper delays
  ```

**Full Suite Validation:**
```bash
# All tests must pass consistently (run multiple times to check for intermittent failures)
wctl run-pytest tests/nodb/ -v                        # All tests pass
wctl run-pytest tests/nodb/ -m slow -v                # Slow/timing tests pass
wctl run-pytest tests/nodb/test_lock_race_conditions.py -v --count=3  # No intermittent failures
```

---

## 5. Debugging Context and Background

### 5.1 Original Bug Investigation
**Date:** November 2025  
**Symptom:** 504 Gateway Timeout in `/runs/<runid>/<config>/rq/api/build_climate` endpoint  
**Trigger:** Profile playback system making rapid sequential requests  
**Timeline:** Requests taking 30+ seconds, exceeding HAProxy timeout  

**Root Analysis:**
- Profile playback makes rapid requests: `POST build_climate` → `POST build_climate` → `POST build_climate`
- Each request: `climate = Climate.getInstance(wd)` → `with climate.locked():` → `climate.parse_inputs()`
- `parse_inputs()` is heavy operation (2+ seconds with file I/O)
- Multiple requests queue up waiting for Redis lock
- First request succeeds, others get `NoDbAlreadyLockedError` immediately
- BUT: timing window allows multiple processes to check `islocked()` simultaneously and all see "available"

**Implemented Fix:**
- Added `time.sleep(1.0)` in `api.py` after `parse_inputs()` call
- Added `time.sleep(1.0)` in `playback.py` between requests  
- Added response time tracking to monitor lock contention effects

### 5.2 Redis Locking Architecture Context

**Lock Key Pattern:** `nodb-lock:{runid}:{relpath}`  
**Storage:** Redis DB 0 (distributed locks), DB 13 (NoDb cache)  
**TTL:** Default 6 hours (`LOCK_DEFAULT_TTL = 6 * 3600`)  
**Token:** UUID-based ownership validation  
**Legacy:** Hash fields `locked:{relpath}` for UI compatibility  

**Critical Code Paths:**
```python
# Lock acquisition (base.py:1314-1342)
def lock(self, ttl: Optional[int] = None):
    lock_key = self._distributed_lock_key
    token = uuid.uuid4().hex
    payload = _serialize_lock_payload(token, ttl_seconds)
    acquired = redis_lock_client.set(lock_key, payload, nx=True, ex=ttl_seconds)
    if not acquired:
        raise NoDbAlreadyLockedError(message)

# Context manager (base.py:957-978)  
@contextmanager
def locked(self, validate_on_success: bool = True):
    self.lock()
    try:
        yield
    except Exception:
        self.unlock()
        raise
    self.dump_and_unlock()
```

### 5.3 Test Infrastructure Context

**Test Organization:**
- `MockNoDbController` class simulates heavy operations
- `LockContentionSimulator` orchestrates concurrent scenarios
- `short_lock_ttl()` context manager tests TTL expiration
- `trigger_lock_scenarios.py` script for manual debugging

**Key Test Patterns:**
```python
# Rapid sequential pattern (reproduces profile playback)
for i in range(request_count):
    controller = MockNoDbController.getInstance(wd)
    with controller.locked():
        controller.heavy_operation(0.5)  # 500ms work

# Thundering herd pattern (reproduces concurrent access)
def worker(thread_id):
    controller = MockNoDbController.getInstance(wd)
    with controller.locked():
        controller.heavy_operation(2.0)  # 2s work

threads = [Thread(target=worker, args=(i,)) for i in range(5)]
```

---

## 6. Deliverables and Success Criteria

### 6.1 Core Deliverables

**A. Race Condition Analysis Report**
- Document current test failure patterns
- Identify specific timing windows causing failures
- Map each test failure to one of the 5 race condition types
- Provide timing analysis (expected vs actual durations)

**B. Lock Implementation Fixes**
- Fix any bugs in `wepppy/nodb/base.py` locking mechanism
- Ensure atomic operations where needed
- Validate TTL handling and token management
- Add defensive programming for edge cases

**C. Test Suite Stabilization and Evolution**  
- Fix all intermittent test failures
- **Convert reproduction tests to regression tests** after fixes are applied
- Update test assertions to validate fixed behavior instead of reproducing bugs
- Rename tests for clarity (test_reproduce_* → test_regression_* or test_fixed_*)
- Ensure tests consistently pass/fail as expected
- Add missing test coverage for edge cases
- Improve test reliability and timing assertions

**D. Enhanced Debugging Infrastructure**
- Improve `lock_contention_utils.py` if needed
- Add better error messages and diagnostics
- Enhance `trigger_lock_scenarios.py` for edge cases
- Document debugging workflows

### 6.2 Validation Commands (Must All Pass)

**Primary Test Suite:**
```bash
# Full test suite - must pass consistently
wctl run-pytest tests/nodb/ -v

# Race condition tests specifically  
wctl run-pytest tests/nodb/test_lock_race_conditions.py -v

# Build climate specific tests
wctl run-pytest tests/nodb/test_build_climate_race_conditions.py -v

# Run multiple times to check for intermittent failures
wctl run-pytest tests/nodb/test_lock_race_conditions.py --count=5 -v

# Slow tests with timing dependencies
wctl run-pytest tests/nodb/ -m slow -v
```

**Manual Validation:**
```bash
# Trigger scripts should work without errors
wctl exec weppcloud python tests/nodb/trigger_lock_scenarios.py thundering_herd /tmp/test1 --threads 5
wctl exec weppcloud python tests/nodb/trigger_lock_scenarios.py rapid_sequential /tmp/test2 --requests 10
wctl exec weppcloud python tests/nodb/trigger_lock_scenarios.py ttl_expiration /tmp/test3
```

**Integration Validation:**
```bash
# Build climate endpoint should work (if test environment supports it)
# Profile playback should work without timeouts
wctl run-test-profile us-small-wbt-daymet-rap-wepp  # If available
```

### 6.3 Success Criteria Checklist

**Functional Requirements:**
- [ ] All tests in `tests/nodb/` pass consistently
- [ ] No intermittent failures across multiple test runs
- [ ] Race condition tests reproduce bugs when expected
- [ ] Race condition tests validate fixes when expected
- [ ] Manual trigger scripts work for all scenarios

**Performance Requirements:**
- [ ] Rapid sequential tests complete in <15 seconds total
- [ ] Thundering herd tests resolve locks correctly (1 winner, N-1 losers)
- [ ] TTL expiration tests detect timeouts within expected windows
- [ ] Response time tracking shows reasonable lock acquisition times

**Stability Requirements:**
- [ ] Tests can run 10+ times without failures
- [ ] No leaked locks after test completion
- [ ] No Redis connection issues during test execution
- [ ] Mock controllers behave consistently

**Documentation Requirements:**
- [ ] Any code changes are commented with race condition context
- [ ] Test failure root causes are documented
- [ ] Debugging workflows are clear and reproducible
- [ ] Handoff report includes specific timings and test results

---

## 7. Implementation Strategy

### 7.1 Execution Order (Critical Path)

**Phase 1: Diagnostic (30 minutes)**
1. Run full test suite to identify current failure patterns
2. Analyze specific timing issues and error messages  
3. Map failures to the 5 race condition categories
4. Document baseline performance metrics

**Phase 2: Core Fixes (60 minutes)**
1. Fix any fundamental bugs in `wepppy/nodb/base.py`
2. Address singleton pattern issues if found
3. Fix TTL handling and token management bugs
4. Ensure proper cleanup in failure scenarios

**Phase 3: Test Stabilization and Evolution (45 minutes)**
1. Fix test infrastructure issues (fixtures, timing)
2. **Convert reproduction tests to regression tests** after core fixes
3. Update test assertions: old buggy behavior → new fixed behavior
4. Rename tests for clarity (test_reproduce_* → test_regression_*)
5. Improve test assertions and error handling
6. Add missing edge case coverage
7. Validate test isolation and cleanup

**Phase 4: Validation (30 minutes)**
1. Run test suite multiple times to ensure consistency
2. Test manual debugging scripts
3. Validate performance characteristics
4. Document any remaining limitations

### 7.2 Debugging Methodology

**For Each Test Failure:**
1. **Reproduce:** Run the failing test in isolation 5+ times
2. **Timing:** Add debug prints to understand timing windows
3. **State:** Check Redis lock state before/after operations
4. **Race:** Identify which of the 5 race types is occurring
5. **Fix:** Apply targeted fix based on race condition type
6. **Test Evolution:** After core fix, update test assertions from bug reproduction to regression validation
7. **Validate:** Ensure fix doesn't break other scenarios

**Redis State Inspection:**
```python
# Add to failing tests for debugging
from tests.nodb.lock_contention_utils import verify_lock_state_consistency
state = verify_lock_state_consistency(controller)
print(f"Lock state: {state}")

# Manual Redis inspection
redis-cli -n 0 KEYS "nodb-lock:*"
redis-cli -n 0 GET "nodb-lock:runid:climate.nodb"
```

### 7.3 Common Fix Patterns

**Rapid Sequential Issues:**
- Add temporal separation (`time.sleep()`)
- Use exponential backoff for retries
- Queue operations instead of failing fast

**Singleton Issues:**  
- Make cache operations atomic
- Add proper locking around instance creation
- Clear caches reliably in test fixtures

**TTL Issues:**
- Validate operation time vs TTL before starting
- Add TTL renewal for long operations
- Graceful degradation when TTL expires

**Token Issues:**
- Improve token validation and cleanup
- Add force unlock capabilities
- Better error messages for token mismatches

**Clear Locks Issues:**
- Coordinate with active operations
- Add warning periods before clearing
- Improve scope isolation

---

## 8. Handoff Report Template

**When task is complete, provide this structured report:**

### 8.1 Execution Summary
```
Task: NoDb Lock Race Condition Resolution
Start Time: [timestamp]
End Time: [timestamp]  
Total Duration: [minutes]
Overall Status: [SUCCESS/PARTIAL/FAILED]
```

### 8.2 Test Results
```
Final Test Run Results:
- tests/nodb/ overall: [PASS/FAIL] ([X] passed, [Y] failed)
- test_lock_race_conditions.py: [PASS/FAIL] 
- test_build_climate_race_conditions.py: [PASS/FAIL]
- Multiple run consistency: [STABLE/INTERMITTENT]
- Manual trigger scripts: [WORKING/ISSUES]

Timing Analysis:
- Rapid sequential test duration: [X]s (expected <15s)
- Thundering herd lock resolution: [correct/incorrect] 
- TTL expiration detection: [within/outside] expected window
- Response time tracking: [reasonable/concerning] averages
```

### 8.3 Issues Resolved
```
Race Condition Fixes Applied:
1. [Type]: [Description of issue] → [Fix implemented]
2. [Type]: [Description of issue] → [Fix implemented]
[...]

Core Implementation Changes:
- wepppy/nodb/base.py: [changes made]
- Test infrastructure: [improvements made]
- Other files: [list changes]
```

### 8.4 Issues Remaining  
```
Known Limitations:
- [Description of any unresolved issues]
- [Workarounds or mitigation strategies]
- [Recommended follow-up work]

Test Environment Notes:
- [Any environment-specific requirements]
- [Redis configuration dependencies]
- [Timing sensitivity notes]
```

### 8.5 Validation Evidence
```
Commands Run Successfully:
✅ wctl run-pytest tests/nodb/ -v
✅ wctl run-pytest tests/nodb/test_lock_race_conditions.py --count=5 -v  
✅ wctl exec weppcloud python tests/nodb/trigger_lock_scenarios.py thundering_herd /tmp/test --threads 5
[... list all validation commands that passed]

Performance Metrics:
- Lock acquisition time: [average] ms
- Test suite execution time: [total] minutes
- Race condition reproduction rate: [consistent/variable]
```

---

## 9. Risk Mitigation and Constraints

### 9.1 High-Risk Changes (Avoid)
- **Do not modify core Redis configuration** - could break production
- **Do not change lock key formats** - backward compatibility critical
- **Do not alter NoDb serialization** - legacy payloads must still load
- **Do not break existing singleton behavior** - other code depends on it

### 9.2 Safe Modification Zones
- **Test infrastructure improvements** - isolated to test environment
- **Better error handling** - defensive programming is safe
- **Timing adjustments** - delays and timeouts are generally safe
- **Diagnostic improvements** - better logging and debugging

### 9.3 Rollback Plan
If changes cause broader issues:
1. **Revert core base.py changes** - keep test-only modifications
2. **Document specific failure modes** - for future investigation  
3. **Isolate problematic tests** - mark with `@pytest.mark.skip` temporarily
4. **Provide clear handoff** - explain what worked vs what didn't

### 9.4 Environment Dependencies
- **Redis availability** - tests require Redis connection
- **Docker environment** - use `wctl` commands for consistency
- **Timing sensitivity** - some tests depend on precise timing
- **Resource isolation** - tests should clean up after themselves

---

## 10. Test Evolution Strategy (Critical Implementation Detail)

### 10.1 Reproduction vs Regression Testing Philosophy

**Current State:** The test suite contains both:
- **Reproduction tests** that demonstrate bugs exist (e.g., `test_reproduce_original_bug_scenario`)
- **Prevention tests** that validate fixes work (e.g., `test_rapid_sequential_with_delays`)

**After Fixes Applied:** Reproduction tests should be converted to regression tests that validate the fixed behavior.

### 10.2 Specific Test Transformations Required

**test_reproduce_original_bug_scenario:**
```python
# BEFORE (reproduces the 504 timeout bug):
assert len(successful_requests) == 1, f"Expected 1 success, got {len(successful_requests)}"
assert len(failed_requests) == 4, f"Expected 4 failures due to lock contention"

# AFTER (validates the fix prevents timeouts):
assert len(successful_requests) == 5, f"Expected all 5 to succeed with fixes, got {len(successful_requests)}"
assert len(failed_requests) == 0, f"Expected no failures with proper locking fixes"
```

**test_rapid_sequential_without_delays:**
```python
# BEFORE (demonstrates race condition):
assert success_count >= 1, "At least one operation should succeed"
# (implicitly expects others to fail)

# AFTER (validates race condition is resolved):
assert success_count == request_count, f"All {request_count} operations should succeed with fixes"
```

### 10.3 Recommended Test Names After Evolution

**Convert these test names:**
- `test_reproduce_original_bug_scenario` → `test_regression_no_504_timeouts`
- `test_rapid_sequential_without_delays` → `test_regression_rapid_sequential_all_succeed`
- `test_thundering_herd_lock_acquisition` → `test_regression_thundering_herd_orderly_processing`

**Keep these test names (already validate positive behavior):**
- `test_rapid_sequential_with_delays` (validates delays work)
- `test_concurrent_getinstance_calls` (validates singleton behavior)
- `test_build_climate_with_mitigation_delays` (validates endpoint fixes)

### 10.4 Implementation Guidance

**Two-Phase Approach:**
1. **Phase 1:** Run reproduction tests to confirm bugs exist and understand timing
2. **Phase 2:** After core fixes, convert reproduction tests to regression validation

**Conversion Process:**
```python
# Step 1: Apply core locking fixes to wepppy/nodb/base.py
# Step 2: Update test assertions and names
# Step 3: Validate all tests pass with new behavior
```

**Documentation Updates:**
- Update test docstrings to reflect new purpose
- Update README.md test descriptions
- Comment any timing changes or mitigation strategies

---

## 11. Context Management and Focus

**Given the complexity of this task and the large amount of context, prioritize as follows:**

### 11.1 Critical Path Focus
1. **Start with test failures** - let failing tests guide investigation
2. **Focus on reproducible issues** - intermittent failures are secondary
3. **Fix one race type at a time** - don't try to solve everything simultaneously
4. **Validate each fix thoroughly** - before moving to next issue

### 11.2 Context Window Management
- **Read anchor documents first** - establishes foundation
- **Focus on failing test code** - most relevant for immediate fixes
- **Reference implementation patterns** - from working fixes in api.py/playback.py
- **Use search strategically** - grep for specific error patterns

### 11.3 Decision Framework
For each potential change, ask:
- **Does this fix a specific test failure?** (prioritize)
- **Could this break other functionality?** (avoid if high risk)
- **Is this change testable and reversible?** (prefer)
- **Does this follow existing patterns?** (maintain consistency)

---

This prompt provides complete context and explicit guidance for resolving NoDb lock race conditions. The agent should execute methodically, validate thoroughly, and provide clear handoff documentation upon completion.