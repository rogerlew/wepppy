#!/usr/bin/env python3
"""Manual lock contention trigger script for debugging unresolved lock scenarios.

This script can be used to manually create various lock race conditions
for debugging and validation purposes. It's designed to be run outside
of the test suite for manual investigation.

Usage:
    python trigger_lock_scenarios.py [scenario] [working_directory]

Scenarios:
    thundering_herd    - Multiple threads competing for same lock
    rapid_sequential   - Rapid sequential lock acquisitions  
    ttl_expiration     - Operations that exceed lock TTL
    token_corruption   - Corrupt lock tokens mid-operation
    orphaned_locks     - Create locks without local tokens
    deadlock_sim       - Simulate circular wait conditions
"""

import argparse
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional

# Add wepppy to path for imports
sys.path.insert(0, '/workdir/wepppy')

from wepppy.nodb.base import NoDbBase, clear_locks
from tests.nodb.lock_contention_utils import (
    LockContentionSimulator, 
    short_lock_ttl,
    corrupt_lock_token,
    force_redis_lock_expiry,
    create_orphaned_lock,
    verify_lock_state_consistency
)


class DebugNoDbController(NoDbBase):
    """Debug controller for manual lock testing."""
    
    filename = "debug_lock_test.nodb"
    
    def __init__(self, wd: str, cfg_fn: str = "debug.cfg", run_group: Optional[str] = None):
        # Ensure working directory and config exist
        wd_path = Path(wd)
        wd_path.mkdir(parents=True, exist_ok=True)
        
        config_path = wd_path / cfg_fn
        if not config_path.exists():
            config_path.write_text("""
[general]
dem_db = debug
""")
        
        super().__init__(wd, cfg_fn, run_group=run_group)
        self.operation_count = 0
        
    def debug_operation(self, duration: float = 1.0, label: str = "operation"):
        """Perform a debug operation with configurable duration."""
        print(f"Starting {label} (duration: {duration}s)")
        start_time = time.time()
        
        with self.locked():
            time.sleep(duration)
            self.operation_count += 1
            
        elapsed = time.time() - start_time
        print(f"Completed {label} in {elapsed:.2f}s (operation #{self.operation_count})")
        

def setup_debug_environment(working_directory: str) -> str:
    """Set up a clean debug environment."""
    wd_path = Path(working_directory)
    wd_path.mkdir(parents=True, exist_ok=True)
    
    # Create minimal config file
    config_path = wd_path / "debug.cfg"
    config_path.write_text("""
[general]
dem_db = debug
""")
    
    # Create initial .nodb file
    try:
        initial_controller = DebugNoDbController(str(wd_path))
        initial_controller.lock()
        initial_controller.dump()
        initial_controller.unlock()
        print("Created initial .nodb file")
    except Exception as e:
        print(f"Warning: Could not create initial .nodb file: {e}")
    
    # Clear any existing locks
    try:
        cleared = clear_locks(str(wd_path))
        if cleared:
            print(f"Cleared {len(cleared)} existing locks")
    except Exception as e:
        print(f"Warning: Could not clear existing locks: {e}")
        
    # Clear instances for fresh start
    if hasattr(DebugNoDbController, '_instances'):
        DebugNoDbController._instances.clear()
        
    return str(wd_path)


def scenario_thundering_herd(working_directory: str, num_threads: int = 5):
    """Create thundering herd scenario."""
    print(f"\n=== THUNDERING HERD SCENARIO ({num_threads} threads) ===")
    
    wd = setup_debug_environment(working_directory)
    simulator = LockContentionSimulator(DebugNoDbController, wd)
    
    print("Starting concurrent lock attempts...")
    results = simulator.thundering_herd(num_threads, operation_duration=2.0)
    
    print("\nResults:")
    for result in results:
        status = result["status"]
        duration = result["duration"]
        thread_id = result["thread_id"]
        
        if status == "success":
            print(f"  Thread {thread_id}: SUCCESS ({duration:.2f}s)")
        elif status == "lock_error":
            print(f"  Thread {thread_id}: LOCK ERROR ({duration:.2f}s)")
        else:
            error = result.get("error", "unknown")
            print(f"  Thread {thread_id}: ERROR - {error}")
            
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"\nSummary: {success_count}/{num_threads} threads succeeded")
    

