"""Typed parsing and deterministic INI serialization for project configuration."""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
import json
import math
import re
from typing import TypeAlias

from wepppy.project_config_sanitization import assert_materialization_safe

__all__ = [
    "CanonicalConfigError",
    "CanonicalScalar",
    "CanonicalValue",
    "normalize_source_text",
    "parse_config_text",
    "serialize_config",
    "validate_canonical_config_text",
]

CanonicalScalar: TypeAlias = None | bool | int | float | str
CanonicalValue: TypeAlias = CanonicalScalar | list[CanonicalScalar]

_SECTION_RE = re.compile(r"^\[([^\[\]]+)\]$")
_ASSIGNMENT_RE = re.compile(r"^([^=:#]+?)\s*=\s*(.*)$")
_INTEGER_RE = re.compile(r"[+-]?\d+")
_FLOAT_RE = re.compile(
    r"[+-]?(?:(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?|\d+[eE][+-]?\d+)"
)


class CanonicalConfigError(ValueError):
    """Raised when config text cannot be represented without guessing."""


def _inline_comment_index(value: str) -> int | None:
    quote: str | None = None
    escaped = False
    depth = 0
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if quote is not None:
            if character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character == "[":
            depth += 1
        elif character == "]":
            depth = max(0, depth - 1)
        elif character in {"#", ";"} and depth == 0 and (index == 0 or value[index - 1].isspace()):
            return index
    return None


def _validate_scalar(value: object, *, location: str) -> CanonicalScalar:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalConfigError(f"{location}: non-finite floats are unsupported")
        return value
    raise CanonicalConfigError(f"{location}: unsupported value type {type(value).__name__}")


def _parse_value(raw_value: str, *, location: str, allow_legacy: bool) -> CanonicalValue:
    value = raw_value.strip()
    if not value:
        if allow_legacy:
            return None
        raise CanonicalConfigError(f"{location}: no-value options are unsupported")
    if _inline_comment_index(value) is not None:
        raise CanonicalConfigError(f"{location}: inline comments are unsupported")

    lowered = value.casefold()
    if lowered in {"none", "null"}:
        if not allow_legacy and value != "None":
            raise CanonicalConfigError(f"{location}: null must be encoded as None")
        return None
    if lowered in {"true", "false"}:
        if not allow_legacy and value not in {"true", "false"}:
            raise CanonicalConfigError(f"{location}: booleans must be lowercase")
        return lowered == "true"
    if _INTEGER_RE.fullmatch(value):
        parsed_int = int(value)
        if not allow_legacy and value != str(parsed_int):
            raise CanonicalConfigError(f"{location}: integer is not canonical")
        return parsed_int
    if _FLOAT_RE.fullmatch(value):
        parsed_float = float(value)
        if not math.isfinite(parsed_float):
            raise CanonicalConfigError(f"{location}: non-finite floats are unsupported")
        if not allow_legacy and value != repr(parsed_float):
            raise CanonicalConfigError(f"{location}: float is not canonical")
        return parsed_float
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed_list = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise CanonicalConfigError(f"{location}: invalid list literal") from exc
        if not isinstance(parsed_list, list):
            raise CanonicalConfigError(f"{location}: only list literals are supported")
        normalized = [_validate_scalar(item, location=f"{location}[]") for item in parsed_list]
        if not allow_legacy and value != _serialize_list(normalized):
            raise CanonicalConfigError(f"{location}: list is not canonical")
        return normalized
    if allow_legacy and value.startswith("(") and value.endswith(")"):
        try:
            parsed_tuple = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise CanonicalConfigError(f"{location}: invalid legacy tuple literal") from exc
        if not isinstance(parsed_tuple, tuple):
            raise CanonicalConfigError(f"{location}: unsupported legacy literal")
        return [_validate_scalar(item, location=f"{location}[]") for item in parsed_tuple]
    if value[0] in {'"', "'"}:
        try:
            parsed_string = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise CanonicalConfigError(f"{location}: invalid quoted string") from exc
        if not isinstance(parsed_string, str):
            raise CanonicalConfigError(f"{location}: unsupported literal")
        if not allow_legacy and value != _serialize_string(parsed_string):
            raise CanonicalConfigError(f"{location}: string is not canonical")
        return parsed_string
    if allow_legacy:
        return value
    raise CanonicalConfigError(f"{location}: unquoted strings are unsupported")


def _serialize_string(value: str) -> str:
    if "\n" in value or "\r" in value:
        raise CanonicalConfigError("multiline strings are unsupported")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _serialize_scalar(value: CanonicalScalar) -> str:
    value = _validate_scalar(value, location="value")
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    return _serialize_string(value)


def _serialize_list(value: Sequence[CanonicalScalar]) -> str:
    encoded: list[str] = []
    for item in value:
        checked = _validate_scalar(item, location="list item")
        if isinstance(checked, bool):
            encoded.append("True" if checked else "False")
        else:
            encoded.append(_serialize_scalar(checked))
    return f"[{', '.join(encoded)}]"


