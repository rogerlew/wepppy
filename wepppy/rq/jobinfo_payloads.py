from __future__ import annotations

"""Shared helpers for parsing job info/job status request payloads."""

from typing import Any, Iterable, Mapping, Sequence


__all__ = ["extract_job_ids", "normalize_job_id_inputs"]


def normalize_job_id_inputs(raw_values: Any) -> list[str]:
    normalized: list[str] = []
    if raw_values is None:
        return normalized

    seen: set[str] = set()

    def _consume(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return
            if "," in stripped:
                for part in stripped.split(","):
                    _consume(part)
                return
            if stripped in seen:
                return
            seen.add(stripped)
            normalized.append(stripped)
            return
        if isinstance(value, dict):
            for payload in value.values():
                _consume(payload)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                _consume(item)
            return

        job_id = str(value).strip()
        if not job_id or job_id in seen:
            return
        seen.add(job_id)
        normalized.append(job_id)

    _consume(raw_values)
    return normalized


def _list_from_query_args(query_args: Any, key: str) -> list[Any]:
    if query_args is None:
        return []
    if hasattr(query_args, "getlist"):
        values = query_args.getlist(key)
        if values:
            return list(values)
        if hasattr(query_args, "get"):
            value = query_args.get(key)
            if value is not None and value != "":
                return [value]
        return []
    if isinstance(query_args, Mapping):
        value = query_args.get(key)
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]
    if isinstance(query_args, Sequence) and not isinstance(query_args, (str, bytes, bytearray)):
        return [value for query_key, value in query_args if query_key == key]
    return []


def extract_job_ids(payload: Any | None = None, query_args: Any | None = None) -> list[str]:
    job_ids: list[str] = []

    if payload is not None:
        if isinstance(payload, dict):
            if any(key in payload for key in ("job_ids", "jobs", "ids")):
                job_ids = normalize_job_id_inputs(
                    payload.get("job_ids") or payload.get("jobs") or payload.get("ids")
                )
            else:
                job_ids = normalize_job_id_inputs(list(payload.values()))
        else:
            job_ids = normalize_job_id_inputs(payload)

    if not job_ids and query_args is not None:
        arg_values = _list_from_query_args(query_args, "job_id")
        if not arg_values:
            arg_values = _list_from_query_args(query_args, "job_ids")
        job_ids = normalize_job_id_inputs(arg_values)

    return job_ids
