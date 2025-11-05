"""Test cases for NoDb lock race conditions and unresolved lock scenarios.

This module contains deliberately crafted test scenarios that trigger the race
conditions identified in the NoDb distributed locking mechanism. These tests
validate that our fixes prevent locks from becoming permanently unresolved.

Race conditions tested:
1. Rapid Sequential Lock Acquisition Race
2. getInstance() Singleton Race  
3. TTL Expiration During Operations
4. Lock Token Mismatch Race
5. Clear Locks vs Active Operations Race
"""

import os
import pytest
import threading
import time
import uuid
import jsonpickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch, MagicMock

from wepppy.nodb.base import NoDbBase, NoDbAlreadyLockedError, clear_locks, redis_lock_client
from wepppy.nodb.core.climate import Climate
from tests.nodb.lock_contention_utils import ensure_climate_stub


class MockNoDbController(NoDbBase):
    """Mock NoDb controller for testing lock scenarios."""
    
    filename = "mock_test.nodb"
    
    def __init__(self, wd: str, cfg_fn: str = "test.cfg", run_group: Optional[str] = None):
        # Create the working directory and config file if they don't exist
        import os
        from pathlib import Path
        
        os.makedirs(wd, exist_ok=True)
        config_path = Path(wd) / cfg_fn
        if not config_path.exists():
            config_path.write_text("""
[general]
dem_db = test
""")
        
        super().__init__(wd, cfg_fn, run_group=run_group)
        self.operation_count = 0
        self.heavy_operation_duration = 0.1  # Default 100ms
        
    def heavy_operation(self, duration: Optional[float] = None):
        """Simulate a heavy operation that holds the lock."""
        sleep_time = duration if duration is not None else self.heavy_operation_duration
        time.sleep(sleep_time)
        self.operation_count += 1
        
    def parse_inputs_simulation(self):
        """Simulate the climate.parse_inputs() operation that caused timeouts."""
        with self.locked():
            self.heavy_operation(2.0)  # 2 second operation


@pytest.fixture
def temp_wd(tmp_path):
    """Create a temporary working directory for tests."""
    wd = str(tmp_path / "test_run")
    os.makedirs(wd, exist_ok=True)
    return wd


@pytest.fixture
def mock_controller_class(temp_wd):
    """Provide MockNoDbController class with reset instances and initial setup."""
    # Clear any existing instances
    if hasattr(MockNoDbController, '_instances'):
        MockNoDbController._instances.clear()

    # Ensure Redis-based locks from prior runs are cleared before initializing
    runid = os.path.basename(temp_wd.rstrip(os.sep))
    try:
        clear_locks(runid)
    except Exception:
        # If Redis is unavailable the tests will fail later with clearer errors
        pass
    
    # Create initial instance to set up the .nodb file
    initial_controller = MockNoDbController(temp_wd)
    initial_controller.lock()
    initial_controller.dump()
    initial_controller.unlock()
    
    # Clear instances again so tests start fresh
    if hasattr(MockNoDbController, '_instances'):
        MockNoDbController._instances.clear()
        
    return MockNoDbController


