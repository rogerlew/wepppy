"""Helper utilities for creating NoDb lock race conditions and unresolved lock scenarios.

This module provides utility functions and context managers to deliberately
trigger lock race conditions for testing and validation purposes.
"""

import contextlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import List, Callable, Any, Optional, Dict
from unittest.mock import patch
from pathlib import Path

from wepppy.nodb.base import NoDbBase, NoDbAlreadyLockedError, redis_lock_client


class LockContentionSimulator:
    """Utility class to simulate various lock contention scenarios."""
    
    def __init__(self, controller_class: type, working_directory: str):
        self.controller_class = controller_class
        self.working_directory = working_directory
        self.results: List[Dict[str, Any]] = []
        
    def rapid_fire_requests(self, num_requests: int, operation_duration: float = 0.1) -> List[Dict[str, Any]]:
        """Simulate rapid sequential requests like profile playback."""
        results = []
        
        for i in range(num_requests):
            result = {"request_id": i, "start_time": time.time()}
            
            try:
                controller = self.controller_class.getInstance(self.working_directory)
                
                with controller.locked():
                    time.sleep(operation_duration)  # Simulate work
                    
                result.update({
                    "status": "success",
                    "duration": time.time() - result["start_time"]
                })
                
            except NoDbAlreadyLockedError as e:
                result.update({
                    "status": "lock_error",
                    "error": str(e),
                    "duration": time.time() - result["start_time"]
                })
            except Exception as e:
                result.update({
                    "status": "error", 
                    "error": str(e),
                    "duration": time.time() - result["start_time"]
                })
                
            results.append(result)
            
        return results
        
    def thundering_herd(self, num_threads: int, operation_duration: float = 0.5) -> List[Dict[str, Any]]:
        """Simulate thundering herd scenario with concurrent threads."""
        results = []
        results_lock = threading.Lock()
        
        def worker(thread_id: int):
            result = {"thread_id": thread_id, "start_time": time.time()}
            
            try:
                controller = self.controller_class.getInstance(self.working_directory)
                
                with controller.locked():
                    time.sleep(operation_duration)
                    
                result.update({
                    "status": "success", 
                    "duration": time.time() - result["start_time"]
                })
                
            except NoDbAlreadyLockedError as e:
                result.update({
                    "status": "lock_error",
                    "error": str(e),
                    "duration": time.time() - result["start_time"]
                })
            except Exception as e:
                result.update({
                    "status": "error",
                    "error": str(e),
                    "duration": time.time() - result["start_time"]
                })
                
            with results_lock:
                results.append(result)
                
        # Start all threads simultaneously
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join(timeout=10)
            
        return results
        
    def singleton_race(self, num_threads: int) -> List[Dict[str, Any]]:
        """Test getInstance() singleton behavior under contention."""
        instances = []
        instances_lock = threading.Lock()
        
        def get_instance(thread_id: int):
            try:
                instance = self.controller_class.getInstance(self.working_directory)
                with instances_lock:
                    instances.append({"thread_id": thread_id, "instance_id": id(instance)})
            except Exception as e:
                with instances_lock:
                    instances.append({"thread_id": thread_id, "error": str(e)})
                    
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=get_instance, args=(i,))
            threads.append(thread)
            
        for thread in threads:
            thread.start()
            
        for thread in threads:
            thread.join(timeout=5)
            
        return instances


def ensure_climate_stub(wd: str, cfg_name: str = "test.cfg") -> None:
    """
    Create a lightweight ``climate.nodb`` payload for tests that exercise
    locking behaviour without needing the full Climate configuration stack.
    """
    from wepppy.nodb.core.climate import Climate

    path = Path(wd)
    path.mkdir(parents=True, exist_ok=True)

    cfg_path = path / cfg_name
    if not cfg_path.exists():
        cfg_path.write_text(
            "[general]\n"
            "dem_db = test\n"
            "[climate]\n"
            "cligen_db = dummy\n"
            "observed_clis_wc = dummy\n"
            "future_clis_wc = dummy\n"
            "use_gridmet_wind_when_applicable = true\n"
        )

    original_init = Climate.__init__

    def lightweight_init(self, wd: str, cfg_fn: str, run_group: Optional[str] = None, group_name: Optional[str] = None) -> None:
        NoDbBase.__init__(self, wd, cfg_fn, run_group=run_group, group_name=group_name)

    try:
        Climate.__init__ = lightweight_init
        climate = Climate(wd, cfg_name)
        climate.lock()
        climate.dump()
        climate.unlock()
    finally:
        Climate.__init__ = original_init

    if hasattr(Climate, '_instances'):
        Climate._instances.clear()


@contextlib.contextmanager
def short_lock_ttl(ttl_seconds: int = 1):
    """Context manager to temporarily set a very short lock TTL for testing."""
    with patch('wepppy.nodb.base.LOCK_DEFAULT_TTL', ttl_seconds):
        yield


