import concurrent.futures
import time
import os
import argparse
import logging
import tempfile
import statistics
from typing import List, Tuple

# We assume this function is available in your environment.
# If it's in a different location, adjust the import path.
from wepppy.all_your_base.geo.webclients import wmesque_retrieve

# --- Basic Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
)

# Hardcoded parameters for the specific WMSesque request
DATASET = 'nlcd/2019'
BBOX = [-116.42555236816408, 45.233799855252855, -116.32701873779298, 45.303146403608935]
CELLSIZE = 30.0

def run_request(endpoint: str, output_dir: str, request_id: int) -> Tuple[bool, float, str]:
    """
    Executes a single wmesque_retrieve call and measures its performance.

    Returns a tuple of (success, duration, message).
    """
    start_time = time.monotonic()
    output_path = os.path.join(output_dir, f"output_{request_id}.tif")
    error_message = ""
    
    try:
        logging.info(f"Request {request_id}: Starting download...")
        ret = wmesque_retrieve(
            dataset=DATASET,
            extent=BBOX,
            fname=output_path,
            cellsize=CELLSIZE,
            v=2,
            wmesque_endpoint=endpoint
        )

        if ret != 1:
            raise RuntimeError(f"wmesque_retrieve returned unexpected value: {ret}")
        
        # Verify that the file was actually created
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("Output file was not created or is empty.")
            
        logging.info(f"Request {request_id}: Success.")
        success = True

    except Exception as e:
        logging.error(f"Request {request_id}: FAILED - {e}")
        success = False
        error_message = str(e)
        
    finally:
        # Clean up the downloaded file immediately
        if os.path.exists(output_path):
            os.remove(output_path)
            
    end_time = time.monotonic()
    duration = end_time - start_time
    return success, duration, error_message

def main(url: str, total_requests: int, concurrency: int):
    """
    Main function to run the benchmark.
    """
    print("--- WMSesque Benchmark ---")
    print(f"Target URL: {url}")
    print(f"Total Requests: {total_requests}")
    print(f"Concurrency Level: {concurrency}")
    print("--------------------------\n")

    results: List[Tuple[bool, float, str]] = []
    
    # Create a temporary directory for output files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Start the main timer
        overall_start_time = time.monotonic()
        
        # Use ThreadPoolExecutor to run requests concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(run_request, url, temp_dir, i)
                for i in range(total_requests)
            ]

            pending = set(futures)
            while pending:
                done, pending = concurrent.futures.wait(
                    pending,
                    timeout=10,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                if not done:
                    logging.warning('Benchmark still waiting on requests after 10 seconds; continuing to wait.')
                    continue

                for future in done:
                    try:
                        results.append(future.result())
                    except Exception:
                        for remaining in pending:
                            remaining.cancel()
                        raise

        overall_end_time = time.monotonic()

    # --- Process and print results ---
    total_duration = overall_end_time - overall_start_time
    successes = [res for res in results if res[0]]
    failures = [res for res in results if not res[0]]
    
    successful_requests = len(successes)
    failed_requests = len(failures)
    
    print("\n--- Benchmark Results ---")
    print(f"Total time elapsed: {total_duration:.2f} seconds")
    
    if total_duration > 0:
        requests_per_sec = successful_requests / total_duration
        print(f"Requests per second (RPS): {requests_per_sec:.2f}")
    
    print(f"Successful requests: {successful_requests}")
    print(f"Failed requests: {failed_requests}")

    if successes:
        latencies = [res[1] for res in successes]
        print(f"\nLatencies for successful requests:")
        print(f"  Average: {statistics.mean(latencies):.2f} s")
        print(f"  Median:  {statistics.median(latencies):.2f} s")
        print(f"  Min:     {min(latencies):.2f} s")
        print(f"  Max:     {max(latencies):.2f} s")
        print(f"  Stdev:   {statistics.stdev(latencies):.2f} s")
    
    if failures:
        print("\nFailure reasons (first 5):")
        for i, f in enumerate(failures[:5]):
            print(f"  {i+1}: {f[2]}")
    
    print("-------------------------\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark script for WMSesque services.")
    parser.add_argument(
        "-u", "--url",
        required=True,
        help="The base URL of the WMSesque service to test (e.g., https://wmesque-flask.example.com)."
    )
    parser.add_argument(
        "-n", "--requests",
        type=int,
        default=50,
        help="Total number of requests to send."
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent requests to run in parallel."
    )
    args = parser.parse_args()
    
    main(args.url, args.requests, args.concurrency)

# python benchmark_wmesque.py -u "https://wmesque2.bearhive.duckdns.org" -n 500 -c 100

"""
flask

--- Benchmark Results ---
Total time elapsed: 7.52 seconds
Requests per second (RPS): 66.50
Successful requests: 500
Failed requests: 0

Latencies for successful requests:
  Average: 1.35 s
  Median:  1.48 s
  Min:     0.14 s
  Max:     1.53 s
  Stdev:   0.32 s
  

  fast-api
  --- Benchmark Results ---
Total time elapsed: 3.24 seconds
Requests per second (RPS): 154.35
Successful requests: 500
Failed requests: 0

Latencies for successful requests:
  Average: 0.62 s
  Median:  0.64 s
  Min:     0.28 s
  Max:     0.80 s
  Stdev:   0.08 s
  """