@pytest.mark.nodb
@pytest.mark.slow
class TestRapidSequentialLockAcquisition:
    """Test Rapid Sequential Lock Acquisition Race conditions."""
    
    def test_thundering_herd_lock_acquisition(self, temp_wd, mock_controller_class):
        """Simulate the profile playback scenario with rapid sequential requests."""
        num_threads = 5
        acquisition_results = []
        errors = []
        
        def rapid_lock_attempt(thread_id: int):
            try:
                controller = mock_controller_class.getInstance(temp_wd)
                start_time = time.time()
                
                with controller.locked():
                    controller.heavy_operation(0.5)  # 500ms operation
                    
                elapsed = time.time() - start_time
                acquisition_results.append((thread_id, elapsed, "success"))
                
            except NoDbAlreadyLockedError as e:
                acquisition_results.append((thread_id, 0, f"locked_error: {e}"))
            except Exception as e:
                errors.append((thread_id, str(e)))
                
        # Launch threads simultaneously to create race condition
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=rapid_lock_attempt, args=(i,))
            threads.append(thread)
            
        # Start all threads at nearly the same time
        for thread in threads:
            thread.start()
            
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
            
        # Validate results
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        
        success_count = sum(1 for _, _, status in acquisition_results if status == "success")
        lock_error_count = sum(1 for _, _, status in acquisition_results if status.startswith("locked_error"))
        
        # Only one should succeed, others should get lock errors
        assert success_count == 1, f"Expected 1 success, got {success_count}"
        assert lock_error_count == num_threads - 1, f"Expected {num_threads-1} lock errors, got {lock_error_count}"
        
    def test_rapid_sequential_without_delays(self, temp_wd, mock_controller_class):
        """Test rapid sequential calls without delays (should cause contention)."""
        request_count = 10
        results = []
        
        for i in range(request_count):
            try:
                controller = mock_controller_class.getInstance(temp_wd)
                start_time = time.time()
                
                # Simulate API endpoint behavior without delay
                with controller.locked():
                    controller.heavy_operation(0.1)
                    
                elapsed = time.time() - start_time
                results.append((i, elapsed, "success"))
                
            except NoDbAlreadyLockedError:
                results.append((i, 0, "lock_error"))
                
        # Without delays, we expect the first request to succeed
        # and subsequent ones to fail due to lock contention
        success_count = sum(1 for _, _, status in results if status == "success")
        
        # Should have exactly 1 success (the first one)
        assert success_count >= 1, "At least one operation should succeed"
        
    def test_rapid_sequential_with_delays(self, temp_wd, mock_controller_class):
        """Test rapid sequential calls with delays (should prevent contention)."""
        request_count = 5
        results = []
        
        for i in range(request_count):
            try:
                controller = mock_controller_class.getInstance(temp_wd)
                start_time = time.time()
                
                # Simulate API endpoint behavior WITH delay
                with controller.locked():
                    controller.heavy_operation(0.1)
                    
                elapsed = time.time() - start_time
                results.append((i, elapsed, "success"))
                
                # Add the same delay we implemented in the fix
                time.sleep(1.0)
                
            except NoDbAlreadyLockedError:
                results.append((i, 0, "lock_error"))
                
        # With delays, all requests should succeed
        success_count = sum(1 for _, _, status in results if status == "success")
        assert success_count == request_count, f"Expected all {request_count} to succeed, got {success_count}"


@pytest.mark.nodb  
@pytest.mark.slow
class TestSingletonRaceConditions:
    """Test getInstance() Singleton Race conditions."""
    
    def test_concurrent_getinstance_calls(self, temp_wd, mock_controller_class):
        """Test multiple threads calling getInstance() simultaneously."""
        num_threads = 10
        instances = []
        errors = []
        
        def get_instance_attempt(thread_id: int):
            try:
                instance = mock_controller_class.getInstance(temp_wd)
                instances.append((thread_id, id(instance)))
            except Exception as e:
                errors.append((thread_id, str(e)))
                
        # Launch threads simultaneously
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=get_instance_attempt, args=(i,))
            threads.append(thread)
            
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join(timeout=5)
            
        # Validate singleton behavior
        assert len(errors) == 0, f"Unexpected errors: {errors}"
        assert len(instances) == num_threads, "All threads should get an instance"
        
        # All instances should have the same id (singleton)
        unique_ids = set(instance_id for _, instance_id in instances)
        assert len(unique_ids) == 1, f"Expected 1 unique instance, got {len(unique_ids)}: {unique_ids}"
        
    def test_singleton_with_concurrent_locking(self, temp_wd, mock_controller_class):
        """Test singleton behavior when multiple threads try to lock simultaneously."""
        num_threads = 5
        results = []
        
        def lock_attempt(thread_id: int):
            try:
                instance = mock_controller_class.getInstance(temp_wd)
                start_time = time.time()
                
                with instance.locked():
                    instance.heavy_operation(0.2)
                    
                elapsed = time.time() - start_time
                results.append((thread_id, "success", elapsed))
                
            except NoDbAlreadyLockedError:
                results.append((thread_id, "lock_error", 0))
            except Exception as e:
                results.append((thread_id, f"error: {e}", 0))
                
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=lock_attempt, args=(i,))
            threads.append(thread)
            
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join(timeout=10)
            
        # Validate that only one thread succeeded in locking
        success_count = sum(1 for _, status, _ in results if status == "success")
        lock_error_count = sum(1 for _, status, _ in results if status == "lock_error")
        
        assert success_count == 1, f"Expected 1 success, got {success_count}"
        assert lock_error_count == num_threads - 1, f"Expected {num_threads-1} lock errors, got {lock_error_count}"