def scenario_rapid_sequential(working_directory: str, num_requests: int = 10):
    """Create rapid sequential lock scenario."""
    print(f"\n=== RAPID SEQUENTIAL SCENARIO ({num_requests} requests) ===")
    
    wd = setup_debug_environment(working_directory)
    simulator = LockContentionSimulator(DebugNoDbController, wd)
    
    print("Starting rapid sequential requests...")
    results = simulator.rapid_fire_requests(num_requests, operation_duration=0.5)
    
    print("\nResults:")
    for result in results:
        req_id = result["request_id"]
        status = result["status"]
        duration = result["duration"]
        
        if status == "success":
            print(f"  Request {req_id}: SUCCESS ({duration:.2f}s)")
        elif status == "lock_error":
            print(f"  Request {req_id}: LOCK ERROR ({duration:.2f}s)")
        else:
            error = result.get("error", "unknown")
            print(f"  Request {req_id}: ERROR - {error}")
            
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"\nSummary: {success_count}/{num_requests} requests succeeded")


def scenario_ttl_expiration(working_directory: str):
    """Create TTL expiration scenario."""
    print("\n=== TTL EXPIRATION SCENARIO ===")
    
    wd = setup_debug_environment(working_directory)
    
    with short_lock_ttl(3):  # 3 second TTL
        print("Creating controller with 3-second TTL...")
        controller = DebugNoDbController.getInstance(wd)
        
        print("Starting operation that exceeds TTL...")
        try:
            controller.debug_operation(duration=5.0, label="long operation")
            print("ERROR: Operation completed without TTL expiry!")
        except Exception as e:
            print(f"Expected failure due to TTL expiry: {e}")
            
        print("\nTrying to acquire lock after TTL expiry...")
        try:
            controller2 = DebugNoDbController.getInstance(wd)
            controller2.debug_operation(duration=0.5, label="post-expiry operation")
            print("SUCCESS: Acquired lock after TTL expiry")
        except Exception as e:
            print(f"Failed to acquire lock after expiry: {e}")


def scenario_token_corruption(working_directory: str):
    """Create token corruption scenario."""
    print("\n=== TOKEN CORRUPTION SCENARIO ===")
    
    wd = setup_debug_environment(working_directory)
    controller = DebugNoDbController.getInstance(wd)
    
    print("Acquiring lock normally...")
    controller.lock()
    
    print("Lock state before corruption:")
    state = verify_lock_state_consistency(controller)
    print(f"  Redis lock exists: {state['redis_lock_exists']}")
    print(f"  Local token: {state['local_token']}")
    print(f"  Controller locked: {state['controller_locked']}")
    
    print("\nCorrupting lock token...")
    with corrupt_lock_token(controller):
        print("Lock state after corruption:")
        state = verify_lock_state_consistency(controller)
        print(f"  Redis lock exists: {state['redis_lock_exists']}")
        print(f"  Local token: {state['local_token']}")
        print(f"  Controller locked: {state['controller_locked']}")
        
        print("\nTrying to unlock with corrupted token...")
        try:
            controller.unlock()
            print("ERROR: Unlock succeeded with corrupted token!")
        except Exception as e:
            print(f"Expected failure: {e}")
            
        print("\nTrying force unlock...")
        try:
            controller.unlock('--force')
            print("SUCCESS: Force unlock worked")
        except Exception as e:
            print(f"Force unlock failed: {e}")


def scenario_orphaned_locks(working_directory: str):
    """Create orphaned lock scenario."""
    print("\n=== ORPHANED LOCKS SCENARIO ===")
    
    wd = setup_debug_environment(working_directory)
    controller = DebugNoDbController.getInstance(wd)
    
    print("Creating orphaned lock (Redis lock without local token)...")
    success = create_orphaned_lock(controller)
    
    if not success:
        print("Failed to create orphaned lock (Redis unavailable?)")
        return
        
    print("Lock state after creating orphan:")
    state = verify_lock_state_consistency(controller)
    print(f"  Redis lock exists: {state['redis_lock_exists']}")
    print(f"  Local token: {state['local_token']}")
    print(f"  Controller locked: {state['controller_locked']}")
    print(f"  States consistent: {state['states_consistent']}")
    
    print("\nTrying to acquire lock when orphaned lock exists...")
    try:
        controller.lock()
        print("ERROR: Lock acquisition succeeded despite orphaned lock!")
    except Exception as e:
        print(f"Expected failure: {e}")
        
    print("\nClearing orphaned locks...")
    cleared = clear_locks(controller.runid)
    print(f"Cleared {len(cleared)} locks")
    
    print("\nTrying to acquire lock after cleanup...")
    try:
        controller.lock()
        controller.unlock()
        print("SUCCESS: Lock acquired after cleanup")
    except Exception as e:
        print(f"Failed to acquire lock after cleanup: {e}")


