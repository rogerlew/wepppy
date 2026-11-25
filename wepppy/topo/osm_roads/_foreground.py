"""Bounded foreground Overpass acquisition for the Roads download control."""

import asyncio
import json
import logging
import math
import random
import time
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from uuid import uuid4

import httpx

from .errors import OSMRoadsUpstreamError

_LOG = logging.getLogger(__name__)
_TRANSIENT_STATUS = {429, 502, 503, 504}
_TOTAL_SECONDS = 25


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


async def fetch_ways(
    url: str, query: str, timeout: int, process: Callable[[list], list]
) -> list:
    clock = asyncio.get_running_loop().time
    started = clock()
    deadline = started + _TOTAL_SECONDS
    reference = uuid4().hex
    headers = {
        "User-Agent": "WEPPcloud-Roads (+https://wepp.cloud/)",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }
    async with httpx.AsyncClient(
        headers=headers, timeout=timeout, follow_redirects=False
    ) as client:
        for attempt in (1, 2):
            status = None
            retry_after = None
            retryable = False
            try:
                async with asyncio.timeout_at(min(deadline, clock() + timeout)):
                    async with client.stream(
                        "POST", url, data={"data": query}
                    ) as response:
                        status = response.status_code
                        if status == 200:
                            ways = await _read_ways(response)
                            result = process(ways)
                            _LOG.info(
                                "OSM download %s attempt=%d status=200 elapsed_s=%.2f ways=%d",
                                reference,
                                attempt,
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
                message, code = (
                    "Timed out waiting for OpenStreetMap.",
                    "upstream_timeout",
                )
            except OSMRoadsUpstreamError as exc:
                message, code = exc.message, exc.code
            except httpx.TransportError as exc:
                retryable = isinstance(
                    exc,
                    (
                        httpx.ConnectError,
                        httpx.ReadError,
                        httpx.WriteError,
                        httpx.RemoteProtocolError,
                    ),
                )
                message, code = (
                    "The connection to OpenStreetMap failed.",
                    "upstream_connection_error",
                )

            elapsed = clock() - started
            delay = None
            if retryable and attempt == 1:
                proposed = max(random.uniform(4, 6), retry_after or 0)
                if clock() + proposed + 1 < deadline:
                    delay = proposed
                else:
                    retry_after = math.ceil(proposed)
            _LOG.warning(
                "OSM download %s attempt=%d reason=%s upstream_status=%s elapsed_s=%.2f retry_delay_s=%s",
                reference,
                attempt,
                code,
                status,
                elapsed,
                delay,
            )
            if delay is not None:
                await asyncio.sleep(delay)
                continue
            details = {
                "attempts": attempt,
                "retryable": retryable or code == "upstream_timeout",
                "elapsed_seconds": round(elapsed, 1),
                "reference": reference,
            }
            if status is not None:
                details["upstream_status"] = status
            if retry_after:
                details["retry_after_seconds"] = retry_after
            raise OSMRoadsUpstreamError(message, code=code, context=details)