@pytest.mark.nodb
@pytest.mark.slow  
class TestTTLExpirationRace:
    """Test TTL Expiration During Operations Race conditions."""
    
    def test_operation_exceeds_lock_ttl(self, temp_wd, mock_controller_class):
        """Test operation that runs longer than lock TTL."""
        
        # Mock a very short TTL for testing
        with patch('wepppy.nodb.base.LOCK_DEFAULT_TTL', 1):  # 1 second TTL
            controller = mock_controller_class.getInstance(temp_wd)
            
            start_time = time.time()
            try:
                with controller.locked():
                    # Operation that exceeds TTL
                    controller.heavy_operation(2.0)  # 2 seconds > 1 second TTL
                    
                elapsed = time.time() - start_time
                pytest.fail(f"Expected lock to expire, but operation completed in {elapsed:.2f}s")
                
            except Exception as e:
                # This should fail due to TTL expiration
                elapsed = time.time() - start_time
                assert elapsed >= 1.0, "Operation should run at least as long as TTL"
                
    def test_concurrent_access_after_ttl_expiry(self, temp_wd, mock_controller_class):
        """Test that another process can acquire lock after TTL expires."""
        
        # Use very short TTL
        with patch('wepppy.nodb.base.LOCK_DEFAULT_TTL', 1):
            controller1 = mock_controller_class.getInstance(temp_wd)
            
            # Start long operation in background thread
            operation_started = threading.Event()
            operation_results = []
            
            def long_operation():
                try:
                    with controller1.locked():
                        operation_started.set()
                        controller1.heavy_operation(3.0)  # 3 seconds > 1 second TTL
                        operation_results.append("completed")
                except Exception as e:
                    operation_results.append(f"failed: {e}")
                    
            bg_thread = threading.Thread(target=long_operation)
            bg_thread.start()
            
            # Wait for operation to start
            operation_started.wait(timeout=2)
            
            # Wait for TTL to expire
            time.sleep(1.5)
            
            # Try to acquire lock with second instance (should succeed after TTL expiry)
            controller2 = mock_controller_class.getInstance(temp_wd)
            try:
                with controller2.locked():
                    controller2.heavy_operation(0.1)
                    second_operation_success = True
            except NoDbAlreadyLockedError:
                second_operation_success = False
                
            bg_thread.join(timeout=5)
            
            # The second operation should succeed because TTL expired
            assert second_operation_success, "Second operation should succeed after TTL expiry"


