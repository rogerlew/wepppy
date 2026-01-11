#!/usr/bin/env python3
"""
Submit payload.zip to wepp.cloud culvert batch endpoint and poll until completion.

This script uploads a payload ZIP file to the WEPPcloud culvert batch API,
then polls the job status endpoint until the job completes or times out.

Usage:
    # Default host (wepp.cloud)
    python submit_payload.py --payload /path/to/payload.zip

    # Testing host override via CLI
    python submit_payload.py --payload payload.zip --host wc.bearhive.duckdns.org

    # Testing host override via environment variable
    WEPPCLOUD_HOST=wc.bearhive.duckdns.org python submit_payload.py --payload payload.zip

    # With explicit hash/size (skips local computation)
    python submit_payload.py --payload payload.zip \\
        --zip-sha256 abc123... --total-bytes 12345678

    # Custom polling/timeout
    python submit_payload.py --payload payload.zip \\
        --poll-seconds 10 --timeout-seconds 7200

Environment variables:
    WEPPCLOUD_HOST: Override the default wepp.cloud host (no http/https prefix).

Test payload (pre-built):
    tests/culverts/test_payloads/santee_10m_no_hydroenforcement/payload.zip

Exit codes:
    0: Job completed successfully
    1: Job failed or error occurred
    2: Timeout exceeded
    3: Invalid arguments or payload
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import requests

# Constants
DEFAULT_HOST = "wepp.cloud"
DEFAULT_POLL_SECONDS = 5
DEFAULT_TIMEOUT_SECONDS = 3600 * 20
UPLOAD_ENDPOINT = "/rq-engine/api/culverts-wepp-batch/"

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class SubmissionError(Exception):
    """Raised when submission or polling fails."""

    pass


def _timestamp() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compute_sha256(path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _resolve_host(cli_host: Optional[str]) -> str:
    """Resolve the target host from CLI arg or environment."""
    if cli_host:
        return cli_host
    return os.getenv("WEPPCLOUD_HOST", DEFAULT_HOST)


def _build_base_url(host: str) -> str:
    """Build the base URL with HTTPS protocol."""
    # Strip any existing protocol prefix
    host = host.replace("https://", "").replace("http://", "").rstrip("/")
    return f"https://{host}"


def _resolve_status_url(status_url: str, base_url: str) -> str:
    """Resolve status URL, prefixing base_url if relative."""
    if status_url.startswith("http://") or status_url.startswith("https://"):
        return status_url
    # Relative URL - prefix with base URL
    return urljoin(base_url, status_url)


def upload_payload(
    payload_path: Path,
    base_url: str,
    zip_sha256: Optional[str] = None,
    total_bytes: Optional[int] = None,
) -> dict[str, Any]:
    """
    Upload payload.zip to the culvert batch endpoint.

    Returns the JSON response containing job_id, culvert_batch_uuid, status_url.
    """
    endpoint = urljoin(base_url, UPLOAD_ENDPOINT)

    logger.info(f"Upload target: {endpoint}")
    logger.info(f"Payload file: {payload_path}")

    # Compute hash and size if not provided
    if total_bytes is None:
        total_bytes = payload_path.stat().st_size
    logger.info(f"Payload size: {total_bytes:,} bytes")

    if zip_sha256 is None:
        logger.info("Computing SHA256 hash...")
        zip_sha256 = _compute_sha256(payload_path)
    logger.info(f"Payload SHA256: {zip_sha256}")

    # Prepare multipart upload
    form_data = {
        "zip_sha256": zip_sha256,
        "total_bytes": str(total_bytes),
    }

    logger.info(f"Uploading payload to {endpoint}...")
    start_time = time.monotonic()

    with payload_path.open("rb") as f:
        files = {"payload.zip": (payload_path.name, f, "application/zip")}
        response = requests.post(
            endpoint,
            files=files,
            data=form_data,
            timeout=(30, 3600),  # 30s connect, 60 min upload timeout
        )

    elapsed = time.monotonic() - start_time
    logger.info(f"Upload completed in {elapsed:.1f}s, status: {response.status_code}")

    if response.status_code != 200:
        logger.error(f"Upload failed: {response.status_code}")
        try:
            error_body = response.json()
            logger.error(f"Response: {error_body}")
        except Exception:
            logger.error(f"Response text: {response.text[:500]}")
        raise SubmissionError(f"Upload failed with status {response.status_code}")

    result = response.json()
    logger.info(f"Response: job_id={result.get('job_id')}")
    logger.info(f"Response: culvert_batch_uuid={result.get('culvert_batch_uuid')}")
    logger.info(f"Response: status_url={result.get('status_url')}")

    return result


def poll_until_complete(
    status_url: str,
    poll_seconds: int = DEFAULT_POLL_SECONDS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """
    Poll the status URL until the job completes, fails, or times out.

    Returns the final status response.
    """
    logger.info(f"Polling status: {status_url}")
    logger.info(f"Poll interval: {poll_seconds}s, timeout: {timeout_seconds}s")

    start_time = time.monotonic()
    last_status = None
    poll_count = 0

    while True:
        poll_count += 1
        elapsed = time.monotonic() - start_time

        if elapsed > timeout_seconds:
            logger.error(f"Timeout exceeded after {elapsed:.1f}s ({poll_count} polls)")
            raise SubmissionError("Polling timeout exceeded")

        try:
            response = requests.get(status_url, timeout=30)
            response.raise_for_status()
            status_data = response.json()
        except requests.RequestException as e:
            logger.warning(f"Poll {poll_count} failed: {e}")
            time.sleep(poll_seconds)
            continue

        status = status_data.get("status", "unknown")

        # Log status changes
        if status != last_status:
            logger.info(
                f"Poll {poll_count} ({elapsed:.0f}s): status={status}"
            )
            last_status = status
        else:
            # Periodic heartbeat even if status unchanged
            if poll_count % 12 == 0:  # Every ~60s at default 5s interval
                logger.info(f"Poll {poll_count} ({elapsed:.0f}s): status={status}")

        # Check terminal states
        if status == "finished":
            logger.info(f"Job completed successfully after {elapsed:.1f}s")
            return status_data
        elif status in ("failed", "stopped", "canceled"):
            logger.error(f"Job terminated with status: {status}")
            return status_data
        elif status == "not_found":
            logger.error("Job not found - may have expired or invalid job_id")
            raise SubmissionError("Job not found")

        time.sleep(poll_seconds)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Submit payload.zip to wepp.cloud and poll until completion.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--payload",
        required=True,
        type=Path,
        help="Path to payload.zip file",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help=f"WEPPcloud host (default: WEPPCLOUD_HOST env or {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--zip-sha256",
        type=str,
        default=None,
        help="SHA256 hash of payload.zip (computed if not provided)",
    )
    parser.add_argument(
        "--total-bytes",
        type=int,
        default=None,
        help="Size of payload.zip in bytes (computed if not provided)",
    )
    parser.add_argument(
        "--poll-seconds",
        type=int,
        default=DEFAULT_POLL_SECONDS,
        help=f"Polling interval in seconds (default: {DEFAULT_POLL_SECONDS})",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Maximum wait time in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )

    args = parser.parse_args()

    # Validate payload exists
    if not args.payload.exists():
        logger.error(f"Payload file not found: {args.payload}")
        return 3
    if not args.payload.is_file():
        logger.error(f"Payload is not a file: {args.payload}")
        return 3

    # Resolve host and build base URL
    host = _resolve_host(args.host)
    base_url = _build_base_url(host)

    logger.info("=" * 60)
    logger.info("Culvert Batch Payload Submission")
    logger.info("=" * 60)
    logger.info(f"Host: {host}")
    logger.info(f"Base URL: {base_url}")

    try:
        # Upload payload
        upload_result = upload_payload(
            payload_path=args.payload,
            base_url=base_url,
            zip_sha256=args.zip_sha256,
            total_bytes=args.total_bytes,
        )

        # Get status URL
        status_url = upload_result.get("status_url")
        if not status_url:
            logger.error("No status_url in response")
            return 1

        # Resolve relative URL
        full_status_url = _resolve_status_url(status_url, base_url)

        # Print Job Dashboard link for real-time monitoring
        job_id = upload_result.get("job_id")
        if job_id:
            dashboard_url = f"{base_url}/weppcloud/rq/job-dashboard/{job_id}"
            logger.info("-" * 60)
            logger.info(f"Job Dashboard: {dashboard_url}")

        # Poll until completion
        logger.info("-" * 60)
        final_status = poll_until_complete(
            status_url=full_status_url,
            poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds,
        )

        # Summary
        logger.info("=" * 60)
        logger.info("Final Summary")
        logger.info("=" * 60)
        logger.info(f"Job ID: {upload_result.get('job_id')}")
        logger.info(f"Batch UUID: {upload_result.get('culvert_batch_uuid')}")
        logger.info(f"Final Status: {final_status.get('status')}")

        if final_status.get("status") == "finished":
            batch_uuid = upload_result.get("culvert_batch_uuid")
            browse_url = f"{base_url}/culverts/{batch_uuid}/browse/"
            logger.info(f"Browse results: {browse_url}")
            return 0
        else:
            return 1

    except SubmissionError as e:
        logger.error(f"Submission failed: {e}")
        return 1
    except requests.RequestException as e:
        logger.error(f"Network error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
