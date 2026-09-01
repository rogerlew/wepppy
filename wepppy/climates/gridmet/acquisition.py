"""Shared failure contract for GridMET HTTP acquisition."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import date, timedelta
from typing import Any

import requests

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (5.0, 10.0)
SINGLE_LOCATION_TIMEOUT = (10.0, 60.0)
GRID_TIMEOUT = (10.0, 120.0)
MAX_SINGLE_LOCATION_BYTES = 32 * 1024 * 1024
MAX_GRID_BYTES = 512 * 1024 * 1024
TRANSIENT_HTTP_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
_LOG = logging.getLogger(__name__)


class GridMetAcquisitionError(RuntimeError):
    """GridMET could not provide a validated response within policy bounds."""


class GridMetPayloadError(ValueError):
    """An upstream response did not contain the requested GridMET payload."""


_TRANSIENT_REQUEST_ERRORS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.ContentDecodingError,
)


def _retry_or_raise(
    *,
    attempt: int,
    operation: str,
    reason: str,
    sleep: Callable[[float], None],
    cause: BaseException | None = None,
) -> None:
    if attempt + 1 >= MAX_ATTEMPTS:
        error = GridMetAcquisitionError(
            f"GridMET {operation} failed after {MAX_ATTEMPTS} attempts: {reason}"
        )
        if cause is None:
            raise error
        raise error from cause
    delay = BACKOFF_SECONDS[attempt]
    _LOG.warning(
        "GridMET %s retry %d/%d after %s; waiting %.1fs",
        operation,
        attempt + 2,
        MAX_ATTEMPTS,
        reason,
        delay,
    )
    sleep(delay)


def validate_single_location_payload(
    payload: Any,
    required_series: Sequence[str],
    *,
    start_date: date,
    end_date: date,
) -> Mapping[str, Any]:
    if not isinstance(payload, dict):
        raise GridMetPayloadError("JSON root is not an object")
    records = payload.get("data")
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise GridMetPayloadError("JSON data must contain exactly one object")
    data = records[0]
    dates = data.get("yyyy-mm-dd")
    if not isinstance(dates, list) or not dates:
        raise GridMetPayloadError("yyyy-mm-dd must be a non-empty array")
    try:
        parsed_dates = []
        for value in dates:
            if not isinstance(value, str):
                raise TypeError
            parsed_dates.append(date.fromisoformat(value))
    except (TypeError, ValueError) as exc:
        raise GridMetPayloadError("yyyy-mm-dd contains an invalid date") from exc
    expected_dates = [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    ]
    if parsed_dates != expected_dates:
        raise GridMetPayloadError(
            f"yyyy-mm-dd does not exactly cover {start_date.isoformat()} through "
            f"{end_date.isoformat()}"
        )
    expected_length = len(dates)
    for key in required_series:
        values = data.get(key)
        if not isinstance(values, list):
            raise GridMetPayloadError(f"{key} must be an array")
        if len(values) != expected_length:
            raise GridMetPayloadError(
                f"{key} length {len(values)} does not match date length {expected_length}"
            )
        try:
            for value in values:
                float(value)
        except (TypeError, ValueError) as exc:
            raise GridMetPayloadError(f"{key} contains a non-numeric value") from exc
    return data


def request_single_location_json(
    url: str,
    *,
    required_series: Sequence[str],
    start_date: date,
    end_date: date,
    get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> Mapping[str, Any]:
    get = requests.get if get is None else get
    sleep = time.sleep if sleep is None else sleep
    operation = "single-location request"
    for attempt in range(MAX_ATTEMPTS):
        response = None
        try:
            response = get(
                url,
                headers={"Accept": "application/json", "referer": "https://wepp.cloud"},
                timeout=SINGLE_LOCATION_TIMEOUT,
                allow_redirects=False,
                stream=True,
            )
            status = int(response.status_code)
            if status != 200:
                if status not in TRANSIENT_HTTP_STATUSES:
                    raise GridMetAcquisitionError(
                        f"GridMET {operation} returned non-retryable HTTP {status}"
                    )
                response.close()
                response = None
                _retry_or_raise(
                    attempt=attempt,
                    operation=operation,
                    reason=f"transient HTTP {status}",
                    sleep=sleep,
                )
                continue
            declared_length = response.headers.get("Content-Length")
            if declared_length is not None:
                try:
                    if int(declared_length) > MAX_SINGLE_LOCATION_BYTES:
                        raise GridMetPayloadError(
                            f"JSON response exceeds {MAX_SINGLE_LOCATION_BYTES} byte limit"
                        )
                except ValueError as exc:
                    raise GridMetPayloadError("invalid Content-Length header") from exc
            content = bytearray()
            try:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    content.extend(chunk)
                    if len(content) > MAX_SINGLE_LOCATION_BYTES:
                        raise GridMetPayloadError(
                            f"JSON response exceeds {MAX_SINGLE_LOCATION_BYTES} byte limit"
                        )
                payload = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                response.close()
                response = None
                _retry_or_raise(
                    attempt=attempt,
                    operation=operation,
                    reason="invalid JSON response",
                    sleep=sleep,
                    cause=exc,
                )
                continue
            try:
                return validate_single_location_payload(
                    payload,
                    required_series,
                    start_date=start_date,
                    end_date=end_date,
                )
            except GridMetPayloadError as exc:
                response.close()
                response = None
                _retry_or_raise(
                    attempt=attempt,
                    operation=operation,
                    reason=str(exc),
                    sleep=sleep,
                    cause=exc,
                )
        except GridMetPayloadError as exc:
            if response is not None:
                response.close()
                response = None
            _retry_or_raise(
                attempt=attempt,
                operation=operation,
                reason=str(exc),
                sleep=sleep,
                cause=exc,
            )
        except _TRANSIENT_REQUEST_ERRORS as exc:
            if response is not None:
                response.close()
                response = None
            _retry_or_raise(
                attempt=attempt,
                operation=operation,
                reason=type(exc).__name__,
                sleep=sleep,
                cause=exc,
            )
        finally:
            if response is not None:
                response.close()
    raise AssertionError("bounded GridMET retry loop exited unexpectedly")