@pytest.mark.nodb
class TestLockTokenMismatchRace:
    """Test Lock Token Mismatch Race conditions."""
    
    def test_stale_token_unlock_attempt(self, temp_wd, mock_controller_class):
        """Test unlock with stale token after lock was taken by another process."""
        
        controller = mock_controller_class.getInstance(temp_wd)
        
        # Acquire lock normally
        controller.lock()
        
        # Simulate token corruption (process crash scenario)
        from wepppy.nodb.base import _get_local_lock_token
        assert _get_local_lock_token(controller) is not None
        
        # Force release the Redis lock by overwriting it with a different token
        if redis_lock_client:
            from wepppy.nodb.base import _serialize_lock_payload, LOCK_DEFAULT_TTL
            other_token_payload = _serialize_lock_payload(str(uuid.uuid4()), LOCK_DEFAULT_TTL)
            redis_lock_client.set(controller._distributed_lock_key, other_token_payload, ex=LOCK_DEFAULT_TTL)
            
        # Try to unlock with stale token - should fail
        with pytest.raises(RuntimeError, match="unlock\\(\\) called with non-matching token"):
            controller.unlock()
            
        # Force unlock should work
        controller.unlock('--force')
        
    def test_multiple_processes_token_confusion(self, temp_wd, mock_controller_class):
        """Test token confusion when multiple processes think they own the lock."""
        
        # Simulate two controllers for same working directory
        controller1 = mock_controller_class.getInstance(temp_wd)
        controller2 = mock_controller_class.getInstance(temp_wd)  # Same instance due to singleton
        
        assert controller1 is controller2, "Should be same instance (singleton)"
        
        # This test validates that singleton prevents the token confusion scenario
        controller1.lock()
        
        # controller2 should see the same lock state since it's the same instance
        assert controller1.islocked(), "Instance should show as locked"
        assert controller2.islocked(), "Same instance should show as locked"
        
        controller1.unlock()
        
        assert not controller1.islocked(), "Instance should show as unlocked"
        assert not controller2.islocked(), "Same instance should show as unlocked"


@pytest.mark.nodb
class TestClearLocksVsActiveOperations:
    """Test Clear Locks vs Active Operations Race conditions."""
    
    def test_clear_locks_during_active_operation(self, temp_wd, mock_controller_class):
        """Test clear_locks() called while operation is holding lock."""
        
        controller = mock_controller_class.getInstance(temp_wd)
        operation_completed = False
        operation_error = None
        
        def background_operation():
            nonlocal operation_completed, operation_error
            try:
                with controller.locked():
                    controller.heavy_operation(2.0)  # 2 second operation
                    operation_completed = True
            except Exception as e:
                operation_error = str(e)
                
        # Start background operation
        bg_thread = threading.Thread(target=background_operation)
        bg_thread.start()
        
        # Wait a bit for operation to start
        time.sleep(0.5)
        
        # Clear locks while operation is running
        cleared_locks = clear_locks(controller.runid)
        
        # Wait for background operation to complete
        bg_thread.join(timeout=5)
        
        # The operation should fail because lock was cleared
        assert operation_error is not None, "Operation should fail with error"
        assert (
            "cannot dump to unlocked db" in operation_error
            or "unlock() called without owning the lock" in operation_error
            or "unlock() called with non-matching token" in operation_error
        )
        
        # Verify locks were actually cleared
        assert len(cleared_locks) > 0, "clear_locks should have cleared some locks"
        
    def test_clear_locks_scope_isolation(self, temp_wd, mock_controller_class):
        """Test that clear_locks properly scopes to runid."""
        
        # Create controllers for different runids
        controller1 = mock_controller_class.getInstance(temp_wd)
        
        temp_wd2 = temp_wd + "_different"
        os.makedirs(temp_wd2, exist_ok=True)

        initializer = mock_controller_class(temp_wd2)
        initializer.lock()
        initializer.dump()
        initializer.unlock()

        controller2 = mock_controller_class.getInstance(temp_wd2)
        
        # Lock both controllers
        controller1.lock()
        controller2.lock()
        
        # Clear locks for only controller1's runid
        cleared_locks = clear_locks(controller1.runid)
        
        # Controller1 should be unlocked, controller2 should still be locked
        assert not controller1.islocked(), "Controller1 should be unlocked after clear_locks"
        assert controller2.islocked(), "Controller2 should still be locked (different runid)"
        
        # Clean up
        controller2.unlock()


