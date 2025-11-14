from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np

from dateutil.relativedelta import relativedelta

try:  # Optional dependency: only needed when inspecting DSS files
    from pydsstools.heclib.dss import HecDss as _HecDss
    from pydsstools.core import (
        DssPathName as _DssPathName,
        HecTime as _HecTime,
        dss_info as _dss_info,
        setMessageLevel as _set_message_level,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - executed when pydsstools missing
    _PYDSSTOOLS_ERROR = exc
    _HecDss = None  # type: ignore[assignment]
    _DssPathName = None  # type: ignore[assignment]
    _HecTime = None  # type: ignore[assignment]
    _dss_info = None  # type: ignore[assignment]
    _set_message_level = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised via integration tests
    _PYDSSTOOLS_ERROR = None

__all__ = ["build_preview"]

_MISSING_THRESHOLD = -1e30


@dataclass(frozen=True, slots=True)
class DssRecordRow:
    index: int
    pathname: str
    a_part: str
    b_part: str
    c_part: str
    d_part: str
    e_part: str
    f_part: str
    start_display: str
    start_raw: str
    end_display: str
    value_count: int | None
    logical_values: int | None
    stored_values: int | None
    record_type: str
    data_type_code: int | None
    notes: Sequence[str]


@dataclass(frozen=True, slots=True)
class DssPreview:
    filename: str
    file_path: str
    file_size_bytes: int
    file_size_label: str
    modified_label: str
    record_count: int
    record_type_counts: Sequence[tuple[str, int]]
    unique_parts: dict[str, Sequence[str]]
    rows: Sequence[DssRecordRow]


def build_preview(path: str) -> DssPreview:
    """
    Parse a DSS file and return a summary suitable for rendering in the browse microservice.
    """
    runtime = _require_runtime()
    normalized_path = str(Path(path).resolve())
    stats = Path(normalized_path).stat()

    _silence_messages(runtime.set_message_level)

    a_parts: set[str] = set()
    b_parts: set[str] = set()
    c_parts: set[str] = set()
    d_parts: set[str] = set()
    e_parts: set[str] = set()
    f_parts: set[str] = set()
    rows: list[DssRecordRow] = []

    with runtime.hec_dss.Open(normalized_path, mode="r") as fid:
        pathnames = sorted(fid.getPathnameList("/*/*/*/*/*/*/"))
        for index, pathname in enumerate(pathnames, start=1):
            parsed = runtime.dss_pathname(pathname)
            a_part = parsed.getAPart()
            b_part = parsed.getBPart()
            c_part = parsed.getCPart()
            d_part = parsed.getDPart()
            e_part = parsed.getEPart()
            f_part = parsed.getFPart()

            a_parts.add(a_part)
            b_parts.add(b_part)
            c_parts.add(c_part)
            d_parts.add(d_part)
            e_parts.add(e_part)
            f_parts.add(f_part)

            record_type = fid._record_type(pathname) or ""
            data_type_code: int | None = None
            logical_values: int | None = None
            stored_values: int | None = None
            notes: list[str] = []

            try:
                info = runtime.dss_info(fid, pathname)
            except Exception as exc:  # pragma: no cover - defensive
                notes.append(f"Metadata unavailable ({exc})")
                row = _row_from_parts(
                    index=index,
                    pathname=pathname,
                    a_part=a_part,
                    b_part=b_part,
                    c_part=c_part,
                    d_part=d_part,
                    e_part=e_part,
                    f_part=f_part,
                    start_dt=None,
                    end_dt=None,
                    interval_label=e_part,
                    record_type=record_type,
                    data_type_code=None,
                    logical_values=None,
                    stored_values=None,
                    notes=notes,
                )
                rows.append(row)
                continue

            data_type_code = getattr(info, "dataType", None)
            logical_raw = getattr(info, "logicalNumberValues", 0)
            stored_raw = getattr(info, "numberValues", 0)
            logical_values = int(logical_raw) if logical_raw else None
            stored_values = int(stored_raw) if stored_raw else None

            start_dt = _parse_d_part(d_part, runtime.hec_time)
            if start_dt is None and d_part:
                notes.append("Unable to parse D-part date")

            summary = None
            try:
                summary = _summarize_record(fid, pathname, runtime.hec_time)
            except Exception:  # pragma: no cover - defensive
                summary = None

            actual_start = summary.start if summary else start_dt
            if _is_irregular_interval(e_part):
                notes.append("Irregular interval")

            end_dt = summary.end if summary else _estimate_end(start_dt, e_part, stored_values)
            if end_dt is None and stored_values and stored_values > 1 and not _is_irregular_interval(e_part):
                notes.append("Unable to estimate end date")

            row = _row_from_parts(
                index=index,
                pathname=pathname,
                a_part=a_part,
                b_part=b_part,
                c_part=c_part,
                d_part=d_part,
                e_part=e_part,
                f_part=f_part,
                start_dt=actual_start,
                end_dt=end_dt,
                interval_label=e_part,
                record_type=record_type,
                data_type_code=data_type_code,
                logical_values=logical_values,
                stored_values=summary.count if summary else stored_values,
                notes=notes,
            )
            rows.append(row)

    type_counts = Counter(row.record_type or "Unknown" for row in rows)
    part_summary = {
        "A": sorted(filter(None, a_parts)),
        "B": sorted(filter(None, b_parts)),
        "C": sorted(filter(None, c_parts)),
        "D": sorted(filter(None, d_parts)),
        "E": sorted(filter(None, e_parts)),
        "F": sorted(filter(None, f_parts)),
    }

    preview = DssPreview(
        filename=Path(normalized_path).name,
        file_path=normalized_path,
        file_size_bytes=stats.st_size,
        file_size_label=_format_size(stats.st_size),
        modified_label=_format_mtime(stats.st_mtime),
        record_count=len(rows),
        record_type_counts=tuple(sorted(type_counts.items())),
        unique_parts=part_summary,
        rows=tuple(rows),
    )
    return preview


def _row_from_parts(
    *,
    index: int,
    pathname: str,
    a_part: str,
    b_part: str,
    c_part: str,
    d_part: str,
    e_part: str,
    f_part: str,
    start_dt: datetime | None,
    end_dt: datetime | None,
    interval_label: str,
    record_type: str,
    data_type_code: int | None,
    logical_values: int | None,
    stored_values: int | None,
    notes: Sequence[str],
) -> DssRecordRow:
    start_display = _format_date(start_dt) or (d_part or "—")
    end_display = _format_date(end_dt) or ("—" if not end_dt else "")
    start_raw = d_part or ""
    value_count = logical_values or stored_values
    normalized_notes = tuple(note for note in notes if note)

    return DssRecordRow(
        index=index,
        pathname=pathname,
        a_part=a_part,
        b_part=b_part,
        c_part=c_part,
        d_part=d_part,
        e_part=interval_label,
        f_part=f_part,
        start_display=start_display,
        start_raw=start_raw,
        end_display=end_display,
        value_count=value_count,
        logical_values=logical_values,
        stored_values=stored_values,
        record_type=record_type or "Unknown",
        data_type_code=data_type_code,
        notes=normalized_notes,
    )


def _parse_d_part(value: str, hec_time_cls: type | None) -> datetime | None:
    if not value or hec_time_cls is None:
        return None
    try:
        hec_time = hec_time_cls(value)
    except Exception:
        return None
    return hec_time.python_datetime


def _estimate_end(start_dt: datetime | None, e_part: str, count: int | None) -> datetime | None:
    if start_dt is None or not count or count <= 1:
        return start_dt
    increment = _parse_interval(e_part)
    if increment is None:
        return None
    steps = count - 1
    if isinstance(increment, relativedelta):
        cursor = start_dt
        for _ in range(steps):
            cursor = cursor + increment
        return cursor
    return start_dt + increment * steps


def _parse_interval(e_part: str) -> timedelta | relativedelta | None:
    if not e_part:
        return None
    normalized = e_part.strip().upper()
    if _is_irregular_interval(normalized):
        return None
    normalized = normalized.replace("-", "")
    digits = []
    letters = []
    for char in normalized:
        if char.isdigit() and not letters:
            digits.append(char)
        else:
            letters.append(char)
    if not digits or not letters:
        return None
    quantity = int("".join(digits))
    unit = "".join(letters)
    if not quantity:
        return None

    timedelta_units = {
        "SEC": "seconds",
        "SECS": "seconds",
        "SECOND": "seconds",
        "SECONDS": "seconds",
        "MIN": "minutes",
        "MINS": "minutes",
        "MINUTE": "minutes",
        "MINUTES": "minutes",
        "H": "hours",
        "HR": "hours",
        "HRS": "hours",
        "HOUR": "hours",
        "HOURS": "hours",
        "DAY": "days",
        "DAYS": "days",
        "WEEK": "weeks",
        "WEEKS": "weeks",
    }
    relativedelta_units = {
        "MON": "months",
        "MONTH": "months",
        "MONTHS": "months",
        "YR": "years",
        "YRS": "years",
        "YEAR": "years",
        "YEARS": "years",
    }

    if unit in timedelta_units:
        kwargs = {timedelta_units[unit]: quantity}
        return timedelta(**kwargs)
    if unit in relativedelta_units:
        kwargs = {relativedelta_units[unit]: quantity}
        return relativedelta(**kwargs)
    return None


def _is_irregular_interval(value: str) -> bool:
    return value.strip().upper().startswith("IR") if value else False


def _format_date(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d")


def _format_size(size: int) -> str:
    units = ["bytes", "KB", "MB", "GB", "TB"]
    amount = float(size)
    unit_index = 0
    while amount >= 1024 and unit_index < len(units) - 1:
        amount /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{int(amount)} {units[unit_index]}"
    return f"{amount:.1f} {units[unit_index]}"


def _format_mtime(timestamp: float) -> str:
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def _silence_messages(setter: Callable[[int, int], Any] | None) -> None:
    if setter is None:
        return
    for method_id in range(0, 19):
        try:
            setter(method_id, 0)
        except Exception:  # pragma: no cover - defensive
            break


def _require_runtime():
    if (
        _HecDss is None
        or _DssPathName is None
        or _HecTime is None
        or _dss_info is None
        or _set_message_level is None
    ):
        raise ModuleNotFoundError(
            "pydsstools is required to inspect DSS files"
        ) from _PYDSSTOOLS_ERROR
    return _DssRuntime(
        hec_dss=_HecDss,
        dss_pathname=_DssPathName,
        dss_info=_dss_info,
        hec_time=_HecTime,
        set_message_level=_set_message_level,
    )


@dataclass(frozen=True, slots=True)
class _DssRuntime:
    hec_dss: Any
    dss_pathname: Any
    dss_info: Any
    hec_time: Any
    set_message_level: Callable[[int, int], Any]


@dataclass(frozen=True)
class _RecordSummary:
    start: datetime
    end: datetime
    count: int


def _summarize_record(fid: Any, pathname: str, hec_time_cls: type | None) -> _RecordSummary | None:
    try:
        ts = fid.read_ts(pathname)
    except Exception:
        return None

    values = getattr(ts, "values", None)
    if values is None:
        return None

    arr = np.asarray(values, dtype=float)
    valid_mask = arr > _MISSING_THRESHOLD
    if not np.any(valid_mask):
        return None

    times = getattr(ts, "times", None)
    if times:
        converted = [_hectime_value_to_datetime(value, hec_time_cls) for value in times]
        filtered = [dt for dt, flag in zip(converted, valid_mask) if dt is not None and flag]
        if not filtered:
            return None
        return _RecordSummary(filtered[0], filtered[-1], len(filtered))

    start_dt = _hectime_to_datetime(getattr(ts, "startDateTime", None), hec_time_cls)
    interval_minutes = getattr(ts, "interval", 0) or 0
    valid_indices = np.where(valid_mask)[0]
    if valid_indices.size == 0 or start_dt is None or interval_minutes <= 0:
        return None

    first_idx = int(valid_indices[0])
    last_idx = int(valid_indices[-1])
    adjusted_start = start_dt + timedelta(minutes=interval_minutes * first_idx)
    end_dt = adjusted_start + timedelta(minutes=interval_minutes * (last_idx - first_idx)) if last_idx >= first_idx else adjusted_start
    count = int(valid_indices.size)
    return _RecordSummary(adjusted_start, end_dt, count)


def _hectime_to_datetime(text: str | None, hec_time_cls: type | None) -> datetime | None:
    if not text or hec_time_cls is None:
        return None
    try:
        hec_time = hec_time_cls(text)
    except Exception:
        return None
    return getattr(hec_time, "python_datetime", None)


def _hectime_value_to_datetime(value: int, hec_time_cls: type | None) -> datetime | None:
    if hec_time_cls is None:
        return None
    getter = getattr(hec_time_cls, "getPyDateTimeFromValue", None)
    if getter is None:
        return None
    try:
        return getter(value)
    except Exception:
        return None
