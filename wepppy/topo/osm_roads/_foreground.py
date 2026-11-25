"""Bounded foreground Overpass acquisition for the Roads download control."""

import asyncio
import json
import logging
import math
import re
from datetime import datetime, timezone
from urllib.parse import urljoin
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from uuid import uuid4

import httpx

from .errors import OSMRoadsUpstreamError

_LOG = logging.getLogger(__name__)
_TRANSIENT_STATUS = {429, 502, 504}


def _retry_after(value: str) -> int | None:
    if not value:
        return None
    if value.isascii() and value.isdecimal():
        # Saturate unrepresentable delays; never let a long header escape the budget.
        return min(int(value.lstrip("0")[:10] or "0"), 2**31 - 1)
    try:
        return max(0, math.ceil(parsedate_to_datetime(value).timestamp() - time.time()))
    except (ValueError, TypeError, OverflowError, OSError):
        return None


async def _read_ways(response: httpx.Response) -> list:
    if response.headers.get("content-encoding", "identity").lower() != "identity":
        raise OSMRoadsUpstreamError(
            "OpenStreetMap returned an unsupported encoding.",
            code="upstream_invalid_response",
        )
    data = bytearray()
    async for chunk in response.aiter_raw():
        if len(data) + len(chunk) > 8 * 1024 * 1024:
            raise OSMRoadsUpstreamError(
                "The OpenStreetMap response exceeded the download limit.",
                code="upstream_invalid_response",
            )
        data.extend(chunk)
    try:
        payload = json.loads(data)
    except (ValueError, RecursionError) as exc:
        raise OSMRoadsUpstreamError(
            "OpenStreetMap returned invalid JSON.", code="upstream_invalid_response"
        ) from exc
    remark = payload.get("remark") if isinstance(payload, dict) else None
    if isinstance(remark, str) and any(
        word in remark.lower() for word in ("timed out", "timeout")
    ):
        raise OSMRoadsUpstreamError(
            "The OpenStreetMap query timed out.", code="upstream_timeout"
        )
    if (
        remark
        or not isinstance(payload, dict)
        or not isinstance(payload.get("elements"), list)
    ):
        raise OSMRoadsUpstreamError(
            "OpenStreetMap returned an incomplete result.",
            code="upstream_invalid_response",
        )
    return payload["elements"]


def _parse_slot(text: str) -> tuple[str, int]:
    for line in text.splitlines():
        if re.fullmatch(r"[1-9]\d* slots? available now\.?", line.strip()):
            return "available", 0
        match = re.match(r"Slot available after: (\S+?),", line)
        if match:
            try:
                release = datetime.strptime(match[1], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                break
            return "scheduled", max(1, math.ceil(release.timestamp() - time.time()))
        if line.startswith("Currently running"):
            return "running", 5
    return "unknown", 60


async def fetch_slot(url: str) -> dict:
    state, seconds = "unknown", 60
    try:
        async with asyncio.timeout(5), httpx.AsyncClient(follow_redirects=False) as client:
            async with client.stream("GET", urljoin(url, "status"), headers={
                "Accept-Encoding": "identity", "User-Agent": "WEPPcloud-Roads (+https://wepp.cloud/)",
            }) as response:
                if response.status_code == 200 and response.headers.get("content-encoding", "identity").lower() == "identity":
                    data = bytearray()
                    async for chunk in response.aiter_raw():
                        if len(data) + len(chunk) > 16384:
                            break
                        data.extend(chunk)
                    else:
                        state, seconds = _parse_slot(data.decode("utf-8", errors="replace"))
    except (httpx.TransportError, TimeoutError) as exc:
        _LOG.warning("OSM slot check failed: %s", type(exc).__name__)
    if state == "unknown":
        _LOG.warning("OSM slot availability unknown; advising a 60-second wait")
    return {"state": state, "wait_seconds": seconds, "check_again": state == "running"}


async def fetch_ways(
    url: str, query: str, timeout: int, process: Callable[[list], list]
) -> list:
    clock = asyncio.get_running_loop().time
    started = clock()
    reference = uuid4().hex
    headers = {
        "User-Agent": "WEPPcloud-Roads (+https://wepp.cloud/)",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }
    async with httpx.AsyncClient(
        headers=headers, timeout=timeout, follow_redirects=False
    ) as client:
        status = None
        retry_after = None
        retryable = False
        try:
            async with asyncio.timeout(timeout):
                async with client.stream(
                    "POST", url, data={"data": query}
                ) as response:
                    status = response.status_code
                    if status == 200:
                        ways = await _read_ways(response)
                        result = process(ways)
                        _LOG.info(
                            "OSM download %s attempt=1 status=200 elapsed_s=%.2f ways=%d",
                            reference,
                            clock() - started,
                            len(ways),
                        )
                        return result
                    retry_after = _retry_after(
                        response.headers.get("Retry-After", "")
                    )
                    retryable = status in _TRANSIENT_STATUS
                    if status in (408, 504):
                        message, code = (
                            f"OpenStreetMap reported a timeout (HTTP {status}).",
                            "upstream_timeout",
                        )
                    else:
                        message, code = (
                            f"OpenStreetMap returned HTTP {status}.",
                            "upstream_http_error",
                        )
        except (TimeoutError, httpx.TimeoutException):
            retryable = True
            message, code = (
                "Timed out waiting for OpenStreetMap.",
                "upstream_timeout",
            )
        except OSMRoadsUpstreamError as exc:
            message, code = exc.message, exc.code
        except httpx.TransportError:
            message, code = (
                "The connection to OpenStreetMap failed.",
                "upstream_connection_error",
            )

        elapsed = clock() - started
        _LOG.warning("OSM download %s attempt=1 reason=%s upstream_status=%s elapsed_s=%.2f retryable=%s",
                     reference, code, status, elapsed, retryable)
        details = {"attempts": 1, "retryable": retryable, "elapsed_seconds": round(elapsed, 1),
                   "reference": reference}
        if status is not None:
            details["upstream_status"] = status
        if retry_after:
            details["retry_after_seconds"] = retry_after
        raise OSMRoadsUpstreamError(message, code=code, context=details)