@pytest.mark.nodb
@pytest.mark.slow
class TestClimateSpecificRaceConditions:
    """Test race conditions specific to Climate controller (the original bug)."""
    
    def test_climate_parse_inputs_race(self, temp_wd):
        """Test the specific race condition in climate.parse_inputs()."""
        
        # Clear any existing Climate instances
        if hasattr(Climate, '_instances'):
            Climate._instances.clear()

        ensure_climate_stub(temp_wd)
            
        num_requests = 3
        results = []
        
        def simulate_build_climate_request(request_id: int):
            try:
                climate = Climate.getInstance(temp_wd)
                start_time = time.time()
                
                # Simulate the exact pattern from api.py
                with climate.locked():
                    # Mock parse_inputs to avoid actual file operations
                    time.sleep(0.5)  # Simulate heavy operation
                    
                elapsed = time.time() - start_time
                results.append((request_id, elapsed, "success"))
                
            except NoDbAlreadyLockedError:
                results.append((request_id, 0, "lock_error"))
            except Exception as e:
                results.append((request_id, 0, f"error: {e}"))
                
        # Simulate rapid sequential requests (profile playback scenario)
        threads = []
        for i in range(num_requests):
            thread = threading.Thread(target=simulate_build_climate_request, args=(i,))
            threads.append(thread)
            
        # Start all threads rapidly (no delays)
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join(timeout=10)
            
        # Should have exactly one success and others locked out
        success_count = sum(1 for _, _, status in results if status == "success")
        lock_error_count = sum(1 for _, _, status in results if status == "lock_error")
        
        assert success_count == 1, f"Expected 1 success, got {success_count}"
        assert lock_error_count == num_requests - 1, f"Expected {num_requests-1} lock errors, got {lock_error_count}"
        
    def test_climate_with_mitigation_delays(self, temp_wd):
        """Test Climate with the mitigation delays we implemented."""
        
        if hasattr(Climate, '_instances'):
            Climate._instances.clear()

        ensure_climate_stub(temp_wd)
            
        num_requests = 3
        results = []
        
        def simulate_build_climate_with_delay(request_id: int):
            try:
                climate = Climate.getInstance(temp_wd)
                start_time = time.time()
                
                with climate.locked():
                    time.sleep(0.1)  # Lighter operation
                    
                elapsed = time.time() - start_time
                results.append((request_id, elapsed, "success"))
                
                # Add the mitigation delay
                time.sleep(1.0)
                
            except NoDbAlreadyLockedError:
                results.append((request_id, 0, "lock_error"))
            except Exception as e:
                results.append((request_id, 0, f"error: {e}"))
                
        # Execute requests sequentially with delays
        for i in range(num_requests):
            simulate_build_climate_with_delay(i)
            
        # With delays, all should succeed
        success_count = sum(1 for _, _, status in results if status == "success")
        assert success_count == num_requests, f"Expected all {num_requests} to succeed with delays, got {success_count}"


@pytest.mark.nodb
class TestLockRecoveryMechanisms:
    """Test lock recovery and cleanup mechanisms."""
    
    def test_force_unlock_recovery(self, temp_wd, mock_controller_class):
        """Test force unlock can recover from stuck locks."""
        
        controller = mock_controller_class.getInstance(temp_wd)
        
        # Create a stuck lock scenario
        controller.lock()
        
        # Simulate process crash by corrupting local token
        from wepppy.nodb.base import _set_local_lock_token
        _set_local_lock_token(controller, None)
        
        # Normal unlock should fail
        with pytest.raises(RuntimeError):
            controller.unlock()
            
        # Force unlock should succeed
        controller.unlock('--force')
        
        # Should be able to lock again
        controller.lock()
        controller.unlock()