def _serialize_value(value: CanonicalValue) -> str:
    if isinstance(value, list):
        return _serialize_list(value)
    return _serialize_scalar(value)


def parse_config_text(text: str) -> dict[str, dict[str, CanonicalValue]]:
    """Parse canonical config text and reject ambiguity or collisions."""

    if text.startswith("\ufeff"):
        raise CanonicalConfigError("UTF-8 byte-order marks are unsupported")
    if "\r" in text:
        raise CanonicalConfigError("only LF line endings are supported")

    result: dict[str, dict[str, CanonicalValue]] = {}
    section_casefold: dict[str, str] = {}
    option_casefold: dict[str, dict[str, str]] = {}
    current_section: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        section_match = _SECTION_RE.fullmatch(stripped)
        if section_match is not None:
            section = section_match.group(1).strip()
            folded = section.casefold()
            if section in result or folded in section_casefold:
                raise CanonicalConfigError(f"line {line_number}: duplicate or case-colliding section {section!r}")
            result[section] = {}
            option_casefold[section] = {}
            section_casefold[folded] = section
            current_section = section
            continue
        if current_section is None:
            raise CanonicalConfigError(f"line {line_number}: option appears before a section")
        assignment = _ASSIGNMENT_RE.fullmatch(line)
        if assignment is None:
            raise CanonicalConfigError(f"line {line_number}: unsupported config syntax")
        option, raw_value = assignment.groups()
        option = option.strip()
        folded = option.casefold()
        if option in result[current_section] or folded in option_casefold[current_section]:
            raise CanonicalConfigError(f"line {line_number}: duplicate or case-colliding option {option!r}")
        result[current_section][option] = _parse_value(
            raw_value,
            location=f"line {line_number} [{current_section}] {option}",
            allow_legacy=False,
        )
        option_casefold[current_section][folded] = option
    return result


def serialize_config(config: Mapping[str, Mapping[str, CanonicalValue]]) -> bytes:
    """Serialize a typed map to the contract's byte-identical INI form."""

    section_names = list(config)
    if len({name.casefold() for name in section_names}) != len(section_names):
        raise CanonicalConfigError("duplicate or case-colliding sections")
    chunks: list[str] = []
    for section in sorted(section_names):
        if not section or any(character in section for character in "[]\r\n"):
            raise CanonicalConfigError(f"invalid section name {section!r}")
        options = config[section]
        option_names = list(options)
        if len({name.casefold() for name in option_names}) != len(option_names):
            raise CanonicalConfigError(f"[{section}]: duplicate or case-colliding options")
        lines = [f"[{section}]"]
        for option in sorted(option_names):
            if not option or any(character in option for character in "=:#\r\n"):
                raise CanonicalConfigError(f"[{section}]: invalid option name {option!r}")
            lines.append(f"{option} = {_serialize_value(options[option])}")
        chunks.append("\n".join(lines))
    text = "\n\n".join(chunks) + "\n"
    assert_materialization_safe(text)
    return text.encode("utf-8")


def validate_canonical_config_text(text: str) -> dict[str, dict[str, CanonicalValue]]:
    """Return the typed map only when input is already byte-canonical."""

    parsed = parse_config_text(text)
    if serialize_config(parsed) != text.encode("utf-8"):
        raise CanonicalConfigError("sections, options, whitespace, or terminal LF are not canonical")
    return parsed


def normalize_source_text(text: str) -> str:
    """Normalize legacy lexical forms while preserving source order/comments."""

    output: list[str] = []
    sections: dict[str, str] = {}
    options: dict[str, dict[str, str]] = {}
    current_section: str | None = None
    for line_number, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            output.append(line.rstrip())
            continue
        section_match = _SECTION_RE.fullmatch(stripped)
        if section_match is not None:
            section = section_match.group(1).strip()
            folded = section.casefold()
            if folded in sections:
                raise CanonicalConfigError(
                    f"line {line_number + 1}: duplicate or case-colliding section {section!r}"
                )
            sections[folded] = section
            options[section] = {}
            current_section = section
            output.append(f"[{section}]")
            continue
        if current_section is None:
            raise CanonicalConfigError(f"line {line_number + 1}: option appears before a section")
        assignment = _ASSIGNMENT_RE.fullmatch(line)
        if assignment is None:
            raise CanonicalConfigError(f"line {line_number + 1}: unsupported source syntax")
        option, raw_value = assignment.groups()
        option = option.strip()
        folded = option.casefold()
        if folded in options[current_section]:
            raise CanonicalConfigError(
                f"line {line_number + 1}: duplicate or case-colliding option {option!r}"
            )
        options[current_section][folded] = option
        comment_index = _inline_comment_index(raw_value)
        comment: str | None = None
        if comment_index is not None:
            comment = raw_value[comment_index:].strip()
            raw_value = raw_value[:comment_index].rstrip()
        value = _parse_value(raw_value, location=f"line {line_number + 1} {option}", allow_legacy=True)
        if comment is not None:
            output.append(f"# {comment.lstrip('#;').strip()}")
        output.append(f"{option} = {_serialize_value(value)}")
    return "\n".join(output) + "\n"
