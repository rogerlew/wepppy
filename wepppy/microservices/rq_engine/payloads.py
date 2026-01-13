from __future__ import annotations

from typing import Any, Iterable

from fastapi import Request
from starlette.datastructures import FormData

_TRUE_TOKENS = {"1", "true", "yes", "on"}
_FALSE_TOKENS = {"0", "false", "no", "off"}


def _normalize_scalar(
    value: Any,
    *,
    coerce_boolean: bool,
    trim_strings: bool,
) -> Any:
    if isinstance(value, str):
        token = value.strip() if trim_strings else value
        if coerce_boolean:
            lowered = token.lower()
            if lowered in _TRUE_TOKENS:
                return True
            if lowered in _FALSE_TOKENS:
                return False
        return token
    if coerce_boolean and isinstance(value, (int, float)):
        return bool(value)
    return value


def _normalize_payload_value(
    value: Any,
    *,
    coerce_boolean: bool,
    trim_strings: bool,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_payload_value(
                inner,
                coerce_boolean=coerce_boolean,
                trim_strings=trim_strings,
            )
            for key, inner in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        normalized = [
            _normalize_payload_value(
                item,
                coerce_boolean=coerce_boolean,
                trim_strings=trim_strings,
            )
            for item in value
        ]
        if len(normalized) == 1:
            return normalized[0]
        return normalized
    return _normalize_scalar(
        value,
        coerce_boolean=coerce_boolean,
        trim_strings=trim_strings,
    )


def _form_to_dict(form: FormData) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in form.multi_items():
        if key in data:
            existing = data[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                data[key] = [existing, value]
        else:
            data[key] = value
    return data


async def parse_request_payload(
    request: Request,
    *,
    boolean_fields: Iterable[str] | None = None,
    trim_strings: bool = True,
) -> dict[str, Any]:
    boolean_field_set = set(boolean_fields or [])
    data: dict[str, Any] = {}

    try:
        raw_json = await request.json()
    except Exception:
        raw_json = None

    if isinstance(raw_json, dict):
        data.update(raw_json)

    if not data:
        try:
            form = await request.form()
        except Exception:
            form = None
        if form:
            data.update(_form_to_dict(form))

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        normalized[key] = _normalize_payload_value(
            value,
            coerce_boolean=key in boolean_field_set,
            trim_strings=trim_strings,
        )
    return normalized


__all__ = ["parse_request_payload"]