@contextlib.contextmanager 
def corrupt_lock_token(controller: NoDbBase):
    """Context manager to corrupt a controller's lock token (simulate process crash)."""
    from wepppy.nodb.base import _set_local_lock_token, _get_local_lock_token
    
    original_token = _get_local_lock_token(controller)
    try:
        # Corrupt the token
        _set_local_lock_token(controller, None)
        yield
    finally:
        # Restore original token
        _set_local_lock_token(controller, original_token)


def force_redis_lock_expiry(controller: NoDbBase) -> bool:
    """Force expire a Redis lock key for testing TTL scenarios."""
    if redis_lock_client is None:
        return False
        
    lock_key = controller._distributed_lock_key
    return bool(redis_lock_client.delete(lock_key))


def create_orphaned_lock(controller: NoDbBase) -> bool:
    """Create an orphaned lock scenario (Redis lock exists but no local token)."""
    from wepppy.nodb.base import _set_local_lock_token, _serialize_lock_payload
    import uuid
    
    if redis_lock_client is None:
        return False
        
    # Create Redis lock without local token
    lock_key = controller._distributed_lock_key
    token = uuid.uuid4().hex
    payload = _serialize_lock_payload(token, 300)  # 5 minute TTL
    
    success = redis_lock_client.set(lock_key, payload, nx=True, ex=300)
    if success:
        # Don't set local token - creates orphaned state
        redis_lock_client.hset(controller.runid, controller._file_lock_key, 'true')
        
    return bool(success)


class AsyncLockTester:
    """Utility for testing locks with async-style operations."""
    
    def __init__(self, controller_class: type, working_directory: str):
        self.controller_class = controller_class
        self.working_directory = working_directory
        
    def submit_parallel_operations(self, operations: List[Callable], max_workers: int = 4) -> List[Future]:
        """Submit multiple operations in parallel using ThreadPoolExecutor."""
        futures = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for operation in operations:
                future = executor.submit(operation)
                futures.append(future)
                
        return futures
        
    def wait_for_results(self, futures: List[Future], timeout: float = 10.0) -> List[Dict[str, Any]]:
        """Wait for parallel operations to complete and collect results."""
        results = []
        
        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=timeout)
                results.append({"operation_id": i, "status": "success", "result": result})
            except Exception as e:
                results.append({"operation_id": i, "status": "error", "error": str(e)})
                
        return results


def verify_lock_state_consistency(controller: NoDbBase) -> Dict[str, Any]:
    """Verify that Redis and local lock states are consistent."""
    if redis_lock_client is None:
        return {"error": "Redis client unavailable"}
        
    from wepppy.nodb.base import _get_local_lock_token
    
    # Check Redis distributed lock
    redis_lock_exists = redis_lock_client.exists(controller._distributed_lock_key)
    redis_payload = redis_lock_client.get(controller._distributed_lock_key)
    
    # Check Redis hash field
    hash_value = redis_lock_client.hget(controller.runid, controller._file_lock_key)
    
    # Check local token
    local_token = _get_local_lock_token(controller)
    
    # Check controller state
    controller_locked = controller.islocked()
    
    return {
        "redis_lock_exists": bool(redis_lock_exists),
        "redis_payload": redis_payload.decode() if redis_payload else None,
        "hash_value": hash_value.decode() if hash_value else None,
        "local_token": local_token,
        "controller_locked": controller_locked,
        "states_consistent": (
            bool(redis_lock_exists) == controller_locked and
            (hash_value.decode() if hash_value else "false") == ("true" if controller_locked else "false")
        )
    }


class LockDeadlockSimulator:
    """Simulate potential deadlock scenarios (though NoDb doesn't currently support nested locks)."""
    
    def __init__(self, controller_class: type):
        self.controller_class = controller_class
        
    def simulate_circular_wait(self, wd1: str, wd2: str) -> Dict[str, Any]:
        """Simulate circular wait scenario with two controllers."""
        results = {"thread1": None, "thread2": None, "deadlock_detected": False}
        
        def worker1():
            try:
                controller1 = self.controller_class.getInstance(wd1)
                controller2 = self.controller_class.getInstance(wd2)
                
                with controller1.locked():
                    time.sleep(0.1)
                    # Try to acquire second lock (potential deadlock)
                    with controller2.locked():
                        time.sleep(0.1)
                        
                results["thread1"] = "success"
            except Exception as e:
                results["thread1"] = f"error: {e}"
                
        def worker2():
            try:
                controller2 = self.controller_class.getInstance(wd2)  
                controller1 = self.controller_class.getInstance(wd1)
                
                with controller2.locked():
                    time.sleep(0.1)
                    # Try to acquire first lock (potential deadlock)
                    with controller1.locked():
                        time.sleep(0.1)
                        
                results["thread2"] = "success"
            except Exception as e:
                results["thread2"] = f"error: {e}"
                
        thread1 = threading.Thread(target=worker1)
        thread2 = threading.Thread(target=worker2)
        
        start_time = time.time()
        thread1.start()
        thread2.start()
        
        thread1.join(timeout=5)
        thread2.join(timeout=5)
        
        # Check if threads are still alive (potential deadlock)
        if thread1.is_alive() or thread2.is_alive():
            results["deadlock_detected"] = True
            
        results["total_time"] = time.time() - start_time
        return results
