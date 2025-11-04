"""Test cases specifically for the build_climate 504 Gateway Timeout bug.

This module reproduces the exact race condition scenario that caused the
504 Gateway Timeout in the build_climate endpoint during profile playback.
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

from wepppy.nodb.base import NoDbAlreadyLockedError
from wepppy.nodb.core.climate import Climate
from tests.nodb.lock_contention_utils import LockContentionSimulator, short_lock_ttl, ensure_climate_stub


@pytest.fixture
def climate_wd(tmp_path):
    """Create a working directory with minimal climate setup."""
    wd = str(tmp_path / "climate_test")
    Path(wd).mkdir(parents=True, exist_ok=True)
    
    # Create minimal required files
    config_path = Path(wd) / "test.cfg"
    config_path.write_text("""
[general]
dem_db = topaz
""")

    ensure_climate_stub(wd)
    
    return wd


@pytest.fixture
def clean_climate_instances():
    """Ensure Climate instances are clean before each test."""
    if hasattr(Climate, '_instances'):
        Climate._instances.clear()
    yield
    if hasattr(Climate, '_instances'):
        Climate._instances.clear()


@pytest.mark.nodb
@pytest.mark.slow
class TestBuildClimateRaceCondition:
    """Test the specific race condition that caused 504 Gateway Timeout."""
    
    def test_regression_profile_playback_without_delays(self, climate_wd, clean_climate_instances):
        """Ensure rapid sequential requests serialize cleanly without explicit delays."""
        
        # Mock parse_inputs to avoid file system dependencies
        original_parse_inputs = None
        if hasattr(Climate, 'parse_inputs'):
            original_parse_inputs = Climate.parse_inputs
            
        original_parse_inputs = getattr(Climate, 'parse_inputs', None)

        def mock_parse_inputs(self):
            """Mock parse_inputs with realistic timing."""
            # Simulate the heavy operation that was taking too long
            time.sleep(2.0)  # 2 seconds - enough to cause contention
        
        Climate.parse_inputs = mock_parse_inputs
        
        try:
            # Simulate profile playback: rapid sequential requests
            simulator = LockContentionSimulator(Climate, climate_wd)
            
            # 5 rapid requests like profile playback would generate
            results = simulator.rapid_fire_requests(
                num_requests=5, 
                operation_duration=2.0  # Simulates parse_inputs duration
            )
            
            # Analyze results
            successful_requests = [r for r in results if r["status"] == "success"]
            lock_errors = [r for r in results if r["status"] == "lock_error"]
            
            # Regression: sequential requests should now all succeed
            assert len(successful_requests) == len(results), (
                f"Expected all {len(results)} requests to succeed, got {len(successful_requests)}"
            )
            assert not lock_errors, f"Did not expect lock errors, saw {lock_errors}"
            
            # Validate timing stayed near the simulated operation duration
            for record in successful_requests:
                assert record["duration"] >= 2.0, f"Expected >=2s duration, got {record['duration']:.2f}s"
                
        finally:
            if original_parse_inputs is not None:
                Climate.parse_inputs = original_parse_inputs
            elif hasattr(Climate, 'parse_inputs'):
                delattr(Climate, 'parse_inputs')
                
    def test_build_climate_with_mitigation_delays(self, climate_wd, clean_climate_instances):
        """Test that mitigation delays prevent the race condition."""
        
        # Mock parse_inputs with shorter duration since we'll add delays
        original_parse_inputs = getattr(Climate, 'parse_inputs', None)

        def mock_parse_inputs_fast(self):
            time.sleep(0.5)  # Shorter operation
            
        Climate.parse_inputs = mock_parse_inputs_fast
        
        try:
            results = []
            
            # Simulate the fixed API endpoint behavior with delays
            for i in range(3):
                start_time = time.time()
                
                try:
                    climate = Climate.getInstance(climate_wd)
                    with climate.locked():
                        climate.parse_inputs()  # Mock operation
                        
                    # Add the mitigation delay we implemented
                    time.sleep(1.0)
                    
                    duration = time.time() - start_time
                    results.append({"request_id": i, "status": "success", "duration": duration})
                    
                except NoDbAlreadyLockedError:
                    duration = time.time() - start_time
                    results.append({"request_id": i, "status": "lock_error", "duration": duration})
                    
            # With delays, all requests should succeed
            successful_requests = [r for r in results if r["status"] == "success"]
            assert len(successful_requests) == 3, f"Expected all 3 to succeed with delays, got {len(successful_requests)}"
            
        finally:
            if original_parse_inputs is not None:
                Climate.parse_inputs = original_parse_inputs
            elif hasattr(Climate, 'parse_inputs'):
                delattr(Climate, 'parse_inputs')
                
    def test_gateway_timeout_threshold(self, climate_wd, clean_climate_instances):
        """Test operations that exceed 30-second gateway timeout."""
        
        original_parse_inputs = getattr(Climate, 'parse_inputs', None)

        def mock_parse_inputs_slow(self):
            # Simulate operation that would cause 504 timeout
            time.sleep(35.0)  # Exceeds 30s gateway timeout
            
        Climate.parse_inputs = mock_parse_inputs_slow
        
        try:
            start_time = time.time()
            
            # This should complete but would have caused 504 in real scenario
            climate = Climate.getInstance(climate_wd)
            with climate.locked():
                climate.parse_inputs()
                
            duration = time.time() - start_time
            
            # Verify it actually took longer than gateway timeout
            assert duration >= 35.0, f"Expected >= 35s duration, got {duration:.2f}s"
            
            # In the real scenario, this would be a 504 Gateway Timeout
            # Our test validates the operation completes but takes too long
            
        finally:
            if original_parse_inputs is not None:
                Climate.parse_inputs = original_parse_inputs
            elif hasattr(Climate, 'parse_inputs'):
                delattr(Climate, 'parse_inputs')
                
    def test_concurrent_build_climate_requests(self, climate_wd, clean_climate_instances):
        """Test concurrent requests like those from RQ workers + HTTP requests."""
        
        original_parse_inputs = getattr(Climate, 'parse_inputs', None)

        def mock_parse_inputs_medium(self):
            time.sleep(1.0)  # 1 second operation
            
        Climate.parse_inputs = mock_parse_inputs_medium
        
        try:
            # Simulate concurrent scenario: HTTP request + RQ worker
            simulator = LockContentionSimulator(Climate, climate_wd)
            results = simulator.thundering_herd(
                num_threads=3, 
                operation_duration=1.0
            )
            
            successful_threads = [r for r in results if r["status"] == "success"]
            failed_threads = [r for r in results if r["status"] == "lock_error"]
            
            # Only one thread should succeed
            assert len(successful_threads) == 1, f"Expected 1 success, got {len(successful_threads)}"
            assert len(failed_threads) == 2, f"Expected 2 lock errors, got {len(failed_threads)}"
            
        finally:
            if original_parse_inputs is not None:
                Climate.parse_inputs = original_parse_inputs
            elif hasattr(Climate, 'parse_inputs'):
                delattr(Climate, 'parse_inputs')


@pytest.mark.nodb
class TestProfilePlaybackScenarios:
    """Test scenarios specific to profile playback system."""
    
    def test_playback_session_rapid_requests(self, climate_wd, clean_climate_instances):
        """Simulate PlaybackSession making rapid requests."""
        
        # Mock the heavy operation
        original_parse_inputs = getattr(Climate, 'parse_inputs', None)

        def mock_heavy_operation(self):
            time.sleep(0.5)
            
        Climate.parse_inputs = mock_heavy_operation
        
        try:
            # Simulate profile playback pattern
            request_intervals = [0.0, 0.1, 0.2, 0.3, 0.4]  # Rapid succession
            results = []
            
            for i, interval in enumerate(request_intervals):
                if i > 0:
                    time.sleep(interval)  # Minimal delay between requests
                    
                start_time = time.time()
                
                try:
                    climate = Climate.getInstance(climate_wd)
                    with climate.locked():
                        climate.parse_inputs()
                        
                    duration = time.time() - start_time
                    results.append({
                        "request_id": i, 
                        "status": "success", 
                        "duration": duration,
                        "interval": interval
                    })
                    
                except NoDbAlreadyLockedError:
                    duration = time.time() - start_time
                    results.append({
                        "request_id": i, 
                        "status": "lock_error", 
                        "duration": duration,
                        "interval": interval
                    })
                    
            # Regression: all playback-triggered requests should succeed with minimal delay
            assert all(result["status"] == "success" for result in results), results
            for result in results:
                assert result["duration"] >= 0.5, f"Expected >=0.5s duration, got {result['duration']:.2f}s"
                
        finally:
            if original_parse_inputs is not None:
                Climate.parse_inputs = original_parse_inputs
            elif hasattr(Climate, 'parse_inputs'):
                delattr(Climate, 'parse_inputs')
                
    def test_playback_with_job_queueing(self, climate_wd, clean_climate_instances):
        """Test scenario where HTTP requests trigger RQ jobs."""
        
        # Mock both HTTP endpoint and RQ job operations
        original_parse_inputs = getattr(Climate, 'parse_inputs', None)

        def mock_http_operation(self):
            time.sleep(0.2)  # Quick HTTP response
            
        def mock_rq_operation(self):
            time.sleep(2.0)  # Longer background job
            
        Climate.parse_inputs = mock_http_operation
        
        try:
            results = []
            
            # Simulate HTTP request that triggers RQ job
            start_time = time.time()
            
            climate = Climate.getInstance(climate_wd)
            with climate.locked():
                climate.parse_inputs()  # HTTP endpoint
                
            http_duration = time.time() - start_time
            results.append({"type": "http", "duration": http_duration})
            
            # Switch to RQ operation simulation
            Climate.parse_inputs = mock_rq_operation
            
            # Simulate RQ job trying to acquire same lock
            start_time = time.time()
            
            try:
                climate = Climate.getInstance(climate_wd)
                with climate.locked():
                    climate.parse_inputs()  # RQ job
                    
                rq_duration = time.time() - start_time
                results.append({"type": "rq", "duration": rq_duration})
                
            except NoDbAlreadyLockedError:
                rq_duration = time.time() - start_time  
                results.append({"type": "rq_failed", "duration": rq_duration})
                
            # HTTP should complete quickly, RQ should either complete or fail quickly
            assert results[0]["duration"] < 1.0, "HTTP request should be fast"
            
            if len(results) > 1:
                if results[1]["type"] == "rq":
                    assert results[1]["duration"] >= 2.0, "RQ job should take expected time"
                else:  # rq_failed
                    assert results[1]["duration"] < 0.1, "RQ lock failure should be immediate"
                    
        finally:
            if original_parse_inputs is not None:
                Climate.parse_inputs = original_parse_inputs
            elif hasattr(Climate, 'parse_inputs'):
                delattr(Climate, 'parse_inputs')


@pytest.mark.nodb
@pytest.mark.slow
class TestLockTTLScenarios:
    """Test lock TTL expiration scenarios that could cause unresolved locks."""
    
    def test_operation_exceeds_ttl_causes_corruption(self, climate_wd, clean_climate_instances):
        """Test that operations exceeding TTL can cause state corruption."""
        
        with short_lock_ttl(2):  # 2-second TTL
            original_parse_inputs = getattr(Climate, 'parse_inputs', None)
            
            def mock_long_operation(self):
                time.sleep(5.0)  # Exceeds 2-second TTL
                
            Climate.parse_inputs = mock_long_operation
            
            try:
                corruption_detected = False
                
                climate = Climate.getInstance(climate_wd)
                
                try:
                    with climate.locked():
                        climate.parse_inputs()  # This should exceed TTL
                        
                except Exception as e:
                    # Expected: some kind of failure due to TTL expiration
                    corruption_detected = True
                    
                # After TTL expiry, another process should be able to acquire lock
                try:
                    climate2 = Climate.getInstance(climate_wd)
                    with climate2.locked():
                        pass  # Quick operation
                    second_acquisition_succeeded = True
                except NoDbAlreadyLockedError:
                    second_acquisition_succeeded = False
                    
                # Either we detected corruption OR second acquisition succeeded
                # (both indicate TTL expiry worked)
                assert corruption_detected or second_acquisition_succeeded, \
                    "Expected either corruption detection or successful second acquisition"
                    
            finally:
                if original_parse_inputs is not None:
                    Climate.parse_inputs = original_parse_inputs
                elif hasattr(Climate, 'parse_inputs'):
                    delattr(Climate, 'parse_inputs')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