def scenario_deadlock_simulation(working_directory: str):
    """Simulate potential deadlock scenario."""
    print("\n=== DEADLOCK SIMULATION SCENARIO ===")
    
    # Create two working directories
    wd1 = setup_debug_environment(working_directory + "_1")
    wd2 = setup_debug_environment(working_directory + "_2")
    
    print("Note: NoDb doesn't currently support nested locks,")
    print("so this tests potential circular wait scenarios.")
    
    results = {"thread1": None, "thread2": None}
    
    def worker1():
        try:
            controller1 = DebugNoDbController.getInstance(wd1)
            controller2 = DebugNoDbController.getInstance(wd2)
            
            print("Thread 1: Acquiring lock 1...")
            with controller1.locked():
                time.sleep(1)
                print("Thread 1: Trying to acquire lock 2...")
                try:
                    with controller2.locked():
                        print("Thread 1: Acquired both locks!")
                        time.sleep(1)
                except Exception as e:
                    print(f"Thread 1: Failed to acquire lock 2: {e}")
                    
            results["thread1"] = "completed"
        except Exception as e:
            results["thread1"] = f"error: {e}"
            
    def worker2():
        try:
            controller2 = DebugNoDbController.getInstance(wd2)
            controller1 = DebugNoDbController.getInstance(wd1)
            
            time.sleep(0.5)  # Slight delay to create race condition
            print("Thread 2: Acquiring lock 2...")
            with controller2.locked():
                time.sleep(1)
                print("Thread 2: Trying to acquire lock 1...")
                try:
                    with controller1.locked():
                        print("Thread 2: Acquired both locks!")
                        time.sleep(1)
                except Exception as e:
                    print(f"Thread 2: Failed to acquire lock 1: {e}")
                    
            results["thread2"] = "completed"
        except Exception as e:
            results["thread2"] = f"error: {e}"
            
    print("Starting deadlock simulation...")
    thread1 = threading.Thread(target=worker1)
    thread2 = threading.Thread(target=worker2)
    
    start_time = time.time()
    thread1.start()
    thread2.start()
    
    thread1.join(timeout=10)
    thread2.join(timeout=10)
    
    elapsed = time.time() - start_time
    
    print(f"\nResults after {elapsed:.2f}s:")
    print(f"  Thread 1: {results['thread1']}")
    print(f"  Thread 2: {results['thread2']}")
    
    if thread1.is_alive() or thread2.is_alive():
        print("WARNING: Threads still alive - potential deadlock!")
    else:
        print("All threads completed - no deadlock detected")


def main():
    parser = argparse.ArgumentParser(description="Trigger NoDb lock race conditions for debugging")
    parser.add_argument("scenario", choices=[
        "thundering_herd", "rapid_sequential", "ttl_expiration", 
        "token_corruption", "orphaned_locks", "deadlock_sim"
    ], help="Lock scenario to trigger")
    parser.add_argument("working_directory", nargs="?", default="/tmp/debug_locks", 
                       help="Working directory for test (default: /tmp/debug_locks)")
    parser.add_argument("--threads", type=int, default=5, 
                       help="Number of threads for concurrent scenarios")
    parser.add_argument("--requests", type=int, default=10,
                       help="Number of requests for sequential scenarios")
    
    args = parser.parse_args()
    
    print(f"Triggering scenario: {args.scenario}")
    print(f"Working directory: {args.working_directory}")
    
    try:
        if args.scenario == "thundering_herd":
            scenario_thundering_herd(args.working_directory, args.threads)
        elif args.scenario == "rapid_sequential":
            scenario_rapid_sequential(args.working_directory, args.requests)
        elif args.scenario == "ttl_expiration":
            scenario_ttl_expiration(args.working_directory)
        elif args.scenario == "token_corruption":
            scenario_token_corruption(args.working_directory)
        elif args.scenario == "orphaned_locks":
            scenario_orphaned_locks(args.working_directory)
        elif args.scenario == "deadlock_sim":
            scenario_deadlock_simulation(args.working_directory)
            
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nScenario complete.")


if __name__ == "__main__":
    main()