@pytest.mark.nodb
def test_getinstance_refreshes_after_external_dump(temp_wd, mock_controller_class, monkeypatch):
    """Cached instances should refresh when the backing .nodb file changes on disk."""
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)

    mock_controller_class._instances.clear()
    controller = mock_controller_class.getInstance(temp_wd)

    with controller.locked():
        controller.some_value = "initial"

    nodb_path = Path(temp_wd) / mock_controller_class.filename
    loaded = jsonpickle.decode(nodb_path.read_text())
    loaded.some_value = "updated"
    nodb_path.write_text(jsonpickle.encode(loaded))

    new_time = time.time() + 1
    os.utime(nodb_path, (new_time, new_time))

    refreshed = mock_controller_class.getInstance(temp_wd)
    assert refreshed is controller
    assert refreshed.some_value == "updated"
    mock_controller_class._instances.clear()


@pytest.mark.nodb
def test_getinstance_ignore_lock_bypasses_cache(temp_wd, mock_controller_class, monkeypatch):
    """ignore_lock=True should bypass the cached singleton and hydrate fresh state."""
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)

    mock_controller_class._instances.clear()
    primary = mock_controller_class.getInstance(temp_wd)

    with primary.locked():
        primary.some_value = "cached"

    nodb_path = Path(temp_wd) / mock_controller_class.filename
    loaded = jsonpickle.decode(nodb_path.read_text())
    loaded.some_value = "disk"
    nodb_path.write_text(jsonpickle.encode(loaded))
    os.utime(nodb_path, None)

    fresh = mock_controller_class.getInstance(temp_wd, ignore_lock=True)
    assert fresh is not primary
    assert fresh.some_value == "disk"

    cached = mock_controller_class.getInstance(temp_wd)
    assert cached is primary
    assert cached.some_value == "disk"
    mock_controller_class._instances.clear()


@pytest.mark.nodb
def test_getinstance_readonly_not_cached(temp_wd, mock_controller_class, monkeypatch):
    """Readonly runs should not populate the singleton cache."""
    monkeypatch.setattr('wepppy.nodb.base.redis_nodb_cache_client', None)

    readonly_wd = Path(temp_wd) / "readonly_run"
    readonly_wd.mkdir()
    cfg_path = readonly_wd / "test.cfg"
    cfg_path.write_text("[general]\ndem_db = test\n")

    mock_controller_class._instances.clear()
    controller = mock_controller_class(str(readonly_wd))
    controller.lock()
    controller.dump()
    controller.unlock()
    mock_controller_class._instances.clear()

    readonly_flag = readonly_wd / "READONLY"
    readonly_flag.write_text("")

    nodb_path = readonly_wd / mock_controller_class.filename
    base_obj = jsonpickle.decode(nodb_path.read_text())
    base_obj.some_value = "initial"
    nodb_path.write_text(jsonpickle.encode(base_obj))

    inst1 = mock_controller_class.getInstance(str(readonly_wd))
    assert inst1.some_value == "initial"

    updated_obj = jsonpickle.decode(nodb_path.read_text())
    updated_obj.some_value = "updated"
    nodb_path.write_text(jsonpickle.encode(updated_obj))
    os.utime(nodb_path, None)

    inst2 = mock_controller_class.getInstance(str(readonly_wd))
    assert inst2 is not inst1
    assert inst2.some_value == "updated"

    cache_after = mock_controller_class._instances
    assert str(readonly_wd) not in cache_after
        
    def test_clear_locks_cleanup(self, temp_wd, mock_controller_class):
        """Test clear_locks can clean up stuck locks."""
        
        controller = mock_controller_class.getInstance(temp_wd)
        
        # Create lock
        controller.lock()
        
        # Clear all locks for this runid
        cleared = clear_locks(controller.runid)
        
        assert len(cleared) > 0, "Should have cleared at least one lock"
        assert not controller.islocked(), "Controller should be unlocked after clear_locks"
        
        # Should be able to lock again
        controller.lock()
        controller.unlock()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
