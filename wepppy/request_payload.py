"""Framework-independent mutation payload validation (MRS-01)."""
from __future__ import annotations

import json
import math
from urllib.parse import unquote_to_bytes
from typing import Any, Iterable


class RequestPayloadError(Exception):
    """Malformed supplied input; never an absent/default request."""

    code = "invalid_request"
    message = "Invalid request payload."

    def __init__(self, field: str | None = None):
        super().__init__(self.message)
        self.field = field

    def envelope(self) -> dict:
        error = {"code": self.code, "message": self.message}
        if self.field is not None:
            error["details"] = {"field": self.field}
        return {"error": error}


def media_type(value: str) -> str:
    return value.split(";", 1)[0].strip().lower()


def is_json_media(value: str) -> bool:
    return value == "application/json" or (value.startswith("application/") and value.endswith("+json"))


def validate_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise RequestPayloadError()
    if isinstance(value, dict):
        for item in value.values():
            validate_finite(item)
    elif isinstance(value, list):
        for item in value:
            validate_finite(item)


def decode_json(body: bytes, *, allow_list: bool = False) -> Any:
    if not body:
        return {}
    try:
        value = json.loads(body)
    except (ValueError, UnicodeError) as exc:
        raise RequestPayloadError() from exc
    if not isinstance(value, dict) and not (allow_list and isinstance(value, list)):
        raise RequestPayloadError()
    validate_finite(value)
    return value


def validate_form_encoding(body: bytes) -> None:
    try:
        unquote_to_bytes(body).decode("utf-8")
    except UnicodeError as exc:
        raise RequestPayloadError() from exc


def scalar_boolean(value: Any, *, trim_strings: bool = True, extra_tokens: bool = False) -> Any:
    # Null/blank are deliberate domain sentinels; callers retain their policy.
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip() if trim_strings else value
        if token == "":
            return token
        true = {"true", "1", "yes", "on"}
        false = {"false", "0", "no", "off"}
        if extra_tokens:
            true.add("y")
            false.add("n")
        if token.lower() in true:
            return True
        if token.lower() in false:
            return False
    elif isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    raise RequestPayloadError()


def normalize_value(value: Any, *, coerce_boolean: bool, trim_strings: bool) -> Any:
    if coerce_boolean:
        return scalar_boolean(value, trim_strings=trim_strings)
    if isinstance(value, dict):
        return {key: normalize_value(item, coerce_boolean=False, trim_strings=trim_strings)
                for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        values = [normalize_value(item, coerce_boolean=False, trim_strings=trim_strings) for item in value]
        return values[0] if len(values) == 1 else values
    return value.strip() if trim_strings and isinstance(value, str) else value


def normalize_payload(data: dict, *, boolean_fields: Iterable[str] = (), trim_strings: bool = True,
                      form: bool = False, extra_boolean_tokens: bool = False, blank_false_fields: Iterable[str] = ()) -> dict:
    fields = set(boolean_fields)
    blank_false = set(blank_false_fields)
    result = {}
    for key, value in data.items():
        if key not in fields:
            result[key] = normalize_value(value, coerce_boolean=False, trim_strings=trim_strings)
            continue
        try:
            values = value if form and isinstance(value, list) else [value]
            normalized = [scalar_boolean(item, trim_strings=trim_strings, extra_tokens=extra_boolean_tokens)
                          for item in values]
            compared = [False if item == "" and key in blank_false else item for item in normalized]
            if not compared or any(item != compared[0] for item in compared[1:]):
                raise RequestPayloadError()
            result[key] = compared[0] if len(compared) > 1 else normalized[0]
        except RequestPayloadError as exc:
            raise RequestPayloadError(key) from exc
    pairs = [(name, name + "_hillslopes") for name in ("clean", "prep", "run")]
    pairs += [("checkbox_burn_" + name, "burn_" + name) for name in ("shrubs", "grass")]
    validate_boolean_aliases(result, [(a, b) for a, b in pairs if a in fields and b in fields])
    return result


def validate_boolean_aliases(payload: dict, pairs: Iterable[tuple[str, str]]) -> None:
    for canonical, alias in pairs:
        a, b = payload.get(canonical), payload.get(alias)
        if a is not None and b is not None and bool(a) != bool(b):
            raise RequestPayloadError(canonical)
