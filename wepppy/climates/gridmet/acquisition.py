"""Shared failure contract for GridMET HTTP acquisition."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, nullcontext
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from wepppy.climates.gridmet.admission import GridMetAdmissionConfig

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
        if cause is None or isinstance(cause, requests.exceptions.RequestException):
            # Requests exceptions may contain the complete private query URL.
            raise error from None
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


def _prepare_admission(admission: GridMetAdmissionConfig | None, timeout):
    if admission is None:
        return None, None
    # Local import avoids a cycle: admission errors share our acquisition base.
    from wepppy.climates.gridmet.admission import GridMetAdmissionController

    admission.validate_http_timeout(timeout)
    deadline = time.monotonic() + admission.wait_timeout_seconds
    return GridMetAdmissionController(admission), deadline


@contextmanager
def _admitted_response(get, url, *, controller, deadline, request_kind, **kwargs):
    context = (
        nullcontext()
        if controller is None
        else controller.acquire(request_kind=request_kind, deadline=deadline)
    )
    with context as permit:
        response = None
        try:
            if permit is not None:
                permit.check()
            response = get(url, **kwargs)
            if permit is not None:
                permit.check()
            yield response, permit
        finally:
            # Close the upstream connection while its permit is still held.
            if response is not None:
                response.close()
            if permit is not None:
                permit.check()


def _checked_response_chunks(response, permit, *, chunk_size) -> Iterator[bytes]:
    chunks = iter(response.iter_content(chunk_size=chunk_size))
    while True:
        if permit is not None:
            permit.check()
        try:
            chunk = next(chunks)
        except StopIteration:
            if permit is not None:
                permit.check()
            return
        if permit is not None:
            permit.check()
        yield chunk


def request_single_location_json(
    url: str,
    *,
    required_series: Sequence[str],
    start_date: date,
    end_date: date,
    get: Callable[..., Any] | None = None,
    sleep: Callable[[float], None] | None = None,
    admission: GridMetAdmissionConfig | None = None,
) -> Mapping[str, Any]:
    get = requests.get if get is None else get
    sleep = time.sleep if sleep is None else sleep
    operation = "single-location request"
    controller, deadline = _prepare_admission(admission, SINGLE_LOCATION_TIMEOUT)
    for attempt in range(MAX_ATTEMPTS):
        try:
            with _admitted_response(
                get,
                url,
                controller=controller,
                deadline=deadline,
                request_kind="point",
                headers={"Accept": "application/json", "referer": "https://wepp.cloud"},
                timeout=SINGLE_LOCATION_TIMEOUT,
                allow_redirects=False,
                stream=True,
            ) as (response, permit):
                status = int(response.status_code)
                if status != 200:
                    if status not in TRANSIENT_HTTP_STATUSES:
                        raise GridMetAcquisitionError(
                            f"GridMET {operation} returned non-retryable HTTP {status}"
                        )
                    raise GridMetPayloadError(f"transient HTTP {status}")
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
                for chunk in _checked_response_chunks(
                    response, permit, chunk_size=64 * 1024
                ):
                    content.extend(chunk)
                    if len(content) > MAX_SINGLE_LOCATION_BYTES:
                        raise GridMetPayloadError(
                            f"JSON response exceeds {MAX_SINGLE_LOCATION_BYTES} byte limit"
                        )
            # Parsing and validation do not occupy an upstream connection.
            try:
                payload = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise GridMetPayloadError("invalid JSON response") from exc
            return validate_single_location_payload(
                payload,
                required_series,
                start_date=start_date,
                end_date=end_date,
            )
        except GridMetPayloadError as exc:
            _retry_or_raise(
                attempt=attempt,
                operation=operation,
                reason=str(exc),
                sleep=sleep,
                cause=exc,
            )
        except _TRANSIENT_REQUEST_ERRORS as exc:
            _retry_or_raise(
                attempt=attempt,
                operation=operation,
                reason=type(exc).__name__,
                sleep=sleep,
                cause=exc,
            )
    raise AssertionError("bounded GridMET retry loop exited unexpectedly")
